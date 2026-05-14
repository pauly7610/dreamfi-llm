"""Encrypted connector secret helpers."""
from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken

from dreamfi.config import get_settings
from dreamfi.connectors import ConnectorSpec
from dreamfi.db.models import ConnectorSetting


class ConnectorSecretError(ValueError):
    """Raised when a connector secret cannot be stored or read safely."""


@dataclass(frozen=True)
class EncryptedSecret:
    ciphertext: str
    key_id: str


def _raw_secret_key() -> str:
    return get_settings().dreamfi_connector_secret_key.strip()


def connector_secret_key_configured() -> bool:
    return bool(_raw_secret_key())


def _fernet_key() -> bytes:
    value = _raw_secret_key()
    if not value:
        raise ConnectorSecretError("DREAMFI_CONNECTOR_SECRET_KEY is required to store connector API keys")
    try:
        Fernet(value.encode("utf-8"))
        return value.encode("utf-8")
    except ValueError:
        digest = hashlib.sha256(value.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)


def connector_secret_key_id() -> str:
    return hashlib.sha256(_fernet_key()).hexdigest()[:16]


def encrypt_connector_secret(value: str) -> EncryptedSecret:
    stripped = value.strip()
    token = Fernet(_fernet_key()).encrypt(stripped.encode("utf-8")).decode("utf-8")
    return EncryptedSecret(ciphertext=token, key_id=connector_secret_key_id())


def decrypt_connector_secret(ciphertext: str) -> str:
    try:
        return Fernet(_fernet_key()).decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ConnectorSecretError("connector secret could not be decrypted with the configured key") from exc


def connector_secret_env_names(connector: ConnectorSpec) -> tuple[str, ...]:
    token = connector.connector_id.upper().replace("-", "_")
    return (
        f"DREAMFI_CONNECTOR_SECRET_{token}",
        f"DREAMFI_{token}_API_KEY",
    )


def resolve_connector_secret(connector: ConnectorSpec, setting: ConnectorSetting | None) -> str | None:
    if setting is not None and setting.secret_ciphertext:
        return decrypt_connector_secret(setting.secret_ciphertext)
    for env_name in connector_secret_env_names(connector):
        value = os.getenv(env_name)
        if value and value.strip():
            return value.strip()
    return None


def connector_secret_storage(setting: ConnectorSetting | None, connector: ConnectorSpec) -> str:
    if setting is not None and setting.secret_ciphertext:
        return "encrypted"
    if any(os.getenv(name) for name in connector_secret_env_names(connector)):
        return "env"
    if setting is not None and setting.secret_sha256:
        return "metadata_only"
    return "missing"
