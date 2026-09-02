from typing import Literal


Action = Literal[
    "RETRY",
    "PAYMENT_LINK",
    "ALTERNATIVE_METHOD",
    "HUMAN_REVIEW",
]


def make_fast_decision(
    amount: float,
    failure_reason: str,
    customer_type: str,
):
    """
    Fast deterministic decision engine.

    Returns a decision when the situation is simple enough
    to handle without calling the LLM.
    """

    reason = failure_reason.lower().strip()

    # Rule 1: Temporary bank/network problems
    if any(
        keyword in reason
        for keyword in [
            "timeout",
            "network",
            "temporary",
            "server error",
            "gateway error",
        ]
    ):
        return {
            "recommended_action": "RETRY",
            "reason": "The failure appears temporary and can be safely retried.",
            "confidence": 0.90,
            "source": "RULE_ENGINE",
        }

    # Rule 2: Authentication-related failures
    if any(
        keyword in reason
        for keyword in [
            "authentication",
            "auth failed",
            "otp failed",
            "verification failed",
        ]
    ):
        return {
            "recommended_action": "ALTERNATIVE_METHOD",
            "reason": "Authentication failure may persist on the current payment method.",
            "confidence": 0.85,
            "source": "RULE_ENGINE",
        }

    # Rule 3: Large transaction + unknown failure
    if amount >= 100000:
        return {
            "recommended_action": "HUMAN_REVIEW",
            "reason": "High-value transaction requires additional review.",
            "confidence": 0.95,
            "source": "RULE_ENGINE",
        }

    # Rule 4: New customer + repeated/unknown failure
    if customer_type.lower() == "new" and any(
        keyword in reason
        for keyword in [
            "failed",
            "declined",
            "rejected",
        ]
    ):
        return {
            "recommended_action": "PAYMENT_LINK",
            "reason": "A payment link provides a safer alternative for a new customer.",
            "confidence": 0.80,
            "source": "RULE_ENGINE",
        }

    # No deterministic rule matched.
    # Return None so the AI can handle the case.
    return None