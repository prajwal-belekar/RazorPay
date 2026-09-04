from datetime import datetime, timezone
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import razorpay_configured
from app.database import get_db
from app.models import Payment, RecoveryExecution
from app.services.razorpay_service import (
    RazorpayNotConfigured,
    create_order,
    fetch_payments,
    verify_webhook_signature,
)
from app.services.webhook_service import process_razorpay_webhook


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/payments",
    tags=["Payments"],
)


class CreateOrderRequest(BaseModel):
    amount: float = Field(gt=0, description="Amount in Indian Rupees (INR)")


class WebhookResponse(BaseModel):
    status: str
    event: str | None = None


class SyncRazorpayResponse(BaseModel):
    success: bool
    source: str
    fetched: int
    created: int
    updated: int
    skipped: int
    failed: int


@router.get("")
def get_payments(db: Session = Depends(get_db)):
    payments = (
        db.query(Payment)
        .order_by(Payment.id.desc())
        .all()
    )

    return [
        {
            "id": payment.id,
            "amount": payment.amount,
            "currency": getattr(payment, "currency", None) or "INR",
            "failure_reason": payment.failure_reason,
            "customer_type": payment.customer_type,
            "recommended_action": payment.recommended_action,
            "reason": payment.reason,
            "confidence": payment.confidence,
            "decision_source": payment.decision_source,
            "recovery_status": payment.recovery_status,
            "payment_status": payment.payment_status,
            "retry_count": payment.retry_count,
            "previous_recovery_attempts": payment.previous_recovery_attempts,
            "created_at": payment.created_at.isoformat()
            if payment.created_at
            else None,
            "razorpay_payment_id": payment.razorpay_payment_id,
            "razorpay_order_id": payment.razorpay_order_id,
            "payment_method": payment.payment_method,
            "error_code": payment.error_code,
            "gateway": payment.gateway or "razorpay",
            "payment_timestamp": (
                payment.payment_timestamp.isoformat()
                if payment.payment_timestamp
                else None
            ),
            # Action Firewall decision (persisted between AI recommendation
            # and any action execution).
            "firewall_decision": payment.firewall_decision,
            "firewall_reason": payment.firewall_reason,
            "firewall_policy_version": payment.firewall_policy_version,
            "firewall_checks": payment.firewall_checks or [],
            "firewall_evaluated_at": (
                payment.firewall_evaluated_at.isoformat()
                if payment.firewall_evaluated_at
                else None
            ),
            "proof": _payment_proof(payment, db),
        }
        for payment in payments
    ]


def _payment_proof(payment: Payment, db: Session) -> dict | None:
    execution = (
        db.query(RecoveryExecution)
        .filter(
            RecoveryExecution.payment_id == payment.id,
            RecoveryExecution.status == "SUCCESS",
            RecoveryExecution.proof_hash.isnot(None),
        )
        .order_by(RecoveryExecution.id.desc())
        .first()
    )
    if execution is None:
        return None
    return {
        "proof_id": f"execution-{execution.id}",
        "transaction_id": f"Payment #{payment.id}",
        "razorpay_payment_id": payment.razorpay_payment_id,
        "recovery_action": execution.action,
        "recovery_timestamp": execution.completed_at.isoformat() if execution.completed_at else None,
        "recovered_amount": payment.amount,
        "ai_confidence": payment.confidence,
        "policy_version": execution.firewall_policy_version,
        "firewall_decision": execution.firewall_decision,
        "execution_id": execution.id,
        "proof_payload": execution.proof_payload,
        "proof_hash": execution.proof_hash,
        "proof_status": execution.proof_status or "NOT_VERIFIED",
        "tx_hash": execution.chain_tx_hash,
        "block_number": execution.chain_block_number,
        "network": execution.chain_network,
    }


@router.post("/create-order")
def create_payment_order(
    request: CreateOrderRequest,
):
    """Create a Razorpay TEST order for a given INR amount."""
    try:
        order = create_order(amount_in_inr=request.amount)
    except RazorpayNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:  # pragma: no cover - upstream SDK failure
        logger.error("create-order failed: %s", exc)
        raise HTTPException(status_code=502, detail="Razorpay create-order failed.")

    # Never expose the secret key; only return safe order details.
    return {
        "id": order.get("id"),
        "amount": order.get("amount"),
        "currency": order.get("currency"),
        "status": order.get("status"),
    }


@router.post("/webhook", response_model=WebhookResponse)
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Receive and verify a Razorpay webhook.

    Delegates to the unified webhook processor so this endpoint behaves
    identically to ``POST /api/webhooks/razorpay``. Only verified webhooks
    are processed; events are stored, deduplicated, and synchronised onto
    the Payment records (no recovery execution).
    """
    raw_body = await request.body()
    body_text = raw_body.decode("utf-8")

    if not x_razorpay_signature:
        raise HTTPException(status_code=400, detail="Missing webhook signature.")

    try:
        verified = verify_webhook_signature(body_text, x_razorpay_signature)
    except Exception as exc:  # pragma: no cover - config error
        raise HTTPException(status_code=500, detail="Webhook verification unavailable.")

    if not verified:
        raise HTTPException(status_code=400, detail="Invalid webhook signature.")

    try:
        result = await process_razorpay_webhook(body_text, db)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Webhook processing failed: %s", exc)
        db.rollback()
        raise HTTPException(status_code=500, detail="Webhook processing failed.")

    return WebhookResponse(status=result["status"], event=result.get("event"))


@router.post("/sync-razorpay", response_model=SyncRazorpayResponse)
def sync_razorpay_transactions(
    count: int = Query(default=20, ge=1, le=100, description="Number of payments to fetch from Razorpay"),
    db: Session = Depends(get_db),
):
    """Synchronize recent Razorpay TEST-mode payment transactions into PostgreSQL.

    READ-ONLY against Razorpay:
      - Fetches payments from Razorpay TEST mode.
      - Transforms and sanitizes the data.
      - Upserts into the PostgreSQL payments table (by razorpay_payment_id).
      - NEVER creates orders, charges, payment links, captures, retries,
        or customer notifications.
      - NEVER triggers automated AI analysis or recovery executions.
    """
    if not razorpay_configured():
        raise HTTPException(
            status_code=503,
            detail="Razorpay TEST credentials are not configured.",
        )

    try:
        resp = fetch_payments(count=count)
    except RazorpayNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("Razorpay sync fetch failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="Failed to fetch transactions from Razorpay API.",
        )

    items = resp.get("items", []) if isinstance(resp, dict) else (resp if isinstance(resp, list) else [])

    created_count = 0
    updated_count = 0
    skipped_count = 0
    failed_count = 0

    for item in items:
        if not isinstance(item, dict):
            skipped_count += 1
            continue

        pay_id = item.get("id")
        if not pay_id or not str(pay_id).startswith("pay_"):
            skipped_count += 1
            continue

        try:
            amount_paise = item.get("amount")
            amount_inr = (
                round(float(amount_paise) / 100.0, 2)
                if amount_paise is not None
                else 0.0
            )
            currency = item.get("currency") or "INR"
            order_id = item.get("order_id")
            status = item.get("status") or "unknown"
            method = item.get("method")
            error_code = item.get("error_code")
            error_desc = item.get("error_description")
            created_at_epoch = item.get("created_at")

            payment_timestamp = None
            if created_at_epoch is not None:
                try:
                    payment_timestamp = datetime.fromtimestamp(
                        int(created_at_epoch), tz=timezone.utc
                    )
                except (TypeError, ValueError, OSError):
                    payment_timestamp = None

            existing = (
                db.query(Payment)
                .filter(Payment.razorpay_payment_id == pay_id)
                .first()
            )

            if existing:
                existing.amount = amount_inr
                existing.currency = currency
                existing.payment_status = status
                if method:
                    existing.payment_method = method
                if order_id:
                    existing.razorpay_order_id = order_id
                if error_code:
                    existing.error_code = error_code
                if error_desc:
                    existing.failure_reason = error_desc
                if payment_timestamp:
                    existing.payment_timestamp = payment_timestamp
                if not existing.gateway:
                    existing.gateway = "razorpay"

                if status in ("captured", "succeeded", "paid"):
                    existing.recovery_status = "SUCCESS"

                updated_count += 1
            else:
                failure_reason = (
                    error_desc
                    or (f"Payment {status}" if status != "captured" else "None")
                )
                rec_status = (
                    "SUCCESS"
                    if status in ("captured", "succeeded", "paid")
                    else ("AUTHORIZED" if status == "authorized" else "PENDING")
                )

                new_payment = Payment(
                    amount=amount_inr,
                    currency=currency,
                    failure_reason=failure_reason,
                    customer_type="Regular",
                    payment_status=status,
                    payment_method=method,
                    error_code=error_code,
                    gateway="razorpay",
                    razorpay_payment_id=pay_id,
                    razorpay_order_id=order_id,
                    payment_timestamp=payment_timestamp,
                    recovery_status=rec_status,
                    retry_count=0,
                    previous_recovery_attempts=0,
                )
                db.add(new_payment)
                created_count += 1
        except Exception as exc:
            logger.error("Failed to sync payment %s: %s", pay_id, exc)
            failed_count += 1

    try:
        db.commit()
    except Exception as exc:
        logger.error("Database commit failed during sync: %s", exc)
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Database commit failed during transaction sync.",
        )

    return SyncRazorpayResponse(
        success=True,
        source="RAZORPAY_TEST",
        fetched=len(items),
        created=created_count,
        updated=updated_count,
        skipped=skipped_count,
        failed=failed_count,
    )