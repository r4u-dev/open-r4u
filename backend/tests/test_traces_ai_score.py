
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.models.projects import Project
from app.models.traces import Trace
from app.models.evaluation import Grader, Grade
from app.enums import ScoreType

@pytest.mark.asyncio
async def test_list_traces_with_ai_score_and_sorting(
    client: AsyncClient,
    test_session: AsyncSession,
):
    # Setup: Create Project
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    # Setup: Create Grader
    grader = Grader(
        project_id=project.id,
        name="Test Grader",
        prompt="Grade this",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=100,
    )
    test_session.add(grader)
    await test_session.flush()

    # Setup: Create Traces
    # Trace 1: High score
    trace1 = Trace(
        project_id=project.id,
        model="gpt-4",
        started_at=datetime(2025, 10, 15, 10, 0, 0),
        input_items=[],
        output_items=[],
    )
    test_session.add(trace1)
    await test_session.flush()
    
    grade1 = Grade(
        grader_id=grader.id,
        trace_id=trace1.id,
        score_float=0.9,
        grading_started_at=datetime.now(),
    )
    test_session.add(grade1)

    # Trace 2: Low score
    trace2 = Trace(
        project_id=project.id,
        model="gpt-4",
        started_at=datetime(2025, 10, 15, 11, 0, 0),
        input_items=[],
        output_items=[],
    )
    test_session.add(trace2)
    await test_session.flush()

    grade2 = Grade(
        grader_id=grader.id,
        trace_id=trace2.id,
        score_float=0.1,
        grading_started_at=datetime.now(),
    )
    test_session.add(grade2)

    # Trace 3: No score
    trace3 = Trace(
        project_id=project.id,
        model="gpt-4",
        started_at=datetime(2025, 10, 15, 12, 0, 0),
        input_items=[],
        output_items=[],
    )
    test_session.add(trace3)
    await test_session.commit()

    # Test 1: Verify ai_score is present
    response = await client.get("/v1/traces")
    assert response.status_code == 200
    data = response.json()
    
    # Map by id for easier checking
    traces_by_id = {t["id"]: t for t in data}
    
    assert traces_by_id[trace1.id]["ai_score"] == 0.9
    assert traces_by_id[trace2.id]["ai_score"] == 0.1
    assert traces_by_id[trace3.id]["ai_score"] is None

    # Test 2: Sort by ai_score DESC
    # Expected: Trace 1 (0.9), Trace 2 (0.1), Trace 3 (None)
    response = await client.get("/v1/traces?sort_field=ai_score&sort_order=desc")
    assert response.status_code == 200
    data = response.json()
    
    assert data[0]["id"] == trace1.id
    assert data[1]["id"] == trace2.id
    assert data[2]["id"] == trace3.id

    # Test 3: Sort by ai_score ASC
    # Expected: Trace 2 (0.1), Trace 1 (0.9), Trace 3 (None) - NULLS LAST
    response = await client.get("/v1/traces?sort_field=ai_score&sort_order=asc")
    assert response.status_code == 200
    data = response.json()
    
    assert data[0]["id"] == trace2.id
    assert data[1]["id"] == trace1.id
    assert data[2]["id"] == trace3.id
