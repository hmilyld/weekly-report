# 安全政策

## 支持范围

当前仅维护最新的 `1.x` 版本（默认分支 `main`）。更早的版本不再接收安全修复。

## 如何报告漏洞

**请不要公开提交 issue。**

请通过 GitHub 的私密漏洞报告通道提交：

- 打开 <https://github.com/hmilyld/weekly-report/security/advisories/new>
- 或进入仓库 **Security → Report a vulnerability**

报告中请尽量包含：受影响版本或提交、复现步骤、影响面（是否可读取他人数据 / 是否可绕过认证 / 是否泄露密钥）、以及你建议的修复方向。

## 我们关注的范围

- 认证与授权：JWT、API Token、`password_version` 失效机制、管理员权限校验
- 加密：信封加密（DEK 包装、AAD 绑定）、密文写入是否可能回退为明文
- 数据隔离：跨用户读写日报 / 周报 / 月报 / 待办
- 注入与 SSRF：SQL 拼接、大模型地址校验
- 依赖漏洞：`backend/requirements.txt` 与 `frontend/pnpm-lock.yaml` 中的已知 CVE

## 已知的设计取舍

以下行为是当前版本的**有意设计**，已在 README「安全与备份」中说明，不属于漏洞：

- 内容使用 AES-GCM 信封加密，主密钥 `ENCRYPTION_MASTER_KEY` 与数据库必须一起备份；丢失主密钥不可恢复
- API Token 为长期有效、无作用域限制；修改密码不会吊销 Token，需显式 `DELETE /api/v1/tokens`

如果你认为上述取舍带来了具体的可利用风险，欢迎按上面的通道报告，我们会在文档中更新说明。

## 处理流程

1. 维护者确认收到报告（通常一周内）
2. 评估影响并给出修复计划；必要时先发布缓解措施
3. 修复发布后在 advisory 中公开说明，并按需为报告者署名
