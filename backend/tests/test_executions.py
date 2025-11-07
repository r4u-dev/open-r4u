"""Tests for task execution functionality."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import FinishReason
from app.models.executions import ExecutionResult
from app.models.projects import Project
from app.models.tasks import Implementation, Task
from app.schemas.executions import ExecutionResultBase as ServiceExecutionResult
from app.services.executor import LLMExecutor


@pytest_asyncio.fixture
async def test_project(test_session: AsyncSession) -> Project:
    """Create a test project."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.commit()
    await test_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def test_task(
    test_session: AsyncSession,
    test_project: Project) -> Task:
    """Create a test task."""
    task = Task(
            name="Test Task",
            description="Test task",
            project_id=test_project.id,
        path="test/path",
        response_schema={"type": "object", "properties": {"summary": {"type": "string"}}})
    test_session.add(task)
    await test_session.commit()
    await test_session.refresh(task)
    return task


@pytest_asyncio.fixture
async def test_implementation(test_session: AsyncSession, test_task: Task) -> Implementation:
    """Create a test implementation."""
    implementation = Implementation(
        task_id=test_task.id,
        version="1.0",
        prompt="Summarize this text: {{text}}",
        model="gpt-4",
        temperature=0.7,
        max_output_tokens=100)
    test_session.add(implementation)
    await test_session.commit()
    await test_session.refresh(implementation)

    # Update the task to set this as the production version
    test_task.production_version_id = implementation.id
    await test_session.commit()
    await test_session.refresh(test_task)

    return implementation


class TestExecutor:
    """Tests for the LLM executor service."""

    def test_render_prompt_simple(self):
        """Test simple prompt rendering without variables."""
        from unittest.mock import MagicMock

        from app.services.executor import LLMExecutor

        mock_settings = MagicMock()
        mock_settings.openai_api_key = None
        mock_settings.anthropic_api_key = None
        mock_settings.google_api_key = None
        mock_settings.cohere_api_key = None
        mock_settings.mistral_api_key = None
        mock_settings.together_api_key = None

        executor = LLMExecutor(mock_settings)
        prompt = "Hello, world!"
        result = executor._render_template(prompt)
        assert result == "Hello, world!"

    def test_render_prompt_with_variables(self):
        """Test prompt rendering with variables."""
        from unittest.mock import MagicMock

        from app.services.executor import LLMExecutor

        mock_settings = MagicMock()
        mock_settings.openai_api_key = None
        mock_settings.anthropic_api_key = None
        mock_settings.google_api_key = None
        mock_settings.cohere_api_key = None
        mock_settings.mistral_api_key = None
        mock_settings.together_api_key = None

        executor = LLMExecutor(mock_settings)
        prompt = "Hello, {{name}}! You are {{age}} years old."
        variables = {"name": "Alice", "age": 30}
        result = executor._render_template(prompt, variables)
        assert result == "Hello, Alice! You are 30 years old."

    def test_render_prompt_missing_variable(self):
        """Test prompt rendering with missing variable only warns and preserves token."""
        from unittest.mock import MagicMock

        from app.services.executor import LLMExecutor

        mock_settings = MagicMock()
        mock_settings.openai_api_key = None
        mock_settings.anthropic_api_key = None
        mock_settings.google_api_key = None
        mock_settings.cohere_api_key = None
        mock_settings.mistral_api_key = None
        mock_settings.together_api_key = None

        executor = LLMExecutor(mock_settings)
        prompt = "Hello, {{name}}!"
        variables = {"age": 30}

        result = executor._render_template(prompt, variables)
        assert result == prompt

    def test_render_template_preserves_single_braces(self):
        """Test that single braces are left untouched during rendering."""
        from unittest.mock import MagicMock

        from app.services.executor import LLMExecutor

        mock_settings = MagicMock()
        mock_settings.openai_api_key = None
        mock_settings.anthropic_api_key = None
        mock_settings.google_api_key = None
        mock_settings.cohere_api_key = None
        mock_settings.mistral_api_key = None
        mock_settings.together_api_key = None

        executor = LLMExecutor(mock_settings)
        # Test with JSON-like content that has single braces
        prompt = 'Return JSON: {"name": "{{name}}", "status": "active"}'
        variables = {"name": "Alice"}
        result = executor._render_template(prompt, variables)
        assert result == 'Return JSON: {"name": "Alice", "status": "active"}'

    def test_render_template_nested_structures(self):
        """Test recursive rendering in lists and dicts."""
        from unittest.mock import MagicMock

        from app.services.executor import LLMExecutor

        mock_settings = MagicMock()
        mock_settings.openai_api_key = None
        mock_settings.anthropic_api_key = None
        mock_settings.google_api_key = None
        mock_settings.cohere_api_key = None
        mock_settings.mistral_api_key = None
        mock_settings.together_api_key = None

        executor = LLMExecutor(mock_settings)
        variables = {"user": "Bob", "age": 25}
        
        # Test nested dict and list
        nested = {
            "greeting": "Hello {{user}}",
            "details": ["Age: {{age}}", "Status: active"],
            "raw_json": {"key": "value"}
        }
        result = executor._render_template(nested, variables)
        
        assert result["greeting"] == "Hello Bob"
        assert result["details"] == ["Age: 25", "Status: active"]
        assert result["raw_json"] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_llm_executor_success(self, test_implementation):
        """Test successful LLM execution."""
        # The fixture is already awaited by pytest
        implementation = test_implementation

        # Mock settings
        mock_settings = MagicMock()
        mock_settings.openai_api_key = "test-key"
        mock_settings.anthropic_api_key = None
        mock_settings.google_api_key = None
        mock_settings.cohere_api_key = None
        mock_settings.mistral_api_key = None
        mock_settings.together_api_key = None

        # Mock LiteLLM response
        mock_choice = MagicMock()
        mock_choice.message.content = "This is a test response."
        mock_choice.finish_reason = "stop"

        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 20
        mock_usage.total_tokens = 30
        mock_usage.cached_tokens = 5
        mock_usage.reasoning_tokens = 15

        # Mirror LiteLLM's nested usage structure
        mock_usage.prompt_tokens_details = {"cached_tokens": 5}
        mock_usage.completion_tokens_details = {"reasoning_tokens": 15}

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage
        mock_response.system_fingerprint = "test-fingerprint"
        mock_response.model_dump.return_value = {"test": "response"}

        # Mock LiteLLM acompletion
        with patch("app.services.executor.acompletion") as mock_acompletion:
            mock_acompletion.return_value = mock_response

            executor = LLMExecutor(mock_settings)
            result = await executor.execute(
                implementation, variables={"text": "Test text"},
            )

            assert result.result_text == "This is a test response."
            assert result.finish_reason == FinishReason.STOP
            assert result.prompt_tokens == 10
            assert result.completion_tokens == 20
            assert result.total_tokens == 30
            assert result.cached_tokens == 5
            assert result.reasoning_tokens == 15

    @pytest.mark.asyncio
    async def test_llm_executor_with_tool_calls(self, test_implementation):
        """Test LLM execution with tool calls using proper schemas."""
        # The fixture is already awaited by pytest
        implementation = test_implementation

        # Mock settings
        mock_settings = MagicMock()
        mock_settings.openai_api_key = "test-key"
        mock_settings.anthropic_api_key = None
        mock_settings.google_api_key = None
        mock_settings.cohere_api_key = None
        mock_settings.mistral_api_key = None
        mock_settings.together_api_key = None

        # Mock tool call
        mock_function = MagicMock()
        mock_function.name = "get_weather"
        mock_function.arguments = '{"location": "New York"}'

        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_123"
        mock_tool_call.type = "function"
        mock_tool_call.function = mock_function

        # Mock LiteLLM response with tool calls
        mock_choice = MagicMock()
        mock_choice.message.content = None  # No content when tool calls are made
        mock_choice.message.tool_calls = [mock_tool_call]
        mock_choice.finish_reason = "tool_calls"

        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 5
        mock_usage.total_tokens = 15

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage
        mock_response.system_fingerprint = "test-fingerprint"
        mock_response.model_dump.return_value = {"test": "response"}

        # Mock LiteLLM acompletion
        with patch("app.services.executor.acompletion") as mock_acompletion:
            mock_acompletion.return_value = mock_response

            executor = LLMExecutor(mock_settings)
            result = await executor.execute(
                implementation, variables={"text": "What's the weather?"},
            )

            assert result.finish_reason == FinishReason.TOOL_CALLS
            # result_json is now list[OutputItem] - includes FunctionToolCallItem and OutputMessageItem
            assert result.result_json is not None
            assert len(result.result_json) == 2  # Tool call + message
            # Find the tool call item (items are Pydantic models or dicts after model_dump)
            tool_call_item = None
            for item in result.result_json:
                # Handle both Pydantic models and dicts
                item_type = item.type if hasattr(item, "type") else item.get("type") if isinstance(item, dict) else None
                if item_type == "function_call":
                    tool_call_item = item.model_dump() if hasattr(item, "model_dump") else item
                    break
            assert tool_call_item is not None
            assert tool_call_item["type"] == "function_call"
            assert tool_call_item["id"] == "call_123"
            assert tool_call_item["call_id"] == "call_123"
            assert tool_call_item["name"] == "get_weather"
            assert tool_call_item["arguments"] == '{"location": "New York"}'
            assert tool_call_item["status"] == "completed"

    @pytest.mark.asyncio
    async def test_execute_task_with_overrides_creates_temp_implementation(
        self, client: AsyncClient, test_session: AsyncSession, test_implementation,
    ):
        """Test that executing a task with overrides creates a temporary implementation."""
        # The fixture is already awaited by pytest
        implementation = test_implementation
        task = implementation.task

        # Mock the executor
        mock_result = ServiceExecutionResult(
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            prompt_rendered="Test prompt with overrides",
            result_text="Test result with different model",
            finish_reason=FinishReason.STOP,
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            cached_tokens=2,
            reasoning_tokens=3)

        with patch("app.services.executions_service.LLMExecutor") as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor.execute = AsyncMock(return_value=mock_result)
            mock_executor_class.return_value = mock_executor

            response = await client.post(
                "/v1/executions",
                json={
                    "task_id": task.id,
                    "arguments": {"text": "test"},
                    "model": "gpt-3.5-turbo",
                    "temperature": 0.5,
                })

            if response.status_code != 201:
                print(f"Response status: {response.status_code}")
                print(f"Response content: {response.text}")
            assert response.status_code == 201
            data = response.json()
            assert data["task_id"] == task.id
            assert data["result_text"] == "Test result with different model"

            # Verify temp implementation was created
            from sqlalchemy import select

            from app.models.tasks import Implementation

            query = select(Implementation).where(Implementation.temp == True)
            result = await test_session.execute(query)
            temp_impls = result.scalars().all()

            assert len(temp_impls) == 1
            temp_impl = temp_impls[0]
            assert temp_impl.model == "gpt-3.5-turbo"
            assert temp_impl.temperature == 0.5
            assert temp_impl.temp == True
            assert temp_impl.version.endswith("-temp")

    @pytest.mark.asyncio
    async def test_llm_executor_api_error(self, test_implementation):
        """Test LLM execution with API error."""
        # The fixture is already awaited by pytest
        implementation = test_implementation

        # Mock settings
        mock_settings = MagicMock()
        mock_settings.openai_api_key = "test-key"
        mock_settings.anthropic_api_key = None
        mock_settings.google_api_key = None
        mock_settings.cohere_api_key = None
        mock_settings.mistral_api_key = None
        mock_settings.together_api_key = None

        # Mock LiteLLM with error
        with patch("app.services.executor.acompletion") as mock_acompletion:
            mock_acompletion.side_effect = Exception("API Error")

            executor = LLMExecutor(mock_settings)
            result = await executor.execute(
                implementation, variables={"text": "Test text"},
            )

            assert result.error == "API Error"
            assert result.result_text is None

    @pytest.mark.asyncio
    async def test_llm_executor_template_error(
        self, test_implementation,
    ):
        """Test LLM execution with missing template variable (should warn, not fail)."""
        # The fixture is already awaited by pytest
        implementation = test_implementation

        # Mock settings
        mock_settings = MagicMock()
        mock_settings.openai_api_key = "test-key"
        mock_settings.anthropic_api_key = None
        mock_settings.google_api_key = None
        mock_settings.cohere_api_key = None
        mock_settings.mistral_api_key = None
        mock_settings.together_api_key = None

        executor = LLMExecutor(mock_settings)
        # Missing required variable - should warn but not fail, preserve template
        result = await executor.execute(implementation, variables={})

        # Template should be preserved with {{text}} intact
        assert "{{text}}" in result.prompt_rendered
        # Execution should proceed (may fail on API auth, but not template error)
        assert result.error is not None
        # Error should be from API, not template
        assert "Missing variable" not in result.error



class TestExecutionAPI:
    """Tests for execution API endpoints."""

    @pytest.mark.asyncio
    async def test_execute_implementation_success(
        self, client: AsyncClient, test_session: AsyncSession, test_implementation,
    ):
        """Test successful implementation execution via API."""
        # The fixture is already awaited by pytest
        implementation = test_implementation

        # Mock the service result (database ExecutionResult)
        mock_result = ExecutionResult(
            id=1,
            task_id=1,
            implementation_id=implementation.id,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            prompt_rendered="Summarize this text: Hello world",
            arguments={"text": "Hello world"},
            result_text="A greeting message.",
            finish_reason=FinishReason.STOP,
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            cached_tokens=2,
            reasoning_tokens=3,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC))

        with patch("app.api.v1.executions.svc.execute") as mock_execute:
            mock_execute.return_value = mock_result

            response = await client.post(
                "/v1/executions",
                json={"implementation_id": implementation.id, "arguments": {"text": "Hello world"}})

            assert response.status_code == 201
            data = response.json()
            assert data["implementation_id"] == implementation.id
            assert data["result_text"] == "A greeting message."
            assert data["prompt_tokens"] == 10
            assert data["cached_tokens"] == 2
            assert data["reasoning_tokens"] == 3

    @pytest.mark.asyncio
    async def test_execute_implementation_with_tool_calls(
        self, client: AsyncClient, test_implementation: Implementation,
    ):
        """Test implementation execution with tool calls via API."""
        # Mock the service result with tool calls (no separate tool_calls field)
        mock_result = ExecutionResult(
            id=1,
            task_id=1,
            implementation_id=test_implementation.id,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            prompt_rendered="What's the weather?",
            result_text="Made 1 tool call(s)",
            finish_reason=FinishReason.TOOL_CALLS,
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            cached_tokens=2,
            reasoning_tokens=3,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC))

        with patch("app.api.v1.executions.svc.execute") as mock_execute:
            mock_execute.return_value = mock_result

            response = await client.post(
                "/v1/executions",
                json={"implementation_id": test_implementation.id, "arguments": {"text": "What's the weather?"}})

            assert response.status_code == 201
            data = response.json()
            assert data["implementation_id"] == test_implementation.id
            assert data["result_text"] == "Made 1 tool call(s)"



    @pytest.mark.asyncio
    async def test_execute_implementation_not_found(self, client: AsyncClient):
        """Test executing non-existent implementation returns 404."""
        response = await client.post(
            "/v1/executions", json={"implementation_id": 999, "arguments": {}},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_task_executions(
        self, client: AsyncClient, test_session: AsyncSession, test_implementation,
    ):
        """Test listing executions for a task."""
        # The fixture is already awaited by pytest
        implementation = test_implementation
        task = implementation.task

        # Create some execution results
        execution1 = ExecutionResult(
            task_id=task.id,
            implementation_id=implementation.id,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            prompt_rendered="Test prompt 1",
            arguments={"key": "value1"},
            result_text="Result 1")
        execution2 = ExecutionResult(
            task_id=task.id,
            implementation_id=implementation.id,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            prompt_rendered="Test prompt 2",
            arguments={"key": "value2"},
            result_text="Result 2")

        test_session.add_all([execution1, execution2])
        await test_session.commit()

        response = await client.get(f"/v1/executions?task_id={task.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(item["task_id"] == task.id for item in data)

    @pytest.mark.asyncio
    async def test_list_implementation_executions(
        self, client: AsyncClient, test_session: AsyncSession, test_implementation,
    ):
        """Test listing executions for an implementation."""
        # The fixture is already awaited by pytest
        implementation = test_implementation

        # Create some execution results
        execution1 = ExecutionResult(
            task_id=1,  # Mock task_id
            implementation_id=implementation.id,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            prompt_rendered="Test prompt 1",
            arguments={"key": "value1"},
            result_text="Result 1")
        execution2 = ExecutionResult(
            task_id=1,  # Mock task_id
            implementation_id=implementation.id,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            prompt_rendered="Test prompt 2",
            arguments={"key": "value2"},
            result_text="Result 2")

        test_session.add_all([execution1, execution2])
        await test_session.commit()

        response = await client.get(f"/v1/executions?implementation_id={implementation.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(item["implementation_id"] == implementation.id for item in data)

    @pytest.mark.asyncio
    async def test_get_execution(
        self, client: AsyncClient, test_session: AsyncSession, test_implementation,
    ):
        """Test getting a specific execution by ID."""
        # The fixture is already awaited by pytest
        implementation = test_implementation
        task = implementation.task

        execution = ExecutionResult(
            task_id=task.id,
            implementation_id=implementation.id,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            prompt_rendered="Test prompt",
            result_text="Test result",
            arguments={"key": "value"})

        test_session.add(execution)
        await test_session.commit()
        await test_session.refresh(execution)

        response = await client.get(f"/v1/executions/{execution.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == execution.id
        assert data["task_id"] == task.id
        assert data["result_text"] == "Test result"
        assert data["arguments"] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_get_execution_not_found(self, client: AsyncClient):
        """Test getting non-existent execution returns 404."""
        response = await client.get("/v1/executions/99999")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_all_executions(
        self, client: AsyncClient, test_session: AsyncSession, test_implementation,
    ):
        """Test listing all executions."""
        # The fixture is already awaited by pytest
        implementation = test_implementation
        task = implementation.task

        execution = ExecutionResult(
            task_id=task.id,
            implementation_id=implementation.id,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            prompt_rendered="Test prompt",
            result_text="Test result")

        test_session.add(execution)
        await test_session.commit()

        response = await client.get("/v1/executions")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_delete_execution(
        self, client: AsyncClient, test_session: AsyncSession, test_implementation,
    ):
        """Test deleting an execution."""
        # The fixture is already awaited by pytest
        implementation = test_implementation
        task = implementation.task

        execution = ExecutionResult(
            task_id=task.id,
            implementation_id=implementation.id,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            prompt_rendered="Test prompt",
            arguments={"key": "value"},
            result_text="Test result")

        test_session.add(execution)
        await test_session.commit()
        await test_session.refresh(execution)

        response = await client.delete(f"/v1/executions/{execution.id}")

        assert response.status_code == 204

        # Verify deletion
        query = select(ExecutionResult).where(ExecutionResult.id == execution.id)
        result = await test_session.execute(query)
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_delete_execution_not_found(self, client: AsyncClient):
        """Test deleting non-existent execution returns 404."""
        response = await client.delete("/v1/executions/99999")

        assert response.status_code == 404

