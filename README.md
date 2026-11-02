# 周报/月报自动生成系统

按天记录进展，由大模型汇总成周报和月报。前端 React + Vite，后端 Python FastAPI，SQLite 存储，支持多用户与管理员/普通用户两种角色。

界面为中文，可安装为 PWA（桌面 / 手机），支持跟随系统、亮色、暗色三种主题。

## 功能

- **日报** — 桌面端月历、手机端周列表，点格子记录当天进展，支持增删改
- **周报 / 月报** — 调用大模型把日报汇总成周报或月报，生成后可编辑、复制、重新生成
- **工作待办** — 记录待办与截止日期，逾期和临期自动标记，已完成的分页查看
- **多用户** — 管理员创建/删除用户、切换角色；每个用户的数据互相隔离，列表显示最近登录时间
- **系统配置** — 管理员在线修改大模型地址、模型名称、API Key，支持连接测试
- **API Token** — 用 Token 从脚本或外部服务写入日报、读取周报与待办，无需登录
- **安全** — JWT 登录保护；日报/周报/月报/待办内容按用户密钥加密存储；改密后旧 token 失效

### 角色权限

| 功能 | 管理员 (admin) | 普通用户 (user) |
|------|:-:|:-:|
| 日报 / 周报 / 月报 / 待办 | ✓ | ✓ |
| 修改自己的密码 | ✓ | ✓ |
| 管理自己的 API Token | ✓ | ✓ |
| 大模型配置 | ✓ | ✗ |
| 用户管理（创建 / 删除 / 改角色） | ✓ | ✗ |

---

## 快速开始（Docker）

```bash
# 1. 生成 JWT 密钥并写入 .env
echo "JWT_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(64))')" > .env

# 2. 启动（默认使用 Docker Hub 镜像）
docker compose up -d

# 3. 打开 http://localhost:18001
```

- 数据库落在 `./data/weekly_report.db`，升级镜像不会丢失。
- 想用 GitHub 镜像：`IMAGE=ghcr.io/hmilyld/weekly-report:latest docker compose up -d`
- 本地改代码后重建：`docker compose up -d --build`

### 镜像来源

| 来源 | 地址 | 说明 |
|---|---|---|
| Docker Hub | `hmilyld/weekly-report` | 手动执行 `./scripts/docker-publish.sh [tag]` 发布 |
| GitHub Container Registry | `ghcr.io/hmilyld/weekly-report` | 推送 `v*` 标签自动发布 |

GitHub 镜像的标签规则：`1.2.0`（精确版本）、`1.2`、`1`、`latest`。预发布（如 `v1.2.0-rc1`）只发精确版本，不移动浮动标签与 `latest`。

发布方式见下方「发布与部署」。

### 手动构建镜像

```bash
docker build -t weekly-report:latest .

docker run -d \
  --name weekly-report \
  -p 18001:18001 \
  -v $(pwd)/data:/app/data \
  -e JWT_SECRET_KEY=your-secret-key-here \
  weekly-report:latest
```

---

## 本地开发

### 一键脚本（推荐）

```bash
bash scripts/dev.sh start     # 同时启动前后端
bash scripts/dev.sh status    # 查看状态
bash scripts/dev.sh logs      # 查看日志
bash scripts/dev.sh restart   # 重启
bash scripts/dev.sh stop      # 停止
```

首次运行会安装依赖。日志与 PID 文件在 `.dev/`（已忽略，不会提交）。

### 后端

```bash
cd backend
uv venv                                 # 创建虚拟环境
uv pip install -r requirements.txt      # 安装依赖
uv run uvicorn main:app --reload --port 18001
```

### 前端

```bash
cd frontend
pnpm install
pnpm dev        # http://localhost:5173，/api 代理到 :18001
pnpm build      # 产物在 frontend/dist，后端会直接托管
pnpm generate:icons   # 重新生成应用图标（SVG；装了 ffmpeg 时同时输出 PNG）
```

### 首次使用

首次访问会跳到初始化页面，创建第一个账号（自动成为管理员）。系统没有默认账号。

### 数据迁移

升级后启动后端会自动补齐新增字段与表（`main.py` 里的 `_migrate_db()`），无需手动执行脚本。旧版单用户数据库会保留原有数据，并把第一个用户提升为管理员。

> 从加密改造之前的版本升级时，首次登录会顺带把历史明文内容重新加密。

---

## 发布与部署

### 打标签自动发布到 GitHub 镜像

```bash
git tag -a v1.2.0 -m "v1.2.0"
git push origin v1.2.0
```

工作流 `.github/workflows/release-image.yml` 会依次：校验标签 → 构建镜像 → 启动容器请求 `/api/v1/health` 做冒烟测试 → 推送到 `ghcr.io`。冒烟测试不通过不会推送。

也可以在 Actions 页面手动运行 **Release image** 并填写标签（标签必须已存在于远端）。

### 手动发布到 Docker Hub

```bash
./scripts/docker-publish.sh          # 推送 latest
./scripts/docker-publish.sh v1.0.0   # 推送指定版本 + latest
```

脚本会本地构建、跑冒烟测试，再推送。

### 升级已部署的实例

```bash
docker compose pull && docker compose up -d
```

数据库结构变更是增量的（只加字段/表），旧数据保留；回滚到旧镜像也安全。

---

## 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `JWT_SECRET_KEY` | 生产必填 | 开发环境随机生成 | JWT 签名密钥；生产缺失会启动失败 |
| `DATABASE_URL` | 否 | `sqlite:///./data/weekly_report.db` | 数据库连接串 |
| `CORS_ORIGINS` | 否 | `*` | 允许的来源，逗号分隔 |
| `ENV` / `ENVIRONMENT` | 否 | `development` | 设为 `production` 时启用 HSTS 等更严格的默认值 |
| `IMAGE` | 否 | `hmilyld/weekly-report:latest` | `docker compose` 使用的镜像 |

大模型地址、模型名与 API Key 不通过环境变量配置，保存在数据库里，登录后在「系统配置」页面修改。

---

## API 接口

除特别标注外，均需要 `Authorization: Bearer <token>`。所有接口前缀为 `/api/v1`。

### 认证

| 方法 | 路径 | 说明 | 认证 |
|---|---|---|---|
| GET | `/auth/status` | 是否需要初始化 | ✗ |
| POST | `/auth/setup` | 初始化第一个管理员账号 | ✗ |
| POST | `/auth/login` | 登录获取 token | ✗ |
| POST | `/auth/change-password` | 修改密码（需当前密码，返回新 token） | ✓ |
| POST | `/auth/logout` | 退出并清除服务端密钥缓存 | ✓ |

### 日报

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/daily?start_date=&end_date=` | 按日期范围查询 |
| GET | `/daily/week/{week_start}` | 按周查询 |
| POST | `/daily` | 创建/覆盖某天的日报 |
| DELETE | `/daily/{date}` | 删除某天的日报 |

### 周报 / 月报

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/weekly` · `/weekly/{week_start}` | 查询周报 |
| POST | `/weekly/{week_start}` | 生成/重新生成 |
| PUT | `/weekly/{week_start}` | 编辑正文 |
| GET | `/monthly` · `/monthly/{year}/{month}` | 查询月报 |
| POST | `/monthly/{year}/{month}` | 生成/重新生成 |
| PUT | `/monthly/{year}/{month}` | 编辑正文 |

### 待办

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/tasks` | 未完成待办 |
| GET | `/tasks/completed?offset=&limit=` | 已完成待办（分页） |
| POST | `/tasks` | 新建待办（内容 + 可选截止日期） |
| PUT | `/tasks/{id}` | 更新内容、截止日期或完成状态 |
| DELETE | `/tasks/{id}` | 删除待办 |

### 配置（管理员）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/config` | 读取配置（API Key 脱敏） |
| PUT | `/config` | 更新配置 |
| POST | `/config/test` | 测试大模型连接 |

### 用户

| 方法 | 路径 | 说明 | 认证 |
|---|---|---|---|
| GET | `/users/me` | 当前用户（含最近登录时间） | ✓ |
| GET | `/users` | 用户列表 | admin |
| POST | `/users` | 创建用户 | admin |
| PUT | `/users/{id}/role` | 修改角色 | admin |
| DELETE | `/users/{id}` | 删除用户 | admin |

### API Token

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/tokens` | 列出自己的 Token |
| POST | `/tokens` | 创建 Token（完整值只返回一次） |
| DELETE | `/tokens/{id}` | 删除 Token |

### 外部接口（`X-API-Token` 认证）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/external/daily` | 写入某天日报（可指定 `date`、`append`） |
| GET | `/external/daily/current-week` | 读取本周日报 |
| GET | `/external/weekly/recent` | 读取本周与上周周报 |
| POST | `/external/weekly/generate` | 生成当周周报 |
| GET | `/external/tasks/pending` | 读取未完成待办 |
| POST | `/external/tasks` | 新建待办 |
| GET | `/external/docs` | 接口说明 |

### 健康检查

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 返回 `{"status":"ok"}`，用于容器健康检查 |

---

## 技术栈

- **前端**：React 18、Vite 5、React Router 6、Axios、Lucide 图标、vite-plugin-pwa；手写 CSS（设计令牌见 `frontend/src/styles/tokens.css`）
- **后端**：Python 3.11、FastAPI、SQLAlchemy 2、python-jose、passlib/bcrypt、cryptography（AES-GCM 加密存储）、httpx
- **数据库**：SQLite（单文件，随 `./data` 挂载持久化）
- **部署**：多阶段 Docker 构建（Node 20 构建前端 + Python 3.11 运行），单容器同时提供 API 与前端

---

## 文档

| 文件 | 内容 |
|---|---|
| `PRODUCT.md` | 产品定位、用户、能力与约束（改需求前先读） |
| `DESIGN.md` | 设计系统：令牌、排版、组件、交互规则（改界面前先读） |
| `AGENTS.md` | 仓库结构与开发约定、提交规范、发布流程（给人和 AI 协作用） |
