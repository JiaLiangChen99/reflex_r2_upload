"""Starlette routes for browser-direct R2 uploads."""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Route

from reflex_r2_upload.config import get_expires, missing_r2_env, public_base_url, route_prefix
from reflex_r2_upload.http import fail, ok, read_json, require_fields
from reflex_r2_upload.keys import allocate_storage_path, validate_storage_path
from reflex_r2_upload.payload import file_bridge_payload
from reflex_r2_upload.storage import (
    DEFAULT_CONTENT_TYPE,
    create_presigned_get_url,
    create_presigned_put_url,
    object_exists,
)


def create_upload_api(*, prefix: str | None = None) -> Starlette:
    """Create a Starlette app with presign / complete routes for R2 direct upload."""
    mounted_prefix = (prefix or route_prefix()).rstrip("/")

    async def storage_config(_request: Request):
        missing = missing_r2_env()
        base = public_base_url()
        return ok(
            {
                "ready": not missing,
                "missingEnv": missing or None,
                "publicBaseUrl": base or None,
                "routePrefix": mounted_prefix,
            }
        )

    async def presign(request: Request):
        if missing_r2_env():
            return fail("R2 未配置，请设置 .env 中的 R2_* 环境变量", status_code=503)

        data = await read_json(request)
        missing = require_fields(data, "keyPrefix", "filename")
        if missing:
            return fail(missing)

        key_prefix = str(data["keyPrefix"]).strip()
        filename = str(data["filename"]).strip()
        content_type = str(data.get("contentType") or DEFAULT_CONTENT_TYPE).strip()
        allowed = data.get("allowedExtensions")
        extensions = allowed if isinstance(allowed, list) else None

        try:
            storage_path = allocate_storage_path(
                key_prefix,
                filename,
                allowed_extensions=extensions,
            )
        except ValueError as error:
            return fail(str(error))

        try:
            upload_url = create_presigned_put_url(storage_path, content_type)
        except RuntimeError as error:
            return fail(str(error), status_code=500)

        return ok(
            {
                "uploadUrl": upload_url,
                "storagePath": storage_path,
                "contentType": content_type,
            }
        )

    async def complete(request: Request):
        data = await read_json(request)
        missing = require_fields(
            data, "keyPrefix", "storagePath", "originalFilename", "fileSizeBytes"
        )
        if missing:
            return fail(missing)

        try:
            file_size = int(data["fileSizeBytes"])
        except (TypeError, ValueError):
            return fail("fileSizeBytes 无效")
        if file_size < 1:
            return fail("fileSizeBytes 无效")

        key_prefix = str(data["keyPrefix"]).strip()
        try:
            key = validate_storage_path(key_prefix, str(data["storagePath"]))
        except ValueError as error:
            return fail(str(error))

        return ok(
            file_bridge_payload(
                key_prefix=key_prefix,
                storage_path=key,
                original_filename=str(data["originalFilename"]),
                file_size_bytes=file_size,
                content_type=str(data.get("contentType") or DEFAULT_CONTENT_TYPE),
            )
        )

    async def signed_read(request: Request):
        """Issue a presigned GET URL for private bucket objects (server-side only)."""
        if missing_r2_env():
            return fail("R2 未配置，请设置 .env 中的 R2_* 环境变量", status_code=503)

        data = await read_json(request)
        missing = require_fields(data, "keyPrefix", "storagePath")
        if missing:
            return fail(missing)

        key_prefix = str(data["keyPrefix"]).strip()
        try:
            key = validate_storage_path(key_prefix, str(data["storagePath"]))
        except ValueError as error:
            return fail(str(error))

        if not object_exists(key):
            return fail("对象不存在", status_code=404)

        expires_raw = data.get("expiresIn")
        expires_in = None
        if expires_raw is not None:
            try:
                expires_in = max(60, int(expires_raw))
            except (TypeError, ValueError):
                return fail("expiresIn 无效")

        try:
            signed = create_presigned_get_url(key, expires_in=expires_in)
        except RuntimeError as error:
            return fail(str(error), status_code=500)

        return ok(
            {
                "signedUrl": signed,
                "storagePath": key,
                "keyPrefix": key_prefix,
                "expiresIn": expires_in or get_expires(),
            }
        )

    return Starlette(
        routes=[
            Route(f"{mounted_prefix}/config", storage_config, methods=["GET"]),
            Route(f"{mounted_prefix}/presign", presign, methods=["POST"]),
            Route(f"{mounted_prefix}/complete", complete, methods=["POST"]),
            Route(f"{mounted_prefix}/signed-read", signed_read, methods=["POST"]),
        ],
    )
