"""OpenAI integration for R4U observability."""

from datetime import datetime
from typing import Any

from ..client import R4UClient
from ..utils import extract_call_path


class OpenAIWrapper:
    """Wrapper for OpenAI client that automatically creates traces."""

    def __init__(self, client: Any, r4u_client: R4UClient):
        """Initialize the wrapper.
        
        Args:
            client: Original OpenAI client
            r4u_client: R4U client for creating traces
        """
        self._original_client = client
        self._r4u_client = r4u_client
        
        # Wrap the chat completions
        if hasattr(client, 'chat') and hasattr(client.chat, 'completions'):
            self.chat = ChatCompletionsWrapper(client.chat, r4u_client)
        else:
            self.chat = client.chat if hasattr(client, 'chat') else None

    def __getattr__(self, name: str) -> Any:
        """Delegate other attributes to the original client."""
        return getattr(self._original_client, name)


class ChatCompletionsWrapper:
    """Wrapper for OpenAI chat completions."""

    def __init__(self, chat_client: Any, r4u_client: R4UClient):
        """Initialize the wrapper.
        
        Args:
            chat_client: Original chat client
            r4u_client: R4U client for creating traces
        """
        self._original_chat = chat_client
        self._r4u_client = r4u_client
        self.completions = CompletionsWrapper(chat_client.completions, r4u_client)

    def __getattr__(self, name: str) -> Any:
        """Delegate other attributes to the original client."""
        return getattr(self._original_chat, name)


class CompletionsWrapper:
    """Wrapper for OpenAI completions that creates traces."""

    def __init__(self, completions_client: Any, r4u_client: R4UClient):
        """Initialize the wrapper.
        
        Args:
            completions_client: Original completions client
            r4u_client: R4U client for creating traces
        """
        self._original_completions = completions_client
        self._r4u_client = r4u_client
        
        # Detect if this is an async client by checking the client type
        import inspect
        self._is_async = inspect.iscoroutinefunction(completions_client.create)

    def create(self, **kwargs) -> Any:
        """Create completion with tracing.
        
        This method handles both sync and async OpenAI clients.
        For AsyncOpenAI, this returns a coroutine that should be awaited.
        """
        if self._is_async:
            # For async clients, return the coroutine
            return self._trace_completion_async(self._original_completions.create, **kwargs)
        else:
            # For sync clients, call synchronously
            return self._trace_completion(self._original_completions.create, **kwargs)

    async def acreate(self, **kwargs) -> Any:
        """Create completion asynchronously with tracing.
        
        This is kept for backward compatibility but async clients should use create().
        """
        return await self._trace_completion_async(self._original_completions.create, **kwargs)

    def _trace_completion(self, original_method: Any, **kwargs) -> Any:
        """Trace a synchronous completion call."""
        started_at = datetime.utcnow()
        model = kwargs.get('model', 'unknown')
        messages = kwargs.get('messages', [])
        
        # Extract call path
        call_path, line_number = extract_call_path()
        
        try:
            # Call the original method
            result = original_method(**kwargs)
            completed_at = datetime.utcnow()
            
            # Extract result content
            result_content = None
            if hasattr(result, 'choices') and len(result.choices) > 0:
                if hasattr(result.choices[0], 'message') and hasattr(result.choices[0].message, 'content'):
                    result_content = result.choices[0].message.content
            
            # Create trace
            self._create_trace_sync(
                model=model,
                messages=messages,
                result=result_content,
                started_at=started_at,
                completed_at=completed_at,
                path=call_path
            )
            
            return result
            
        except Exception as e:
            completed_at = datetime.utcnow()
            
            # Create trace with error
            self._create_trace_sync(
                model=model,
                messages=messages,
                error=str(e),
                started_at=started_at,
                completed_at=completed_at,
                path=call_path
            )
            
            # Re-raise the exception
            raise

    async def _trace_completion_async(self, original_method: Any, **kwargs) -> Any:
        """Trace an asynchronous completion call."""
        started_at = datetime.utcnow()
        model = kwargs.get('model', 'unknown')
        messages = kwargs.get('messages', [])
        
        # Extract call path
        call_path, line_number = extract_call_path()
        
        try:
            # Call the original method
            result = await original_method(**kwargs)
            completed_at = datetime.utcnow()
            
            # Extract result content
            result_content = None
            if hasattr(result, 'choices') and len(result.choices) > 0:
                if hasattr(result.choices[0], 'message') and hasattr(result.choices[0].message, 'content'):
                    result_content = result.choices[0].message.content
            
            # Create trace
            await self._create_trace_async(
                model=model,
                messages=messages,
                result=result_content,
                started_at=started_at,
                completed_at=completed_at,
                path=call_path
            )
            
            return result
            
        except Exception as e:
            completed_at = datetime.utcnow()
            
            # Create trace with error
            await self._create_trace_async(
                model=model,
                messages=messages,
                error=str(e),
                started_at=started_at,
                completed_at=completed_at,
                path=call_path
            )
            
            # Re-raise the exception
            raise

    def _create_trace_sync(self, **kwargs):
        """Create trace synchronously."""
        try:
            self._r4u_client.create_trace(**kwargs)
        except Exception as e:
            # Log the error but don't fail the original request
            print(f"Failed to create trace: {e}")

    async def _create_trace_async(self, **kwargs):
        """Create trace asynchronously."""
        try:
            await self._r4u_client.create_trace_async(**kwargs)
        except Exception as e:
            # Log the error but don't fail the original request
            print(f"Failed to create trace: {e}")

    def __getattr__(self, name: str) -> Any:
        """Delegate other attributes to the original client."""
        return getattr(self._original_completions, name)


def wrap_openai(
    client: Any, 
    api_url: str = "http://localhost:8000", 
    timeout: float = 30.0
) -> OpenAIWrapper:
    """Wrap an OpenAI client to automatically create traces.
    
    Args:
        client: OpenAI client instance
        api_url: R4U API base URL
        timeout: HTTP timeout for trace requests
        
    Returns:
        Wrapped client that creates traces automatically
        
    Example:
        >>> from openai import OpenAI
        >>> from r4u.integrations.openai import wrap_openai
        >>> 
        >>> client = OpenAI()
        >>> traced_client = wrap_openai(client)
        >>> 
        >>> # This will automatically create a trace
        >>> response = traced_client.chat.completions.create(
        ...     model="gpt-3.5-turbo",
        ...     messages=[{"role": "user", "content": "Hello!"}]
        ... )
    """
    r4u_client = R4UClient(api_url=api_url, timeout=timeout)
    return OpenAIWrapper(client, r4u_client)