from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Payment, RecoveryExecution
from app.services.ai_service import analyze_payment_failure
from app.services.recovery_engine import compute_recovery_score


router = APIRouter(prefix="/api/simulator", tags=["Simulator"])


class SimulationRequest(BaseModel):
    payment_id: int
    horizon_days: int = Field(default=7, ge=1, le=30)
    retry_count: int | None = Field(default=None, ge=0, le=20)
    selected_strategies: list[str] | None = None


def _probability(value: float) -> float:
    return round(max(0.05, min(0.98, value)), 4)


def _strategy_result(
    strategy: str,
    probability: float,
    payment: Payment,
    reason: str,
    required_action: str,
    risk: str,
    cost_factor: float,
) -> dict[str, Any]:
    probability = _probability(probability)
    expected_value = round((payment.amount or 0.0) * probability, 2)
    roi = round(expected_value / max((payment.amount or 0.0) * cost_factor, 1), 2)
    return {
        "strategy": strategy,
        "probability": probability,
        "expected_value": expected_value,
        "roi": roi,
        "risk": risk,
        "required_action": required_action,
        "reason": reason,
        "predicted": True,
    }


@router.post("/run")
async def run_simulation(request: SimulationRequest, db: Session = Depends(get_db)):
    """Return predictions for one persisted payment; never creates an execution."""
    payment = db.query(Payment).filter(Payment.id == request.payment_id).first()
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found.")

    retry_count = (
        request.retry_count
        if request.retry_count is not None
        else (payment.retry_count or 0) + (payment.previous_recovery_attempts or 0)
    )
    ai_decision = await analyze_payment_failure(
        amount=payment.amount,
        failure_reason=payment.failure_reason,
        payment_method=payment.payment_method,
        customer_type=payment.customer_type,
        retry_count=retry_count,
        previous_recovery_attempts=payment.previous_recovery_attempts or 0,
        payment_timestamp=payment.payment_timestamp,
    )
    calculated_score = compute_recovery_score(
        amount=payment.amount,
        failure_reason=payment.failure_reason,
        payment_method=payment.payment_method,
        customer_type=payment.customer_type,
        retry_count=retry_count,
        previous_recovery_attempts=payment.previous_recovery_attempts or 0,
    )
    base = float(ai_decision.get("recovery_score") or calculated_score)
    reason_text = (payment.failure_reason or "").lower()
    transient = any(word in reason_text for word in ("timeout", "network", "temporary", "gateway", "unavailable"))
    method_problem = any(word in reason_text for word in ("declined", "authentication", "insufficient", "expired", "invalid"))
    predictions = [
        _strategy_result("DELAYED_RETRY", base + (0.06 if transient else -0.02), payment,
                         "A delayed retry gives a transient gateway issue time to clear.",
                         "Schedule one retry within the selected recovery horizon.", "MEDIUM", 0.12),
        _strategy_result("PAYMENT_LINK", base + (0.04 if method_problem else -0.01), payment,
                         "A payment link lets the customer choose an available payment method.",
                         "Create and deliver a Razorpay payment link.", "LOW", 0.10),
        _strategy_result("SOFT_PUSH_REMINDER", base - 0.10, payment,
                         "A reminder is less invasive when there is no strong technical recovery signal.",
                         "Send a customer reminder through a configured messaging channel.", "LOW", 0.06),
        _strategy_result("HYBRID_RECOVERY_CASCADE", base + (0.07 if method_problem or not transient else 0.03), payment,
                         "A retry followed by a payment link covers both transient and method-specific failures.",
                         "Schedule a retry, then create a payment link only if needed.", "HIGH", 0.18),
    ]
    allowed = set(request.selected_strategies or [])
    if allowed:
        predictions = [item for item in predictions if item["strategy"] in allowed]
    recommended = max(predictions, key=lambda item: item["probability"]) if predictions else None
    latest = (
        db.query(RecoveryExecution)
        .filter(RecoveryExecution.payment_id == payment.id)
        .order_by(RecoveryExecution.id.desc())
        .first()
    )
    actual = None
    if latest is not None:
        actual = {
            "status": latest.status,
            "action": latest.action,
            "amount": payment.amount if latest.status == "SUCCESS" else None,
            "timestamp": latest.completed_at.isoformat() if latest.completed_at else None,
            "execution_id": latest.id,
            "proof_status": latest.proof_status,
            "predicted": False,
        }
    return {
        "payment": {
            "id": payment.id,
            "amount": payment.amount,
            "failure_reason": payment.failure_reason,
            "payment_method": payment.payment_method,
            "customer_history": payment.customer_type,
            "retry_count": retry_count,
        },
        "ai": {
            "confidence": ai_decision.get("confidence"),
            "decision_source": ai_decision.get("decision_source"),
            "reason": ai_decision.get("reason"),
        },
        "predictions": predictions,
        "recommended_strategy": recommended["strategy"] if recommended else None,
        "actual": actual,
        "predicted": True,
    }