from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.messaging.broker import broker, declare_topology
from app.services.outbox import outbox_publisher


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    stop_event = asyncio.Event()
    await broker.connect()
    await declare_topology()
    task = asyncio.create_task(outbox_publisher.run_forever(stop_event))

    try:
        yield
    finally:
        stop_event.set()
        await task
        await broker.close()


app = FastAPI(title="Async Payment Processing", version="0.1.0", lifespan=lifespan)
app.include_router(api_router)


@app.get("/health", include_in_schema=False)
async def health() -> dict[str, str]:
    return {"status": "ok"}
