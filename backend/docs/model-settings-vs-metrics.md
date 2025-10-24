# Model Settings vs Metrics Separation

## Overview

This document explains the separation of model settings from metrics in the R4U trace detail panel. Previously, token usage metrics were incorrectly grouped with model configuration settings. This has been corrected to provide better clarity and organization.

## Problem

The original implementation displayed token usage metrics (prompt_tokens, completion_tokens, total_tokens) in the "Model Settings" section. This was incorrect because:

1. **Token counts are metrics** - They measure the result of an API call, not configuration
2. **Settings are parameters** - They control how the model behaves before the call
3. **Confused semantics** - Mixing metrics with settings made it unclear what was configuration vs measurement

## Solution

Separated the data into two distinct categories:

### Model Settings

**Definition**: Parameters that control model behavior and are sent as part of the request.

**Examples**:

- `temperature`: Controls randomness (0.0 to 2.0)
- `max_tokens`: Maximum tokens in the response
- `tool_choice`: Which tools the model can use ("auto", "none", or specific tool)
- `top_p`: Nucleus sampling parameter
- `frequency_penalty`: Reduces repetition
- `presence_penalty`: Encourages new topics

### Metrics

**Definition**: Measurements and statistics from the API response.

**Examples**:

- `prompt_tokens`: Number of tokens in the input
- `completion_tokens`: Number of tokens in the output
- `total_tokens`: Sum of prompt and completion tokens
- `cached_tokens`: Tokens served from cache (if applicable)
- `reasoning_tokens`: Tokens used for reasoning (o1 models)

## Implementation

### Backend Schema

The trace model already had the correct fields defined in `app/models/traces.py`:

```python
# Request parameters (Model Settings)
temperature: Mapped[float | None]
tool_choice: Mapped[dict[str, Any] | None]
max_tokens: Mapped[int | None]

# Token usage (Metrics)
prompt_tokens: Mapped[int | None]
completion_tokens: Mapped[int | None]
total_tokens: Mapped[int | None]
cached_tokens: Mapped[int | None]
reasoning_tokens: Mapped[int | None]
```

No backend changes were needed - the schema was already correct.

### Frontend Changes

#### 1. Type Definitions

Updated `frontend/src/lib/types/trace.ts`:

```typescript
export interface Trace {
    // ... other fields
    modelSettings: Record<string, string | number | boolean>;
    metrics: Record<string, number>; // NEW!
    // ... other fields
}
```

#### 2. API Mapping

Updated `frontend/src/services/tracesApi.ts` to separate the data:

```typescript
// Build model settings (parameters that control model behavior)
const modelSettings: Record<string, string | number | boolean> = {};
if (backendTrace.temperature !== null) {
    modelSettings.temperature = backendTrace.temperature;
}
if (backendTrace.max_tokens !== null) {
    modelSettings.max_tokens = backendTrace.max_tokens;
}
if (backendTrace.tool_choice !== null) {
    modelSettings.tool_choice =
        typeof backendTrace.tool_choice === "string"
            ? backendTrace.tool_choice
            : JSON.stringify(backendTrace.tool_choice);
}

// Build metrics (usage and performance data)
const metrics: Record<string, number> = {};
if (backendTrace.prompt_tokens !== null) {
    metrics.prompt_tokens = backendTrace.prompt_tokens;
}
if (backendTrace.completion_tokens !== null) {
    metrics.completion_tokens = backendTrace.completion_tokens;
}
if (backendTrace.total_tokens !== null) {
    metrics.total_tokens = backendTrace.total_tokens;
}
if (backendTrace.cached_tokens !== null) {
    metrics.cached_tokens = backendTrace.cached_tokens;
}
if (backendTrace.reasoning_tokens !== null) {
    metrics.reasoning_tokens = backendTrace.reasoning_tokens;
}
```

#### 3. UI Component

Updated `frontend/src/components/trace/TraceDetailPanel.tsx`:

- **Model Settings Section**: Now only shows configuration parameters
- **Metrics Section**: New collapsible section for usage statistics

```typescript
<Section title="Model Settings" section="modelSettings">
    <div className="space-y-1 font-mono">
        {Object.keys(trace.modelSettings).length > 0 ? (
            Object.entries(trace.modelSettings).map(([key, value]) => (
                <div key={key} className="flex justify-between">
                    <span className="text-muted-foreground">{key}:</span>
                    <span className="text-foreground">{JSON.stringify(value)}</span>
                </div>
            ))
        ) : (
            <span className="text-muted-foreground italic">
                No model settings
            </span>
        )}
    </div>
</Section>

<Section title="Metrics" section="metrics">
    <div className="space-y-1 font-mono">
        {Object.keys(trace.metrics).length > 0 ? (
            Object.entries(trace.metrics).map(([key, value]) => (
                <div key={key} className="flex justify-between">
                    <span className="text-muted-foreground">{key}:</span>
                    <span className="text-foreground">{value.toLocaleString()}</span>
                </div>
            ))
        ) : (
            <span className="text-muted-foreground italic">
                No metrics available
            </span>
        )}
    </div>
</Section>
```

## User Experience

### Before (Incorrect)

```
┌─ Model Settings ──────────────┐
│ temperature: 0.7              │
│ prompt_tokens: 123            │  ❌ Not a setting!
│ completion_tokens: 456        │  ❌ Not a setting!
│ total_tokens: 579             │  ❌ Not a setting!
└───────────────────────────────┘
```

### After (Correct)

The trace detail panel now shows sections in a logical flow:

```
┌─ Prompt ──────────────────────┐
│ System instructions here...   │
└───────────────────────────────┘

┌─ Input Messages ──────────────┐
│ user: Hello                   │
│ assistant: Hi there!          │
└───────────────────────────────┘

┌─ Output ──────────────────────┐
│ Model response here...        │
└───────────────────────────────┘

┌─ Model Settings ──────────────┐
│ temperature: 0.7              │  ✅ Controls randomness
│ max_tokens: 1000              │  ✅ Controls response length
│ tool_choice: "auto"           │  ✅ Controls tool usage
└───────────────────────────────┘

┌─ Metrics ─────────────────────┐
│ prompt_tokens: 123            │  ✅ Input measurement
│ completion_tokens: 456        │  ✅ Output measurement
│ total_tokens: 579             │  ✅ Total usage
│ cached_tokens: 50             │  ✅ Cache statistics
└───────────────────────────────┘

┌─ Raw HTTP Request ────────────┐
│ (Collapsible, lazy loaded)    │
└───────────────────────────────┘

┌─ Raw HTTP Response ───────────┐
│ (Collapsible, lazy loaded)    │
└───────────────────────────────┘
```

## Benefits

### Clarity

- Users immediately understand which fields are configuration vs measurement
- Easier to troubleshoot performance issues by looking at metrics
- Easier to reproduce calls by looking at settings
- **Logical flow**: Prompt → Input → Output → Settings → Metrics

### Accuracy

- Semantically correct categorization
- Matches industry standards (OpenAI API documentation separates these concepts)
- Aligns with how developers think about API calls
- **Natural reading order**: Shows the conversation flow before technical details

### Extensibility

- Easy to add new model settings (e.g., `top_p`, `frequency_penalty`)
- Easy to add new metrics (e.g., `latency_ms`, `cost_usd`)
- Clear separation of concerns

### User Experience

- **Input-Output proximity**: Users can easily compare what was sent vs received
- **Technical details below**: Settings and metrics are available but don't interrupt the main flow
- **Progressive disclosure**: Most important info (conversation) shown first

## Testing

### Backend Tests

Added tests to verify model settings and metrics are stored correctly:

```python
async def test_trace_with_model_settings(self, client: AsyncClient):
    """Test trace with model settings like temperature, max_tokens, tool_choice."""
    payload = {
        "model": "gpt-4",
        "input": [...],
        "temperature": 0.7,
        "max_tokens": 150,
        "tool_choice": "auto",
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "total_tokens": 30,
        ...
    }

    response = await client.post("/traces", json=payload)
    data = response.json()

    # Verify model settings
    assert data["temperature"] == 0.7
    assert data["max_tokens"] == 150
    assert data["tool_choice"] is not None

    # Verify metrics
    assert data["prompt_tokens"] == 10
    assert data["completion_tokens"] == 20
    assert data["total_tokens"] == 30
```

Test Status: ✅ All tests passing

## Edge Cases

### Empty Settings

If no model settings were configured, displays: "No model settings"

### Empty Metrics

If no metrics are available (e.g., API error before completion), displays: "No metrics available"

### tool_choice Formats

`tool_choice` can be:

- String: `"auto"`, `"none"`, `"required"`
- Object: `{"type": "function", "function": {"name": "get_weather"}}`

Both formats are handled correctly.

### max_tokens Migration

The `max_tokens` field was added in a database migration. The frontend gracefully handles traces created before this migration.

## Future Enhancements

### Additional Model Settings

- `top_p`: Nucleus sampling parameter
- `frequency_penalty`: Penalty for token frequency
- `presence_penalty`: Penalty for token presence
- `stop_sequences`: Custom stop sequences
- `seed`: For reproducible outputs (supported by some models)

### Additional Metrics

- `latency_ms`: Total request latency
- `cost_usd`: Calculated cost in USD
- `cache_hit_rate`: Percentage of tokens from cache
- `first_token_latency`: Time to first token (for streaming)
- `tokens_per_second`: Throughput metric

### Cost Calculation

Future enhancement could add automatic cost calculation based on:

- Model pricing
- Token counts
- Cache usage
- Batch discounts

## Related Documentation

- [HTTP Trace Viewing](./http-trace-viewing.md)
- [Prompt and Input Messages Extraction](./prompt-and-input-messages.md)
- [Implementation Summary](./IMPLEMENTATION_SUMMARY.md)
- Backend Trace Model: `app/models/traces.py`
- Backend Trace Schema: `app/schemas/traces.py`
- Frontend Types: `frontend/src/lib/types/trace.ts`

## Migration Notes

### For Users

No action required. The UI will automatically display the separated sections.

### For Developers

If you're integrating with the R4U API:

- **Model settings** are request parameters you control
- **Metrics** are response data you measure
- Both are available in the `TraceRead` response schema
- Frontend automatically separates them in the UI

### Database

No migration required. The database schema already had the correct separation.

## Conclusion

This change improves the usability and accuracy of the trace detail panel by properly categorizing model configuration parameters (settings) separately from usage statistics (metrics). This aligns with industry standards and makes the platform more intuitive for users.
