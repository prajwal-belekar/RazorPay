"""Lightweight, non-destructive schema migrations.

Uses ``ALTER TABLE ... ADD COLUMN IF NOT EXISTS`` so existing PostgreSQL
rows are never touched or destroyed. New columns are added as NULLABLE
to remain backward compatible with records created before the integration.
"""

from sqlalchemy import text

from app.database import engine

# (column_name, sql_type) - must stay in sync with models.Payment
_PAYMENT_ADD_COLUMNS = [
    ("razorpay_payment_id", "VARCHAR"),
    ("razorpay_order_id", "VARCHAR"),
    ("razorpay_signature", "VARCHAR"),
    ("payment_status", "VARCHAR"),
    ("error_code", "VARCHAR"),
    ("gateway", "VARCHAR"),
    ("webhook_received_at", "TIMESTAMP WITH TIME ZONE"),
    ("recovery_score", "FLOAT"),
    ("payment_method", "VARCHAR"),
    ("payment_timestamp", "TIMESTAMP WITH TIME ZONE"),
    ("previous_recovery_attempts", "INTEGER"),
    ("firewall_decision", "VARCHAR"),
    ("firewall_reason", "TEXT"),
    ("firewall_policy_version", "VARCHAR"),
    ("firewall_checks", "JSON"),
    ("firewall_evaluated_at", "TIMESTAMP WITH TIME ZONE"),
    ("last_recovery_attempt_at", "TIMESTAMP WITH TIME ZONE"),
    ("recovery_probability", "FLOAT"),
    ("expected_recovery", "FLOAT"),
    ("risk_level", "VARCHAR"),
    ("ai_decision_at", "TIMESTAMP WITH TIME ZONE"),
    ("firewall_approved", "BOOLEAN"),
    ("firewall_checked_at", "TIMESTAMP WITH TIME ZONE"),
]

_EXECUTION_ADD_COLUMNS = [
    ("proof_payload", "JSON"),
    ("proof_hash", "VARCHAR"),
    ("proof_status", "VARCHAR"),
    ("chain_tx_hash", "VARCHAR"),
    ("chain_block_number", "INTEGER"),
    ("chain_network", "VARCHAR"),
]


def migrate():
    """Apply any missing nullable columns and tables."""
    from app.database import Base
    from app.models import FirewallAuditLog  # noqa: F401

    with engine.begin() as conn:
        for col_name, sql_type in _PAYMENT_ADD_COLUMNS:
            conn.execute(
                text(
                    f"ALTER TABLE payments "
                    f"ADD COLUMN IF NOT EXISTS {col_name} {sql_type} NULL"
                )
            )
        for col_name, sql_type in _EXECUTION_ADD_COLUMNS:
            conn.execute(
                text(
                    f"ALTER TABLE recovery_executions "
                    f"ADD COLUMN IF NOT EXISTS {col_name} {sql_type} NULL"
                )
            )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS firewall_audit_logs (
                    id SERIAL PRIMARY KEY,
                    payment_id INTEGER NOT NULL REFERENCES payments(id),
                    recommended_action VARCHAR NOT NULL,
                    approved BOOLEAN NOT NULL,
                    risk_level VARCHAR NULL,
                    policy_version VARCHAR NOT NULL,
                    reason TEXT NOT NULL,
                    checks JSON NULL,
                    evaluation_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )

