"""Google GenAI integration for R4U observability."""

import os
from typing import Optional

from r4u.integrations.http.tracer import AbstractTracer, RequestInfo
from ..client import R4UClient, r4u_client
from ..utils import extract_call_path
from .http.requests import trace_session

try:
    from google.generativeai import GenerativeModel as OriginalGenerativeModel
    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    GOOGLE_GENAI_AVAILABLE = False
    OriginalGenerativeModel = object  # type: ignore


class GoogleGenAITracer(AbstractTracer):
    """Tracer for Google GenAI client."""
    
    def __init__(self, r4u_client: R4UClient):
        self._r4u_client = r4u_client

    def trace_request(self, request_info: RequestInfo):
        """Trace a request."""
        # Google GenAI uses different endpoints, we'll handle the main generation endpoint
        if "/v1beta/models/" in request_info.url and ":generateContent" in request_info.url:
            trace = self._get_generate_content_trace(request_info)
        else:
            # For other endpoints, we can add more specific handling as needed
            trace = self._get_generic_trace(request_info)

        if trace is not None:
            self._r4u_client.create_trace(**trace)

    def _get_generate_content_trace(self, request_info: RequestInfo) -> Optional[dict]:
        """Trace a generateContent request."""
        import json
        
        try:
            request_json = json.loads(request_info.request_payload)
            print(f"{request_info.method.upper()} {request_info.url}")
            print(json.dumps(request_json, indent=2))
            
            # Extract model name from URL
            model_name = "unknown"
            if "/v1beta/models/" in request_info.url:
                parts = request_info.url.split("/v1beta/models/")
                if len(parts) > 1:
                    model_part = parts[1].split(":")[0]
                    model_name = model_part
            
            # Extract messages from request
            messages = []
            if "contents" in request_json:
                for content in request_json["contents"]:
                    if "parts" in content:
                        for part in content["parts"]:
                            if "text" in part:
                                role = content.get("role", "user")
                                messages.append({
                                    "role": role,
                                    "content": part["text"]
                                })
            
            # Extract call path
            call_path, _ = extract_call_path()
            
            return {
                "model": model_name,
                "messages": messages,
                "started_at": request_info.started_at,
                "completed_at": request_info.completed_at,
                "path": call_path,
                "project": os.getenv("R4U_PROJECT", "Default Project"),
            }
        except Exception as e:
            print(f"Failed to parse Google GenAI request: {e}")
            return None

    def _get_generic_trace(self, request_info: RequestInfo) -> Optional[dict]:
        """Trace a generic request."""
        import json
        
        try:
            request_json = json.loads(request_info.request_payload)
            print(f"{request_info.method.upper()} {request_info.url}")
            print(json.dumps(request_json, indent=2))
            
            # Extract call path
            call_path, _ = extract_call_path()
            
            return {
                "model": "unknown",
                "messages": [],
                "started_at": request_info.started_at,
                "completed_at": request_info.completed_at,
                "path": call_path,
                "project": os.getenv("R4U_PROJECT", "Default Project"),
            }
        except Exception as e:
            print(f"Failed to parse Google GenAI request: {e}")
            return None


class GenerativeModel(OriginalGenerativeModel):
    """GenerativeModel wrapper that automatically creates traces."""
    
    def __init__(self, *args, **kwargs):
        """Initialize the wrapper."""
        if not GOOGLE_GENAI_AVAILABLE:
            raise ImportError(
                "Google GenAI is not installed. Please install it with: "
                "pip install google-generativeai"
            )
        
        super().__init__(*args, **kwargs)
        
        # Patch the HTTP client for tracing
        if hasattr(self, '_client') and self._client:
            trace_session(self._client._session, GoogleGenAITracer(r4u_client))
