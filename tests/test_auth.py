"""Tests for upload authorization tokens."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

import reflex_r2_upload.auth as auth
import reflex_r2_upload.config as config
from reflex_r2_upload.auth import issue_upload_token, verify_upload_token
from reflex_r2_upload.config import configure_r2, configure_upload_auth
from reflex_r2_upload.routes import create_upload_api


@pytest.fixture(autouse=True)
def reset_auth_state():
    configure_r2(None)
    configure_upload_auth(require_upload_token=None, require_bridge_signature=None)
    auth.set_presign_guard(None)
    yield
    configure_r2(None)
    configure_upload_auth(require_upload_token=None, require_bridge_signature=None)
    auth.set_presign_guard(None)


def test_issue_and_verify_upload_token(monkeypatch):
    monkeypatch.setenv("REFLEX_R2_UPLOAD_SECRET", "unit-test-secret")
    token = issue_upload_token("demo/uploads")
    assert verify_upload_token(token, "demo/uploads")
    assert not verify_upload_token(token, "demo/other")
    assert not verify_upload_token("bad.token", "demo/uploads")


def test_presign_rejects_missing_token(monkeypatch):
    monkeypatch.setenv("REFLEX_R2_UPLOAD_SECRET", "unit-test-secret")
    monkeypatch.setenv("R2_ACCOUNT_ID", "acct")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("R2_BUCKET_NAME", "bucket")

    client = TestClient(create_upload_api())
    response = client.post(
        "/_reflex_r2_upload/presign",
        json={
            "keyPrefix": "demo/uploads",
            "filename": "a.glb",
            "fileSizeBytes": 1,
        },
    )

    assert response.status_code == 401
    assert "未授权" in response.json()["detail"]


def test_presign_accepts_valid_token(monkeypatch):
    monkeypatch.setenv("REFLEX_R2_UPLOAD_SECRET", "unit-test-secret")
    monkeypatch.setenv("R2_ACCOUNT_ID", "acct")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("R2_BUCKET_NAME", "bucket")

    token = issue_upload_token("demo/uploads")
    client = TestClient(create_upload_api())

    monkeypatch.setattr(
        "reflex_r2_upload.routes.allocate_storage_path",
        lambda *_a, **_k: "demo/uploads/a.glb",
    )
    monkeypatch.setattr(
        "reflex_r2_upload.routes.create_presigned_put_url",
        lambda *_a, **_k: "https://example/upload",
    )
    response = client.post(
        "/_reflex_r2_upload/presign",
        json={
            "keyPrefix": "demo/uploads",
            "filename": "a.glb",
            "fileSizeBytes": 1,
            "uploadToken": token,
        },
    )

    assert response.status_code == 200
    assert response.json()["uploadUrl"] == "https://example/upload"


def test_presign_guard_allows_without_token(monkeypatch):
    monkeypatch.setenv("REFLEX_R2_UPLOAD_SECRET", "unit-test-secret")
    monkeypatch.setenv("R2_ACCOUNT_ID", "acct")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("R2_BUCKET_NAME", "bucket")

    def allow(_request, _data):
        return True

    client = TestClient(create_upload_api(presign_guard=allow))
    monkeypatch.setattr(
        "reflex_r2_upload.routes.allocate_storage_path",
        lambda *_a, **_k: "demo/uploads/a.glb",
    )
    monkeypatch.setattr(
        "reflex_r2_upload.routes.create_presigned_put_url",
        lambda *_a, **_k: "https://example/upload",
    )
    response = client.post(
        "/_reflex_r2_upload/presign",
        json={
            "keyPrefix": "demo/uploads",
            "filename": "a.glb",
            "fileSizeBytes": 1,
        },
    )

    assert response.status_code == 200


def test_require_upload_token_can_be_disabled(monkeypatch):
    monkeypatch.setenv("R2_ACCOUNT_ID", "acct")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("R2_BUCKET_NAME", "bucket")

    client = TestClient(create_upload_api(require_upload_token=False))
    monkeypatch.setattr(
        "reflex_r2_upload.routes.allocate_storage_path",
        lambda *_a, **_k: "demo/uploads/a.glb",
    )
    monkeypatch.setattr(
        "reflex_r2_upload.routes.create_presigned_put_url",
        lambda *_a, **_k: "https://example/upload",
    )
    response = client.post(
        "/_reflex_r2_upload/presign",
        json={
            "keyPrefix": "demo/uploads",
            "filename": "a.glb",
            "fileSizeBytes": 1,
        },
    )

    assert response.status_code == 200


def test_require_upload_token_env_override(monkeypatch):
    monkeypatch.setenv("REFLEX_R2_REQUIRE_UPLOAD_TOKEN", "0")
    assert config.require_upload_token() is False


@patch("reflex_r2_upload.routes.missing_r2_env", return_value=[])
@patch("reflex_r2_upload.routes.object_exists", return_value=True)
@patch("reflex_r2_upload.routes.create_presigned_get_url", return_value="https://signed/get")
def test_signed_read_accepts_valid_token(_url, _exists, _env, monkeypatch):
    monkeypatch.setenv("REFLEX_R2_UPLOAD_SECRET", "unit-test-secret")
    token = issue_upload_token("demo/uploads")
    client = TestClient(create_upload_api())
    response = client.post(
        "/_reflex_r2_upload/signed-read",
        json={
            "keyPrefix": "demo/uploads",
            "storagePath": "demo/uploads/a.glb",
            "uploadToken": token,
        },
    )
    assert response.status_code == 200
    assert response.json()["signedUrl"] == "https://signed/get"


@patch("reflex_r2_upload.routes.missing_r2_env", return_value=[])
@patch("reflex_r2_upload.routes.object_exists", return_value=True)
@patch("reflex_r2_upload.routes.create_presigned_get_url", return_value="https://signed/get")
def test_signed_read_rejects_missing_token(_url, _exists, _env, monkeypatch):
    monkeypatch.setenv("REFLEX_R2_UPLOAD_SECRET", "unit-test-secret")
    client = TestClient(create_upload_api())
    response = client.post(
        "/_reflex_r2_upload/signed-read",
        json={
            "keyPrefix": "demo/uploads",
            "storagePath": "demo/uploads/a.glb",
        },
    )
    assert response.status_code == 401

