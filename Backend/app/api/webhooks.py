"""Razorpay webhook HTTP endpoint.

Receives Razorpay webhooks, verifies the HMAC-SHA256 signature using the
official webhook secret, and dispatches the body to the webhook service for
storage, deduplication, and Payment synchronisation.

The raw body is always read and verified before parsing, so a malformed or
unauthenticated request can never trigger processing.
"""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.razorpay_service import (
    RazorpayNotConfigured,
    verify_webhook_signature,
)
from app.services.webhook_service import process_razorpay_webhook

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/webhooks",
    tags=["Webhooks"],
)


class WebhookResponse(BaseModel):
    status: str
    event: str | None = None
    processed: bool | None = None


@router.post("/razorpay", response_model=WebhookResponse)
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Receive and verify a Razorpay webhook.

    Only events with a valid ``X-Razorpay-Signature`` header are processed.
    """
    if not x_razorpay_signature:
        raise HTTPException(status_code=400, detail="Missing webhook signature.")

    raw_body = await request.body()
    body_text = raw_body.decode("utf-8")

    try:
        verified = verify_webhook_signature(body_text, x_razorpay_signature)
    except RazorpayNotConfigured as exc:
        logger.error("Webhook secret not configured: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:  # pragma: no cover - defensive
        logger.exception("Webhook signature verification error")
        raise HTTPException(
            status_code=500, detail="Webhook verification unavailable."
        )

    if not verified:
        logger.warning("Rejected Razorpay webhook with invalid signature")
        raise HTTPException(status_code=400, detail="Invalid webhook signature.")

    try:
        result = await process_razorpay_webhook(body_text, db)
    except ValueError as exc:
        # Malformed JSON after valid signature - reasonable client error.
        logger.warning("Malformed webhook payload: %s", exc)
        raise HTTPException(status_code=400, detail="Malformed webhook payload.")
    except Exception:  # pragma: no cover - defensive
        logger.exception("Razorpay webhook processing failed")
        db.rollback()
        raise HTTPException(status_code=500, detail="Webhook processing failed.")

    return WebhookResponse(
        status=result["status"],
        event=result.get("event"),
        processed=result.get("processed"),
    )
