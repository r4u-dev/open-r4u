"""Google GenAI integration for R4U observability."""

from .http.requests import trace_session

try:
    from google.generativeai import GenerativeModel as OriginalGenerativeModel
    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    GOOGLE_GENAI_AVAILABLE = False
    OriginalGenerativeModel = object  # type: ignore


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
            trace_session(self._client._session, "google")
