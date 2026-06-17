"""Typed payloads for upload_zone bridge callbacks (schema version 1)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal, NotRequired, TypeAlias, TypedDict

from reflex_r2_upload.payload import BRIDGE_PAYLOAD_VERSION, UploadErrorCode

__all__ = [
    "BRIDGE_PAYLOAD_VERSION",
    "UploadBridgePayload",
    "UploadErrorCode",
    "UploadErrorPayload",
    "UploadFilePayload",
    "UploadPayloadError",
    "UploadPayloadJson",
    "UploadResult",
    "UploadSuccessMultiplePayload",
    "UploadSuccessSinglePayload",
    "UploadedFile",
    "parse_upload_payload",
]


class UploadFilePayload(TypedDict):
    """One uploaded file (camelCase keys match the browser bridge JSON)."""

    version: NotRequired[int]
    error: NotRequired[Literal[False]]
    ok: bool
    keyPrefix: str
    storagePath: str
    originalFilename: str
    fileSizeBytes: int
    contentType: str
    publicUrl: NotRequired[str | None]


class UploadErrorPayload(TypedDict):
    version: NotRequired[int]
    error: Literal[True]
    message: str
    code: NotRequired[str]


class UploadSuccessSinglePayload(UploadFilePayload):
    error: Literal[False]


class UploadSuccessMultiplePayload(TypedDict):
    version: int
    error: Literal[False]
    keyPrefix: str
    files: list[UploadFilePayload]


UploadBridgePayload: TypeAlias = (
    UploadErrorPayload | UploadSuccessSinglePayload | UploadSuccessMultiplePayload
)

UploadPayloadJson: TypeAlias = str


class UploadPayloadError(ValueError):
    """Raised when the bridge JSON indicates failure or is invalid."""

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


@dataclass(frozen=True, slots=True)
class UploadedFile:
    """One uploaded file in snake_case for application code."""

    key_prefix: str
    storage_path: str
    original_filename: str
    file_size_bytes: int
    content_type: str
    public_url: str | None

    @classmethod
    def from_payload(
        cls,
        data: UploadFilePayload,
        *,
        fallback_key_prefix: str = "",
    ) -> UploadedFile:
        key_prefix = str(data.get("keyPrefix") or fallback_key_prefix)
        public_raw = data.get("publicUrl")
        return cls(
            key_prefix=key_prefix,
            storage_path=data["storagePath"],
            original_filename=data["originalFilename"],
            file_size_bytes=int(data["fileSizeBytes"]),
            content_type=data["contentType"],
            public_url=public_raw if public_raw else None,
        )


@dataclass(frozen=True, slots=True)
class UploadResult:
    """Parsed successful upload callback."""

    version: int
    key_prefix: str
    files: tuple[UploadedFile, ...]

    @property
    def file(self) -> UploadedFile:
        """Return the only file; raises if zero or multiple files were uploaded."""
        if not self.files:
            raise ValueError("no files uploaded")
        if len(self.files) != 1:
            raise ValueError("expected exactly one uploaded file")
        return self.files[0]


def _file_items(data: dict[str, Any]) -> tuple[list[UploadFilePayload], str]:
    top_prefix = str(data.get("keyPrefix") or "")
    if "files" in data:
        raw = data["files"]
        if not isinstance(raw, list) or not raw:
            raise UploadPayloadError(
                "files 字段无效",
                code=UploadErrorCode.INVALID_PAYLOAD,
            )
        return raw, top_prefix

    if "storagePath" in data:
        return [data], top_prefix or str(data.get("keyPrefix") or "")  # type: ignore[list-item]

    raise UploadPayloadError(
        "缺少 storagePath 或 files",
        code=UploadErrorCode.INVALID_PAYLOAD,
    )


def parse_upload_payload(payload_json: UploadPayloadJson) -> UploadResult:
    """Parse ``on_success`` bridge JSON into :class:`UploadResult`.

    Schema version 1 fields are documented in ``docs/bridge-payload.md``.

    Raises :class:`UploadPayloadError` when JSON is invalid or ``error: true``.
    """
    if not payload_json or not payload_json.strip():
        raise UploadPayloadError("空回调", code=UploadErrorCode.INVALID_PAYLOAD)

    try:
        data: dict[str, Any] = json.loads(payload_json)
    except json.JSONDecodeError as error:
        raise UploadPayloadError(
            "回调数据解析失败",
            code=UploadErrorCode.INVALID_PAYLOAD,
        ) from error

    if not isinstance(data, dict):
        raise UploadPayloadError(
            "回调数据格式无效",
            code=UploadErrorCode.INVALID_PAYLOAD,
        )

    if data.get("error"):
        raise UploadPayloadError(
            str(data.get("message") or "上传失败"),
            code=data.get("code"),
        )

    version = int(data.get("version") or BRIDGE_PAYLOAD_VERSION)

    try:
        items, top_prefix = _file_items(data)
        files = tuple(
            UploadedFile.from_payload(item, fallback_key_prefix=top_prefix)
            for item in items
        )
    except (KeyError, TypeError, ValueError) as error:
        raise UploadPayloadError(
            "回调数据字段不完整",
            code=UploadErrorCode.INVALID_PAYLOAD,
        ) from error

    if not files:
        raise UploadPayloadError(
            "未包含上传文件",
            code=UploadErrorCode.INVALID_PAYLOAD,
        )

    key_prefix = top_prefix or files[0].key_prefix
    return UploadResult(version=version, key_prefix=key_prefix, files=files)
