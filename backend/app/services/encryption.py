"""Encryption service for securely storing API keys."""

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


class EncryptionService:
    """Service for encrypting and decrypting sensitive data like API keys."""

    def __init__(self) -> None:
        """Initialize the encryption service with the master key from settings."""
        settings = get_settings()
        # Get encryption key from environment variable
        # If not set, generate a new one (for development only)
        encryption_key = getattr(settings, "encryption_key", None)

        if not encryption_key:
            msg = (
                "ENCRYPTION_KEY environment variable is not set. "
                "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
            raise ValueError(msg)

        # Ensure the key is in bytes format
        if isinstance(encryption_key, str):
            encryption_key = encryption_key.encode()

        self.fernet = Fernet(encryption_key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string.

        Args:
            plaintext: The plaintext string to encrypt

        Returns:
            The encrypted string (base64 encoded)

        """
        if not plaintext:
            return ""

        encrypted_bytes = self.fernet.encrypt(plaintext.encode())
        return encrypted_bytes.decode()

    def decrypt(self, encrypted: str) -> str:
        """Decrypt an encrypted string.

        Args:
            encrypted: The encrypted string (base64 encoded)

        Returns:
            The decrypted plaintext string

        Raises:
            ValueError: If the encrypted string is invalid or cannot be decrypted

        """
        if not encrypted:
            return ""

        try:
            decrypted_bytes = self.fernet.decrypt(encrypted.encode())
            return decrypted_bytes.decode()
        except InvalidToken as e:
            msg = "Failed to decrypt data. The encryption key may have changed or the data is corrupted."
            raise ValueError(msg) from e


# Singleton instance
_encryption_service: EncryptionService | None = None


def get_encryption_service() -> EncryptionService:
    """Get or create the encryption service singleton.

    Returns:
        The encryption service instance

    """
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service
