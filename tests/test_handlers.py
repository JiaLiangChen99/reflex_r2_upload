"""Tests for demo upload handler helpers."""

import json

import pytest

import reflex_r2_upload as r2
from reflex_r2_demo.upload_handlers import (
    describe_upload,
    parse_upload_or_error,
    signed_url_for_storage,
)
from reflex_r2_upload.payload import file_bridge_payload


@pytest.fixture(autouse=True)
def bridge_signing_secret(monkeypatch):
    monkeypatch.setenv("REFLEX_R2_UPLOAD_SECRET", "unit-test-bridge-secret")


def test_parse_upload_or_error_success():
    payload = json.dumps(
        file_bridge_payload(
            key_prefix="demo/x",
            storage_path="demo/x/a.glb",
            original_filename="a.glb",
            file_size_bytes=1,
            content_type="model/gltf-binary",
        )
    )
    result, err, code = parse_upload_or_error(payload)
    assert result is not None
    assert err == ""
    assert code is None


def test_describe_upload_private():
    payload = json.dumps(
        file_bridge_payload(
            key_prefix="p",
            storage_path="p/f.glb",
            original_filename="f.glb",
            file_size_bytes=1,
            content_type="model/gltf-binary",
        )
    )
    result, _, _ = parse_upload_or_error(payload)
    text = describe_upload(result)
    assert "私有对象" in text
    assert "publicUrl=null" in text


def test_signed_url_for_storage_uses_public_when_set(monkeypatch):
    monkeypatch.setattr(
        r2,
        "signed_read_url",
        lambda *_a, **_k: "https://signed.example/get",
    )
    url = signed_url_for_storage(
        "demo/a.glb",
        public_url="https://cdn.example/a.glb",
    )
    assert url == "https://cdn.example/a.glb"


def test_signed_url_for_storage_presign_when_private(monkeypatch):
    monkeypatch.setattr(
        r2,
        "signed_read_url",
        lambda path, expires_in=None: f"signed:{path}",
    )
    url = signed_url_for_storage("demo/a.glb", public_url=None)
    assert url == "signed:demo/a.glb"
