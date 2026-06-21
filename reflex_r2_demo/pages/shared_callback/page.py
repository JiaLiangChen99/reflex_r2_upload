"""Shared on_success handler across multiple upload zones."""

from __future__ import annotations

import reflex as rx
import reflex_r2_upload as r2
from reflex_r2_demo.pages.common import example_shell, glb_upload_zone, info_callout, upload_result_panel
from reflex_r2_demo.upload_handlers import parse_upload_or_error


class State(rx.State):
    message: str = "任选一个区域上传 / Upload from either zone"
    detail: str = (
        "同一 handler 根据 result.key_prefix 区分来源。"
        " One handler; distinguish zones via result.key_prefix."
    )
    has_error: bool = False
    last_path: str = ""
    last_key_prefix: str = ""

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
        self.last_key_prefix = result.key_prefix
        self.message = (
            f"共享回调：prefix={result.key_prefix} file={uploaded.original_filename}"
        )
        self.detail = (
            "可将不同 prefix 映射到不同业务表或目录策略。"
            " Map each prefix to different tables or storage policies."
        )


def page() -> rx.Component:
    return example_shell(
        "共享回调 + 不同 key_prefix",
        "Shared callback + different key_prefix",
        "两个上传区绑定同一个 on_success，在 handler 里用 key_prefix 分流。",
        "Two upload zones share one on_success; branch logic on key_prefix.",
        info_callout(
            "同一页面多个 upload_zone 可复用一个 Python 回调，减少重复代码。",
            "Multiple upload_zone components can share one Python callback on the same page.",
        ),
        rx.hstack(
            glb_upload_zone(
                key_prefix="demo/shared/zone-a",
                on_success=State.on_uploaded,
                label_zh="区域 A",
                label_en="Zone A",
                class_name="flex-1",
            ),
            glb_upload_zone(
                key_prefix="demo/shared/zone-b",
                on_success=State.on_uploaded,
                label_zh="区域 B",
                label_en="Zone B",
                class_name="flex-1",
            ),
            spacing="4",
            class_name="w-full",
        ),
        upload_result_panel(
            message=State.message,
            detail=State.detail,
            has_error=State.has_error,
            storage_path=State.last_path,
            extra=rx.cond(
                State.last_key_prefix != "",
                rx.text(
                    "key_prefix: ",
                    State.last_key_prefix,
                    class_name="mt-1 font-mono text-xs text-gray-500",
                ),
                rx.fragment(),
            ),
        ),
    )
