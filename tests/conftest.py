"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from reflex_r2_upload.config import configure_rate_limit, configure_upload_limits
from reflex_r2_upload.rate_limit import reset_rate_limit_state


@pytest.fixture(autouse=True)
def relaxed_upload_limits():
    """Disable rate limits and upload-size caps unless a test overrides them."""
    from reflex_r2_upload.config import configure_verbose_config

    configure_rate_limit(requests=0, window_seconds=60)
    configure_upload_limits(max_upload_bytes=0)
    configure_verbose_config(None)
    reset_rate_limit_state()
    yield
    configure_rate_limit(requests=0, window_seconds=60)
    configure_upload_limits(max_upload_bytes=0)
    configure_verbose_config(None)
    reset_rate_limit_state()
