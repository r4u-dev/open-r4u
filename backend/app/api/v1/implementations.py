"""API endpoints for Implementation management."""


from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.tasks import ImplementationCreate, ImplementationRead
from app.services.implementation_service import ImplementationService
from app.services.pricing_service import PricingService

router = APIRouter(prefix="/implementations", tags=["implementations"])


def get_pricing_service() -> PricingService:
    """Dependency provider for PricingService."""
    return PricingService()


def get_implementation_service(
    session: AsyncSession = Depends(get_session),
) -> ImplementationService:
    """Dependency provider for ImplementationService."""
    return ImplementationService(session)


@router.get("", response_model=list[ImplementationRead])
async def list_implementations(
    task_id: int | None = None,
    service: ImplementationService = Depends(get_implementation_service),
) -> list[ImplementationRead]:
    """Return all implementations, optionally filtered by task_id."""
    implementations = await service.list_implementations(task_id=task_id)
    return [ImplementationRead.model_validate(impl) for impl in implementations]


@router.get("/models")
async def list_available_models(
    pricing_service: PricingService = Depends(get_pricing_service),
) -> list[str]:
    """Return a flat list of available model names from models.yaml.

    Aggregates models from all providers via PricingService.
    """
    by_provider = pricing_service.get_available_models()
    models_set: set[str] = set()
    for models in by_provider.values():
        models_set.update(models)
    return sorted(models_set)


@router.get("/{implementation_id}", response_model=ImplementationRead)
async def get_implementation(
    implementation_id: int,
    service: ImplementationService = Depends(get_implementation_service),
) -> ImplementationRead:
    """Get a specific implementation by ID."""
    implementation = await service.get_implementation(implementation_id)

    if not implementation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Implementation with id {implementation_id} not found",
        )

    return ImplementationRead.model_validate(implementation)


@router.post("", response_model=ImplementationRead, status_code=status.HTTP_201_CREATED)
async def create_implementation(
    task_id: int,
    payload: ImplementationCreate,
    service: ImplementationService = Depends(get_implementation_service),
) -> ImplementationRead:
    """Create a new implementation version for a task."""
    try:
        implementation = await service.create_implementation(
            task_id=task_id,
            payload=payload,
        )
        return ImplementationRead.model_validate(implementation)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.put("/{implementation_id}", response_model=ImplementationRead)
async def update_implementation(
    implementation_id: int,
    payload: ImplementationCreate,
    service: ImplementationService = Depends(get_implementation_service),
) -> ImplementationRead:
    """Update an existing implementation."""
    try:
        implementation = await service.update_implementation(
            implementation_id=implementation_id,
            payload=payload,
        )
        return ImplementationRead.model_validate(implementation)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete("/{implementation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_implementation(
    implementation_id: int,
    service: ImplementationService = Depends(get_implementation_service),
) -> None:
    """Delete an implementation."""
    try:
        await service.delete_implementation(implementation_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/{implementation_id}/set-production", response_model=ImplementationRead)
async def set_production_version(
    implementation_id: int,
    service: ImplementationService = Depends(get_implementation_service),
) -> ImplementationRead:
    """Set this implementation as the production version for its task."""
    try:
        implementation = await service.set_production_version(implementation_id)
        return ImplementationRead.model_validate(implementation)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

