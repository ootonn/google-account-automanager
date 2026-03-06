# Antigravity OAuth 绑定验证记录（2026-03-06）

## 目标与约束核对
- 仅支持 Antigravity OAuth：已满足（后端管理客户端固定 `provider=antigravity`）。
- 全自动回调：已满足（Playwright 自动捕获 callback URL 并提交）。
- CPA 侧尽可能走 API：已满足（`codex-auth-url` / `oauth-callback` / `get-auth-status`）。
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
