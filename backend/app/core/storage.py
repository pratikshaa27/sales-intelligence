"""File storage abstraction (spec §2/§24: object storage if required). No OBJECT_STORAGE_*
credentials are configured for local/dev, so this defaults to local disk under UPLOAD_DIR;
swap in an S3-compatible implementation behind the same interface once credentials exist —
callers (product_service, etc.) never touch the filesystem or a bucket client directly.
"""

import re
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import get_settings

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
}
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

# Browsers/OSes disagree on the MIME type for a .csv file (text/csv, application/csv,
# application/vnd.ms-excel are all seen in the wild) so all three are accepted for imports.
ALLOWED_IMPORT_CONTENT_TYPES = {"text/csv", "application/csv", "application/vnd.ms-excel"}
MAX_IMPORT_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


class UnsupportedFileError(Exception):
    pass


# Magic-byte signatures for the binary content types we accept, checked against the file's
# actual bytes rather than trusting the client-supplied Content-Type header alone (spec §20:
# "file upload validation" — a spoofed header must not let arbitrary content through under a
# safe-looking type). Types with no reliable signature (plain text/markdown/CSV) are exempt —
# free-form text has nothing to sniff, and it's never executed or parsed as a binary format.
FILE_SIGNATURES: dict[str, list[bytes]] = {
    "application/pdf": [b"%PDF-"],
    "application/msword": [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],
    # .docx (and .xlsx/.pptx) are zip containers — this confirms "valid zip", not the specific
    # Office subtype, which would need inspecting the archive's internal parts to verify.
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [b"PK\x03\x04"],
}


def validate_file_signature(content_type: str, content: bytes) -> bool:
    """True if `content` starts with a known-good signature for `content_type`, or if that
    type has no reliable signature to check."""
    signatures = FILE_SIGNATURES.get(content_type)
    if not signatures:
        return True
    return any(content.startswith(sig) for sig in signatures)


def sanitize_filename(filename: str) -> str:
    base = Path(filename).name  # strip any directory components
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base)
    return base[:200] or "file"


class FileStorage(ABC):
    @abstractmethod
    async def save(self, *, key: str, content: bytes) -> str:
        """Persist content under `key`, returning the storage key actually used."""

    @abstractmethod
    async def read(self, key: str) -> bytes: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...


class LocalFileStorage(FileStorage):
    def __init__(self, root: str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not str(path).startswith(str(self.root.resolve())):
            raise UnsupportedFileError("Invalid storage key")
        return path

    async def save(self, *, key: str, content: bytes) -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return key

    async def read(self, key: str) -> bytes:
        return self._resolve(key).read_bytes()

    async def delete(self, key: str) -> None:
        path = self._resolve(key)
        if path.exists():
            path.unlink()


def get_file_storage() -> FileStorage:
    settings = get_settings()
    return LocalFileStorage(settings.upload_dir)


def build_storage_key(*, organization_id: uuid.UUID, product_id: uuid.UUID, filename: str) -> str:
    safe_name = sanitize_filename(filename)
    return f"products/{organization_id}/{product_id}/{uuid.uuid4().hex}_{safe_name}"


def build_import_storage_key(*, organization_id: uuid.UUID, filename: str) -> str:
    safe_name = sanitize_filename(filename)
    return f"imports/{organization_id}/{uuid.uuid4().hex}_{safe_name}"
