# Configuration

**Language:** [中文](../zh/configuration.md) · [English](../en/README.md)

| [Docs home](../en/README.md) | **Configuration** | [Bridge](bridge-payload.md) | [Private bucket](private-bucket.md) | [Architecture](architecture.md) |

---

Cloudflare R2 credentials are required. Use **either** method below (code config overrides env vars).

## Option 1: Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `R2_ACCOUNT_ID` | Yes | Cloudflare account ID |
| `R2_ACCESS_KEY_ID` | Yes | R2 API token access key |
| `R2_SECRET_ACCESS_KEY` | Yes | R2 API token secret |
| `R2_BUCKET_NAME` | Yes | Bucket name |
| `R2_PUBLIC_BASE_URL` | No | Public CDN / custom domain |
| `REFLEX_R2_ROUTE_PREFIX` | No | Reserved route prefix, default `/_reflex_r2_upload` |
| `REFLEX_R2_PRESIGN_EXPIRES` | No | Upload URL TTL (seconds), default 600 |
| `REFLEX_R2_GET_EXPIRES` | No | Private read URL TTL (seconds), default 3600 |

Use `export`, `.env` + `dotenv`, or your host's secret manager.

## Option 2: `R2Config`

```python
import reflex_r2_upload as r2

r2_config = r2.R2Config(
    account_id="...",
    access_key_id="...",
    secret_access_key="...",
    bucket_name="my-bucket",
    public_base_url="https://assets.example.com",  # optional
)

r2.wrap_app(app, r2_config=r2_config)
# or: r2.configure_r2(r2_config)
```

## R2 bucket CORS

Allow your site origin to `PUT` to the R2 endpoint so the browser can upload directly.

## Verify readiness

```bash
curl http://localhost:8000/_reflex_r2_upload/config
```

`"ready": true` means all required credentials are present.

---

| [← Docs home](../en/README.md) | [Bridge Payload →](bridge-payload.md) |
