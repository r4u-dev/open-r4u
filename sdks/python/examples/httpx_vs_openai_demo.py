#!/usr/bin/env python3
"""
Comparison demo: httpx vs AsyncOpenAI approaches.

This example shows the difference between using httpx directly
vs using the AsyncOpenAI client from our tracing package.
"""

import asyncio

from r4u.tracing.openai import AsyncOpenAI


def demonstrate_approaches():
    """Demonstrate the different approaches to OpenAI streaming."""
    print("\n" + "="*70)
    print("HTTPX VS ASYNC OPENAI APPROACHES")
    print("="*70)
    
    print("""
APPROACH 1: Using httpx directly (what we had before)
====================================================

```python
import httpx
from r4u.tracing.http.httpx import trace_async_client

# You need to know about httpx
async with httpx.AsyncClient() as client:
    trace_async_client(client, tracer)
    
    # You need to build requests manually
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
    
    # You need to handle httpx responses
    response = await client.send(request, stream=True)
    
    # You need to parse streaming responses manually
    async for chunk in response.aiter_bytes():
        # Parse SSE format manually
        for line in chunk.decode('utf-8').strip().split('\\n'):
            if line.startswith('data: '):
                data = line[6:]
                if data == '[DONE]':
                    break
                # Parse JSON manually
                chunk_data = json.loads(data)
                # Extract content manually
                if 'choices' in chunk_data:
                    delta = chunk_data['choices'][0].get('delta', {})
                    if 'content' in delta:
                        print(delta['content'], end='')
```

Problems with httpx approach:
- ❌ Need to know httpx API
- ❌ Need to build requests manually
- ❌ Need to handle authentication manually
- ❌ Need to parse SSE format manually
- ❌ Need to extract content manually
- ❌ More error-prone
- ❌ More boilerplate code

APPROACH 2: Using AsyncOpenAI client (what we have now)
======================================================

```python
from r4u.tracing.openai import AsyncOpenAI

# Just use the high-level OpenAI API
client = AsyncOpenAI(api_key="your-api-key")

# Use OpenAI's clean API
stream = await client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}],
    stream=True
)

# Process streaming response easily
async for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

Benefits of AsyncOpenAI approach:
- ✅ Pure OpenAI API - no httpx knowledge needed
- ✅ Automatic request building
- ✅ Automatic authentication handling
- ✅ Automatic SSE parsing
- ✅ Automatic content extraction
- ✅ Less error-prone
- ✅ Less boilerplate code
- ✅ Same tracing benefits
- ✅ Compatible with existing OpenAI code

WHY THE ASYNC OPENAI APPROACH IS BETTER:
========================================

1. **Abstraction Level**: AsyncOpenAI provides a higher-level abstraction
2. **Ease of Use**: Much simpler API for common use cases
3. **Error Handling**: Better error handling and validation
4. **Type Safety**: Better type hints and IDE support
5. **Maintenance**: OpenAI handles API changes, not you
6. **Features**: Access to all OpenAI features easily
7. **Documentation**: Well-documented OpenAI API
8. **Community**: Large community using OpenAI client

The httpx approach is still useful for:
- Custom HTTP clients
- Non-OpenAI APIs
- Advanced HTTP configurations
- When you need low-level control

But for OpenAI specifically, AsyncOpenAI is the better choice!
""")


async def test_client_creation():
    """Test both approaches for client creation."""
    print("\n" + "="*70)
    print("TESTING CLIENT CREATION")
    print("="*70)
    
    print("\n1. Creating AsyncOpenAI client...")
    try:
        client = AsyncOpenAI(api_key="test-key")
        print("✅ AsyncOpenAI client created successfully")
        print(f"   Type: {type(client)}")
        print(f"   Has chat.completions: {hasattr(client, 'chat')}")
        print(f"   Has models: {hasattr(client, 'models')}")
        print(f"   Has embeddings: {hasattr(client, 'embeddings')}")
    except Exception as e:
        print(f"❌ Error creating AsyncOpenAI client: {e}")
    
    print("\n2. Comparing with httpx approach...")
    print("   httpx approach requires:")
    print("   - Import httpx")
    print("   - Create AsyncClient")
    print("   - Call trace_async_client")
    print("   - Build requests manually")
    print("   - Handle authentication manually")
    print("   - Parse responses manually")
    
    print("\n   AsyncOpenAI approach requires:")
    print("   - Import AsyncOpenAI")
    print("   - Create client with API key")
    print("   - Use high-level API methods")
    print("   - That's it!")


async def main():
    """Run the comparison demo."""
    demonstrate_approaches()
    await test_client_creation()
    
    print("\n" + "="*70)
    print("COMPARISON DEMO COMPLETE")
    print("="*70)
    print("""
Key Takeaways:
1. AsyncOpenAI provides a much cleaner API than httpx
2. No need to know about httpx when using OpenAI
3. Automatic handling of authentication, parsing, etc.
4. Same tracing benefits with much less code
5. Better error handling and type safety
6. More maintainable and less error-prone
7. Use AsyncOpenAI for OpenAI APIs, httpx for custom HTTP clients
""")


if __name__ == "__main__":
    asyncio.run(main())
