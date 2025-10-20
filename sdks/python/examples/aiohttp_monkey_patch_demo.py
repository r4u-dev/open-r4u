#!/usr/bin/env python3
"""
Demonstration of aiohttp monkey patching for automatic tracing.

This example shows how to use the monkey patching functionality to automatically
trace all aiohttp clients without manually patching each instance.
"""

import asyncio
import aiohttp
from r4u.tracing.http.aiohttp import trace_all, untrace_all


async def demo_basic_requests():
    """Demonstrate basic aiohttp requests with monkey patching."""
    print("🔍 Testing basic aiohttp requests with monkey patching...")
    
    async with aiohttp.ClientSession() as session:
        try:
            # These requests will be automatically traced
            async with session.get("https://httpbin.org/get") as response:
                data = await response.json()
                print(f"✓ GET request completed: {response.status}")
            
            async with session.post("https://httpbin.org/post", 
                                  json={"message": "Hello from aiohttp"}) as response:
                data = await response.json()
                print(f"✓ POST request completed: {response.status}")
                
        except Exception as e:
            print(f"✗ Request failed: {e}")



async def demo_concurrent_requests():
    """Demonstrate concurrent requests with tracing."""
    print("🔍 Testing concurrent requests with monkey patching...")
    
    async with aiohttp.ClientSession() as session:
        # Create multiple concurrent requests
        tasks = []
        for i in range(3):
            task = session.get(f"https://httpbin.org/delay/{i+1}")
            tasks.append(task)
        
        try:
            # Execute all requests concurrently
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, response in enumerate(responses):
                if isinstance(response, Exception):
                    print(f"✗ Request {i+1} failed: {response}")
                else:
                    async with response:
                        print(f"✓ Concurrent request {i+1} completed: {response.status}")
                        
        except Exception as e:
            print(f"✗ Concurrent requests failed: {e}")


async def demo_streaming_response():
    """Demonstrate streaming response handling."""
    print("🔍 Testing streaming response with monkey patching...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("https://httpbin.org/stream/5") as response:
                print(f"✓ Streaming request started: {response.status}")
                
                # Read streaming response
                chunk_count = 0
                async for line in response.content:
                    chunk_count += 1
                    if chunk_count <= 3:  # Show first 3 chunks
                        print(f"  📦 Chunk {chunk_count}: {line.decode().strip()}")
                
                print(f"✓ Streaming completed: {chunk_count} chunks received")
                
        except Exception as e:
            print(f"✗ Streaming request failed: {e}")


async def main():
    """Main demonstration function."""
    print("🚀 Starting aiohttp monkey patching demonstration\n")
    
    # Enable monkey patching for all aiohttp clients
    print("📝 Enabling monkey patching for aiohttp...")
    trace_all()
    print("✓ Monkey patching enabled - all new aiohttp sessions will be automatically traced\n")
    
    # Test basic requests
    await demo_basic_requests()
    print()
    
    
    # Test concurrent requests
    await demo_concurrent_requests()
    print()
    
    # Test streaming response
    await demo_streaming_response()
    print()
    
    # Disable monkey patching
    print("📝 Disabling monkey patching...")
    untrace_all()
    print("✓ Monkey patching disabled - aiohttp sessions will no longer be automatically traced\n")
    
    print("🎉 Demonstration completed!")
    print("\n💡 Key benefits of aiohttp monkey patching:")
    print("   • No need to manually patch each aiohttp session")
    print("   • Works with all HTTP methods (GET, POST, PUT, DELETE, etc.)")
    print("   • Supports concurrent and streaming requests")
    print("   • Can be enabled/disabled globally")


if __name__ == "__main__":
    asyncio.run(main())
