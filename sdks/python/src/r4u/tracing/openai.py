"""OpenAI integration for R4U observability."""

from openai import AsyncOpenAI as OriginalAsyncOpenAI
from openai import OpenAI as OriginalOpenAI

from .http.httpx import trace_async_client, trace_client


class OpenAI(OriginalOpenAI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        trace_client(self._client, "openai")


class AsyncOpenAI(OriginalAsyncOpenAI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        trace_async_client(self._client, "openai")
