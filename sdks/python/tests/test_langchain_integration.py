"""Tests for the LangChain integration helpers."""

from __future__ import annotations

import importlib
import sys
import types
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def langchain_module(monkeypatch: pytest.MonkeyPatch):
    """Provide the langchain integration module with stubbed LangChain deps."""

    # Create stub modules for langchain_core callbacks
    base_module = types.ModuleType("langchain_core.callbacks.base")

    class BaseCallbackHandler:  # pragma: no cover - structural stub
        pass

    class AsyncCallbackHandler(BaseCallbackHandler):  # pragma: no cover - structural stub
        pass

    setattr(base_module, "BaseCallbackHandler", BaseCallbackHandler)
    setattr(base_module, "AsyncCallbackHandler", AsyncCallbackHandler)

    callbacks_module = types.ModuleType("langchain_core.callbacks")
    setattr(callbacks_module, "base", base_module)

    core_module = types.ModuleType("langchain_core")
    setattr(core_module, "callbacks", callbacks_module)

    monkeypatch.setitem(sys.modules, "langchain_core", core_module)
    monkeypatch.setitem(sys.modules, "langchain_core.callbacks", callbacks_module)
    monkeypatch.setitem(sys.modules, "langchain_core.callbacks.base", base_module)

    # Ensure we start from a clean import state
    if "r4u.integrations.langchain" in sys.modules:
        del sys.modules["r4u.integrations.langchain"]

    module = importlib.import_module("r4u.integrations.langchain")
    return module


def _first_call_kwargs(mock_client: MagicMock) -> Dict[str, Any]:
    assert mock_client.create_trace.called, "Expected create_trace to be called"
    return mock_client.create_trace.call_args.kwargs


def test_sync_handler_creates_trace_on_success(langchain_module, monkeypatch):
    client = MagicMock()
    handler = langchain_module.R4ULangChainCallbackHandler(r4u_client=client)

    monkeypatch.setattr(langchain_module, "extract_call_path", lambda max_depth=50: ("test_path", 10))

    run_id = "sync-run"
    handler.on_llm_start({"id": "gpt-test"}, ["hello"], run_id=run_id)

    result = SimpleNamespace(generations=[[SimpleNamespace(text="Hi there!")]])
    handler.on_llm_end(result, run_id=run_id)

    payload = _first_call_kwargs(client)
    assert payload["model"] == "gpt-test"
    assert payload["messages"] == [{"role": "user", "content": "hello"}]
    assert payload["result"] == "Hi there!"
    assert payload["path"] == "test_path"
    assert isinstance(payload["started_at"], datetime)
    assert isinstance(payload["completed_at"], datetime)
    assert "error" not in payload


def test_sync_handler_captures_errors(langchain_module, monkeypatch):
    client = MagicMock()
    handler = langchain_module.R4ULangChainCallbackHandler(r4u_client=client)

    monkeypatch.setattr(langchain_module, "extract_call_path", lambda max_depth=50: ("err_path", 42))

    run_id = "error-run"
    handler.on_llm_start({}, ["prompt"], run_id=run_id)
    handler.on_llm_error(RuntimeError("boom"), run_id=run_id)

    payload = _first_call_kwargs(client)
    assert payload["path"] == "err_path"
    assert payload["error"] == "boom"
    assert "result" not in payload


@pytest.mark.asyncio
async def test_async_handler_creates_trace(langchain_module, monkeypatch):
    calls: List[Dict[str, Any]] = []

    class AsyncClient:
        async def create_trace_async(self, **kwargs: Any) -> None:
            calls.append(kwargs)

    handler = langchain_module.R4UAsyncLangChainCallbackHandler(r4u_client=AsyncClient())

    monkeypatch.setattr(langchain_module, "extract_call_path", lambda max_depth=50: ("async_path", 99))

    run_id = "async-run"
    await handler.on_llm_start({"name": "gpt-async"}, [[{"role": "user", "content": "hi"}]], run_id=run_id)

    message = SimpleNamespace(content="Hello async!")
    generation = SimpleNamespace(message=message)
    result = SimpleNamespace(generations=[[generation]])
    await handler.on_llm_end(result, run_id=run_id)

    assert len(calls) == 1
    payload = calls[0]
    assert payload["model"] == "gpt-async"
    assert payload["result"] == "Hello async!"
    assert payload["path"] == "async_path"
    assert payload["messages"] == [{"role": "user", "content": "hi"}]


def test_wrap_langchain_attaches_callbacks(langchain_module, monkeypatch):
    sync_handler = MagicMock(name="sync_handler")
    async_handler = MagicMock(name="async_handler")

    monkeypatch.setattr(langchain_module, "R4ULangChainCallbackHandler", MagicMock(return_value=sync_handler))
    monkeypatch.setattr(langchain_module, "R4UAsyncLangChainCallbackHandler", MagicMock(return_value=async_handler))

    class DummyRunnable:
        def __init__(self) -> None:
            self.callbacks: List[Any] = []

        def with_config(self, *, callbacks: List[Any], **_: Any) -> "DummyRunnable":
            self.callbacks = callbacks
            return self

    runnable = DummyRunnable()
    wrapped = langchain_module.wrap_langchain(runnable, r4u_client=MagicMock())

    assert wrapped is runnable
    assert runnable.callbacks == [sync_handler, async_handler]
    assert getattr(wrapped, "_r4u_handlers") == [sync_handler, async_handler]