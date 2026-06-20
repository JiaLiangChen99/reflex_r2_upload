# 安全机制与生产部署

**语言:** [中文](../README.md) · [English](../en/security.md)

| [文档首页](../README.md) | [配置](configuration.md) | **安全** | [Bridge](bridge-payload.md) | [架构](architecture.md) |

---

本库默认开启多项上传安全机制。开放 Demo 可共享 `key_prefix`；**登录应用**应额外绑定用户身份与读权限。

## 内置安全（默认开启）

| 机制 | 作用 |
|------|------|
| **upload token** | HMAC 令牌绑定 `keyPrefix`、扩展名白名单、Content-Type；`presign` / `complete` / `signed-read` 需携带 |
| **bridge 签名** | `/complete` 响应含 `bridgeSignature`；`parse_upload_payload()` 默认验签，防伪造回调 |
| **对象存在校验** | `complete` 调用 `head_object`，校验对象存在且 `fileSizeBytes` 与 R2 `ContentLength` 一致 |
| **大小上限** | `REFLEX_R2_MAX_UPLOAD_BYTES`（默认 100 MiB）；presign 绑定 `ContentLength` |
| **Content-Type 策略** | 危险类型 blocklist；扩展名与 MIME 匹配；token 绑定的类型优先于客户端 |
| **限流** | 按 IP 限制 API 请求（默认 60 次 / 60 秒），超限返回 429 |
| **/config 最小化** | 默认仅 `{ "ready": bool }`；诊断字段需 `REFLEX_R2_VERBOSE_CONFIG=1` |

关闭 token 或 bridge 验签（`REFLEX_R2_REQUIRE_*=0`）**仅用于本地调试**。

## upload token 流程

1. `upload_zone` 渲染时服务端签发 token，写入 `data-upload-token`
2. 浏览器 JS 在 `presign` / `complete` 请求体中携带 `uploadToken`
3. 服务端验证签名、过期时间、`keyPrefix` 与 token 内 `p` 一致
4. 扩展名（`e`）与 Content-Type（`c`）以 token 为准；**presign 忽略客户端 `allowedExtensions`**

手动签发（高级场景）：

```python
token = r2.issue_upload_token(
    key_prefix="uploads/user-42",
    allowed_extensions=[".png", ".jpg"],
    content_type="image/png",
)
```

## bridge 签名

`/complete` 成功响应示例字段：

```json
{
  "storagePath": "demo/uploads/model.glb",
  "bridgeSignature": "..."
}
```

JS 将 `bridgeSignature` 透传到 `on_success` JSON。Python 侧：

```python
result = r2.parse_upload_payload(payload_json)  # 默认验签
```

验签失败 → `UploadPayloadError`，`code=INVALID_SIGNATURE`。

关闭验签（仅开发）：

```python
r2.wrap_app(app, require_bridge_signature=False)
# 或 REFLEX_R2_REQUIRE_BRIDGE_SIGNATURE=0
```

## 生产环境：绑定用户 prefix

Demo 中所有访客可共用 `demo/uploads`。生产环境应让 **已登录用户** 只能写入自己的目录：

```python
def get_user_id(request):
    # 从 Reflex session / JWT / Cookie 读取
    ...

r2.wrap_app(
    app,
    presign_guard=r2.make_user_key_prefix_guard(get_user_id),
)

# 页面上的 prefix 必须与当前用户一致
r2.upload_zone(
    key_prefix=r2.user_key_prefix(current_user_id),
    on_success=State.on_uploaded,
)
```

### prefix 白名单

限制 API 接受的 `keyPrefix`：

```python
r2.wrap_app(app, allowed_key_prefixes=["avatars/", "uploads/"])
# 或 R2Config(allowed_key_prefixes=("avatars/", "uploads/"))
```

### 自定义 guard

```python
async def my_guard(request, data) -> bool:
    key_prefix = str(data.get("keyPrefix", ""))
    # 自定义鉴权逻辑
    return True

r2.wrap_app(app, presign_guard=my_guard)
```

`presign_guard` 同时作用于 `presign`、`complete`、`signed-read`。

## 私有读访问

HTTP 路由 `POST /signed-read` 与 presign 相同，需 **upload token + guard**。

**推荐**：在 Reflex 事件中调用 `signed_read_url()`，先校验业务读权限再签发：

```python
@rx.event
def preview(self):
    if not self.user_can_read(self.storage_path):
        return
    self.temp_url = r2.signed_read_url(self.storage_path, expires_in=300)
```

`expiresIn` 被限制在 `[60, REFLEX_R2_GET_EXPIRES]` 秒。

## 业务层仍需自行负责

| 项 | 说明 |
|----|------|
| 用户登录态 | `presign_guard` 需读取真实 session，库不提供登录 UI |
| 读权限 | `signed_read_url()` 前校验谁可读该 `storagePath` |
| 密钥管理 | R2 凭证、`REFLEX_R2_UPLOAD_SECRET` 仅存服务端 |
| CORS | R2 桶需允许站点 Origin 的 `PUT` |
| `on_error` | `upload_zone` 的 `on_error` 参数尚未实现 |

## 相关配置

完整环境变量见 [配置](configuration.md)。与安全直接相关的项：

| 变量 | 默认 | 说明 |
|------|------|------|
| `REFLEX_R2_UPLOAD_SECRET` | 从 R2 凭证派生 | HMAC 密钥 |
| `REFLEX_R2_UPLOAD_TOKEN_TTL` | `7200` | token 有效期（秒） |
| `REFLEX_R2_REQUIRE_UPLOAD_TOKEN` | `1` | 是否强制 token |
| `REFLEX_R2_REQUIRE_BRIDGE_SIGNATURE` | `1` | 是否验 bridge 签名 |
| `REFLEX_R2_MAX_UPLOAD_BYTES` | `104857600` | 单文件上限 |
| `REFLEX_R2_RATE_LIMIT_REQUESTS` | `60` | 限流阈值；`0` 关闭 |
| `REFLEX_R2_RATE_LIMIT_WINDOW` | `60` | 限流窗口（秒） |
| `REFLEX_R2_VERBOSE_CONFIG` | `0` | `/config` 是否返回诊断字段 |

---

| [← 配置](configuration.md) | [文档首页](../README.md) | [Bridge Payload →](bridge-payload.md) |
