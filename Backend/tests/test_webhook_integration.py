"""Automated tests for Razorpay Webhook integration in RecoverAI backend."""

import hashlib
import hmac
import json
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import FirewallAuditLog, Payment, RazorpayWebhook, RecoveryExecution
from app.services.razorpay_service import reset_client


TEST_WEBHOOK_SECRET = "whsec_test_secret_key_abcdef123456"


def compute_webhook_signature(body: str, secret: str = TEST_WEBHOOK_SECRET) -> str:
    """Compute HMAC-SHA256 signature according to Razorpay specification."""
    return hmac.new(
        key=secret.encode("utf-8"),
        msg=body.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


class TestRazorpayWebhookIntegration(unittest.TestCase):
    """Test Razorpay Webhook endpoints, signature verification, persistence, and idempotency."""

    def _cleanup_test_data(self):
        db = SessionLocal()
        try:
            pay_ids = db.query(Payment.id).filter(
                Payment.razorpay_payment_id.like("pay_test_%")
            )
            db.query(RecoveryExecution).filter(
                RecoveryExecution.payment_id.in_(pay_ids)
            ).delete(synchronize_session=False)
            db.query(FirewallAuditLog).filter(
                FirewallAuditLog.payment_id.in_(pay_ids)
            ).delete(synchronize_session=False)
            db.query(RazorpayWebhook).filter(
                RazorpayWebhook.razorpay_payment_id.like("pay_test_%")
            ).delete(synchronize_session=False)
            db.query(Payment).filter(
                Payment.razorpay_payment_id.like("pay_test_%")
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

    def test_missing_signature_header_rejected(self):
        """Webhooks missing X-Razorpay-Signature header must be rejected with 400."""
        payload = json.dumps({"event": "payment.failed"})
        response = self.client.post(
            "/api/webhooks/razorpay",
            content=payload,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("missing", response.json()["detail"].lower())

    @patch.dict(os.environ, {"RAZORPAY_WEBHOOK_SECRET": "xxxxx"})
    def test_unconfigured_webhook_secret_returns_503(self):
        """When webhook secret is placeholder or missing, return 503."""
        payload = json.dumps({"event": "payment.failed"})
        response = self.client.post(
            "/api/webhooks/razorpay",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Razorpay-Signature": "dummy_sig_123",
            },
        )
        self.assertEqual(response.status_code, 503)
        self.assertIn("not configured", response.json()["detail"].lower())

    @patch.dict(os.environ, {"RAZORPAY_WEBHOOK_SECRET": TEST_WEBHOOK_SECRET})
    def test_invalid_signature_rejected(self):
        """Webhooks with an invalid signature must be rejected with 400."""
        payload = json.dumps({"event": "payment.failed"})
        response = self.client.post(
            "/api/webhooks/razorpay",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Razorpay-Signature": "invalid_signature_hex_0000",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("invalid", response.json()["detail"].lower())

    @patch.dict(os.environ, {"RAZORPAY_WEBHOOK_SECRET": TEST_WEBHOOK_SECRET})
    def test_payment_failed_event_creates_recovery_candidate(self):
        """payment.failed webhook creates a Payment with status=failed and recovery_status=PENDING."""
        pay_id = "pay_test_fail_9901"
        order_id = "order_test_fail_9901"

        payload_dict = {
            "entity": "event",
            "event": "payment.failed",
            "created_at": 1714100100,
            "payload": {
                "payment": {
                    "entity": {
                        "id": pay_id,
                        "entity": "payment",
                        "amount": 125000,  # 1250.00 INR
                        "currency": "INR",
                        "status": "failed",
                        "order_id": order_id,
                        "method": "upi",
                        "error_code": "BAD_REQUEST_ERROR",
                        "error_description": "Bank system timeout during UPI transfer",
                        "created_at": 1714100100,
                    }
                }
            },
        }
        raw_body = json.dumps(payload_dict)
        signature = compute_webhook_signature(raw_body)

        response = self.client.post(
            "/api/webhooks/razorpay",
            content=raw_body,
            headers={
                "Content-Type": "application/json",
                "X-Razorpay-Signature": signature,
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "PROCESSED")
        self.assertEqual(data["event"], "payment.failed")

        # Verify record in PostgreSQL database
        payment = (
            self.db.query(Payment)
            .filter(Payment.razorpay_payment_id == pay_id)
            .first()
        )
        self.assertIsNotNone(payment)
        self.assertEqual(payment.amount, 1250.00)
        self.assertEqual(payment.payment_status, "failed")
        self.assertEqual(payment.recovery_status, "PENDING")
        self.assertEqual(payment.failure_reason, "Bank system timeout during UPI transfer")
        self.assertEqual(payment.error_code, "BAD_REQUEST_ERROR")
        self.assertEqual(payment.payment_method, "upi")
        self.assertEqual(payment.gateway, "razorpay")

    @patch.dict(os.environ, {"RAZORPAY_WEBHOOK_SECRET": TEST_WEBHOOK_SECRET})
    def test_payment_captured_event_updates_existing_record(self):
        """payment.captured updates an existing failed payment to recovery_status=SUCCESS."""
        pay_id = "pay_test_cap_9902"
        order_id = "order_test_cap_9902"

        # 1. First send payment.failed event
        fail_payload = {
            "entity": "event",
            "event": "payment.failed",
            "created_at": 1714100200,
            "payload": {
                "payment": {
                    "entity": {
                        "id": pay_id,
                        "amount": 250000,  # 2500.00 INR
                        "currency": "INR",
                        "status": "failed",
                        "order_id": order_id,
                        "method": "card",
                        "error_code": "GATEWAY_ERROR",
                        "error_description": "Card gateway timeout",
                        "created_at": 1714100200,
                    }
                }
            },
        }
        raw_fail = json.dumps(fail_payload)
        sig_fail = compute_webhook_signature(raw_fail)
        res_fail = self.client.post(
            "/api/webhooks/razorpay",
            content=raw_fail,
            headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig_fail},
        )
        self.assertEqual(res_fail.status_code, 200)

        initial_count = self.db.query(Payment).count()

        # 2. Now send payment.captured event for the same payment
        captured_payload = {
            "entity": "event",
            "event": "payment.captured",
            "created_at": 1714100260,
            "payload": {
                "payment": {
                    "entity": {
                        "id": pay_id,
                        "amount": 250000,
                        "currency": "INR",
                        "status": "captured",
                        "order_id": order_id,
                        "method": "card",
                        "created_at": 1714100260,
                    }
                }
            },
        }
        raw_cap = json.dumps(captured_payload)
        sig_cap = compute_webhook_signature(raw_cap)
        res_cap = self.client.post(
            "/api/webhooks/razorpay",
            content=raw_cap,
            headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig_cap},
        )
        self.assertEqual(res_cap.status_code, 200)
        self.assertEqual(res_cap.json()["event"], "payment.captured")

        # Verify no duplicate payment row was created
        final_count = self.db.query(Payment).count()
        self.assertEqual(final_count, initial_count)

        # Verify the record status was updated to SUCCESS and captured
        self.db.expire_all()
        payment = (
            self.db.query(Payment)
            .filter(Payment.razorpay_payment_id == pay_id)
            .first()
        )
        self.assertIsNotNone(payment)
        self.assertEqual(payment.payment_status, "captured")
        self.assertEqual(payment.recovery_status, "SUCCESS")

    @patch.dict(os.environ, {"RAZORPAY_WEBHOOK_SECRET": TEST_WEBHOOK_SECRET})
    def test_idempotency_duplicate_webhook_ignored(self):
        """Sending the exact same webhook payload twice returns DUPLICATE with no duplicate rows."""
        pay_id = "pay_test_dedup_9903"
        payload_dict = {
            "entity": "event",
            "event": "payment.failed",
            "created_at": 1714100300,
            "payload": {
                "payment": {
                    "entity": {
                        "id": pay_id,
                        "amount": 50000,
                        "currency": "INR",
                        "status": "failed",
                        "method": "upi",
                        "error_code": "BAD_REQUEST_ERROR",
                        "error_description": "Insufficient funds",
                        "created_at": 1714100300,
                    }
                }
            },
        }
        raw_body = json.dumps(payload_dict)
        signature = compute_webhook_signature(raw_body)

        # First delivery
        res1 = self.client.post(
            "/api/webhooks/razorpay",
            content=raw_body,
            headers={"Content-Type": "application/json", "X-Razorpay-Signature": signature},
        )
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.json()["status"], "PROCESSED")

        payments_count_1 = self.db.query(Payment).count()
        webhook_count_1 = self.db.query(RazorpayWebhook).count()

        # Second delivery of identical webhook
        res2 = self.client.post(
            "/api/webhooks/razorpay",
            content=raw_body,
            headers={"Content-Type": "application/json", "X-Razorpay-Signature": signature},
        )
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.json()["status"], "DUPLICATE")

        payments_count_2 = self.db.query(Payment).count()
        webhook_count_2 = self.db.query(RazorpayWebhook).count()

        # Counts must NOT increase
        self.assertEqual(payments_count_1, payments_count_2)
        self.assertEqual(webhook_count_1, webhook_count_2)

    def test_existing_endpoints_remain_functional(self):
        """GET /health and GET /api/payments must continue working."""
        res_health = self.client.get("/health")
        self.assertEqual(res_health.status_code, 200)
        self.assertEqual(res_health.json()["status"], "healthy")

        res_payments = self.client.get("/api/payments")
        self.assertEqual(res_payments.status_code, 200)
        self.assertIsInstance(res_payments.json(), list)

    @patch.dict(os.environ, {"RAZORPAY_WEBHOOK_SECRET": TEST_WEBHOOK_SECRET})
    def test_webhook_secret_never_leaked(self):
        """Webhook responses must never contain the webhook secret."""
        payload_dict = {
            "entity": "event",
            "event": "payment.failed",
            "created_at": 1714100400,
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_test_leak_check",
                        "amount": 10000,
                        "currency": "INR",
                        "status": "failed",
                        "created_at": 1714100400,
                    }
                }
            },
        }
        raw_body = json.dumps(payload_dict)
        signature = compute_webhook_signature(raw_body)
        response = self.client.post(
            "/api/webhooks/razorpay",
            content=raw_body,
            headers={"Content-Type": "application/json", "X-Razorpay-Signature": signature},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(TEST_WEBHOOK_SECRET, response.text)
        self.assertNotIn("secret", response.text.lower())


if __name__ == "__main__":
    unittest.main()
