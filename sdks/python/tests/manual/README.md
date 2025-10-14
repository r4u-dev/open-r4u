# Manual Test Scripts

This directory contains manual test scripts that are useful for development, debugging, and demonstration purposes. These tests are **NOT** run automatically by pytest.

## Why Manual Tests?

These scripts are kept separate because they:
- Require manual execution with real OpenAI API calls
- Are used for development debugging and validation
- Serve as demonstrations of call path tracking
- Need real backend server running
- May incur API costs if run frequently

## Available Tests

### 1. `test_call_path.py`
**Purpose**: End-to-end test with real OpenAI API  
**Tests**: Nested function call path tracking  
**Requires**: OpenAI API key, backend server running

```bash
python3 tests/manual/test_call_path.py
```

Expected output:
```
Expected path: test_call_path.py::main->outer_function->inner_function
✓ Trace created successfully!
✓ Call path captured
```

---

### 2. `test_call_path_simple.py`
**Purpose**: Debug utility for testing `extract_call_path()` directly  
**Tests**: Call path extraction at different nesting levels  
**Requires**: Nothing (pure Python)

```bash
python3 tests/manual/test_call_path_simple.py
```

Expected output:
```
Called from level_1->level_2->level_3:
  Path: test_call_path_simple.py::level_1->level_2->level_3
✓ Full call chain captured
```

---

### 3. `test_e2e_path.py`
**Purpose**: End-to-end test with mocked OpenAI  
**Tests**: Full call chain with mocked LLM calls  
**Requires**: Nothing (uses mocks)

```bash
python3 tests/manual/test_e2e_path.py
```

Expected output:
```
🎉 SUCCESS: Call path tracking is working correctly!
The path shows: test_e2e_path.py::main->helper_function->simulate_llm_call
```

---

### 4. `test_path_tracking.py`
**Purpose**: End-to-end test with real OpenAI API and backend  
**Tests**: Complete integration with real API and trace storage  
**Requires**: OpenAI API key, backend server running

```bash
python3 tests/manual/test_path_tracking.py
```

Expected output:
```
🎉 SUCCESS: Call path tracking is working perfectly!
Call Path: test_path_tracking.py::main->process_request->helper_function
```

---

## When to Use Manual Tests

### During Development
- Testing new call path features
- Debugging path extraction issues
- Validating nested function tracking

### Before Release
- Verify real API integration works
- Check E2E flow with actual OpenAI calls
- Validate trace storage in backend

### For Demonstration
- Show how call path tracking works
- Demonstrate nested function capture
- Showcase the SDK capabilities

---

## Prerequisites

### For Real API Tests (test_call_path.py, test_path_tracking.py)

1. **OpenAI API Key**:
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```

2. **Backend Server Running**:
   ```bash
   cd /path/to/backend
   docker compose up
   # or
   uvicorn app.main:app --reload
   ```

3. **Verify Backend**:
   ```bash
   curl http://localhost:8000/traces
   ```

### For Mocked Tests (test_e2e_path.py, test_call_path_simple.py)

No prerequisites needed - these use mocks or pure Python testing.

---

## Running All Manual Tests

```bash
# From project root
cd /home/coder/workspace/open-r4u/sdks/python

# Run each test
python3 tests/manual/test_call_path_simple.py
python3 tests/manual/test_e2e_path.py

# These require API key + backend:
export OPENAI_API_KEY="sk-..."
python3 tests/manual/test_call_path.py
python3 tests/manual/test_path_tracking.py
```

---

## For Automated Testing

For automated CI/CD testing, use the pytest suite instead:

```bash
pytest tests/ -v
```

This runs only the automated tests in `test_client.py`, `test_openai_integration.py`, and `test_utils.py`.

---

## Contributing

When adding new manual tests:
1. Place them in this `tests/manual/` directory
2. Add a `#!/usr/bin/env python3` shebang
3. Include clear print output showing what's being tested
4. Document prerequisites in this README
5. Make sure they don't run automatically in pytest

---

## Troubleshooting

### "No traces created"
- Check backend server is running: `curl http://localhost:8000/traces`
- Verify API key is set: `echo $OPENAI_API_KEY`

### "Module not found"
- Run from project root: `cd /path/to/sdks/python`
- Check Python path: `export PYTHONPATH=.`

### "OpenAI API error"
- Verify API key is valid
- Check internet connection
- Ensure you have API credits
