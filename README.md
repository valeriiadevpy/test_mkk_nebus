# Async Payment Processing

FastAPI microservice for asynchronous payment processing. It accepts payment requests, stores payments and outbox events in PostgreSQL, publishes events to RabbitMQ, processes them in one consumer, and sends the final result to a client webhook.

## Stack

- FastAPI and Pydantic v2
- SQLAlchemy 2.0 async mode
- PostgreSQL
- RabbitMQ and FastStream
- Alembic migrations
- Docker Compose

## Architecture

1. `POST /api/v1/payments` validates `X-API-Key` and required `Idempotency-Key`.
2. The API creates a `pending` payment and a `payment.created` outbox record in one database transaction.
3. The API process runs a background outbox publisher that locks pending outbox rows with `FOR UPDATE SKIP LOCKED` and publishes them to the `payments.new` queue.
4. The consumer receives messages from `payments.new`, emulates gateway processing for 2-5 seconds, and sets the payment status to `succeeded` in 90% of cases or `failed` in 10% of cases.
5. The consumer sends a webhook notification to the original `webhook_url`.
6. Webhook errors are retried 3 times with exponential backoff. Consumer-level failures are retried 3 times and then sent to the `payments.failed` DLQ through the `payments.dlx` exchange.

The consumer is idempotent for retries: if a payment was already processed but webhook delivery failed, the next message retry sends the webhook for the stored final status instead of reprocessing the payment.

## Run

The compose file uses `.env.example` so the service can be started without extra setup:

```bash
docker compose up --build
```

Services:

- API: `http://localhost:8000`
- OpenAPI: `http://localhost:8000/docs`
- RabbitMQ management: `http://localhost:15672` with `guest` / `guest`
- PostgreSQL: `localhost:5432`

To override settings, edit `.env.example` or create your own env file and update `docker-compose.yml`.

## API

All endpoints require:

- `X-API-Key: change-me`

### Create Payment

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me" \
  -H "Idempotency-Key: order-1001" \
  -d '{
    "amount": "1250.50",
    "currency": "RUB",
    "description": "Order #1001",
    "metadata": {"customer_id": "42"},
    "webhook_url": "https://example.com/webhooks/payments"
  }'
```

Response:

```json
{
  "payment_id": "9a78e069-7624-4be6-9633-9af845c58957",
  "status": "pending",
  "created_at": "2026-09-29T10:15:30.000000Z"
}
```

Repeating the same request with the same `Idempotency-Key` returns the same payment instead of creating a duplicate.

### Get Payment

```bash
curl http://localhost:8000/api/v1/payments/9a78e069-7624-4be6-9633-9af845c58957 \
  -H "X-API-Key: change-me"
```

Response:

```json
{
  "id": "9a78e069-7624-4be6-9633-9af845c58957",
  "amount": "1250.50",
  "currency": "RUB",
  "description": "Order #1001",
  "metadata": {"customer_id": "42"},
  "status": "succeeded",
  "webhook_url": "https://example.com/webhooks/payments",
  "created_at": "2026-09-29T10:15:30.000000Z",
  "processed_at": "2026-09-29T10:15:34.000000Z"
}
```

## Database

Run migrations inside Docker:

```bash
docker compose run --rm migrator
```

The initial migration creates:

- `payments`
- `outbox`

## RabbitMQ

Queues and exchanges:

- Exchange: `payments`
- Queue: `payments.new`
- Dead-letter exchange: `payments.dlx`
- Dead-letter queue: `payments.failed`

Messages that still fail after 3 consumer attempts are published to the dead-letter exchange with retry headers.

## Notes

- `Idempotency-Key` is unique in the database.
- The outbox publisher marks messages as `failed` only after repeated broker publication failures.
- Webhook payloads include payment id, amount, currency, description, metadata, final status, and timestamps.
