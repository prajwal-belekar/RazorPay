from typing import Dict


async def execute_recovery_action(
    action: str,
    amount: float,
):
    """
    Executes a simulated recovery action.

    This is intentionally simulated for now.
    Later we will connect it to Razorpay APIs.
    """

    if action == "RETRY":
        return {
            "action": "RETRY",
            "status": "SUCCESS",
            "message": f"Payment retry initiated for ₹{amount:,.2f}.",
        }

    if action == "PAYMENT_LINK":
        return {
            "action": "PAYMENT_LINK",
            "status": "SUCCESS",
            "message": "Payment link generation initiated.",
        }

    if action == "ALTERNATIVE_METHOD":
        return {
            "action": "ALTERNATIVE_METHOD",
            "status": "SUCCESS",
            "message": "Alternative payment method recommended.",
        }

    if action == "HUMAN_REVIEW":
        return {
            "action": "HUMAN_REVIEW",
            "status": "PENDING",
            "message": "Payment has been escalated for human review.",
        }

    return {
        "action": action,
        "status": "FAILED",
        "message": "Unknown recovery action.",
    }