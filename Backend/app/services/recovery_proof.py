"""Cryptographic proofs for provider-confirmed recovery executions."""

import hashlib
import json
from datetime import datetime
from typing import Any


def build_proof_payload(
    *,
    transaction_id: str,
    razorpay_payment_id: str | None,
    action: str,
    recovery_timestamp: datetime,
    recovered_amount: float,
    ai_confidence: float | None,
    policy_version: str | None,
    firewall_decision: str | None,
    execution_id: int,
) -> dict[str, Any]:
    """Build the versioned, deterministic data covered by the proof hash."""
    return {
        "version": 1,
        "transaction_id": transaction_id,
        "razorpay_payment_id": razorpay_payment_id,
        "recovery_action": action,
        "recovery_timestamp": recovery_timestamp.isoformat(),
        "recovered_amount": recovered_amount,
        "ai_confidence": ai_confidence,
        "policy_version": policy_version,
        "firewall_decision": firewall_decision,
        "execution_id": execution_id,
    }


def canonical_json(payload: dict[str, Any]) -> str:
    """Serialize proof data in one stable representation."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def hash_proof(payload: dict[str, Any]) -> str:
    """Return a SHA-256 digest for canonical recovery data."""
    digest = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def verify_proof(payload: dict[str, Any], proof_hash: str | None) -> bool:
    """Verify a locally stored proof without claiming blockchain settlement."""
    return bool(proof_hash) and hash_proof(payload) == proof_hash