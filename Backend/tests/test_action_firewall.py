"""Automated tests for RecoverAI Action Firewall / Merchant Governance Layer."""

from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import FirewallAuditLog, Payment
from app.services.action_firewall import (
    ActionFirewall,
    AUTONOMOUS_LIMIT_INR,
    MIN_CONFIDENCE,
    MIN_RECOVERY_PROBABILITY,
    MAX_RETRIES,
    COOLDOWN_MINUTES,
)


class TestActionFirewall(unittest.TestCase):
    """Test policy checks, governance evaluation, and firewall endpoint."""

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()

    def tearDown(self):
        # Clean up test payments and audit logs
        self.db.query(FirewallAuditLog).filter(
            FirewallAuditLog.payment_id.in_(
                self.db.query(Payment.id).filter(Payment.failure_reason == "TEST_FIREWALL")
            )
        ).delete(synchronize_session=False)
        self.db.query(Payment).filter(
            Payment.failure_reason == "TEST_FIREWALL"
        ).delete(synchronize_session=False)
        self.db.commit()
        self.db.close()

    def test_1_valid_low_risk_retry_approved(self):
        """Valid low-risk RETRY should be approved with all checks passing."""
        result = ActionFirewall.evaluate(
            amount=25000.0,
            action="RETRY",
            confidence=0.92,
            recovery_probability=0.88,
            retry_count=0,
            previous_recovery_attempts=0,
            payment_status="failed",
            recovery_status="PENDING",
            risk_level="LOW",
        )
        self.assertTrue(result["approved"])
        self.assertEqual(result["action"], "RETRY")
        self.assertEqual(result["risk_level"], "LOW")
        self.assertEqual(result["reason"], "All autonomous recovery policy checks passed")
        for check in result["checks"]:
            self.assertTrue(check["passed"], f"Check {check['name']} failed unexpectedly")

    def test_2_amount_exceeds_limit_rejected(self):
        """Amount > ₹50,000 must be rejected by transaction_limit check."""
        result = ActionFirewall.evaluate(
            amount=75000.0,  # > 50,000
            action="RETRY",
            confidence=0.95,
            recovery_probability=0.90,
            retry_count=0,
            payment_status="failed",
        )
        self.assertFalse(result["approved"])
        self.assertIn("exceeds autonomous execution limit", result["reason"].lower())
        limit_check = next(c for c in result["checks"] if c["name"] == "transaction_limit")
        self.assertFalse(limit_check["passed"])

    def test_3_low_confidence_rejected(self):
        """AI Confidence < 0.85 must be rejected by confidence_threshold check."""
        result = ActionFirewall.evaluate(
            amount=10000.0,
            action="RETRY",
            confidence=0.80,  # < 0.85
            recovery_probability=0.85,
            retry_count=0,
            payment_status="failed",
        )
        self.assertFalse(result["approved"])
        self.assertIn("confidence below", result["reason"].lower())
        conf_check = next(c for c in result["checks"] if c["name"] == "confidence_threshold")
        self.assertFalse(conf_check["passed"])

    def test_4_low_recovery_probability_rejected(self):
        """Recovery probability < 0.70 must be rejected by recovery_probability check."""
        result = ActionFirewall.evaluate(
            amount=15000.0,
            action="RETRY",
            confidence=0.90,
            recovery_probability=0.65,  # < 0.70
            retry_count=0,
            payment_status="failed",
        )
        self.assertFalse(result["approved"])
        self.assertIn("recovery probability below", result["reason"].lower())
        prob_check = next(c for c in result["checks"] if c["name"] == "recovery_probability")
        self.assertFalse(prob_check["passed"])

    def test_5_retry_count_limit_reached_rejected(self):
        """Retry count >= 2 must be rejected by retry_count check."""
        result = ActionFirewall.evaluate(
            amount=10000.0,
            action="RETRY",
            confidence=0.90,
            recovery_probability=0.85,
            retry_count=2,  # >= 2
            payment_status="failed",
        )
        self.assertFalse(result["approved"])
        self.assertIn("maximum retry limit reached", result["reason"].lower())
        retry_check = next(c for c in result["checks"] if c["name"] == "retry_count")
        self.assertFalse(retry_check["passed"])

    def test_6_already_captured_payment_rejected(self):
        """Payments that are already captured or recovered must be rejected."""
        result_captured = ActionFirewall.evaluate(
            amount=10000.0,
            action="RETRY",
            confidence=0.90,
            recovery_probability=0.85,
            payment_status="captured",
        )
        self.assertFalse(result_captured["approved"])
        self.assertIn("no longer eligible", result_captured["reason"].lower())
        status_check = next(c for c in result_captured["checks"] if c["name"] == "payment_status")
        self.assertFalse(status_check["passed"])

        result_success = ActionFirewall.evaluate(
            amount=10000.0,
            action="RETRY",
            confidence=0.90,
            recovery_probability=0.85,
            recovery_status="SUCCESS",
        )
        self.assertFalse(result_success["approved"])

    def test_7_unknown_action_rejected(self):
        """Unsupported action (e.g. REFUND or CHARGE_AGAIN) must be rejected."""
        result = ActionFirewall.evaluate(
            amount=10000.0,
            action="REFUND_CUSTOMER",
            confidence=0.90,
            recovery_probability=0.85,
            payment_status="failed",
        )
        self.assertFalse(result["approved"])
        self.assertIn("unsupported recovery action", result["reason"].lower())
        action_check = next(c for c in result["checks"] if c["name"] == "allowed_action")
        self.assertFalse(action_check["passed"])

    def test_8_cooldown_within_15_minutes_rejected(self):
        """RETRY within 15 minutes of prior attempt must be rejected."""
        now = datetime.now(timezone.utc)
        recent_attempt = now - timedelta(minutes=5)  # 5m ago < 15m

        result = ActionFirewall.evaluate(
            amount=10000.0,
            action="RETRY",
            confidence=0.90,
            recovery_probability=0.85,
            retry_count=1,
            last_recovery_attempt_at=recent_attempt,
            now=now,
        )
        self.assertFalse(result["approved"])
        self.assertIn("cooldown", result["reason"].lower())
        cooldown_check = next(c for c in result["checks"] if c["name"] == "cooldown")
        self.assertFalse(cooldown_check["passed"])

    def test_9_cooldown_after_15_minutes_approved(self):
        """RETRY after 15 minutes of prior attempt must be approved."""
        now = datetime.now(timezone.utc)
        prior_attempt = now - timedelta(minutes=20)  # 20m ago >= 15m

        result = ActionFirewall.evaluate(
            amount=10000.0,
            action="RETRY",
            confidence=0.90,
            recovery_probability=0.85,
            retry_count=1,
            last_recovery_attempt_at=prior_attempt,
            now=now,
        )
        self.assertTrue(result["approved"])
        cooldown_check = next(c for c in result["checks"] if c["name"] == "cooldown")
        self.assertTrue(cooldown_check["passed"])

    def test_10_prior_retry_missing_timestamp_fails_safely(self):
        """If retry_count > 0 but last_recovery_attempt_at is missing, fail safely."""
        result = ActionFirewall.evaluate(
            amount=10000.0,
            action="RETRY",
            confidence=0.90,
            recovery_probability=0.85,
            retry_count=1,
            last_recovery_attempt_at=None,
        )
        self.assertFalse(result["approved"])
        self.assertIn("cooldown timestamp unavailable", result["reason"].lower())
        cooldown_check = next(c for c in result["checks"] if c["name"] == "cooldown")
        self.assertFalse(cooldown_check["passed"])

    def test_11_api_endpoint_evaluation_and_audit_logging(self):
        """POST /api/recovery/firewall/{payment_id} evaluates and creates audit records."""
        # Create failed payment in DB with high confidence decision
        payment = Payment(
            amount=18000.0,
            failure_reason="TEST_FIREWALL",
            customer_type="Regular",
            payment_status="failed",
            recovery_status="PENDING",
            recommended_action="RETRY",
            confidence=0.92,
            recovery_probability=0.85,
            retry_count=0,
            risk_level="LOW",
        )
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        pid = payment.id

        # Call POST /api/recovery/firewall/{pid}
        res = self.client.post(f"/api/recovery/firewall/{pid}")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertTrue(data["approved"])
        self.assertEqual(data["action"], "RETRY")
        self.assertEqual(data["policy_version"], "v1.0")
        self.assertEqual(len(data["checks"]), 7)

        # Verify Payment model columns were updated
        self.db.expire_all()
        saved = self.db.query(Payment).filter(Payment.id == pid).first()
        self.assertTrue(saved.firewall_approved)
        self.assertEqual(saved.firewall_decision, "APPROVED")
        self.assertIsNotNone(saved.firewall_checked_at)

        # Verify FirewallAuditLog entry was inserted
        audit = (
            self.db.query(FirewallAuditLog)
            .filter(FirewallAuditLog.payment_id == pid)
            .order_by(FirewallAuditLog.id.desc())
            .first()
        )
        self.assertIsNotNone(audit)
        self.assertEqual(audit.recommended_action, "RETRY")
        self.assertTrue(audit.approved)
        self.assertEqual(audit.policy_version, "v1.0")

    def test_12_api_nonexistent_payment_returns_404(self):
        """POST /api/recovery/firewall/999999 returns 404."""
        res = self.client.post("/api/recovery/firewall/999999")
        self.assertEqual(res.status_code, 404)
        self.assertIn("not found", res.json()["detail"].lower())

    @patch("app.services.razorpay_service.create_order")
    def test_13_firewall_never_executes_razorpay_actions(self, mock_razorpay):
        """Evaluating the firewall must never make any call to Razorpay APIs."""
        payment = Payment(
            amount=10000.0,
            failure_reason="TEST_FIREWALL",
            customer_type="Regular",
            payment_status="failed",
            recovery_status="PENDING",
            recommended_action="RETRY",
            confidence=0.95,
            recovery_probability=0.90,
            retry_count=0,
        )
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)

        res = self.client.post(f"/api/recovery/firewall/{payment.id}")
        self.assertEqual(res.status_code, 200)

        # Assert no Razorpay call was initiated
        mock_razorpay.assert_not_called()


if __name__ == "__main__":
    unittest.main()

