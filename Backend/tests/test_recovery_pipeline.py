"""Automated tests for the RecoverAI recovery orchestration pipeline.

Tests the end-to-end flow:

    payment -> AI Decision -> Action Firewall -> DRY_RUN Execution

covering the webhook-triggered path and the manual ``process`` endpoint.
External services (Ollama / Razorpay) are mocked so no real calls are made.
"""

import hashlib
import hmac
import json
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import FirewallAuditLog, Payment, RazorpayWebhook, RecoveryExecution
from app.services.recovery_execution_service import (
    DRY_RUN,
    SIMULATED,
)
from app.services.razorpay_service import reset_client

TEST_WEBHOOK_SECRET = "whsec_orch_secret_key_abcdef"


def compute_webhook_signature(body: str, secret: str = TEST_WEBHOOK_SECRET) -> str:
    return hmac.new(
        key=secret.encode("utf-8"),
        msg=body.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


def _decision_dict(**overrides) -> dict:
    base = {
        "recommended_action": "RETRY",
        "recovery_probability": 0.85,
        "confidence": 0.9,
        "expected_recovery": 8500.0,
        "risk_level": "LOW",
        "reason": "Transient gateway error; retry recommended.",
        "decision_source": "OLLAMA",
        "model": "test-model",
    }
    base.update(overrides)
    return base


class TestRecoveryPipeline(unittest.TestCase):
    """Test the orchestration pipeline via the process endpoint and webhook."""

    def _cleanup(self):
        db = SessionLocal()
        try:
            db.query(RazorpayWebhook).filter(
                RazorpayWebhook.razorpay_payment_id.like("pay_orch_%")
            ).delete(synchronize_session=False)
            db.query(FirewallAuditLog).filter(
                FirewallAuditLog.payment_id.in_(
                    db.query(Payment.id).filter(
                        Payment.failure_reason == "TEST_PIPELINE"
                    )
                )
            ).delete(synchronize_session=False)
            db.query(RecoveryExecution).filter(
                RecoveryExecution.payment_id.in_(
                    db.query(Payment.id).filter(
                        Payment.failure_reason == "TEST_PIPELINE"
                    )
                )
            ).delete(synchronize_session=False)
            db.query(FirewallAuditLog).filter(
                FirewallAuditLog.payment_id.in_(
                    db.query(Payment.id).filter(
                        Payment.razorpay_payment_id.like("pay_orch_%")
                    )
                )
            ).delete(synchronize_session=False)
            db.query(Payment).filter(
                Payment.failure_reason == "TEST_PIPELINE"
            ).delete(synchronize_session=False)
            db.query(Payment).filter(
                Payment.razorpay_payment_id.like("pay_orch_%")
            ).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()

    def setUp(self):
        self._cleanup()
        self.client = TestClient(app)
        self.db = SessionLocal()
        reset_client()

    def tearDown(self):
        self.db.close()
        self._cleanup()
        reset_client()

    def _create_payment(self, **overrides) -> Payment:
        defaults = dict(
            amount=10000.0,
            failure_reason="TEST_PIPELINE",
            customer_type="Regular",
            payment_status="failed",
            recovery_status="PENDING",
            recommended_action="RETRY",
            confidence=0.9,
            recovery_probability=0.85,
            expected_recovery=8500.0,
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

    def _apply_ai(self, payment, decision):
        """Apply an AI decision onto the payment (mirrors analyze_and_persist_payment)."""
        payment.recommended_action = decision["recommended_action"]
        payment.confidence = decision["confidence"]
        payment.recovery_probability = decision["recovery_probability"]
        payment.recovery_score = decision["recovery_probability"]
        payment.expected_recovery = decision.get("expected_recovery")
        payment.risk_level = decision["risk_level"]
        payment.reason = decision["reason"]
        payment.decision_source = decision.get("decision_source", "OLLAMA")
        payment.ai_decision_at = datetime.now(timezone.utc)
        return {
            "payment_id": payment.id,
            "amount": payment.amount,
            "recommended_action": decision["recommended_action"],
            "recovery_probability": decision["recovery_probability"],
            "confidence": decision["confidence"],
            "expected_recovery": decision.get("expected_recovery"),
            "risk_level": decision["risk_level"],
            "reason": decision["reason"],
            "decision_source": decision.get("decision_source", "OLLAMA"),
            "model": decision.get("model"),
            "ai_decision_at": datetime.now(timezone.utc),
        }

    def _run_process_with_ai(self, payment, decision):
        """Invoke the process endpoint with a mocked AI decision."""
        async def fake_ai(p):
            return self._apply_ai(p, decision)
        fake = AsyncMock(side_effect=fake_ai)
        with patch("app.services.recovery_orchestrator.analyze_and_persist_payment", fake):
            return self.client.post(f"/api/recovery/process/{payment.id}")

    # ------------------------------------------------------------------
    # 1. Valid failed payment -> AI -> Firewall -> DRY_RUN execution
    # ------------------------------------------------------------------
    def test_pipeline_successful_dry_run(self):
        payment = self._create_payment()
        res = self._run_process_with_ai(payment, _decision_dict())
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["eligible"])
        self.assertEqual(data["ai_decision"]["recommended_action"], "RETRY")
        self.assertTrue(data["firewall"]["approved"])
        self.assertEqual(data["execution"]["status"], SIMULATED)
        self.assertEqual(data["execution"]["execution_mode"], DRY_RUN)
        self.assertTrue(data["execution"]["simulated"])

        # Verify execution persisted with DRY_RUN in DB
        self.db.expire_all()
        exec_row = self.db.query(RecoveryExecution).filter(
            RecoveryExecution.payment_id == payment.id
        ).first()
        self.assertIsNotNone(exec_row)
        self.assertEqual(exec_row.execution_mode, DRY_RUN)
        self.assertEqual(exec_row.status, SIMULATED)

    # ------------------------------------------------------------------
    # 2. Low AI confidence -> Firewall rejects -> execution NOT called
    # ------------------------------------------------------------------
    def test_low_confidence_rejected(self):
        payment = self._create_payment()
        res = self._run_process_with_ai(payment, _decision_dict(confidence=0.5))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["firewall"]["approved"])
        self.assertEqual(data["execution"]["status"], "NOT_EXECUTED")

        # No execution row should exist
        self.db.expire_all()
        count = self.db.query(RecoveryExecution).filter(
            RecoveryExecution.payment_id == payment.id
        ).count()
        self.assertEqual(count, 0)

    # ------------------------------------------------------------------
    # 3. Low recovery probability -> Firewall rejects
    # ------------------------------------------------------------------
    def test_low_recovery_probability_rejected(self):
        payment = self._create_payment()
        res = self._run_process_with_ai(payment, _decision_dict(recovery_probability=0.5))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["firewall"]["approved"])
        self.assertEqual(data["execution"]["status"], "NOT_EXECUTED")

    # ------------------------------------------------------------------
    # 4. Already recovered payment -> pipeline rejected
    # ------------------------------------------------------------------
    def test_already_recovered_pipeline_rejected(self):
        payment = self._create_payment(
            recovery_status="SUCCESS",
            payment_status="captured",
        )
        async def fake_ai(p):
            return self._apply_ai(p, _decision_dict())
        fake = AsyncMock(side_effect=fake_ai)
        with patch("app.services.recovery_orchestrator.analyze_and_persist_payment", fake):
            res = self.client.post(f"/api/recovery/process/{payment.id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["eligible"])
        # AI must NOT be called for ineligible payment
        fake.assert_not_awaited()

    # ------------------------------------------------------------------
    # 5. Maximum retry count -> Firewall rejects
    # ------------------------------------------------------------------
    def test_max_retry_rejected(self):
        payment = self._create_payment(retry_count=2)
        res = self._run_process_with_ai(payment, _decision_dict())
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["firewall"]["approved"])
        self.assertEqual(data["execution"]["status"], "NOT_EXECUTED")

    # ------------------------------------------------------------------
    # 6. Transaction amount above limit -> Firewall rejects
    # ------------------------------------------------------------------
    def test_amount_above_limit_rejected(self):
        payment = self._create_payment(amount=75000.0)
        res = self._run_process_with_ai(payment, _decision_dict())
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["firewall"]["approved"])
        self.assertEqual(data["execution"]["status"], "NOT_EXECUTED")

    # ------------------------------------------------------------------
    # 7. Duplicate webhook -> pipeline does not execute twice
    # ------------------------------------------------------------------
    @patch.dict(os.environ, {"RAZORPAY_WEBHOOK_SECRET": TEST_WEBHOOK_SECRET})
    def test_duplicate_webhook_pipeline_not_rerun(self):
        pay_id = "pay_orch_dedup_001"
        payload_dict = {
            "entity": "event",
            "event": "payment.failed",
            "created_at": 1714101000,
            "payload": {
                "payment": {
                    "entity": {
                        "id": pay_id,
                        "amount": 100000,
                        "currency": "INR",
                        "status": "failed",
                        "method": "upi",
                        "error_code": "BAD_REQUEST_ERROR",
                        "error_description": "Bank timeout",
                        "created_at": 1714101000,
                    }
                }
            },
        }
        raw_body = json.dumps(payload_dict)
        signature = compute_webhook_signature(raw_body)
        headers = {"Content-Type": "application/json", "X-Razorpay-Signature": signature}

        mock_pipeline = AsyncMock(return_value={"eligible": True, "status": "ok"})
        with patch("app.services.webhook_service.process_failed_payment", mock_pipeline):
            res1 = self.client.post("/api/webhooks/razorpay", content=raw_body, headers=headers)
            self.assertEqual(res1.status_code, 200)
            self.assertEqual(res1.json()["status"], "PROCESSED")

            res2 = self.client.post("/api/webhooks/razorpay", content=raw_body, headers=headers)
            self.assertEqual(res2.status_code, 200)
            self.assertEqual(res2.json()["status"], "DUPLICATE")

        # Pipeline must be triggered exactly once
        self.assertEqual(mock_pipeline.await_count, 1)

    # ------------------------------------------------------------------
    # 8. AI unavailable -> existing rule fallback is used
    # ------------------------------------------------------------------
    def test_ai_unavailable_uses_fallback(self):
        payment = self._create_payment()
        with patch(
            "app.services.recovery_ai_service._call_ollama_raw",
            side_effect=RuntimeError("Ollama unavailable"),
        ):
            res = self.client.post(f"/api/recovery/process/{payment.id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["eligible"])
        self.assertEqual(
            data["ai_decision"]["decision_source"],
            "RULE_ENGINE_FALLBACK",
        )
        self.assertIsNotNone(data["ai_decision"]["recommended_action"])

    # ------------------------------------------------------------------
    # 9.Execution remains DRY_RUN (verified via execute service)
    # ------------------------------------------------------------------
    def test_execution_remains_dry_run(self):
        payment = self._create_payment()
        res = self._run_process_with_ai(payment, _decision_dict())
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["execution"]["execution_mode"], DRY_RUN)
        self.assertNotEqual(data["execution"]["status"], "LIVE")

    # ------------------------------------------------------------------
    # 10. Captured payment -> recovery pipeline is NOT triggered
    # ------------------------------------------------------------------
    @patch.dict(os.environ, {"RAZORPAY_WEBHOOK_SECRET": TEST_WEBHOOK_SECRET})
    def test_captured_webhook_does_not_trigger_pipeline(self):
        pay_id = "pay_orch_cap_002"
        payload_dict = {
            "entity": "event",
            "event": "payment.captured",
            "created_at": 1714102000,
            "payload": {
                "payment": {
                    "entity": {
                        "id": pay_id,
                        "amount": 100000,
                        "currency": "INR",
                        "status": "captured",
                        "method": "card",
                        "created_at": 1714102000,
                    }
                }
            },
        }
        raw_body = json.dumps(payload_dict)
        signature = compute_webhook_signature(raw_body)
        headers = {"Content-Type": "application/json", "X-Razorpay-Signature": signature}

        mock_pipeline = AsyncMock(return_value={"eligible": True})
        with patch("app.services.webhook_service.process_failed_payment", mock_pipeline):
            res = self.client.post("/api/webhooks/razorpay", content=raw_body, headers=headers)
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["event"], "payment.captured")

        # Pipeline must never be invoked for captured events
        mock_pipeline.assert_not_awaited()

        # Payment should be marked recovered
        payment = self.db.query(Payment).filter(
            Payment.razorpay_payment_id == pay_id
        ).first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.recovery_status, "SUCCESS")

    # ------------------------------------------------------------------
    # Additional: process endpoint for non-existent payment -> 404
    # ------------------------------------------------------------------
    def test_process_payment_not_found_404(self):
        res = self.client.post("/api/recovery/process/999999")
        self.assertEqual(res.status_code, 404)
        self.assertIn("not found", res.json()["detail"].lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
