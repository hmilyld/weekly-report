# 安全政策

## 支持范围

维护最新 `1.x` 版本（默认分支 `main`）。更早的版本不再接收安全修复。

## 报告漏洞

请勿公开提交 Issue。通过 GitHub 私密漏洞报告通道提交：

- 仓库页面 **Security → Report a vulnerability**
- 或直接访问 <https://github.com/hmilyld/weekly-report/security/advisories/new>

报告应包含：受影响版本或提交、复现步骤、影响范围（是否可读取他人数据、是否可绕过认证、
是否泄露密钥）、以及建议的修复方向。

## 覆盖范围

- 认证与授权：JWT、API Token、`password_version` 失效机制、管理员权限校验
- 加密：信封加密（DEK 包装、AAD 绑定）、密文写入是否可能回退为明文
- 数据隔离：跨用户读写日报、周报、月报与待办
- 注入与 SSRF：SQL 拼接、大模型地址校验
- 依赖漏洞：`backend/requirements.txt` 与 `frontend/pnpm-lock.yaml` 中的已知 CVE

## 已知的设计取舍

以下行为是当前版本的有意设计，已在 README「安全与备份」中说明，不属于漏洞：

- 内容使用 AES-GCM 信封加密。主密钥 `ENCRYPTION_MASTER_KEY` 必须与数据库一起备份；
  丢失主密钥后内容不可恢复。
- API Token 长期有效且无作用域限制。修改密码不会吊销 Token，需通过 `DELETE /api/v1/tokens`
  显式吊销。

若认为上述取舍在特定部署场景下带来可利用风险，请按上述通道报告，维护者会在文档中更新说明。

## 已知依赖风险

扫描命令：

```bash
uvx pip-audit -r backend/requirements.txt
cd frontend && pnpm audit --prod --registry https://registry.npmjs.org
```

默认镜像源（npmmirror）未实现 audit 端点，因此 npm 侧必须显式指定 registry。

| 依赖 | 公告 | 当前处置 |
|---|---|---|
| `python-jose` 3.5.0 | PYSEC-2026-4298：HMAC 初始化接受未加 PEM 包装的非对称公钥；在算法未显式限制时，可用服务公钥伪造 HS256 Token | 本项目仅使用 HS256 与对称密钥，`jwt.decode(..., algorithms=[...])` 显式限制算法，且不配置非对称密钥，该路径不可达。根治方案为迁移到 PyJWT |
| `ecdsa` 0.19.2 | PYSEC-2026-1325：P-256 曲线上的 Minerva 时序攻击，仅在调用 `SigningKey.sign_digest()` 时成立 | 项目不生成也不校验 ECDSA 签名；该包仅为 python-jose 的传递依赖，不在执行路径上 |
| `react-router` 6.30.6（经 `react-router-dom`） | 开放重定向（`<Link>`、`useNavigate` 反斜杠处理）与 SSR 水合 `deserializeErrors()` 构造器注入；修复版本为 7.18.0 及以上 | 应用为纯客户端渲染，无 SSR 水合路径；导航目标全部来自代码内固定路由，不接受用户输入 |
| `starlette` | 旧版本存在 7 条 PYSEC 公告 | 已随 FastAPI 0.165.0 升级到 1.10.0，全部修复 |

## 处理流程

1. 维护者确认收到报告，通常在七个工作日内回复。
2. 评估影响并给出修复计划；必要时先发布缓解措施。
3. 修复发布后在 advisory 中公开说明，并按需为报告者署名。
