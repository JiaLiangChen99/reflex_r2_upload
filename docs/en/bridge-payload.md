# Bridge Payload (Version 1)

**Language:** [中文](../zh/bridge-payload.md) · [English](../en/README.md)

| [Docs home](../en/README.md) | [Configuration](configuration.md) | [Security](security.md) | **Bridge** | [Architecture](architecture.md) |

---

`upload_zone` sends JSON to `on_success` via a hidden input. Parse it with `parse_upload_payload()` → `UploadResult` / `UploadedFile`.

By default, the server-issued **`bridgeSignature`** is verified (see [Security](security.md)).

## Top-level fields

| Field | Type | Description |
|-------|------|-------------|
| `version` | `int` | Always `1` |
| `error` | `bool` | `false` success, `true` failure |

## Success — single file (flat)

```json
{
  "version": 1,
  "error": false,
  "ok": true,
  "keyPrefix": "demo/uploads",
  "storagePath": "demo/uploads/model.glb",
  "originalFilename": "model.glb",
  "fileSizeBytes": 1048576,
  "contentType": "model/gltf-binary",
  "publicUrl": "https://cdn.example.com/demo/uploads/model.glb",
  "bridgeSignature": "..."
}
```

`publicUrl` is `null` when no public domain is configured. See [private-bucket.md](private-bucket.md).

`bridgeSignature` comes from `/complete`; JS forwards it into the bridge JSON. `parse_upload_payload()` verifies it by default.

## Success — multiple files

```json
{
  "version": 1,
  "error": false,
  "keyPrefix": "demo/uploads",
  "files": [
    {
      "ok": true,
      "storagePath": "demo/uploads/a.glb",
      "bridgeSignature": "...",
      "...": "same fields as single file"
    }
  ]
}
```

## Failure

```json
{
  "version": 1,
  "error": true,
  "message": "R2 not configured",
  "code": "R2_NOT_CONFIGURED"
}
```

### Error codes (`code`)

| Value | Meaning |
|-------|---------|
| `R2_NOT_CONFIGURED` | Missing R2 credentials |
| `CONFIG_FETCH_FAILED` | Cannot reach `/_reflex_r2_upload/config` |
| `UPLOAD_FAILED` | Generic upload failure |
| `STORAGE_PUT_FAILED` | Browser PUT to R2 failed |
| `CORS_BLOCKED` | Likely missing R2 CORS |
| `UNAUTHORIZED` | Upload token or guard auth failed |
| `INVALID_SIGNATURE` | Invalid or missing bridge signature |
| `EXTENSION_NOT_ALLOWED` | Extension not in token allowlist |
| `INVALID_PAYLOAD` | Invalid JSON or parse failure |

## Python

```python
try:
    result = r2.parse_upload_payload(payload_json)
except r2.UploadPayloadError as error:
    print(error.code, error.message)
```

Disable bridge verification (dev only):

```python
r2.wrap_app(app, require_bridge_signature=False)
```

## Intentionally omitted

- User / entity IDs → use `key_prefix` or Reflex State  
- Bucket name / account → server config only  
- Presigned PUT URL / upload token → short-lived, never in bridge  

---

| [← Security](security.md) | [Docs home](../en/README.md) | [Private bucket →](private-bucket.md) |
