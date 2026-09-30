from __future__ import annotations

from faststream import FastStream

from app.messaging.broker import broker, declare_topology
from app.workers import consumer

app = FastStream(broker)


@app.after_startup
async def setup_topology() -> None:
    await declare_topology()
