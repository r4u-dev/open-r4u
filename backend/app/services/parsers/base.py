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
    ) -> TraceCreate:
        """Parse HTTP request/response into a TraceCreate object.
        
        Args:
            request_body: Parsed JSON request body
            response_body: Parsed JSON response body
            started_at: When the request started
            completed_at: When the request completed
            error: Error message if any
            metadata: Additional metadata
            
        Returns:
            TraceCreate object ready for database insertion

        """
