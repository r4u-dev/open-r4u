#!/usr/bin/env python3
"""Example demonstrating URL filtering for HTTP tracing.

This example shows how to configure URL filtering to only trace requests
to specific AI provider APIs while ignoring other HTTP requests.
"""

import httpx
import requests

from r4u.client import ConsoleTracer
from r4u.tracing.http.auto import configure_url_filter, trace_all_http


def main():
    """Demonstrate URL filtering functionality."""
    print("URL Filtering Example")
    print("====================")

    # Method 1: Configure filter separately, then enable tracing
    print("\n1. Method 1: Configure filter separately...")
    configure_url_filter(
        allow_urls=[
            "https://api.openai.com/*",      # OpenAI API
            "https://api.anthropic.com/*",   # Anthropic API
            "https://api.groq.com/*",        # Groq API
        ],
        deny_urls=[
            "https://api.openai.com/v1/models",  # Deny models endpoint specifically
        ],
    )
    print("   ✓ Filter configured to allow OpenAI, Anthropic, and Groq APIs")
    print("   ✓ Deny patterns configured to block OpenAI models endpoint")

    # Enable tracing with console output
    print("\n2. Enabling HTTP tracing...")
    tracer = ConsoleTracer()
    trace_all_http(tracer)
    print("   ✓ HTTP tracing enabled for all libraries")

    # Method 2: Configure filter and enable tracing in one call
    print("\n3. Method 2: Configure filter and enable tracing in one call...")
    trace_all_http(
        tracer=tracer,
        allow_urls=["https://api.custom.com/*"],  # This extends the defaults
        deny_urls=["https://api.openai.com/v1/files/*"],  # Additional deny pattern
    )
    print("   ✓ Filter extended with custom patterns")
    print("   ✓ Additional deny pattern added")

    # Test with httpx
    print("\n4. Testing with httpx...")
    try:
        with httpx.Client() as client:
            # This should be traced (OpenAI API - allowed)
            print("   Making request to OpenAI API (should be traced)...")
            response = client.get("https://api.openai.com/v1/chat/completions")
            print(f"   Response status: {response.status_code}")

            # This should be traced (Anthropic API - allowed)
            print("   Making request to Anthropic API (should be traced)...")
            response = client.get("https://api.anthropic.com/v1/messages")
            print(f"   Response status: {response.status_code}")

            # This should NOT be traced (models endpoint - denied)
            print("   Making request to OpenAI models endpoint (should NOT be traced)...")
            response = client.get("https://api.openai.com/v1/models")
            print(f"   Response status: {response.status_code}")

            # This should NOT be traced (other API - not in allow list)
            print("   Making request to httpbin (should NOT be traced)...")
            response = client.get("https://httpbin.org/get")
            print(f"   Response status: {response.status_code}")

    except Exception as e:
        print(f"   Error with httpx: {e}")

    # Test with requests
    print("\n5. Testing with requests...")
    try:
        with requests.Session() as session:
            # This should be traced (Groq API - allowed)
            print("   Making request to Groq API (should be traced)...")
            response = session.get("https://api.groq.com/openai/v1/chat/completions")
            print(f"   Response status: {response.status_code}")

            # This should NOT be traced (other API - not in allow list)
            print("   Making request to GitHub API (should NOT be traced)...")
            response = session.get("https://api.github.com/user")
            print(f"   Response status: {response.status_code}")

    except Exception as e:
        print(f"   Error with requests: {e}")

    print("\n6. Summary:")
    print("   - Requests to OpenAI, Anthropic, and Groq APIs were traced")
    print("   - Requests to OpenAI models endpoint were NOT traced (denied)")
    print("   - Requests to other APIs were NOT traced (not in allow list)")
    print("   - Custom patterns were added to extend the default allow list")
    print("   - Check the console output above for the actual trace data")

    print("\n✓ URL filtering example completed!")


if __name__ == "__main__":
    main()
