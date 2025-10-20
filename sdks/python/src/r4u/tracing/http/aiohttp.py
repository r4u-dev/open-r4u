from __future__ import annotations

from datetime import datetime, timezone
import functools
import types
from typing import Callable

import aiohttp

from r4u.client import HTTPTrace
from .tracer import AbstractTracer, PrintTracer


def _create_async_wrapper(original: Callable, tracer: AbstractTracer):
    """Create wrapper for aiohttp session methods like _request."""
    @functools.wraps(original)
    async def wrapper(self, *args, **kwargs):
        # Extract method and url from args/kwargs for aiohttp session methods
        method = args[0] if len(args) > 0 else kwargs.get('method', 'GET')
        url = args[1] if len(args) > 1 else kwargs.get('url')
        
        started_at = datetime.now(timezone.utc)
        request_payload = kwargs.get('data') or kwargs.get('json') or b""
        if isinstance(request_payload, str):
            request_payload = request_payload.encode('utf-8')
        elif not isinstance(request_payload, bytes):
            request_payload = b""

        trace_ctx = {
            "method": str(method).upper(),
            "url": str(url),
            "started_at": started_at,
            "request_bytes": request_payload,
            "request_headers": dict(kwargs.get('headers', {})),
        }

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
            status_code = response.status if response else 0
            response_headers = dict(response.headers) if response else {}
            response_bytes = await response.read() if response else b""

            trace = HTTPTrace(
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

            tracer.trace_request(trace)

    return wrapper

def trace_async_client(session: aiohttp.ClientSession, tracer: AbstractTracer = None) -> None:
    """
    Trace an aiohttp ClientSession.

    This wraps the _request method which is the core method used by all HTTP methods.
    """
    # Check if already patched to avoid double-patching
    if hasattr(session._request, '_r4u_patched'):
        return

    tracer = tracer or PrintTracer()
    wrapper = _create_async_wrapper(session._request, tracer)
    wrapper._r4u_patched = True  # Mark as patched
    session._request = types.MethodType(wrapper, session)
