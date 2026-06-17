"""Global upload script + provider wrapper."""

from __future__ import annotations

import reflex as rx

from reflex_r2_upload.upload_zone import UPLOAD_RUNTIME_SCRIPT


def r2_upload_provider(
    *children,
    backend_base: str = "",
    route_prefix: str = "/_reflex_r2_upload",
    presign_expires: int = 600,
    **props,
) -> rx.Component:
    """Wrap page content and inject the browser upload runtime once."""
    return rx.fragment(
        rx.el.script(UPLOAD_RUNTIME_SCRIPT),
        rx.el.div(
            *children,
            data_backend_base=backend_base,
            data_route_prefix=route_prefix.rstrip("/"),
            data_presign_expires=str(presign_expires),
            class_name=props.pop("class_name", None) or "contents",
            **props,
        ),
    )
