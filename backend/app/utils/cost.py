"""Cost calculation utilities for LLM traces."""

from app.models.traces import Trace
from app.services.pricing_service import PricingService

# Global pricing service instance
_pricing_service = PricingService()


def calculate_trace_cost(trace: Trace) -> float:
    """Calculate the cost of a trace in USD.

    Args:
        trace: Trace model instance with token usage data

    Returns:
        Cost in USD, or 0.0 if token data is not available or pricing unavailable

    """
    cost = _pricing_service.calculate_cost(
        model=trace.model,
        prompt_tokens=trace.prompt_tokens,
        completion_tokens=trace.completion_tokens,
        cached_tokens=trace.cached_tokens,
    )

    return cost if cost is not None else 0.0


def calculate_traces_cost(traces: list[Trace]) -> list[float]:
    """Calculate costs for multiple traces.

    Args:
        traces: List of Trace model instances

    Returns:
        List of costs in USD corresponding to each trace

    """
    return [calculate_trace_cost(trace) for trace in traces]
