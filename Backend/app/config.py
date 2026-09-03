import os
from pathlib import Path

from dotenv import load_dotenv


# Load environment variables from Backend/.env (or root .env)
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _get(name: str, default: str = "") -> str:
    return os.getenv(name, default)


# PostgreSQL
DATABASE_URL = _get(
    "DATABASE_URL",
    "postgresql://postgres@localhost:5432/recoverai",
)

# Razorpay TEST credentials
RAZORPAY_KEY_ID = _get("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = _get("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = _get("RAZORPAY_WEBHOOK_SECRET", "")

# Local Ollama AI decision engine.
# OLLAMA_MODEL must come from the environment; never hardcode a model here.
OLLAMA_URL = _get("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = _get("OLLAMA_MODEL", "")
OLLAMA_TIMEOUT = float(_get("OLLAMA_TIMEOUT", "120"))


def razorpay_configured() -> bool:
    """Return True when real Razorpay TEST credentials are present."""
    key_id = os.getenv("RAZORPAY_KEY_ID", "")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "")
    return bool(
        key_id
        and key_id not in ("rzp_test_xxxxx", "your_test_key_id", "your_key_id", "...")
        and key_secret
        and key_secret not in ("xxxxx", "your_test_key_secret", "your_key_secret", "...")
    )


def razorpay_webhook_configured() -> bool:
    """Return True when a real Razorpay webhook secret is configured."""
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
    return bool(
        secret
        and secret not in ("xxxxx", "your_webhook_secret", "your_test_webhook_secret", "...")
    )


def get_razorpay_public_config() -> dict:
    """Return safe public Razorpay status without leaking any secrets."""
    configured = razorpay_configured()
    webhook_configured = razorpay_webhook_configured()
    current_key_id = os.getenv("RAZORPAY_KEY_ID", RAZORPAY_KEY_ID)
    key_id_preview = None
    if configured and current_key_id:
        if len(current_key_id) > 12:
            key_id_preview = f"{current_key_id[:8]}...{current_key_id[-4:]}"
        else:
            key_id_preview = f"{current_key_id[:4]}..."

    return {
        "configured": configured,
        "webhook_configured": webhook_configured,
        "mode": "test" if "test" in current_key_id.lower() else ("live" if configured else "none"),
        "key_id_preview": key_id_preview,
        "currency": "INR",
    }

