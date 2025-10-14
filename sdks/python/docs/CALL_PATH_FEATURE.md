# Call Path Tracking Feature

## Overview

The R4U SDK now automatically tracks where LLM calls originate from in your codebase. This provides valuable debugging and observability information.

## How It Works

When an LLM call is made through a wrapped client, the SDK:

1. Inspects the Python call stack using `inspect.currentframe()`
2. Identifies the user code that initiated the call
3. Builds a call path showing the file and function chain
4. Includes this path in the trace sent to the R4U API

## Path Format

The path is formatted as: `file.py::function1->function2->function3`

Example:
```
src/chatbot/main.py::handle_request->process_query->call_llm
```

## Implementation

### Core Utility: `src/r4u/utils.py`

The `extract_call_path()` function performs the stack inspection:

- Skips internal frames (r4u SDK, OpenAI SDK internals)
- Identifies the first user code frame as the "target file"
- Collects all functions in the call chain within that file
- Returns relative path from current working directory
- Returns tuple of (path_signature, line_number)

### Integration: `src/r4u/integrations/openai.py`

The OpenAI wrapper has been updated to:

1. Call `extract_call_path()` at the start of each LLM request
2. Pass the path to `create_trace()` / `create_trace_async()`
3. Include path in both successful and error traces

### Client: `src/r4u/client.py`

The R4U client schemas have been updated:

- `TraceCreate` now accepts optional `path` parameter
- `TraceRead` includes `path` field in responses
- Both sync and async methods support path tracking

## Usage Examples

### Automatic Tracking (Recommended)

```python
from openai import OpenAI
from r4u.integrations.openai import wrap_openai

def process_request():
    client = wrap_openai(OpenAI())
    response = client.chat.completions.create(...)
    # Trace will include path="your_file.py::process_request"
```

### With Nested Functions

```python
def main():
    handle_request()

def handle_request():
    query_llm("question")

def query_llm(text):
    traced_client.chat.completions.create(...)
    # Trace will include: "file.py::main->handle_request->query_llm"
```

### Manual Extraction

```python
from r4u.utils import extract_call_path

def my_function():
    path, line_num = extract_call_path()
    print(f"Called from: {path} at line {line_num}")
```

## Testing

### Unit Tests

`tests/test_utils.py` includes comprehensive tests for:
- Basic call path extraction
- Nested function call chains
- File name capture
- Line number accuracy

### Integration Tests

`test_path_tracking.py` - End-to-end test with real OpenAI calls
`test_call_path_simple.py` - Simple verification of path extraction

### Examples

`examples/path_tracking_example.py` - Demonstration of the feature

## Benefits

1. **Debugging**: Quickly identify which part of your code made an LLM call
2. **Monitoring**: Track usage patterns across your codebase
3. **Auditing**: Understand the execution context of each LLM interaction
4. **Cost Attribution**: Associate API costs with specific features/functions

## Technical Details

### Frame Filtering

The implementation skips:
- `utils.py` frames (the extraction function itself)
- `patcher.py` frames (internal wrapping)
- `_base_client.py` frames (OpenAI SDK internals)
- Module-level frames (`<module>`)
- Wrapper function frames

### Relative Paths

Paths are made relative to the current working directory when possible:
- `/home/user/project/src/main.py` → `src/main.py`
- Falls back to absolute path if relative conversion fails

### Error Handling

- Returns `("unknown", 0)` if no valid frame is found
- Gracefully handles stack inspection failures
- Never causes LLM calls to fail

## Future Enhancements

Potential improvements:
- Configurable path format
- Support for filtering by package/module
- Option to include line numbers in path string
- Support for other LLM providers (Anthropic, Cohere, etc.)