"""Tests for pricing service edge cases and error handling."""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open

from app.services.pricing_service import PricingService


class TestPricingEdgeCases:
    """Test edge cases and error handling for pricing service."""

    def test_missing_models_yaml_file(self):
        """Test behavior when models.yaml file is missing."""
        with patch('app.services.pricing_service.logger') as mock_logger:
            service = PricingService("/non/existent/path/models.yaml")
            assert service._pricing_data == {}
            mock_logger.error.assert_called_once()

    def test_invalid_yaml_file(self):
        """Test behavior when models.yaml file has invalid YAML."""
        invalid_yaml = "invalid: yaml: content: ["
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_yaml)
            temp_path = f.name
        
        try:
            with patch('app.services.pricing_service.logger') as mock_logger:
                service = PricingService(temp_path)
                assert service._pricing_data == {}
                mock_logger.error.assert_called_once()
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_empty_yaml_file(self):
        """Test behavior with empty YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("")
            temp_path = f.name
        
        try:
            service = PricingService(temp_path)
            assert service._pricing_data is None
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_missing_providers_key(self):
        """Test behavior when YAML is missing 'providers' key."""
        invalid_data = {"not_providers": {}}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(invalid_data, f)
            temp_path = f.name
        
        try:
            service = PricingService(temp_path)
            cost = service.calculate_cost("gpt-5", 1000, 500)
            assert cost is None
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_missing_models_key(self):
        """Test behavior when provider is missing 'models' key."""
        invalid_data = {
            "providers": {
                "openai": {
                    "display_name": "OpenAI"
                    # Missing 'models' key
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(invalid_data, f)
            temp_path = f.name
        
        try:
            service = PricingService(temp_path)
            cost = service.calculate_cost("gpt-5", 1000, 500)
            assert cost is None
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_missing_pricing_fields(self):
        """Test behavior when model pricing is missing required fields."""
        incomplete_data = {
            "providers": {
                "openai": {
                    "models": {
                        "gpt-5": {
                            "input_usd_per_million": 1.25
                            # Missing output_usd_per_million
                        }
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(incomplete_data, f)
            temp_path = f.name
        
        try:
            with patch('app.services.pricing_service.logger') as mock_logger:
                service = PricingService(temp_path)
                cost = service.calculate_cost("gpt-5", 1000, 500)
                assert cost is None
                mock_logger.error.assert_called_once()
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_gemini_missing_threshold_fields(self):
        """Test Gemini pricing with missing threshold fields."""
        incomplete_gemini_data = {
            "providers": {
                "google": {
                    "models": {
                        "gemini-2.5-pro": {
                            "long_context_threshold_tokens": 200000,
                            "input_usd_per_million": {
                                "default": 1.25
                                # Missing long_context
                            },
                            "cached_input_usd_per_million": {
                                "default": 0.125,
                                "long_context": 0.250,
                            },
                            "output_usd_per_million": {
                                "default": 10.00,
                                "long_context": 15.00,
                            },
                        }
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(incomplete_gemini_data, f)
            temp_path = f.name
        
        try:
            with patch('app.services.pricing_service.logger') as mock_logger:
                service = PricingService(temp_path)
                cost = service.calculate_cost("gemini-2.5-pro", 250000, 10000)
                assert cost is None
                mock_logger.error.assert_called_once()
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_zero_tokens(self):
        """Test cost calculation with zero tokens."""
        complete_data = {
            "providers": {
                "openai": {
                    "models": {
                        "gpt-5": {
                            "input_usd_per_million": 1.25,
                            "cached_input_usd_per_million": 0.125,
                            "output_usd_per_million": 10.00,
                        }
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(complete_data, f)
            temp_path = f.name
        
        try:
            service = PricingService(temp_path)
            
            # Zero tokens should return zero cost
            cost = service.calculate_cost("gpt-5", 0, 0, 0)
            assert cost == 0.0
            
            # Zero prompt tokens, non-zero completion
            cost = service.calculate_cost("gpt-5", 0, 100, 0)
            assert cost == 0.001  # 100 * 10.00 / 1_000_000
            
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_very_large_token_counts(self):
        """Test cost calculation with very large token counts."""
        complete_data = {
            "providers": {
                "openai": {
                    "models": {
                        "gpt-5": {
                            "input_usd_per_million": 1.25,
                            "cached_input_usd_per_million": 0.125,
                            "output_usd_per_million": 10.00,
                        }
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(complete_data, f)
            temp_path = f.name
        
        try:
            service = PricingService(temp_path)
            
            # Very large token counts
            cost = service.calculate_cost("gpt-5", 1000000, 500000, 100000)
            expected = (900000 * 1.25 + 100000 * 0.125 + 500000 * 10.00) / 1_000_000
            assert cost == pytest.approx(expected, rel=1e-6)
            
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_cached_tokens_exceed_prompt_tokens(self):
        """Test behavior when cached tokens exceed prompt tokens."""
        complete_data = {
            "providers": {
                "openai": {
                    "models": {
                        "gpt-5": {
                            "input_usd_per_million": 1.25,
                            "cached_input_usd_per_million": 0.125,
                            "output_usd_per_million": 10.00,
                        }
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(complete_data, f)
            temp_path = f.name
        
        try:
            service = PricingService(temp_path)
            
            # Cached tokens exceed prompt tokens (edge case)
            cost = service.calculate_cost("gpt-5", 100, 50, 150)
            # Should handle gracefully: input_tokens = 100 - 150 = -50, but we don't allow negative
            # The service should handle this by treating it as 0 input tokens
            expected = (0 * 1.25 + 150 * 0.125 + 50 * 10.00) / 1_000_000
            assert cost == pytest.approx(expected, rel=1e-6)
            
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_gemini_exactly_at_threshold(self):
        """Test Gemini pricing exactly at the threshold."""
        gemini_data = {
            "providers": {
                "google": {
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
                        }
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(gemini_data, f)
            temp_path = f.name
        
        try:
            service = PricingService(temp_path)
            
            # Exactly at threshold should use default pricing
            cost = service.calculate_cost("gemini-2.5-pro", 200000, 1000, 0)
            expected = (200000 * 1.25 + 1000 * 10.00) / 1_000_000
            assert cost == pytest.approx(expected, rel=1e-6)
            
            # Just above threshold should use long context pricing
            cost = service.calculate_cost("gemini-2.5-pro", 200001, 1000, 0)
            expected = (200001 * 2.50 + 1000 * 15.00) / 1_000_000
            assert cost == pytest.approx(expected, rel=1e-6)
            
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_model_name_with_special_characters(self):
        """Test model name resolution with special characters."""
        complete_data = {
            "providers": {
                "openai": {
                    "models": {
                        "gpt-5": {
                            "input_usd_per_million": 1.25,
                            "cached_input_usd_per_million": 0.125,
                            "output_usd_per_million": 10.00,
                        }
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(complete_data, f)
            temp_path = f.name
        
        try:
            service = PricingService(temp_path)
            
            # Test various special character patterns
            test_cases = [
                "gpt-5-v1.0",
                "gpt-5-beta-2024",
                "gpt-5-alpha-2024-01-01",
                "gpt-5-rc1",
            ]
            
            for model_name in test_cases:
                cost = service.calculate_cost(model_name, 1000, 500)
                # Should match base model "gpt-5"
                expected = (1000 * 1.25 + 500 * 10.00) / 1_000_000
                assert cost == pytest.approx(expected, rel=1e-6)
            
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_pricing_service_reload(self):
        """Test that pricing service can reload data."""
        initial_data = {
            "providers": {
                "openai": {
                    "models": {
                        "gpt-5": {
                            "input_usd_per_million": 1.25,
                            "cached_input_usd_per_million": 0.125,
                            "output_usd_per_million": 10.00,
                        }
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(initial_data, f)
            temp_path = f.name
        
        try:
            service = PricingService(temp_path)
            
            # Initial cost calculation
            cost = service.calculate_cost("gpt-5", 1000, 500)
            expected = (1000 * 1.25 + 500 * 10.00) / 1_000_000
            assert cost == pytest.approx(expected, rel=1e-6)
            
            # Update the file
            updated_data = {
                "providers": {
                    "openai": {
                        "models": {
                            "gpt-5": {
                                "input_usd_per_million": 2.50,  # Doubled price
                                "cached_input_usd_per_million": 0.25,
                                "output_usd_per_million": 20.00,
                            }
                        }
                    }
                }
            }
            
            with open(temp_path, 'w') as f:
                yaml.dump(updated_data, f)
            
            # Reload data
            service._load_pricing_data()
            
            # New cost calculation should reflect updated pricing
            cost = service.calculate_cost("gpt-5", 1000, 500)
            expected = (1000 * 2.50 + 500 * 20.00) / 1_000_000
            assert cost == pytest.approx(expected, rel=1e-6)
            
        finally:
            Path(temp_path).unlink(missing_ok=True)
