#!/usr/bin/env python3
"""Test script to verify call path tracking with real OpenAI calls."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from openai import OpenAI
from r4u.tracing.openai import wrap_openai


def helper_function():
    """Helper function that makes the actual OpenAI call."""
    client = OpenAI()
    traced_client = wrap_openai(client, api_url="http://localhost:8000")
    
    response = traced_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Say only 'Hello from R4U!'"}],
        max_tokens=10
    )
    
    return response.choices[0].message.content


def process_request():
    """Process function that calls helper."""
    return helper_function()


def main():
    """Main function to test call path tracking."""
    print("=" * 60)
    print("R4U Call Path Tracking Test")
    print("=" * 60)
    print()
    print("Expected path format:")
    print("  test_path_tracking.py::main->process_request->helper_function")
    print()
    
    # Get initial trace count
    from r4u.client import get_r4u_client
    r4u_client = get_r4u_client()
    initial_traces = r4u_client.list_traces()
    initial_count = len(initial_traces)
    print(f"Initial trace count: {initial_count}")
    print()
    
    # Make the call through nested functions
    print("Making OpenAI call through nested functions...")
    try:
        result = process_request()
        print(f"✓ OpenAI Response: {result}")
    except Exception as e:
        print(f"✗ Error making OpenAI call: {e}")
        return False
    
    print()
    
    # Check the trace
    print("Checking trace...")
    final_traces = r4u_client.list_traces()
    final_count = len(final_traces)
    print(f"Final trace count: {final_count}")
    
    if final_count > initial_count:
        print(f"✓ {final_count - initial_count} new trace(s) created")
        print()
        
        # Get the latest trace
        new_traces = sorted(final_traces, key=lambda t: t.id)[initial_count:]
        latest_trace = new_traces[-1]
        
        print("Trace Details:")
        print(f"  ID: {latest_trace.id}")
        print(f"  Model: {latest_trace.model}")
        print(f"  Messages: {len(latest_trace.messages)}")
        print(f"  Result: {latest_trace.result}")
        print(f"  Call Path: {latest_trace.path}")
        print()
        
        # Validate the call path
        if latest_trace.path:
            print("Call Path Analysis:")
            print(f"  ✓ Path captured: {latest_trace.path}")
            
            # Check for expected components
            checks = {
                "test_path_tracking.py": "File name",
                "main": "main function",
                "process_request": "process_request function",
                "helper_function": "helper_function function",
                "->": "Call chain separator"
            }
            
            all_passed = True
            for component, description in checks.items():
                if component in latest_trace.path:
                    print(f"  ✓ Contains {description}")
                else:
                    print(f"  ✗ Missing {description}")
                    all_passed = False
            
            print()
            if all_passed:
                print("🎉 SUCCESS: Call path tracking is working perfectly!")
            else:
                print("⚠ WARNING: Some components missing from call path")
            
            return all_passed
        else:
            print("✗ FAILURE: No call path captured in trace")
            return False
    else:
        print("✗ FAILURE: No new trace was created")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)