# Task Grouping Documentation

## Overview

Traces are automatically grouped into tasks based on similarity of their path, model, and instructions. This grouping uses a **hybrid approach** combining automatic and batch processing.

## When Traces Are Grouped

### 1. Automatic Matching (On Trace Creation)

When a new trace is created via `POST /traces`, the system **automatically tries to match it to an existing task**.

- **Fast operation**: Only queries existing tasks, doesn't analyze other traces
- **Non-blocking**: If matching fails, trace creation still succeeds
- **Conditions**: Only matches if a similar task already exists

**Example**:

```bash
# First trace creates no task (no existing tasks to match)
POST /traces
{
  "model": "gpt-4",
  "path": "/greet",
  "instructions": "Greet user Alice politely",
  ...
}
# Result: trace.task_id = null

# After manually creating a task (see batch grouping below)...

# Second similar trace automatically matches existing task
POST /traces
{
  "model": "gpt-4",
  "path": "/greet",
  "instructions": "Greet user Bob politely",
  ...
}
# Result: trace.task_id = <existing_task_id>
```

### 2. Batch Grouping (Manual/Scheduled)

To create new tasks from ungrouped traces, use the batch grouping endpoint:

```bash
POST /tasks/group-traces?project_id=1&min_cluster_size=2&similarity_threshold=0.6
```

This endpoint:

- Finds all ungrouped traces (`task_id = null`)
- Groups them by path
- Analyzes instruction similarity
- Infers templates with placeholders (e.g., `{var_0}`, `{var_1}`)
- Creates new tasks for groups with ≥ `min_cluster_size` traces
- Assigns traces to their new tasks

**When to use**:

- Periodically (e.g., daily cron job) to batch-process new traces
- After importing historical data
- When you want to reorganize groupings with different parameters

### 3. Manual Grouping (Individual Traces)

Force a single trace to be grouped:

```bash
POST /traces/{trace_id}/group
```

This endpoint:

- Tries to match existing tasks first (fast)
- If no match, analyzes similar traces and creates a new task
- Useful for ungrouped traces that need immediate attention

## Grouping Algorithm

### Step 1: Path Grouping

Traces are first grouped by their `path` field (e.g., `/api/greet`, `/api/weather`).

### Step 2: Instruction Extraction

Instructions are extracted from:

1. `trace.instructions` field (if present)
2. System/developer messages in `trace.input_items`

### Step 3: Similarity Scoring

Traces are compared using:

- **70% Jaccard similarity**: Token overlap between instructions
- **30% Length similarity**: Penalizes very different lengths
- **Threshold**: Default 0.6 (configurable)

### Step 4: Template Inference

For grouped traces, a template is inferred:

- Identifies common parts
- Replaces variable parts with placeholders: `{{var_0}}`, `{{var_1}}`, etc.
- Example: `["Greet Alice", "Greet Bob"]` → `"Greet {{var_0}}"`

### Step 5: Task Creation

A task is created with:

- `path`: From traces
- `prompt`: Template inferred from trace prompts
- `instructions`: Template inferred from trace instructions
- `model`, `tools`, `temperature`, etc.: From reference trace

## Configuration

### Similarity Threshold

Controls how similar traces must be to group together:

- `0.6` (default): Moderate similarity required
- `0.8`: Strict - only very similar traces group
- `0.4`: Loose - more diverse traces group

### Min Cluster Size

Minimum traces needed to create a task:

- `2` (default): At least 2 similar traces
- `3+`: Requires more evidence before creating tasks

### Max Sample Size

Maximum traces used for template inference:

- `100` (default): Balance between accuracy and performance
- Higher values: More accurate templates but slower
- Lower values: Faster but may miss patterns

## Examples

### Example 1: Chat Greetings

**Traces**:

```
1. path="/chat", instructions="Say hello to Alice"
2. path="/chat", instructions="Say hello to Bob"
3. path="/chat", instructions="Say hello to Charlie"
```

**After batch grouping**:

```
Task created:
- path: "/chat"
- instructions: "Say hello to {{var_0}}"
- traces: [1, 2, 3]
```

### Example 2: Weather Queries

**Traces**:

```
1. path="/weather", instructions="Get weather for NYC"
2. path="/weather", instructions="Get weather for LA"
3. path="/weather", instructions="Get weather for Chicago"
```

**After batch grouping**:

```
Task created:
- path: "/weather"
- instructions: "Get weather for {{var_0}}"
- traces: [1, 2, 3]
```

### Example 3: Mixed Paths (No Grouping)

**Traces**:

```
1. path="/chat", instructions="Say hello to Alice"
2. path="/weather", instructions="Get weather for NYC"
```

**After batch grouping**:

```
No tasks created (different paths, only 1 trace per path)
```

## Workflow Recommendations

### For Development

1. Create traces normally via `POST /traces`
2. Traces auto-match to existing tasks
3. Periodically run batch grouping to create new tasks

### For Production

1. Set up a daily cron job:
    ```bash
    curl -X POST "https://api.example.com/tasks/group-traces?min_cluster_size=3"
    ```
2. Traces auto-match on creation (99% of cases)
3. Batch job handles the remaining 1% and creates new tasks

### For Data Import

1. Import all historical traces
2. Run batch grouping once:
    ```bash
    POST /tasks/group-traces?min_cluster_size=2&similarity_threshold=0.6
    ```
3. Future traces auto-match to created tasks

## API Endpoints Summary

| Endpoint                   | Purpose                     | When to Use                          |
| -------------------------- | --------------------------- | ------------------------------------ |
| `POST /traces`             | Create trace                | Always - auto-matches existing tasks |
| `POST /tasks/group-traces` | Batch create tasks          | Periodically or after imports        |
| `POST /traces/{id}/group`  | Force single trace grouping | For specific ungrouped traces        |

## Performance Considerations

### Fast: Auto-matching (on trace creation)

- **Latency**: +10-50ms per trace
- **Operations**: 1 query to find tasks, similarity comparison
- **When**: Every trace creation
- **Impact**: Minimal - trace creation remains fast

### Slow: Batch grouping

- **Latency**: Seconds to minutes depending on trace count
- **Operations**: Multiple queries, template inference, task creation
- **When**: Scheduled/manual batch operations
- **Impact**: Higher - should be run in background

## Monitoring

Track these metrics to optimize grouping:

- **Auto-match rate**: % of traces matched on creation
- **Ungrouped traces**: Traces with `task_id = null`
- **Tasks created**: New tasks per batch run
- **Grouping latency**: Time for batch operations

Ideal state:

- Auto-match rate: >90%
- Ungrouped traces: <100
- Batch runs: Daily or less frequent
