"""RecoverAI Recovery Execution Engine.

Executes approved recovery actions (RETRY / PAYMENT_LINK / REMINDER / HYBRID)
in a safe DRY-RUN sandbox mode by default. This is the final stage of the
three-stage pipeline:

    AI Decision Engine   -> "What should we do?"
    Action Firewall      -> "Are we allowed to do it?"
    Execution Engine     -> "Perform the approved action."  <-- This service

Guarantees:
  - DRY-RUN is the default and SAFE mode (controlled by RECOVERY_DRY_RUN,
    which defaults to TRUE). While enabled the engine NEVER calls real Razorpay
    APIs, sends messages (SMS / WhatsApp / email), or charges customers.
  - ONLY RETRY and PAYMENT_LINK have a real (LIVE) execution path, and these are
    only reachable when an operator explicitly sets RECOVERY_DRY_RUN=false with
    Razorpay TEST/SANDBOX credentials. DRY_RUN is enforced otherwise.
  - The real RETRY path uses the supported Razorpay recovery mechanism:
    create a fresh auto-capture Order for the retry attempt. A failed payment
    can NOT be re-charged via its original payment id; a new Order is the
    documented way to attempt a fresh payment. No charge occurs until the
    customer completes checkout.
  - The real PAYMENT_LINK path creates a hosted Razorpay payment link. Creating
    a link does not charge the customer; it only produces a shareable URL.
  - REMINDER is DRY-RUN ONLY for this step. It is simulated against a
    deterministic channel (EMAIL/SMS/WHATSAPP) but NEVER sends any real
    customer notification and never calls an external messaging provider.
  - HYBRID is DRY-RUN ONLY for this step. It is a controlled, simulated
    orchestration of RETRY -> PAYMENT_LINK -> REMINDER with deterministic stop
    logic. HYBRID always passes through the Action Firewall (including the
    15-minute RETRY cooldown) and never triggers any real Razorpay retry,
    payment-link creation, charge, capture, or customer notification.
  - NEVER executes unless the Action Firewall has explicitly approved.
  - Every execution attempt is recorded in an auditable RecoveryExecution row.
  - Idempotent: duplicate executions of the same action are safely detected.
  - No secrets, credentials, or sensitive customer PII is stored or returned.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.config import recovery_dry_run_enabled
from app.models import Payment, RecoveryExecution
from app.services.action_firewall import ActionFirewall, POLICY_VERSION

logger = logging.getLogger(__name__)

# Execution modes
DRY_RUN = "DRY_RUN"
LIVE = "LIVE"

# Execution statuses
BLOCKED = "BLOCKED"
SIMULATED = "SIMULATED"
SUCCESS = "SUCCESS"
FAILED = "FAILED"

# Supported recovery actions
SUPPORTED_ACTIONS = {"RETRY", "PAYMENT_LINK", "REMINDER", "HYBRID"}

# Actions that have a real (LIVE) execution path. RETRY and PAYMENT_LINK are
# implemented; REMINDER / HYBRID stay simulation-only for safety in this step.
_LIVE_SUPPORTED_ACTIONS = {"RETRY", "PAYMENT_LINK"}

# HYBRID simulates a controlled recovery sequence. This is the ordered list of
# child strategies that the hybrid orchestrator attempts, stopping as soon as an
# earlier stage would recover the payment.
HYBRID_STEP_ORDER = ("RETRY", "PAYMENT_LINK", "REMINDER")

# Deterministic simulation rule for HYBRID DRY_RUN: when a payment's recovery
# probability is strictly above this threshold, the simulated RETRY stage is
# treated as having recovered the payment, so the hybrid sequence stops there
# (it never continues to PAYMENT_LINK / REMINDER). At or below this threshold
# the simulated RETRY does not recover the payment and the sequence proceeds.
# This is a simulation heuristic only — it never touches Razorpay and never
# marks a payment as genuinely recovered.
RETRY_RECOVERY_SIMULATION_THRESHOLD = 0.85

# Reminder delivery channels. Represents how a future customer reminder could
# be delivered. REMINDER is DRY_RUN ONLY for this step: nothing is ever sent
# and no external messaging provider is called.
REMINDER_CHANNELS = {"EMAIL", "SMS", "WHATSAPP"}

# Deterministic default channel used by the REMINDER simulation when no real
# customer contact information is available (there is none on the Payment).
DEFAULT_REMINDER_CHANNEL = "EMAIL"

# Idempotency window: hours after which a previous execution record is considered
# stale and a new execution is allowed.
_IDEMPOTENCY_WINDOW_HOURS = 24

# Razorpay response keys that are NEVER persisted or returned (defensive).
_SENSITIVE_KEYS = {
    "secret",
    "key",
    "token",
    "authorization",
    "auth",
    "password",
    "signature",
    "credential",
    "bank_account",
    "card",
    "cvv",
    "reference",
}

# Provider identifier for real Razorpay executions.
_PROVIDER_RAZORPAY = "razorpay"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _build_idempotency_key(payment_id: int, action: str) -> str:
    return f"exec:{payment_id}:{action}"


def _check_duplicate(
    db: Session,
    payment_id: int,
    action: str,
) -> Optional[RecoveryExecution]:
    """Check if an equivalent execution already exists within the idempotency window."""
    key = _build_idempotency_key(payment_id, action)
    recent = (
        db.query(RecoveryExecution)
        .filter(
            RecoveryExecution.idempotency_key == key,
            RecoveryExecution.status.in_([SIMULATED, SUCCESS, BLOCKED]),
        )
        .order_by(RecoveryExecution.id.desc())
        .first()
    )
    if recent is None:
        return None

    # Check if within idempotency window
    if recent.completed_at:
        elapsed = (_now() - recent.completed_at).total_seconds() / 3600.0
        if elapsed < _IDEMPOTENCY_WINDOW_HOURS:
            return recent

    return None


def _persist_execution(
    db: Session,
    payment: Payment,
    action: str,
    execution_mode: str,
    status: str,
    firewall_approved: bool,
    firewall_decision: str,
    firewall_reason: str,
    firewall_policy_version: str,
    idempotency_key: str,
    simulated: bool = True,
    result_message: str = "",
    error: str = "",
    provider: str = "",
    provider_reference_id: str = "",
    provider_response: Optional[Dict[str, Any]] = None,
) -> RecoveryExecution:
    """Create and persist a RecoveryExecution audit record."""
    now = _now()
    execution = RecoveryExecution(
        payment_id=payment.id,
        action=action,
        status=status,
        idempotency_key=idempotency_key,
        firewall_decision=firewall_decision,
        firewall_reason=firewall_reason,
        firewall_policy_version=firewall_policy_version,
        execution_mode=execution_mode,
        simulated=simulated,
        result_message=result_message,
        error=error if error else None,
        provider=provider or None,
        provider_reference_id=provider_reference_id or None,
        provider_response=provider_response or None,
        started_at=now,
        completed_at=now,
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    return execution


def _execution_to_dict(execution: RecoveryExecution) -> dict:
    """Serialize a RecoveryExecution record to a safe API response dict."""
    return {
        "id": execution.id,
        "payment_id": execution.payment_id,
        "action": execution.action,
        "execution_mode": execution.execution_mode,
        "status": execution.status,
        "simulated": execution.simulated,
        "result_message": execution.result_message,
        "firewall_approved": execution.firewall_decision == "APPROVED",
        "firewall_decision": execution.firewall_decision,
        "firewall_reason": execution.firewall_reason,
        "firewall_policy_version": execution.firewall_policy_version,
        "idempotency_key": execution.idempotency_key,
        "provider": execution.provider,
        "provider_reference_id": execution.provider_reference_id,
        "provider_response": execution.provider_response or {},
        "error": execution.error,
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
        "created_at": execution.created_at.isoformat() if execution.created_at else None,
    }


# ---------------------------------------------------------------------------
# Action simulation helpers (DRY_RUN only)
# ---------------------------------------------------------------------------


def _simulate_retry(payment: Payment) -> str:
    return (
        f"Payment retry simulated successfully for payment #{payment.id} "
        f"(amount: INR {payment.amount:.2f}). No real Razorpay order created."
    )


def _simulate_payment_link(payment: Payment) -> str:
    return (
        f"Payment link generation simulated for payment #{payment.id} "
        f"(amount: INR {payment.amount:.2f}). No real Razorpay link created."
    )


def _resolve_reminder_channel(payment: Payment) -> str:
    """Deterministically resolve the reminder delivery channel for a payment.

    This step does NOT send anything and has no external notification provider.
    There are no customer contact fields on Payment today, so no real contact
    information exists to send to. A deterministic channel is chosen so the
    simulation is stable and auditable without fabricating contact details.
    """
    return DEFAULT_REMINDER_CHANNEL


def _simulate_reminder(payment: Payment) -> str:
    channel = _resolve_reminder_channel(payment)
    return (
        f"Customer reminder simulated for payment #{payment.id} via {channel}. "
        f"No real {channel} message was sent to any customer, and no external "
        f"notification provider was called."
    )


def _evaluate_stage_firewall(payment: Payment, action: str, now: datetime) -> Dict[str, Any]:
    """Evaluate the Action Firewall for a single HYBRID child strategy.

    The same authoritative firewall is used for each child so that per-stage
    safety rules (transaction limit, confidence, probability, retry limit,
    eligibility, and the RETRY/HYBRID cooldown) are never bypassed.
    """
    from app.services.action_firewall import ActionFirewall

    return ActionFirewall.evaluate(
        amount=payment.amount or 0.0,
        action=action,
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
        now=now,
    )


def _simulate_hybrid_steps(payment: Payment, now: Optional[datetime] = None) -> Dict[str, Any]:
    """Compute a deterministic DRY_RUN HYBRID step sequence.

    Simulates the controlled recovery sequence:

        HYBRID -> RETRY -> (recovered) STOP
                        -> (not recovered) PAYMENT_LINK -> (needs customer) REMINDER

    None of the stages actually touches Razorpay, sends a notification, or
    charges the customer. ``recovered`` flags are simulation heuristics only and
    never change the payment's persistence state.

    Returns a dict:
        {
          "steps": [ {action, status, reason, recovered, passed_firewall}, ... ],
          "status": "SUCCESS" | "SIMULATED" | "BLOCKED",
          "recovered": bool,
          "message": str,
        }
    """
    now = now or _now()
    steps: list[Dict[str, Any]] = []

    # Stage 1 — RETRY (always first)
    retry_fw = _evaluate_stage_firewall(payment, "RETRY", now)
    if not retry_fw["approved"]:
        # RETRY is blocked (e.g. cooldown / maximum retry reached). The hybrid
        # sequence safely stops — we never attempt another recovery stage that
        # would effectively retry shortly after the last one.
        steps.append(
            {
                "action": "RETRY",
                "status": "BLOCKED",
                "recovered": False,
                "passed_firewall": False,
                "reason": retry_fw["reason"],
            }
        )
        return {
            "steps": steps,
            "status": "BLOCKED",
            "recovered": False,
            "message": (
                f"Hybrid recovery blocked for payment #{payment.id}: RETRY stage "
                f"rejected by the Action Firewall ({retry_fw['reason']}). No child "
                f"strategy was executed."
            ),
        }

    # Simulated RETRY outcome: a high recovery probability is treated (in
    # simulation only) as the retry recovering the payment, so we STOP here.
    prob = (
        payment.recovery_probability
        if payment.recovery_probability is not None
        else payment.recovery_score or 0.0
    )
    retry_recovered = prob > RETRY_RECOVERY_SIMULATION_THRESHOLD
    if retry_recovered:
        steps.append(
            {
                "action": "RETRY",
                "status": "SUCCESS",
                "recovered": True,
                "passed_firewall": True,
                "reason": (
                    f"Simulated retry recovers payment #{payment.id} "
                    f"(recovery probability {prob:.2f} >= "
                    f"{RETRY_RECOVERY_SIMULATION_THRESHOLD:.2f})."
                ),
            }
        )
        return {
            "steps": steps,
            "status": "SUCCESS",
            "recovered": True,
            "message": (
                f"Hybrid recovery simulated for payment #{payment.id}. "
                f"Stage RETRY simulated as recovered: no further strategy needed. "
                f"No real Razorpay retry or payment link was created."
            ),
        }

    steps.append(
        {
            "action": "RETRY",
            "status": "SIMULATED",
            "recovered": False,
            "passed_firewall": True,
            "reason": (
                f"Simulated retry for payment #{payment.id} did not recover the "
                f"payment (recovery probability {prob:.2f})."
            ),
        }
    )

    # Stage 2 — PAYMENT_LINK (fallback when retry did not recover)
    link_fw = _evaluate_stage_firewall(payment, "PAYMENT_LINK", now)
    if not link_fw["approved"]:
        steps.append(
            {
                "action": "PAYMENT_LINK",
                "status": "BLOCKED",
                "recovered": False,
                "passed_firewall": False,
                "reason": link_fw["reason"],
            }
        )
    elif not payment.payment_method:
        # No payment instrument on file, so a payment link cannot be used yet.
        steps.append(
            {
                "action": "PAYMENT_LINK",
                "status": "SKIPPED",
                "recovered": False,
                "passed_firewall": True,
                "reason": (
                    "No payment instrument available to create a payment link; "
                    "the link would require customer action to pay."
                ),
            }
        )
    else:
        # A payment link would be created, but in simulation it requires the
        # customer to complete a new payment, so it does not complete recovery.
        steps.append(
            {
                "action": "PAYMENT_LINK",
                "status": "SIMULATED",
                "recovered": False,
                "passed_firewall": True,
                "reason": (
                    "Simulated payment link created; requires customer action to "
                    "complete payment. No real Razorpay link was created."
                ),
            }
        )

    # Stage 3 — REMINDER (fallback when the link requires customer action)
    rem_fw = _evaluate_stage_firewall(payment, "REMINDER", now)
    if not rem_fw["approved"]:
        steps.append(
            {
                "action": "REMINDER",
                "status": "BLOCKED",
                "recovered": False,
                "passed_firewall": False,
                "reason": rem_fw["reason"],
            }
        )
    else:
        steps.append(
            {
                "action": "REMINDER",
                "status": "SIMULATED",
                "recovered": False,
                "passed_firewall": True,
                "reason": (
                    "Simulated reminder; no real SMS/WhatsApp/email was sent to "
                    "any customer."
                ),
            }
        )

    step_labels = ", ".join(
        f"{_hybrid_step_label(st['action'])}({st['status']})" for st in steps
    )
    return {
        "steps": steps,
        "status": "SIMULATED",
        "recovered": False,
        "message": (
            f"Hybrid recovery simulated for payment #{payment.id}: "
            f"{step_labels}. "
            f"No real Razorpay retry, payment link, or customer notification "
            f"occurred."
        ),
    }


def _hybrid_step_label(action: str) -> str:
    """Human-readable label for a HYBRID child strategy in result messages."""
    return {"RETRY": "retry", "PAYMENT_LINK": "payment link", "REMINDER": "reminder"}.get(
        action, action.lower()
    )


def _simulate_hybrid(payment: Payment) -> str:
    """DRY_RUN HYBRID simulation summary (kept for compatibility)."""
    return _simulate_hybrid_steps(payment)["message"]


_SIMULATION_HANDLERS = {
    "RETRY": _simulate_retry,
    "PAYMENT_LINK": _simulate_payment_link,
    "REMINDER": _simulate_reminder,
    "HYBRID": _simulate_hybrid,
}


# ---------------------------------------------------------------------------
# Real (LIVE) execution helpers — RETRY and PAYMENT_LINK
# ---------------------------------------------------------------------------


def _sanitise_provider_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """Return a safe subset of a Razorpay response, dropping any sensitive keys.

    Only a small allow-list of public order/payment/link fields is kept. Raw
    credentials, IDs that include secrets, and SDK internals are never stored.
    """
    allowed = {
        "id",
        "amount",
        "amount_paid",
        "amount_due",
        "currency",
        "receipt",
        "status",
        "attempts",
        "created_at",
        "entity",
        "payment_capture",
        "notes",
        "short_url",
        "reference_id",
        "accept_partial",
        "description",
        "reminder_enable",
    }
    safe: Dict[str, Any] = {}
    for key, value in response.items() if isinstance(response, dict) else []:
        low = str(key).lower()
        if low in _SENSITIVE_KEYS:
            continue
        if low in allowed:
            safe[key] = value
    return safe


def _execute_retry_live(payment: Payment) -> Dict[str, Any]:
    """Execute a real Razorpay TEST/SANDBOX RETRY for a failed payment.

    A failed Razorpay Payment (id ``pay_xxx``) is in a final ``failed`` state
    and CANNOT be re-charged with that same payment id. The documented Razorpay
    recovery mechanism for a retry is to create a NEW Order (auto-capture) for
    the same amount, which lets the customer attempt a fresh payment. This
    function creates that new Order.

    Creating an Order does NOT charge the customer — no payment is made until
    the customer completes a new checkout against the returned ``order_id``.
    ``SUCCESS`` here means the retry order was created by Razorpay, NOT that
    the money was received. The payment itself is never marked recovered.

    This function MUST only be reached when the Action Firewall approved AND an
    operator explicitly disabled DRY_RUN.
    """
    from app.services.razorpay_service import create_order

    logger.info("Recovery RETRY started for payment %d", payment.id)
    receipt = f"recovery-{payment.id}"
    order = create_order(amount_in_inr=payment.amount, receipt=receipt)

    order_id = order.get("id") if isinstance(order, dict) else None
    if not order_id:
        raise ValueError("Razorpay returned an invalid order for the RETRY attempt.")

    return {
        "provider": _PROVIDER_RAZORPAY,
        "provider_reference_id": order_id,
        "provider_response": _sanitise_provider_response(order),
        "result_message": (
            f"Recovery RETRY executed for payment #{payment.id}: created a fresh "
            f"Razorpay order {order_id} for INR {payment.amount:.2f}. "
            f"No customer was charged; payment will only complete when a new "
            f"checkout is finished against this order."
        ),
    }


def _execute_payment_link_live(payment: Payment) -> Dict[str, Any]:
    """Execute a real Razorpay TEST/SANDBOX PAYMENT_LINK for a failed payment.

    Creates a hosted Razorpay payment link for the outstanding amount. Creating
    a payment link does NOT charge the customer — it only generates a shareable
    URL the customer can use to pay later. ``SUCCESS`` here means the link was
    created by Razorpay, NOT that money was received. The payment is never
    marked recovered.

    This function MUST only be reached when the Action Firewall approved AND an
    operator explicitly disabled DRY_RUN.
    """
    from app.services.razorpay_service import create_payment_link

    logger.info("Recovery PAYMENT_LINK started for payment %d", payment.id)
    receipt = f"recovery-link-{payment.id}"
    link = create_payment_link(
        amount_in_inr=payment.amount,
        receipt=receipt,
        description=(
            f"Recover payment #{payment.id} - update payment method to complete"
        ),
    )

    link_id = link.get("id") if isinstance(link, dict) else None
    if not link_id:
        raise ValueError("Razorpay returned an invalid payment link for the retry attempt.")

    return {
        "provider": _PROVIDER_RAZORPAY,
        "provider_reference_id": link_id,
        "provider_response": _sanitise_provider_response(link),
        "result_message": (
            f"Recovery PAYMENT_LINK executed for payment #{payment.id}: created a "
            f"hosted Razorpay payment link for INR {payment.amount:.2f}. "
            f"No customer was charged; payment will only complete when the "
            f"customer completes checkout against this link."
        ),
    }


# Actions with a real (LIVE) path and their executor. Only reachable after the
# Action Firewall approves AND the operator explicitly disabled DRY_RUN.
_LIVE_HANDLERS = {
    "RETRY": _execute_retry_live,
    "PAYMENT_LINK": _execute_payment_link_live,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def execute_recovery_action(
    *,
    payment: Payment,
    action: Optional[str] = None,
    execution_mode: str = DRY_RUN,
    db: Session,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Execute (or simulate) an approved recovery action for a payment.

    This is the single entry point for the Recovery Execution Engine.
    It MUST NOT be called unless the Action Firewall has approved the action.

    Parameters:
        payment: The Payment ORM instance.
        action: The recovery action to execute (defaults to payment.recommended_action).
        execution_mode: DRY_RUN (default/safe) or LIVE (real RETRY, only when
                        RECOVERY_DRY_RUN is explicitly disabled).
        db: Database session.

    Returns:
        A structured dict with execution status and details.

    Raises:
        ValueError: Payment not found, no AI decision, unsupported action, or
                    execution mode is not allowed / is blocked by DRY_RUN.
    """
    now = now or _now()

    # --- Validate inputs --------------------------------------------------
    if payment is None:
        raise ValueError("Payment not found.")

    action = (action or payment.recommended_action or "").strip().upper()
    if not action:
        raise ValueError(
            "No recovery action specified and no AI decision exists for this payment."
        )
    if action not in SUPPORTED_ACTIONS:
        raise ValueError(
            f"Unsupported recovery action '{action}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_ACTIONS))}."
        )

    # --- Resolve execution mode -------------------------------------------
    # DRY_RUN is the SAFE default and is enforced by the global switch
    # RECOVERY_DRY_RUN (default TRUE). While DRY_RUN is enabled the engine can
    # never reach a real Razorpay call, no matter what mode a caller requests.
    requested_mode = (execution_mode or DRY_RUN).strip().upper()
    if requested_mode not in (DRY_RUN, LIVE):
        raise ValueError(
            f"Execution mode '{execution_mode}' is not supported. "
            f"Supported modes: {DRY_RUN}, {LIVE}."
        )

    if recovery_dry_run_enabled():
        # Safety switch ON (default): only DRY_RUN is ever permitted. A caller
        # asking for LIVE is refused safely; Razorpay is never contacted.
        if requested_mode != DRY_RUN:
            raise ValueError(
                f"Execution mode '{requested_mode}' is not supported. "
                f"RECOVERY_DRY_RUN is enabled; only DRY_RUN is currently permitted."
            )
        effective_mode = DRY_RUN
    else:
        # Operator explicitly disabled DRY_RUN (TEST/SANDBOX only). Only RETRY
        # has a real path; every other action stays DRY_RUN for safety.
        if requested_mode == LIVE:
            if action not in _LIVE_SUPPORTED_ACTIONS:
                raise ValueError(
                    f"Execution mode 'LIVE' is not supported for action '{action}'. "
                    f"Only {', '.join(sorted(_LIVE_SUPPORTED_ACTIONS))} has a real path."
                )
            effective_mode = LIVE
        else:
            effective_mode = DRY_RUN

    # --- Idempotency check ------------------------------------------------
    idempotency_key = _build_idempotency_key(payment.id, action)
    duplicate = _check_duplicate(db, payment.id, action)
    if duplicate is not None:
        result = _execution_to_dict(duplicate)
        result["executed"] = False
        result["status"] = "ALREADY_EXECUTED"
        result["duplicate_of"] = duplicate.id
        return result

    # --- Firewall gate (MANDATORY - never bypassed) -----------------------
    firewall = ActionFirewall.evaluate(
        amount=payment.amount or 0.0,
        action=action,
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
        now=now,
    )

    if not firewall["approved"]:
        execution = _persist_execution(
            db=db,
            payment=payment,
            action=action,
            execution_mode=effective_mode,
            status=BLOCKED,
            firewall_approved=False,
            firewall_decision="BLOCKED",
            firewall_reason=firewall["reason"],
            firewall_policy_version=firewall["policy_version"],
            idempotency_key=idempotency_key,
            simulated=False,
            result_message=f"Action blocked by Action Firewall: {firewall['reason']}",
        )
        result = _execution_to_dict(execution)
        result["executed"] = False
        return result

    # --- LIVE: real Razorpay TEST/SANDBOX execution ------------------------
    if effective_mode == LIVE:
        live_executor = _LIVE_HANDLERS.get(action)
        try:
            live_result = live_executor(payment)
        except ValueError as exc:
            # Safe application-level failure; no secrets or stack traces.
            execution = _persist_execution(
                db=db,
                payment=payment,
                action=action,
                execution_mode=effective_mode,
                status=FAILED,
                firewall_approved=True,
                firewall_decision="APPROVED",
                firewall_reason=firewall["reason"],
                firewall_policy_version=firewall["policy_version"],
                idempotency_key=idempotency_key,
                simulated=False,
                result_message="Recovery %s failed for payment %d" % (action, payment.id),
                error=str(exc),
            )
            logger.warning("Recovery %s failed for payment %d: %s", action, payment.id, exc)
            result = _execution_to_dict(execution)
            result["executed"] = False
            return result
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Recovery %s failed for payment %d", action, payment.id)
            execution = _persist_execution(
                db=db,
                payment=payment,
                action=action,
                execution_mode=effective_mode,
                status=FAILED,
                firewall_approved=True,
                firewall_decision="APPROVED",
                firewall_reason=firewall["reason"],
                firewall_policy_version=firewall["policy_version"],
                idempotency_key=idempotency_key,
                simulated=False,
                result_message="Recovery %s failed for payment %d" % (action, payment.id),
                error="Razorpay recovery execution failed internally.",
            )
            result = _execution_to_dict(execution)
            result["executed"] = False
            return result

        # Successfully created the provider resource (order OR payment link).
        # Persist the execution and update local payment state safely. The
        # payment is NOT marked recovered (money was not received); only the
        # recovery attempt is recorded.
        execution = _persist_execution(
            db=db,
            payment=payment,
            action=action,
            execution_mode=effective_mode,
            status=SUCCESS,
            firewall_approved=True,
            firewall_decision="APPROVED",
            firewall_reason=firewall["reason"],
            firewall_policy_version=firewall["policy_version"],
            idempotency_key=idempotency_key,
            simulated=False,
            result_message=live_result["result_message"],
            provider=live_result.get("provider"),
            provider_reference_id=live_result.get("provider_reference_id"),
            provider_response=live_result.get("provider_response"),
        )

        # Safe local state update: record the provider reference and the
        # recovery attempt, but never mark the payment as captured/recovered.
        payment.razorpay_order_id = live_result.get("provider_reference_id")
        payment.retry_count = (payment.retry_count or 0) + 1
        payment.last_recovery_attempt_at = _now()
        payment.recovery_status = (
            payment.recovery_status
            if payment.recovery_status
            else "PENDING"
        )
        db.commit()
        db.refresh(payment)

        result = _execution_to_dict(execution)
        result["executed"] = True
        return result

    # --- DRY_RUN: simulate the action -------------------------------------
    simulate_fn = _SIMULATION_HANDLERS.get(action)
    if simulate_fn is None:
        raise ValueError(f"No simulation handler for action '{action}'.")

    message = simulate_fn(payment)

    hybrid_steps = None
    hybrid_status = None
    if action == "HYBRID":
        # HYBRID is DRY_RUN-only in this step. Delegate to the structured
        # orchestrator so the result exposes the deterministic per-stage
        # sequence (RETRY -> PAYMENT_LINK -> REMINDER) for auditing.
        hybrid = _simulate_hybrid_steps(payment)
        message = hybrid["message"]
        hybrid_steps = hybrid["steps"]
        hybrid_status = hybrid["status"]

    provider_response = None
    if hybrid_steps is not None:
        provider_response = {
            "steps": hybrid_steps,
            "recovered": False,
        }

    execution = _persist_execution(
        db=db,
        payment=payment,
        action=action,
        execution_mode=effective_mode,
        status=(SUCCESS if hybrid_status == "SUCCESS" else SIMULATED),
        firewall_approved=True,
        firewall_decision="APPROVED",
        firewall_reason=firewall["reason"],
        firewall_policy_version=firewall["policy_version"],
        idempotency_key=idempotency_key,
        simulated=True,
        result_message=message,
        provider_response=provider_response,
    )

    result = _execution_to_dict(execution)
    result["executed"] = True
    if hybrid_steps is not None:
        result["steps"] = hybrid_steps
        result["recovered"] = False
    return result
