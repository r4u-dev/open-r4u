"""LangChain integration for R4U observability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Type, Union, cast
from uuid import UUID

from ..client import R4UClient
from ..utils import extract_call_path

_BaseHandlerProto: Type[Any]
_AsyncHandlerProto: Type[Any]

try:  # pragma: no cover - import guards
    from langchain_core.callbacks.base import (  # type: ignore
        AsyncCallbackHandler as _CoreAsyncCallbackHandler,
        BaseCallbackHandler as _CoreBaseCallbackHandler,
    )
    _LANGCHAIN_AVAILABLE = True
    _BaseHandlerProto = _CoreBaseCallbackHandler  # type: ignore[assignment]
    _AsyncHandlerProto = _CoreAsyncCallbackHandler  # type: ignore[assignment]
except Exception:  # pragma: no cover - fallback for legacy langchain
    try:
        from langchain.callbacks.base import (  # type: ignore
            AsyncCallbackHandler as _LegacyAsyncCallbackHandler,  # type: ignore[attr-defined]
            BaseCallbackHandler as _LegacyBaseCallbackHandler,
        )
        _LANGCHAIN_AVAILABLE = True
        _BaseHandlerProto = _LegacyBaseCallbackHandler  # type: ignore[assignment]
        _AsyncHandlerProto = _LegacyAsyncCallbackHandler  # type: ignore[assignment]
    except Exception:  # pragma: no cover - handled in class initialisers
        _BaseHandlerProto = object  # type: ignore[assignment]
        _AsyncHandlerProto = object  # type: ignore[assignment]
        _LANGCHAIN_AVAILABLE = False

_ASYNC_SUPPORTED = _LANGCHAIN_AVAILABLE and _AsyncHandlerProto is not object
_BaseHandler = cast(Type[Any], _BaseHandlerProto)
_AsyncHandler = cast(Type[Any], _AsyncHandlerProto)


@dataclass
class _RunState:
    """Mutable state captured for a single LangChain LLM run."""

    model: str
    messages: List[Dict[str, str]]
    started_at: datetime
    path: Optional[str]


def _normalise_messages(prompts: Sequence[Any]) -> List[Dict[str, str]]:
    """Convert LangChain prompt inputs to R4U message dictionaries."""

    if not prompts:
        return []

    # LangChain batches prompts, so focus on the first input
    primary = prompts[0]

    def _coerce(obj: Any) -> Iterable[Dict[str, str]]:
        if obj is None:
            return []
        if isinstance(obj, str):
            return [{"role": "user", "content": obj}]
        if isinstance(obj, dict):
            role = obj.get("role") or obj.get("type") or "user"
            content = obj.get("content") or obj.get("text") or str(obj)
            return [{"role": role, "content": str(content)}]
        if isinstance(obj, (list, tuple)):
            messages: List[Dict[str, str]] = []
            for item in obj:
                messages.extend(list(_coerce(item)))
            return messages

        role = getattr(obj, "role", None) or getattr(obj, "type", None) or "user"
        content = getattr(obj, "content", None)
        if isinstance(content, (list, tuple)):
            # Join multi-part message content
            content = " ".join(str(part) for part in content)
        if content is None:
            content = getattr(obj, "text", str(obj))
        return [{"role": str(role), "content": str(content)}]

    return list(_coerce(primary))


def _extract_model_name(serialised: Dict[str, Any], **kwargs: Any) -> str:
    """Determine the model name from LangChain metadata."""

    invocation_params = kwargs.get("invocation_params") or {}
    model = (
        invocation_params.get("model")
        or kwargs.get("model_name")
        or serialised.get("id")
        or serialised.get("name")
        or serialised.get("model")
        or serialised.get("class")
    )
    return str(model) if model else "unknown"


def _extract_result_text(result: Any) -> Optional[str]:
    """Pull a human-readable result string from LangChain outputs."""

    if result is None:
        return None

    generations = getattr(result, "generations", None)
    if generations:
        first_generation = generations[0][0] if generations[0] else None
        if first_generation is not None:
            message = getattr(first_generation, "message", None)
            if message is not None and hasattr(message, "content"):
                content = message.content
                if isinstance(content, (list, tuple)):
                    return " ".join(str(part) for part in content)
                return str(content)
            text = getattr(first_generation, "text", None)
            if text is not None:
                return str(text)

    if hasattr(result, "output_text"):
        return str(result.output_text)

    if hasattr(result, "content"):
        content = result.content
        if isinstance(content, (list, tuple)):
            return " ".join(str(part) for part in content)
        return str(content)

    if isinstance(result, str):
        return result

    # Fallback to repr to avoid raising errors
    return repr(result)


class _LangChainCallbackMixin:
    """Shared behaviour for sync and async LangChain callback handlers."""

    def __init__(
        self,
        *,
        r4u_client: Optional[R4UClient] = None,
        api_url: str = "http://localhost:8000",
        timeout: float = 30.0,
    ) -> None:
        self._client = r4u_client or R4UClient(api_url=api_url, timeout=timeout)
        self._runs: Dict[str, _RunState] = {}

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------
    def _start_run(
        self,
        serialised: Dict[str, Any],
        prompts: Sequence[Any],
        run_id: Union[str, UUID],
        **kwargs: Any,
    ) -> None:
        call_path, _ = extract_call_path(max_depth=100)
        run_state = _RunState(
            model=_extract_model_name(serialised, **kwargs),
            messages=_normalise_messages(prompts),
            started_at=datetime.utcnow(),
            path=call_path,
        )
        self._runs[str(run_id)] = run_state

    def _pop_run_state(self, run_id: Union[str, UUID]) -> Optional[_RunState]:
        return self._runs.pop(str(run_id), None)

    def _build_trace_payload(
        self,
        *,
        run_state: _RunState,
        result: Optional[Any] = None,
        error: Optional[BaseException] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": run_state.model,
            "messages": run_state.messages,
            "started_at": run_state.started_at,
            "completed_at": datetime.utcnow(),
            "path": run_state.path,
        }
        if error is not None:
            payload["error"] = str(error)
        else:
            payload["result"] = _extract_result_text(result)
        return payload

    def _safe_trace_sync(self, payload: Dict[str, Any]) -> None:
        try:
            self._client.create_trace(**payload)
        except Exception as exc:  # pragma: no cover - network failures
            print(f"Failed to create LangChain trace: {exc}")

    async def _safe_trace_async(self, payload: Dict[str, Any]) -> None:
        try:
            await self._client.create_trace_async(**payload)
        except Exception as exc:  # pragma: no cover - network failures
            print(f"Failed to create LangChain trace: {exc}")


if _LANGCHAIN_AVAILABLE:

    class R4ULangChainCallbackHandler(_LangChainCallbackMixin, _BaseHandler):
        """Synchronous LangChain callback handler that emits R4U traces."""

        def __init__(
            self,
            *,
            r4u_client: Optional[R4UClient] = None,
            api_url: str = "http://localhost:8000",
            timeout: float = 30.0,
        ) -> None:
            super().__init__(r4u_client=r4u_client, api_url=api_url, timeout=timeout)

        def on_llm_start(
            self,
            serialized: Dict[str, Any],
            prompts: Sequence[Any],
            *,
            run_id: Union[str, UUID],
            parent_run_id: Optional[Union[str, UUID]] = None,
            **kwargs: Any,
        ) -> None:
            self._start_run(serialized, prompts, run_id, **kwargs)

        def on_llm_end(
            self,
            response: Any,
            *,
            run_id: Union[str, UUID],
            parent_run_id: Optional[Union[str, UUID]] = None,
            **kwargs: Any,
        ) -> None:
            run_state = self._pop_run_state(run_id)
            if run_state is None:
                return
            payload = self._build_trace_payload(run_state=run_state, result=response)
            self._safe_trace_sync(payload)

        def on_llm_error(
            self,
            error: BaseException,
            *,
            run_id: Union[str, UUID],
            parent_run_id: Optional[Union[str, UUID]] = None,
            **kwargs: Any,
        ) -> None:
            run_state = self._pop_run_state(run_id)
            if run_state is None:
                return
            payload = self._build_trace_payload(run_state=run_state, error=error)
            self._safe_trace_sync(payload)


    if _ASYNC_SUPPORTED:

        class R4UAsyncLangChainCallbackHandler(_LangChainCallbackMixin, _AsyncHandler):
            """Asynchronous LangChain callback handler that emits R4U traces."""

            def __init__(
                self,
                *,
                r4u_client: Optional[R4UClient] = None,
                api_url: str = "http://localhost:8000",
                timeout: float = 30.0,
            ) -> None:
                super().__init__(r4u_client=r4u_client, api_url=api_url, timeout=timeout)

            async def on_llm_start(
                self,
                serialized: Dict[str, Any],
                prompts: Sequence[Any],
                *,
                run_id: Union[str, UUID],
                parent_run_id: Optional[Union[str, UUID]] = None,
                **kwargs: Any,
            ) -> None:
                self._start_run(serialized, prompts, run_id, **kwargs)

            async def on_llm_end(
                self,
                response: Any,
                *,
                run_id: Union[str, UUID],
                parent_run_id: Optional[Union[str, UUID]] = None,
                **kwargs: Any,
            ) -> None:
                run_state = self._pop_run_state(run_id)
                if run_state is None:
                    return
                payload = self._build_trace_payload(run_state=run_state, result=response)
                await self._safe_trace_async(payload)

            async def on_llm_error(
                self,
                error: BaseException,
                *,
                run_id: Union[str, UUID],
                parent_run_id: Optional[Union[str, UUID]] = None,
                **kwargs: Any,
            ) -> None:
                run_state = self._pop_run_state(run_id)
                if run_state is None:
                    return
                payload = self._build_trace_payload(run_state=run_state, error=error)
                await self._safe_trace_async(payload)

    else:  # pragma: no cover - exercised when async callbacks unavailable

        class _AsyncUnavailableHandler:
            """Placeholder async handler when LangChain lacks async callbacks."""

            def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401
                raise ImportError(
                    "LangChain async callbacks are unavailable. Upgrade LangChain to use async tracing."
                )

        R4UAsyncLangChainCallbackHandler = _AsyncUnavailableHandler  # type: ignore[assignment]


else:  # pragma: no cover - exercised when LangChain is absent

    class _MissingLangChainCallbackHandler:
        """Placeholder that raises a helpful error when LangChain is missing."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401
            raise ImportError(
                "LangChain is not installed. Install 'langchain' or 'langchain-core' to use the R4U LangChain integration."
            )

    R4ULangChainCallbackHandler = _MissingLangChainCallbackHandler  # type: ignore[assignment]
    R4UAsyncLangChainCallbackHandler = _MissingLangChainCallbackHandler  # type: ignore[assignment]


def wrap_langchain(
    runnable: Any,
    *,
    r4u_client: Optional[R4UClient] = None,
    api_url: str = "http://localhost:8000",
    timeout: float = 30.0,
) -> Any:
    """Attach R4U tracing callbacks to a LangChain runnable or LLM.

    Args:
        runnable: Any LangChain runnable, chain, or model instance supporting callbacks.
        r4u_client: Optional shared R4U client. If omitted a new one is created.
        api_url: Base URL for the R4U API when constructing a client.
        timeout: Timeout in seconds for R4U HTTP calls.

    Returns:
        The runnable configured with R4U callback handlers.

    Raises:
        ImportError: If LangChain is not installed.
        TypeError: If the provided runnable cannot be configured with callbacks.
    """

    if not _LANGCHAIN_AVAILABLE:
        raise ImportError(
            "LangChain is not installed. Install 'langchain' or 'langchain-core' to use the R4U LangChain integration."
        )

    client = r4u_client or R4UClient(api_url=api_url, timeout=timeout)

    handlers: List[Any] = [R4ULangChainCallbackHandler(r4u_client=client)]
    if _ASYNC_SUPPORTED:
        handlers.append(R4UAsyncLangChainCallbackHandler(r4u_client=client))

    configured = None
    if hasattr(runnable, "with_config") and callable(getattr(runnable, "with_config")):
        configured = runnable.with_config(callbacks=handlers)
    elif hasattr(runnable, "callbacks"):
        existing = getattr(runnable, "callbacks", None) or []
        setattr(runnable, "callbacks", [*existing, *handlers])
        configured = runnable

    if configured is None:
        raise TypeError(
            "The provided runnable does not support callback configuration. "
            "Ensure it exposes a 'with_config' method or 'callbacks' attribute."
        )

    setattr(configured, "_r4u_handlers", handlers)
    return configured


__all__ = [
    "R4ULangChainCallbackHandler",
    "R4UAsyncLangChainCallbackHandler",
    "wrap_langchain",
]
