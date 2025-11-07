"""API endpoints for managing providers and models."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.providers import (
    ModelCreate,
    ModelResponse,
    ProviderCreate,
    ProviderResponse,
    ProviderUpdate,
)
from app.services.provider_service import ProviderService

router = APIRouter(prefix="/providers", tags=["providers"])


def get_provider_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProviderService:
    """Get provider service dependency."""
    return ProviderService(session)


@router.get("", response_model=list[ProviderResponse])
async def list_providers(
    service: Annotated[ProviderService, Depends(get_provider_service)],
) -> list[ProviderResponse]:
    """List all providers.

    Returns:
        List of all providers (without decrypted API keys)

    """
    providers = await service.list_providers()
    return [
        ProviderResponse(
            id=p.id,
            name=p.name,
            display_name=p.display_name,
            base_url=p.base_url,
            has_api_key=p.api_key_encrypted is not None,
            models=[
                ModelResponse(
                    id=m.id,
                    name=m.name,
                    display_name=m.display_name,
                    provider_id=m.provider_id,
                )
                for m in p.models
            ],
        )
        for p in providers
    ]


@router.get("/models", response_model=list[str])
async def list_all_models(
    service: Annotated[ProviderService, Depends(get_provider_service)],
) -> list[str]:
    """Return models from providers with API keys configured as canonical identifiers."""

    models = await service.list_canonical_model_names_with_api_keys()
    return models


@router.get("/with-keys", response_model=list[ProviderResponse])
async def list_providers_with_keys(
    service: Annotated[ProviderService, Depends(get_provider_service)],
) -> list[ProviderResponse]:
    """List all providers that have API keys configured.

    Returns:
        List of providers with API keys

    """
    providers = await service.list_providers_with_api_keys()
    return [
        ProviderResponse(
            id=p.id,
            name=p.name,
            display_name=p.display_name,
            base_url=p.base_url,
            has_api_key=True,
            models=[
                ModelResponse(
                    id=m.id,
                    name=m.name,
                    display_name=m.display_name,
                    provider_id=m.provider_id,
                )
                for m in p.models
            ],
        )
        for p in providers
    ]


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(
    provider_id: int,
    service: Annotated[ProviderService, Depends(get_provider_service)],
) -> ProviderResponse:
    """Get a provider by ID.

    Args:
        provider_id: The provider ID

    Returns:
        The provider

    Raises:
        HTTPException: If provider not found

    """
    provider = await service.get_provider_by_id(provider_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider with ID {provider_id} not found",
        )

    return ProviderResponse(
        id=provider.id,
        name=provider.name,
        display_name=provider.display_name,
        base_url=provider.base_url,
        has_api_key=provider.api_key_encrypted is not None,
        models=[
            ModelResponse(
                id=m.id,
                name=m.name,
                display_name=m.display_name,
                provider_id=m.provider_id,
            )
            for m in provider.models
        ],
    )


@router.post("", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(
    provider_data: ProviderCreate,
    service: Annotated[ProviderService, Depends(get_provider_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProviderResponse:
    """Create a new provider.

    Args:
        provider_data: The provider data
        service: The provider service
        session: The database session

    Returns:
        The created provider

    Raises:
        HTTPException: If provider with that name already exists

    """
    # Check if provider already exists
    existing = await service.get_provider_by_name(provider_data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider with name '{provider_data.name}' already exists",
        )

    provider = await service.create_provider(
        name=provider_data.name,
        display_name=provider_data.display_name,
        api_key=provider_data.api_key,
        base_url=provider_data.base_url,
    )

    # If models are provided (for custom providers), add them
    if provider_data.models:
        for model_name in provider_data.models:
            model_name = model_name.strip()
            if model_name:
                await service.add_model_to_provider(
                    provider_id=provider.id,
                    name=model_name,
                    display_name=model_name,
                )

    await session.commit()

    # Re-fetch provider with models eagerly loaded
    provider = await service.get_provider_by_id(provider.id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve created provider",
        )

    return ProviderResponse(
        id=provider.id,
        name=provider.name,
        display_name=provider.display_name,
        base_url=provider.base_url,
        has_api_key=provider.api_key_encrypted is not None,
        models=[
            ModelResponse(
                id=m.id,
                name=m.name,
                display_name=m.display_name,
                provider_id=m.provider_id,
            )
            for m in provider.models
        ],
    )


@router.put("/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    provider_id: int,
    provider_data: ProviderUpdate,
    service: Annotated[ProviderService, Depends(get_provider_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProviderResponse:
    """Update a provider.

    Args:
        provider_id: The provider ID
        provider_data: The provider data
        service: The provider service
        session: The database session

    Returns:
        The updated provider

    Raises:
        HTTPException: If provider not found

    """
    try:
        provider = await service.update_provider(
            provider_id=provider_id,
            display_name=provider_data.display_name,
            api_key=provider_data.api_key,
            base_url=provider_data.base_url,
        )
        await session.commit()

        # Re-fetch provider with models eagerly loaded
        provider = await service.get_provider_by_id(provider_id)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve updated provider",
            )

        return ProviderResponse(
            id=provider.id,
            name=provider.name,
            display_name=provider.display_name,
            base_url=provider.base_url,
            has_api_key=provider.api_key_encrypted is not None,
            models=[
                ModelResponse(
                    id=m.id,
                    name=m.name,
                    display_name=m.display_name,
                    provider_id=m.provider_id,
                )
                for m in provider.models
            ],
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    provider_id: int,
    service: Annotated[ProviderService, Depends(get_provider_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """Delete a provider.

    Args:
        provider_id: The provider ID
        service: The provider service
        session: The database session

    Raises:
        HTTPException: If provider not found

    """
    try:
        await service.delete_provider(provider_id)
        await session.commit()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.get("/{provider_id}/models", response_model=list[ModelResponse])
async def list_provider_models(
    provider_id: int,
    service: Annotated[ProviderService, Depends(get_provider_service)],
) -> list[ModelResponse]:
    """List all models for a provider.

    Args:
        provider_id: The provider ID
        service: The provider service

    Returns:
        List of models for the provider

    """
    models = await service.list_models_by_provider(provider_id)
    return [
        ModelResponse(
            id=m.id,
            name=m.name,
            display_name=m.display_name,
            provider_id=m.provider_id,
        )
        for m in models
    ]


@router.post(
    "/{provider_id}/models",
    response_model=ModelResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_model_to_provider(
    provider_id: int,
    model_data: ModelCreate,
    service: Annotated[ProviderService, Depends(get_provider_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ModelResponse:
    """Add a model to a provider.

    Args:
        provider_id: The provider ID
        model_data: The model data
        service: The provider service
        session: The database session

    Returns:
        The created model

    Raises:
        HTTPException: If provider not found

    """
    try:
        model = await service.add_model_to_provider(
            provider_id=provider_id,
            name=model_data.name,
            display_name=model_data.display_name,
        )
        await session.commit()
        return ModelResponse(
            id=model.id,
            name=model.name,
            display_name=model.display_name,
            provider_id=model.provider_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.delete("/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    model_id: int,
    service: Annotated[ProviderService, Depends(get_provider_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """Delete a model.

    Args:
        model_id: The model ID
        service: The provider service
        session: The database session

    Raises:
        HTTPException: If model not found

    """
    try:
        await service.delete_model(model_id)
        await session.commit()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
