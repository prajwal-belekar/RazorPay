"""RecoverAI AI Action Firewall / Merchant Governance Layer.

A strict safety boundary between the AI recovery recommendation and autonomous execution:

    AI Recovery Decision
            |
            v
      Action Firewall   <-- This service (EVALUATION ONLY)
            |
            v
    APPROVED / BLOCKED

GUARANTEES:
1. DRY-RUN ONLY: Evaluation NEVER executes any real payment retry, charge,
   payment link, message, or gateway mutation.
2. DETERMINISTIC & AUDITABLE: Evaluates 7 core safety policies:
   - Transaction limit (<= ₹50,000)
   - AI confidence threshold (>= 0.85)
   - Recovery probability threshold (>= 0.70)
   - Maximum retry count (< 2)
   - Payment status guard (not captured, succeeded, or recovered)
   - Allowed actions (RETRY, PAYMENT_LINK, REMINDER, HYBRID)
   - Cooldown guard (15 minutes for RETRY; fails safely if timestamp missing on prior attempts)
3. Never logs or returns secrets, credentials, or sensitive customer details.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models import FirewallAuditLog, Payment

logger = logging.getLogger(__name__)

POLICY_VERSION = "v1.0"

# Governance Thresholds
AUTONOMOUS_LIMIT_INR = 50_000.0
MIN_CONFIDENCE = 0.85
MIN_RECOVERY_PROBABILITY = 0.70
MAX_RETRIES = 2
COOLDOWN_MINUTES = 15.0

ALLOWED_ACTIONS = {"RETRY", "PAYMENT_LINK", "REMINDER", "HYBRID"}

_NON_ELIGIBLE_PAYMENT_STATUS = {
    "captured",
    "succeeded",
    "authorized-captured",
    "paid",
}
_NON_ELIGIBLE_RECOVERY_STATUS = {"SUCCESS", "RECOVERED"}


class ActionFirewall:
    """Reusable governance service evaluating recovery actions against merchant safety policies."""

    @staticmethod
    def evaluate(
        *,
        amount: float,
        action: Optional[str],
        confidence: Optional[float] = None,
        recovery_probability: Optional[float] = None,
        retry_count: int = 0,
        previous_recovery_attempts: int = 0,
        payment_status: Optional[str] = None,
        recovery_status: Optional[str] = None,
        last_recovery_attempt_at: Optional[datetime] = None,
        risk_level: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Evaluate all safety checks for a recovery candidate.

        Returns a structured dictionary:
        {
            "approved": bool,
            "action": str,
            "risk_level": str,
            "policy_version": str,
            "reason": str,
            "checks": [
                {"name": "...", "passed": bool}
            ]
        }
        """
        now = now or datetime.now(timezone.utc)
        clean_action = (action or "").strip().upper()
        amount_val = float(amount or 0.0)
        conf_val = float(confidence) if confidence is not None else 0.0
        prob_val = float(recovery_probability) if recovery_probability is not None else 0.0
        retries_val = int(retry_count or 0)
        prev_attempts_val = int(previous_recovery_attempts or 0)
        total_retries = retries_val + prev_attempts_val

        checks: List[Dict[str, Any]] = []
        failure_reasons: List[str] = []

        # 1. TRANSACTION LIMIT CHECK
        limit_passed = amount_val <= AUTONOMOUS_LIMIT_INR
        checks.append({"name": "transaction_limit", "passed": limit_passed})
        if not limit_passed:
            failure_reasons.append("Transaction exceeds autonomous execution limit")

        # 2. AI CONFIDENCE CHECK
        conf_passed = confidence is not None and conf_val >= MIN_CONFIDENCE
        checks.append({"name": "confidence_threshold", "passed": conf_passed})
        if not conf_passed:
            failure_reasons.append("AI confidence below autonomous execution threshold")

        # 3. RECOVERY PROBABILITY CHECK
        prob_passed = recovery_probability is not None and prob_val >= MIN_RECOVERY_PROBABILITY
        checks.append({"name": "recovery_probability", "passed": prob_passed})
        if not prob_passed:
            failure_reasons.append("Recovery probability below required threshold")

        # 4. RETRY COUNT CHECK
        # Limit is 2; if retry_count >= 2, reject
        retry_passed = retries_val < MAX_RETRIES and total_retries < MAX_RETRIES
        checks.append({"name": "retry_count", "passed": retry_passed})
        if not retry_passed:
            failure_reasons.append("Maximum retry limit reached")

        # 5. PAYMENT STATUS CHECK
        status_clean = (payment_status or "").strip().lower()
        rec_clean = (recovery_status or "").strip().upper()
        already_settled = (
            status_clean in _NON_ELIGIBLE_PAYMENT_STATUS
            or rec_clean in _NON_ELIGIBLE_RECOVERY_STATUS
        )
        status_passed = not already_settled
        checks.append({"name": "payment_status", "passed": status_passed})
        if not status_passed:
            failure_reasons.append("Payment is no longer eligible for recovery")

        # 6. ALLOWED ACTION CHECK
        action_passed = clean_action in ALLOWED_ACTIONS
        checks.append({"name": "allowed_action", "passed": action_passed})
        if not action_passed:
            failure_reasons.append(f"Unsupported recovery action '{action}'")

        # 7. COOLDOWN CHECK (Applies to RETRY and HYBRID)
        cooldown_passed = True
        cooldown_reason = None
        if clean_action in ("RETRY", "HYBRID"):
            has_prior_attempt = (total_retries > 0) or (last_recovery_attempt_at is not None)
            if has_prior_attempt:
                if last_recovery_attempt_at is None:
                    # Fail safely if prior retry occurred but timestamp is unavailable
                    cooldown_passed = False
                    cooldown_reason = "Cooldown timestamp unavailable; retry blocked for safety"
                else:
                    # Check elapsed minutes
                    attempt_time = last_recovery_attempt_at
                    if attempt_time.tzinfo is None:
                        attempt_time = attempt_time.replace(tzinfo=timezone.utc)
                    elapsed_minutes = (now - attempt_time).total_seconds() / 60.0
                    if elapsed_minutes < COOLDOWN_MINUTES:
                        cooldown_passed = False
                        cooldown_reason = (
                            f"Action within {int(COOLDOWN_MINUTES)}-minute cooldown window "
                            f"({elapsed_minutes:.1f}m elapsed)"
                        )
                    else:
                        cooldown_passed = True

        checks.append({"name": "cooldown", "passed": cooldown_passed})
        if not cooldown_passed and cooldown_reason:
            failure_reasons.append(cooldown_reason)

        approved = len(failure_reasons) == 0
        overall_reason = (
            "All autonomous recovery policy checks passed"
            if approved
            else failure_reasons[0]
        )

        # Derive or preserve risk level
        derived_risk = risk_level
        if not derived_risk:
            if prob_val >= 0.80 and amount_val <= 25_000:
                derived_risk = "LOW"
            elif prob_val >= 0.60:
                derived_risk = "MEDIUM"
            else:
                derived_risk = "HIGH"

        return {
            "approved": approved,
            "action": clean_action or "UNKNOWN",
            "risk_level": derived_risk,
            "policy_version": POLICY_VERSION,
            "reason": overall_reason,
            "checks": checks,
        }


def evaluate_policy(*args, **kwargs) -> Dict[str, Any]:
    """Compatibility wrapper redirecting to ActionFirewall.evaluate."""
    # Map kwargs if legacy caller uses different signature
    amount = kwargs.get("amount", 0.0)
    action = kwargs.get("action") or kwargs.get("recommended_action") or "RETRY"
    confidence = kwargs.get("confidence")
    recovery_probability = kwargs.get("recovery_probability") or kwargs.get("recovery_score")
    retry_count = kwargs.get("retry_count", 0)
    previous_recovery_attempts = kwargs.get("previous_recovery_attempts", 0)
    payment_status = kwargs.get("payment_status")
    recovery_status = kwargs.get("recovery_status")
    last_recovery_attempt_at = kwargs.get("last_recovery_attempt_at")
    risk_level = kwargs.get("risk_level")
    now = kwargs.get("now")

    return ActionFirewall.evaluate(
        amount=amount,
        action=action,
        confidence=confidence,
        recovery_probability=recovery_probability,
        retry_count=retry_count,
        previous_recovery_attempts=previous_recovery_attempts,
        payment_status=payment_status,
        recovery_status=recovery_status,
        last_recovery_attempt_at=last_recovery_attempt_at,
        risk_level=risk_level,
        now=now,
    )


def record_firewall_audit(
    *,
    payment: Payment,
    firewall_result: Dict[str, Any],
    db: Session,
) -> FirewallAuditLog:
    """Persist firewall evaluation outcome on the Payment and create an immutable audit record."""
    now = datetime.now(timezone.utc)

    # 1. Update Payment model columns
    payment.firewall_approved = firewall_result["approved"]
    payment.firewall_decision = "APPROVED" if firewall_result["approved"] else "BLOCKED"
    payment.firewall_reason = firewall_result["reason"]
    payment.firewall_policy_version = firewall_result["policy_version"]
    payment.firewall_checks = firewall_result["checks"]
    payment.firewall_evaluated_at = now
    payment.firewall_checked_at = now

    # 2. Insert into immutable audit log table
    audit_entry = FirewallAuditLog(
        payment_id=payment.id,
        recommended_action=firewall_result["action"],
        approved=firewall_result["approved"],
        risk_level=firewall_result.get("risk_level"),
        policy_version=firewall_result["policy_version"],
        reason=firewall_result["reason"],
        checks=firewall_result["checks"],
        evaluation_timestamp=now,
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)
    db.refresh(payment)

    return audit_entry
