"""Upload size and GET expiry limit helpers."""

from __future__ import annotations

from typing import Any

from reflex_r2_upload.config import max_upload_bytes, resolve_get_expires


def parse_file_size_bytes(data: dict[str, Any]) -> tuple[int | None, str | None]:
    """Parse ``fileSizeBytes`` from a JSON body."""
    raw = data.get("fileSizeBytes")
    if raw is None:
        return None, "缺少字段：fileSizeBytes"
    try:
        size = int(raw)
    except (TypeError, ValueError):
        return None, "fileSizeBytes 无效"
    if size < 1:
        return None, "fileSizeBytes 无效"
    return size, None


def validate_file_size_bytes(size: int) -> str | None:
    """Return an error message when ``size`` exceeds the configured upload cap."""
    limit = max_upload_bytes()
    if limit <= 0:
        return None
    if size > limit:
        return f"文件大小超过上限（{limit} 字节）"
    return None


def clamp_get_expires(expires_in: int | None) -> int:
    """Clamp a requested GET TTL to configured bounds."""
    return resolve_get_expires(expires_in)
