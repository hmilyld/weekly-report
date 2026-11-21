# 架构说明

面向要改后端、加密逻辑或部署方式的人。安装与使用见 [`README.md`](../README.md)，
目录与命令约定见 [`AGENTS.md`](../AGENTS.md)，视觉系统见 [`DESIGN.md`](../DESIGN.md)。

## 1. 运行形态

单容器、单进程、单文件数据库：

```
浏览器 / Android 客户端
        │  HTTPS（由反向代理终止）
        ▼
┌──────────────────────────────────────────┐
│ uvicorn + FastAPI（:18001）               │
│  ├── /api/v1/*     → routers             │
│  └── 其他路径       → frontend/dist 静态  │
└──────────────────────────────────────────┘
        │
        ▼
   ./data/weekly_report.db（SQLite，WAL）
```

- 前端构建产物在镜像里，后端用 catch-all 托管，因此**只有一个对外端口**。
- 没有 Redis、消息队列或外部对象存储；所有状态都在数据库与加密主密钥里。
- `./data` 是唯一需要持久化的目录；备份必须同时包含数据库与 `ENCRYPTION_MASTER_KEY`。

## 2. 模块边界

| 层 | 位置 | 职责 | 不该做的事 |
|---|---|---|---|
| HTTP | `app/routers/` | 参数校验、状态码、响应模型 | 直接拼 SQL、直接做加密 |
| 持久化 | `app/crud/` | 查询、写入、级联删除 | 决定 HTTP 状态码 |
| 模型 | `app/models.py`、`app/schemas.py` | ORM 与对外契约 | 业务判断 |
| 横切 | `auth` `crypto` `envelope` `encryption_utils` `key_cache` `migration` `date_range` `llm_client` | 认证、加密、迁移、LLM 调用 | 依赖 routers |

前端同构分层：`api/`（axios 封装）→ `pages/`（路由页面）→ `components/`（`ui/` 通用组件、
`tasks/`、`settings/` 业务组件）→ `contexts/`（认证、主题）→ `utils/`（纯函数）。
页面只组合组件、发请求、管自己的状态；跨页共享的状态放 context。

## 3. 请求链路

**带 JWT 的网页请求**

1. `api/index.js` 的请求拦截器从 `localStorage.token` 注入 `Authorization: Bearer …`
2. `get_current_user`（或数据接口的 `get_authenticated_user`）解出 `sub` / `pwd_ver`
3. 校验 `pwd_ver == users.password_version`：改密后旧 JWT 立即失效
4. router 调 `crud`，密文在此解密成明文对象返回
5. 响应拦截器遇到 `401` 触发重新登录；`402`（当前密码错误）**不**触发登出

**带 API Token 的脚本请求**

同一个路由集，`X-API-Token` 走 `get_authenticated_user`。JWT 与 Token 同时存在时以 JWT 为准，
且 JWT 无效时**不会**回退到 Token。Token 只能访问数据接口，认证/配置/用户/Token 管理接口对它返回 401。

状态码语义：`401` 凭据缺失或无效，`402` 会话有效但当前密码不对，`403` 已认证但非管理员，
`409` 加密密钥缺失（`encryption_key_missing`）或内容无法解密（`decryption_failed`）。

## 4. 加密链路（信封加密）

```
ENCRYPTION_MASTER_KEY (32B, base64)
        │ HKDF
        ▼
       KEK  ──wrap──▶ users.wrapped_dek（AAD 绑定该用户）
                          │ 启动时解包
                          ▼
                    key_cache[user_id] = DEK
                          │
        内容明文 ──AES-GCM(DEK, AAD=表名+用户)──▶ content_encrypted / nonce / tag
```

- 启动时 `load_all_user_deks()` 把所有 DEK 解包进内存，**重启后不需要任何人登录**。
- 写入时若该用户没有 DEK → `EncryptionKeyMissingError` → `409`，**不存在落明文的路径**。
- 老用户（`wrapped_dek` 为 NULL）在登录时一次性迁移；迁移失败不阻塞登录，但读被标记、写返回 409。
- 迁移前会生成一次 `data/pre-envelope-*.db` 快照（0600）作为回滚点。
- `AppConfig.api_key` 同样用 KEK 包装（`ek1:` 前缀），旧值在启动时重新包装。
- 解密后的对象用 `set_committed_value` 写回属性，避免明文被 ORM 自动回写。

**不要改的参数**：`app/auth.py` 里遗留 KDF（`derive_user_key`）的参数是冻结的，
它决定老数据的可读性；改动会让历史密文永久无法解密。

## 5. 启动顺序

`main.py` 的 lifespan 依次执行，任何一步失败都拒绝启动：

1. `init_database()`：建表 → 补列（`schema_migrations`）→ 迁移前快照 → 清理明文残留 → 种子配置
2. `get_kek()`：校验主密钥，生产环境缺失即失败
3. `migrate_app_config_secret()`：把旧格式的 LLM API Key 重新包装
4. `load_all_user_deks()`：恢复所有 DEK 到内存缓存

数据库迁移是**增量**的（只加列/加表，不删不改类型），随启动自动完成，不使用 Alembic。

## 6. 报告生成链路

1. 用户按天写日报（明文进，AES-GCM 密文出）
2. 生成周报/月报时，router 取该周期的日报 → 解密 → 拼成 prompt
3. `llm_client` 调 OpenAI 兼容接口（地址来自 `AppConfig`，调用前做 SSRF 校验：允许 loopback，拒绝私网/保留段）
4. 结果加密后写入 `weekly_reports` / `monthly_reports`

错误映射：超时、HTTP 非 2xx、响应结构异常、连接失败各有独立文案；
`POST /weekly/{week_start}?force=false` 在已有报告时返回 `generated=false` 且不调用模型。

## 7. 数据模型

```
users 1──N daily_reports
      1──N weekly_reports
      1──N monthly_reports
      1──N tasks
      1──N api_tokens
app_config（单行，id=1）
```

所有内容表的明文列只在迁移前存在；写入路径只写 `content_encrypted` + `nonce` + `tag`
（`content_version=2`）。删除用户时显式清理五张子表，并移除 `key_cache` 中该 id 的 DEK
（SQLite 会复用最大 rowid，残留会导致下一个用户继承旧密钥）。

## 8. 关键不变量

改动前请确认这几条仍然成立，它们是对外与对旧数据的承诺：

| 不变量 | 原因 |
|---|---|
| `/api/v1` 路径、请求响应结构、状态码 | README 与 `docs/android-api.md` 已有客户端 |
| 响应体里的 `_decryption_failed` 键名 | 客户端据此提示用户，属线协议 |
| 环境变量名（`JWT_SECRET_KEY`、`ENCRYPTION_MASTER_KEY`、`DATABASE_URL`、`ENV`、`CORS_ORIGINS`） | 部署文档与 compose 已固化 |
| 镜像名、端口 18001、`./data` 挂载 | 用户升级路径 |
| 遗留 KDF 参数 | 决定历史密文能否解密 |
| 现有 SQLite 数据可直接被新版本读取 | 升级不要求导出/导入 |

## 9. 验证入口

| 目标 | 命令 |
|---|---|
| 后端单测（含加密、迁移、认证契约） | `cd backend && uv run pytest` |
| 覆盖率 | `cd backend && uv run pytest --cov=app --cov-report=term-missing` |
| 后端风格 | `cd backend && uv run ruff check . && uv run ruff format --check .` |
| 前端单测 | `cd frontend && pnpm test` |
| 前端风格与构建 | `cd frontend && pnpm lint && pnpm format:check && pnpm build` |

CI（`.github/workflows/ci.yml`）在 Python 3.11 / 3.12 与 Node 24 上跑同一组命令；
发布镜像由 `release-image.yml` 在 `v*` 标签上构建并做健康检查。
