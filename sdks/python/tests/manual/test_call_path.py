#!/usr/bin/env python3
"""Test script to verify call path extraction."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from openai import OpenAI
from r4u.integrations.openai import wrap_openai
from r4u.client import R4UClient


def inner_function():
    """Inner function that makes the actual OpenAI call."""
    client = OpenAI()
    traced_client = wrap_openai(client, api_url="http://localhost:8000")
    
    response = traced_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Say 'Path test!'"}],
        max_tokens=5
    )
    
    return response.choices[0].message.content


def outer_function():
    """Outer function that calls inner_function."""
    return inner_function()


def main():
    """Main function to test call path."""
    print("Testing call path extraction...")
    print("Expected path: test_call_path.py::main->outer_function->inner_function")
    print()
    
    # Get initial trace count
    r4u_client = R4UClient(api_url="http://localhost:8000")
    initial_traces = r4u_client.list_traces()
    initial_count = len(initial_traces)
    
    # Make the call
    result = outer_function()
    print(f"OpenAI Response: {result}")
    
    # Check the trace
    final_traces = r4u_client.list_traces()
    final_count = len(final_traces)
    
    if final_count > initial_count:
        new_traces = sorted(final_traces, key=lambda t: t.id)[initial_count:]
        latest_trace = new_traces[-1]
        
        print(f"\n✓ Trace created successfully!")
        print(f"  Trace ID: {latest_trace.id}")
        print(f"  Model: {latest_trace.model}")
        print(f"  Call Path: {latest_trace.path}")
        
        if latest_trace.path:
            print(f"\n✓ Call path captured: {latest_trace.path}")
            if "test_call_path.py" in latest_trace.path:
                print("✓ File name is correct")
            if "main" in latest_trace.path and "outer_function" in latest_trace.path and "inner_function" in latest_trace.path:
                print("✓ Call chain is correct")
            else:
                print("! Warning: Expected main->outer_function->inner_function in path")
        else:
            print("✗ No call path captured")
    else:
        print("✗ No trace was created")


if __name__ == "__main__":
    main()