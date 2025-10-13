"""R4U HTTP client for creating traces."""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import httpx
from pydantic import BaseModel


class MessageCreate(BaseModel):
    """Schema for creating a message."""
    role: str
    content: str


class TraceCreate(BaseModel):
    """Schema for trace creation payload."""
    model: str
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: datetime
    completed_at: datetime
    messages: List[MessageCreate]


class TraceRead(BaseModel):
    """Schema for trace responses."""
    id: int
    model: str
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: datetime
    completed_at: datetime
    messages: List[Dict[str, Any]]


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
        messages: List[Dict[str, str]],
        result: Optional[str] = None,
        error: Optional[str] = None,
        started_at: Optional[Union[datetime, str]] = None,
        completed_at: Optional[Union[datetime, str]] = None,
    ) -> TraceRead:
        """Create a trace asynchronously.
        
        Args:
            model: Model name used for the LLM call
            messages: List of messages in the conversation
            result: Result content from the LLM
            error: Error message if the call failed
            started_at: When the call started
            completed_at: When the call completed
            
        Returns:
            The created trace
        """
        if started_at is None:
            started_at = datetime.utcnow()
        if completed_at is None:
            completed_at = datetime.utcnow()
            
        # Convert string timestamps to datetime if needed
        if isinstance(started_at, str):
            started_at = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        if isinstance(completed_at, str):
            completed_at = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))

        trace_data = TraceCreate(
            model=model,
            result=result,
            error=error,
            started_at=started_at,
            completed_at=completed_at,
            messages=[MessageCreate(role=msg["role"], content=msg["content"]) for msg in messages]
        )

        response = await self.async_client.post(
            f"{self.api_url}/traces",
            json=trace_data.model_dump(mode="json"),
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        
        return TraceRead(**response.json())

    def create_trace(
        self,
        model: str,
        messages: List[Dict[str, str]],
        result: Optional[str] = None,
        error: Optional[str] = None,
        started_at: Optional[Union[datetime, str]] = None,
        completed_at: Optional[Union[datetime, str]] = None,
    ) -> TraceRead:
        """Create a trace synchronously.
        
        Args:
            model: Model name used for the LLM call
            messages: List of messages in the conversation
            result: Result content from the LLM
            error: Error message if the call failed
            started_at: When the call started
            completed_at: When the call completed
            
        Returns:
            The created trace
        """
        if started_at is None:
            started_at = datetime.utcnow()
        if completed_at is None:
            completed_at = datetime.utcnow()
            
        # Convert string timestamps to datetime if needed
        if isinstance(started_at, str):
            started_at = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        if isinstance(completed_at, str):
            completed_at = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))

        trace_data = TraceCreate(
            model=model,
            result=result,
            error=error,
            started_at=started_at,
            completed_at=completed_at,
            messages=[MessageCreate(role=msg["role"], content=msg["content"]) for msg in messages]
        )

        response = self.sync_client.post(
            f"{self.api_url}/traces",
            json=trace_data.model_dump(mode="json"),
            headers={"Content-Type": "application/json"}
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