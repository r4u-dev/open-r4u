"""Abstract tracer for HTTP request tracing."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from r4u.client import AbstractClient, HTTPTrace


class AbstractTracer(ABC):
    """Abstract base class for HTTP request tracers."""
    
    @abstractmethod
    def trace_request(self, trace: HTTPTrace) -> None:
        """Trace a complete HTTP request with all details.
        
        Args:
            trace: Complete HTTPTrace record including timings, headers and payloads.
        """
        pass


class UniversalTracer(AbstractTracer):
    """Universal tracer that captures raw request/response data."""
    
    def __init__(self, r4u_client: AbstractClient, provider: str):
        """Initialize the universal tracer.
        
        Args:
            r4u_client: R4U HTTP client for creating traces
        """
        self._r4u_client = r4u_client
        self._provider = provider
    
    def trace_request(self, trace: HTTPTrace) -> None:
        """Forward finalized HTTPTrace to the R4U client."""

        trace.metadata["provider"] = self._provider
        try:
            self._r4u_client.send(trace)
        except Exception as error:
            # Log error but don't fail the request
            print(f"Failed to create HTTP trace: {error}")
    


class PrintTracer(AbstractTracer):
    """Simple tracer that prints request information to stdout."""
    
    def trace_request(self, trace: HTTPTrace) -> None:
        """Print request information."""
        # Derive elapsed from timestamps
        elapsed_ms: Optional[float] = None
        try:
            elapsed_ms = (trace.completed_at - trace.started_at).total_seconds() * 1000
        except Exception:
            elapsed_ms = None
        elapsed_str = f"{elapsed_ms:.2f}ms" if elapsed_ms is not None else "unknown"

        method = trace.metadata.get("method") if isinstance(trace.metadata, dict) else None
        url = trace.metadata.get("url") if isinstance(trace.metadata, dict) else None

        if trace.error:
            if method and url:
                print(f"{method} {url} failed: {trace.error}")
            else:
                print(f"{trace.endpoint} failed: {trace.error}")
        else:
            print("--------------------------------")    
            if method and url:
                print(f"{method} {url} -> {trace.status_code} ({elapsed_str})")
            else:
                print(f"{trace.endpoint} -> {trace.status_code} ({elapsed_str})")
            print(f"Request payload: {trace.request}")
            print(f"Response payload: {trace.response}")
