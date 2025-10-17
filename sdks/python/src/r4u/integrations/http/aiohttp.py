from __future__ import annotations

from datetime import datetime, timezone
import functools
import types
from typing import Callable

import aiohttp

from .tracer import AbstractTracer, PrintTracer, RequestInfo


def _create_async_wrapper(original: Callable, tracer: AbstractTracer):
    """Create wrapper for aiohttp session methods like _request."""
    @functools.wraps(original)
    async def wrapper(self, *args, **kwargs):
        # Extract method and url from args/kwargs for aiohttp session methods
        method = args[0] if len(args) > 0 else kwargs.get('method', 'GET')
        url = args[1] if len(args) > 1 else kwargs.get('url')
        
        # Create a mock request info for tracing
        request_info = RequestInfo(
            method=str(method).upper(),
            url=str(url),
            headers=kwargs.get('headers', {}),
            request_payload=kwargs.get('data') or kwargs.get('json'),
            started_at=datetime.now(timezone.utc)
        )

        response = None
        error = None
        try:
            response = await original(*args, **kwargs)
            return response
        except Exception as e:
            error = str(e)
            raise
        finally:
            completed_at = datetime.now(timezone.utc)
            request_info.status_code = response.status if response else None
            request_info.error = error
            request_info.response_size = response.headers.get('content-length') if response else None
            request_info.completed_at = completed_at

            if response and response.content:
                request_info.response_payload = await response.read()

            tracer.trace_request(request_info)

    return wrapper

def trace_async_client(session: aiohttp.ClientSession, tracer: AbstractTracer = None) -> None:
    """
    Trace an aiohttp ClientSession.
    
    This wraps the _request method which is the core method used by all HTTP methods.
    """
    tracer = tracer or PrintTracer()
    session._request = types.MethodType(_create_async_wrapper(session._request, tracer), session)
