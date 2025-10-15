"""LangChain integration for R4U observability."""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Union

from ..client import R4UClient
from ..utils import extract_call_path

try:
    from langchain_core.callbacks.base import BaseCallbackHandler
    from langchain_core.messages import BaseMessage
    from langchain_core.outputs import LLMResult
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    BaseCallbackHandler = object  # type: ignore
    BaseMessage = object  # type: ignore
    LLMResult = object  # type: ignore


class R4UCallbackHandler(BaseCallbackHandler):  # type: ignore
    """LangChain callback handler that automatically creates traces in R4U."""

    def __init__(self, r4u_client: R4UClient, project: str):
        """Initialize the callback handler.

        Args:
            r4u_client: R4U client for creating traces
            project: Project name for traces
        """
        if not LANGCHAIN_AVAILABLE:
            raise ImportError(
                "LangChain is not installed. Please install it with: "
                "pip install langchain-core"
            )
        
        self._r4u_client = r4u_client
        self._project = project
        self._current_trace: Dict[str, Any] = {}
        self._call_path: Optional[str] = None
        
    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs: Any,
    ) -> None:
        """Called when LLM starts running."""
        self._current_trace = {
            "started_at": datetime.utcnow(),
            "model": self._extract_model_name(serialized, kwargs),
            "messages": [],
            "tools": None,
        }
        
        # Extract call path
        self._call_path, _ = extract_call_path()
        
        # Handle prompt-based calls (non-chat models)
        if prompts:
            for prompt in prompts:
                self._current_trace["messages"].append({
                    "role": "user",
                    "content": prompt,
                })
    
    def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[Any]],  # List of BaseMessage when langchain available
        **kwargs: Any,
    ) -> None:
        """Called when chat model starts running."""
        self._current_trace = {
            "started_at": datetime.utcnow(),
            "model": self._extract_model_name(serialized, kwargs),
            "messages": [],
            "tools": None,
        }
        
        # Extract call path
        self._call_path, _ = extract_call_path()
        
        # Extract messages from LangChain message objects
        # messages is a list of message lists (batch support)
        if messages and len(messages) > 0:
            # Get the first message list (most common case)
            message_list = messages[0]
            for msg in message_list:
                normalized_msg = self._normalize_langchain_message(msg)
                if normalized_msg:
                    self._current_trace["messages"].append(normalized_msg)
        
        # Extract tools if provided
        invocation_params = kwargs.get("invocation_params", {})
        tools = self._extract_tools(invocation_params)
        if tools:
            self._current_trace["tools"] = tools
    
    def on_llm_end(
        self,
        response: Any,  # LLMResult when langchain available
        **kwargs: Any,
    ) -> None:
        """Called when LLM ends running."""
        completed_at = datetime.utcnow()
        
        # Extract the assistant's response text for the result field
        # Don't add assistant message to messages array - only input messages go there
        result_text = None
        if response.generations and len(response.generations) > 0:
            generation = response.generations[0][0]
            
            # Handle chat message responses
            if hasattr(generation, "message"):
                assistant_msg = self._normalize_langchain_message(generation.message)
                if assistant_msg:
                    content = assistant_msg.get("content")
                    # Only set result if there's actual text content
                    if isinstance(content, str) and content.strip():
                        result_text = content
            # Handle text generation responses
            elif hasattr(generation, "text"):
                text = generation.text
                if text and text.strip():
                    result_text = text
        
        # Create the trace
        self._create_trace(
            completed_at=completed_at,
            result=result_text,
            error=None,
        )
    
    def on_llm_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        **kwargs: Any,
    ) -> None:
        """Called when LLM encounters an error."""
        completed_at = datetime.utcnow()
        
        # Create trace with error
        self._create_trace(
            completed_at=completed_at,
            result=None,
            error=str(error),
        )
    
    def _create_trace(
        self,
        completed_at: datetime,
        result: Optional[str],
        error: Optional[str],
    ) -> None:
        """Create a trace in R4U."""
        try:
            payload = {
                "model": self._current_trace.get("model", "unknown"),
                "messages": self._current_trace.get("messages", []),
                "started_at": self._current_trace.get("started_at", datetime.utcnow()),
                "completed_at": completed_at,
                "path": self._call_path,
                "result": result,
                "error": error,
                "project": self._project,
            }
            
            # Add tools if present
            tools = self._current_trace.get("tools")
            if tools:
                payload["tools"] = tools
            
            self._r4u_client.create_trace(**payload)
        except Exception as e:
            # Don't let tracing errors break the application
            print(f"Failed to create trace: {e}")
    
    @staticmethod
    def _extract_model_name(serialized: Dict[str, Any], kwargs: Dict[str, Any]) -> str:
        """Extract the model name from serialized data or kwargs."""
        # Try to get from invocation params
        invocation_params = kwargs.get("invocation_params", {})
        if "model" in invocation_params:
            return invocation_params["model"]
        if "model_name" in invocation_params:
            return invocation_params["model_name"]
        
        # Try to get from serialized
        if "name" in serialized:
            return serialized["name"]
        if "id" in serialized and isinstance(serialized["id"], list):
            # LangChain stores class path as list like ['langchain', 'chat_models', 'openai', 'ChatOpenAI']
            return serialized["id"][-1] if serialized["id"] else "unknown"
        
        return "unknown"
    
    @staticmethod
    def _normalize_langchain_message(message: Any) -> Optional[Dict[str, Any]]:
        """Normalize a LangChain message to R4U format."""
        if not message:
            return None
        
        normalized: Dict[str, Any] = {}
        
        # Extract role
        if hasattr(message, "type"):
            role_map = {
                "human": "user",
                "ai": "assistant",
                "system": "system",
                "function": "function",
                "tool": "tool",
            }
            normalized["role"] = role_map.get(message.type, message.type)
        else:
            normalized["role"] = "user"
        
        # Extract content
        if hasattr(message, "content"):
            normalized["content"] = message.content
        
        # Extract name if present
        if hasattr(message, "name") and message.name:
            normalized["name"] = message.name
        
        # Extract tool calls from AI messages
        if hasattr(message, "tool_calls") and message.tool_calls:
            tool_calls = []
            for tool_call in message.tool_calls:
                tc_dict = {
                    "type": "function",
                }
                
                if isinstance(tool_call, dict):
                    tool_id = tool_call.get("id")
                    tc_dict["id"] = tool_id if tool_id else None  # type: ignore
                    tc_dict["function"] = {  # type: ignore
                        "name": tool_call.get("name"),
                        "arguments": tool_call.get("args", {}),
                    }
                else:
                    tool_id = getattr(tool_call, "id", None)
                    tc_dict["id"] = tool_id if tool_id else None  # type: ignore
                    tc_dict["function"] = {  # type: ignore
                        "name": getattr(tool_call, "name", None),
                        "arguments": getattr(tool_call, "args", {}),
                    }
                
                tool_calls.append(tc_dict)
            
            normalized["tool_calls"] = tool_calls
        
        # Extract additional_kwargs (may contain function/tool call info)
        if hasattr(message, "additional_kwargs") and message.additional_kwargs:
            additional = message.additional_kwargs
            
            # Handle function calls (older format)
            if "function_call" in additional:
                func_call = additional["function_call"]
                normalized.setdefault("tool_calls", []).append({
                    "type": "function",
                    "function": {
                        "name": func_call.get("name"),
                        "arguments": R4UCallbackHandler._parse_json_safe(func_call.get("arguments", "{}")),
                    }
                })
            
            # Handle tool calls if not already extracted
            if "tool_calls" in additional and "tool_calls" not in normalized:
                tool_calls = []
                for tc in additional["tool_calls"]:
                    tool_calls.append({
                        "id": tc.get("id"),
                        "type": tc.get("type", "function"),
                        "function": {
                            "name": tc.get("function", {}).get("name"),
                            "arguments": R4UCallbackHandler._parse_json_safe(
                                tc.get("function", {}).get("arguments", "{}")
                            ),
                        }
                    })
                normalized["tool_calls"] = tool_calls
        
        # Handle tool message responses
        if hasattr(message, "tool_call_id") and message.tool_call_id:
            normalized["tool_call_id"] = message.tool_call_id
        
        return normalized
    
    @staticmethod
    def _parse_json_safe(value: Any) -> Any:
        """Safely parse JSON, returning the original value if parsing fails."""
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, ValueError):
                return value
        return value
    
    @staticmethod
    def _extract_tools(invocation_params: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Extract tool definitions from invocation parameters."""
        tools = invocation_params.get("tools", [])
        if not tools:
            return None
        
        normalized_tools = []
        for tool in tools:
            if isinstance(tool, dict):
                # Already in dict format
                tool_def = {
                    "type": tool.get("type", "function"),
                    "name": tool.get("function", {}).get("name"),
                    "description": tool.get("function", {}).get("description"),
                    "parameters": tool.get("function", {}).get("parameters"),
                }
            else:
                # Try to extract from object
                tool_def = {
                    "type": getattr(tool, "type", "function"),
                    "name": getattr(getattr(tool, "function", None), "name", None),
                    "description": getattr(getattr(tool, "function", None), "description", None),
                    "parameters": getattr(getattr(tool, "function", None), "parameters", None),
                }
            
            # Only add if we have a name
            if tool_def.get("name"):
                normalized_tools.append({k: v for k, v in tool_def.items() if v is not None})
        
        return normalized_tools if normalized_tools else None


def wrap_langchain(
    api_url: str = "http://localhost:8000",
    timeout: float = 30.0,
    project: Optional[str] = None,
) -> "R4UCallbackHandler":
    """Create a LangChain callback handler that sends traces to R4U.
    
    Args:
        api_url: Base URL for the R4U API
        timeout: HTTP request timeout in seconds
        project: Project name for traces. If not provided, uses R4U_PROJECT env variable or defaults to "Default Project"
    
    Returns:
        R4UCallbackHandler that can be used with LangChain
    
    Example:
        >>> from langchain_openai import ChatOpenAI
        >>> from r4u.integrations.langchain import wrap_langchain
        >>> 
        >>> # Create the callback handler
        >>> r4u_handler = wrap_langchain(api_url="http://localhost:8000")
        >>> 
        >>> # Use with any LangChain model
        >>> llm = ChatOpenAI(model="gpt-3.5-turbo", callbacks=[r4u_handler])
        >>> result = llm.invoke("What is the capital of France?")
        >>> 
        >>> # Or with chains
        >>> chain = prompt | llm
        >>> result = chain.invoke({"input": "Hello"}, config={"callbacks": [r4u_handler]})
    
    Raises:
        ImportError: If langchain-core is not installed
    """
    if not LANGCHAIN_AVAILABLE:
        raise ImportError(
            "LangChain is not installed. Please install it with: "
            "pip install langchain-core"
        )
    
    if project is None:
        project = os.getenv("R4U_PROJECT", "Default Project")
    
    r4u_client = R4UClient(api_url=api_url, timeout=timeout)
    return R4UCallbackHandler(r4u_client, project)
