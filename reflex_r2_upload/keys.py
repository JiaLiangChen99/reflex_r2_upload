"""Object key helpers (path prefix, safe names, collision avoidance)."""

from __future__ import annotations

import re
from pathlib import Path

from reflex_r2_upload.storage import object_exists


def safe_filename(filename: str) -> str:
    name = Path(filename).name.strip()
    name = re.sub(r"[^\w.\- ()\u4e00-\u9fff]", "_", name)
    return name or "upload.bin"


def normalize_prefix(key_prefix: str) -> str:
    prefix = key_prefix.strip().strip("/")
    if not prefix:
        raise ValueError("key_prefix 不能为空")
    if ".." in prefix.split("/"):
        raise ValueError("key_prefix 不能包含 ..")
    return prefix


def is_allowed_extension(filename: str, allowed: list[str] | None) -> bool:
    if not allowed:
        return True
    suffix = Path(filename).suffix.lower()
    normalized = {ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in allowed}
    return suffix in normalized


def allocate_storage_path(
    key_prefix: str,
    filename: str,
    *,
    allowed_extensions: list[str] | None = None,
) -> str:
    prefix = normalize_prefix(key_prefix)
    safe_name = safe_filename(filename)
    if not is_allowed_extension(safe_name, allowed_extensions):
        allowed_text = ", ".join(allowed_extensions or [])
        raise ValueError(f"不允许的文件类型：{safe_name}（允许：{allowed_text}）")
    base = f"{prefix}/{safe_name}"
    return unique_storage_key(base)


def validate_storage_path(key_prefix: str, storage_path: str) -> str:
    prefix = normalize_prefix(key_prefix)
    key = storage_path.lstrip("/")
    expected = f"{prefix}/"
    if not key.startswith(expected):
        raise ValueError("storagePath 与 keyPrefix 不匹配")
    return key


def unique_storage_key(base_key: str) -> str:
    key = base_key.lstrip("/")
    if not object_exists(key):
        return key

    path = Path(key)
    parent = path.parent
    stem = path.stem
    suffix = path.suffix
    index = 2
    while True:
        candidate_name = f"{stem}_{index}{suffix}"
        if str(parent) not in {".", ""}:
            candidate = str(parent / candidate_name).replace("\\", "/")
        else:
            candidate = candidate_name
        if not object_exists(candidate):
            return candidate
        index += 1
