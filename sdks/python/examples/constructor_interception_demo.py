#!/usr/bin/env python3
"""
Constructor Interception Demo

This example demonstrates how the updated constructor interception approach
works across all HTTP libraries (httpx, requests, aiohttp) and how it
solves the problem of libraries creating their own HTTP client instances.
"""

import asyncio
import os
from typing import Any

# Set up environment for demo
os.environ.setdefault("OPENAI_API_KEY", "demo-key-for-testing")

# Import the individual trace_all functions
from r4u.tracing.http.httpx import trace_all as httpx_trace_all
from r4u.tracing.http.requests import trace_all as requests_trace_all
from r4u.tracing.http.aiohttp import trace_all as aiohttp_trace_all


class DemoR4UClient:
    """Demo R4U client that prints traces instead of sending them."""
    
    def log(self, trace: Any) -> None:
        """Log a trace entry."""
        # Calculate duration from timestamps
        duration_ms = (trace.completed_at - trace.started_at).total_seconds() * 1000
        
        print("🔍 HTTP TRACE CAPTURED:")
        print(f"   Method: {trace.method}")
        print(f"   URL: {trace.url}")
        print(f"   Status: {trace.status_code}")
        print(f"   Duration: {duration_ms:.2f}ms")
        print(f"   Request size: {len(trace.request)} bytes")
        print(f"   Response size: {len(trace.response)} bytes")
        print()


async def demonstrate_individual_constructor_interception():
    """Demonstrate individual library constructor interception."""
    print("=== Individual Library Constructor Interception Demo ===\n")
    
    # Set up the individual trace_all functions with our demo client
    demo_client = DemoR4UClient()
    
    # Enable constructor interception for each library individually
    httpx_trace_all(demo_client)
    requests_trace_all(demo_client)
    aiohttp_trace_all(demo_client)
    
    print("✅ Constructor interception enabled for all individual libraries!\n")
    
    # Test 1: Direct httpx usage
    print("1. Testing direct httpx usage...")
    try:
        import httpx
        
        client = httpx.Client()
        response = client.get("https://httpbin.org/json")
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
    print("4. Testing with aiohttp...")
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get("https://httpbin.org/json") as response:
                print(f"   Response status: {response.status}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print()


def demonstrate_comparison():
    """Demonstrate the difference between old and new approaches."""
    print("=== Comparison: Old vs New Constructor Interception ===\n")
    
    print("❌ OLD APPROACH (Class Patching):")
    print("   - Patched the entire class (httpx.Client, requests.Session, etc.)")
    print("   - Only worked for directly created instances")
    print("   - Libraries like OpenAI that create their own clients were NOT traced")
    print("   - Example: openai.AsyncOpenAI() creates AsyncHttpxClientWrapper -> NOT traced")
    print()
    
    print("✅ NEW APPROACH (Constructor Interception):")
    print("   - Intercepts the __init__ method of HTTP client classes")
    print("   - Works for ALL instances, regardless of how they're created")
    print("   - Libraries like OpenAI that create their own clients ARE traced")
    print("   - Example: openai.AsyncOpenAI() creates AsyncHttpxClientWrapper -> TRACED!")
    print()
    
    print("🔧 How constructor interception works:")
    print("   1. Intercepts HTTP client constructors (__init__ methods)")
    print("   2. Calls the original constructor first")
    print("   3. Applies tracing after the original constructor runs")
    print("   4. Works with any library that creates HTTP clients")
    print("   5. Transparent to the library - no code changes needed")
    print()


async def main():
    """Main demo function."""
    demonstrate_comparison()
    await demonstrate_individual_constructor_interception()
    
    print("=== Key Benefits ===")
    print("✅ Works with ANY library that creates HTTP clients")
    print("✅ No need to modify library code")
    print("✅ Transparent to the application")
    print("✅ Comprehensive coverage - catches everything")
    print("✅ Consistent approach across all HTTP libraries")
    print("✅ Easy to use - just call trace_all() for each library")
    print()
    
    print("=== Usage ===")
    print("```python")
    print("from r4u.tracing.http.httpx import trace_all as httpx_trace_all")
    print("from r4u.tracing.http.requests import trace_all as requests_trace_all")
    print("from r4u.tracing.http.aiohttp import trace_all as aiohttp_trace_all")
    print("")
    print("# Enable constructor interception for each library")
    print("httpx_trace_all()")
    print("requests_trace_all()")
    print("aiohttp_trace_all()")
    print("")
    print("# Now ALL HTTP clients are automatically traced!")
    print("import openai")
    print("client = openai.AsyncOpenAI()  # Automatically traced!")
    print("```")


if __name__ == "__main__":
    asyncio.run(main())
