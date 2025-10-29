from __future__ import annotations

import functools
import types
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from async_trace import print_async_trace, print_trace
import httpx

from r4u.client import AbstractTracer, HTTPTrace
from r4u.tracing.http.filters import should_trace_url
from r4u.utils import extract_call_path

if TYPE_CHECKING:
    from collections.abc import Callable


class StreamingResponseWrapper:
    """Wrapper for httpx.Response that tracks streaming completion and collects content."""

    def __init__(
        self,
        response: httpx.Response,
        trace_ctx: dict,
        tracer: AbstractTracer,
    ):
        self._response = response
        self._trace_ctx = trace_ctx
        self._content_collected = b""
        self._is_streaming_complete = False
        self._error = None
        self._tracer = tracer

    # Delegate all attributes to the original response
    def __getattr__(self, name):
        return getattr(self._response, name)

    # Override streaming methods to track content
    def iter_bytes(self, chunk_size: int | None = None):
        try:
            for chunk in self._response.iter_bytes(chunk_size):
                self._content_collected += chunk
                yield chunk
        except Exception as e:
            self._error = str(e)
            raise
        finally:
            self._complete_streaming()

    def iter_text(self, chunk_size: int | None = None):
        try:
            for chunk in self._response.iter_text(chunk_size):
                self._content_collected += chunk.encode("utf-8")
                yield chunk
        except Exception as e:
            self._error = str(e)
            raise
        finally:
            self._complete_streaming()

    def iter_lines(self):
        try:
            for line in self._response.iter_lines():
                self._content_collected += line.encode("utf-8") + b"\n"
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
    async def aiter_bytes(self, chunk_size: int | None = None):
        try:
            async for chunk in self._response.aiter_bytes(chunk_size):
                self._content_collected += chunk
                yield chunk
        except Exception as e:
            self._error = str(e)
            raise
        finally:
            self._complete_streaming()

    async def aiter_text(self, chunk_size: int | None = None):
        try:
            async for chunk in self._response.aiter_text(chunk_size):
                self._content_collected += chunk.encode("utf-8")
                yield chunk
        except Exception as e:
            self._error = str(e)
            raise
        finally:
            self._complete_streaming()

    async def aiter_lines(self):
        try:
            async for line in self._response.aiter_lines():
                self._content_collected += line.encode("utf-8") + b"\n"
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
            if hasattr(self._response, "aclose"):
                await self._response.aclose()
        finally:
            self._complete_streaming()

    def close(self):
        try:
            if hasattr(self._response, "close"):
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
            url=self._trace_ctx.get("url", ""),
            method=self._trace_ctx.get("method", ""),
            path=self._trace_ctx.get("path"),
            started_at=self._trace_ctx["started_at"],
            completed_at=self._trace_ctx["completed_at"],
            status_code=self._trace_ctx.get("status_code", 0),
            error=self._trace_ctx.get("error"),
            request=self._trace_ctx["request_bytes"],
            request_headers=self._trace_ctx["request_headers"],
            response=self._trace_ctx.get("response_bytes", b""),
            response_headers=self._trace_ctx.get("response_headers", {}),
        )
        try:
            self._tracer.log(trace)
        except Exception as error:
            # Log error but don't fail the request
            print(f"Failed to create HTTP trace: {error}")


def _is_streaming_request(kwargs: dict) -> bool:
    """Check if the request is configured for streaming using httpx's stream parameter."""
    return kwargs.get("stream", False)


def _build_trace_context(request: httpx.Request) -> dict:
    """Build initial trace context from httpx request."""
    started_at = datetime.now(timezone.utc)
    headers_dict = dict(request.headers)

    # Extract call path
    call_path_with_no = extract_call_path()
    print_trace()

    return {
        "method": request.method.upper(),
        "url": str(request.url),
        "started_at": started_at,
        "request_bytes": request.content or b"",
        "request_headers": headers_dict,
        "path": call_path_with_no[0] if call_path_with_no else None,
    }


def _finalize_trace(
    trace_ctx: dict,
    response: httpx.Response,
    error: str | None,
) -> HTTPTrace:
    completed_at = datetime.now(timezone.utc)
    status_code = response.status_code if response else 0
    response_bytes = response.content or b"" if response else b""
    response_headers = dict(response.headers) if response else {}

    return HTTPTrace(
        url=trace_ctx.get("url", ""),
        method=trace_ctx.get("method", ""),
        path=trace_ctx.get("path"),
        started_at=trace_ctx["started_at"],
        completed_at=completed_at,
        status_code=status_code,
        error=error,
        request=trace_ctx["request_bytes"],
        request_headers=trace_ctx["request_headers"],
        response=response_bytes,
        response_headers=response_headers,
    )


def _create_async_wrapper(original: Callable, tracer: AbstractTracer):
    @functools.wraps(original)
    async def wrapper(self, *args, **kwargs):
        # Check if we should trace this URL
        if not should_trace_url(str(args[0].url)):
            return await original(*args, **kwargs)

        trace_ctx = _build_trace_context(args[0])

        response = None
        error = None
        try:
            response = await original(*args, **kwargs)

            # Check if this is a streaming request using httpx's stream parameter
            if _is_streaming_request(kwargs):
                # Wrap the response to track streaming completion
                return StreamingResponseWrapper(response, trace_ctx, tracer)
            # For non-streaming responses, trace immediately
            trace = _finalize_trace(trace_ctx, response, error)
            try:
                tracer.log(trace)
            except Exception as trace_error:
                # Log error but don't fail the request
                print(f"Failed to create HTTP trace: {trace_error}")
            return response

        except Exception as e:
            error = str(e)
            trace = _finalize_trace(trace_ctx, response, error)
            try:
                tracer.log(trace)
            except Exception as trace_error:
                # Log error but don't fail the request
                print(f"Failed to create HTTP trace: {trace_error}")
            raise

    return wrapper


def _create_sync_wrapper(original: Callable, tracer: AbstractTracer):
    @functools.wraps(original)
    def wrapper(self, *args, **kwargs):
        # Check if we should trace this URL
        if not should_trace_url(str(args[0].url)):
            return original(*args, **kwargs)
        trace_ctx = _build_trace_context(args[0])

        response = None
        error = None
        try:
            response = original(*args, **kwargs)

            # Check if this is a streaming request using httpx's stream parameter
            if _is_streaming_request(kwargs):
                # Wrap the response to track streaming completion
                return StreamingResponseWrapper(response, trace_ctx, tracer)
            # For non-streaming responses, trace immediately
            trace = _finalize_trace(trace_ctx, response, error)
            try:
                tracer.log(trace)
            except Exception as trace_error:
                # Log error but don't fail the request
                print(f"Failed to create HTTP trace: {trace_error}")
            return response

        except Exception as e:
            error = str(e)
            trace = _finalize_trace(trace_ctx, response, error)
            try:
                tracer.log(trace)
            except Exception as trace_error:
                # Log error but don't fail the request
                print(f"Failed to create HTTP trace: {trace_error}")
            raise

    return wrapper


def trace_async_client(client: httpx.AsyncClient, tracer: AbstractTracer) -> None:
    """Trace an asynchronous httpx client."""
    if hasattr(client.send, "_r4u_patched"):
        return

    # Patch send method (this handles both regular and streaming requests)
    wrapper = _create_async_wrapper(client.send, tracer)
    wrapper._r4u_patched = True
    client.send = types.MethodType(wrapper, client)


def trace_client(client: httpx.Client, tracer: AbstractTracer) -> None:
    """Trace a synchronous httpx client."""
    if hasattr(client.send, "_r4u_patched"):
        return

    # Patch send method (this handles both regular and streaming requests)
    wrapper = _create_sync_wrapper(client.send, tracer)
    wrapper._r4u_patched = True
    client.send = types.MethodType(wrapper, client)


def _create_httpx_constructor_wrapper(
    original_init: Callable,
    client_class: type,
    tracer: AbstractTracer,
):
    """Create a wrapper for httpx client constructors."""

    @functools.wraps(original_init)
    def wrapper(self, *args, **kwargs):
        # Call original constructor
        original_init(self, *args, **kwargs)

        # Apply tracing
        try:
            if isinstance(self, client_class):
                if hasattr(self, "send") and not hasattr(self.send, "_r4u_patched"):
                    if "Async" in client_class.__name__:
                        trace_async_client(self, tracer)
                    else:
                        trace_client(self, tracer)
        except Exception as e:
            # Don't fail client creation if tracing fails
            print(f"Failed to apply tracing to {client_class.__name__}: {e}")

    return wrapper


def trace_all(tracer: AbstractTracer) -> None:
    """Intercept httpx client creation to automatically trace all instances.

    This function intercepts the httpx.Client and httpx.AsyncClient constructors
    to automatically apply tracing to all instances that will be created.
    This approach works even when libraries create their own httpx client instances.

    Args:
        tracer: Tracer instance

    Example:
        >>> from r4u.tracing.http.httpx import trace_all
        >>> trace_all()
        >>>
        >>> # Now all httpx clients will be automatically traced
        >>> import httpx
        >>> client = httpx.Client()  # Automatically traced
        >>> async_client = httpx.AsyncClient()  # Automatically traced

    """
    # Check if already patched to avoid double-patching
    if hasattr(httpx.Client, "_r4u_constructor_patched"):
        return

    # Store original constructors
    httpx._original_client_init = httpx.Client.__init__
    httpx._original_async_client_init = httpx.AsyncClient.__init__

    # Create constructor wrappers
    httpx.Client.__init__ = _create_httpx_constructor_wrapper(
        httpx.Client.__init__,
        httpx.Client,
        tracer,
    )
    httpx.AsyncClient.__init__ = _create_httpx_constructor_wrapper(
        httpx.AsyncClient.__init__,
        httpx.AsyncClient,
        tracer,
    )

    # Mark as patched
    httpx.Client._r4u_constructor_patched = True
    httpx.AsyncClient._r4u_constructor_patched = True


def untrace_all() -> None:
    """Remove constructor interception from httpx classes.

    This restores the original httpx.Client and httpx.AsyncClient constructors.
    """
    if not hasattr(httpx.Client, "_r4u_constructor_patched"):
        return

    # Restore original constructors
    if hasattr(httpx, "_original_client_init"):
        httpx.Client.__init__ = httpx._original_client_init
        delattr(httpx, "_original_client_init")

    if hasattr(httpx, "_original_async_client_init"):
        httpx.AsyncClient.__init__ = httpx._original_async_client_init
        delattr(httpx, "_original_async_client_init")

    # Remove patch markers
    if hasattr(httpx.Client, "_r4u_constructor_patched"):
        delattr(httpx.Client, "_r4u_constructor_patched")
    if hasattr(httpx.AsyncClient, "_r4u_constructor_patched"):
        delattr(httpx.AsyncClient, "_r4u_constructor_patched")
