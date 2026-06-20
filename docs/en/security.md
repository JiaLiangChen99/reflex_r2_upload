# Security & production deployment

**Language:** [中文](../zh/security.md) · [English](../en/README.md)

| [Docs home](../en/README.md) | [Configuration](configuration.md) | **Security** | [Bridge](bridge-payload.md) | [Architecture](architecture.md) |

---

The library ships secure defaults. Open demos may share a `key_prefix`; **logged-in apps** should bind uploads to the authenticated user and authorize reads.

## Built-in protections (on by default)

| Mechanism | Purpose |
|-----------|---------|
| **Upload token** | HMAC token binds `keyPrefix`, extension allowlist, Content-Type; required on presign / complete / signed-read |
| **Bridge signature** | `/complete` returns `bridgeSignature`; `parse_upload_payload()` verifies it by default |
| **Object verification** | `complete` calls `head_object`; checks existence and `fileSizeBytes` vs R2 `ContentLength` |
| **Size cap** | `REFLEX_R2_MAX_UPLOAD_BYTES` (default 100 MiB); presign binds `ContentLength` on PUT |
| **Content-Type policy** | Dangerous MIME blocklist; extension/MIME matching; token-bound type overrides client |
| **Rate limiting** | Per-IP API limits (default 60 req / 60 s); returns 429 when exceeded |
| **Minimal `/config`** | Default `{ "ready": bool }` only; diagnostics need `REFLEX_R2_VERBOSE_CONFIG=1` |

Disabling tokens or bridge verification (`REFLEX_R2_REQUIRE_*=0`) is **for local debugging only**.

## Upload token flow

1. Server issues a token when `upload_zone` renders → `data-upload-token`
2. Browser JS sends `uploadToken` in presign / complete bodies
3. Server verifies signature, expiry, and that `keyPrefix` matches token field `p`
4. Extensions (`e`) and Content-Type (`c`) come from the token; **presign ignores client `allowedExtensions`**

Manual issue (advanced):

```python
token = r2.issue_upload_token(
    key_prefix="uploads/user-42",
    allowed_extensions=[".png", ".jpg"],
    content_type="image/png",
)
```

## Bridge signature

`/complete` success includes:

```json
{
  "storagePath": "demo/uploads/model.glb",
  "bridgeSignature": "..."
}
```

JS forwards `bridgeSignature` into the `on_success` JSON. In Python:

```python
result = r2.parse_upload_payload(payload_json)  # verifies by default
```

Verification failure → `UploadPayloadError` with `code=INVALID_SIGNATURE`.

Disable (dev only):

```python
r2.wrap_app(app, require_bridge_signature=False)
# or REFLEX_R2_REQUIRE_BRIDGE_SIGNATURE=0
```

## Production: per-user prefix

Demos may share `demo/uploads`. In production, each logged-in user should write only to their own prefix:

```python
def get_user_id(request):
    # Read from Reflex session / JWT / cookie
    ...

r2.wrap_app(
    app,
    presign_guard=r2.make_user_key_prefix_guard(get_user_id),
)

r2.upload_zone(
    key_prefix=r2.user_key_prefix(current_user_id),
    on_success=State.on_uploaded,
)
```

### Prefix allowlist

```python
r2.wrap_app(app, allowed_key_prefixes=["avatars/", "uploads/"])
```

### Custom guard

```python
async def my_guard(request, data) -> bool:
    return True  # your auth logic

r2.wrap_app(app, presign_guard=my_guard)
```

The guard applies to presign, complete, and signed-read.

## Private reads

The HTTP `POST /signed-read` route requires the same upload token + guard as presign.

**Recommended**: call `signed_read_url()` inside Reflex events after your own read authorization:

```python
@rx.event
def preview(self):
    if not self.user_can_read(self.storage_path):
        return
    self.temp_url = r2.signed_read_url(self.storage_path, expires_in=300)
```

`expiresIn` is clamped to `[60, REFLEX_R2_GET_EXPIRES]` seconds.

## Still your responsibility

| Item | Notes |
|------|-------|
| Login/session | `presign_guard` must read real session state |
| Read authorization | Check who may read `storagePath` before `signed_read_url()` |
| Secrets | R2 credentials and `REFLEX_R2_UPLOAD_SECRET` stay server-side |
| CORS | Bucket must allow your site origin to `PUT` |
| `on_error` | Declared on `upload_zone` but not implemented yet |

## Related configuration

Full env reference: [Configuration](configuration.md). Security-related:

| Variable | Default | Description |
|----------|---------|-------------|
| `REFLEX_R2_UPLOAD_SECRET` | derived from R2 creds | HMAC secret |
| `REFLEX_R2_UPLOAD_TOKEN_TTL` | `7200` | Token TTL (seconds) |
| `REFLEX_R2_REQUIRE_UPLOAD_TOKEN` | `1` | Require upload token |
| `REFLEX_R2_REQUIRE_BRIDGE_SIGNATURE` | `1` | Verify bridge signature |
| `REFLEX_R2_MAX_UPLOAD_BYTES` | `104857600` | Max file size |
| `REFLEX_R2_RATE_LIMIT_REQUESTS` | `60` | Rate limit; `0` = off |
| `REFLEX_R2_RATE_LIMIT_WINDOW` | `60` | Window (seconds) |
| `REFLEX_R2_VERBOSE_CONFIG` | `0` | Verbose `/config` |

---

| [← Configuration](configuration.md) | [Docs home](../en/README.md) | [Bridge Payload →](bridge-payload.md) |
