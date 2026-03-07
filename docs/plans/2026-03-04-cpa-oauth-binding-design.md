# CPA OAuth 批量绑定设计

**目标**
- 在现有 BitBrowser 自动化体系内新增 CPA 绑定能力。
- OAuth 全流程必须在 BitBrowser 窗口内完成。
- 支持批量账号执行，失败可定位，可重试。

**约束**
- 复用当前任务系统（`web/backend/routers/tasks.py`）做批量与并发。
- 复用现有 BitBrowser 打开方式（`openBrowser` + Playwright CDP）。
- 参考现有 CPA 上传/清理模式（`auto_reg_gpt/src/register.py`, `auto_reg_gpt/src/clean.py`）。
- Provider 固定为 `antigravity`，不对外暴露可配置项。
- OAuth 回调 URL 必须自动捕获并提交，禁止人工复制粘贴。

## 方案对比

### 方案 A（推荐）：CPA OAuth URL + BitBrowser 授权 + 状态轮询
- 流程：
  1. 后端调用 CPA `GET /v0/management/antigravity-auth-url` 获取 `url` 与 `state`。
  2. 在目标账号对应 BitBrowser 窗口打开该 `url` 并完成授权。
  3. Playwright 自动捕获 OAuth callback URL（`framenavigated` + `page.url` 检测）。
  4. 后端调用 `POST /v0/management/oauth-callback` 自动提交 callback URL。
  5. 后端轮询 CPA `GET /v0/management/get-auth-status?state=...` 直到 `ok/error`。
  6. 可选用 `GET /v0/management/auth-files` 做结果核验。
- 优点：
  - API 简单，稳定，职责清晰（CPA 负责 token 落盘）。
  - 不需要本地自己交换 token，减少脆弱逻辑。
  - 与官方管理 API 文档一致，维护成本最低。
- 缺点：
  - 依赖 BitBrowser 页面在授权完成后能正确回调。

### 方案 B：本地自己做 OpenAI OAuth 交换后再上传 auth file
- 流程：类似 `register.py`，自行走授权和 token 交换，再 `POST /v0/management/auth-files` 上传。
- 优点：可完全自控。
- 缺点：实现复杂，易受上游变更影响，和“尽可能简单鲁棒”相冲突。

### 方案 C：自动化 CPA Web 管理面板点击操作
- 优点：看起来“所见即所得”。
- 缺点：最脆弱（UI 改版即坏），不建议。

## 推荐结论
- 采用**方案 A**，绑定链路固定为 Antigravity：
  - 主链路：`antigravity-auth-url` + 自动捕获 callback + `oauth-callback` + `get-auth-status`。
  - 不提供 provider 切换入口，所有 CPA 管理 API 请求都写死 `provider=antigravity`。

## 数据与状态设计（保持最小改动）
- 不新增数据库表。
- 复用 `config` 键值存储新增配置：
  - `cpa_base_url`
  - `cpa_management_token`
  - `cpa_poll_timeout_seconds`（默认 300）
  - `cpa_poll_interval_seconds`（默认 2）
  - `cpa_oauth_capture_timeout_seconds`（默认 180）
- 账号维度不强制新增字段，先通过任务日志 + `message` 展示绑定结果，避免 schema 膨胀。

## 批量执行策略
- 复用当前任务系统并发（1-5）。
- 默认建议并发 1-2（OAuth 页面交互稳定优先）。
- 每个账号独立状态机，互不影响；单账号失败不阻断其他账号。

## 失败恢复策略
- 网络失败：CPA API 调用指数退避重试。
- OAuth 超时：账号标记失败，允许重跑单账号任务。
- 回调未捕获：返回 `callback_not_captured`，账号标记失败并允许重试。
- 幂等策略：同账号重复绑定时先查 `auth-files`，可配置“跳过已存在”或“覆盖更新”。

## 安全策略
- OAuth 只在 BitBrowser 内进行，不在无头 HTTP 会话里模拟登录。
- 管理 Token 不写日志；前端输入框默认密码态展示。
- 所有外部调用统一超时与重试，避免线程长时间阻塞。

