"""Tests for upload payload parsing."""

import json

import pytest

import reflex_r2_upload as r2


def test_parse_v1_single_file_payload():
    payload = json.dumps(
        {
            "version": 1,
            "error": False,
            "ok": True,
            "keyPrefix": "demo/uploads",
            "storagePath": "demo/a.glb",
            "originalFilename": "a.glb",
            "fileSizeBytes": 42,
            "contentType": "model/gltf-binary",
            "publicUrl": "https://cdn.example.com/demo/a.glb",
        }
    )
    result = r2.parse_upload_payload(payload)
    assert result.version == 1
    assert result.key_prefix == "demo/uploads"
    assert result.file.storage_path == "demo/a.glb"
    assert result.file.key_prefix == "demo/uploads"
    assert result.file.public_url == "https://cdn.example.com/demo/a.glb"


def test_parse_public_url_null():
    payload = json.dumps(
        {
            "version": 1,
            "error": False,
            "ok": True,
            "keyPrefix": "demo/uploads",
            "storagePath": "demo/a.glb",
            "originalFilename": "a.glb",
            "fileSizeBytes": 42,
            "contentType": "model/gltf-binary",
            "publicUrl": None,
        }
    )
    result = r2.parse_upload_payload(payload)
    assert result.file.public_url is None


def test_parse_multi_file_payload():
    file_item = {
        "version": 1,
        "error": False,
        "ok": True,
        "keyPrefix": "demo/uploads",
        "storagePath": "demo/a.glb",
        "originalFilename": "a.glb",
        "fileSizeBytes": 1,
        "contentType": "model/gltf-binary",
        "publicUrl": None,
    }
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
    payload = json.dumps(
        {
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
    assert result.version == 1
    assert result.file.key_prefix == "legacy"


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
