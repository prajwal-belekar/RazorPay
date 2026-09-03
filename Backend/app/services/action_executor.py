"""Recovery Action Executor.

Executes a recovery action (RETRY / PAYMENT_LINK / REMINDER / HYBRID) for a
failed payment, ALWAYS gated by the AI Action Firewall, with idempotency and
an honest, auditable lifecycle.

Guarantees:
  - Every action passes through :func:`evaluate_policy` at execution time.
    If the firewall does not return ``APPROVED`` the action is refused and
    recorded as ``BLOCKED`` / ``HUMAN_REVIEW`` - never executed.
  - Idempotent: each (payment, action, attempt) has a unique
    ``idempotency_key`` so a duplicate request can never execute twice.
  - ``SUCCESS`` is only ever recorded when the payment provider actually
    confirms the action (e.g. a payment link or fresh order was created).
    Provider failures and missing Razorpay TEST credentials always become
    ``FAILED`` - never a faked success.
  - No secrets are persisted; provider responses are stored sanitised.

Lifecycle of an execution record:
    PENDING -> EXECUTING -> SUCCESS / FAILED / BLOCKED / HUMAN_REVIEW
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Payment, RecoveryExecution
from app.services.action_firewall import evaluate_policy
from app.services.recovery_proof import build_proof_payload, hash_proof
from app.services import razorpay_service

logger = logging.getLogger(__name__)

# ActionExecutor statuses (mirror the Payment recovery_status markers).
PENDING = "PENDING"
EXECUTING = "EXECUTING"
SUCCESS = "SUCCESS"
FAILED = "FAILED"
BLOCKED = "BLOCKED"
HUMAN_REVIEW = "HUMAN_REVIEW"

# Execution terminal statuses - nothing may run again on an existing record.
TERMINAL = {SUCCESS, FAILED, BLOCKED, HUMAN_REVIEW}

# Strategy lives on Payment.recommended_action / execution.action.
SUPPORTED_ACTIONS = {"RETRY", "PAYMENT_LINK", "REMINDER", "HYBRID"}

# Number of provider "legs" each hybrid action composes.
# HYBRID = RETRY (fresh order) followed by a PAYMENT_LINK fallback.
_HYBRID_LEGS = ("RETRY", "PAYMENT_LINK")

# Public additions to the exec response so the dashboard can act on a link.
_LINK_KEYS = ("id", "short_url", "status", "amount", "currency")

_NOT_CONFIGURED_HINT = (
    "Razorpay TEST credentials are not configured. "
    "Set real RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET in Backend/.env."
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------
# Provider adapters
# --------------------------------------------------------------------------
# These thin wrappers isolate every Razorpay SDK call so the executor is
# unit-testable without real credentials and so no SDK call is ever made
# outside these functions. They are monkeypatched in the test suite.


def _provider_create_order(amount_inr: float, receipt: str):
    """Create a fresh Razorpay order (the supported RETRY mechanism)."""
    return razorpay_service.create_order(amount_in_inr=amount_inr, receipt=receipt)


def _provider_create_payment_link(amount_inr: float, receipt: str):
    """Create a Razorpay payment link (the supported PAYMENT_LINK mechanism)."""
    return razorpay_service.create_payment_link(
        amount_in_inr=amount_inr,
        receipt=receipt,
        description="RecoverAI recovery payment",
    )


# Dispatch table: action -> provider function that performs the supported
# provider operation. REMINDER intentionally has no provider (no messaging
# service is configured), so it resolves to None.
_PROVIDER_FUNCS = {
    "RETRY": _provider_create_order,
    "PAYMENT_LINK": _provider_create_payment_link,
}


# --------------------------------------------------------------------------
# Sanitisation
# --------------------------------------------------------------------------


def sanitize_link_response(response: dict) -> dict:
    """Return a public-safe subset of a provider payment-link/order response."""
    if not isinstance(response, dict):
        return {}
    return {k: response.get(k) for k in _LINK_KEYS if k in response}


def _sanitize_error(exc: Exception) -> str:
    """Return a short, secret-free error description."""
    msg = getattr(exc, "message", None) or str(exc)
    return (msg or "Unknown provider error.")[:500]


# --------------------------------------------------------------------------
# Execution record helpers
# --------------------------------------------------------------------------


def _build_idempotency_key(payment: Payment, action: str) -> str:
    """Deterministic key preventing duplicate execution of the same action.

    Key is based on payment + action only (per spec), not on attempt number,
    so that re-executing the same request payload is always detected as a
    duplicate regardless of the current attempt counter state.
    """
    return f"recovery:{payment.id}:{action}"


# --------------------------------------------------------------------------
# Core executor
# --------------------------------------------------------------------------


def _new_execution(
    db: Session,
    payment: Payment,
    action: str,
    status: str,
    idempotency_key: str,
    firewall: dict,
    **fields,
) -> RecoveryExecution:
    """Persist a new execution record (only on the PENDING/block paths)."""
    execution = RecoveryExecution(
        payment_id=payment.id,
        action=action,
        status=status,
        idempotency_key=idempotency_key,
        firewall_decision=firewall.get("decision"),
        firewall_reason=firewall.get("reason"),
        firewall_policy_version=firewall.get("policy_version"),
        provider="razorpay",
        **fields,
    )
    db.add(execution)
    db.flush()
    return execution


def _gate(
    db: Session,
    payment: Payment,
    action: str,
    now: datetime,
    **overrides,
):
    """Run the Action Firewall gate.

    Returns 2-tuple (decision: str, firewall: dict). Refuses execution unless
    the decision is ``APPROVED``. This is the single source of truth for
    whether an action may proceed - the executor never executes without it.

    Naive datetimes (returned by some DBs such as SQLite in tests) are
    normalised to UTC before the firewall compares them against ``now``.
    """

    def to_utc(value):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    firewall = evaluate_policy(
        amount=payment.amount or 0.0,
        confidence=payment.confidence,
        retry_count=payment.retry_count or 0,
        previous_recovery_attempts=payment.previous_recovery_attempts or 0,
        payment_status=payment.payment_status,
        recovery_status=payment.recovery_status,
        payment_timestamp=to_utc(payment.payment_timestamp),
        webhook_received_at=to_utc(payment.webhook_received_at),
        last_recovery_attempt_at=to_utc(payment.last_recovery_attempt_at),
        gateway=payment.gateway or "razorpay",
        now=now.astimezone(timezone.utc) if now.tzinfo else now,
        **overrides,
    )
    return firewall.get("decision"), firewall


def execute_recovery_action(
    payment_id: int,
    action: str,
    db: Session,
    now: datetime | None = None,
) -> dict:
    """Execute (or refuse) a recovery action for a payment.

    Returns a dict serialisation of the resulting ``RecoveryExecution`` plus
    an ``outcome`` marker for the caller.

    Raises:
        ValueError: unknown payment id or unsupported action.
    """
    now = now or _now()

    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if payment is None:
        raise ValueError(f"Payment {payment_id} not found.")

    action = (action or payment.recommended_action or "REMINDER").upper()
    if action not in SUPPORTED_ACTIONS:
        raise ValueError(f"Unsupported recovery action: {action}")

    # Order of checks matters: idempotency first (cheap, no side effects),
    # then the firewall gate (never bypassed).
    idempotency_key = _build_idempotency_key(payment, action)

    existing = (
        db.query(RecoveryExecution)
        .filter(RecoveryExecution.idempotency_key == idempotency_key)
        .first()
    )
    if existing is not None:
        return {
            **_execution_to_dict(existing),
            "outcome": "DUPLICATE",
            "duplicate_of": existing.id,
        }

    # --- Firewall gate (never bypassed) -------------------------------
    decision, firewall = _gate(db, payment, action, now)

    if decision != "APPROVED":
        status = HUMAN_REVIEW if decision == "HUMAN_REVIEW" else BLOCKED
        execution = _new_execution(
            db, payment, action, status, idempotency_key, firewall,
            started_at=now,
            completed_at=now,
            error=firewall.get("reason"),
        )
        db.commit()
        return {**_execution_to_dict(execution), "outcome": status}

    # --- Approved - begin execution -----------------------------------
    execution = _new_execution(
        db, payment, action, EXECUTING, idempotency_key, firewall,
        started_at=now,
    )
    db.commit()

    try:
        _execute_approved(execution, payment, action, db)
    except razorpay_service.RazorpayNotConfigured as exc:
        _fail(db, payment, execution, exc, hint=_NOT_CONFIGURED_HINT)
    except Exception as exc:  # noqa: BLE001 - normalised into FAILED
        logger.exception("Recovery action %s failed for payment %s", action, payment.id)
        _fail(db, payment, execution, exc)
        db.commit()
        return {**_execution_to_dict(execution), "outcome": FAILED}

    # _execute_approved persists terminal SUCCESS already; here we only emit.
    return {**_execution_to_dict(execution), "outcome": execution.status}


def _execute_approved(
    execution: RecoveryExecution,
    payment: Payment,
    action: str,
    db: Session,
) -> None:
    """Run the approved strategy against the provider.

    Only sets ``SUCCESS`` when the provider confirms the operation.
    Raises on provider failure so the caller can record ``FAILED``.
    """
    if action == "REMINDER":
        # No messaging provider is configured. Record as PENDING rather than
        # pretending WhatsApp/SMS was sent - truthful about the limitation.
        execution.status = PENDING
        execution.error = (
            "No messaging provider configured; reminder left pending."
        )
        db.commit()
        _mark_payment_status(db, payment, execution)
        return

    if action == "HYBRID":
        _execute_hybrid(execution, payment, db)
        return

    # RETRY / PAYMENT_LINK
    provider = _PROVIDER_FUNCS[action]
    response = provider(payment.amount or 0.0, f"recovery-{payment.id}")
    _record_provider_success(db, execution, payment, response)


def _execute_hybrid(
    execution: RecoveryExecution,
    payment: Payment,
    db: Session,
) -> None:
    """Execute the approved HYBRID sequence: RETRY then a PAYMENT_LINK leg.

    Both legs must be confirmed by the provider for the hybrid to be a
    success. Any provider failure raises and fails the whole execution.
    """
    results = {}
    for leg in _HYBRID_LEGS:
        provider = _PROVIDER_FUNCS[leg]
        response = provider(payment.amount or 0.0, f"recovery-{payment.id}")
        results[leg] = sanitize_link_response(response)

    execution.provider_response = results
    execution.provider_reference_id = ";".join(
        (_dict_ref(r) for r in results.values() if _dict_ref(r))
    ) or None
    execution.status = SUCCESS
    execution.completed_at = _now()
    _create_local_proof(db, payment, execution)
    db.commit()
    _touch_payment(db, payment, execution)


def _dict_ref(response: dict):
    """Return a compact provider reference for a leg's response."""
    if isinstance(response, dict):
        return response.get("id")
    return None


def _record_provider_success(
    db: Session,
    execution: RecoveryExecution,
    payment: Payment,
    response,
) -> None:
    """Store a provider-confirmed success (SUCCESS) for RETRY/PAYMENT_LINK."""
    sanitized = sanitize_link_response(response or {})
    execution.provider_response = sanitized
    execution.provider_reference_id = (sanitized or {}).get("id")
    execution.status = SUCCESS
    execution.completed_at = _now()
    execution.error = None
    db.commit()
    _create_local_proof(db, payment, execution)
    _touch_payment(db, payment, execution)


def _create_local_proof(
    db: Session,
    payment: Payment,
    execution: RecoveryExecution,
) -> None:
    """Persist a local proof only after the provider reports SUCCESS."""
    timestamp = execution.completed_at or _now()
    payload = build_proof_payload(
        transaction_id=f"Payment #{payment.id}",
        razorpay_payment_id=payment.razorpay_payment_id,
        action=execution.action,
        recovery_timestamp=timestamp,
        recovered_amount=payment.amount or 0.0,
        ai_confidence=payment.confidence,
        policy_version=execution.firewall_policy_version,
        firewall_decision=execution.firewall_decision,
        execution_id=execution.id,
    )
    execution.proof_payload = payload
    execution.proof_hash = hash_proof(payload)
    execution.proof_status = "NOT_VERIFIED"
    db.commit()


def _touch_payment(
    db: Session,
    payment: Payment,
    execution: RecoveryExecution,
) -> None:
    """Record a real, provider-attempted execution on the Payment.

    Called only for SUCCESS / FAILED outcomes - i.e. an actual attempt was
    made. Consumes the retry budget and starts the cooldown so we never
    re-attempt too soon. PENDING/BLOCKED/HUMAN_REVIEW never consume retries.
    """
    payment.recovery_status = execution.status
    payment.previous_recovery_attempts = (payment.previous_recovery_attempts or 0) + 1
    payment.retry_count = (payment.retry_count or 0) + 1
    payment.last_recovery_attempt_at = _now()
    db.commit()


def _mark_payment_status(
    db: Session,
    payment: Payment,
    execution: RecoveryExecution,
) -> None:
    """Mirror a non-attempt status (e.g. PENDING) onto the Payment."""
    payment.recovery_status = execution.status
    db.commit()


def _fail(
    db: Session,
    payment: Payment,
    execution: RecoveryExecution,
    exc: Exception,
    hint: str | None = None,
) -> None:
    """Record an honest FAILED terminal state - never a fabricated success."""
    execution.status = FAILED
    execution.completed_at = _now()
    execution.error = hint or _sanitize_error(exc)
    db.commit()
    _touch_payment(db, payment, execution)


def _execution_to_dict(execution: RecoveryExecution) -> dict:
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
