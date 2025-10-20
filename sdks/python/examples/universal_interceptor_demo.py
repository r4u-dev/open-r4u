#!/usr/bin/env python3
"""
Universal HTTP Client Interceptor Demo

This example demonstrates how the universal HTTP client interceptor works
to automatically trace HTTP requests from libraries like OpenAI, even when
they create their own HTTP client instances.

The universal interceptor intercepts HTTP client creation at the constructor
level, ensuring that ALL HTTP clients are traced, regardless of how they
are created.
"""

import asyncio
import os
from typing import Any, Dict

# Set up environment for demo
os.environ.setdefault("OPENAI_API_KEY", "demo-key-for-testing")

# Import the universal interceptor BEFORE importing any HTTP libraries
from r4u.tracing.http.auto import intercept_all_http_clients
from r4u.client import get_r4u_client


class DemoR4UClient:
    """Demo R4U client that prints traces instead of sending them."""
    
    def log(self, trace: Any) -> None:
        """Log a trace entry."""
        # Calculate duration from timestamps
        duration_ms = (trace.completed_at - trace.started_at).total_seconds() * 1000
        
        print(f"🔍 HTTP TRACE CAPTURED:")
        print(f"   Method: {trace.method}")
        print(f"   URL: {trace.url}")
        print(f"   Status: {trace.status_code}")
        print(f"   Duration: {duration_ms:.2f}ms")
        print(f"   Request size: {len(trace.request)} bytes")
        print(f"   Response size: {len(trace.response)} bytes")
        print()


async def demonstrate_universal_interception():
    """Demonstrate universal HTTP client interception."""
    print("=== Universal HTTP Client Interceptor Demo ===\n")
    
    # Set up the universal interceptor with our demo client
    demo_client = DemoR4UClient()
    intercept_all_http_clients(demo_client)
    
    print("✅ Universal interceptor enabled - ALL HTTP clients will be traced!\n")
    
    # Test 1: Direct httpx usage
    print("1. Testing direct httpx usage...")
    try:
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get("https://httpbin.org/json")
            print(f"   Response status: {response.status_code}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print()
    
    # Test 2: Direct requests usage
    print("2. Testing direct requests usage...")
    try:
        import requests
        
        session = requests.Session()
        response = session.get("https://httpbin.org/json")
        print(f"   Response status: {response.status_code}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print()
    
    # Test 3: OpenAI client (this is the key test!)
    print("3. Testing OpenAI client (the main use case)...")
    try:
        import openai
        
        # Create OpenAI client - this should be automatically traced!
        client = openai.AsyncOpenAI(api_key="demo-key")
        
        # Make a request (this will fail due to invalid API key, but we should see the trace)
        try:
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello!"}],
                max_tokens=10
            )
        except Exception as e:
            print(f"   Expected error (invalid API key): {type(e).__name__}")
            print("   ✅ But the HTTP request was still traced!")
        
    except Exception as e:
        print(f"   Error creating OpenAI client: {e}")
    
    print()
    
    # Test 4: Another library that might create HTTP clients
    print("4. Testing with another library...")
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get("https://httpbin.org/json") as response:
                print(f"   Response status: {response.status}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print()


def demonstrate_comparison():
    """Demonstrate the difference between regular tracing and universal interception."""
    print("=== Comparison: Regular vs Universal Interception ===\n")
    
    print("❌ WITHOUT Universal Interceptor:")
    print("   - Only directly created HTTP clients are traced")
    print("   - Libraries like OpenAI that create their own clients are NOT traced")
    print("   - Example: openai.AsyncOpenAI() creates AsyncHttpxClientWrapper -> NOT traced")
    print()
    
    print("✅ WITH Universal Interceptor:")
    print("   - ALL HTTP clients are traced, regardless of how they're created")
    print("   - Libraries like OpenAI that create their own clients ARE traced")
    print("   - Example: openai.AsyncOpenAI() creates AsyncHttpxClientWrapper -> TRACED!")
    print()
    
    print("🔧 How it works:")
    print("   1. Intercepts HTTP client constructors (__init__ methods)")
    print("   2. Applies tracing after the original constructor runs")
    print("   3. Works with any library that creates HTTP clients")
    print("   4. Transparent to the library - no code changes needed")
    print()


async def main():
    """Main demo function."""
    demonstrate_comparison()
    await demonstrate_universal_interception()
    
    print("=== Key Benefits ===")
    print("✅ Works with ANY library that creates HTTP clients")
    print("✅ No need to modify library code")
    print("✅ Transparent to the application")
    print("✅ Comprehensive coverage - catches everything")
    print("✅ Easy to use - just call intercept_all_http_clients()")
    print()
    
    print("=== Usage ===")
    print("```python")
    print("from r4u.tracing.http.auto import intercept_all_http_clients")
    print("")
    print("# Enable universal interception")
    print("intercept_all_http_clients()")
    print("")
    print("# Now ALL HTTP clients are automatically traced!")
    print("import openai")
    print("client = openai.AsyncOpenAI()  # Automatically traced!")
    print("```")


if __name__ == "__main__":
    asyncio.run(main())
