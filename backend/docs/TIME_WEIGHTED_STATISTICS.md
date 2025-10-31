# Time-Weighted Statistics - Quick Reference

## Overview

Open R4U's task statistics use **exponential time decay** to weight traces by recency. This means **recent traces have exponentially more impact** on calculated metrics than older traces, ensuring your statistics reflect current performance rather than historical data.

## Key Concept: Half-Life Decay

```
weight = 0.5^(age_hours / half_life_hours)
```

**Half-life** is the time it takes for a trace's weight to decay to 50% of its original value.

### Default Configuration

- **Half-life**: 168 hours (7 days)
- A trace from 1 week ago: **50% weight**
- A trace from 2 weeks ago: **25% weight**
- A trace from 3 weeks ago: **12.5% weight**

## Why Time Weighting?

| Without Time Weighting | With Time Weighting |
|------------------------|---------------------|
| Historical outliers skew metrics | Recent performance dominates |
| Stale data affects decisions | Metrics reflect current state |
| Can't detect recent regressions | Automatically adapts to changes |
| Equal weight to 6-month-old traces | Old traces have minimal impact |

## API Quick Start

### Get Task with Recent Performance Metrics

```bash
# Default: 7-day half-life, 95th percentile
GET /v1/tasks/123?percentile=95&half_life_hours=168
```

### Focus on Last 24 Hours

```bash
# Aggressive recency bias (yesterday = 50% weight)
GET /v1/tasks/123?percentile=95&half_life_hours=24
```

### Include More Historical Data

```bash
# Slower decay (30 days ago = 50% weight)
GET /v1/tasks/123?percentile=95&half_life_hours=720
```

## Half-Life Selection Guide

| Half-Life | Use Case | Example |
|-----------|----------|---------|
| **1 hour** | Real-time alerting | Detect immediate performance issues |
| **24 hours** | Daily monitoring | "How is this task performing today?" |
| **168 hours (7 days)** | Weekly trends (default) | Balanced view of recent performance |
| **720 hours (30 days)** | Monthly baselines | Include seasonal patterns |

### Rules of Thumb

- **Short half-life (< 48h)**: Use for real-time monitoring and quick drift detection
- **Medium half-life (7-14 days)**: Use for general performance metrics and SLA monitoring
- **Long half-life (> 30 days)**: Use for capacity planning and long-term trends

## Common Patterns

### Pattern 1: Real-Time Monitoring

```python
# Monitor current performance with aggressive recency bias
task, cost_percentile, latency_percentile = await service.get_task_with_percentiles(
    task_id=123,
    percentile=95,
    half_life_hours=24.0  # Yesterday's traces = 50% weight
)

if latency_percentile > SLA_THRESHOLD:
    alert("Task 123 currently exceeds SLA!")
```

### Pattern 2: Detect Performance Drift

```python
# Compare recent vs historical performance
_, cost_recent, _ = await service.get_task_with_percentiles(
    task_id=123,
    percentile=95,
    half_life_hours=24.0  # Recent
)

_, cost_baseline, _ = await service.get_task_with_percentiles(
    task_id=123,
    percentile=95,
    half_life_hours=720.0  # Historical
)

drift_pct = (cost_recent - cost_baseline) / cost_baseline * 100
if drift_pct > 20:
    alert(f"Cost increased {drift_pct:.1f}% recently!")
```

### Pattern 3: Dashboard Metrics

```python
# Show different time windows on dashboard
task_stats = {
    "last_hour": await service.get_task_with_percentiles(
        task_id=123, percentile=95, half_life_hours=1.0
    ),
    "last_day": await service.get_task_with_percentiles(
        task_id=123, percentile=95, half_life_hours=24.0
    ),
    "last_week": await service.get_task_with_percentiles(
        task_id=123, percentile=95, half_life_hours=168.0
    ),
}
```

## Weight Examples

### Example 1: 24-Hour Half-Life

| Trace Age | Weight | Impact |
|-----------|--------|--------|
| Now | 100% | Full weight |
| 12 hours ago | 71% | Strong impact |
| 24 hours ago | 50% | Half weight |
| 2 days ago | 25% | Reduced impact |
| 4 days ago | 6% | Minimal impact |

### Example 2: 7-Day Half-Life (Default)

| Trace Age | Weight | Impact |
|-----------|--------|--------|
| Now | 100% | Full weight |
| 3.5 days ago | 71% | Strong impact |
| 7 days ago | 50% | Half weight |
| 14 days ago | 25% | Reduced impact |
| 28 days ago | 6% | Minimal impact |

### Example 3: 30-Day Half-Life

| Trace Age | Weight | Impact |
|-----------|--------|--------|
| Now | 100% | Full weight |
| 15 days ago | 71% | Strong impact |
| 30 days ago | 50% | Half weight |
| 60 days ago | 25% | Reduced impact |
| 120 days ago | 6% | Minimal impact |

## Comparison: Weighted vs Unweighted

### Scenario: Recent Performance Degradation

**Traces:**
- 100 old traces: 0.5s latency (6 months ago)
- 10 new traces: 5.0s latency (last week)

**Unweighted P95:**
- All traces equal → P95 ≈ 0.5s (misleading!)

**Weighted P95 (7-day half-life):**
- Old traces have ~1% weight
- New traces have ~100% weight
- P95 ≈ 5.0s (reflects current state!)

## Service Layer Examples

### Example 1: List Expensive Tasks (Recent)

```python
service = TaskService(session)

# Focus on recent costs
tasks_with_stats = await service.list_tasks_with_percentiles(
    project_id=1,
    percentile=95,
    half_life_hours=24.0  # Last 24 hours
)

# Sort by recent cost
expensive_tasks = sorted(
    tasks_with_stats,
    key=lambda x: x[1] or 0,  # cost_percentile
    reverse=True
)

for task, cost_percentile, latency_percentile in expensive_tasks[:10]:
    print(f"{task.name}:")
    print(f"  Cost Percentile (24h): ${cost_percentile:.4f}")
    print(f"  Latency Percentile (24h): {latency_percentile:.2f}s")
```

### Example 2: SLA Monitoring

```python
# Check if current performance meets SLAs
SLA_LATENCY = 2.0  # seconds
SLA_COST = 0.10  # USD

task, cost_percentile, latency_percentile = await service.get_task_with_percentiles(
    task_id=123,
    percentile=95,
    half_life_hours=1.0  # Real-time view
)

sla_violations = []
if latency_percentile and latency_percentile > SLA_LATENCY:
    sla_violations.append(f"Latency: {latency_percentile:.2f}s > {SLA_LATENCY}s")
if cost_percentile and cost_percentile > SLA_COST:
    sla_violations.append(f"Cost: ${cost_percentile:.4f} > ${SLA_COST}")

if sla_violations:
    alert(f"Task {task.name} SLA violations: {', '.join(sla_violations)}")
```

### Example 3: Multi-Timescale Analysis

```python
# Analyze performance at different timescales
timescales = {
    "realtime": 1.0,      # 1 hour
    "daily": 24.0,        # 1 day
    "weekly": 168.0,      # 7 days
    "monthly": 720.0,     # 30 days
}

results = {}
for scale_name, half_life in timescales.items():
    _, cost, latency = await service.get_task_with_percentiles(
        task_id=123,
        percentile=95,
        half_life_hours=half_life
    )
    results[scale_name] = {"cost": cost, "latency": latency}

print("Performance across timescales:")
for scale, metrics in results.items():
    print(f"  {scale:10s}: ${metrics['cost']:.4f}, {metrics['latency']:.2f}s")

# Detect if recent performance is worse than baseline
if results["realtime"]["cost"] > results["monthly"]["cost"] * 1.5:
    alert("Real-time cost is 50% higher than monthly baseline!")
```

## Utility Functions

### Calculate Time Decay Weight

```python
from app.utils.statistics import calculate_time_decay_weight
from datetime import datetime, timedelta, UTC

now = datetime.now(UTC)
week_ago = now - timedelta(hours=168)

weight = calculate_time_decay_weight(
    trace_time=week_ago,
    reference_time=now,
    half_life_hours=168.0
)
# Returns: 0.5 (50% weight)
```

### Calculate Weighted Percentile

```python
from app.utils.statistics import calculate_weighted_percentile

# Values from traces (e.g., costs)
values = [0.01, 0.02, 0.05, 0.10, 0.15]

# Weights based on trace age
weights = [0.25, 0.5, 0.7, 0.9, 1.0]  # Recent = higher weight

p95 = calculate_weighted_percentile(values, weights, 95)
# Returns: Value closer to recent traces
```

## Testing

Run tests specific to time-weighted calculations:

```bash
# All time-weighted tests
uv run pytest tests/test_task_statistics.py -k "weighted" -v

# Time decay tests
uv run pytest tests/test_task_statistics.py -k "time_decay" -v

# Specific scenarios
uv run pytest tests/test_task_statistics.py::test_time_weighted_cost_percentile -v
uv run pytest tests/test_task_statistics.py::test_time_weighted_latency_percentile -v
```

## Best Practices

### ✅ DO

- Use **short half-life (24h)** for alerting and real-time monitoring
- Use **medium half-life (7 days)** for dashboards and general metrics
- Use **long half-life (30+ days)** for capacity planning and trends
- Compare multiple timescales to detect drift
- Set SLAs based on time-weighted metrics, not historical averages

### ❌ DON'T

- Don't use very long half-life (> 60 days) for operational metrics
- Don't compare weighted percentiles with different half-lives directly
- Don't ignore the half-life parameter - it significantly affects results
- Don't use time-weighted stats for historical analysis (use raw data instead)

## Troubleshooting

### Issue: Metrics seem too low

**Cause**: Half-life too short, old expensive/slow traces have minimal weight

**Solution**: Increase `half_life_hours` to include more historical data

```bash
# Instead of:
GET /v1/tasks/123?half_life_hours=24

# Try:
GET /v1/tasks/123?half_life_hours=168
```

### Issue: Metrics don't reflect recent changes

**Cause**: Half-life too long, old traces still dominate

**Solution**: Decrease `half_life_hours` for stronger recency bias

```bash
# Instead of:
GET /v1/tasks/123?half_life_hours=720

# Try:
GET /v1/tasks/123?half_life_hours=24
```

### Issue: Metrics are unstable

**Cause**: Not enough traces, or half-life too short with sparse data

**Solution**: Increase `half_life_hours` or wait for more traces

## Related Documentation

- [Task Statistics](./TASK_STATISTICS.md) - Complete documentation
- [API Reference](../README.md) - API endpoints
- [Testing Guide](../tests/test_task_statistics.py) - Test examples
