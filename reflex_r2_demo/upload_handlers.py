"""Reference upload handlers for copy-paste into your Reflex app.

These functions illustrate common patterns; the demo page imports and uses them.
"""

from __future__ import annotations

import reflex_r2_upload as r2


def parse_upload_or_error(
    payload_json: r2.UploadPayloadJson,
) -> tuple[r2.UploadResult | None, str, str | None]:
    """Parse bridge JSON; return ``(result, error_message, error_code)``."""
    try:
        return r2.parse_upload_payload(payload_json), "", None
    except r2.UploadPayloadError as error:
        return None, error.message, error.code


def describe_upload(result: r2.UploadResult) -> str:
    """Human-readable summary distinguishing public vs private access."""
    file = result.file
    if file.public_url:
        return (
            f"公开访问：{file.original_filename} → {file.public_url} "
            f"[{result.key_prefix}]"
        )
    return (
        f"私有对象：{file.original_filename} @ {file.storage_path} "
        f"(publicUrl=null，需服务端 presigned GET) [{result.key_prefix}]"
    )


def describe_multi_upload(result: r2.UploadResult) -> str:
    names = ", ".join(f.original_filename for f in result.files)
    return f"已上传 {len(result.files)} 个文件：{names} [{result.key_prefix}]"


def signed_url_for_storage(
    storage_path: str,
    *,
    public_url: str | None = None,
    expires_in: int | None = None,
) -> str:
    """Return ``public_url`` or issue presigned GET for private objects."""
    if public_url:
        return public_url
    return r2.signed_read_url(storage_path, expires_in=expires_in)
