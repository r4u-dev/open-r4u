"""Tests for task execution functionality."""

from datetime import datetime, timezone
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
    test_project: Project,
) -> Task:
    """Create a test task."""
    task = Task(
        project_id=test_project.id,
        path="test/path",
    )
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
        max_output_tokens=100,
    )
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
        from app.services.executor import LLMExecutor
        from unittest.mock import MagicMock

        mock_settings = MagicMock()
        mock_settings.openai_api_key = None
        mock_settings.anthropic_api_key = None
        mock_settings.google_api_key = None
        mock_settings.cohere_api_key = None
        mock_settings.mistral_api_key = None
        mock_settings.together_api_key = None
        
        executor = LLMExecutor(mock_settings)
        prompt = "Hello, world!"
        result = executor._render_prompt(prompt)
        assert result == "Hello, world!"

    def test_render_prompt_with_variables(self):
        """Test prompt rendering with variables."""
        from app.services.executor import LLMExecutor
        from unittest.mock import MagicMock

        mock_settings = MagicMock()
        mock_settings.openai_api_key = None
        mock_settings.anthropic_api_key = None
        mock_settings.google_api_key = None
        mock_settings.cohere_api_key = None
        mock_settings.mistral_api_key = None
        mock_settings.together_api_key = None
        
        executor = LLMExecutor(mock_settings)
        prompt = "Hello, {name}! You are {age} years old."
        variables = {"name": "Alice", "age": 30}
        result = executor._render_prompt(prompt, variables)
        assert result == "Hello, Alice! You are 30 years old."

    def test_render_prompt_missing_variable(self):
        """Test prompt rendering with missing variable raises error."""
        from app.services.executor import LLMExecutor
        from unittest.mock import MagicMock

        mock_settings = MagicMock()
        mock_settings.openai_api_key = None
        mock_settings.anthropic_api_key = None
        mock_settings.google_api_key = None
        mock_settings.cohere_api_key = None
        mock_settings.mistral_api_key = None
        mock_settings.together_api_key = None
        
        executor = LLMExecutor(mock_settings)
        prompt = "Hello, {name}!"
        variables = {"age": 30}

        with pytest.raises(ValueError, match="Missing variable"):
            executor._render_prompt(prompt, variables)

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
                implementation, variables={"text": "Test text"}
            )

            assert result.result_text == "This is a test response."
            assert result.finish_reason == FinishReason.STOP
            assert result.prompt_tokens == 10
            assert result.completion_tokens == 20
            assert result.total_tokens == 30
            assert result.cached_tokens == 5
            assert result.reasoning_tokens == 15

    @pytest.mark.asyncio
    async def test_execute_task_with_overrides_creates_temp_implementation(
        self, client: AsyncClient, test_session: AsyncSession, test_implementation
    ):
        """Test that executing a task with overrides creates a temporary implementation."""
        # The fixture is already awaited by pytest
        implementation = test_implementation
        task = implementation.task
        
        # Mock the executor
        mock_result = ServiceExecutionResult(
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            prompt_rendered="Test prompt with overrides",
            result_text="Test result with different model",
            finish_reason=FinishReason.STOP,
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            cached_tokens=2,
            reasoning_tokens=3,
        )

        with patch("app.services.executions_service.LLMExecutor") as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor.execute = AsyncMock(return_value=mock_result)
            mock_executor_class.return_value = mock_executor

            response = await client.post(
                f"/executions/tasks/{task.id}/execute",
                json={
                    "variables": {"text": "test"},
                    "model": "gpt-3.5-turbo",
                    "temperature": 0.5,
                },
            )

            if response.status_code != 201:
                print(f"Response status: {response.status_code}")
                print(f"Response content: {response.text}")
            assert response.status_code == 201
            data = response.json()
            assert data["task_id"] == task.id
            assert data["result_text"] == "Test result with different model"
            
            # Verify temp implementation was created
            from app.models.tasks import Implementation
            from sqlalchemy import select
            
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
                implementation, variables={"text": "Test text"}
            )

            assert result.error == "API Error"
            assert result.result_text is None

    @pytest.mark.asyncio
    async def test_llm_executor_template_error(
        self, test_implementation
    ):
        """Test LLM execution with template rendering error."""
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
        # Missing required variable - this should trigger template rendering error
        result = await executor.execute(implementation, variables={})

        assert result.error is not None
        assert "Missing variable" in result.error



class TestExecutionAPI:
    """Tests for execution API endpoints."""

    @pytest.mark.asyncio
    async def test_execute_implementation_success(
        self, client: AsyncClient, test_session: AsyncSession, test_implementation
    ):
        """Test successful implementation execution via API."""
        # The fixture is already awaited by pytest
        implementation = test_implementation
        
        # Mock the service result (database ExecutionResult)
        mock_result = ExecutionResult(
            id=1,
            task_id=1,
            implementation_id=implementation.id,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            prompt_rendered="Summarize this text: Hello world",
            result_text="A greeting message.",
            finish_reason=FinishReason.STOP,
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            cached_tokens=2,
            reasoning_tokens=3,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        with patch("app.api.v1.executions.svc.execute") as mock_execute:
            mock_execute.return_value = mock_result

            response = await client.post(
                f"/executions/implementations/{implementation.id}/execute",
                json={"variables": {"text": "Hello world"}},
            )

            assert response.status_code == 201
            data = response.json()
            assert data["implementation_id"] == implementation.id
            assert data["result_text"] == "A greeting message."
            assert data["prompt_tokens"] == 10
            assert data["cached_tokens"] == 2
            assert data["reasoning_tokens"] == 3


    @pytest.mark.asyncio
    async def test_execute_implementation_not_found(self, client: AsyncClient):
        """Test executing non-existent implementation returns 404."""
        response = await client.post(
            "/executions/implementations/99999/execute", json={"variables": {}}
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_task_executions(
        self, client: AsyncClient, test_session: AsyncSession, test_implementation
    ):
        """Test listing executions for a task."""
        # The fixture is already awaited by pytest
        implementation = test_implementation
        task = implementation.task
        
        # Create some execution results
        execution1 = ExecutionResult(
            task_id=task.id,
            implementation_id=implementation.id,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            prompt_rendered="Test prompt 1",
            result_text="Result 1",
        )
        execution2 = ExecutionResult(
            task_id=task.id,
            implementation_id=implementation.id,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            prompt_rendered="Test prompt 2",
            result_text="Result 2",
        )

        test_session.add_all([execution1, execution2])
        await test_session.commit()

        response = await client.get(f"/executions/tasks/{task.id}/executions")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(item["task_id"] == task.id for item in data)

    @pytest.mark.asyncio
    async def test_list_implementation_executions(
        self, client: AsyncClient, test_session: AsyncSession, test_implementation
    ):
        """Test listing executions for an implementation."""
        # The fixture is already awaited by pytest
        implementation = test_implementation
        
        # Create some execution results
        execution1 = ExecutionResult(
            task_id=1,  # Mock task_id
            implementation_id=implementation.id,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            prompt_rendered="Test prompt 1",
            result_text="Result 1",
        )
        execution2 = ExecutionResult(
            task_id=1,  # Mock task_id
            implementation_id=implementation.id,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            prompt_rendered="Test prompt 2",
            result_text="Result 2",
        )

        test_session.add_all([execution1, execution2])
        await test_session.commit()

        response = await client.get(f"/executions/implementations/{implementation.id}/executions")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(item["implementation_id"] == implementation.id for item in data)

    @pytest.mark.asyncio
    async def test_get_execution(
        self, client: AsyncClient, test_session: AsyncSession, test_implementation
    ):
        """Test getting a specific execution by ID."""
        # The fixture is already awaited by pytest
        implementation = test_implementation
        task = implementation.task
        
        execution = ExecutionResult(
            task_id=task.id,
            implementation_id=implementation.id,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            prompt_rendered="Test prompt",
            result_text="Test result",
            variables={"key": "value"},
        )

        test_session.add(execution)
        await test_session.commit()
        await test_session.refresh(execution)

        response = await client.get(f"/executions/{execution.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == execution.id
        assert data["task_id"] == task.id
        assert data["result_text"] == "Test result"
        assert data["variables"] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_get_execution_not_found(self, client: AsyncClient):
        """Test getting non-existent execution returns 404."""
        response = await client.get("/executions/99999")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_all_executions(
        self, client: AsyncClient, test_session: AsyncSession, test_implementation
    ):
        """Test listing all executions."""
        # The fixture is already awaited by pytest
        implementation = test_implementation
        task = implementation.task
        
        execution = ExecutionResult(
            task_id=task.id,
            implementation_id=implementation.id,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            prompt_rendered="Test prompt",
            result_text="Test result",
        )

        test_session.add(execution)
        await test_session.commit()

        response = await client.get("/executions")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_delete_execution(
        self, client: AsyncClient, test_session: AsyncSession, test_implementation
    ):
        """Test deleting an execution."""
        # The fixture is already awaited by pytest
        implementation = test_implementation
        task = implementation.task
        
        execution = ExecutionResult(
            task_id=task.id,
            implementation_id=implementation.id,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            prompt_rendered="Test prompt",
            result_text="Test result",
        )

        test_session.add(execution)
        await test_session.commit()
        await test_session.refresh(execution)

        response = await client.delete(f"/executions/{execution.id}")

        assert response.status_code == 204

        # Verify deletion
        query = select(ExecutionResult).where(ExecutionResult.id == execution.id)
        result = await test_session.execute(query)
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_delete_execution_not_found(self, client: AsyncClient):
        """Test deleting non-existent execution returns 404."""
        response = await client.delete("/executions/99999")

        assert response.status_code == 404

