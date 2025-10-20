#!/usr/bin/env python3
"""
Example demonstrating httpx streaming response tracing.

This example shows how the r4u library automatically detects and traces
streaming HTTP responses, collecting the complete response content when
streaming is finished.
"""

import asyncio
import json

import httpx
from r4u.tracing.http.httpx import trace_async_client, trace_client
from r4u.client import R4UClient


class StreamingTracer:
    """Custom tracer that shows streaming detection."""
    
    def trace_request(self, request_info):
        """Override to show streaming-specific information."""
        # RawRequestInfo from HTTP tracing
        print("\n=== STREAMING TRACE (Raw) ===")
        print(f"Endpoint: {request_info.endpoint}")
        print(f"Operation: {request_info.operation_type}")
        print(f"Duration: {request_info.duration_ms:.2f}ms")
        print(f"Status: {request_info.status_code}")
        print(f"Request size: {request_info.request_size} bytes")
        print(f"Response size: {request_info.response_size} bytes")
        
        # Show if this was a streaming response
        if request_info.response_size > 0:
            try:
                response_data = json.loads(request_info.response_payload.decode('utf-8'))
                if isinstance(response_data, dict) and 'stream' in str(response_data):
                    print("✅ Streaming response detected and traced!")
                else:
                    print("📄 Regular response traced")
            except Exception:
                print("📄 Response traced (non-JSON)")
        else:
            # RawRequestInfo from HTTP tracing
            print("\n=== STREAMING TRACE (Legacy) ===")
            print(f"{request_info.method} {request_info.url} -> {request_info.status_code}")
            if request_info.response_size:
                print(f"Response size: {request_info.response_size} bytes")
                print("✅ Streaming response detected and traced!")


async def test_async_streaming():
    """Test async streaming with httpx."""
    print("\n" + "="*60)
    print("TESTING ASYNC STREAMING WITH HTTPX")
    print("="*60)
    
    # Create a tracer
    tracer = StreamingTracer()
    
    # Create and trace an async client
    async with httpx.AsyncClient() as client:
        trace_async_client(client, tracer)
        
        # Test 1: Simulate a streaming API call (like OpenAI chat completions)
        print("\n1. Testing streaming chat completions simulation...")
        
        # Create a mock streaming request
        request_data = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hello, world!"}],
            "stream": True,  # This will trigger streaming detection
            "max_tokens": 100
        }
        
        try:
            # Method 1: Using client.send() with stream=True (recommended for streaming)
            print("Using client.send() with stream=True...")
            request = client.build_request("POST", "https://httpbin.org/stream/5", json=request_data)
            response = await client.send(request, stream=True)
            
            print(f"Response status: {response.status_code}")
            print("Reading streaming response...")
            
            # Read the streaming response
            collected_content = b""
            async for chunk in response.iter_bytes():
                collected_content += chunk
                print(f"Received chunk: {len(chunk)} bytes")
            
            print(f"Total content collected: {len(collected_content)} bytes")
            
        except Exception as e:
            print(f"Error in streaming test: {e}")
        
        # Test 2: Regular (non-streaming) request
        print("\n2. Testing regular (non-streaming) request...")
        
        try:
            response = await client.get("https://httpbin.org/json")
            print(f"Response status: {response.status_code}")
            print(f"Response content length: {len(response.content)} bytes")
            
        except Exception as e:
            print(f"Error in regular request: {e}")


def test_sync_streaming():
    """Test sync streaming with httpx."""
    print("\n" + "="*60)
    print("TESTING SYNC STREAMING WITH HTTPX")
    print("="*60)
    
    # Create a tracer
    tracer = StreamingTracer()
    
    # Create and trace a sync client
    with httpx.Client() as client:
        trace_client(client, tracer)
        
        # Test 1: Simulate a streaming API call
        print("\n1. Testing streaming chat completions simulation...")
        
        request_data = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hello, world!"}],
            "stream": True,  # This will trigger streaming detection
            "max_tokens": 100
        }
        
        try:
            # Method 1: Using client.send() with stream=True (recommended for streaming)
            print("Using client.send() with stream=True...")
            request = client.build_request("POST", "https://httpbin.org/stream/3", json=request_data)
            response = client.send(request, stream=True)
            
            print(f"Response status: {response.status_code}")
            print("Reading streaming response...")
            
            # Read the streaming response
            collected_content = b""
            for chunk in response.iter_bytes():
                collected_content += chunk
                print(f"Received chunk: {len(chunk)} bytes")
            
            print(f"Total content collected: {len(collected_content)} bytes")
            
        except Exception as e:
            print(f"Error in streaming test: {e}")
        
        # Test 2: Regular (non-streaming) request
        print("\n2. Testing regular (non-streaming) request...")
        
        try:
            response = client.get("https://httpbin.org/json")
            print(f"Response status: {response.status_code}")
            print(f"Response content length: {len(response.content)} bytes")
            
        except Exception as e:
            print(f"Error in regular request: {e}")



def demonstrate_streaming_detection():
    """Demonstrate how streaming detection works."""
    print("\n" + "="*60)
    print("STREAMING DETECTION EXPLANATION")
    print("="*60)
    
    print("""
The httpx tracing system detects streaming responses using httpx's stream parameter:

1. httpx stream parameter:
   - client.send(request, stream=True) - the most reliable way to indicate streaming
   - When stream=True is passed, the response is wrapped for tracing
   - No complex detection logic needed - just use the stream parameter

2. How it works:
   - When stream=True is passed to client.send(), response is wrapped
   - Content is collected as it's read via iter_bytes(), iter_text(), etc.
   - Trace is sent only when streaming completes or is aborted

3. Usage:
   ```python
   # Streaming request (recommended approach)
   request = client.build_request("POST", url, json=data)
   response = await client.send(request, stream=True)
   async for chunk in response.iter_bytes():
       process_chunk(chunk)
   # Trace sent here when streaming completes
   
   # Regular request  
   response = await client.post(url, json=data)
   # Trace sent immediately
   ```

Key Benefits:
- ✅ Simple and reliable - uses httpx's own stream parameter
- ✅ Complete response content is captured
- ✅ Accurate timing (includes full streaming duration)
- ✅ Works with both sync and async httpx clients
- ✅ No complex detection logic needed
- ✅ Handles errors and aborted streams gracefully
""")


async def main():
    """Run all streaming examples."""
    demonstrate_streaming_detection()
    
    # Test async streaming
    await test_async_streaming()
    
    # Test sync streaming
    test_sync_streaming()
    
    
    print("\n" + "="*60)
    print("STREAMING TRACING DEMO COMPLETE")
    print("="*60)
    print("""
Key Takeaways:
1. Use client.send(request, stream=True) for streaming requests
2. Streaming responses are automatically wrapped and traced
3. Complete response content is collected during streaming
4. Traces are sent when streaming completes or is aborted
5. Provides detailed tracing information
6. Simple and reliable - uses httpx's own stream parameter
""")


if __name__ == "__main__":
    asyncio.run(main())
