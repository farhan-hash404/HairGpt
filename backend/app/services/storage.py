from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path

from app.core.config import settings

# Application-level envelope encryption for stored images. Uses cryptography's
# Fernet when available; otherwise a clearly-labeled XOR-obfuscation dev fallback
# (NOT secure — production must install `cryptography` and set IMAGE_ENCRYPTION_KEY).
try:  # pragma: no cover
    from cryptography.fernet import Fernet

    _HAS_FERNET = True
except Exception:  # pragma: no cover
    _HAS_FERNET = False


def _derive_key() -> bytes:
    raw = settings.image_encryption_key or settings.secret_key
    digest = hashlib.sha256(raw.encode()).digest()
    return base64.urlsafe_b64encode(digest)


class _Cipher:
    def __init__(self):
        self._key = _derive_key()
        self._fernet = Fernet(self._key) if _HAS_FERNET else None

    def encrypt(self, data: bytes) -> bytes:
        if self._fernet:
            return self._fernet.encrypt(data)
        # Dev fallback (insecure): XOR with repeated key. Prefixed so we know the mode.
        k = hashlib.sha256(self._key).digest()
        return b"XORDEV:" + bytes(b ^ k[i % len(k)] for i, b in enumerate(data))

    def decrypt(self, blob: bytes) -> bytes:
        if blob.startswith(b"XORDEV:"):
            k = hashlib.sha256(self._key).digest()
            data = blob[len(b"XORDEV:") :]
            return bytes(b ^ k[i % len(k)] for i, b in enumerate(data))
        if self._fernet:
            return self._fernet.decrypt(blob)
        raise RuntimeError("Cannot decrypt: cryptography not installed")


_cipher = _Cipher()


class StorageBackend:
    def put(self, key: str, data: bytes) -> None: ...
    def get(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...


class LocalStorage(StorageBackend):
    """Encrypted-at-rest local disk storage (dev default)."""

    def __init__(self, root: str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        safe = key.replace("..", "_").lstrip("/")
        p = self.root / safe
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def put(self, key: str, data: bytes) -> None:
        self._path(key).write_bytes(_cipher.encrypt(data))

    def get(self, key: str) -> bytes:
        return _cipher.decrypt(self._path(key).read_bytes())

    def delete(self, key: str) -> None:
        p = self._path(key)
        if p.exists():
            p.unlink()


class S3Storage(StorageBackend):  # pragma: no cover - requires boto3 + bucket
    """S3-compatible storage with server-side + app-level encryption."""

    def __init__(self):
        import boto3

        self._s3 = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
        )
        self._bucket = settings.s3_bucket

    def put(self, key: str, data: bytes) -> None:
        self._s3.put_object(Bucket=self._bucket, Key=key, Body=_cipher.encrypt(data), ServerSideEncryption="AES256")

    def get(self, key: str) -> bytes:
        obj = self._s3.get_object(Bucket=self._bucket, Key=key)
        return _cipher.decrypt(obj["Body"].read())

    def delete(self, key: str) -> None:
        self._s3.delete_object(Bucket=self._bucket, Key=key)


def build_storage() -> StorageBackend:
    if settings.storage_backend == "s3":
        try:
            return S3Storage()
        except Exception:
            pass
    return LocalStorage(settings.storage_local_dir)


_backend: StorageBackend | None = None


def get_storage() -> StorageBackend:
    """Resolve the storage backend lazily so configuration is honored at call
    time rather than frozen at import time (which also makes it testable)."""
    global _backend
    if _backend is None:
        _backend = build_storage()
    return _backend


def reset_storage() -> None:
    """Drop the cached backend so the next call re-reads configuration."""
    global _backend
    _backend = None


def make_storage_key(user_id, session_id, view: str) -> str:
    ext = "bin"
    return f"users/{user_id}/scans/{session_id}/{view}.{ext}"


class _StorageProxy(StorageBackend):
    """Import-safe handle: `from app.services.storage import storage` stays valid
    while the underlying backend is resolved (and can be reset) at call time."""

    def put(self, key: str, data: bytes) -> None:
        get_storage().put(key, data)

    def get(self, key: str) -> bytes:
        return get_storage().get(key)

    def delete(self, key: str) -> None:
        get_storage().delete(key)


storage = _StorageProxy()
