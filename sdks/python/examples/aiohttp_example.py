#!/usr/bin/env python3
"""
Example demonstrating aiohttp tracing with R4U.
"""

import asyncio
import aiohttp
from r4u.tracing.http import trace_aiohttp_client, PrintTracer


async def main():
    """Demonstrate aiohttp tracing."""
    
    # Create an aiohttp session
    async with aiohttp.ClientSession() as session:
        # Enable tracing on the session
        trace_aiohttp_client(session, PrintTracer())
        
        print("Making HTTP requests with aiohttp tracing enabled...")
        
        # Make some test requests
        try:
            # GET request
            async with session.get('https://httpbin.org/get') as response:
                print(f"GET response status: {response.status}")
                data = await response.json()
                print(f"Response data keys: {list(data.keys())}")
        
        except Exception as e:
            print(f"GET request failed: {e}")
        
        try:
            # POST request with JSON data
            test_data = {"message": "Hello from aiohttp!", "timestamp": "2024-01-01T00:00:00Z"}
            async with session.post('https://httpbin.org/post', json=test_data) as response:
                print(f"POST response status: {response.status}")
                data = await response.json()
                print(f"Posted data: {data.get('json', {})}")
        
        except Exception as e:
            print(f"POST request failed: {e}")
        
        try:
            # Request that will fail (to test error handling)
            async with session.get('https://httpbin.org/status/404') as response:
                print(f"404 response status: {response.status}")
        
        except Exception as e:
            print(f"404 request failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
