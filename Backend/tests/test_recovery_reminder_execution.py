"""Automated tests for the RecoverAI REMINDER recovery execution path.

REMINDER is DRY-RUN ONLY for this step:
  - safe by default (RECOVERY_DRY_RUN=true -> simulates, never sends)
  - never sends SMS / WhatsApp / email and never calls an external
    notification provider
  - never calls Razorpay (no order, no payment link, no charge)
  - always gated by the Action Firewall (never bypassed)
  - idempotent (no duplicate reminders)
  - recorded on the existing RecoveryExecution row with provider fields null
  - does NOT apply the RETRY/HYBRID cooldown

The Razorpay client is always mocked; no customer is ever contacted and no real
notification is ever sent.
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
    execute_recovery_action,
)
from app.config import RECOVERY_DRY_RUN


MARKER = "TEST_REMINDER"

class TestRecoveryReminderExecution(unittest.TestCase):
    """Reminder execution engine — DRY_RUN-only safety and pipeline gating."""

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
            amount=8000.0,
            failure_reason=MARKER,
            customer_type="Regular",
            payment_status="failed",
            recovery_status="PENDING",
            recommended_action="REMINDER",
            confidence=0.9,
            recovery_probability=0.8,
            expected_recovery=6400.0,
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
    def test_1_reminder_dry_run_simulated(self):
        """RECOVERY_DRY_RUN default true: REMINDER simulates; nothing is sent."""
        self.assertTrue(RECOVERY_DRY_RUN in ("", "true"))
        payment = self._create_payment()
        with patch("app.services.razorpay_service.create_order") as mock_order, \
             patch("app.services.razorpay_service.create_payment_link") as mock_link:
            result = execute_recovery_action(
                payment=payment, action="REMINDER", db=self.db
            )
        mock_order.assert_not_called()
        mock_link.assert_not_called()
        self.assertTrue(result["executed"])
        self.assertEqual(result["execution_mode"], DRY_RUN)
        self.assertEqual(result["status"], SIMULATED)
        self.assertTrue(result["simulated"])
        # Clear signal that no real reminder was sent.
        self.assertIn("simulated for payment", result["result_message"].lower())
        self.assertIn("no real", result["result_message"].lower())
        self.assertIn("no external notification provider was called", result["result_message"].lower())

    def test_2_firewall_approved_reminder_allowed(self):
        """Firewall-approved REMINDER proceeds to execution (simulated)."""
        payment = self._create_payment()
        result = execute_recovery_action(
            payment=payment, action="REMINDER", db=self.db
        )
        self.assertTrue(result["executed"])
        self.assertEqual(result["status"], SIMULATED)
        self.assertTrue(result["firewall_approved"])

    def test_2b_live_reminder_never_supported_even_if_dry_run_disabled(self):
        """REMINDER has NO live path: LIVE is refused even with DRY_RUN off."""
        payment = self._create_payment()
        with patch.dict(os.environ, {"RECOVERY_DRY_RUN": "false"}, clear=False):
            with self.assertRaises(ValueError) as ctx:
                execute_recovery_action(
                    payment=payment, action="REMINDER", execution_mode=LIVE, db=self.db
                )
            self.assertIn("not supported for action 'REMINDER'", str(ctx.exception))

    # ------------------------------------------------------------------
    # Firewall gating
    # ------------------------------------------------------------------
    def test_3_low_confidence_blocked(self):
        """Confidence below threshold -> REMINDER is BLOCKED."""
        payment = self._create_payment(confidence=0.5)
        result = execute_recovery_action(
            payment=payment, action="REMINDER", db=self.db
        )
        self.assertFalse(result["executed"])
        self.assertEqual(result["status"], BLOCKED)

    def test_4_low_probability_blocked(self):
        """Recovery probability below threshold -> BLOCKED."""
        payment = self._create_payment(recovery_probability=0.3)
        result = execute_recovery_action(
            payment=payment, action="REMINDER", db=self.db
        )
        self.assertEqual(result["status"], BLOCKED)

    def test_5_amount_above_limit_blocked(self):
        """Amount > Rs 50,000 -> BLOCKED, no reminder."""
        payment = self._create_payment(amount=75000.0)
        result = execute_recovery_action(
            payment=payment, action="REMINDER", db=self.db
        )
        self.assertEqual(result["status"], BLOCKED)

    def test_6_captured_recovered_blocked(self):
        """Already captured/recovered payment -> BLOCKED."""
        payment = self._create_payment(
            payment_status="captured", recovery_status="SUCCESS"
        )
        result = execute_recovery_action(
            payment=payment, action="REMINDER", db=self.db
        )
        self.assertEqual(result["status"], BLOCKED)

    def test_7_max_retry_blocked(self):
        """retry_count >= 2 -> BLOCKED (retry-limit check)."""
        payment = self._create_payment(retry_count=2)
        result = execute_recovery_action(
            payment=payment, action="REMINDER", db=self.db
        )
        self.assertEqual(result["status"], BLOCKED)

    def test_8_reminder_not_blocked_by_retry_cooldown(self):
        """RETRY/HYBRID cooldown does NOT apply to REMINDER."""
        recent = datetime.now(timezone.utc) - timedelta(minutes=2)
        payment = self._create_payment(
            retry_count=1,
            previous_recovery_attempts=0,
            last_recovery_attempt_at=recent,
        )
        result = execute_recovery_action(
            payment=payment, action="REMINDER", db=self.db
        )
        self.assertTrue(result["executed"])
        self.assertEqual(result["status"], SIMULATED)

    def test_9_unknown_action_rejected(self):
        """Unknown action -> rejected safely; no notification/Razorpay."""
        payment = self._create_payment()
        with self.assertRaises(ValueError):
            with patch("app.services.razorpay_service.create_order") as mock_order:
                execute_recovery_action(payment=payment, action="CARRIER_PIGEON", db=self.db)
                mock_order.assert_not_called()

    # ------------------------------------------------------------------
    # Idempotency / duplicate protection
    # ------------------------------------------------------------------
    def test_10_duplicate_reminder_no_second_execution(self):
        """Duplicate REMINDER execution -> ALREADY_EXECUTED, no duplicate."""
        payment = self._create_payment()
        first = execute_recovery_action(
            payment=payment, action="REMINDER", db=self.db
        )
        self.assertEqual(first["status"], SIMULATED)
        second = execute_recovery_action(
            payment=payment, action="REMINDER", db=self.db
        )
        self.assertEqual(second["status"], "ALREADY_EXECUTED")
        self.assertFalse(second["executed"])
        self.assertEqual(second["duplicate_of"], first["id"])

    # ------------------------------------------------------------------
    # Provider isolation
    # ------------------------------------------------------------------
    def test_11_no_external_notification_provider_called_dry_run(self):
        """No external notification provider is invoked in DRY_RUN."""
        payment = self._create_payment()
        result = execute_recovery_action(
            payment=payment, action="REMINDER", db=self.db
        )
        # The message explicitly states nothing was sent to a customer.
        self.assertIn("no external notification provider was called", result["result_message"].lower())
        self.assertIsNone(result["provider"])
        self.assertIsNone(result["provider_reference_id"])

    def test_12_no_razorpay_call_in_dry_run(self):
        """No Razorpay order/link is created for REMINDER in DRY_RUN."""
        payment = self._create_payment()
        with patch("app.services.razorpay_service.create_order") as mock_order, \
             patch("app.services.razorpay_service.create_payment_link") as mock_link:
            result = execute_recovery_action(
                payment=payment, action="REMINDER", db=self.db
            )
        mock_order.assert_not_called()
        mock_link.assert_not_called()
        self.assertEqual(result["status"], SIMULATED)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def test_13_reminder_persisted(self):
        """REMINDER execution is persisted on RecoveryExecution."""
        payment = self._create_payment()
        result = execute_recovery_action(
            payment=payment, action="REMINDER", db=self.db
        )
        execution = (
            self.db.query(RecoveryExecution)
            .filter(RecoveryExecution.payment_id == payment.id)
            .filter(RecoveryExecution.action == "REMINDER")
            .order_by(RecoveryExecution.id.desc())
            .first()
        )
        self.assertIsNotNone(execution)
        self.assertEqual(execution.id, result["id"])
        self.assertEqual(execution.status, SIMULATED)
        self.assertEqual(execution.execution_mode, DRY_RUN)
        self.assertTrue(execution.simulated)

    def test_14_provider_fields_null_in_dry_run(self):
        """provider / provider_reference_id remain null in DRY_RUN REMINDER."""
        payment = self._create_payment()
        result = execute_recovery_action(
            payment=payment, action="REMINDER", db=self.db
        )
        self.assertIsNone(result["provider"])
        self.assertIsNone(result["provider_reference_id"])
        execution = (
            self.db.query(RecoveryExecution)
            .filter(RecoveryExecution.payment_id == payment.id)
            .filter(RecoveryExecution.action == "REMINDER")
            .first()
        )
        self.assertIsNone(execution.provider)
        self.assertIsNone(execution.provider_reference_id)

    def test_15_retry_still_works(self):
        """RETRY still simulates/executes correctly."""
        payment = self._create_payment(recommended_action="RETRY")
        with patch("app.services.razorpay_service.create_order") as mock_order:
            result = execute_recovery_action(
                payment=payment, action="RETRY", db=self.db
            )
        mock_order.assert_not_called()
        self.assertEqual(result["status"], SIMULATED)
        self.assertEqual(result["execution_mode"], DRY_RUN)

    def test_16_payment_link_still_works(self):
        """PAYMENT_LINK still simulates/executes correctly."""
        payment = self._create_payment(recommended_action="PAYMENT_LINK")
        with patch("app.services.razorpay_service.create_payment_link") as mock_link:
            result = execute_recovery_action(
                payment=payment, action="PAYMENT_LINK", db=self.db
            )
        mock_link.assert_not_called()
        self.assertEqual(result["status"], SIMULATED)
        self.assertEqual(result["execution_mode"], DRY_RUN)


if __name__ == "__main__":
    unittest.main()
