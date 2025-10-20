# OpenAI Streaming Tracing Solution

## Overview

This document explains the complete solution for tracing OpenAI streaming requests using the r4u tracing package. The solution provides automatic tracing for both streaming and non-streaming OpenAI requests without requiring any knowledge of the underlying HTTP client (httpx).

## The Problem

When using OpenAI's streaming API, the response content is not immediately available. Instead, it's received in chunks over time. This makes it challenging to trace the complete request/response cycle because:

1. The response object is not the final result
2. Content is received incrementally
3. We need to capture the complete response after streaming is finished
4. We need to handle both successful completion and errors/aborts

## The Solution

The r4u tracing package provides a complete solution that handles all these challenges automatically:

### 1. High-Level AsyncOpenAI Client

```python
from r4u.tracing.openai import AsyncOpenAI

# Create client (automatically traces requests)
client = AsyncOpenAI(api_key="your-api-key")

# Use only the high-level OpenAI API
stream = await client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}],
    stream=True
)

# Process streaming response
async for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

### 2. Automatic Tracing

The AsyncOpenAI client automatically:
- Traces the underlying httpx client
- Detects streaming requests via `stream=True` parameter
- Collects complete response content during streaming
- Sends traces when requests complete (success or error)
- Handles all OpenAI features: chat, tools, function calling

### 3. No httpx Knowledge Required

You never need to:
- Import httpx
- Know about httpx
- Use httpx directly
- Build requests manually
- Handle authentication manually
- Parse responses manually

## How It Works

### 1. Client Wrapping

The `AsyncOpenAI` class wraps the original OpenAI client:

```python
class AsyncOpenAI(OriginalAsyncOpenAI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        trace_async_client(self._client, UniversalTracer(get_r4u_client(), "openai"))
```

### 2. Streaming Detection

The tracing system detects streaming requests by checking the `stream=True` parameter:

```python
def _is_streaming_request(request: httpx.Request) -> bool:
    """Check if this is a streaming request based on the stream parameter."""
    return getattr(request, '_stream', False)
```

### 3. Response Wrapping

For streaming requests, the response is wrapped with a `StreamingResponseWrapper`:

```python
class StreamingResponseWrapper:
    """Wrapper for httpx.Response that tracks streaming completion and collects content."""
    
    def __init__(self, response: httpx.Response, request_info: Any, tracer: AbstractTracer):
        self._response = response
        self._request_info = request_info
        self._tracer = tracer
        self._content_collected = b""
        self._is_streaming_complete = False
        self._error = None
    
    # Delegate all attributes to the original response
    def __getattr__(self, name):
        return getattr(self._response, name)
    
    # Override streaming methods to track content
    async def aiter_bytes(self, chunk_size: Optional[int] = None):
        try:
            async for chunk in self._response.aiter_bytes(chunk_size):
                self._content_collected += chunk
                yield chunk
        except Exception as e:
            self._error = str(e)
            raise
        finally:
            self._complete_streaming()
```

### 4. Content Collection

The wrapper collects content from all streaming methods:
- `aiter_bytes()` - collects raw bytes
- `aiter_text()` - collects text content
- `aiter_lines()` - collects line-by-line content
- `aread()` - collects complete response
- `aclose()` - handles connection closure

### 5. Trace Completion

When streaming completes, the wrapper:
- Updates the request info with collected content
- Calculates accurate timing (includes full streaming duration)
- Sends the complete trace

```python
def _complete_streaming(self):
    """Complete the streaming trace when streaming is finished."""
    if self._is_streaming_complete:
        return
    
    self._is_streaming_complete = True
    
    # Update request info with collected content
    self._update_raw_request_info_with_content()
    
    # Send trace
    self._tracer.trace_request(self._request_info)
```

## Key Benefits

### 1. **Pure OpenAI API**
- Use only the high-level OpenAI API
- No need to know about httpx
- Compatible with existing OpenAI code

### 2. **Automatic Tracing**
- No manual setup required
- All requests are automatically traced
- Works with streaming and non-streaming requests

### 3. **Complete Response Content**
- Captures the complete response content
- Handles all streaming methods
- Works with chunked responses

### 4. **Accurate Timing**
- Includes full streaming duration
- Measures from request start to completion
- Handles both success and error cases

### 5. **Error Handling**
- Captures errors during streaming
- Handles connection aborts
- Provides error context in traces

### 6. **All OpenAI Features**
- Chat completions
- Function calling
- Tool usage
- Models API
- Embeddings API
- And more

## Usage Examples

### Basic Streaming

```python
from r4u.tracing.openai import AsyncOpenAI

client = AsyncOpenAI(api_key="your-api-key")

stream = await client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}],
    stream=True
)

async for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

### Streaming with Tools

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"}
                },
                "required": ["location"]
            }
        }
    }
]

stream = await client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "What's the weather in Paris?"}],
    tools=tools,
    tool_choice="auto",
    stream=True
)

async for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
    elif chunk.choices[0].delta.tool_calls:
        print(f"[Tool calls: {len(chunk.choices[0].delta.tool_calls)}]")
```

### Non-Streaming Requests

```python
response = await client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}],
    max_tokens=100
)

print(response.choices[0].message.content)
```

## Comparison with httpx Approach

### httpx Approach (Not Recommended for OpenAI)

```python
import httpx
from r4u.tracing.http.httpx import trace_async_client

async with httpx.AsyncClient() as client:
    trace_async_client(client, tracer)
    
    request = client.build_request(
        "POST",
        "https://api.openai.com/v1/chat/completions",
        json={
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hello!"}],
            "stream": True
        },
        headers={"Authorization": f"Bearer {api_key}"}
    )
    
    response = await client.send(request, stream=True)
    
    async for chunk in response.aiter_bytes():
        # Parse SSE format manually
        for line in chunk.decode('utf-8').strip().split('\n'):
            if line.startswith('data: '):
                data = line[6:]
                if data == '[DONE]':
                    break
                chunk_data = json.loads(data)
                if 'choices' in chunk_data:
                    delta = chunk_data['choices'][0].get('delta', {})
                    if 'content' in delta:
                        print(delta['content'], end='')
```

**Problems:**
- Need to know httpx API
- Need to build requests manually
- Need to handle authentication manually
- Need to parse SSE format manually
- Need to extract content manually
- More error-prone
- More boilerplate code

### AsyncOpenAI Approach (Recommended)

```python
from r4u.tracing.openai import AsyncOpenAI

client = AsyncOpenAI(api_key="your-api-key")

stream = await client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}],
    stream=True
)

async for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

**Benefits:**
- Pure OpenAI API - no httpx knowledge needed
- Automatic request building
- Automatic authentication handling
- Automatic SSE parsing
- Automatic content extraction
- Less error-prone
- Less boilerplate code
- Same tracing benefits
- Compatible with existing OpenAI code

## Conclusion

The r4u tracing package provides a complete solution for tracing OpenAI streaming requests that:

1. **Eliminates the need for httpx knowledge** - Use only the high-level OpenAI API
2. **Provides automatic tracing** - No manual setup required
3. **Captures complete response content** - Handles all streaming scenarios
4. **Offers accurate timing** - Includes full streaming duration
5. **Handles all OpenAI features** - Chat, tools, function calling, etc.
6. **Is easy to use** - Just import and use the AsyncOpenAI client

This solution makes it easy to add comprehensive tracing to OpenAI applications without any of the complexity of handling HTTP clients directly.
