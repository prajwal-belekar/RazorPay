"""RecoverAI Recovery Engine.

Turns a failed payment into an actionable recovery decision:

  Input:  amount, failure reason, payment method, customer type/history,
          retry count, previous recovery attempts, payment timestamp
  Output: a recovery score (0-100) and a recommended strategy drawn from
          {RETRY, PAYMENT_LINK, REMINDER, HYBRID} plus an explanation.

The engine is deterministic and offline-safe (no external model dependency)
so it can always produce a decision for a failed Razorpay payment. It never
invents customer information: any input the upstream gateway does not
provide defaults to "unknown", and the scoring accounts for that honestly.

IMPORTANT: This module only *recommends* recovery. It never executes the
recovery action itself.
"""

from datetime import datetime
from typing import Dict, Optional

# Supported recovery strategies.
STRATEGY_RETRY = "RETRY"
STRATEGY_PAYMENT_LINK = "PAYMENT_LINK"
STRATEGY_REMINDER = "REMINDER"
STRATEGY_HYBRID = "HYBRID"

DEFAULT_STRATEGY = STRATEGY_RETRY

MAX_AUTO_RETRIES = 2      # beyond this, repeated RETRY is discouraged
HIGH_VALUE_INR = 100_000  # amounts above this get extra caution

# Keywords hinting at a transient / retryable failure.
TRANSIENT_KEYWORDS = [
    "timeout", "network", "temporary", "server error", "gateway error",
    "try again", "later", "unavailable", "timed out", "busy",
]

# Keywords hinting that the payment method itself is the problem.
AUTH_OR_METHOD_KEYWORDS = [
    "authentication", "auth failed", "otp failed", "verification",
    "invalid card", "card declined", "insufficient balance",
    "insufficient funds", "limit exceeded", "token expired",
]


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _contains_any(text: str, keywords) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


def compute_recovery_score(
    amount: float,
    failure_reason: Optional[str],
    payment_method: Optional[str] = None,
    customer_type: Optional[str] = None,
    retry_count: int = 0,
    previous_recovery_attempts: int = 0,
    payment_timestamp: Optional[datetime] = None,
) -> float:
    """Return a recovery-score probability clamped to [0, 1].

    Scoring is additive from a neutral 0.50 base and only moves when there
    is real signal. Unknown inputs leave the score closer to neutral.
    """
    reason = (failure_reason or "").strip()
    score = 0.50

    # Strong positive signal: a clearly transient failure is more recoverable.
    if _contains_any(reason, TRANSIENT_KEYWORDS):
        score += 0.20

    # Negative signal: the method/authentication itself is the problem.
    if _contains_any(reason, AUTH_OR_METHOD_KEYWORDS):
        score -= 0.15

    # Large amounts are less likely to be auto-recovered.
    if amount and amount >= HIGH_VALUE_INR:
        score -= 0.10

    # Repeated failures reduce the chance of a successful auto-recovery,
    # especially once past the auto-retry budget.
    total_attempts = int(retry_count or 0) + int(previous_recovery_attempts or 0)
    if total_attempts > 0:
        score -= min(0.05 * total_attempts, 0.20)

    # Simple UPI/card failures that are transient remain fairly recoverable,
    # but never over-promise with unknowable data.
    method = (payment_method or "").lower()
    if method and _contains_any(reason, TRANSIENT_KEYWORDS):
        score += 0.05

    return round(_clamp01(score), 4)


def recommend_strategy(
    amount: float,
    failure_reason: Optional[str],
    payment_method: Optional[str] = None,
    customer_type: Optional[str] = None,
    retry_count: int = 0,
    previous_recovery_attempts: int = 0,
    recovery_score: Optional[float] = None,
) -> Dict[str, object]:
    """Choose a recovery strategy from {RETRY, PAYMENT_LINK, REMINDER, HYBRID}.

    Returns a dict with ``recommended_action``, ``reason``, ``confidence``,
    and ``strategy`` so the caller can persist them onto the Payment record.
    """
    if recovery_score is None:
        recovery_score = compute_recovery_score(
            amount=amount,
            failure_reason=failure_reason,
            payment_method=payment_method,
            customer_type=customer_type,
            retry_count=retry_count,
            previous_recovery_attempts=previous_recovery_attempts,
        )

    reason = (failure_reason or "").strip()
    total_attempts = int(retry_count or 0) + int(previous_recovery_attempts or 0)
    transient = _contains_any(reason, TRANSIENT_KEYWORDS)
    method_problem = _contains_any(reason, AUTH_OR_METHOD_KEYWORDS)
    is_new_customer = (customer_type or "").lower() in ("new", "first time")

    # 1) If the same failure keeps happening AND the method looks problematic,
    #    combine a retry with a payment-link fallback (HYBRID).
    if total_attempts >= MAX_AUTO_RETRIES and (method_problem or not transient):
        return {
            "recommended_action": STRATEGY_HYBRID,
            "strategy": STRATEGY_HYBRID,
            "reason": (
                "Repeated failures on this method; offer a fresh payment "
                "link while keeping a scheduled retry."
            ),
            "confidence": round(_clamp01(0.55 + 0.05 * (0 < total_attempts < 3)), 4),
        }

    # 2) Transient failures are the safest to RETRY automatically.
    if transient and not method_problem:
        return {
            "recommended_action": STRATEGY_RETRY,
            "strategy": STRATEGY_RETRY,
            "reason": "Failure appears temporary; a retry is low-risk.",
            "confidence": round(_clamp01(0.80 + recovery_score * 0.15), 4),
        }

    # 3) A fresh/unknown customer with a method problem is better handed a
    #    non-interactive payment link than an aggressive retry.
    if is_new_customer or method_problem:
        return {
            "recommended_action": STRATEGY_PAYMENT_LINK,
            "strategy": STRATEGY_PAYMENT_LINK,
            "reason": (
                "Offer a payment link so the customer can complete payment "
                "on their own terms."
            ),
            "confidence": round(_clamp01(0.70 + recovery_score * 0.10), 4),
        }

    # 4) For low-risk, low-urgency cases a gentle REMINDER is more
    #    appropriate than an aggressive technical retry.
    if (
        amount
        and amount < 10_000
        and not transient
        and not method_problem
        and not is_new_customer
    ):
        return {
            "recommended_action": STRATEGY_REMINDER,
            "strategy": STRATEGY_REMINDER,
            "reason": (
                "Low-value failure with no clear technical blocker; a "
                "reminder is sufficient before any technical retry."
            ),
            "confidence": round(_clamp01(0.65 + recovery_score * 0.10), 4),
        }

    # 5) Default: a safe, single retry.
    return {
        "recommended_action": STRATEGY_RETRY,
        "strategy": STRATEGY_RETRY,
        "reason": "Default low-risk recovery: retry the failed payment once.",
        "confidence": round(_clamp01(0.60 + recovery_score * 0.10), 4),
    }


def build_recovery_decision(
    *,
    amount: float,
    failure_reason: Optional[str],
    payment_method: Optional[str] = None,
    customer_type: Optional[str] = None,
    retry_count: int = 0,
    previous_recovery_attempts: int = 0,
    payment_timestamp: Optional[datetime] = None,
) -> Dict[str, object]:
    """Produce a complete, persistable recovery decision.

    Convenience wrapper combining scoring + strategy selection into a single
    dict with a ``decision_source`` labelled ``RECOVERY_ENGINE``.
    """
    recovery_score = compute_recovery_score(
        amount=amount,
        failure_reason=failure_reason,
        payment_method=payment_method,
        customer_type=customer_type,
        retry_count=retry_count,
        previous_recovery_attempts=previous_recovery_attempts,
        payment_timestamp=payment_timestamp,
    )
    strategy = recommend_strategy(
        amount=amount,
        failure_reason=failure_reason,
        payment_method=payment_method,
        customer_type=customer_type,
        retry_count=retry_count,
        previous_recovery_attempts=previous_recovery_attempts,
        recovery_score=recovery_score,
    )
    return {
        "recovery_score": recovery_score,
        "confidence": strategy["confidence"],
        "recommended_action": strategy["recommended_action"],
        "strategy": strategy["strategy"],
        "reason": strategy["reason"],
        "decision_source": "RECOVERY_ENGINE",
    }
