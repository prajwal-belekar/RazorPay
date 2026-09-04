"""Automated tests for Real Razorpay TEST-Mode Transaction Sync in RecoverAI backend."""

import hashlib
import hmac
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import FirewallAuditLog, Payment, RazorpayWebhook, RecoveryExecution
from app.services.razorpay_service import RazorpayNotConfigured, reset_client


TEST_WEBHOOK_SECRET = "whsec_test_secret_key_abcdef123456"


def compute_webhook_signature(body: str, secret: str = TEST_WEBHOOK_SECRET) -> str:
    return hmac.new(
        key=secret.encode("utf-8"),
        msg=body.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


class TestRazorpaySync(unittest.TestCase):
    """Test suite covering all aspects of Razorpay TEST-mode transaction synchronization."""

    def _cleanup_test_data(self):
        db = SessionLocal()
        try:
            pay_ids = [
                p.id
                for p in db.query(Payment.id).filter(
                    Payment.razorpay_payment_id.like("pay_sync_%")
                    | Payment.razorpay_payment_id.like("pay_test_%")
                ).all()
            ]
            if pay_ids:
                db.query(RecoveryExecution).filter(
                    RecoveryExecution.payment_id.in_(pay_ids)
                ).delete(synchronize_session=False)
                db.query(FirewallAuditLog).filter(
                    FirewallAuditLog.payment_id.in_(pay_ids)
                ).delete(synchronize_session=False)

            db.query(RazorpayWebhook).filter(
                RazorpayWebhook.razorpay_payment_id.like("pay_sync_%")
                | RazorpayWebhook.razorpay_payment_id.like("pay_test_%")
            ).delete(synchronize_session=False)

            db.query(Payment).filter(
                Payment.razorpay_payment_id.like("pay_sync_%")
                | Payment.razorpay_payment_id.like("pay_test_%")
            ).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()

    def setUp(self):
        self._cleanup_test_data()
        self.client = TestClient(app)
        self.db = SessionLocal()
        reset_client()

    def tearDown(self):
        self.db.close()
        self._cleanup_test_data()
        reset_client()

    def _sample_razorpay_payments(self):
        return {
            "entity": "collection",
            "count": 2,
            "items": [
                {
                    "id": "pay_sync_test_001",
                    "entity": "payment",
                    "amount": 250000,  # 2500.00 INR
                    "currency": "INR",
                    "status": "failed",
                    "order_id": "order_sync_test_001",
                    "invoice_id": None,
                    "international": False,
                    "method": "upi",
                    "amount_refunded": 0,
                    "refund_status": None,
                    "captured": False,
                    "description": "Test transaction 1",
                    "card_id": None,
                    "bank": None,
                    "wallet": None,
                    "vpa": "customer@upi",
                    "email": "customer@example.com",
                    "contact": "+919999999999",
                    "notes": [],
                    "fee": None,
                    "tax": None,
                    "error_code": "BAD_REQUEST_ERROR",
                    "error_description": "Payment was declined by issuing bank",
                    "error_source": "bank",
                    "error_step": "payment_authorization",
                    "error_reason": "payment_failed",
                    "acquirer_data": {},
                    "created_at": 1725400000,
                },
                {
                    "id": "pay_sync_test_002",
                    "entity": "payment",
                    "amount": 100000,  # 1000.00 INR
                    "currency": "INR",
                    "status": "captured",
                    "order_id": "order_sync_test_002",
                    "method": "card",
                    "error_code": None,
                    "error_description": None,
                    "created_at": 1725403600,
                },
            ],
        }

    @patch("app.api.payments.fetch_payments")
    @patch("app.api.payments.razorpay_configured", return_value=True)
    def test_01_successful_razorpay_payment_fetch(self, mock_configured, mock_fetch):
        mock_fetch.return_value = self._sample_razorpay_payments()

        resp = self.client.post("/api/payments/sync-razorpay?count=10")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["source"], "RAZORPAY_TEST")
        self.assertEqual(data["fetched"], 2)
        self.assertEqual(data["created"], 2)
        self.assertEqual(data["updated"], 0)
        self.assertEqual(data["skipped"], 0)

    @patch("app.api.payments.fetch_payments")
    @patch("app.api.payments.razorpay_configured", return_value=True)
    def test_02_new_payment_inserted(self, mock_configured, mock_fetch):
        mock_fetch.return_value = self._sample_razorpay_payments()

        resp = self.client.post("/api/payments/sync-razorpay")
        self.assertEqual(resp.status_code, 200)

        p1 = self.db.query(Payment).filter(Payment.razorpay_payment_id == "pay_sync_test_001").first()
        self.assertIsNotNone(p1)
        self.assertEqual(p1.razorpay_order_id, "order_sync_test_001")
        self.assertEqual(p1.payment_status, "failed")

    @patch("app.api.payments.fetch_payments")
    @patch("app.api.payments.razorpay_configured", return_value=True)
    def test_03_existing_payment_updated(self, mock_configured, mock_fetch):
        # Pre-seed payment with older status
        pre = Payment(
            amount=500.0,
            failure_reason="Temporary timeout",
            customer_type="Regular",
            payment_status="pending",
            razorpay_payment_id="pay_sync_test_001",
            recovery_status="PENDING",
            retry_count=0,
        )
        self.db.add(pre)
        self.db.commit()

        mock_fetch.return_value = self._sample_razorpay_payments()
        resp = self.client.post("/api/payments/sync-razorpay")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["updated"], 1)
        self.assertEqual(data["created"], 1)

        self.db.expire_all()
        updated = self.db.query(Payment).filter(Payment.razorpay_payment_id == "pay_sync_test_001").first()
        self.assertEqual(updated.amount, 2500.0)
        self.assertEqual(updated.payment_status, "failed")
        self.assertEqual(updated.payment_method, "upi")
        self.assertEqual(updated.error_code, "BAD_REQUEST_ERROR")

    @patch("app.api.payments.fetch_payments")
    @patch("app.api.payments.razorpay_configured", return_value=True)
    def test_04_duplicate_razorpay_payment_does_not_create_duplicate_db_row(self, mock_configured, mock_fetch):
        mock_fetch.return_value = self._sample_razorpay_payments()

        # Call sync twice
        self.client.post("/api/payments/sync-razorpay")
        self.client.post("/api/payments/sync-razorpay")

        rows = self.db.query(Payment).filter(Payment.razorpay_payment_id == "pay_sync_test_001").all()
        self.assertEqual(len(rows), 1)

    @patch("app.api.payments.fetch_payments")
    @patch("app.api.payments.razorpay_configured", return_value=True)
    def test_05_amount_paise_to_inr_conversion(self, mock_configured, mock_fetch):
        mock_fetch.return_value = {
            "entity": "collection",
            "count": 1,
            "items": [
                {
                    "id": "pay_sync_test_001",
                    "amount": 499950,  # 4999.50 INR
                    "currency": "INR",
                    "status": "failed",
                }
            ],
        }
        self.client.post("/api/payments/sync-razorpay")
        p = self.db.query(Payment).filter(Payment.razorpay_payment_id == "pay_sync_test_001").first()
        self.assertEqual(p.amount, 4999.50)

    @patch("app.api.payments.fetch_payments")
    @patch("app.api.payments.razorpay_configured", return_value=True)
    def test_06_payment_status_mapping(self, mock_configured, mock_fetch):
        mock_fetch.return_value = self._sample_razorpay_payments()
        self.client.post("/api/payments/sync-razorpay")

        p1 = self.db.query(Payment).filter(Payment.razorpay_payment_id == "pay_sync_test_001").first()
        p2 = self.db.query(Payment).filter(Payment.razorpay_payment_id == "pay_sync_test_002").first()
        self.assertEqual(p1.payment_status, "failed")
        self.assertEqual(p2.payment_status, "captured")
        self.assertEqual(p2.recovery_status, "SUCCESS")

    @patch("app.api.payments.fetch_payments")
    @patch("app.api.payments.razorpay_configured", return_value=True)
    def test_07_payment_method_mapping(self, mock_configured, mock_fetch):
        mock_fetch.return_value = self._sample_razorpay_payments()
        self.client.post("/api/payments/sync-razorpay")

        p1 = self.db.query(Payment).filter(Payment.razorpay_payment_id == "pay_sync_test_001").first()
        p2 = self.db.query(Payment).filter(Payment.razorpay_payment_id == "pay_sync_test_002").first()
        self.assertEqual(p1.payment_method, "upi")
        self.assertEqual(p2.payment_method, "card")

    @patch("app.api.payments.fetch_payments")
    @patch("app.api.payments.razorpay_configured", return_value=True)
    def test_08_error_code_mapping(self, mock_configured, mock_fetch):
        mock_fetch.return_value = self._sample_razorpay_payments()
        self.client.post("/api/payments/sync-razorpay")

        p1 = self.db.query(Payment).filter(Payment.razorpay_payment_id == "pay_sync_test_001").first()
        self.assertEqual(p1.error_code, "BAD_REQUEST_ERROR")

    @patch("app.api.payments.fetch_payments")
    @patch("app.api.payments.razorpay_configured", return_value=True)
    def test_09_failure_description_mapping(self, mock_configured, mock_fetch):
        mock_fetch.return_value = self._sample_razorpay_payments()
        self.client.post("/api/payments/sync-razorpay")

        p1 = self.db.query(Payment).filter(Payment.razorpay_payment_id == "pay_sync_test_001").first()
        self.assertEqual(p1.failure_reason, "Payment was declined by issuing bank")

    @patch("app.api.payments.fetch_payments")
    @patch("app.api.payments.razorpay_configured", return_value=True)
    def test_10_razorpay_payment_id_persistence(self, mock_configured, mock_fetch):
        mock_fetch.return_value = self._sample_razorpay_payments()
        self.client.post("/api/payments/sync-razorpay")

        p = self.db.query(Payment).filter(Payment.razorpay_payment_id == "pay_sync_test_001").first()
        self.assertEqual(p.razorpay_payment_id, "pay_sync_test_001")

    @patch("app.api.payments.fetch_payments")
    @patch("app.api.payments.razorpay_configured", return_value=True)
    def test_11_razorpay_order_id_persistence(self, mock_configured, mock_fetch):
        mock_fetch.return_value = self._sample_razorpay_payments()
        self.client.post("/api/payments/sync-razorpay")

        p = self.db.query(Payment).filter(Payment.razorpay_payment_id == "pay_sync_test_001").first()
        self.assertEqual(p.razorpay_order_id, "order_sync_test_001")

    @patch("app.api.payments.fetch_payments")
    @patch("app.api.payments.razorpay_configured", return_value=True)
    def test_12_currency_persistence(self, mock_configured, mock_fetch):
        mock_fetch.return_value = self._sample_razorpay_payments()
        self.client.post("/api/payments/sync-razorpay")

        p = self.db.query(Payment).filter(Payment.razorpay_payment_id == "pay_sync_test_001").first()
        self.assertEqual(p.currency, "INR")

    @patch("app.api.payments.fetch_payments")
    @patch("app.api.payments.razorpay_configured", return_value=True)
    def test_13_timestamp_persistence(self, mock_configured, mock_fetch):
        mock_fetch.return_value = self._sample_razorpay_payments()
        self.client.post("/api/payments/sync-razorpay")

        p = self.db.query(Payment).filter(Payment.razorpay_payment_id == "pay_sync_test_001").first()
        expected = datetime.fromtimestamp(1725400000, tz=timezone.utc)
        self.assertEqual(p.payment_timestamp, expected)

    @patch("app.api.payments.fetch_payments")
    @patch("app.api.payments.razorpay_configured", return_value=True)
    def test_14_existing_ai_fields_preserved(self, mock_configured, mock_fetch):
        pre = Payment(
            amount=500.0,
            failure_reason="Old error",
            customer_type="VIP",
            payment_status="failed",
            razorpay_payment_id="pay_sync_test_001",
            recommended_action="PAYMENT_LINK",
            reason="Customer has strong payment history",
            confidence=0.88,
            decision_source="OLLAMA",
            recovery_probability=0.82,
            expected_recovery=410.0,
            risk_level="LOW",
            recovery_status="PENDING",
            retry_count=1,
        )
        self.db.add(pre)
        self.db.commit()

        mock_fetch.return_value = self._sample_razorpay_payments()
        self.client.post("/api/payments/sync-razorpay")

        self.db.expire_all()
        p = self.db.query(Payment).filter(Payment.razorpay_payment_id == "pay_sync_test_001").first()
        self.assertEqual(p.recommended_action, "PAYMENT_LINK")
        self.assertEqual(p.reason, "Customer has strong payment history")
        self.assertEqual(p.confidence, 0.88)
        self.assertEqual(p.decision_source, "OLLAMA")
        self.assertEqual(p.recovery_probability, 0.82)
        self.assertEqual(p.expected_recovery, 410.0)
        self.assertEqual(p.risk_level, "LOW")

    @patch("app.api.payments.fetch_payments")
    @patch("app.api.payments.razorpay_configured", return_value=True)
    def test_15_existing_recovery_fields_preserved(self, mock_configured, mock_fetch):
        pre = Payment(
            amount=500.0,
            failure_reason="Initial failure",
            customer_type="Regular",
            payment_status="failed",
            razorpay_payment_id="pay_sync_test_001",
            recovery_status="PENDING",
            retry_count=1,
            previous_recovery_attempts=1,
        )
        self.db.add(pre)
        self.db.commit()

        mock_fetch.return_value = self._sample_razorpay_payments()
        self.client.post("/api/payments/sync-razorpay")

        self.db.expire_all()
        p = self.db.query(Payment).filter(Payment.razorpay_payment_id == "pay_sync_test_001").first()
        self.assertEqual(p.retry_count, 1)
        self.assertEqual(p.previous_recovery_attempts, 1)

    @patch("app.api.payments.fetch_payments")
    @patch("app.api.payments.razorpay_configured", return_value=True)
    def test_16_existing_firewall_fields_preserved(self, mock_configured, mock_fetch):
        pre = Payment(
            amount=500.0,
            failure_reason="Initial failure",
            customer_type="Regular",
            payment_status="failed",
            razorpay_payment_id="pay_sync_test_001",
            firewall_decision="APPROVED",
            firewall_reason="Policy passed",
            firewall_policy_version="v1.0",
            firewall_approved=True,
            recovery_status="PENDING",
            retry_count=0,
        )
        self.db.add(pre)
        self.db.commit()

        mock_fetch.return_value = self._sample_razorpay_payments()
        self.client.post("/api/payments/sync-razorpay")

        self.db.expire_all()
        p = self.db.query(Payment).filter(Payment.razorpay_payment_id == "pay_sync_test_001").first()
        self.assertEqual(p.firewall_decision, "APPROVED")
        self.assertEqual(p.firewall_reason, "Policy passed")
        self.assertEqual(p.firewall_policy_version, "v1.0")
        self.assertTrue(p.firewall_approved)

    @patch("app.api.payments.fetch_payments")
    @patch("app.api.payments.razorpay_configured", return_value=True)
    @patch("app.services.recovery_orchestrator.process_failed_payment")
    def test_17_sync_does_not_trigger_recovery(self, mock_orchestrator, mock_configured, mock_fetch):
        mock_fetch.return_value = self._sample_razorpay_payments()
        self.client.post("/api/payments/sync-razorpay")

        # Must not call orchestrator or execute recovery
        mock_orchestrator.assert_not_called()
        p = self.db.query(Payment).filter(Payment.razorpay_payment_id == "pay_sync_test_001").first()
        execs = self.db.query(RecoveryExecution).filter(RecoveryExecution.payment_id == p.id).all()
        self.assertEqual(len(execs), 0)

    @patch("app.api.payments.fetch_payments")
    @patch("app.api.payments.razorpay_configured", return_value=True)
    @patch("app.services.razorpay_service.create_order")
    def test_18_sync_does_not_create_razorpay_orders(self, mock_create_order, mock_configured, mock_fetch):
        mock_fetch.return_value = self._sample_razorpay_payments()
        self.client.post("/api/payments/sync-razorpay")
        mock_create_order.assert_not_called()

    @patch("app.api.payments.fetch_payments")
    @patch("app.api.payments.razorpay_configured", return_value=True)
    @patch("app.services.razorpay_service.create_payment_link")
    def test_19_sync_does_not_create_payment_links(self, mock_create_link, mock_configured, mock_fetch):
        mock_fetch.return_value = self._sample_razorpay_payments()
        self.client.post("/api/payments/sync-razorpay")
        mock_create_link.assert_not_called()

    @patch("app.api.payments.fetch_payments")
    @patch("app.api.payments.razorpay_configured", return_value=True)
    @patch("razorpay.Client")
    def test_20_sync_does_not_capture_charge_payments(self, mock_client_cls, mock_configured, mock_fetch):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_fetch.return_value = self._sample_razorpay_payments()

        self.client.post("/api/payments/sync-razorpay")
        mock_client.payment.capture.assert_not_called()

    @patch("app.api.payments.fetch_payments")
    @patch("app.api.payments.razorpay_configured", return_value=True)
    def test_21_secrets_never_appear_in_response(self, mock_configured, mock_fetch):
        mock_fetch.return_value = self._sample_razorpay_payments()
        resp = self.client.post("/api/payments/sync-razorpay")
        sync_text = resp.text

        for secret_name in [
            "RAZORPAY_KEY_SECRET",
            "RAZORPAY_WEBHOOK_SECRET",
            "authorization",
            "signature",
            "card_number",
            "cvv",
        ]:
            self.assertNotIn(secret_name, sync_text)

        # Also verify enriched GET /api/payments
        get_resp = self.client.get("/api/payments")
        get_text = get_resp.text
        for secret_name in [
            "RAZORPAY_KEY_SECRET",
            "RAZORPAY_WEBHOOK_SECRET",
            "authorization",
            "signature",
            "card_number",
            "cvv",
        ]:
            self.assertNotIn(secret_name, get_text)

    @patch("app.api.payments.fetch_payments")
    @patch("app.api.payments.razorpay_configured", return_value=True)
    def test_22_customer_contact_pii_not_returned(self, mock_configured, mock_fetch):
        mock_fetch.return_value = self._sample_razorpay_payments()
        resp = self.client.post("/api/payments/sync-razorpay")
        self.assertNotIn("+919999999999", resp.text)
        self.assertNotIn("customer@example.com", resp.text)

        get_resp = self.client.get("/api/payments")
        self.assertNotIn("+919999999999", get_resp.text)
        self.assertNotIn("customer@example.com", get_resp.text)

    @patch("app.api.payments.fetch_payments")
    @patch("app.api.payments.razorpay_configured", return_value=True)
    def test_23_razorpay_api_failure_handled_safely(self, mock_configured, mock_fetch):
        mock_fetch.side_effect = Exception("Upstream connection reset")
        resp = self.client.post("/api/payments/sync-razorpay")
        self.assertEqual(resp.status_code, 502)
        self.assertIn("Failed to fetch transactions", resp.json()["detail"])

    @patch("app.api.payments.razorpay_configured", return_value=False)
    def test_24_missing_credentials_handled_safely(self, mock_configured):
        resp = self.client.post("/api/payments/sync-razorpay")
        self.assertEqual(resp.status_code, 503)
        self.assertIn("not configured", resp.json()["detail"])

    @patch("app.api.payments.fetch_payments")
    @patch("app.api.payments.razorpay_configured", return_value=True)
    def test_25_webhook_plus_sync_do_not_create_duplicate_payment_rows(self, mock_configured, mock_fetch):
        # 1. Process webhook for pay_sync_test_001
        webhook_payload = json.dumps({
            "entity": "event",
            "account_id": "acc_test",
            "event": "payment.failed",
            "contains": ["payment"],
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_sync_test_001",
                        "amount": 250000,
                        "currency": "INR",
                        "status": "failed",
                        "order_id": "order_sync_test_001",
                        "method": "upi",
                        "error_code": "BAD_REQUEST_ERROR",
                        "error_description": "Declined",
                        "created_at": 1725400000,
                    }
                }
            },
            "created_at": 1725400000,
        })
        sig = compute_webhook_signature(webhook_payload)

        with patch("app.services.razorpay_service.os.getenv", return_value=TEST_WEBHOOK_SECRET):
            webhook_resp = self.client.post(
                "/api/payments/webhook",
                data=webhook_payload,
                headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"},
            )
            self.assertEqual(webhook_resp.status_code, 200)

        # 2. Run sync with the same payment
        mock_fetch.return_value = self._sample_razorpay_payments()
        sync_resp = self.client.post("/api/payments/sync-razorpay")
        self.assertEqual(sync_resp.status_code, 200)

        # 3. Verify exactly 1 Payment row in DB
        rows = self.db.query(Payment).filter(Payment.razorpay_payment_id == "pay_sync_test_001").all()
        self.assertEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
