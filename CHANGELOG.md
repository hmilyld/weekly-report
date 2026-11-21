# 变更日志

本文件记录面向用户的变更。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 新增

- 内容信封加密：主密钥派生 KEK 包装每用户 DEK，内容以 AES-GCM + AAD 加密，重启后无需重新登录
- 统一 `/api/v1` 数据接口：同一套路由同时服务网页端与 API Token 客户端，移除旧的 `/api/v1/external/*`
- CI 质量门禁：后端 ruff + pytest，前端 eslint + prettier + 构建
- 开发依赖清单 `backend/dev-requirements.txt`

### 变更

- 缺少 DEK 时写入返回 `409 encryption_key_missing`，不再有任何明文落库路径
- 响应中的 `_decryption_failed` 字段固定为客户端契约

### 文档

- 新增 MIT 许可证
- 校准 README 与产品 / 设计 / 协作文档

## [1.1.0] - 2026-11-17

### 新增

- 改用原生 `<dialog>` 对话框，补齐表单校验与无障碍细节

### 修复

- 前端清单版本号对齐到发布标签

### 文档

- 同步设计系统与协作约定到本轮改动

## [1.0.2] - 2026-11-11

### 新增

- 日报编辑默认有序列表，回车自动续号

## [1.0.1] - 2026-11-04

### 新增

- 手机端日报列表去掉操作列，删除移入编辑弹窗

### 修复

- 修改密码与退出登录

### 文档

- 按当前实现校准 README 与产品 / 设计 / 协作文档

## [1.0.0] - 2026-11-02

首个公开版本：日报 / 周报 / 月报、待办、多用户与角色权限、系统配置、API Token、PWA 安装。

[Unreleased]: https://github.com/hmilyld/weekly-report/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/hmilyld/weekly-report/compare/v1.0.2...v1.1.0
[1.0.2]: https://github.com/hmilyld/weekly-report/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/hmilyld/weekly-report/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/hmilyld/weekly-report/releases/tag/v1.0.0
