"""API endpoints for Grader management."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings, Settings
from app.database import get_session
from app.schemas.evaluation import (
    GraderCreate,
    GraderListItem,
    GraderRead,
    GraderUpdate,
)
from app.services.grading_service import GradingService, NotFoundError

router = APIRouter(prefix="/graders", tags=["graders"])


def get_grading_service(settings: Settings = Depends(get_settings)) -> GradingService:
    """Dependency to get a GradingService instance."""
    return GradingService(settings)


@router.post("", response_model=GraderRead, status_code=status.HTTP_201_CREATED)
async def create_grader(
    payload: GraderCreate,
    session: AsyncSession = Depends(get_session),
    grading_service: GradingService = Depends(get_grading_service),
) -> GraderRead:
    """Create a new grader for a project."""
    try:
        grader = await grading_service.create_grader(
            session=session,
            project_id=payload.project_id,
            name=payload.name,
            description=payload.description,
            prompt=payload.prompt,
            score_type=payload.score_type,
            model=payload.model,
            temperature=payload.temperature,
            reasoning=payload.reasoning,
            response_schema=payload.response_schema,
            max_output_tokens=payload.max_output_tokens,
            is_active=payload.is_active,
        )
        
        # Add grade_count for response
        grader_dict = GraderRead.model_validate(grader).model_dump()
        grader_dict["grade_count"] = 0
        return GraderRead(**grader_dict)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("", response_model=list[GraderListItem])
async def list_graders(
    project_id: int = Query(..., description="ID of the project"),
    session: AsyncSession = Depends(get_session),
    grading_service: GradingService = Depends(get_grading_service),
) -> list[GraderListItem]:
    """List all graders for a project."""
    try:
        graders_with_counts = await grading_service.list_graders(session, project_id)
        
        result = []
        for grader, grade_count in graders_with_counts:
            grader_dict = GraderListItem.model_validate(grader).model_dump()
            grader_dict["grade_count"] = grade_count
            result.append(GraderListItem(**grader_dict))
        
        return result
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{grader_id}", response_model=GraderRead)
async def get_grader(
    grader_id: int,
    session: AsyncSession = Depends(get_session),
    grading_service: GradingService = Depends(get_grading_service),
) -> GraderRead:
    """Get a specific grader by ID."""
    try:
        grader = await grading_service.get_grader(session, grader_id)
        
        # Get grade count
        grades = await grading_service.list_grades(session, grader_id=grader_id)
        
        grader_dict = GraderRead.model_validate(grader).model_dump()
        grader_dict["grade_count"] = len(grades)
        return GraderRead(**grader_dict)
    
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


@router.patch("/{grader_id}", response_model=GraderRead)
async def update_grader(
    grader_id: int,
    payload: GraderUpdate,
    session: AsyncSession = Depends(get_session),
    grading_service: GradingService = Depends(get_grading_service),
) -> GraderRead:
    """Update a grader."""
    try:
        # Filter out None values
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        
        grader = await grading_service.update_grader(
            session=session,
            grader_id=grader_id,
            **updates,
        )
        
        # Get grade count
        grades = await grading_service.list_grades(session, grader_id=grader_id)
        
        grader_dict = GraderRead.model_validate(grader).model_dump()
        grader_dict["grade_count"] = len(grades)
        return GraderRead(**grader_dict)
    
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{grader_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_grader(
    grader_id: int,
    session: AsyncSession = Depends(get_session),
    grading_service: GradingService = Depends(get_grading_service),
) -> None:
    """Delete a grader and all associated grades."""
    try:
        await grading_service.delete_grader(session, grader_id)
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

