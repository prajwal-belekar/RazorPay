from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Payment
from app.services.ai_service import analyze_payment_failure
from app.services.action_executor import execute_recovery_action


router = APIRouter(prefix="/api/ai", tags=["AI"])


class PaymentAnalysisRequest(BaseModel):
    amount: float
    failure_reason: str
    customer_type: str = "Unknown"
    payment_method: str | None = None
    retry_count: int = 0
    previous_recovery_attempts: int = 0
    transaction_age_minutes: int | None = None


class RecoveryRequest(BaseModel):
    payment_id: int
    action: str


@router.post("/analyze")
async def analyze_payment(
    request: PaymentAnalysisRequest,
    db: Session = Depends(get_db),
):
    # Get the real AI decision (Ollama) with deterministic fallback.
    decision = await analyze_payment_failure(
        amount=request.amount,
        failure_reason=request.failure_reason,
        customer_type=request.customer_type,
        payment_method=request.payment_method,
        retry_count=request.retry_count,
        previous_recovery_attempts=request.previous_recovery_attempts,
        transaction_age_minutes=request.transaction_age_minutes,
    )

    # Create payment record with the recommendation (never execute).
    payment = Payment(
        amount=request.amount,
        failure_reason=request.failure_reason,
        customer_type=request.customer_type,
        payment_method=request.payment_method,
        recommended_action=decision["recommended_action"],
        reason=decision["reason"],
        confidence=decision["confidence"],
        decision_source=decision["decision_source"],
        recovery_status="PENDING",
        retry_count=0,
    )

    # Save to PostgreSQL
    db.add(payment)
    db.commit()
    db.refresh(payment)

    return {
        "payment_id": payment.id,
        "model": decision.get("model"),
        "recommended_action": decision["recommended_action"],
        "confidence": decision["confidence"],
        "reason": decision["reason"],
        "recommended_delay_minutes": decision.get("recommended_delay_minutes"),
        "decision_source": decision["decision_source"],
    }


@router.post("/recover")
async def recover_payment(
    request: RecoveryRequest,
    db: Session = Depends(get_db),
):
    # Find the exact payment
    payment = db.query(Payment).filter(
        Payment.id == request.payment_id
    ).first()

    if not payment:
        return {
            "action": request.action,
            "status": "FAILED",
            "message": f"Payment {request.payment_id} not found.",
        }

    # Make sure requested action matches the AI recommendation
    if request.action != payment.recommended_action:
        return {
            "action": request.action,
            "status": "FAILED",
            "message": (
                f"Action {request.action} does not match "
                f"recommended action {payment.recommended_action}."
            ),
        }

    try:
        result = execute_recovery_action(
            payment_id=payment.id,
            action=request.action,
            db=db,
        )
    except ValueError as exc:
        return {"payment_id": payment.id, "action": request.action, "status": "FAILED", "message": str(exc)}

    return {
        "payment_id": payment.id,
        "action": request.action,
        "status": result.get("status", "FAILED"),
        "message": result.get("error") or result.get("outcome", "FAILED"),
        "execution_id": result.get("id"),
    }

@router.get("/payments")
async def get_payments(
    db: Session = Depends(get_db),
):
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
            "retry_count": payment.retry_count,
            "created_at": payment.created_at,
        }
        for payment in payments
    ]