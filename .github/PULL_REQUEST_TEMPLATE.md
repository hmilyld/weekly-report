## 改了什么

<!-- 一两句话说明这次改动，以及它解决的问题。 -->

## 关联 issue

<!-- 例如 Closes #12；没有就写「无」。 -->

## 如何验证

<!-- 给出可复现的验证步骤或命令，便于审阅者复核。 -->

## 检查清单

- [ ] `cd backend && uv run ruff check . && uv run ruff format --check . && uv run pytest` 通过
- [ ] `cd frontend && pnpm lint && pnpm format:check && pnpm build` 通过
- [ ] UI 改动附截图，并检查 1440px / 390px 与亮色 / 暗色
- [ ] 未提交 `.env`、`data/`、数据库文件或任何真实密钥

## 兼容性影响

<!-- 是否触及 /api/v1 契约、错误码、环境变量名、数据格式或默认行为？
     若有，请说明影响范围、迁移方案与版本建议；没有则写「无」。 -->

## 回滚方式

<!-- 直接 revert 即可，还是需要额外的数据或配置处理？ -->
