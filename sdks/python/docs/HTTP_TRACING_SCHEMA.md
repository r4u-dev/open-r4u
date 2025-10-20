# HTTP Tracing Schema

## Overview

The R4U tracing package uses a simplified `HTTPTrace` schema for comprehensive HTTP request/response tracing. This schema is provider-agnostic and focuses on capturing essential HTTP data without unnecessary complexity.

## HTTPTrace Schema

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Optional, Any

class HTTPTrace(BaseModel):
    """Schema for HTTP trace creation (provider-agnostic)."""

    # Timing
    started_at: datetime = Field(..., description="When the request started")
    completed_at: datetime = Field(..., description="When the request completed")

    # Status
    status_code: int = Field(..., description="HTTP status code")
    error: Optional[str] = Field(None, description="Error message if any")

    # Raw data
    request: bytes = Field(..., description="Complete raw request bytes (raw or JSON)")
    request_headers: Dict[str, str] = Field(..., description="Complete raw request headers")
    response: bytes = Field(..., description="Complete raw response bytes (raw or JSON)")
    response_headers: Dict[str, str] = Field(..., description="Complete raw response headers")

    # Optional extracted fields for convenience
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = ConfigDict(extra="allow")
```

## Key Features

### 1. **Provider Agnostic**
- No hardcoded provider detection logic
- Provider is passed explicitly when setting up tracing
- Works with any HTTP client (httpx, requests, aiohttp)

### 2. **Simplified Schema**
- Removed unnecessary fields like `endpoint`, `operation_type`
- Focus on essential HTTP data: timing, status, headers, payloads
- Metadata field for additional context (method, URL, etc.)

### 3. **Raw Data Capture**
- Captures complete request/response bytes
- Preserves original headers
- No data transformation or parsing

### 4. **Streaming Support**
- Handles both regular and streaming requests
- Collects complete response content during streaming
- Accurate timing includes full streaming duration

## Usage Examples

### Basic HTTP Tracing

```python
from r4u.tracing.http.httpx import trace_async_client
from r4u.tracing.http.tracer import PrintTracer

# Trace an httpx client
async with httpx.AsyncClient() as client:
    trace_async_client(client, "my-provider")
    
    # All requests are automatically traced
    response = await client.get("https://api.example.com/data")
```

### Custom Tracer

```python
from r4u.tracing.http.tracer import AbstractTracer
from r4u.client import HTTPTrace

class MyTracer(AbstractTracer):
    def trace_request(self, trace: HTTPTrace) -> None:
        # Access trace data
        print(f"Request: {trace.metadata.get('method')} {trace.metadata.get('url')}")
        print(f"Status: {trace.status_code}")
        print(f"Duration: {(trace.completed_at - trace.started_at).total_seconds() * 1000:.2f}ms")
        
        # Access raw data
        if trace.request:
            print(f"Request body: {trace.request.decode()}")
        if trace.response:
            print(f"Response body: {trace.response.decode()}")
```

### Streaming Requests

```python
# Streaming requests are automatically detected and traced
request = client.build_request("GET", "https://api.example.com/stream")
response = await client.send(request, stream=True)

# Content is collected during streaming
async for chunk in response.aiter_bytes():
    print(chunk.decode())

# Trace is sent when streaming completes
```

## Migration from RawRequestInfo

The old `RawRequestInfo` schema has been replaced with `HTTPTrace`. Key changes:

### Removed Fields
- `endpoint` - No longer needed, provider is explicit
- `operation_type` - Removed complexity
- `request_size`, `response_size` - Can be calculated from bytes
- `duration_ms` - Can be calculated from timestamps
- `error_type` - Simplified to just error message

### New Structure
- `request` instead of `request_payload`
- `response` instead of `response_payload`
- `request_headers` instead of `headers`
- `metadata` for additional context (method, URL, etc.)

### Updated Tracer Interface

```python
# Old interface
def trace_request(self, request_info: RawRequestInfo) -> None:
    pass

# New interface
def trace_request(self, trace: HTTPTrace) -> None:
    pass
```

## Benefits

1. **Simpler API** - Fewer fields, clearer purpose
2. **Provider Agnostic** - No hardcoded provider logic
3. **Better Performance** - Less data processing overhead
4. **Easier Testing** - Simpler schema to mock and test
5. **Future Proof** - Extensible metadata field for new requirements

## Implementation Details

### HTTP Client Integration

The tracing is implemented at the HTTP client level:

- **httpx**: Patches `client.send()` method
- **requests**: Patches `session.send()` method  
- **aiohttp**: Patches `session._request()` method

### Streaming Detection

Streaming requests are detected using the `stream=True` parameter in httpx, or by wrapping response objects for other clients.

### Error Handling

All tracing errors are logged but don't fail the original request, ensuring observability doesn't break functionality.

## Best Practices

1. **Use explicit providers** - Pass provider name when setting up tracing
2. **Handle metadata carefully** - Store method, URL, and other context in metadata
3. **Test with real requests** - Verify tracing works with actual HTTP calls
4. **Monitor performance** - Ensure tracing doesn't significantly impact request latency
5. **Use appropriate tracers** - Choose between PrintTracer for debugging and UniversalTracer for production
