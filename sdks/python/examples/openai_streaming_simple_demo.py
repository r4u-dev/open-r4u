#!/usr/bin/env python3
"""
Simple OpenAI streaming demo with httpx tracing.

This example demonstrates the httpx streaming tracing system using
a simple streaming endpoint. It shows how streaming responses
are automatically traced.
"""

import asyncio

import httpx
from r4u.tracing.http.httpx import trace_async_client, trace_client


class SimpleStreamingTracer:
    """Simple tracer that shows streaming information."""
    
    def trace_request(self, request_info):
        """Override to show streaming-specific information."""
        print("\n=== STREAMING TRACE ===")
        print(f"{request_info.method} {request_info.url} -> {request_info.status_code}")
        if request_info.response_size:
            print(f"Response size: {request_info.response_size} bytes")
            print("✅ Streaming response traced!")
        else:
            print("❌ No response content")


async def test_async_streaming():
    """Test async streaming with httpx tracing."""
    print("\n" + "="*50)
    print("TESTING ASYNC STREAMING WITH HTTPX TRACING")
    print("="*50)
    
    tracer = SimpleStreamingTracer()
    
    async with httpx.AsyncClient() as client:
        trace_async_client(client, tracer)
        
        # Test streaming request
        print("\n1. Testing streaming request...")
        
        try:
            request = client.build_request(
                "GET",  # Use GET for httpbin.org/stream
                "https://httpbin.org/stream/3",
                headers={"Content-Type": "application/json"}
            )
            
            response = await client.send(request, stream=True)
            
            print(f"Response status: {response.status_code}")
            print("Streaming response:")
            
            chunk_count = 0
            total_bytes = 0
            
            async for chunk in response.aiter_bytes():
                chunk_count += 1
                total_bytes += len(chunk)
                print(f"  Chunk {chunk_count}: {len(chunk)} bytes")
            
            print(f"Total: {chunk_count} chunks, {total_bytes} bytes")
            
        except Exception as e:
            print(f"Error: {e}")


def test_sync_streaming():
    """Test sync streaming with httpx tracing."""
    print("\n" + "="*50)
    print("TESTING SYNC STREAMING WITH HTTPX TRACING")
    print("="*50)
    
    tracer = SimpleStreamingTracer()
    
    with httpx.Client() as client:
        trace_client(client, tracer)
        
        print("\n1. Testing streaming request...")
        
        try:
            request = client.build_request(
                "GET",
                "https://httpbin.org/stream/2",
                headers={"Content-Type": "application/json"}
            )
            
            response = client.send(request, stream=True)
            
            print(f"Response status: {response.status_code}")
            print("Streaming response:")
            
            chunk_count = 0
            total_bytes = 0
            
            for chunk in response.iter_bytes():
                chunk_count += 1
                total_bytes += len(chunk)
                print(f"  Chunk {chunk_count}: {len(chunk)} bytes")
            
            print(f"Total: {chunk_count} chunks, {total_bytes} bytes")
            
        except Exception as e:
            print(f"Error: {e}")


def demonstrate_streaming_tracing():
    """Demonstrate how streaming tracing works."""
    print("\n" + "="*50)
    print("STREAMING TRACING EXPLANATION")
    print("="*50)
    
    print("""
The httpx tracing system automatically detects and traces streaming responses:

1. How it works:
   - When stream=True is passed to client.send(), response is wrapped
   - Content is collected as it's read via iter_bytes() or aiter_bytes()
   - Complete response is reconstructed from all chunks
   - Trace is sent when streaming completes

2. What gets traced:
   - Complete request payload
   - Complete response payload (all chunks combined)
   - Accurate timing (full streaming duration)
   - Request/response sizes
   - Error information if any

3. Usage:
   ```python
   # Streaming request
   request = client.build_request("GET", url)
   response = await client.send(request, stream=True)
   
   async for chunk in response.aiter_bytes():
       process_chunk(chunk)
   # Complete trace sent here when streaming finishes
   ```

Key Benefits:
- ✅ Complete response content is captured
- ✅ Accurate timing includes full streaming duration
- ✅ Works with both sync and async httpx clients
- ✅ No changes needed to existing code
- ✅ Automatic detection using httpx's stream parameter
""")


async def main():
    """Run all streaming examples."""
    demonstrate_streaming_tracing()
    
    # Test async streaming
    await test_async_streaming()
    
    # Test sync streaming
    test_sync_streaming()
    
    print("\n" + "="*50)
    print("STREAMING TRACING DEMO COMPLETE")
    print("="*50)
    print("""
Key Takeaways:
1. Use client.send(request, stream=True) for streaming requests
2. Complete response content is automatically collected and traced
3. Accurate timing includes full streaming duration
4. Works with both sync and async httpx clients
5. Traces are sent when streaming completes or is aborted
""")


if __name__ == "__main__":
    asyncio.run(main())
