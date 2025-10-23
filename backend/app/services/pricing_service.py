"""Pricing service for calculating AI model execution costs."""

import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)


class PricingService:
    """Service for calculating execution costs based on model pricing."""

    def __init__(self, models_yaml_path: str | None = None):
        """Initialize pricing service with models.yaml path."""
        if models_yaml_path is None:
            # Default to models.yaml in the backend directory
            backend_dir = Path(__file__).parent.parent.parent
            models_yaml_path = backend_dir / "models.yaml"
        
        self.models_yaml_path = Path(models_yaml_path)
        self._pricing_data: Dict[str, Any] = {}
        self._load_pricing_data()

    def _load_pricing_data(self) -> None:
        """Load pricing data from models.yaml file."""
        try:
            with open(self.models_yaml_path, 'r', encoding='utf-8') as f:
                self._pricing_data = yaml.safe_load(f)
            logger.info(f"Loaded pricing data from {self.models_yaml_path}")
        except FileNotFoundError:
            logger.error(f"Pricing file not found: {self.models_yaml_path}")
            self._pricing_data = {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing pricing file: {e}")
            self._pricing_data = {}

    def _resolve_model_name(self, model: str) -> Tuple[str, str]:
        """
        Resolve model name to provider and model name.
        
        Handles:
        - Exact match: "gpt-5" -> ("openai", "gpt-5")
        - Versioned models: "gpt-5-2024-10-01" -> ("openai", "gpt-5")
        - Provider prefixed: "openai/gpt-5" -> ("openai", "gpt-5")
        
        Returns:
            Tuple of (provider, model_name)
        """
        # Handle provider prefixed models (e.g., "openai/gpt-5")
        if '/' in model:
            provider, model_name = model.split('/', 1)
            return provider, model_name
        
        # Try to infer provider from model name patterns
        model_lower = model.lower()
        
        # OpenAI models
        if model_lower.startswith(('gpt-', 'o1', 'o3')):
            return "openai", model
        
        # Anthropic models
        if model_lower.startswith(('claude-', 'claude')):
            return "anthropic", model
        
        # Google models
        if model_lower.startswith(('gemini-', 'gemini')):
            return "google", model
        
        # xAI/Grok models
        if model_lower.startswith(('grok-', 'grok')):
            return "grok", model
        
        # Default to openai if no pattern matches
        logger.warning(f"Could not infer provider for model '{model}', defaulting to 'openai'")
        return "openai", model

    def _strip_version_suffix(self, model_name: str) -> str:
        """Remove version suffix from model name (e.g., 'gpt-5-2024-10-01' -> 'gpt-5')."""
        # Pattern to match version suffixes like -2024-10-01, -v1, -beta, etc.
        # Be more specific to avoid matching model version numbers like -5
        version_pattern = r'-\d{4}-\d{2}-\d{2}$|-\d{4}-\d{2}$|-\d{4}$|-[a-zA-Z]+[\d.-]*$'
        return re.sub(version_pattern, '', model_name)

    def _get_model_pricing(self, provider: str, model_name: str) -> Optional[Dict[str, Any]]:
        """Get pricing information for a specific model."""
        if not self._pricing_data or 'providers' not in self._pricing_data:
            return None
        
        providers = self._pricing_data['providers']
        if provider not in providers:
            return None
        
        provider_data = providers[provider]
        if 'models' not in provider_data:
            return None
        
        models = provider_data['models']
        
        # Try exact match first
        if model_name in models:
            return models[model_name]
        
        # Try without version suffix
        base_model = self._strip_version_suffix(model_name)
        if base_model != model_name and base_model in models:
            return models[base_model]
        
        return None

    def _calculate_gemini_cost(
        self, 
        pricing: Dict[str, Any], 
        prompt_tokens: int, 
        completion_tokens: int,
        cached_tokens: int = 0
    ) -> float:
        """Calculate cost for Gemini models with threshold-based pricing."""
        # Check if this is a Gemini model with threshold pricing
        threshold = pricing.get('long_context_threshold_tokens')
        if threshold is None:
            # Use simple pricing
            input_rate = pricing['input_usd_per_million']
            output_rate = pricing['output_usd_per_million']
            cached_rate = pricing.get('cached_input_usd_per_million', 0)
        else:
            # Use threshold-based pricing
            if prompt_tokens > threshold:
                # Long context pricing
                input_rate = pricing['input_usd_per_million']['long_context']
                output_rate = pricing['output_usd_per_million']['long_context']
                cached_rate = pricing['cached_input_usd_per_million']['long_context']
            else:
                # Default pricing
                input_rate = pricing['input_usd_per_million']['default']
                output_rate = pricing['output_usd_per_million']['default']
                cached_rate = pricing['cached_input_usd_per_million']['default']
        
        # Calculate costs
        input_tokens = max(0, prompt_tokens - cached_tokens)  # Ensure non-negative
        input_cost = (input_tokens * input_rate) / 1_000_000
        cached_cost = (cached_tokens * cached_rate) / 1_000_000
        output_cost = (completion_tokens * output_rate) / 1_000_000
        
        return input_cost + cached_cost + output_cost

    def calculate_cost(
        self,
        model: str,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        cached_tokens: int | None = None,
    ) -> Optional[float]:
        """
        Calculate execution cost based on token usage and model pricing.
        
        Args:
            model: Model name (e.g., "gpt-5", "openai/gpt-5", "gpt-5-2024-10-01")
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            cached_tokens: Number of cached tokens (optional)
            
        Returns:
            Total cost in USD, or None if pricing unavailable
        """
        if prompt_tokens is None or completion_tokens is None:
            logger.warning("Missing required token counts for cost calculation")
            return None
        
        if prompt_tokens < 0 or completion_tokens < 0:
            logger.warning("Invalid token counts (negative values)")
            return None
        
        cached_tokens = cached_tokens or 0
        if cached_tokens < 0:
            logger.warning("Invalid cached token count (negative value)")
            return None
        
        # Resolve model name to provider and model
        provider, model_name = self._resolve_model_name(model)
        
        # Get pricing information
        pricing = self._get_model_pricing(provider, model_name)
        if not pricing:
            logger.warning(f"No pricing data found for model '{model}' (provider: {provider}, model: {model_name})")
            return None
        
        try:
            # Handle Gemini models with threshold pricing
            if provider == "google" and "long_context_threshold_tokens" in pricing:
                return self._calculate_gemini_cost(pricing, prompt_tokens, completion_tokens, cached_tokens)
            
            # Standard pricing calculation
            input_rate = pricing['input_usd_per_million']
            output_rate = pricing['output_usd_per_million']
            cached_rate = pricing.get('cached_input_usd_per_million', 0)
            
            # Calculate costs
            input_tokens = max(0, prompt_tokens - cached_tokens)  # Ensure non-negative
            input_cost = (input_tokens * input_rate) / 1_000_000
            cached_cost = (cached_tokens * cached_rate) / 1_000_000
            output_cost = (completion_tokens * output_rate) / 1_000_000
            
            total_cost = input_cost + cached_cost + output_cost
            logger.debug(f"Cost calculation for {model}: input={input_cost:.6f}, cached={cached_cost:.6f}, output={output_cost:.6f}, total={total_cost:.6f}")
            
            return total_cost
            
        except KeyError as e:
            logger.error(f"Missing pricing field for model '{model}': {e}")
            return None
        except Exception as e:
            logger.error(f"Error calculating cost for model '{model}': {e}")
            return None

    def get_available_models(self) -> Dict[str, list[str]]:
        """Get list of available models by provider."""
        if not self._pricing_data or 'providers' not in self._pricing_data:
            return {}
        
        result = {}
        for provider, provider_data in self._pricing_data['providers'].items():
            if 'models' in provider_data:
                result[provider] = list(provider_data['models'].keys())
        
        return result
