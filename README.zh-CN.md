# reflex-r2-upload

**Language:** [English](README.md) · **中文**

**源码与文档：** [GitHub](https://github.com/JiaLiangChen99/reflex_r2_upload) · [文档首页](docs/README.md) · [Documentation (English)](docs/en/README.md)

Reflex 自定义组件：在 Reflex 应用里把文件 **直传** 到 **Cloudflare R2**（presigned PUT），大文件不经 Python 后端中转。

**能做什么**

- `upload_zone` 上传区域（预设样式或无样式 `.root`）
- `wrap_app(app)` 一行接入 Reflex（注入 JS + 挂载 Starlette 路由）
- `parse_upload_payload` 解析上传完成回调（路径、文件名、可选公开 URL）
- 公开 CDN 读，或私有桶 `signed_read_url()` 临时读
- **内置上传安全机制** — token、bridge 签名、大小上限、限流（见 [安全](docs/zh/security.md)）

---

## 安装

```bash
pip install reflex-r2-upload
```

---

## 快速开始

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
            key_prefix="demo/uploads",
            accept=".glb,model/gltf-binary",
            allowed_extensions=[".glb"],
            content_type="model/gltf-binary",
            on_success=State.on_uploaded,
        ),
        padding="2em",
    )


app = rx.App()
app.add_page(index)
r2.wrap_app(app)  # 默认开启安全选项
```

说明：

1. 引入 `reflex_r2_upload`，在页面中使用 `upload_zone`（`key_prefix` 为桶内路径前缀）。
2. `add_page` 后调用 **`wrap_app(app)`**。
3. 用 **`parse_upload_payload`** 解析 `on_success` 回调 JSON。

无默认样式的上传区：

```python
r2.upload_zone.root(
    rx.vstack(rx.icon("upload"), rx.text("拖放或点击选择"), spacing="2", align="center"),
    key_prefix="demo/uploads",
    allowed_extensions=[".glb"],
    content_type="model/gltf-binary",
    on_success=State.on_uploaded,
    class_name="rounded-xl border-2 border-dashed p-8",
)
```

---

## 配置

需要 Cloudflare R2 凭证。R2 桶需配置 **CORS**，允许站点 Origin 对存储端点发 `PUT`。

### 方式一：环境变量

复制 [`.env.example`](.env.example) 并填写 R2 凭证。

| 变量 | 必填 | 默认 | 说明 |
|------|------|------|------|
| `R2_ACCOUNT_ID` | 是 | — | Cloudflare 账号 ID |
| `R2_ACCESS_KEY_ID` | 是 | — | R2 API 令牌 |
| `R2_SECRET_ACCESS_KEY` | 是 | — | R2 API 令牌 |
| `R2_BUCKET_NAME` | 是 | — | 桶名 |
| `R2_PUBLIC_BASE_URL` | 否 | — | 公开 CDN / 自定义域名 |
| `REFLEX_R2_ROUTE_PREFIX` | 否 | `/_reflex_r2_upload` | 保留 API 前缀 |
| `REFLEX_R2_PRESIGN_EXPIRES` | 否 | `600` | 上传 URL 有效期（秒） |
| `REFLEX_R2_GET_EXPIRES` | 否 | `3600` | 私有读 URL 最大 TTL（秒） |
| `REFLEX_R2_UPLOAD_SECRET` | 否 | 自动派生 | upload token 与 bridge 签名密钥 |
| `REFLEX_R2_UPLOAD_TOKEN_TTL` | 否 | `7200` | upload token 有效期（秒） |
| `REFLEX_R2_MAX_UPLOAD_BYTES` | 否 | `104857600` | 单文件上限（100 MiB）；`0` = 不限制 |
| `REFLEX_R2_RATE_LIMIT_REQUESTS` | 否 | `60` | 每 IP 窗口内 API 请求数；`0` = 关闭 |
| `REFLEX_R2_RATE_LIMIT_WINDOW` | 否 | `60` | 限流窗口（秒） |
| `REFLEX_R2_REQUIRE_UPLOAD_TOKEN` | 否 | `1` | presign/complete/signed-read 需 upload token |
| `REFLEX_R2_REQUIRE_BRIDGE_SIGNATURE` | 否 | `1` | 回调 JSON 需服务端 `bridgeSignature` |
| `REFLEX_R2_VERBOSE_CONFIG` | 否 | `0` | `GET /config` 返回诊断字段 |

### 方式二：`R2Config`

```python
r2_config = r2.R2Config(
    account_id="...",
    access_key_id="...",
    secret_access_key="...",
    bucket_name="my-bucket",
    public_base_url="https://assets.example.com",  # 可选
    max_upload_bytes=50 * 1024 * 1024,
    allowed_key_prefixes=("uploads/",),
)

r2.wrap_app(app, r2_config=r2_config)
```

代码配置优先于环境变量。密钥只应存在于服务端，不要放进前端或 `rx.State`。

完整说明：[配置](docs/zh/configuration.md)

---

## 上传流程

```
浏览器 → GET /config（是否 ready）
      → POST /presign（uploadToken + fileSizeBytes）
      → PUT R2（presigned URL，Content-Length 绑定）
      → POST /complete（head_object 校验对象存在）
      → on_success bridge JSON（服务端签名）
      → Reflex State 中 parse_upload_payload()
```

详见 [架构与实现](docs/zh/architecture.md)、[Bridge Payload](docs/zh/bridge-payload.md)。

---

## 生产环境加固

库默认已开启 upload token、bridge 签名、大小上限与限流。对**登录用户**应用，建议绑定用户专属 prefix：

```python
def get_user_id(request):
    # 从 Reflex session / JWT / Cookie 读取
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

可选 prefix 白名单：

```python
r2.wrap_app(app, allowed_key_prefixes=["demo/uploads", "avatars/"])
```

私有读 — 优先在 Reflex 事件里调用 helper，而非暴露 HTTP 路由：

```python
@rx.event
def preview(self):
    # 签发前先校验读权限
    self.temp_url = r2.signed_read_url(self.storage_path, expires_in=300)
```

完整指南：[安全](docs/zh/security.md)

---

## 公开读 vs 私有读

| 模式 | 配置 | bridge `publicUrl` | 读访问 |
|------|------|-------------------|--------|
| 公开 CDN | 配置 `R2_PUBLIC_BASE_URL` | CDN URL | 直接用 `file.public_url` |
| 私有桶 | 不配置公开域名 | `null` | Reflex 事件中 `signed_read_url()` |

见 [私有桶](docs/zh/private-bucket.md)。

---

## API 一览

| 符号 | 作用 |
|------|------|
| `wrap_app(app, ...)` | 集成入口 |
| `R2Config` / `configure_r2` | 代码方式配置凭证与选项 |
| `upload_zone` / `upload_zone.root` | 上传组件 |
| `parse_upload_payload` | 解析带签名的上传回调 |
| `signed_read_url` | 私有桶临时读 URL（服务端） |
| `issue_upload_token` | 手动签发 upload token |
| `make_user_key_prefix_guard` | 生产环境按用户绑定 prefix |
| `make_allowed_key_prefixes_guard` | prefix 白名单 guard |
| `user_key_prefix` | 生成 `uploads/{user_id}` 风格 prefix |
| `is_public_access_configured()` | 是否配置了公开 CDN |

---

## 文档

| 中文 | English |
|------|---------|
| [文档首页](docs/README.md) | [Docs home](docs/en/README.md) |
| [配置](docs/zh/configuration.md) | [Configuration](docs/en/configuration.md) |
| [安全](docs/zh/security.md) | [Security](docs/en/security.md) |
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
