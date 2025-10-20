#!/usr/bin/env python3
"""
Pure AsyncOpenAI client demo with automatic tracing.

This example demonstrates how to use the AsyncOpenAI client from our
tracing package using only the high-level OpenAI API, without any
direct httpx usage. All tracing happens automatically behind the scenes.
"""

import asyncio
import os

from r4u.tracing.openai import AsyncOpenAI


async def openai_streaming_with_pure_api():
    """Test OpenAI streaming using only the high-level AsyncOpenAI API."""
    print("\n" + "="*70)
    print("TESTING OPENAI STREAMING WITH PURE API (NO HTTPX)")
    print("="*70)
    
    # Check for OpenAI API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key:")
        print("export OPENAI_API_KEY='your-api-key-here'")
        return
    
    # Create AsyncOpenAI client (automatically traces requests)
    client = AsyncOpenAI(api_key=api_key)
    
    # Test 1: Simple streaming chat completion
    print("\n1. Testing simple streaming chat completion...")
    
    try:
        # Use only the high-level OpenAI API - no httpx knowledge needed!
        stream = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Keep responses concise."},
                {"role": "user", "content": "Explain quantum computing in one sentence."}
            ],
            stream=True,
            max_tokens=100,
            temperature=0.7
        )
        
        print("Streaming response:")
        collected_content = ""
        chunk_count = 0
        
        # Process streaming response using OpenAI's high-level API
        async for chunk in stream:
            chunk_count += 1
            if chunk.choices:
                choice = chunk.choices[0]
                if choice.delta.content:
                    content = choice.delta.content
                    print(content, end="", flush=True)
                    collected_content += content
        
        print(f"\n\nComplete response: {collected_content}")
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
    
    try:
        # Use only the high-level OpenAI API
        stream = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Use tools when appropriate."},
                {"role": "user", "content": "What's the weather like in Paris, France? Please use the weather tool."}
            ],
            tools=tools,
            tool_choice="auto",
            stream=True,
            max_tokens=200,
            temperature=0.5
        )
        
        print("Streaming response with tools:")
        collected_content = ""
        chunk_count = 0
        tool_calls_detected = False
        
        async for chunk in stream:
            chunk_count += 1
            if chunk.choices:
                choice = chunk.choices[0]
                if choice.delta.content:
                    content = choice.delta.content
                    print(content, end="", flush=True)
                    collected_content += content
                elif choice.delta.tool_calls:
                    if not tool_calls_detected:
                        print(f"\n[Tool calls detected: {len(choice.delta.tool_calls)}]")
                        tool_calls_detected = True
        
        print(f"\n\nComplete response: {collected_content}")
        print(f"Total chunks received: {chunk_count}")
        
    except Exception as e:
        print(f"Error in tools streaming test: {e}")
    
    # Test 3: Non-streaming request for comparison
    print("\n\n3. Testing non-streaming request...")
    
    try:
        # Use only the high-level OpenAI API
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "Tell me a short joke about programming."}
            ],
            max_tokens=50,
            temperature=0.7
        )
        
        print("Non-streaming response:")
        print(response.choices[0].message.content)
        
    except Exception as e:
        print(f"Error in non-streaming test: {e}")
    
    # Test 4: Other OpenAI API endpoints
    print("\n\n4. Testing other OpenAI API endpoints...")
    
    try:
        # List models
        models = await client.models.list()
        print(f"Available models: {len(models.data)} models")
        
        # Create embeddings
        embedding = await client.embeddings.create(
            model="text-embedding-3-small",
            input="Hello, world!"
        )
        print(f"Embedding created: {len(embedding.data[0].embedding)} dimensions")
        
    except Exception as e:
        print(f"Error in other API tests: {e}")


async def openai_client_features():
    """Test various OpenAI client features."""
    print("\n" + "="*70)
    print("TESTING OPENAI CLIENT FEATURES")
    print("="*70)
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY environment variable not set")
        return
    
    client = AsyncOpenAI(api_key=api_key)
    
    # Test different models
    print("\n1. Testing different models...")
    
    models_to_test = ["gpt-4o-mini", "gpt-3.5-turbo"]
    
    for model in models_to_test:
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Say 'Hello' in one word."}],
                max_tokens=10
            )
            print(f"✅ {model}: {response.choices[0].message.content}")
        except Exception as e:
            print(f"❌ {model}: {e}")
    
    # Test different parameters
    print("\n2. Testing different parameters...")
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Count from 1 to 5."}],
            max_tokens=20,
            temperature=0.1,  # Low temperature for consistent output
            top_p=0.9,
            frequency_penalty=0.0,
            presence_penalty=0.0
        )
        print(f"✅ Low temperature response: {response.choices[0].message.content}")
    except Exception as e:
        print(f"❌ Parameter test: {e}")


def demonstrate_pure_openai_usage():
    """Demonstrate pure OpenAI usage without httpx knowledge."""
    print("\n" + "="*70)
    print("PURE OPENAI USAGE EXPLANATION")
    print("="*70)
    
    print("""
The r4u tracing package provides automatic tracing for OpenAI clients
using only the high-level OpenAI API - no httpx knowledge required:

1. Pure OpenAI API Usage:
   ```python
   from r4u.tracing.openai import AsyncOpenAI
   
   # Create client (automatically traces requests)
   client = AsyncOpenAI(api_key="your-api-key")
   
   # Use only OpenAI's high-level API
   stream = await client.chat.completions.create(
       model="gpt-4",
       messages=[{"role": "user", "content": "Hello!"}],
       stream=True
   )
   
   # Process streaming response
   async for chunk in stream:
       if chunk.choices[0].delta.content:
           print(chunk.choices[0].delta.content, end="")
   ```

2. What happens behind the scenes:
   - AsyncOpenAI wraps the original OpenAI client
   - Automatically traces the underlying httpx client
   - Uses direct R4U client for comprehensive tracing
   - Detects streaming requests via stream=True parameter
   - Collects complete response content during streaming
   - Sends traces when requests complete

3. Key Benefits:
   - ✅ Pure OpenAI API - no httpx knowledge needed
   - ✅ Automatic tracing - no manual setup required
   - ✅ Complete response content captured
   - ✅ Accurate timing includes full streaming duration
   - ✅ Works with all OpenAI features: chat, tools, function calling
   - ✅ Compatible with existing OpenAI client code
   - ✅ All tracing happens transparently

4. No httpx required:
   - You never need to import httpx
   - You never need to know about httpx
   - You never need to use httpx directly
   - All HTTP handling is done by the OpenAI client
   - All tracing is done automatically behind the scenes
""")


async def main():
    """Run all pure OpenAI examples."""
    demonstrate_pure_openai_usage()
    
    # Test streaming with pure API
    await openai_streaming_with_pure_api()
    
    # Test client features
    await openai_client_features()
    
    print("\n" + "="*70)
    print("PURE OPENAI TRACING DEMO COMPLETE")
    print("="*70)
    print("""
Key Takeaways:
1. Use AsyncOpenAI from r4u.tracing.openai for automatic tracing
2. Use only the high-level OpenAI API - no httpx knowledge needed
3. All requests (streaming and non-streaming) are automatically traced
4. Complete response content is captured with accurate timing
5. Works with all OpenAI features: chat, tools, function calling
6. All tracing happens transparently behind the scenes
7. Zero configuration required - just import and use
""")


if __name__ == "__main__":
    asyncio.run(main())
