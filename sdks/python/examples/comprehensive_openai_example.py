"""Comprehensive OpenAI client examples with R4U HTTP tracing.

This example demonstrates:
1. Simple synchronous calls
2. Asynchronous calls
3. Conversation with history
4. Tool/function calling
5. File uploads (vision)

All traces are automatically captured at the HTTP transport level.
"""

import asyncio
import base64
import os
from pathlib import Path

# Import traced OpenAI clients from R4U
from r4u.tracing.openai import AsyncOpenAI, OpenAI


# =============================================================================
# 1. SIMPLE SYNCHRONOUS CALL
# =============================================================================

def example_simple_sync():
    """Example 1: Simple synchronous call."""
    print("=" * 70)
    print("EXAMPLE 1: Simple Synchronous Call")
    print("=" * 70)
    
    client = OpenAI()
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": "What is the capital of France?"}
        ],
        temperature=0.7,
    )
    
    print(f"Response: {response.choices[0].message.content}")
    print(f"Tokens: {response.usage.total_tokens}")
    print("✓ Trace automatically sent to R4U backend\n")


# =============================================================================
# 2. SIMPLE ASYNC CALL
# =============================================================================

async def example_simple_async():
    """Example 2: Simple asynchronous call."""
    print("=" * 70)
    print("EXAMPLE 2: Simple Asynchronous Call")
    print("=" * 70)
    
    client = AsyncOpenAI()
    
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": "What is 2+2?"}
        ],
        temperature=0.7,
    )
    
    print(f"Response: {response.choices[0].message.content}")
    print(f"Tokens: {response.usage.total_tokens}")
    print("✓ Trace automatically sent to R4U backend\n")


# =============================================================================
# 3. CONVERSATION WITH HISTORY
# =============================================================================

def example_conversation_sync():
    """Example 3: Multi-turn conversation with history."""
    print("=" * 70)
    print("EXAMPLE 3: Conversation with History (Sync)")
    print("=" * 70)
    
    client = OpenAI()
    
    # Build conversation history
    messages = [
        {"role": "system", "content": "You are a helpful math tutor."},
        {"role": "user", "content": "What is 5 + 3?"},
    ]
    
    # First turn
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
    )
    
    assistant_response = response.choices[0].message.content
    print(f"Turn 1 - User: What is 5 + 3?")
    print(f"Turn 1 - Assistant: {assistant_response}\n")
    
    # Add to history
    messages.append({"role": "assistant", "content": assistant_response})
    messages.append({"role": "user", "content": "Now multiply that by 2"})
    
    # Second turn
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
    )
    
    print(f"Turn 2 - User: Now multiply that by 2")
    print(f"Turn 2 - Assistant: {response.choices[0].message.content}")
    print(f"Total tokens: {response.usage.total_tokens}")
    print("✓ Both turns traced separately\n")


async def example_conversation_async():
    """Example 4: Multi-turn conversation with history (async)."""
    print("=" * 70)
    print("EXAMPLE 4: Conversation with History (Async)")
    print("=" * 70)
    
    client = AsyncOpenAI()
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Tell me a joke about programming"},
    ]
    
    # First turn
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.9,
    )
    
    assistant_response = response.choices[0].message.content
    print(f"Turn 1 - User: Tell me a joke about programming")
    print(f"Turn 1 - Assistant: {assistant_response}\n")
    
    # Add to history
    messages.append({"role": "assistant", "content": assistant_response})
    messages.append({"role": "user", "content": "Explain why that's funny"})
    
    # Second turn
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
    )
    
    print(f"Turn 2 - User: Explain why that's funny")
    print(f"Turn 2 - Assistant: {response.choices[0].message.content}")
    print("✓ Both turns traced\n")


# =============================================================================
# 5. TOOL/FUNCTION CALLING
# =============================================================================

def get_current_weather(location: str, unit: str = "celsius") -> str:
    """Mock function to get weather."""
    return f"The weather in {location} is 22 degrees {unit} and sunny."


def example_tools_sync():
    """Example 5: Using tools/function calling (sync)."""
    print("=" * 70)
    print("EXAMPLE 5: Tool/Function Calling (Sync)")
    print("=" * 70)
    
    client = OpenAI()
    
    # Define tools
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_current_weather",
                "description": "Get the current weather in a given location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA",
                        },
                        "unit": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                            "description": "The temperature unit",
                        },
                    },
                    "required": ["location"],
                },
            },
        }
    ]
    
    messages = [
        {"role": "user", "content": "What's the weather like in Paris?"}
    ]
    
    # First call - model requests tool
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )
    
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls
    
    print(f"User: What's the weather like in Paris?")
    
    if tool_calls:
        print(f"Assistant: [Calling tool: {tool_calls[0].function.name}]")
        
        # Add assistant's response to messages
        messages.append(response_message)
        
        # Call the function
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = eval(tool_call.function.arguments)
            function_response = get_current_weather(**function_args)
            
            print(f"Tool result: {function_response}")
            
            # Add function response to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": function_response,
            })
        
        # Second call - get final response
        final_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )
        
        print(f"Assistant: {final_response.choices[0].message.content}")
        print(f"Total tokens (final): {final_response.usage.total_tokens}")
    
    print("✓ Tool calls traced\n")


async def example_tools_async():
    """Example 6: Using tools/function calling (async)."""
    print("=" * 70)
    print("EXAMPLE 6: Tool/Function Calling (Async)")
    print("=" * 70)
    
    client = AsyncOpenAI()
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "calculate",
                "description": "Perform mathematical calculations",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "The mathematical expression to evaluate",
                        },
                    },
                    "required": ["expression"],
                },
            },
        }
    ]
    
    messages = [
        {"role": "user", "content": "What is (15 * 8) + 42?"}
    ]
    
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )
    
    response_message = response.choices[0].message
    
    print(f"User: What is (15 * 8) + 42?")
    
    if response_message.tool_calls:
        print(f"Assistant: [Calling tool: {response_message.tool_calls[0].function.name}]")
        
        messages.append(response_message)
        
        for tool_call in response_message.tool_calls:
            function_args = eval(tool_call.function.arguments)
            result = eval(function_args["expression"])
            
            print(f"Tool result: {result}")
            
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": tool_call.function.name,
                "content": str(result),
            })
        
        final_response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )
        
        print(f"Assistant: {final_response.choices[0].message.content}")
    
    print("✓ Async tool calls traced\n")


# =============================================================================
# 7. VISION - IMAGE UPLOAD
# =============================================================================

def example_vision_url():
    """Example 7: Vision with image URL."""
    print("=" * 70)
    print("EXAMPLE 7: Vision with Image URL")
    print("=" * 70)
    
    client = OpenAI()
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
                        },
                    },
                ],
            }
        ],
        max_tokens=300,
    )
    
    print(f"Response: {response.choices[0].message.content}")
    print(f"Tokens: {response.usage.total_tokens}")
    print("✓ Vision request traced\n")


def example_vision_base64():
    """Example 8: Vision with base64-encoded image."""
    print("=" * 70)
    print("EXAMPLE 8: Vision with Base64 Image")
    print("=" * 70)
    
    client = OpenAI()
    
    # Create a simple test image (1x1 red pixel PNG)
    # In real usage, you'd read an actual image file
    test_image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What color is this pixel?"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{test_image_base64}"
                        },
                    },
                ],
            }
        ],
        max_tokens=100,
    )
    
    print(f"Response: {response.choices[0].message.content}")
    print("✓ Base64 image traced\n")


async def example_vision_async():
    """Example 9: Vision with image (async)."""
    print("=" * 70)
    print("EXAMPLE 9: Vision (Async)")
    print("=" * 70)
    
    client = AsyncOpenAI()
    
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image briefly"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Cat03.jpg/1200px-Cat03.jpg"
                        },
                    },
                ],
            }
        ],
        max_tokens=200,
    )
    
    print(f"Response: {response.choices[0].message.content}")
    print("✓ Async vision traced\n")


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def run_sync_examples():
    """Run all synchronous examples."""
    print("\n" + "=" * 70)
    print("SYNCHRONOUS EXAMPLES")
    print("=" * 70 + "\n")
    
    example_simple_sync()
    example_conversation_sync()
    example_tools_sync()
    example_vision_url()
    example_vision_base64()


async def run_async_examples():
    """Run all asynchronous examples."""
    print("\n" + "=" * 70)
    print("ASYNCHRONOUS EXAMPLES")
    print("=" * 70 + "\n")
    
    await example_simple_async()
    await example_conversation_async()
    await example_tools_async()
    await example_vision_async()


def main():
    """Main function to run all examples."""
    print("\n" + "=" * 70)
    print("OpenAI Client Examples with R4U HTTP Tracing")
    print("=" * 70 + "\n")
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("   Set it with: export OPENAI_API_KEY='your-key-here'")
        return
    
    print("✓ Using R4U traced OpenAI clients (automatic tracing enabled)\n")
    
    # Run synchronous examples
    run_sync_examples()
    
    # Run asynchronous examples
    asyncio.run(run_async_examples())
    
    print("\n" + "=" * 70)
    print("ALL EXAMPLES COMPLETED")
    print("=" * 70)
    print("\nAll traces have been sent to R4U backend!")
    print("Check your R4U dashboard to see the captured traces.")
    print("\nWhat was traced:")
    print("  ✓ Simple calls (sync & async)")
    print("  ✓ Multi-turn conversations")
    print("  ✓ Tool/function calls")
    print("  ✓ Vision requests (URL & base64)")
    print("\nAll captured at HTTP transport level! 🎉\n")


if __name__ == "__main__":
    main()
