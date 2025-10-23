"""Example demonstrating path tracking in HTTP traces.

This example shows how r4u automatically captures the call path (the chain of
functions that led to an LLM API call) and includes it in the trace data.

The call path helps you understand:
- Which part of your code made the API call
- The execution flow that led to the call
- Better debugging and analysis of your LLM usage

IMPORTANT: You must call trace_all() BEFORE importing OpenAI!
"""

import os
import time

# STEP 1: Import R4U and enable tracing FIRST (before OpenAI)
from r4u.tracing.http.httpx import trace_all, untrace_all

tracer = trace_all()

# STEP 2: Import OpenAI AFTER enabling tracing
from openai import OpenAI


def query_llm(question: str) -> str:
    """Direct LLM query function.

    The call path for this will be: <module>::main->query_llm
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    response = client.chat.completions.create(
        model="gpt-3.5-turbo", messages=[{"role": "user", "content": question}],
    )

    return response.choices[0].message.content


def analyze_text(text: str) -> str:
    """Analyze text using LLM.

    The call path for this will be: <module>::main->process_document->analyze_text
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a text analysis expert."},
            {"role": "user", "content": f"Analyze this text: {text}"},
        ],
    )

    return response.choices[0].message.content


def summarize_text(text: str) -> str:
    """Summarize text using LLM.

    The call path for this will be: <module>::main->process_document->summarize_text
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a summarization expert."},
            {"role": "user", "content": f"Summarize this text: {text}"},
        ],
    )

    return response.choices[0].message.content


def process_document(text: str) -> dict:
    """Process document with multiple LLM operations.

    This function calls other functions that make LLM API calls,
    demonstrating how the call path captures the full execution chain.
    """
    print("\n📄 Processing document...")

    # This will have path: <module>::main->process_document->analyze_text
    analysis = analyze_text(text)
    print("✓ Analysis complete")

    # This will have path: <module>::main->process_document->summarize_text
    summary = summarize_text(text)
    print("✓ Summary complete")

    return {"analysis": analysis, "summary": summary}


def main():
    """Main function demonstrating path tracking."""
    print("=" * 60)
    print("Path Tracking Example")
    print("=" * 60)
    print("\nThis example demonstrates how r4u captures the call path")
    print("for each LLM API call, helping you understand which part")
    print("of your code made the request.\n")

    # Example 1: Simple direct call
    print("1️⃣  Direct query (path: <module>::main->query_llm)")
    answer = query_llm("What is the capital of France?")
    print(f"   Answer: {answer[:50]}...")

    # Example 2: Nested function calls
    print("\n2️⃣  Document processing (nested calls)")
    document = "Artificial intelligence is transforming the world."
    results = process_document(document)
    print(f"   Analysis: {results['analysis'][:50]}...")
    print(f"   Summary: {results['summary'][:50]}...")

    # Example 3: Multiple direct calls from same location
    print("\n3️⃣  Multiple direct calls (same path)")
    for i in range(2):
        answer = query_llm(f"Count to {i + 1}")
        print(f"   Call {i + 1}: {answer[:30]}...")

    print("\n" + "=" * 60)
    print("✅ All API calls completed!")
    print("=" * 60)
    print("\nWaiting for traces to be sent to backend...")
    print("(Background worker sends traces every 1 second)")

    # Wait for traces to be sent (background worker sends every 1s)
    time.sleep(2)

    print("\n📊 Check your traces at: http://localhost:8000/api/v1/http-traces")
    print(
        "   Each trace will include the 'path' field showing where it was called from.\n",
    )

    # Cleanup
    untrace_all()

    print("Example completed! 🎉\n")


if __name__ == "__main__":
    # Check if API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("   Please set it with: export OPENAI_API_KEY='your-key-here'")
        exit(1)

    main()
