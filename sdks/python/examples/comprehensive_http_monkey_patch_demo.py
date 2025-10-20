#!/usr/bin/env python3
"""
Comprehensive demonstration of HTTP library monkey patching.

This example shows how to use the monkey patching functionality to automatically
trace all HTTP requests from multiple libraries (httpx, aiohttp, requests) without
manually patching each instance.
"""

import asyncio
import httpx
import aiohttp
import requests
from r4u.tracing.http.auto import trace_all_http, untrace_all_http


async def demo_httpx_requests():
    """Demonstrate httpx requests with monkey patching."""
    print("🔍 Testing httpx with monkey patching...")
    
    # Sync httpx client
    with httpx.Client() as client:
        try:
            response = client.get("https://httpbin.org/get")
            print(f"✓ httpx sync request completed: {response.status_code}")
        except Exception as e:
            print(f"✗ httpx sync request failed: {e}")
    
    # Async httpx client
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("https://httpbin.org/get")
            print(f"✓ httpx async request completed: {response.status_code}")
        except Exception as e:
            print(f"✗ httpx async request failed: {e}")


async def demo_aiohttp_requests():
    """Demonstrate aiohttp requests with monkey patching."""
    print("🔍 Testing aiohttp with monkey patching...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("https://httpbin.org/get") as response:
                print(f"✓ aiohttp request completed: {response.status}")
        except Exception as e:
            print(f"✗ aiohttp request failed: {e}")


def demo_requests_library():
    """Demonstrate requests library with monkey patching."""
    print("🔍 Testing requests library with monkey patching...")
    
    try:
        response = requests.get("https://httpbin.org/get")
        print(f"✓ requests library request completed: {response.status_code}")
    except Exception as e:
        print(f"✗ requests library request failed: {e}")


async def demo_mixed_http_libraries():
    """Demonstrate using multiple HTTP libraries together."""
    print("🔍 Testing mixed HTTP libraries with monkey patching...")
    
    # Create tasks for different HTTP libraries
    tasks = []
    
    # httpx async task
    async def httpx_task():
        async with httpx.AsyncClient() as client:
            response = await client.get("https://httpbin.org/get")
            return f"httpx: {response.status_code}"
    
    # aiohttp task
    async def aiohttp_task():
        async with aiohttp.ClientSession() as session:
            async with session.get("https://httpbin.org/get") as response:
                return f"aiohttp: {response.status}"
    
    # Add tasks
    tasks.append(httpx_task())
    tasks.append(aiohttp_task())
    
    # Execute concurrently
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                print(f"✗ Task failed: {result}")
            else:
                print(f"✓ {result}")
    except Exception as e:
        print(f"✗ Mixed HTTP libraries test failed: {e}")


async def main():
    """Main demonstration function."""
    print("🚀 Starting comprehensive HTTP monkey patching demonstration\n")
    
    # Enable monkey patching for all HTTP libraries
    print("📝 Enabling monkey patching for all HTTP libraries...")
    trace_all_http()
    print("✓ Monkey patching enabled - all HTTP libraries will be automatically traced\n")
    
    # Test individual libraries
    await demo_httpx_requests()
    print()
    
    await demo_aiohttp_requests()
    print()
    
    demo_requests_library()
    print()
    
    # Test mixed usage
    await demo_mixed_http_libraries()
    print()
    
    
    # Disable monkey patching
    print("📝 Disabling monkey patching...")
    untrace_all_http()
    print("✓ Monkey patching disabled - HTTP libraries will no longer be automatically traced\n")
    
    print("🎉 Comprehensive demonstration completed!")
    print("\n💡 Key benefits of comprehensive HTTP monkey patching:")
    print("   • Single function call enables tracing for all HTTP libraries")
    print("   • Works with sync and async HTTP clients")
    print("   • Supports concurrent requests across different libraries")
    print("   • Global enable/disable control")
    print("   • No need to manually patch individual instances")
    print("\n📚 Supported HTTP libraries:")
    print("   • httpx (sync and async)")
    print("   • aiohttp (async)")
    print("   • requests (sync)")


if __name__ == "__main__":
    asyncio.run(main())
