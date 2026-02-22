"""Application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed runtime configuration."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    app_name: str = "RAG SMS Platform"
    environment: str = Field(default="development", alias="ENVIRONMENT")
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@postgres:5432/ragsms",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")

    qdrant_url: str = Field(default="http://qdrant:6333", alias="QDRANT_URL")
    qdrant_api_key: str | None = Field(default=None, alias="QDRANT_API_KEY")
    qdrant_collection: str = Field(default="properties", alias="QDRANT_COLLECTION")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    cohere_api_key: str | None = Field(default=None, alias="COHERE_API_KEY")

    llm_provider: str = Field(default="openai", alias="LLM_PROVIDER")
    llm_model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL")
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")

    twilio_account_sid: str | None = Field(default=None, alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str | None = Field(default=None, alias="TWILIO_AUTH_TOKEN")
    twilio_phone_number: str | None = Field(default=None, alias="TWILIO_PHONE_NUMBER")

    gohighlevel_api_key: str | None = Field(default=None, alias="GHL_API_KEY")
    gohighlevel_location_id: str | None = Field(default=None, alias="GHL_LOCATION_ID")

    webhook_secret: str = Field(default="dev-secret", alias="WEBHOOK_SECRET")

    retrieval_top_k: int = Field(default=8, alias="RETRIEVAL_TOP_K")
    rerank_top_n: int = Field(default=4, alias="RERANK_TOP_N")
    chunk_size: int = Field(default=600, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=100, alias="CHUNK_OVERLAP")

    default_agency_id: str = Field(default="agency-demo", alias="DEFAULT_AGENCY_ID")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return singleton settings instance."""

    return Settings()
