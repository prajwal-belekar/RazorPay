"""RecoverAI Recovery Orchestrator.

Coordinates the end-to-end recovery pipeline for a failed payment:

    payment
      -> AI Recovery Decision Engine   (recovery_ai_service)
      -> Action Firewall               (action_firewall)
      -> Recovery Execution (DRY_RUN)  (recovery_execution_service)

This is the single orchestration entry point used by BOTH:

  - the Razorpay ``payment.failed`` webhook handler, and
  - the manual testing endpoint ``POST /api/recovery/process/{payment_id}``.

Guarantees:
  - Reuses existing services; creates no duplicate models or tables.
  - Execution stays DRY_RUN; no real Razorpay retry / charge / link / message.
  - Never runs recovery for captured / already-recovered payments.
  - Fail-safe: if AI is unavailable the existing rule fallback is used; if the
    firewall rejects, execution is never invoked; execution failures are
    persisted on the existing schema.
  - No secrets, credentials, or stack traces are ever exposed in results.
"""

import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models import Payment
from app.services.action_firewall import ActionFirewall, record_firewall_audit
from app.services.recovery_ai_service import (
    SOURCE_OLLAMA,
    analyze_and_persist_payment,
)
from app.services.recovery_execution_service import (
    DRY_RUN,
    execute_recovery_action,
)

logger = logging.getLogger(__name__)

# Recovery statuses that mean "this payment is no longer a recovery candidate".
_NON_ELIGIBLE_RECOVERY = {"SUCCESS", "RECOVERED", "AUTHORIZED"}
_NON_ELIGIBLE_PAYMENT_STATUS = {"captured", "succeeded", "paid"}


def _payment_is_eligible(payment: Payment) -> tuple[bool, str]:
    """Return (eligible, reason) for the recovery pipeline.

    A payment is eligible only when it is a genuine failed transaction that
    has not already been recovered or captured.
    """
    status = (payment.payment_status or "").lower()
    recovery = (payment.recovery_status or "").upper()

    if recovery in _NON_ELIGIBLE_RECOVERY:
        return False, (
            f"Payment is already {recovery.lower()} and not eligible for recovery."
        )
    if status in _NON_ELIGIBLE_PAYMENT_STATUS:
        return False, (
            f"Payment status '{payment.payment_status}' is not eligible for recovery."
        )
    if payment.amount is None or payment.amount <= 0:
        return False, "Payment has no amount and cannot be recovered."

    return True, ""


def _safe_execution_summary(execution: Dict[str, Any]) -> Dict[str, Any]:
    """Return a sanitised, DRY_RUN-safe execution summary for the API response."""
    return {
        "execution_id": execution.get("id"),
        "payment_id": execution.get("payment_id"),
        "action": execution.get("action"),
        "status": execution.get("status"),
        "execution_mode": execution.get("execution_mode", DRY_RUN),
        "simulated": execution.get("simulated"),
        "result_message": execution.get("result_message"),
        "firewall_approved": execution.get("firewall_approved"),
        "firewall_decision": execution.get("firewall_decision"),
        "firewall_reason": execution.get("firewall_reason"),
        "firewall_policy_version": execution.get("firewall_policy_version"),
        "error": execution.get("error"),
    }


async def process_failed_payment(
    payment_id: int,
    db: Session,
) -> Dict[str, Any]:
    """Run the full recovery pipeline for a failed payment.

    Returns a structured dict containing the AI decision, the firewall
    evaluation, and the DRY_RUN execution result (when approved). When the
    payment is not eligible, returns early with an ``eligible=False`` marker.

    Raises:
        ValueError: if the payment does not exist.
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if payment is None:
        raise ValueError(f"Payment {payment_id} not found.")

    # --- 1. Eligibility gate -------------------------------------------
    eligible, reason = _payment_is_eligible(payment)
    if not eligible:
        logger.info("Skipping recovery pipeline for payment %d: %s", payment_id, reason)
        return {
            "payment_id": payment_id,
            "eligible": False,
            "reason": reason,
        }

    # --- 2. AI Recovery Decision ---------------------------------------
    ai_decision = await analyze_and_persist_payment(payment)
    db.commit()

    # --- 3. Action Firewall --------------------------------------------
    decision_source = ai_decision.get("decision_source", SOURCE_OLLAMA)
    firewall_result = ActionFirewall.evaluate(
        amount=payment.amount,
        action=payment.recommended_action,
        confidence=payment.confidence,
        recovery_probability=(
            payment.recovery_probability
            if payment.recovery_probability is not None
            else payment.recovery_score
        ),
        retry_count=payment.retry_count or 0,
        previous_recovery_attempts=payment.previous_recovery_attempts or 0,
        payment_status=payment.payment_status,
        recovery_status=payment.recovery_status,
        last_recovery_attempt_at=payment.last_recovery_attempt_at,
        risk_level=payment.risk_level,
    )

    # Persist firewall audit + payment-level firewall fields
    record_firewall_audit(
        payment=payment,
        firewall_result=firewall_result,
        db=db,
    )

    # --- 4. Recovery Execution (DRY_RUN only) --------------------------
    execution_summary: Optional[Dict[str, Any]] = None
    if not firewall_result["approved"]:
        logger.info(
            "Recovery blocked by Action Firewall for payment %d: %s",
            payment_id,
            firewall_result["reason"],
        )
    else:
        try:
            execution = execute_recovery_action(
                payment=payment,
                action=payment.recommended_action,
                execution_mode=DRY_RUN,
                db=db,
            )
            execution_summary = _safe_execution_summary(execution)
        except ValueError as exc:
            logger.warning(
                "Recovery execution skipped for payment %d: %s",
                payment_id,
                exc,
            )
            execution_summary = {
                "status": "SKIPPED",
                "reason": str(exc),
                "execution_mode": DRY_RUN,
            }
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Recovery execution failed for payment %d", payment_id)
            execution_summary = {
                "status": "FAILED",
                "result_message": "Recovery execution failed internally.",
                "execution_mode": DRY_RUN,
            }

    result = {
        "payment_id": payment_id,
        "eligible": True,
        "ai_decision": {
            "payment_id": payment_id,
            "amount": ai_decision.get("amount"),
            "recommended_action": ai_decision.get("recommended_action"),
            "recovery_probability": ai_decision.get("recovery_probability"),
            "confidence": ai_decision.get("confidence"),
            "expected_recovery": ai_decision.get("expected_recovery"),
            "risk_level": ai_decision.get("risk_level"),
            "reason": ai_decision.get("reason"),
            "decision_source": decision_source,
            "model": ai_decision.get("model"),
            "ai_decision_at": (
                ai_decision["ai_decision_at"].isoformat()
                if hasattr(ai_decision.get("ai_decision_at"), "isoformat")
                else ai_decision.get("ai_decision_at")
            ),
        },
        "firewall": {
            "approved": firewall_result["approved"],
            "action": firewall_result["action"],
            "risk_level": firewall_result["risk_level"],
            "policy_version": firewall_result["policy_version"],
            "reason": firewall_result["reason"],
            "checks": firewall_result["checks"],
        },
        "execution": execution_summary
        if execution_summary is not None
        else {
            "status": "NOT_EXECUTED",
            "reason": "Execution was not invoked because the firewall did not approve.",
            "execution_mode": DRY_RUN,
        },
    }

    logger.info("Recovery pipeline completed for payment %d", payment_id)
    return result
