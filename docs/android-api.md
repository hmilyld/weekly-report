# Android 客户端对接说明

Android 客户端与网页端使用**同一套 `/api/v1` 数据接口**，认证方式为 API Token。旧的 `/api/v1/external/*` 已移除。

## 1. 认证

- 在网页端「系统配置 → API Token」创建 Token（完整值只显示一次）。
- 每个请求携带：

```
X-API-Token: <token>
```

- Token 仅具备**数据权限**：可读写日报 / 周报 / 月报 / 待办；调用 `/auth/change-password`、`/auth/logout`、`/config`、`/users`、`/tokens` 会返回 `401`（凭据类型不被接受；`403` 只表示已认证但角色不足）。`/auth/login`、`/auth/status`、`/auth/setup` 本身无需认证。
- 若同时携带 JWT 与 Token，以 JWT 为准；JWT 无效时不会回退到 Token。客户端固定用一种认证方式即可。
- 当前版本 Token 为长期有效、明文存储、改密不会自动吊销（加固计划见 README）。需要作废时，用 JWT 调用 `DELETE /api/v1/tokens`（吊销全部）或 `DELETE /api/v1/tokens/{id}`。在 Android 端应存入 `EncryptedSharedPreferences` / Keystore，不要写入日志或明文备份。

## 2. 端点

所有路径前缀 `/api/v1`。日期格式 `yyyy-mm-dd`；周报以**周一**为 `week_start`。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/daily?start_date=&end_date=` | 按日期范围读取日报 |
| GET | `/daily/week/{week_start}` | 按周读取日报 |
| POST | `/daily` | 写入日报（见下文 append / date 语义） |
| DELETE | `/daily/{date}` | 删除某天日报 |
| GET | `/weekly?limit=` | 最近周报（默认 12，`limit` 1–52） |
| GET | `/weekly/{week_start}` | 单条周报（未生成返回 404） |
| POST | `/weekly/{week_start}?force=` | 生成周报；`force=false` 且已存在则不调用模型 |
| PUT | `/weekly/{week_start}` | 编辑正文 |
| GET | `/monthly?limit=` | 最近月报（默认 12，`limit` 1–120） |
| GET | `/monthly/{year}/{month}` | 单条月报 |
| POST | `/monthly/{year}/{month}` | 生成月报 |
| PUT | `/monthly/{year}/{month}` | 编辑正文 |
| GET | `/tasks` | 全部待办 |
| GET | `/tasks/pending` | 未完成待办 |
| GET | `/tasks/completed?offset=&limit=` | 已完成待办（分页） |
| POST | `/tasks` | 新建待办（`content` + 可选 `deadline`） |
| PUT | `/tasks/{id}` | 更新内容 / 截止日期 / 完成状态 |
| DELETE | `/tasks/{id}` | 删除待办 |

完整机器可读定义：`GET /openapi.json`。

## 3. 日报写入语义

```json
POST /api/v1/daily
{"content": "今天完成了 xxx", "append": true}
```

- `date` 省略 → 默认今天；显式传入则写指定日期。
- `append` 默认 `false`（覆盖当天内容）；`true` 时在已有内容后追加，以换行分隔。
- 响应为 canonical 日报对象（`id`、`date`、`content`、时间戳）。
- **注意**：`content` 请求字段超过 50000 字符会被拒（422）。

## 4. 周报生成语义

```
POST /api/v1/weekly/2026-11-16?force=false
```

- `force` 默认 `true`：总是调用模型重新生成。
- `force=false` 且该周已有周报：直接返回现有内容，`generated=false`，不消耗模型调用。
- `force=false` 但已有周报无法解密：返回 `409`（`decryption_failed`），不会把空内容当结果返回。
- 生成失败返回 `502`（模型配置或网络问题）；该周无日报或全为空返回 `400`。

## 5. 读取失败的表示（重要）

数据列表响应含 `_decryption_failed` 布尔字段：

```json
{"reports": [{"date": "2026-11-17", "content": "", "_decryption_failed": true}], "_decryption_failed": true}
```

为 `true` 时表示服务端密钥不可用（主密钥配置错误等），**不要**把空字符串当作"没有数据"展示给用户；应提示"内容暂时无法解密，请在网页端检查服务器配置"。

## 6. 错误码

| 状态码 | `code` / 含义 | 客户端处理 |
|---|---|---|
| 400 | 参数越界（如周起始日超范围、截止日期早于今天） | 修正请求参数 |
| 401 | Token 无效或已删除 | 提示重新生成 Token |
| 403 | 已认证但角色不足 | 改用管理员账号，或改用网页端 |
| 404 | 周报/月报尚未生成 | 展示"未生成"，可触发生成 |
| 409 | `encryption_key_missing` | 账号尚未完成加密迁移：提示先在网页端登录一次 |
| 409 | `decryption_failed` | 内容无法解密：提示检查服务端密钥配置 |
| 422 | 请求体验证失败 | 检查字段格式（日期、长度） |
| 502 | LLM 生成失败 | 提示稍后重试或检查模型配置 |

## 7. 已移除接口的替代

| 旧接口 | 替代 |
|---|---|
| `POST /external/daily` | `POST /daily`（`date` 可省略，`append` 同义） |
| `GET /external/daily/current-week` | `GET /daily?start_date=<周一>&end_date=<周日>` |
| `GET /external/weekly/recent` | `GET /weekly`（最近 12 条） |
| `POST /external/weekly/generate` | `POST /weekly/{week_start}?force=` |
| `GET /external/tasks/pending` | `GET /tasks/pending` |
| `POST /external/tasks` | `POST /tasks` |
| `GET /external/docs` | `GET /openapi.json` |

## 6. 认证失败与 Token 管理

- `401`：未带凭据、Token 无效、或 JWT 已过期/因改密失效——重新登录或改用新 Token。
- `403`：凭据类型不对（例如用 API Token 访问 `/config`、`/users`、`/tokens`）或角色不足。
- 改密**不会**吊销 API Token；需要吊销时用 JWT 调用 `DELETE /api/v1/tokens`（吊销全部）或 `DELETE /api/v1/tokens/{id}`。
