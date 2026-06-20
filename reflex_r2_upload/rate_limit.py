"""Simple in-memory rate limiting for upload API routes."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.requests import Request

from reflex_r2_upload.config import rate_limit_requests, rate_limit_window_seconds

_HIT_LOG: dict[str, deque[float]] = defaultdict(deque)


def reset_rate_limit_state() -> None:
    """Clear in-memory counters (for tests)."""
    _HIT_LOG.clear()


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def rate_limit_error(request: Request) -> str | None:
    """Return an error message when the client exceeded the rate limit."""
    limit = rate_limit_requests()
    window = rate_limit_window_seconds()
    if limit <= 0 or window <= 0:
        return None

    now = time.monotonic()
    ip = client_ip(request)
    hits = _HIT_LOG[ip]
    cutoff = now - window
    while hits and hits[0] <= cutoff:
        hits.popleft()

    if len(hits) >= limit:
        return "请求过于频繁，请稍后再试"

    hits.append(now)
    return None
