"""R2 integration tests (require real credentials in .env)."""

from __future__ import annotations

import os
import uuid

import httpx
import pytest
from dotenv import load_dotenv

from reflex_r2_upload.config import missing_r2_env
from reflex_r2_upload.routes import create_upload_api
from reflex_r2_upload.storage import object_exists

load_dotenv()

pytestmark = pytest.mark.r2

_requires_r2 = pytest.mark.skipif(
    bool(missing_r2_env()),
    reason="R2 credentials not configured in .env",
)


@pytest.fixture
def api():
    return create_upload_api()


@_requires_r2
def test_config_ready(api):
    with httpx.Client(
        transport=httpx.ASGITransport(app=api),
        base_url="http://test",
    ) as client:
        response = client.get("/_reflex_r2_upload/config")
    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True
    assert not data.get("missingEnv")


@_requires_r2
def test_presign_put_complete_flow(api):
    key_prefix = f"test/reflex_r2/{uuid.uuid4().hex}"
    filename = "probe.txt"
    body = b"reflex-r2-upload integration test"

    with httpx.Client(
        transport=httpx.ASGITransport(app=api),
        base_url="http://test",
        timeout=30.0,
    ) as client:
        presign = client.post(
            "/_reflex_r2_upload/presign",
            json={
                "keyPrefix": key_prefix,
                "filename": filename,
                "contentType": "text/plain",
            },
        )
        assert presign.status_code == 200, presign.text
        presign_data = presign.json()

        put = httpx.put(
            presign_data["uploadUrl"],
            content=body,
            headers={"Content-Type": "text/plain"},
            timeout=30.0,
        )
        assert put.status_code in {200, 201}, put.text

        storage_path = presign_data["storagePath"]
        complete = client.post(
            "/_reflex_r2_upload/complete",
            json={
                "keyPrefix": key_prefix,
                "storagePath": storage_path,
                "originalFilename": filename,
                "fileSizeBytes": len(body),
                "contentType": "text/plain",
            },
        )
        assert complete.status_code == 200, complete.text
        result = complete.json()
        assert result["version"] == 1
        assert result["keyPrefix"] == key_prefix
        assert result["storagePath"] == storage_path
        assert result["fileSizeBytes"] == len(body)
        assert "publicUrl" in result

    assert object_exists(storage_path)

    with httpx.Client(
        transport=httpx.ASGITransport(app=api),
        base_url="http://test",
        timeout=30.0,
    ) as client:
        signed = client.post(
            "/_reflex_r2_upload/signed-read",
            json={"keyPrefix": key_prefix, "storagePath": storage_path},
        )
        assert signed.status_code == 200, signed.text
        assert signed.json()["signedUrl"].startswith("http")

    if os.environ.get("REFLEX_R2_TEST_CLEANUP", "1") != "0":
        from reflex_r2_upload.storage import _bucket_name, _r2_client

        _r2_client().delete_object(Bucket=_bucket_name(), Key=storage_path.lstrip("/"))
