"""Automated tests for RecoverAI AI Recovery Decision Engine (app/services/recovery_ai_service.py)."""

import os
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.database import SessionLocal
from app.main import app
from app.models import Payment, RecoveryExecution
from app.services.recovery_ai_service import (
    RecoveryDecisionOutput,
    compute_rule_fallback,
    generate_recovery_decision,
    ALLOWED_ACTIONS,
    ALLOWED_RISK_LEVELS,
    SOURCE_OLLAMA,
    SOURCE_FALLBACK,
)


class TestRecoveryAIDecisionEngine(unittest.TestCase):
    """Test AI recovery decision generation, validation, fallback, and API endpoints."""

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()

    def tearDown(self):
        # Clean up any test records created
        self.db.query(RecoveryExecution).filter(
            RecoveryExecution.payment_id.in_(
                self.db.query(Payment.id).filter(Payment.failure_reason == "TEST_RECOVERY_AI")
            )
        ).delete(synchronize_session=False)
        self.db.query(Payment).filter(
            Payment.failure_reason == "TEST_RECOVERY_AI"
        ).delete(synchronize_session=False)
        self.db.commit()
        self.db.close()

    def test_pydantic_validation_valid_output(self):
        """Valid output should validate successfully."""
        data = {
            "recommended_action": "RETRY",
            "recovery_probability": 0.88,
            "confidence": 0.92,
            "expected_recovery": 1500.0,
            "risk_level": "LOW",
            "reason": "Temporary gateway timeout; safe to retry.",
        }
        output = RecoveryDecisionOutput(**data)
        self.assertEqual(output.recommended_action, "RETRY")
        self.assertEqual(output.risk_level, "LOW")
        self.assertAlmostEqual(output.recovery_probability, 0.88)

    def test_pydantic_validation_invalid_action_rejected(self):
        """Invalid recovery action must raise ValidationError."""
        data = {
            "recommended_action": "INVALID_ACTION_XYZ",
            "recovery_probability": 0.5,
            "confidence": 0.5,
            "risk_level": "LOW",
            "reason": "Valid reason explanation.",
        }
        with self.assertRaises(ValidationError):
            RecoveryDecisionOutput(**data)

    def test_pydantic_validation_out_of_bounds_probability(self):
        """Probability > 1.0 or < 0.0 must raise ValidationError."""
        data_over = {
            "recommended_action": "RETRY",
            "recovery_probability": 1.5,
            "confidence": 0.5,
            "risk_level": "LOW",
            "reason": "Valid reason.",
        }
        with self.assertRaises(ValidationError):
            RecoveryDecisionOutput(**data_over)

        data_under = {
            "recommended_action": "RETRY",
            "recovery_probability": -0.2,
            "confidence": 0.5,
            "risk_level": "LOW",
            "reason": "Valid reason.",
        }
        with self.assertRaises(ValidationError):
            RecoveryDecisionOutput(**data_under)

    def test_pydantic_validation_invalid_risk_level_rejected(self):
        """Risk level must be one of LOW, MEDIUM, HIGH."""
        data = {
            "recommended_action": "RETRY",
            "recovery_probability": 0.5,
            "confidence": 0.5,
            "risk_level": "EXTREME",
            "reason": "Valid reason.",
        }
        with self.assertRaises(ValidationError):
            RecoveryDecisionOutput(**data)

    def test_rule_fallback_deterministic(self):
        """Deterministic fallback should produce consistent, compliant structure."""
        fb = compute_rule_fallback(
            amount=5000.0,
            failure_reason="Gateway timeout on card processing",
            payment_method="card",
            customer_type="Regular",
        )
        self.assertIn(fb["recommended_action"], ALLOWED_ACTIONS)
        self.assertIn(fb["risk_level"], ALLOWED_RISK_LEVELS)
        self.assertGreaterEqual(fb["recovery_probability"], 0.0)
        self.assertLessEqual(fb["recovery_probability"], 1.0)
        self.assertLessEqual(fb["expected_recovery"], 5000.0)
        self.assertEqual(fb["decision_source"], SOURCE_FALLBACK)

    @patch("app.services.recovery_ai_service._call_ollama_raw")
    def test_ollama_failure_safely_falls_back(self, mock_ollama):
        """When Ollama fails or raises, the engine falls back without crashing."""
        import asyncio
        mock_ollama.side_effect = Exception("Connection refused by Ollama host")

        loop = asyncio.new_event_loop()
        decision = loop.run_until_complete(
            generate_recovery_decision(
                amount=10000.0,
                failure_reason="Bank network timeout",
                customer_type="Regular",
            )
        )
        loop.close()

        self.assertEqual(decision["decision_source"], SOURCE_FALLBACK)
        self.assertIn(decision["recommended_action"], ALLOWED_ACTIONS)
        self.assertLessEqual(decision["expected_recovery"], 10000.0)

    @patch("app.services.recovery_ai_service._call_ollama_raw")
    def test_ollama_success_with_clamped_expected_recovery(self, mock_ollama):
        """Valid Ollama response is accepted and expected_recovery is clamped if excessive."""
        import asyncio
        mock_ollama.return_value = {
            "recommended_action": "RETRY",
            "recovery_probability": 0.85,
            "confidence": 0.90,
            "expected_recovery": 999999.0,  # exceeds amount
            "risk_level": "LOW",
            "reason": "Temporary network timeout; immediate retry is low risk.",
        }

        loop = asyncio.new_event_loop()
        decision = loop.run_until_complete(
            generate_recovery_decision(
                amount=2000.0,
                failure_reason="timeout",
            )
        )
        loop.close()

        self.assertEqual(decision["decision_source"], SOURCE_OLLAMA)
        self.assertEqual(decision["recommended_action"], "RETRY")
        self.assertEqual(decision["expected_recovery"], 2000.0)  # clamped to amount

    def test_api_analyze_and_get_decision_flow(self):
        """Test POST /api/recovery/analyze/{id} and GET /api/recovery/{id}/decision."""
        # 1. Create a failed payment in the DB
        test_payment = Payment(
            amount=7500.0,
            failure_reason="TEST_RECOVERY_AI",
            customer_type="Regular",
            payment_status="failed",
            recovery_status="PENDING",
        )
        self.db.add(test_payment)
        self.db.commit()
        self.db.refresh(test_payment)
        pid = test_payment.id

        # 2. Call POST /api/recovery/analyze/{pid}
        res_analyze = self.client.post(f"/api/recovery/analyze/{pid}")
        self.assertEqual(res_analyze.status_code, 200)
        data = res_analyze.json()

        self.assertEqual(data["payment_id"], pid)
        self.assertEqual(data["amount"], 7500.0)
        self.assertIn(data["recommended_action"], ALLOWED_ACTIONS)
        self.assertIn(data["risk_level"], ALLOWED_RISK_LEVELS)
        self.assertGreaterEqual(data["recovery_probability"], 0.0)
        self.assertLessEqual(data["recovery_probability"], 1.0)
        self.assertLessEqual(data["expected_recovery"], 7500.0)
        self.assertTrue(len(data["reason"]) > 0)
        self.assertIn("ai_decision_at", data)

        # 3. Verify PostgreSQL persistence
        self.db.expire_all()
        saved_payment = self.db.query(Payment).filter(Payment.id == pid).first()
        self.assertIsNotNone(saved_payment.ai_decision_at)
        self.assertEqual(saved_payment.recommended_action, data["recommended_action"])
        self.assertEqual(saved_payment.risk_level, data["risk_level"])
        self.assertAlmostEqual(saved_payment.recovery_probability, data["recovery_probability"], places=3)
        self.assertAlmostEqual(saved_payment.expected_recovery, data["expected_recovery"], places=2)

        # 4. Call GET /api/recovery/{pid}/decision
        res_get = self.client.get(f"/api/recovery/{pid}/decision")
        self.assertEqual(res_get.status_code, 200)
        get_data = res_get.json()
        self.assertEqual(get_data["payment_id"], pid)
        self.assertEqual(get_data["recommended_action"], data["recommended_action"])
        self.assertEqual(get_data["risk_level"], data["risk_level"])
        self.assertEqual(get_data["decision_source"], data["decision_source"])

    def test_api_analyze_nonexistent_payment_returns_404(self):
        """POST /api/recovery/analyze/999999 returns 404."""
        res = self.client.post("/api/recovery/analyze/999999")
        self.assertEqual(res.status_code, 404)
        self.assertIn("not found", res.json()["detail"].lower())

    def test_api_get_decision_nonexistent_payment_returns_404(self):
        """GET /api/recovery/999999/decision returns 404."""
        res = self.client.get("/api/recovery/999999/decision")
        self.assertEqual(res.status_code, 404)
        self.assertIn("not found", res.json()["detail"].lower())

    def test_api_analyze_already_successful_payment_returns_400(self):
        """POST /api/recovery/analyze/{id} on an already recovered/captured payment returns 400."""
        recovered_payment = Payment(
            amount=3000.0,
            failure_reason="TEST_RECOVERY_AI",
            customer_type="Regular",
            payment_status="captured",
            recovery_status="SUCCESS",
        )
        self.db.add(recovered_payment)
        self.db.commit()
        self.db.refresh(recovered_payment)
        pid = recovered_payment.id

        res = self.client.post(f"/api/recovery/analyze/{pid}")
        self.assertEqual(res.status_code, 400)
        self.assertIn("already", res.json()["detail"].lower())


if __name__ == "__main__":
    unittest.main()

