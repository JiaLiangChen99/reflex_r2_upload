# 配置

**语言:** [中文](../README.md) · [English](../en/configuration.md)

| [文档首页](../README.md) | **配置** | [Bridge](bridge-payload.md) | [私有桶](private-bucket.md) | [架构](architecture.md) |

---

需要 Cloudflare R2 凭证，**二选一**（代码配置优先于环境变量）。

## 方式一：环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `R2_ACCOUNT_ID` | 是 | Cloudflare 账号 ID |
| `R2_ACCESS_KEY_ID` | 是 | R2 API 令牌 |
| `R2_SECRET_ACCESS_KEY` | 是 | R2 API 令牌 |
| `R2_BUCKET_NAME` | 是 | 桶名 |
| `R2_PUBLIC_BASE_URL` | 否 | 公开 CDN / 自定义域名 |
| `REFLEX_R2_ROUTE_PREFIX` | 否 | 保留路由前缀，默认 `/_reflex_r2_upload` |
| `REFLEX_R2_PRESIGN_EXPIRES` | 否 | 上传 presigned URL 有效期（秒），默认 600 |
| `REFLEX_R2_GET_EXPIRES` | 否 | 私有读 presigned URL 有效期（秒），默认 3600 |

本地开发可用 `export` 或 `.env` + `python-dotenv`；部署时由平台密钥管理注入。

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
)

r2.wrap_app(app, r2_config=r2_config)
# 或：r2.configure_r2(r2_config)
```

## R2 桶 CORS

浏览器直传需在 R2 控制台为桶配置 CORS，允许你的站点 Origin 对存储端点执行 `PUT`。

## 检查配置是否就绪

```bash
# 启动应用后
curl http://localhost:8000/_reflex_r2_upload/config
```

返回 `"ready": true` 表示凭证齐全。

---

| [← 文档首页](../README.md) | [Bridge Payload →](bridge-payload.md) |
