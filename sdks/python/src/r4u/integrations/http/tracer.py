"""Abstract tracer for HTTP request tracing."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional


@dataclass
class RequestInfo:
    """Information about an HTTP request for tracing."""
    
    method: str
    url: str
    
    # Request details
    headers: Optional[Dict[str, str]] = None
    request_payload: Optional[str] = None
    request_size: Optional[int] = None
    
    # Response details
    status_code: Optional[int] = None
    response_payload: Optional[str] = None
    response_size: Optional[int] = None
    error: Optional[str] = None
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Set default values after initialization."""
        if self.headers is None:
            self.headers = {}


class AbstractTracer(ABC):
    """Abstract base class for HTTP request tracers."""
    
    @abstractmethod
    def trace_request(self, request_info: RequestInfo) -> None:
        """Trace a complete HTTP request with all details.
        
        Args:
            request_info: Complete request information including method, URL, status, timing, etc.
        """
        pass


class PrintTracer(AbstractTracer):
    """Simple tracer that prints request information to stdout."""
    
    def trace_request(self, request_info: RequestInfo) -> None:
        """Print request information."""
        if request_info.error:
            print(f"{request_info.method} {request_info.url} failed: {request_info.error}")
        else:
            # Calculate elapsed time from timestamps if both are available
            if request_info.started_at and request_info.completed_at:
                elapsed = (request_info.completed_at - request_info.started_at).total_seconds() * 1000
                elapsed_str = f"{elapsed:.2f}ms"
            else:
                elapsed_str = "unknown"

            print("--------------------------------")    
            print(f"{request_info.method} {request_info.url} -> {request_info.status_code} ({elapsed_str})")
            print(f"Request payload: {request_info.request_payload}")
            print(f"Response payload: {request_info.response_payload}")
