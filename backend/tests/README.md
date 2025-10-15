# Backend Tests

This directory contains comprehensive tests for the R4U backend API endpoints.

## Structure

- `conftest.py` - Pytest configuration with fixtures for database and HTTP client
- `test_projects.py` - Tests for project management endpoints
- `test_traces.py` - Tests for trace recording endpoints

## Running Tests

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run specific test file
pytest tests/test_projects.py

# Run specific test
pytest tests/test_projects.py::TestProjectEndpoints::test_create_project

# Run with coverage (if coverage is installed)
pytest tests/ --cov=app --cov-report=html
```

## Test Coverage

### Projects API (`test_projects.py`)
- ✅ Creating projects with and without description
- ✅ Duplicate name validation
- ✅ Listing all projects
- ✅ Getting project by ID (success and 404 cases)
- ✅ Getting project by name (success and 404 cases)
- ✅ Empty project list

### Traces API (`test_traces.py`)
- ✅ Creating traces with default project auto-creation
- ✅ Creating traces with custom project auto-creation
- ✅ Creating traces with multiple messages
- ✅ Creating traces with tool definitions
- ✅ Creating traces with tool calls
- ✅ Creating traces with errors
- ✅ Creating traces with call path tracking
- ✅ Listing traces (with ordering)
- ✅ Empty trace list
- ✅ Minimal trace creation (required fields only)
- ✅ Project reuse verification
- ✅ Response schema validation

## Test Database

Tests use an in-memory SQLite database with:
- Async support via `aiosqlite`
- Foreign key constraints enabled
- StaticPool for connection management
- Each test gets a fresh database instance

## Fixtures

### `test_engine`
Creates an async SQLAlchemy engine with in-memory SQLite database for each test.

### `test_session`
Provides an async database session for tests.

### `client`
Provides an async HTTP client (`httpx.AsyncClient`) with dependency overrides to use the test database session.

## Adding New Tests

1. Create a new test class or add methods to existing classes
2. Use the `client` fixture to make HTTP requests
3. Use the `test_session` fixture if direct database access is needed
4. Follow the pattern: Arrange → Act → Assert

Example:
```python
async def test_my_endpoint(self, client: AsyncClient):
    """Test description."""
    # Arrange
    payload = {"key": "value"}
    
    # Act
    response = await client.post("/endpoint", json=payload)
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "value"
```

## Database Portability

The models use database-agnostic JSON types that work with both:
- PostgreSQL (uses JSONB)
- SQLite (uses JSON)

This is achieved using SQLAlchemy's type variants:
```python
JSONType = JSON().with_variant(JSONB(astext_type=Text()), "postgresql")
```
