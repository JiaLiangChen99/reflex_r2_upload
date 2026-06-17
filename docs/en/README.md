# reflex-r2-upload Documentation

**Language:** [中文](../docs/README.md) · **English**

[Project README (English)](../README.md) · [README 中文](../README.zh-CN.md)

---

## Quick navigation

| Document | Description |
|----------|-------------|
| [Configuration](configuration.md) | Environment variables & `R2Config` |
| [Bridge Payload](bridge-payload.md) | Upload callback JSON schema (v1) |
| [Private bucket](private-bucket.md) | Read access without a public CDN |
| [Architecture](architecture.md) | Design, data flow, reserved routes |

## Suggested reading order

**Getting started**

1. [Configuration](configuration.md) — R2 credentials  
2. [Project README](../../README.md) — install & `wrap_app`  
3. [Bridge Payload](bridge-payload.md) — parse `on_success`  

**Public CDN vs private bucket**

- `R2_PUBLIC_BASE_URL` set → use `publicUrl` in [Bridge Payload](bridge-payload.md)  
- No public domain → [Private bucket](private-bucket.md)  

**Contributors**

- [Architecture](architecture.md)

---

[中文文档](../README.md) · [Project README](../../README.md)
