"""Tests for demo auth and presign_guard."""

from __future__ import annotations

from starlette.requests import Request

from reflex_r2_demo.demo_auth import (
    DEMO_SESSION_COOKIE,
    demo_presign_guard,
    issue_session_token,
    is_open_demo_prefix,
    user_id_from_request,
)


def _request_with_cookie(token: str | None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if token is not None:
        headers.append(
            (b"cookie", f"{DEMO_SESSION_COOKIE}={token}".encode("latin-1"))
        )
    return Request({"type": "http", "headers": headers, "method": "POST", "path": "/"})


def test_is_open_demo_prefix():
    assert is_open_demo_prefix("demo/basic/uploads")
    assert is_open_demo_prefix("demo/")
    assert not is_open_demo_prefix("uploads/alice")


def test_demo_presign_guard_open_prefix_without_cookie():
    request = _request_with_cookie(None)
    assert demo_presign_guard(request, {"keyPrefix": "demo/basic/uploads"})


def test_demo_presign_guard_user_prefix_requires_login(monkeypatch):
    monkeypatch.setenv("REFLEX_R2_DEMO_SESSION_SECRET", "test-secret")
    request = _request_with_cookie(None)
    assert not demo_presign_guard(request, {"keyPrefix": "uploads/alice"})

    token = issue_session_token("alice")
    authed = _request_with_cookie(token)
    assert demo_presign_guard(authed, {"keyPrefix": "uploads/alice"})
    assert not demo_presign_guard(authed, {"keyPrefix": "uploads/bob"})


def test_user_id_from_request(monkeypatch):
    monkeypatch.setenv("REFLEX_R2_DEMO_SESSION_SECRET", "test-secret")
    token = issue_session_token("bob")
    request = _request_with_cookie(token)
    assert user_id_from_request(request) == "bob"
