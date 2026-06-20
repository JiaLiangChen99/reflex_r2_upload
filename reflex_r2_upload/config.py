"""Runtime configuration for reflex-r2-upload (environment variables or ``R2Config``)."""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass

DEFAULT_ROUTE_PREFIX = "/_reflex_r2_upload"
DEFAULT_PRESIGN_EXPIRES = 600
DEFAULT_GET_EXPIRES = 3600
DEFAULT_UPLOAD_TOKEN_TTL = 7200
DEFAULT_MAX_UPLOAD_BYTES = 100 * 1024 * 1024
DEFAULT_RATE_LIMIT_REQUESTS = 60
DEFAULT_RATE_LIMIT_WINDOW = 60
MIN_GET_EXPIRES = 60

R2_ENV_KEYS = (
    "R2_ACCOUNT_ID",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_BUCKET_NAME",
)

_require_upload_token_override: bool | None = None
_require_bridge_signature_override: bool | None = None
_verbose_config_override: bool | None = None
_rate_limit_requests_override: int | None = None
_rate_limit_window_override: int | None = None
_max_upload_bytes_override: int | None = None
_allowed_key_prefixes: frozenset[str] | None = None
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
    upload_secret: str = ""
    require_upload_token: bool = True
    upload_token_ttl: int = DEFAULT_UPLOAD_TOKEN_TTL
    require_bridge_signature: bool = True
    allowed_key_prefixes: tuple[str, ...] = ()
    max_upload_bytes: int = DEFAULT_MAX_UPLOAD_BYTES
    rate_limit_requests: int = DEFAULT_RATE_LIMIT_REQUESTS
    rate_limit_window_seconds: int = DEFAULT_RATE_LIMIT_WINDOW
    verbose_config: bool = False


def configure_r2(config: R2Config | None) -> None:
    """Set R2 credentials in process memory (``None`` clears runtime override)."""
    global _runtime
    _runtime = config
    if config is not None and config.allowed_key_prefixes:
        configure_allowed_key_prefixes(config.allowed_key_prefixes)
    elif config is None:
        configure_allowed_key_prefixes(None)
    try:
        from reflex_r2_upload.storage import clear_r2_client_cache

        clear_r2_client_cache()
    except ImportError:
        pass


def configure_allowed_key_prefixes(prefixes: Sequence[str] | None) -> None:
    """Restrict API ``keyPrefix`` values to an explicit allowlist (``None`` clears)."""
    global _allowed_key_prefixes
    if prefixes is None:
        _allowed_key_prefixes = None
        return

    from reflex_r2_upload.keys import normalize_prefix

    _allowed_key_prefixes = frozenset(
        normalize_prefix(prefix) for prefix in prefixes if str(prefix).strip()
    )


def is_key_prefix_allowed(key_prefix: str) -> bool:
    """Return whether ``key_prefix`` is permitted by the configured allowlist."""
    if _allowed_key_prefixes is None:
        if _runtime is not None and _runtime.allowed_key_prefixes:
            configure_allowed_key_prefixes(_runtime.allowed_key_prefixes)
        else:
            return True

    if _allowed_key_prefixes is None:
        return True

    from reflex_r2_upload.keys import normalize_prefix

    try:
        return normalize_prefix(key_prefix) in _allowed_key_prefixes
    except ValueError:
        return False


def configure_upload_auth(
    *,
    require_upload_token: bool | None = None,
    require_bridge_signature: bool | None = None,
) -> None:
    """Override upload-token and bridge-signature requirements."""
    global _require_upload_token_override, _require_bridge_signature_override
    if require_upload_token is not None:
        _require_upload_token_override = require_upload_token
    if require_bridge_signature is not None:
        _require_bridge_signature_override = require_bridge_signature


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


def upload_token_secret() -> str:
    return _runtime_or_env("upload_secret", "REFLEX_R2_UPLOAD_SECRET")


def require_upload_token() -> bool:
    if _require_upload_token_override is not None:
        return bool(_require_upload_token_override)
    if _runtime is not None:
        return bool(_runtime.require_upload_token)
    raw = os.environ.get("REFLEX_R2_REQUIRE_UPLOAD_TOKEN", "").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    return True


def upload_token_ttl() -> int:
    if _runtime is not None:
        return max(300, int(_runtime.upload_token_ttl))
    raw = os.environ.get("REFLEX_R2_UPLOAD_TOKEN_TTL", "").strip()
    if not raw:
        return DEFAULT_UPLOAD_TOKEN_TTL
    try:
        return max(300, int(raw))
    except ValueError:
        return DEFAULT_UPLOAD_TOKEN_TTL


def require_bridge_signature() -> bool:
    if _require_bridge_signature_override is not None:
        return bool(_require_bridge_signature_override)
    if _runtime is not None:
        return bool(_runtime.require_bridge_signature)
    raw = os.environ.get("REFLEX_R2_REQUIRE_BRIDGE_SIGNATURE", "").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    return True


def configure_rate_limit(
    *,
    requests: int | None = None,
    window_seconds: int | None = None,
) -> None:
    """Override API rate limits (``requests=0`` disables limiting)."""
    global _rate_limit_requests_override, _rate_limit_window_override
    if requests is not None:
        _rate_limit_requests_override = requests
    if window_seconds is not None:
        _rate_limit_window_override = window_seconds


def configure_upload_limits(*, max_upload_bytes: int | None = None) -> None:
    """Override the maximum upload object size in bytes (``0`` disables the cap)."""
    global _max_upload_bytes_override
    _max_upload_bytes_override = max_upload_bytes


def max_upload_bytes() -> int:
    if _max_upload_bytes_override is not None:
        return max(0, int(_max_upload_bytes_override))
    if _runtime is not None:
        return max(0, int(_runtime.max_upload_bytes))
    raw = os.environ.get("REFLEX_R2_MAX_UPLOAD_BYTES", "").strip()
    if not raw:
        return DEFAULT_MAX_UPLOAD_BYTES
    try:
        return max(0, int(raw))
    except ValueError:
        return DEFAULT_MAX_UPLOAD_BYTES


def rate_limit_requests() -> int:
    if _rate_limit_requests_override is not None:
        return max(0, int(_rate_limit_requests_override))
    if _runtime is not None:
        return max(0, int(_runtime.rate_limit_requests))
    raw = os.environ.get("REFLEX_R2_RATE_LIMIT_REQUESTS", "").strip()
    if not raw:
        return DEFAULT_RATE_LIMIT_REQUESTS
    try:
        return max(0, int(raw))
    except ValueError:
        return DEFAULT_RATE_LIMIT_REQUESTS


def rate_limit_window_seconds() -> int:
    if _rate_limit_window_override is not None:
        return max(1, int(_rate_limit_window_override))
    if _runtime is not None:
        return max(1, int(_runtime.rate_limit_window_seconds))
    raw = os.environ.get("REFLEX_R2_RATE_LIMIT_WINDOW", "").strip()
    if not raw:
        return DEFAULT_RATE_LIMIT_WINDOW
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_RATE_LIMIT_WINDOW


def resolve_get_expires(expires_in: int | None = None) -> int:
    """Return a GET URL TTL clamped to ``[MIN_GET_EXPIRES, get_expires()]``."""
    cap = get_expires()
    if expires_in is None:
        return cap
    try:
        requested = int(expires_in)
    except (TypeError, ValueError):
        return cap
    return min(max(MIN_GET_EXPIRES, requested), cap)


def verbose_config() -> bool:
    if _verbose_config_override is not None:
        return bool(_verbose_config_override)
    if _runtime is not None:
        return bool(_runtime.verbose_config)
    raw = os.environ.get("REFLEX_R2_VERBOSE_CONFIG", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def configure_verbose_config(enabled: bool | None) -> None:
    """Override whether ``GET /config`` returns diagnostic fields."""
    global _verbose_config_override
    _verbose_config_override = enabled


def build_config_payload(*, route_prefix_value: str) -> dict[str, object]:
    """Return the public ``/config`` JSON body."""
    missing = missing_r2_env()
    payload: dict[str, object] = {"ready": not missing}
    if verbose_config():
        payload["missingEnv"] = missing or None
        base = public_base_url()
        payload["publicBaseUrl"] = base or None
        payload["routePrefix"] = route_prefix_value
    return payload
