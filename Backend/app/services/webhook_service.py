"""Razorpay webhook processing: receive, validate, store, and synchronize.

This module is the single source of truth for handling Razorpay payment
lifecycle webhooks. For every verified event it:

  - deterministically deduplicates (idempotency) via a unique key,
  - stores a safe audit record in ``razorpay_webhooks``,
  - links / updates the existing ``Payment`` record with the latest
    Razorpay status and metadata,
  - NEVER executes recovery automatically. A failed payment is only
    marked as a "recovery candidate"; actual recovery is a later step.

No secrets are ever persisted or logged.
"""

import json
import logging
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Payment, RazorpayWebhook
from app.services.websocket_manager import broadcast_payment_update
from app.database import SessionLocal

logger = logging.getLogger(__name__)

GATEWAY = "razorpay"

# Webhook event types this pipeline understands.
SUPPORTED_EVENTS = {
    "payment.failed",
    "payment.captured",
    "payment.authorized",
    "order.paid",
}

# Payment.recovery_status markers describing lifecycle state only.
RECOVERY_CANDIDATE = "PENDING"       # failed but recoverable (not yet executed)
RECOVERED = "SUCCESS"                # payment captured / order paid
ATTRIBUTED = "AUTHORIZED"            # payment authorized but not yet captured


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _entities(payload: dict):
    """Return the payment and order entities from a webhook payload.

    Razorpay nests entities depending on the event: payment.* uses
    payload.payment.entity, order.* uses payload.order.entity.
    """
    payment_entity = (
        payload.get("payload", {})
        .get("payment", {})
        .get("entity", {})
    ) or {}
    order_entity = (
        payload.get("payload", {})
        .get("order", {})
        .get("entity", {})
    ) or {}
    return payment_entity, order_entity


def _amount_inr(entity: dict):
    """Convert Razorpay paise amount to INR (or None)."""
    amount = entity.get("amount")
    if amount is None:
        return None
    try:
        return float(amount) / 100.0
    except (TypeError, ValueError):
        return None


def _event_timestamp(payload: dict) -> datetime:
    """Razorpay webhooks carry ``created_at`` as epoch seconds."""
    try:
        ts = int(payload.get("created_at"))
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return _now()


def _dedup_key(payload: dict, payment_entity: dict, order_entity: dict) -> str:
    """Deterministic idempotency key for one logical Razorpay event."""
    event = str(payload.get("event", "unknown"))
    created_at = payload.get("created_at", "no-ts")
    payment_id = payment_entity.get("id")
    order_id = payment_entity.get("order_id") or order_entity.get("id")

    if payment_id:
        return f"{event}:payment:{payment_id}:{created_at}"
    if order_id:
        return f"{event}:order:{order_id}:{created_at}"
    return f"{event}:noid:{created_at}"


def _sanitize_payload(payload: dict) -> dict:
    """Return a payload copy with any sensitive fields removed.

    Webhook payloads contain payment/order data, not credentials; this is
    a defensive sweep to guarantee nothing secret-like is stored.
    """
    sensitive_keys = {
        "key", "secret", "token", "password", "authorization",
        "x_razorpay_signature", "signature",
    }
    if not isinstance(payload, dict):
        return payload

    out = {}
    for key, value in payload.items():
        if key.lower() in sensitive_keys:
            continue
        if isinstance(value, dict):
            out[key] = _sanitize_payload(value)
        elif isinstance(value, list):
            out[key] = [
                _sanitize_payload(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            out[key] = value
    return out


def _extract_failure_reason(payment_entity: dict) -> str:
    return (
        payment_entity.get("error_description")
        or payment_entity.get("failure_reason")
        or "Payment failed"
    )


def _payment_timestamp(payment_entity: dict) -> datetime | None:
    """Razorpay payments carry ``created_at`` as epoch seconds."""
    try:
        ts = int(payment_entity.get("created_at"))
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _resolve_payment(
    db: Session,
    payment_entity: dict,
    order_entity: dict,
) -> Payment | None:
    """Return the linked Payment record, creating one if we can identify it."""
    payment_id = payment_entity.get("id")
    order_id = payment_entity.get("order_id") or order_entity.get("id")

    if not payment_id and not order_id:
        return None

    payment = None
    if payment_id:
        payment = (
            db.query(Payment)
            .filter(Payment.razorpay_payment_id == payment_id)
            .first()
        )
    if payment is None and order_id:
        payment = (
            db.query(Payment)
            .filter(Payment.razorpay_order_id == order_id)
            .first()
        )

    if payment is None:
        payment = Payment(
            amount=0.0,
            failure_reason="Unknown",
            customer_type="Unknown",
            gateway=GATEWAY,
            razorpay_payment_id=payment_id,
            razorpay_order_id=order_id,
            webhook_received_at=_now(),
        )
        db.add(payment)
        db.flush()

    return payment


async def _sync_payment(
    payment: Payment,
    payment_entity: dict,
    order_entity: dict,
    event: str,
):
    """Update a Payment record from a Razorpay webhook entity.

    Synchronises lifecycle state and failure metadata without triggering
    recovery actions or AI execution.
    """
    payment.gateway = GATEWAY
    payment.razorpay_payment_id = payment.razorpay_payment_id or payment_entity.get("id")
    payment.razorpay_order_id = payment.razorpay_order_id or (
        payment_entity.get("order_id") or order_entity.get("id")
    )
    payment.webhook_received_at = _now()

    amount = _amount_inr(payment_entity) or _amount_inr(order_entity)
    if amount is not None:
        payment.amount = amount

    raz_status = payment_entity.get("status") or order_entity.get("status")

    if event == "payment.failed":
        payment.payment_status = raz_status or "failed"
        payment.failure_reason = _extract_failure_reason(payment_entity)
        payment.error_code = payment_entity.get("error_code")
        if not payment.customer_type or payment.customer_type == "Unknown":
            payment.customer_type = "Regular"
        payment.payment_method = payment_entity.get("method") or payment.payment_method
        payment.payment_timestamp = (
            _payment_timestamp(payment_entity) or payment.payment_timestamp
        )
        payment.recovery_status = RECOVERY_CANDIDATE

    elif event in ("payment.captured", "order.paid"):
        payment.payment_status = raz_status or "captured"
        payment.recovery_status = RECOVERED

    elif event == "payment.authorized":
        payment.payment_status = raz_status or "authorized"
        payment.recovery_status = ATTRIBUTED


async def process_razorpay_webhook(raw_body: str, db: Session) -> dict:
    """Process a verified Razorpay webhook body.

    Idempotent: re-delivery of the same event returns DUPLICATE without
    creating duplicate records or re-synchronising the Payment.
    """
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON webhook body: {exc}")

    event = payload.get("event", "")
    logger.info("Razorpay webhook received: %s", event)
    payment_entity, order_entity = _entities(payload)

    dedup_key = _dedup_key(payload, payment_entity, order_entity)

    # Idempotency guard: ignore events we have already processed.
    existing = (
        db.query(RazorpayWebhook)
        .filter(RazorpayWebhook.dedup_key == dedup_key)
        .first()
    )
    if existing:
        logger.info("Duplicate Razorpay webhook ignored (dedup_key=%s)", dedup_key)
        return {
            "event": event,
            "status": "DUPLICATE",
            "processed": existing.processed,
        }

    event_obj = RazorpayWebhook(
        dedup_key=dedup_key,
        event_type=event,
        razorpay_payment_id=payment_entity.get("id"),
        razorpay_order_id=payment_entity.get("order_id")
        or order_entity.get("id"),
        amount=_amount_inr(payment_entity) or _amount_inr(order_entity),
        currency=payment_entity.get("currency") or order_entity.get("currency"),
        payment_status=payment_entity.get("status") or order_entity.get("status"),
        method=payment_entity.get("method"),
        failure_reason=_extract_failure_reason(payment_entity)
        if event == "payment.failed"
        else None,
        event_timestamp=_event_timestamp(payload),
        payload=json.dumps(_sanitize_payload(payload)),
    )
    db.add(event_obj)

    if event not in SUPPORTED_EVENTS:
        logger.info("Unsolicited webhook event ignored: %s", event)
        # Persist the audit record so we have a trace, but flag unprocessed.
        event_obj.processed = False
        db.commit()
        return {"event": event, "status": "IGNORED", "processed": False}

    try:
        payment = _resolve_payment(db, payment_entity, order_entity)
        if payment is not None:
            await _sync_payment(payment, payment_entity, order_entity, event)

        # Link the audit row to the payment-facing ids.
        event_obj.processed = True
        db.commit()

        result = {
            "event": event,
            "status": "PROCESSED",
            "processed": True,
            "payment_id": payment.id if payment is not None else None,
        }
    except IntegrityError:
        # Another concurrent delivery won the race - treat as duplicate.
        db.rollback()
        logger.info("Concurrent duplicate Razorpay webhook ignored: %s", dedup_key)
        return {"event": event, "status": "DUPLICATE", "processed": True}
    except Exception:
        db.rollback()
        logger.exception("Razorpay webhook processing failed (dedup_key=%s)", dedup_key)
        raise
    finally:
        # Broadcast update to connected WebSocket clients
        try:
            await broadcast_payment_update(SessionLocal)
        except Exception as e:
            logger.warning(f"Failed to broadcast WebSocket update: {e}")

    return result
