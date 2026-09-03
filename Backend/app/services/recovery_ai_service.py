"""RecoverAI AI Recovery Decision Engine.

Analyzes failed payments and produces structured recovery recommendations
using the configured local LLM (Ollama), with an offline-safe deterministic fallback.

Guarantees:
1. ONLY produces a recommendation; NEVER executes a recovery action.
2. Validates all AI outputs against strict schemas:
   - recommended_action must be one of: RETRY, PAYMENT_LINK, REMINDER, HYBRID
   - recovery_probability in [0.0, 1.0]
   - confidence in [0.0, 1.0]
   - expected_recovery <= amount and >= 0.0
   - risk_level in: LOW, MEDIUM, HIGH
3. Offline-safe: if Ollama is unreachable, misconfigured, or returns invalid
   data, falls back cleanly to the deterministic rule engine (RULE_ENGINE_FALLBACK).
4. No sensitive secrets or unverified input injection.
"""

from datetime import datetime, timezone
import json
import logging
import re
from typing import Any, Dict, Optional

import httpx
from pydantic import BaseModel, Field, field_validator

from app import config
from app.models import Payment
from app.services.recovery_engine import compute_recovery_score, recommend_strategy

logger = logging.getLogger(__name__)

ALLOWED_ACTIONS = ("RETRY", "PAYMENT_LINK", "REMINDER", "HYBRID")
ALLOWED_RISK_LEVELS = ("LOW", "MEDIUM", "HIGH")

SOURCE_OLLAMA = "OLLAMA"
SOURCE_FALLBACK = "RULE_ENGINE_FALLBACK"

_MAX_FIELD_LEN = 200
_TEXT_FIELD_NAMES = ("amount", "failure_reason", "error_code", "payment_method", "customer_type")


class RecoveryDecisionOutput(BaseModel):
    """Strictly-validated AI recovery recommendation contract."""

    recommended_action: str = Field(
        description="One of RETRY, PAYMENT_LINK, REMINDER, HYBRID"
    )
    recovery_probability: float = Field(
        ge=0.0, le=1.0, description="Estimated recovery probability between 0 and 1"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence score between 0 and 1"
    )
    expected_recovery: Optional[float] = Field(
        default=None, ge=0.0, description="Expected recovered amount in INR"
    )
    risk_level: str = Field(
        description="Risk level: LOW, MEDIUM, or HIGH"
    )
    reason: str = Field(
        min_length=5, max_length=600, description="Practical concise explanation"
    )

    @field_validator("recommended_action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        clean = (v or "").strip().upper()
        if clean not in ALLOWED_ACTIONS:
            raise ValueError(f"Invalid recommended_action '{v}'. Must be one of {ALLOWED_ACTIONS}")
        return clean

    @field_validator("risk_level")
    @classmethod
    def validate_risk(cls, v: str) -> str:
        clean = (v or "").strip().upper()
        if clean not in ALLOWED_RISK_LEVELS:
            raise ValueError(f"Invalid risk_level '{v}'. Must be one of {ALLOWED_RISK_LEVELS}")
        return clean


def _sanitize_field(name: Optional[str], value: Any) -> str:
    """Sanitize free-text fields before injecting into prompts."""
    if value is None:
        return "unknown"
    raw = str(value).strip()

    if name in _TEXT_FIELD_NAMES:
        raw = re.sub(r"[\r\n\t\x00-\x08\x0b\x0c\x0e-\x1f{}\"']", " ", raw)
        raw = re.sub(r"\s+", " ", raw).strip()
        raw = raw[:_MAX_FIELD_LEN] or "unknown"
    else:
        raw = raw[:_MAX_FIELD_LEN] or "0"

    return raw


def build_ai_prompt(
    amount: float,
    failure_reason: Optional[str],
    error_code: Optional[str],
    payment_method: Optional[str],
    customer_type: Optional[str],
    retry_count: int,
    previous_attempts: int,
    transaction_age_minutes: Optional[int],
) -> str:
    """Construct a rigorous prompt demanding structured JSON only."""
    return f"""You are RecoverAI, an autonomous payment recovery DECISION ENGINE for e-commerce and fintech.
Your role is solely to RECOMMEND the optimal recovery strategy for a failed transaction.
You NEVER execute or authorize real financial transactions.

Failed Payment Details:
- amount_inr: {_sanitize_field('amount', amount)}
- failure_reason: {_sanitize_field('failure_reason', failure_reason)}
- error_code: {_sanitize_field('error_code', error_code)}
- payment_method: {_sanitize_field('payment_method', payment_method)}
- customer_type: {_sanitize_field('customer_type', customer_type)}
- retry_count: {_sanitize_field(None, retry_count)}
- previous_recovery_attempts: {_sanitize_field(None, previous_attempts)}
- transaction_age_minutes: {_sanitize_field(None, transaction_age_minutes)}

Strategy Guidelines:
1. RETRY: For transient network timeouts, gateway errors, or temporary bank downtimes.
2. PAYMENT_LINK: For card expiry, invalid credentials, or when customer needs to select an alternative payment method.
3. REMINDER: For gentle notifications on low-value abandoned checkouts or soft declines.
4. HYBRID: For high-value customers with persistent errors needing automated retry plus customer notification.

Risk Level Guidelines:
- LOW: High probability of recovery, low financial risk.
- MEDIUM: Moderate recovery chance or multiple prior attempts.
- HIGH: Persistent failure, unauthorized attempt, or excessive retries.

Return ONLY a single valid JSON object with EXACTLY these keys (no markdown fences, no explanatory text):
{{
  "recommended_action": "RETRY",
  "recovery_probability": 0.85,
  "confidence": 0.90,
  "expected_recovery": {amount * 0.85:.2f},
  "risk_level": "LOW",
  "reason": "Clear explanation of the rationale for this recommendation."
}}
"""


async def _call_ollama_raw(prompt: str) -> Dict[str, Any]:
    """Send prompt to local Ollama LLM endpoint."""
    model = config.OLLAMA_MODEL.strip()
    if not model:
        raise RuntimeError("OLLAMA_MODEL is not configured in environment")

    async with httpx.AsyncClient(timeout=config.OLLAMA_TIMEOUT) as client:
        response = await client.post(
            config.OLLAMA_URL,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
            },
        )
        response.raise_for_status()
        data = response.json()

    raw_response = data.get("response", "")
    # Parse JSON, handling potential markdown wrappers defensively
    clean_text = raw_response.strip()
    if clean_text.startswith("```json"):
        clean_text = clean_text[7:]
    if clean_text.startswith("```"):
        clean_text = clean_text[3:]
    if clean_text.endswith("```"):
        clean_text = clean_text[:-3]

    return json.loads(clean_text.strip())


def compute_rule_fallback(
    amount: float,
    failure_reason: Optional[str],
    payment_method: Optional[str] = None,
    customer_type: Optional[str] = None,
    retry_count: int = 0,
    previous_attempts: int = 0,
    payment_timestamp: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Deterministic, reliable fallback decision using the built-in rule engine."""
    recovery_score = compute_recovery_score(
        amount=amount,
        failure_reason=failure_reason,
        payment_method=payment_method,
        customer_type=customer_type,
        retry_count=retry_count,
        previous_recovery_attempts=previous_attempts,
        payment_timestamp=payment_timestamp,
    )
    strategy = recommend_strategy(
        amount=amount,
        failure_reason=failure_reason,
        payment_method=payment_method,
        customer_type=customer_type,
        retry_count=retry_count,
        previous_recovery_attempts=previous_attempts,
        recovery_score=recovery_score,
    )

    prob = round(float(recovery_score), 4)
    expected = round(amount * prob, 2)
    risk = "LOW" if prob >= 0.70 else ("MEDIUM" if prob >= 0.40 else "HIGH")

    return {
        "recommended_action": strategy["recommended_action"],
        "recovery_probability": prob,
        "confidence": strategy["confidence"],
        "expected_recovery": expected,
        "risk_level": risk,
        "reason": strategy["reason"],
        "decision_source": SOURCE_FALLBACK,
        "model": "deterministic-rules",
    }


async def generate_recovery_decision(
    amount: float,
    failure_reason: Optional[str] = None,
    error_code: Optional[str] = None,
    customer_type: Optional[str] = None,
    payment_method: Optional[str] = None,
    retry_count: int = 0,
    previous_recovery_attempts: int = 0,
    payment_timestamp: Optional[datetime] = None,
    transaction_age_minutes: Optional[int] = None,
) -> Dict[str, Any]:
    """Execute the full AI decision engine with validation and safe fallback.

    Returns a dict with:
      - recommended_action (RETRY | PAYMENT_LINK | REMINDER | HYBRID)
      - recovery_probability (float 0..1)
      - confidence (float 0..1)
      - expected_recovery (float <= amount)
      - risk_level (LOW | MEDIUM | HIGH)
      - reason (str)
      - decision_source (OLLAMA | RULE_ENGINE_FALLBACK)
      - model (str)
      - ai_decision_at (str ISO)
    """
    amount = max(0.0, float(amount or 0.0))

    prompt = build_ai_prompt(
        amount=amount,
        failure_reason=failure_reason,
        error_code=error_code,
        payment_method=payment_method,
        customer_type=customer_type,
        retry_count=retry_count,
        previous_attempts=previous_recovery_attempts,
        transaction_age_minutes=transaction_age_minutes,
    )

    decision_data: Optional[Dict[str, Any]] = None
    decision_source = SOURCE_OLLAMA
    model_name = config.OLLAMA_MODEL or "unset"

    try:
        raw_output = await _call_ollama_raw(prompt)
        validated = RecoveryDecisionOutput(**raw_output)

        # Enforce expected_recovery invariants
        expected_rec = validated.expected_recovery
        if expected_rec is None:
            expected_rec = round(amount * validated.recovery_probability, 2)
        else:
            expected_rec = min(amount, max(0.0, float(expected_rec)))

        decision_data = {
            "recommended_action": validated.recommended_action,
            "recovery_probability": validated.recovery_probability,
            "confidence": validated.confidence,
            "expected_recovery": expected_rec,
            "risk_level": validated.risk_level,
            "reason": validated.reason.strip(),
            "decision_source": SOURCE_OLLAMA,
            "model": model_name,
        }
    except Exception as exc:
        logger.warning("Ollama AI recovery engine call failed (%s); falling back to rule engine", exc)
        fallback = compute_rule_fallback(
            amount=amount,
            failure_reason=failure_reason,
            payment_method=payment_method,
            customer_type=customer_type,
            retry_count=retry_count,
            previous_attempts=previous_recovery_attempts,
            payment_timestamp=payment_timestamp,
        )
        decision_data = fallback

    decision_data["ai_decision_at"] = datetime.now(timezone.utc)
    return decision_data


async def analyze_and_persist_payment(
    payment: Payment,
) -> Dict[str, Any]:
    """Analyze a Payment record with the AI engine and return formatted decision dict.

    Does NOT commit the db session; caller handles transaction lifecycle.
    """
    now = datetime.now(timezone.utc)
    tx_age_minutes = None
    if payment.payment_timestamp:
        try:
            delta = now - payment.payment_timestamp
            tx_age_minutes = max(0, int(delta.total_seconds() // 60))
        except Exception:
            tx_age_minutes = None

    decision = await generate_recovery_decision(
        amount=payment.amount,
        failure_reason=payment.failure_reason,
        error_code=payment.error_code,
        customer_type=payment.customer_type,
        payment_method=payment.payment_method,
        retry_count=payment.retry_count or 0,
        previous_recovery_attempts=payment.previous_recovery_attempts or 0,
        payment_timestamp=payment.payment_timestamp,
        transaction_age_minutes=tx_age_minutes,
    )

    # Persist decision onto Payment entity
    payment.recommended_action = decision["recommended_action"]
    payment.confidence = decision["confidence"]
    payment.recovery_score = decision["recovery_probability"]
    payment.recovery_probability = decision["recovery_probability"]
    payment.expected_recovery = decision["expected_recovery"]
    payment.risk_level = decision["risk_level"]
    payment.reason = decision["reason"]
    payment.decision_source = decision["decision_source"]
    payment.ai_decision_at = decision["ai_decision_at"]

    # Format return dictionary for API consumers
    return {
        "payment_id": payment.id,
        "amount": payment.amount,
        "recommended_action": decision["recommended_action"],
        "recovery_probability": decision["recovery_probability"],
        "confidence": decision["confidence"],
        "expected_recovery": decision["expected_recovery"],
        "risk_level": decision["risk_level"],
        "reason": decision["reason"],
        "decision_source": decision["decision_source"],
        "model": decision.get("model"),
        "ai_decision_at": decision["ai_decision_at"].isoformat(),
    }

