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

The path is formatted as: `file.py::function`

Example:

```
src/chatbot/main.py::call_llm
```

The function represents where `extract_call_path()` is called from (the first non-library frame).

## Implementation

### Core Utility: `src/r4u/utils.py`

The `extract_call_path()` function performs the stack inspection:

- Uses `inspect.stack()` to get all stack frames
- Filters out library files (site-packages, standard library)
- Identifies the first non-library file in the call stack
- Returns the file path and function name where the call originated
- Returns relative path from current working directory when possible
- Returns tuple of (call_path, line_number) formatted as `"file.py::function"`

### Integration: `src/r4u/tracing/openai.py`

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
from r4u.tracing.openai import wrap_openai

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
    # Trace will include: "file.py::query_llm"
```

Note: The path shows only the immediate function where the call is made, not the full chain.

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

- Direct call path extraction
- Nested function calls
- Class method calls
- Return format validation
- Max depth parameter
- Line number accuracy

### Examples

`examples/extract_call_path_example.py` - Comprehensive demonstration of the feature with various use cases

## Benefits

1. **Debugging**: Quickly identify which part of your code made an LLM call
2. **Monitoring**: Track usage patterns across your codebase
3. **Auditing**: Understand the execution context of each LLM interaction
4. **Cost Attribution**: Associate API costs with specific features/functions

## Technical Details

### Frame Filtering

The implementation filters out:

- All library files (site-packages, standard library)
- Python internal files (files starting with `<`)
- Returns the first non-library file found in the stack

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

- Optional full call chain format (file.py::func1->func2->func3)
- Configurable library path filtering
- Support for filtering by package/module patterns
- Option to include line numbers in path string
- Support for other LLM providers (Anthropic, Cohere, etc.)
