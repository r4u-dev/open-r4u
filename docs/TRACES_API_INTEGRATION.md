# Traces API Integration

This document describes the integration of the traces API with the frontend, including infinite scrolling pagination support.

## Overview

The traces feature now fetches real data from the backend API instead of using mock data. The implementation includes:

- **Backend**: Pagination support with `limit` and `offset` parameters
- **Frontend**: API service to fetch traces with infinite scrolling
- **Tests**: Comprehensive pagination tests

## Backend Changes

### API Endpoint: `/traces`

**File**: `backend/app/api/v1/traces.py`

The `list_traces` endpoint now supports pagination:

```python
@router.get("", response_model=list[TraceRead])
async def list_traces(
    limit: int = Query(25, ge=1, le=100, description="Number of traces to return"),
    offset: int = Query(0, ge=0, description="Number of traces to skip"),
    session: AsyncSession = Depends(get_session),
) -> list[TraceRead]:
```

**Parameters**:
- `limit`: Number of traces to return (default: 25, min: 1, max: 100)
- `offset`: Number of traces to skip (default: 0, min: 0)

**Response**: List of `TraceRead` objects ordered by `started_at` descending (newest first)

**Examples**:
```bash
# Get first 25 traces (default)
GET /traces

# Get first 10 traces
GET /traces?limit=10

# Get next 10 traces (skip first 10)
GET /traces?limit=10&offset=10

# Get maximum allowed (100 traces)
GET /traces?limit=100
```

### Tests

**File**: `backend/tests/test_traces.py`

Added two new test methods:

1. `test_list_traces_with_pagination`: Tests pagination with various limit/offset combinations
2. `test_list_traces_pagination_limits`: Tests parameter validation (min/max limits)

Run tests:
```bash
cd backend
uv run pytest tests/test_traces.py -v
```

## Frontend Changes

### API Service

**File**: `frontend/src/services/tracesApi.ts`

New service to interact with the traces API:

```typescript
export const tracesApi = {
  /**
   * Fetch traces with pagination support
   */
  async fetchTraces(params: FetchTracesParams = {}): Promise<Trace[]> {
    const { limit = 25, offset = 0 } = params;
    // ...
  },

  /**
   * Fetch a single trace by ID
   */
  async fetchTraceById(id: string): Promise<Trace | null> {
    // ...
  },
};
```

#### Data Mapping

The service includes a `mapBackendTraceToFrontend` function that transforms backend trace data to match the frontend's `Trace` interface:

**Backend Fields → Frontend Fields**:
- `id` (number) → `id` (string)
- `started_at` → `timestamp`
- `error` → `status` ("error" if error exists, otherwise "success")
- `error` → `errorMessage`
- `model` → Provider detection (openai, anthropic, google, etc.)
- `model` → Type detection (text, image, audio)
- `path` → `endpoint`
- `result` → `output`
- `input` (array of InputItem) → `inputMessages` (filtered MESSAGE types)
- Token fields → `modelSettings`
- `started_at` + `completed_at` → `latency` (calculated)

**Fields Not Available from Backend** (left empty):
- `cost`: Set to 0 (cost calculation not yet implemented)
- `taskVersion`: Set to undefined (task name not available)
- `rawRequest`: Empty string (not stored in backend)
- `rawResponse`: Empty string (not stored in backend)

### Traces Page

**File**: `frontend/src/pages/Traces.tsx`

The Traces page now:

1. **Fetches real data** from the API on mount
2. **Implements infinite scrolling** with Intersection Observer
3. **Loads more traces** automatically when scrolling to the bottom
4. **Filters by time period** (client-side filtering)
5. **Sorts traces** (client-side sorting)

Key changes:
- Removed dependency on `mockTraces`
- Added `traces` state to store fetched data
- Added `hasMore` state to track if more data is available
- Modified `loadMoreTraces` to fetch from API instead of slicing local data
- Updated `handleTimePeriodChange` to refetch from API

### API Configuration

**File**: `frontend/src/services/api.ts`

Updated default API URL:
```typescript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
```

Changed from port 4000 to 8000 to match the backend's default port.

## Usage

### Running the Application

1. **Start the backend**:
```bash
cd backend
uv run uvicorn app.main:app --reload
```
The API will be available at `http://localhost:8000`

2. **Start the frontend**:
```bash
cd frontend
npm run dev
# or
pnpm dev
```
The frontend will be available at `http://localhost:8080`

3. **Navigate to the Traces page** and verify:
   - Traces load from the API
   - Infinite scrolling works when scrolling to the bottom
   - Time period filter triggers a new API fetch
   - Empty state shows when no traces exist

### Testing the API

**Create a test trace**:
```bash
curl -X POST http://localhost:8000/traces \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "input": [
      {"type": "message", "role": "user", "content": "Hello!"}
    ],
    "result": "Hi there!",
    "started_at": "2025-01-15T10:00:00Z",
    "completed_at": "2025-01-15T10:00:02Z"
  }'
```

**List traces with pagination**:
```bash
# First page
curl http://localhost:8000/traces?limit=10&offset=0

# Second page
curl http://localhost:8000/traces?limit=10&offset=10
```

## Future Improvements

1. **Cost Calculation**: Implement cost calculation based on token usage and model pricing
2. **Task/Implementation Integration**: Display task version when traces are linked to implementations
3. **Raw Request/Response Storage**: Store and display raw HTTP request/response data
4. **Server-Side Filtering**: Add time period filtering to the API
5. **Server-Side Sorting**: Add sorting parameters to the API
6. **Single Trace Endpoint**: Add `GET /traces/{id}` endpoint
7. **Total Count**: Return total count in response headers or metadata for better pagination UI
8. **Cursor-Based Pagination**: Consider cursor-based pagination for better performance with large datasets

## Architecture Diagram

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│  Frontend       │         │  Backend API    │         │  Database       │
│  (React)        │         │  (FastAPI)      │         │  (PostgreSQL)   │
│                 │         │                 │         │                 │
│  Traces.tsx     │──GET───▶│  /traces        │         │                 │
│                 │         │  ?limit=25      │         │                 │
│  • Infinite     │         │  &offset=0      │         │                 │
│    scroll       │         │                 │         │                 │
│  • Time filter  │         │  Pagination ────┼────────▶│  SELECT *       │
│  • Sort         │         │  • limit        │         │  FROM trace     │
│                 │         │  • offset       │         │  ORDER BY       │
│                 │◀────────┤  • validation   │◀────────┤  started_at     │
│  Display traces │  JSON   │                 │  Rows   │  LIMIT 25       │
│                 │         │  TraceRead[]    │         │  OFFSET 0       │
└─────────────────┘         └─────────────────┘         └─────────────────┘
```

## Related Files

- **Backend**:
  - `backend/app/api/v1/traces.py` - API endpoints
  - `backend/app/models/traces.py` - Database models
  - `backend/app/schemas/traces.py` - Pydantic schemas
  - `backend/tests/test_traces.py` - Tests

- **Frontend**:
  - `frontend/src/pages/Traces.tsx` - Main traces page
  - `frontend/src/services/tracesApi.ts` - API service
  - `frontend/src/services/api.ts` - Base API client
  - `frontend/src/lib/types/trace.ts` - Type definitions

## Migration Notes

- **No database migrations required** - Pagination is query-level only
- **No breaking changes** - Endpoint is backward compatible (default behavior unchanged)
- **Mock data preserved** - `frontend/src/lib/mock-data/traces.ts` still exists but is no longer used
