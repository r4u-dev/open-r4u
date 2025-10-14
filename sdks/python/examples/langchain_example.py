"""LangChain example that sends traces through the R4U integration.

This sample shows how to wrap a LangChain runnable (``ChatOpenAI``) with
``wrap_langchain`` so every invocation automatically creates a trace in the
R4U backend.

Usage:
    export OPENAI_API_KEY="sk-your-key"
    python examples/langchain_openai.py

The example assumes the R4U API is reachable at http://localhost:8000. Adjust
``API_URL`` below to point to your deployment.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from langchain_openai import ChatOpenAI

from r4u.integrations.langchain import wrap_langchain

API_URL = os.getenv("R4U_API_URL", "http://localhost:8000")
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def build_chain() -> Any:
    """Construct the LangChain runnable to wrap with R4U tracing."""

    llm = ChatOpenAI(model=MODEL_NAME)
    return wrap_langchain(llm, api_url=API_URL)


def run_sync() -> None:
    """Run a synchronous invocation to demonstrate tracing."""

    chain = build_chain()
    prompt = "Summarise the benefits of observability for LLM applications in one sentence."
    response = chain.invoke(prompt)
    print("Sync response:\n", response)


async def run_async() -> None:
    """Run an asynchronous invocation to demonstrate async tracing."""

    chain = build_chain()
    prompt = "What is the meaning of life, the universe, and everything?"
    response = await chain.ainvoke(prompt)
    print("Async response:\n", response)


if __name__ == "__main__":
    run_sync()
    asyncio.run(run_async())
