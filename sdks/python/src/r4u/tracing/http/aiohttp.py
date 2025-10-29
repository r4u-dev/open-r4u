from __future__ import annotations

import functools
import types
from collections.abc import Callable
from datetime import datetime, timezone

import aiohttp

from r4u.client import AbstractTracer, HTTPTrace
from r4u.tracing.http.filters import should_trace_url
from r4u.utils import extract_call_path


class StreamingResponseWrapper:
    """Wrapper for aiohttp.ClientResponse that tracks streaming completion and collects content."""

    def __init__(
        self,
        response: aiohttp.ClientResponse,
        trace_ctx: dict,
        tracer: AbstractTracer | None = None,
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
    async def iter_chunked(self, chunk_size: int = 8192):
        """Iterate over response content in chunks."""
        try:
            async for chunk in self._response.content.iter_chunked(chunk_size):
                self._content_collected += chunk
                yield chunk
        except Exception as e:
            self._error = str(e)
            raise
        finally:
            self._complete_streaming()

    async def iter_any(self):
        """Iterate over response content in any available chunks."""
        try:
            async for chunk in self._response.content.iter_any():
                self._content_collected += chunk
                yield chunk
        except Exception as e:
            self._error = str(e)
            raise
        finally:
            self._complete_streaming()

    async def iter_line(self):
        """Iterate over response content line by line."""
        try:
            async for line in self._response.content.iter_line():
                self._content_collected += line + b"\n"
                yield line
        except Exception as e:
            self._error = str(e)
            raise
        finally:
            self._complete_streaming()

    async def read(self):
        """Read all response content."""
        try:
            content = await self._response.read()
            self._content_collected = content
            return content
        except Exception as e:
            self._error = str(e)
            raise
        finally:
            self._complete_streaming()

    async def text(self):
        """Read response content as text."""
        try:
            content = await self._response.text()
            self._content_collected = content.encode("utf-8")
            return content
        except Exception as e:
            self._error = str(e)
            raise
        finally:
            self._complete_streaming()

    async def json(self):
        """Read response content as JSON."""
        try:
            content = await self._response.json()
            # For JSON, we need to get the raw content
            raw_content = await self._response.read()
            self._content_collected = raw_content
            return content
        except Exception as e:
            self._error = str(e)
            raise
        finally:
            self._complete_streaming()

    async def close(self):
        """Close the response."""
        try:
            await self._response.close()
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
        """Finalize and send the trace."""
        completed_at = datetime.now(timezone.utc)
        self._trace_ctx["completed_at"] = completed_at
        self._trace_ctx["status_code"] = self._response.status
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
    """Check if the request is configured for streaming.

    For aiohttp, we detect streaming by checking if any streaming methods
    are likely to be used. Since aiohttp doesn't have a stream parameter,
    we'll assume streaming if the response is not immediately consumed.
    """
    # For aiohttp, we can't easily detect streaming at request time
    # We'll handle this by wrapping all responses and detecting streaming
    # based on which methods are called
    return True  # Always wrap responses to handle both streaming and non-streaming


def _create_async_wrapper(original: Callable, tracer: AbstractTracer):
    """Create wrapper for aiohttp session methods like _request."""

    @functools.wraps(original)
    async def wrapper(self, *args, **kwargs):
        # Extract method and url from args/kwargs for aiohttp session methods
        method = args[0] if len(args) > 0 else kwargs.get("method", "GET")
        url = args[1] if len(args) > 1 else kwargs.get("url")

        # Check if we should trace this URL
        if not should_trace_url(str(url)):
            return await original(*args, **kwargs)

        started_at = datetime.now(timezone.utc)
        request_payload = kwargs.get("data") or kwargs.get("json") or b""
        if isinstance(request_payload, str):
            request_payload = request_payload.encode("utf-8")
        elif not isinstance(request_payload, bytes):
            request_payload = b""

        call_path_and_no = extract_call_path(is_async=True)

        trace_ctx = {
            "method": str(method).upper(),
            "url": str(url),
            "started_at": started_at,
            "request_bytes": request_payload,
            "request_headers": dict(kwargs.get("headers", {})),
            "path": call_path_and_no[0] if call_path_and_no else None,
        }

        response = None
        error = None
        try:
            response = await original(*args, **kwargs)

            # Always wrap the response to handle both streaming and non-streaming
            return StreamingResponseWrapper(response, trace_ctx, tracer)

        except Exception as e:
            error = str(e)
            # For errors, we still need to send a trace
            completed_at = datetime.now(timezone.utc)
            trace = HTTPTrace(
                url=trace_ctx.get("url", ""),
                method=trace_ctx.get("method", ""),
                path=trace_ctx.get("path"),
                started_at=trace_ctx["started_at"],
                completed_at=completed_at,
                status_code=0,
                error=error,
                request=trace_ctx["request_bytes"],
                request_headers=trace_ctx["request_headers"],
                response=b"",
                response_headers={},
            )
            try:
                tracer.log(trace)
            except Exception as trace_error:
                # Log error but don't fail the request
                print(f"Failed to create HTTP trace: {trace_error}")
            raise

    return wrapper


def trace_async_client(
    session: aiohttp.ClientSession,
    tracer: AbstractTracer | None = None,
) -> None:
    """Trace an aiohttp ClientSession.

    This wraps the _request method which is the core method used by all HTTP methods.
    """
    # Check if already patched to avoid double-patching
    if hasattr(session._request, "_r4u_patched"):
        return

    wrapper = _create_async_wrapper(session._request, tracer)
    wrapper._r4u_patched = True  # Mark as patched
    session._request = types.MethodType(wrapper, session)


def _create_aiohttp_constructor_wrapper(
    original_init: Callable,
    session_class: type,
    tracer: AbstractTracer | None,
):
    """Create a wrapper for aiohttp session constructors."""

    @functools.wraps(original_init)
    def wrapper(self, *args, **kwargs):
        # Call original constructor
        original_init(self, *args, **kwargs)

        # Apply tracing
        try:
            if isinstance(self, session_class):
                if hasattr(self, "_request") and not hasattr(
                    self._request,
                    "_r4u_patched",
                ):
                    trace_async_client(self, tracer)
        except Exception as e:
            # Don't fail session creation if tracing fails
            print(f"Failed to apply tracing to {session_class.__name__}: {e}")

    return wrapper


def trace_all(tracer: AbstractTracer) -> None:
    """Intercept aiohttp session creation to automatically trace all instances.

    This function intercepts the aiohttp.ClientSession constructor to automatically
    apply tracing to all instances that will be created.
    This approach works even when libraries create their own aiohttp session instances.

    Args:
        tracer: Tracer instance

    Example:
        >>> from r4u.tracing.http.aiohttp import trace_all
        >>> trace_all()
        >>>
        >>> # Now all aiohttp sessions will be automatically traced
        >>> import aiohttp
        >>> session = aiohttp.ClientSession()  # Automatically traced
        >>> async with session.get('https://api.example.com/data') as response:
        ...     data = await response.json()

    """
    # Check if already patched to avoid double-patching
    if hasattr(aiohttp.ClientSession, "_r4u_constructor_patched"):
        return

    # Store original constructor
    aiohttp._original_client_session_init = aiohttp.ClientSession.__init__

    # Create constructor wrapper
    aiohttp.ClientSession.__init__ = _create_aiohttp_constructor_wrapper(
        aiohttp.ClientSession.__init__,
        aiohttp.ClientSession,
        tracer,
    )

    # Mark as patched
    aiohttp.ClientSession._r4u_constructor_patched = True


def untrace_all() -> None:
    """Remove constructor interception from aiohttp.ClientSession class.

    This restores the original aiohttp.ClientSession constructor.
    """
    if not hasattr(aiohttp.ClientSession, "_r4u_constructor_patched"):
        return

    # Restore original constructor
    if hasattr(aiohttp, "_original_client_session_init"):
        aiohttp.ClientSession.__init__ = aiohttp._original_client_session_init
        delattr(aiohttp, "_original_client_session_init")

    # Remove patch marker
    if hasattr(aiohttp.ClientSession, "_r4u_constructor_patched"):
        delattr(aiohttp.ClientSession, "_r4u_constructor_patched")
