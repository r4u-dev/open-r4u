#!/usr/bin/env python3
"""
Example demonstrating requests HTTP client tracing with R4U.

This example shows how to trace HTTP requests made with the requests library.
"""

import requests
from r4u.tracing.http import trace_requests_session


def example_trace_session():
    """Example of tracing a requests.Session."""
    print("=== Tracing requests.Session ===")
    
    # Create a session and trace it
    session = requests.Session()
    trace_requests_session(session)
    
    # Make some requests
    try:
        response = session.get('https://httpbin.org/get', timeout=10)
        print(f"Response status: {response.status_code}")
        
        response = session.post('https://httpbin.org/post', json={'key': 'value'}, timeout=10)
        print(f"Response status: {response.status_code}")
        
    except Exception as e:
        print(f"Request failed: {e}")




def example_custom_tracer():
    """Example of using a custom tracer."""
    print("\n=== Using custom tracer ===")
    
    class CustomTracer:
        def trace_request(self, request_info):
            print(f"🔍 {request_info.method} {request_info.url}")
            if request_info.status_code:
                print(f"   Status: {request_info.status_code}")
            if request_info.error:
                print(f"   Error: {request_info.error}")
            if request_info.started_at and request_info.completed_at:
                elapsed = (request_info.completed_at - request_info.started_at).total_seconds() * 1000
                print(f"   Duration: {elapsed:.2f}ms")
    
    # Create a session with custom tracer
    session = requests.Session()
    trace_requests_session(session, CustomTracer())
    
    try:
        response = session.get('https://httpbin.org/get', timeout=10)
        print(f"Response status: {response.status_code}")
        
    except Exception as e:
        print(f"Request failed: {e}")


def example_error_handling():
    """Example showing error handling in tracing."""
    print("\n=== Error handling example ===")
    
    session = requests.Session()
    trace_requests_session(session)
    
    # This will fail and be traced
    try:
        response = session.get('https://httpbin.org/status/500', timeout=10)
        print(f"Response status: {response.status_code}")
    except Exception as e:
        print(f"Request failed: {e}")
    
    # This will also fail (network error)
    try:
        response = session.get('https://nonexistent-domain-12345.com', timeout=10)
        print(f"Response status: {response.status_code}")
    except Exception as e:
        print(f"Request failed: {e}")


if __name__ == "__main__":
    print("R4U Requests Tracing Example")
    print("=" * 50)
    
    example_trace_session()
    example_custom_tracer()
    example_error_handling()
    
    print("\n" + "=" * 50)
    print("Example completed!")
