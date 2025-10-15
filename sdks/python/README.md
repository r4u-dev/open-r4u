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

# Create the R4U callback handler
r4u_handler = wrap_langchain(api_url="http://localhost:8000")

# Add it to your LangChain model
llm = ChatOpenAI(model="gpt-3.5-turbo", callbacks=[r4u_handler])

# Use it normally - traces will be automatically created
response = llm.invoke("Hello, world!")
```

The LangChain integration uses callback handlers to capture all LLM calls, including:
- **Message history**: All messages in a conversation are automatically captured
- **Tool/Function calls**: Tool definitions and invocations are tracked
- **Agents**: Multi-step agent executions are fully traced
- **Chains**: Works seamlessly with LangChain chains and runnables

For more details, see [docs/LANGCHAIN_INTEGRATION.md](docs/LANGCHAIN_INTEGRATION.md).

You can find runnable examples in `examples/basic_langchain.py` and `examples/advanced_langchain.py`.

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

For a complete walk-through that includes tool definitions, tool call messages, and the final tool-assisted response, check out `examples/tool_calls_example.py`. The example issues real OpenAI Chat Completions requests (requiring `OPENAI_API_KEY`) and performs the multi-turn loop that fulfils the tool invocation before asking for the final assistant answer.

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