#!/usr/bin/env python3
"""OpenAI Tool Calls Tracing Example.

This example demonstrates how to trace OpenAI API calls that use function/tool calling
with R4U. It shows both single and parallel tool calls being automatically traced.

Setup:
1. Install: uv add openai
2. Set: export OPENAI_API_KEY="your-key"
3. Run: uv run python examples/openai_tool_calls_example.py

IMPORTANT: trace_all() must be called BEFORE importing OpenAI!
"""

import json
import os
import sys
import time

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


# Define example tools/functions
def get_current_weather(location: str, unit: str = "celsius") -> dict:
    """Get the current weather for a location."""
    # This is a mock function - in reality, you'd call a weather API
    weather_data = {
        "location": location,
        "temperature": 22,
        "unit": unit,
        "forecast": "sunny",
        "humidity": 65,
    }
    print(f"🌤️  Getting weather for {location}...")
    return weather_data


def calculate_sum(numbers: list[float]) -> dict:
    """Calculate the sum of a list of numbers."""
    total = sum(numbers)
    print(f"🧮 Calculating sum of {numbers}...")
    return {"sum": total, "count": len(numbers)}


def search_database(query: str, limit: int = 10) -> dict:
    """Search a database with a query."""
    # Mock search results
    print(f"🔍 Searching database for: {query}...")
    return {
        "query": query,
        "results": [
            {"id": 1, "title": "Result 1", "relevance": 0.95},
            {"id": 2, "title": "Result 2", "relevance": 0.87},
        ],
        "total": 2,
    }


# Tool definitions for OpenAI
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Get the current weather in a given location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA",
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "The temperature unit to use",
                    },
                },
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_sum",
            "description": "Calculate the sum of a list of numbers",
            "parameters": {
                "type": "object",
                "properties": {
                    "numbers": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "List of numbers to sum",
                    },
                },
                "required": ["numbers"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_database",
            "description": "Search a database with a query string",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        },
    },
]


# Map function names to actual functions
available_functions = {
    "get_current_weather": get_current_weather,
    "calculate_sum": calculate_sum,
    "search_database": search_database,
}


def run_conversation(client: OpenAI, user_message: str) -> str:
    """Run a conversation with tool calls."""
    print(f"\n{'=' * 60}")
    print(f"💬 User: {user_message}")
    print(f"{'=' * 60}\n")

    messages = [{"role": "user", "content": user_message}]

    # First API call - model decides which tools to call
    print("📤 Sending initial request to OpenAI...")
    response = client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    # Check if the model wants to call tools
    if tool_calls:
        print(f"🔧 Model requested {len(tool_calls)} tool call(s)\n")

        # Add the assistant's response to messages
        messages.append(response_message)

        # Execute each tool call
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            print(f"🛠️  Calling tool: {function_name}")
            print(f"   Arguments: {function_args}")

            # Call the actual function
            function_to_call = available_functions[function_name]
            function_response = function_to_call(**function_args)

            print(f"   Response: {function_response}\n")

            # Add function response to messages
            messages.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps(function_response),
                },
            )

        # Second API call - get final response from model
        print("📤 Sending tool results back to OpenAI...")
        second_response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=messages,
        )

        final_message = second_response.choices[0].message.content
    else:
        # No tool calls needed
        final_message = response_message.content

    print(f"🤖 Assistant: {final_message}\n")
    return final_message


def main():
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: Please set OPENAI_API_KEY environment variable")
        print("Example: export OPENAI_API_KEY='sk-...'")
        return

    print("🚀 Starting OpenAI Tool Calls Example with R4U Tracing...\n")
    print("✓ Tracing enabled (via trace_all() called before OpenAI import)\n")

    try:
        # Create OpenAI client (automatically traced)
        client = OpenAI()

        # Example 1: Single tool call
        print("\n📋 Example 1: Single Tool Call")
        print("-" * 60)
        run_conversation(
            client,
            "What's the weather like in San Francisco?",
        )

        # Example 2: Parallel tool calls
        print("\n📋 Example 2: Parallel Tool Calls")
        print("-" * 60)
        run_conversation(
            client,
            "What's the weather in London and Paris? Also calculate the sum of 10, 20, and 30.",
        )

        # Example 3: Database search
        print("\n📋 Example 3: Database Search Tool")
        print("-" * 60)
        run_conversation(
            client,
            "Search the database for 'machine learning tutorials'",
        )

        # Example 4: No tool call needed
        print("\n📋 Example 4: No Tool Call Needed")
        print("-" * 60)
        run_conversation(
            client,
            "What is the capital of France?",
        )

        # Success message
        print("\n" + "=" * 60)
        print("✅ Success! All requests were traced and sent to:")
        print(f"   {os.getenv('R4U_API_URL', 'http://localhost:8000')}/http-traces")
        print("=" * 60)

        print("\n📊 Traced Information Includes:")
        print("  • All API calls (initial + follow-up with tool results)")
        print("  • Complete tool definitions sent to the model")
        print("  • Tool call requests from the model")
        print("  • Tool execution results sent back")
        print("  • Final responses from the model")
        print("  • Full request/response bodies, headers, and timing")

        # Wait for trace to be sent (background worker sends every 5s)
        print("\n⏳ Waiting for traces to be sent to backend...")
        time.sleep(6)

        print("🎉 Check your R4U dashboard to see all the traced tool calls!")
        print("   You should see multiple HTTP traces for each conversation.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Clean up: disable tracing
        untrace_all()
        print("\n✓ Tracing disabled")


if __name__ == "__main__":
    main()

