from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.config import settings
from app.db.session import async_session_maker
from app.messaging.broker import broker, payments_exchange, payments_new_queue
from app.models.outbox import OutboxMessage, OutboxStatus

logger = logging.getLogger(__name__)


class OutboxPublisher:
    async def run_forever(self, stop_event: asyncio.Event) -> None:
        while not stop_event.is_set():
            try:
                await self.publish_pending_once()
            except Exception:
                logger.exception("Outbox polling iteration failed.")

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=settings.outbox_poll_interval_seconds)
            except TimeoutError:
                pass

    async def publish_pending_once(self) -> None:
        async with async_session_maker() as session:
            async with session.begin():
                result = await session.execute(
                    select(OutboxMessage)
                    .where(OutboxMessage.status == OutboxStatus.pending.value)
                    .order_by(OutboxMessage.created_at)
                    .limit(settings.outbox_batch_size)
                    .with_for_update(skip_locked=True)
                )
                messages = result.scalars().all()

                for message in messages:
                    try:
                        event = {"event_id": str(message.id), **message.payload}
                        await broker.publish(
                            event,
                            queue=payments_new_queue,
                            exchange=payments_exchange,
                            routing_key="payments.new",
                            persist=True,
                        )
                    except Exception as exc:
                        message.attempts += 1
                        message.last_error = str(exc)
                        if message.attempts >= settings.outbox_max_attempts:
                            message.status = OutboxStatus.failed.value
                        logger.exception("Failed to publish outbox message %s.", message.id)
                    else:
                        message.status = OutboxStatus.published.value
                        message.published_at = datetime.now(UTC)
                        message.last_error = None


outbox_publisher = OutboxPublisher()
