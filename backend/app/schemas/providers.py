"""Pydantic schemas for providers and models."""

from pydantic import BaseModel, ConfigDict, Field


class ModelBase(BaseModel):
    """Base schema for model."""

    name: str = Field(..., description="Model name")
    display_name: str = Field(..., description="Model display name")


class ModelCreate(ModelBase):
    """Schema for creating a model."""


class ModelResponse(ModelBase):
    """Schema for model response."""

    id: int
    provider_id: int
    model_config = ConfigDict(from_attributes=True)


class ProviderBase(BaseModel):
    """Base schema for provider."""

    name: str = Field(..., description="Provider name (unique identifier)")
    display_name: str = Field(..., description="Provider display name")
    base_url: str | None = Field(None, description="Base URL for custom providers")


class ProviderCreate(BaseModel):
    """Schema for creating a provider."""

    name: str = Field(..., description="Provider name (unique identifier)")
    display_name: str = Field(..., description="Provider display name")
    base_url: str | None = Field(None, description="Base URL for custom providers")
    api_key: str | None = Field(None, description="API key for the provider")
    models: list[str] | None = Field(
        None,
        description="Comma-separated model names (for custom providers)",
    )


class ProviderUpdate(BaseModel):
    """Schema for updating a provider."""

    display_name: str | None = Field(None, description="Provider display name")
    api_key: str | None = Field(None, description="API key for the provider")
    base_url: str | None = Field(None, description="Base URL for custom providers")


class ProviderResponse(ProviderBase):
    """Schema for provider response."""

    id: int
    has_api_key: bool = Field(
        ...,
        description="Whether the provider has an API key configured",
    )
    models: list[ModelResponse] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class ProviderWithModelsResponse(ProviderResponse):
    """Schema for provider response with models."""
