"""Tests for ProviderService provider/model utilities."""

import pytest

from app.models.providers import Model, Provider
from app.services.provider_service import ProviderService


@pytest.mark.asyncio
async def test_canonicalize_model_with_prefixed_identifier(test_session):
    """Canonicalization should match exact model names (versions preserved)."""
    provider = Provider(name="openai", display_name="OpenAI")
    test_session.add(provider)
    await test_session.flush()

    model = Model(provider_id=provider.id, name="gpt-5", display_name="GPT-5")
    test_session.add(model)
    await test_session.commit()

    service = ProviderService(test_session)

    assert await service.canonicalize_model("openai/gpt-5") == "openai/gpt-5"
    # Versioned model not in DB, so returns original
    assert await service.canonicalize_model("openai/gpt-5-2024-10-01") == "openai/gpt-5-2024-10-01"


@pytest.mark.asyncio
async def test_canonicalize_model_without_prefix(test_session):
    """Canonicalization without provider prefix should return canonical form when unique."""
    provider = Provider(name="anthropic", display_name="Anthropic")
    test_session.add(provider)
    await test_session.flush()

    model = Model(provider_id=provider.id, name="claude-sonnet-4", display_name="Claude Sonnet 4")
    test_session.add(model)
    await test_session.commit()

    service = ProviderService(test_session)

    assert await service.canonicalize_model("claude-sonnet-4") == "anthropic/claude-sonnet-4"


@pytest.mark.asyncio
async def test_canonicalize_model_ambiguous(test_session):
    """When multiple providers share the same model name, return the original identifier."""
    provider_a = Provider(name="provider-a", display_name="Provider A")
    provider_b = Provider(name="provider-b", display_name="Provider B")
    test_session.add_all([provider_a, provider_b])
    await test_session.flush()

    test_session.add_all([
        Model(provider_id=provider_a.id, name="shared-model", display_name="Shared"),
        Model(provider_id=provider_b.id, name="shared-model", display_name="Shared"),
    ])
    await test_session.commit()

    service = ProviderService(test_session)

    assert await service.canonicalize_model("shared-model") == "shared-model"


@pytest.mark.asyncio
async def test_list_canonical_model_names(test_session):
    """list_canonical_model_names should return sorted canonical identifiers."""
    provider = Provider(name="google", display_name="Google")
    test_session.add(provider)
    await test_session.flush()

    test_session.add_all([
        Model(provider_id=provider.id, name="gemini-2.5-pro", display_name="Gemini 2.5 Pro"),
        Model(provider_id=provider.id, name="gemini-2.5-flash", display_name="Gemini 2.5 Flash"),
    ])
    await test_session.commit()

    service = ProviderService(test_session)

    names = await service.list_canonical_model_names()
    assert names == [
        "google/gemini-2.5-flash",
        "google/gemini-2.5-pro",
    ]

