"""Extended examples: public vs private bucket, multi-file, shared handler."""

from __future__ import annotations

import reflex as rx
import reflex_r2_upload as r2
from reflex_r2_demo.upload_handlers import (
    describe_multi_upload,
    describe_upload,
    parse_upload_or_error,
    signed_url_for_storage,
)


class ExamplesState(rx.State):
    """Patterns demonstrated on /examples."""

    message: str = "选择一个示例上传区"
    detail: str = ""
    has_error: bool = False
    last_path: str = ""
    last_key_prefix: str = ""
    access_mode: str = ""  # public | private
    public_url: str = ""
    signed_read_url: str = ""
    is_public_bucket: bool = r2.is_public_access_configured()

    @rx.event
    def on_single_uploaded(self, payload_json: r2.UploadPayloadJson):
        """Example 1 & 2: single file; branch on ``public_url``."""
        result, err, code = parse_upload_or_error(payload_json)
        if result is None:
            self._set_error(err, code)
            return

        uploaded = result.file
        self._set_success(uploaded.storage_path, result.key_prefix)
        self.message = describe_upload(result)
        if uploaded.public_url:
            self.access_mode = "public"
            self.public_url = uploaded.public_url
            self.signed_read_url = ""
            self.detail = "公开桶：直接使用 publicUrl 展示或下载。"
        else:
            self.access_mode = "private"
            self.public_url = ""
            self.signed_read_url = ""
            self.detail = "私有桶：publicUrl 为 null，点击下方按钮生成临时读链接。"

    @rx.event
    def on_multi_uploaded(self, payload_json: r2.UploadPayloadJson):
        """Example 3: ``multiple=True`` multi-file upload."""
        result, err, code = parse_upload_or_error(payload_json)
        if result is None:
            self._set_error(err, code)
            return

        self.has_error = False
        self.last_path = result.files[0].storage_path
        self.last_key_prefix = result.key_prefix
        self.message = describe_multi_upload(result)
        self.detail = "多文件时 bridge 返回 files[]；用 result.files 遍历。"
        self.access_mode = "private" if not result.files[0].public_url else "public"

    @rx.event
    def on_shared_handler_uploaded(self, payload_json: r2.UploadPayloadJson):
        """Example 4: one handler, multiple zones — use ``result.key_prefix``."""
        result, err, code = parse_upload_or_error(payload_json)
        if result is None:
            self._set_error(err, code)
            return

        uploaded = result.file
        self._set_success(uploaded.storage_path, result.key_prefix)
        self.message = f"共享回调：prefix={result.key_prefix} file={uploaded.original_filename}"
        self.detail = "同一 on_success 可根据 key_prefix 分流到不同业务逻辑。"
        self.access_mode = "public" if uploaded.public_url else "private"

    @rx.event
    def generate_signed_read_url(self):
        """Private bucket: server-side presigned GET (demo only — add auth in prod)."""
        if not self.last_path or not self.last_key_prefix:
            self.detail = "请先上传文件"
            return
        try:
            self.signed_read_url = signed_url_for_storage(self.last_path)
            self.detail = "已生成 presigned GET（限时）。生产环境请先校验用户读权限。"
        except RuntimeError as error:
            self._set_error(str(error), None)

    def _set_error(self, message: str, code: str | None) -> None:
        self.has_error = True
        self.message = f"[{code}] {message}" if code else message
        self.detail = ""

    def _set_success(self, storage_path: str, key_prefix: str) -> None:
        self.has_error = False
        self.last_path = storage_path
        self.last_key_prefix = key_prefix


def examples_page() -> rx.Component:
    return rx.container(
        rx.link("← 返回首页", href="/", class_name="text-sm text-violet-600"),
        rx.heading("上传模式示例", size="7", class_name="mt-4"),
        rx.hstack(
            rx.badge(
                rx.cond(
                    ExamplesState.is_public_bucket,
                    "R2_PUBLIC_BASE_URL 已配置（公开 CDN 模式）",
                    "未配置 R2_PUBLIC_BASE_URL（私有桶模式）",
                ),
                color_scheme=rx.cond(ExamplesState.is_public_bucket, "green", "orange"),
            ),
            class_name="mt-2",
        ),
        rx.text(ExamplesState.message, class_name="mt-4 text-sm"),
        rx.text(ExamplesState.detail, class_name="mt-2 text-xs text-gray-500"),
        rx.cond(
            ExamplesState.access_mode == "public",
            rx.link(
                "打开 publicUrl",
                href=ExamplesState.public_url,
                is_external=True,
                class_name="mt-2 block text-sm text-violet-600",
            ),
            rx.fragment(),
        ),
        rx.cond(
            ExamplesState.access_mode == "private",
            rx.vstack(
                rx.button(
                    "生成 presigned GET（私有桶读）",
                    on_click=ExamplesState.generate_signed_read_url,
                    size="2",
                ),
                rx.cond(
                    ExamplesState.signed_read_url != "",
                    rx.link(
                        "打开临时读链接",
                        href=ExamplesState.signed_read_url,
                        is_external=True,
                        class_name="text-sm text-violet-600 break-all",
                    ),
                    rx.fragment(),
                ),
                spacing="2",
                align="start",
                class_name="mt-2",
            ),
            rx.fragment(),
        ),
        rx.separator(class_name="my-8"),
        rx.heading("1. 单文件上传", size="4"),
        rx.text("公开/私有由是否配置 R2_PUBLIC_BASE_URL 决定", class_name="text-xs text-gray-500"),
        _zone(
            key_prefix="demo/examples/single",
            on_success=ExamplesState.on_single_uploaded,
            label="单文件 .glb",
        ),
        rx.separator(class_name="my-8"),
        rx.heading("2. 多文件上传", size="4"),
        _zone(
            key_prefix="demo/examples/multi",
            on_success=ExamplesState.on_multi_uploaded,
            label="多选 .glb",
            multiple=True,
        ),
        rx.separator(class_name="my-8"),
        rx.heading("3. 共享回调 + 不同 key_prefix", size="4"),
        rx.hstack(
            _zone(
                key_prefix="demo/examples/zone-a",
                on_success=ExamplesState.on_shared_handler_uploaded,
                label="Zone A",
                class_name="flex-1",
            ),
            _zone(
                key_prefix="demo/examples/zone-b",
                on_success=ExamplesState.on_shared_handler_uploaded,
                label="Zone B",
                class_name="flex-1",
            ),
            spacing="4",
            class_name="w-full",
        ),
        padding="2em",
        max_width="48rem",
    )


def _zone(
    *,
    key_prefix: str,
    on_success,
    label: str,
    multiple: bool = False,
    class_name: str = "",
) -> rx.Component:
    return rx.box(
        r2.upload_zone.root(
            rx.text(label, class_name="text-sm font-medium"),
            key_prefix=key_prefix,
            accept=".glb,model/gltf-binary",
            allowed_extensions=[".glb"],
            content_type="model/gltf-binary",
            on_success=on_success,
            multiple=multiple,
            class_name=(
                "mt-2 w-full rounded-lg border border-dashed border-gray-300 "
                "px-4 py-6 text-center hover:border-violet-300"
            ),
        ),
        class_name=class_name,
    )
