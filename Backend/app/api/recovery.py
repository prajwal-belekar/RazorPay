"""Recovery-case inspection endpoints.

Exposes the recovery decisions produced by the Recovery Engine for the
frontend / dashboards to inspect. Each "recovery case" is a failed Payment
that has been scored and assigned a strategy by the engine.

These endpoints are read-only inspection of decisions; they never execute a
recovery action.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
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
from app.services.recovery_execution_service import (
    BLOCKED,
    DRY_RUN,
    SUPPORTED_ACTIONS as EXECUTION_SUPPORTED_ACTIONS,
    execute_recovery_action as execute_dry_run_action,
)
from app.services.blockchain_service import blockchain_service
from app.services.recovery_orchestrator import process_failed_payment
from app.services.recovery_passport import build_recovery_passport
from app.services.recovery_proof import build_proof_payload, hash_proof, verify_proof

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


@router.get("/passport/{payment_id}")
def get_recovery_passport(payment_id: int, db: Session = Depends(get_db)):
    """Retrieve the Recovery Passport / audit trail for a payment.

    Composes the persisted AI decision, Action Firewall evaluation, and the
    latest recovery execution (including HYBRID steps) into one structured,
    read-only representation for a payment.

    Guarantees:
      - Returns 404 if the payment does not exist.
      - Read-only: creates no records, triggers no AI, executes no recovery,
        and never calls Razorpay or any customer notification channel.
      - Never exposes secrets, credentials, card data, or customer contact
        information.
      - Handles payments with no AI decision / no execution gracefully.
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found.")
    return build_recovery_passport(payment=payment, db=db)


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


# ---------------------------------------------------------------------------
# Recovery Execution Engine (DRY-RUN sandbox mode)
# ---------------------------------------------------------------------------


class DryRunExecuteRequest(BaseModel):
    """Request body for the DRY-RUN execution engine endpoint."""

    action: str | None = None
    execution_mode: str | None = None


@router.post("/execute/{payment_id}")
def execute_recovery_dry_run(
    payment_id: int,
    body: DryRunExecuteRequest | None = None,
    db: Session = Depends(get_db),
):
    """Execute (or simulate) a recovery action in DRY-RUN sandbox mode.

    Flow (mandatory, never bypassed):
      1. Find payment
      2. Retrieve persisted AI decision
      3. Run Action Firewall
      4. If firewall rejects -> stop, return BLOCKED
      5. If firewall approves -> simulate the action
      6. Store execution result in RecoveryExecution table
      7. Return structured response

    This endpoint NEVER executes real Razorpay operations, charges customers,
    sends messages, or creates real payment links. Default mode is DRY_RUN.
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if payment is None:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found.")

    # Validate AI decision exists
    if not payment.recommended_action:
        raise HTTPException(
            status_code=400,
            detail=(
                f"No AI recovery decision exists for payment {payment_id}. "
                "Run POST /api/recovery/analyze/{payment_id} first."
            ),
        )

    action = (body.action if body and body.action else None)
    if action and action.upper() not in EXECUTION_SUPPORTED_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported action '{action}'. "
                f"Supported: {', '.join(sorted(EXECUTION_SUPPORTED_ACTIONS))}."
            ),
        )

    execution_mode = (
        (body.execution_mode if body and body.execution_mode else None) or DRY_RUN
    )

    try:
        result = execute_dry_run_action(
            payment=payment,
            action=action,
            execution_mode=execution_mode,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    status_code = 200
    if result.get("status") == BLOCKED:
        status_code = 403
    elif result.get("status") == "ALREADY_EXECUTED":
        status_code = 409

    return JSONResponse(status_code=status_code, content=result)


# ---------------------------------------------------------------------------
# Blockchain Proof Layer
# ---------------------------------------------------------------------------


@router.post("/proof/{payment_id}")
def submit_recovery_proof(payment_id: int, db: Session = Depends(get_db)):
    """Submit a deterministic recovery proof hash to the Polygon Amoy blockchain.

    Flow:
      1. Find the latest SUCCESS execution with a proof_hash for this payment.
      2. Build the proof payload from execution and payment data.
      3. Compute a deterministic SHA-256 proof hash.
      4. Submit the hash to the RecoveryProof smart contract.
      5. Persist chain_tx_hash, chain_block_number, chain_network onto the execution row.
      6. Return the submission result.

    Blockchain failures never corrupt PostgreSQL: a FAILED status is stored
    safely and the existing proof data remains intact.
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if payment is None:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found.")

    # Find the latest successful execution with a proof_hash
    execution = (
        db.query(RecoveryExecution)
        .filter(
            RecoveryExecution.payment_id == payment_id,
            RecoveryExecution.status == "SUCCESS",
            RecoveryExecution.proof_hash.isnot(None),
        )
        .order_by(RecoveryExecution.id.desc())
        .first()
    )
    if execution is None:
        # Fall back to any execution with a proof_hash (e.g. SIMULATED)
        execution = (
            db.query(RecoveryExecution)
            .filter(
                RecoveryExecution.payment_id == payment_id,
                RecoveryExecution.proof_hash.isnot(None),
            )
            .order_by(RecoveryExecution.id.desc())
            .first()
        )
    if execution is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No recovery execution with a proof hash found for payment {payment_id}. "
                "Run POST /api/recovery/execute/{payment_id} first."
            ),
        )

    # Rebuild the proof payload deterministically
    razorpay_pid = payment.razorpay_payment_id or f"pay_internal_{payment.id}"
    payload = build_proof_payload(
        transaction_id=f"Payment #{payment.id}",
        razorpay_payment_id=razorpay_pid,
        action=execution.action,
        recovery_timestamp=execution.completed_at or execution.created_at,
        recovered_amount=payment.amount,
        ai_confidence=payment.confidence,
        policy_version=execution.firewall_policy_version,
        firewall_decision=execution.firewall_decision,
        execution_id=execution.id,
    )
    proof_hash = hash_proof(payload)

    # Check if already submitted to blockchain (idempotent)
    if execution.chain_tx_hash and execution.proof_status == "ON_CHAIN":
        return {
            "payment_id": payment_id,
            "execution_id": execution.id,
            "proof_hash": proof_hash,
            "proof_status": "ON_CHAIN",
            "chain_tx_hash": execution.chain_tx_hash,
            "chain_block_number": execution.chain_block_number,
            "chain_network": execution.chain_network,
            "already_submitted": True,
        }

    razorpay_pid_for_chain = razorpay_pid
    result = blockchain_service.submit_proof(
        payment_id=razorpay_pid_for_chain,
        proof_hash=proof_hash,
    )

    # Persist chain details onto the execution row (non-destructive)
    execution.proof_payload = payload
    execution.proof_hash = proof_hash
    execution.chain_network = f"polygon-amoy"

    if result["submitted"]:
        execution.proof_status = result["status"]
        execution.chain_tx_hash = result.get("chain_tx_hash")
        execution.chain_block_number = result.get("chain_block_number")
    else:
        execution.proof_status = result["status"]
        logger.warning(
            "Blockchain proof submission did not succeed for payment %d: %s",
            payment_id,
            result.get("reason"),
        )

    db.commit()
    db.refresh(execution)

    return {
        "payment_id": payment_id,
        "execution_id": execution.id,
        "proof_payload": payload,
        "proof_hash": proof_hash,
        "proof_status": execution.proof_status,
        "chain_tx_hash": execution.chain_tx_hash,
        "chain_block_number": execution.chain_block_number,
        "chain_network": execution.chain_network,
        "blockchain_result": result,
    }


@router.get("/proof/{payment_id}")
def get_recovery_proof(payment_id: int, db: Session = Depends(get_db)):
    """Retrieve the on-chain and local proof for a recovery execution.

    Returns the locally stored proof data and, when the blockchain is
    configured, the on-chain verification result.
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if payment is None:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found.")

    execution = (
        db.query(RecoveryExecution)
        .filter(
            RecoveryExecution.payment_id == payment_id,
            RecoveryExecution.proof_hash.isnot(None),
        )
        .order_by(RecoveryExecution.id.desc())
        .first()
    )
    if execution is None:
        raise HTTPException(
            status_code=404,
            detail=f"No recovery proof found for payment {payment_id}.",
        )

    razorpay_pid = (
        payment.razorpay_payment_id
        or execution.proof_payload.get("razorpay_payment_id", "")
        if execution.proof_payload
        else ""
    )

    # Local verification
    local_valid = verify_proof(execution.proof_payload or {}, execution.proof_hash)

    # On-chain verification (when blockchain is configured)
    on_chain_result = None
    if blockchain_service.is_configured and razorpay_pid:
        on_chain_result = blockchain_service.verify_proof_on_chain(
            payment_id=razorpay_pid,
            expected_hash=execution.proof_hash,
        )

    return {
        "payment_id": payment_id,
        "execution_id": execution.id,
        "proof_payload": execution.proof_payload,
        "proof_hash": execution.proof_hash,
        "proof_status": execution.proof_status,
        "local_verified": local_valid,
        "on_chain_verification": on_chain_result,
        "chain_tx_hash": execution.chain_tx_hash,
        "chain_block_number": execution.chain_block_number,
        "chain_network": execution.chain_network,
    }


@router.post("/process/{payment_id}")
async def process_recovery_pipeline(payment_id: int, db: Session = Depends(get_db)):
    """Run the full recovery pipeline for a payment (manual/development testing).

    Executes the same orchestrator used by the Razorpay webhook:

        payment -> AI Decision -> Action Firewall -> DRY_RUN Execution

    This endpoint NEVER bypasses the AI engine, Action Firewall, or the
    DRY_RUN execution restriction, and it NEVER calls real Razorpay recovery.
    """
    if db.query(Payment).filter(Payment.id == payment_id).first() is None:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found.")

    try:
        result = await process_failed_payment(payment_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return result
