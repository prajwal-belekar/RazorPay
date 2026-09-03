"""Razorpay TEST-mode service.

Encapsulates all Razorpay API interaction so the SDK logic is not
scattered across route handlers. Uses test credentials exclusively from
environment variables; no secrets are ever exposed through responses.
"""

import logging
import os
from pathlib import Path

import razorpay
from dotenv import load_dotenv

from app.config import (
    RAZORPAY_KEY_ID,
    RAZORPAY_KEY_SECRET,
    RAZORPAY_WEBHOOK_SECRET,
    razorpay_configured,
)

_ENV_FILE = Path(__file__).resolve().parent.parent.parent / "Backend" / ".env"
# Fallback: Backend/.env two levels up (when cwd is project root)
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

logger = logging.getLogger(__name__)


class RazorpayNotConfigured(Exception):
    """Raised when Razorpay TEST credentials are missing/placeholder."""


class RazorpaySignatureError(Exception):
    """Raised when a webhook/payment signature cannot be verified."""


_client = None


def reset_client():
    """Reset cached Razorpay client instance (useful for tests or env reloads)."""
    global _client
    _client = None


def get_client():
    """Return a lazily-initialised Razorpay client (test mode)."""
    global _client
    if _client is not None:
        return _client

    if not razorpay_configured():
        raise RazorpayNotConfigured(
            "Razorpay TEST credentials are not configured. "
            "Set RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET in Backend/.env "
            "with real test keys."
        )

    import os
    key_id = os.getenv("RAZORPAY_KEY_ID", RAZORPAY_KEY_ID)
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", RAZORPAY_KEY_SECRET)

    _client = razorpay.Client(
        auth=(key_id, key_secret)
    )
    return _client


def create_order(amount_in_inr: float, receipt: str | None = None):
    """Create a Razorpay TEST order.

    Args:
        amount_in_inr: amount in Indian Rupees (float).
        receipt: optional merchant receipt string.

    Returns:
        dict: the Razorpay order object.
    """
    client = get_client()

    amount_paise = int(round(amount_in_inr * 100))

    data = {
        "amount": amount_paise,
        "currency": "INR",
        "payment_capture": 1,
    }
    if receipt:
        data["receipt"] = receipt

    return client.order.create(data=data)


def create_payment_link(
    amount_in_inr: float,
    receipt: str | None = None,
    description: str | None = None,
):
    """Create a Razorpay TEST payment link.

    Generates a fresh payment link (a new payment flow) so the customer can
    complete a payment that previously failed. Returns the sanitised,
    public-safe subset of the Razorpay response (id + short_url); raw
    credentials are never returned or stored.

    Args:
        amount_in_inr: amount in Indian Rupees (float).
        receipt: optional merchant receipt string.
        description: optional line-item/note description.

    Returns:
        dict: sanitised payment-link object with ``id`` and ``short_url``.
    """
    client = get_client()

    amount_paise = int(round(amount_in_inr * 100))

    data = {
        "amount": amount_paise,
        "currency": "INR",
        "accept_partial": False,
    }
    if receipt:
        data["reference_id"] = receipt
    if description:
        data["description"] = description

    link = client.payment_link.create(data=data)

    return {
        "id": link.get("id"),
        "short_url": link.get("short_url"),
        "status": link.get("status"),
        "amount": link.get("amount"),
        "currency": link.get("currency"),
        "accept_partial": link.get("accept_partial"),
    }


def fetch_order(order_id: str):
    """Fetch a Razorpay order by id."""
    client = get_client()
    return client.order.fetch(order_id)


def fetch_payment(payment_id: str):
    """Fetch a Razorpay payment by id."""
    client = get_client()
    return client.payment.fetch(payment_id)


def fetch_payments(count: int = 10, skip: int = 0):
    """Fetch a page of Razorpay payments (newest first by default).

    Args:
        count: number of records to return (max 100).
        skip: number of records to skip (pagination offset).

    Returns:
        dict: the Razorpay ``payment.all`` response containing an
        ``items`` list plus paging metadata.
    """
    client = get_client()

    count = max(1, min(int(count), 100))
    skip = max(0, int(skip))

    data = {"count": count}
    if skip:
        data["skip"] = skip

    return client.payment.all(data=data)


def check_payment_status(payment_id: str):
    """Fetch a payment and return a minimal, useful status summary.

    Returns a lightweight dict (not the full SDK object) with the fields
    RecoverAI typically needs to reason about a payment.
    """
    payment = fetch_payment(payment_id)

    return {
        "id": payment.get("id"),
        "amount": payment.get("amount"),
        "status": payment.get("status"),
        "method": payment.get("method"),
        "currency": payment.get("currency"),
        "order_id": payment.get("order_id"),
        "international": payment.get("international"),
        "captured": payment.get("captured"),
        "error_description": payment.get("error_description"),
        "error_code": payment.get("error_code"),
        "created_at": payment.get("created_at"),
    }


def fetch_payment_order_info(payment_id: str):
    """Fetch a payment together with its order for RecoverAI context.

    Combines the payment details and (when available) the linked order
    object so downstream analysis has both in one call.
    """
    payment = fetch_payment(payment_id)

    order = None
    order_id = payment.get("order_id")
    if order_id:
        try:
            order = fetch_order(order_id)
        except Exception as exc:  # pragma: no cover - order may be missing
            logger.warning(
                "Could not fetch order %s for payment %s: %s",
                order_id,
                payment_id,
                exc,
            )

    return {
        "payment": payment,
        "order": order,
    }


def verify_webhook_signature(body: str, signature: str) -> bool:
    """Verify a Razorpay webhook signature using HMAC-SHA256.

    ``body`` must be the exact raw request body string that Razorpay
    signed (the unmodified JSON payload). Uses the webhook secret only;
    does not require the order/payment client credentials.
    """
    load_dotenv(_ENV_FILE, override=True)
    webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", RAZORPAY_WEBHOOK_SECRET)
    if not webhook_secret or webhook_secret in ("xxxxx", "your_webhook_secret", "your_test_webhook_secret", "..."):
        raise RazorpayNotConfigured(
            "RAZORPAY_WEBHOOK_SECRET is not configured. Set RAZORPAY_WEBHOOK_SECRET in Backend/.env."
        )

    try:
        utility = razorpay.Utility()
        return utility.verify_webhook_signature(
            body,
            signature,
            webhook_secret,
        )
    except razorpay.errors.SignatureVerificationError:
        return False
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Webhook signature verification failed: %s", exc)
        return False


def verify_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """Verify a payment-response signature (used for order payments)."""
    try:
        client = get_client()
        return client.utility.verify_payment_signature(
            {
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
            }
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Payment signature verification failed: %s", exc)
        return False
