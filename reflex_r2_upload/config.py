"""Runtime configuration for reflex-r2-upload (environment variables or ``R2Config``)."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_ROUTE_PREFIX = "/_reflex_r2_upload"
DEFAULT_PRESIGN_EXPIRES = 600
DEFAULT_GET_EXPIRES = 3600

R2_ENV_KEYS = (
    "R2_ACCOUNT_ID",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_BUCKET_NAME",
)

_runtime: R2Config | None = None


@dataclass(frozen=True, slots=True)
class R2Config:
    """Cloudflare R2 credentials and options (pass to ``wrap_app(r2_config=...)``)."""

    account_id: str
    access_key_id: str
    secret_access_key: str
    bucket_name: str
    public_base_url: str = ""
    presign_expires: int = DEFAULT_PRESIGN_EXPIRES
    get_expires: int = DEFAULT_GET_EXPIRES
    route_prefix: str = DEFAULT_ROUTE_PREFIX


def configure_r2(config: R2Config | None) -> None:
    """Set R2 credentials in process memory (``None`` clears runtime override)."""
    global _runtime
    _runtime = config
    try:
        from reflex_r2_upload.storage import clear_r2_client_cache

        clear_r2_client_cache()
    except ImportError:
        pass


def _runtime_or_env(attr: str, env_key: str) -> str:
    if _runtime is not None:
        return str(getattr(_runtime, attr)).strip()
    return os.environ.get(env_key, "").strip()


def account_id() -> str:
    return _runtime_or_env("account_id", "R2_ACCOUNT_ID")


def access_key_id() -> str:
    return _runtime_or_env("access_key_id", "R2_ACCESS_KEY_ID")


def secret_access_key() -> str:
    return _runtime_or_env("secret_access_key", "R2_SECRET_ACCESS_KEY")


def bucket_name() -> str:
    return _runtime_or_env("bucket_name", "R2_BUCKET_NAME")


def missing_r2_env() -> list[str]:
    """Return names of missing required settings (env var names for messages)."""
    pairs = (
        ("account_id", "R2_ACCOUNT_ID"),
        ("access_key_id", "R2_ACCESS_KEY_ID"),
        ("secret_access_key", "R2_SECRET_ACCESS_KEY"),
        ("bucket_name", "R2_BUCKET_NAME"),
    )
    return [env_key for attr, env_key in pairs if not _runtime_or_env(attr, env_key)]


def ensure_r2_config() -> None:
    missing = missing_r2_env()
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(
            f"缺少 R2 配置：{joined}。"
            "请设置对应环境变量，或调用 wrap_app(r2_config=R2Config(...))。"
        )


def public_base_url() -> str:
    value = _runtime_or_env("public_base_url", "R2_PUBLIC_BASE_URL")
    return value.rstrip("/")


def presign_expires() -> int:
    if _runtime is not None:
        return max(60, int(_runtime.presign_expires))
    raw = os.environ.get("REFLEX_R2_PRESIGN_EXPIRES", "").strip()
    if not raw:
        return DEFAULT_PRESIGN_EXPIRES
    try:
        return max(60, int(raw))
    except ValueError:
        return DEFAULT_PRESIGN_EXPIRES


def get_expires() -> int:
    if _runtime is not None:
        return max(60, int(_runtime.get_expires))
    raw = os.environ.get("REFLEX_R2_GET_EXPIRES", "").strip()
    if not raw:
        return DEFAULT_GET_EXPIRES
    try:
        return max(60, int(raw))
    except ValueError:
        return DEFAULT_GET_EXPIRES


def is_public_access_configured() -> bool:
    return bool(public_base_url())


def route_prefix() -> str:
    if _runtime is not None and _runtime.route_prefix:
        return _runtime.route_prefix.rstrip("/") or DEFAULT_ROUTE_PREFIX
    for key in ("REFLEX_R2_ROUTE_PREFIX", "REFLEX_R2_API_PREFIX"):
        value = os.environ.get(key, "").strip()
        if value:
            return value.rstrip("/")
    return DEFAULT_ROUTE_PREFIX
