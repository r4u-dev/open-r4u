"""Integration tests for cost calculation in executions."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from app.services.executions_service import execute
from app.services.pricing_service import PricingService
from app.schemas.executions import ExecutionResultBase
from app.models.tasks import Implementation, Task
from app.models.projects import Project
from app.enums import FinishReason


@pytest.fixture
def mock_session():
    """Mock database session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def mock_settings():
    """Mock settings."""
    settings = MagicMock()
    return settings


@pytest.fixture
def sample_task():
    """Sample task for testing."""
    project = Project(id=1, name="Test Project")
    task = Task(id=1, project_id=1, project=project)
    return task


@pytest.fixture
def sample_implementation(sample_task):
    """Sample implementation for testing."""
    impl = Implementation(
        id=1,
        task_id=1,
        version="1.0",
        prompt="Test prompt",
        model="gpt-5",
        temperature=0.7,
        max_output_tokens=1000,
        temp=False,
    )
    impl.task = sample_task
    return impl


@pytest.fixture
def sample_execution_result():
    """Sample execution result from LLM executor."""
    return ExecutionResultBase(
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        prompt_rendered="Test prompt rendered",
        result_text="Test response",
        result_json=None,
        tool_calls=None,
        error=None,
        finish_reason=FinishReason.STOP,
        prompt_tokens=1000,
        completion_tokens=500,
        total_tokens=1500,
        cached_tokens=0,
        reasoning_tokens=None,
        system_fingerprint="test-fingerprint",
        provider_response={"test": "response"},
    )


class TestExecutionCostIntegration:
    """Integration tests for cost calculation in executions."""

    @pytest.mark.asyncio
    async def test_execute_with_cost_calculation(
        self, mock_session, mock_settings, sample_task, sample_implementation, sample_execution_result
    ):
        """Test execution with cost calculation."""
        # Mock the task query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_task
        mock_session.execute.return_value = mock_result
        sample_task.production_version = sample_implementation
        
        # Mock the LLM executor
        with patch('app.services.executions_service.LLMExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor.execute.return_value = sample_execution_result
            mock_executor_class.return_value = mock_executor
            
            # Mock the pricing service
            with patch('app.services.executions_service.PricingService') as mock_pricing_class:
                mock_pricing = MagicMock()
                mock_pricing.calculate_cost.return_value = 0.00625  # Expected cost
                mock_pricing_class.return_value = mock_pricing
                
                # Execute
                result = await execute(
                    session=mock_session,
                    settings=mock_settings,
                    task_id=1,
                    variables={"test": "value"},
                )
                
                # Verify pricing service was called correctly
                mock_pricing.calculate_cost.assert_called_once_with(
                    model="gpt-5",
                    prompt_tokens=1000,
                    completion_tokens=500,
                    cached_tokens=0,
                )
                
                # Verify execution was saved with cost
                mock_session.add.assert_called_once()
                saved_execution = mock_session.add.call_args[0][0]
                assert saved_execution.cost == 0.00625
                assert saved_execution.task_id == 1
                assert saved_execution.implementation_id == 1

    @pytest.mark.asyncio
    async def test_execute_with_cached_tokens_cost_calculation(
        self, mock_session, mock_settings, sample_task, sample_implementation
    ):
        """Test execution with cached tokens cost calculation."""
        # Mock the task query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_task
        mock_session.execute.return_value = mock_result
        sample_task.production_version = sample_implementation
        
        # Create execution result with cached tokens
        execution_result = ExecutionResultBase(
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            prompt_rendered="Test prompt rendered",
            result_text="Test response",
            prompt_tokens=1000,
            completion_tokens=500,
            cached_tokens=200,
        )
        
        # Mock the LLM executor
        with patch('app.services.executions_service.LLMExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor.execute.return_value = execution_result
            mock_executor_class.return_value = mock_executor
            
            # Mock the pricing service
            with patch('app.services.executions_service.PricingService') as mock_pricing_class:
                mock_pricing = MagicMock()
                mock_pricing.calculate_cost.return_value = 0.005025  # Expected cost with cached tokens
                mock_pricing_class.return_value = mock_pricing
                
                # Execute
                result = await execute(
                    session=mock_session,
                    settings=mock_settings,
                    task_id=1,
                )
                
                # Verify pricing service was called with cached tokens
                mock_pricing.calculate_cost.assert_called_once_with(
                    model="gpt-5",
                    prompt_tokens=1000,
                    completion_tokens=500,
                    cached_tokens=200,
                )
                
                # Verify execution was saved with cost
                saved_execution = mock_session.add.call_args[0][0]
                assert saved_execution.cost == 0.005025

    @pytest.mark.asyncio
    async def test_execute_with_missing_token_data(
        self, mock_session, mock_settings, sample_task, sample_implementation
    ):
        """Test execution when token data is missing."""
        # Mock the task query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_task
        mock_session.execute.return_value = mock_result
        sample_task.production_version = sample_implementation
        
        # Create execution result with missing token data
        execution_result = ExecutionResultBase(
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            prompt_rendered="Test prompt rendered",
            result_text="Test response",
            prompt_tokens=None,  # Missing token data
            completion_tokens=500,
        )
        
        # Mock the LLM executor
        with patch('app.services.executions_service.LLMExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor.execute.return_value = execution_result
            mock_executor_class.return_value = mock_executor
            
            # Mock the pricing service
            with patch('app.services.executions_service.PricingService') as mock_pricing_class:
                mock_pricing = MagicMock()
                mock_pricing_class.return_value = mock_pricing
                
                # Execute
                result = await execute(
                    session=mock_session,
                    settings=mock_settings,
                    task_id=1,
                )
                
                # Verify pricing service was not called
                mock_pricing.calculate_cost.assert_not_called()
                
                # Verify execution was saved with None cost
                saved_execution = mock_session.add.call_args[0][0]
                assert saved_execution.cost is None

    @pytest.mark.asyncio
    async def test_execute_with_pricing_service_error(
        self, mock_session, mock_settings, sample_task, sample_implementation, sample_execution_result
    ):
        """Test execution when pricing service returns None."""
        # Mock the task query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_task
        mock_session.execute.return_value = mock_result
        sample_task.production_version = sample_implementation
        
        # Mock the LLM executor
        with patch('app.services.executions_service.LLMExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor.execute.return_value = sample_execution_result
            mock_executor_class.return_value = mock_executor
            
            # Mock the pricing service to return None (no pricing data)
            with patch('app.services.executions_service.PricingService') as mock_pricing_class:
                mock_pricing = MagicMock()
                mock_pricing.calculate_cost.return_value = None
                mock_pricing_class.return_value = mock_pricing
                
                # Execute
                result = await execute(
                    session=mock_session,
                    settings=mock_settings,
                    task_id=1,
                )
                
                # Verify pricing service was called
                mock_pricing.calculate_cost.assert_called_once()
                
                # Verify execution was saved with None cost
                saved_execution = mock_session.add.call_args[0][0]
                assert saved_execution.cost is None

    @pytest.mark.asyncio
    async def test_execute_with_gemini_model(
        self, mock_session, mock_settings, sample_task
    ):
        """Test execution with Gemini model for threshold pricing."""
        # Create Gemini implementation
        gemini_impl = Implementation(
            id=1,
            task_id=1,
            version="1.0",
            prompt="Test prompt",
            model="gemini-2.5-pro",
            temperature=0.7,
            max_output_tokens=1000,
            temp=False,
        )
        gemini_impl.task = sample_task
        sample_task.production_version = gemini_impl
        
        # Mock the task query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_task
        mock_session.execute.return_value = mock_result
        
        # Create execution result with high token count (above threshold)
        execution_result = ExecutionResultBase(
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            prompt_rendered="Test prompt rendered",
            result_text="Test response",
            prompt_tokens=250000,  # Above Gemini threshold
            completion_tokens=10000,
            cached_tokens=0,
        )
        
        # Mock the LLM executor
        with patch('app.services.executions_service.LLMExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor.execute.return_value = execution_result
            mock_executor_class.return_value = mock_executor
            
            # Mock the pricing service
            with patch('app.services.executions_service.PricingService') as mock_pricing_class:
                mock_pricing = MagicMock()
                mock_pricing.calculate_cost.return_value = 0.775  # Expected cost for long context
                mock_pricing_class.return_value = mock_pricing
                
                # Execute
                result = await execute(
                    session=mock_session,
                    settings=mock_settings,
                    task_id=1,
                )
                
                # Verify pricing service was called with Gemini model
                mock_pricing.calculate_cost.assert_called_once_with(
                    model="gemini-2.5-pro",
                    prompt_tokens=250000,
                    completion_tokens=10000,
                    cached_tokens=0,
                )
                
                # Verify execution was saved with cost
                saved_execution = mock_session.add.call_args[0][0]
                assert saved_execution.cost == 0.775

    @pytest.mark.asyncio
    async def test_execute_with_versioned_model(
        self, mock_session, mock_settings, sample_task, sample_execution_result
    ):
        """Test execution with versioned model name."""
        # Create implementation with versioned model
        versioned_impl = Implementation(
            id=1,
            task_id=1,
            version="1.0",
            prompt="Test prompt",
            model="gpt-5-2024-10-01",  # Versioned model
            temperature=0.7,
            max_output_tokens=1000,
            temp=False,
        )
        versioned_impl.task = sample_task
        sample_task.production_version = versioned_impl
        
        # Mock the task query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_task
        mock_session.execute.return_value = mock_result
        
        # Mock the LLM executor
        with patch('app.services.executions_service.LLMExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor.execute.return_value = sample_execution_result
            mock_executor_class.return_value = mock_executor
            
            # Mock the pricing service
            with patch('app.services.executions_service.PricingService') as mock_pricing_class:
                mock_pricing = MagicMock()
                mock_pricing.calculate_cost.return_value = 0.00625
                mock_pricing_class.return_value = mock_pricing
                
                # Execute
                result = await execute(
                    session=mock_session,
                    settings=mock_settings,
                    task_id=1,
                )
                
                # Verify pricing service was called with versioned model
                mock_pricing.calculate_cost.assert_called_once_with(
                    model="gpt-5-2024-10-01",
                    prompt_tokens=1000,
                    completion_tokens=500,
                    cached_tokens=0,
                )

    @pytest.mark.asyncio
    async def test_execute_with_provider_prefixed_model(
        self, mock_session, mock_settings, sample_task, sample_execution_result
    ):
        """Test execution with provider-prefixed model name."""
        # Create implementation with provider-prefixed model
        prefixed_impl = Implementation(
            id=1,
            task_id=1,
            version="1.0",
            prompt="Test prompt",
            model="openai/gpt-5",  # Provider-prefixed model
            temperature=0.7,
            max_output_tokens=1000,
            temp=False,
        )
        prefixed_impl.task = sample_task
        sample_task.production_version = prefixed_impl
        
        # Mock the task query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_task
        mock_session.execute.return_value = mock_result
        
        # Mock the LLM executor
        with patch('app.services.executions_service.LLMExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor.execute.return_value = sample_execution_result
            mock_executor_class.return_value = mock_executor
            
            # Mock the pricing service
            with patch('app.services.executions_service.PricingService') as mock_pricing_class:
                mock_pricing = MagicMock()
                mock_pricing.calculate_cost.return_value = 0.00625
                mock_pricing_class.return_value = mock_pricing
                
                # Execute
                result = await execute(
                    session=mock_session,
                    settings=mock_settings,
                    task_id=1,
                )
                
                # Verify pricing service was called with provider-prefixed model
                mock_pricing.calculate_cost.assert_called_once_with(
                    model="openai/gpt-5",
                    prompt_tokens=1000,
                    completion_tokens=500,
                    cached_tokens=0,
                )
