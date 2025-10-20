from __future__ import annotations

from datetime import datetime, timezone
import functools
import types
from typing import Callable, Optional

import httpx

from r4u.client import get_r4u_client, HTTPTrace

from .tracer import AbstractTracer, UniversalTracer


class StreamingResponseWrapper:
    """Wrapper for httpx.Response that tracks streaming completion and collects content."""
    
    def __init__(self, response: httpx.Response, trace_ctx: dict, tracer: AbstractTracer):
        self._response = response
        self._trace_ctx = trace_ctx
        self._tracer = tracer
        self._content_collected = b""
        self._is_streaming_complete = False
        self._error = None
    
    # Delegate all attributes to the original response
    def __getattr__(self, name):
        return getattr(self._response, name)
    
    # Override streaming methods to track content
    def iter_bytes(self, chunk_size: Optional[int] = None):
        try:
            for chunk in self._response.iter_bytes(chunk_size):
                self._content_collected += chunk
                yield chunk
        except Exception as e:
            self._error = str(e)
            raise
        finally:
            self._complete_streaming()
    
    def iter_text(self, chunk_size: Optional[int] = None):
        try:
            for chunk in self._response.iter_text(chunk_size):
                self._content_collected += chunk.encode('utf-8')
                yield chunk
        except Exception as e:
            self._error = str(e)
            raise
        finally:
            self._complete_streaming()
    
    def iter_lines(self):
        try:
            for line in self._response.iter_lines():
                self._content_collected += line.encode('utf-8') + b'\n'
                yield line
        except Exception as e:
            self._error = str(e)
            raise
        finally:
            self._complete_streaming()
    
    def read(self):
        try:
            content = self._response.read()
            self._content_collected = content
            return content
        except Exception as e:
            self._error = str(e)
            raise
        finally:
            self._complete_streaming()
    
    # Async methods
    async def aiter_bytes(self, chunk_size: Optional[int] = None):
        try:
            async for chunk in self._response.aiter_bytes(chunk_size):
                self._content_collected += chunk
                yield chunk
        except Exception as e:
            self._error = str(e)
            raise
        finally:
            self._complete_streaming()
    
    async def aiter_text(self, chunk_size: Optional[int] = None):
        try:
            async for chunk in self._response.aiter_text(chunk_size):
                self._content_collected += chunk.encode('utf-8')
                yield chunk
        except Exception as e:
            self._error = str(e)
            raise
        finally:
            self._complete_streaming()
    
    async def aiter_lines(self):
        try:
            async for line in self._response.aiter_lines():
                self._content_collected += line.encode('utf-8') + b'\n'
                yield line
        except Exception as e:
            self._error = str(e)
            raise
        finally:
            self._complete_streaming()
    
    async def aread(self):
        try:
            content = await self._response.aread()
            self._content_collected = content
            return content
        except Exception as e:
            self._error = str(e)
            raise
        finally:
            self._complete_streaming()
    
    async def aclose(self):
        try:
            if hasattr(self._response, 'aclose'):
                await self._response.aclose()
        finally:
            self._complete_streaming()
    
    def close(self):
        try:
            if hasattr(self._response, 'close'):
                self._response.close()
        finally:
            self._complete_streaming()
    
    def _complete_streaming(self):
        """Complete the streaming trace when streaming is finished."""
        if self._is_streaming_complete:
            return
        
        self._is_streaming_complete = True
        
        # Build and send final HTTPTrace
        self._finalize_and_send_trace()
    
    def _finalize_and_send_trace(self):
        completed_at = datetime.now(timezone.utc)
        self._trace_ctx["completed_at"] = completed_at
        self._trace_ctx["status_code"] = self._response.status_code
        self._trace_ctx["error"] = self._error
        self._trace_ctx["response_bytes"] = self._content_collected
        self._trace_ctx["response_headers"] = dict(self._response.headers)

        trace = HTTPTrace(
            started_at=self._trace_ctx["started_at"],
            completed_at=self._trace_ctx["completed_at"],
            status_code=self._trace_ctx.get("status_code", 0),
            error=self._trace_ctx.get("error"),
            request=self._trace_ctx["request_bytes"],
            request_headers=self._trace_ctx["request_headers"],
            response=self._trace_ctx.get("response_bytes", b""),
            response_headers=self._trace_ctx.get("response_headers", {}),
            metadata={
                "method": self._trace_ctx.get("method"),
                "url": self._trace_ctx.get("url"),
            },
        )
        self._tracer.trace_request(trace)


def _is_streaming_request(kwargs: dict) -> bool:
    """Check if the request is configured for streaming using httpx's stream parameter."""
    return kwargs.get('stream', False)


def _build_trace_context(request: httpx.Request) -> dict:
    """Build initial trace context from httpx request."""
    started_at = datetime.now(timezone.utc)
    headers_dict = dict(request.headers)
    return {
        "method": request.method.upper(),
        "url": str(request.url),
        "started_at": started_at,
        "request_bytes": request.content or b"",
        "request_headers": headers_dict,
    }

def _finalize_trace(trace_ctx: dict, response: httpx.Response, error: Optional[str]) -> HTTPTrace:
    completed_at = datetime.now(timezone.utc)
    status_code = response.status_code if response else 0
    response_bytes = response.content or b"" if response else b""
    response_headers = dict(response.headers) if response else {}

    return HTTPTrace(
        started_at=trace_ctx["started_at"],
        completed_at=completed_at,
        status_code=status_code,
        error=error,
        request=trace_ctx["request_bytes"],
        request_headers=trace_ctx["request_headers"],
        response=response_bytes,
        response_headers=response_headers,
        metadata={
            "method": trace_ctx.get("method"),
            "url": trace_ctx.get("url"),
        },
    )


def _create_async_wrapper(original: Callable, tracer: AbstractTracer):
    @functools.wraps(original)
    async def wrapper(self, *args, **kwargs):
        trace_ctx = _build_trace_context(args[0])

        response = None
        error = None
        try:
            response = await original(*args, **kwargs)
            
            # Check if this is a streaming request using httpx's stream parameter
            if _is_streaming_request(kwargs):
                # Wrap the response to track streaming completion
                return StreamingResponseWrapper(response, trace_ctx, tracer)
            else:
                # For non-streaming responses, trace immediately
                trace = _finalize_trace(trace_ctx, response, error)
                tracer.trace_request(trace)
                return response
                
        except Exception as e:
            error = str(e)
            trace = _finalize_trace(trace_ctx, response, error)
            tracer.trace_request(trace)
            raise

    return wrapper


def _create_sync_wrapper(original: Callable, tracer: AbstractTracer):

    @functools.wraps(original)
    def wrapper(self, *args, **kwargs):
        trace_ctx = _build_trace_context(args[0])

        response = None
        error = None
        try:
            response = original(*args, **kwargs)
            
            # Check if this is a streaming request using httpx's stream parameter
            if _is_streaming_request(kwargs):
                # Wrap the response to track streaming completion
                return StreamingResponseWrapper(response, trace_ctx, tracer)
            else:
                # For non-streaming responses, trace immediately
                trace = _finalize_trace(trace_ctx, response, error)
                tracer.trace_request(trace)
                return response
                
        except Exception as e:
            error = str(e)
            trace = _finalize_trace(trace_ctx, response, error)
            tracer.trace_request(trace)
            raise

    return wrapper


def trace_async_client(client: httpx.AsyncClient, provider: str) -> None:
    """
    Trace an asynchronous httpx client.
    """
    
    if hasattr(client.send, '_r4u_patched'):
        return

    # Patch send method (this handles both regular and streaming requests)
    wrapper = _create_async_wrapper(client.send, UniversalTracer(get_r4u_client(), provider))
    wrapper._r4u_patched = True
    client.send = types.MethodType(wrapper, client)


def trace_client(client: httpx.Client, provider: str) -> None:
    """
    Trace a synchronous httpx client.
    """
    
    if hasattr(client.send, '_r4u_patched'):
        return

    # Patch send method (this handles both regular and streaming requests)
    wrapper = _create_sync_wrapper(client.send, UniversalTracer(get_r4u_client(), provider))
    wrapper._r4u_patched = True
    client.send = types.MethodType(wrapper, client)