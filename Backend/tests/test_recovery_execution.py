"""Automated tests for RecoverAI Recovery Execution Engine.

Tests the DRY-RUN sandbox execution engine, covering:
  - Firewall-approved RETRY dry-run execution
  - Firewall-rejected actions are blocked
  - Payment not found (404)
  - Missing AI decision (400)
  - Captured payment blocked by firewall
  - Retry limit reached blocked by firewall
  - Low AI confidence blocked by firewall
  - All four action types in dry-run mode (RETRY, PAYMENT_LINK, REMINDER, HYBRID)
  - Duplicate execution idempotency
  - No real Razorpay API calls are made
  - Existing endpoints remain functional
"""

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Payment, RecoveryExecution
from app.services.recovery_execution_service import (
    BLOCKED,
    DRY_RUN,
    SIMULATED,
    SUPPORTED_ACTIONS,
)


class TestRecoveryExecutionEngine(unittest.TestCase):
    """Test the Recovery Execution Engine (DRY-RUN sandbox mode)."""

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()

    def tearDown(self):
        # Clean up test data
        self.db.query(RecoveryExecution).filter(
            RecoveryExecution.payment_id.in_(
                self.db.query(Payment.id).filter(
                    Payment.failure_reason == "TEST_EXECUTION"
                )
            )
        ).delete(synchronize_session=False)
        self.db.query(Payment).filter(
            Payment.failure_reason == "TEST_EXECUTION"
        ).delete(synchronize_session=False)
        self.db.commit()
        self.db.close()

    def _create_eligible_payment(self, **overrides) -> Payment:
        """Helper: create a failed payment eligible for recovery."""
        defaults = dict(
            amount=15000.0,
            failure_reason="TEST_EXECUTION",
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
    # 1. Firewall-approved RETRY -> DRY_RUN execution succeeds
    # ------------------------------------------------------------------
    def test_1_firewall_approved_retry_dry_run_succeeds(self):
        payment = self._create_eligible_payment()
        res = self.client.post(f"/api/recovery/execute/{payment.id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["executed"])
        self.assertEqual(data["execution_mode"], DRY_RUN)
        self.assertEqual(data["status"], SIMULATED)
        self.assertEqual(data["action"], "RETRY")
        self.assertTrue(data["simulated"])
        self.assertIn("simulated", data["result_message"].lower())

    # ------------------------------------------------------------------
    # 2. Firewall-rejected action -> execution blocked
    # ------------------------------------------------------------------
    def test_2_firewall_rejected_action_blocked(self):
        # Amount exceeds ₹50,000 limit -> firewall rejects
        payment = self._create_eligible_payment(amount=75000.0)
        res = self.client.post(f"/api/recovery/execute/{payment.id}")
        self.assertEqual(res.status_code, 403)
        data = res.json()
        # The 403 comes from the endpoint returning BLOCKED status
        self.assertFalse(data["executed"])
        self.assertEqual(data["status"], BLOCKED)

    # ------------------------------------------------------------------
    # 3. Payment doesn't exist -> 404
    # ------------------------------------------------------------------
    def test_3_payment_not_found_returns_404(self):
        res = self.client.post("/api/recovery/execute/999999")
        self.assertEqual(res.status_code, 404)
        self.assertIn("not found", res.json()["detail"].lower())

    # ------------------------------------------------------------------
    # 4. No AI decision exists -> appropriate error
    # ------------------------------------------------------------------
    def test_4_no_ai_decision_returns_400(self):
        payment = self._create_eligible_payment(recommended_action=None)
        res = self.client.post(f"/api/recovery/execute/{payment.id}")
        self.assertEqual(res.status_code, 400)
        self.assertIn("no ai recovery decision", res.json()["detail"].lower())

    # ------------------------------------------------------------------
    # 5. Captured payment -> execution blocked by firewall
    # ------------------------------------------------------------------
    def test_5_captured_payment_blocked_by_firewall(self):
        payment = self._create_eligible_payment(
            payment_status="captured",
            recovery_status="SUCCESS",
        )
        res = self.client.post(f"/api/recovery/execute/{payment.id}")
        self.assertEqual(res.status_code, 403)
        data = res.json()
        self.assertFalse(data["executed"])
        self.assertEqual(data["status"], BLOCKED)

    # ------------------------------------------------------------------
    # 6. Retry limit reached -> blocked by firewall
    # ------------------------------------------------------------------
    def test_6_retry_limit_reached_blocked(self):
        payment = self._create_eligible_payment(retry_count=2)
        res = self.client.post(f"/api/recovery/execute/{payment.id}")
        self.assertEqual(res.status_code, 403)
        data = res.json()
        self.assertFalse(data["executed"])
        self.assertEqual(data["status"], BLOCKED)

    # ------------------------------------------------------------------
    # 7. Low AI confidence -> blocked by firewall
    # ------------------------------------------------------------------
    def test_7_low_confidence_blocked(self):
        payment = self._create_eligible_payment(confidence=0.50)
        res = self.client.post(f"/api/recovery/execute/{payment.id}")
        self.assertEqual(res.status_code, 403)
        data = res.json()
        self.assertFalse(data["executed"])
        self.assertEqual(data["status"], BLOCKED)

    # ------------------------------------------------------------------
    # 8. RETRY dry run -> simulated
    # ------------------------------------------------------------------
    def test_8_retry_dry_run_simulated(self):
        payment = self._create_eligible_payment(recommended_action="RETRY")
        res = self.client.post(
            f"/api/recovery/execute/{payment.id}",
            json={"action": "RETRY"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["executed"])
        self.assertEqual(data["action"], "RETRY")
        self.assertEqual(data["status"], SIMULATED)
        self.assertTrue(data["simulated"])
        self.assertIn("retry", data["result_message"].lower())

    # ------------------------------------------------------------------
    # 9. PAYMENT_LINK dry run -> simulated
    # ------------------------------------------------------------------
    def test_9_payment_link_dry_run_simulated(self):
        payment = self._create_eligible_payment(recommended_action="PAYMENT_LINK")
        res = self.client.post(
            f"/api/recovery/execute/{payment.id}",
            json={"action": "PAYMENT_LINK"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["executed"])
        self.assertEqual(data["action"], "PAYMENT_LINK")
        self.assertEqual(data["status"], SIMULATED)
        self.assertTrue(data["simulated"])
        self.assertIn("payment link", data["result_message"].lower())

    # ------------------------------------------------------------------
    # 10. REMINDER dry run -> simulated
    # ------------------------------------------------------------------
    def test_10_reminder_dry_run_simulated(self):
        payment = self._create_eligible_payment(recommended_action="REMINDER")
        res = self.client.post(
            f"/api/recovery/execute/{payment.id}",
            json={"action": "REMINDER"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["executed"])
        self.assertEqual(data["action"], "REMINDER")
        self.assertEqual(data["status"], SIMULATED)
        self.assertTrue(data["simulated"])
        self.assertIn("reminder", data["result_message"].lower())

    # ------------------------------------------------------------------
    # 11. HYBRID dry run -> simulated retry + fallback payment link
    # ------------------------------------------------------------------
    def test_11_hybrid_dry_run_simulated(self):
        payment = self._create_eligible_payment(recommended_action="HYBRID")
        res = self.client.post(
            f"/api/recovery/execute/{payment.id}",
            json={"action": "HYBRID"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["executed"])
        self.assertEqual(data["action"], "HYBRID")
        self.assertEqual(data["status"], SIMULATED)
        self.assertTrue(data["simulated"])
        msg = data["result_message"].lower()
        self.assertIn("retry", msg)
        self.assertIn("payment link", msg)
        self.assertIn("hybrid", msg)

    # ------------------------------------------------------------------
    # 12. Duplicate execution -> safely handled
    # ------------------------------------------------------------------
    def test_12_duplicate_execution_safely_handled(self):
        payment = self._create_eligible_payment()

        # First execution
        res1 = self.client.post(f"/api/recovery/execute/{payment.id}")
        self.assertEqual(res1.status_code, 200)
        self.assertTrue(res1.json()["executed"])
        first_id = res1.json()["id"]

        # Second execution (duplicate)
        res2 = self.client.post(f"/api/recovery/execute/{payment.id}")
        self.assertEqual(res2.status_code, 409)
        data2 = res2.json()
        self.assertFalse(data2["executed"])
        self.assertEqual(data2["status"], "ALREADY_EXECUTED")
        self.assertEqual(data2["duplicate_of"], first_id)

    # ------------------------------------------------------------------
    # 13. Verify no Razorpay execution API is called
    # ------------------------------------------------------------------
    @patch("app.services.razorpay_service.create_order")
    @patch("app.services.razorpay_service.create_payment_link")
    def test_13_no_razorpay_api_called(self, mock_link, mock_order):
        payment = self._create_eligible_payment()
        res = self.client.post(f"/api/recovery/execute/{payment.id}")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["executed"])
        self.assertTrue(res.json()["simulated"])
        mock_order.assert_not_called()
        mock_link.assert_not_called()

    # ------------------------------------------------------------------
    # 14. Existing GET /api/payments still works
    # ------------------------------------------------------------------
    def test_14_existing_payments_endpoint_works(self):
        res = self.client.get("/api/payments")
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.json(), list)

    # ------------------------------------------------------------------
    # 15. Unsupported action returns 400
    # ------------------------------------------------------------------
    def test_unsupported_action_returns_400(self):
        payment = self._create_eligible_payment()
        res = self.client.post(
            f"/api/recovery/execute/{payment.id}",
            json={"action": "REFUND"},
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("unsupported", res.json()["detail"].lower())

    # ------------------------------------------------------------------
    # 16. Execution record persisted in database
    # ------------------------------------------------------------------
    def test_execution_record_persisted_in_db(self):
        payment = self._create_eligible_payment()
        res = self.client.post(f"/api/recovery/execute/{payment.id}")
        self.assertEqual(res.status_code, 200)
        exec_id = res.json()["id"]

        # Verify in database
        self.db.expire_all()
        execution = (
            self.db.query(RecoveryExecution)
            .filter(RecoveryExecution.id == exec_id)
            .first()
        )
        self.assertIsNotNone(execution)
        self.assertEqual(execution.payment_id, payment.id)
        self.assertEqual(execution.action, "RETRY")
        self.assertEqual(execution.status, SIMULATED)
        self.assertEqual(execution.execution_mode, DRY_RUN)
        self.assertTrue(execution.simulated)
        self.assertIsNotNone(execution.result_message)
        self.assertIsNotNone(execution.started_at)
        self.assertIsNotNone(execution.completed_at)

    # ------------------------------------------------------------------
    # 17. Firewall checks stored on execution record
    # ------------------------------------------------------------------
    def test_firewall_checks_stored_on_execution(self):
        payment = self._create_eligible_payment()
        res = self.client.post(f"/api/recovery/execute/{payment.id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertTrue(data["firewall_approved"])
        self.assertEqual(data["firewall_decision"], "APPROVED")
        self.assertIsNotNone(data["firewall_reason"])
        self.assertIsNotNone(data["firewall_policy_version"])

    # ------------------------------------------------------------------
    # 18. Health endpoint still works
    # ------------------------------------------------------------------
    def test_health_endpoint_still_works(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "healthy")

    # ------------------------------------------------------------------
    # 19. Default execution mode is DRY_RUN
    # ------------------------------------------------------------------
    def test_default_execution_mode_is_dry_run(self):
        payment = self._create_eligible_payment()
        # No execution_mode in request body -> defaults to DRY_RUN
        res = self.client.post(f"/api/recovery/execute/{payment.id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["execution_mode"], DRY_RUN)

    # ------------------------------------------------------------------
    # 20. Explicit DRY_RUN mode works
    # ------------------------------------------------------------------
    def test_explicit_dry_run_mode_works(self):
        payment = self._create_eligible_payment()
        res = self.client.post(
            f"/api/recovery/execute/{payment.id}",
            json={"execution_mode": "DRY_RUN"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["execution_mode"], DRY_RUN)
        self.assertTrue(res.json()["simulated"])

    # ------------------------------------------------------------------
    # 21. LIVE mode is rejected
    # ------------------------------------------------------------------
    def test_live_mode_rejected(self):
        payment = self._create_eligible_payment()
        res = self.client.post(
            f"/api/recovery/execute/{payment.id}",
            json={"execution_mode": "LIVE"},
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("not supported", res.json()["detail"].lower())


class TestRecoveryExecutionServiceDirect(unittest.TestCase):
    """Direct unit tests for the RecoveryExecutionService functions."""

    def setUp(self):
        self.db = SessionLocal()

    def tearDown(self):
        self.db.query(RecoveryExecution).filter(
            RecoveryExecution.payment_id.in_(
                self.db.query(Payment.id).filter(
                    Payment.failure_reason == "TEST_EXEC_SVC"
                )
            )
        ).delete(synchronize_session=False)
        self.db.query(Payment).filter(
            Payment.failure_reason == "TEST_EXEC_SVC"
        ).delete(synchronize_session=False)
        self.db.commit()
        self.db.close()

    def _create_payment(self, **overrides) -> Payment:
        defaults = dict(
            amount=20000.0,
            failure_reason="TEST_EXEC_SVC",
            customer_type="Regular",
            payment_status="failed",
            recovery_status="PENDING",
            recommended_action="PAYMENT_LINK",
            confidence=0.90,
            recovery_probability=0.80,
            expected_recovery=16000.0,
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

    def test_service_rejects_none_payment(self):
        from app.services.recovery_execution_service import execute_recovery_action
        with self.assertRaises(ValueError) as ctx:
            execute_recovery_action(payment=None, db=self.db)
        self.assertIn("not found", str(ctx.exception).lower())

    def test_service_rejects_no_action(self):
        from app.services.recovery_execution_service import execute_recovery_action
        payment = self._create_payment(recommended_action=None)
        with self.assertRaises(ValueError) as ctx:
            execute_recovery_action(payment=payment, db=self.db)
        self.assertIn("no recovery action", str(ctx.exception).lower())

    def test_service_rejects_unsupported_action(self):
        from app.services.recovery_execution_service import execute_recovery_action
        payment = self._create_payment()
        with self.assertRaises(ValueError) as ctx:
            execute_recovery_action(payment=payment, action="CHARGE_AGAIN", db=self.db)
        self.assertIn("unsupported", str(ctx.exception).lower())

    def test_service_rejects_live_mode(self):
        from app.services.recovery_execution_service import execute_recovery_action
        payment = self._create_payment()
        with self.assertRaises(ValueError) as ctx:
            execute_recovery_action(
                payment=payment, execution_mode="LIVE", db=self.db
            )
        self.assertIn("not supported", str(ctx.exception).lower())

    def test_service_all_four_actions_simulated(self):
        from app.services.recovery_execution_service import execute_recovery_action
        for action in ("RETRY", "PAYMENT_LINK", "REMINDER", "HYBRID"):
            payment = self._create_payment()
            result = execute_recovery_action(
                payment=payment, action=action, db=self.db
            )
            self.assertTrue(result["executed"], f"Action {action} was not executed")
            self.assertEqual(result["status"], SIMULATED)
            self.assertTrue(result["simulated"])
            self.assertEqual(result["action"], action)


if __name__ == "__main__":
    unittest.main()
