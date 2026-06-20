"""Tests for signed-read route and presigned GET."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient

from reflex_r2_upload.auth import issue_upload_token
from reflex_r2_upload.routes import create_upload_api


def test_signed_read_requires_fields(monkeypatch):
    monkeypatch.setenv("REFLEX_R2_UPLOAD_SECRET", "unit-test-secret")
    monkeypatch.setenv("R2_ACCOUNT_ID", "acct")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("R2_BUCKET_NAME", "bucket")

    client = TestClient(create_upload_api())
    response = client.post("/_reflex_r2_upload/signed-read", json={})
    assert response.status_code == 400


def test_signed_read_rejects_missing_token(monkeypatch):
    monkeypatch.setenv("REFLEX_R2_UPLOAD_SECRET", "unit-test-secret")
    monkeypatch.setenv("R2_ACCOUNT_ID", "acct")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("R2_BUCKET_NAME", "bucket")

    client = TestClient(create_upload_api())
    response = client.post(
        "/_reflex_r2_upload/signed-read",
        json={
            "keyPrefix": "demo/uploads",
            "storagePath": "demo/uploads/a.glb",
        },
    )
    assert response.status_code == 401
    assert "未授权" in response.json()["detail"]


@patch("reflex_r2_upload.routes.missing_r2_env", return_value=[])
@patch("reflex_r2_upload.routes.object_exists", return_value=True)
@patch("reflex_r2_upload.routes.create_presigned_get_url", return_value="https://signed/get")
@patch("reflex_r2_upload.routes.get_expires", return_value=3600)
def test_signed_read_success(_exp, _url, _exists, _env, monkeypatch):
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
    data = response.json()
    assert data["signedUrl"] == "https://signed/get"
    assert data["storagePath"] == "demo/uploads/a.glb"


@patch("reflex_r2_upload.storage.ensure_r2_config")
@patch("reflex_r2_upload.storage._r2_client")
def test_create_presigned_get_url(mock_client, _ensure):
    mock_client.return_value = MagicMock(
        generate_presigned_url=MagicMock(return_value="https://get.example")
    )
    from reflex_r2_upload.storage import create_presigned_get_url

    url = create_presigned_get_url("demo/a.glb", expires_in=120)
    assert url == "https://get.example"
    mock_client.return_value.generate_presigned_url.assert_called_once()
    call = mock_client.return_value.generate_presigned_url.call_args
    assert call[0][0] == "get_object"
    assert call[1]["ExpiresIn"] == 120
