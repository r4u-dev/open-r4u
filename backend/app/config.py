from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    app_url: str = "http://localhost:8080"

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

    min_segment_words: int = 3
    min_cluster_size: int = 10
    # if unset, will be set to number_of_traces // 5
    min_matching_traces: int | None = None

    max_task_name_length: int = 25
    max_task_description_length: int = 150


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()
