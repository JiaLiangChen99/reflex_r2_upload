# Bridge Payload (Version 1)

**Language:** [中文](../zh/bridge-payload.md) · [English](../en/README.md)

| [Docs home](../en/README.md) | [Configuration](configuration.md) | **Bridge** | [Private bucket](private-bucket.md) | [Architecture](architecture.md) |

---

`upload_zone` sends JSON to `on_success` via a hidden input. Parse it with `parse_upload_payload()` → `UploadResult` / `UploadedFile`.

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
  "publicUrl": "https://cdn.example.com/demo/uploads/model.glb"
}
```

`publicUrl` is `null` when no public domain is configured. See [private-bucket.md](private-bucket.md).

## Success — multiple files

```json
{
  "version": 1,
  "error": false,
  "keyPrefix": "demo/uploads",
  "files": [ { "...": "same fields as single file" } ]
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
| `INVALID_PAYLOAD` | `parse_upload_payload` failed |

## Python

```python
result = r2.parse_upload_payload(payload_json)
file = result.file  # .key_prefix, .storage_path, .public_url (optional)
```

## Intentionally omitted

- User / entity IDs → use `key_prefix` or Reflex State  
- Bucket name / account → server config only  
- Presigned PUT URL → short-lived, never in bridge  

---

| [← Configuration](configuration.md) | [Docs home](../en/README.md) | [Private bucket →](private-bucket.md) |
