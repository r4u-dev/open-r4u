"""Base class for provider-specific parsers."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from app.schemas.traces import TraceCreate


class ProviderParser(ABC):
    """Abstract base class for provider-specific parsers."""

    @abstractmethod
    def can_parse(self, url: str) -> bool:
        """Check if this parser can handle the given URL.

        Args:
            url: The API endpoint URL from the request

        Returns:
            True if this parser can handle the URL, False otherwise

        """

    @abstractmethod
    def parse(
        self,
        request_body: dict[str, Any],
        response_body: dict[str, Any],
        started_at: datetime,
        completed_at: datetime,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
        call_path: str | None = None,
        is_streaming: bool = False,
        streaming_response: str | None = None,
        request_path: str | None = None,
    ) -> TraceCreate:
        """Parse HTTP request/response into a TraceCreate object.

        Args:
            project_id: Project ID
            request_body: Parsed JSON request body
            response_body: Parsed JSON response body
            started_at: When the request started
            completed_at: When the request completed
            error: Error message if any
            metadata: Additional metadata
            call_path: The call path where the request was made
            is_streaming: Whether this is a streaming response
            streaming_response: Raw streaming response (SSE format) if is_streaming is True

        Returns:
            TraceCreate object ready for database insertion

        """
