#!/usr/bin/env python3
"""Complete end-to-end test with mock OpenAI to verify path tracking."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from unittest.mock import Mock, patch
from r4u.integrations.openai import wrap_openai
from r4u.client import R4UClient


def simulate_llm_call():
    """Simulates making an LLM call."""
    # Create mock OpenAI client
    mock_client = Mock()
    mock_response = Mock()
    mock_choice = Mock()
    mock_message = Mock()
    mock_message.content = "Mock response"
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response
    
    # Wrap it with R4U
    traced_client = wrap_openai(mock_client, api_url="http://localhost:8000")
    
    # Make the call
    response = traced_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Test"}]
    )
    
    return response


def helper_function():
    """Helper that calls simulate_llm_call."""
    return simulate_llm_call()


def main():
    """Test call path tracking with mocked OpenAI."""
    print("=" * 60)
    print("End-to-End Call Path Test (Mocked)")
    print("=" * 60)
    print()
    
    # Patch the R4U client's create_trace to capture what would be sent
    captured_trace_data = {}
    
    def mock_create_trace(**kwargs):
        captured_trace_data.update(kwargs)
        # Return a mock trace
        mock_trace = Mock()
        mock_trace.id = 999
        return mock_trace
    
    with patch.object(R4UClient, 'create_trace', side_effect=mock_create_trace):
        print("Making mocked LLM call through: main->helper_function->simulate_llm_call")
        result = helper_function()
        print(f"✓ LLM call completed: {result.choices[0].message.content}")
        print()
    
    # Check the captured trace data
    if captured_trace_data:
        print("Trace Data Captured:")
        print(f"  Model: {captured_trace_data.get('model')}")
        print(f"  Messages: {len(captured_trace_data.get('messages', []))}")
        print(f"  Path: {captured_trace_data.get('path')}")
        print()
        
        # Validate the path
        path = captured_trace_data.get('path', '')
        
        print("Path Validation:")
        checks = [
            ("test_e2e_path.py" in path, "Contains file name"),
            ("main" in path, "Contains main function"),
            ("helper_function" in path, "Contains helper_function"),
            ("simulate_llm_call" in path, "Contains simulate_llm_call"),
            ("->" in path, "Contains call chain separator"),
        ]
        
        all_passed = True
        for passed, description in checks:
            status = "✓" if passed else "✗"
            print(f"  {status} {description}")
            if not passed:
                all_passed = False
        
        print()
        if all_passed:
            print("🎉 SUCCESS: Call path tracking is working correctly!")
            print()
            print("The path shows: test_e2e_path.py::main->helper_function->simulate_llm_call")
            print("This means the SDK captured the full call chain!")
            return True
        else:
            print("⚠ FAILURE: Some validation checks failed")
            print(f"Actual path: {path}")
            return False
    else:
        print("✗ FAILURE: No trace data was captured")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)