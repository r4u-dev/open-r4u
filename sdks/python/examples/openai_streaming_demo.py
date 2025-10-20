#!/usr/bin/env python3
"""
OpenAI streaming demo with httpx tracing (no API key required).

This example demonstrates the httpx streaming tracing system using
a mock OpenAI-like API endpoint. It shows how streaming responses
are automatically traced without requiring a real OpenAI API key.
"""

import asyncio
import json
from typing import Dict, Any

import httpx
from r4u.tracing.http.httpx import trace_async_client, trace_client
from r4u.client import R4UClient


class OpenAIStreamingTracer:
    """Custom tracer that shows OpenAI-style streaming information."""
    
    def trace_request(self, request_info):
        """Override to show OpenAI-style streaming information."""
        # RawRequestInfo from HTTP tracing
        print(f"\n=== OPENAI-STYLE STREAMING TRACE ===")
        print(f"Endpoint: {request_info.endpoint}")
        print(f"Operation: {request_info.operation_type}")
        print(f"Duration: {request_info.duration_ms:.2f}ms")
        print(f"Status: {request_info.status_code}")
        print(f"Request size: {request_info.request_size} bytes")
        print(f"Response size: {request_info.response_size} bytes")
        
        # Parse and show request details
        try:
            request_data = json.loads(request_info.request_payload.decode('utf-8'))
            print(f"Model: {request_data.get('model', 'unknown')}")
            print(f"Stream: {request_data.get('stream', False)}")
            print(f"Max tokens: {request_data.get('max_tokens', 'unlimited')}")
            print(f"Temperature: {request_data.get('temperature', 'default')}")
            
            # Show message count
            messages = request_data.get('messages', [])
            print(f"Messages: {len(messages)}")
            if messages:
                print(f"First message: {messages[0].get('role', 'unknown')} - {messages[0].get('content', '')[:50]}...")
            
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"Could not parse request: {e}")
            
            # Parse and show response details
            try:
                response_data = json.loads(request_info.response_payload.decode('utf-8'))
                if isinstance(response_data, list):
                    print(f"Stream chunks: {len(response_data)}")
                    # Show first and last chunk info
                    if response_data:
                        first_chunk = response_data[0]
                        last_chunk = response_data[-1]
                        print(f"First chunk: {first_chunk.get('choices', [{}])[0].get('delta', {}).get('content', '')[:30]}...")
                        if len(response_data) > 1:
                            print(f"Last chunk: {last_chunk.get('choices', [{}])[0].get('delta', {}).get('content', '')[:30]}...")
                else:
                    print(f"Response type: {type(response_data)}")
                    
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"Could not parse response: {e}")
            
            print("✅ OpenAI-style streaming response traced!")
        else:
            # Fallback for other tracers
            print(f"\n=== OPENAI-STYLE STREAMING TRACE (Legacy) ===")
            print(f"{request_info.method} {request_info.url} -> {request_info.status_code}")
            if request_info.response_size:
                print(f"Response size: {request_info.response_size} bytes")
                print("✅ OpenAI-style streaming response traced!")


async def test_openai_style_streaming():
    """Test OpenAI-style streaming with httpx tracing using mock endpoint."""
    print("\n" + "="*70)
    print("TESTING OPENAI-STYLE STREAMING WITH HTTPX TRACING")
    print("="*70)
    
    # Create a tracer
    tracer = OpenAIStreamingTracer()
    
    # Create and trace an async httpx client
    async with httpx.AsyncClient() as client:
        trace_async_client(client, tracer)
        
        # Test 1: Simple streaming chat completion (using httpbin.org/stream)
        print("\n1. Testing simple streaming chat completion...")
        
        request_data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant. Keep responses concise."},
                {"role": "user", "content": "Explain quantum computing in one sentence."}
            ],
            "stream": True,
            "max_tokens": 100,
            "temperature": 0.7
        }
        
        try:
            # Build request and send with streaming
            request = client.build_request(
                "POST",
                "https://httpbin.org/stream/3",  # Mock streaming endpoint
                json=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            response = await client.send(request, stream=True)
            
            print(f"Response status: {response.status_code}")
            print("Streaming response:")
            
            # Read the streaming response
            collected_content = ""
            chunk_count = 0
            
            async for chunk in response.aiter_bytes():
                chunk_count += 1
                chunk_text = chunk.decode('utf-8')
                print(f"Chunk {chunk_count}: {len(chunk_text)} bytes")
                collected_content += chunk_text
            
            print(f"\nComplete response: {len(collected_content)} bytes")
            print(f"Total chunks received: {chunk_count}")
            
        except Exception as e:
            print(f"Error in streaming test: {e}")
        
        # Test 2: Streaming with tools
        print("\n\n2. Testing streaming with tools...")
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get the current weather in a given location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The city and state, e.g. San Francisco, CA"
                            }
                        },
                        "required": ["location"]
                    }
                }
            }
        ]
        
        request_data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant. Use tools when appropriate."},
                {"role": "user", "content": "What's the weather like in Paris, France? Please use the weather tool."}
            ],
            "tools": tools,
            "tool_choice": "auto",
            "stream": True,
            "max_tokens": 200,
            "temperature": 0.5
        }
        
        try:
            request = client.build_request(
                "POST",
                "https://httpbin.org/stream/2",  # Mock streaming endpoint
                json=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            response = await client.send(request, stream=True)
            
            print(f"Response status: {response.status_code}")
            print("Streaming response with tools:")
            
            collected_content = ""
            chunk_count = 0
            
            async for chunk in response.aiter_bytes():
                chunk_count += 1
                chunk_text = chunk.decode('utf-8')
                print(f"Chunk {chunk_count}: {len(chunk_text)} bytes")
                collected_content += chunk_text
            
            print(f"\nComplete response: {len(collected_content)} bytes")
            print(f"Total chunks received: {chunk_count}")
            
        except Exception as e:
            print(f"Error in tools streaming test: {e}")


def test_sync_openai_style_streaming():
    """Test OpenAI-style streaming with sync httpx client."""
    print("\n" + "="*70)
    print("TESTING SYNC OPENAI-STYLE STREAMING")
    print("="*70)
    
    tracer = OpenAIStreamingTracer()
    
    with httpx.Client() as client:
        trace_client(client, tracer)
        
        request_data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "user", "content": "Tell me a short joke about programming."}
            ],
            "stream": True,
            "max_tokens": 50
        }
        
        try:
            request = client.build_request(
                "POST",
                "https://httpbin.org/stream/2",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            response = client.send(request, stream=True)
            
            print(f"Response status: {response.status_code}")
            print("Streaming response:")
            
            chunk_count = 0
            for chunk in response.iter_bytes():
                chunk_count += 1
                chunk_text = chunk.decode('utf-8')
                print(f"Chunk {chunk_count}: {len(chunk_text)} bytes")
            
            print(f"Total chunks received: {chunk_count}")
            
        except Exception as e:
            print(f"Error in sync streaming test: {e}")



def demonstrate_openai_streaming_tracing():
    """Demonstrate how OpenAI streaming tracing works."""
    print("\n" + "="*70)
    print("OPENAI STREAMING TRACING EXPLANATION")
    print("="*70)
    
    print("""
The httpx tracing system works seamlessly with OpenAI streaming API calls:

1. OpenAI Streaming API:
   - Uses Server-Sent Events (SSE) format
   - Each chunk contains partial response data
   - Final chunk contains '[DONE]' marker

2. How httpx tracing works:
   - When stream=True is passed to client.send(), response is wrapped
   - Content is collected as it's read via aiter_bytes() or iter_bytes()
   - Complete response is reconstructed from all chunks
   - Trace is sent when streaming completes

3. What gets traced:
   - Complete request payload (model, messages, parameters)
   - Complete response payload (all chunks combined)
   - Accurate timing (full streaming duration)
   - Request/response sizes
   - Error information if any

4. Usage:
   ```python
   # OpenAI streaming request
   request = client.build_request("POST", "https://api.openai.com/v1/chat/completions", 
                                 json={"model": "gpt-4", "messages": [...], "stream": True})
   response = await client.send(request, stream=True)
   
   async for chunk in response.aiter_bytes():
       # Process SSE chunks
       process_chunk(chunk)
   # Complete trace sent here when streaming finishes
   ```

Key Benefits:
- ✅ Complete OpenAI response content is captured
- ✅ Accurate timing includes full streaming duration
- ✅ Works with tools, function calling, and all OpenAI features
- ✅ No changes needed to existing OpenAI streaming code
- ✅ Automatic detection using httpx's stream parameter
""")


async def main():
    """Run all OpenAI streaming examples."""
    demonstrate_openai_streaming_tracing()
    
    # Test async streaming
    await test_openai_style_streaming()
    
    # Test sync streaming
    test_sync_openai_style_streaming()
    
    
    print("\n" + "="*70)
    print("OPENAI STREAMING TRACING DEMO COMPLETE")
    print("="*70)
    print("""
Key Takeaways:
1. Use client.send(request, stream=True) for OpenAI streaming
2. Complete response content is automatically collected and traced
3. Works with all OpenAI features: chat, tools, function calling
4. Accurate timing includes full streaming duration
5. No changes needed to existing OpenAI streaming code
6. Traces are sent when streaming completes or is aborted
7. Works with both sync and async httpx clients
""")


if __name__ == "__main__":
    asyncio.run(main())
