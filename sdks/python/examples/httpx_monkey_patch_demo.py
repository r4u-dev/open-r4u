#!/usr/bin/env python3
"""
Demonstration of httpx monkey patching for automatic tracing.

This example shows how to use the monkey patching functionality to automatically
trace all httpx clients without manually patching each instance.
"""

import asyncio
import httpx
from r4u.tracing.http.httpx import trace_all, untrace_all


async def demo_async_client():
    """Demonstrate async client tracing."""
    print("🔍 Testing async httpx client with monkey patching...")
    
    async with httpx.AsyncClient() as client:
        try:
            # This request will be automatically traced
            response = await client.get("https://httpbin.org/get")
            print(f"✓ Async request completed: {response.status_code}")
        except Exception as e:
            print(f"✗ Async request failed: {e}")


def demo_sync_client():
    """Demonstrate sync client tracing."""
    print("🔍 Testing sync httpx client with monkey patching...")
    
    with httpx.Client() as client:
        try:
            # This request will be automatically traced
            response = client.get("https://httpbin.org/get")
            print(f"✓ Sync request completed: {response.status_code}")
        except Exception as e:
            print(f"✗ Sync request failed: {e}")



async def main():
    """Main demonstration function."""
    print("🚀 Starting httpx monkey patching demonstration\n")
    
    # Enable monkey patching for all httpx clients
    print("📝 Enabling monkey patching for httpx...")
    trace_all()
    print("✓ Monkey patching enabled - all new httpx clients will be automatically traced\n")
    
    # Test sync client
    demo_sync_client()
    print()
    
    # Test async client
    await demo_async_client()
    print()
    
    
    # Disable monkey patching
    print("📝 Disabling monkey patching...")
    untrace_all()
    print("✓ Monkey patching disabled - httpx clients will no longer be automatically traced\n")
    
    print("🎉 Demonstration completed!")
    print("\n💡 Key benefits of monkey patching:")
    print("   • No need to manually patch each httpx client")
    print("   • Works with both sync and async clients")
    print("   • Can be enabled/disabled globally")


if __name__ == "__main__":
    asyncio.run(main())
