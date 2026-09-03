"""Recovery-case inspection endpoints.

Exposes the recovery decisions produced by the Recovery Engine for the
frontend / dashboards to inspect. Each "recovery case" is a failed Payment
that has been scored and assigned a strategy by the engine.

These endpoints are read-only inspection of decisions; they never execute a
recovery action.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Payment, RecoveryExecution
from app.services.action_executor import (
    SUPPORTED_ACTIONS,
    execute_recovery_action,
)
from app.services.action_firewall import ActionFirewall, record_firewall_audit
from app.services.recovery_ai_service import analyze_and_persist_payment
from app.services.recovery_proof import verify_proof

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/recovery",
    tags=["Recovery"],
)


# Statuses that mean "this payment is not an actionable recovery candidate".
_NON_CANDIDATE = {"SUCCESS", "RECOVERED", "AUTHORIZED"}


def _proof_for_payment(payment: Payment, db: Session) -> dict | None:
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


def _to_case(payment: Payment, db: Session) -> dict:
    """Shape a Payment into a recovery-case view for inspection."""
    return {
        "payment_id": payment.id,
        "razorpay_payment_id": payment.razorpay_payment_id,
        "razorpay_order_id": payment.razorpay_order_id,
        "amount": payment.amount,
        "payment_method": payment.payment_method,
        "failure_reason": payment.failure_reason,
        "recovery_score": payment.recovery_score,
        "recovery_probability": payment.recovery_probability or payment.recovery_score,
        "expected_recovery": payment.expected_recovery,
        "risk_level": payment.risk_level,
        "confidence": payment.confidence,
        "recommended_action": payment.recommended_action,
        "strategy": payment.recommended_action,
        "reason": payment.reason,
        "decision_source": payment.decision_source,
        "ai_decision_at": (
            payment.ai_decision_at.isoformat()
            if payment.ai_decision_at
            else None
        ),
        "recovery_status": payment.recovery_status,
        "payment_status": payment.payment_status,
        "retry_count": payment.retry_count,
        "previous_recovery_attempts": payment.previous_recovery_attempts,
        "payment_timestamp": (
            payment.payment_timestamp.isoformat()
            if payment.payment_timestamp
            else None
        ),
        # Action Firewall decision (persisted at candidate-creation time).
        "firewall": (
            {
                "decision": payment.firewall_decision,
                "reason": payment.firewall_reason,
                "policy_version": payment.firewall_policy_version,
                "evaluated_at": (
                    payment.firewall_evaluated_at.isoformat()
                    if payment.firewall_evaluated_at
                    else None
                ),
                "checks": payment.firewall_checks or [],
            }
            if payment.firewall_evaluated_at is not None
            else None
        ),
        "created_at": (
            payment.created_at.isoformat() if payment.created_at else None
        ),
        "proof": _proof_for_payment(payment, db),
    }


@router.get("/cases")
def list_recovery_cases(
    only_candidates: bool = True,
    db: Session = Depends(get_db),
):
    """List recovery decisions.

    By default returns only actionable recovery candidates (failed payments
    awaiting recovery). Pass ``only_candidates=false`` to include every
    record.
    """
    q = db.query(Payment).order_by(Payment.id.desc())
    if only_candidates:
        q = q.filter(Payment.recovery_status.notin_(_NON_CANDIDATE))
    payments = q.all()
    return [_to_case(p, db) for p in payments]


@router.get("/cases/{payment_id}")
def get_recovery_case(payment_id: int, db: Session = Depends(get_db)):
    """Inspect a single recovery decision for a payment."""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found.")
    return _to_case(payment, db)


@router.post("/analyze/{payment_id}")
async def analyze_payment_recovery(
    payment_id: int,
    db: Session = Depends(get_db),
):
    """Run the AI Recovery Decision Engine for a failed payment.

    Generates a structured recovery recommendation and persists it onto the Payment entity.
    Never executes a recovery action.
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if payment is None:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found.")

    # Eligibility check: payments already successfully captured or recovered are not eligible
    if (
        payment.recovery_status in ("SUCCESS", "RECOVERED")
        or payment.payment_status == "captured"
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Payment {payment_id} is already recovered or captured (status: {payment.recovery_status or payment.payment_status}).",
        )

    decision = await analyze_and_persist_payment(payment)
    db.commit()
    db.refresh(payment)

    return decision


@router.get("/{payment_id}/decision")
def get_payment_recovery_decision(
    payment_id: int,
    db: Session = Depends(get_db),
):
    """Retrieve the latest AI recovery recommendation for a payment."""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if payment is None:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found.")

    if not payment.recommended_action:
        raise HTTPException(
            status_code=404,
            detail=f"No AI recovery decision has been generated yet for payment {payment_id}.",
        )

    prob = (
        payment.recovery_probability
        if payment.recovery_probability is not None
        else payment.recovery_score
    )
    return {
        "payment_id": payment.id,
        "amount": payment.amount,
        "recommended_action": payment.recommended_action,
        "recovery_probability": prob,
        "confidence": payment.confidence,
        "expected_recovery": payment.expected_recovery,
        "risk_level": payment.risk_level,
        "reason": payment.reason,
        "decision_source": payment.decision_source,
        "ai_decision_at": (
            payment.ai_decision_at.isoformat()
            if payment.ai_decision_at
            else None
        ),
    }


@router.post("/firewall/{payment_id}")
async def evaluate_payment_firewall(
    payment_id: int,
    db: Session = Depends(get_db),
):
    """Evaluate whether an AI recovery action is permitted by the Action Firewall.

    This endpoint is purely evaluative (DRY RUN ONLY).
    It NEVER executes any real payment retry, link creation, or gateway mutation.
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if payment is None:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found.")

    # Retrieve persisted AI decision values, or analyze if not yet populated
    if (
        not payment.recommended_action
        and payment.recovery_status not in ("SUCCESS", "RECOVERED")
        and payment.payment_status != "captured"
    ):
        try:
            await analyze_and_persist_payment(payment)
            db.commit()
            db.refresh(payment)
        except Exception as exc:
            logger.warning("Could not auto-generate AI decision for firewall evaluation: %s", exc)

    prob = (
        payment.recovery_probability
        if payment.recovery_probability is not None
        else payment.recovery_score
    )

    result = ActionFirewall.evaluate(
        amount=payment.amount,
        action=payment.recommended_action or "RETRY",
        confidence=payment.confidence,
        recovery_probability=prob,
        retry_count=payment.retry_count or 0,
        previous_recovery_attempts=payment.previous_recovery_attempts or 0,
        payment_status=payment.payment_status,
        recovery_status=payment.recovery_status,
        last_recovery_attempt_at=payment.last_recovery_attempt_at,
        risk_level=payment.risk_level,
    )

    # Persist the evaluation result and audit log
    record_firewall_audit(payment=payment, firewall_result=result, db=db)

    return result


class VerifyProofRequest(BaseModel):
    execution_id: int


@router.post("/proofs/verify")
def verify_recovery_proof(body: VerifyProofRequest, db: Session = Depends(get_db)):
    """Verify a stored proof hash against its canonical recovery payload."""
    execution = (
        db.query(RecoveryExecution)
        .filter(RecoveryExecution.id == body.execution_id)
        .first()
    )
    if execution is None or execution.status != "SUCCESS" or not execution.proof_payload:
        raise HTTPException(status_code=404, detail="Recovery proof not available.")
    valid = verify_proof(execution.proof_payload, execution.proof_hash)
    return {
        "verified": valid,
        "proof_status": execution.proof_status or "NOT_VERIFIED",
        "proof_hash": execution.proof_hash,
        "chain_tx_hash": execution.chain_tx_hash,
        "chain_block_number": execution.chain_block_number,
        "chain_network": execution.chain_network,
    }


class ExecuteActionRequest(BaseModel):
    """Request body to execute a recovery action for a payment."""

    action: str | None = None


def _to_execution(execution: RecoveryExecution) -> dict:
    """Shape a RecoveryExecution row for the API response."""
    return {
        "id": execution.id,
        "payment_id": execution.payment_id,
        "action": execution.action,
        "status": execution.status,
        "firewall_decision": execution.firewall_decision,
        "firewall_reason": execution.firewall_reason,
        "firewall_policy_version": execution.firewall_policy_version,
        "idempotency_key": execution.idempotency_key,
        "provider": execution.provider,
        "provider_reference_id": execution.provider_reference_id,
        "provider_response": execution.provider_response or {},
        "error": execution.error,
        "started_at": (
            execution.started_at.isoformat() if execution.started_at else None
        ),
        "completed_at": (
            execution.completed_at.isoformat() if execution.completed_at else None
        ),
        "created_at": (
            execution.created_at.isoformat() if execution.created_at else None
        ),
        "proof_payload": execution.proof_payload,
        "proof_hash": execution.proof_hash,
        "proof_status": execution.proof_status,
        "chain_tx_hash": execution.chain_tx_hash,
        "chain_block_number": execution.chain_block_number,
        "chain_network": execution.chain_network,
    }


@router.get("/cases/{payment_id}/executions")
def list_recovery_executions(payment_id: int, db: Session = Depends(get_db)):
    """List the recovery action executions recorded for a payment."""
    if db.query(Payment).filter(Payment.id == payment_id).first() is None:
        raise HTTPException(status_code=404, detail="Payment not found.")
    executions = (
        db.query(RecoveryExecution)
        .filter(RecoveryExecution.payment_id == payment_id)
        .order_by(RecoveryExecution.id.desc())
        .all()
    )
    return [_to_execution(e) for e in executions]


@router.post("/cases/{payment_id}/execute")
def execute_recovery(payment_id: int, body: ExecuteActionRequest | None = None,
                     db: Session = Depends(get_db)):
    """Execute (or refuse) a recovery action for a payment.

    The action defaults to the engine's ``recommended_action`` when no
    explicit ``action`` is supplied. Every execution is gated by the Action
    Firewall (never bypassed); the result is a ``RecoveryExecution`` record.

    ``DUPLICATE`` is returned (with the existing record) if the exact same
    attempt was already executed, so a request can never double-charge.
    """
    if db.query(Payment).filter(Payment.id == payment_id).first() is None:
        raise HTTPException(status_code=404, detail="Payment not found.")

    action = (body.action if body and body.action else None)
    if action and action.upper() not in SUPPORTED_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported action '{action}'. "
                   f"Supported: {', '.join(sorted(SUPPORTED_ACTIONS))}.",
        )

    try:
        result = execute_recovery_action(payment_id=payment_id, action=action, db=db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    body_safe = dict(result)
    body_safe.pop("outcome", None)
    body_safe.pop("duplicate_of", None)
    return {
        "outcome": result.get("outcome"),
        "duplicate_of": result.get("duplicate_of"),
        "execution": body_safe,
    }
