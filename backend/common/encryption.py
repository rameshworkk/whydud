"""AES-256-GCM encryption helpers for email bodies and sensitive fields."""
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings


def _get_key(key_setting: str = "EMAIL_ENCRYPTION_KEY") -> bytes:
    """Return the raw 32-byte key from hex-encoded settings value."""
    hex_key = getattr(settings, key_setting, "")
    if not hex_key:
        raise ValueError(f"{key_setting} is not configured — cannot encrypt/decrypt.")
    return bytes.fromhex(hex_key)


def encrypt(plaintext: str, key_setting: str = "EMAIL_ENCRYPTION_KEY") -> bytes:
    """Encrypt a UTF-8 string with AES-256-GCM.

    Returns: nonce (12 bytes) || ciphertext+tag
    """
    if not plaintext:
        return b""
    key = _get_key(key_setting)
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return nonce + ct


def decrypt(data: bytes, key_setting: str = "EMAIL_ENCRYPTION_KEY") -> str:
    """Decrypt AES-256-GCM ciphertext produced by encrypt().

    Expects: nonce (12 bytes) || ciphertext+tag
    """
    if not data:
        return ""
    key = _get_key(key_setting)
    nonce = data[:12]
    ct = data[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ct, None).decode("utf-8")
