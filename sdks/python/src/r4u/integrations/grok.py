"""Grok integration for R4U observability."""

import json
from typing import Any, Dict, Optional

from r4u.integrations.http.tracer import AbstractTracer, RequestInfo
from ..client import R4UClient, r4u_client
from ..utils import extract_call_path

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

# Try to import Grok client - this will be a placeholder since we don't have the actual client
try:
    # This is a placeholder - in reality, you would import the actual Grok client
    # from grok import GrokClient as OriginalGrokClient
    # GROK_AVAILABLE = True
    GROK_AVAILABLE = False
    OriginalGrokClient = object  # type: ignore
except ImportError:
    GROK_AVAILABLE = False
    OriginalGrokClient = object  # type: ignore


def get_chat_completions_trace(request_info: RequestInfo) -> Optional[Dict[str, Any]]:
    """Extract trace information from a Grok chat completions request."""
    try:
        request_json = json.loads(request_info.request_payload) if request_info.request_payload else {}
        response_json = json.loads(request_info.response_payload) if request_info.response_payload else {}
        
        # Extract messages from request
        messages = request_json.get("messages", [])
        if not messages:
            return None
            
        # Extract model from request
        model = request_json.get("model", "grok-beta")
        
        # Extract response content
        result = None
        if response_json and "choices" in response_json:
            choices = response_json["choices"]
            if choices and len(choices) > 0:
                choice = choices[0]
                if "message" in choice:
                    result = choice["message"].get("content", "")
                elif "delta" in choice and "content" in choice["delta"]:
                    result = choice["delta"]["content"]
        
        # Extract token usage
        usage = response_json.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        total_tokens = usage.get("total_tokens")
        
        # Extract tools if present
        tools = request_json.get("tools")
        tool_definitions = None
        if tools:
            tool_definitions = []
            for tool in tools:
                if isinstance(tool, dict) and "function" in tool:
                    func = tool["function"]
                    tool_definitions.append({
                        "name": func.get("name"),
                        "description": func.get("description"),
                        "parameters": func.get("parameters"),
                        "type": "function"
                    })
        
        # Build trace payload
        trace_payload = {
            "model": model,
            "messages": messages,
            "result": result,
            "started_at": request_info.started_at,
            "completed_at": request_info.completed_at,
            "path": extract_call_path(),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "tools": tool_definitions,
            "trace_metadata": {
                "url": request_info.url,
                "method": request_info.method,
                "status_code": request_info.status_code,
                "request_size": request_info.request_size,
                "response_size": request_info.response_size,
            }
        }
        
        # Add error if present
        if request_info.error:
            trace_payload["error"] = str(request_info.error)
            
        return trace_payload
        
    except Exception as e:
        print(f"Failed to parse Grok request: {e}")
        return None


class GrokTracer(AbstractTracer):
    """Tracer for Grok client."""
    
    def __init__(self, r4u_client: R4UClient):
        self._r4u_client = r4u_client

    def trace_request(self, request_info: RequestInfo):
        """Trace a request."""
        # Grok API typically uses chat/completions endpoint
        if request_info.url.endswith("/chat/completions"):
            trace = get_chat_completions_trace(request_info)
        else:
            # For other endpoints, create a generic trace
            trace = self._get_generic_trace(request_info)

        if trace is not None:
            self._r4u_client.create_trace(**trace)

    def _get_generic_trace(self, request_info: RequestInfo) -> Optional[Dict[str, Any]]:
        """Create a generic trace for non-chat endpoints."""
        try:
            request_json = json.loads(request_info.request_payload) if request_info.request_payload else {}
            response_json = json.loads(request_info.response_payload) if request_info.response_payload else {}
            
            # Extract basic information
            model = request_json.get("model", "grok-beta")
            messages = request_json.get("messages", [])
            
            # Try to extract result from response
            result = None
            if response_json:
                if "choices" in response_json and response_json["choices"]:
                    choice = response_json["choices"][0]
                    if "message" in choice:
                        result = choice["message"].get("content", "")
                    elif "text" in choice:
                        result = choice["text"]
                elif "text" in response_json:
                    result = response_json["text"]
            
            return {
                "model": model,
                "messages": messages,
                "result": result,
                "started_at": request_info.started_at,
                "completed_at": request_info.completed_at,
                "path": extract_call_path(),
                "trace_metadata": {
                    "url": request_info.url,
                    "method": request_info.method,
                    "status_code": request_info.status_code,
                    "endpoint_type": "generic",
                }
            }
            
        except Exception as e:
            print(f"Failed to parse Grok generic request: {e}")
            return None


def trace_client(client: httpx.Client):
    httpx.trace_client(client, GrokTracer(r4u_client))


def trace_async_client(client: httpx.AsyncClient):
    httpx.trace_async_client(client, GrokTracer(r4u_client))