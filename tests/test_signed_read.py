"""Tests for signed-read route and presigned GET."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from reflex_r2_upload.routes import create_upload_api


def test_signed_read_requires_fields():
    api = create_upload_api()
    with httpx.Client(
        transport=httpx.ASGITransport(app=api),
        base_url="http://test",
    ) as client:
        response = client.post("/_reflex_r2_upload/signed-read", json={})
    assert response.status_code == 400


@patch("reflex_r2_upload.routes.missing_r2_env", return_value=[])
@patch("reflex_r2_upload.routes.object_exists", return_value=True)
@patch("reflex_r2_upload.routes.create_presigned_get_url", return_value="https://signed/get")
@patch("reflex_r2_upload.routes.get_expires", return_value=3600)
def test_signed_read_success(_exp, _url, _exists, _env):
    api = create_upload_api()
    with httpx.Client(
        transport=httpx.ASGITransport(app=api),
        base_url="http://test",
    ) as client:
        response = client.post(
            "/_reflex_r2_upload/signed-read",
            json={
                "keyPrefix": "demo/uploads",
                "storagePath": "demo/uploads/a.glb",
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
