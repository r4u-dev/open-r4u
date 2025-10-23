# HTTP Transport-Level Tracing

This document describes the HTTP transport-level tracing feature that captures raw HTTP requests/responses and parses them on the backend based on the provider.

## Overview

The HTTP tracing system consists of three main components:

1. **SDK HTTP Patchers**: Patch HTTP libraries (httpx, aiohttp, requests) to capture raw request/response data
2. **Backend Parser Service**: Parse provider-specific formats (OpenAI, Anthropic, Google GenAI) into structured traces
3. **HTTP Trace API Endpoint**: Accept raw HTTP traces and store them as structured traces

## Architecture

```
┌─────────────────┐
│   Application   │
│  (uses OpenAI)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  HTTP Library   │
│  (httpx/aiohttp │
│   /requests)    │
└────────┬────────┘
         │ [patched]
         ▼
┌─────────────────┐      Raw HTTP Data       ┌──────────────────┐
│  HTTP Tracer    │ ──────────────────────►  │  R4U Backend     │
│  (SDK Client)   │                          │  /http-traces    │
└─────────────────┘                          └────────┬─────────┘
                                                      │
                                                      ▼
                                             ┌─────────────────┐
                                             │  HTTPTrace DB   │
                                             │    (persisted)  │
                                             └────────┬────────┘
                                                      │
                                                      ▼
                                             ┌─────────────────┐
                                             │ Parser Service  │
                                             │ - OpenAI        │
                                             │ - Anthropic     │
                                             │ - Google GenAI  │
                                             └────────┬────────┘
                                                      │
                                                      ▼
                                             ┌─────────────────┐
                                             │  Trace Storage  │
                                             │  (linked to     │
                                             │   HTTPTrace)    │
                                             └─────────────────┘
```

## Supported Providers

### 1. OpenAI

- **URL Pattern**: `api.openai.com`
- **API Formats**:
    - Chat Completions API (traditional)
    - Responses API (new) ✨
- **Extracted Fields**:
    - Model, messages/input, tools, temperature
    - Token usage (prompt, completion, cached, reasoning)
    - Finish reason, system fingerprint
    - Response format/schema
- **Note**: Automatically detects and supports both Chat Completions and Responses API formats
- **See**: [OpenAI Responses API Support](OPENAI_RESPONSES_API.md) for details

### 2. Anthropic (Claude)

- **URL Pattern**: `api.anthropic.com`
- **API Format**: Anthropic Messages API
- **Extracted Fields**:
    - Model, messages, system prompt, tools
    - Token usage (input, output)
    - Stop reason (mapped to finish reason)
    - Temperature

### 3. Google Generative AI

- **URL Pattern**: `generativelanguage.googleapis.com`
- **API Format**: Google GenAI API
- **Extracted Fields**:
    - Model, contents, system instruction
    - Token usage (prompt, candidates, total)
    - Finish reason (mapped)
    - Generation config (temperature)

## API Endpoint

### POST /http-traces

Create a trace from raw HTTP request/response data.

This endpoint:

1. Persists the raw HTTPTrace to the database
2. Parses the HTTP data based on the provider
3. Creates a structured Trace linked to the HTTPTrace

**Request Body**:

```json
{
    "started_at": "2024-01-01T12:00:00Z",
    "completed_at": "2024-01-01T12:00:01Z",
    "status_code": 200,
    "error": null,
    "request": "{\"model\": \"gpt-4\", \"messages\": [...]}",
    "request_headers": {
        "content-type": "application/json",
        "host": "api.openai.com"
    },
    "response": "{\"id\": \"chatcmpl-123\", \"choices\": [...]}",
    "response_headers": {
        "content-type": "application/json"
    },
    "metadata": {
        "url": "https://api.openai.com/v1/chat/completions",
        "method": "POST",
        "project": "My Project",
        "path": "my.module.function"
    }
}
```

**Note**: Request and response should be sent as strings (not bytes or hex-encoded).

**Response**: Standard `TraceRead` object with structured data

**Error Codes**:

- `400`: Unable to parse the trace (unsupported provider or invalid format)
- `500`: Internal server error

**Data Persistence**:

- HTTPTrace is always persisted, even if parsing fails
- If parsing succeeds, a Trace is created with a foreign key to the HTTPTrace
- If parsing fails, the HTTPTrace remains in the database without an associated Trace

## SDK Usage

### Python SDK

```python
from openai import OpenAI
from r4u.client import get_r4u_client
from r4u.tracing.http.requests import patch_requests

# Initialize R4U client
r4u_client = get_r4u_client()

# Patch HTTP library
patch_requests(r4u_client)

# Use OpenAI normally - tracing happens automatically
client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)

# Cleanup
r4u_client.close()
```

## Adding New Providers

To add support for a new LLM provider:

1. **Create a new parser class** in `backend/app/services/http_trace_parser.py`:

```python
class NewProviderParser(ProviderParser):
    """Parser for New Provider API format."""

    def can_parse(self, url: str) -> bool:
        """Check if URL is a New Provider endpoint."""
        parsed = urlparse(url)
        return "newprovider.com" in parsed.netloc

    def parse(
        self,
        request_body: dict[str, Any],
        response_body: dict[str, Any],
        started_at: datetime,
        completed_at: datetime,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TraceCreate:
        """Parse New Provider API request/response."""
        # Implement parsing logic
        # ...
        return TraceCreate(...)
```

2. **Register the parser** in `HTTPTraceParserService.__init__`:

```python
def __init__(self):
    self.parsers: list[ProviderParser] = [
        OpenAIParser(),
        AnthropicParser(),
        GoogleGenAIParser(),
        NewProviderParser(),  # Add here
    ]
```

## Benefits

1. **Provider-Agnostic SDKs**: SDK code doesn't need to know about provider-specific formats
2. **Centralized Parsing**: All parsing logic is in one place (backend)
3. **Easy Updates**: Update parser logic without changing SDK
4. **Complete Data**: Captures raw request/response for debugging
5. **Extensible**: Easy to add new providers

## Implementation Notes

### Data Flow

1. HTTP library makes a request to LLM API
2. Patched HTTP library captures raw request/response
3. SDK sends HTTPTrace to backend `/http-traces` endpoint
4. Backend persists HTTPTrace to database (always stored)
5. Backend determines provider from URL
6. Appropriate parser extracts structured data
7. Structured Trace is created and linked to HTTPTrace via foreign key
8. Both HTTPTrace and Trace are stored in database

### Error Handling

- If provider is unsupported: HTTPTrace is saved, returns 400 with error message
- If parsing fails: HTTPTrace is saved, returns 400 with parsing error details
- If request/response is not valid JSON: HTTPTrace is saved, returns 400
- Network errors: Logged on SDK side, doesn't fail user's request

**Note**: HTTPTrace is always persisted to the database, even when parsing fails. This ensures raw data is never lost and can be inspected or reprocessed later.

### Performance

- HTTP traces are sent asynchronously (queue + worker thread)
- Parsing happens on backend, doesn't block SDK
- Failed trace sends don't affect application performance

## Testing

Run the test suite:

```bash
cd backend
pytest tests/test_http_traces.py -v
```

## Database Schema

### HTTPTrace Table

Stores raw HTTP request/response data:

- `id`: Primary key
- `started_at`, `completed_at`: Timing information
- `status_code`: HTTP status code
- `error`: Error message (if any)
- `request`, `response`: Raw request/response as strings
- `request_headers`, `response_headers`: Headers as JSONB
- `metadata`: Additional metadata as JSONB

### Trace Table

Stores parsed, structured trace data:

- `http_trace_id`: Foreign key to HTTPTrace (nullable)
- All existing trace fields (model, tokens, etc.)

**Relationship**: Each Trace has an optional reference to an HTTPTrace. Each HTTPTrace can have at most one Trace.

## Future Enhancements

1. **Streaming Support**: Handle streaming responses
2. **More Providers**: Add support for more LLM providers
3. **Compression**: Compress large request/response bodies
4. **Batching**: Batch multiple traces in single request
5. **Schema Validation**: Validate provider-specific schemas
6. **Reprocessing**: UI to reprocess failed HTTPTraces with updated parsers
