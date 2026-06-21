"""Demo session auth shared by Reflex State and presign_guard.

Uses a signed cookie so HTTP upload routes can read the same identity as the UI.
Not for production — replace with your real session/JWT logic.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

from starlette.requests import Request

import reflex_r2_upload as r2
from reflex_r2_upload.keys import normalize_prefix

DEMO_SESSION_COOKIE = "reflex_r2_demo_session"
DEMO_USERS = ("alice", "bob")
OPEN_DEMO_PREFIX = "demo/"
SESSION_TTL_SECONDS = 7200


def _session_secret() -> bytes:
    explicit = os.environ.get("REFLEX_R2_DEMO_SESSION_SECRET", "").strip()
    if explicit:
        return explicit.encode("utf-8")
    upload_secret = os.environ.get("REFLEX_R2_UPLOAD_SECRET", "").strip()
    if upload_secret:
        return upload_secret.encode("utf-8")
    return b"reflex-r2-demo-dev-only-change-in-production"


def _encode_payload(payload: dict[str, Any]) -> str:
    payload_b64 = (
        base64.urlsafe_b64encode(
            json.dumps(payload, separators=(",", ":")).encode("utf-8")
        )
        .decode("ascii")
        .rstrip("=")
    )
    signature = hmac.new(
        _session_secret(),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload_b64}.{signature}"


def _decode_token(token: str) -> dict[str, Any] | None:
    if not token or not isinstance(token, str):
        return None
    try:
        payload_b64, signature = token.rsplit(".", 1)
        expected = hmac.new(
            _session_secret(),
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


def issue_session_token(user_id: str, *, ttl: int = SESSION_TTL_SECONDS) -> str:
    """Issue a signed demo session token for ``user_id``."""
    normalized = str(user_id).strip()
    if normalized not in DEMO_USERS:
        raise ValueError(f"未知演示用户：{normalized}")
    payload = {"sub": normalized, "exp": int(time.time()) + ttl}
    return _encode_payload(payload)


def decode_session_token(token: str) -> dict[str, Any] | None:
    """Decode a demo session token, or ``None`` when invalid/expired."""
    return _decode_token(token)


def user_id_from_request(request: Request) -> str | None:
    """Read the logged-in demo user id from the HTTP request cookie."""
    token = request.cookies.get(DEMO_SESSION_COOKIE)
    payload = decode_session_token(token) if token else None
    if payload is None:
        return None
    user_id = str(payload.get("sub", "")).strip()
    return user_id or None


def is_open_demo_prefix(key_prefix: str) -> bool:
    """Return whether ``key_prefix`` is allowed without login (open examples)."""
    try:
        normalized = normalize_prefix(key_prefix)
    except ValueError:
        return False
    return normalized == OPEN_DEMO_PREFIX.rstrip("/") or normalized.startswith(
        OPEN_DEMO_PREFIX
    )


def demo_presign_guard(request: Request, data: dict[str, Any]) -> bool:
    """Allow open ``demo/`` prefixes; bind ``uploads/{user_id}`` to session cookie."""
    try:
        requested = normalize_prefix(str(data.get("keyPrefix", "")))
    except ValueError:
        return False

    if is_open_demo_prefix(requested):
        return True

    user_id = user_id_from_request(request)
    if not user_id:
        return False
    expected = r2.user_key_prefix(user_id, template="uploads/{user_id}")
    return requested == expected
