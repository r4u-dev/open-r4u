"""LangChain Google GenAI integration for R4U observability."""

from typing import Any

from r4u.integrations.google_genai import GoogleGenAITracer

from ...client import r4u_client
from ..http.requests import trace_requests_session


try:
    from langchain_google_genai import ChatGoogleGenerativeAI as OriginalChatGoogleGenerativeAI
    LANGCHAIN_GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    LANGCHAIN_GOOGLE_GENAI_AVAILABLE = False
    OriginalChatGoogleGenerativeAI = object  # type: ignore


class ChatGoogleGenerativeAI(OriginalChatGoogleGenerativeAI):
    """ChatGoogleGenerativeAI wrapper that automatically creates traces."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize the wrapper."""
        if not LANGCHAIN_GOOGLE_GENAI_AVAILABLE:
            raise ImportError(
                "LangChain Google GenAI is not installed. Please install it with: "
                "pip install langchain-google-genai"
            )
        
        super().__init__(*args, **kwargs)
        trace_requests_session(self.client._client._session, GoogleGenAITracer(r4u_client))