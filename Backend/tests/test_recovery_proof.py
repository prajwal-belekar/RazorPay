import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Payment, RecoveryExecution
from app.services import action_executor
from app.services.recovery_proof import verify_proof


class RecoveryProofTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()
        self.payment = Payment(
            amount=18500,
            failure_reason="Bank Timeout",
            customer_type="Returning",
            confidence=0.93,
            razorpay_payment_id="pay_test_123",
        )
        self.session.add(self.payment)
        self.session.flush()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def _execution(self, status="EXECUTING"):
        execution = RecoveryExecution(
            payment_id=self.payment.id,
            action="RETRY",
            status=status,
            firewall_decision="APPROVED",
            firewall_policy_version="v1",
            idempotency_key=f"test:{self.payment.id}:{status}",
            completed_at=datetime.now(timezone.utc),
        )
        self.session.add(execution)
        self.session.flush()
        return execution

    def test_success_generates_locally_verifiable_proof(self):
        execution = self._execution()

        action_executor._record_provider_success(
            self.session,
            execution,
            self.payment,
            {"id": "order_test_123", "amount": 1850000, "currency": "INR"},
        )

        self.assertEqual(execution.status, action_executor.SUCCESS)
        self.assertEqual(execution.proof_status, "NOT_VERIFIED")
        self.assertTrue(execution.proof_hash.startswith("sha256:"))
        self.assertTrue(verify_proof(execution.proof_payload, execution.proof_hash))
        self.assertEqual(execution.proof_payload["execution_id"], execution.id)
        self.assertEqual(execution.proof_payload["razorpay_payment_id"], "pay_test_123")

    def test_failed_recovery_has_no_proof(self):
        execution = self._execution()

        action_executor._fail(
            self.session,
            self.payment,
            execution,
            RuntimeError("provider unavailable"),
        )

        self.assertEqual(execution.status, action_executor.FAILED)
        self.assertIsNone(execution.proof_payload)
        self.assertIsNone(execution.proof_hash)
        self.assertIsNone(execution.proof_status)

    def test_tampered_proof_does_not_verify(self):
        execution = self._execution()
        action_executor._record_provider_success(
            self.session,
            execution,
            self.payment,
            {"id": "order_test_123"},
        )

        tampered = dict(execution.proof_payload)
        tampered["recovered_amount"] = 1
        self.assertFalse(verify_proof(tampered, execution.proof_hash))


if __name__ == "__main__":
    unittest.main()