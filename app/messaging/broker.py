from __future__ import annotations

from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue

from app.core.config import settings

broker = RabbitBroker(settings.rabbitmq_url)

payments_exchange = RabbitExchange("payments", durable=True)
dead_letter_exchange = RabbitExchange("payments.dlx", durable=True)

payments_new_queue = RabbitQueue(
    "payments.new",
    durable=True,
    routing_key="payments.new",
    arguments={
        "x-dead-letter-exchange": "payments.dlx",
        "x-dead-letter-routing-key": "payments.failed",
    },
)
payments_failed_queue = RabbitQueue(
    "payments.failed",
    durable=True,
    routing_key="payments.failed",
)


async def declare_topology() -> None:
    payments_exchange_obj = await broker.declare_exchange(payments_exchange)
    dead_letter_exchange_obj = await broker.declare_exchange(dead_letter_exchange)

    new_queue = await broker.declare_queue(payments_new_queue)
    failed_queue = await broker.declare_queue(payments_failed_queue)

    await new_queue.bind(payments_exchange_obj, routing_key="payments.new")
    await failed_queue.bind(dead_letter_exchange_obj, routing_key="payments.failed")
