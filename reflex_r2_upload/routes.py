"""Starlette routes for browser-direct R2 uploads."""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Route

from reflex_r2_upload.auth import (
    PresignGuard,
    authorize_storage_request,
    authorize_upload_request,
    set_presign_guard,
    upload_token_policy,
)
from reflex_r2_upload.config import (
    build_config_payload,
    get_expires,
    missing_r2_env,
    require_upload_token as config_require_upload_token,
    route_prefix,
)
from reflex_r2_upload.content_types import (
    resolve_presign_content_type,
    validate_content_type,
    validate_content_type_for_filename,
)
from reflex_r2_upload.http import fail, ok, read_json, require_fields
from reflex_r2_upload.keys import allocate_storage_path, validate_storage_path
from reflex_r2_upload.limits import (
    clamp_get_expires,
    parse_file_size_bytes,
    validate_file_size_bytes,
)
from reflex_r2_upload.payload import file_bridge_payload
from reflex_r2_upload.rate_limit import rate_limit_error
from reflex_r2_upload.storage import (
    DEFAULT_CONTENT_TYPE,
    create_presigned_get_url,
    create_presigned_put_url,
    object_content_length,
    object_exists,
)


def create_upload_api(
    *,
    prefix: str | None = None,
    require_upload_token: bool | None = None,
    presign_guard: PresignGuard | None = None,
) -> Starlette:
    """Create a Starlette app with presign / complete routes for R2 direct upload."""
    mounted_prefix = (prefix or route_prefix()).rstrip("/")
    if presign_guard is not None:
        set_presign_guard(presign_guard)

    def _require_upload_token_enabled() -> bool:
        if require_upload_token is not None:
            return bool(require_upload_token)
        return config_require_upload_token()

    async def storage_config(_request: Request):
        return ok(build_config_payload(route_prefix_value=mounted_prefix))

    async def presign(request: Request):
        if missing_r2_env():
            return fail("R2 未配置，请设置 .env 中的 R2_* 环境变量", status_code=503)

        throttled = rate_limit_error(request)
        if throttled:
            return fail(throttled, status_code=429)

        data = await read_json(request)
        missing = require_fields(data, "keyPrefix", "filename")
        if missing:
            return fail(missing)

        file_size, size_error = parse_file_size_bytes(data)
        if size_error:
            return fail(size_error)
        assert file_size is not None
        size_limit_error = validate_file_size_bytes(file_size)
        if size_limit_error:
            return fail(size_limit_error)

        key_prefix = str(data["keyPrefix"]).strip()
        filename = str(data["filename"]).strip()
        client_content_type = str(data.get("contentType") or DEFAULT_CONTENT_TYPE).strip()
        extensions: list[str] | None = None
        token_content_type: str | None = None

        auth_error = await authorize_upload_request(
            request,
            data,
            key_prefix,
            require_token=require_upload_token,
            presign_guard=presign_guard,
        )
        if auth_error:
            return fail(auth_error, status_code=401)

        upload_token = data.get("uploadToken")
        if isinstance(upload_token, str) and upload_token:
            token_extensions, token_content_type = upload_token_policy(
                upload_token,
                key_prefix,
            )
            if token_extensions is not None:
                extensions = token_extensions

        content_type = resolve_presign_content_type(
            client_content_type,
            token_content_type,
            require_upload_token=_require_upload_token_enabled(),
        )
        type_error = validate_content_type_for_filename(
            content_type,
            filename,
            extensions,
        )
        if type_error:
            return fail(type_error)

        try:
            storage_path = allocate_storage_path(
                key_prefix,
                filename,
                allowed_extensions=extensions,
            )
        except ValueError as error:
            return fail(str(error))

        try:
            upload_url = create_presigned_put_url(
                storage_path,
                content_type,
                content_length=file_size,
            )
        except RuntimeError as error:
            return fail(str(error), status_code=500)

        return ok(
            {
                "uploadUrl": upload_url,
                "storagePath": storage_path,
                "contentType": content_type,
                "fileSizeBytes": file_size,
            }
        )

    async def complete(request: Request):
        if missing_r2_env():
            return fail("R2 未配置，请设置 .env 中的 R2_* 环境变量", status_code=503)

        throttled = rate_limit_error(request)
        if throttled:
            return fail(throttled, status_code=429)

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

        size_limit_error = validate_file_size_bytes(file_size)
        if size_limit_error:
            return fail(size_limit_error)

        key_prefix = str(data["keyPrefix"]).strip()
        auth_error = await authorize_upload_request(
            request,
            data,
            key_prefix,
            require_token=require_upload_token,
            presign_guard=presign_guard,
        )
        if auth_error:
            return fail(auth_error, status_code=401)

        try:
            key = validate_storage_path(key_prefix, str(data["storagePath"]))
        except ValueError as error:
            return fail(str(error))

        try:
            actual_size = object_content_length(key)
        except RuntimeError as error:
            return fail(str(error), status_code=500)

        if actual_size is None:
            return fail("对象不存在或未完成上传", status_code=404)

        if actual_size != file_size:
            return fail("fileSizeBytes 与 R2 对象大小不一致")

        original_filename = str(data["originalFilename"])
        client_content_type = str(data.get("contentType") or DEFAULT_CONTENT_TYPE).strip()
        token_extensions: list[str] | None = None
        token_content_type: str | None = None
        upload_token = data.get("uploadToken")
        if isinstance(upload_token, str) and upload_token:
            token_extensions, token_content_type = upload_token_policy(
                upload_token,
                key_prefix,
            )
        content_type = resolve_presign_content_type(
            client_content_type,
            token_content_type,
            require_upload_token=_require_upload_token_enabled(),
        )
        type_error = validate_content_type_for_filename(
            content_type,
            original_filename,
            token_extensions,
        )
        if type_error is None:
            type_error = validate_content_type(content_type)
        if type_error:
            return fail(type_error)

        return ok(
            file_bridge_payload(
                key_prefix=key_prefix,
                storage_path=key,
                original_filename=original_filename,
                file_size_bytes=file_size,
                content_type=content_type,
            )
        )

    async def signed_read(request: Request):
        """Issue a presigned GET URL for private bucket objects (server-side only)."""
        if missing_r2_env():
            return fail("R2 未配置，请设置 .env 中的 R2_* 环境变量", status_code=503)

        throttled = rate_limit_error(request)
        if throttled:
            return fail(throttled, status_code=429)

        data = await read_json(request)
        missing = require_fields(data, "keyPrefix", "storagePath")
        if missing:
            return fail(missing)

        key_prefix = str(data["keyPrefix"]).strip()
        auth_error = await authorize_storage_request(
            request,
            data,
            key_prefix,
            require_token=require_upload_token,
            presign_guard=presign_guard,
            unauthorized_message="未授权的读访问请求",
        )
        if auth_error:
            return fail(auth_error, status_code=401)

        try:
            key = validate_storage_path(key_prefix, str(data["storagePath"]))
        except ValueError as error:
            return fail(str(error))

        if not object_exists(key):
            return fail("对象不存在", status_code=404)

        expires_raw = data.get("expiresIn")
        expires_in: int | None = None
        if expires_raw is not None:
            try:
                expires_in = clamp_get_expires(int(expires_raw))
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
                "expiresIn": expires_in if expires_in is not None else get_expires(),
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
