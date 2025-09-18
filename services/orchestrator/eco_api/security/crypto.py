from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

NONCE_LENGTH = 12
KEY_LENGTH = 32
SALT_LENGTH = 16


class EncryptionError(Exception):
    """Raised when encryption or decryption fails."""


@dataclass(frozen=True)
class WorkspaceCipher:
    key: bytes

    def encrypt_bytes(self, data: bytes) -> bytes:
        nonce = os.urandom(NONCE_LENGTH)
        aesgcm = AESGCM(self.key)
        ciphertext = aesgcm.encrypt(nonce, data, associated_data=None)
        return nonce + ciphertext

    def decrypt_bytes(self, payload: bytes) -> bytes:
        if len(payload) <= NONCE_LENGTH:
            raise EncryptionError("Encrypted payload is too short")
        nonce = payload[:NONCE_LENGTH]
        ciphertext = payload[NONCE_LENGTH:]
        aesgcm = AESGCM(self.key)
        return aesgcm.decrypt(nonce, ciphertext, associated_data=None)

    def encrypt_file(self, source: Path, target: Path) -> None:
        data = source.read_bytes()
        encrypted = self.encrypt_bytes(data)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(encrypted)

    def decrypt_file(self, source: Path, target: Path) -> None:
        data = source.read_bytes()
        decrypted = self.decrypt_bytes(data)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(decrypted)


def generate_salt() -> bytes:
    return os.urandom(SALT_LENGTH)


def derive_key(passphrase: str, salt: bytes) -> bytes:
    kdf = Scrypt(
        salt=salt,
        length=KEY_LENGTH,
        n=2**14,
        r=8,
        p=1,
    )
    return kdf.derive(passphrase.encode("utf-8"))


def build_cipher(passphrase: str, salt: bytes) -> WorkspaceCipher:
    key = derive_key(passphrase, salt)
    return WorkspaceCipher(key=key)
