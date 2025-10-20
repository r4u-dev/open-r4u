# Parser Architecture - Modular Design

## Directory Structure

```
backend/app/services/
│
├── __init__.py
├── http_trace_parser.py          ← Main service orchestrator
│
└── parsers/                       ← Provider-specific parsers
    ├── __init__.py                ← Exports all parsers
    ├── base.py                    ← Abstract base class
    ├── openai.py                  ← OpenAI API parser
    ├── anthropic.py               ← Anthropic API parser
    └── google_genai.py            ← Google GenAI parser
```

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   HTTPTraceParserService                        │
│                  (http_trace_parser.py)                         │
│                                                                  │
│  • Receives raw HTTP request/response                           │
│  • Decodes hex-encoded data                                     │
│  • Parses JSON bodies                                           │
│  • Determines provider from URL                                 │
│  • Routes to appropriate parser                                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │     ProviderParser (ABC)      │
         │       (parsers/base.py)       │
         │                               │
         │  • can_parse(url) -> bool     │
         │  • parse(...) -> TraceCreate  │
         └───────────────┬───────────────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
         ▼                               ▼
┌─────────────────┐            ┌─────────────────┐
│  OpenAIParser   │            │ AnthropicParser │
│ (openai.py)     │            │ (anthropic.py)  │
│                 │            │                 │
│ • OpenAI Chat   │            │ • Messages API  │
│   Completions   │            │ • System prompt │
│ • Tool calls    │            │ • Content blocks│
│ • Reasoning     │            │ • Tool use      │
│ • Token details │            │                 │
└─────────────────┘            └─────────────────┘
         │
         ▼
┌─────────────────┐
│GoogleGenAIParser│
│(google_genai.py)│
│                 │
│ • Contents      │
│ • System instr. │
│ • Parts format  │
│ • Candidates    │
└─────────────────┘
```

## Request Flow

```
1. HTTP Request arrives at /http-traces endpoint
   │
   ▼
2. HTTPTraceParserService.parse_http_trace()
   │
   ├─→ Decode hex-encoded request/response
   │
   ├─→ Parse JSON bodies
   │
   ├─→ Extract URL from metadata or headers
   │
   ▼
3. Find matching parser
   │
   ├─→ OpenAIParser.can_parse(url)?
   ├─→ AnthropicParser.can_parse(url)?
   ├─→ GoogleGenAIParser.can_parse(url)?
   │
   ▼
4. Provider-specific parsing
   │
   ├─→ Extract model, messages, tokens, etc.
   ├─→ Map provider format to common TraceCreate
   │
   ▼
5. Return TraceCreate object
   │
   ▼
6. Store in database via http_traces endpoint
```

## Interface Design

### Base Parser Interface
```python
class ProviderParser(ABC):
    @abstractmethod
    def can_parse(self, url: str) -> bool:
        """Check if this parser handles the given URL."""
        
    @abstractmethod
    def parse(
        self,
        request_body: dict,
        response_body: dict,
        started_at: datetime,
        completed_at: datetime,
        error: str | None = None,
        metadata: dict | None = None,
    ) -> TraceCreate:
        """Parse request/response into TraceCreate."""
```

### Parser Implementation
```python
class OpenAIParser(ProviderParser):
    def can_parse(self, url: str) -> bool:
        return "openai.com" in urlparse(url).netloc
    
    def parse(self, ...) -> TraceCreate:
        # Extract OpenAI-specific fields
        # Map to common TraceCreate format
        return TraceCreate(...)
```

## Key Benefits

### 🎯 **Separation of Concerns**
- Each parser handles one provider
- Main service handles orchestration
- Base class defines contract

### 🔧 **Easy Maintenance**
- Fix OpenAI parsing? Edit `openai.py` only
- No risk of breaking other providers
- Clear file boundaries

### 📈 **Simple Extension**
- Create new file: `parsers/cohere.py`
- Implement `ProviderParser` interface
- Register in service
- Done!

### 🧪 **Testability**
- Can test each parser independently
- Mock specific parsers for testing
- Clear test boundaries

### 📚 **Code Organization**
- ~550 lines → 5 files of ~100-180 lines each
- Easy to find provider-specific logic
- Better IDE navigation

## Example: Adding a New Provider

```
Step 1: Create parser file
───────────────────────────
parsers/mistral.py
│
class MistralParser(ProviderParser):
    def can_parse(self, url: str) -> bool:
        return "mistral.ai" in urlparse(url).netloc
    
    def parse(self, ...) -> TraceCreate:
        # Mistral-specific parsing
        return TraceCreate(...)


Step 2: Export in __init__.py
──────────────────────────────
from app.services.parsers.mistral import MistralParser

__all__ = [
    "ProviderParser",
    "OpenAIParser",
    "AnthropicParser",
    "GoogleGenAIParser",
    "MistralParser",  # ← Add here
]


Step 3: Register in service
────────────────────────────
class HTTPTraceParserService:
    def __init__(self):
        self.parsers = [
            OpenAIParser(),
            AnthropicParser(),
            GoogleGenAIParser(),
            MistralParser(),  # ← Add here
        ]
```

## Summary

✅ **Modular architecture** - Each provider in its own file
✅ **Clear interfaces** - Abstract base class defines contract
✅ **Easy to extend** - Add new parser without touching existing code
✅ **Better maintainability** - Changes isolated to specific files
✅ **All tests passing** - No breaking changes

The parser is now ready to scale with many more providers!
