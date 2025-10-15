# Token Usage and Metadata Tracking

Added comprehensive tracking for token usage, response schemas, and custom metadata to R4U traces.

## New Fields

### Token Usage
- **`prompt_tokens`** (int, optional): Number of tokens in the prompt
- **`completion_tokens`** (int, optional): Number of tokens in the completion
- **`total_tokens`** (int, optional): Total tokens used (prompt + completion)

### Response Schema
- **`response_schema`** (dict, optional): JSON schema for structured outputs
  - Automatically captured from OpenAI's `response_format` parameter
  - Supports `json_schema` structured outputs
  - Useful for tracking what format was requested from the LLM

### Custom Metadata
- **`trace_metadata`** (dict, optional): Flexible key-value metadata
  - Store environment information (production, staging, etc.)
  - Track user IDs, session IDs
  - Add custom fields specific to your application
  - Useful for filtering and analyzing traces

## Automatic Token Tracking

Token usage is **automatically extracted** from OpenAI responses when using the OpenAI integration:

```python
from openai import OpenAI
from r4u.integrations.openai import wrap_openai

client = OpenAI()
wrapped_client = wrap_openai(client, api_url="http://localhost:8000")

# Token usage is automatically tracked!
response = wrapped_client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)
# The trace will include prompt_tokens, completion_tokens, and total_tokens
```

## Response Schema Tracking

Response schemas are **automatically captured** when using structured outputs:

```python
response = wrapped_client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Generate a person"}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "person",
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"}
                },
                "required": ["name"]
            }
        }
    }
)
# The trace will include the complete response_schema
```

## Manual Metadata

Add custom metadata when creating traces directly:

```python
from r4u import R4UClient

client = R4UClient(api_url="http://localhost:8000")

trace = client.create_trace(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}],
    result="Hi there!",
    prompt_tokens=10,
    completion_tokens=15,
    total_tokens=25,
    trace_metadata={
        "environment": "production",
        "user_id": "user_123",
        "session_id": "session_abc",
        "feature_flag": "new_feature_v2"
    }
)
```

## Database Schema

The `trace` table includes these new columns:

```sql
-- Token usage
prompt_tokens INTEGER NULL
completion_tokens INTEGER NULL
total_tokens INTEGER NULL

-- Schema and metadata  
response_schema JSONB NULL  -- PostgreSQL, JSON for SQLite
trace_metadata JSONB NULL   -- PostgreSQL, JSON for SQLite
```

## API Examples

### Create trace with all fields
```bash
curl -X POST http://localhost:8000/traces \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello"}],
    "result": "Hi!",
    "started_at": "2025-10-15T10:00:00Z",
    "completed_at": "2025-10-15T10:00:01Z",
    "project": "My Project",
    "prompt_tokens": 10,
    "completion_tokens": 5,
    "total_tokens": 15,
    "response_schema": {
      "type": "object",
      "properties": {
        "answer": {"type": "string"}
      }
    },
    "trace_metadata": {
      "environment": "prod",
      "user_id": "user_123"
    }
  }'
```

## Migration

A database migration has been created and applied:
- Migration: `c166fc620924_add_tokens_schema_metadata_to_traces.py`
- Adds 5 new columns to the `trace` table
- Backwards compatible (all fields are nullable)

## Use Cases

1. **Cost Tracking**: Monitor token usage to track API costs
2. **Performance Analysis**: Identify expensive queries
3. **Schema Validation**: Track what schemas were used for structured outputs
4. **Debugging**: Add context via metadata (user, session, environment)
5. **Feature Flags**: Track which features were active during trace
6. **A/B Testing**: Tag traces with experiment IDs
7. **Multi-tenancy**: Track customer/tenant information

## Testing

Comprehensive tests added in `backend/tests/test_traces.py`:
- `test_create_trace_with_tokens_and_metadata`: Full example with all new fields
- `test_create_trace_with_partial_tokens`: Partial token data
- `test_trace_includes_all_fields`: Verify all fields in response

All 23 backend tests and 36 SDK tests pass ✅
