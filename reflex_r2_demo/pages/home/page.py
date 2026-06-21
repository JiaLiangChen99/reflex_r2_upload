"""Demo home page — links to each example."""

from __future__ import annotations

import reflex as rx
import reflex_r2_upload as r2

from reflex_r2_demo.pages.common import bilingual_heading, bilingual_text


def _example_card(
    *,
    href: str,
    title_zh: str,
    title_en: str,
    desc_zh: str,
    desc_en: str,
    tag_zh: str,
    tag_en: str,
) -> rx.Component:
    return rx.link(
        rx.box(
            rx.hstack(
                rx.vstack(
                    rx.heading(title_zh, size="4"),
                    rx.text(title_en, class_name="text-sm font-normal text-gray-500"),
                    spacing="0",
                    align="start",
                ),
                rx.vstack(
                    rx.badge(tag_zh, color_scheme="violet", variant="soft"),
                    rx.badge(tag_en, color_scheme="gray", variant="outline"),
                    spacing="1",
                    align="end",
                ),
                justify="between",
                align="start",
                class_name="w-full",
            ),
            bilingual_text(
                desc_zh,
                desc_en,
                class_name="mt-3 text-sm text-gray-600",
            ),
            class_name=(
                "block rounded-xl border border-gray-200 bg-white p-5 "
                "transition hover:border-violet-300 hover:shadow-sm"
            ),
        ),
        href=href,
        class_name="no-underline text-inherit",
    )


def page() -> rx.Component:
    return rx.container(
        rx.badge("中文 / EN", color_scheme="gray", variant="soft"),
        bilingual_heading(
            "reflex-r2-upload 示例",
            "reflex-r2-upload Examples",
            size="8",
        ),
        bilingual_text(
            f"库版本 {r2.__version__} · 请在 .env 中配置 R2 凭证",
            f"Library v{r2.__version__} · Configure R2 credentials in .env",
            class_name="mt-2 text-sm text-gray-500",
        ),
        bilingual_text(
            "每个示例独立页面，UI 与 State 位于 pages/<name>/page.py；"
            "上传经浏览器直传 Cloudflare R2。",
            "Each example lives in pages/<name>/page.py (UI + State). "
            "Files upload directly from the browser to Cloudflare R2.",
            class_name="mt-2 text-sm text-gray-600",
        ),
        rx.vstack(
            _example_card(
                href="/examples/basic",
                title_zh="基础单文件上传",
                title_en="Basic single-file upload",
                desc_zh="最小 upload_zone + parse_upload_payload，开放 demo/ 前缀。",
                desc_en="Minimal upload_zone + parse_upload_payload; open demo/ prefix.",
                tag_zh="入门",
                tag_en="Starter",
            ),
            _example_card(
                href="/examples/multi",
                title_zh="多文件上传",
                title_en="Multi-file upload",
                desc_zh="multiple=True，bridge 返回 files[]。",
                desc_en="multiple=True; bridge payload returns files[].",
                tag_zh="多文件",
                tag_en="Multi",
            ),
            _example_card(
                href="/examples/shared-callback",
                title_zh="共享回调",
                title_en="Shared callback",
                desc_zh="两个上传区、同一 on_success，用 key_prefix 分流。",
                desc_en="Two zones, one on_success handler; route by key_prefix.",
                tag_zh="模式",
                tag_en="Pattern",
            ),
            _example_card(
                href="/examples/private-read",
                title_zh="公开 / 私有读",
                title_en="Public / private read",
                desc_zh="根据 R2_PUBLIC_BASE_URL 区分 publicUrl 与 presigned GET。",
                desc_en="publicUrl vs presigned GET depending on R2_PUBLIC_BASE_URL.",
                tag_zh="访问控制",
                tag_en="Access",
            ),
            _example_card(
                href="/examples/auth",
                title_zh="登录 + 用户隔离",
                title_en="Login + per-user isolation",
                desc_zh="Cookie 会话 + presign_guard，每人只能写入 uploads/{user_id}/。",
                desc_en="Cookie session + presign_guard; each user writes uploads/{user_id}/ only.",
                tag_zh="鉴权",
                tag_en="Auth",
            ),
            spacing="4",
            class_name="mt-8 w-full max-w-2xl",
        ),
        padding="2em",
    )
