"""Authenticated upload — per-user key_prefix + presign_guard."""

from __future__ import annotations

import reflex as rx
import reflex_r2_upload as r2
from reflex_r2_demo.demo_auth import (
    DEMO_SESSION_COOKIE,
    DEMO_USERS,
    issue_session_token,
)
from reflex_r2_demo.pages.common import (
    bilingual_text,
    example_shell,
    glb_upload_zone,
    info_callout,
    section_heading,
    upload_result_panel,
)
from reflex_r2_demo.upload_handlers import parse_upload_or_error


class AuthState(rx.State):
    """Demo login state; session cookie is also read by demo_presign_guard."""

    session_token: str = rx.Cookie(name=DEMO_SESSION_COOKIE, path="/", max_age=7200)
    login_message: str = ""
    selected_user: str = DEMO_USERS[0]

    @rx.var(cache=True)
    def user_id(self) -> str:
        from reflex_r2_demo.demo_auth import decode_session_token

        payload = decode_session_token(self.session_token)
        if payload is None:
            return ""
        return str(payload.get("sub", ""))

    @rx.var(cache=True)
    def is_authenticated(self) -> bool:
        return self.user_id != ""

    @rx.var(cache=True)
    def upload_prefix(self) -> str:
        if not self.user_id:
            return ""
        return r2.user_key_prefix(self.user_id, template="uploads/{user_id}")

    @rx.event
    def set_selected_user(self, value: str):
        self.selected_user = value

    @rx.event
    def login(self):
        try:
            self.session_token = issue_session_token(self.selected_user)
        except ValueError as error:
            self.login_message = str(error)
            return
        self.login_message = (
            f"已登录为 {self.selected_user}（Cookie 已写入）"
            f" / Logged in as {self.selected_user} (cookie set)"
        )

    @rx.event
    def logout(self):
        self.session_token = ""
        self.login_message = "已退出登录 / Logged out"


class UploadState(rx.State):
    message: str = "登录后上传 / Upload after login"
    detail: str = (
        "presign_guard 从 Cookie 解析用户，只允许 keyPrefix=uploads/{user_id}。"
        " presign_guard reads the cookie and allows uploads/{user_id} only."
    )
    has_error: bool = False
    last_path: str = ""

    @rx.event
    async def on_uploaded(self, payload_json: r2.UploadPayloadJson):
        auth = await self.get_state(AuthState)
        if not auth.is_authenticated:
            self.has_error = True
            self.message = "未登录 / Not logged in"
            return

        result, err, code = parse_upload_or_error(payload_json)
        if result is None:
            self.has_error = True
            self.message = f"[{code}] {err}" if code else err
            return

        uploaded = result.file
        expected_prefix = auth.upload_prefix
        if not uploaded.storage_path.startswith(expected_prefix + "/"):
            self.has_error = True
            self.message = (
                "storage_path 与当前用户 prefix 不一致"
                " / storage_path does not match the current user prefix"
            )
            return

        self.has_error = False
        self.last_path = uploaded.storage_path
        self.message = f"已上传 / Uploaded: {uploaded.original_filename}"
        self.detail = (
            f"用户 {auth.user_id} · prefix {result.key_prefix} · "
            "HTTP 与 UI 共用同一 Cookie 鉴权。"
            f" User {auth.user_id}; HTTP and UI share the same session cookie."
        )


def _login_panel() -> rx.Component:
    return rx.box(
        section_heading("演示登录", "Demo login"),
        bilingual_text(
            "选择 alice 或 bob 模拟不同用户（非生产方案，无密码）。",
            "Pick alice or bob to simulate users (demo only, no password).",
            class_name="mt-2 text-sm text-gray-600",
        ),
        rx.hstack(
            rx.select(
                DEMO_USERS,
                value=AuthState.selected_user,
                on_change=AuthState.set_selected_user,
                size="2",
            ),
            rx.button(
                rx.vstack(
                    rx.text("登录", class_name="text-sm"),
                    rx.text("Login", class_name="text-xs opacity-80"),
                    spacing="0",
                ),
                on_click=AuthState.login,
                size="2",
            ),
            rx.button(
                rx.vstack(
                    rx.text("退出", class_name="text-sm"),
                    rx.text("Logout", class_name="text-xs opacity-80"),
                    spacing="0",
                ),
                on_click=AuthState.logout,
                size="2",
                variant="outline",
                disabled=~AuthState.is_authenticated,
            ),
            spacing="3",
            class_name="mt-3 flex-wrap",
        ),
        rx.cond(
            AuthState.login_message != "",
            rx.text(AuthState.login_message, class_name="mt-2 text-xs text-gray-500"),
            rx.fragment(),
        ),
        rx.cond(
            AuthState.is_authenticated,
            rx.vstack(
                rx.text(
                    "当前用户：",
                    AuthState.user_id,
                    " · prefix：",
                    AuthState.upload_prefix,
                    class_name="font-mono text-xs text-emerald-700",
                ),
                rx.text(
                    "Current user: ",
                    AuthState.user_id,
                    " · prefix: ",
                    AuthState.upload_prefix,
                    class_name="font-mono text-xs text-gray-500",
                ),
                spacing="1",
                align="start",
                class_name="mt-3",
            ),
            bilingual_text(
                "未登录时无法通过 presign_guard（uploads/ 前缀需 Cookie）。",
                "Without login, presign_guard rejects uploads/ prefixes (cookie required).",
                class_name="mt-3 text-xs text-amber-700",
            ),
        ),
        class_name="rounded-lg border border-gray-200 bg-gray-50 p-4 mt-4",
    )


def _how_it_works() -> rx.Component:
    return rx.box(
        section_heading("实现要点", "How it works"),
        rx.unordered_list(
            rx.list_item(
                bilingual_text(
                    "demo_auth.py：issue_session_token / user_id_from_request",
                    "demo_auth.py: issue_session_token / user_id_from_request",
                    class_name="text-xs text-gray-600",
                ),
            ),
            rx.list_item(
                bilingual_text(
                    "Reflex 层：AuthState.session_token（rx.Cookie）驱动 UI",
                    "Reflex layer: AuthState.session_token (rx.Cookie) drives the UI",
                    class_name="text-xs text-gray-600",
                ),
            ),
            rx.list_item(
                bilingual_text(
                    "HTTP 层：presign_guard 从 Request.cookies 读取同一 token",
                    "HTTP layer: presign_guard reads the same token from Request.cookies",
                    class_name="text-xs text-gray-600",
                ),
            ),
            rx.list_item(
                bilingual_text(
                    "on_success 再次校验 storage_path 是否属于当前用户 prefix",
                    "on_success verifies storage_path belongs to the current user prefix",
                    class_name="text-xs text-gray-600",
                ),
            ),
            class_name="mt-3 list-disc space-y-3 pl-5",
        ),
        class_name="mt-8",
    )


def page() -> rx.Component:
    return example_shell(
        "登录 + 用户隔离上传",
        "Login + per-user isolated upload",
        "AuthState 用 rx.Cookie 保存会话；wrap_app(presign_guard=demo_presign_guard) "
        "在 HTTP 层校验同一 Cookie，确保每人只能写入 uploads/{user_id}/。",
        "AuthState stores the session in rx.Cookie; wrap_app(presign_guard=demo_presign_guard) "
        "validates the same cookie on HTTP routes so each user writes uploads/{user_id}/ only.",
        info_callout(
            "本页演示：alice 只能上传到 uploads/alice/，bob 只能上传到 uploads/bob/；"
            "未登录或伪造 prefix 会在 presign 阶段返回 401。",
            "alice may write uploads/alice/ only; bob uploads/bob/ only. "
            "Missing login or a wrong prefix returns 401 at presign.",
        ),
        _login_panel(),
        rx.cond(
            AuthState.is_authenticated,
            glb_upload_zone(
                key_prefix=AuthState.upload_prefix,
                on_success=UploadState.on_uploaded,
                label_zh="上传到 uploads/{user_id}/（当前用户专属）",
                label_en="Upload to uploads/{user_id}/ (current user only)",
            ),
            rx.box(
                bilingual_text(
                    "请先登录后再显示上传区域。",
                    "Log in to reveal the upload zone.",
                    class_name="text-sm text-gray-500",
                ),
                class_name="mt-4 rounded-lg border border-dashed border-gray-300 p-8 text-center",
            ),
        ),
        upload_result_panel(
            message=UploadState.message,
            detail=UploadState.detail,
            has_error=UploadState.has_error,
            storage_path=UploadState.last_path,
        ),
        _how_it_works(),
    )
