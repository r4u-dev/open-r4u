# Testing the Traces API Integration

This guide will help you test the complete traces integration between the frontend and backend.

## Prerequisites

1. **Backend running** on port 8000
2. **Frontend running** on port 8080
3. **Database** initialized with migrations

## Step 1: Start the Backend

```bash
cd backend

# Make sure database is up to date
uv run alembic upgrade head

# Start the backend server
uv run uvicorn app.main:app --reload
```

The backend should be available at: `http://localhost:8000`

## Step 2: Create Test Traces

Run this script to create sample traces in the database:

```bash
# Create 30 test traces with various models and statuses
for i in {1..30}; do
  curl -X POST http://localhost:8000/traces \
    -H "Content-Type: application/json" \
    -d '{
      "model": "gpt-4-turbo",
      "input": [
        {"type": "message", "role": "system", "content": "You are a helpful assistant."},
        {"type": "message", "role": "user", "content": "Test message '$i'"}
      ],
      "result": "This is a test response for trace '$i'",
      "started_at": "'$(date -u -d "$i minutes ago" +%Y-%m-%dT%H:%M:%SZ)'",
      "completed_at": "'$(date -u -d "$i minutes ago" +%Y-%m-%dT%H:%M:%SZ)'",
      "prompt_tokens": '$((100 + RANDOM % 100))',
      "completion_tokens": '$((50 + RANDOM % 50))',
      "total_tokens": '$((150 + RANDOM % 150))',
      "temperature": 0.7
    }'
  echo ""
done

# Create some error traces
for i in {1..5}; do
  curl -X POST http://localhost:8000/traces \
    -H "Content-Type: application/json" \
    -d '{
      "model": "claude-3-sonnet",
      "input": [
        {"type": "message", "role": "user", "content": "Error test '$i'"}
      ],
      "error": "Rate limit exceeded",
      "started_at": "'$(date -u -d "$i minutes ago" +%Y-%m-%dT%H:%M:%SZ)'"
    }'
  echo ""
done
```

## Step 3: Verify Backend API

Test the pagination endpoints:

```bash
# Get first 10 traces
curl http://localhost:8000/traces?limit=10 | jq 'length'
# Should output: 10

# Get next 10 traces
curl http://localhost:8000/traces?limit=10&offset=10 | jq 'length'
# Should output: 10

# Get all traces (should be capped at 25 by default)
curl http://localhost:8000/traces | jq 'length'
# Should output: 25

# Verify traces are ordered by started_at desc (newest first)
curl http://localhost:8000/traces?limit=2 | jq '.[0].started_at, .[1].started_at'

# Test validation - should return 422 error
curl http://localhost:8000/traces?limit=0
curl http://localhost:8000/traces?limit=101
curl http://localhost:8000/traces?offset=-1
```

## Step 4: Start the Frontend

```bash
cd frontend

# Install dependencies if needed
npm install

# Start the dev server
npm run dev
```

The frontend should be available at: `http://localhost:8080`

## Step 5: Test Frontend Integration

### Manual Testing

1. **Navigate to Traces page**
   - Open `http://localhost:8080` in your browser
   - Click on the "Traces" tab

2. **Verify initial load**
   - ✅ Should see 25 traces loaded from the API
   - ✅ First trace should be automatically selected
   - ✅ Detail panel should show on the right
   - ✅ Should see "Loading more traces..." briefly

3. **Test infinite scrolling**
   - Scroll to the bottom of the traces list
   - ✅ Should automatically load 25 more traces
   - ✅ Should see "Loading more traces..." indicator
   - ✅ After all traces loaded, should see "No more traces to load"

4. **Test time period filter**
   - Click on different time periods (5m, 15m, 1h, 4h)
   - ✅ Should refetch traces from API
   - ✅ Client-side filtering should work
   - ✅ Loading indicator should appear

5. **Test sorting**
   - Click on column headers (Status, Task, Type, Model, Latency, Cost, Timestamp)
   - ✅ Should sort traces in ascending order
   - ✅ Click again to sort in descending order
   - ✅ Sorting is client-side (no API call)

6. **Test trace details**
   - Click on different traces
   - ✅ Detail panel should update
   - ✅ Should show all available fields
   - ✅ Empty fields (cost, taskVersion, rawRequest/Response) should be handled gracefully

7. **Verify data mapping**
   - Check that backend data is correctly mapped:
   - ✅ Status: Shows "success" or "error" based on error field
   - ✅ Provider: Detected from model name (openai, anthropic, etc.)
   - ✅ Type: text/image/audio detected from model
   - ✅ Latency: Calculated from timestamps
   - ✅ Model settings: Shows temperature, tokens

### Browser Console Testing

Open the browser console and verify:

```javascript
// Should see API requests
// API Request URL: http://localhost:8000/traces?limit=25&offset=0
// API Response data: [...]

// No errors in console
// No failed network requests
```

## Step 6: Test Error Handling

### Backend Down

1. Stop the backend server
2. Refresh the frontend
3. ✅ Should see error in console: "Failed to fetch traces"
4. ✅ Should show "No traces found" message

### Empty Database

1. Clear all traces from database:
```bash
curl -X DELETE http://localhost:8000/traces  # If endpoint exists
# Or manually via SQL
```
2. Refresh the frontend
3. ✅ Should show "No traces found" message
4. ✅ No errors in console

### Network Timeout

1. Add a network throttle in Chrome DevTools
2. Scroll to load more traces
3. ✅ Should handle timeout gracefully
4. ✅ Error logged to console

## Step 7: Run Backend Tests

```bash
cd backend

# Run all trace tests
uv run pytest tests/test_traces.py -v

# Run only pagination tests
uv run pytest tests/test_traces.py::TestTraceEndpoints::test_list_traces_with_pagination -v
uv run pytest tests/test_traces.py::TestTraceEndpoints::test_list_traces_pagination_limits -v
```

Expected output:
```
tests/test_traces.py::TestTraceEndpoints::test_list_traces_with_pagination PASSED
tests/test_traces.py::TestTraceEndpoints::test_list_traces_pagination_limits PASSED
```

## Checklist

- [ ] Backend running on port 8000
- [ ] Backend tests all passing (21/21)
- [ ] Frontend builds successfully
- [ ] Frontend running on port 8080
- [ ] Sample traces created in database
- [ ] API endpoint `/traces` returns paginated results
- [ ] Frontend fetches traces on mount
- [ ] Infinite scrolling loads more traces
- [ ] Time period filter triggers refetch
- [ ] Sorting works correctly
- [ ] Trace selection and detail panel work
- [ ] No console errors
- [ ] Data mapping is correct (backend → frontend)
- [ ] Empty states handled gracefully
- [ ] Error states handled gracefully

## Troubleshooting

### Frontend shows "No traces found" but database has traces

1. Check backend is running: `curl http://localhost:8000/health`
2. Check API endpoint: `curl http://localhost:8000/traces | jq`
3. Check browser console for CORS errors
4. Verify API_BASE_URL in `frontend/src/services/api.ts` is correct

### Infinite scrolling not working

1. Check browser console for errors
2. Verify `observerRef` is attached to DOM element
3. Check `hasMore` state in React DevTools
4. Verify backend returns correct number of traces

### Traces not sorted correctly

1. Sorting is client-side, check `filteredAndSortedTraces` memo
2. Verify `sortField` and `sortDirection` state
3. Check timestamp format from backend

### Missing fields in trace details

Expected empty fields (not implemented yet):
- `cost`: Always 0
- `taskVersion`: Always undefined
- `rawRequest`: Always empty string
- `rawResponse`: Always empty string

These are documented limitations and will be implemented in future updates.

## Performance Testing

### Load Test

Create 1000 traces:

```bash
for i in {1..1000}; do
  curl -X POST http://localhost:8000/traces \
    -H "Content-Type: application/json" \
    -d '{
      "model": "gpt-4",
      "input": [{"type": "message", "role": "user", "content": "Test"}],
      "result": "Response",
      "started_at": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
    }' > /dev/null 2>&1
done
```

Then test:
- ✅ Initial load should be fast (< 1s)
- ✅ Infinite scroll should load smoothly
- ✅ UI should remain responsive
- ✅ Memory usage should be reasonable

## Next Steps

After verification:

1. **Deploy to staging** and test with real data
2. **Implement cost calculation** based on token usage
3. **Add task/implementation linking** to show task names
4. **Store raw request/response** in HTTP traces
5. **Add server-side filtering** for time periods
6. **Add server-side sorting** for better performance
7. **Implement cursor-based pagination** for large datasets

## Related Documentation

- [Traces API Integration](./TRACES_API_INTEGRATION.md)
- [Backend README](../backend/README.md)
- [Frontend README](../frontend/README.md)
