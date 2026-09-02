import json
import httpx


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen3:8b"


async def analyze_payment_failure(
    amount: float,
    failure_reason: str,
    customer_type: str,
):
    prompt = f"""
You are RecoverAI, an autonomous payment recovery decision engine.

Analyze this failed payment:

Amount: ₹{amount}
Failure Reason: {failure_reason}
Customer Type: {customer_type}

Choose exactly ONE recovery action:

- RETRY
- PAYMENT_LINK
- ALTERNATIVE_METHOD
- HUMAN_REVIEW

Return ONLY valid JSON.

The JSON must have exactly these fields:

{{
    "recommended_action": "RETRY",
    "reason": "Short explanation",
    "confidence": 0.75
}}

Rules:
- recommended_action must be one of the four allowed actions.
- confidence must be a number between 0 and 1.
- reason must be short and practical.
- Do not include markdown.
- Do not include additional fields.
- Do not include any text outside the JSON.
"""

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "format": "json",
            },
        )

        response.raise_for_status()

        data = response.json()

        ai_response = data["response"]

        try:
            decision = json.loads(ai_response)
        except json.JSONDecodeError:
            raise ValueError(
                f"Ollama returned invalid JSON: {ai_response}"
            )

        decision["source"] = "QWEN3"
        
        return {
            "model": MODEL_NAME,
            "decision": decision,
        }