"""App-level integration (wrap_app, api_transformer chaining)."""

from __future__ import annotations

from collections.abc import Callable, Sequence

import reflex as rx
from starlette.applications import Starlette
from starlette.types import ASGIApp

from reflex_r2_upload.config import R2Config, configure_r2, route_prefix as env_route_prefix
from reflex_r2_upload.provider import r2_upload_provider
from reflex_r2_upload.routes import create_upload_api

_API_TRANSFORMER = Callable[[ASGIApp], ASGIApp] | Starlette


def _chain_api_transformer(
    existing: Sequence[_API_TRANSFORMER] | _API_TRANSFORMER | None,
    new_api: Starlette,
) -> Sequence[_API_TRANSFORMER] | _API_TRANSFORMER:
    if existing is None:
        return new_api
    if isinstance(existing, Sequence) and not isinstance(existing, (str, bytes)):
        return [*existing, new_api]
    return [existing, new_api]


def wrap_app(
    app: rx.App,
    *,
    r2_config: R2Config | None = None,
    backend_base: str = "",
    route_prefix: str | None = None,
    presign_expires: int | None = None,
) -> rx.App:
    """Enable R2 browser uploads for the entire Reflex app."""
    if r2_config is not None:
        configure_r2(r2_config)

    prefix = route_prefix if route_prefix is not None else env_route_prefix()
    upload_api = create_upload_api(prefix=prefix)

    app.app_wraps[(1, "R2UploadProvider")] = lambda _: r2_upload_provider(
        backend_base=backend_base,
        route_prefix=prefix,
        presign_expires=presign_expires or 600,
    )
    app.api_transformer = _chain_api_transformer(app.api_transformer, upload_api)
    return app
