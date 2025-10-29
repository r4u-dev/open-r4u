#!/usr/bin/env python3
"""
Async OpenAI API Tracing Example

This example demonstrates how to trace asynchronous OpenAI API calls with R4U.
The AsyncOpenAI client uses httpx.AsyncClient internally, so we trace at the HTTP level.

Prerequisites:
1. Install: uv add openai
2. Set: export OPENAI_API_KEY="your-key"
3. Run: uv run python examples/async_openai_example.py
"""

import asyncio
import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()

# STEP 1: Import R4U tracing FIRST
from r4u.tracing import trace_all, untrace_all

# STEP 2: Enable tracing BEFORE importing OpenAI
# This is crucial because OpenAI creates its httpx client when imported
trace_all()

# STEP 3: NOW import AsyncOpenAI (its httpx client will be automatically patched)
try:
    from openai import AsyncOpenAI
except ImportError:
    print("Error: OpenAI library not installed.")
    print("Install it with: uv add openai")
    sys.exit(1)


async def example_basic_async_completion():
    """Example: Basic async chat completion with tracing."""
    print("\n" + "=" * 70)
    print("Example 1: Basic Async Chat Completion")
    print("=" * 70)

    # Create async OpenAI client
    client = AsyncOpenAI()

    print("\n📤 Making async OpenAI API request...")
    print("Question: What is 5 + 3?")

    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "What is 5 + 3? Answer briefly."}],
            max_tokens=20,
        )

        answer = response.choices[0].message.content
        print(f"📥 Response: {answer}")
        print(f"✓ Tokens: {response.usage.total_tokens}")

        print("\n✅ Async request completed!")
        print("🔍 This request was automatically traced!")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def example_concurrent_requests():
    """Example: Multiple concurrent async requests with tracing."""
    print("\n" + "=" * 70)
    print("Example 2: Concurrent Async Requests")
    print("=" * 70)

    client = AsyncOpenAI()

    questions = [
        "What is the capital of Japan?",
        "What is 10 * 12?",
        "What color is grass?",
        "What programming language starts with P?",
        "What is the largest planet?",
    ]

    print(f"\n📤 Making {len(questions)} concurrent API requests...")

    async def ask_question(question: str, index: int):
        """Make a single API call."""
        try:
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": f"{question} Answer briefly."}],
                max_tokens=30,
            )
            answer = response.choices[0].message.content.strip()
            return index, question, answer, None
        except Exception as e:
            return index, question, None, str(e)

    # Execute all requests concurrently
    start_time = time.time()
    tasks = [ask_question(q, i) for i, q in enumerate(questions, 1)]
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start_time

    # Display results
    print("\n📥 Results:")
    successful = 0
    for index, question, answer, error in results:
        if error:
            print(f"{index}. ❌ {question}")
            print(f"   Error: {error}")
        else:
            print(f"{index}. ✓ {question}")
            print(f"   → {answer}")
            successful += 1

    print(f"\n✅ Completed {successful}/{len(questions)} requests in {elapsed:.2f}s")
    print("🔍 All requests were traced concurrently!")

    return successful > 0


async def example_async_streaming():
    """Example: Async streaming with tracing."""
    print("\n" + "=" * 70)
    print("Example 3: Async Streaming")
    print("=" * 70)

    client = AsyncOpenAI()

    print("\n📤 Making async streaming API request...")
    print("Question: Count from 1 to 5 in words.")

    try:
        stream = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "Count from 1 to 5 in words, one per line."}
            ],
            stream=True,
            max_tokens=50,
        )

        print("\n📥 Streaming response:")
        print("-" * 50)

        full_response = ""
        async for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                full_response += content
                print(content, end="", flush=True)

        print("\n" + "-" * 50)

        print("\n✅ Async streaming completed!")
        print("🔍 The entire streamed response was captured in the trace!")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def example_error_handling():
    """Example: Error handling with async requests."""
    print("\n" + "=" * 70)
    print("Example 4: Error Handling")
    print("=" * 70)

    client = AsyncOpenAI()

    print("\n📤 Making request that may fail...")

    try:
        # Request with very low max_tokens to potentially trigger issues
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "user",
                    "content": "Write a detailed essay about artificial intelligence.",
                }
            ],
            max_tokens=5,  # Too few tokens for the request
        )

        answer = response.choices[0].message.content
        finish_reason = response.choices[0].finish_reason

        print(f"📥 Response: {answer}")
        print(f"📊 Finish reason: {finish_reason}")

        if finish_reason == "length":
            print("⚠️  Response was cut off due to max_tokens limit (expected behavior)")

        print("\n✅ Request completed (with limitations)!")
        print("🔍 Even incomplete responses are traced for debugging!")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        print("🔍 Errors are also captured in traces!")
        return False


async def example_with_context_manager():
    """Example: Using async context manager."""
    print("\n" + "=" * 70)
    print("Example 5: Async Context Manager")
    print("=" * 70)

    print("\n📤 Using AsyncOpenAI with context manager...")

    try:
        async with AsyncOpenAI() as client:
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Say hello in a creative way."}],
                max_tokens=30,
            )

            answer = response.choices[0].message.content
            print(f"📥 Response: {answer}")

        print("\n✅ Context manager pattern works with tracing!")
        print("🔍 Requests in context managers are traced normally!")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def main():
    """Main async function to run all examples."""
    print("=" * 70)
    print("Async OpenAI API Tracing with R4U SDK")
    print("=" * 70)
    print("\nThis demonstrates automatic HTTP-level tracing of async OpenAI calls.")
    print("All async HTTP requests are captured and traced for observability.")

    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\n❌ Error: OPENAI_API_KEY environment variable not set")
        print("Please set it before running this example.")
        sys.exit(1)

    api_url = os.getenv("R4U_API_URL", "http://localhost:8000")
    print(f"\n✓ R4U API URL: {api_url}")

    print("\n✓ HTTP tracing already enabled (via trace_all() called at module level)")
    print("✓ All async OpenAI API calls will be automatically traced!")

    try:
        # Run all examples
        examples = [
            ("Basic Async Completion", example_basic_async_completion),
            ("Concurrent Requests", example_concurrent_requests),
            ("Async Streaming", example_async_streaming),
            ("Error Handling", example_error_handling),
            ("Context Manager", example_with_context_manager),
        ]

        results = {}
        for name, example_func in examples:
            try:
                success = await example_func()
                results[name] = success
            except Exception as e:
                print(f"\n❌ Unexpected error in {name}: {e}")
                results[name] = False

        # Summary
        print("\n" + "=" * 70)
        print("Summary")
        print("=" * 70)

        successful = sum(1 for v in results.values() if v)
        total = len(results)

        for name, success in results.items():
            status = "✅" if success else "❌"
            print(f"{status} {name}")

        print(f"\n{successful}/{total} examples completed successfully")

        # Wait for traces to be sent (background worker sends every 5s)
        print("\n⏳ Waiting for traces to be sent to backend...")
        await asyncio.sleep(6)

        print("\n" + "=" * 70)
        print("🎉 Async demo complete!")
        print("=" * 70)
        print("\nAll async OpenAI API requests have been traced!")
        print(f"\nTraces sent to: {api_url}/http-traces")
        print("\nBenefits of async tracing:")
        print("  • Concurrent requests are all traced")
        print("  • Streaming responses are fully captured")
        print("  • Errors and exceptions are logged")
        print("  • No performance impact on async operations")

    finally:
        # Cleanup
        print("\n🔧 Disabling async HTTP tracing...")
        untrace_all()
        print("✓ Tracing disabled")


if __name__ == "__main__":
    asyncio.run(main())
