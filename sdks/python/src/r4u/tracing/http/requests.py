from __future__ import annotations

from datetime import datetime, timezone
import functools
import types
from typing import Callable

import requests

from r4u.client import HTTPTrace, get_r4u_client
from .tracer import AbstractTracer, UniversalTracer


def _build_trace_context(request: requests.PreparedRequest) -> dict:
    """Build initial trace context from a requests PreparedRequest."""
    started_at = datetime.now(timezone.utc)
    request_payload = request.body or b""
    if isinstance(request_payload, str):
        request_payload = request_payload.encode("utf-8")

    return {
        "method": request.method.upper(),
        "url": request.url,
        "started_at": started_at,
        "request_bytes": request_payload,
        "request_headers": dict(request.headers),
    }


def _finalize_trace(trace_ctx: dict, response: requests.Response, error: str = None) -> HTTPTrace:
    """Create final HTTPTrace from context and response."""
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


def _create_send_wrapper(original: Callable, tracer: AbstractTracer):
    """Create wrapper for requests.Session.send method."""
    @functools.wraps(original)
    def wrapper(self, request, **kwargs):
        trace_ctx = _build_trace_context(request)

        response = None
        error = None
        try:
            response = original(request, **kwargs)
            return response
        except Exception as e:
            error = str(e)
            raise
        finally:
            trace = _finalize_trace(trace_ctx, response, error)
            tracer.trace_request(trace)

    return wrapper


def trace_session(session: requests.Session, provider: str) -> None:
    """
    Trace a requests.Session.
    
    This wraps the send method which is the core method used by all HTTP methods
    (get, post, put, delete, etc.).
    
    Args:
        session: The requests.Session instance to trace
        provider: LLM provider
    
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
    if hasattr(session.send, '_r4u_patched'):
        return
    
    wrapper = _create_send_wrapper(session.send, UniversalTracer(get_r4u_client(), provider))
    wrapper._r4u_patched = True  # Mark as patched
    session.send = types.MethodType(wrapper, session)
