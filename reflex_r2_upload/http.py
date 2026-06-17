"""Minimal JSON helpers for Starlette routes."""

from __future__ import annotations

import json
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse, Response


async def read_json(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
    except (json.JSONDecodeError, ValueError):
        return {}
    return body if isinstance(body, dict) else {}


def ok(data: dict[str, Any], *, status_code: int = 200) -> JSONResponse:
    return JSONResponse(data, status_code=status_code)


def fail(detail: str, *, status_code: int = 400) -> JSONResponse:
    return JSONResponse({"detail": detail}, status_code=status_code)


def require_fields(data: dict[str, Any], *names: str) -> str | None:
    for name in names:
        value = data.get(name)
        if value is None or (isinstance(value, str) and not value.strip()):
            return f"缺少字段：{name}"
    return None
