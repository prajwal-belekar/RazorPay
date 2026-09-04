"""Automated tests for the RecoverAI Recovery Passport / Audit Trail.

Covers the ``GET /api/recovery/passport/{payment_id}`` read-only endpoint:

  1. Valid passport (all sections populated)
  2. Nonexistent payment -> 404
  3. Payment with no recovery execution -> graceful
  4. Payment with an AI decision
  5. Firewall approved
  6. Firewall rejected
  7. RETRY execution surfaced
  8. PAYMENT_LINK execution surfaced
  9. REMINDER execution surfaced
  10. HYBRID execution with structured steps
  11. DRY_RUN fields surfaced
  12. Provider fields remain null
  13. No Razorpay call
  14. No mutation when fetching the passport
  15. Secrets never returned
  16. Existing endpoints / behaviour preserved (plus full regression suite)
"""

import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import FirewallAuditLog, Payment, RecoveryExecution

TEST_MARKER = "TEST_PASSPORT"


class TestRecoveryPassport(unittest.TestCase):
    """Test the Recovery Passport read-only API."""

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()
        self._cleanup()

    def tearDown(self):
        self._cleanup()
        self.db.close()

    def _cleanup(self):
        ids = [
            row.id
            for row in self.db.query(Payment.id)
            .filter(Payment.failure_reason == TEST_MARKER)
            .all()
        ]
        if ids:
            self.db.query(FirewallAuditLog).filter(
                FirewallAuditLog.payment_id.in_(ids)
            ).delete(synchronize_session=False)
            self.db.query(RecoveryExecution).filter(
                RecoveryExecution.payment_id.in_(ids)
            ).delete(synchronize_session=False)
            self.db.query(Payment).filter(Payment.id.in_(ids)).delete(
                synchronize_session=False
            )
            self.db.commit()

    def _create_payment(self, **overrides) -> Payment:
        defaults = dict(
            amount=20000.0,
            failure_reason=TEST_MARKER,
            customer_type="Regular",
            payment_status="failed",
            recovery_status="PENDING",
            recommended_action="RETRY",
            confidence=0.92,
            recovery_probability=0.85,
            expected_recovery=17000.0,
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

    def _add_ai_decision(self, payment: Payment, **overrides):
        decision = dict(
            recommended_action="RETRY",
            confidence=0.92,
            recovery_probability=0.85,
            expected_recovery=17000.0,
            risk_level="LOW",
            reason="Transient gateway error; retry recommended.",
            decision_source="OLLAMA",
        )
        decision.update(overrides)
        payment.recommended_action = decision["recommended_action"]
        payment.confidence = decision["confidence"]
        payment.recovery_probability = decision["recovery_probability"]
        payment.recovery_score = decision["recovery_probability"]
        payment.expected_recovery = decision.get("expected_recovery")
        payment.risk_level = decision["risk_level"]
        payment.reason = decision.get("reason")
        payment.decision_source = decision.get("decision_source")
        payment.ai_decision_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(payment)

    def _add_firewall_audit(self, payment: Payment, approved: bool = True):
        audit = FirewallAuditLog(
            payment_id=payment.id,
            recommended_action=payment.recommended_action or "RETRY",
            approved=approved,
            risk_level=payment.risk_level or "LOW",
            policy_version="v1.0",
            reason=(
                "All autonomous recovery policy checks passed"
                if approved
                else "AI confidence below autonomous execution threshold"
            ),
            checks=[
                {"name": "transaction_limit", "passed": True},
                {"name": "confidence_threshold", "passed": approved},
                {"name": "recovery_probability", "passed": True},
                {"name": "retry_count", "passed": True},
                {"name": "payment_status", "passed": True},
                {"name": "allowed_action", "passed": True},
                {"name": "cooldown", "passed": True},
            ],
            evaluation_timestamp=datetime.now(timezone.utc),
        )
        self.db.add(audit)
        self.db.commit()

    # ------------------------------------------------------------------
    # 1. Valid passport — all sections populated
    # ------------------------------------------------------------------
    def test_1_valid_passport(self):
        payment = self._create_payment()
        self._add_ai_decision(payment)
        self._add_firewall_audit(payment, approved=True)
        self.client.post(f"/api/recovery/execute/{payment.id}")

        res = self.client.get(f"/api/recovery/passport/{payment.id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["payment_id"], payment.id)
        self.assertEqual(data["failure_reason"], TEST_MARKER)
        self.assertEqual(data["payment_status"], "failed")
        self.assertEqual(data["recovery_status"], "PENDING")
        self.assertIsNotNone(data["timestamp"])

        self.assertEqual(data["ai_decision"]["action"], "RETRY")
        self.assertEqual(data["ai_decision"]["confidence"], 0.92)
        self.assertEqual(data["ai_decision"]["recovery_probability"], 0.85)

        self.assertTrue(data["firewall"]["approved"])
        self.assertEqual(data["firewall"]["policy_version"], "v1.0")
        self.assertGreaterEqual(len(data["firewall"]["checks"]), 1)

        self.assertEqual(data["recovery"]["action"], "RETRY")
        self.assertEqual(data["recovery"]["execution_mode"], "DRY_RUN")
        self.assertEqual(data["recovery"]["status"], "SIMULATED")
        self.assertEqual(data["hybrid_steps"], [])

    # ------------------------------------------------------------------
    # 2. Nonexistent payment -> 404
    # ------------------------------------------------------------------
    def test_2_nonexistent_payment_returns_404(self):
        res = self.client.get("/api/recovery/passport/999999")
        self.assertEqual(res.status_code, 404)
        self.assertIn("not found", res.json()["detail"].lower())

    # ------------------------------------------------------------------
    # 3. Payment with no recovery execution -> graceful
    # ------------------------------------------------------------------
    def test_3_payment_with_no_execution(self):
        payment = self._create_payment()
        self._add_ai_decision(payment)
        self._add_firewall_audit(payment, approved=True)

        res = self.client.get(f"/api/recovery/passport/{payment.id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertIsNone(data["recovery"])
        self.assertEqual(data["hybrid_steps"], [])
        self.assertIsNotNone(data["ai_decision"])
        self.assertIsNotNone(data["firewall"])

    # ------------------------------------------------------------------
    # 4. Payment with an AI decision
    # ------------------------------------------------------------------
    def test_4_ai_decision_surfaced(self):
        payment = self._create_payment()
        self._add_ai_decision(
            payment,
            recommended_action="REMINDER",
            confidence=0.95,
            recovery_probability=0.80,
        )

        res = self.client.get(f"/api/recovery/passport/{payment.id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["ai_decision"]["action"], "REMINDER")
        self.assertEqual(data["ai_decision"]["confidence"], 0.95)
        self.assertEqual(data["ai_decision"]["recovery_probability"], 0.80)
        self.assertIsNotNone(data["ai_decision"]["ai_decision_at"])

    def test_4b_payment_without_ai_decision(self):
        payment = self._create_payment(recommended_action=None)
        res = self.client.get(f"/api/recovery/passport/{payment.id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIsNone(data["ai_decision"])

    # ------------------------------------------------------------------
    # 5. Firewall approved
    # ------------------------------------------------------------------
    def test_5_firewall_approved(self):
        payment = self._create_payment()
        self._add_ai_decision(payment)
        self._add_firewall_audit(payment, approved=True)

        res = self.client.get(f"/api/recovery/passport/{payment.id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertTrue(data["firewall"]["approved"])
        self.assertEqual(data["firewall"]["action"], "RETRY")
        self.assertEqual(data["firewall"]["policy_version"], "v1.0")
        self.assertEqual(data["firewall"]["risk_level"], "LOW")
        self.assertEqual(data["firewall"]["reason"], "All autonomous recovery policy checks passed")
        self.assertGreaterEqual(len(data["firewall"]["checks"]), 1)

    # ------------------------------------------------------------------
    # 6. Firewall rejected
    # ------------------------------------------------------------------
    def test_6_firewall_rejected(self):
        payment = self._create_payment()
        self._add_ai_decision(payment, confidence=0.5)
        self._add_firewall_audit(payment, approved=False)

        res = self.client.get(f"/api/recovery/passport/{payment.id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertFalse(data["firewall"]["approved"])
        self.assertEqual(
            data["firewall"]["reason"],
            "AI confidence below autonomous execution threshold",
        )
        confidence_check = next(
            c
            for c in data["firewall"]["checks"]
            if c["name"] == "confidence_threshold"
        )
        self.assertFalse(confidence_check["passed"])

    # ------------------------------------------------------------------
    # 7. RETRY execution
    # ------------------------------------------------------------------
    def test_7_retry_execution_surfaced(self):
        payment = self._create_payment(recommended_action="RETRY")
        self._add_ai_decision(payment)
        res = self.client.post(f"/api/recovery/execute/{payment.id}")
        self.assertEqual(res.status_code, 200)

        res = self.client.get(f"/api/recovery/passport/{payment.id}")
        data = res.json()
        self.assertEqual(data["recovery"]["action"], "RETRY")
        self.assertIn("simulated", data["recovery"]["result_message"].lower())

    # ------------------------------------------------------------------
    # 8. PAYMENT_LINK execution
    # ------------------------------------------------------------------
    def test_8_payment_link_execution_surfaced(self):
        payment = self._create_payment(recommended_action="PAYMENT_LINK")
        self._add_ai_decision(payment)
        res = self.client.post(
            f"/api/recovery/execute/{payment.id}",
            json={"action": "PAYMENT_LINK"},
        )
        self.assertEqual(res.status_code, 200)

        data = self.client.get(f"/api/recovery/passport/{payment.id}").json()
        self.assertEqual(data["recovery"]["action"], "PAYMENT_LINK")
        self.assertIn("payment link", data["recovery"]["result_message"].lower())

    # ------------------------------------------------------------------
    # 9. REMINDER execution
    # ------------------------------------------------------------------
    def test_9_reminder_execution_surfaced(self):
        payment = self._create_payment(recommended_action="REMINDER")
        self._add_ai_decision(payment)
        res = self.client.post(
            f"/api/recovery/execute/{payment.id}",
            json={"action": "REMINDER"},
        )
        self.assertEqual(res.status_code, 200)

        data = self.client.get(f"/api/recovery/passport/{payment.id}").json()
        self.assertEqual(data["recovery"]["action"], "REMINDER")
        self.assertIsNotNone(data["recovery"]["execution_mode"])

    # ------------------------------------------------------------------
    # 10. HYBRID execution with structured steps
    # ------------------------------------------------------------------
    def test_10_hybrid_execution_with_steps(self):
        payment = self._create_payment(recommended_action="HYBRID")
        self._add_ai_decision(payment, recommended_action="HYBRID", recovery_probability=0.75)
        res = self.client.post(
            f"/api/recovery/execute/{payment.id}",
            json={"action": "HYBRID"},
        )
        self.assertEqual(res.status_code, 200)

        data = self.client.get(f"/api/recovery/passport/{payment.id}").json()
        self.assertEqual(data["recovery"]["action"], "HYBRID")

        self.assertEqual(len(data["hybrid_steps"]), 3)
        actions = [step["action"] for step in data["hybrid_steps"]]
        self.assertEqual(actions, ["RETRY", "PAYMENT_LINK", "REMINDER"])
        for step in data["hybrid_steps"]:
            self.assertIn(step["status"], {"SIMULATED", "SKIPPED", "BLOCKED"})
            self.assertIn("recovered", step)
            self.assertIn("reason", step)

    # ------------------------------------------------------------------
    # 11. DRY_RUN fields surfaced
    # ------------------------------------------------------------------
    def test_11_dry_run_fields(self):
        payment = self._create_payment(recommended_action="RETRY")
        self._add_ai_decision(payment)
        self.client.post(f"/api/recovery/execute/{payment.id}")

        data = self.client.get(f"/api/recovery/passport/{payment.id}").json()
        self.assertEqual(data["recovery"]["execution_mode"], "DRY_RUN")
        self.assertTrue(data["recovery"]["simulated"])
        self.assertEqual(data["recovery"]["status"], "SIMULATED")

    # ------------------------------------------------------------------
    # 12. Provider fields remain null (DRY_RUN)
    # ------------------------------------------------------------------
    def test_12_provider_fields_null(self):
        payment = self._create_payment(recommended_action="PAYMENT_LINK")
        self._add_ai_decision(payment)
        self.client.post(
            f"/api/recovery/execute/{payment.id}",
            json={"action": "PAYMENT_LINK"},
        )

        data = self.client.get(f"/api/recovery/passport/{payment.id}").json()
        self.assertIsNone(data["recovery"]["provider"])
        self.assertIsNone(data["recovery"]["provider_reference_id"])

    # ------------------------------------------------------------------
    # 13. No Razorpay call
    # ------------------------------------------------------------------
    @patch("app.services.razorpay_service.create_order")
    @patch("app.services.razorpay_service.create_payment_link")
    def test_13_no_razorpay_call(self, mock_link, mock_order):
        payment = self._create_payment()
        self._add_ai_decision(payment)
        self._add_firewall_audit(payment, approved=True)

        res = self.client.get(f"/api/recovery/passport/{payment.id}")
        self.assertEqual(res.status_code, 200)
        mock_order.assert_not_called()
        mock_link.assert_not_called()

    # ------------------------------------------------------------------
    # 14. No mutation when fetching the passport
    # ------------------------------------------------------------------
    def test_14_no_mutation_on_fetch(self):
        payment = self._create_payment()
        self._add_ai_decision(payment)
        self._add_firewall_audit(payment, approved=True)
        self.client.post(f"/api/recovery/execute/{payment.id}")

        self.db.expire_all()
        audit_count = self.db.query(FirewallAuditLog).filter(
            FirewallAuditLog.payment_id == payment.id
        ).count()
        exec_count = self.db.query(RecoveryExecution).filter(
            RecoveryExecution.payment_id == payment.id
        ).count()
        before = (
            self.db.query(Payment).filter(Payment.id == payment.id).first()
        )
        before_snapshot = {
            "recommended_action": before.recommended_action,
            "confidence": before.confidence,
            "recovery_probability": before.recovery_probability,
            "firewall_decision": before.firewall_decision,
            "recovery_status": before.recovery_status,
            "payment_status": before.payment_status,
            "retry_count": before.retry_count,
        }

        res = self.client.get(f"/api/recovery/passport/{payment.id}")
        self.assertEqual(res.status_code, 200)

        self.db.expire_all()
        after_audit_count = self.db.query(FirewallAuditLog).filter(
            FirewallAuditLog.payment_id == payment.id
        ).count()
        after_exec_count = self.db.query(RecoveryExecution).filter(
            RecoveryExecution.payment_id == payment.id
        ).count()
        after = self.db.query(Payment).filter(Payment.id == payment.id).first()
        after_snapshot = {
            "recommended_action": after.recommended_action,
            "confidence": after.confidence,
            "recovery_probability": after.recovery_probability,
            "firewall_decision": after.firewall_decision,
            "recovery_status": after.recovery_status,
            "payment_status": after.payment_status,
            "retry_count": after.retry_count,
        }

        self.assertEqual(after_audit_count, audit_count)
        self.assertEqual(after_exec_count, exec_count)
        self.assertEqual(after_snapshot, before_snapshot)

    # ------------------------------------------------------------------
    # 15. Secrets never returned
    # ------------------------------------------------------------------
    def test_15_secrets_never_returned(self):
        payment = self._create_payment(
            razorpay_signature="sekrit_signature_1234567890",
            razorpay_order_id="order_test_secret_0987654321",
        )
        self._add_ai_decision(payment)
        self.client.post(f"/api/recovery/execute/{payment.id}")

        res = self.client.get(f"/api/recovery/passport/{payment.id}")
        self.assertEqual(res.status_code, 200)
        raw = json.dumps(res.json()).lower()

        self.assertNotIn("sekrit_signature_1234567890", raw)
        self.assertNotIn("order_test_secret_0987654321", raw)
        self.assertNotIn("razorpay_signature", raw)
        self.assertNotIn("secret", raw)
        self.assertNotIn("signature", res.json()["recovery"]["result_message"].lower() or "simulated")

    # ------------------------------------------------------------------
    # 16. Existing recovery endpoints remain functional
    # ------------------------------------------------------------------
    def test_16_existing_recovery_endpoints_functional(self):
        payment = self._create_payment()
        self._add_ai_decision(payment)

        # Cases list endpoint still works
        res = self.client.get("/api/recovery/cases")
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.json(), list)

        # Decision endpoint still works
        res = self.client.get(f"/api/recovery/{payment.id}/decision")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["recommended_action"], "RETRY")

        # Executions endpoint still works
        res = self.client.get(f"/api/recovery/cases/{payment.id}/executions")
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.json(), list)

        # Health endpoint still works
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "healthy")


if __name__ == "__main__":
    unittest.main(verbosity=2)