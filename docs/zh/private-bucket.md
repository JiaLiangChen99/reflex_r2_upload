# 私有桶（Private Bucket）访问指南

**语言:** [中文](../README.md) · [English](../en/private-bucket.md)

| [文档首页](../README.md) | [配置](configuration.md) | [Bridge](bridge-payload.md) | **私有桶** | [架构](architecture.md) |

---

上传流程与公开桶 **完全相同**（presign → PUT → complete）。差异在 **读访问**：

| 模式 | 配置 | bridge `publicUrl` | 读访问方式 |
|------|------|-------------------|------------|
| 公开桶 | `R2_PUBLIC_BASE_URL` 或 `R2Config.public_base_url` | CDN URL | 直接用 `publicUrl` |
| 私有桶 | 不配置公开域名 | `null` | 服务端 `signed_read_url()` |

## 上传后处理（Python）

```python
import reflex_r2_upload as r2

@rx.event
def on_uploaded(self, payload_json: r2.UploadPayloadJson):
    result = r2.parse_upload_payload(payload_json)
    file = result.file

    if file.public_url:
        self.display_url = file.public_url
    else:
        self.storage_path = file.storage_path
        self.key_prefix = result.key_prefix
```

## 生成临时读链接（推荐：服务端 helper）

```python
# 生产环境：先校验当前用户是否有权读取 storage_path
url = r2.signed_read_url(file.storage_path)

url = r2.signed_read_url(file.storage_path, expires_in=300)
```

`expires_in` 会被限制在 **60 秒** 与 `REFLEX_R2_GET_EXPIRES`（默认 3600 秒）之间。

`signed_read_url()` 不经 HTTP 路由，不受 upload token 约束，但 **你必须在调用前自行鉴权**。

## HTTP 保留路由（需 upload token）

`POST /_reflex_r2_upload/signed-read`

```json
{
  "keyPrefix": "demo/uploads",
  "storagePath": "demo/uploads/model.glb",
  "uploadToken": "...",
  "expiresIn": 3600
}
```

与 `presign` 相同，需要有效的 **upload token** 和（若配置）**presign_guard**。`expiresIn` 会被 clamp 到 `[60, REFLEX_R2_GET_EXPIRES]`。

生产环境更推荐在 Reflex 事件中调用 `signed_read_url()`，在 helper 调用前完成业务层读权限校验。

## 相关配置

见 [configuration.md](configuration.md) 中的 `R2_PUBLIC_BASE_URL`、`REFLEX_R2_GET_EXPIRES`。鉴权机制见 [security.md](security.md)。

---

| [← Bridge Payload](bridge-payload.md) | [文档首页](../README.md) | [架构 →](architecture.md) |
