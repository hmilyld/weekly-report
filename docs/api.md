# HTTP API

所有接口前缀为 `/api/v1`。机器可读定义见 `/openapi.json`，交互式文档见 `/docs`。
Android 与其他客户端对接见 [`android-api.md`](android-api.md)。

## 认证

- 数据接口（日报、周报、月报、待办）同时接受 `Authorization: Bearer <JWT>` 与 `X-API-Token: <Token>`。
  两者同时携带时以 JWT 为准；JWT 无效时不会回退到 Token。
- 认证与管理接口（`/auth`、`/config`、`/users`、`/tokens`）仅接受 JWT。使用 API Token 调用返回 `401`；
  Token 只能读写内容数据，无法管理账号、配置或其他 Token。

登录失败限流按客户端 IP 计数，规则为 5 次 / 60 秒。部署在反向代理之后时，容器的对端地址是代理 IP，
需要把代理地址加入 `FORWARDED_ALLOW_IPS`（仅在代理可信时使用 `*`），否则所有客户端共用同一限流桶。

## 状态码

| 状态码 | 含义 |
|---|---|
| `400` | 参数越界，例如周起始日超出可处理范围、截止日期早于今天。响应体为 `{"detail": ...}` |
| `401` | 未认证或凭据失效，包括 JWT 过期、改密后旧 JWT 失效、API Token 无效 |
| `402` | 会话有效，但改密请求中的当前密码不正确；前端就地提示，不退出登录 |
| `403` | 已认证但角色不足，例如非管理员访问管理接口 |
| `409` | 加密密钥缺失或内容无法解密，拒绝写入或拒绝返回空内容 |
| `422` | 请求体或路径参数不合法（Pydantic 校验） |

## 端点

### 认证

| 方法 | 路径 | 说明 | 认证 |
|---|---|---|---|
| GET | `/auth/status` | 是否需要初始化 | 否 |
| POST | `/auth/setup` | 初始化第一个管理员账号 | 否 |
| POST | `/auth/login` | 登录并获取 token | 否 |
| POST | `/auth/change-password` | 修改密码，需当前密码，返回新 token | 是 |
| POST | `/auth/logout` | 退出登录，不影响同账号其他设备 | 是 |

### 日报

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/daily?start_date=&end_date=` | 按日期范围查询 |
| GET | `/daily/week/{week_start}` | 按周查询 |
| POST | `/daily` | 创建或覆盖某天日报；`date` 可省略，默认今天；`append=true` 追加 |
| DELETE | `/daily/{date}` | 删除某天的日报 |

### 周报与月报

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/weekly?limit=`、`/weekly/{week_start}` | 查询周报；`limit` 取值 1 至 52，默认 12 |
| POST | `/weekly/{week_start}?force=` | 生成或重新生成；`force=false` 且报告已存在时不调用模型，返回 `generated=false` |
| PUT | `/weekly/{week_start}` | 编辑正文 |
| GET | `/monthly?limit=`、`/monthly/{year}/{month}` | 查询月报；`limit` 取值 1 至 120，默认 12 |
| POST | `/monthly/{year}/{month}` | 生成或重新生成 |
| PUT | `/monthly/{year}/{month}` | 编辑正文 |

### 待办

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/tasks` | 全部待办 |
| GET | `/tasks/pending` | 未完成待办，支持 API Token |
| GET | `/tasks/completed?offset=&limit=` | 已完成待办，分页 |
| POST | `/tasks` | 新建待办，内容与可选截止日期 |
| PUT | `/tasks/{id}` | 更新内容、截止日期或完成状态 |
| DELETE | `/tasks/{id}` | 删除待办 |

### 配置（管理员）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/config` | 读取配置，API Key 脱敏 |
| PUT | `/config` | 更新配置 |
| POST | `/config/test` | 测试大模型连接 |

### 用户

| 方法 | 路径 | 说明 | 认证 |
|---|---|---|---|
| GET | `/users/me` | 当前用户，含最近登录时间 | 是 |
| GET | `/users` | 用户列表 | 管理员 |
| POST | `/users` | 创建用户 | 管理员 |
| PUT | `/users/{id}/role` | 修改角色 | 管理员 |
| DELETE | `/users/{id}` | 删除用户 | 管理员 |

### API Token

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/tokens` | 列出自己的 Token，返回值掩码 |
| POST | `/tokens` | 创建 Token，完整值只返回一次 |
| DELETE | `/tokens` | 吊销自己的全部 Token，用于换机或怀疑泄露 |
| DELETE | `/tokens/{id}` | 删除单个 Token |

Token 与登录密码相互独立：修改密码不会吊销 API Token，但会立即使旧 JWT 失效；需要吊销时使用
`DELETE /tokens`。当前版本 Token 明文存储、长期有效、无作用域限制，等效于该账号的数据读写权限，
应按凭据管理。

## 调用示例

API Token 与 JWT 使用同一套数据接口。创建入口为网页端「系统配置」中的 API Token 面板。

```bash
# 追加一条今天的日报，无需登录
curl -X POST http://localhost:18001/api/v1/daily \
  -H "X-API-Token: <Token>" \
  -H "Content-Type: application/json" \
  -d '{"content":"今天完成了 xxx","append":true}'

# 读取指定日期范围的日报
curl "http://localhost:18001/api/v1/daily?start_date=2026-11-16&end_date=2026-11-22" \
  -H "X-API-Token: <Token>"

# 生成周报；已存在时不覆盖，返回 generated=false
curl -X POST "http://localhost:18001/api/v1/weekly/2026-11-16?force=false" \
  -H "X-API-Token: <Token>"

# 未完成待办
curl http://localhost:18001/api/v1/tasks/pending \
  -H "X-API-Token: <Token>"
```

## 补充说明

- 旧的 `/api/v1/external/*` 已移除，请改用上表中的同义接口。第三方脚本需要按本文档重新指向，
  完整定义见 `/openapi.json`。
- 账号未完成加密迁移时（升级后从未登录过），写入接口返回 `409` 与 `code: encryption_key_missing`，
  不会写入明文；在网页端登录一次即可解决。内容无法解密时，读取与生成接口返回 `409`
  与 `code: decryption_failed`。
- 数据接口的读取响应带有 `_decryption_failed` 字段，客户端应据此提示用户，不应将空内容视为
  「没有数据」。周报接口在 `force=false` 且已有报告无法解密时返回 `409`。

## 健康检查

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 返回 `{"status":"ok"}`，用于容器健康检查 |
