# reflex-r2-upload

**Language:** [English](README.md) · **中文**

Reflex 自定义组件：在 Reflex 应用里把文件 **直传** 到 **Cloudflare R2**（presigned PUT），大文件不经 Python 后端中转。

**能做什么**

- `upload_zone` 上传区域（可自定义样式）
- `wrap_app(app)` 接入 Reflex
- 上传完成回调 `parse_upload_payload` → 路径、文件名、可选公开 URL
- 公开 CDN 读，或私有桶 `signed_read_url` 临时读

---

## 安装

```bash
pip install reflex-r2-upload
```

---

## 配置

需要 Cloudflare R2 凭证，任选一种方式提供。

### 方式一：环境变量

在进程环境中设置（本地常用 `export` 或 `.env` + `load_dotenv()`，部署常用平台密钥注入）：

| 变量 | 必填 | 说明 |
|------|------|------|
| `R2_ACCOUNT_ID` | 是 | Cloudflare 账号 ID |
| `R2_ACCESS_KEY_ID` | 是 | R2 API 令牌 |
| `R2_SECRET_ACCESS_KEY` | 是 | R2 API 令牌 |
| `R2_BUCKET_NAME` | 是 | 桶名 |
| `R2_PUBLIC_BASE_URL` | 否 | 公开 CDN / 自定义域名（见下方示例） |
| `REFLEX_R2_PRESIGN_EXPIRES` | 否 | 上传 URL 有效期（秒），默认 600 |
| `REFLEX_R2_GET_EXPIRES` | 否 | 私有读 URL 有效期（秒），默认 3600 |

R2 桶需配置 **CORS**，允许站点 Origin 对存储端点发 `PUT`。

### 方式二：代码传入 `R2Config`

```python
import reflex as rx
import reflex_r2_upload as r2

r2_config = r2.R2Config(
    account_id="...",
    access_key_id="...",
    secret_access_key="...",
    bucket_name="my-bucket",
    public_base_url="https://assets.example.com",  # 可选
)

app = rx.App()
app.add_page(index)
r2.wrap_app(app, r2_config=r2_config)
```

也可单独调用 `r2.configure_r2(r2_config)`（须在首次上传请求之前）。

> 代码配置优先于同名环境变量。密钥只应存在于服务端，不要放进前端或 `rx.State`。

---

## 用法

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
        self.message = f"已上传：{file.original_filename}"
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

说明：

1. 引入 `reflex_r2_upload`。
2. 页面中使用 `upload_zone`，`key_prefix` 为桶内对象路径前缀。
3. 创建 `app` 并 `add_page` 后调用 **`wrap_app(app)`**（或 `wrap_app(app, r2_config=...)`）。
4. 上传完成后触发 `on_success`；用 **`parse_upload_payload`** 解析 JSON。

无默认样式的上传区：

```python
r2.upload_zone.root(
    rx.vstack(rx.icon("upload"), rx.text("拖放或点击选择"), spacing="2", align="center"),
    key_prefix="users/1/uploads",
    on_success=State.on_uploaded,
    class_name="rounded-xl border-2 border-dashed p-8",
)
```

---

## 示例

### 公开读（配置了 `R2_PUBLIC_BASE_URL` 或 `R2Config.public_base_url`）

```python
file = r2.parse_upload_payload(payload_json).file
if file.public_url:
    return rx.image(src=file.public_url)
```

### 私有读（未配置公开域名）

```python
@rx.event
def preview(self):
    # 生产环境：先校验用户是否有权读取
    self.temp_url = r2.signed_read_url(self.storage_path)
```

### 判断是否公开模式

```python
if r2.is_public_access_configured():
    ...
```

---

## API 一览

| 符号 | 作用 |
|------|------|
| `wrap_app(app, r2_config=...)` | 集成入口 |
| `R2Config` / `configure_r2` | 代码方式提供 R2 凭证 |
| `upload_zone` / `upload_zone.root` | 上传组件 |
| `parse_upload_payload` | 解析上传回调 |
| `signed_read_url` | 私有桶临时读 URL |
| `is_public_access_configured()` | 是否配置了公开域名 |

---

## 文档

**[📖 文档首页](docs/README.md)** · **[📖 Documentation (English)](docs/en/README.md)**

| 中文 | English |
|------|---------|
| [配置](docs/zh/configuration.md) | [Configuration](docs/en/configuration.md) |
| [Bridge Payload](docs/zh/bridge-payload.md) | [Bridge Payload](docs/en/bridge-payload.md) |
| [私有桶](docs/zh/private-bucket.md) | [Private bucket](docs/en/private-bucket.md) |
| [架构与实现](docs/zh/architecture.md) | [Architecture](docs/en/architecture.md) |

---

## 许可证

MIT

## 参与贡献

欢迎 Pull Request。较大改动请先开 Issue 讨论。

## 致谢

- [Reflex](https://reflex.dev)
- [Cloudflare R2](https://developers.cloudflare.com/r2/)
