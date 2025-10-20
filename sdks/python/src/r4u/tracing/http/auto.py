"""
Auto-tracing module for HTTP libraries.

This module provides convenient functions to automatically trace all HTTP requests
from various HTTP libraries without requiring manual patching of individual instances.
"""

from contextlib import suppress
from typing import Optional

from r4u.client import AbstractTracer


def trace_all_http(tracer: Optional[AbstractTracer] = None) -> None:
    """
    Enable automatic tracing for all supported HTTP libraries.

    This function monkey patches all supported HTTP libraries to automatically
    trace all HTTP requests made through them.

    Example:
        >>> from r4u.tracing.http.auto import trace_all_http
        >>> trace_all_http()  # Enable tracing for all HTTP libraries
        >>>
        >>> # Now all HTTP requests will be automatically traced
        >>> import httpx
        >>> import requests
        >>> import aiohttp
        >>>
        >>> # All of these will be automatically traced
        >>> httpx_client = httpx.Client()
        >>> requests_session = requests.Session()
        >>> aiohttp_session = aiohttp.ClientSession()
    """
    with suppress(Exception):
        from .httpx import trace_all as trace_httpx_all
        trace_httpx_all(tracer)

    with suppress(Exception):
        from .requests import trace_all as trace_requests_all
        trace_requests_all(tracer)

    with suppress(Exception):
        from .aiohttp import trace_all as trace_aiohttp_all
        trace_aiohttp_all(tracer)


def untrace_all_http() -> None:
    """
    Disable automatic tracing for all supported HTTP libraries.

    This function removes monkey patching from all supported HTTP libraries,
    restoring their original behavior.
    """
    with suppress(Exception):
        from .httpx import untrace_all as untrace_httpx_all
        untrace_httpx_all()

    with suppress(Exception):
        from .requests import untrace_all as untrace_requests_all
        untrace_requests_all()

    with suppress(Exception):
        from .aiohttp import untrace_all as untrace_aiohttp_all
        untrace_aiohttp_all()


# Convenience aliases
trace_all = trace_all_http
untrace_all = untrace_all_http