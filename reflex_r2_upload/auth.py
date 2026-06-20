"""Upload authorization tokens and optional request guards."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from starlette.requests import Request

from reflex_r2_upload.config import (
    bucket_name,
    is_key_prefix_allowed,
    require_upload_token,
    secret_access_key,
    upload_token_ttl,
    upload_token_secret,
)
from reflex_r2_upload.keys import normalize_prefix

PresignGuard = Callable[
    [Request, dict[str, Any]],
    bool | Awaitable[bool],
]

_runtime_presign_guard: PresignGuard | None = None


def set_presign_guard(guard: PresignGuard | None) -> None:
    """Register a global guard for presign, complete, and signed-read (``None`` clears)."""
    global _runtime_presign_guard
    _runtime_presign_guard = guard


def get_presign_guard() -> PresignGuard | None:
    return _runtime_presign_guard


def _secret_bytes() -> bytes:
    explicit = upload_token_secret()
    if explicit:
        return explicit.encode("utf-8")

    secret = secret_access_key()
    bucket = bucket_name()
    if secret and bucket:
        material = f"{secret}:{bucket}".encode("utf-8")
        return hmac.new(b"reflex-r2-upload-v1", material, hashlib.sha256).digest()

    raise RuntimeError(
        "无法签发 upload token：请设置 REFLEX_R2_UPLOAD_SECRET，"
        "或配置完整的 R2 凭证（将自动派生上传密钥）。"
    )


def _normalize_extension_list(allowed: Sequence[str] | None) -> list[str] | None:
    if allowed is None:
        return None
    normalized: list[str] = []
    for ext in allowed:
        text = str(ext).strip().lower()
        if not text:
            continue
        normalized.append(text if text.startswith(".") else f".{text}")
    return normalized


def _decode_upload_token(token: str) -> dict[str, Any] | None:
    if not token or not isinstance(token, str):
        return None

    try:
        payload_b64, signature = token.rsplit(".", 1)
        expected = hmac.new(
            _secret_bytes(),
            payload_b64.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return None

        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
        if int(payload["exp"]) < int(time.time()):
            return None
        return payload
    except (ValueError, TypeError, json.JSONDecodeError, KeyError):
        return None


def issue_upload_token(
    key_prefix: str,
    *,
    ttl: int | None = None,
    allowed_extensions: Sequence[str] | None = None,
    content_type: str | None = None,
) -> str:
    """Issue an HMAC upload token bound to ``key_prefix`` and optional upload policy."""
    prefix = normalize_prefix(key_prefix)
    expires = int(time.time()) + (ttl if ttl is not None else upload_token_ttl())
    payload: dict[str, Any] = {"p": prefix, "exp": expires}
    normalized_ext = _normalize_extension_list(allowed_extensions)
    if normalized_ext is not None:
        payload["e"] = normalized_ext
    if content_type and str(content_type).strip():
        payload["c"] = str(content_type).strip()
    payload_b64 = (
        base64.urlsafe_b64encode(
            json.dumps(payload, separators=(",", ":")).encode("utf-8")
        )
        .decode("ascii")
        .rstrip("=")
    )
    signature = hmac.new(
        _secret_bytes(),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload_b64}.{signature}"


def verify_upload_token(token: str, key_prefix: str) -> bool:
    """Return whether ``token`` is valid for ``key_prefix``."""
    payload = _decode_upload_token(token)
    if payload is None:
        return False

    try:
        prefix = normalize_prefix(key_prefix)
    except ValueError:
        return False
    return str(payload["p"]) == prefix


def upload_token_policy(
    token: str,
    key_prefix: str,
) -> tuple[list[str] | None, str | None]:
    """Return ``(allowed_extensions, content_type)`` encoded in a verified token.

    ``allowed_extensions`` is ``None`` when the token does not restrict extensions.
    """
    payload = _decode_upload_token(token)
    if payload is None:
        return None, None

    try:
        if normalize_prefix(key_prefix) != str(payload["p"]):
            return None, None
    except ValueError:
        return None, None

    extensions: list[str] | None = None
    if "e" in payload:
        raw = payload["e"]
        extensions = list(raw) if isinstance(raw, list) else []

    bound_content_type = None
    if isinstance(payload.get("c"), str) and payload["c"].strip():
        bound_content_type = payload["c"].strip()
    return extensions, bound_content_type


async def authorize_storage_request(
    request: Request,
    data: dict[str, Any],
    key_prefix: str,
    *,
    require_token: bool | None = None,
    presign_guard: PresignGuard | None = None,
    unauthorized_message: str = "未授权的请求",
) -> str | None:
    """Return an error message when unauthorized, else ``None``."""
    try:
        normalized_prefix = normalize_prefix(key_prefix)
    except ValueError as error:
        return str(error)

    if not is_key_prefix_allowed(normalized_prefix):
        return "不允许的 keyPrefix"

    guard = presign_guard if presign_guard is not None else get_presign_guard()
    if guard is not None:
        allowed = guard(request, data)
        if hasattr(allowed, "__await__"):
            allowed = await allowed  # type: ignore[misc]
        if allowed:
            return None

    must_have_token = (
        require_upload_token() if require_token is None else require_token
    )
    if not must_have_token and guard is None:
        return None

    token = data.get("uploadToken")
    if isinstance(token, str) and verify_upload_token(token, key_prefix):
        return None

    return unauthorized_message


async def authorize_upload_request(
    request: Request,
    data: dict[str, Any],
    key_prefix: str,
    *,
    require_token: bool | None = None,
    presign_guard: PresignGuard | None = None,
) -> str | None:
    """Authorize presign/complete; alias of :func:`authorize_storage_request`."""
    return await authorize_storage_request(
        request,
        data,
        key_prefix,
        require_token=require_token,
        presign_guard=presign_guard,
        unauthorized_message="未授权的上传请求",
    )


def upload_auth_enabled() -> bool:
    """Whether storage routes require authorization."""
    if get_presign_guard() is not None:
        return True
    if require_upload_token():
        return True
    return False


def _bridge_signing_bytes(
    *,
    key_prefix: str,
    storage_path: str,
    original_filename: str,
    file_size_bytes: int,
    content_type: str,
    public_url: str | None,
) -> bytes:
    from reflex_r2_upload.payload import BRIDGE_PAYLOAD_VERSION

    body = {
        "v": BRIDGE_PAYLOAD_VERSION,
        "p": normalize_prefix(key_prefix),
        "s": storage_path.lstrip("/"),
        "f": original_filename,
        "b": int(file_size_bytes),
        "c": content_type,
        "u": public_url or "",
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return b"bridge-v1:" + canonical.encode("utf-8")


def sign_bridge_file_payload(
    *,
    key_prefix: str,
    storage_path: str,
    original_filename: str,
    file_size_bytes: int,
    content_type: str,
    public_url: str | None,
) -> str:
    """Return an HMAC hex digest for a verified bridge file payload."""
    message = _bridge_signing_bytes(
        key_prefix=key_prefix,
        storage_path=storage_path,
        original_filename=original_filename,
        file_size_bytes=file_size_bytes,
        content_type=content_type,
        public_url=public_url,
    )
    return hmac.new(_secret_bytes(), message, hashlib.sha256).hexdigest()


def verify_bridge_file_payload(data: dict[str, Any]) -> bool:
    """Return whether ``data`` carries a valid server ``bridgeSignature``."""
    signature = data.get("bridgeSignature")
    if not isinstance(signature, str) or not signature:
        return False

    try:
        public_raw = data.get("publicUrl")
        expected = sign_bridge_file_payload(
            key_prefix=str(data["keyPrefix"]),
            storage_path=str(data["storagePath"]),
            original_filename=str(data["originalFilename"]),
            file_size_bytes=int(data["fileSizeBytes"]),
            content_type=str(data["contentType"]),
            public_url=public_raw if public_raw else None,
        )
        return hmac.compare_digest(expected, signature)
    except (TypeError, ValueError, KeyError):
        return False


def user_key_prefix(user_id: str, *, template: str = "uploads/{user_id}") -> str:
    """Build a normalized per-user storage prefix for ``upload_zone(key_prefix=...)``."""
    return normalize_prefix(template.format(user_id=user_id))


def make_allowed_key_prefixes_guard(prefixes: Sequence[str]) -> PresignGuard:
    """Return a guard that only allows explicit ``keyPrefix`` values."""

    allowed = frozenset(normalize_prefix(prefix) for prefix in prefixes)

    def guard(_request: Request, data: dict[str, Any]) -> bool:
        try:
            requested = normalize_prefix(str(data.get("keyPrefix", "")))
        except ValueError:
            return False
        return requested in allowed

    return guard


def make_user_key_prefix_guard(
    get_user_id: Callable[[Request], str | None],
    *,
    prefix_template: str = "uploads/{user_id}",
) -> PresignGuard:
    """Return a guard that binds ``keyPrefix`` to the authenticated user."""

    def guard(request: Request, data: dict[str, Any]) -> bool:
        user_id = get_user_id(request)
        if not user_id:
            return False
        expected = user_key_prefix(user_id, template=prefix_template)
        try:
            requested = normalize_prefix(str(data.get("keyPrefix", "")))
        except ValueError:
            return False
        return requested == expected

    return guard
