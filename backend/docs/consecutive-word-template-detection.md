# Consecutive Word-Based Template Detection

## Overview

Open R4U uses an intelligent template detection algorithm to automatically group similar traces and infer common prompt templates. As of the latest version, the system uses a **consecutive word-based approach** to identify template patterns.

## Problem Statement

Previously, template detection used heuristic-based rules that could fail in certain scenarios:

- **Large argument values**: When traces had very large variable values (e.g., long descriptions, comprehensive text), the ratio of template tokens to placeholder tokens would be too small, causing false negatives
- **Inconsistent grouping**: Short common phrases might be matched even when they weren't meaningful templates

## Solution: Consecutive Word Detection

The new approach uses a simple but powerful rule:

> **Two traces will be grouped together if they have at least `n` consecutive words in common.**

### What Counts as a Word?

- **Words**: Alphanumeric sequences (e.g., `Hello`, `user123`, `Bob`)
- **Not words**: Punctuation, whitespace, special characters (e.g., `,`, `.`, `!`, spaces)

### Example

Given these traces with `min_consecutive_words=3`:

```
"You are a personal assistant for Mr. Smith"
"You are a personal assistant for Mr. Johnson"
```

The algorithm detects:
- "You are a personal assistant for Mr" = 7 consecutive words ✅
- This exceeds the threshold of 3, so it becomes a template anchor
- Result: `"You are a personal assistant for Mr. {{var_0}}"`

## Configuration

### Default Value

The default `min_consecutive_words` is **3**, which works well for most use cases.

### Configuring the Threshold

#### 1. When Creating Traces (TracesService)

```python
from app.services.traces_service import TracesService

service = TracesService(
    min_cluster_size=3,
    min_consecutive_words=5  # Require 5 consecutive words
)
```

#### 2. When Using TaskGrouper Directly

```python
from app.services.task_grouping import TaskGrouper

grouper = TaskGrouper(
    session,
    min_cluster_size=3,
    similarity_threshold=0.6,
    min_consecutive_words=4  # Require 4 consecutive words
)
```

#### 3. Via API Endpoint

```bash
POST /v1/tasks/group
{
  "similarity_threshold": 0.6,
  "min_cluster_size": 2,
  "min_consecutive_words": 5
}
```

#### 4. Using Template Inference Directly

```python
from app.services.template_inference import infer_template_from_strings

template = infer_template_from_strings(
    strings=["Hello there friend", "Hello there buddy"],
    min_consecutive_words=3
)
# Result: "Hello there {{var_0}}" (3 consecutive words: "Hello", "there")
```

## Use Cases

### Use Case 1: Handling Large Arguments

**Problem**: User biographies or descriptions are very long, making the ratio of template to variable very small.

**Solution**: With consecutive word detection, the common parts are still detected regardless of variable size.

```python
inferrer = TemplateInferrer(min_consecutive_words=3)

large_bio_1 = "software engineer with 15 years of experience..."  # 100 words
large_bio_2 = "data scientist specializing in ML and NLP..."      # 80 words

strings = [
    f"You are a personal assistant for {large_bio_1}",
    f"You are a personal assistant for {large_bio_2}",
]

# Still detects the common pattern!
template = inferrer.infer_template(strings)
# Result: "You are a personal assistant for {{var_0}}"
```

### Use Case 2: Stricter Matching

**Problem**: Don't want to group traces that only share 1-2 common words.

**Solution**: Increase the threshold to require more consecutive words.

```python
# Require 5 consecutive words minimum
inferrer = TemplateInferrer(min_consecutive_words=5)

strings = [
    "Hello Alice",  # Only 1 word "Hello" is common
    "Hello Bob",
]

template = inferrer.infer_template(strings)
# Result: "{{var_0}}" - Not enough consecutive words, entire string is variable
```

### Use Case 3: Lenient Matching

**Problem**: Want to group traces that share even a single common word.

**Solution**: Set threshold to 1.

```python
inferrer = TemplateInferrer(min_consecutive_words=1)

strings = [
    "Hello Alice",
    "Hello Bob",
]

template = inferrer.infer_template(strings)
# Result: "Hello {{var_0}}"
```

## How It Works

### Algorithm Steps

1. **Tokenization**: Split strings into words (alphanumeric) and separators (punctuation, whitespace)
   ```
   "Hello, world!" → ["Hello", ",", " ", "world", "!"]
   ```

2. **Find Common Token Sequences**: Search for token sequences that appear in all input strings

3. **Count Words in Sequences**: For each candidate sequence, count how many words (not separators) it contains
   ```
   "Hello, world" → 2 words ("Hello", "world")
   "Hello, " → 1 word ("Hello")
   ```

4. **Filter by Threshold**: Keep only sequences with `>= min_consecutive_words`

5. **Build Template**: Use the qualifying sequences as anchors, with variables between them

### Example Walkthrough

Input strings (with `min_consecutive_words=3`):
```
"User Alice logged in today at 10am"
"User Bob logged in today at 2pm"
```

Step 1 - Tokenize:
```
["User", " ", "Alice", " ", "logged", " ", "in", " ", "today", " ", "at", " ", "10am"]
["User", " ", "Bob", " ", "logged", " ", "in", " ", "today", " ", "at", " ", "2pm"]
```

Step 2 - Find common sequences:
- "User " (1 word) ❌ Too short
- "User ", "Alice", " ", "logged", " ", "in", " ", "today" → "User ... logged in today" (5 words) ✅
- " at " (1 word) ❌ Too short

Step 3 - Build template:
```
"User {{var_0}} logged in today at {{var_1}}"
```

## Recommendations

### Choosing the Right Threshold

| Threshold | Use Case | Trade-off |
|-----------|----------|-----------|
| **1** | Very lenient grouping, accept single word matches | May group unrelated traces |
| **2** | Moderate grouping, require at least two words | Good for short prompts |
| **3** (default) | Balanced approach, meaningful phrases | Recommended for most cases |
| **4-5** | Strict grouping, require substantial overlap | May miss valid templates with shorter common parts |
| **6+** | Very strict, only group nearly identical prompts | Risk of creating too many separate implementations |

### Best Practices

1. **Start with default (3)**: Works well for most applications
2. **Increase for noisy data**: If you're getting too many false positives, increase to 4-5
3. **Decrease for short prompts**: If your prompts are typically 5-10 words total, use 2
4. **Monitor grouping results**: Check the implementations being created and adjust as needed

## Migration Notes

### Backward Compatibility

The new approach is backward compatible:
- Existing implementations are not affected
- Existing tests updated to use `min_consecutive_words=1` for old behavior
- Default value (3) provides better grouping for most use cases

### Updating Existing Code

If you were relying on the old heuristic behavior, you can get similar results by setting `min_consecutive_words=1`:

```python
# Old behavior (approximately)
inferrer = TemplateInferrer(min_consecutive_words=1)
```

## Technical Details

### Implementation

The core logic is in `app/services/template_inference.py`:

```python
def _is_token_sequence_meaningful(self, tokens: list[str], count: int) -> bool:
    """Check if a token sequence is meaningful as an anchor.

    Counts only alphanumeric tokens (words), not punctuation or separators.
    A sequence is meaningful if it contains at least min_consecutive_words.
    """
    word_count = sum(1 for token in tokens if token.isalnum())
    return word_count >= self.min_consecutive_words
```

### Performance

- **Time Complexity**: O(n * m^2) where n is number of strings and m is average string length
- **Space Complexity**: O(m) for tokenization
- **Practical Performance**: Sub-millisecond for typical prompts (<1000 chars)

## Examples

### Example 1: Personal Assistant

```python
from app.services.template_inference import infer_template_from_strings

strings = [
    "You are a personal assistant for Mr. Smith",
    "You are a personal assistant for Mr. Johnson",
    "You are a personal assistant for Mr. Williams",
]

template = infer_template_from_strings(strings, min_consecutive_words=3)
print(template)
# Output: "You are a personal assistant for Mr. {{var_0}}"
```

### Example 2: Weather Queries

```python
strings = [
    "Get weather for NYC",
    "Get weather for LA",
    "Get weather for Chicago",
]

template = infer_template_from_strings(strings, min_consecutive_words=3)
print(template)
# Output: "Get weather for {{var_0}}"
```

### Example 3: Complex Prompts

```python
strings = [
    "Analyze the sentiment of this review: Great product!",
    "Analyze the sentiment of this review: Terrible service.",
    "Analyze the sentiment of this review: Pretty good overall.",
]

template = infer_template_from_strings(strings, min_consecutive_words=3)
print(template)
# Output: "Analyze the sentiment of this review: {{var_0}}"
```

## Testing

Comprehensive tests are available in:
- `tests/test_consecutive_word_template.py` - New consecutive word tests
- `tests/test_template_inference.py` - Backward compatibility tests
- `tests/test_task_grouping.py` - Integration tests

Run tests:
```bash
cd backend
uv run pytest tests/test_consecutive_word_template.py -v
uv run pytest tests/test_template_inference.py -v
```

## Related Documentation

- [Implementation Model Migration](implementation-model-migration.md)
- [Implementation Versions](implementation-versions.md)
