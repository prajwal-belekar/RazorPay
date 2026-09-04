"""Automated tests for the RecoverAI real RETRY execution path.

Covers the requirement that a RETRY is:
  - safe by default (RECOVERY_DRY_RUN=true -> never calls Razorpay, simulated)
  - only reaching the real Razorpay TEST/SANDBOX path when an operator
    explicitly disables DRY_RUN (RECOVERY_DRY_RUN=false)
  - always gated by the Action Firewall (never bypassed)
  - idempotent (no duplicate retries)
  - recorded without exposing secrets
  - never marking the payment recovered just because an API call was accepted

The Razorpay API is always mocked; no real customer charge is ever made.
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


MARKER = "TEST_RETRY_LIVE"

class TestRecoveryRetryExecution(unittest.TestCase):
    """Retry execution engine — DRY_RUN safety and real (sandbox) path."""

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
            recommended_action="RETRY",
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
    def test_1_retry_dry_run_true_no_razorpay_call(self):
        """RECOVERY_DRY_RUN default true: RETRY simulates and never calls Razorpay."""
        self.assertTrue(RECOVERY_DRY_RUN in ("", "true"))
        payment = self._create_payment()
        with patch("app.services.razorpay_service.create_order") as mock_order:
            result = execute_recovery_action(payment=payment, action="RETRY", db=self.db)
        mock_order.assert_not_called()
        self.assertTrue(result["executed"])
        self.assertEqual(result["execution_mode"], DRY_RUN)
        self.assertEqual(result["status"], SIMULATED)
        self.assertTrue(result["simulated"])
        self.assertIn("simulated", result["result_message"].lower())

    def test_2_live_rejected_when_dry_run_enabled(self):
        """With RECOVERY_DRY_RUN=true, requesting LIVE is refused safely."""
        with patch.dict(os.environ, {"RECOVERY_DRY_RUN": "true"}, clear=False):
            payment = self._create_payment()
            with self.assertRaises(ValueError):
                execute_recovery_action(
                    payment=payment, action="RETRY", execution_mode=LIVE, db=self.db
                )

    def test_15_dry_run_stays_true_by_default(self):
        """DRY_RUN must remain the default (never default to false)."""
        # Explicitly clear the env so config default applies.
        with patch.dict(os.environ, {}, clear=True):
            import app.config as config_mod
            # force re-read of the default
            self.assertTrue(config_mod.recovery_dry_run_enabled())
        # Config constant default is "true"
        self.assertNotEqual(RECOVERY_DRY_RUN.strip().lower(), "false")

    # ------------------------------------------------------------------
    # Firewall gating
    # ------------------------------------------------------------------
    def test_3_firewall_approval_proceeds(self):
        """With DRY_RUN disabled, an approved RETRY proceeds to the real path."""
        payment = self._create_payment()
        with patch.dict(os.environ, {"RECOVERY_DRY_RUN": "false"}, clear=False):
            with patch(
                "app.services.razorpay_service.create_order",
            ) as mock_order:
                mock_order.return_value = {
                    "id": "order_test_abc123",
                    "amount": 1500000,
                    "currency": "INR",
                    "status": "created",
                    "attempts": 0,
                }
                result = execute_recovery_action(
                    payment=payment, action="RETRY", execution_mode=LIVE, db=self.db
                )
        mock_order.assert_called_once()
        self.assertTrue(result["executed"])
        self.assertEqual(result["execution_mode"], LIVE)
        self.assertEqual(result["status"], SUCCESS)
        self.assertFalse(result["simulated"])
        self.assertEqual(result["provider"], "razorpay")
        self.assertEqual(result["provider_reference_id"], "order_test_abc123")

    def test_4_firewall_rejection_no_razorpay_call(self):
        """Firewall rejection: Razorpay is never called, execution is BLOCKED."""
        # Low confidence -> firewall rejects
        payment = self._create_payment(confidence=0.5)
        with patch.dict(os.environ, {"RECOVERY_DRY_RUN": "false"}, clear=False):
            with patch("app.services.razorpay_service.create_order") as mock_order:
                result = execute_recovery_action(
                    payment=payment, action="RETRY", execution_mode=LIVE, db=self.db
                )
        mock_order.assert_not_called()
        self.assertFalse(result["executed"])
        self.assertEqual(result["status"], BLOCKED)

    def test_5_low_confidence_no_execution(self):
        """Confidence below threshold -> no execution (even with DRY_RUN off)."""
        payment = self._create_payment(confidence=0.5)
        with patch.dict(os.environ, {"RECOVERY_DRY_RUN": "false"}, clear=False):
            with patch("app.services.razorpay_service.create_order") as mock_order:
                result = execute_recovery_action(
                    payment=payment, action="RETRY", execution_mode=LIVE, db=self.db
                )
        mock_order.assert_not_called()
        self.assertEqual(result["status"], BLOCKED)

    def test_6_low_probability_no_execution(self):
        """Recovery probability below threshold -> no execution."""
        payment = self._create_payment(recovery_probability=0.4)
        with patch.dict(os.environ, {"RECOVERY_DRY_RUN": "false"}, clear=False):
            with patch("app.services.razorpay_service.create_order") as mock_order:
                result = execute_recovery_action(
                    payment=payment, action="RETRY", execution_mode=LIVE, db=self.db
                )
        mock_order.assert_not_called()
        self.assertEqual(result["status"], BLOCKED)

    def test_7_amount_above_limit_no_execution(self):
        """Amount > Rs 50,000 -> firewall rejects, no execution."""
        payment = self._create_payment(amount=75000.0)
        with patch.dict(os.environ, {"RECOVERY_DRY_RUN": "false"}, clear=False):
            with patch("app.services.razorpay_service.create_order") as mock_order:
                result = execute_recovery_action(
                    payment=payment, action="RETRY", execution_mode=LIVE, db=self.db
                )
        mock_order.assert_not_called()
        self.assertEqual(result["status"], BLOCKED)

    def test_8_retry_count_at_limit_no_execution(self):
        """retry_count >= 2 -> firewall rejects, no execution."""
        payment = self._create_payment(retry_count=2)
        with patch.dict(os.environ, {"RECOVERY_DRY_RUN": "false"}, clear=False):
            with patch("app.services.razorpay_service.create_order") as mock_order:
                result = execute_recovery_action(
                    payment=payment, action="RETRY", execution_mode=LIVE, db=self.db
                )
        mock_order.assert_not_called()
        self.assertEqual(result["status"], BLOCKED)

    def test_9_cooldown_no_execution(self):
        """Cooldown < 15 minutes -> firewall rejects, no execution."""
        recent = datetime.now(timezone.utc) - timedelta(minutes=5)
        payment = self._create_payment(
            retry_count=1, previous_recovery_attempts=1, last_recovery_attempt_at=recent
        )
        with patch.dict(os.environ, {"RECOVERY_DRY_RUN": "false"}, clear=False):
            with patch("app.services.razorpay_service.create_order") as mock_order:
                result = execute_recovery_action(
                    payment=payment, action="RETRY", execution_mode=LIVE, db=self.db
                )
        mock_order.assert_not_called()
        self.assertEqual(result["status"], BLOCKED)

    def test_10_captured_payment_no_execution(self):
        """Already captured payment -> firewall rejects, no execution."""
        payment = self._create_payment(payment_status="captured", recovery_status="SUCCESS")
        with patch.dict(os.environ, {"RECOVERY_DRY_RUN": "false"}, clear=False):
            with patch("app.services.razorpay_service.create_order") as mock_order:
                result = execute_recovery_action(
                    payment=payment, action="RETRY", execution_mode=LIVE, db=self.db
                )
        mock_order.assert_not_called()
        self.assertEqual(result["status"], BLOCKED)

    def test_11_recovered_payment_no_execution(self):
        """Already recovered payment -> firewall rejects, no execution."""
        payment = self._create_payment(recovery_status="SUCCESS")
        with patch.dict(os.environ, {"RECOVERY_DRY_RUN": "false"}, clear=False):
            with patch("app.services.razorpay_service.create_order") as mock_order:
                result = execute_recovery_action(
                    payment=payment, action="RETRY", execution_mode=LIVE, db=self.db
                )
        mock_order.assert_not_called()
        self.assertEqual(result["status"], BLOCKED)

    # ------------------------------------------------------------------
    # Razorpay failure / success handling
    # ------------------------------------------------------------------
    def test_11b_razorpay_api_failure_safe_state(self):
        """Razorpay API failure -> FAILED, safe error, no fabricated success."""
        payment = self._create_payment()
        with patch.dict(os.environ, {"RECOVERY_DRY_RUN": "false"}, clear=False):
            with patch(
                "app.services.razorpay_service.create_order",
                side_effect=Exception("auth failed"),
            ):
                result = execute_recovery_action(
                    payment=payment, action="RETRY", execution_mode=LIVE, db=self.db
                )
        self.assertFalse(result["executed"])
        self.assertEqual(result["status"], FAILED)
        self.assertFalse(result["simulated"])
        # The payment must NOT be marked recovered.
        self.db.expire(payment)
        self.assertEqual(payment.recovery_status, "PENDING")
        self.assertNotIn("auth failed", str(result.get("provider_response")))

    def test_11c_razorpay_invalid_order_safe_failure(self):
        """Razorpay returns an invalid order (no id) -> FAILED, no success."""
        payment = self._create_payment()
        with patch.dict(os.environ, {"RECOVERY_DRY_RUN": "false"}, clear=False):
            with patch(
                "app.services.razorpay_service.create_order",
                return_value={"status": "failed"},

            ):
                result = execute_recovery_action(
                    payment=payment, action="RETRY", execution_mode=LIVE, db=self.db
                )
        self.assertFalse(result["executed"])
        self.assertEqual(result["status"], FAILED)

    # ------------------------------------------------------------------
    # Success persistence — never mark payment recovered
    # ------------------------------------------------------------------
    def test_12_success_persisted_not_marked_recovered(self):
        """Successful sandbox order creation is persisted; payment NOT marked recovered."""
        payment = self._create_payment()
        with patch.dict(os.environ, {"RECOVERY_DRY_RUN": "false"}, clear=False):
            with patch(
                "app.services.razorpay_service.create_order",
                return_value={
                    "id": "order_persist_001",
                    "amount": 1500000,
                    "currency": "INR",
                    "status": "created",
                },
            ):
                result = execute_recovery_action(
                    payment=payment, action="RETRY", execution_mode=LIVE, db=self.db
                )
        self.assertEqual(result["status"], SUCCESS)
        self.assertEqual(result["provider_reference_id"], "order_persist_001")

        self.db.expire(payment)
        # Local state updated: new order + retry_count incremented.
        self.assertEqual(payment.razorpay_order_id, "order_persist_001")
        self.assertEqual(payment.retry_count, 1)
        self.assertIsNotNone(payment.last_recovery_attempt_at)
        # IMPORTANT: not marked captured / recovered (money not received).
        self.assertNotEqual(payment.recovery_status.upper(), "SUCCESS")
        self.assertNotEqual(payment.recovery_status.upper(), "RECOVERED")

        # Execution record persisted.
        execution = (
            self.db.query(RecoveryExecution)
            .filter(RecoveryExecution.payment_id == payment.id)
            .filter(RecoveryExecution.provider_reference_id == "order_persist_001")
            .first()
        )
        self.assertIsNotNone(execution)
        self.assertEqual(execution.status, SUCCESS)
        self.assertEqual(execution.execution_mode, LIVE)
        self.assertFalse(execution.simulated)
        self.assertEqual(execution.provider, "razorpay")

    def test_13_duplicate_execution_no_second_retry(self):
        """Duplicate execution is detected; Razorpay is not called twice."""
        payment = self._create_payment()
        with patch.dict(os.environ, {"RECOVERY_DRY_RUN": "false"}, clear=False):
            with patch(
                "app.services.razorpay_service.create_order",
                return_value={"id": "order_dup_001", "amount": 1500000, "currency": "INR"},
            ) as mock_order:
                first = execute_recovery_action(
                    payment=payment, action="RETRY", execution_mode=LIVE, db=self.db
                )
                self.assertEqual(first["status"], SUCCESS)
                second = execute_recovery_action(
                    payment=payment, action="RETRY", execution_mode=LIVE, db=self.db
                )
                self.assertEqual(second["status"], "ALREADY_EXECUTED")
                self.assertFalse(second["executed"])
                # create_order called exactly once for the single real retry
                mock_order.assert_called_once()

    def test_14_secrets_never_returned(self):
        """Sanitisation drops sensitive keys from provider response and result."""
        payment = self._create_payment()
        secretish = {
            "id": "order_sec_001",
            "amount": 1500000,
            "currency": "INR",
            "secret": "top_secret",
            "key": "rzp_key",
            "authorization": "Basic XXX",
            "bank_account": {"number": "1111", "ifsc": "ABC"},
        }
        with patch.dict(os.environ, {"RECOVERY_DRY_RUN": "false"}, clear=False):
            with patch(
                "app.services.razorpay_service.create_order",
                return_value=secretish,
            ):
                result = execute_recovery_action(
                    payment=payment, action="RETRY", execution_mode=LIVE, db=self.db
                )
        blob = str(result)
        for secret in ("top_secret", "rzp_key", "Basic XXX", "1111"):
            self.assertNotIn(secret, blob)
        # provider_reference_id is still available
        self.assertEqual(result["provider_reference_id"], "order_sec_001")


if __name__ == "__main__":
    unittest.main()
