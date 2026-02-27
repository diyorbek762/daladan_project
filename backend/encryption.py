"""
Daladan Platform — Application-Level PII Encryption
Uses Fernet symmetric encryption from the cryptography library.
Encryption key is loaded from FERNET_KEY environment variable — never hardcoded.
"""
import logging
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from backend.config import get_settings

logger = logging.getLogger("daladan.encryption")


@lru_cache()
def _get_fernet() -> Fernet:
    """
    Get a cached Fernet cipher instance.
    Key is loaded from the FERNET_KEY environment variable.

    Raises RuntimeError if the key is not configured.
    """
    settings = get_settings()
    key = settings.FERNET_KEY
    if not key:
        raise RuntimeError(
            "FERNET_KEY environment variable is not set. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(key.encode("utf-8"))


def encrypt_pii(plaintext: str) -> str:
    """
    Encrypt a PII string (e.g., phone number) using Fernet.
    Returns a base64-encoded ciphertext string safe for DB storage.

    Args:
        plaintext: The sensitive data to encrypt

    Returns:
        Encrypted string (URL-safe base64)
    """
    if not plaintext:
        return plaintext
    cipher = _get_fernet()
    encrypted = cipher.encrypt(plaintext.encode("utf-8"))
    return encrypted.decode("utf-8")


def decrypt_pii(ciphertext: str) -> str:
    """
    Decrypt a Fernet-encrypted PII string back to plaintext.

    Args:
        ciphertext: The encrypted data from the database

    Returns:
        Decrypted plaintext string

    Raises:
        ValueError: If decryption fails (tampered or wrong key)
    """
    if not ciphertext:
        return ciphertext
    try:
        cipher = _get_fernet()
        decrypted = cipher.decrypt(ciphertext.encode("utf-8"))
        return decrypted.decode("utf-8")
    except InvalidToken:
        logger.error("Failed to decrypt PII — possible key mismatch or data tampering")
        raise ValueError("Decryption failed — data may be corrupted or key has changed")


def generate_key() -> str:
    """Generate a new Fernet key. Utility for initial setup."""
    return Fernet.generate_key().decode("utf-8")
