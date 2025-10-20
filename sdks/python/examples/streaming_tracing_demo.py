#!/usr/bin/env python3
"""
Comprehensive demonstration of streaming tracing for HTTP libraries.

This example shows how streaming tracing works with aiohttp and requests,
similar to the httpx streaming implementation.
"""

import asyncio
import aiohttp
import requests
from r4u.tracing.http.auto import trace_all_http, untrace_all_http


async def demo_aiohttp_streaming():
    """Demonstrate aiohttp streaming tracing."""
    print("🔍 aiohttp Streaming Tracing Demo")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Streaming with iter_chunked
        print("📡 Test 1: Streaming with iter_chunked")
        try:
            async with session.get("https://httpbin.org/stream/5") as response:
                print(f"   Status: {response.status}")
                chunk_count = 0
                async for chunk in response.iter_chunked(1024):
                    chunk_count += 1
                    print(f"   📦 Chunk {chunk_count}: {len(chunk)} bytes")
                    if chunk_count >= 3:  # Limit for demo
                        break
                print(f"   ✅ Received {chunk_count} chunks")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
        
        # Test 2: Streaming with iter_any
        print("📡 Test 2: Streaming with iter_any")
        try:
            async with session.get("https://httpbin.org/stream/3") as response:
                print(f"   Status: {response.status}")
                chunk_count = 0
                async for chunk in response.iter_any():
                    chunk_count += 1
                    print(f"   📦 Chunk {chunk_count}: {len(chunk)} bytes")
                    if chunk_count >= 2:  # Limit for demo
                        break
                print(f"   ✅ Received {chunk_count} chunks")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
        
        # Test 3: Non-streaming (direct read)
        print("📡 Test 3: Non-streaming (direct read)")
        try:
            async with session.get("https://httpbin.org/get") as response:
                print(f"   Status: {response.status}")
                content = await response.read()
                print(f"   📄 Response size: {len(content)} bytes")
                print("   ✅ Non-streaming read completed")
        except Exception as e:
            print(f"   ❌ Error: {e}")


def demo_requests_streaming():
    """Demonstrate requests streaming tracing."""
    print("\n🔍 requests Streaming Tracing Demo")
    print("=" * 50)
    
    # Test 1: Streaming with iter_content
    print("📡 Test 1: Streaming with iter_content")
    try:
        response = requests.get("https://httpbin.org/stream/5", stream=True)
        print(f"   Status: {response.status_code}")
        chunk_count = 0
        for chunk in response.iter_content(chunk_size=1024):
            chunk_count += 1
            print(f"   📦 Chunk {chunk_count}: {len(chunk)} bytes")
            if chunk_count >= 3:  # Limit for demo
                break
        print(f"   ✅ Received {chunk_count} chunks")
        response.close()
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    
    # Test 2: Streaming with iter_lines
    print("📡 Test 2: Streaming with iter_lines")
    try:
        response = requests.get("https://httpbin.org/stream/3", stream=True)
        print(f"   Status: {response.status_code}")
        line_count = 0
        for line in response.iter_lines():
            line_count += 1
            print(f"   📄 Line {line_count}: {len(line)} bytes")
            if line_count >= 2:  # Limit for demo
                break
        print(f"   ✅ Received {line_count} lines")
        response.close()
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    
    # Test 3: Non-streaming (stream=False)
    print("📡 Test 3: Non-streaming (stream=False)")
    try:
        response = requests.get("https://httpbin.org/get", stream=False)
        print(f"   Status: {response.status_code}")
        print(f"   📄 Response size: {len(response.content)} bytes")
        print("   ✅ Non-streaming read completed")
        response.close()
    except Exception as e:
        print(f"   ❌ Error: {e}")


async def demo_mixed_streaming():
    """Demonstrate mixed streaming across libraries."""
    print("\n🔍 Mixed Library Streaming Demo")
    print("=" * 50)
    
    # Concurrent streaming with both libraries
    print("📡 Concurrent streaming with aiohttp and requests")
    
    async def aiohttp_task():
        async with aiohttp.ClientSession() as session:
            async with session.get("https://httpbin.org/stream/2") as response:
                chunk_count = 0
                async for chunk in response.iter_chunked(1024):
                    chunk_count += 1
                    print(f"   🔄 aiohttp chunk {chunk_count}: {len(chunk)} bytes")
                return f"aiohttp: {chunk_count} chunks"
    
    def requests_task():
        response = requests.get("https://httpbin.org/stream/2", stream=True)
        chunk_count = 0
        for chunk in response.iter_content(chunk_size=1024):
            chunk_count += 1
            print(f"   🔄 requests chunk {chunk_count}: {len(chunk)} bytes")
        response.close()
        return f"requests: {chunk_count} chunks"
    
    try:
        # Run aiohttp task
        aiohttp_result = await aiohttp_task()
        print(f"   ✅ {aiohttp_result}")
        
        # Run requests task
        requests_result = requests_task()
        print(f"   ✅ {requests_result}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")


async def demo_streaming_vs_non_streaming():
    """Demonstrate the difference between streaming and non-streaming."""
    print("\n🔍 Streaming vs Non-Streaming Comparison")
    print("=" * 50)
    
    print("📡 requests: stream=True vs stream=False")
    
    # Streaming
    print("   🔄 Streaming (stream=True):")
    try:
        response = requests.get("https://httpbin.org/stream/2", stream=True)
        print(f"      Status: {response.status_code}")
        chunk_count = 0
        for chunk in response.iter_content(chunk_size=1024):
            chunk_count += 1
            print(f"      📦 Chunk {chunk_count}: {len(chunk)} bytes")
        print(f"      ✅ Streaming: {chunk_count} chunks received")
        response.close()
    except Exception as e:
        print(f"      ❌ Streaming error: {e}")
    
    # Non-streaming
    print("   📄 Non-streaming (stream=False):")
    try:
        response = requests.get("https://httpbin.org/get", stream=False)
        print(f"      Status: {response.status_code}")
        print(f"      📄 Content size: {len(response.content)} bytes")
        print("      ✅ Non-streaming: content loaded at once")
        response.close()
    except Exception as e:
        print(f"      ❌ Non-streaming error: {e}")


async def main():
    """Main demonstration function."""
    print("🚀 Starting Streaming Tracing Demonstration")
    print("=" * 60)
    print()
    
    # Enable monkey patching for all HTTP libraries
    print("📝 Enabling monkey patching for all HTTP libraries...")
    trace_all_http()
    print("✅ Monkey patching enabled - streaming tracing is now active\n")
    
    # Demo aiohttp streaming
    await demo_aiohttp_streaming()
    
    # Demo requests streaming
    demo_requests_streaming()
    
    # Demo mixed streaming
    await demo_mixed_streaming()
    
    # Demo streaming vs non-streaming
    await demo_streaming_vs_non_streaming()
    
    # Disable monkey patching
    print("\n📝 Disabling monkey patching...")
    untrace_all_http()
    print("✅ Monkey patching disabled\n")
    
    print("🎉 Streaming Tracing Demonstration Completed!")
    print("\n💡 Key Features of Streaming Tracing:")
    print("   • Automatic detection of streaming vs non-streaming requests")
    print("   • Content collection during streaming for complete trace data")
    print("   • Support for all streaming methods (iter_content, iter_lines, etc.)")
    print("   • Works with both sync and async HTTP libraries")
    print("   • Proper error handling and trace completion")
    print("\n📚 Supported Streaming Methods:")
    print("   • aiohttp: iter_chunked(), iter_any(), iter_line(), read(), text(), json()")
    print("   • requests: iter_content(), iter_lines(), content, text, json()")
    print("   • httpx: iter_bytes(), iter_text(), iter_lines(), read(), aread()")


if __name__ == "__main__":
    asyncio.run(main())
