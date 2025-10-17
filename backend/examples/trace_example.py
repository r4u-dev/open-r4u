"""
Example of using the restructured Traces API.

This demonstrates creating traces with different input item types.
"""

import asyncio
from datetime import datetime, timezone

import httpx


async def create_simple_trace():
    """Create a simple trace with just messages."""
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        payload = {
            "model": "gpt-4",
            "input": [
                {"type": "message", "role": "user", "content": "Hello, how are you?"},
                {"type": "message", "role": "assistant", "content": "I'm doing well, thank you!"},
            ],
            "result": "I'm doing well, thank you!",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "prompt_tokens": 10,
            "completion_tokens": 8,
            "total_tokens": 18,
            "finish_reason": "stop",
            "project": "Example Project",
        }
        
        response = await client.post("/traces", json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")


async def create_trace_with_tool_calls():
    """Create a trace with tool calls and results."""
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        payload = {
            "model": "gpt-4",
            "instructions": "You are a helpful weather assistant.",
            "temperature": 0.7,
            "tool_choice": "auto",
            "input": [
                {"type": "message", "role": "user", "content": "What's the weather in NYC?"},
                {
                    "type": "tool_call",
                    "id": "call_weather_123",
                    "tool_name": "get_weather",
                    "arguments": {"location": "New York City", "unit": "fahrenheit"},
                },
                {
                    "type": "tool_result",
                    "call_id": "call_weather_123",
                    "tool_name": "get_weather",
                    "result": {"temperature": 72, "condition": "sunny", "humidity": 45},
                },
                {
                    "type": "message",
                    "role": "assistant",
                    "content": "The weather in NYC is sunny and 72°F with 45% humidity.",
                },
            ],
            "result": "The weather in NYC is sunny and 72°F with 45% humidity.",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "prompt_tokens": 25,
            "completion_tokens": 18,
            "total_tokens": 43,
            "finish_reason": "stop",
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get current weather for a location",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {"type": "string"},
                                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                            },
                            "required": ["location"],
                        },
                    },
                }
            ],
            "project": "Weather Assistant",
        }
        
        response = await client.post("/traces", json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")


async def create_trace_with_media():
    """Create a trace with image input."""
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        payload = {
            "model": "gpt-4-vision",
            "input": [
                {"type": "message", "role": "user", "content": "What's in this image?"},
                {
                    "type": "image",
                    "url": "https://example.com/cat.jpg",
                    "mime_type": "image/jpeg",
                    "metadata": {"size": "1920x1080"},
                },
                {
                    "type": "message",
                    "role": "assistant",
                    "content": "I see a cat sitting on a windowsill.",
                },
            ],
            "result": "I see a cat sitting on a windowsill.",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "prompt_tokens": 1050,  # Images use more tokens
            "completion_tokens": 12,
            "total_tokens": 1062,
            "finish_reason": "stop",
            "project": "Vision Analysis",
        }
        
        response = await client.post("/traces", json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")


async def create_trace_with_mcp_tools():
    """Create a trace with MCP tool interactions."""
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        payload = {
            "model": "gpt-4",
            "input": [
                {"type": "message", "role": "user", "content": "Search for recent AI papers"},
                {
                    "type": "mcp_tool_call",
                    "id": "mcp_search_001",
                    "server": "arxiv-server",
                    "tool_name": "search_papers",
                    "arguments": {"query": "artificial intelligence", "max_results": 5},
                },
                {
                    "type": "mcp_tool_result",
                    "call_id": "mcp_search_001",
                    "server": "arxiv-server",
                    "tool_name": "search_papers",
                    "result": {
                        "papers": [
                            {"title": "Paper 1", "authors": ["Author A"], "date": "2025-10-01"},
                            {"title": "Paper 2", "authors": ["Author B"], "date": "2025-09-15"},
                        ]
                    },
                },
                {
                    "type": "message",
                    "role": "assistant",
                    "content": "Here are 2 recent AI papers: Paper 1 by Author A, and Paper 2 by Author B.",
                },
            ],
            "result": "Here are 2 recent AI papers: Paper 1 by Author A, and Paper 2 by Author B.",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "prompt_tokens": 30,
            "completion_tokens": 25,
            "total_tokens": 55,
            "finish_reason": "stop",
            "project": "Research Assistant",
        }
        
        response = await client.post("/traces", json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")


async def create_trace_with_reasoning():
    """Create a trace with reasoning tokens (for o1/o3 models)."""
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        payload = {
            "model": "o1-preview",
            "instructions": "Think step by step to solve this math problem.",
            "temperature": 1.0,
            "input": [
                {
                    "type": "message",
                    "role": "user",
                    "content": "Solve this complex math problem: ...",
                },
                {
                    "type": "message",
                    "role": "assistant",
                    "content": "Here's the solution: ...",
                },
            ],
            "reasoning": "First, I identified the equation type. Then I applied the quadratic formula...",
            "result": "Here's the solution: ...",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "prompt_tokens": 50,
            "completion_tokens": 100,
            "reasoning_tokens": 2500,  # O1 models use reasoning tokens
            "total_tokens": 2650,
            "cached_tokens": 25,
            "finish_reason": "stop",
            "reasoning_effort": "high",
            "system_fingerprint": "fp_o1_preview_2025",
            "project": "Math Solver",
        }
        
        response = await client.post("/traces", json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")


async def main():
    """Run all examples."""
    print("=" * 80)
    print("1. Simple Trace")
    print("=" * 80)
    await create_simple_trace()
    
    print("\n" + "=" * 80)
    print("2. Trace with Tool Calls")
    print("=" * 80)
    await create_trace_with_tool_calls()
    
    print("\n" + "=" * 80)
    print("3. Trace with Media (Image)")
    print("=" * 80)
    await create_trace_with_media()
    
    print("\n" + "=" * 80)
    print("4. Trace with MCP Tools")
    print("=" * 80)
    await create_trace_with_mcp_tools()
    
    print("\n" + "=" * 80)
    print("5. Trace with Reasoning (O1/O3 models)")
    print("=" * 80)
    await create_trace_with_reasoning()


if __name__ == "__main__":
    asyncio.run(main())
