from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_api_key
from app.db.session import get_session
from app.schemas.payment import PaymentCreate, PaymentCreated, PaymentDetails
from app.services.payments import payment_service

router = APIRouter(
    prefix="/payments",
    tags=["payments"],
    dependencies=[Depends(require_api_key)],
)


@router.post("", response_model=PaymentCreated, status_code=status.HTTP_202_ACCEPTED)
async def create_payment(
    payload: PaymentCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)],
) -> PaymentCreated:
    payment = await payment_service.create_payment(session, payload, idempotency_key)
    return PaymentCreated.model_validate(payment)


@router.get("/{payment_id}", response_model=PaymentDetails)
async def get_payment(
    payment_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PaymentDetails:
    payment = await payment_service.get_payment(session, payment_id)
    return PaymentDetails.model_validate(payment)
