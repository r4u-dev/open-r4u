from __future__ import annotations

from datetime import datetime, timezone
import functools
import types
from typing import Callable

import requests

from .tracer import AbstractTracer, PrintTracer, RequestInfo


def _build_request_info(request: requests.PreparedRequest) -> RequestInfo:
    """Build RequestInfo from a requests PreparedRequest."""
    return RequestInfo(
        method=request.method.upper(),
        url=request.url,
        headers=dict(request.headers),
        request_payload=request.body,
        started_at=datetime.now(timezone.utc)
    )


def _update_request_info(request_info: RequestInfo, response: requests.Response, error: str = None) -> None:
    """
    Common logic for processing request info after request completion.
    """
    completed_at = datetime.now(timezone.utc)
    request_info.status_code = response.status_code if response else None
    request_info.error = error
    request_info.response_size = len(response.content) if response and response.content else None
    request_info.completed_at = completed_at
    
    if response and response.content:
        request_info.response_payload = response.content


def _create_send_wrapper(original: Callable, tracer: AbstractTracer):
    """Create wrapper for requests.Session.send method."""
    @functools.wraps(original)
    def wrapper(self, request, **kwargs):
        request_info = _build_request_info(request)

        response = None
        error = None
        try:
            response = original(request, **kwargs)
            return response
        except Exception as e:
            error = str(e)
            raise
        finally:
            _update_request_info(request_info, response, error)
            tracer.trace_request(request_info)

    return wrapper


def trace_session(session: requests.Session, tracer: AbstractTracer = None) -> None:
    """
    Trace a requests.Session.
    
    This wraps the send method which is the core method used by all HTTP methods
    (get, post, put, delete, etc.).
    
    Args:
        session: The requests.Session instance to trace
        tracer: Optional tracer instance. If None, uses PrintTracer()
    
    Example:
        >>> import requests
        >>> from r4u.integrations.http.requests import trace_session
        >>> 
        >>> session = requests.Session()
        >>> trace_session(session)
        >>> 
        >>> response = session.get('https://api.example.com/data')
    """
    # Check if already patched to avoid double-patching
    if hasattr(session.send, '_r4u_patched'):
        return
    
    tracer = tracer or PrintTracer()
    wrapper = _create_send_wrapper(session.send, tracer)
    wrapper._r4u_patched = True  # Mark as patched
    session.send = types.MethodType(wrapper, session)
