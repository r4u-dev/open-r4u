# Background Task Grouping Architecture

## Overview

Task grouping is a CPU-intensive operation that analyzes trace instructions to find similar patterns and group them into tasks with templated prompts. To prevent blocking the main API request flow, task grouping runs in a separate background process.

## Problem Statement

The current implementation runs task grouping synchronously during trace creation:
- **Blocking**: API requests wait for CPU-intensive template matching to complete
- **No throttling**: Each new trace triggers grouping, even when previous grouping is still running
- **Resource waste**: Multiple grouping operations may run on overlapping data

## Solution Architecture

### Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Process                         │
│                                                                 │
│  ┌──────────────┐      ┌─────────────────────────────────┐   │
│  │ TracesService│─────▶│ TaskGroupingQueue (Singleton)   │   │
│  └──────────────┘      │                                 │   │
│                        │  - Queues grouping requests     │   │
│                        │  - Throttles duplicate requests │   │
│                        │  - Uses multiprocessing.Queue   │   │
│                        └─────────────────────────────────┘   │
│                                      │                         │
└──────────────────────────────────────│─────────────────────────┘
                                       │ multiprocessing.Queue
                                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Background Worker Process                    │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  TaskGroupingWorker                                      │ │
│  │                                                          │ │
│  │  1. Reads requests from queue (blocking)                │ │
│  │  2. Processes one request at a time (serialized)        │ │
│  │  3. Skips intermediate requests (throttling)            │ │
│  │  4. Performs CPU-intensive TemplateFinder operations    │ │
│  │  5. Creates tasks/implementations in database           │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Separate Process (not asyncio)**
   - Task grouping is CPU-bound (template matching, string analysis)
   - Python's GIL prevents true parallelism with asyncio
   - Multiprocessing allows the worker to use a separate CPU core

2. **Single Worker Process**
   - Only one grouping operation runs at a time
   - Prevents race conditions when creating tasks/implementations
   - Simpler than coordinating multiple workers with locks

3. **Request Throttling**
   - Queue tracks the latest request per (project_id, path) combination
   - When processing, skip if a newer request exists for same (project_id, path)
   - Prevents processing stale data when traces arrive rapidly

4. **Non-Blocking API**
   - `create_trace` returns immediately after queuing grouping request
   - Traces are created and returned to client without waiting
   - Grouping happens asynchronously in background

## Implementation Details

### 1. TaskGroupingQueue (Queue Manager)

**Location**: `backend/app/services/task_grouping_queue.py`

**Responsibilities**:
- Singleton pattern to ensure single queue instance
- Manages multiprocessing.Queue for sending requests to worker
- Tracks pending requests to enable throttling
- Thread-safe operations (uses threading.Lock)

**Key Methods**:
- `enqueue_grouping(project_id, path, trace_id)`: Add grouping request
- `get_pending_request(project_id, path)`: Check if newer request exists
- `start_worker()`: Launch background worker process
- `stop_worker()`: Gracefully shutdown worker

### 2. TaskGroupingWorker (Background Process)

**Location**: `backend/app/workers/task_grouping_worker.py`

**Responsibilities**:
- Runs in separate process
- Reads grouping requests from queue (blocking wait)
- Checks for newer requests before processing (throttling)
- Performs template matching with TemplateFinder
- Creates tasks and implementations in database
- Handles errors without crashing

**Processing Flow**:
```python
while True:
    request = queue.get()  # Blocking wait

    # Check if newer request exists (throttling)
    if has_newer_request(request):
        continue  # Skip this request

    # Perform grouping
    try:
        await group_and_create_tasks(request)
    except Exception as e:
        log_error(e)
```

### 3. Integration with TracesService

**Changes to `traces_service.py`**:
- Remove synchronous call to `_try_create_implementation_from_similar_traces`
- Replace with `queue_manager.enqueue_grouping(project_id, path, trace_id)`
- Trace creation returns immediately without waiting for grouping

**Before**:
```python
# In _auto_match_implementation
if not matching:
    await self._try_create_implementation_from_similar_traces(...)
```

**After**:
```python
# In _auto_match_implementation
if not matching:
    queue_manager.enqueue_grouping(project_id, trace.path, trace.id)
```

### 4. Lifecycle Management

**Startup** (in `app/main.py`):
```python
@app.on_event("startup")
async def startup_event():
    queue_manager = get_task_grouping_queue()
    queue_manager.start_worker()
```

**Shutdown** (in `app/main.py`):
```python
@app.on_event("shutdown")
async def shutdown_event():
    queue_manager = get_task_grouping_queue()
    queue_manager.stop_worker()
```

## Throttling Strategy

### Problem
If 10 traces arrive within 1 second while a grouping operation is running (takes ~5 seconds), we don't want to run grouping 10 times on overlapping data.

### Solution
Track the **latest** request for each (project_id, path) combination:

```python
pending_requests = {
    (project_id, path): {
        "trace_id": latest_trace_id,
        "timestamp": time.time()
    }
}
```

When worker processes a request:
1. Check if a **newer** trace_id exists for same (project_id, path)
2. If yes, skip current request (it's stale)
3. If no, proceed with grouping

**Example**:
- Trace 1 arrives → Queue grouping for (project_1, "/chat")
- Trace 2 arrives → Update pending to trace 2 for (project_1, "/chat")
- Trace 3 arrives → Update pending to trace 3 for (project_1, "/chat")
- Worker processes trace 1 → Sees trace 3 is pending → Skips trace 1
- Worker processes trace 2 → Sees trace 3 is pending → Skips trace 2
- Worker processes trace 3 → No newer request → Processes grouping

Result: Only 1 grouping operation for 3 traces (processes the last one)

## Database Access

### Challenge
The worker process needs database access but runs separately from FastAPI.

### Solution
Worker creates its own database session:
- Uses same connection string from settings
- Creates AsyncSession for each grouping operation
- Properly closes sessions after use
- Uses connection pooling for efficiency

```python
async def process_grouping_request(request):
    async with AsyncSessionLocal() as session:
        # Perform grouping with this session
        await create_tasks_from_grouping(session, request)
```

## Error Handling

### Worker Resilience
The worker must never crash from a single error:

```python
try:
    await process_grouping(request)
except Exception as e:
    logger.error(f"Grouping failed for {request}: {e}", exc_info=True)
    # Continue processing next request
```

### Queue Manager Resilience
- If worker process dies, log error but keep API running
- Provide health check endpoint to monitor worker status
- Consider auto-restart on worker crash (future enhancement)

## Performance Characteristics

### Before (Synchronous)
- Trace creation latency: **50-500ms** (includes grouping)
- API blocks during CPU-intensive template matching
- No parallelism (GIL)

### After (Asynchronous)
- Trace creation latency: **5-10ms** (just queue operation)
- API never blocks on grouping
- Grouping uses separate CPU core
- Throttling reduces redundant work

### Trade-offs
- **Pro**: Fast API responses, better scalability
- **Pro**: CPU-intensive work doesn't block other requests
- **Pro**: Automatic throttling reduces waste
- **Con**: Slight delay before tasks are created
- **Con**: More complex architecture
- **Con**: Requires process management

## Testing Strategy

### Unit Tests
- `test_task_grouping_queue.py`: Queue operations, throttling logic
- `test_task_grouping_worker.py`: Worker processing, error handling

### Integration Tests
- Test full flow: create trace → worker processes → verify task created
- Test throttling: create multiple traces rapidly → verify only last processed
- Test error recovery: inject error → verify worker continues

### Load Tests
- Create 100 traces rapidly → verify all get processed eventually
- Measure latency improvement vs synchronous version

## Future Enhancements

1. **Multiple Workers**: Process different (project_id, path) combinations in parallel
2. **Priority Queue**: Process certain projects or paths first
3. **Metrics**: Track queue depth, processing time, skip rate
4. **Health Checks**: Monitor worker liveness from API
5. **Auto-restart**: Automatically restart worker if it crashes
6. **Distributed Queue**: Use Redis instead of multiprocessing.Queue for horizontal scaling

## Migration Path

1. ✅ Create queue manager and worker modules
2. ✅ Add lifecycle hooks to main.py
3. ✅ Modify TracesService to use queue
4. ✅ Write tests for new components
5. ✅ Deploy and monitor
6. 🔄 Remove old synchronous grouping code after validation

## Configuration

New settings in `app/config.py`:

```python
class Settings(BaseSettings):
    # Existing settings...

    # Task grouping settings
    task_grouping_enabled: bool = True
    task_grouping_queue_size: int = 1000
    task_grouping_worker_timeout: int = 300  # 5 minutes
```

## Monitoring

Log key events:
- Request enqueued: `logger.info(f"Enqueued grouping for trace {trace_id}")`
- Request skipped: `logger.info(f"Skipped grouping for trace {trace_id} (newer request exists)")`
- Request processed: `logger.info(f"Processed grouping for trace {trace_id}, created {n} tasks")`
- Worker errors: `logger.error(f"Worker error: {error}", exc_info=True)`

Metrics to track:
- Queue depth over time
- Processing time per request
- Skip rate (throttling effectiveness)
- Error rate

## Summary

This architecture moves CPU-intensive task grouping to a background worker process, enabling:
- ✅ **Fast API responses**: Trace creation returns immediately
- ✅ **Serialized processing**: One grouping at a time prevents race conditions
- ✅ **Automatic throttling**: Only processes latest request per (project, path)
- ✅ **Better resource utilization**: Worker uses separate CPU core
- ✅ **Resilient**: Errors in grouping don't affect API stability
