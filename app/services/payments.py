from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outbox import OutboxMessage
from app.models.payment import Payment, PaymentStatus
from app.schemas.payment import PaymentCreate


class PaymentService:
    async def create_payment(
        self,
        session: AsyncSession,
        data: PaymentCreate,
        idempotency_key: str,
    ) -> Payment:
        existing_payment = await self.get_by_idempotency_key(session, idempotency_key)
        if existing_payment is not None:
            return existing_payment

        payment = Payment(
            amount=data.amount,
            currency=data.currency.value,
            description=data.description,
            metadata_=data.metadata,
            status=PaymentStatus.pending.value,
            idempotency_key=idempotency_key,
            webhook_url=str(data.webhook_url),
        )
        session.add(payment)
        await session.flush()

        session.add(
            OutboxMessage(
                event_type="payment.created",
                aggregate_id=str(payment.id),
                payload={"payment_id": str(payment.id)},
            )
        )

        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            existing_payment = await self.get_by_idempotency_key(session, idempotency_key)
            if existing_payment is None:
                raise
            return existing_payment

        return payment

    async def get_payment(self, session: AsyncSession, payment_id: uuid.UUID) -> Payment:
        payment = await session.get(Payment, payment_id)
        if payment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found.")
        return payment

    async def get_by_idempotency_key(self, session: AsyncSession, idempotency_key: str) -> Payment | None:
        result = await session.execute(select(Payment).where(Payment.idempotency_key == idempotency_key))
        return result.scalar_one_or_none()


payment_service = PaymentService()
