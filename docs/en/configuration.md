# Configuration

**Language:** [中文](../zh/configuration.md) · [English](../en/README.md)

| [Docs home](../en/README.md) | **Configuration** | [Security](security.md) | [Bridge](bridge-payload.md) | [Architecture](architecture.md) |

---

Cloudflare R2 credentials are required. Use **either** method below (code config overrides env vars).

## Option 1: Environment variables

### R2 credentials

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `R2_ACCOUNT_ID` | Yes | — | Cloudflare account ID |
| `R2_ACCESS_KEY_ID` | Yes | — | R2 API token access key |
| `R2_SECRET_ACCESS_KEY` | Yes | — | R2 API token secret |
| `R2_BUCKET_NAME` | Yes | — | Bucket name |
| `R2_PUBLIC_BASE_URL` | No | — | Public CDN / custom domain; omit for private bucket |

### Routes & URL TTL

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REFLEX_R2_ROUTE_PREFIX` | No | `/_reflex_r2_upload` | Reserved API prefix |
| `REFLEX_R2_PRESIGN_EXPIRES` | No | `600` | Upload presigned URL TTL (seconds), min 60 |
| `REFLEX_R2_GET_EXPIRES` | No | `3600` | Max private read URL TTL; `expiresIn` floor is 60 |

### Upload security

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REFLEX_R2_UPLOAD_SECRET` | No | derived | HMAC secret for tokens & bridge signatures |
| `REFLEX_R2_UPLOAD_TOKEN_TTL` | No | `7200` | Upload token TTL (seconds) |
| `REFLEX_R2_REQUIRE_UPLOAD_TOKEN` | No | `1` | Require token on presign / complete / signed-read |
| `REFLEX_R2_REQUIRE_BRIDGE_SIGNATURE` | No | `1` | Verify bridge signature in callbacks |
| `REFLEX_R2_MAX_UPLOAD_BYTES` | No | `104857600` | Max file size (100 MiB); `0` = unlimited |
| `REFLEX_R2_RATE_LIMIT_REQUESTS` | No | `60` | API requests per IP per window; `0` = off |
| `REFLEX_R2_RATE_LIMIT_WINDOW` | No | `60` | Rate limit window (seconds) |
| `REFLEX_R2_VERBOSE_CONFIG` | No | `0` | `1` exposes `missingEnv` etc. on `/config` |

Use `export`, `.env` + `dotenv`, or your host's secret manager. Template: [`.env.example`](../../.env.example)

## Option 2: `R2Config`

```python
import reflex_r2_upload as r2

r2_config = r2.R2Config(
    account_id="...",
    access_key_id="...",
    secret_access_key="...",
    bucket_name="my-bucket",
    public_base_url="https://assets.example.com",
    presign_expires=600,
    get_expires=3600,
    route_prefix="/_reflex_r2_upload",
    upload_secret="",
    require_upload_token=True,
    upload_token_ttl=7200,
    require_bridge_signature=True,
    allowed_key_prefixes=("uploads/", "avatars/"),
    max_upload_bytes=50 * 1024 * 1024,
    rate_limit_requests=60,
    rate_limit_window_seconds=60,
    verbose_config=False,
)

r2.wrap_app(app, r2_config=r2_config)
```

## `wrap_app` parameters

| Parameter | Description |
|-----------|-------------|
| `r2_config` | `R2Config` instance |
| `backend_base` | Explicit backend origin (dev split frontend/backend) |
| `route_prefix` | Override reserved route prefix |
| `presign_expires` | Presign TTL hint injected into frontend |
| `require_upload_token` | Override upload token requirement |
| `require_bridge_signature` | Override bridge signature verification |
| `allowed_key_prefixes` | Allowlist for API `keyPrefix` values |
| `presign_guard` | Custom auth guard (see [Security](security.md)) |

Runtime overrides without rebuilding `R2Config`:

```python
r2.configure_upload_auth(require_upload_token=True, require_bridge_signature=True)
r2.configure_allowed_key_prefixes(["uploads/"])
```

## R2 bucket CORS

Allow your site origin to `PUT` to the R2 endpoint so the browser can upload directly.

## Verify readiness

```bash
curl http://localhost:8000/_reflex_r2_upload/config
```

Default response:

```json
{ "ready": true }
```

With `REFLEX_R2_VERBOSE_CONFIG=1`, also returns `missingEnv`, `publicBaseUrl`, `routePrefix`.

---

| [← Docs home](../en/README.md) | [Security →](security.md) | [Bridge Payload →](bridge-payload.md) |
