# 贡献指南

本文件说明本地环境搭建、提交规范与合并要求。仓库结构、代码风格、测试组织与发布流程见
[`AGENTS.md`](AGENTS.md)。

## 沟通语言

Issue、Pull Request 与提交信息使用中文；技术名词（JWT、AAD、DEK 等）保留英文原文。

## 环境要求

| 工具 | 版本 | 说明 |
|---|---|---|
| Python | 3.15 | 与镜像一致；`pyproject.toml` 要求 `>=3.11`，CI 覆盖 3.11 与 3.15 |
| Node.js | 26 | 与镜像一致，见 `.nvmrc` |
| pnpm | 9 | 前端包管理器，`pnpm-lock.yaml` 已锁定；Node 26 不再内置 corepack，需自行安装 |
| uv | 较新版本 | 后端虚拟环境与依赖安装 |
| Docker | 可选 | 仅运行或验证镜像时需要 |

## 本地开发

推荐使用仓库自带的一键脚本：

```bash
bash scripts/dev.sh start     # 同时启动前后端
bash scripts/dev.sh status
bash scripts/dev.sh logs
bash scripts/dev.sh stop
```

手动启动：

```bash
# 后端，http://localhost:18001
cd backend
uv venv
uv pip install -r requirements.txt -r dev-requirements.txt
uv run uvicorn main:app --reload --port 18001

# 前端，http://localhost:5173，/api 代理到 18001
cd frontend
pnpm install
pnpm dev
```

首次访问会引导创建管理员账号。大模型配置在网页端「系统配置」中填写，不依赖环境变量。

## 提交前检查

```bash
# 后端
cd backend && uv run ruff check . && uv run ruff format --check . && uv run pytest

# 前端
cd frontend && pnpm lint && pnpm format:check && pnpm test && pnpm build
```

界面改动需在 Pull Request 中附截图，并检查 1440px 与 390px 两种宽度、亮色与暗色两种主题。

## 提交信息

提交信息遵循 [Conventional Commits](https://www.conventionalcommits.org/)，描述使用中文：

```
feat: 新增月报功能
fix: 修复深色模式下登录按钮无边框的问题
docs: 更新部署说明
```

常用前缀：`feat`、`fix`、`docs`、`style`、`refactor`、`test`、`ci`、`chore`。

## 提交 Pull Request

1. 从 `main` 创建分支，一次 Pull Request 只处理一件事。
2. 在描述中说明改动内容、原因与验证方式。
3. 勾选 Pull Request 模板中的检查项。
4. 涉及公共契约的改动必须单独说明，并给出兼容或迁移方案。公共契约包括 `/api/v1` 的路径、
   请求与响应结构、错误码、环境变量名、数据库结构与数据格式。

## 不应包含的改动

- 不手动编辑生成产物，包括 `frontend/dist/`、`__pycache__/` 与 `*.db`。
- 不提交 `.env`、`data/`、`data/.encryption_key` 或任何真实密钥。测试使用
  `backend/tests/conftest.py` 中的固定主密钥。
- 不删除测试、文档或许可证信息。

## 相关文档

| 文件 | 内容 |
|---|---|
| [`PRODUCT.md`](PRODUCT.md) | 产品定位、用户、能力与约束 |
| [`DESIGN.md`](DESIGN.md) | 设计系统：令牌、排版、组件与交互规则 |
| [`docs/architecture.md`](docs/architecture.md) | 运行形态、模块边界、请求与加密链路 |
| [`docs/api.md`](docs/api.md) | HTTP 端点、认证方式、状态码与调用示例 |
| [`docs/android-api.md`](docs/android-api.md) | Android 与 API Token 客户端对接 |
| [`SECURITY.md`](SECURITY.md) | 漏洞报告通道与已知风险 |

安全问题请勿公开提交 Issue，报告方式见 [`SECURITY.md`](SECURITY.md)。
