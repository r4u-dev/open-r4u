"""Statistical utility functions."""

import math
import statistics
from collections.abc import Sequence
from datetime import UTC, datetime


def calculate_percentile(values: Sequence[float], percentile: float) -> float | None:
    """Calculate the given percentile of a sequence of values.

    Args:
        values: Sequence of numeric values
        percentile: Percentile to calculate (0-100)

    Returns:
        The percentile value, or None if values is empty

    Raises:
        ValueError: If percentile is not between 0 and 100

    Examples:
        >>> calculate_percentile([1, 2, 3, 4, 5], 50)
        3.0
        >>> calculate_percentile([1, 2, 3, 4, 5], 95)
        4.8
        >>> calculate_percentile([], 50)
        None

    """
    if not values:
        return None

    if not 0 <= percentile <= 100:
        raise ValueError("Percentile must be between 0 and 100")

    # Convert to list and sort
    sorted_values = sorted(values)

    # Use quantiles for percentile calculation
    # quantiles expects a value between 0 and 1
    if len(sorted_values) == 1:
        return float(sorted_values[0])

    # For single value, return it
    try:
        result = statistics.quantiles(sorted_values, n=100, method="inclusive")
        # quantiles returns n-1 cut points, so for n=100 we get 99 values
        # representing percentiles 1-99
        if percentile == 0:
            return float(sorted_values[0])
        if percentile == 100:
            return float(sorted_values[-1])
        # percentile is 1-100, index is 0-98
        index = int(percentile) - 1
        return float(result[index])
    except statistics.StatisticsError:
        # Fallback for edge cases
        return float(sorted_values[0])


def calculate_time_decay_weight(
    trace_time: datetime,
    reference_time: datetime | None = None,
    half_life_hours: float = 168.0,
) -> float:
    """Calculate exponential decay weight based on trace age.

    Uses half-life decay: weight = 0.5^(age_hours / half_life_hours)

    Args:
        trace_time: Timestamp of the trace
        reference_time: Reference time (defaults to now)
        half_life_hours: Hours for weight to decay to 50% (default: 168 = 7 days)

    Returns:
        Weight between 0 and 1 (recent traces have weight closer to 1)

    Examples:
        >>> now = datetime.now(UTC)
        >>> calculate_time_decay_weight(now, now, half_life_hours=168)
        1.0
        >>> week_ago = now - timedelta(hours=168)
        >>> calculate_time_decay_weight(week_ago, now, half_life_hours=168)
        0.5

    """
    if reference_time is None:
        reference_time = datetime.now(UTC)

    # Ensure both datetimes are timezone-aware for comparison
    if trace_time.tzinfo is None:
        trace_time = trace_time.replace(tzinfo=UTC)
    if reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=UTC)

    # Calculate age in hours
    age = (reference_time - trace_time).total_seconds() / 3600

    # Exponential decay using half-life
    # weight = 0.5^(age / half_life)
    weight = math.pow(0.5, age / half_life_hours)

    return weight


def calculate_weighted_percentile(
    values: Sequence[float],
    weights: Sequence[float],
    percentile: float,
) -> float | None:
    """Calculate weighted percentile of values.

    Args:
        values: Sequence of numeric values
        weights: Sequence of weights corresponding to each value
        percentile: Percentile to calculate (0-100)

    Returns:
        The weighted percentile value, or None if values is empty

    Raises:
        ValueError: If percentile is not between 0 and 100, or if lengths don't match

    Examples:
        >>> values = [1.0, 2.0, 3.0, 4.0, 5.0]
        >>> weights = [1.0, 1.0, 1.0, 1.0, 1.0]  # Equal weights
        >>> calculate_weighted_percentile(values, weights, 50)
        3.0
        >>> # Recent values weighted more heavily
        >>> weights = [0.5, 0.7, 0.9, 1.0, 1.0]
        >>> calculate_weighted_percentile(values, weights, 50)
        # Will be closer to higher values

    """
    if not values:
        return None

    if not 0 <= percentile <= 100:
        raise ValueError("Percentile must be between 0 and 100")

    if len(values) != len(weights):
        raise ValueError("Values and weights must have the same length")

    # Sort values and weights together
    sorted_pairs = sorted(zip(values, weights), key=lambda x: x[0])
    sorted_values = [v for v, _ in sorted_pairs]
    sorted_weights = [w for _, w in sorted_pairs]

    # Calculate cumulative weights
    total_weight = sum(sorted_weights)
    if total_weight == 0:
        return None

    cumulative_weights = []
    cumsum = 0
    for w in sorted_weights:
        cumsum += w
        cumulative_weights.append(cumsum / total_weight * 100)

    # Find the value at the desired percentile
    target_percentile = percentile

    # Handle edge cases
    if target_percentile <= 0:
        return float(sorted_values[0])
    if target_percentile >= 100:
        return float(sorted_values[-1])

    # Find the index where cumulative weight crosses the target percentile
    for i, cum_weight in enumerate(cumulative_weights):
        if cum_weight >= target_percentile:
            if i == 0:
                return float(sorted_values[0])

            # Linear interpolation between adjacent values
            prev_weight = cumulative_weights[i - 1] if i > 0 else 0
            weight_range = cum_weight - prev_weight

            if weight_range == 0:
                return float(sorted_values[i])

            # How far between the two values?
            fraction = (target_percentile - prev_weight) / weight_range
            value_range = sorted_values[i] - sorted_values[i - 1]
            return float(sorted_values[i - 1] + fraction * value_range)

    return float(sorted_values[-1])
