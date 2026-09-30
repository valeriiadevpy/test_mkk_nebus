from __future__ import annotations

import asyncio
from datetime import datetime
from decimal import Decimal

import httpx

from app.core.config import settings
from app.models.payment import Payment


def _json_safe_amount(value: Decimal) -> str:
    return format(value, "f")


def build_webhook_payload(payment: Payment) -> dict:
    return {
        "payment_id": str(payment.id),
        "amount": _json_safe_amount(payment.amount),
        "currency": payment.currency,
        "description": payment.description,
        "metadata": payment.metadata_,
        "status": payment.status,
        "created_at": _format_datetime(payment.created_at),
        "processed_at": _format_datetime(payment.processed_at),
    }


def _format_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


async def send_payment_webhook(payment: Payment) -> None:
    payload = build_webhook_payload(payment)

    async with httpx.AsyncClient(timeout=10) as client:
        for attempt in range(1, settings.webhook_max_retries + 1):
            try:
                response = await client.post(payment.webhook_url, json=payload)
                response.raise_for_status()
                return
            except httpx.HTTPError:
                if attempt >= settings.webhook_max_retries:
                    raise
                await asyncio.sleep(settings.retry_base_delay_seconds * (2 ** (attempt - 1)))
