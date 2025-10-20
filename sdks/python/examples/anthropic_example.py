"""Example demonstrating Anthropic integration with R4U tracing."""

import asyncio
import os
from anthropic import Anthropic as OriginalAnthropic, AsyncAnthropic as OriginalAsyncAnthropic
from r4u.tracing import Anthropic, AsyncAnthropic, wrap_anthropic


def sync_anthropic_example():
    """Example using synchronous Anthropic client with tracing."""
    print("=== Synchronous Anthropic Example ===")
    
    # Method 1: Use the wrapped client directly
    client = Anthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY", "your-api-key-here")
    )
    
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=100,
            messages=[
                {"role": "user", "content": "Hello! Can you tell me a short joke?"}
            ]
        )
        print(f"Response: {response.content[0].text}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Method 2: Wrap an existing client
    original_client = OriginalAnthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY", "your-api-key-here")
    )
    wrapped_client = wrap_anthropic(original_client)
    
    try:
        response = wrapped_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=100,
            messages=[
                {"role": "user", "content": "What's the capital of France?"}
            ]
        )
        print(f"Response: {response.content[0].text}")
    except Exception as e:
        print(f"Error: {e}")


async def async_anthropic_example():
    """Example using asynchronous Anthropic client with tracing."""
    print("=== Asynchronous Anthropic Example ===")
    
    # Method 1: Use the wrapped async client directly
    client = AsyncAnthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY", "your-api-key-here")
    )
    
    try:
        response = await client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=100,
            messages=[
                {"role": "user", "content": "Hello! Can you tell me a short joke?"}
            ]
        )
        print(f"Response: {response.content[0].text}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Method 2: Wrap an existing async client
    original_client = OriginalAsyncAnthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY", "your-api-key-here")
    )
    wrapped_client = wrap_anthropic(original_client)
    
    try:
        response = await wrapped_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=100,
            messages=[
                {"role": "user", "content": "What's the capital of France?"}
            ]
        )
        print(f"Response: {response.content[0].text}")
    except Exception as e:
        print(f"Error: {e}")


def anthropic_with_tools_example():
    """Example using Anthropic client with tools/function calling."""
    print("=== Anthropic with Tools Example ===")
    
    client = Anthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY", "your-api-key-here")
    )
    
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=100,
            messages=[
                {"role": "user", "content": "What's the weather like in New York?"}
            ],
            tools=[
                {
                    "name": "get_weather",
                    "description": "Get the current weather for a location",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The city and state, e.g. San Francisco, CA"
                            }
                        },
                        "required": ["location"]
                    }
                }
            ]
        )
        print(f"Response: {response.content[0].text}")
    except Exception as e:
        print(f"Error: {e}")


def anthropic_with_structured_output_example():
    """Example using Anthropic client with structured output."""
    print("=== Anthropic with Structured Output Example ===")
    
    client = Anthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY", "your-api-key-here")
    )
    
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=100,
            messages=[
                {"role": "user", "content": "Extract the name and age from: John is 25 years old."}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "person_info",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "age": {"type": "integer"}
                        },
                        "required": ["name", "age"]
                    }
                }
            }
        )
        print(f"Response: {response.content[0].text}")
    except Exception as e:
        print(f"Error: {e}")


async def main():
    """Run all examples."""
    print("Anthropic Integration Examples with R4U Tracing")
    print("=" * 60)
    
    # Set up environment
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Warning: ANTHROPIC_API_KEY not set. Examples will fail with authentication errors.")
        print("Set your API key: export ANTHROPIC_API_KEY='your-key-here'")
        print()
    
    # Run synchronous examples
    sync_anthropic_example()
    
    # Run asynchronous examples
    await async_anthropic_example()
    
    # Run tools example
    anthropic_with_tools_example()
    
    # Run structured output example
    anthropic_with_structured_output_example()
    
    print("\nAll examples completed!")
    print("Check your R4U dashboard to see the traces.")


if __name__ == "__main__":
    asyncio.run(main())
