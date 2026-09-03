"""Automated tests for Razorpay integration in RecoverAI backend."""

import os
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
import razorpay.errors

from app.config import get_razorpay_public_config, razorpay_configured
from app.main import app
from app.services.razorpay_service import (
    RazorpayNotConfigured,
    get_client,
    reset_client,
)


class TestRazorpayConfiguration(unittest.TestCase):
    """Test Razorpay configuration detection and public exposure safeguards."""

    def tearDown(self):
        reset_client()

    @patch.dict(os.environ, {"RAZORPAY_KEY_ID": "rzp_test_xxxxx", "RAZORPAY_KEY_SECRET": "xxxxx"})
    def test_unconfigured_with_placeholder_credentials(self):
        reset_client()
        self.assertFalse(razorpay_configured())
        with self.assertRaises(RazorpayNotConfigured):
            get_client()

    @patch.dict(os.environ, {"RAZORPAY_KEY_ID": "", "RAZORPAY_KEY_SECRET": ""})
    def test_unconfigured_with_empty_credentials(self):
        reset_client()
        self.assertFalse(razorpay_configured())
        with self.assertRaises(RazorpayNotConfigured):
            get_client()

    @patch.dict(
        os.environ,
        {
            "RAZORPAY_KEY_ID": "rzp_test_1234567890abcdef",
            "RAZORPAY_KEY_SECRET": "topsecretkey9876543210",
        },
    )
    def test_configured_with_valid_credentials(self):
        reset_client()
        self.assertTrue(razorpay_configured())
        config = get_razorpay_public_config()
        self.assertTrue(config["configured"])
        self.assertEqual(config["mode"], "test")
        # Preview must mask the key and never contain the secret
        self.assertIn("rzp_test", config["key_id_preview"])
        self.assertNotIn("topsecretkey9876543210", str(config))
        self.assertNotIn("secret", str(config).lower())


class TestRazorpayEndpoints(unittest.TestCase):
    """Test FastAPI Razorpay endpoints with TestClient."""

    def setUp(self):
        self.client = TestClient(app)
        reset_client()

    def tearDown(self):
        reset_client()

    def test_health_endpoint_remains_functional(self):
        """GET /health must return 200 healthy."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertEqual(data.get("service"), "recoverai-backend")

    def test_existing_payments_endpoint_unaffected(self):
        """GET /api/payments must continue to return 200 with existing DB payments."""
        response = self.client.get("/api/payments")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_config_endpoint_safe(self):
        """GET /api/razorpay/config returns status without leaking secrets."""
        response = self.client.get("/api/razorpay/config")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("configured", data)
        self.assertIn("mode", data)
        # Secret key must NEVER appear in body
        self.assertNotIn("secret", response.text.lower())

    @patch.dict(os.environ, {"RAZORPAY_KEY_ID": "rzp_test_xxxxx", "RAZORPAY_KEY_SECRET": "xxxxx"})
    def test_endpoints_return_503_when_unconfigured(self):
        """When credentials are placeholders, endpoints must return 503."""
        reset_client()

        res = self.client.get("/api/razorpay/payments")
        self.assertEqual(res.status_code, 503)
        self.assertIn("not configured", res.json()["detail"].lower())

        res = self.client.get("/api/razorpay/payments/pay_sample123")
        self.assertEqual(res.status_code, 503)

        res = self.client.get("/api/razorpay/payments/pay_sample123/order")
        self.assertEqual(res.status_code, 503)

        res = self.client.get("/api/razorpay/orders/order_sample123")
        self.assertEqual(res.status_code, 503)

        res = self.client.post("/api/razorpay/orders", json={"amount": 100.0})
        self.assertEqual(res.status_code, 503)

    @patch.dict(
        os.environ,
        {
            "RAZORPAY_KEY_ID": "rzp_test_1234567890abcdef",
            "RAZORPAY_KEY_SECRET": "topsecretkey9876543210",
        },
    )
    @patch("app.services.razorpay_service.razorpay.Client")
    def test_list_payments_mocked(self, mock_client_cls):
        """GET /api/razorpay/payments returns payment list when configured."""
        reset_client()
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        mock_instance.payment.all.return_value = {
            "count": 2,
            "items": [
                {"id": "pay_001", "amount": 150000, "status": "captured", "currency": "INR"},
                {"id": "pay_002", "amount": 80000, "status": "failed", "currency": "INR"},
            ],
        }

        response = self.client.get("/api/razorpay/payments?count=2")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 2)
        self.assertEqual(len(data["items"]), 2)
        self.assertEqual(data["items"][0]["id"], "pay_001")
        # Ensure secret is not in output
        self.assertNotIn("topsecretkey9876543210", response.text)

    @patch.dict(
        os.environ,
        {
            "RAZORPAY_KEY_ID": "rzp_test_1234567890abcdef",
            "RAZORPAY_KEY_SECRET": "topsecretkey9876543210",
        },
    )
    @patch("app.services.razorpay_service.razorpay.Client")
    def test_get_single_payment_mocked(self, mock_client_cls):
        """GET /api/razorpay/payments/{id} returns sanitized payment details."""
        reset_client()
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        mock_instance.payment.fetch.return_value = {
            "id": "pay_001",
            "amount": 150000,
            "status": "captured",
            "method": "upi",
            "currency": "INR",
            "order_id": "order_999",
            "captured": True,
            "created_at": 1714000000,
        }

        response = self.client.get("/api/razorpay/payments/pay_001")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], "pay_001")
        self.assertEqual(data["status"], "captured")
        self.assertEqual(data["method"], "upi")
        self.assertNotIn("topsecretkey9876543210", response.text)

    @patch.dict(
        os.environ,
        {
            "RAZORPAY_KEY_ID": "rzp_test_1234567890abcdef",
            "RAZORPAY_KEY_SECRET": "topsecretkey9876543210",
        },
    )
    @patch("app.services.razorpay_service.razorpay.Client")
    def test_get_order_mocked(self, mock_client_cls):
        """GET /api/razorpay/orders/{id} returns order details."""
        reset_client()
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        mock_instance.order.fetch.return_value = {
            "id": "order_999",
            "entity": "order",
            "amount": 150000,
            "amount_paid": 150000,
            "amount_due": 0,
            "currency": "INR",
            "receipt": "rcpt_100",
            "status": "paid",
            "attempts": 1,
            "created_at": 1714000000,
        }

        response = self.client.get("/api/razorpay/orders/order_999")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], "order_999")
        self.assertEqual(data["status"], "paid")
        self.assertEqual(data["receipt"], "rcpt_100")

    @patch.dict(
        os.environ,
        {
            "RAZORPAY_KEY_ID": "rzp_test_1234567890abcdef",
            "RAZORPAY_KEY_SECRET": "topsecretkey9876543210",
        },
    )
    @patch("app.services.razorpay_service.razorpay.Client")
    def test_create_order_mocked(self, mock_client_cls):
        """POST /api/razorpay/orders safely creates order in test mode."""
        reset_client()
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        mock_instance.order.create.return_value = {
            "id": "order_new123",
            "amount": 50000,
            "currency": "INR",
            "status": "created",
            "receipt": "rcpt_demo",
            "created_at": 1714000000,
        }

        response = self.client.post(
            "/api/razorpay/orders",
            json={"amount": 500.00, "receipt": "rcpt_demo"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], "order_new123")
        self.assertEqual(data["amount"], 50000)
        self.assertEqual(data["status"], "created")
        # Verify paise conversion
        mock_instance.order.create.assert_called_once_with(
            data={"amount": 50000, "currency": "INR", "payment_capture": 1, "receipt": "rcpt_demo"}
        )

    @patch.dict(
        os.environ,
        {
            "RAZORPAY_KEY_ID": "rzp_test_1234567890abcdef",
            "RAZORPAY_KEY_SECRET": "topsecretkey9876543210",
        },
    )
    @patch("app.services.razorpay_service.razorpay.Client")
    def test_bad_request_error_mapping(self, mock_client_cls):
        """Razorpay BadRequestError maps to HTTP 400."""
        reset_client()
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        mock_instance.payment.fetch.side_effect = razorpay.errors.BadRequestError(
            "The id provided does not exist"
        )

        response = self.client.get("/api/razorpay/payments/pay_nonexistent")
        self.assertEqual(response.status_code, 400)
        self.assertIn("does not exist", response.json()["detail"])

    @patch.dict(
        os.environ,
        {
            "RAZORPAY_KEY_ID": "rzp_test_1234567890abcdef",
            "RAZORPAY_KEY_SECRET": "topsecretkey9876543210",
        },
    )
    @patch("app.services.razorpay_service.razorpay.Client")
    def test_gateway_error_mapping(self, mock_client_cls):
        """Razorpay GatewayError maps to HTTP 504."""
        reset_client()
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        mock_instance.payment.all.side_effect = razorpay.errors.GatewayError("Gateway timeout")

        response = self.client.get("/api/razorpay/payments")
        self.assertEqual(response.status_code, 504)

    @patch.dict(
        os.environ,
        {
            "RAZORPAY_KEY_ID": "rzp_test_1234567890abcdef",
            "RAZORPAY_KEY_SECRET": "topsecretkey9876543210",
        },
    )
    @patch("app.services.razorpay_service.razorpay.Client")
    def test_server_error_mapping(self, mock_client_cls):
        """Razorpay ServerError maps to HTTP 502."""
        reset_client()
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        mock_instance.payment.all.side_effect = razorpay.errors.ServerError("Upstream failure")

        response = self.client.get("/api/razorpay/payments")
        self.assertEqual(response.status_code, 502)


if __name__ == "__main__":
    unittest.main()

