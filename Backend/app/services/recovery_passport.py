"""RecoverAI Recovery Passport / Audit Trail builder.

Composes a single structured, read-only "passport" for a payment from the
existing persisted records — it never mutates data, never triggers AI,
never executes recovery, and never calls Razorpay:

    Payment             -> payment identity, failure reason, AI decision,
                           persisted firewall fields, statuses
    FirewallAuditLog    -> latest firewall evaluation (action, risk, checks)
    RecoveryExecution   -> latest recovery execution (action, mode, status,
                           provider reference, steps for HYBRID)

The passport deliberately exposes NO secrets: raw credential/card/signature
fields are never included, and only the structured ``steps`` subset of a
HYBRID ``provider_response`` is surfaced.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models import FirewallAuditLog, Payment, RecoveryExecution


def _iso(value: Optional[datetime]) -> Optional[str]:
    """Serialize a datetime to ISO-8601, or None."""
    if value is None:
        return None
    return value.isoformat()


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    """Normalise a naive datetime to an aware one (assumed UTC) for max()."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _latest_timestamp(*candidates: Optional[datetime]) -> Optional[datetime]:
    """Return the latest non-None timestamp among the candidates."""
    aware = [c for c in (_as_utc(c) for c in candidates) if c is not None]
    if not aware:
        return None
    return max(aware)


def _load_latest_audit(db: Session, payment_id: int) -> Optional[FirewallAuditLog]:
    """Return the most recent firewall audit record for a payment."""
    return (
        db.query(FirewallAuditLog)
        .filter(FirewallAuditLog.payment_id == payment_id)
        .order_by(FirewallAuditLog.id.desc())
        .first()
    )


def _load_latest_execution(db: Session, payment_id: int) -> Optional[RecoveryExecution]:
    """Return the most recent recovery execution record for a payment."""
    return (
        db.query(RecoveryExecution)
        .filter(RecoveryExecution.payment_id == payment_id)
        .order_by(RecoveryExecution.id.desc())
        .first()
    )


def _ai_decision(payment: Payment) -> Optional[Dict[str, Any]]:
    """Persisted AI decision for the payment, or None when no decision exists."""
    if not payment.recommended_action:
        return None
    probability = (
        payment.recovery_probability
        if payment.recovery_probability is not None
        else payment.recovery_score
    )
    return {
        "action": payment.recommended_action,
        "confidence": payment.confidence,
        "recovery_probability": probability,
        "expected_recovery": payment.expected_recovery,
        "risk_level": payment.risk_level,
        "reason": payment.reason,
        "decision_source": payment.decision_source,
        "ai_decision_at": _iso(payment.ai_decision_at),
    }


def _firewall(
    payment: Payment,
    audit: Optional[FirewallAuditLog],
) -> Optional[Dict[str, Any]]:
    """Latest firewall evaluation: prefer the audit log, fall back to payment fields."""
    if audit is not None:
        return {
            "approved": audit.approved,
            "action": audit.recommended_action,
            "risk_level": audit.risk_level,
            "policy_version": audit.policy_version,
            "reason": audit.reason,
            "checks": audit.checks or [],
            "evaluated_at": _iso(audit.evaluation_timestamp),
        }
    if payment.firewall_evaluated_at is not None:
        return {
            "approved": payment.firewall_approved,
            "action": payment.recommended_action,
            "risk_level": payment.risk_level,
            "policy_version": payment.firewall_policy_version,
            "reason": payment.firewall_reason,
            "checks": payment.firewall_checks or [],
            "evaluated_at": _iso(payment.firewall_evaluated_at),
        }
    return None


def _recovery(execution: Optional[RecoveryExecution]) -> Optional[Dict[str, Any]]:
    """Latest recovery execution summary, or None when no execution exists."""
    if execution is None:
        return None
    return {
        "execution_id": execution.id,
        "action": execution.action,
        "execution_mode": execution.execution_mode,
        "status": execution.status,
        "simulated": execution.simulated,
        "provider": execution.provider,
        "provider_reference_id": execution.provider_reference_id,
        "result_message": execution.result_message,
        "error": execution.error,
        "started_at": _iso(execution.started_at),
        "completed_at": _iso(execution.completed_at),
    }


def _hybrid_steps(execution: Optional[RecoveryExecution]) -> list[Dict[str, Any]]:
    """Structured HYBRID child-strategy steps, or an empty list.

    Only the sanitised ``steps`` subset of a HYBRID ``provider_response`` is
    surfaced. Nothing else from ``provider_response`` is ever exposed.
    """
    if execution is None or execution.action != "HYBRID":
        return []
    response = execution.provider_response or {}
    if not isinstance(response, dict):
        return []
    steps = response.get("steps") or []
    if not isinstance(steps, list):
        return []
    return [
        {
            "action": step.get("action"),
            "status": step.get("status"),
            "recovered": step.get("recovered"),
            "passed_firewall": step.get("passed_firewall"),
            "reason": step.get("reason"),
        }
        for step in steps
        if isinstance(step, dict)
    ]


def build_recovery_passport(payment: Payment, db: Session) -> Dict[str, Any]:
    """Build the Recovery Passport / audit trail for a payment.

    Read-only: performs no writes, triggers no AI, executes no recovery,
    and never contacts Razorpay or any customer channel.
    """
    audit = _load_latest_audit(db, payment.id)
    execution = _load_latest_execution(db, payment.id)

    timestamp = _latest_timestamp(
        execution.completed_at if execution else None,
        payment.ai_decision_at,
        audit.evaluation_timestamp if audit else None,
        payment.firewall_evaluated_at,
        payment.last_recovery_attempt_at,
        payment.created_at,
    )

    return {
        "payment_id": payment.id,
        "failure_reason": payment.failure_reason,
        "payment_status": payment.payment_status,
        "recovery_status": payment.recovery_status,
        "ai_decision": _ai_decision(payment),
        "firewall": _firewall(payment, audit),
        "recovery": _recovery(execution),
        "hybrid_steps": _hybrid_steps(execution),
        "timestamp": _iso(timestamp),
    }