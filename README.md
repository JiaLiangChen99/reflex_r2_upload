# reflex-r2-upload

**Language:** **English** · [中文](https://github.com/JiaLiangChen99/reflex_r2_upload/blob/main/README.zh-CN.md)

**Source & docs:** [GitHub](https://github.com/JiaLiangChen99/reflex_r2_upload) · [Documentation](https://github.com/JiaLiangChen99/reflex_r2_upload/tree/main/docs/en/README.md) · [中文文档](https://github.com/JiaLiangChen99/reflex_r2_upload/tree/main/docs/README.md)

A Reflex custom component for **browser-direct uploads** to **Cloudflare R2** (presigned PUT). Large files never pass through your Python backend.

**What it does**

- `upload_zone` — upload UI (styled or headless via `.root`)
- `wrap_app(app)` — one-line Reflex integration
- `parse_upload_payload` — typed callback after upload (path, filename, optional public URL)
- Public CDN URLs or private-bucket `signed_read_url` for temporary reads

---

## Installation

```bash
pip install reflex-r2-upload
```

---

## Configuration

Cloudflare R2 credentials are required. Use either method below.

### Option 1: Environment variables

Set in the process environment (`export`, `.env` + `load_dotenv()`, or your host's secret manager):

| Variable | Required | Description |
|----------|----------|-------------|
| `R2_ACCOUNT_ID` | Yes | Cloudflare account ID |
| `R2_ACCESS_KEY_ID` | Yes | R2 API token access key |
| `R2_SECRET_ACCESS_KEY` | Yes | R2 API token secret |
| `R2_BUCKET_NAME` | Yes | Bucket name |
| `R2_PUBLIC_BASE_URL` | No | Public CDN / custom domain (see examples) |
| `REFLEX_R2_PRESIGN_EXPIRES` | No | Upload URL TTL (seconds), default 600 |
| `REFLEX_R2_GET_EXPIRES` | No | Private read URL TTL (seconds), default 3600 |

Configure **CORS** on the R2 bucket so your site origin can `PUT` to the storage endpoint.

### Option 2: `R2Config` in code

```python
import reflex as rx
import reflex_r2_upload as r2

r2_config = r2.R2Config(
    account_id="...",
    access_key_id="...",
    secret_access_key="...",
    bucket_name="my-bucket",
    public_base_url="https://assets.example.com",  # optional
)

app = rx.App()
app.add_page(index)
r2.wrap_app(app, r2_config=r2_config)
```

You can also call `r2.configure_r2(r2_config)` before the first upload request.

> Code config overrides environment variables. Keep secrets on the server only — never in the frontend or `rx.State`.

---

## Usage

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
            key_prefix="users/1/uploads",
            accept=".glb,model/gltf-binary",
            allowed_extensions=[".glb"],
            on_success=State.on_uploaded,
        ),
        padding="2em",
    )


app = rx.App()
app.add_page(index)
r2.wrap_app(app)
```

In this example:

1. Import `reflex_r2_upload`.
2. Add `upload_zone` to your page; `key_prefix` is the object path prefix in the bucket.
3. After `add_page`, call **`wrap_app(app)`** (or `wrap_app(app, r2_config=...)`).
4. On success, `on_success` receives JSON; parse it with **`parse_upload_payload`**.

Headless upload area (custom styling):

```python
r2.upload_zone.root(
    rx.vstack(rx.icon("upload"), rx.text("Drop or click to upload"), spacing="2", align="center"),
    key_prefix="users/1/uploads",
    on_success=State.on_uploaded,
    class_name="rounded-xl border-2 border-dashed p-8",
)
```

---

## Examples

### Public read (`R2_PUBLIC_BASE_URL` or `R2Config.public_base_url`)

```python
file = r2.parse_upload_payload(payload_json).file
if file.public_url:
    return rx.image(src=file.public_url)
```

### Private read (no public domain)

```python
@rx.event
def preview(self):
    # Production: authorize before issuing a read URL
    self.temp_url = r2.signed_read_url(self.storage_path)
```

### Check public vs private mode

```python
if r2.is_public_access_configured():
    ...
```

---

## API overview

| Symbol | Purpose |
|--------|---------|
| `wrap_app(app, r2_config=...)` | Integration entry point |
| `R2Config` / `configure_r2` | Credentials in code |
| `upload_zone` / `upload_zone.root` | Upload components |
| `parse_upload_payload` | Parse upload callback |
| `signed_read_url` | Temporary private read URL |
| `is_public_access_configured()` | Whether a public domain is configured |

---

## Documentation

Full docs live on GitHub (not bundled on PyPI):

**[📖 Docs (English)](https://github.com/JiaLiangChen99/reflex_r2_upload/tree/main/docs/en/README.md)** · **[📖 文档（中文）](https://github.com/JiaLiangChen99/reflex_r2_upload/tree/main/docs/README.md)** · **[README 中文](https://github.com/JiaLiangChen99/reflex_r2_upload/blob/main/README.zh-CN.md)**

| English | 中文 |
|---------|------|
| [Configuration](https://github.com/JiaLiangChen99/reflex_r2_upload/blob/main/docs/en/configuration.md) | [配置](https://github.com/JiaLiangChen99/reflex_r2_upload/blob/main/docs/zh/configuration.md) |
| [Bridge Payload](https://github.com/JiaLiangChen99/reflex_r2_upload/blob/main/docs/en/bridge-payload.md) | [Bridge Payload](https://github.com/JiaLiangChen99/reflex_r2_upload/blob/main/docs/zh/bridge-payload.md) |
| [Private bucket](https://github.com/JiaLiangChen99/reflex_r2_upload/blob/main/docs/en/private-bucket.md) | [私有桶](https://github.com/JiaLiangChen99/reflex_r2_upload/blob/main/docs/zh/private-bucket.md) |
| [Architecture](https://github.com/JiaLiangChen99/reflex_r2_upload/blob/main/docs/en/architecture.md) | [架构与实现](https://github.com/JiaLiangChen99/reflex_r2_upload/blob/main/docs/zh/architecture.md) |

---

## License

MIT

## Contributing

Pull requests are welcome. For larger changes, please open an issue first.

## Acknowledgments

- [Reflex](https://reflex.dev)
- [Cloudflare R2](https://developers.cloudflare.com/r2/)
