# 周报自动生成系统

基于日报自动生成周报的全栈应用。前端 React + Vite，后端 Python FastAPI，SQLite 数据库。支持多用户，区分管理员和普通用户角色。

## 功能

- **多用户系统** — 支持管理员创建/删除用户、切换角色，每个用户独立管理自己的数据
- **日报管理** — 日历视图 + 周列表视图，支持增删改查
- **周报生成** — 基于日报调用大模型 API 自动生成周报，支持手动编辑
- **系统配置** — 管理员可在线修改大模型地址、模型名称、API Key，支持连接测试
- **API Token** — 创建 Token 后可通过外部 API 提交日报，无需登录
- **认证** — JWT 登录保护，密码修改后旧 token 自动失效
- **PWA** — 支持安装为桌面/移动应用，离线访问应用外壳
- **主题** — 支持跟随系统 / 亮色 / 暗色三种主题模式

### 角色权限

| 功能 | 管理员 (admin) | 普通用户 (user) |
|------|:-:|:-:|
| 日报/周报/待办管理 | ✓ | ✓ |
| 修改自己的密码 | ✓ | ✓ |
| 管理 API Token | ✓ | ✓ |
| 管理大模型配置 | ✓ | ✗ |
| 用户管理（创建/删除/改角色） | ✓ | ✗ |

---

## 本地开发

### 后端

```bash
cd backend
uv venv                          # 创建虚拟环境
uv pip install -r requirements.txt   # 安装依赖
uv run uvicorn main:app --reload --port 18001   # 启动开发服务器
```

### 前端

```bash
cd frontend
pnpm install
pnpm dev
```

前端开发服务器运行在 `http://localhost:5173`，API 请求代理到后端 `http://localhost:18001`。

### 首次使用

首次访问时系统会自动跳转到初始化页面，设置管理员用户名和密码。没有默认账号。

### 数据迁移（从旧版单用户升级）

如果已有旧版数据库，升级后启动后端会自动迁移：添加 `role` 字段并将现有用户提升为管理员。也可手动执行：

```bash
cd backend && uv run python ../scripts/migrate_to_multiuser.py
```

---

## Docker 构建与运行

### 使用 docker-compose（推荐）

```bash
# 1. 创建 .env 文件，设置 JWT 密钥
echo "JWT_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(64))')" > .env

# 2. 启动
docker compose up -d --build
```

访问 `http://localhost:18001`

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

## 推送到 Docker Hub

使用一键发布脚本（含冒烟测试）：

```bash
./scripts/docker-publish.sh          # 推送 latest 标签
./scripts/docker-publish.sh v1.0.0   # 推送指定版本 + latest
```

---

## API 接口

### 认证接口

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/v1/auth/status` | 检查是否需要初始化 | ✗ |
| POST | `/api/v1/auth/setup` | 初始化管理员账号 | ✗ |
| POST | `/api/v1/auth/login` | 登录获取 token | ✗ |
| POST | `/api/v1/auth/change-password` | 修改密码 | ✓ |

### 日报接口

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/v1/daily` | 查询日报（支持日期范围） | ✓ |
| GET | `/api/v1/daily/week/{date}` | 按周查询日报 | ✓ |
| POST | `/api/v1/daily` | 创建/更新日报 | ✓ |
| DELETE | `/api/v1/daily/{date}` | 删除日报 | ✓ |

### 周报接口

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/v1/weekly` | 查询所有周报 | ✓ |
| GET | `/api/v1/weekly/{week_start}` | 获取指定周报 | ✓ |
| POST | `/api/v1/weekly/{week_start}` | 生成/重新生成周报 | ✓ |
| PUT | `/api/v1/weekly/{week_start}` | 编辑周报内容 | ✓ |

### 配置接口

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/v1/config` | 获取配置（API Key 脱敏） | admin |
| PUT | `/api/v1/config` | 更新配置 | admin |
| POST | `/api/v1/config/test` | 测试大模型连接 | admin |

### 用户管理接口

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/v1/users/me` | 获取当前用户信息 | ✓ |
| GET | `/api/v1/users` | 列出所有用户 | admin |
| POST | `/api/v1/users` | 创建新用户 | admin |
| DELETE | `/api/v1/users/{id}` | 删除用户 | admin |
| PUT | `/api/v1/users/{id}/role` | 修改用户角色 | admin |

### Token 管理接口

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/v1/tokens` | 列出所有 Token | ✓ |
| POST | `/api/v1/tokens` | 创建 Token | ✓ |
| DELETE | `/api/v1/tokens/{id}` | 删除 Token | ✓ |

### 外部接口（Token 认证）

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/v1/external/daily` | 通过 Token 提交日报 | X-API-Token |
| GET | `/api/v1/external/daily/current-week` | 获取当周日报 | X-API-Token |
| GET | `/api/v1/external/weekly/recent` | 获取当周+上周周报 | X-API-Token |
| GET | `/api/v1/external/docs` | 获取接口文档 | X-API-Token |

### 健康检查

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/v1/health` | 服务健康检查 | ✗ |

---

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `JWT_SECRET_KEY` | 生产环境必填 | JWT 签名密钥 |
| `DATABASE_URL` | 否 | 数据库连接字符串，默认 SQLite |
| `CORS_ORIGINS` | 否 | CORS 允许来源，逗号分隔 |
| `ENV` | 否 | `production` 或 `development`（影响安全头和 JWT 密钥检查） |

---

## 技术栈

- **前端**: React 18 + Vite 5 + React Router 6 + Axios + Lucide Icons + vite-plugin-pwa
- **后端**: Python 3.11 + FastAPI + SQLAlchemy + python-jose + passlib
- **数据库**: SQLite
- **认证**: JWT (24h 有效期，密码修改后自动失效)，支持多用户角色 (admin/user)
- **容器**: Docker 多阶段构建 (Node 18 + Python 3.11)
- **包管理**: pnpm (前端) + uv (后端)
