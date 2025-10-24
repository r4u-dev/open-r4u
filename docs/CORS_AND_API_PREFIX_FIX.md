# CORS and API Prefix Fix

## Problem

The frontend was unable to communicate with the backend due to two issues:

1. **CORS Error (405 Method Not Allowed)**: The backend wasn't configured to accept requests from the frontend origin (localhost:8080)
2. **API Prefix Mismatch**: Frontend services were using `/v1/` prefix in API paths, but backend endpoints don't have this prefix

## Solutions Implemented

### 1. Added CORS Middleware to Backend

**File**: `backend/app/main.py`

Added CORS middleware to allow requests from the frontend:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://localhost:3000",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Allowed Origins**:
- `http://localhost:8080` - Default Vite dev server
- `http://localhost:3000` - Alternative React dev server
- `http://127.0.0.1:8080` - IPv4 localhost
- `http://127.0.0.1:3000` - IPv4 localhost alternative

### 2. Fixed Frontend API Prefixes

Removed incorrect `/v1/` prefix from frontend API services to match backend routes.

#### Changes Made:

**File**: `frontend/src/services/evaluationsApi.ts`
```typescript
// Before
private baseEndpoint = '/v1/evaluations';

// After
private baseEndpoint = '/evaluations';
```

**File**: `frontend/src/services/testCasesApi.ts`
```typescript
// Before
private baseEndpoint = '/v1/test-cases';

// After
private baseEndpoint = '/test-cases';
```

**File**: `frontend/src/services/tracesApi.ts`
```typescript
// Already correct - no prefix needed
const response = await apiClient.get<BackendTrace[]>(
  `/traces?${queryParams.toString()}`
);
```

## Backend API Routes

The backend exposes routes **without** a `/v1/` prefix:

```
GET  /health
GET  /projects
GET  /tasks
GET  /traces                  ✅ Traces endpoint
POST /traces
GET  /implementations
GET  /executions
GET  /graders
GET  /grades
GET  /http-traces
```

## Testing

### Test CORS is Working

```bash
# From frontend (with dev server running on localhost:8080)
curl -H "Origin: http://localhost:8080" \
     -H "Access-Control-Request-Method: GET" \
     -X OPTIONS \
     http://localhost:8000/traces -v
```

Expected headers in response:
```
access-control-allow-origin: http://localhost:8080
access-control-allow-credentials: true
access-control-allow-methods: *
access-control-allow-headers: *
```

### Test API Endpoint

```bash
# Direct API test
curl http://localhost:8000/traces?limit=10
```

Should return JSON array of traces, not 405 error.

### Test Frontend Integration

1. Start backend: `cd backend && uv run uvicorn app.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Open browser to `http://localhost:8080`
4. Navigate to Traces page
5. Check browser console - should see successful API requests
6. Check Network tab - should see 200 responses, not 405

## Important Notes

### Missing Backend Endpoints

The following frontend services reference endpoints that **don't exist** in the backend:

- ❌ `/evaluations` - evaluationsApi will fail
- ❌ `/test-cases` - testCasesApi will fail

These need to be either:
1. Implemented in the backend
2. Removed from frontend if not needed
3. Updated to use different endpoints

### Working Endpoints

- ✅ `/traces` - Fully implemented with pagination
- ✅ `/projects` - Exists in backend
- ✅ `/tasks` - Exists in backend
- ✅ `/implementations` - Exists in backend
- ✅ `/http-traces` - Exists in backend

## Production Considerations

For production deployment, update CORS origins to include:

```python
allow_origins=[
    "https://yourdomain.com",
    "https://www.yourdomain.com",
    # Add your production domains
]
```

Or use environment variables:

```python
import os

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8080").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Verification Checklist

- [x] CORS middleware added to backend
- [x] Backend allows localhost:8080 origin
- [x] evaluationsApi prefix fixed
- [x] testCasesApi prefix fixed
- [x] tracesApi using correct path
- [x] Backend tests still passing
- [x] Frontend builds successfully
- [ ] Frontend can fetch traces (test manually)
- [ ] No CORS errors in browser console
- [ ] No 405 errors in Network tab

## Related Files

- `backend/app/main.py` - CORS configuration
- `frontend/src/services/api.ts` - Base API client
- `frontend/src/services/tracesApi.ts` - Traces API
- `frontend/src/services/evaluationsApi.ts` - Evaluations API (needs backend endpoint)
- `frontend/src/services/testCasesApi.ts` - Test Cases API (needs backend endpoint)

## Next Steps

1. **Test the integration**: Start both servers and verify traces load in frontend
2. **Implement missing endpoints**: Add `/evaluations` and `/test-cases` to backend if needed
3. **Environment configuration**: Move CORS origins to environment variables
4. **Security review**: Ensure CORS settings are appropriate for production
