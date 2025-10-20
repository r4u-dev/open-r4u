"""Example demonstrating the new raw tracing approach."""

import asyncio
import os
from r4u.tracing import OpenAI, AsyncOpenAI, Anthropic, AsyncAnthropic
from r4u.client import get_r4u_client


def sync_openai_example():
    """Example using synchronous OpenAI client with raw tracing."""
    print("=== Synchronous OpenAI Example with Raw Tracing ===")
    
    # The OpenAI client now automatically uses raw tracing
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here")
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "Hello! Tell me a short joke."}
            ],
            max_tokens=100
        )
        print(f"Response: {response.choices[0].message.content}")
    except Exception as e:
        print(f"Error: {e}")


async def async_openai_example():
    """Example using asynchronous OpenAI client with raw tracing."""
    print("=== Asynchronous OpenAI Example with Raw Tracing ===")
    
    # The AsyncOpenAI client now automatically uses raw tracing
    client = AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here")
    )
    
    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "What's the capital of France?"}
            ],
            max_tokens=50
        )
        print(f"Response: {response.choices[0].message.content}")
    except Exception as e:
        print(f"Error: {e}")


def sync_anthropic_example():
    """Example using synchronous Anthropic client with raw tracing."""
    print("=== Synchronous Anthropic Example with Raw Tracing ===")
    
    # The Anthropic client now automatically uses raw tracing
    client = Anthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY", "your-api-key-here")
    )
    
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=100,
            messages=[
                {"role": "user", "content": "Hello! Tell me a short joke."}
            ]
        )
        print(f"Response: {response.content[0].text}")
    except Exception as e:
        print(f"Error: {e}")


async def async_anthropic_example():
    """Example using asynchronous Anthropic client with raw tracing."""
    print("=== Asynchronous Anthropic Example with Raw Tracing ===")
    
    # The AsyncAnthropic client now automatically uses raw tracing
    client = AsyncAnthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY", "your-api-key-here")
    )
    
    try:
        response = await client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=100,
            messages=[
                {"role": "user", "content": "What's the capital of France?"}
            ]
        )
        print(f"Response: {response.content[0].text}")
    except Exception as e:
        print(f"Error: {e}")


def raw_trace_analysis_example():
    """Example showing how to analyze raw traces."""
    print("=== Raw Trace Analysis Example ===")
    
    # Get the R4U client
    r4u_client = get_r4u_client()
    
    try:
        # List all raw traces
        raw_traces = r4u_client.list_raw_traces()
        print(f"Found {len(raw_traces)} raw traces")
        
        if raw_traces:
            # Get the first trace
            trace = raw_traces[0]
            print(f"\nTrace ID: {trace.id}")
            print(f"Provider: {trace.provider}")
            print(f"Endpoint: {trace.endpoint}")
            print(f"Model: {trace.model}")
            print(f"Operation Type: {trace.operation_type}")
            print(f"Duration: {trace.duration_ms:.2f}ms")
            print(f"Status Code: {trace.status_code}")
            
            # Access raw request/response data
            print(f"\nRaw Request Size: {trace.raw_request['size']} bytes")
            print(f"Raw Response Size: {trace.raw_response['size']} bytes")
            
            # The raw payloads are compressed and base64 encoded
            # You can decompress them for analysis:
            from r4u.tracing.http.tracer import decompress_payload
            import json
            
            # Decompress and parse request
            request_data = json.loads(decompress_payload(trace.raw_request['payload']))
            print(f"\nRequest Model: {request_data.get('model', 'unknown')}")
            
            # Decompress and parse response
            response_data = json.loads(decompress_payload(trace.raw_response['payload']))
            print(f"Response Object: {response_data.get('object', 'unknown')}")
            
    except Exception as e:
        print(f"Error analyzing traces: {e}")


async def main():
    """Run all examples."""
    print("Raw Tracing Examples with R4U")
    print("=" * 50)
    
    # Set up environment
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not set. OpenAI examples will fail.")
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Warning: ANTHROPIC_API_KEY not set. Anthropic examples will fail.")
    print()
    
    # Run examples
    sync_openai_example()
    print()
    
    await async_openai_example()
    print()
    
    sync_anthropic_example()
    print()
    
    await async_anthropic_example()
    print()
    
    raw_trace_analysis_example()
    
    print("\nAll examples completed!")
    print("Check your R4U dashboard to see the raw traces.")
    print("\nKey Benefits of Raw Tracing:")
    print("- Complete request/response data preserved")
    print("- No data loss from parsing")
    print("- Automatic provider detection")
    print("- Future-proof against API changes")
    print("- Single implementation for all providers")


if __name__ == "__main__":
    asyncio.run(main())
