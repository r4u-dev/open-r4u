# Raw Request/Response Tracing Recommendations

## Executive Summary

Based on analysis of the current R4U tracing implementation, I recommend transitioning to a **raw request/response capture approach** that preserves complete API details without parsing. This approach addresses the complexity and differences between LLM providers while ensuring no data loss.

## Current State Analysis

### Current Approach: Parsed Tracing
The existing implementation uses provider-specific parsing logic that:
- Extracts specific fields (messages, tokens, tools) from requests/responses
- Normalizes data into a common `TraceCreate` schema
- Loses provider-specific details and edge cases
- Requires maintenance for each new provider/API version

### Key Issues with Current Approach
1. **Data Loss**: Provider-specific fields are filtered out during parsing
2. **Maintenance Burden**: Each provider requires custom parsing logic
3. **Version Fragility**: API changes break parsing logic
4. **Incomplete Coverage**: New endpoints/features require code updates
5. **Complexity**: 600+ lines of parsing code per provider

## Recommended Approach: Raw Request/Response Tracing

### Core Principle
**Capture everything, parse nothing** - Store complete request/response payloads as-is, with minimal metadata extraction.

### Benefits

#### 1. **Complete Data Preservation**
- No data loss from parsing or normalization
- All provider-specific fields preserved
- Future-proof against API changes
- Captures edge cases and undocumented features

#### 2. **Reduced Maintenance**
- Single implementation for all providers
- No provider-specific parsing logic
- Automatic support for new endpoints
- No version-specific code maintenance

#### 3. **Enhanced Debugging**
- Complete request/response context available
- Raw payloads for troubleshooting
- Headers, status codes, and timing preserved
- Error details without parsing artifacts

#### 4. **Flexibility**
- Post-processing can extract any field
- Multiple analysis approaches possible
- Custom queries on raw data
- Provider-specific analysis when needed

## Implementation Strategy

### 1. Enhanced RequestInfo Schema

```python
@dataclass
class RawRequestInfo:
    """Complete HTTP request/response information for raw tracing."""
    
    # Request details
    method: str
    url: str
    headers: Dict[str, str]
    request_payload: bytes
    request_size: int
    
    # Response details  
    status_code: int
    response_payload: bytes
    response_size: int
    response_headers: Dict[str, str]
    
    # Timing
    started_at: datetime
    completed_at: datetime
    duration_ms: float
    
    # Error information
    error: Optional[str] = None
    error_type: Optional[str] = None
    
    # Provider identification
    provider: str  # "openai", "anthropic", "google", etc.
    endpoint: str  # "/chat/completions", "/messages", etc.
    
    # Optional extracted metadata (for indexing/search)
    model: Optional[str] = None
    operation_type: Optional[str] = None  # "chat", "embedding", "image", etc.
```

### 2. Universal Tracer Implementation

```python
class UniversalTracer(AbstractTracer):
    """Universal tracer that captures raw request/response data."""
    
    def __init__(self, r4u_client: R4UClient):
        self._r4u_client = r4u_client
    
    def trace_request(self, request_info: RawRequestInfo) -> None:
        """Store complete raw request/response data."""
        
        # Extract minimal metadata for indexing
        metadata = self._extract_basic_metadata(request_info)
        
        # Create trace with raw payloads
        trace_data = {
            "provider": request_info.provider,
            "endpoint": request_info.endpoint,
            "model": metadata.get("model"),
            "operation_type": metadata.get("operation_type"),
            "started_at": request_info.started_at,
            "completed_at": request_info.completed_at,
            "duration_ms": request_info.duration_ms,
            "status_code": request_info.status_code,
            "error": request_info.error,
            
            # Raw payloads (base64 encoded for storage)
            "raw_request": {
                "method": request_info.method,
                "url": request_info.url,
                "headers": request_info.headers,
                "payload": base64.b64encode(request_info.request_payload).decode(),
                "size": request_info.request_size
            },
            "raw_response": {
                "status_code": request_info.status_code,
                "headers": request_info.response_headers,
                "payload": base64.b64encode(request_info.response_payload).decode(),
                "size": request_info.response_size
            }
        }
        
        self._r4u_client.create_raw_trace(**trace_data)
    
    def _extract_basic_metadata(self, request_info: RawRequestInfo) -> Dict[str, Any]:
        """Extract minimal metadata for indexing without full parsing."""
        try:
            # Only extract essential fields for search/indexing
            if request_info.request_payload:
                request_json = json.loads(request_info.request_payload.decode())
                return {
                    "model": request_json.get("model"),
                    "operation_type": self._infer_operation_type(request_info.url)
                }
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
        return {}
    
    def _infer_operation_type(self, url: str) -> str:
        """Infer operation type from URL without parsing."""
        if "/chat/completions" in url or "/messages" in url:
            return "chat"
        elif "/embeddings" in url:
            return "embedding"
        elif "/images" in url:
            return "image"
        elif "/audio" in url:
            return "audio"
        return "unknown"
```

### 3. Enhanced Client Schema

```python
class RawTraceCreate(BaseModel):
    """Schema for raw trace creation."""
    
    # Basic metadata
    provider: str
    endpoint: str
    model: Optional[str] = None
    operation_type: Optional[str] = None
    
    # Timing
    started_at: datetime
    completed_at: datetime
    duration_ms: float
    
    # Status
    status_code: int
    error: Optional[str] = None
    
    # Raw data
    raw_request: Dict[str, Any]
    raw_response: Dict[str, Any]
    
    # Optional extracted fields for convenience
    extracted_metadata: Optional[Dict[str, Any]] = None

class RawTraceRead(BaseModel):
    """Schema for raw trace responses."""
    
    id: int
    project_id: int
    
    # All fields from RawTraceCreate
    provider: str
    endpoint: str
    model: Optional[str] = None
    operation_type: Optional[str] = None
    started_at: datetime
    completed_at: datetime
    duration_ms: float
    status_code: int
    error: Optional[str] = None
    raw_request: Dict[str, Any]
    raw_response: Dict[str, Any]
    extracted_metadata: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(from_attributes=True)
```

### 4. Provider Detection

```python
class ProviderDetector:
    """Detect LLM provider from request URL and headers."""
    
    @staticmethod
    def detect_provider(url: str, headers: Dict[str, str]) -> str:
        """Detect provider from URL and headers."""
        url_lower = url.lower()
        
        if "api.openai.com" in url_lower or "openai" in headers.get("authorization", ""):
            return "openai"
        elif "api.anthropic.com" in url_lower or "anthropic" in headers.get("x-api-key", ""):
            return "anthropic"
        elif "generativelanguage.googleapis.com" in url_lower:
            return "google"
        elif "api.groq.com" in url_lower:
            return "groq"
        elif "api.cohere.ai" in url_lower:
            return "cohere"
        else:
            return "unknown"
```

## Migration Strategy

### Phase 1: Dual Support
- Implement raw tracing alongside existing parsed tracing
- Add feature flag to enable raw tracing
- Maintain backward compatibility

### Phase 2: Gradual Migration
- Enable raw tracing for new integrations
- Migrate existing providers one by one
- Update dashboard to support both formats

### Phase 3: Full Transition
- Deprecate parsed tracing
- Remove provider-specific parsing code
- Optimize storage and retrieval for raw data

## Storage Considerations

### 1. Compression
```python
import gzip
import base64

def compress_payload(payload: bytes) -> str:
    """Compress payload for storage."""
    compressed = gzip.compress(payload)
    return base64.b64encode(compressed).decode()

def decompress_payload(compressed_data: str) -> bytes:
    """Decompress payload for retrieval."""
    compressed = base64.b64decode(compressed_data)
    return gzip.decompress(compressed)
```

### 2. Size Limits
- Implement configurable size limits for raw payloads
- Truncate oversized payloads with metadata
- Store size information for analysis

### 3. Retention Policies
- Implement tiered storage (hot/cold)
- Archive old raw traces
- Compress historical data

## Query and Analysis

### 1. Raw Data Access
```python
# Retrieve raw trace
trace = client.get_raw_trace(trace_id)

# Decode request/response
request_data = json.loads(decompress_payload(trace.raw_request["payload"]))
response_data = json.loads(decompress_payload(trace.raw_response["payload"]))

# Access any field without parsing limitations
model = request_data.get("model")
temperature = request_data.get("temperature")
custom_field = request_data.get("provider_specific_field")
```

### 2. Flexible Analysis
```python
# Extract specific fields as needed
def extract_tokens_from_trace(trace: RawTraceRead) -> Dict[str, int]:
    """Extract token usage from any provider's response."""
    response_data = json.loads(decompress_payload(trace.raw_response["payload"]))
    
    # Handle different provider formats
    if trace.provider == "openai":
        usage = response_data.get("usage", {})
        return {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0)
        }
    elif trace.provider == "anthropic":
        usage = response_data.get("usage", {})
        return {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        }
    # Add more providers as needed
    return {}
```

## Implementation Benefits

### 1. **Simplified Codebase**
- Remove 2000+ lines of provider-specific parsing code
- Single universal tracer implementation
- Reduced testing surface area

### 2. **Enhanced Reliability**
- No parsing errors or data corruption
- Complete request/response context
- Better error debugging capabilities

### 3. **Future-Proof Design**
- Automatic support for new providers
- No code changes for API updates
- Flexible analysis capabilities

### 4. **Better User Experience**
- Complete data visibility
- Custom analysis possibilities
- No data loss concerns

## Recommendations

### Immediate Actions
1. **Implement Universal Tracer**: Create the `UniversalTracer` class
2. **Add Raw Trace Schema**: Extend client with raw trace support
3. **Create Migration Path**: Implement dual support for gradual transition

### Medium-term Goals
1. **Update Dashboard**: Support raw trace visualization
2. **Add Analysis Tools**: Provide utilities for raw data analysis
3. **Optimize Storage**: Implement compression and retention policies

### Long-term Vision
1. **Remove Parsed Tracing**: Complete migration to raw approach
2. **Advanced Analytics**: Build provider-agnostic analysis tools
3. **API Standardization**: Work toward common LLM API standards

## Conclusion

The raw request/response tracing approach provides a robust, maintainable, and future-proof solution for LLM observability. By preserving complete API details without parsing, we eliminate data loss, reduce maintenance burden, and provide maximum flexibility for analysis and debugging.

This approach aligns with the principle of "capture everything, analyze later" and positions R4U as a comprehensive observability platform that can adapt to any LLM provider's API without code changes.
