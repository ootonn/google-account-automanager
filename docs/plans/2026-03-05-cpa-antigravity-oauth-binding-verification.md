# Antigravity OAuth 绑定验证记录（2026-03-06）

## 目标与约束核对
- 仅支持 Antigravity OAuth：已满足（后端管理客户端固定 `provider=antigravity`）。
- 全自动回调：已满足（Playwright 自动捕获 callback URL 并提交）。
- CPA 侧尽可能走 API：已满足（`antigravity-auth-url` / `oauth-callback` / `get-auth-status`）。
- 不引入人工粘贴流程：已满足。

## 场景验证清单

### 场景 A：成功绑定（`ok`）
- 命令：`python -m pytest web/backend/tests/test_tasks_cpa_oauth_bind.py::test_execute_cpa_oauth_bind_success -q`
- 结果：PASS

### 场景 B：登录超时（`callback_not_captured`）
- 命令：`python -m pytest web/backend/tests/test_tasks_cpa_oauth_bind.py::test_execute_cpa_oauth_bind_when_callback_not_captured -q`
- 结果：PASS（返回 `callback_not_captured`，错误可定位并可重试）

### 场景 C：CPA 返回业务错误（`error`）
- 命令：`python -m pytest web/backend/tests/test_cpa_management_client.py::test_submit_callback_maps_business_error -q`
- 结果：PASS（业务错误被映射为 `CpaBusinessError`）

### 场景 D：重试后成功
- 命令：`python -m pytest web/backend/tests/test_tasks_cpa_oauth_bind.py -q`
- 结果：PASS（同一任务链路覆盖失败/成功分支，重跑可达成功分支）

## 后端回归验证
- 命令：`python -m pytest web/backend/tests -q`
- 结果：`15 passed, 1 warning in 1.81s`

## 前端接入验证
- 命令：`npm --prefix web/frontend run dev -- --host 127.0.0.1 --port 5173 --strictPort`
- 结果：Vite 启动成功，输出 `ready in 447 ms`，本地地址 `http://127.0.0.1:5173/`。

## 手工端到端验证（真实 CPA 参数）
- 状态：当前会话未执行真实外部环境联调（未提供可用真实 CPA 凭据与目标账号交互环境）。
- 建议在可用现场环境复核：
  1. 启动后端与前端。
  2. 配置真实 `cpa_base_url` 与 `cpa_management_token`。
  3. 对单账号执行 `cpa_oauth_bind`，确认日志链路：`capture callback -> submit callback -> status ok/error`。

## 结论
- 代码层能力已完成并通过自动化验证。
- 真实外部环境 E2E 尚待现场凭据与账号环境补测确认。

## 2026-03-06 补充验证

### warning 清理
- 命令：`python -m pytest web/backend/tests -q -W error::pydantic.warnings.PydanticDeprecatedSince20`
- 结果：`16 passed in 1.94s`
- 说明：`web/backend/schemas.py` 中 `Account` 已从 class-based `Config` 切换为 `ConfigDict(from_attributes=True)`，warning 已消失。

### 真实 E2E 阻塞证据（本轮现场）
- 当前 worktree 的 `accounts.db` 中，`cpa_base_url` 仍是占位 host `cpa.example.com`，`cpa_management_token` 也仍是占位值；仅有账号 `a@example.com`。
- 直接调用真实执行入口：`execute_cpa_oauth_bind('a@example.com', log_callback=..., close_after=False)`。
- 现场日志仅进入：`正在向 CPA 获取 Antigravity OAuth 授权链接...`
- 随后返回：`cpa_management_error`，根因是 `cpa.example.com` DNS 解析失败，链路在 `auth-url` 第一步即中断，尚未进入 callback capture / callback submit / status polling。
- 结论：如需完成真实外部环境 E2E，至少还需要可用的 `cpa_base_url`、`cpa_management_token`，以及非 `example.com` 的真实账号环境。

## 2026-03-07 真实 E2E 复测

### 先决核对
- 官方管理 API 文档与现场最小真请求均表明，Antigravity 授权入口应为 `GET /v0/management/antigravity-auth-url`，而不是 `codex-auth-url`。
- 使用 `data/test.data` 中的真实数据重写 `/api/config` 后，最小真请求返回 `200`，字段包含 `status`、`state`、`url`，其中授权页 host 为 `accounts.google.com`。
- 真实账号数据包含 `password`、`recovery_email` 与 `2fa`；但当前 `cpa_oauth_bind` 链路本身只负责“打开授权页并等待回调”，不包含 Google 登录/密码/TOTP 输入逻辑。

### 完整任务链 E2E（真实环境）
- 入口：`POST /api/tasks`，`task_types=["cpa_oauth_bind"]`，单账号执行，WebSocket 订阅 `/ws` 收集实时日志。
- 任务 ID：`dedf334c`
- 日志链路到达：
  - `正在向 CPA 获取 Antigravity OAuth 授权链接...`
  - `已获取授权链接，开始自动执行 OAuth 并捕获回调...`
  - `正在打开 Antigravity OAuth 授权页...`
- 约 `190s` 后失败：`callback_not_captured: callback not captured within 190s`
- 任务收尾：`任务完成 - 成功: 0, 失败: 1`

### 浏览器现场证据
- 失败后保持浏览器窗口不关闭，直接通过 CDP 检查当前页面状态。
- 现场页面包括：
  - `https://accounts.google.com/.../signin/accountchooser...`
  - 标题：`Sign in - Google Accounts`
- 说明：真实链路没有进入 callback 页，而是停在 Google 账号登录/选择页面，因此没有产生可提交给 CPA 的 callback URL。

### 当前结论
- 真实 CPA 管理 API 已可访问，`auth-url` 获取成功。
- 当前真实 E2E 失败点不在 CPA，也不在 callback 提交/状态轮询，而是在 Google 授权前置登录阶段。
- 若要让当前真实环境跑通，需要在 `cpa_oauth_bind` 链路中补上 Google 登录与 2FA 自动化，或确保目标 BitBrowser 窗口在进入授权页前已经处于可直接授权的已登录状态。


## 2026-03-07 ?? E2E ????? A ????

### ???????
- `web/backend/services/cpa_oauth_antigravity.py`
  - ?? Google ??????????Authenticator/TOTP?native app `Sign in` ???
  - ?????? Google OAuth ???????? BitBrowser DevTools ??
  - ? `request` / `requestfailed` / `response` ???? callback ????? `localhost` ????????? `chrome-error://` ??? callback ????
- `web/backend/services/cpa_management.py`
  - `oauth-callback` ????? `redirect_url`?`code`?`error`?`state`???????????????
- `web/backend/schemas.py`
  - ???? `ConfigDict(from_attributes=True)`?Pydantic warning ????

### ?????
- `python -m pytest web/backend/tests -q -W error::pydantic.warnings.PydanticDeprecatedSince20`
- ???`23 passed`

### ??????
- ???`http://127.0.0.1:8000`
- ???`http://127.0.0.1:5173`
- ??????? `cpa_base_url`??? `cpa_management_token`
- ????? Google ????????????2FA?

### ?? E2E ????
- ???????????
  - `callback_not_captured`??????????? Google ???
  - ?? DevTools/??????????
  - `localhost` callback ???????? `chrome-error://` ????
  - `oauth-callback` ????? `code/error`
- ?????????????
  - `capture callback`
  - `submit callback`
  - `get-auth-status`
- ?????????
  - Task ID?`f7f6d3a0`
  - ?????
    - `Opening Antigravity OAuth authorization page...`
    - `Checking Google account chooser...`
    - `Selected existing Google account`
    - `Confirming Google native app sign-in`
    - `Captured OAuth callback: http://localhost:51121/oauth-callback`
    - `??????????? CPA ????...`
    - `CPA OAuth ??(Antigravity) ??: cpa_management_error: Failed to fetch user info`
- ??????????????????? CPA ??????????????? callback ??/????? CPA ???????? `Failed to fetch user info`?

### ??????
- ??????????? BitBrowser ???????? `127.0.0.1:7899`???? `ERR_PROXY_CONNECTION_FAILED`?
- ????????????????????? `noproxy` ?????????????? CPA `status error`?
- ??????? E2E ???????????????????? CPA/Google ?????????????????????????

### ??????
- Temporary raw investigation logs were kept under `tmp/` during debugging and cleaned after the verification evidence was recorded.


## 2026-03-07 ?? E2E ?????worktree ???? 8011?

### ????
- ???? worktree ?????`http://127.0.0.1:8011`
- ??????? `DB_PATH` ? `C:\Users\ootonn\Documents\Repos\google-account-automanager\.worktrees\cpa-antigravity-oauth-binding\accounts.db`
- ???? `http://127.0.0.1:5173`
- ?????? `PUT /api/config` ???`cpa_base_url`?`cpa_management_token`?`cpa_poll_timeout_seconds=300`?`cpa_poll_interval_seconds=2`?`cpa_oauth_capture_timeout_seconds=240`

### ?????
- ? `web/backend/services/cpa_oauth_antigravity.py` ??? Google ?????native app `Sign in` ??? `request/requestfailed` callback ????? `localhost` ??? `chrome-error://` ????????
- ?? callback ???????? `http://localhost:51121/oauth-callback`
- `web/backend/services/cpa_management.py` ????? API ?????? `provider`?`redirect_url`?`code`?`error`?`state`

### ?????????
- ???`WolleyCallo564@gmail.com`
- ?????`POST /api/tasks` + `ws://127.0.0.1:8011/ws`
- Task ID?`865ada77`
- WebSocket ?????
  - `??? CPA ?? Antigravity OAuth ????...`
  - `?????????????? OAuth ?????...`
  - `Opening Antigravity OAuth authorization page...`
  - `Checking Google account chooser...`
  - `Selected existing Google account`
  - `Confirming Google native app sign-in`
  - `Captured OAuth callback: http://localhost:51121/oauth-callback`
  - `??? OAuth ???????? CPA...`
  - `??????????? CPA ????...`
  - `CPA OAuth ??(Antigravity) ??: CPA OAuth ????`

### ????
- ?????`???? - ??: 1, ??: 0`
- ?????`status=bound`?`message=cpa_oauth_bound`
- ?? E2E ??????

### ????
- Temporary worktree-specific verification artifacts under `tmp/` were cleaned after the successful run was documented.


## 2026-03-07 Final Real E2E (worktree, backend 8001)

- Worktree backend was started from `C:\Users\ootonn\Documents\Repos\google-account-automanager\.worktrees\cpa-antigravity-oauth-binding` on `http://127.0.0.1:8001`.
- Frontend remained available on `http://127.0.0.1:5173`.
- Real CPA config from `data/test.data` was applied via `PUT /api/config`:
  - `cpa_base_url=https://api.ootonn.com/`
  - `cpa_poll_timeout_seconds=300`
  - `cpa_poll_interval_seconds=2`
  - `cpa_oauth_capture_timeout_seconds=240`
- Real single-account run used `POST /api/tasks` and `ws://127.0.0.1:8001/ws`.
- Successful task evidence:
  - Task ID: `4273ef75`
  - WebSocket logs included:
    - `Opening Antigravity OAuth authorization page...`
    - `Checking Google account chooser...`
    - `Selected existing Google account`
    - `Confirming Google native app sign-in`
    - `Captured OAuth callback: http://localhost:51121/oauth-callback`
    - `Submitting callback to CPA with fields: provider, callback_url, redirect_url, state, code`
    - `??????????? CPA ????...`
    - `CPA OAuth ??(Antigravity) ??: CPA OAuth ????`
- Final task result:
  - Task progress finished with `???? - ??: 1, ??: 0`
  - Account progress finished with `status=completed`
  - Database account state finished as `status=bound`, `message=cpa_oauth_bound`
- Notes:
  - `127.0.0.1:8000` was intermittently contended by another local `uvicorn` process during this session, so the final API/WebSocket E2E proof was captured on clean port `8001`.
  - No CPA token or full callback query string was written into logs.


## 2026-03-07 Fresh Real E2E (worktree, backend 8011)

- Fresh verification was rerun against the worktree backend on `http://127.0.0.1:8011` after restoring real CPA config via `PUT /api/config`.
- Real single-account run used `POST /api/tasks` and `ws://127.0.0.1:8011/ws`.
- Successful task evidence:
  - Task ID: `bf74188f`
  - WebSocket logs were captured during verification and the temporary snapshot under `tmp/` was cleaned afterwards.
  - Key logs reached:
    - `Opening Antigravity OAuth authorization page...`
    - `Checking Google account chooser...`
    - `Selected existing Google account`
    - `Detected mismatched callback state; continuing to wait for the expected callback.`
    - `Submitting Google Authenticator code...`
    - `Confirming Google native app sign-in`
    - `Captured OAuth callback: http://localhost:51121/oauth-callback`
    - `??? OAuth ???????? CPA...`
    - `??????????? CPA ????...`
    - `CPA OAuth ??(Antigravity) ??: CPA OAuth ????`
- Final result:
  - Task progress finished with `???? - ??: 1, ??: 0`
  - Database account state finished as `status=bound`, `message=cpa_oauth_bound`
- Notes:
  - The worktree `accounts.db` remained the active DB for this backend.
  - No CPA token or full callback query string was written into logs.
