"""Bridge payload schema (version 1) shared by routes and browser runtime."""

from __future__ import annotations

from reflex_r2_upload.storage import public_url_or_none

BRIDGE_PAYLOAD_VERSION = 1


class UploadErrorCode:
    """Machine-readable bridge error codes."""

    R2_NOT_CONFIGURED = "R2_NOT_CONFIGURED"
    CONFIG_FETCH_FAILED = "CONFIG_FETCH_FAILED"
    UPLOAD_FAILED = "UPLOAD_FAILED"
    INVALID_PAYLOAD = "INVALID_PAYLOAD"
    EXTENSION_NOT_ALLOWED = "EXTENSION_NOT_ALLOWED"
    STORAGE_PUT_FAILED = "STORAGE_PUT_FAILED"
    CORS_BLOCKED = "CORS_BLOCKED"


def file_bridge_payload(
    *,
    key_prefix: str,
    storage_path: str,
    original_filename: str,
    file_size_bytes: int,
    content_type: str,
) -> dict:
    """Build a version-1 per-file success object for the Reflex bridge."""
    return {
        "version": BRIDGE_PAYLOAD_VERSION,
        "error": False,
        "ok": True,
        "keyPrefix": key_prefix,
        "storagePath": storage_path,
        "originalFilename": original_filename,
        "fileSizeBytes": file_size_bytes,
        "contentType": content_type,
        "publicUrl": public_url_or_none(storage_path),
    }


def success_bridge_payload(
    *,
    key_prefix: str,
    files: list[dict],
) -> dict:
    """Build top-level success bridge JSON (single file flat, multi-file nested)."""
    if len(files) == 1:
        return files[0]
    return {
        "version": BRIDGE_PAYLOAD_VERSION,
        "error": False,
        "keyPrefix": key_prefix,
        "files": files,
    }


def error_bridge_payload(
    message: str,
    *,
    code: str | None = None,
) -> dict:
    """Build version-1 error bridge JSON."""
    body: dict = {
        "version": BRIDGE_PAYLOAD_VERSION,
        "error": True,
        "message": message,
    }
    if code:
        body["code"] = code
    return body
