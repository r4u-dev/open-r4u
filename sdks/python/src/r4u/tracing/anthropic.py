"""Anthropic integration for R4U observability."""

from anthropic import Anthropic as OriginalAnthropic
from anthropic import AsyncAnthropic as OriginalAsyncAnthropic

from .http.httpx import trace_async_client, trace_client


class Anthropic(OriginalAnthropic):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        trace_client(self._client, "anthropic")


class AsyncAnthropic(OriginalAsyncAnthropic):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        trace_async_client(self._client, "anthropic")
