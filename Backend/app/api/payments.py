import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Payment, RecoveryExecution
from app.services.razorpay_service import (
    RazorpayNotConfigured,
    create_order,
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