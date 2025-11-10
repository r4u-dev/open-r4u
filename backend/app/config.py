from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/postgres"
    log_level: str = "INFO"

    # Encryption key for storing API keys securely
    encryption_key: str | None = None

    # LLM Provider API Keys and Configuration for LiteLLM
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    google_api_key: str | None = None
    cohere_api_key: str | None = None
    mistral_api_key: str | None = None
    together_api_key: str | None = None
    # Add more providers as needed

    min_segment_words: int = 2
    min_matching_traces: int = 2
    min_cluster_size: int = 2


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()
