# 安全审计与代码质量报告

**项目:** 日周报管理系统 (weekly-report)
**审计日期:** 2026-06-06
**审计范围:** 后端安全、前端代码质量、基础设施部署

---

## 统计摘要

| 严重程度 | 后端 | 前端 | 基础设施 | 合计 |
|---------|------|------|---------|------|
| Critical | 3 | 0 | 0 | **3** |
| High | 6 | 2 | 3 | **11** |
| Medium | 7 | 10 | 10 | **27** |
| Low | 5 | 10 | 6 | **21** |
| Info | 4 | 6 | 2 | **12** |
| **合计** | **25** | **28** | **21** | **74** |

---

## 一、Critical 级别问题 (3)

### C-1: 硬编码默认 JWT 密钥
- **文件:** `backend/app/config.py:10`
- **问题:** `jwt_secret_key` 默认值 `"dev-secret-change-in-production"`，若未设置环境变量，所有 JWT 使用公开已知密钥签名，攻击者可伪造任意 token 冒充用户
- **修复:** 生产环境必须强制要求设置 `JWT_SECRET_KEY`，未设置时拒绝启动

### C-2: CORS 允许所有来源 + 启用凭证
- **文件:** `backend/main.py:50-56`
- **问题:** `allow_origins=["*"]` + `allow_credentials=True`，任何恶意网站均可发起带凭证的跨域请求
- **修复:** 限制 `allow_origins` 为实际前端域名，或至少移除 `allow_credentials=True`

### C-3: LLM API Key 明文返回
- **文件:** `backend/app/routers/config.py:16-27`
- **问题:** `GET /api/v1/config` 返回完整的 `api_key`，代码中有注释说要脱敏但实际未执行
- **修复:** 只返回掩码版本（如 `"sk-...xxxx"`），前端更新时提交新 key 即可

---

## 二、High 级别问题 (11)

### H-1: 登录接口无速率限制
- **文件:** `backend/app/routers/auth.py:60-69`
- **问题:** 可无限次暴力破解密码
- **修复:** 添加速率限制中间件（如 `slowapi`），限制每分钟 5 次失败尝试

### H-2: 初始化接口竞态条件
- **文件:** `backend/app/routers/auth.py:38-57`
- **问题:** `POST /setup` 检查用户数量和创建用户之间存在竞态，可能创建多个管理员
- **修复:** 使用数据库级锁或唯一约束

### H-3: 无密码复杂度要求
- **文件:** `backend/app/schemas.py:21`, `backend/app/routers/auth.py:19-22`
- **问题:** 仅要求 `min_length=6`，可设置 `"111111"` 等弱密码
- **修复:** 添加大小写、数字、特殊字符要求

### H-4: 无 Token 吊销/登出机制
- **文件:** `backend/app/auth.py:27-42`
- **问题:** JWT 24 小时有效期内无法撤销，修改密码不会使已签发的 token 失效
- **修复:** 实现 token 黑名单，或修改密码时使旧 token 失效

### H-5: LLM 错误响应泄露内部信息
- **文件:** `backend/app/llm_client.py:69-77`, `backend/app/routers/weekly.py:95`
- **问题:** 上游 API 错误详情、内部 URL 等直接返回给客户端
- **修复:** 返回通用错误消息，详细信息仅记录在服务端日志

### H-6: SSRF 漏洞（用户可控 LLM API URL）
- **文件:** `backend/app/routers/config.py:30-43`, `backend/app/llm_client.py:63-64`
- **问题:** `llm_api_url` 可设置为内网地址（如云元数据 `http://169.254.169.254/`），造成 SSRF
- **修复:** 验证 URL 协议（仅允许 https），拒绝私有 IP 地址

### H-7: JWT 存储在 localStorage（前端）
- **文件:** `frontend/src/App.jsx:25`, `frontend/src/api/index.js:10`
- **问题:** localStorage 可被任意 JS 访问，XSS 攻击可窃取 token
- **修复:** 改用 httpOnly Cookie，或至少存储在内存中

### H-8: 容器以 root 用户运行
- **文件:** `Dockerfile`
- **问题:** 未指定 `USER` 指令，应用以 root 权限运行
- **修复:** 添加非 root 用户并切换

### H-9: JWT 密钥硬编码在 Docker 镜像层
- **文件:** `Dockerfile:41`
- **问题:** `ENV JWT_SECRET_KEY=change-this-in-production` 烘焙在镜像中，`docker inspect` 可见
- **修复:** 移除 `ENV` 行，仅在运行时注入

### H-10: docker-compose 弱默认密钥
- **文件:** `docker-compose.yml:13`
- **问题:** `JWT_SECRET_KEY=${JWT_SECRET_KEY:-super-secret-change-me}` 回退值可猜测
- **修复:** 移除默认值，未设置时直接报错

### H-11: 无安全响应头
- **文件:** `backend/main.py`
- **问题:** 缺少 `X-Content-Type-Options`、`X-Frame-Options`、`Strict-Transport-Security`、`Content-Security-Policy`
- **修复:** 添加安全头中间件

---

## 三、Medium 级别问题 (27)

### 后端 (7)

| # | 文件 | 问题 | 修复 |
|---|------|------|------|
| M-1 | `backend/app/schemas.py:28-29` | 日报内容无长度限制 | 添加 `max_length` |
| M-2 | `backend/app/routers/tokens.py:21` | Token 名称无长度限制 | 添加 `max_length` |
| M-3 | `backend/app/schemas.py:79-80` | LLM API URL 无格式验证 | 使用 `HttpUrl` 类型 |
| M-4 | `backend/app/auth.py:55` | JWT `sub` 解析 `int()` 无异常处理 | try/except 返回 401 |
| M-5 | `backend/app/routers/weekly.py:60-77` | 手动编辑覆盖 `generated_at` | 添加独立 `updated_at` 字段 |
| M-6 | `backend/main.py:21-34` | `_init_db()` 异常无 rollback | 添加 `db.rollback()` |
| M-7 | `backend/main.py:74-80` | SPA catch-all 可能泄露文件 | 验证 resolve 路径在 STATIC_DIR 内 |

### 前端 (10)

| # | 文件 | 问题 | 修复 |
|---|------|------|------|
| M-8 | `DailyReport.jsx:199-202` | `handleDelete` 无错误处理 | 添加 try/catch |
| M-9 | `DailyReport.jsx:212-215` | `key={refreshKey}` 强制重建组件 | 改用 prop 传递刷新信号 |
| M-10 | `WeeklyReport.jsx:55-66` | `savedReports` 请求后未使用（死代码） | 移除 |
| M-11 | `DailyReport.jsx`, `WeeklyReport.jsx` | `getMonday` 等工具函数重复定义 | 提取到 `utils/date.js` |
| M-12 | `CalendarView.jsx:166-206` | 日历单元格无键盘可访问性 | 添加 `role="button"` + `tabIndex` |
| M-13 | `DailyReport.jsx:118-119` | 周列表项无键盘可访问性 | 同上 |
| M-14 | `DailyEditModal.jsx:43` | 模态框无 `role="dialog"` | 添加 ARIA 属性 |
| M-15 | `api/index.js:42-43` | 查询参数未 URL 编码 | 添加 `encodeURIComponent` |
| M-16 | `WeeklyReport.jsx:139-158` | `setTimeout` 未清理 | 使用 `useEffect` cleanup |
| M-17 | `global.css:1387-1389` | `!important` 覆盖内联样式 | 移除内联样式改用 CSS 类 |

### 基础设施 (10)

| # | 文件 | 问题 | 修复 |
|---|------|------|------|
| M-18 | `Dockerfile:2,18` | 基础镜像未固定版本 | 固定 patch 版本 |
| M-19 | `Dockerfile:11` | pnpm install 失败时静默回退 | 移除 stderr 重定向 |
| M-20 | `docker-compose.yml:1` | `version: '3.8'` 已弃用 | 移除 |
| M-21 | `docker-compose.yml` | 无 healthcheck | 添加 |
| M-22 | `backend/main.py` | 无 `/health` 端点 | 添加 |
| M-23 | `docker-compose.yml:9` | 端口绑定 `0.0.0.0` | 改为 `127.0.0.1:8000:8000` |
| M-24 | CORS | 允许所有来源（同 C-2） | 限制来源 |
| M-25 | 无速率限制 | 同 H-1 | 添加中间件 |
| M-26 | 无 HTTPS | 未配置 TLS 终止 | 文档说明或添加 nginx |
| M-27 | `.env.example` | 与 `config.py` 默认值不一致 | 统一 |

---

## 四、Low 级别问题 (21)

### 后端
- L-1: `python-jose` 不再维护，建议迁移至 `PyJWT`
- L-2: bcrypt 版本固定但无 lockfile
- L-3: JWT 未使用 httpOnly Cookie（与前端 H-7 关联）
- L-4: 无安全响应头（已合并到 H-11）
- L-5: `datetime.utcnow` 已弃用，应改用 `datetime.now(UTC)`

### 前端
- L-6: `document.execCommand('copy')` 已弃用，应使用 `navigator.clipboard`
- L-7: `ThemeContext` 值未 memoize
- L-8: `!important` 在多处使用（移动端菜单、桌面端 textarea）
- L-9: `setTimeout` 组件卸载后警告
- L-10: 关闭按钮使用字符 `✕` 而非图标
- L-11: `handleDelete` 签名不一致
- L-12: `CalendarView` 日期计算可 memoize
- L-13: `handleSave` 未使用 `useCallback`
- L-14: `Settings.jsx:101` 测试连接前先保存配置（非预期行为）
- L-15: 响应式设计整体良好（正面）

### 基础设施
- L-16: 无 `.dockerignore` 文件
- L-17: 无资源限制（内存/CPU）
- L-18: 发布脚本无冒烟测试
- L-19: 发布脚本始终推送 latest 标签
- L-20: 日志未配置大小限制
- L-21: PWA API 缓存可能返回过期数据

---

## 五、Info 级别 (12)

- ✅ 无 SQL 注入风险（全部使用 SQLAlchemy ORM 参数化查询）
- ✅ API Token 明文存储在数据库（建议存储哈希）
- ✅ 单用户系统设计（按设计）
- ✅ 无 HTTPS 强制（需文档说明）
- ✅ 无 dangerouslySetInnerHTML（安全）
- ✅ 触摸目标符合 WCAG 2.5.5（44px）
- ✅ 响应式设计完善（移动端侧边栏、桌面端顶栏、安全区域适配）
- ✅ Hook 规则正确遵循
- ✅ 代码风格一致（单引号、无分号、2 空格缩进）
- ✅ Vite source map 默认关闭（正确）
- ✅ .gitignore 正确排除 .env 和 data/
- ✅ aria-label 在按钮上正确使用

---

## 六、优先修复建议

### 立即修复（影响生产安全）
1. **C-1 + C-3:** 移除硬编码 JWT 密钥默认值，强制环境变量；API Key 脱敏返回
2. **C-2:** 限制 CORS 来源
3. **H-6:** LLM URL SSRF 防护
4. **H-8 + H-9:** Docker 非 root 用户 + 移除镜像中的密钥

### 短期修复（1-2 周）
5. **H-1 + H-2:** 登录速率限制 + 初始化接口防竞态
6. **H-3:** 密码复杂度要求
7. **H-4:** Token 吊销机制
8. **H-11:** 安全响应头
9. **M-7:** SPA 路径遍历防护

### 中期优化（1 个月）
10. **M-11:** 提取共享工具函数
11. **M-12/M-13/M-14:** 前端可访问性改进
12. **M-18-M-22:** Docker 配置优化
13. **L-5:** 替换 `datetime.utcnow`
14. **L-1:** 评估迁移至 PyJWT
