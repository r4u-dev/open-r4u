#!/usr/bin/env python3
"""
Simple OpenAI API Tracing Example

This example shows the simplest way to trace OpenAI API calls with R4U.

Setup:
1. Install: uv add openai
2. Set: export OPENAI_API_KEY="your-key"
3. Run: uv run python examples/simple_openai_example.py

IMPORTANT: trace_all() must be called BEFORE importing OpenAI!
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


def main():
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: Please set OPENAI_API_KEY environment variable")
        print("Example: export OPENAI_API_KEY='sk-...'")
        return

    print("🚀 Starting OpenAI API call with R4U tracing...\n")
    print("✓ Tracing enabled (via trace_all() called before OpenAI import)\n")

    try:
        # Create OpenAI client (automatically traced because we called trace_all() first)
        client = OpenAI()

        # Make a simple API call
        print("📤 Sending request to OpenAI...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say hello in 5 words"}],
            max_tokens=20,
        )

        # Print the response
        answer = response.choices[0].message.content
        print(f"📥 Response: {answer}\n")

        # Print trace info
        print("✅ Success! The request was traced and sent to:")
        print(f"   {os.getenv('R4U_API_URL', 'http://localhost:8000')}/http-traces\n")

        print("The trace includes:")
        print("  • Full request URL and method")
        print("  • Request/response headers")
        print("  • Request/response bodies")
        print("  • Timing information")
        print("  • Status codes\n")

        # Wait a moment for the trace to be sent (background worker sends every 5s)
        print("⏳ Waiting for trace to be sent to backend...")
        import time

        time.sleep(6)  # Wait longer than 5s to ensure batch is sent

        print("🎉 Check your R4U dashboard to see the trace!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Clean up: disable tracing
        untrace_all()
        print("\n✓ Tracing disabled")


if __name__ == "__main__":
    main()
