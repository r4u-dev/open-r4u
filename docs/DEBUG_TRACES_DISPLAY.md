# Debugging Traces Display Issue

## Problem
Frontend fetches traces successfully from the API but displays "No traces found" message.

## What We've Done

### 1. Fixed CORS (✓ Working)
- Added CORS middleware to backend
- Backend responds with correct CORS headers
- No 405 errors

### 2. Fixed API Endpoints (✓ Working)
- Changed default API URL to port 8000
- Removed `/v1` prefix from all API services
- API calls returning 200 OK with data

### 3. Created Fresh Test Data (✓ Done)
- Created 10 traces with current timestamps
- Traces exist in database with timestamps from Oct 24, 2025

### 4. Changed Default Time Period
- Changed from "1h" to "4h" to be more permissive

### 5. Temporarily Disabled Time Filtering
- Commented out time filter in `filteredAndSortedTraces`
- Should now show ALL fetched traces regardless of timestamp

## Debugging Steps

### Step 1: Open Browser Console
Open the browser console (F12) and check for these logs:

#### Expected Logs on Page Load:
```
Fetched traces from API: 25
First trace: {id: "52", timestamp: "2025-10-24T09:29:05Z", ...}
Filtering traces: {
  total: 25,
  filtered: 25,
  timePeriod: "4h",
  cutoffTime: "...",
  now: "...",
  sampleTimestamp: "2025-10-24T09:29:05Z"
}
```

### Step 2: Check What You See

#### Scenario A: Console shows "Fetched traces: 25" but filtered: 0
**Problem**: Time filtering is still removing traces
**Solution**:
1. Check the file was saved correctly
2. Refresh the page (Ctrl+Shift+R)
3. Check if `filteredAndSortedTraces` is really using the disabled filter

#### Scenario B: Console shows "Fetched traces: 0"
**Problem**: API request failing or returning empty array
**Check**:
```javascript
// In console, manually check the API:
fetch('http://localhost:8000/traces?limit=5')
  .then(r => r.json())
  .then(data => console.log('API data:', data));
```

#### Scenario C: No console logs at all
**Problem**: Component not re-rendering or useEffect not running
**Solution**: Hard refresh (Ctrl+Shift+R) or restart dev server

#### Scenario D: Console shows error messages
**Problem**: JavaScript error breaking the component
**Solution**: Share the error message for specific fix

### Step 3: Network Tab Check

1. Open Network tab in DevTools
2. Filter by "traces"
3. Look for the GET request to `/traces`
4. Click on it and check:
   - Status: Should be 200
   - Response: Should contain array of traces with data

### Step 4: React DevTools Check

If you have React DevTools installed:

1. Open React DevTools
2. Find the `Traces` component
3. Check state values:
   - `traces` - should be array with data
   - `filteredAndSortedTraces` - should equal traces (since filtering is disabled)
   - `isLoading` - should be false after load
   - `timePeriod` - should be "4h"

## Quick Verification Commands

### Backend Check:
```bash
# Should return 5 traces with current timestamps
curl http://localhost:8000/traces?limit=5
```

### Frontend Check (in browser console):
```javascript
// Check if traces state has data
// This only works if you've added React DevTools
```

## Common Issues & Solutions

### Issue 1: Traces filtered by time despite disabled filter
**Symptom**: `total: 25, filtered: 0` in console
**Fix**: The edit might not have saved. Check line 73 of `Traces.tsx`:
```typescript
// Should look like this:
const filtered = traces; // traces.filter((trace) => new Date(trace.timestamp) >= cutoffTime);
```

### Issue 2: Input field type is wrong
**Symptom**: TypeScript error or wrong data type
**Fix**: Check the `BackendTrace` interface matches backend schema

### Issue 3: Empty inputMessages array
**Symptom**: Traces have empty inputMessages
**Fix**: Check that backend traces have input items with type "MESSAGE"

### Issue 4: Timestamp format mismatch
**Symptom**: Invalid Date errors in console
**Fix**: Backend returns ISO 8601 format, should work with `new Date()`

## Expected Data Flow

1. **Component Mounts** → `useEffect` triggers
2. **API Call** → `tracesApi.fetchTraces()` called
3. **Backend Response** → Array of BackendTrace objects
4. **Data Mapping** → Each BackendTrace mapped to frontend Trace type
5. **State Update** → `setTraces(fetchedTraces)`
6. **Memo Recalculation** → `filteredAndSortedTraces` updated
7. **Render** → TraceTable receives traces array
8. **Display** → Table rows render for each trace

## Where to Look

### Key Files:
- `frontend/src/pages/Traces.tsx` - Main component (line 73 has disabled filter)
- `frontend/src/services/tracesApi.ts` - API service and data mapping
- `frontend/src/components/trace/TraceTable.tsx` - Table display component

### Key State:
- `traces` - Raw data from API
- `filteredAndSortedTraces` - After filtering and sorting (currently just = traces)
- `isLoading` - Loading state
- `hasMore` - Pagination state

## What to Report Back

Please share:
1. **Console logs** - Copy the "Fetched traces" and "Filtering traces" logs
2. **Network tab** - Screenshot or copy the response from GET /traces
3. **Any errors** - Full error messages from console
4. **What you see** - "No traces found" or something else?

## Temporary Workaround

If all else fails, you can test with hardcoded data:

In `Traces.tsx`, after the useEffect that fetches traces, add:
```typescript
useEffect(() => {
  // Hardcoded test data
  setTraces([{
    id: "test-1",
    timestamp: new Date().toISOString(),
    status: "success",
    type: "text",
    endpoint: "/test",
    provider: "openai",
    model: "gpt-4",
    latency: 100,
    cost: 0,
    prompt: "Test",
    inputMessages: [],
    modelSettings: {},
    output: "Test output",
    rawRequest: "",
    rawResponse: "",
  }]);
}, []);
```

This will tell us if the problem is with:
- Data fetching (if hardcoded data shows up)
- Data rendering (if hardcoded data also doesn't show)

## Next Steps Based on Findings

1. **If traces show with hardcoded data** → Issue is with API fetch or data mapping
2. **If traces still don't show with hardcoded data** → Issue is with rendering logic
3. **If console shows traces but table is empty** → Issue in TraceTable component
4. **If filtered count is 0** → Time filtering not actually disabled
