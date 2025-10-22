# Implementation Versions

## Overview

The Implementation Versions feature allows you to manage multiple versions of LLM configurations for each task. This enables A/B testing, rollback capabilities, and version tracking of your prompts and model configurations.

## Concepts

### Task
A **Task** represents a logical grouping of similar API calls or use cases (e.g., "customer support chat", "weather queries"). Each task can have multiple implementation versions.

### Implementation
An **Implementation** is a specific version of the LLM configuration for a task. It includes:
- Prompt/instructions
- Model name
- Temperature and other parameters
- Tools configuration
- Response schema
- Reasoning configuration

### Production Version
Each task has a `production_version_id` that points to the implementation currently deployed in production. This allows you to:
- Deploy new versions without affecting production
- Easily switch between versions
- Roll back to previous versions if needed

## Data Model

```
Project (1) ──→ (many) Task (1) ──→ (many) Implementation
                       │
                       └──→ production_version_id ──→ Implementation
```

**Relationships:**
- A Task belongs to one Project
- A Task has many Implementations (versions)
- A Task has one production_version (nullable reference to an Implementation)
- An Implementation belongs to one Task

## Database Schema

### Task Table
- `id`: Primary key
- `project_id`: Foreign key to project
- `path`: API path (e.g., "/api/chat")
- `production_version_id`: Foreign key to implementation (nullable)
- `created_at`, `updated_at`: Timestamps

### Implementation Table
- `id`: Primary key
- `task_id`: Foreign key to task (CASCADE DELETE)
- `version`: Version string (e.g., "1.0", "1.1", "2.0-beta")
- `prompt`: The prompt text
- `model`: Model name (e.g., "gpt-4", "claude-3-opus")
- `temperature`: Temperature parameter (optional)
- `reasoning`: Reasoning configuration as JSONB (optional)
- `tools`: List of tool definitions as JSONB (optional)
- `tool_choice`: Tool choice configuration as JSONB (optional)
- `response_schema`: Response schema as JSONB (optional)
- `max_output_tokens`: Maximum output tokens
- `created_at`, `updated_at`: Timestamps

## API Endpoints

### Tasks

#### Create Task
Creates a new task with an initial implementation version.

```http
POST /tasks
Content-Type: application/json

{
  "project": "My Project",
  "path": "/api/chat",
  "implementation": {
    "version": "1.0",
    "prompt": "You are a helpful assistant",
    "model": "gpt-4",
    "max_output_tokens": 2000,
    "temperature": 0.7
  }
}
```

**Response:**
```json
{
  "id": 1,
  "project_id": 1,
  "path": "/api/chat",
  "production_version_id": 1
}
```

#### List Tasks
```http
GET /tasks
GET /tasks?project_id=1
```

#### Get Task
```http
GET /tasks/{task_id}
```

#### Delete Task
Deletes a task and all its implementations (cascade).

```http
DELETE /tasks/{task_id}
```

### Implementations

#### Create Implementation Version
Creates a new implementation version for a task.

```http
POST /implementations?task_id=1
Content-Type: application/json

{
  "version": "1.1",
  "prompt": "You are a helpful assistant with improved capabilities",
  "model": "gpt-4-turbo",
  "max_output_tokens": 4000,
  "temperature": 0.8
}
```

**Response:**
```json
{
  "id": 2,
  "task_id": 1,
  "version": "1.1",
  "prompt": "You are a helpful assistant with improved capabilities",
  "model": "gpt-4-turbo",
  "max_output_tokens": 4000,
  "temperature": 0.8
}
```

#### List Implementations
```http
GET /implementations                  # All implementations
GET /implementations?task_id=1       # Implementations for specific task
```

#### Get Implementation
```http
GET /implementations/{implementation_id}
```

#### Update Implementation
```http
PUT /implementations/{implementation_id}
Content-Type: application/json

{
  "version": "1.1.1",
  "prompt": "Updated prompt",
  "model": "gpt-4-turbo",
  "max_output_tokens": 4000
}
```

#### Delete Implementation
```http
DELETE /implementations/{implementation_id}
```

#### Set Production Version
Sets an implementation as the production version for its task.

```http
POST /implementations/{implementation_id}/set-production
```

**Response:** Returns the implementation that was set as production.

## Usage Examples

### Example 1: Creating a Task with Initial Version

```python
import httpx

async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
    response = await client.post("/tasks", json={
        "project": "Customer Support",
        "path": "/api/support/chat",
        "implementation": {
            "version": "1.0",
            "prompt": "You are a customer support assistant. Be helpful and professional.",
            "model": "gpt-4",
            "max_output_tokens": 2000,
            "temperature": 0.7
        }
    })
    task = response.json()
    print(f"Created task {task['id']} with production version {task['production_version_id']}")
```

### Example 2: Creating a New Version

```python
# Create a new version with improved prompt
response = await client.post(
    f"/implementations?task_id={task['id']}",
    json={
        "version": "1.1",
        "prompt": "You are a customer support assistant. Be helpful, professional, and empathetic.",
        "model": "gpt-4",
        "max_output_tokens": 2000,
        "temperature": 0.7
    }
)
new_version = response.json()
print(f"Created version {new_version['version']} with id {new_version['id']}")
```

### Example 3: Switching to New Version

```python
# Set new version as production
response = await client.post(f"/implementations/{new_version['id']}/set-production")
print(f"Switched to version {new_version['version']}")

# Verify the task's production version was updated
task_response = await client.get(f"/tasks/{task['id']}")
updated_task = task_response.json()
assert updated_task['production_version_id'] == new_version['id']
```

### Example 4: Rolling Back

```python
# Roll back to previous version
response = await client.post(f"/implementations/{previous_version_id}/set-production")
print("Rolled back to previous version")
```

### Example 5: Listing All Versions

```python
# Get all versions for a task
response = await client.get(f"/implementations?task_id={task['id']}")
versions = response.json()

print(f"Task has {len(versions)} versions:")
for impl in versions:
    is_production = "🟢 PRODUCTION" if impl['id'] == task['production_version_id'] else ""
    print(f"  - v{impl['version']}: {impl['model']} {is_production}")
```

## Workflow Patterns

### Pattern 1: Gradual Rollout

1. Create new implementation version
2. Test with a small percentage of traffic (handled by your application logic)
3. Monitor metrics
4. Set as production if successful

```python
# 1. Create new version
new_impl = create_implementation(task_id, version="2.0", ...)

# 2. Your application routes 10% of traffic to new_impl
# (This is handled in your application code, not the API)

# 3. If metrics look good, promote to production
set_production_version(new_impl['id'])
```

### Pattern 2: A/B Testing

1. Create multiple versions (A and B)
2. Your application randomly assigns users to versions
3. Track metrics for each version
4. Promote the winner to production

```python
# Create variant A
impl_a = create_implementation(task_id, version="2.0-A", ...)

# Create variant B
impl_b = create_implementation(task_id, version="2.0-B", ...)

# Your app randomly chooses between impl_a and impl_b
# After collecting data, promote the winner:
set_production_version(winner_impl['id'])
```

### Pattern 3: Environment-Based Versions

1. Create versions for different environments
2. Use different production_version_id for dev/staging/prod

```python
# Development
dev_impl = create_implementation(task_id, version="2.0-dev", ...)

# Staging
staging_impl = create_implementation(task_id, version="2.0-staging", ...)

# Production
prod_impl = create_implementation(task_id, version="2.0", ...)

# Your deployment pipeline sets the appropriate version
# based on the environment
```

## Best Practices

### Versioning Strategy
- Use semantic versioning: `major.minor.patch` (e.g., "1.2.3")
- Use suffixes for pre-release versions: "2.0-beta", "2.0-rc1"
- Keep version names descriptive and sortable

### Version Management
- **Never delete** the production version without setting a new one first
- Keep at least 2-3 previous versions for quick rollback
- Document significant changes in version notes (store in a separate system)

### Testing
- Always test new versions in a non-production environment first
- Compare metrics between versions before promoting
- Have a rollback plan ready

### Cascading Deletes
- Deleting a task will delete all its implementations
- Be careful when deleting tasks - this is irreversible
- Consider soft deletes if you need an audit trail

## Migration from Old Schema

If you're migrating from the old schema where task fields were stored directly on the task:

```python
# Old schema (deprecated)
task = {
    "project_id": 1,
    "path": "/api/chat",
    "prompt": "You are helpful",
    "model": "gpt-4",
    "temperature": 0.7,
    ...
}

# New schema
# 1. Create task
task = create_task(
    project="My Project",
    path="/api/chat",
    implementation={
        "version": "1.0",
        "prompt": "You are helpful",
        "model": "gpt-4",
        "temperature": 0.7,
        ...
    }
)

# 2. Task now has production_version_id pointing to the implementation
```

## Database Queries

### Get Task with Production Implementation

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.tasks import Task, Implementation

# Eager load production version
query = (
    select(Task)
    .options(selectinload(Task.production_version))
    .where(Task.id == task_id)
)
result = await session.execute(query)
task = result.scalar_one()

if task.production_version:
    print(f"Production version: {task.production_version.version}")
    print(f"Model: {task.production_version.model}")
```

### Get All Versions for a Task

```python
query = (
    select(Implementation)
    .where(Implementation.task_id == task_id)
    .order_by(Implementation.created_at.desc())
)
result = await session.execute(query)
implementations = result.scalars().all()
```

## Security Considerations

- Only authorized users should be able to set production versions
- Consider adding approval workflows for production version changes
- Log all version changes for audit purposes
- Implement rate limiting on version creation to prevent abuse

## Performance Tips

- Index on `task_id` in the implementation table (already done)
- Index on `production_version_id` in the task table (already done)
- Use eager loading when fetching tasks with their production versions
- Cache production version information in your application layer

## Troubleshooting

### Issue: Cannot delete implementation that is set as production
**Solution:** Set a different implementation as production first, then delete.

```python
# Set another version as production
set_production_version(other_impl_id)

# Now you can delete the old one
delete_implementation(old_impl_id)
```

### Issue: Task has no production version
**Solution:** This is allowed in the schema. Set a production version:

```python
# List all implementations for the task
implementations = list_implementations(task_id)

# Set one as production
set_production_version(implementations[0]['id'])
```

### Issue: Circular dependency warning in migrations
**Solution:** This is expected due to the bidirectional relationship between Task and Implementation. The migration will still work correctly.

## Related Features

- **Traces**: Link traces to tasks to see which implementation version was used
- **Evaluation**: Compare metrics across different implementation versions
- **Projects**: Organize tasks and their implementations by project
