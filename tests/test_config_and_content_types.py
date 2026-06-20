"""Tests for /config disclosure and Content-Type policy."""

from __future__ import annotations

from unittest.mock import patch

from starlette.testclient import TestClient

from reflex_r2_upload.auth import issue_upload_token
from reflex_r2_upload.config import configure_verbose_config
from reflex_r2_upload.routes import create_upload_api


def test_config_minimal_by_default():
    client = TestClient(create_upload_api())
    response = client.get("/_reflex_r2_upload/config")
    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {"ready"}


def test_config_verbose_when_enabled():
    configure_verbose_config(True)
    client = TestClient(create_upload_api())
    response = client.get("/_reflex_r2_upload/config")
    data = response.json()
    assert "missingEnv" in data
    assert "publicBaseUrl" in data
    assert "routePrefix" in data


@patch("reflex_r2_upload.routes.missing_r2_env", return_value=[])
@patch("reflex_r2_upload.routes.allocate_storage_path", return_value="demo/uploads/x.glb")
@patch("reflex_r2_upload.routes.create_presigned_put_url", return_value="https://put")
def test_presign_blocks_html_content_type(_put, _alloc, _missing, monkeypatch):
    monkeypatch.setenv("REFLEX_R2_UPLOAD_SECRET", "unit-test-secret")
    monkeypatch.setenv("R2_ACCOUNT_ID", "acct")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("R2_BUCKET_NAME", "bucket")

    client = TestClient(create_upload_api(require_upload_token=False))
    response = client.post(
        "/_reflex_r2_upload/presign",
        json={
            "keyPrefix": "demo/uploads",
            "filename": "x.glb",
            "fileSizeBytes": 1,
            "contentType": "text/html",
        },
    )
    assert response.status_code == 400
    assert "Content-Type" in response.json()["detail"]


@patch("reflex_r2_upload.routes.missing_r2_env", return_value=[])
@patch("reflex_r2_upload.routes.allocate_storage_path", return_value="demo/uploads/model.glb")
@patch("reflex_r2_upload.routes.create_presigned_put_url", return_value="https://put")
def test_presign_rejects_mismatched_type_for_extension(_put, _alloc, _missing, monkeypatch):
    monkeypatch.setenv("REFLEX_R2_UPLOAD_SECRET", "unit-test-secret")
    monkeypatch.setenv("R2_ACCOUNT_ID", "acct")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("R2_BUCKET_NAME", "bucket")

    token = issue_upload_token(
        "demo/uploads",
        allowed_extensions=[".glb"],
        content_type="image/png",
    )
    client = TestClient(create_upload_api())
    response = client.post(
        "/_reflex_r2_upload/presign",
        json={
            "keyPrefix": "demo/uploads",
            "filename": "model.glb",
            "fileSizeBytes": 1,
            "contentType": "text/html",
            "uploadToken": token,
        },
    )
    assert response.status_code == 400
    assert "Content-Type" in response.json()["detail"]


@patch("reflex_r2_upload.routes.missing_r2_env", return_value=[])
@patch("reflex_r2_upload.routes.allocate_storage_path", return_value="demo/uploads/model.glb")
@patch("reflex_r2_upload.routes.create_presigned_put_url", return_value="https://put")
def test_presign_ignores_client_content_type_when_token_bound(_put, _alloc, _missing, monkeypatch):
    monkeypatch.setenv("REFLEX_R2_UPLOAD_SECRET", "unit-test-secret")
    monkeypatch.setenv("R2_ACCOUNT_ID", "acct")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("R2_BUCKET_NAME", "bucket")

    token = issue_upload_token(
        "demo/uploads",
        allowed_extensions=[".glb"],
        content_type="model/gltf-binary",
    )
    client = TestClient(create_upload_api())
    response = client.post(
        "/_reflex_r2_upload/presign",
        json={
            "keyPrefix": "demo/uploads",
            "filename": "model.glb",
            "fileSizeBytes": 1,
            "contentType": "text/html",
            "uploadToken": token,
        },
    )
    assert response.status_code == 200
    assert _put.call_args.args[1] == "model/gltf-binary"
