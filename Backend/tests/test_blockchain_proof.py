"""Automated tests for RecoverAI Blockchain Proof Layer.

Tests the Polygon Amoy proof submission and retrieval endpoints, covering:
  - Proof submission when blockchain is not configured (NOT_SUBMITTED)
  - Idempotent re-submission (already on chain)
  - Blockchain failure does not corrupt PostgreSQL (FAILED status stored)
  - Proof retrieval when no execution exists (404)
  - Proof retrieval returns local + on-chain verification
  - Deterministic proof hash (build_proof_payload + hash_proof)
  - Private key never exposed in responses
"""

import unittest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Payment, RecoveryExecution
from app.services.recovery_execution_service import (
    DRY_RUN,
    SIMULATED,
)
from app.services.recovery_proof import build_proof_payload, hash_proof, verify_proof


class TestBlockchainProofLayer(unittest.TestCase):
    """Test the Blockchain Proof Layer (Polygon Amoy integration)."""

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()

    def tearDown(self):
        # Clean up test data
        self.db.query(RecoveryExecution).filter(
            RecoveryExecution.payment_id.in_(
                self.db.query(Payment.id).filter(
                    Payment.failure_reason == "TEST_PROOF"
                )
            )
        ).delete(synchronize_session=False)
        self.db.query(Payment).filter(
            Payment.failure_reason == "TEST_PROOF"
        ).delete(synchronize_session=False)
        self.db.commit()
        self.db.close()

    def _create_payment_with_execution(self) -> tuple[Payment, RecoveryExecution]:
        """Helper: create a failed payment and a successful execution with proof."""
        payment = Payment(
            amount=10000.0,
            failure_reason="TEST_PROOF",
            customer_type="Regular",
            payment_status="failed",
            recovery_status="PENDING",
            recommended_action="RETRY",
            confidence=0.9,
            recovery_probability=0.8,
            expected_recovery=8000.0,
            risk_level="LOW",
            retry_count=0,
            previous_recovery_attempts=0,
            razorpay_payment_id="pay_test_blockchain_123",
        )
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)

        from datetime import datetime, timezone
        execution = RecoveryExecution(
            payment_id=payment.id,
            action="RETRY",
            status=SIMULATED,
            idempotency_key=f"proof-test:{payment.id}:RETRY",
            firewall_decision="APPROVED",
            firewall_reason="Test firewall approval",
            firewall_policy_version="v1.0",
            execution_mode=DRY_RUN,
            simulated=True,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)

        # Generate a proof hash deterministically and store it
        payload = build_proof_payload(
            transaction_id=f"Payment #{payment.id}",
            razorpay_payment_id=payment.razorpay_payment_id,
            action=execution.action,
            recovery_timestamp=execution.completed_at,
            recovered_amount=payment.amount,
            ai_confidence=payment.confidence,
            policy_version=execution.firewall_policy_version,
            firewall_decision=execution.firewall_decision,
            execution_id=execution.id,
        )
        proof_hash = hash_proof(payload)
        execution.proof_payload = payload
        execution.proof_hash = proof_hash
        self.db.commit()
        self.db.refresh(execution)

        return payment, execution

    # ------------------------------------------------------------------
    # 1. Proof submission when blockchain is NOT configured
    # ------------------------------------------------------------------
    def test_1_submit_proof_not_configured(self):
        payment, execution = self._create_payment_with_execution()
        with patch(
            "app.api.recovery.blockchain_service.submit_proof",
            return_value={
                "submitted": False,
                "status": "NOT_SUBMITTED",
                "reason": "Blockchain not configured. Proof stored locally only.",
                "chain_network": None,
                "chain_tx_hash": None,
                "chain_block_number": None,
            },
        ):
            res = self.client.post(f"/api/recovery/proof/{payment.id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["payment_id"], payment.id)
        self.assertEqual(data["execution_id"], execution.id)
        self.assertEqual(data["proof_status"], "NOT_SUBMITTED")
        self.assertIsNotNone(data["proof_hash"])
        self.assertTrue(data["proof_hash"].startswith("sha256:"))

        # Verify the execution row was not corrupted
        self.db.expire_all()
        db_exec = self.db.query(RecoveryExecution).filter(
            RecoveryExecution.id == execution.id
        ).first()
        self.assertEqual(db_exec.proof_status, "NOT_SUBMITTED")
        self.assertIsNone(db_exec.chain_tx_hash)
        self.assertIsNotNone(db_exec.proof_payload)

    # ------------------------------------------------------------------
    # 2. Idempotent re-submission when ON_CHAIN
    # ------------------------------------------------------------------
    def test_2_submit_proof_idempotent(self):
        payment, execution = self._create_payment_with_execution()
        execution.proof_status = "ON_CHAIN"
        execution.chain_tx_hash = "0x" + "ab" * 32
        execution.chain_block_number = 123456
        self.db.commit()

        res = self.client.post(f"/api/recovery/proof/{payment.id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["already_submitted"])
        self.assertEqual(data["proof_status"], "ON_CHAIN")
        self.assertEqual(data["chain_tx_hash"], "0x" + "ab" * 32)

    # ------------------------------------------------------------------
    # 3. Blockchain failure does NOT corrupt PostgreSQL
    # ------------------------------------------------------------------
    def test_3_blockchain_failure_stores_failed_status(self):
        payment, execution = self._create_payment_with_execution()
        with patch(
            "app.api.recovery.blockchain_service.submit_proof",
            return_value={
                "submitted": False,
                "status": "SUBMISSION_FAILED",
                "reason": "Blockchain transaction failed: TimeoutError",
                "chain_network": "polygon-amoy (80002)",
                "chain_tx_hash": None,
                "chain_block_number": None,
            },
        ):
            res = self.client.post(f"/api/recovery/proof/{payment.id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["proof_status"], "SUBMISSION_FAILED")
        self.assertIn("blockchain_result", data)
        self.assertFalse(data["blockchain_result"]["submitted"])

        # PostgreSQL row must still be intact and marked FAILED safely
        self.db.expire_all()
        db_exec = self.db.query(RecoveryExecution).filter(
            RecoveryExecution.id == execution.id
        ).first()
        self.assertEqual(db_exec.proof_status, "SUBMISSION_FAILED")
        self.assertIsNotNone(db_exec.proof_hash)
        self.assertIsNotNone(db_exec.proof_payload)

    # ------------------------------------------------------------------
    # 4. Proof submission when no execution exists -> 404
    # ------------------------------------------------------------------
    def test_4_submit_proof_no_execution_404(self):
        payment = Payment(
            amount=10000.0,
            failure_reason="TEST_PROOF",
            customer_type="Regular",
            payment_status="failed",
            recovery_status="PENDING",
        )
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        res = self.client.post(f"/api/recovery/proof/{payment.id}")
        self.assertEqual(res.status_code, 404)
        self.assertIn("no recovery execution", res.json()["detail"].lower())

    # ------------------------------------------------------------------
    # 5. Proof submission for non-existent payment -> 404
    # ------------------------------------------------------------------
    def test_5_submit_proof_payment_not_found_404(self):
        res = self.client.post("/api/recovery/proof/999999")
        self.assertEqual(res.status_code, 404)
        self.assertIn("not found", res.json()["detail"].lower())

    # ------------------------------------------------------------------
    # 6. GET proof returns local + on-chain verification
    # ------------------------------------------------------------------
    def test_6_get_proof_returns_verification(self):
        payment, execution = self._create_payment_with_execution()
        with patch(
            "app.api.recovery.blockchain_service._configured",
            True,
        ), patch(
            "app.api.recovery.blockchain_service.verify_proof_on_chain",
            return_value={
                "verified": True,
                "status": "VERIFIED",
                "on_chain_hash": "0x" + "cd" * 32,
                "expected_hash": "0x" + "cd" * 32,
                "chain_network": "polygon-amoy (80002)",
            },
        ):
            res = self.client.get(f"/api/recovery/proof/{payment.id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["payment_id"], payment.id)
        self.assertTrue(data["local_verified"])
        self.assertIsNotNone(data["proof_hash"])
        self.assertIsNotNone(data["on_chain_verification"])
        self.assertTrue(data["on_chain_verification"]["verified"])
        self.assertEqual(data["on_chain_verification"]["status"], "VERIFIED")

    # ------------------------------------------------------------------
    # 7. GET proof for payment with no proof -> 404
    # ------------------------------------------------------------------
    def test_7_get_proof_no_proof_404(self):
        payment = Payment(
            amount=10000.0,
            failure_reason="TEST_PROOF",
            customer_type="Regular",
            payment_status="failed",
            recovery_status="PENDING",
        )
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        res = self.client.get(f"/api/recovery/proof/{payment.id}")
        self.assertEqual(res.status_code, 404)
        self.assertIn("no recovery proof", res.json()["detail"].lower())

    # ------------------------------------------------------------------
    # 8. GET proof for non-existent payment -> 404
    # ------------------------------------------------------------------
    def test_8_get_proof_payment_not_found_404(self):
        res = self.client.get("/api/recovery/proof/999999")
        self.assertEqual(res.status_code, 404)
        self.assertIn("not found", res.json()["detail"].lower())

    # ------------------------------------------------------------------
    # 9. Proof hash is deterministic and verifiable
    # ------------------------------------------------------------------
    def test_9_proof_hash_deterministic(self):
        payment, execution = self._create_payment_with_execution()
        payload = build_proof_payload(
            transaction_id=f"Payment #{payment.id}",
            razorpay_payment_id=payment.razorpay_payment_id,
            action=execution.action,
            recovery_timestamp=execution.completed_at,
            recovered_amount=payment.amount,
            ai_confidence=payment.confidence,
            policy_version=execution.firewall_policy_version,
            firewall_decision=execution.firewall_decision,
            execution_id=execution.id,
        )
        h1 = hash_proof(payload)
        h2 = hash_proof(payload)
        self.assertEqual(h1, h2)
        self.assertTrue(verify_proof(payload, h1))
        self.assertFalse(verify_proof(payload, "sha256:" + "0" * 64))

    # ------------------------------------------------------------------
    # 10. Private key is never exposed in any response
    # ------------------------------------------------------------------
    def test_10_private_key_never_exposed(self):
        payment, execution = self._create_payment_with_execution()
        with patch(
            "app.api.recovery.blockchain_service.submit_proof",
            return_value={
                "submitted": False,
                "status": "NOT_SUBMITTED",
                "reason": "Blockchain not configured.",
                "chain_network": None,
                "chain_tx_hash": None,
                "chain_block_number": None,
            },
        ):
            res = self.client.post(f"/api/recovery/proof/{payment.id}")
        body = res.text
        self.assertNotIn("BLOCKCHAIN_PRIVATE_KEY", body)
        self.assertNotIn("private_key", body.lower())
        self.assertNotIn("0x" + "a" * 64, body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
