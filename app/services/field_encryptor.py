"""
Artha AI: AES-256-GCM Encryption for PCI-DSS Compliance.
Encrypts sensitive financial fields (card PAN, account numbers) at the
application layer — defense-in-depth beyond database encryption.

WHY AES-256-GCM: It provides both confidentiality (AES) and integrity
(GCM's GHASH authentication tag), so tampered ciphertext is detected
before decryption. This is the standard used by Stripe and Square for
PCI-DSS Level 1 compliance.
"""
import base64
import os
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
    logger.warning("cryptography package not installed. Run: pip install cryptography")


class FinancialFieldEncryptor:
    """
    Application-layer AES-256-GCM encryptor for PCI-DSS sensitive fields.

    Invariants:
    1. Every encryption call generates a fresh cryptographic nonce (96-bit).
    2. The authentication tag (128-bit) is verified on every decryption.
    3. The master key is NEVER logged or serialized to disk.
    """

    NONCE_SIZE = 12  # 96 bits — GCM standard

    def __init__(self, master_key_b64: str | None = None):
        raw_key = master_key_b64 or os.environ.get("ARTHA_MASTER_KEY_B64")
        if not raw_key:
            raise RuntimeError(
                "ARTHA_MASTER_KEY_B64 environment variable not set. "
                "Generate with: python3 -c \"import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())\""
            )
        self._key = base64.b64decode(raw_key)
        if len(self._key) != 32:
            raise ValueError("Master key must be exactly 32 bytes (AES-256).")
        self._aesgcm = AESGCM(self._key)

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypts a sensitive string field.
        Returns a base64-encoded string: nonce (12B) || ciphertext+tag.
        """
        if not HAS_CRYPTO:
            raise RuntimeError("cryptography package not installed.")

        nonce = os.urandom(self.NONCE_SIZE)
        ciphertext = self._aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        payload = nonce + ciphertext
        return base64.b64encode(payload).decode("utf-8")

    def decrypt(self, encrypted_b64: str) -> str:
        """
        Decrypts and authenticates an encrypted field.
        Raises cryptography.exceptions.InvalidTag if tampered.
        """
        if not HAS_CRYPTO:
            raise RuntimeError("cryptography package not installed.")

        payload = base64.b64decode(encrypted_b64)
        nonce = payload[:self.NONCE_SIZE]
        ciphertext = payload[self.NONCE_SIZE:]
        plaintext = self._aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
