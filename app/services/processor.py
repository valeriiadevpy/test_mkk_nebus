from __future__ import annotations

import asyncio
import random
import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.db.session import async_session_maker
from app.models.payment import Payment, PaymentStatus
from app.services.webhooks import send_payment_webhook


async def process_payment(payment_id: uuid.UUID) -> None:
    async with async_session_maker() as session:
        async with session.begin():
            result = await session.execute(select(Payment).where(Payment.id == payment_id).with_for_update())
            payment = result.scalar_one_or_none()
            if payment is None:
                return

            if payment.status == PaymentStatus.pending.value:
                await asyncio.sleep(random.uniform(2, 5))
                payment.status = (
                    PaymentStatus.succeeded.value if random.random() < 0.9 else PaymentStatus.failed.value
                )
                payment.processed_at = datetime.now(UTC)

        await session.refresh(payment)

    await send_payment_webhook(payment)
