"""Read access helpers for public vs private R2 buckets."""

from __future__ import annotations

from reflex_r2_upload.config import is_public_access_configured
from reflex_r2_upload.storage import create_presigned_get_url, public_url_or_none

__all__ = [
    "create_presigned_get_url",
    "is_public_access_configured",
    "public_url_or_none",
    "signed_read_url",
]


def signed_read_url(
    storage_path: str,
    *,
    expires_in: int | None = None,
) -> str:
    """Return a time-limited presigned GET URL (private bucket pattern).

    Call from server-side Reflex events only — never expose R2 credentials to
  the browser. In production, verify the user may read ``storage_path`` before
    calling this helper.
    """
    return create_presigned_get_url(storage_path, expires_in=expires_in)
