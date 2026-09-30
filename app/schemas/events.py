from __future__ import annotations

import uuid

from pydantic import BaseModel


class PaymentCreatedEvent(BaseModel):
    event_id: uuid.UUID
    payment_id: uuid.UUID
