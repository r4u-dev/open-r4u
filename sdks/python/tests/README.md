# R4U Python SDK Test Suite

This directory contains comprehensive tests for the R4U Python SDK, focusing on HTTP request tracing functionality.

## Test Structure

### Test Files

- **`conftest.py`** - Shared pytest fixtures and test utilities
- **`test_client.py`** - Tests for the core client and HTTPTrace model
- **`test_httpx_wrapper.py`** - Tests for httpx HTTP client wrapper
- **`test_requests_wrapper.py`** - Tests for requests HTTP client wrapper
- **`test_aiohttp_wrapper.py`** - Tests for aiohttp HTTP client wrapper

## Running Tests

### Run All Tests
```bash
uv run pytest tests/ -v
```

### Run Specific Test File
```bash
uv run pytest tests/test_client.py -v
uv run pytest tests/test_httpx_wrapper.py -v
uv run pytest tests/test_requests_wrapper.py -v
uv run pytest tests/test_aiohttp_wrapper.py -v
```

### Run Specific Test Class or Function
```bash
uv run pytest tests/test_client.py::TestHTTPTraceModel -v
uv run pytest tests/test_httpx_wrapper.py::TestTraceAll -v
```

### Run with Coverage
```bash
uv run pytest tests/ --cov=src/r4u --cov-report=html
```

## Test Coverage

### Core Client Tests (`test_client.py`)

**HTTPTrace Model**
- Creation with required fields
- Error handling
- Metadata support
- Serialization to JSON
- Various HTTP methods (GET, POST, PUT, DELETE, etc.)
- Empty request/response bodies
- Large payload handling

**ConsoleTracer**
- Logging traces to console
- AbstractTracer interface implementation

**R4UClient**
- Initialization with custom API URL and timeout
- URL normalization (trailing slash removal)
- Trace queueing
- Background worker thread operation
- Batch sending of traces to API
- Error handling during trace transmission
- Proper cleanup and resource management
- AbstractTracer interface implementation

**get_r4u_client**
- Singleton pattern
- Environment variable configuration
- Custom timeout support

### httpx Wrapper Tests (`test_httpx_wrapper.py`)

**Helper Functions**
- `_build_trace_context()` - Request context building
- `_finalize_trace()` - Trace finalization with timing
- `_is_streaming_request()` - Streaming detection

**StreamingResponseWrapper**
- Attribute delegation to original response
- Content collection during streaming
- Chunk iteration (`iter_bytes()`, `iter_text()`, `iter_lines()`)
- Error handling during streaming
- Trace completion on stream end

**Sync Client Tracing**
- Wrapping `httpx.Client.send()` method
- Double-patching prevention
- Request data capture
- Exception handling

**Async Client Tracing**
- Wrapping `httpx.AsyncClient.send()` method
- Double-patching prevention
- Request data capture with async/await
- Exception handling in async context

**Auto-Tracing**
- Constructor interception via `trace_all()`
- Automatic tracing of new client instances
- Cleanup via `untrace_all()`

### requests Wrapper Tests (`test_requests_wrapper.py`)

**Helper Functions**
- `_build_trace_context()` - PreparedRequest context building
- `_finalize_trace()` - Trace finalization
- `_is_streaming_request()` - Stream parameter detection
- String body handling

**StreamingResponseWrapper**
- Attribute delegation
- Content property access
- Text property access
- JSON method access
- Content iteration (`iter_content()`, `iter_lines()`)
- Error handling during streaming
- Proper response closing

**Session Tracing**
- Wrapping `requests.Session.send()` method
- Double-patching prevention
- Request data capture
- Exception handling
- Streaming request detection

**Auto-Tracing**
- Constructor interception via `trace_all()`
- Automatic tracing of new session instances
- Default tracer usage
- Cleanup via `untrace_all()`

**End-to-End**
- Full request lifecycle with tracing

### aiohttp Wrapper Tests (`test_aiohttp_wrapper.py`)

**Helper Functions**
- `_is_streaming_request()` - Always returns True for aiohttp

**StreamingResponseWrapper**
- Attribute delegation
- Content reading (`read()`, `text()`, `json()`)
- Chunk iteration (`iter_chunked()`, `iter_any()`, `iter_line()`)
- Error handling during async streaming
- Proper async resource cleanup
- Duplicate trace prevention

**Async Client Tracing**
- Wrapping `aiohttp.ClientSession._request()` method
- Double-patching prevention
- Request data capture with various data formats
- Header capture
- Exception handling

**Auto-Tracing**
- Constructor interception via `trace_all()`
- Automatic tracing of new session instances
- Default tracer usage
- Cleanup via `untrace_all()`

**End-to-End**
- Full async request lifecycle
- Multiple concurrent requests

## Fixtures

### Shared Fixtures (from `conftest.py`)

- **`mock_tracer`** - Mock tracer with call tracking
- **`sample_http_trace`** - Pre-configured HTTPTrace instance
- **`sample_request_data`** - Sample request data dict
- **`sample_response_data`** - Sample response data dict
- **`streaming_response_data`** - Sample streaming response data
- **`capturing_tracer`** - Real tracer that captures traces in memory
- **`mock_http_server`** - Mock HTTP server for response simulation

### Test-Specific Fixtures

Each test file defines fixtures for:
- Mock HTTP requests (library-specific format)
- Mock HTTP responses (library-specific format)
- Mock streaming responses

## Test Patterns

### Unit Tests
- Test individual functions and classes in isolation
- Mock external dependencies
- Focus on single responsibility

### Integration Tests
- Test wrapper integration with HTTP clients
- Verify end-to-end request/response flow
- Validate trace creation and transmission

### Async Tests
- Use `@pytest.mark.asyncio` decorator
- Test async/await patterns
- Verify async resource cleanup

## Key Testing Principles

1. **Isolation** - Tests don't depend on external services
2. **Mocking** - External HTTP calls and network operations are mocked
3. **Coverage** - Tests cover happy paths, error cases, and edge cases
4. **Async Support** - Full testing of async operations
5. **Resource Cleanup** - Proper cleanup of HTTP clients and connections

## Dependencies

Test dependencies are defined in `pyproject.toml`:
- `pytest` - Testing framework
- `pytest-asyncio` - Async test support
- `pytest-mock` - Enhanced mocking
- `httpx` - HTTP client library
- `requests` - HTTP client library
- `aiohttp` - Async HTTP client library

## Continuous Integration

These tests are designed to run in CI/CD pipelines without requiring:
- Running backend API server
- Network connectivity
- External services
- Real API keys

All external dependencies are mocked for fast, reliable test execution.
