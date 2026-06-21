"""Basic single-file upload example."""

from __future__ import annotations

import reflex as rx
import reflex_r2_upload as r2
from reflex_r2_demo.pages.common import example_shell, glb_upload_zone, info_callout, upload_result_panel
from reflex_r2_demo.upload_handlers import describe_upload, parse_upload_or_error


class State(rx.State):
    message: str = "尚未上传 / No upload yet"
    detail: str = (
        "开放前缀 demo/basic/uploads，无需登录。"
        " Open prefix demo/basic/uploads; no login required."
    )
    has_error: bool = False
    last_path: str = ""

    @rx.event
    def on_uploaded(self, payload_json: r2.UploadPayloadJson):
        result, err, code = parse_upload_or_error(payload_json)
        if result is None:
            self.has_error = True
            self.message = f"[{code}] {err}" if code else err
            self.detail = ""
            return

        uploaded = result.file
        self.has_error = False
        self.last_path = uploaded.storage_path
        self.message = describe_upload(result)
        self.detail = (
            "presign_guard 允许 demo/ 前缀，无需 Cookie。"
            " presign_guard allows demo/ prefixes without a session cookie."
        )


def page() -> rx.Component:
    return example_shell(
        "基础单文件上传",
        "Basic single-file upload",
        "拖放或选择 GLB 文件。适合作为接入 reflex-r2-upload 的最小模板。",
        "Drag or select a GLB file. Minimal template to integrate reflex-r2-upload.",
        info_callout(
            "展示 upload_zone、wrap_app 与 parse_upload_payload 的最小闭环。",
            "Shows the smallest loop: upload_zone, wrap_app, and parse_upload_payload.",
        ),
        glb_upload_zone(
            key_prefix="demo/basic/uploads",
            on_success=State.on_uploaded,
        ),
        upload_result_panel(
            message=State.message,
            detail=State.detail,
            has_error=State.has_error,
            storage_path=State.last_path,
        ),
    )
