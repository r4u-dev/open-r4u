"""Demonstrate automatic tracing of tool calls with the real OpenAI API.

The script performs a two-step chat completion:

1. The assistant is encouraged to call a weather lookup tool.
2. A local Python implementation fulfils the tool request and feeds the result
   back to OpenAI to obtain the natural-language answer.

Every OpenAI call goes through `wrap_openai`, so both requests and responses
are captured automatically by the R4U backend.

Prerequisites:

* The `OPENAI_API_KEY` environment variable must be set.
* The R4U backend should be running locally at http://localhost:8000.
* The OpenAI Python SDK (>=1.0) must be installed.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from openai import OpenAI

from r4u.tracing.openai import wrap_openai


def lookup_weather(location: str) -> Dict[str, Any]:
    """Return a dummy weather payload for the requested location."""

    return {
        "location": location,
        "temperature_c": 22,
        "humidity": 0.48,
        "conditions": "clear",
    }


TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "lookup_weather",
            "description": "Retrieve the current weather for a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City and country to look up.",
                    }
                },
                "required": ["location"],
            },
        },
    }
]


def call_openai_with_tools() -> None:
    """Run the multi-turn conversation and print the final assistant reply."""

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is required to run this example.")

    base_client = OpenAI(api_key=api_key)
    traced_client = wrap_openai(base_client, api_url="http://localhost:8000")

    initial_messages: List[Dict[str, Any]] = [
        {"role": "system", "content": "You are a helpful weather assistant."},
        {
            "role": "user",
            "content": "What's the weather like in Paris right now?",
        },
    ]

    chat = traced_client.chat
    if chat is None:
        raise RuntimeError("OpenAI client does not expose chat completions.")

    first_response = chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0,
        messages=initial_messages,
        tools=TOOLS,
        tool_choice="auto",
    )

    first_choice = first_response.choices[0]
    assistant_message = first_choice.message

    tool_calls = getattr(assistant_message, "tool_calls", None) or []
    messages: List[Dict[str, Any]] = [*initial_messages]

    normalized_assistant: Dict[str, Any] = {
        "role": getattr(assistant_message, "role", "assistant"),
        "content": getattr(assistant_message, "content", None),
    }

    if tool_calls:
        normalized_calls = []
        for tool_call in tool_calls:
            call_id = getattr(tool_call, "id", None) or f"call_{len(normalized_calls)+1}"
            function = getattr(tool_call, "function", None)
            if function and getattr(function, "arguments", None):
                raw_arguments = function.arguments
                if isinstance(raw_arguments, str):
                    arguments: Dict[str, Any] = json.loads(raw_arguments)
                else:
                    arguments = raw_arguments
            else:
                arguments = {}
            normalized_calls.append(
                {
                    "id": call_id,
                    "type": getattr(tool_call, "type", "function"),
                    "function": {
                        "name": getattr(function, "name", "unknown_tool"),
                        "arguments": json.dumps(arguments),
                    },
                }
            )
        normalized_assistant["tool_calls"] = normalized_calls
    messages.append(normalized_assistant)

    if not tool_calls:
        print(getattr(assistant_message, "content", "Assistant did not call a tool."))
        print("Trace sent to R4U API. No tool call was issued in this run.")
        return

    for tool_call in normalized_assistant["tool_calls"]:
        raw_arguments = tool_call["function"].get("arguments", "{}")
        if isinstance(raw_arguments, str):
            arguments = json.loads(raw_arguments or "{}")
        else:
            arguments = raw_arguments or {}
        tool_name = tool_call["function"].get("name", "unknown_tool")
        tool_result: Dict[str, Any]
        if tool_name == "lookup_weather":
            tool_result = lookup_weather(arguments.get("location", "unknown"))
        else:
            tool_result = {"error": f"No handler for tool '{tool_name}'"}
        messages.append(
            {
                "role": "tool",
                "name": tool_name,
                "tool_call_id": tool_call["id"],
                "content": json.dumps(tool_result),
            }
        )

    follow_up_response = chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0,
        messages=messages,
        tools=TOOLS,
    )

    final_choice = follow_up_response.choices[0]
    final_message = final_choice.message
    print(getattr(final_message, "content", "<no content>"))
    print("Trace with tool usage sent to R4U API. Check your dashboard for details.")


def main() -> None:
    """Entry point for the script."""

    call_openai_with_tools()


if __name__ == "__main__":
    main()
