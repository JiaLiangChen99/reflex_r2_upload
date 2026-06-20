# reflex-r2-upload

**Language:** **English** · [中文](README.zh-CN.md)

**Source & docs:** [GitHub](https://github.com/JiaLiangChen99/reflex_r2_upload) · [Documentation](docs/en/README.md) · [中文文档](docs/README.md)

A Reflex component library for **browser-direct uploads** to **Cloudflare R2** (presigned PUT). Large files never pass through your Python backend.

**What it does**

- `upload_zone` — upload UI (styled preset or headless via `.root`)
- `wrap_app(app)` — one-line Reflex integration (JS runtime + Starlette routes)
- `parse_upload_payload` — typed callback after upload (path, filename, optional public URL)
- Public CDN URLs or private-bucket `signed_read_url()` for temporary reads
- **Built-in upload security** — tokens, bridge signatures, size limits, rate limiting (see [Security](docs/en/security.md))

---

## Installation

```bash
pip install reflex-r2-upload
```

---

## Quick start

```python
import reflex as rx
import reflex_r2_upload as r2


class State(rx.State):
    @rx.event
    def on_uploaded(self, payload_json: r2.UploadPayloadJson):
        try:
            result = r2.parse_upload_payload(payload_json)
        except r2.UploadPayloadError as error:
            self.message = error.message
            return
        file = result.file
        self.message = f"Uploaded: {file.original_filename}"
        self.storage_path = file.storage_path


def index() -> rx.Component:
    return rx.container(
        r2.upload_zone(
            key_prefix="demo/uploads",
            accept=".glb,model/gltf-binary",
            allowed_extensions=[".glb"],
            content_type="model/gltf-binary",
            on_success=State.on_uploaded,
        ),
        padding="2em",
    )


app = rx.App()
app.add_page(index)
r2.wrap_app(app)  # secure defaults enabled
```

Steps:

1. Import `reflex_r2_upload` and add `upload_zone` to your page (`key_prefix` = object path prefix in the bucket).
2. Call **`wrap_app(app)`** after `add_page`.
3. Parse the `on_success` JSON with **`parse_upload_payload`**.

Headless upload area:

```python
r2.upload_zone.root(
    rx.vstack(rx.icon("upload"), rx.text("Drop or click to upload"), spacing="2", align="center"),
    key_prefix="demo/uploads",
    allowed_extensions=[".glb"],
    content_type="model/gltf-binary",
    on_success=State.on_uploaded,
    class_name="rounded-xl border-2 border-dashed p-8",
)
```

---

## Configuration

Cloudflare R2 credentials are required. Configure **CORS** on the bucket so your site origin can `PUT` to the storage endpoint.

### Option 1: Environment variables

Copy [`.env.example`](.env.example) and fill in R2 credentials.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `R2_ACCOUNT_ID` | Yes | — | Cloudflare account ID |
| `R2_ACCESS_KEY_ID` | Yes | — | R2 API token access key |
| `R2_SECRET_ACCESS_KEY` | Yes | — | R2 API token secret |
| `R2_BUCKET_NAME` | Yes | — | Bucket name |
| `R2_PUBLIC_BASE_URL` | No | — | Public CDN / custom domain |
| `REFLEX_R2_ROUTE_PREFIX` | No | `/_reflex_r2_upload` | Reserved API prefix |
| `REFLEX_R2_PRESIGN_EXPIRES` | No | `600` | Upload URL TTL (seconds) |
| `REFLEX_R2_GET_EXPIRES` | No | `3600` | Private read URL max TTL (seconds) |
| `REFLEX_R2_UPLOAD_SECRET` | No | derived | HMAC secret for upload tokens & bridge signatures |
| `REFLEX_R2_UPLOAD_TOKEN_TTL` | No | `7200` | Upload token lifetime (seconds) |
| `REFLEX_R2_MAX_UPLOAD_BYTES` | No | `104857600` | Max file size (100 MiB); `0` = unlimited |
| `REFLEX_R2_RATE_LIMIT_REQUESTS` | No | `60` | API requests per IP per window; `0` = off |
| `REFLEX_R2_RATE_LIMIT_WINDOW` | No | `60` | Rate limit window (seconds) |
| `REFLEX_R2_REQUIRE_UPLOAD_TOKEN` | No | `1` | Require upload token on presign/complete/signed-read |
| `REFLEX_R2_REQUIRE_BRIDGE_SIGNATURE` | No | `1` | Require server `bridgeSignature` in callbacks |
| `REFLEX_R2_VERBOSE_CONFIG` | No | `0` | Expose diagnostic fields on `GET /config` |

### Option 2: `R2Config`

```python
r2_config = r2.R2Config(
    account_id="...",
    access_key_id="...",
    secret_access_key="...",
    bucket_name="my-bucket",
    public_base_url="https://assets.example.com",  # optional
    max_upload_bytes=50 * 1024 * 1024,
    allowed_key_prefixes=("uploads/",),
)

r2.wrap_app(app, r2_config=r2_config)
```

Code config overrides environment variables. Keep secrets on the server only — never in the frontend or `rx.State`.

Full reference: [Configuration](docs/en/configuration.md)

---

## Upload flow

```
Browser → GET /config (ready?)
       → POST /presign (uploadToken + fileSizeBytes)
       → PUT R2 (presigned URL, Content-Length bound)
       → POST /complete (verify object exists in R2)
       → on_success bridge JSON (server-signed)
       → parse_upload_payload() in Reflex State
```

Details: [Architecture](docs/en/architecture.md) · [Bridge Payload](docs/en/bridge-payload.md)

---

## Production hardening

The library ships secure defaults (upload tokens, bridge signatures, size caps, rate limits). For **logged-in apps**, bind uploads to the current user:

```python
def get_user_id(request):
    # Read from Reflex session / JWT / cookie
    ...

r2.wrap_app(
    app,
    presign_guard=r2.make_user_key_prefix_guard(get_user_id),
)

# In your page — prefix must match the logged-in user
r2.upload_zone(
    key_prefix=r2.user_key_prefix(current_user_id),
    on_success=State.on_uploaded,
)
```

Optional prefix allowlist:

```python
r2.wrap_app(app, allowed_key_prefixes=["demo/uploads", "avatars/"])
```

Private reads — prefer server-side helper over the HTTP route:

```python
@rx.event
def preview(self):
    # Authorize before issuing
    self.temp_url = r2.signed_read_url(self.storage_path, expires_in=300)
```

Full guide: [Security](docs/en/security.md)

---

## Public vs private read

| Mode | Config | Bridge `publicUrl` | Read access |
|------|--------|-------------------|-------------|
| Public CDN | `R2_PUBLIC_BASE_URL` set | CDN URL | Use `file.public_url` |
| Private | No public domain | `null` | `signed_read_url()` in Reflex events |

See [Private bucket](docs/en/private-bucket.md).

---

## API overview

| Symbol | Purpose |
|--------|---------|
| `wrap_app(app, ...)` | Integration entry point |
| `R2Config` / `configure_r2` | Credentials & options in code |
| `upload_zone` / `upload_zone.root` | Upload UI components |
| `parse_upload_payload` | Parse signed upload callback |
| `signed_read_url` | Temporary private read URL (server-side) |
| `issue_upload_token` | Manually issue an upload token |
| `make_user_key_prefix_guard` | Per-user prefix guard for production |
| `make_allowed_key_prefixes_guard` | Allowlist guard |
| `user_key_prefix` | Build `uploads/{user_id}` style prefix |
| `is_public_access_configured()` | Whether a public CDN is configured |

---

## Documentation

| English | 中文 |
|---------|------|
| [Docs home](docs/en/README.md) | [文档首页](docs/README.md) |
| [Configuration](docs/en/configuration.md) | [配置](docs/zh/configuration.md) |
| [Security](docs/en/security.md) | [安全](docs/zh/security.md) |
| [Bridge Payload](docs/en/bridge-payload.md) | [Bridge Payload](docs/zh/bridge-payload.md) |
| [Private bucket](docs/en/private-bucket.md) | [私有桶](docs/zh/private-bucket.md) |
| [Architecture](docs/en/architecture.md) | [架构与实现](docs/zh/architecture.md) |

---

## License

MIT

## Contributing

Pull requests are welcome. For larger changes, please open an issue first.

## Acknowledgments

- [Reflex](https://reflex.dev)
- [Cloudflare R2](https://developers.cloudflare.com/r2/)
