"""Tests for object key helpers."""

import pytest

from reflex_r2_upload.keys import (
    allocate_storage_path,
    normalize_prefix,
    safe_filename,
    validate_storage_path,
)


def test_safe_filename_strips_path():
    assert safe_filename("../../../etc/passwd") == "passwd"


def test_normalize_prefix_rejects_traversal():
    with pytest.raises(ValueError, match="\\.\\."):
        normalize_prefix("demo/../secret")


def test_validate_storage_path_prefix():
    key = validate_storage_path("demo/uploads", "demo/uploads/file.glb")
    assert key == "demo/uploads/file.glb"


def test_allocate_storage_path_extension(monkeypatch):
    monkeypatch.setattr(
        "reflex_r2_upload.keys.object_exists",
        lambda _key: False,
    )
    path = allocate_storage_path(
        "demo/uploads",
        "model.glb",
        allowed_extensions=[".glb"],
    )
    assert path == "demo/uploads/model.glb"
