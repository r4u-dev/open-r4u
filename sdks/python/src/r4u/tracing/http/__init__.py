"""HTTP tracing for R4U."""

from .aiohttp import trace_async_client as trace_aiohttp_client
from .httpx import trace_async_client as trace_httpx_async_client
from .httpx import trace_client as trace_httpx_client
from .requests import trace_session as trace_requests_session

__all__ = [
    "trace_aiohttp_client",
    "trace_httpx_async_client",
    "trace_httpx_client",
    "trace_requests_session",
]
