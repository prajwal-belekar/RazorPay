from sqlalchemy import Boolean, Column, Integer, String, Float, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)

    amount = Column(Float, nullable=False)

    failure_reason = Column(String, nullable=False)

    customer_type = Column(String, nullable=False)

    recommended_action = Column(String, nullable=True)

    reason = Column(String, nullable=True)

    confidence = Column(Float, nullable=True)

    decision_source = Column(String, nullable=True)

    recovery_status = Column(String, nullable=True)

    retry_count = Column(Integer, default=0)

    # Razorpay integration fields (nullable to preserve existing records)
    razorpay_payment_id = Column(String, nullable=True, index=True)

    razorpay_order_id = Column(String, nullable=True, index=True)

    razorpay_signature = Column(String, nullable=True)

    payment_status = Column(String, nullable=True)

    error_code = Column(String, nullable=True)

    gateway = Column(String, nullable=True)

    webhook_received_at = Column(DateTime(timezone=True), nullable=True)

    # Recovery-engine fields (nullable to preserve existing records)
    recovery_score = Column(Float, nullable=True)

    payment_method = Column(String, nullable=True)

    payment_timestamp = Column(DateTime(timezone=True), nullable=True)

    previous_recovery_attempts = Column(Integer, default=0, nullable=True)

    # Action Firewall / Merchant Governance Guard fields (nullable to
    # preserve existing records). Stores the outcome of the policy layer that
    # sits between the AI recommendation and any action execution.
    firewall_decision = Column(String, nullable=True)

    firewall_reason = Column(Text, nullable=True)

    firewall_policy_version = Column(String, nullable=True)

    firewall_checks = Column(JSON, nullable=True)

    firewall_evaluated_at = Column(DateTime(timezone=True), nullable=True)

    firewall_approved = Column(Boolean, nullable=True)

    firewall_checked_at = Column(DateTime(timezone=True), nullable=True)

    # When the last recovery action was actually executed for this payment.
    # Drives the firewall cooldown (we refuse to re-attempt too soon).
    last_recovery_attempt_at = Column(DateTime(timezone=True), nullable=True)

    # AI Recovery Decision Engine output fields (nullable to preserve existing records).
    # Populated by POST /api/recovery/analyze/{payment_id}.
    recovery_probability = Column(Float, nullable=True)   # 0-1 probability estimate
    expected_recovery = Column(Float, nullable=True)       # amount × probability, in INR
    risk_level = Column(String, nullable=True)             # LOW / MEDIUM / HIGH
    ai_decision_at = Column(DateTime(timezone=True), nullable=True)  # last decision timestamp

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

class RecoveryExecution(Base):
    """Audit persisted for every executed recovery action.

    One row per action execution attempt. ``idempotency_key`` is unique and
    deterministic so a retried request can never execute the same action
    twice. ``status`` follows the lifecycle:

        PENDING -> EXECUTING -> SUCCESS / FAILED / BLOCKED / HUMAN_REVIEW

    ``SUCCESS`` is only ever set when the payment provider confirms the
    action (e.g. a payment link was created). ``provider_response`` is a
    sanitised copy - never raw credentials.
    """

    __tablename__ = "recovery_executions"

    id = Column(Integer, primary_key=True, index=True)

    payment_id = Column(Integer, ForeignKey("payments.id"), index=True, nullable=False)

    action = Column(String, nullable=False)

    status = Column(String, nullable=False)

    firewall_decision = Column(String, nullable=True)

    firewall_reason = Column(Text, nullable=True)

    firewall_policy_version = Column(String, nullable=True)

    idempotency_key = Column(String, unique=True, index=True, nullable=False)

    provider = Column(String, nullable=True)

    provider_reference_id = Column(String, nullable=True)

    provider_response = Column(JSON, nullable=True)

    error = Column(Text, nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)

    completed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Local proof fields; chain fields remain NULL until a real integration confirms them.
    proof_payload = Column(JSON, nullable=True)

    proof_hash = Column(String, nullable=True, index=True)

    proof_status = Column(String, nullable=True)

    chain_tx_hash = Column(String, nullable=True)

    chain_block_number = Column(Integer, nullable=True)

    chain_network = Column(String, nullable=True)


class RazorpayWebhook(Base):
    """Audit / event store for every verified Razorpay webhook.

    Used for idempotency (unique ``dedup_key``), debugging, and replay
    safety. ``dedup_key`` deterministically identifies one logical Razorpay
    event so the same webhook delivered multiple times never creates
    duplicate Payment records or duplicate downstream actions.
    """

    __tablename__ = "razorpay_webhooks"

    id = Column(Integer, primary_key=True, index=True)

    # Deterministic idempotency key: "event_type:payment_or_order_id:created_at"
    dedup_key = Column(String, unique=True, index=True, nullable=False)

    event_type = Column(String, index=True)

    razorpay_payment_id = Column(String, index=True)

    razorpay_order_id = Column(String, index=True)

    amount = Column(Float)

    currency = Column(String)

    payment_status = Column(String)

    method = Column(String)

    failure_reason = Column(String)

    event_timestamp = Column(DateTime(timezone=True))

    # Sanitised copy of the raw payload (no secrets are stored).
    payload = Column(Text)

    # Whether the event was successfully processed (as opposed to ignored).
    processed = Column(Boolean, default=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class FirewallAuditLog(Base):
    """Audit record for every evaluation of the AI Action Firewall.

    Records the policy decision without storing any secrets or credentials.
    """

    __tablename__ = "firewall_audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    payment_id = Column(Integer, ForeignKey("payments.id"), index=True, nullable=False)

    recommended_action = Column(String, nullable=False)

    approved = Column(Boolean, nullable=False)

    risk_level = Column(String, nullable=True)

    policy_version = Column(String, nullable=False)

    reason = Column(Text, nullable=False)

    checks = Column(JSON, nullable=True)

    evaluation_timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )