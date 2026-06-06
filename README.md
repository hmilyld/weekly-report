# 周报自动生成系统

基于日报自动生成周报的全栈应用。前端 React + Vite，后端 Python FastAPI，SQLite 数据库。

## 功能

- **日报管理** — 按周查看，支持增删改查
- **周报生成** — 基于日报调用大模型 API 自动生成周报
- **系统配置** — 在线修改大模型地址、模型名称、API Key
- **认证** — JWT 单用户登录保护

---

## 本地开发

### 后端

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 前端

```bash
cd frontend
pnpm install
pnpm dev
```

前端开发服务器运行在 `http://localhost:5173`，API 请求代理到后端 `http://localhost:8000`。

### 默认账号

- 用户名: `admin`
- 密码: `admin123`

---

## Docker 构建与运行

### 构建镜像

```bash
docker build -t weekly-report:latest .
```

### 运行容器

```bash
docker run -d \
  --name weekly-report \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -e JWT_SECRET_KEY=your-secret-key-here \
  weekly-report:latest
```

访问 `http://localhost:8000`

### 使用 docker-compose

```bash
# 可选：创建 .env 文件
echo "JWT_SECRET_KEY=your-secret-key-here" > .env

docker-compose up -d --build
```

---

## 推送到 Docker Hub

```bash
# 1. 登录 Docker Hub
docker login

# 2. 打标签（替换 <username> 为你的 Docker Hub 用户名）
docker tag weekly-report:latest <username>/weekly-report:latest
docker tag weekly-report:latest <username>/weekly-report:1.0.0

# 3. 推送
docker push <username>/weekly-report:latest
docker push <username>/weekly-report:1.0.0
```

---

## API 接口

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/v1/auth/login` | 登录获取 token | ✗ |
| POST | `/api/v1/auth/change-password` | 修改密码 | ✓ |
| GET | `/api/v1/daily` | 查询日报（支持日期范围） | ✓ |
| GET | `/api/v1/daily/week/{date}` | 按周查询日报 | ✓ |
| POST | `/api/v1/daily` | 创建/更新日报 | ✓ |
| DELETE | `/api/v1/daily/{date}` | 删除日报 | ✓ |
| GET | `/api/v1/weekly` | 查询所有周报 | ✓ |
| GET | `/api/v1/weekly/{week_start}` | 获取/自动生成周报 | ✓ |
| POST | `/api/v1/weekly/{week_start}` | 强制重新生成周报 | ✓ |
| GET | `/api/v1/config` | 获取配置 | ✓ |
| PUT | `/api/v1/config` | 更新配置 | ✓ |
| POST | `/api/v1/config/test` | 测试大模型连接 | ✓ |

---

## 技术栈

- **前端**: React 18 + Vite 5 + React Router 6 + Axios + Lucide Icons
- **后端**: Python 3.11 + FastAPI + SQLAlchemy + python-jose + passlib
- **数据库**: SQLite
- **认证**: JWT (24h 有效期)
- **容器**: Docker 多阶段构建 (Node 18 + Python 3.11)
