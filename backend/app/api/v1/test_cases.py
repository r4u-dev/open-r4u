"""API endpoints for Test Case management."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_session
from app.schemas.evaluation import (
    TestCaseCreate,
    TestCaseListItem,
    TestCaseRead,
    TestCasesFromTracesRequest,
    TestCasesFromTracesResponse,
    TestCaseUpdate,
)
from app.services.evaluation_service import (
    BadRequestError,
    EvaluationService,
    NotFoundError,
)

router = APIRouter(prefix="/test-cases", tags=["test-cases"])


def get_evaluation_service(
    settings: Settings = Depends(get_settings),
) -> EvaluationService:
    """Dependency to get an EvaluationService instance."""
    return EvaluationService(settings)


@router.post("", response_model=TestCaseRead, status_code=status.HTTP_201_CREATED)
async def create_test_case(
    payload: TestCaseCreate,
    session: AsyncSession = Depends(get_session),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> TestCaseRead:
    """Create a new test case for a task."""
    try:
        test_case = await evaluation_service.create_test_case(
            session=session,
            task_id=payload.task_id,
            description=payload.description,
            arguments=payload.arguments,
            expected_output=payload.expected_output,
        )
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create test case: {e!s}",
        )

    return TestCaseRead.model_validate(test_case)


@router.get("", response_model=list[TestCaseListItem])
async def list_test_cases(
    task_id: int | None = Query(None, description="Filter by task ID"),
    session: AsyncSession = Depends(get_session),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> list[TestCaseListItem]:
    """List test cases, optionally filtered by task_id."""
    try:
        test_cases = await evaluation_service.list_test_cases(
            session=session,
            task_id=task_id,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list test cases: {e!s}",
        )

    return [TestCaseListItem.model_validate(test_case) for test_case in test_cases]


@router.get(
    "/{test_case_id}",
    response_model=TestCaseRead,
)
async def get_test_case(
    test_case_id: int,
    session: AsyncSession = Depends(get_session),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> TestCaseRead:
    """Get a specific test case by ID."""
    try:
        test_case = await evaluation_service.get_test_case(
            session=session,
            test_case_id=test_case_id,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get test case: {e!s}",
        )

    return TestCaseRead.model_validate(test_case)


@router.patch(
    "/{test_case_id}",
    response_model=TestCaseRead,
)
async def update_test_case(
    test_case_id: int,
    payload: TestCaseUpdate,
    session: AsyncSession = Depends(get_session),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> TestCaseRead:
    """Update a test case."""
    try:
        # Convert payload to dict, excluding None values
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}

        test_case = await evaluation_service.update_test_case(
            session=session,
            test_case_id=test_case_id,
            **updates,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update test case: {e!s}",
        )

    return TestCaseRead.model_validate(test_case)


@router.delete(
    "/{test_case_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_test_case(
    test_case_id: int,
    session: AsyncSession = Depends(get_session),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> None:
    """Delete a test case."""
    try:
        await evaluation_service.delete_test_case(
            session=session,
            test_case_id=test_case_id,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete test case: {e!s}",
        )


@router.post(
    "/from-traces",
    response_model=TestCasesFromTracesResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_test_cases_from_traces(
    payload: TestCasesFromTracesRequest,
    session: AsyncSession = Depends(get_session),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> TestCasesFromTracesResponse:
    """Create test cases from existing traces.

    This endpoint takes a list of trace IDs and creates test cases for a task.
    The input messages are extracted from the trace input items, and the expected
    output is generated by concatenating all text items from the trace output.
    """
    try:
        test_cases = await evaluation_service.create_test_cases_from_traces(
            session=session,
            task_id=payload.task_id,
            trace_ids=payload.trace_ids,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create test cases from traces: {e!s}",
        )

    return TestCasesFromTracesResponse(
        created_count=len(test_cases),
        test_cases=[TestCaseRead.model_validate(tc) for tc in test_cases],
    )
