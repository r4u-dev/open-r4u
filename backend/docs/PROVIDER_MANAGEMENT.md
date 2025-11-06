# Provider and API Key Management

## Overview

This document describes the provider and API key management system for Open R4U. The system allows users to securely store and manage API keys for various LLM providers through the UI.

## Architecture

### Database Schema

#### Provider Table
- `id`: Primary key
- `name`: Unique provider identifier (e.g., "openai", "anthropic")
- `display_name`: Human-readable name (e.g., "OpenAI", "Anthropic (Claude)")
- `base_url`: Optional base URL for custom providers
- `api_key_encrypted`: Encrypted API key (nullable)
- `created_at`: Timestamp
- `updated_at`: Timestamp

#### Model Table
- `id`: Primary key
- `provider_id`: Foreign key to provider
- `name`: Model identifier (e.g., "gpt-4", "claude-3-opus")
- `display_name`: Human-readable model name
- `created_at`: Timestamp
- `updated_at`: Timestamp
- Unique constraint on `(provider_id, name)`

### Security

#### Encryption
- API keys are encrypted at rest using **Fernet symmetric encryption** from the `cryptography` library
- Master encryption key is stored in the `ENCRYPTION_KEY` environment variable
- Keys are only decrypted when needed (e.g., making LLM API calls)
- API responses NEVER include decrypted keys

#### Key Generation
Generate a new encryption key:
```bash
python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

Add to `.env` file:
```
ENCRYPTION_KEY=your-generated-key-here
```

**IMPORTANT**:
- Never commit the encryption key to version control
- Store it securely (e.g., secrets manager in production)
- If the key is lost, all encrypted API keys become unrecoverable
- Changing the key will invalidate all existing encrypted keys

### Data Flow

1. **Startup**: Application loads providers and models from `models.yaml`
2. **User adds API key**: Key is encrypted and stored in database
3. **LLM call**: Key is decrypted on-demand and used for API request
4. **API responses**: Only return `has_api_key: bool`, never the actual key

## Setup

### 1. Install Dependencies

```bash
cd backend
uv add cryptography pyyaml
```

### 2. Generate Encryption Key

```bash
python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

### 3. Configure Environment

Create or update `.env` file:
```env
ENCRYPTION_KEY=your-generated-key-here
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/postgres
```

### 4. Run Migrations

```bash
uv run alembic upgrade head
```

### 5. Start Application

The application will automatically load providers and models from `models.yaml` on startup.

```bash
uv run uvicorn app.main:app --reload
```

## API Endpoints

### Providers

#### List all providers
```http
GET /api/v1/providers
```

Returns all providers with `has_api_key` flag but without decrypted keys.

#### List providers with API keys
```http
GET /api/v1/providers/with-keys
```

Returns only providers that have API keys configured.

#### Get provider by ID
```http
GET /api/v1/providers/{provider_id}
```

#### Create custom provider
```http
POST /api/v1/providers
Content-Type: application/json

{
  "name": "my-custom-provider",
  "display_name": "My Custom Provider",
  "base_url": "https://api.example.com/v1",
  "api_key": "sk-...",
  "models": ["model-1", "model-2", "model-3"]
}
```

For custom providers, `models` should be a list of model names (comma-separated string in the frontend).

#### Update provider (add/update API key)
```http
PUT /api/v1/providers/{provider_id}
Content-Type: application/json

{
  "api_key": "sk-new-key...",
  "display_name": "Updated Display Name",
  "base_url": "https://new-url.example.com"
}
```

All fields are optional. Only provided fields will be updated.

#### Delete provider
```http
DELETE /api/v1/providers/{provider_id}
```

Only custom providers can be deleted. Predefined providers from `models.yaml` should remain.

### Models

#### List all models for a provider
```http
GET /api/v1/providers/{provider_id}/models
```

#### Add model to provider
```http
POST /api/v1/providers/{provider_id}/models
Content-Type: application/json

{
  "name": "model-name",
  "display_name": "Model Display Name"
}
```

#### Delete model
```http
DELETE /api/v1/providers/models/{model_id}
```

## Frontend Integration

### Display Providers with API Keys

```typescript
// Fetch providers that have API keys configured
const response = await fetch('/api/v1/providers/with-keys');
const providers = await response.json();

// Each provider has:
// - id, name, display_name, base_url
// - has_api_key: boolean
// - models: array of models
```

### Add/Update Provider

```typescript
// For existing providers (OpenAI, Anthropic, etc.)
// Use PUT to update with API key
await fetch(`/api/v1/providers/${providerId}`, {
  method: 'PUT',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    api_key: userApiKey
  })
});

// For custom providers
// Use POST to create
await fetch('/api/v1/providers', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: 'custom-provider-123',
    display_name: 'My Custom Provider',
    base_url: 'https://api.example.com/v1',
    api_key: userApiKey,
    models: ['model-1', 'model-2'] // Array of model names
  })
});
```

### Provider Selection Flow

1. User clicks "Add Provider"
2. Fetch all providers: `GET /api/v1/providers`
3. Show dropdown with:
   - All predefined providers (from `models.yaml`)
   - "Custom Provider" option
4. If user selects predefined provider:
   - Get provider ID from response
   - Show API key input
   - Use `PUT /api/v1/providers/{id}` to update
5. If user selects "Custom Provider":
   - Show: name, display_name, base_url, api_key, models (comma-separated)
   - Use `POST /api/v1/providers` to create

## Predefined Providers (from models.yaml)

The following providers are automatically loaded on startup:
- OpenAI
- Anthropic (Claude)
- xAI (Grok)
- Google (Gemini)

Each provider comes with predefined models. Users only need to add their API keys.

## Usage with LiteLLM

To integrate with LiteLLM for making LLM calls:

```python
from app.services.provider_service import ProviderService
from app.database import get_session

async with get_session() as session:
    service = ProviderService(session)
    provider = await service.get_provider_by_name("openai")

    if provider:
        api_key = service.get_decrypted_api_key(provider)
        # Use api_key with LiteLLM
```

## Testing

Run tests:
```bash
cd backend
uv run pytest tests/test_encryption.py -v
uv run pytest tests/test_providers.py -v
```

## Security Best Practices

1. **Never log API keys**: Ensure keys don't appear in logs
2. **HTTPS in production**: All API calls should use HTTPS
3. **Key rotation**: Plan for periodic key rotation
4. **Audit trail**: Log when keys are added/modified (user, timestamp)
5. **Access control**: Implement user authentication and authorization
6. **Backup**: Document backup process for encrypted keys
7. **Monitoring**: Monitor for unauthorized access attempts

## Migration from Environment Variables

If you have existing API keys in environment variables (from `config.py`), you can migrate them:

1. Keep environment variables as fallback
2. Add UI to import from environment variables
3. Eventually deprecate environment variable approach
4. Or use environment variables for system-wide defaults

## Troubleshooting

### "ENCRYPTION_KEY environment variable is not set"
- Generate a new key and add to `.env`
- Make sure `.env` is loaded by the application

### "Failed to decrypt data"
- Encryption key may have changed
- Data may be corrupted
- Re-enter API keys through the UI

### "Provider with name 'X' already exists"
- Provider names must be unique
- Use PUT to update existing provider
- Or choose a different name for custom provider

## Future Enhancements

- Key rotation mechanism
- Multiple API keys per provider (with rotation)
- API key validation/testing endpoint
- Usage tracking per API key
- Rate limiting per provider
- Multi-tenancy support (per-user API keys)
- Integration with secret management services (AWS Secrets Manager, HashiCorp Vault)
