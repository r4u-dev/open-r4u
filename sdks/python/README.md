# R4U Python SDK

An observability SDK for LLM applications that automatically traces and monitors your AI interactions.

## Installation

```bash
pip install r4u
```

For OpenAI integration:
```bash
pip install r4u[openai]
```

## Quick Start

### OpenAI Integration

```python
from openai import OpenAI
from r4u.integrations.openai import wrap_openai

# Initialize your OpenAI client
client = OpenAI(api_key="your-api-key")

# Wrap it with R4U observability
traced_client = wrap_openai(client, api_url="http://localhost:8000")

# Use it normally - traces will be automatically created
response = traced_client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Hello, world!"}]
)
```

### Manual Tracing

```python
from r4u.client import R4UClient

client = R4UClient(api_url="http://localhost:8000")

# Create a trace manually
trace = await client.create_trace(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"}
    ],
    result="Hi there!",
    started_at="2024-01-01T00:00:00Z",
    completed_at="2024-01-01T00:00:01Z"
)
```

## Features

- **Automatic LLM Tracing**: Wrap your existing LLM clients to automatically create traces
- **OpenAI Integration**: Native support for OpenAI's Python SDK
- **Async Support**: Full async/await support
- **Error Tracking**: Automatic error capture and reporting
- **Minimal Overhead**: Lightweight wrapper with minimal performance impact

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for development setup and guidelines.