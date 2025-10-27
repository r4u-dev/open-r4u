"""API endpoints for Grade management."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings, Settings
from app.database import get_session
from app.schemas.evaluation import (
    GradeListItem,
    GradeRead,
    GradeTargetRequest,
)
from app.services.grading_service import GradingService, NotFoundError, BadRequestError

router = APIRouter(prefix="/grades", tags=["grades"])


def get_grading_service(settings: Settings = Depends(get_settings)) -> GradingService:
    """Dependency to get a GradingService instance."""
    return GradingService(settings)


@router.post(
    "/graders/{grader_id}/grade",
    response_model=GradeRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_grade(
    grader_id: int,
    payload: GradeTargetRequest,
    session: AsyncSession = Depends(get_session),
    grading_service: GradingService = Depends(get_grading_service),
) -> GradeRead:
    """Execute grading for a trace or execution result.
    
    The request body must specify either trace_id or execution_result_id.
    """
    try:
        grade = await grading_service.execute_grading(
            session=session,
            grader_id=grader_id,
            trace_id=payload.trace_id,
            execution_result_id=payload.execution_result_id,
            test_case_id=payload.test_case_id,
        )
        
        return GradeRead.model_validate(grade)
    
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
    except BadRequestError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{grade_id}", response_model=GradeRead)
async def get_grade(
    grade_id: int,
    session: AsyncSession = Depends(get_session),
    grading_service: GradingService = Depends(get_grading_service),
) -> GradeRead:
    """Get a specific grade by ID."""
    try:
        grade = await grading_service.get_grade(session, grade_id)
        return GradeRead.model_validate(grade)
    
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/traces/{trace_id}/grades", response_model=list[GradeListItem])
async def list_grades_for_trace(
    trace_id: int,
    session: AsyncSession = Depends(get_session),
    grading_service: GradingService = Depends(get_grading_service),
) -> list[GradeListItem]:
    """List all grades for a trace."""
    try:
        grades = await grading_service.list_grades_for_trace(session, trace_id)
        return [GradeListItem.model_validate(grade) for grade in grades]
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/executions/{execution_result_id}/grades", response_model=list[GradeListItem])
async def list_grades_for_execution(
    execution_result_id: int,
    session: AsyncSession = Depends(get_session),
    grading_service: GradingService = Depends(get_grading_service),
) -> list[GradeListItem]:
    """List all grades for an execution result."""
    try:
        grades = await grading_service.list_grades_for_execution(
            session, execution_result_id
        )
        return [GradeListItem.model_validate(grade) for grade in grades]
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/graders/{grader_id}/grades", response_model=list[GradeListItem])
async def list_grades_for_grader(
    grader_id: int,
    session: AsyncSession = Depends(get_session),
    grading_service: GradingService = Depends(get_grading_service),
) -> list[GradeListItem]:
    """List all grades produced by a grader."""
    try:
        grades = await grading_service.list_grades_for_grader(session, grader_id)
        return [GradeListItem.model_validate(grade) for grade in grades]
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/{grade_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_grade(
    grade_id: int,
    session: AsyncSession = Depends(get_session),
    grading_service: GradingService = Depends(get_grading_service),
) -> None:
    """Delete a grade."""
    try:
        await grading_service.delete_grade(session, grade_id)
    
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

