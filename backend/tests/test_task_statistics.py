"""Tests for task statistics (cost and latency percentiles)."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.projects import Project
from app.models.tasks import Implementation, Task
from app.models.traces import Trace
from app.services.task_service import TaskService
from app.utils.cost import calculate_trace_cost, calculate_traces_cost
from app.utils.statistics import (
    calculate_percentile,
    calculate_time_decay_weight,
    calculate_weighted_percentile,
)


@pytest_asyncio.fixture
def mock_openai_client():
    """Mock the OpenAI client to avoid requiring API keys."""
    with patch("app.services.task_service.get_async_openai_client") as mock:
        # Create mock client
        mock_client = AsyncMock()

        # Create mock response with parsed output
        mock_response = MagicMock()
        mock_parsed = MagicMock()
        mock_parsed.name = "Auto-generated Task"
        mock_parsed.description = "Auto-generated task description from instructions"
        mock_response.output_parsed = mock_parsed

        # Set up the client's responses.parse method
        mock_client.responses.parse = AsyncMock(return_value=mock_response)

        # Return the mock client
        mock.return_value = mock_client

        yield mock


@pytest.mark.asyncio
async def test_calculate_time_decay_weight():
    """Test time decay weight calculation."""
    now = datetime.now(UTC)

    # Current time should have weight 1.0
    weight_now = calculate_time_decay_weight(now, now, half_life_hours=168)
    assert weight_now == 1.0

    # One week ago (one half-life) should have weight 0.5
    week_ago = now - timedelta(hours=168)
    weight_week = calculate_time_decay_weight(week_ago, now, half_life_hours=168)
    assert weight_week == pytest.approx(0.5, rel=0.01)

    # Two weeks ago (two half-lives) should have weight 0.25
    two_weeks_ago = now - timedelta(hours=336)
    weight_two_weeks = calculate_time_decay_weight(
        two_weeks_ago,
        now,
        half_life_hours=168,
    )
    assert weight_two_weeks == pytest.approx(0.25, rel=0.01)

    # Test with different half-life (24 hours)
    day_ago = now - timedelta(hours=24)
    weight_day = calculate_time_decay_weight(day_ago, now, half_life_hours=24)
    assert weight_day == pytest.approx(0.5, rel=0.01)


@pytest.mark.asyncio
async def test_calculate_weighted_percentile():
    """Test weighted percentile calculation."""
    values = [1.0, 2.0, 3.0, 4.0, 5.0]

    # Equal weights should give same result as unweighted
    equal_weights = [1.0, 1.0, 1.0, 1.0, 1.0]
    p50_equal = calculate_weighted_percentile(values, equal_weights, 50)
    assert p50_equal is not None

    # Recent values weighted more heavily
    # Weights: older traces have lower weight
    decay_weights = [0.25, 0.5, 0.75, 0.9, 1.0]
    p50_weighted = calculate_weighted_percentile(values, decay_weights, 50)
    # Should be higher than equal weight case
    assert p50_weighted is not None
    assert p50_weighted > p50_equal

    # Test edge cases
    assert calculate_weighted_percentile([], [], 50) is None
    assert calculate_weighted_percentile([5.0], [1.0], 50) == 5.0

    # Test error cases
    with pytest.raises(ValueError):
        calculate_weighted_percentile([1, 2, 3], [1, 2, 3], 150)

    with pytest.raises(ValueError):
        calculate_weighted_percentile([1, 2, 3], [1, 2], 50)  # Mismatched lengths


@pytest.mark.asyncio
async def test_calculate_percentile():
    """Test percentile calculation."""
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]

    # Test 50th percentile (median)
    p50 = calculate_percentile(values, 50)
    assert p50 == pytest.approx(5.5, rel=0.01)

    # Test 95th percentile
    p95 = calculate_percentile(values, 95)
    assert p95 == pytest.approx(9.5, rel=0.01)

    # Test edge cases
    assert calculate_percentile([], 50) is None
    assert calculate_percentile([5.0], 50) == 5.0

    # Test error case
    with pytest.raises(ValueError):
        calculate_percentile([1, 2, 3], 150)


@pytest.mark.asyncio
async def test_calculate_trace_cost():
    """Test trace cost calculation."""
    # Create a mock trace
    trace = Trace(
        model="gpt-3.5-turbo",
        prompt_tokens=1000,
        completion_tokens=500,
        cached_tokens=0,
        started_at=datetime.now(UTC),
        project_id=1,
    )

    cost = calculate_trace_cost(trace)

    # GPT-3.5-turbo: $0.50/1M input, $1.50/1M output
    # Expected: (1000/1M * 0.50) + (500/1M * 1.50) = 0.0005 + 0.00075 = 0.00125
    assert cost == pytest.approx(0.00125, rel=0.01)


@pytest.mark.asyncio
async def test_calculate_trace_cost_with_caching():
    """Test trace cost calculation with cached tokens."""
    trace = Trace(
        model="gpt-4.1",
        prompt_tokens=1000,
        completion_tokens=500,
        cached_tokens=500,  # Half the prompt was cached
        started_at=datetime.now(UTC),
        project_id=1,
    )

    cost = calculate_trace_cost(trace)

    # GPT-4.1: $2.00/1M input, $8.00/1M output, $0.50/1M cached
    # Expected: (500/1M * 2.00) + (500/1M * 0.50) + (500/1M * 8.00) = 0.001 + 0.00025 + 0.004 = 0.00525
    assert cost == pytest.approx(0.00525, rel=0.01)


@pytest.mark.asyncio
async def test_calculate_traces_cost():
    """Test calculating costs for multiple traces."""
    traces = [
        Trace(
            model="gpt-3.5-turbo",
            prompt_tokens=100,
            completion_tokens=50,
            cached_tokens=0,
            started_at=datetime.now(UTC),
            project_id=1,
        ),
        Trace(
            model="gpt-3.5-turbo",
            prompt_tokens=200,
            completion_tokens=100,
            cached_tokens=0,
            started_at=datetime.now(UTC),
            project_id=1,
        ),
    ]

    costs = calculate_traces_cost(traces)

    assert len(costs) == 2
    # GPT-3.5: $0.5/1M input, $1.5/1M output
    # First: (100/1M * 0.5) + (50/1M * 1.5) = 0.00005 + 0.000075 = 0.000125
    assert costs[0] == pytest.approx(0.000125, rel=0.01)
    # Second: (200/1M * 0.5) + (100/1M * 1.5) = 0.0001 + 0.00015 = 0.00025
    assert costs[1] == pytest.approx(0.00025, rel=0.01)


@pytest.mark.asyncio
async def test_get_traces_for_task(test_session: AsyncSession):
    """Test fetching traces for a task."""
    # Create project
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    # Create task
    task = Task(
        name="Test Task",
        description="Test task description",
        project_id=project.id,
    )
    test_session.add(task)
    await test_session.flush()

    # Create implementation
    impl = Implementation(
        task_id=task.id,
        prompt="Test prompt",
        model="gpt-3.5-turbo",
        max_output_tokens=1000,
    )
    test_session.add(impl)
    await test_session.flush()

    # Create traces
    base_time = datetime.now(UTC)
    for i in range(5):
        trace = Trace(
            project_id=project.id,
            implementation_id=impl.id,
            model="gpt-4",
            started_at=base_time + timedelta(seconds=i),
            completed_at=base_time + timedelta(seconds=i + 1),
            prompt_tokens=100 * (i + 1),
            completion_tokens=50 * (i + 1),
        )
        test_session.add(trace)

    await test_session.commit()

    # Test fetching traces
    service = TaskService(test_session)
    traces = await service.get_traces_for_task(task.id)

    assert len(traces) == 5

    # Test pagination
    traces_page1 = await service.get_traces_for_task(task.id, limit=2, offset=0)
    assert len(traces_page1) == 2

    traces_page2 = await service.get_traces_for_task(task.id, limit=2, offset=2)
    assert len(traces_page2) == 2


@pytest.mark.asyncio
async def test_calculate_task_cost_percentile(test_session: AsyncSession):
    """Test calculating cost percentile for a task."""
    # Create project
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    # Create task
    task = Task(
        name="Test Task",
        description="Test task description",
        project_id=project.id,
    )
    test_session.add(task)
    await test_session.flush()

    # Create implementation
    impl = Implementation(
        task_id=task.id,
        prompt="Test prompt",
        model="gpt-3.5-turbo",
        max_output_tokens=1000,
    )
    test_session.add(impl)
    await test_session.flush()

    # Create traces with varying costs
    base_time = datetime.now(UTC)
    for i in range(10):
        trace = Trace(
            project_id=project.id,
            implementation_id=impl.id,
            model="gpt-3.5-turbo",
            started_at=base_time + timedelta(seconds=i),
            completed_at=base_time + timedelta(seconds=i + 1),
            prompt_tokens=100 * (i + 1),  # 100, 200, 300, ..., 1000
            completion_tokens=50 * (i + 1),  # 50, 100, 150, ..., 500
        )
        test_session.add(trace)

    await test_session.commit()

    # Test cost percentile calculation
    service = TaskService(test_session)
    cost_percentile = await service.calculate_task_cost_percentile(task.id, percentile=95.0)

    assert cost_percentile is not None
    assert cost_percentile > 0


@pytest.mark.asyncio
async def test_calculate_task_latency_percentile(test_session: AsyncSession):
    """Test calculating latency percentile for a task."""
    # Create project
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    # Create task
    task = Task(
        name="Test Task",
        description="Test task description",
        project_id=project.id,
    )
    test_session.add(task)
    await test_session.flush()

    # Create implementation
    impl = Implementation(
        task_id=task.id,
        prompt="Test prompt",
        model="gpt-3.5-turbo",
        max_output_tokens=1000,
    )
    test_session.add(impl)
    await test_session.flush()

    # Create traces with varying latencies
    base_time = datetime.now(UTC)
    latencies = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]

    for i, latency in enumerate(latencies):
        trace = Trace(
            project_id=project.id,
            implementation_id=impl.id,
            model="gpt-4",
            started_at=base_time + timedelta(seconds=i * 10),
            completed_at=base_time + timedelta(seconds=i * 10 + latency),
            prompt_tokens=100,
            completion_tokens=50,
        )
        test_session.add(trace)

    await test_session.commit()

    # Test latency percentile calculation
    service = TaskService(test_session)
    latency_percentile = await service.calculate_task_latency_percentile(
        task.id,
        percentile=95.0,
    )

    assert latency_percentile is not None
    assert latency_percentile == pytest.approx(4.75, rel=0.1)

    # Test median
    latency_p50 = await service.calculate_task_latency_percentile(
        task.id,
        percentile=50.0,
    )
    assert latency_p50 == pytest.approx(2.75, rel=0.1)


@pytest.mark.asyncio
async def test_get_task_with_percentiles(test_session: AsyncSession):
    """Test getting a task with cost and latency percentiles."""
    # Create project
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    # Create task
    task = Task(
        name="Test Task",
        description="Test task description",
        project_id=project.id,
    )
    test_session.add(task)
    await test_session.flush()

    # Create implementation
    impl = Implementation(
        task_id=task.id,
        prompt="Test prompt",
        model="gpt-3.5-turbo",
        max_output_tokens=1000,
    )
    test_session.add(impl)
    await test_session.flush()

    # Create traces
    base_time = datetime.now(UTC)
    for i in range(5):
        trace = Trace(
            project_id=project.id,
            implementation_id=impl.id,
            model="gpt-3.5-turbo",
            started_at=base_time + timedelta(seconds=i),
            completed_at=base_time + timedelta(seconds=i + 1),
            prompt_tokens=100 * (i + 1),
            completion_tokens=50 * (i + 1),
        )
        test_session.add(trace)

    await test_session.commit()

    # Test getting task with percentiles
    service = TaskService(test_session)
    (
        task_result,
        cost_percentile,
        latency_percentile,
        last_activity,
    ) = await service.get_task_with_percentiles(
        task.id,
        percentile=95.0,
    )

    assert task_result is not None
    assert task_result.id == task.id
    assert cost_percentile is not None
    assert cost_percentile > 0
    assert latency_percentile is not None
    assert latency_percentile > 0
    assert last_activity is not None


@pytest.mark.asyncio
async def test_list_tasks_with_percentiles(test_session: AsyncSession):
    """Test listing tasks with cost and latency percentiles."""
    # Create project
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    # Create multiple tasks
    tasks = []
    for i in range(3):
        task = Task(
            name=f"Test Task {i}",
            description=f"Test task description {i}",
            project_id=project.id,
        )
        test_session.add(task)
        await test_session.flush()

        # Create implementation
        impl = Implementation(
            task_id=task.id,
            prompt=f"Test prompt {i}",
            model="gpt-3.5-turbo",
            max_output_tokens=1000,
        )
        test_session.add(impl)
        await test_session.flush()

        # Create traces
        base_time = datetime.now(UTC)
        for j in range(5):
            trace = Trace(
                project_id=project.id,
                implementation_id=impl.id,
                model="gpt-3.5-turbo",
                started_at=base_time + timedelta(seconds=j),
                completed_at=base_time + timedelta(seconds=j + 1),
                prompt_tokens=100 * (j + 1),
                completion_tokens=50 * (j + 1),
            )
            test_session.add(trace)

        tasks.append(task)

    await test_session.commit()

    # Test listing tasks with percentiles
    service = TaskService(test_session)
    results = await service.list_tasks_with_percentiles(
        project_id=project.id,
        percentile=95.0,
    )

    assert len(results) == 3
    for task_result, cost_percentile, latency_percentile, last_activity in results:
        assert task_result is not None
        assert cost_percentile is not None
        assert cost_percentile > 0
        assert latency_percentile is not None
        assert latency_percentile > 0
        assert last_activity is not None


@pytest.mark.asyncio
async def test_task_api_includes_percentiles(
    client: AsyncClient,
    test_session: AsyncSession,
    mock_openai_client,
):
    """Test that task API endpoints include cost and latency percentiles."""
    # Create a task via API
    payload = {
        "project": "Test Project",
        "path": "/api/test",
        "name": "Test Task",
        "description": "Test task description",
        "implementation": {
            "version": "0.1",
            "prompt": "Test prompt",
            "model": "gpt-3.5-turbo",
            "max_output_tokens": 1000,
        },
    }

    create_response = await client.post("/v1/tasks", json=payload)
    assert create_response.status_code == 201
    task_data = create_response.json()
    task_id = task_data["id"]

    # Add some traces
    from sqlalchemy import select

    impl_query = select(Implementation).where(Implementation.task_id == task_id)
    impl_result = await test_session.execute(impl_query)
    impl = impl_result.scalar_one()

    project_query = select(Project).where(Project.name == "Test Project")
    project_result = await test_session.execute(project_query)
    project = project_result.scalar_one()

    base_time = datetime.now(UTC)
    for i in range(5):
        trace = Trace(
            project_id=project.id,
            implementation_id=impl.id,
            model="gpt-3.5-turbo",
            started_at=base_time + timedelta(seconds=i),
            completed_at=base_time + timedelta(seconds=i + 1),
            prompt_tokens=100 * (i + 1),
            completion_tokens=50 * (i + 1),
        )
        test_session.add(trace)

    await test_session.commit()

    # Get task and verify percentiles are included
    get_response = await client.get(f"/v1/tasks/{task_id}")
    assert get_response.status_code == 200
    task_data = get_response.json()

    assert "cost_percentile" in task_data
    assert "latency_percentile" in task_data
    assert "last_activity" in task_data
    assert task_data["cost_percentile"] is not None
    assert task_data["latency_percentile"] is not None
    assert task_data["last_activity"] is not None

    # List tasks and verify percentiles are included
    list_response = await client.get("/v1/tasks")
    assert list_response.status_code == 200
    tasks = list_response.json()

    assert len(tasks) > 0
    for task in tasks:
        assert "cost_percentile" in task
        assert "latency_percentile" in task
        assert "last_activity" in task


@pytest.mark.asyncio
async def test_task_with_no_traces(test_session: AsyncSession):
    """Test that tasks with no traces return None for percentiles."""
    # Create project
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    # Create task without traces
    task = Task(
        name="Empty Task",
        description="Task with no traces",
        project_id=project.id,
    )
    test_session.add(task)
    await test_session.flush()

    # Create implementation but no traces
    impl = Implementation(
        task_id=task.id,
        prompt="Test prompt",
        model="gpt-4",
        max_output_tokens=1000,
    )
    test_session.add(impl)
    await test_session.commit()

    # Test that percentiles return None
    service = TaskService(test_session)
    cost_percentile = await service.calculate_task_cost_percentile(task.id)
    latency_percentile = await service.calculate_task_latency_percentile(task.id)

    assert cost_percentile is None
    assert latency_percentile is None


@pytest.mark.asyncio
async def test_custom_percentile_values(test_session: AsyncSession):
    """Test that custom percentile values work correctly."""
    # Create project
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    # Create task
    task = Task(
        name="Test Task",
        description="Test task description",
        project_id=project.id,
    )
    test_session.add(task)
    await test_session.flush()

    # Create implementation
    impl = Implementation(
        task_id=task.id,
        prompt="Test prompt",
        model="gpt-3.5-turbo",
        max_output_tokens=1000,
    )
    test_session.add(impl)
    await test_session.flush()

    # Create traces
    base_time = datetime.now(UTC)
    for i in range(10):
        trace = Trace(
            project_id=project.id,
            implementation_id=impl.id,
            model="gpt-3.5-turbo",
            started_at=base_time + timedelta(seconds=i),
            completed_at=base_time + timedelta(seconds=i + 1 + i * 0.1),
            prompt_tokens=100 * (i + 1),
            completion_tokens=50 * (i + 1),
        )
        test_session.add(trace)

    await test_session.commit()

    # Test different percentiles
    service = TaskService(test_session)

    p50 = await service.calculate_task_cost_percentile(task.id, percentile=50.0)
    p75 = await service.calculate_task_cost_percentile(task.id, percentile=75.0)
    p95 = await service.calculate_task_cost_percentile(task.id, percentile=95.0)
    p99 = await service.calculate_task_cost_percentile(task.id, percentile=99.0)

    assert p50 is not None
    assert p75 is not None
    assert p95 is not None
    assert p99 is not None

    # Higher percentiles should have higher or equal values
    assert p50 <= p75 <= p95 <= p99


@pytest.mark.asyncio
async def test_time_weighted_cost_percentile(test_session: AsyncSession):
    """Test that recent traces have more impact on cost percentile."""
    # Create project
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    # Create task
    task = Task(
        name="Test Task",
        description="Test task description",
        project_id=project.id,
    )
    test_session.add(task)
    await test_session.flush()

    # Create implementation
    impl = Implementation(
        task_id=task.id,
        prompt="Test prompt",
        model="gpt-3.5-turbo",
        max_output_tokens=1000,
    )
    test_session.add(impl)
    await test_session.flush()

    # Create traces with different ages and costs
    now = datetime.now(UTC)

    # Old expensive trace (2 weeks ago)
    old_expensive = Trace(
        project_id=project.id,
        implementation_id=impl.id,
        model="gpt-3.5-turbo",
        started_at=now - timedelta(hours=336),  # 2 weeks ago
        completed_at=now - timedelta(hours=336) + timedelta(seconds=1),
        prompt_tokens=10000,  # Very expensive
        completion_tokens=5000,
    )
    test_session.add(old_expensive)

    # Recent cheap traces (last hour)
    for i in range(5):
        cheap_trace = Trace(
            project_id=project.id,
            implementation_id=impl.id,
            model="gpt-3.5-turbo",
            started_at=now - timedelta(minutes=i),
            completed_at=now - timedelta(minutes=i) + timedelta(seconds=1),
            prompt_tokens=100,  # Very cheap
            completion_tokens=50,
        )
        test_session.add(cheap_trace)

    await test_session.commit()

    # Test cost percentile with time weighting
    service = TaskService(test_session)

    # With short half-life (1 hour), old trace should have minimal impact
    cost_percentile_short = await service.calculate_task_cost_percentile(
        task.id,
        percentile=95.0,
        half_life_hours=1.0,
    )

    # With long half-life (1000 hours), old trace should have more impact
    cost_percentile_long = await service.calculate_task_cost_percentile(
        task.id,
        percentile=95.0,
        half_life_hours=1000.0,
    )

    # Short half-life should give lower P95 (recent cheap traces dominate)
    # Long half-life should give higher P95 (old expensive trace has more weight)
    assert cost_percentile_short is not None
    assert cost_percentile_long is not None
    assert cost_percentile_short < cost_percentile_long


@pytest.mark.asyncio
async def test_time_weighted_latency_percentile(test_session: AsyncSession):
    """Test that recent traces have more impact on latency percentile."""
    # Create project
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    # Create task
    task = Task(
        name="Test Task",
        description="Test task description",
        project_id=project.id,
    )
    test_session.add(task)
    await test_session.flush()

    # Create implementation
    impl = Implementation(
        task_id=task.id,
        prompt="Test prompt",
        model="gpt-4",
        max_output_tokens=1000,
    )
    test_session.add(impl)
    await test_session.flush()

    # Create traces with different ages and latencies
    now = datetime.now(UTC)

    # Old slow trace (2 weeks ago)
    old_slow = Trace(
        project_id=project.id,
        implementation_id=impl.id,
        model="gpt-4",
        started_at=now - timedelta(hours=336),  # 2 weeks ago
        completed_at=now - timedelta(hours=336) + timedelta(seconds=10),  # 10 seconds
        prompt_tokens=100,
        completion_tokens=50,
    )
    test_session.add(old_slow)

    # Recent fast traces (last hour)
    for i in range(5):
        fast_trace = Trace(
            project_id=project.id,
            implementation_id=impl.id,
            model="gpt-3.5-turbo",
            started_at=now - timedelta(minutes=i),
            completed_at=now
            - timedelta(minutes=i)
            + timedelta(seconds=0.5),  # 0.5 seconds
            prompt_tokens=100,
            completion_tokens=50,
        )
        test_session.add(fast_trace)

    await test_session.commit()

    # Test latency percentile with time weighting
    service = TaskService(test_session)

    # With short half-life (1 hour), old trace should have minimal impact
    latency_percentile_short = await service.calculate_task_latency_percentile(
        task.id,
        percentile=95.0,
        half_life_hours=1.0,
    )

    # With long half-life (1000 hours), old trace should have more impact
    latency_percentile_long = await service.calculate_task_latency_percentile(
        task.id,
        percentile=95.0,
        half_life_hours=1000.0,
    )

    # Short half-life should give lower P95 (recent fast traces dominate)
    # Long half-life should give higher P95 (old slow trace has more weight)
    assert latency_percentile_short is not None
    assert latency_percentile_long is not None
    assert latency_percentile_short < latency_percentile_long


@pytest.mark.asyncio
async def test_api_accepts_half_life_parameter(
    client: AsyncClient,
    test_session: AsyncSession,
    mock_openai_client,
):
    """Test that API endpoints accept half_life_hours parameter."""
    # Create a task via API
    payload = {
        "project": "Test Project",
        "path": "/api/test",
        "name": "Test Task",
        "description": "Test task description",
        "implementation": {
            "version": "0.1",
            "prompt": "Test prompt",
            "model": "gpt-3.5-turbo",
            "max_output_tokens": 1000,
        },
    }

    create_response = await client.post("/v1/tasks", json=payload)
    assert create_response.status_code == 201
    task_data = create_response.json()
    task_id = task_data["id"]

    # Add some traces
    from sqlalchemy import select

    impl_query = select(Implementation).where(Implementation.task_id == task_id)
    impl_result = await test_session.execute(impl_query)
    impl = impl_result.scalar_one()

    project_query = select(Project).where(Project.name == "Test Project")
    project_result = await test_session.execute(project_query)
    project = project_result.scalar_one()

    base_time = datetime.now(UTC)
    for i in range(5):
        trace = Trace(
            project_id=project.id,
            implementation_id=impl.id,
            model="gpt-3.5-turbo",
            started_at=base_time + timedelta(seconds=i),
            completed_at=base_time + timedelta(seconds=i + 1),
            prompt_tokens=100 * (i + 1),
            completion_tokens=50 * (i + 1),
        )
        test_session.add(trace)

    await test_session.commit()

    # Test with custom half_life_hours
    get_response = await client.get(
        f"/v1/tasks/{task_id}?percentile=95&half_life_hours=24",
    )
    assert get_response.status_code == 200
    task_data = get_response.json()

    assert "cost_percentile" in task_data
    assert "latency_percentile" in task_data
    assert "last_activity" in task_data

    # Test list endpoint with half_life_hours
    list_response = await client.get("/v1/tasks?percentile=95&half_life_hours=24")
    assert list_response.status_code == 200
    tasks = list_response.json()
    assert len(tasks) > 0
