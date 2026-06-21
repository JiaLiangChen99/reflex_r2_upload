"""Multi-file upload example."""

from __future__ import annotations

import reflex as rx
import reflex_r2_upload as r2
from reflex_r2_demo.pages.common import example_shell, glb_upload_zone, info_callout, upload_result_panel
from reflex_r2_demo.upload_handlers import describe_multi_upload, parse_upload_or_error


class State(rx.State):
    message: str = "尚未上传 / No upload yet"
    detail: str = "可选择多个 .glb 文件。 / Select multiple .glb files."
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

        self.has_error = False
        self.last_path = result.files[0].storage_path
        self.message = describe_multi_upload(result)
        self.detail = (
            f"共 {len(result.files)} 个文件；用 result.files 遍历。"
            f" {len(result.files)} file(s); iterate result.files in your handler."
        )


def page() -> rx.Component:
    return example_shell(
        "多文件上传",
        "Multi-file upload",
        "upload_zone 设置 multiple=True，一次选择多个文件依次直传 R2。",
        "Set multiple=True on upload_zone; each file uploads to R2 in sequence.",
        info_callout(
            "多文件时 bridge JSON 使用 files[] 结构，而非单文件的扁平字段。",
            "Multi-file bridge JSON uses a files[] array instead of flat single-file fields.",
        ),
        glb_upload_zone(
            key_prefix="demo/multi/uploads",
            on_success=State.on_uploaded,
            label_zh="多选 .glb 文件",
            label_en="Select multiple .glb files",
            multiple=True,
        ),
        upload_result_panel(
            message=State.message,
            detail=State.detail,
            has_error=State.has_error,
            storage_path=State.last_path,
        ),
    )
