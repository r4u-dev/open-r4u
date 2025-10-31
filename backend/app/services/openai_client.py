from functools import lru_cache

from openai import AsyncClient, Client


@lru_cache
def get_openai_client() -> Client:
    """Get a cached instance of the OpenAI Client."""
    return Client()


@lru_cache
def get_async_openai_client() -> AsyncClient:
    """Get a cached instance of the OpenAI AsyncClient."""
    return AsyncClient()
