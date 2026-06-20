"""Tests for the complete upload route."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

import reflex_r2_upload.auth as auth
from reflex_r2_upload.auth import issue_upload_token
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


def _complete_payload(*, token: str, file_size: int = 12) -> dict:
    return {
        "keyPrefix": "demo/uploads",
        "storagePath": "demo/uploads/file.glb",
        "originalFilename": "file.glb",
        "fileSizeBytes": file_size,
        "contentType": "model/gltf-binary",
        "uploadToken": token,
    }


@patch("reflex_r2_upload.routes.missing_r2_env", return_value=[])
def test_complete_rejects_missing_object(_missing, monkeypatch):
    monkeypatch.setenv("REFLEX_R2_UPLOAD_SECRET", "unit-test-secret")
    token = issue_upload_token("demo/uploads")
    client = TestClient(create_upload_api())

    with patch("reflex_r2_upload.routes.object_content_length", return_value=None):
        response = client.post(
            "/_reflex_r2_upload/complete",
            json=_complete_payload(token=token),
        )

    assert response.status_code == 404
    assert "不存在" in response.json()["detail"]


@patch("reflex_r2_upload.routes.missing_r2_env", return_value=[])
def test_complete_rejects_size_mismatch(_missing, monkeypatch):
    monkeypatch.setenv("REFLEX_R2_UPLOAD_SECRET", "unit-test-secret")
    token = issue_upload_token("demo/uploads")
    client = TestClient(create_upload_api())

    with patch("reflex_r2_upload.routes.object_content_length", return_value=99):
        response = client.post(
            "/_reflex_r2_upload/complete",
            json=_complete_payload(token=token, file_size=12),
        )

    assert response.status_code == 400
    assert "大小不一致" in response.json()["detail"]


@patch("reflex_r2_upload.routes.missing_r2_env", return_value=[])
def test_complete_accepts_verified_object(_missing, monkeypatch):
    monkeypatch.setenv("REFLEX_R2_UPLOAD_SECRET", "unit-test-secret")
    token = issue_upload_token("demo/uploads")
    client = TestClient(create_upload_api())

    with patch("reflex_r2_upload.routes.object_content_length", return_value=12):
        response = client.post(
            "/_reflex_r2_upload/complete",
            json=_complete_payload(token=token, file_size=12),
        )

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["storagePath"] == "demo/uploads/file.glb"
    assert data["fileSizeBytes"] == 12
    assert isinstance(data.get("bridgeSignature"), str)
    assert data["bridgeSignature"]
