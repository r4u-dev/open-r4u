#!/usr/bin/env python3
"""Templated Prompts with Automatic Implementation Matching

This example demonstrates how R4U automatically:
1. Detects similar prompts with variable parts
2. Creates implementations with templates like "Hello {name}!"
3. Extracts placeholder values for each trace

When you run this example multiple times with different values,
R4U will group similar prompts and create templates automatically.

Setup:
1. Install: uv add openai
2. Set: export OPENAI_API_KEY="your-key"
3. Run: uv run python examples/templated_prompts_example.py

IMPORTANT: trace_all() must be called BEFORE importing OpenAI!
"""

import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()

# STEP 1: Import R4U tracing FIRST
from r4u.tracing.http.auto import trace_all, untrace_all

# STEP 2: Enable tracing BEFORE importing OpenAI
trace_all()

# STEP 3: NOW import OpenAI
try:
    from openai import OpenAI
except ImportError:
    print("Error: OpenAI library not installed.")
    print("Install it with: uv add openai")
    sys.exit(1)


def make_personalized_request(client, user_name: str, user_role: str):
    """Make a request with personalized system prompt."""
    print(f"\n📤 Making request for user: {user_name} ({user_role})")

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": f"You are a helpful assistant for {user_role}. The user's name is {user_name}. Always be professional and courteous.",
            },
            {
                "role": "user",
                "content": "What can you help me with?",
            },
        ],
        max_tokens=100,
    )

    answer = response.choices[0].message.content
    print(f"📥 Response: {answer[:100]}...")
    return response


def make_greeting_request(client, user_name: str, greeting_style: str):
    """Make a request with templated greeting prompt."""
    print(f"\n📤 Making greeting request for: {user_name} (style: {greeting_style})")

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": f"You are a friendly greeter. Greet user {user_name} in a {greeting_style} manner and ask how their day is going.",
            },
            {
                "role": "user",
                "content": "Hello!",
            },
        ],
        max_tokens=80,
    )

    answer = response.choices[0].message.content
    print(f"📥 Response: {answer[:100]}...")
    return response


def make_task_request(client, task_type: str, priority: str, user_id: str):
    """Make a request with task-specific prompt."""
    print(
        f"\n📤 Making task request: {task_type} (priority: {priority}, user: {user_id})",
    )

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": f"You are a task management assistant. Handle {task_type} tasks for user ID {user_id} with {priority} priority. Provide clear and actionable guidance.",
            },
            {
                "role": "user",
                "content": "What should I focus on?",
            },
        ],
        max_tokens=100,
    )

    answer = response.choices[0].message.content
    print(f"📥 Response: {answer[:100]}...")
    return response


def main():
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: Please set OPENAI_API_KEY environment variable")
        print("Example: export OPENAI_API_KEY='sk-...'")
        return

    print("=" * 80)
    print("🎯 Templated Prompts with Automatic Implementation Matching")
    print("=" * 80)
    print("\nThis example demonstrates R4U's automatic template detection:")
    print("  • Makes multiple requests with similar prompts")
    print("  • R4U detects patterns and creates templates")
    print("  • Placeholder values are automatically extracted")
    print("  • After 3+ similar requests, an implementation is auto-created")
    print()

    try:
        # Create OpenAI client (automatically traced)
        client = OpenAI()

        # Example 1: Personalized assistant prompts
        print("\n" + "=" * 80)
        print("Example 1: Personalized Assistant Prompts")
        print("=" * 80)
        print("These requests have the same structure but different values.")
        print(
            "Expected template: 'You are a helpful assistant for {role}. The user's name is {name}...'",
        )

        make_personalized_request(client, "Alice", "software developer")
        make_personalized_request(client, "Bob", "data analyst")
        make_personalized_request(client, "Charlie", "product manager")

        # Example 2: Greeting prompts
        print("\n" + "=" * 80)
        print("Example 2: Greeting Prompts")
        print("=" * 80)
        print("These greetings vary by name and style.")
        print(
            "Expected template: 'You are a friendly greeter. Greet user {name} in a {style} manner...'",
        )

        make_greeting_request(client, "Diana", "warm and enthusiastic")
        make_greeting_request(client, "Eve", "formal and professional")
        make_greeting_request(client, "Frank", "casual and friendly")

        # Example 3: Task management prompts
        print("\n" + "=" * 80)
        print("Example 3: Task Management Prompts")
        print("=" * 80)
        print("These tasks have multiple variables: type, priority, and user ID.")
        print(
            "Expected template: 'You are a task management assistant. Handle {task_type} tasks for user ID {user_id} with {priority} priority...'",
        )

        make_task_request(client, "coding", "high", "user_101")
        make_task_request(client, "review", "medium", "user_102")
        make_task_request(client, "documentation", "low", "user_103")

        # Wait for traces to be sent
        print("\n" + "=" * 80)
        print("⏳ Waiting for traces to be sent to R4U backend...")
        print("=" * 80)
        time.sleep(6)

        # Print summary
        print("\n" + "=" * 80)
        print("✅ Success! All requests have been traced.")
        print("=" * 80)
        print("\nWhat happens next in R4U:")
        print("\n1️⃣  First 2 traces: Stored without implementation")
        print("   • No grouping yet (need minimum 3 similar traces)")
        print()
        print("2️⃣  Third trace triggers automatic grouping:")
        print("   • R4U finds all similar traces")
        print("   • Infers template from common patterns")
        print("   • Creates Task and Implementation")
        print("   • Links all 3 traces to new implementation")
        print()
        print("3️⃣  For each trace, R4U extracts placeholder values:")
        print("   • Example 1: {name: 'Alice', role: 'software developer'}")
        print("   • Example 2: {name: 'Bob', role: 'data analyst'}")
        print("   • Example 3: {name: 'Charlie', role: 'product manager'}")
        print()
        print("4️⃣  Future traces with similar prompts:")
        print("   • Automatically match existing implementation")
        print("   • Extract new placeholder values")
        print("   • No new implementation needed")
        print()
        print("🔍 View your traces and implementations:")
        r4u_url = os.getenv("R4U_API_URL", "http://localhost:8000")
        print(f"   • Traces: {r4u_url}/api/v1/traces")
        print(f"   • Tasks: {r4u_url}/api/v1/tasks")
        print(f"   • Implementations: {r4u_url}/api/v1/implementations")
        print()
        print("💡 Tips:")
        print("   • Run this example multiple times to see matching in action")
        print("   • Try modifying the prompts slightly - they'll still match!")
        print("   • Check trace.prompt_variables to see extracted values")
        print()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Clean up
        untrace_all()
        print("✓ Tracing disabled\n")


if __name__ == "__main__":
    main()
