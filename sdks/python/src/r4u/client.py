"""R4U HTTP client for creating traces."""

import os
import queue
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List, Optional

import httpx
import atexit
from time import sleep
from pydantic import BaseModel, ConfigDict, Field


class HTTPTrace(BaseModel):
    """Schema for HTTP trace creation (provider-agnostic)."""

    # Request identification
    url: str = Field(..., description="The request URL")
    method: str = Field(..., description="The HTTP method (GET, POST, etc.)")

    # Timing
    started_at: datetime = Field(..., description="When the request started")
    completed_at: datetime = Field(..., description="When the request completed")

    # Status
    status_code: int = Field(..., description="HTTP status code")
    error: Optional[str] = Field(None, description="Error message if any")

    # Raw data
    request: bytes = Field(..., description="Complete raw request bytes (raw or JSON)")
    request_headers: Dict[str, str] = Field(
        ..., description="Complete raw request headers"
    )
    response: bytes = Field(
        ..., description="Complete raw response bytes (raw or JSON)"
    )
    response_headers: Dict[str, str] = Field(
        ..., description="Complete raw response headers"
    )

    # Optional extracted fields for convenience
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    model_config = ConfigDict(extra="allow")


class AbstractTracer(ABC):
    """Abstract base class for HTTP request tracing."""

    @abstractmethod
    def log(self, trace: HTTPTrace) -> None:
        """Log a trace entry

        Args:
            trace: HTTP trace to log.
        """
        raise NotImplementedError


class ConsoleTracer(AbstractTracer):
    """Tracer for printing HTTP traces to the console."""

    def log(self, trace: HTTPTrace) -> None:
        """Log a trace entry.

        Args:
            trace: HTTP trace to log.
        """
        print(trace.model_dump_json(indent=2))


class R4UClient(AbstractTracer):
    """Tracer for logging HTTP traces on R4U Server."""

    def __init__(
        self,
        api_url: str = "http://localhost:8000",
        timeout: float = 30.0,
    ):
        """Initialize the R4U tracer.

        Args:
            api_url: Base URL for the R4U Server
            timeout: HTTP request timeout in seconds
        """
        self.api_url = api_url.rstrip("/")
        self._sync_client = httpx.Client(base_url=self.api_url, timeout=timeout)

        # Queue-based processing
        self._trace_queue: queue.Queue = queue.Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_worker = threading.Event()
        self._start_worker_thread()
        atexit.register(self.close)

    def log(self, trace: HTTPTrace) -> None:
        """Log a trace entry.

        Args:
            trace: HTTP trace to log.
        """
        self._trace_queue.put(trace)

    def _start_worker_thread(self) -> None:
        """Start the worker thread for processing trace queue."""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._stop_worker.clear()
            self._worker_thread = threading.Thread(
                target=self._worker_loop, daemon=True
            )
            self._worker_thread.start()

    def _worker_loop(self) -> None:
        """Worker thread loop that processes trace queue every 5 seconds."""
        while not self._stop_worker.is_set():
            try:
                # Collect all traces in queue
                traces_to_send = []
                while True:
                    try:
                        trace = self._trace_queue.get_nowait()
                        traces_to_send.append(trace)
                    except queue.Empty:
                        break

                # Send all traces if any exist
                if traces_to_send:
                    self._send_traces_batch(traces_to_send)

                # Wait 1 seconds or until stop event is set
                self._stop_worker.wait(1.0)
            except Exception as e:
                # Log error but continue processing
                print(f"Error in worker thread: {e}")

    def _send_traces_batch(self, traces: List[HTTPTrace]) -> None:
        """Send a batch of traces to the server.

        Args:
            traces: List of traces to send.
        """
        for trace in traces:
            try:
                self._sync_client.post(
                    f"{self.api_url}/http-traces",
                    json=trace.model_dump(mode="json", by_alias=True),
                    headers={"Content-Type": "application/json"},
                ).raise_for_status()
            except Exception as e:
                # Log error but continue processing other traces
                print(f"Error sending trace: {e}")

    def stop_worker(self) -> None:
        """Stop the worker thread."""
        self._stop_worker.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)

    def close(self):
        """Close HTTP clients and stop worker thread."""
        sleep(1)
        self.stop_worker()
        if self._sync_client:
            self._sync_client.close()

    def __del__(self):
        """Cleanup on deletion."""
        self.stop_worker()
        if self._sync_client:
            self._sync_client.close()


@lru_cache(maxsize=1)
def get_r4u_client() -> AbstractTracer:
    """Get the R4U client."""

    return R4UClient(
        api_url=os.getenv("R4U_API_URL", "http://localhost:8000"),
        timeout=float(os.getenv("R4U_TIMEOUT", "30.0")),
    )
