#!/usr/bin/env python3
"""OpenAI API Tracing Example with R4U SDK

This example demonstrates how to trace OpenAI API calls using R4U's HTTP-level tracing.
Since the OpenAI Python client uses httpx under the hood, we can automatically trace
all API calls by enabling HTTP tracing.

Prerequisites:
1. Install dependencies:
   uv add openai

2. Set your OpenAI API key:
   export OPENAI_API_KEY="your-api-key-here"

3. Make sure the R4U backend is running:
   The traces will be sent to http://localhost:8000/http-traces

Run this example:
   uv run python examples/openai_tracing_example.py
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

# STEP 1: Import R4U tracing FIRST
from r4u.tracing.http.auto import trace_all, untrace_all

# STEP 2: Enable tracing BEFORE importing OpenAI
# This is crucial because OpenAI creates its httpx client when imported
trace_all()

# STEP 3: NOW import OpenAI (its httpx client will be automatically patched)
try:
    from openai import OpenAI
except ImportError:
    print("Error: OpenAI library not installed.")
    print("Install it with: uv add openai")
    sys.exit(1)


def check_prerequisites():
    """Check if all prerequisites are met."""
    issues = []

    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        issues.append("⚠️  OPENAI_API_KEY environment variable not set")

    # Check for R4U API URL
    api_url = os.getenv("R4U_API_URL", "http://localhost:8000")
    print(f"✓ R4U API URL: {api_url}")

    if issues:
        print("\nPrerequisites not met:")
        for issue in issues:
            print(f"  {issue}")
        print("\nPlease set OPENAI_API_KEY before running this example.")
        return False

    return True


def example_basic_chat_completion():
    """Example: Basic chat completion with tracing."""
    print("\n" + "=" * 70)
    print("Example 1: Basic Chat Completion")
    print("=" * 70)

    # Create OpenAI client
    client = OpenAI()

    # Make a simple chat completion request
    print("\n📤 Making OpenAI API request...")
    print("Question: What is the capital of France? Answer in one sentence.")

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {
                    "role": "user",
                    "content": "What is the capital of France? Answer in one sentence.",
                },
            ],
            max_tokens=50,
            temperature=0.7,
        )

        answer = response.choices[0].message.content
        print(f"\n📥 Response: {answer}")
        print(f"✓ Tokens used: {response.usage.total_tokens}")
        print(f"✓ Model: {response.model}")
        print("\n✅ Request completed successfully!")
        print("🔍 Check your R4U dashboard - this request should be traced!")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def example_streaming_chat_completion():
    """Example: Streaming chat completion with tracing."""
    print("\n" + "=" * 70)
    print("Example 2: Streaming Chat Completion")
    print("=" * 70)

    # Create OpenAI client
    client = OpenAI()

    print("\n📤 Making streaming OpenAI API request...")
    print("Question: Write a haiku about programming.")

    try:
        stream = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a creative poet."},
                {"role": "user", "content": "Write a haiku about programming."},
            ],
            stream=True,
            max_tokens=100,
        )

        print("\n📥 Streaming response:")
        print("-" * 50)

        full_response = ""
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                full_response += content
                print(content, end="", flush=True)

        print("\n" + "-" * 50)
        print("\n✅ Streaming completed successfully!")
        print("🔍 Check your R4U dashboard - this streaming request should be traced!")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def example_multiple_requests():
    """Example: Multiple requests to show batch tracing."""
    print("\n" + "=" * 70)
    print("Example 3: Multiple Requests")
    print("=" * 70)

    client = OpenAI()

    questions = [
        "What is 2 + 2?",
        "What color is the sky?",
        "Name a programming language.",
    ]

    print(f"\n📤 Making {len(questions)} API requests...")

    successful = 0
    for i, question in enumerate(questions, 1):
        try:
            print(f"\n{i}. {question}")
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": question}],
                max_tokens=30,
            )
            answer = response.choices[0].message.content.strip()
            print(f"   → {answer}")
            successful += 1
        except Exception as e:
            print(f"   ❌ Error: {e}")

    print(f"\n✅ Completed {successful}/{len(questions)} requests successfully!")
    print("🔍 Check your R4U dashboard - all requests should be traced!")

    return successful > 0


def example_with_function_calling():
    """Example: Function calling with tracing."""
    print("\n" + "=" * 70)
    print("Example 4: Function Calling")
    print("=" * 70)

    client = OpenAI()

    # Define a function for the model to call
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
                            "description": "The city name, e.g. San Francisco",
                        },
                        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                    },
                    "required": ["location"],
                },
            },
        },
    ]

    print("\n📤 Making OpenAI API request with function calling...")
    print("Question: What's the weather like in Paris?")

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "What's the weather like in Paris?"}],
            tools=tools,
            tool_choice="auto",
        )

        message = response.choices[0].message

        if message.tool_calls:
            print("\n📥 Model wants to call function:")
            for tool_call in message.tool_calls:
                print(f"   Function: {tool_call.function.name}")
                print(f"   Arguments: {tool_call.function.arguments}")
        else:
            print(f"\n📥 Response: {message.content}")

        print("\n✅ Function calling request completed!")
        print("🔍 Check your R4U dashboard - this request should be traced!")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def main():
    """Main function to run all examples."""
    print("=" * 70)
    print("OpenAI API Tracing with R4U SDK")
    print("=" * 70)
    print(
        "\nThis example demonstrates automatic HTTP-level tracing of OpenAI API calls.",
    )
    print("All HTTP requests made by the OpenAI client will be captured and sent")
    print("to your R4U backend for observability and monitoring.")

    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)

    print("\n✓ HTTP tracing already enabled (via trace_all() called at module level)")
    print("✓ All OpenAI API calls will be automatically traced!")

    try:
        # Run examples
        examples = [
            ("Basic Chat Completion", example_basic_chat_completion),
            ("Streaming Chat Completion", example_streaming_chat_completion),
            ("Multiple Requests", example_multiple_requests),
            ("Function Calling", example_with_function_calling),
        ]

        results = {}
        for name, example_func in examples:
            try:
                success = example_func()
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

        # Give time for traces to be sent (background worker sends every 5s)
        print("\n⏳ Waiting for traces to be sent to backend...")
        import time

        time.sleep(6)

        print("\n" + "=" * 70)
        print("🎉 Demo complete!")
        print("=" * 70)
        print("\nAll OpenAI API requests have been traced and sent to:")
        print(f"  {os.getenv('R4U_API_URL', 'http://localhost:8000')}/http-traces")
        print("\nYou can now:")
        print("  1. Check your R4U dashboard to see the traces")
        print("  2. Analyze request/response patterns")
        print("  3. Monitor API usage and costs")
        print("  4. Debug issues with full request/response data")

    finally:
        # Cleanup: disable HTTP tracing
        print("\n🔧 Disabling HTTP tracing...")
        untrace_all()
        print("✓ HTTP tracing disabled")


if __name__ == "__main__":
    main()
