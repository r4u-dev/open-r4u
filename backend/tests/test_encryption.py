"""Tests for encryption service."""

import pytest
from cryptography.fernet import Fernet

from app.services.encryption import EncryptionService


def test_encrypt_decrypt():
    """Test basic encryption and decryption."""
    # Create a test encryption key
    test_key = Fernet.generate_key().decode()

    # Mock the settings
    class MockSettings:
        encryption_key = test_key

    # Replace get_settings temporarily
    import app.services.encryption as enc_module

    original_get_settings = enc_module.get_settings
    enc_module.get_settings = lambda: MockSettings()

    try:
        service = EncryptionService()

        plaintext = "my-secret-api-key-12345"
        encrypted = service.encrypt(plaintext)

        # Encrypted text should be different from plaintext
        assert encrypted != plaintext
        assert len(encrypted) > 0

        # Decrypt should return original
        decrypted = service.decrypt(encrypted)
        assert decrypted == plaintext
    finally:
        enc_module.get_settings = original_get_settings


def test_encrypt_empty_string():
    """Test encrypting empty string."""
    test_key = Fernet.generate_key().decode()

    class MockSettings:
        encryption_key = test_key

    import app.services.encryption as enc_module

    original_get_settings = enc_module.get_settings
    enc_module.get_settings = lambda: MockSettings()

    try:
        service = EncryptionService()

        encrypted = service.encrypt("")
        assert encrypted == ""

        decrypted = service.decrypt("")
        assert decrypted == ""
    finally:
        enc_module.get_settings = original_get_settings


def test_encryption_service_requires_key():
    """Test that EncryptionService raises error without encryption key."""

    class MockSettings:
        encryption_key = None

    import app.services.encryption as enc_module

    original_get_settings = enc_module.get_settings
    enc_module.get_settings = lambda: MockSettings()

    try:
        with pytest.raises(ValueError, match="ENCRYPTION_KEY"):
            EncryptionService()
    finally:
        enc_module.get_settings = original_get_settings


def test_decrypt_invalid_data():
    """Test decrypting invalid data raises ValueError."""
    test_key = Fernet.generate_key().decode()

    class MockSettings:
        encryption_key = test_key

    import app.services.encryption as enc_module

    original_get_settings = enc_module.get_settings
    enc_module.get_settings = lambda: MockSettings()

    try:
        service = EncryptionService()

        with pytest.raises(ValueError, match="Failed to decrypt"):
            service.decrypt("invalid-encrypted-data")
    finally:
        enc_module.get_settings = original_get_settings


def test_decrypt_with_wrong_key():
    """Test that data encrypted with one key cannot be decrypted with another."""
    key1 = Fernet.generate_key().decode()
    key2 = Fernet.generate_key().decode()

    class MockSettings1:
        encryption_key = key1

    class MockSettings2:
        encryption_key = key2

    import app.services.encryption as enc_module

    original_get_settings = enc_module.get_settings

    try:
        # Encrypt with key1
        enc_module.get_settings = lambda: MockSettings1()
        service1 = EncryptionService()
        encrypted = service1.encrypt("secret")

        # Try to decrypt with key2
        enc_module.get_settings = lambda: MockSettings2()
        service2 = EncryptionService()

        with pytest.raises(ValueError, match="Failed to decrypt"):
            service2.decrypt(encrypted)
    finally:
        enc_module.get_settings = original_get_settings
