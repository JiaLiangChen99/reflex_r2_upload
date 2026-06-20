"""Cloudflare R2 object storage primitives."""

from __future__ import annotations

from functools import lru_cache
from typing import Any
from urllib.parse import quote

from reflex_r2_upload.config import (
    access_key_id,
    account_id,
    bucket_name,
    ensure_r2_config,
    get_expires,
    is_public_access_configured,
    presign_expires,
    public_base_url,
    resolve_get_expires,
    secret_access_key,
)

DEFAULT_CONTENT_TYPE = "application/octet-stream"


def public_url(storage_path: str) -> str:
    """Return a public HTTP URL when ``R2_PUBLIC_BASE_URL`` is set, else the key."""
    optional = public_url_or_none(storage_path)
    if optional is not None:
        return optional
    return storage_path


def public_url_or_none(storage_path: str) -> str | None:
    """Return a public HTTP URL, or ``None`` when no public base is configured."""
    if not storage_path:
        return None
    if storage_path.startswith(("http://", "https://")):
        return storage_path
    base = public_base_url()
    if not base:
        return None
    key = storage_path.lstrip("/")
    encoded = "/".join(quote(part, safe="") for part in key.split("/"))
    return f"{base}/{encoded}"


@lru_cache
def _r2_client() -> Any:
    ensure_r2_config()
    try:
        import boto3
        from botocore.config import Config
    except ImportError as error:
        raise RuntimeError("需要 boto3，请执行：pip install boto3") from error

    aid = account_id()
    return boto3.client(
        "s3",
        endpoint_url=f"https://{aid}.r2.cloudflarestorage.com",
        aws_access_key_id=access_key_id(),
        aws_secret_access_key=secret_access_key(),
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def clear_r2_client_cache() -> None:
    _r2_client.cache_clear()


def _bucket_name() -> str:
    ensure_r2_config()
    return bucket_name()


def _head_object(storage_path: str) -> dict[str, Any] | None:
    """Return S3 head_object metadata, or ``None`` when the key is missing."""
    key = storage_path.lstrip("/")
    if not key:
        return None

    try:
        from botocore.exceptions import ClientError

        return _r2_client().head_object(Bucket=_bucket_name(), Key=key)
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code", "")
        if code in {"404", "NoSuchKey", "NotFound"}:
            return None
        raise


def object_exists(storage_path: str) -> bool:
    return _head_object(storage_path) is not None


def object_content_length(storage_path: str) -> int | None:
    """Return object size in bytes, or ``None`` when the key is missing."""
    metadata = _head_object(storage_path)
    if metadata is None:
        return None
    return int(metadata["ContentLength"])


def create_presigned_put_url(
    storage_path: str,
    content_type: str = DEFAULT_CONTENT_TYPE,
    *,
    expires_in: int | None = None,
    content_length: int | None = None,
) -> str:
    key = storage_path.lstrip("/")
    params: dict[str, Any] = {
        "Bucket": _bucket_name(),
        "Key": key,
        "ContentType": content_type,
    }
    if content_length is not None and content_length > 0:
        params["ContentLength"] = int(content_length)
    return _r2_client().generate_presigned_url(
        "put_object",
        Params=params,
        ExpiresIn=expires_in or presign_expires(),
    )


def create_presigned_get_url(
    storage_path: str,
    *,
    expires_in: int | None = None,
) -> str:
    """Create a time-limited read URL for a private bucket object."""
    key = storage_path.lstrip("/")
    ttl = resolve_get_expires(expires_in)
    return _r2_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": _bucket_name(), "Key": key},
        ExpiresIn=ttl,
    )
