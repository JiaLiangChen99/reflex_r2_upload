"""Tests for R2Config vs environment variables."""

import reflex_r2_upload.config as config
from reflex_r2_upload.config import R2Config, configure_allowed_key_prefixes, configure_r2, configure_upload_auth


def setup_function():
    configure_r2(None)
    configure_upload_auth(require_upload_token=None, require_bridge_signature=None)
    configure_allowed_key_prefixes(None)


def test_r2_config_overrides_env(monkeypatch):
    monkeypatch.setenv("R2_ACCOUNT_ID", "env-account")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "env-key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "env-secret")
    monkeypatch.setenv("R2_BUCKET_NAME", "env-bucket")

    configure_r2(
        R2Config(
            account_id="cfg-account",
            access_key_id="cfg-key",
            secret_access_key="cfg-secret",
            bucket_name="cfg-bucket",
            public_base_url="https://cdn.example.com",
        )
    )

    assert config.account_id() == "cfg-account"
    assert config.bucket_name() == "cfg-bucket"
    assert config.public_base_url() == "https://cdn.example.com"
    assert config.missing_r2_env() == []


def test_env_fallback_when_no_runtime_config(monkeypatch):
    monkeypatch.setenv("R2_ACCOUNT_ID", "env-account")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "env-key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "env-secret")
    monkeypatch.setenv("R2_BUCKET_NAME", "env-bucket")

    assert config.account_id() == "env-account"
    assert config.missing_r2_env() == []


def test_missing_when_nothing_set(monkeypatch):
    for key in config.R2_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)

    missing = config.missing_r2_env()
    assert "R2_ACCOUNT_ID" in missing
    assert "R2_BUCKET_NAME" in missing
