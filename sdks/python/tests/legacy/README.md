# Legacy Tests

This directory contains tests from the old API-based tracing system that have been deprecated.

## Why These Tests Are Here

The R4U SDK has migrated from an **API-based tracing approach** to an **HTTP transport-level tracing approach**. These tests were written for the old system and are no longer compatible with the current implementation.

### Old System (API-based)
- Used wrapper functions like `wrap_openai()`, `wrap_langchain()`
- Required explicit trace creation with `TraceCreate`, `InputEntry`, etc.
- Manually called R4U API endpoints to create traces
- Tests verified wrapper behavior and API calls

### New System (HTTP transport-level)
- Uses traced clients: `from r4u.tracing.openai import OpenAI`
- Automatically captures raw HTTP requests/responses at transport level
- Backend processes HTTP traces to extract relevant data
- No manual trace creation needed - completely transparent

## Test Files in This Directory

- `test_client.py` - Tests for old `TraceCreate` API
- `test_openai_integration.py` - Tests for old `wrap_openai()` function
- `test_langchain_integration.py` - Tests for old `wrap_langchain()` function  
- `test_anthropic_integration.py` - Tests for old Anthropic wrapper
- `test_call_path.py` - Tests for old call path tracking
- `test_e2e_path.py` - End-to-end tests for old system
- `test_path_tracking.py` - Path tracking tests for old system

## Current Test Coverage

Active tests are in the parent `tests/` directory:
- `test_requests_integration.py` - HTTP transport tracing for requests library
- `test_utils.py` - Utility function tests (call path extraction)

## Future Work

These legacy tests could be:
1. **Deleted** - if the old API is completely removed
2. **Rewritten** - to test the new HTTP transport-level system
3. **Archived** - kept for historical reference

For now, they are excluded from pytest discovery via `pyproject.toml`:
```toml
[tool.pytest.ini_options]
norecursedirs = ["tests/legacy", "tests/manual"]
```
