# Output Items Support for OpenAI Responses API

This document describes the implementation of output items support in the traces schema, making it compatible with the OpenAI Responses API.

## Overview

The trace schema has been updated to support structured output items from LLM responses instead of a simple string result. This change makes the system fully compatible with the OpenAI Responses API output format.

## Changes Made

### 1. Schema Changes (`backend/app/schemas/traces.py`)

#### New Output Item Types

Added comprehensive Pydantic models for all OpenAI Responses API output item types:

- **`OutputMessageItem`** - Assistant messages with content
- **`FileSearchToolCallItem`** - File search tool call results
- **`FunctionToolCallItem`** - Function tool call outputs
- **`WebSearchToolCallItem`** - Web search tool call outputs
- **`ComputerToolCallItem`** - Computer use tool call outputs
- **`ReasoningOutputItem`** - Reasoning traces from reasoning models
- **`ImageGenToolCallItem`** - Image generation outputs
- **`CodeInterpreterToolCallItem`** - Code interpreter execution outputs
- **`LocalShellToolCallItem`** - Local shell command outputs
- **`MCPToolCallItem`** - MCP (Model Context Protocol) tool call outputs
- **`MCPListToolsItem`** - MCP server tool listings
- **`MCPApprovalRequestItem`** - MCP approval requests
- **`CustomToolCallItem`** - Custom tool call outputs

#### Union Type

```python
OutputItem = (
    OutputMessageItem
    | FileSearchToolCallItem
    | FunctionToolCallItem
    | WebSearchToolCallItem
    | ComputerToolCallItem
    | ReasoningOutputItem
    | ImageGenToolCallItem
    | CodeInterpreterToolCallItem
    | LocalShellToolCallItem
    | MCPToolCallItem
    | MCPListToolsItem
    | MCPApprovalRequestItem
    | CustomToolCallItem
)
```

#### Schema Updates

- **`TraceBase.result`**: Changed from `str | None` to `list[OutputItem] | None`
- **`TraceCreate`**: Added validator for `result` field
- **`TraceRead.result`**: Maps to `output_items` relationship from database

### 2. Model Changes (`backend/app/models/traces.py`)

#### Removed Field

- Removed `result` text column from `Trace` model (no longer storing as string)

#### New Model

Added `TraceOutputItem` model to store individual output items:

```python
class TraceOutputItem(Base):
    """Individual output item belonging to a trace."""

    id: Mapped[intpk]
    trace_id: Mapped[int]
    type: Mapped[str]  # Discriminator for output item type
    data: Mapped[dict[str, Any]]  # JSONB storage of item data
    position: Mapped[int]  # Order in output array
```

#### Relationship

Added `output_items` relationship to `Trace` model:

```python
output_items: Mapped[list["TraceOutputItem"]] = relationship(
    "TraceOutputItem",
    back_populates="trace",
    cascade="all, delete-orphan",
    order_by="TraceOutputItem.position",
)
```

### 3. Service Changes (`backend/app/services/traces_service.py`)

Updated `TracesService.create_trace()` to:

1. Process output items from `trace_data.result`
2. Create `TraceOutputItem` records for each output item
3. Store item type and serialized data
4. Eager-load `output_items` relationship when returning traces

### 4. Database Migration

Created migration `1702f8060263_add_output_items_support.py`:

- Creates `trace_output_item` table with indexes
- Drops `result` text column from `trace` table
- Provides downgrade path for rollback

## Usage Examples

### Creating a Trace with Output Items

```python
from datetime import datetime
from app.schemas.traces import (
    TraceCreate,
    OutputMessageItem,
    OutputMessageContent,
    MessageItem,
    MessageRole,
)

# Simple message output
trace = TraceCreate(
    model="gpt-4",
    input=[MessageItem(role=MessageRole.USER, content="Hello")],
    result=[
        OutputMessageItem(
            id="msg-123",
            content=[
                OutputMessageContent(type="text", text="Hi there!")
            ],
            status="completed",
        )
    ],
    started_at=datetime.now(),
    project="My Project",
)
```

### Function Tool Call Output

```python
from app.schemas.traces import FunctionToolCallItem

trace = TraceCreate(
    model="gpt-4",
    input=[...],
    result=[
        FunctionToolCallItem(
            id="call-456",
            call_id="call_abc123",
            name="get_weather",
            arguments='{"location": "San Francisco"}',
            status="completed",
        )
    ],
    started_at=datetime.now(),
)
```

### Reasoning Model Output

```python
from app.schemas.traces import ReasoningOutputItem, ReasoningSummary

trace = TraceCreate(
    model="gpt-4o-reasoning",
    input=[...],
    result=[
        ReasoningOutputItem(
            id="reasoning-789",
            summary=[
                ReasoningSummary(type="text", text="Analyzing the problem...")
            ],
            content=[],
            status="completed",
        )
    ],
    started_at=datetime.now(),
)
```

### Multiple Output Items

```python
# A trace can have multiple output items
trace = TraceCreate(
    model="gpt-4",
    input=[...],
    result=[
        OutputMessageItem(id="msg-1", content=[...]),
        FunctionToolCallItem(id="call-1", ...),
        OutputMessageItem(id="msg-2", content=[...]),
    ],
    started_at=datetime.now(),
)
```

## Reading Traces

When reading traces via the API, output items are automatically loaded:

```python
# GET /api/v1/traces/{trace_id}
{
    "id": 123,
    "model": "gpt-4",
    "result": [
        {
            "id": 1,
            "type": "message",
            "data": {
                "id": "msg-123",
                "role": "assistant",
                "content": [{"type": "text", "text": "Hi there!"}],
                "status": "completed"
            },
            "position": 0
        }
    ],
    "input": [...],
    ...
}
```

## Compatibility Notes

### OpenAI Responses API

All output item types follow the OpenAI Responses API specification:

- Each item has a `type` discriminator field
- Item-specific fields match OpenAI's schema
- `extra="allow"` in Pydantic models for forward compatibility

### Backward Compatibility

- Old traces with `result` as text will be migrated (if any exist)
- The migration provides a downgrade path
- API consumers should check for `result` type (string vs array)

## Testing

### Unit Tests

Test creating traces with various output item types:

```python
def test_create_trace_with_output_items():
    trace_data = TraceCreate(
        model="gpt-4",
        input=[MessageItem(role=MessageRole.USER, content="test")],
        result=[
            OutputMessageItem(
                id="msg-1",
                content=[{"type": "text", "text": "response"}],
            )
        ],
        started_at=datetime.now(),
    )

    assert isinstance(trace_data.result, list)
    assert len(trace_data.result) == 1
    assert trace_data.result[0].type == "message"
```

### Integration Tests

Test full trace lifecycle with output items:

1. Create trace with output items
2. Verify items are stored correctly
3. Retrieve trace and verify output items
4. Update trace with new output items
5. Delete trace and verify cascade deletion

## Future Enhancements

1. **Validation**: Add cross-field validation for output items
2. **Indexing**: Consider adding GIN indexes on JSONB data for common queries
3. **Streaming**: Support streaming output items as they're generated
4. **Analytics**: Add aggregation queries for output item types
5. **Compression**: Consider compressing large output items (e.g., images)

## Migration Guide

### For Developers

If you have code that accesses `trace.result` as a string:

**Before:**
```python
if trace.result:
    print(f"Result: {trace.result}")
```

**After:**
```python
if trace.result:
    for item in trace.result:
        if item.type == "message":
            print(f"Message: {item.content}")
```

### For API Consumers

Update your client code to handle `result` as an array of output items:

**Before:**
```javascript
const result = trace.result; // string
```

**After:**
```javascript
const result = trace.result; // array of OutputItem
const messages = result.filter(item => item.type === 'message');
```

## References

- [OpenAI Responses API Documentation](https://platform.openai.com/docs/api-reference/responses)
- [OpenAPI Specification](../../openapi.documented.yml)
- [Schema Definitions](../app/schemas/traces.py)
- [Model Definitions](../app/models/traces.py)
