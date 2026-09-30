from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    api_key: str = Field(default="change-me", validation_alias="API_KEY")
    database_url: str = Field(
        default="postgresql+asyncpg://payments:payments@localhost:5432/payments",
        validation_alias="DATABASE_URL",
    )
    rabbitmq_url: str = Field(default="amqp://guest:guest@localhost:5672/", validation_alias="RABBITMQ_URL")

    outbox_poll_interval_seconds: float = Field(default=1, validation_alias="OUTBOX_POLL_INTERVAL_SECONDS")
    outbox_batch_size: int = Field(default=25, validation_alias="OUTBOX_BATCH_SIZE")
    outbox_max_attempts: int = Field(default=10, validation_alias="OUTBOX_MAX_ATTEMPTS")

    message_max_retries: int = Field(default=3, validation_alias="MESSAGE_MAX_RETRIES")
    webhook_max_retries: int = Field(default=3, validation_alias="WEBHOOK_MAX_RETRIES")
    retry_base_delay_seconds: float = Field(default=1, validation_alias="RETRY_BASE_DELAY_SECONDS")


settings = Settings()
