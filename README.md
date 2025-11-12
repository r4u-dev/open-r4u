# Open R4U 🚀

**Optimize AI & Maximize ROI of your LLM tasks**

[![Website](https://img.shields.io/badge/Website-r4u.dev-blue)](https://r4u.dev)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

Open R4U is an open-source LLM observability and optimization platform that helps you trace, monitor, and optimize your AI applications. Track your LLM usage, analyze performance, and maximize ROI through intelligent insights and recommendations.

**🆕 Features automatic task grouping with background processing** - Similar traces are automatically grouped into tasks with templated prompts, running in a separate process to keep your API fast.

## 🌟 Features

### 🔍 **HTTP-Level Observability**

- **Automatic HTTP Tracing**: Trace all HTTP requests from httpx, requests, and aiohttp libraries
- **Zero Code Changes**: Works transparently with OpenAI, Anthropic, and any HTTP-based LLM API
- **Comprehensive Data Capture**: Full request/response bodies, headers, timing, and errors
- **Streaming Support**: Automatic detection and collection of streaming responses
- **Async Compatible**: Full support for async/await patterns with asyncio

### 📊 **Analytics & Insights**

- **Performance Metrics**: Track latency, token usage, and cost per request
- **Usage Analytics**: Understand your LLM consumption patterns
- **Error Tracking**: Comprehensive error capture and debugging information
- **Request/Response Inspection**: View complete HTTP transactions
- **Project Organization**: Organize traces by projects for better management

### 🔌 **Universal Integrations**

- **OpenAI**: Automatically trace all OpenAI API calls (sync and async)
- **Any HTTP-based LLM API**: Works with Anthropic, Cohere, Hugging Face, and more
- **Multiple HTTP Libraries**: Support for httpx, requests, and aiohttp
- **Non-Invasive**: Tracing errors never break your application

### 🛠 **Developer Experience**

- **Minimal Overhead**: Lightweight SDK with negligible performance impact
- **Self-Hosted**: Run your own instance with full data control
- **REST API**: Complete API for custom integrations
- **Comprehensive Testing**: 102 tests covering all HTTP wrapper functionality
- **Well-Documented**: Extensive examples and troubleshooting guides

### 🤖 **Automatic Task Grouping**

- **Pattern Detection**: Automatically identifies similar traces and groups them into tasks
- **Template Generation**: Creates templated prompts with variable extraction
- **Background Processing**: CPU-intensive grouping runs in separate process
- **Smart Throttling**: Only processes latest trace when multiple arrive rapidly
- **Non-Blocking**: API responses remain fast, grouping happens asynchronously

## 🏗 Architecture

Open R4U uses HTTP-level tracing to capture all LLM API calls transparently:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Your App      │    │   R4U SDK       │    │   R4U Backend   │
│                 │    │                 │    │                 │
│ OpenAI API call │───▶│ httpx wrapper   │───▶│   FastAPI       │
│      ↓          │    │      ↓          │    │      ↓          │
│ httpx.Client    │    │ Intercepts HTTP │    │ Stores traces   │
│      ↓          │    │ Captures data   │    │ PostgreSQL      │
│ HTTP Request    │───▶│ Forwards request│───▶│ Analytics       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

**How it works:**

1. Call `trace_all()` to patch HTTP client constructors (httpx, requests, aiohttp)
2. All HTTP clients created afterwards are automatically traced
3. When your app makes an LLM API call, the HTTP request is intercepted
4. Request/response data is captured and queued
5. Background worker sends traces to backend every 5 seconds
6. Backend stores and analyzes the traces
7. Task grouping worker analyzes similar traces and creates tasks with templates (in background)

**Supported HTTP Libraries:**

- ✅ **httpx** (sync and async) - Used by OpenAI Python SDK
- ✅ **requests** (sync only) - Popular HTTP library
- ✅ **aiohttp** (async only) - High-performance async HTTP

## 🚀 Quick Start

### 1. Start the Backend

```bash
# Clone the repository
git clone https://github.com/your-org/open-r4u.git
cd open-r4u

# Start the backend with Docker Compose
docker compose up -d

# The API will be available at http://localhost:8000
```

### 2. Install the Python SDK

```bash
pip install r4u
# or
uv add r4u
```

### 3. Trace OpenAI API Calls

**🚨 IMPORTANT:** You must call `trace_all()` BEFORE importing OpenAI!

```python
import os

# STEP 1: Import R4U and enable tracing FIRST
from r4u.tracing import trace_all, untrace_all
trace_all()

# STEP 2: Import OpenAI AFTER enabling tracing
from openai import OpenAI

# STEP 3: Use OpenAI normally - all calls are automatically traced!
def main():
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hello!"}]
    )

    print(response.choices[0].message.content)

    # Wait for traces to be sent (background worker sends every 5s)
    import time
    time.sleep(6)

    # Cleanup
    untrace_all()

if __name__ == "__main__":
    main()
```

**Why this order matters:** OpenAI creates its internal httpx client when the module is imported. If you call `trace_all()` afterwards, the client won't be patched and requests won't be traced.

### 4. Async OpenAI Support

```python
import asyncio
import os

# Enable tracing BEFORE importing OpenAI
from r4u.tracing import trace_all, untrace_all
trace_all()

from openai import AsyncOpenAI

async def main():
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Make concurrent requests - all traced!
    tasks = [
        client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"Question {i}"}]
        )
        for i in range(5)
    ]

    responses = await asyncio.gather(*tasks)

    # All 5 requests are traced
    await asyncio.sleep(6)
    untrace_all()

if __name__ == "__main__":
    asyncio.run(main())
```

### 5. Streaming Support

Streaming responses are automatically detected and captured:

```python
from r4u.tracing import trace_all
trace_all()

from openai import OpenAI

client = OpenAI()

# Streaming is automatically detected
stream = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Count to 5"}],
    stream=True
)

# Consume the stream normally
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")

# Full response content is captured in the trace!
```

### 6. View Your Traces

Visit `http://localhost:8000/docs` to explore the API, or use it directly:

```bash
# List all traces
curl http://localhost:8000/api/v1/http-traces

# Get specific trace
curl http://localhost:8000/api/v1/http-traces/{trace_id}
```

## 📚 Documentation

### Python SDK

- [Python SDK README](sdks/python/README.md)
- [HTTP Tracing Schema](sdks/python/docs/HTTP_TRACING_SCHEMA.md)
- [Test Suite Documentation](sdks/python/tests/README.md)
- [Test Implementation Summary](sdks/python/tests/IMPLEMENTATION_SUMMARY.md)

### Examples

- **⭐ [Working OpenAI Example](sdks/python/examples/working_openai_example.py)** - Recommended starting point
- [Simple OpenAI Example](sdks/python/examples/simple_openai_example.py) - Minimal example
- [Comprehensive OpenAI Example](sdks/python/examples/openai_tracing_example.py) - Multiple patterns
- [Async OpenAI Example](sdks/python/examples/async_openai_example.py) - Async/await patterns
- [Examples README](sdks/python/examples/README.md) - Complete guide with troubleshooting
- [Import Order Fix Guide](sdks/python/examples/IMPORT_ORDER_FIX.md) - Explains the import order requirement

### Backend API

- [Backend API Documentation](backend/README.md)
- [Background Task Grouping Architecture](backend/docs/BACKGROUND_TASK_GROUPING.md)
- [API Tests](backend/tests/README.md)

## 🧪 Testing

The Python SDK has comprehensive test coverage:

- **102 tests** covering all HTTP wrapper functionality
- Tests for httpx (sync & async), requests, and aiohttp
- Streaming response handling tests
- Error handling and edge case tests
- All tests pass in < 0.4 seconds

```bash
cd sdks/python
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=src/r4u --cov-report=html
```

## 🛠 Development

### Prerequisites

- Python 3.12+
- PostgreSQL 16+
- Docker & Docker Compose (optional)

### Local Development Setup

```bash
# Clone the repository
git clone https://github.com/your-org/open-r4u.git
cd open-r4u

# Start the database
docker compose up -d db

# Install backend dependencies
cd backend
uv sync

# Run database migrations
alembic upgrade head

# Start the backend
uvicorn app.main:app --reload

# Install SDK dependencies (in another terminal)
cd ../sdks/python
uv install

# Run SDK tests
uv run pytest tests/ -v
```

### Project Structure

```
open-r4u/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── api/v1/            # API endpoints
│   │   ├── models/            # Database models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic
│   │   ├── workers/           # Background workers
│   │   └── main.py            # FastAPI app
│   ├── migrations/            # Database migrations
│   ├── docs/                  # Architecture docs
│   └── tests/                 # Backend tests
├── sdks/python/               # Python SDK
│   ├── src/r4u/
│   │   ├── tracing/
│   │   │   └── http/          # HTTP library wrappers
│   │   │       ├── httpx.py   # httpx wrapper
│   │   │       ├── requests.py # requests wrapper
│   │   │       └── aiohttp.py  # aiohttp wrapper
│   │   ├── client.py          # R4U client
│   │   └── utils.py           # Utilities
│   ├── examples/              # Usage examples
│   │   ├── simple_openai_example.py
│   │   ├── openai_tracing_example.py
│   │   ├── async_openai_example.py
│   │   └── README.md          # Examples documentation
│   ├── tests/                 # SDK tests (102 tests)
│   │   ├── test_client.py
│   │   ├── test_httpx_wrapper.py
│   │   ├── test_requests_wrapper.py
│   │   ├── test_aiohttp_wrapper.py
│   │   └── README.md          # Test documentation
│   └── docs/                  # Documentation
└── compose.yaml               # Docker Compose setup
```

## 🔧 Advanced Usage

### Custom Tracer

Use a custom tracer instead of the default:

```python
from r4u.client import R4UClient
from r4u.tracing import trace_all

# Create custom tracer with specific settings
tracer = R4UClient(
    api_url="https://your-r4u-instance.com",
    timeout=60.0
)

# Use it for tracing
trace_all(tracer)
```

### Selective Tracing

Trace only specific HTTP clients:

```python
from r4u.tracing.http.httpx import trace_client
from r4u.client import get_r4u_client
import httpx

# Create a specific client to trace
client = httpx.Client()

# Trace only this client
tracer = get_r4u_client()
trace_client(client, tracer)

# Other httpx clients won't be traced
```

### Testing with Capturing Tracer

For testing, capture traces in memory instead of sending to backend:

```python
from r4u.client import AbstractTracer, HTTPTrace
from r4u.tracing import trace_all

class CapturingTracer(AbstractTracer):
    def __init__(self):
        self.traces = []

    def log(self, trace: HTTPTrace):
        self.traces.append(trace)

tracer = CapturingTracer()
trace_all(tracer)

# Make API calls...

# Check captured traces
print(f"Captured {len(tracer.traces)} traces")
for trace in tracer.traces:
    print(f"{trace.method} {trace.url} -> {trace.status_code}")
```

## ❓ Troubleshooting

### Traces Not Appearing

**Problem:** Made OpenAI API call but no trace in backend.

**Solutions:**

1. ✅ Check import order - `trace_all()` MUST be before `from openai import OpenAI`
2. ✅ Verify backend is running: `curl http://localhost:8000/health`
3. ✅ Wait 6+ seconds for background worker to send traces
4. ✅ Check backend logs for errors
5. ✅ Run diagnostic script: `uv run python examples/test_patching.py`

### Import Order Issues

If you're getting no traces, the most common issue is import order. See [Import Order Fix Guide](sdks/python/examples/IMPORT_ORDER_FIX.md) for details.

**Quick fix:**

```python
# ✅ Correct order
from r4u.tracing import trace_all
trace_all()
from openai import OpenAI

# ❌ Wrong order
from openai import OpenAI
from r4u.tracing.http.httpx import trace_all
trace_all()  # Too late!
```

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** and add tests
4. **Run the test suite**: `uv run pytest tests/`
5. **Commit your changes**: `git commit -m 'Add amazing feature'`
6. **Push to the branch**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

### Development Guidelines

- Follow Python type hints and use `mypy` for type checking
- Write comprehensive tests for new features (see `sdks/python/tests/`)
- Update documentation for API changes
- Follow the existing code style and patterns
- Test import order requirements for HTTP wrappers

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🌐 Links

- **Website**: [r4u.dev](https://r4u.dev)
- **Documentation**: [docs.r4u.dev](https://docs.r4u.dev) (coming soon)
- **GitHub**: [github.com/your-org/open-r4u](https://github.com/your-org/open-r4u)

## 🙏 Acknowledgments

- Inspired by [Langfuse](https://github.com/langfuse/langfuse) for LLM observability concepts
- Inspired by [LangSmith](https://smith.langchain.com/) for LLM monitoring and evaluation
- Inspired by [Opik](https://github.com/comet-ml/opik) for comprehensive LLM debugging and evaluation
- Built with [FastAPI](https://fastapi.tiangolo.com/) and [SQLAlchemy](https://www.sqlalchemy.org/)
- HTTP-level tracing powered by [httpx](https://www.python-httpx.org/), [requests](https://requests.readthedocs.io/), and [aiohttp](https://docs.aiohttp.org/)
- Powered by the open-source community

---

**Ready to optimize your LLM usage?** [Get started](https://r4u.dev) with R4U today!
