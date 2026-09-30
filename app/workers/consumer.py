from __future__ import annotations

import asyncio
import logging

from faststream.rabbit import RabbitMessage

from app.core.config import settings
from app.messaging.broker import broker, dead_letter_exchange, payments_exchange, payments_new_queue
from app.schemas.events import PaymentCreatedEvent
from app.services.processor import process_payment

logger = logging.getLogger(__name__)


@broker.subscriber(payments_new_queue, payments_exchange)
async def handle_payment_created(event: PaymentCreatedEvent, message: RabbitMessage) -> None:
    try:
        await process_payment(event.payment_id)
    except Exception as exc:
        await retry_or_dead_letter(event, message, exc)


async def retry_or_dead_letter(event: PaymentCreatedEvent, message: RabbitMessage, exc: Exception) -> None:
    retry_count = int(message.headers.get("x-retry-count", 0)) + 1
    payload = event.model_dump(mode="json")

    if retry_count >= settings.message_max_retries:
        logger.exception("Payment message %s moved to DLQ after %s attempts.", event.event_id, retry_count)
        await broker.publish(
            payload,
            exchange=dead_letter_exchange,
            routing_key="payments.failed",
            persist=True,
            headers={"x-retry-count": retry_count, "x-error": str(exc)},
        )
        return

    delay = settings.retry_base_delay_seconds * (2 ** (retry_count - 1))
    logger.warning("Payment message %s failed, retrying in %.1f seconds.", event.event_id, delay)
    await asyncio.sleep(delay)
    await broker.publish(
        payload,
        exchange=payments_exchange,
        routing_key="payments.new",
        persist=True,
        headers={"x-retry-count": retry_count},
    )
