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

# Recovery execution safety switch.
# RECOVERY_DRY_RUN defaults to TRUE and is the SAFE default: while enabled the
# Recovery Execution Engine NEVER calls Razorpay for a real recovery operation —
# it always returns a simulated result. Only an operator intentionally setting
# RECOVERY_DRY_RUN=false (with Razorpay TEST/SANDBOX credentials) enables the
# real RETRY path. It must never default to false.
RECOVERY_DRY_RUN = _get("RECOVERY_DRY_RUN", "true")


def recovery_dry_run_enabled() -> bool:
    """Return True when the safety switch is enabled (default).

    Enabled unless the operator explicitly sets RECOVERY_DRY_RUN to a false
    value (false/0/no/off). Any unset or unknown value keeps DRY_RUN on.
    """
    value = os.getenv("RECOVERY_DRY_RUN", "true").strip().lower()
    return value not in ("false", "0", "no", "off")


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


# Polygon Amoy testnet blockchain configuration.
# All four MUST be set in Backend/.env for on-chain proof submission.
POLYGON_AMOY_RPC_URL = _get("POLYGON_RPC_URL", "")
BLOCKCHAIN_PRIVATE_KEY = _get("BLOCKCHAIN_PRIVATE_KEY", "")
RECOVERY_PROOF_CONTRACT_ADDRESS = _get("RECOVERY_PROOF_CONTRACT_ADDRESS", "")
POLYGON_CHAIN_ID = int(_get("POLYGON_CHAIN_ID", "80002"))


def blockchain_configured() -> bool:
    """Return True when Polygon Amoy blockchain credentials are present."""
    return bool(
        POLYGON_AMOY_RPC_URL
        and BLOCKCHAIN_PRIVATE_KEY
        and RECOVERY_PROOF_CONTRACT_ADDRESS
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
        "blockchain_configured": blockchain_configured(),
        "blockchain_chain_id": POLYGON_CHAIN_ID,
    }

