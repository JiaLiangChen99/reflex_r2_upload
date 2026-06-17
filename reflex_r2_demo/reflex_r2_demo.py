"""Minimal demo for reflex-r2-upload."""

from __future__ import annotations

import reflex as rx
import reflex_r2_upload as r2
from dotenv import load_dotenv
from reflex_r2_demo.examples_page import examples_page
from reflex_r2_demo.upload_handlers import describe_upload, parse_upload_or_error

load_dotenv()


class State(rx.State):
    message: str = "尚未上传"
    last_path: str = ""
    has_error: bool = False

    @rx.event
    def on_uploaded(self, payload_json: r2.UploadPayloadJson):
        result, err, code = parse_upload_or_error(payload_json)
        if result is None:
            self.has_error = True
            self.message = f"[{code}] {err}" if code else err
            return

        uploaded = result.file
        self.has_error = False
        self.last_path = uploaded.storage_path
        self.message = describe_upload(result)


def index() -> rx.Component:
    return rx.container(
        rx.heading("reflex-r2-upload demo", size="8"),
        rx.text(f"包版本：{r2.__version__}", class_name="text-sm text-gray-500"),
        rx.link(
            "查看更多示例（公开/私有桶、多文件、共享回调）→",
            href="/examples",
            class_name="mt-2 inline-block text-sm text-violet-600",
        ),
        rx.text(
            "请在 .env 中配置 R2 密钥；上传经浏览器直传 Cloudflare R2。",
            class_name="mt-2 text-sm text-gray-600",
        ),
        rx.box(
            r2.upload_zone.root(
                rx.vstack(
                    rx.icon("upload", class_name="h-10 w-10 text-violet-600"),
                    rx.text(
                        "拖放 GLB 文件到此处",
                        class_name="text-sm font-medium text-gray-800",
                    ),
                    rx.text(
                        "或点击选择文件",
                        class_name="text-xs text-gray-500",
                    ),
                    spacing="3",
                    align="center",
                ),
                key_prefix="demo/uploads",
                accept=".glb,model/gltf-binary",
                allowed_extensions=[".glb"],
                content_type="model/gltf-binary",
                on_success=State.on_uploaded,
                class_name=(
                    "w-full rounded-xl border-2 border-dashed border-violet-300 "
                    "bg-violet-50/30 px-6 py-10 text-center transition "
                    "hover:border-violet-400 hover:bg-violet-50/60"
                ),
            ),
            class_name="mt-8 max-w-lg",
        ),
        rx.box(
            rx.text(
                State.message,
                class_name=rx.cond(
                    State.has_error,
                    "mt-4 text-sm text-red-600",
                    "mt-4 text-sm text-emerald-600",
                ),
            ),
            rx.cond(
                State.last_path != "",
                rx.text(
                    "storage_path: ",
                    State.last_path,
                    class_name="mt-2 font-mono text-xs text-gray-500",
                ),
                rx.fragment(),
            ),
            class_name="mt-4",
        ),
        padding="2em",
    )


app = rx.App()
app.add_page(index, route="/")
app.add_page(examples_page, route="/examples")

r2.wrap_app(app)
