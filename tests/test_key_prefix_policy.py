"""Tests for keyPrefix allowlist and user-bound guards."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from starlette.requests import Request
from starlette.testclient import TestClient

import reflex_r2_upload.auth as auth
from reflex_r2_upload.auth import (
    issue_upload_token,
    make_allowed_key_prefixes_guard,
    make_user_key_prefix_guard,
    user_key_prefix,
)
from reflex_r2_upload.config import configure_allowed_key_prefixes, configure_upload_auth
from reflex_r2_upload.routes import create_upload_api


@pytest.fixture(autouse=True)
def reset_state():
    configure_upload_auth(require_upload_token=None, require_bridge_signature=None)
    configure_allowed_key_prefixes(None)
    auth.set_presign_guard(None)
    yield
    configure_upload_auth(require_upload_token=None, require_bridge_signature=None)
    configure_allowed_key_prefixes(None)
    auth.set_presign_guard(None)


def test_user_key_prefix_helper():
    assert user_key_prefix("u-123") == "uploads/u-123"


def test_make_user_key_prefix_guard():
    guard = make_user_key_prefix_guard(lambda _request: "u-123")
    request = Request({"type": "http", "headers": [], "method": "POST", "path": "/"})
    assert guard(request, {"keyPrefix": "uploads/u-123"}) is True
    assert guard(request, {"keyPrefix": "uploads/other"}) is False


def test_allowed_key_prefixes_rejects_unknown_prefix(monkeypatch):
    monkeypatch.setenv("REFLEX_R2_UPLOAD_SECRET", "unit-test-secret")
    monkeypatch.setenv("R2_ACCOUNT_ID", "acct")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("R2_BUCKET_NAME", "bucket")
    configure_allowed_key_prefixes(["demo/uploads"])
    token = issue_upload_token("demo/uploads")
    client = TestClient(create_upload_api())

    with patch(
        "reflex_r2_upload.routes.allocate_storage_path",
        lambda *_a, **_k: "demo/uploads/a.glb",
    ), patch(
        "reflex_r2_upload.routes.create_presigned_put_url",
        lambda *_a, **_k: "https://example/upload",
    ):
        ok = client.post(
            "/_reflex_r2_upload/presign",
            json={
                "keyPrefix": "demo/uploads",
                "filename": "a.glb",
                "fileSizeBytes": 1,
                "uploadToken": token,
            },
        )
        blocked = client.post(
            "/_reflex_r2_upload/presign",
            json={
                "keyPrefix": "demo/other-user",
                "filename": "a.glb",
                "fileSizeBytes": 1,
                "uploadToken": issue_upload_token("demo/other-user"),
            },
        )

    assert ok.status_code == 200
    assert blocked.status_code == 401
    assert "keyPrefix" in blocked.json()["detail"]


def test_upload_token_blocks_cross_prefix_without_allowlist(monkeypatch):
    monkeypatch.setenv("REFLEX_R2_UPLOAD_SECRET", "unit-test-secret")
    monkeypatch.setenv("R2_ACCOUNT_ID", "acct")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("R2_BUCKET_NAME", "bucket")
    token_for_a = issue_upload_token("demo/a")
    client = TestClient(create_upload_api())

    with patch(
        "reflex_r2_upload.routes.allocate_storage_path",
        lambda *_a, **_k: "demo/b/file.glb",
    ), patch(
        "reflex_r2_upload.routes.create_presigned_put_url",
        lambda *_a, **_k: "https://example/upload",
    ):
        response = client.post(
            "/_reflex_r2_upload/presign",
            json={
                "keyPrefix": "demo/b",
                "filename": "file.glb",
                "fileSizeBytes": 1,
                "uploadToken": token_for_a,
            },
        )

    assert response.status_code == 401
