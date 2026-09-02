from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Payment


router = APIRouter(
    prefix="/api/payments",
    tags=["Payments"],
)


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
            "retry_count": payment.retry_count,
            "created_at": payment.created_at.isoformat()
            if payment.created_at
            else None,
        }
        for payment in payments
    ]