# 配置

**语言:** [中文](../README.md) · [English](../en/configuration.md)

| [文档首页](../README.md) | **配置** | [安全](security.md) | [Bridge](bridge-payload.md) | [架构](architecture.md) |

---

需要 Cloudflare R2 凭证，**二选一**（代码配置优先于环境变量）。

## 方式一：环境变量

### R2 凭证

| 变量 | 必填 | 默认 | 说明 |
|------|------|------|------|
| `R2_ACCOUNT_ID` | 是 | — | Cloudflare 账号 ID |
| `R2_ACCESS_KEY_ID` | 是 | — | R2 API 令牌 Access Key |
| `R2_SECRET_ACCESS_KEY` | 是 | — | R2 API 令牌 Secret |
| `R2_BUCKET_NAME` | 是 | — | 桶名 |
| `R2_PUBLIC_BASE_URL` | 否 | — | 公开 CDN / 自定义域名；私有桶留空 |

### 路由与 URL 有效期

| 变量 | 必填 | 默认 | 说明 |
|------|------|------|------|
| `REFLEX_R2_ROUTE_PREFIX` | 否 | `/_reflex_r2_upload` | 保留 API 前缀 |
| `REFLEX_R2_PRESIGN_EXPIRES` | 否 | `600` | 上传 presigned URL TTL（秒），最小 60 |
| `REFLEX_R2_GET_EXPIRES` | 否 | `3600` | 私有读 URL 最大 TTL（秒）；实际 `expiresIn` 下限 60 |

### 上传安全

| 变量 | 必填 | 默认 | 说明 |
|------|------|------|------|
| `REFLEX_R2_UPLOAD_SECRET` | 否 | 自动派生 | upload token 与 bridge 签名 HMAC 密钥 |
| `REFLEX_R2_UPLOAD_TOKEN_TTL` | 否 | `7200` | upload token 有效期（秒） |
| `REFLEX_R2_REQUIRE_UPLOAD_TOKEN` | 否 | `1` | `presign` / `complete` / `signed-read` 需 token |
| `REFLEX_R2_REQUIRE_BRIDGE_SIGNATURE` | 否 | `1` | `parse_upload_payload` 验 bridge 签名 |
| `REFLEX_R2_MAX_UPLOAD_BYTES` | 否 | `104857600` | 单文件上限（100 MiB）；`0` = 不限制 |
| `REFLEX_R2_RATE_LIMIT_REQUESTS` | 否 | `60` | 每 IP 窗口内 API 请求数；`0` = 关闭限流 |
| `REFLEX_R2_RATE_LIMIT_WINDOW` | 否 | `60` | 限流窗口（秒） |
| `REFLEX_R2_VERBOSE_CONFIG` | 否 | `0` | `1` 时 `/config` 返回 `missingEnv` 等诊断字段 |

本地开发可用 `export` 或 `.env` + `python-dotenv`；部署时由平台密钥管理注入。

参考模板：[`.env.example`](../../.env.example)

## 方式二：`R2Config`

```python
import reflex_r2_upload as r2

r2_config = r2.R2Config(
    account_id="...",
    access_key_id="...",
    secret_access_key="...",
    bucket_name="my-bucket",
    public_base_url="https://assets.example.com",  # 可选
    presign_expires=600,
    get_expires=3600,
    route_prefix="/_reflex_r2_upload",
    upload_secret="",  # 可选；空则从 R2 凭证派生
    require_upload_token=True,
    upload_token_ttl=7200,
    require_bridge_signature=True,
    allowed_key_prefixes=("uploads/", "avatars/"),
    max_upload_bytes=50 * 1024 * 1024,
    rate_limit_requests=60,
    rate_limit_window_seconds=60,
    verbose_config=False,
)

r2.wrap_app(app, r2_config=r2_config)
# 或：r2.configure_r2(r2_config)
```

## `wrap_app` 参数

| 参数 | 说明 |
|------|------|
| `r2_config` | `R2Config` 实例 |
| `backend_base` | 显式后端 origin（开发环境前后端分离时） |
| `route_prefix` | 覆盖保留路由前缀 |
| `presign_expires` | 注入前端的 presign TTL 提示 |
| `require_upload_token` | 覆盖是否强制 upload token |
| `require_bridge_signature` | 覆盖是否验 bridge 签名 |
| `allowed_key_prefixes` | API 接受的 `keyPrefix` 白名单 |
| `presign_guard` | 自定义鉴权 guard（见 [安全](security.md)） |

```python
r2.wrap_app(
    app,
    r2_config=r2_config,
    presign_guard=r2.make_user_key_prefix_guard(get_user_id),
)
```

运行时覆盖（无需重建 `R2Config`）：

```python
r2.configure_upload_auth(require_upload_token=True, require_bridge_signature=True)
r2.configure_allowed_key_prefixes(["uploads/"])
```

## R2 桶 CORS

浏览器直传需在 R2 控制台为桶配置 CORS，允许你的站点 Origin 对存储端点执行 `PUT`。

## 检查配置是否就绪

```bash
curl http://localhost:8000/_reflex_r2_upload/config
```

默认响应：

```json
{ "ready": true }
```

设置 `REFLEX_R2_VERBOSE_CONFIG=1` 后额外返回 `missingEnv`、`publicBaseUrl`、`routePrefix`。

---

| [← 文档首页](../README.md) | [安全 →](security.md) | [Bridge Payload →](bridge-payload.md) |
