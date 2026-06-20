# Architecture & implementation

**Language:** [中文](../zh/architecture.md) · [English](../en/README.md)

| [Docs home](../en/README.md) | [Configuration](configuration.md) | [Security](security.md) | [Bridge](bridge-payload.md) | **Architecture** |

---

## Overview

`reflex_r2_upload` adds browser-direct uploads to Cloudflare R2 for [Reflex](https://reflex.dev) apps:

1. **`upload_zone`** — upload UI (styled or headless via `.root`)  
2. **`wrap_app(app)`** — inject JS runtime + mount reserved Starlette routes  
3. **Bridge** — hidden `<input>` passes signed JSON to `on_success`  
4. **R2** — presigned PUT from the browser; Python signs URLs and enforces policy  

## Layers

```
Reflex app (State.on_uploaded)
        ↓
reflex_r2_upload
  wrap.py / provider.py   — integration
  upload_zone.py          — UI + browser script
  routes.py               — /_reflex_r2_upload/*
  auth.py / limits.py     — tokens, guards, size caps
  storage.py / keys.py    — R2 + object keys
  config.py               — env vars or R2Config
        ↓
Reflex frontend (:3000)  +  Starlette backend (:8000)  +  Cloudflare R2
```

## Upload flow

```mermaid
sequenceDiagram
    participant Browser
    participant API as /_reflex_r2_upload
    participant R2 as Cloudflare R2
    participant State as Reflex State

    Browser->>API: GET /config
    Browser->>API: POST /presign (uploadToken, fileSizeBytes)
    API-->>Browser: uploadUrl (Content-Length bound)
    Browser->>R2: PUT file
    Browser->>API: POST /complete (head_object verify)
    API-->>Browser: bridge JSON + bridgeSignature
    Browser->>State: on_success (signed JSON)
    State->>State: parse_upload_payload()
```

1. **Presign** — validate token/guard, allocate `storagePath`, return presigned PUT URL  
2. **PUT** — browser uploads directly to R2 (needs bucket CORS)  
3. **Complete** — verify object exists, size matches, return [signed bridge payload](bridge-payload.md)  

## Reserved routes

Underscore prefix (like Reflex `/_event`, `/_upload`). Default: `/_reflex_r2_upload`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/config` | none | `{ "ready": bool }` (+ verbose diagnostics if enabled) |
| POST | `/presign` | upload token + guard | Upload PUT URL |
| POST | `/complete` | upload token + guard | Finish upload, verify object |
| POST | `/signed-read` | upload token + guard | Private read URL |

All POST routes are rate-limited per IP (configurable). Do not override these in your own `api_transformer`.

## Presign / complete bodies

**Presign** (extensions come from upload token, not client):

```json
{
  "keyPrefix": "demo/uploads",
  "filename": "model.glb",
  "contentType": "model/gltf-binary",
  "fileSizeBytes": 1048576,
  "uploadToken": "..."
}
```

**Complete**:

```json
{
  "keyPrefix": "demo/uploads",
  "storagePath": "demo/uploads/model.glb",
  "originalFilename": "model.glb",
  "fileSizeBytes": 1048576,
  "contentType": "model/gltf-binary",
  "uploadToken": "..."
}
```

Server calls `head_object`; rejects if object missing or size mismatch.

## `wrap_app`

```python
r2.wrap_app(app)
r2.wrap_app(app, r2_config=R2Config(...))
r2.wrap_app(app, presign_guard=r2.make_user_key_prefix_guard(get_user_id))
```

- Registers `app_wraps` → injects `UPLOAD_RUNTIME_SCRIPT` once  
- Chains `api_transformer` → mounts `create_upload_api()`  
- Options: `require_upload_token`, `require_bridge_signature`, `allowed_key_prefixes`, `presign_guard`

See [Security](security.md) and [Configuration](configuration.md).

## Bridge pattern

JavaScript writes JSON to a hidden input and dispatches `input` → Reflex calls `@rx.event def on_uploaded(self, payload_json: str)`.

Use `parse_upload_payload()` for typed `UploadResult` with default bridge signature verification.

## Public vs private read

| | Public CDN | Private bucket |
|---|------------|----------------|
| Config | `public_base_url` set | omitted |
| Bridge | `publicUrl` set | `publicUrl: null` |
| Read | `file.public_url` | `signed_read_url()` in Reflex events |

Details: [private-bucket.md](private-bucket.md)

## Built-in security vs app responsibilities

**Built in:** upload tokens, bridge signatures, object verification on complete, size caps, Content-Type policy, rate limiting, minimal `/config`.

**Your app still owns:** login/session, per-user read authorization, secret management, R2 CORS.

Full checklist: [security.md](security.md)

## Known limitations

- `upload_zone` `on_error` is declared but not implemented  
- Open demos may share a `key_prefix` — use `presign_guard` for per-user isolation  

## Module map

| Module | Role |
|--------|------|
| `wrap.py` | `wrap_app` |
| `upload_zone.py` | UI + JS |
| `routes.py` | Starlette routes |
| `auth.py` | Tokens, guards, bridge signatures |
| `limits.py` / `rate_limit.py` | Size caps, TTL clamp, rate limit |
| `content_types.py` | MIME blocklist & matching |
| `storage.py` | boto3 R2 client, presigned URLs |
| `keys.py` | Safe paths, extension checks |
| `types.py` / `payload.py` | Bridge schema v1 |
| `access.py` | `signed_read_url` helper |

Full Chinese version with more diagrams: [../zh/architecture.md](../zh/architecture.md)

---

| [← Private bucket](private-bucket.md) | [Docs home](../en/README.md) |
