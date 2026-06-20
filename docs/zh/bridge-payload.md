# Bridge Payload 契约（Version 1）

**语言:** [中文](../README.md) · [English](../en/bridge-payload.md)

| [文档首页](../README.md) | [配置](configuration.md) | [安全](security.md) | **Bridge** | [架构](architecture.md) |

---

`upload_zone` 通过隐藏 input 将 JSON 传给 `on_success`。应用侧请使用 `parse_upload_payload()` 解析为 `UploadResult` / `UploadedFile`。

默认会验证服务端签发的 **`bridgeSignature`**（见 [安全](security.md)）。

## 顶层字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `version` | `int` | 固定为 `1` |
| `error` | `bool` | `false` 成功，`true` 失败 |

## 成功 — 单文件（扁平）

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
  "publicUrl": "https://cdn.example.com/demo/uploads/model.glb",
  "bridgeSignature": "..."
}
```

`publicUrl` 在未配置公开域名时为 `null`。私有桶见 [private-bucket.md](private-bucket.md)。

`bridgeSignature` 由 `/complete` 响应签发，JS 透传到 bridge JSON。`parse_upload_payload()` 默认验签。

## 成功 — 多文件

```json
{
  "version": 1,
  "error": false,
  "keyPrefix": "demo/uploads",
  "files": [
    {
      "version": 1,
      "error": false,
      "ok": true,
      "keyPrefix": "demo/uploads",
      "storagePath": "demo/uploads/a.glb",
      "originalFilename": "a.glb",
      "fileSizeBytes": 100,
      "contentType": "model/gltf-binary",
      "publicUrl": null,
      "bridgeSignature": "..."
    }
  ]
}
```

## 失败

```json
{
  "version": 1,
  "error": true,
  "message": "R2 未配置，缺少：R2_BUCKET_NAME",
  "code": "R2_NOT_CONFIGURED"
}
```

### 错误码（`code`）

| 值 | 含义 |
|----|------|
| `R2_NOT_CONFIGURED` | 缺少 R2 凭证 |
| `CONFIG_FETCH_FAILED` | 无法读取 `/_reflex_r2_upload/config` |
| `UPLOAD_FAILED` | 通用上传失败 |
| `STORAGE_PUT_FAILED` | 浏览器 PUT R2 失败 |
| `CORS_BLOCKED` | 疑似 R2 CORS 未配置 |
| `UNAUTHORIZED` | upload token 或 guard 鉴权失败 |
| `INVALID_SIGNATURE` | bridge 签名无效或缺失（`parse_upload_payload`） |
| `EXTENSION_NOT_ALLOWED` | 扩展名不在 token 白名单内 |
| `INVALID_PAYLOAD` | JSON 结构无效或解析失败 |

## Python 用法

```python
import reflex_r2_upload as r2

@rx.event
def on_uploaded(self, payload_json: r2.UploadPayloadJson):
    try:
        result = r2.parse_upload_payload(payload_json)
    except r2.UploadPayloadError as error:
        print(error.code, error.message)
        return

    file = result.file
    # file.key_prefix, file.storage_path, file.public_url (Optional)
```

关闭 bridge 验签（仅开发）：

```python
r2.wrap_app(app, require_bridge_signature=False)
```

## 不包含的字段（刻意）

- 用户 ID、业务 entity ID → 放在 `key_prefix` 或 Reflex State
- R2 bucket、account → 仅服务端配置
- presigned PUT URL、upload token → 短命敏感，不进入 bridge

---

| [← 安全](security.md) | [文档首页](../README.md) | [私有桶 →](private-bucket.md) |
