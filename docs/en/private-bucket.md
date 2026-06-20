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

## Temporary read URL (recommended: server helper)

```python
# Production: authorize before issuing
url = r2.signed_read_url(file.storage_path, expires_in=300)
```

`expires_in` is clamped between **60 seconds** and `REFLEX_R2_GET_EXPIRES` (default 3600).

`signed_read_url()` does not use the HTTP route and is not gated by upload tokens — **you must authorize before calling it**.

## Reserved HTTP route (requires upload token)

`POST /_reflex_r2_upload/signed-read`

```json
{
  "keyPrefix": "demo/uploads",
  "storagePath": "demo/uploads/model.glb",
  "uploadToken": "...",
  "expiresIn": 3600
}
```

Same auth as presign: valid **upload token** plus optional **presign_guard**. `expiresIn` is clamped to `[60, REFLEX_R2_GET_EXPIRES]`.

In production, prefer `signed_read_url()` inside Reflex events after your own read authorization.

## Related

[configuration.md](configuration.md) — `R2_PUBLIC_BASE_URL`, `REFLEX_R2_GET_EXPIRES`  
[security.md](security.md) — auth model

---

| [← Bridge Payload](bridge-payload.md) | [Docs home](../en/README.md) | [Architecture →](architecture.md) |
