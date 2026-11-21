# 贡献指南

感谢你愿意改进这个项目。本文说明如何搭建环境、提交改动，以及我们会检查什么。
更细的仓库结构、风格与发布流程见 [`AGENTS.md`](AGENTS.md)。

## 沟通语言

Issue、PR、提交信息都使用中文。技术名词（如 JWT、AAD、DEK）保留英文原文。

## 环境要求

| 工具 | 版本 | 说明 |
|---|---|---|
| Python | 3.11 | 与镜像一致；`pyproject.toml` 要求 `>=3.11` |
| Node.js | 20 或更高 | 前端构建 |
| pnpm | 9 | 前端包管理器，锁定 `pnpm-lock.yaml` |
| uv | 任意较新版本 | 后端环境与依赖安装 |
| Docker | 可选 | 只想跑起来或验证镜像时用 |

## 本地开发

一键脚本（推荐）：

```bash
bash scripts/dev.sh start     # 同时启动前后端
bash scripts/dev.sh status
bash scripts/dev.sh logs
bash scripts/dev.sh stop
```

手动启动：

```bash
# 后端（http://localhost:18001）
cd backend
uv venv
uv pip install -r requirements.txt -r dev-requirements.txt
uv run uvicorn main:app --reload --port 18001

# 前端（http://localhost:5173，/api 代理到 18001）
cd frontend
pnpm install
pnpm dev
```

首次访问会引导创建管理员账号。大模型配置在「系统配置」中填写，无需环境变量。

## 提交前必须通过

```bash
# 后端
cd backend && uv run ruff check . && uv run ruff format --check . && uv run pytest

# 前端
cd frontend && pnpm lint && pnpm format:check && pnpm build
```

改动 UI 时，请在 PR 中附截图，并检查 1440px 与 390px 两种宽度、亮色与暗色两种主题。

## 不需要你处理的

- 不要手动格式化生成产物：`frontend/dist/`、`__pycache__/`、`*.db`
- 不要提交 `.env`、`data/`、`data/.encryption_key` 或任何真实密钥；测试用 `backend/tests/conftest.py` 里的固定主密钥
- 不要为了「顺手清理」而删除测试、文档或许可证信息

## 提交信息

使用 [Conventional Commits](https://www.conventionalcommits.org/)，描述用中文：

```
feat: 新增月报功能
fix: 修复深色模式下登录按钮无边框的 bug
docs: 更新部署说明
```

常用前缀：`feat`、`fix`、`docs`、`style`、`refactor`、`test`、`ci`、`chore`。

## 提交 PR

1. 从 `main` 拉分支，保持一次 PR 只做一件事
2. 在 PR 描述中说明「改了什么、为什么、如何验证」
3. 勾选 PR 模板中的检查项（lint / test / build）
4. 涉及公共契约的改动（`/api/v1` 的路径、请求响应结构、错误码、环境变量名、数据格式）必须单独说明，并给出兼容或迁移方案

## 领域文档

改需求前先读 [`PRODUCT.md`](PRODUCT.md)，改界面前先读 [`DESIGN.md`](DESIGN.md)，改接口前先读 [`README.md`](README.md) 的 API 与 [`docs/android-api.md`](docs/android-api.md)。

## 安全问题

请勿公开提交安全 issue，见 [`SECURITY.md`](SECURITY.md)。
