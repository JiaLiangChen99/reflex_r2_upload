"""Public CDN vs private bucket read access."""

from __future__ import annotations

import reflex as rx
import reflex_r2_upload as r2
from reflex_r2_demo.pages.common import example_shell, glb_upload_zone, info_callout, upload_result_panel
from reflex_r2_demo.upload_handlers import (
    describe_upload,
    parse_upload_or_error,
    signed_url_for_storage,
)


class State(rx.State):
    message: str = "尚未上传 / No upload yet"
    detail: str = ""
    has_error: bool = False
    last_path: str = ""
    access_mode: str = ""
    public_url: str = ""
    signed_read_url: str = ""
    is_public_bucket: bool = r2.is_public_access_configured()

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
        self.public_url = uploaded.public_url or ""
        self.signed_read_url = ""

        if uploaded.public_url:
            self.access_mode = "public"
            self.detail = (
                "公开桶：bridge 含 publicUrl，可直接链接访问。"
                " Public bucket: bridge includes publicUrl for direct access."
            )
        else:
            self.access_mode = "private"
            self.detail = (
                "私有桶：publicUrl 为 null，点击下方生成 presigned GET。"
                " Private bucket: publicUrl is null; generate presigned GET below."
            )

    @rx.event
    def generate_signed_read_url(self):
        if not self.last_path:
            self.detail = "请先上传文件 / Upload a file first"
            return
        try:
            self.signed_read_url = signed_url_for_storage(self.last_path)
            self.detail = (
                "已生成限时读链接（演示用；生产环境须先校验读权限）。"
                " Temporary read URL issued (demo only; authorize reads in production)."
            )
        except RuntimeError as error:
            self.has_error = True
            self.message = str(error)


def _read_access_panel() -> rx.Component:
    return rx.box(
        rx.cond(
            State.access_mode == "public",
            rx.link(
                rx.vstack(
                    rx.text("打开 publicUrl", class_name="text-sm"),
                    rx.text("Open publicUrl", class_name="text-xs text-gray-500"),
                    spacing="0",
                    align="start",
                ),
                href=State.public_url,
                is_external=True,
                class_name="text-violet-600 break-all no-underline",
            ),
            rx.fragment(),
        ),
        rx.cond(
            State.access_mode == "private",
            rx.vstack(
                rx.button(
                    rx.vstack(
                        rx.text("生成 presigned GET（私有桶读）", class_name="text-sm"),
                        rx.text(
                            "Generate presigned GET (private bucket)",
                            class_name="text-xs opacity-80",
                        ),
                        spacing="0",
                    ),
                    on_click=State.generate_signed_read_url,
                    size="2",
                ),
                rx.cond(
                    State.signed_read_url != "",
                    rx.link(
                        rx.vstack(
                            rx.text("打开临时读链接", class_name="text-sm"),
                            rx.text("Open temporary read URL", class_name="text-xs text-gray-500"),
                            spacing="0",
                            align="start",
                        ),
                        href=State.signed_read_url,
                        is_external=True,
                        class_name="text-violet-600 break-all no-underline",
                    ),
                    rx.fragment(),
                ),
                spacing="2",
                align="start",
            ),
            rx.fragment(),
        ),
        class_name="mt-4",
    )


def page() -> rx.Component:
    return example_shell(
        "公开 / 私有读",
        "Public / private read",
        "是否配置 R2_PUBLIC_BASE_URL 决定 bridge 中的 publicUrl；"
        "私有桶在 Reflex 事件中调用 signed_read_url()。",
        "R2_PUBLIC_BASE_URL controls publicUrl in the bridge; "
        "call signed_read_url() in Reflex events for private buckets.",
        info_callout(
            "上传后的读访问：公开 CDN 直接用 URL，私有桶需服务端签发临时 GET。",
            "After upload: public CDN URLs vs server-issued presigned GET for private buckets.",
        ),
        glb_upload_zone(
            key_prefix="demo/private-read/uploads",
            on_success=State.on_uploaded,
        ),
        upload_result_panel(
            message=State.message,
            detail=State.detail,
            has_error=State.has_error,
            storage_path=State.last_path,
            extra=_read_access_panel(),
        ),
        badge=rx.vstack(
            rx.badge(
                rx.cond(
                    State.is_public_bucket,
                    "R2_PUBLIC_BASE_URL 已配置（公开 CDN）",
                    "未配置 R2_PUBLIC_BASE_URL（私有桶）",
                ),
                color_scheme=rx.cond(State.is_public_bucket, "green", "orange"),
            ),
            rx.badge(
                rx.cond(
                    State.is_public_bucket,
                    "R2_PUBLIC_BASE_URL set (public CDN)",
                    "R2_PUBLIC_BASE_URL not set (private bucket)",
                ),
                color_scheme="gray",
                variant="outline",
            ),
            spacing="2",
            align="start",
        ),
    )
