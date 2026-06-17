# reflex-r2-upload 文档

**语言 Language:** **中文** · [English](en/README.md)

[项目 README](../README.zh-CN.md) · [Project README (English)](../README.md)

---

## 快速导航

| 文档 | 说明 |
|------|------|
| [配置](zh/configuration.md) | 环境变量与 `R2Config` |
| [Bridge Payload](zh/bridge-payload.md) | 上传回调 JSON 契约（v1） |
| [私有桶](zh/private-bucket.md) | 无 CDN 时的读访问 |
| [架构与实现](zh/architecture.md) | 原理、数据流、保留路由 |

## 阅读路径

**首次接入**

1. [配置](zh/configuration.md) — 提供 R2 凭证  
2. 根目录 [README](../README.md) — 安装与 `wrap_app` 用法  
3. [Bridge Payload](zh/bridge-payload.md) — 解析 `on_success` 回调  

**公开 CDN vs 私有桶**

- 配置了 `R2_PUBLIC_BASE_URL` → [Bridge Payload](zh/bridge-payload.md) 中的 `publicUrl`  
- 未配置公开域名 → [私有桶](zh/private-bucket.md)  

**二次开发 / 贡献**

- [架构与实现](zh/architecture.md)

---

[English documentation](en/README.md) · [项目 README](../README.md)
