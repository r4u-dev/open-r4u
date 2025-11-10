"""Tests for provider-related API endpoints."""

import pytest

from app.models.providers import Model, Provider


@pytest.mark.asyncio
async def test_list_all_models_endpoint_only_with_api_keys(client, test_session):
    """Ensure `/v1/providers/models` returns only models from providers with API keys."""
    # Provider with API key
    provider_with_key = Provider(
        name="openai",
        display_name="OpenAI",
        api_key_encrypted="encrypted_key_here",
    )
    test_session.add(provider_with_key)
    await test_session.flush()

    # Provider without API key
    provider_without_key = Provider(name="anthropic", display_name="Anthropic")
    test_session.add(provider_without_key)
    await test_session.flush()

    test_session.add_all([
        Model(provider_id=provider_with_key.id, name="gpt-5", display_name="GPT-5"),
        Model(provider_id=provider_without_key.id, name="claude-sonnet-4", display_name="Claude Sonnet 4"),
    ])
    await test_session.commit()

    response = await client.get("/v1/providers/models")
    assert response.status_code == 200
    models = response.json()
    assert "openai/gpt-5" in models
    assert "anthropic/claude-sonnet-4" not in models

