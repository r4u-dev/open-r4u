"""HTTP trace parser service for different LLM providers."""

import json
from datetime import datetime
from typing import Any

from app.schemas.traces import TraceCreate
from app.services.parsers import (
    AnthropicParser,
    GoogleGenAIParser,
    OpenAIParser,
    ProviderParser,
)


class HTTPTraceParserService:
    """Service for parsing HTTP traces from different providers."""

    def __init__(self):
        """Initialize the parser service with all available parsers."""
        self.parsers: list[ProviderParser] = [
            OpenAIParser(),
            AnthropicParser(),
            GoogleGenAIParser(),
        ]

    def _extract_error_from_response(
        self,
        response_body: dict[str, Any],
        parser: ProviderParser,
    ) -> str | None:
        """Extract error message from response body based on provider format.

        Args:
            response_body: Parsed response body
            parser: The provider parser being used

        Returns:
            Error message string if found, None otherwise

        """
        if not response_body:
            return None

        # OpenAI format: {"error": {"message": "...", "type": "...", "code": "..."}}
        if isinstance(parser, OpenAIParser):
            error_obj = response_body.get("error")
            if error_obj and isinstance(error_obj, dict):
                message = error_obj.get("message", "")
                error_type = error_obj.get("type", "")
                code = error_obj.get("code", "")
                parts = [p for p in [error_type, code, message] if p]
                return ": ".join(parts) if parts else None

        # Anthropic format: {"type": "error", "error": {"type": "...", "message": "..."}}
        elif isinstance(parser, AnthropicParser):
            error_obj = response_body.get("error")
            if error_obj and isinstance(error_obj, dict):
                message = error_obj.get("message", "")
                error_type = error_obj.get("type", "")
                parts = [p for p in [error_type, message] if p]
                return ": ".join(parts) if parts else None

        # Google format: {"error": {"code": 400, "message": "...", "status": "..."}}
        elif isinstance(parser, GoogleGenAIParser):
            error_obj = response_body.get("error")
            if error_obj and isinstance(error_obj, dict):
                message = error_obj.get("message", "")
                status = error_obj.get("status", "")
                parts = [p for p in [status, message] if p]
                return ": ".join(parts) if parts else None

        return None

    def parse_http_trace(
        self,
        request: bytes | str,
        request_headers: dict[str, str],
        response: bytes | str,
        response_headers: dict[str, str],
        started_at: datetime,
        completed_at: datetime,
        status_code: int,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
        call_path: str | None = None,
    ) -> TraceCreate:
        """Parse HTTP trace into a TraceCreate object.

        Args:
            request: Raw request as bytes or string
            request_headers: Request headers
            response: Raw response as bytes or string
            response_headers: Response headers
            started_at: When the request started
            completed_at: When the request completed
            status_code: HTTP status code
            error: Error message if any
            metadata: Additional metadata
            call_path: The call path where the request was made

        Returns:
            TraceCreate object ready for database insertion

        Raises:
            ValueError: If unable to parse the trace or determine the provider

        """
        # Convert bytes to strings if needed
        request_str = (
            request.decode("utf-8", errors="replace")
            if isinstance(request, bytes)
            else request
        )
        response_str = (
            response.decode("utf-8", errors="replace")
            if isinstance(response, bytes)
            else response
        )
        # Extract URL from request headers or reconstruct from request
        # For now, we'll try to get it from metadata or request path
        url = metadata.get("url", "") if metadata else ""

        # If URL is not in metadata, try to parse it from the request
        if not url:
            # Try to extract from request line (first line of HTTP request)
            try:
                lines = request_str.split("\n")
                if lines:
                    # Parse "POST /path HTTP/1.1" format
                    parts = lines[0].split()
                    if len(parts) >= 2:
                        path = parts[1]
                        # Try to construct URL from Host header
                        host = request_headers.get(
                            "host",
                            request_headers.get("Host", ""),
                        )
                        if host:
                            url = f"https://{host}{path}"
            except Exception:
                pass

        # Find the appropriate parser
        parser = None
        for p in self.parsers:
            if p.can_parse(url):
                parser = p
                break

        if not parser:
            raise ValueError(f"No parser found for URL: {url}")

        # Parse request and response bodies
        try:
            request_body = json.loads(request_str)
        except Exception as e:
            raise ValueError(f"Failed to parse request body: {e}")

        response_body = {}
        is_streaming = False

        if response_str:
            # Check if this is a streaming response (Server-Sent Events)
            content_type = response_headers.get("content-type", "")
            if "text/event-stream" in content_type or response_str.strip().startswith(
                ("data:", "event:"),
            ):
                is_streaming = True
            else:
                try:
                    response_body = json.loads(response_str)
                except Exception:
                    # If response parsing fails, it's not necessarily an error
                    # (could be streaming or non-JSON response)
                    pass

        # Extract error from response body if status code indicates error and no error set
        if status_code >= 400 and not error:
            extracted_error = self._extract_error_from_response(response_body, parser)
            if extracted_error:
                error = extracted_error

        # Use the parser to create TraceCreate
        return parser.parse(
            request_body=request_body,
            response_body=response_body,
            started_at=started_at,
            completed_at=completed_at,
            error=error,
            metadata=metadata,
            call_path=call_path,
            is_streaming=is_streaming,
            streaming_response=response_str if is_streaming else None,
        )
