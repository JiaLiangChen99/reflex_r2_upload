"""Content-Type validation for presigned uploads."""

from __future__ import annotations

from pathlib import Path

from reflex_r2_upload.storage import DEFAULT_CONTENT_TYPE

# Types that are unsafe to serve from a public CDN without strict headers.
BLOCKED_CONTENT_TYPES = frozenset(
    {
        "text/html",
        "application/xhtml+xml",
        "image/svg+xml",
        "text/javascript",
        "application/javascript",
        "application/ecmascript",
        "text/css",
    }
)

# When an extension whitelist is active, only these types are accepted per suffix.
EXTENSION_CONTENT_TYPES: dict[str, frozenset[str]] = {
    ".glb": frozenset({"model/gltf-binary", "application/octet-stream"}),
    ".gltf": frozenset({"model/gltf+json", "application/octet-stream"}),
    ".png": frozenset({"image/png"}),
    ".jpg": frozenset({"image/jpeg"}),
    ".jpeg": frozenset({"image/jpeg"}),
    ".webp": frozenset({"image/webp"}),
    ".gif": frozenset({"image/gif"}),
    ".pdf": frozenset({"application/pdf"}),
    ".txt": frozenset({"text/plain", "application/octet-stream"}),
    ".json": frozenset({"application/json", "text/plain", "application/octet-stream"}),
    ".zip": frozenset({"application/zip", "application/octet-stream"}),
}


def normalize_content_type(value: str | None) -> str:
    text = str(value or DEFAULT_CONTENT_TYPE).strip().lower()
    return text or DEFAULT_CONTENT_TYPE


def validate_content_type(content_type: str) -> str | None:
    """Return an error message for blocked types, else ``None``."""
    normalized = normalize_content_type(content_type)
    if normalized in BLOCKED_CONTENT_TYPES:
        return f"不允许的 Content-Type：{normalized}"
    return None


def validate_content_type_for_filename(
    content_type: str,
    filename: str,
    allowed_extensions: list[str] | None,
) -> str | None:
    """Ensure ``content_type`` matches the filename suffix when extensions are restricted."""
    blocked = validate_content_type(content_type)
    if blocked:
        return blocked
    if not allowed_extensions:
        return None

    suffix = Path(filename).suffix.lower()
    if not suffix:
        return "缺少文件扩展名"

    normalized_allowed = {
        ext.lower() if ext.startswith(".") else f".{ext.lower()}"
        for ext in allowed_extensions
    }
    if suffix not in normalized_allowed:
        return f"不允许的文件类型：{suffix}"

    allowed_types = EXTENSION_CONTENT_TYPES.get(suffix)
    if allowed_types is None:
        return None

    normalized_type = normalize_content_type(content_type)
    if normalized_type not in allowed_types:
        allowed_text = ", ".join(sorted(allowed_types))
        return f"Content-Type 与扩展名不匹配（允许：{allowed_text}）"
    return None


def resolve_presign_content_type(
    client_content_type: str | None,
    token_content_type: str | None,
    *,
    require_upload_token: bool,
) -> str:
    """Pick the Content-Type for presign (token wins when upload auth is enabled)."""
    if token_content_type:
        return normalize_content_type(token_content_type)
    if require_upload_token:
        return normalize_content_type(DEFAULT_CONTENT_TYPE)
    return normalize_content_type(client_content_type)
