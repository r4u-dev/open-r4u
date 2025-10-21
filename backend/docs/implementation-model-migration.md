# Implementation Model Migration

## Overview

This document describes the migration from storing implementation details directly on the `Task` model to a separate `Implementation` model. This change provides better separation of concerns and allows multiple tasks to potentially share the same implementation configuration in the future.

## What Changed

### Database Schema

#### New `Implementation` Model

A new `implementation` table was created with the following fields:

- `id`: Primary key
- `version`: Implementation version (default: "0.1")
- `prompt`: The prompt/instructions for the LLM
- `model`: Model name (e.g., "gpt-4", "claude-3-opus")
- `temperature`: Temperature parameter (optional)
- `reasoning`: Reasoning configuration as JSONB (optional)
- `tools`: List of tool definitions as JSONB (optional)
- `tool_choice`: Tool choice configuration as JSONB (optional)
- `response_schema`: Response schema as JSONB (optional)
- `max_output_tokens`: Maximum output tokens
- `created_at`: Timestamp
- `updated_at`: Timestamp

#### Updated `Task` Model

The `Task` model was simplified to reference an `Implementation`:

**Removed fields:**
- `prompt`
- `model`
- `tools`
- `response_schema`
- `instructions`
- `temperature`
- `tool_choice`
- `reasoning`

**Added fields:**
- `implementation_id`: Foreign key to `implementation` table

**Retained fields:**
- `id`
- `project_id`
- `path`
- `created_at`
- `updated_at`

### API Changes

#### New `/implementations` Endpoints

```
GET    /implementations              - List all implementations
GET    /implementations/{id}         - Get specific implementation
POST   /implementations              - Create new implementation
PUT    /implementations/{id}         - Update implementation
DELETE /implementations/{id}         - Delete implementation
```

#### Updated `/tasks` Endpoints

The task creation endpoint now requires an `implementation` object:

**Before:**
```json
{
  "project": "My Project",
  "prompt": "You are a helpful assistant",
  "model": "gpt-4",
  "temperature": 0.7,
  "max_output_tokens": 1000
}
```

**After:**
```json
{
  "project": "My Project",
  "path": "/api/chat",
  "implementation": {
    "prompt": "You are a helpful assistant",
    "model": "gpt-4",
    "temperature": 0.7,
    "max_output_tokens": 1000
  }
}
```

Task responses now include the full `implementation` object:

```json
{
  "id": 1,
  "project_id": 1,
  "path": "/api/chat",
  "implementation": {
    "id": 1,
    "version": "0.1",
    "prompt": "You are a helpful assistant",
    "model": "gpt-4",
    "temperature": 0.7,
    "max_output_tokens": 1000,
    ...
  }
}
```

## Migration Instructions

### Running the Migration

The migration was created using Alembic:

```bash
cd backend
uv run alembic upgrade head
```

Migration file: `migrations/versions/5364e89c8105_add_implementation_model.py`

### Data Migration

**Important:** This migration assumes a fresh database. If you have existing data, you'll need to:

1. Create `Implementation` records from existing `Task` data
2. Update `Task` records to reference the new `Implementation` records
3. This can be done with a data migration script

Example data migration (not included):

```python
# Pseudo-code for migrating existing data
async def migrate_data(session):
    tasks = await session.execute(select(Task))
    for task in tasks:
        # Create implementation from task data
        impl = Implementation(
            prompt=task.prompt,
            model=task.model,
            temperature=task.temperature,
            tools=task.tools,
            response_schema=task.response_schema,
            tool_choice=task.tool_choice,
            reasoning=task.reasoning,
            max_output_tokens=4096  # default
        )
        session.add(impl)
        await session.flush()

        # Update task to reference implementation
        task.implementation_id = impl.id

    await session.commit()
```

## Testing

All core functionality is tested:

### Passing Tests
- ✅ `test_tasks.py` - All task CRUD operations (8 tests)
- ✅ `test_implementations.py` - All implementation CRUD operations (10 tests)

### Known Issues

#### Auto-Grouping Feature

The auto-grouping feature (`test_auto_grouping.py`) needs additional work:

1. **Service Updated**: The `task_grouping.py` service has been updated to create separate `Implementation` and `Task` records
2. **Not Integrated**: The auto-grouping is not currently integrated into the trace creation API
3. **Tests Failing**: Auto-grouping tests fail because the feature isn't wired up to the API endpoints

**To Fix:**
1. Integrate `try_match_existing_task()` into the trace creation endpoint
2. Update the auto-grouping logic to properly handle the new schema
3. Ensure eager loading of `implementation` relationship in queries

## Code Examples

### Creating a Task with Implementation

```python
from app.models.tasks import Implementation, Task
from app.models.projects import Project

# Create implementation
implementation = Implementation(
    prompt="You are a helpful assistant",
    model="gpt-4",
    max_output_tokens=2000,
    temperature=0.7,
    tools=[
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"}
                    }
                }
            }
        }
    ]
)
session.add(implementation)
await session.flush()

# Create task
task = Task(
    project_id=project.id,
    implementation_id=implementation.id,
    path="/api/weather"
)
session.add(task)
await session.commit()
```

### Querying Tasks with Implementation

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.tasks import Task

# Eager load implementation
query = (
    select(Task)
    .options(selectinload(Task.implementation))
    .where(Task.project_id == project_id)
)
result = await session.execute(query)
tasks = result.scalars().all()

for task in tasks:
    print(f"Task {task.id}: {task.implementation.model}")
```

## Benefits of This Change

1. **Separation of Concerns**: Implementation details are separated from task grouping logic
2. **Reusability**: Multiple tasks can potentially share the same implementation
3. **Version Control**: Each implementation has a version field for tracking changes
4. **Cleaner API**: Clear distinction between task metadata and LLM configuration
5. **Flexibility**: Easier to add new implementation-specific fields without cluttering the Task model

## Next Steps

1. ✅ Create Implementation model
2. ✅ Create migration
3. ✅ Update API endpoints
4. ✅ Create tests for new endpoints
5. ⚠️ Wire up auto-grouping to trace creation API (optional)
6. ⚠️ Create data migration script for existing databases (if needed)
7. 📝 Update API documentation
8. 📝 Update client SDKs
