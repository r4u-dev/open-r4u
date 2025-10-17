from __future__ import annotations

from datetime import datetime, timezone
import functools
import types
from typing import Any, Callable

import httpx

from .tracer import AbstractTracer, PrintTracer, RequestInfo

def _build_request_info(request: httpx.Request) -> RequestInfo:
    return RequestInfo(
        method=request.method.upper(),
        url=str(request.url),
        headers=request.headers,
        request_payload=request.content,
        started_at=datetime.now(timezone.utc)
    )

def _update_request_info(request_info: RequestInfo, response: Any, error: str = None) -> None:
    """
    Common logic for processing request info after request completion.
    """
    completed_at = datetime.now(timezone.utc)
    request_info.status_code = response.status_code if response else None
    request_info.error = error
    request_info.response_size = len(response.content) if response and response.content else None
    request_info.completed_at = completed_at
    
    # Extract response payload
    if response and response.content:
        try:
            # Try to decode as text first
            response_payload = response.text
        except UnicodeDecodeError:
            # If it's binary, just show the size
            response_payload = f"<binary data, {len(response.content)} bytes>"
        request_info.response_payload = response_payload


def _create_async_wrapper(original: Callable, tracer: AbstractTracer):
    @functools.wraps(original)
    async def wrapper(self, *args, **kwargs):
        request_info = _build_request_info(args[0])

        response = None
        error = None
        try:
            response = await original(*args, **kwargs)
            return response
        except Exception as e:
            error = str(e)
            raise
        finally:
            _update_request_info(request_info, response, error)
            tracer.trace_request(request_info)

    return wrapper


def _create_sync_wrapper(original: Callable, tracer: AbstractTracer):

    @functools.wraps(original)
    def wrapper(self, *args, **kwargs):
        request_info = _build_request_info(args[0])

        response = None
        error = None
        try:
            response = original(*args, **kwargs)
            return response
        except Exception as e:
            error = str(e)
            raise
        finally:
            _update_request_info(request_info, response, error)
            tracer.trace_request(request_info)

    return wrapper


def trace_async_client(client: httpx.AsyncClient, tracer: AbstractTracer = None) -> None:
    """
    Trace an asynchronous httpx client.
    """
    client.send = types.MethodType(_create_async_wrapper(client.send, tracer or PrintTracer()), client)


def trace_client(client: httpx.Client, tracer: AbstractTracer = None) -> None:
    """
    Trace a synchronous httpx client.
    """
    client.send = types.MethodType(_create_sync_wrapper(client.send, tracer or PrintTracer()), client)