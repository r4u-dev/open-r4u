# R4U Python SDK Examples

This directory contains example scripts demonstrating how to use the R4U SDK to trace OpenAI API calls.

## 🚨 CRITICAL: Import Order Matters!

**The most important thing to understand:** You MUST call `trace_all()` BEFORE importing OpenAI!

### ✅ Correct Order

```python
# Step 1: Import R4U tracing
from r4u.tracing.http.httpx import trace_all, untrace_all

# Step 2: Enable tracing BEFORE importing OpenAI
trace_all()

# Step 3: NOW import OpenAI
from openai import OpenAI

# Step 4: Use OpenAI normally (automatically traced)
client = OpenAI()
response = client.chat.completions.create(...)
```

### ❌ Wrong Order (Won't Work)

```python
# DON'T DO THIS - OpenAI imported before trace_all()
from openai import OpenAI
from r4u.tracing.http.httpx import trace_all

trace_all()  # Too late! OpenAI already created its httpx client
client = OpenAI()
```

**Why?** OpenAI's client creates an internal httpx client when the module is imported. If you call `trace_all()` after importing OpenAI, the internal client won't be patched and requests won't be traced.

## Prerequisites

### 1. Install Dependencies

```bash
# Install OpenAI library
uv add openai

# Or with pip
pip install openai
```

### 2. Set Environment Variables

**Option A: Using export commands**

```bash
# Required: Your OpenAI API key
export OPENAI_API_KEY="sk-your-openai-api-key-here"

# Optional: Custom R4U API URL (defaults to http://localhost:8000)
export R4U_API_URL="http://localhost:8000"
```

**Option B: Using .env file (Recommended)**

Create a `.env` file in the project root:

```bash
# .env file
OPENAI_API_KEY=sk-your-openai-api-key-here
R4U_API_URL=http://localhost:8000
```

The examples automatically load environment variables from `.env` using python-dotenv.

### 3. Start R4U Backend

Make sure your R4U backend API is running and accessible. Traces will be sent to:

```
{R4U_API_URL}/http-traces
```

Default: `http://localhost:8000/http-traces`

## Examples

### 1. Working OpenAI Example ⭐ (Recommended)

**File**: `working_openai_example.py`

**Purpose**: Demonstrates the CORRECT way to trace OpenAI API calls with detailed explanations.

**Features**:

- ✅ Correct import order (trace_all before OpenAI)
- ✅ Prerequisites verification
- ✅ Detailed step-by-step output
- ✅ Explains what's happening at each stage
- ✅ Shows what data is captured in traces

**Run it**:

```bash
uv run python examples/working_openai_example.py
```

**Expected output**:

```
🔧 Enabling HTTP tracing...
✅ Tracing enabled!

======================================================================
OpenAI API Tracing - Working Example
======================================================================

📦 Creating OpenAI client...
✅ Client created (automatically traced)

📤 Sending request to OpenAI API...
Question: What is 2 + 2? (Answer briefly)

📥 Response: 2 + 2 equals 4.
📊 Tokens used: 25
📝 Model: gpt-3.5-turbo

✅ API call completed successfully!

⏳ Waiting for background worker to send trace...
✅ Trace should now be in your backend!

🎉 Success!
```

### 2. Simple OpenAI Example

**File**: `simple_openai_example.py`

**Purpose**: Minimal example for quick start.

**Features**:

- Basic chat completion
- Simple error handling
- Concise output

**Run it**:

```bash
uv run python examples/simple_openai_example.py
```

### 3. Comprehensive OpenAI Example

**File**: `openai_tracing_example.py`

**Purpose**: Multiple usage patterns in one script.

**Includes**:

1. Basic chat completion
2. Streaming chat completion
3. Multiple requests in sequence
4. Function/tool calling

**Run it**:

```bash
uv run python examples/openai_tracing_example.py
```

### 4. Async OpenAI Example

**File**: `async_openai_example.py`

**Purpose**: Async/await patterns with OpenAI.

**Includes**:

1. Basic async completion
2. Concurrent requests with `asyncio.gather()`
3. Async streaming with `async for`
4. Error handling in async context
5. Context manager patterns

**Run it**:

```bash
uv run python examples/async_openai_example.py
```

### 5. Diagnostic/Testing Script

**File**: `test_patching.py`

**Purpose**: Diagnose httpx patching issues.

**Use when**:

- Traces aren't appearing in backend
- Unsure if patching is working
- Debugging import order issues

**Run it**:

```bash
uv run python examples/test_patching.py
```

## How It Works

### Tracing Architecture

R4U uses HTTP-level tracing. Since OpenAI's Python client uses `httpx` internally, we can trace all API calls by patching httpx:

```python
from r4u.tracing.http.httpx import trace_all

# Patches httpx.Client and httpx.AsyncClient constructors
trace_all()

# Now ANY httpx client created will be automatically traced
# This includes OpenAI's internal httpx client
```

### What Gets Traced

Each OpenAI API call generates an `HTTPTrace` with:

**Request Details**:

- HTTP method (POST)
- Full URL (https://api.openai.com/v1/chat/completions)
- Request headers (including Authorization)
- Request body (messages, model, parameters)

**Response Details**:

- HTTP status code (200, 429, etc.)
- Response headers
- Response body (completion, usage, etc.)

**Timing Information**:

- Request start time
- Request completion time
- Total duration

**Error Information** (if applicable):

- Error messages
- Exception details

### Background Worker

Traces are sent asynchronously:

1. HTTP request is intercepted
2. Trace data is captured
3. Trace is queued
4. Background worker sends traces every 5 seconds
5. Backend receives and stores traces

This means there's a ~5 second delay before traces appear in your backend.

## Troubleshooting

### Traces Not Appearing

**Problem**: Made OpenAI API call but no trace in backend.

**Solutions**:

1. ✅ Check import order - `trace_all()` MUST be before `from openai import OpenAI`
2. ✅ Verify backend is running: `curl http://localhost:8000/health`
3. ✅ Wait 6+ seconds for background worker to send traces
4. ✅ Check backend logs for errors
5. ✅ Run `test_patching.py` diagnostic script

### "OPENAI_API_KEY environment variable not set"

**Solution**:

```bash
export OPENAI_API_KEY="sk-your-key-here"
```

### "Connection refused" to R4U backend

**Solutions**:

1. Start the backend: `cd backend && uvicorn app.main:app`
2. Check port: Backend should be on port 8000
3. Set custom URL: `export R4U_API_URL="http://localhost:9000"`

### "OpenAI library not installed"

**Solution**:

```bash
uv add openai
# or
pip install openai
```

### Traces Delayed

**Explanation**: Background worker sends traces every 5 seconds. Wait 6+ seconds after API calls.

**To flush immediately** (not implemented yet):

```python
# Future feature
client.close()  # Would flush remaining traces
```

## Advanced Usage

### Custom Tracer

Use a custom tracer instead of default:

```python
from r4u.client import R4UClient
from r4u.tracing.http.httpx import trace_all

# Create custom tracer
tracer = R4UClient(
    api_url="https://your-r4u-instance.com",
    timeout=60.0
)

# Use it for tracing
trace_all(tracer)
```

### Capturing Tracer for Testing

Capture traces in memory instead of sending to backend:

```python
from r4u.client import AbstractTracer, HTTPTrace
from r4u.tracing.http.httpx import trace_all

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
    print(f"  {trace.method} {trace.url} -> {trace.status_code}")
```

### Selective Tracing

Trace only specific clients:

```python
from r4u.tracing.http.httpx import trace_async_client
from r4u.client import get_r4u_client
import httpx

# Create client
client = httpx.AsyncClient()

# Trace only this specific client
tracer = get_r4u_client()
trace_async_client(client, tracer)

# This client is traced, but other httpx clients won't be
```

## Best Practices

1. **Call trace_all() early**: At the very start of your application, before any imports that use httpx
2. **Call untrace_all() on exit**: Clean up when your application shuts down
3. **Use environment variables**: Configure API keys and URLs via environment
4. **Monitor trace volume**: High-traffic apps generate many traces - consider sampling
5. **Secure sensitive data**: Traces include full request/response bodies - be careful with PII
6. **Wait for traces**: Remember the 5-second batch delay

## Example Template

Here's a minimal working template:

```python
#!/usr/bin/env python3
import os

# STEP 1: Enable tracing FIRST
from r4u.tracing.http.httpx import trace_all, untrace_all
trace_all()

# STEP 2: Import OpenAI
from openai import OpenAI

# STEP 3: Use OpenAI (automatically traced)
def main():
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hello!"}]
    )

    print(response.choices[0].message.content)

    # Wait for traces to be sent
    import time
    time.sleep(6)

    untrace_all()

if __name__ == "__main__":
    main()
```

## Learn More

- **HTTP Tracing Schema**: `../docs/HTTP_TRACING_SCHEMA.md`
- **Test Suite**: `../tests/` for more usage patterns
- **Main Documentation**: `../README.md`

## Support

Having issues? Check:

1. Import order (trace_all before OpenAI import)
2. Backend is running
3. Environment variables are set
4. Run diagnostic script: `test_patching.py`

For more help, see the main SDK documentation or open an issue.
