"""Shared layout and upload UI helpers for demo pages."""

from __future__ import annotations

import reflex as rx
import reflex_r2_upload as r2


def back_home() -> rx.Component:
    return rx.link(
        rx.vstack(
            rx.text("← 返回示例首页", class_name="text-sm"),
            rx.text("← Back to examples", class_name="text-xs text-gray-500"),
            spacing="0",
            align="start",
        ),
        href="/",
        class_name="text-violet-600 no-underline",
    )


def bilingual_heading(zh: str, en: str, *, size: str = "7") -> rx.Component:
    return rx.vstack(
        rx.heading(zh, size=size),
        rx.text(en, class_name="text-sm font-normal text-gray-500"),
        spacing="1",
        align="start",
        class_name="w-full",
    )


def bilingual_text(
    zh: str,
    en: str,
    *,
    class_name: str = "text-sm text-gray-600",
) -> rx.Component:
    return rx.vstack(
        rx.text(zh, class_name=class_name),
        rx.text(en, class_name=f"{class_name} text-gray-500"),
        spacing="1",
        align="start",
        class_name="w-full",
    )


def info_callout(zh: str, en: str) -> rx.Component:
    """Highlighted bilingual note box."""
    return rx.box(
        bilingual_text(zh, en, class_name="text-sm text-gray-700"),
        class_name="rounded-lg border border-violet-100 bg-violet-50/60 p-4",
    )


def section_heading(zh: str, en: str) -> rx.Component:
    return bilingual_heading(zh, en, size="4")


def example_shell(
    title_zh: str,
    title_en: str,
    desc_zh: str,
    desc_en: str,
    callout: rx.Component | None = None,
    *children: rx.Component,
    badge: rx.Component | None = None,
) -> rx.Component:
    header: list[rx.Component] = [
        back_home(),
        rx.badge("中文 / EN", color_scheme="gray", variant="soft", class_name="mt-4"),
        bilingual_heading(title_zh, title_en, size="7"),
        bilingual_text(desc_zh, desc_en, class_name="mt-2 text-sm text-gray-600"),
    ]
    if callout is not None:
        header.append(rx.box(callout, class_name="mt-4"))
    if badge is not None:
        header.append(rx.box(badge, class_name="mt-3"))
    return rx.container(
        *header,
        *children,
        padding="2em",
        max_width="48rem",
    )


def glb_upload_zone(
    *,
    key_prefix: str | rx.Var,
    on_success: rx.EventHandler,
    label_zh: str = "拖放或点击选择 .glb 文件",
    label_en: str = "Drag & drop or click to select a .glb file",
    multiple: bool = False,
    class_name: str = "",
) -> rx.Component:
    zone_class = (
        "mt-4 w-full rounded-lg border border-dashed border-gray-300 "
        "px-4 py-6 text-center hover:border-violet-300"
    )
    return rx.box(
        r2.upload_zone.root(
            rx.vstack(
                rx.text(label_zh, class_name="text-sm font-medium"),
                rx.text(label_en, class_name="text-xs text-gray-500"),
                spacing="1",
                align="center",
            ),
            key_prefix=key_prefix,
            accept=".glb,model/gltf-binary",
            allowed_extensions=[".glb"],
            content_type="model/gltf-binary",
            on_success=on_success,
            multiple=multiple,
            class_name=zone_class,
        ),
        class_name=class_name,
    )


def upload_result_panel(
    *,
    message: rx.Var,
    detail: rx.Var,
    has_error: rx.Var,
    storage_path: rx.Var = "",
    extra: rx.Component | None = None,
) -> rx.Component:
    return rx.box(
        rx.text(
            message,
            class_name=rx.cond(
                has_error,
                "mt-6 text-sm text-red-600",
                "mt-6 text-sm text-emerald-700",
            ),
        ),
        rx.cond(
            detail != "",
            rx.text(detail, class_name="mt-2 text-xs text-gray-500"),
            rx.fragment(),
        ),
        rx.cond(
            storage_path != "",
            rx.text(
                "storage_path: ",
                storage_path,
                class_name="mt-2 font-mono text-xs text-gray-500 break-all",
            ),
            rx.fragment(),
        ),
        extra if extra is not None else rx.fragment(),
        class_name="mt-2",
    )
