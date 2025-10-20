"""Async example of using R4U with OpenAI, including streaming support.

This example demonstrates the enhanced OpenAITracer with comprehensive support for:
- Regular async completions
- Streaming completions with tools
- Streaming with structured output (JSON)
- Concurrent streaming requests

To run this example, you need to set your OpenAI API key:
    export OPENAI_API_KEY="your-api-key-here"

The enhanced OpenAITracer now captures:
- All OpenAI API parameters (temperature, max_tokens, tools, etc.)
- Complete response metadata (id, object, created, system_fingerprint)
- Token usage statistics
- Streaming content collection
- Error handling with proper API error format
- Response format and schema information
"""

import asyncio
import os

from r4u.client import ConsoleTracer
from r4u.tracing import trace_all
# Enable universal interception
trace_all(ConsoleTracer())

from openai import AsyncOpenAI


async def test_regular_completions():
    """Test regular async completions with tracing."""
    print("=== Testing Regular Async Completions ===")

    # Initialize async OpenAI client
    client = AsyncOpenAI()

    # Make multiple concurrent chat completions - each will create a trace
    tasks = []
    questions = [
        "What is the capital of France?",
        "Explain quantum computing in simple terms.",
        "What are the benefits of renewable energy?",
    ]

    for question in questions:
        task = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": question},
            ],
            max_tokens=150,
            temperature=0.7,
        )
        tasks.append(task)

    try:
        # Execute all requests concurrently
        responses = await asyncio.gather(*tasks)

        for i, response in enumerate(responses):
            print(f"\nQuestion {i+1}: {questions[i]}")
            print(f"Answer: {response.choices[0].message.content}")
            print(f"Usage: {response.usage}")

    except Exception as e:
        print(f"Error: {e}")


async def test_streaming_completions():
    """Test async streaming completions with tracing."""
    print("\n=== Testing Async Streaming Completions ===")

    client = AsyncOpenAI()

    # Test streaming with tools
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
                            "description": "The city and state, e.g. San Francisco, CA",
                        },
                        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                    },
                    "required": ["location"],
                },
            },
        }
    ]

    try:
        print("Making streaming request with tools...")
        stream = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant. Use tools when appropriate.",
                },
                {
                    "role": "user",
                    "content": "What's the weather like in Paris, France? Please use the weather tool.",
                },
            ],
            tools=tools,
            tool_choice="auto",
            stream=True,
            max_tokens=200,
            temperature=0.5,
        )

        print("Streaming response:")
        collected_content = ""
        async for chunk in stream:
            if chunk.choices:
                choice = chunk.choices[0]
                if choice.delta.content:
                    content = choice.delta.content
                    print(content, end="", flush=True)
                    collected_content += content
                elif choice.delta.tool_calls:
                    print(f"\n[Tool calls detected: {len(choice.delta.tool_calls)}]")

        print(f"\n\nComplete response: {collected_content}")

    except Exception as e:
        print(f"Error in streaming: {e}")


async def test_streaming_with_structured_output():
    """Test streaming with structured output format."""
    print("\n=== Testing Streaming with Structured Output ===")

    client = AsyncOpenAI()

    try:
        print("Making streaming request with JSON response format...")
        stream = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that provides structured responses.",
                },
                {
                    "role": "user",
                    "content": "Create a recipe for chocolate chip cookies. Format your response as JSON with fields: name, ingredients (array), instructions (array), and cooking_time_minutes.",
                },
            ],
            response_format={"type": "json_object"},
            stream=True,
            max_tokens=300,
            temperature=0.3,
        )

        print("Streaming JSON response:")
        collected_content = ""
        async for chunk in stream:
            if chunk.choices:
                choice = chunk.choices[0]
                if choice.delta.content:
                    content = choice.delta.content
                    print(content, end="", flush=True)
                    collected_content += content

        print(f"\n\nComplete JSON response: {collected_content}")

        # Try to parse the JSON to verify it's valid
        import json

        try:
            parsed_json = json.loads(collected_content)
            print(f"✓ Valid JSON with keys: {list(parsed_json.keys())}")
        except json.JSONDecodeError as e:
            print(f"✗ Invalid JSON: {e}")

    except Exception as e:
        print(f"Error in structured streaming: {e}")


async def test_concurrent_streaming():
    """Test multiple concurrent streaming requests."""
    print("\n=== Testing Concurrent Streaming Requests ===")

    client = AsyncOpenAI()

    # Create multiple streaming tasks
    streaming_tasks = []
    topics = [
        "Write a short story about a robot learning to paint",
        "Explain the theory of relativity in simple terms",
        "Describe the process of photosynthesis",
    ]

    for i, topic in enumerate(topics):
        task = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"You are assistant #{i+1}. Be concise and helpful.",
                },
                {"role": "user", "content": topic},
            ],
            stream=True,
            max_tokens=100,
            temperature=0.7,
        )
        streaming_tasks.append((i + 1, topic, task))

    try:
        # Process all streams concurrently
        async def process_stream(assistant_id, topic, stream):
            print(f"\n--- Assistant {assistant_id} responding to: {topic} ---")
            collected = ""
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    print(f"[A{assistant_id}] {content}", end="", flush=True)
                    collected += content
            return f"Assistant {assistant_id} completed: {collected[:50]}..."

        # Execute all streams concurrently
        results = await asyncio.gather(
            *[
                process_stream(assistant_id, topic, stream)
                for assistant_id, topic, stream in streaming_tasks
            ]
        )

        print("\n\nAll streams completed:")
        for result in results:
            print(f"  {result}")

    except Exception as e:
        print(f"Error in concurrent streaming: {e}")


async def main():
    """Run comprehensive async OpenAI examples with tracing."""
    print("🚀 Starting Async OpenAI Tracing Examples")
    print("=" * 50)

    # Check if API key is available
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OpenAI API key not found!")
        print("Please set your OpenAI API key:")
        print("  export OPENAI_API_KEY='your-api-key-here'")
        print("\nThis example demonstrates the enhanced OpenAITracer functionality.")
        print("The tracer now supports:")
        print("  ✓ Comprehensive request/response parameter capture")
        print("  ✓ Streaming response handling with content collection")
        print("  ✓ Tool calling and structured output support")
        print("  ✓ Error handling with proper API error format")
        print("  ✓ Token usage and metadata extraction")
        return

    try:
        # Test regular completions
        await test_regular_completions()

        # Test streaming completions
        await test_streaming_completions()

        # Test streaming with structured output
        await test_streaming_with_structured_output()

        # Test concurrent streaming
        await test_concurrent_streaming()

        print("\n" + "=" * 50)
        print("✅ All async OpenAI tracing examples completed successfully!")
        print("Check your R4U dashboard to see the traces created for each request.")

    except Exception as e:
        print(f"\n❌ Error in main: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
