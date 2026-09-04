"""Automated tests for the RecoverAI PAYMENT_LINK recovery execution path.

Covers the requirement that a PAYMENT_LINK is:
  - safe by default (RECOVERY_DRY_RUN=true -> never calls Razorpay, simulated)
  - only reaching the real Razorpay TEST/SANDBOX path when an operator
    explicitly disables DRY_RUN (RECOVERY_DRY_RUN=false)
  - always gated by the Action Firewall (never bypassed)
  - idempotent (no duplicate payment links)
  - recorded without exposing secrets
  - never marking the payment recovered just because a link was created

The Razorpay API is always mocked; no real payment link is ever created and no
real customer-facing payment API is ever called.
"""

import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Payment, RecoveryExecution
from app.services.recovery_execution_service import (
    BLOCKED,
    DRY_RUN,
    LIVE,
    SIMULATED,
    SUCCESS,
    FAILED,
    execute_recovery_action,
)
from app.config import RECOVERY_DRY_RUN


MARKER = "TEST_PAYMENT_LINK"

class TestRecoveryPaymentLinkExecution(unittest.TestCase):
    """Payment-link execution engine — DRY_RUN safety and real (sandbox) path."""

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()

    def tearDown(self):
        pay_ids = self.db.query(Payment.id).filter(
            Payment.failure_reason == MARKER
        )
        self.db.query(RecoveryExecution).filter(
            RecoveryExecution.payment_id.in_(pay_ids)
        ).delete(synchronize_session=False)
        self.db.query(Payment).filter(
            Payment.failure_reason == MARKER
        ).delete(synchronize_session=False)
        self.db.commit()
        self.db.close()

    def _create_payment(self, **overrides) -> Payment:
        defaults = dict(
            amount=15000.0,
            failure_reason=MARKER,
            customer_type="Regular",
            payment_status="failed",
            recovery_status="PENDING",
            recommended_action="PAYMENT_LINK",
            confidence=0.92,
            recovery_probability=0.85,
            expected_recovery=12750.0,
            risk_level="LOW",
            retry_count=0,
            previous_recovery_attempts=0,
        )
        defaults.update(overrides)
        payment = Payment(**defaults)
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        return payment

    # ------------------------------------------------------------------
    # DRY_RUN safety (default)
    # ------------------------------------------------------------------
    def test_1_dry_run_true_no_razorpay_call(self):
        """RECOVERY_DRY_RUN default true: PAYMENT_LINK simulates, no Razorpay call."""
        self.assertTrue(RECOVERY_DRY_RUN in ("", "true"))
        payment = self._create_payment()
        with patch("app.services.razorpay_service.create_payment_link") as mock_link:
            result = execute_recovery_action(
                payment=payment, action="PAYMENT_LINK", db=self.db
            )
        mock_link.assert_not_called()
        self.assertTrue(result["executed"])
        self.assertEqual(result["execution_mode"], DRY_RUN)
        self.assertEqual(result["status"], SIMULATED)
        self.assertTrue(result["simulated"])
        # Sends a clear signal that a real link was NOT created.
        self.assertIsNone(result["provider_reference_id"])
        self.assertIsNone(result["provider"])

    def test_2_live_rejected_when_dry_run_enabled(self):
        """With RECOVERY_DRY_RUN=true, requesting LIVE is refused safely."""
        with patch.dict(os.environ, {"RECOVERY_DRY_RUN": "true"}, clear=False):
            payment = self._create_payment()
            with self.assertRaises(ValueError):
                execute_recovery_action(
                    payment=payment, action="PAYMENT_LINK",
                    execution_mode=LIVE, db=self.db,
                )

    # ------------------------------------------------------------------
    # Firewall gating
    # ------------------------------------------------------------------
    def test_3_firewall_approval_proceeds(self):
        """With DRY_RUN disabled, an approved PAYMENT_LINK proceeds to the real path."""
        payment = self._create_payment()
        with patch.dict(os.environ, {"RECOVERY_DRY_RUN": "false"}, clear=False):
            with patch(
                "app.services.razorpay_service.create_payment_link",
            ) as mock_link:
                mock_link.return_value = {
                    "id": "plink_test_abc123",
                    "short_url": "https://rzp.io/l/testabc",
                    "amount": 1500000,
                    "currency": "INR",
                    "status": "created",
                    "accept_partial": False,
                }
                result = execute_recovery_action(
                    payment=payment, action="PAYMENT_LINK",
                    execution_mode=LIVE, db=self.db,
                )
        mock_link.assert_called_once()
        self.assertTrue(result["executed"])
        self.assertEqual(result["execution_mode"], LIVE)
        self.assertEqual(result["status"], SUCCESS)
        self.assertFalse(result["simulated"])
        self.assertEqual(result["provider"], "razorpay")
        self.assertEqual(result["provider_reference_id"], "plink_test_abc123")

    def test_4_low_confidence_blocked(self):
        """Confidence below threshold -> firewall rejects, no Razorpay call."""
        payment = self._create_payment(confidence=0.5)
        with patch.dict(os.environ, {"RECOVERY_DRY_RUN": "false"}, clear=False):
            with patch("app.services.razorpay_service.create_payment_link") as mock_link:
                result = execute_recovery_action(
                    payment=payment, action="PAYMENT_LINK",
                    execution_mode=LIVE, db=self.db,
                )
        mock_link.assert_not_called()
        self.assertFalse(result["executed"])
        self.assertEqual(result["status"], BLOCKED)

    def test_5_low_recovery_probability_blocked(self):
        """Recovery probability below threshold -> no execution."""
        payment = self._create_payment(recovery_probability=0.4)
        with patch.dict(os.environ, {"RECOVERY_DRY_RUN": "false"}, clear=False):
            with patch("app.services.razorpay_service.create_payment_link") as mock_link:
                result = execute_recovery_action(
                    payment=payment, action="PAYMENT_LINK",
                    execution_mode=LIVE, db=self.db,
                )
        mock_link.assert_not_called()
        self.assertEqual(result["status"], BLOCKED)

    def test_6_amount_above_limit_blocked(self):
        """Amount > Rs 50,000 -> firewall rejects, no Razorpay call."""
        payment = self._create_payment(amount=75000.0)
        with patch.dict(os.environ, {"RECOVERY_DRY_RUN": "false"}, clear=False):
            with patch("app.services.razorpay_service.create_payment_link") as mock_link:
                result = execute_recovery_action(
                    payment=payment, action="PAYMENT_LINK",
                    execution_mode=LIVE, db=self.db,
                )
        mock_link.assert_not_called()
        self.assertEqual(result["status"], BLOCKED)

    def test_7_invalid_state_blocked(self):
        """Already captured/recovered payment -> firewall rejects for PAYMENT_LINK too."""
        # Captured payment
        payment = self._create_payment(
            payment_status="captured", recovery_status="SUCCESS"
        )
        with patch.dict(os.environ, {"RECOVERY_DRY_RUN": "false"}, clear=False):
            with patch("app.services.razorpay_service.create_payment_link") as mock_link:
                result = execute_recovery_action(
                    payment=payment, action="PAYMENT_LINK",
                    execution_mode=LIVE, db=self.db,
                )
        mock_link.assert_not_called()
        self.assertEqual(result["status"], BLOCKED)

    def test_7b_retry_limit_blocked(self):
        """retry_count >= 2 -> firewall rejects PAYMENT_LINK (retry-limit check)."""
        payment = self._create_payment(retry_count=2)
        with patch.dict(os.environ, {"RECOVERY_DRY_RUN": "false"}, clear=False):
            with patch("app.services.razorpay_service.create_payment_link") as mock_link:
                result = execute_recovery_action(
                    payment=payment, action="PAYMENT_LINK",
                    execution_mode=LIVE, db=self.db,
                )
        mock_link.assert_not_called()
        self.assertEqual(result["status"], BLOCKED)

    def test_7c_cooldown_does_not_apply_to_payment_link(self):
        """Cooldown is RETRY/HYBRID-only; PAYMENT_LINK is allowed after a recent attempt."""
        recent = datetime.now(timezone.utc) - timedelta(minutes=2)
        payment = self._create_payment(
            retry_count=1,
            previous_recovery_attempts=0,
            last_recovery_attempt_at=recent,
        )
        with patch.dict(os.environ, {"RECOVERY_DRY_RUN": "false"}, clear=False):
            with patch(
                "app.services.razorpay_service.create_payment_link",
                return_value={
                    "id": "plink_cooldown_1",
                    "short_url": "https://rzp.io/l/cooldown1",
                    "amount": 1500000,
                    "currency": "INR",
                    "status": "created",
                },
            ) as mock_link:
                result = execute_recovery_action(
                    payment=payment, action="PAYMENT_LINK",
                    execution_mode=LIVE, db=self.db,
                )
        mock_link.assert_called_once()
        self.assertEqual(result["status"], SUCCESS)

    def test_8_unknown_action_rejected(self):
        """Unknown action -> rejected safely; Razorpay is never called."""
        payment = self._create_payment()
        with self.assertRaises(ValueError):
            with patch(
                "app.services.razorpay_service.create_payment_link"
            ) as mock_link:
                execute_recovery_action(
                    payment=payment, action="SMS_BLAST", db=self.db
                )
                mock_link.assert_not_called()

    # ------------------------------------------------------------------
    # Razorpay failure / success handling
    # ------------------------------------------------------------------
    def test_8b_razorpay_api_failure_safe_state(self):
        """Razorpay API failure -> FAILED, safe error, no fabricated success."""
        payment = self._create_payment()
        with patch.dict(os.environ, {"RECOVERY_DRY_RUN": "false"}, clear=False):
            with patch(
                "app.services.razorpay_service.create_payment_link",
                side_effect=Exception("auth failed"),
            ):
                result = execute_recovery_action(
                    payment=payment, action="PAYMENT_LINK",
                    execution_mode=LIVE, db=self.db,
                )
        self.assertFalse(result["executed"])
        self.assertEqual(result["status"], FAILED)
        self.assertFalse(result["simulated"])
        # The payment must NOT be marked recovered.
        self.db.expire(payment)
        self.assertEqual(payment.recovery_status, "PENDING")
        self.assertNotIn("auth failed", str(result.get("provider_response")))

    def test_8c_razorpay_invalid_link_safe_failure(self):
        """Razorpay returns an invalid link (no id) -> FAILED, no success."""
        payment = self._create_payment()
        with patch.dict(os.environ, {"RECOVERY_DRY_RUN": "false"}, clear=False):
            with patch(
                "app.services.razorpay_service.create_payment_link",
                return_value={"status": "failed"},
            ):
                result = execute_recovery_action(
                    payment=payment, action="PAYMENT_LINK",
                    execution_mode=LIVE, db=self.db,
                )
        self.assertFalse(result["executed"])
        self.assertEqual(result["status"], FAILED)

    # ------------------------------------------------------------------
    # Success persistence — never mark payment recovered
    # ------------------------------------------------------------------
    def test_9_success_persisted_not_marked_recovered(self):
        """Successful link creation persisted; payment NOT marked recovered."""
        payment = self._create_payment()
        with patch.dict(os.environ, {"RECOVERY_DRY_RUN": "false"}, clear=False):
            with patch(
                "app.services.razorpay_service.create_payment_link",
                return_value={
                    "id": "plink_persist_001",
                    "short_url": "https://rzp.io/l/persist1",
                    "amount": 1500000,
                    "currency": "INR",
                    "status": "created",
                    "accept_partial": False,
                },
            ):
                result = execute_recovery_action(
                    payment=payment, action="PAYMENT_LINK",
                    execution_mode=LIVE, db=self.db,
                )
        self.assertEqual(result["status"], SUCCESS)
        self.assertEqual(result["provider_reference_id"], "plink_persist_001")

        self.db.expire(payment)
        # Local state updated: provider reference + retry_count incremented.
        self.assertEqual(payment.razorpay_order_id, "plink_persist_001")
        self.assertEqual(payment.retry_count, 1)
        self.assertIsNotNone(payment.last_recovery_attempt_at)
        # IMPORTANT: not marked captured / recovered (money not received).
        self.assertNotEqual(payment.recovery_status.upper(), "SUCCESS")
        self.assertNotEqual(payment.recovery_status.upper(), "RECOVERED")

        # Execution record persisted.
        execution = (
            self.db.query(RecoveryExecution)
            .filter(RecoveryExecution.payment_id == payment.id)
            .filter(RecoveryExecution.provider_reference_id == "plink_persist_001")
            .first()
        )
        self.assertIsNotNone(execution)
        self.assertEqual(execution.status, SUCCESS)
        self.assertEqual(execution.execution_mode, LIVE)
        self.assertFalse(execution.simulated)
        self.assertEqual(execution.provider, "razorpay")

    def test_10_duplicate_execution_no_second_link(self):
        """Duplicate execution is detected; Razorpay is not called twice."""
        payment = self._create_payment()
        with patch.dict(os.environ, {"RECOVERY_DRY_RUN": "false"}, clear=False):
            with patch(
                "app.services.razorpay_service.create_payment_link",
                return_value={
                    "id": "plink_dup_001",
                    "short_url": "https://rzp.io/l/dup1",
                    "amount": 1500000,
                    "currency": "INR",
                    "status": "created",
                },
            ) as mock_link:
                first = execute_recovery_action(
                    payment=payment, action="PAYMENT_LINK",
                    execution_mode=LIVE, db=self.db,
                )
                self.assertEqual(first["status"], SUCCESS)
                second = execute_recovery_action(
                    payment=payment, action="PAYMENT_LINK",
                    execution_mode=LIVE, db=self.db,
                )
                self.assertEqual(second["status"], "ALREADY_EXECUTED")
                self.assertFalse(second["executed"])
                # create_payment_link called exactly once for the single real link
                mock_link.assert_called_once()

    def test_11_secrets_never_returned(self):
        """Sanitisation drops sensitive keys from provider response and result."""
        payment = self._create_payment()
        secretish = {
            "id": "plink_sec_001",
            "short_url": "https://rzp.io/l/sec1",
            "amount": 1500000,
            "currency": "INR",
            "status": "created",
            "secret": "top_secret",
            "key": "rzp_key",
            "authorization": "Basic XXX",
            "bank_account": {"number": "1111", "ifsc": "ABC"},
        }
        with patch.dict(os.environ, {"RECOVERY_DRY_RUN": "false"}, clear=False):
            with patch(
                "app.services.razorpay_service.create_payment_link",
                return_value=secretish,
            ):
                result = execute_recovery_action(
                    payment=payment, action="PAYMENT_LINK",
                    execution_mode=LIVE, db=self.db,
                )
        blob = str(result)
        for secret in ("top_secret", "rzp_key", "Basic XXX", "1111"):
            self.assertNotIn(secret, blob)
        # provider_reference_id is still available
        self.assertEqual(result["provider_reference_id"], "plink_sec_001")


if __name__ == "__main__":
    unittest.main()
