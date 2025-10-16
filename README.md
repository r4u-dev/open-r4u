# Open R4U 🚀

**Optimize AI & Maximize ROI of your LLM tasks**

[![Website](https://img.shields.io/badge/Website-r4u.dev-blue)](https://r4u.dev)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

Open R4U is an open-source LLM observability and optimization platform that helps you trace, monitor, and optimize your AI applications. Track your LLM usage, analyze performance, and maximize ROI through intelligent insights and recommendations.

## 🌟 Features

### 🔍 **LLM Observability**
- **Automatic Tracing**: Seamlessly trace OpenAI and LangChain calls with minimal code changes
- **Call Path Tracking**: Automatically capture where LLM calls originate from in your codebase
- **Message History**: Full conversation tracking with complete message context
- **Tool & Function Call Monitoring**: Track tool definitions, invocations, and responses
- **Error Tracking**: Comprehensive error capture and debugging information

### 📊 **Analytics & Insights**
- **Performance Metrics**: Track latency, token usage, and cost per request
- **Usage Analytics**: Understand your LLM consumption patterns
- **Project Organization**: Organize traces by projects for better management
- **Task Management**: Define and track specific AI tasks and workflows

### 🔌 **Easy Integrations**
- **OpenAI SDK**: Drop-in wrapper for automatic tracing
- **LangChain**: Native callback handler integration
- **Manual Tracing**: Full control with programmatic trace creation
- **Async Support**: Complete async/await compatibility

### 🛠 **Developer Experience**
- **Minimal Overhead**: Lightweight SDK with negligible performance impact
- **Self-Hosted**: Run your own instance with full data control
- **REST API**: Complete API for custom integrations
- **Comprehensive Testing**: Full test coverage with examples

## 🏗 Architecture

Open R4U consists of three main components:

- **Backend API** (`/backend`): FastAPI-based REST API with PostgreSQL database
- **Python SDK** (`/sdks/python`): Client libraries for easy integration
- **Web Interface** (coming soon): Dashboard for visualization and analysis

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Your App      │───▶│   R4U SDK       │───▶│   R4U Backend   │
│                 │    │                 │    │                 │
│ - OpenAI calls  │    │ - Auto tracing  │    │ - FastAPI       │
│ - LangChain     │    │ - Call paths    │    │ - PostgreSQL    │
│ - Custom LLMs   │    │ - Error capture │    │ - Analytics     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### 1. Start the Backend

```bash
# Clone the repository
git clone https://github.com/your-org/open-r4u.git
cd open-r4u

# Start the backend with Docker Compose
docker compose up -d

# The API will be available at http://localhost:8000
```

### 2. Install the Python SDK

```bash
pip install r4u
```

### 3. Start Tracing Your LLM Calls

#### OpenAI Integration

```python
from openai import OpenAI
from r4u.integrations.openai import wrap_openai

# Initialize your OpenAI client
client = OpenAI(api_key="your-api-key")

# Wrap it with R4U observability
traced_client = wrap_openai(client, api_url="http://localhost:8000")

# Use it normally - traces will be automatically created
response = traced_client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Hello, world!"}]
)
```

#### LangChain Integration

```python
from langchain_openai import ChatOpenAI
from r4u.integrations.langchain import wrap_langchain

# Create the R4U callback handler
r4u_handler = wrap_langchain(api_url="http://localhost:8000")

# Add it to your LangChain model
llm = ChatOpenAI(model="gpt-3.5-turbo", callbacks=[r4u_handler])

# Use it normally - traces will be automatically created
response = llm.invoke("Hello, world!")
```

### 4. View Your Traces

Visit `http://localhost:8000/docs` to explore the API and view your traces, or use the API directly:

```bash
# List all traces
curl http://localhost:8000/api/v1/traces

# List all projects
curl http://localhost:8000/api/v1/projects
```

## 📚 Documentation

### SDK Documentation
- [Python SDK README](sdks/python/README.md)
- [LangChain Integration Guide](sdks/python/docs/LANGCHAIN_INTEGRATION.md)
- [Call Path Tracking](sdks/python/docs/CALL_PATH_FEATURE.md)
- [Quick Start Guide](sdks/python/docs/LANGCHAIN_QUICKSTART.md)

### Examples
- [Basic LangChain Example](sdks/python/examples/basic_langchain.py)
- [Advanced LangChain Example](sdks/python/examples/advanced_langchain.py)
- [OpenAI Integration Example](sdks/python/examples/basic_openai.py)
- [Tool Calls Example](sdks/python/examples/tool_calls_example.py)
- [Project Management Example](sdks/python/examples/project_example.py)

### API Documentation
- [Backend API Documentation](backend/README.md)
- [Test Coverage](backend/tests/README.md)

## 🛠 Development

### Prerequisites

- Python 3.12+
- PostgreSQL 16+
- Docker & Docker Compose (optional)

### Local Development Setup

```bash
# Clone the repository
git clone https://github.com/your-org/open-r4u.git
cd open-r4u

# Start the database
docker compose up -d db

# Install backend dependencies
cd backend
uv install

# Run database migrations
alembic upgrade head

# Start the backend
uvicorn app.main:app --reload

# Install SDK dependencies (in another terminal)
cd ../sdks/python
uv install

# Run tests
pytest tests/
```

### Project Structure

```
open-r4u/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/v1/         # API endpoints
│   │   ├── models/         # Database models
│   │   ├── schemas/        # Pydantic schemas
│   │   └── main.py         # FastAPI app
│   ├── migrations/         # Database migrations
│   └── tests/              # Backend tests
├── sdks/python/            # Python SDK
│   ├── src/r4u/
│   │   ├── integrations/   # OpenAI, LangChain integrations
│   │   ├── client.py       # API client
│   │   └── utils.py        # Utilities
│   ├── examples/           # Usage examples
│   └── tests/              # SDK tests
└── compose.yaml            # Docker Compose setup
```

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** and add tests
4. **Run the test suite**: `pytest`
5. **Commit your changes**: `git commit -m 'Add amazing feature'`
6. **Push to the branch**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

### Development Guidelines

- Follow Python type hints and use `mypy` for type checking
- Write comprehensive tests for new features
- Update documentation for API changes
- Follow the existing code style and patterns

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🌐 Links

- **Website**: [r4u.dev](https://r4u.dev)
- **Documentation**: [docs.r4u.dev](https://docs.r4u.dev) (coming soon)

## 🙏 Acknowledgments

- Inspired by [Langfuse](https://github.com/langfuse/langfuse) for LLM observability concepts
- Built with [FastAPI](https://fastapi.tiangolo.com/) and [SQLAlchemy](https://www.sqlalchemy.org/)
- Powered by the open-source community

---

**Ready to optimize your LLM usage?** [Get started](https://r4u.dev) with R4U today!
