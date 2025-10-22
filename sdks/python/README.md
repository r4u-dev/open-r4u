# R4U Python SDK

An observability SDK that automatically traces HTTP requests from your applications, with special support for LLM API calls.

## Installation

```bash
pip install r4u
```

## Quick Start

### Automatic HTTP Tracing

The easiest way to get started is with automatic HTTP tracing. This will trace all HTTP requests made by any supported HTTP library:

```python
from r4u.tracing import trace_all

# Enable automatic tracing for all HTTP libraries
trace_all()

# Now any HTTP requests will be automatically traced
import httpx
import requests
import aiohttp

# All of these will be automatically traced
httpx_client = httpx.Client()
requests_session = requests.Session()
aiohttp_session = aiohttp.ClientSession()
```

### OpenAI Integration

Since OpenAI uses httpx internally, you can trace OpenAI API calls by enabling HTTP tracing:

```python
from r4u.tracing import trace_all

# Enable tracing BEFORE importing OpenAI
trace_all()

# Now import and use OpenAI normally
from openai import OpenAI

client = OpenAI(api_key="your-api-key")
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello, world!"}]
)
```

## Features

- **Automatic HTTP Tracing**: Automatically trace all HTTP requests from supported libraries (httpx, requests, aiohttp)
- **Multiple HTTP Library Support**: Works with httpx, requests, and aiohttp
- **OpenAI Integration**: Automatically trace OpenAI API calls since they use httpx internally
- **Streaming Support**: Full support for streaming HTTP requests and responses
- **Async Support**: Full async/await support for both sync and async HTTP clients
- **Background Processing**: Traces are sent asynchronously in batches to minimize performance impact
- **Error Tracking**: Automatic error capture and reporting
- **Minimal Overhead**: Lightweight wrapper with minimal performance impact
- **Custom Tracers**: Support for custom tracer implementations

### HTTP Trace Data

Each HTTP request generates a comprehensive trace with:

**Request Details**:
- HTTP method (GET, POST, etc.)
- Full URL
- Request headers (including Authorization)
- Request body (raw bytes)

**Response Details**:
- HTTP status code
- Response headers
- Response body (raw bytes, including streaming responses)

**Timing Information**:
- Request start time
- Request completion time
- Total duration

**Error Information** (if applicable):
- Error messages
- Exception details

**Custom Metadata**:
- Additional context you can provide
- Extracted fields for convenience


### Streaming Example

```python
from r4u.tracing import trace_all

# Enable tracing BEFORE importing OpenAI
trace_all()

from openai import OpenAI

client = OpenAI(api_key="your-api-key")

# Streaming requests are automatically traced
stream = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Tell me a story"}],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content is not None:
        print(chunk.choices[0].delta.content, end="")
```

### Custom Tracer Example

```python
from r4u.client import AbstractTracer, HTTPTrace
from r4u.tracing import trace_all

class ConsoleTracer(AbstractTracer):
    def log(self, trace: HTTPTrace):
        print(f"HTTP {trace.method} {trace.url} -> {trace.status_code}")

# Use custom tracer
tracer = ConsoleTracer()
trace_all(tracer)

# All HTTP requests will now be printed to console
```

For more comprehensive examples, see the `examples/` directory.

## Configuration

### Environment Variables

- `R4U_API_URL`: Base URL for the R4U server (default: `http://localhost:8000`)
- `R4U_TIMEOUT`: HTTP request timeout in seconds (default: `30.0`)
- `R4U_TOKEN`: R4U Cloud server authorization token (optional, not needed for local Open R4U Server)


## Development

See the `examples/` directory for comprehensive usage examples and the `tests/` directory for test cases.
