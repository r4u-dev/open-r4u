"""Provider service for managing LLM providers and models."""

from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.providers import Model, Provider
from app.services.encryption import get_encryption_service


class ProviderService:
    """Service for managing LLM providers and models."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the provider service.

        Args:
            session: The database session

        """
        self.session = session
        self.encryption_service = get_encryption_service()

    async def get_provider_by_name(self, name: str) -> Provider | None:
        """Get a provider by name.

        Args:
            name: The provider name

        Returns:
            The provider or None if not found

        """
        result = await self.session.execute(
            select(Provider)
            .options(joinedload(Provider.models))
            .where(Provider.name == name),
        )
        return result.unique().scalar_one_or_none()

    async def get_provider_by_id(self, provider_id: int) -> Provider | None:
        """Get a provider by ID.

        Args:
            provider_id: The provider ID

        Returns:
            The provider or None if not found

        """
        result = await self.session.execute(
            select(Provider)
            .options(joinedload(Provider.models))
            .where(Provider.id == provider_id),
        )
        return result.unique().scalar_one_or_none()

    async def list_providers(self) -> list[Provider]:
        """List all providers.

        Returns:
            List of all providers

        """
        result = await self.session.execute(
            select(Provider).options(joinedload(Provider.models)),
        )
        return list(result.unique().scalars().all())

    async def list_providers_with_api_keys(self) -> list[Provider]:
        """List all providers that have API keys configured.

        Returns:
            List of providers with API keys

        """
        result = await self.session.execute(
            select(Provider)
            .options(joinedload(Provider.models))
            .where(Provider.api_key_encrypted.isnot(None)),
        )
        return list(result.unique().scalars().all())

    async def create_provider(
        self,
        name: str,
        display_name: str,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> Provider:
        """Create a new provider.

        Args:
            name: The provider name (unique identifier)
            display_name: The display name
            api_key: Optional API key to encrypt and store
            base_url: Optional base URL for custom providers

        Returns:
            The created provider

        """
        encrypted_key = None
        if api_key:
            encrypted_key = self.encryption_service.encrypt(api_key)

        provider = Provider(
            name=name,
            display_name=display_name,
            base_url=base_url,
            api_key_encrypted=encrypted_key,
        )
        self.session.add(provider)
        await self.session.flush()
        return provider

    async def update_provider(
        self,
        provider_id: int,
        display_name: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> Provider:
        """Update a provider.

        Args:
            provider_id: The provider ID
            display_name: Optional new display name
            api_key: Optional new API key
            base_url: Optional new base URL

        Returns:
            The updated provider

        Raises:
            ValueError: If provider not found

        """
        provider = await self.get_provider_by_id(provider_id)
        if not provider:
            msg = f"Provider with ID {provider_id} not found"
            raise ValueError(msg)

        if display_name is not None:
            provider.display_name = display_name

        if api_key is not None:
            provider.api_key_encrypted = self.encryption_service.encrypt(api_key)

        if base_url is not None:
            provider.base_url = base_url

        await self.session.flush()
        return provider

    async def delete_provider(self, provider_id: int) -> None:
        """Delete a provider.

        Args:
            provider_id: The provider ID

        Raises:
            ValueError: If provider not found

        """
        provider = await self.get_provider_by_id(provider_id)
        if not provider:
            msg = f"Provider with ID {provider_id} not found"
            raise ValueError(msg)

        await self.session.delete(provider)
        await self.session.flush()

    def get_decrypted_api_key(self, provider: Provider) -> str | None:
        """Get the decrypted API key for a provider.

        Args:
            provider: The provider

        Returns:
            The decrypted API key or None if not set

        """
        if not provider.api_key_encrypted:
            return None
        return self.encryption_service.decrypt(provider.api_key_encrypted)

    async def add_model_to_provider(
        self,
        provider_id: int,
        name: str,
        display_name: str,
    ) -> Model:
        """Add a model to a provider.

        Args:
            provider_id: The provider ID
            name: The model name
            display_name: The model display name

        Returns:
            The created model

        Raises:
            ValueError: If provider not found

        """
        provider = await self.get_provider_by_id(provider_id)
        if not provider:
            msg = f"Provider with ID {provider_id} not found"
            raise ValueError(msg)

        model = Model(
            provider_id=provider_id,
            name=name,
            display_name=display_name,
        )
        self.session.add(model)
        await self.session.flush()
        return model

    async def list_models(self) -> list[Model]:
        """List all models.

        Returns:
            List of all models

        """
        result = await self.session.execute(select(Model))
        return list(result.unique().scalars().all())

    async def list_models_by_provider(self, provider_id: int) -> list[Model]:
        """List all models for a provider.

        Args:
            provider_id: The provider ID

        Returns:
            List of models for the provider

        """
        result = await self.session.execute(
            select(Model).where(Model.provider_id == provider_id),
        )
        return list(result.unique().scalars().all())

    async def get_model_by_id(self, model_id: int) -> Model | None:
        """Get a model by ID.

        Args:
            model_id: The model ID

        Returns:
            The model or None if not found

        """
        result = await self.session.execute(select(Model).where(Model.id == model_id))
        return result.unique().scalar_one_or_none()

    async def delete_model(self, model_id: int) -> None:
        """Delete a model.

        Args:
            model_id: The model ID

        Raises:
            ValueError: If model not found

        """
        model = await self.get_model_by_id(model_id)
        if not model:
            msg = f"Model with ID {model_id} not found"
            raise ValueError(msg)

        await self.session.delete(model)
        await self.session.flush()


async def load_providers_from_yaml(
    session: AsyncSession,
    yaml_path: str | Path,
) -> None:
    """Load providers and models from a YAML file.

    This function reads the models.yaml file and creates providers and models
    in the database if they don't already exist.

    Args:
        session: The database session
        yaml_path: Path to the models.yaml file

    """
    yaml_path = Path(yaml_path)
    if not yaml_path.exists():
        return

    with yaml_path.open() as f:
        data = yaml.safe_load(f)

    if not data or "providers" not in data:
        return

    service = ProviderService(session)

    for provider_name, provider_data in data["providers"].items():
        # Check if provider already exists
        existing_provider = await service.get_provider_by_name(provider_name)

        if not existing_provider:
            # Create new provider without API key (user will add it later)
            display_name = provider_data.get("display_name", provider_name)
            provider = await service.create_provider(
                name=provider_name,
                display_name=display_name,
            )
        else:
            provider = existing_provider

        # Add models to the provider
        models_data = provider_data.get("models", {})
        for model_name in models_data.keys():
            # Check if model already exists
            existing_models = await service.list_models_by_provider(provider.id)
            existing_model_names = {m.name for m in existing_models}

            if model_name not in existing_model_names:
                # Use model name as display name by default
                await service.add_model_to_provider(
                    provider_id=provider.id,
                    name=model_name,
                    display_name=model_name,
                )

    await session.commit()
