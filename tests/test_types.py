"""Tests for upload payload parsing."""

import json

import pytest

import reflex_r2_upload as r2
from reflex_r2_upload.config import configure_upload_auth
from reflex_r2_upload.payload import file_bridge_payload


@pytest.fixture(autouse=True)
def bridge_signing_secret(monkeypatch):
    monkeypatch.setenv("REFLEX_R2_UPLOAD_SECRET", "unit-test-bridge-secret")
    configure_upload_auth(require_bridge_signature=None)
    yield
    configure_upload_auth(require_bridge_signature=None)


def test_parse_v1_single_file_payload(monkeypatch):
    monkeypatch.setenv("R2_PUBLIC_BASE_URL", "https://cdn.example.com")
    body = file_bridge_payload(
        key_prefix="demo/uploads",
        storage_path="demo/a.glb",
        original_filename="a.glb",
        file_size_bytes=42,
        content_type="model/gltf-binary",
    )
    result = r2.parse_upload_payload(json.dumps(body))
    assert result.version == 1
    assert result.key_prefix == "demo/uploads"
    assert result.file.storage_path == "demo/a.glb"
    assert result.file.key_prefix == "demo/uploads"
    assert result.file.public_url == "https://cdn.example.com/demo/a.glb"


def test_parse_public_url_null():
    body = file_bridge_payload(
        key_prefix="demo/uploads",
        storage_path="demo/a.glb",
        original_filename="a.glb",
        file_size_bytes=42,
        content_type="model/gltf-binary",
    )
    result = r2.parse_upload_payload(json.dumps(body))
    assert result.file.public_url is None


def test_parse_multi_file_payload():
    file_item = file_bridge_payload(
        key_prefix="demo/uploads",
        storage_path="demo/a.glb",
        original_filename="a.glb",
        file_size_bytes=1,
        content_type="model/gltf-binary",
    )
    payload = json.dumps(
        {
            "version": 1,
            "error": False,
            "keyPrefix": "demo/uploads",
            "files": [file_item, file_item],
        }
    )
    result = r2.parse_upload_payload(payload)
    assert len(result.files) == 2


def test_parse_legacy_payload_without_version():
    body = file_bridge_payload(
        key_prefix="legacy",
        storage_path="legacy/a.glb",
        original_filename="a.glb",
        file_size_bytes=1,
        content_type="application/octet-stream",
    )
    body.pop("version", None)
    result = r2.parse_upload_payload(json.dumps(body))
    assert result.version == 1
    assert result.file.key_prefix == "legacy"


def test_parse_rejects_forged_signature():
    body = file_bridge_payload(
        key_prefix="demo/uploads",
        storage_path="demo/a.glb",
        original_filename="a.glb",
        file_size_bytes=42,
        content_type="model/gltf-binary",
    )
    body["bridgeSignature"] = "forged"
    with pytest.raises(r2.UploadPayloadError) as exc:
        r2.parse_upload_payload(json.dumps(body))
    assert exc.value.code == r2.UploadErrorCode.INVALID_SIGNATURE


def test_parse_allows_unsigned_when_disabled():
    configure_upload_auth(require_bridge_signature=False)
    payload = json.dumps(
        {
            "version": 1,
            "error": False,
            "ok": True,
            "keyPrefix": "legacy",
            "storagePath": "legacy/a.glb",
            "originalFilename": "a.glb",
            "fileSizeBytes": 1,
            "contentType": "application/octet-stream",
        }
    )
    result = r2.parse_upload_payload(payload)
    assert result.file.storage_path == "legacy/a.glb"


def test_parse_error_payload_with_code():
    with pytest.raises(r2.UploadPayloadError) as exc:
        r2.parse_upload_payload(
            json.dumps(
                {
                    "version": 1,
                    "error": True,
                    "message": "R2 未配置",
                    "code": r2.UploadErrorCode.R2_NOT_CONFIGURED,
                }
            )
        )
    assert exc.value.code == r2.UploadErrorCode.R2_NOT_CONFIGURED
