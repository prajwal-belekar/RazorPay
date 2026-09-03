"""Razorpay read/integration endpoints.

Exposes Razorpay TEST-mode data to RecoverAI / the frontend without ever
leaking credentials. When TEST credentials are not configured, endpoints
return a clear 503 rather than inventing or faking Razorpay data.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
import razorpay.errors

from app.config import get_razorpay_public_config
from app.services.razorpay_service import (
    RazorpayNotConfigured,
    check_payment_status,
    create_order,
    fetch_order,
    fetch_payment_order_info,
    fetch_payments,
)

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/razorpay",
    tags=["Razorpay"],
)


class CreateRazorpayOrderRequest(BaseModel):
    amount: float = Field(gt=0, description="Amount in Indian Rupees (INR)")
    receipt: str | None = Field(default=None, description="Optional merchant receipt identifier")
    notes: dict[str, Any] | None = Field(default=None, description="Optional metadata notes")


def _handle_razorpay_error(exc: Exception) -> HTTPException:
    """Translate a Razorpay error into a clean, safe HTTP response."""
    if isinstance(exc, RazorpayNotConfigured):
        return HTTPException(status_code=503, detail=str(exc))

    if isinstance(exc, razorpay.errors.BadRequestError):
        # Upstream Razorpay rejected invalid inputs or non-existent IDs
        return HTTPException(
            status_code=400,
            detail=str(exc) or "Bad request to Razorpay API.",
        )

    if isinstance(exc, razorpay.errors.SignatureVerificationError):
        return HTTPException(
            status_code=400,
            detail="Razorpay signature verification failed.",
        )

    if isinstance(exc, razorpay.errors.GatewayError):
        return HTTPException(
            status_code=504,
            detail="Razorpay gateway timeout. Please retry.",
        )

    if isinstance(exc, razorpay.errors.ServerError):
        return HTTPException(
            status_code=502,
            detail="Razorpay upstream server error.",
        )

    code = getattr(exc, "status_code", None)
    if code is not None and 400 <= code < 500:
        detail = getattr(exc, "message", None) or getattr(
            exc, "error", {}
        ).get("description", "Razorpay API error.")
        return HTTPException(status_code=code, detail=str(detail))

    # Log error without leaking any credentials
    logger.error("Razorpay API error: %s", exc)
    return HTTPException(
        status_code=502,
        detail="Razorpay API request failed.",
    )


@router.get("/config")
def get_config_status():
    """Return safe public Razorpay configuration status.
    
    Indicates whether valid credentials are configured, environment mode,
    and preview key without exposing secrets.
    """
    return get_razorpay_public_config()


@router.get("/payments")
def list_payments(
    count: int = Query(default=10, ge=1, le=100, description="Number of payments to fetch (1-100)"),
    skip: int = Query(default=0, ge=0, description="Number of payments to skip"),
):
    """List Razorpay TEST payments (newest first).

    Query params:
      - count: number of records (1-100, default 10)
      - skip:  pagination offset (default 0)
    """
    try:
        return fetch_payments(count=count, skip=skip)
    except Exception as exc:  # noqa: BLE001 - normalised below
        raise _handle_razorpay_error(exc)


@router.get("/payments/{payment_id}")
def get_payment(payment_id: str):
    """Fetch a single Razorpay TEST payment."""
    try:
        return check_payment_status(payment_id)
    except Exception as exc:  # noqa: BLE001 - normalised below
        raise _handle_razorpay_error(exc)


@router.get("/payments/{payment_id}/order")
def get_payment_with_order(payment_id: str):
    """Fetch a Razorpay payment together with its linked order."""
    try:
        return fetch_payment_order_info(payment_id)
    except Exception as exc:  # noqa: BLE001 - normalised below
        raise _handle_razorpay_error(exc)


@router.get("/orders/{order_id}")
def get_order(order_id: str):
    """Fetch a single Razorpay TEST order by ID."""
    try:
        order = fetch_order(order_id)
        return {
            "id": order.get("id"),
            "entity": order.get("entity"),
            "amount": order.get("amount"),
            "amount_paid": order.get("amount_paid"),
            "amount_due": order.get("amount_due"),
            "currency": order.get("currency"),
            "receipt": order.get("receipt"),
            "status": order.get("status"),
            "attempts": order.get("attempts"),
            "notes": order.get("notes"),
            "created_at": order.get("created_at"),
        }
    except Exception as exc:  # noqa: BLE001 - normalised below
        raise _handle_razorpay_error(exc)


@router.post("/orders")
def create_order_endpoint(request: CreateRazorpayOrderRequest):
    """Create a new Razorpay TEST order.
    
    Amount is provided in INR (e.g., 500.00). Returns safe sanitized order
    details without leaking any internal credentials.
    """
    try:
        order = create_order(amount_in_inr=request.amount, receipt=request.receipt)
        return {
            "id": order.get("id"),
            "amount": order.get("amount"),
            "currency": order.get("currency"),
            "status": order.get("status"),
            "receipt": order.get("receipt"),
            "created_at": order.get("created_at"),
        }
    except Exception as exc:  # noqa: BLE001 - normalised below
        raise _handle_razorpay_error(exc)
