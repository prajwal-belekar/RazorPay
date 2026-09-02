from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Payment
from app.services.ai_service import analyze_payment_failure


router = APIRouter(prefix="/api/ai", tags=["AI"])


class PaymentAnalysisRequest(BaseModel):
    amount: float
    failure_reason: str
    customer_type: str


class RecoveryRequest(BaseModel):
    payment_id: int
    action: str


@router.post("/analyze")
async def analyze_payment(
    request: PaymentAnalysisRequest,
    db: Session = Depends(get_db),
):
    # Get AI / Rule Engine decision
    result = await analyze_payment_failure(
        amount=request.amount,
        failure_reason=request.failure_reason,
        customer_type=request.customer_type,
    )

    decision = result["decision"]

    # Create payment record
    payment = Payment(
        amount=request.amount,
        failure_reason=request.failure_reason,
        customer_type=request.customer_type,
        recommended_action=decision["recommended_action"],
        reason=decision["reason"],
        confidence=decision["confidence"],
        decision_source=decision.get("source"),
        recovery_status="PENDING",
        retry_count=0,
    )

    # Save to PostgreSQL
    db.add(payment)
    db.commit()
    db.refresh(payment)

    return {
        **result,
        "payment_id": payment.id,
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

    # Execute recovery
    if request.action == "RETRY":
        payment.retry_count += 1
        payment.recovery_status = "SUCCESS"

        db.commit()
        db.refresh(payment)

        return {
            "payment_id": payment.id,
            "action": request.action,
            "status": "SUCCESS",
            "message": (
                f"Payment retry initiated for "
                f"₹{payment.amount:,.2f}."
            ),
        }

    # Other actions can be implemented later
    payment.recovery_status = "SUCCESS"

    db.commit()
    db.refresh(payment)

    return {
        "payment_id": payment.id,
        "action": request.action,
        "status": "SUCCESS",
        "message": f"{request.action} recovery initiated.",
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