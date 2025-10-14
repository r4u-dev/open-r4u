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

For LangChain integration:
```bash
pip install r4u[langchain]
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

### LangChain Integration

```python
from langchain_openai import ChatOpenAI
from r4u.integrations.langchain import wrap_langchain

# Build your LangChain runnable or model
llm = ChatOpenAI(model="gpt-3.5-turbo")

# Wrap it with R4U to attach tracing callbacks (sync + async)
traced_llm = wrap_langchain(llm, api_url="http://localhost:8000")

# Invoke as usual - traces are sent via LangChain's callback system
response = traced_llm.invoke("Hello, world!")
```

Under the hood, the LangChain integration registers synchronous and asynchronous callback handlers rather than monkey-patching methods. This keeps compatibility with the broader LangChain runnable ecosystem while still capturing every LLM call.

You can find a runnable example in `examples/langchain_openai.py` that demonstrates both sync and async invocations.

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

For a complete walk-through that includes tool definitions, tool call messages, and the final tool-assisted response, check out `examples/tool_calls_example.py`. The example wraps a lightweight fake OpenAI client so it can run locally while still exercising the automatic tracing pipeline.

## Features

- **Automatic LLM Tracing**: Wrap your existing LLM clients to automatically create traces
- **Call Path Tracking**: Automatically captures where LLM calls originate from in your code
- **OpenAI & LangChain Integrations**: Automatic tracing for OpenAI SDK calls and LangChain runnables via callbacks
- **Async Support**: Full async/await support
- **Error Tracking**: Automatic error capture and reporting
- **Minimal Overhead**: Lightweight wrapper with minimal performance impact

### Call Path Tracking

The SDK automatically tracks where each LLM call originates from in your codebase:

```python
# In src/app/chatbot.py
def process_query(user_input):
    response = traced_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": user_input}]
    )
    return response

# The trace will include: path="src/app/chatbot.py::process_query->create"
```

For nested function calls, the full call chain is captured:

```python
# The trace will show: "src/main.py::main->handle_request->process_query->create"
def main():
    handle_request()

def handle_request():
    process_query("Hello")

def process_query(text):
    traced_client.chat.completions.create(...)
```

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for development setup and guidelines.