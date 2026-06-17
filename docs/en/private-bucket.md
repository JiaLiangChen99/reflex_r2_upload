# Private bucket access

**Language:** [中文](../zh/private-bucket.md) · [English](../en/README.md)

| [Docs home](../en/README.md) | [Configuration](configuration.md) | [Bridge](bridge-payload.md) | **Private bucket** | [Architecture](architecture.md) |

---

Upload flow is **identical** to a public bucket (presign → PUT → complete). Only **read access** differs:

| Mode | Config | `publicUrl` | Read access |
|------|--------|-------------|-------------|
| Public | `R2_PUBLIC_BASE_URL` or `R2Config.public_base_url` | CDN URL | Use `publicUrl` directly |
| Private | No public domain | `null` | Server-side `signed_read_url()` |

## After upload

```python
result = r2.parse_upload_payload(payload_json)
file = result.file

if file.public_url:
    self.display_url = file.public_url
else:
    self.storage_path = file.storage_path
```

## Temporary read URL (server-side)

```python
# Production: authorize before issuing
url = r2.signed_read_url(file.storage_path, expires_in=300)
```

## Reserved route

`POST /_reflex_r2_upload/signed-read` with `keyPrefix`, `storagePath`, optional `expiresIn`.

**Always authenticate** before issuing read URLs in production.

## Related

[configuration.md](configuration.md) — `R2_PUBLIC_BASE_URL`, `REFLEX_R2_GET_EXPIRES`

---

| [← Bridge Payload](bridge-payload.md) | [Docs home](../en/README.md) | [Architecture →](architecture.md) |
