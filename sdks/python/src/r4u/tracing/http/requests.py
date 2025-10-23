from __future__ import annotations

import functools
import types
from collections.abc import Callable
from datetime import datetime, timezone

import requests

from r4u.client import AbstractTracer, HTTPTrace
from r4u.tracing.http.filters import should_trace_url
from r4u.utils import extract_call_path


class StreamingResponseWrapper:
    """Wrapper for requests.Response that tracks streaming completion and collects content."""

    def __init__(
        self,
        response: requests.Response,
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
    def iter_content(
        self, chunk_size: int | None = None, decode_unicode: bool = False,
    ):
        """Iterate over response content in chunks."""
        try:
            for chunk in self._response.iter_content(chunk_size, decode_unicode):
                if isinstance(chunk, str):
                    self._content_collected += chunk.encode("utf-8")
                else:
                    self._content_collected += chunk
                yield chunk
        except Exception as e:
            self._error = str(e)
            raise
        finally:
            self._complete_streaming()

    def iter_lines(
        self,
        chunk_size: int | None = None,
        decode_unicode: bool = None,
        delimiter: str | None = None,
    ):
        """Iterate over response content line by line."""
        try:
            for line in self._response.iter_lines(
                chunk_size, decode_unicode, delimiter,
            ):
                if isinstance(line, str):
                    self._content_collected += line.encode("utf-8") + b"\n"
                else:
                    self._content_collected += line + b"\n"
                yield line
        except Exception as e:
            self._error = str(e)
            raise
        finally:
            self._complete_streaming()

    @property
    def content(self):
        """Get response content."""
        if not self._is_streaming_complete:
            # If content is accessed directly, read it and complete streaming
            try:
                content = self._response.content
                self._content_collected = content
                self._complete_streaming()
                return content
            except Exception as e:
                self._error = str(e)
                self._complete_streaming()
                raise
        return self._response.content

    @property
    def text(self):
        """Get response text."""
        if not self._is_streaming_complete:
            # If text is accessed directly, read it and complete streaming
            try:
                text = self._response.text
                self._content_collected = text.encode("utf-8")
                self._complete_streaming()
                return text
            except Exception as e:
                self._error = str(e)
                self._complete_streaming()
                raise
        return self._response.text

    def json(self, **kwargs):
        """Get response JSON."""
        if not self._is_streaming_complete:
            # If JSON is accessed directly, read it and complete streaming
            try:
                json_data = self._response.json(**kwargs)
                # For JSON, we need to get the raw content
                self._content_collected = self._response.content
                self._complete_streaming()
                return json_data
            except Exception as e:
                self._error = str(e)
                self._complete_streaming()
                raise
        return self._response.json(**kwargs)

    def close(self):
        """Close the response."""
        try:
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
        """Finalize and send the trace."""
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
    """Check if the request is configured for streaming using requests' stream parameter."""
    return kwargs.get("stream", False)


def _build_trace_context(request: requests.PreparedRequest) -> dict:
    """Build initial trace context from a requests PreparedRequest."""
    started_at = datetime.now(timezone.utc)
    request_payload = request.body or b""
    if isinstance(request_payload, str):
        request_payload = request_payload.encode("utf-8")

    # Extract call path
    call_path, _ = extract_call_path()

    return {
        "method": request.method.upper(),
        "url": request.url,
        "started_at": started_at,
        "request_bytes": request_payload,
        "request_headers": dict(request.headers),
        "path": call_path,
    }


def _finalize_trace(
    trace_ctx: dict, response: requests.Response, error: str = None,
) -> HTTPTrace:
    """Create final HTTPTrace from context and response."""
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


def _create_send_wrapper(original: Callable, tracer: AbstractTracer | None = None):
    """Create wrapper for requests.Session.send method."""

    @functools.wraps(original)
    def wrapper(self, request, **kwargs):
        # Check if we should trace this URL
        if not should_trace_url(request.url):
            return original(request, **kwargs)

        trace_ctx = _build_trace_context(request)

        response = None
        error = None
        try:
            response = original(request, **kwargs)

            # Check if this is a streaming request
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


def trace_session(
    session: requests.Session, tracer: AbstractTracer | None = None,
) -> None:
    """Trace a requests.Session.

    This wraps the send method which is the core method used by all HTTP methods
    (get, post, put, delete, etc.).

    Args:
        session: The requests.Session instance to trace
        tracer: Tracer instance. If None, uses the default R4U client.

    Example:
        >>> import requests
        >>> from r4u.tracing.http.requests import trace_session
        >>>
        >>> session = requests.Session()
        >>> trace_session(session)
        >>>
        >>> response = session.get('https://api.example.com/data')

    """
    # Check if already patched to avoid double-patching
    if hasattr(session.send, "_r4u_patched"):
        return

    wrapper = _create_send_wrapper(session.send, tracer)
    wrapper._r4u_patched = True  # Mark as patched
    session.send = types.MethodType(wrapper, session)


def _create_requests_constructor_wrapper(
    original_init: Callable, session_class: type, tracer: AbstractTracer | None,
):
    """Create a wrapper for requests session constructors."""

    @functools.wraps(original_init)
    def wrapper(self, *args, **kwargs):
        # Call original constructor
        original_init(self, *args, **kwargs)

        # Apply tracing
        try:
            if isinstance(self, session_class):
                if hasattr(self, "send") and not hasattr(self.send, "_r4u_patched"):
                    trace_session(self, tracer)
        except Exception as e:
            # Don't fail session creation if tracing fails
            print(f"Failed to apply tracing to {session_class.__name__}: {e}")

    return wrapper


def trace_all(tracer: AbstractTracer) -> None:
    """Intercept requests session creation to automatically trace all instances.

    This function intercepts the requests.Session constructor to automatically
    apply tracing to all instances that will be created.
    This approach works even when libraries create their own requests session instances.

    Args:
        tracer: Tracer instance

    Example:
        >>> from r4u.tracing.http.requests import trace_all
        >>> trace_all()
        >>>
        >>> # Now all requests sessions will be automatically traced
        >>> import requests
        >>> session = requests.Session()  # Automatically traced
        >>> response = session.get('https://api.example.com/data')

    """
    # Check if already patched to avoid double-patching
    if hasattr(requests.Session, "_r4u_constructor_patched"):
        return

    # Store original constructor
    requests._original_session_init = requests.Session.__init__

    # Create constructor wrapper
    requests.Session.__init__ = _create_requests_constructor_wrapper(
        requests.Session.__init__, requests.Session, tracer,
    )

    # Mark as patched
    requests.Session._r4u_constructor_patched = True


def untrace_all() -> None:
    """Remove constructor interception from requests.Session class.

    This restores the original requests.Session constructor.
    """
    if not hasattr(requests.Session, "_r4u_constructor_patched"):
        return

    # Restore original constructor
    if hasattr(requests, "_original_session_init"):
        requests.Session.__init__ = requests._original_session_init
        delattr(requests, "_original_session_init")

    # Remove patch marker
    if hasattr(requests.Session, "_r4u_constructor_patched"):
        delattr(requests.Session, "_r4u_constructor_patched")
