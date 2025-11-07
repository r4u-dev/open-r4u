"""Tests for pricing service."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from app.services.pricing_service import PricingService


@pytest.fixture
def sample_pricing_data():
    """Sample pricing data for testing."""
    return {
        "providers": {
            "openai": {
                "display_name": "OpenAI",
                "models": {
                    "gpt-5": {
                        "input_usd_per_million": 1.25,
                        "cached_input_usd_per_million": 0.125,
                        "output_usd_per_million": 10.00,
                    },
                    "gpt-5-mini": {
                        "input_usd_per_million": 0.25,
                        "cached_input_usd_per_million": 0.025,
                        "output_usd_per_million": 2.00,
                    },
                },
            },
            "anthropic": {
                "display_name": "Anthropic (Claude)",
                "models": {
                    "claude-sonnet-4": {
                        "input_usd_per_million": 3.00,
                        "cached_input_usd_per_million": 0.30,
                        "output_usd_per_million": 15.00,
                    },
                },
            },
            "google": {
                "display_name": "Google (Gemini)",
                "models": {
                    "gemini-2.5-pro": {
                        "long_context_threshold_tokens": 200000,
                        "input_usd_per_million": {
                            "default": 1.25,
                            "long_context": 2.50,
                        },
                        "cached_input_usd_per_million": {
                            "default": 0.125,
                            "long_context": 0.250,
                        },
                        "output_usd_per_million": {
                            "default": 10.00,
                            "long_context": 15.00,
                        },
                    },
                },
            },
        },
    }


@pytest.fixture
def pricing_service_with_data(sample_pricing_data):
    """Create a pricing service with sample data."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(sample_pricing_data, f)
        temp_path = f.name

    service = PricingService(temp_path)
    yield service

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


class TestPricingService:
    """Test cases for PricingService."""

    def test_init_with_default_path(self):
        """Test initialization with default models.yaml path."""
        with patch.object(PricingService, "_load_pricing_data") as mock_load:
            service = PricingService()
            mock_load.assert_called_once()

    def test_init_with_custom_path(self):
        """Test initialization with custom path."""
        with patch.object(PricingService, "_load_pricing_data") as mock_load:
            custom_path = "/custom/path/models.yaml"
            service = PricingService(custom_path)
            assert service.models_yaml_path == Path(custom_path)
            mock_load.assert_called_once()

    def test_resolve_model_name_exact_match(self, pricing_service_with_data):
        """Test model name resolution for exact matches."""
        service = pricing_service_with_data

        # Test exact match
        provider, model = service._resolve_model_name_from_yaml("gpt-5")
        assert provider == "openai"
        assert model == "gpt-5"

    def test_resolve_model_name_provider_prefixed(self, pricing_service_with_data):
        """Test model name resolution for provider-prefixed models."""
        service = pricing_service_with_data

        # Test provider prefixed
        provider, model = service._resolve_model_name_from_yaml("openai/gpt-5")
        assert provider == "openai"
        assert model == "gpt-5"

    def test_resolve_model_name_versioned(self, pricing_service_with_data):
        """Test model name resolution for versioned models."""
        service = pricing_service_with_data

        # Test versioned model - should match base model
        provider, model = service._resolve_model_name_from_yaml("gpt-5-2024-10-01")
        assert provider == "openai"
        assert model == "gpt-5"  # Version stripped to base model

    def test_resolve_model_name_anthropic(self, pricing_service_with_data):
        """Test model name resolution for Anthropic models."""
        service = pricing_service_with_data

        provider, model = service._resolve_model_name_from_yaml("claude-sonnet-4")
        assert provider == "anthropic"
        assert model == "claude-sonnet-4"

    def test_resolve_model_name_google(self, pricing_service_with_data):
        """Test model name resolution for Google models."""
        service = pricing_service_with_data

        provider, model = service._resolve_model_name_from_yaml("gemini-2.5-pro")
        assert provider == "google"
        assert model == "gemini-2.5-pro"

    def test_resolve_model_name_unknown(self, pricing_service_with_data):
        """Test model name resolution for unknown models."""
        service = pricing_service_with_data

        # Should raise ValueError for unknown models
        with pytest.raises(ValueError, match="not found in models.yaml"):
            service._resolve_model_name_from_yaml("unknown-model")

    def test_strip_version_suffix(self, pricing_service_with_data):
        """Test version suffix stripping."""
        service = pricing_service_with_data

        # Test various version patterns
        assert service._strip_version_suffix("gpt-5-2024-10-01") == "gpt-5"
        assert service._strip_version_suffix("gpt-5-v1") == "gpt-5"
        assert service._strip_version_suffix("gpt-5-beta") == "gpt-5"
        assert service._strip_version_suffix("gpt-5") == "gpt-5"  # No suffix

    def test_get_model_pricing_exact_match(self, pricing_service_with_data):
        """Test getting pricing for exact model match."""
        service = pricing_service_with_data

        pricing = service._get_model_pricing("openai", "gpt-5")
        assert pricing is not None
        assert pricing["input_usd_per_million"] == 1.25

    def test_get_model_pricing_versioned(self, pricing_service_with_data):
        """Test getting pricing for versioned model."""
        service = pricing_service_with_data

        # Should match base model after stripping version
        pricing = service._get_model_pricing("openai", "gpt-5-2024-10-01")
        assert pricing is not None
        assert pricing["input_usd_per_million"] == 1.25

    def test_get_model_pricing_not_found(self, pricing_service_with_data):
        """Test getting pricing for non-existent model."""
        service = pricing_service_with_data

        pricing = service._get_model_pricing("openai", "non-existent-model")
        assert pricing is None

    def test_calculate_cost_basic(self, pricing_service_with_data):
        """Test basic cost calculation."""
        service = pricing_service_with_data

        cost = service.calculate_cost(
            model="openai/gpt-5",
            prompt_tokens=1000,
            completion_tokens=500,
            cached_tokens=0)

        # Expected: (1000 * 1.25 + 0 * 0.125 + 500 * 10.00) / 1_000_000
        expected = (1000 * 1.25 + 500 * 10.00) / 1_000_000
        assert cost == pytest.approx(expected, rel=1e-6)

    def test_calculate_cost_with_cached_tokens(self, pricing_service_with_data):
        """Test cost calculation with cached tokens."""
        service = pricing_service_with_data

        cost = service.calculate_cost(
            model="openai/gpt-5",
            prompt_tokens=1000,
            completion_tokens=500,
            cached_tokens=200)

        # Expected: (800 * 1.25 + 200 * 0.125 + 500 * 10.00) / 1_000_000
        expected = (800 * 1.25 + 200 * 0.125 + 500 * 10.00) / 1_000_000
        assert cost == pytest.approx(expected, rel=1e-6)

    def test_calculate_cost_gemini_default_pricing(self, pricing_service_with_data):
        """Test Gemini cost calculation with default pricing."""
        service = pricing_service_with_data

        cost = service.calculate_cost(
            model="google/gemini-2.5-pro",
            prompt_tokens=100000,  # Below threshold
            completion_tokens=5000,
            cached_tokens=0)

        # Expected: (100000 * 1.25 + 5000 * 10.00) / 1_000_000
        expected = (100000 * 1.25 + 5000 * 10.00) / 1_000_000
        assert cost == pytest.approx(expected, rel=1e-6)

    def test_calculate_cost_gemini_long_context_pricing(self, pricing_service_with_data):
        """Test Gemini cost calculation with long context pricing."""
        service = pricing_service_with_data

        cost = service.calculate_cost(
            model="google/gemini-2.5-pro",
            prompt_tokens=250000,  # Above threshold
            completion_tokens=10000,
            cached_tokens=0)

        # Expected: (250000 * 2.50 + 10000 * 15.00) / 1_000_000
        expected = (250000 * 2.50 + 10000 * 15.00) / 1_000_000
        assert cost == pytest.approx(expected, rel=1e-6)

    def test_calculate_cost_provider_prefixed_model(self, pricing_service_with_data):
        """Test cost calculation with provider-prefixed model."""
        service = pricing_service_with_data

        cost = service.calculate_cost(
            model="openai/gpt-5",
            prompt_tokens=1000,
            completion_tokens=500,
            cached_tokens=0)

        expected = (1000 * 1.25 + 500 * 10.00) / 1_000_000
        assert cost == pytest.approx(expected, rel=1e-6)

    def test_calculate_cost_missing_tokens(self, pricing_service_with_data):
        """Test cost calculation with missing token data."""
        service = pricing_service_with_data

        # Missing prompt_tokens
        cost = service.calculate_cost(
            model="openai/gpt-5",
            prompt_tokens=None,
            completion_tokens=500)
        assert cost is None

        # Missing completion_tokens
        cost = service.calculate_cost(
            model="openai/gpt-5",
            prompt_tokens=1000,
            completion_tokens=None)
        assert cost is None

    def test_calculate_cost_negative_tokens(self, pricing_service_with_data):
        """Test cost calculation with negative token counts."""
        service = pricing_service_with_data

        # Negative prompt_tokens
        cost = service.calculate_cost(
            model="openai/gpt-5",
            prompt_tokens=-100,
            completion_tokens=500)
        assert cost is None

        # Negative completion_tokens
        cost = service.calculate_cost(
            model="openai/gpt-5",
            prompt_tokens=1000,
            completion_tokens=-50)
        assert cost is None

    def test_calculate_cost_unknown_model(self, pricing_service_with_data):
        """Test cost calculation for unknown model."""
        service = pricing_service_with_data

        with patch("app.services.pricing_service.logger") as mock_logger:
            cost = service.calculate_cost(
                model="unknown-model",
                prompt_tokens=1000,
                completion_tokens=500)
            assert cost is None
            mock_logger.warning.assert_called()

    def test_calculate_cost_missing_pricing_data(self, pricing_service_with_data):
        """Test cost calculation when pricing data is missing."""
        service = pricing_service_with_data
        service._pricing_data = {}  # Clear pricing data

        cost = service.calculate_cost(
            model="openai/gpt-5",
            prompt_tokens=1000,
            completion_tokens=500)
        assert cost is None

    def test_get_available_models(self, pricing_service_with_data):
        """Test getting available models by provider."""
        service = pricing_service_with_data

        models = service.get_available_models()

        assert "openai" in models
        assert "openai/gpt-5" in models["openai"]
        assert "openai/gpt-5-mini" in models["openai"]

        assert "anthropic" in models
        assert "anthropic/claude-sonnet-4" in models["anthropic"]

        assert "google" in models
        assert "google/gemini-2.5-pro" in models["google"]

    def test_get_available_models_empty_data(self):
        """Test getting available models with empty pricing data."""
        service = PricingService()
        service._pricing_data = {}

        models = service.get_available_models()
        assert models == {}

    def test_calculate_gemini_cost_method(self, pricing_service_with_data):
        """Test the internal _calculate_gemini_cost method."""
        service = pricing_service_with_data

        pricing = {
            "long_context_threshold_tokens": 200000,
            "input_usd_per_million": {"default": 1.0, "long_context": 2.0},
            "cached_input_usd_per_million": {"default": 0.1, "long_context": 0.2},
            "output_usd_per_million": {"default": 5.0, "long_context": 10.0},
        }

        # Test default pricing
        cost = service._calculate_gemini_cost(pricing, 100000, 1000, 0)
        expected = (100000 * 1.0 + 1000 * 5.0) / 1_000_000
        assert cost == pytest.approx(expected, rel=1e-6)

        # Test long context pricing
        cost = service._calculate_gemini_cost(pricing, 250000, 2000, 5000)
        expected = (245000 * 2.0 + 5000 * 0.2 + 2000 * 10.0) / 1_000_000
        assert cost == pytest.approx(expected, rel=1e-6)
