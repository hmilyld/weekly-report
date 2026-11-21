# 架构说明

本文面向需要修改后端、加密逻辑或部署方式的开发者。安装与使用见 [`README.md`](../README.md)，
目录结构与命令见 [`AGENTS.md`](../AGENTS.md)，视觉系统见 [`DESIGN.md`](../DESIGN.md)。

## 1. 运行形态

单容器、单进程、单文件数据库。

```
浏览器 / Android 客户端
        │ HTTPS（由反向代理终止）
        ▼
┌──────────────────────────────────────────────┐
│ uvicorn + FastAPI（:18001）                  │
│   /api/v1/*     → routers                    │
│   其他路径       → frontend/dist 静态资源     │
└──────────────────────────────────────────────┘
        │
        ▼
   ./data/weekly_report.db（SQLite，WAL 模式）
```

- 前端构建产物打包在镜像内，由后端统一托管，因此仅暴露一个端口。
- 系统不依赖 Redis、消息队列或对象存储；运行状态只存在于数据库与加密主密钥中。
- `./data` 是唯一需要持久化的目录。备份必须同时包含数据库与 `ENCRYPTION_MASTER_KEY`。

## 2. 模块边界

| 层 | 位置 | 职责 | 约束 |
|---|---|---|---|
| HTTP | `app/routers/` | 参数校验、状态码、响应模型 | 不拼接 SQL，不直接处理加密 |
| 持久化 | `app/crud/` | 查询、写入、级联删除 | 不决定 HTTP 状态码 |
| 模型 | `app/models.py`、`app/schemas.py` | ORM 模型与对外契约 | 不承载业务判断 |
| 横切 | `auth`、`crypto`、`envelope`、`encryption_utils`、`key_cache`、`migration`、`date_range`、`llm_client` | 认证、加密、迁移、大模型调用 | 不依赖 `routers` |

前端采用对应分层：`api/`（HTTP 封装）、`pages/`（路由页面）、`components/`（`ui/` 通用组件，
`tasks/` 与 `settings/` 业务组件）、`contexts/`（认证与主题）、`utils/`（纯函数）。
页面负责组合组件、发起请求与管理页面状态；跨页面共享的状态放入 context。

## 3. 请求链路

使用 JWT 的网页请求：

1. `api/index.js` 的请求拦截器从 `localStorage.token` 注入 `Authorization: Bearer ...`。
2. `get_current_user` 或数据接口使用的 `get_authenticated_user` 解析 `sub` 与 `pwd_ver`。
3. 校验 `pwd_ver` 与 `users.password_version` 是否一致；修改密码后旧 JWT 立即失效。
4. router 调用 `crud`，密文在返回前解密为明文对象。
5. 响应拦截器遇到 `401` 触发重新登录；`402` 表示当前密码错误，不触发登出。

使用 API Token 的脚本请求走同一套路由，凭据为 `X-API-Token`，由 `get_authenticated_user` 处理。
同时携带 JWT 与 Token 时以 JWT 为准，JWT 无效时不会回退到 Token。Token 仅可访问数据接口，
访问认证、配置、用户与 Token 管理接口返回 `401`。

状态码语义：`401` 表示凭据缺失或无效，`402` 表示会话有效但当前密码错误，`403` 表示已认证
但权限不足，`409` 表示加密密钥缺失（`encryption_key_missing`）或内容无法解密（`decryption_failed`）。

## 4. 加密链路

```
ENCRYPTION_MASTER_KEY（32 字节，base64）
        │ HKDF
        ▼
       KEK ── 包装 ──▶ users.wrapped_dek（AAD 绑定该用户）
                           │ 启动时解包
                           ▼
                     key_cache[user_id] = DEK
                           │
        明文 ── AES-GCM（DEK，AAD = 表名 + 用户）──▶ content_encrypted / nonce / tag
```

- 启动时 `load_all_user_deks()` 解包全部 DEK 并缓存，重启后无需任何人重新登录。
- 写入时若该用户没有 DEK，抛出 `EncryptionKeyMissingError` 并返回 `409`；不存在写入明文的路径。
- 未迁移的老用户（`wrapped_dek` 为 NULL）在登录时一次性迁移。迁移失败不阻塞登录，
  但读取结果会带失败标记，写入返回 `409`。
- 迁移前生成一次 `data/pre-envelope-*.db` 快照（权限 0600），作为回滚点。
- `AppConfig.api_key` 采用同样的 KEK 包装（`ek1:` 前缀）；旧格式值在启动时重新包装。
- 解密后的对象通过 `set_committed_value` 写回属性，避免明文被 ORM 自动回写。

`app/auth.py` 中遗留 KDF（`derive_user_key`）的参数已冻结：它决定历史密文能否解密，
修改参数会导致既有数据永久不可读。

## 5. 启动顺序

`main.py` 的 lifespan 依次执行，任一步失败即拒绝启动：

1. `init_database()`：创建表、补列（`schema_migrations`）、迁移前快照、清理明文残留、写入种子配置。
2. `get_kek()`：校验主密钥；生产环境缺失时直接失败。
3. `migrate_app_config_secret()`：将旧格式的 LLM API Key 重新包装。
4. `load_all_user_deks()`：恢复全部 DEK 到内存缓存。

数据库迁移是增量式的，只新增列与表，不删除列、不修改类型，随启动自动完成，不使用 Alembic。

## 6. 报告生成链路

1. 用户按天记录日报，明文写入，加密后入库。
2. 生成周报或月报时，router 取出该周期的日报并解密，拼接为提示词。
3. `llm_client` 调用 OpenAI 兼容接口。接口地址来自 `AppConfig`，调用前做 SSRF 校验：
   允许 loopback（自建 Ollama），拒绝私网、链路本地与保留地址。
4. 生成结果加密后写入 `weekly_reports` 或 `monthly_reports`。

各类失败（超时、HTTP 非 2xx、响应结构异常、连接失败）分别映射为独立错误信息。
`POST /weekly/{week_start}?force=false` 在报告已存在时返回 `generated=false`，不调用模型。

## 7. 数据模型

```
users 1──N daily_reports
      1──N weekly_reports
      1──N monthly_reports
      1──N tasks
      1──N api_tokens
app_config（单行，id = 1）
```

内容表的明文列仅存在于迁移前的旧库中；写入路径只写 `content_encrypted`、`nonce` 与 `tag`
（`content_version=2`）。删除用户时显式清理五张子表，并移除 `key_cache` 中对应 id 的 DEK。
SQLite 会复用最大 rowid，残留的缓存条目会被后续用户继承。

## 8. 必须保持的不变量

修改以下内容会破坏对外契约或既有数据，需要单独的兼容或迁移方案：

| 不变量 | 原因 |
|---|---|
| `/api/v1` 的路径、请求与响应结构、状态码 | README 与 `docs/android-api.md` 已有客户端依赖 |
| 响应体中的 `_decryption_failed` 键名 | 客户端据此提示用户，属于线协议 |
| 环境变量名（`JWT_SECRET_KEY`、`ENCRYPTION_MASTER_KEY`、`DATABASE_URL`、`ENV`、`CORS_ORIGINS`） | 部署文档与 compose 文件已固化 |
| 镜像名、端口 18001、`./data` 挂载方式 | 影响用户升级路径 |
| 遗留 KDF 参数 | 决定历史密文能否解密 |
| 现有 SQLite 数据可直接被新版本读取 | 升级不应要求导出与导入 |

## 9. 验证入口

| 目的 | 命令 |
|---|---|
| 后端单元测试（含加密、迁移、认证契约） | `cd backend && uv run pytest` |
| 后端覆盖率 | `cd backend && uv run pytest --cov=app --cov-report=term-missing` |
| 后端风格检查 | `cd backend && uv run ruff check . && uv run ruff format --check .` |
| 前端单元测试 | `cd frontend && pnpm test` |
| 前端风格与构建 | `cd frontend && pnpm lint && pnpm format:check && pnpm build` |

CI（`.github/workflows/ci.yml`）在 Python 3.11、3.12 与 Node 24 上执行同一组命令。
发布镜像由 `release-image.yml` 在 `v*` 标签上构建，并在推送前完成健康检查。
