"""Tests for server-enforced upload extension policy."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from reflex_r2_upload.auth import issue_upload_token, upload_token_policy
from reflex_r2_upload.keys import is_allowed_extension
from reflex_r2_upload.routes import create_upload_api


@pytest.fixture(autouse=True)
def env_secret(monkeypatch):
    monkeypatch.setenv("REFLEX_R2_UPLOAD_SECRET", "unit-test-secret")
    monkeypatch.setenv("R2_ACCOUNT_ID", "acct")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("R2_BUCKET_NAME", "bucket")


def test_upload_token_policy_includes_extensions():
    token = issue_upload_token("demo/uploads", allowed_extensions=[".glb"])
    extensions, _content_type = upload_token_policy(token, "demo/uploads")
    assert extensions == [".glb"]


def test_is_allowed_extension_empty_list_denies_all():
    assert is_allowed_extension("file.glb", []) is False


@patch("reflex_r2_upload.routes.missing_r2_env", return_value=[])
def test_presign_ignores_client_allowed_extensions(_missing):
    token = issue_upload_token("demo/uploads", allowed_extensions=[".glb"])
    client = TestClient(create_upload_api())

    with patch("reflex_r2_upload.keys.object_exists", return_value=False):
        blocked = client.post(
            "/_reflex_r2_upload/presign",
            json={
                "keyPrefix": "demo/uploads",
                "filename": "evil.exe",
                "fileSizeBytes": 1,
                "uploadToken": token,
                "allowedExtensions": [],
            },
        )

    assert blocked.status_code == 400
    assert "不允许的文件类型" in blocked.json()["detail"]


@patch("reflex_r2_upload.routes.missing_r2_env", return_value=[])
def test_presign_accepts_extension_from_token(_missing):
    token = issue_upload_token("demo/uploads", allowed_extensions=[".glb"])
    client = TestClient(create_upload_api())

    with patch(
        "reflex_r2_upload.routes.allocate_storage_path",
        lambda *_a, **_k: "demo/uploads/model.glb",
    ), patch(
        "reflex_r2_upload.routes.create_presigned_put_url",
        lambda *_a, **_k: "https://example/upload",
    ):
        response = client.post(
            "/_reflex_r2_upload/presign",
            json={
                "keyPrefix": "demo/uploads",
                "filename": "model.glb",
                "fileSizeBytes": 1,
                "uploadToken": token,
                "allowedExtensions": [".exe"],
            },
        )

    assert response.status_code == 200


@patch("reflex_r2_upload.routes.missing_r2_env", return_value=[])
def test_presign_uses_token_content_type(_missing):
    token = issue_upload_token(
        "demo/uploads",
        allowed_extensions=[".glb"],
        content_type="model/gltf-binary",
    )
    client = TestClient(create_upload_api())

    with patch(
        "reflex_r2_upload.routes.allocate_storage_path",
        return_value="demo/uploads/model.glb",
    ), patch(
        "reflex_r2_upload.routes.create_presigned_put_url",
        return_value="https://example/upload",
    ) as presign_put:
        response = client.post(
            "/_reflex_r2_upload/presign",
            json={
                "keyPrefix": "demo/uploads",
                "filename": "model.glb",
                "fileSizeBytes": 1,
                "contentType": "application/octet-stream",
                "uploadToken": token,
            },
        )

    assert response.status_code == 200
    assert presign_put.call_args.args[1] == "model/gltf-binary"
