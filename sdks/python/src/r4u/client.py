"""R4U HTTP client for creating traces."""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Union

import httpx
from pydantic import BaseModel, ConfigDict, Field


class ToolFunctionCall(BaseModel):
    """Schema representing a tool function invocation."""

    name: str
    arguments: Any
    model_config = ConfigDict(extra="allow")


class ToolCall(BaseModel):
    """Schema describing an LLM-issued tool call."""

    id: Optional[str] = None
    type: Optional[str] = None
    function: Optional[ToolFunctionCall] = None
    model_config = ConfigDict(extra="allow")


class ToolDefinition(BaseModel):
    """Schema for a tool definition supplied to the LLM."""

    name: str
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = Field(default=None, alias="schema")
    type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    model_config = ConfigDict(extra="allow", populate_by_name=True, serialize_by_alias=True)


class MessageCreate(BaseModel):
    """Schema for creating a message."""

    role: str
    content: Any = None
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    model_config = ConfigDict(extra="allow")


class TraceCreate(BaseModel):
    """Schema for trace creation payload."""

    model: str
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    messages: List[MessageCreate]
    path: Optional[str] = None
    tools: Optional[List[ToolDefinition]] = None
    project: str = "Default Project"


class TraceRead(BaseModel):
    """Schema for trace responses."""

    id: int
    project_id: int
    model: str
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    messages: List[Dict[str, Any]]
    path: Optional[str] = None
    tools: Optional[List[Dict[str, Any]]] = None
    model_config = ConfigDict(from_attributes=True, extra="allow")


class R4UClient:
    """Client for interacting with R4U trace API."""

    def __init__(self, api_url: str = "http://localhost:8000", timeout: float = 30.0):
        """Initialize the R4U client.

        Args:
            api_url: Base URL for the R4U API
            timeout: HTTP request timeout in seconds
        """
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout
        self._async_client: Optional[httpx.AsyncClient] = None
        self._sync_client: Optional[httpx.Client] = None

    @property
    def async_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(timeout=self.timeout)
        return self._async_client

    @property
    def sync_client(self) -> httpx.Client:
        """Get or create sync HTTP client."""
        if self._sync_client is None:
            self._sync_client = httpx.Client(timeout=self.timeout)
        return self._sync_client

    async def create_trace_async(
        self,
        model: str,
        messages: Sequence[Union[MessageCreate, Dict[str, Any]]],
        result: Optional[str] = None,
        error: Optional[str] = None,
        started_at: Optional[Union[datetime, str]] = None,
        completed_at: Optional[Union[datetime, str]] = None,
        path: Optional[str] = None,
        tools: Optional[Sequence[Union[ToolDefinition, Dict[str, Any]]]] = None,
        project: str = "Default Project",
    ) -> TraceRead:
        """Create a trace asynchronously."""
        normalized_started_at, normalized_completed_at = self._normalize_timestamps(
            started_at,
            completed_at,
        )

        trace_data = TraceCreate(
            model=model,
            result=result,
            error=error,
            started_at=normalized_started_at,
            completed_at=normalized_completed_at,
            messages=self._prepare_messages(messages),
            path=path,
            tools=self._prepare_tools(tools),
            project=project,
        )

        response = await self.async_client.post(
            f"{self.api_url}/traces",
            json=trace_data.model_dump(mode="json", by_alias=True),
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()

        return TraceRead(**response.json())

    def create_trace(
        self,
        model: str,
        messages: Sequence[Union[MessageCreate, Dict[str, Any]]],
        result: Optional[str] = None,
        error: Optional[str] = None,
        started_at: Optional[Union[datetime, str]] = None,
        completed_at: Optional[Union[datetime, str]] = None,
        path: Optional[str] = None,
        tools: Optional[Sequence[Union[ToolDefinition, Dict[str, Any]]]] = None,
        project: str = "Default Project",
    ) -> TraceRead:
        """Create a trace synchronously."""
        normalized_started_at, normalized_completed_at = self._normalize_timestamps(
            started_at,
            completed_at,
        )

        trace_data = TraceCreate(
            model=model,
            result=result,
            error=error,
            started_at=normalized_started_at,
            completed_at=normalized_completed_at,
            messages=self._prepare_messages(messages),
            path=path,
            tools=self._prepare_tools(tools),
            project=project,
        )

        response = self.sync_client.post(
            f"{self.api_url}/traces",
            json=trace_data.model_dump(mode="json", by_alias=True),
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()

        return TraceRead(**response.json())

    async def list_traces_async(self) -> List[TraceRead]:
        """List all traces asynchronously."""
        response = await self.async_client.get(f"{self.api_url}/traces")
        response.raise_for_status()
        return [TraceRead(**trace) for trace in response.json()]

    def list_traces(self) -> List[TraceRead]:
        """List all traces synchronously."""
        response = self.sync_client.get(f"{self.api_url}/traces")
        response.raise_for_status()
        return [TraceRead(**trace) for trace in response.json()]

    async def close(self):
        """Close HTTP clients."""
        if self._async_client:
            await self._async_client.aclose()
        if self._sync_client:
            self._sync_client.close()

    def __del__(self):
        """Cleanup on deletion."""
        if self._async_client and not self._async_client.is_closed:
            # Try to close async client if event loop is running
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._async_client.aclose())
            except RuntimeError:
                pass
        if self._sync_client:
            self._sync_client.close()

    @staticmethod
    def _prepare_messages(
        messages: Sequence[Union[MessageCreate, Dict[str, Any]]],
    ) -> List[MessageCreate]:
        """Normalize incoming messages into MessageCreate objects."""
        prepared: List[MessageCreate] = []
        for message in messages:
            if isinstance(message, MessageCreate):
                prepared.append(message)
            else:
                prepared.append(MessageCreate.model_validate(message))
        return prepared

    @staticmethod
    def _prepare_tools(
        tools: Optional[Sequence[Union[ToolDefinition, Dict[str, Any]]]],
    ) -> Optional[List[ToolDefinition]]:
        """Normalize tool definitions for trace creation."""
        if not tools:
            return None

        prepared: List[ToolDefinition] = []
        for tool in tools:
            if isinstance(tool, ToolDefinition):
                prepared.append(tool)
            else:
                prepared.append(ToolDefinition.model_validate(tool))
        return prepared

    @staticmethod
    def _normalize_timestamps(
        started_at: Optional[Union[datetime, str]],
        completed_at: Optional[Union[datetime, str]],
    ) -> tuple[datetime, datetime]:
        """Normalize and default timestamps for trace creation."""
        if started_at is None:
            started = datetime.utcnow()
        else:
            started = R4UClient._coerce_datetime(started_at)

        if completed_at is None:
            completed = datetime.utcnow()
        else:
            completed = R4UClient._coerce_datetime(completed_at)

        return started, completed

    @staticmethod
    def _coerce_datetime(value: Union[datetime, str]) -> datetime:
        """Convert ISO timestamps or datetimes into datetime objects."""
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(value.replace("Z", "+00:00"))