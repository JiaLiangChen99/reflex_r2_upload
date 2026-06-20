"""Tests for upload size caps, GET expiry clamping, and rate limits."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient

from reflex_r2_upload.auth import issue_upload_token
from reflex_r2_upload.config import (
    configure_rate_limit,
    configure_upload_limits,
    get_expires,
    resolve_get_expires,
)
from reflex_r2_upload.rate_limit import reset_rate_limit_state
from reflex_r2_upload.routes import create_upload_api
from reflex_r2_upload.storage import create_presigned_get_url


@pytest.fixture(autouse=True)
def env_secret(monkeypatch):
    monkeypatch.setenv("REFLEX_R2_UPLOAD_SECRET", "unit-test-secret")
    monkeypatch.setenv("R2_ACCOUNT_ID", "acct")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("R2_BUCKET_NAME", "bucket")


def test_resolve_get_expires_clamps_to_cap(monkeypatch):
    monkeypatch.setenv("REFLEX_R2_GET_EXPIRES", "3600")
    assert resolve_get_expires(315360000) == 3600
    assert resolve_get_expires(30) == 60
    assert resolve_get_expires(None) == get_expires()


@patch("reflex_r2_upload.storage.ensure_r2_config")
@patch("reflex_r2_upload.storage._r2_client")
def test_create_presigned_get_url_uses_clamped_ttl(mock_client, _ensure, monkeypatch):
    monkeypatch.setenv("REFLEX_R2_GET_EXPIRES", "3600")
    mock_client.return_value = MagicMock(
        generate_presigned_url=MagicMock(return_value="https://get.example")
    )
    create_presigned_get_url("demo/a.glb", expires_in=999999)
    assert mock_client.return_value.generate_presigned_url.call_args.kwargs["ExpiresIn"] == 3600


@patch("reflex_r2_upload.routes.missing_r2_env", return_value=[])
def test_presign_rejects_oversized_file(_missing):
    configure_upload_limits(max_upload_bytes=1024)
    token = issue_upload_token("demo/uploads", allowed_extensions=[".glb"])
    client = TestClient(create_upload_api())
    response = client.post(
        "/_reflex_r2_upload/presign",
        json={
            "keyPrefix": "demo/uploads",
            "filename": "big.glb",
            "fileSizeBytes": 2048,
            "uploadToken": token,
        },
    )
    assert response.status_code == 400
    assert "超过上限" in response.json()["detail"]


@patch("reflex_r2_upload.routes.missing_r2_env", return_value=[])
@patch("reflex_r2_upload.routes.object_content_length", return_value=2048)
def test_complete_rejects_oversized_file(_size, _missing):
    configure_upload_limits(max_upload_bytes=1024)
    token = issue_upload_token("demo/uploads")
    client = TestClient(create_upload_api())
    response = client.post(
        "/_reflex_r2_upload/complete",
        json={
            "keyPrefix": "demo/uploads",
            "storagePath": "demo/uploads/big.glb",
            "originalFilename": "big.glb",
            "fileSizeBytes": 2048,
            "uploadToken": token,
        },
    )
    assert response.status_code == 400
    assert "超过上限" in response.json()["detail"]


@patch("reflex_r2_upload.routes.missing_r2_env", return_value=[])
@patch("reflex_r2_upload.routes.allocate_storage_path", return_value="demo/uploads/a.glb")
@patch("reflex_r2_upload.routes.create_presigned_put_url", return_value="https://put")
def test_presign_put_url_includes_content_length(_put, _alloc, _missing):
    configure_upload_limits(max_upload_bytes=4096)
    token = issue_upload_token("demo/uploads")
    client = TestClient(create_upload_api())
    response = client.post(
        "/_reflex_r2_upload/presign",
        json={
            "keyPrefix": "demo/uploads",
            "filename": "a.glb",
            "fileSizeBytes": 512,
            "uploadToken": token,
        },
    )
    assert response.status_code == 200
    assert _put.call_args.kwargs["content_length"] == 512


@patch("reflex_r2_upload.routes.missing_r2_env", return_value=[])
@patch("reflex_r2_upload.routes.object_exists", return_value=True)
@patch("reflex_r2_upload.routes.create_presigned_get_url", return_value="https://signed/get")
def test_signed_read_caps_expires_in(_url, _exists, _missing, monkeypatch):
    monkeypatch.setenv("REFLEX_R2_GET_EXPIRES", "3600")
    token = issue_upload_token("demo/uploads")
    client = TestClient(create_upload_api())
    response = client.post(
        "/_reflex_r2_upload/signed-read",
        json={
            "keyPrefix": "demo/uploads",
            "storagePath": "demo/uploads/a.glb",
            "expiresIn": 999999,
            "uploadToken": token,
        },
    )
    assert response.status_code == 200
    assert response.json()["expiresIn"] == 3600


@patch("reflex_r2_upload.routes.missing_r2_env", return_value=[])
@patch("reflex_r2_upload.routes.allocate_storage_path", return_value="demo/uploads/a.glb")
@patch("reflex_r2_upload.routes.create_presigned_put_url", return_value="https://put")
def test_rate_limit_returns_429(_put, _alloc, _missing):
    configure_rate_limit(requests=2, window_seconds=60)
    reset_rate_limit_state()
    token = issue_upload_token("demo/uploads")
    client = TestClient(create_upload_api())

    for _ in range(2):
        response = client.post(
            "/_reflex_r2_upload/presign",
            json={
                "keyPrefix": "demo/uploads",
                "filename": "a.glb",
                "fileSizeBytes": 1,
                "uploadToken": token,
            },
        )
        assert response.status_code != 429

    blocked = client.post(
        "/_reflex_r2_upload/presign",
        json={
            "keyPrefix": "demo/uploads",
            "filename": "a.glb",
            "fileSizeBytes": 1,
            "uploadToken": token,
        },
    )
    assert blocked.status_code == 429
    assert "频繁" in blocked.json()["detail"]
