# CPA Antigravity OAuth Binding Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在现有任务系统中新增仅面向 Antigravity 的全自动 CPA OAuth 绑定能力（无人工复制粘贴回调 URL）。

**Architecture:** 后端新增 `CpaManagementClient` 负责 CPA 管理 API 调用，新增 Antigravity OAuth 自动化服务负责 BitBrowser+Playwright 登录与回调捕获，由 `tasks.py` 新任务类型编排全流程并推送状态；前端仅负责发起任务与配置项管理。

**Tech Stack:** FastAPI, SQLite(config 表), requests, Playwright(CDP), Vue 3, Axios, pytest

---

### Task 1: 建立测试基线与任务类型骨架

**Files:**
- Modify: `pyproject.toml`
- Modify: `web/backend/schemas.py`
- Create: `web/backend/tests/conftest.py`
- Create: `web/backend/tests/test_schema_cpa_oauth.py`

**Step 1: 写失败测试（任务类型与配置模型）**

```python
# web/backend/tests/test_schema_cpa_oauth.py
from web.backend.schemas import TaskType, ConfigUpdate, ConfigResponse

def test_task_type_contains_cpa_oauth_bind():
    assert TaskType.cpa_oauth_bind.value == "cpa_oauth_bind"

def test_config_contains_cpa_fields():
    update = ConfigUpdate(
        cpa_base_url="https://cpa.example.com",
        cpa_management_token="token",
        cpa_poll_timeout_seconds=300,
        cpa_poll_interval_seconds=2,
        cpa_oauth_capture_timeout_seconds=180,
    )
    assert update.cpa_base_url.startswith("https://")
```

**Step 2: 运行测试确认失败**

Run: `uv run pytest web/backend/tests/test_schema_cpa_oauth.py -q`  
Expected: FAIL，提示 `TaskType` 无 `cpa_oauth_bind` 或 `ConfigUpdate` 缺字段。

**Step 3: 最小实现让测试通过**
- 在 `TaskType` 中新增 `cpa_oauth_bind = "cpa_oauth_bind"`。
- 在 `ConfigUpdate/ConfigResponse` 中新增：
  - `cpa_base_url`
  - `cpa_management_token`
  - `cpa_poll_timeout_seconds`
  - `cpa_poll_interval_seconds`
  - `cpa_oauth_capture_timeout_seconds`

**Step 4: 重跑测试**

Run: `uv run pytest web/backend/tests/test_schema_cpa_oauth.py -q`  
Expected: PASS。

**Step 5: Commit**

```bash
git add pyproject.toml web/backend/schemas.py web/backend/tests/conftest.py web/backend/tests/test_schema_cpa_oauth.py
git commit -m "test: add schema baseline for cpa antigravity oauth task"
```

### Task 2: 扩展配置 API（Antigravity 固定，不暴露 provider）

**Files:**
- Modify: `web/backend/routers/config.py`
- Create: `web/backend/tests/test_config_router_cpa_fields.py`

**Step 1: 写失败测试（读写 CPA 配置字段）**

```python
# web/backend/tests/test_config_router_cpa_fields.py
from fastapi.testclient import TestClient
from web.backend.main import app

def test_config_get_contains_cpa_fields():
    c = TestClient(app)
    data = c.get("/api/config").json()
    assert "cpa_base_url" in data
    assert "cpa_management_token" in data
```

**Step 2: 运行测试确认失败**

Run: `uv run pytest web/backend/tests/test_config_router_cpa_fields.py -q`  
Expected: FAIL，返回 JSON 不含 CPA 字段。

**Step 3: 最小实现**
- `get_all_config` 增加 CPA 字段读取。
- `update_config` 增加对应写入逻辑。
- 保证不新增 `cpa_provider` 字段（硬编码 Antigravity）。

**Step 4: 重跑测试**

Run: `uv run pytest web/backend/tests/test_config_router_cpa_fields.py -q`  
Expected: PASS。

**Step 5: Commit**

```bash
git add web/backend/routers/config.py web/backend/tests/test_config_router_cpa_fields.py
git commit -m "feat: add cpa config fields without provider option"
```

### Task 3: 新增 CPA 管理 API 客户端（仅 Antigravity）

**Files:**
- Create: `web/backend/services/__init__.py`
- Create: `web/backend/services/cpa_management.py`
- Create: `web/backend/tests/test_cpa_management_client.py`

**Step 1: 写失败测试（请求路径/参数/错误映射）**

```python
# web/backend/tests/test_cpa_management_client.py
from web.backend.services.cpa_management import CpaManagementClient

def test_build_auth_url_request_contains_antigravity_provider():
    client = CpaManagementClient("https://cpa.example.com", "token")
    req = client._build_auth_url_request("a@example.com")
    assert req["params"]["provider"] == "antigravity"
```

**Step 2: 运行测试确认失败**

Run: `uv run pytest web/backend/tests/test_cpa_management_client.py -q`  
Expected: FAIL，模块不存在。

**Step 3: 最小实现**
- 创建 `CpaManagementClient`，包含：
  - `get_antigravity_auth_url(email)`
  - `submit_oauth_callback(callback_url)`
  - `get_auth_status(state)`
- `provider` 内部写死 `antigravity`，不接受外部传入。
- 统一超时、重试、异常类型（网络错误、HTTP 错误、业务错误）。

**Step 4: 重跑测试**

Run: `uv run pytest web/backend/tests/test_cpa_management_client.py -q`  
Expected: PASS。

**Step 5: Commit**

```bash
git add web/backend/services/__init__.py web/backend/services/cpa_management.py web/backend/tests/test_cpa_management_client.py
git commit -m "feat: add cpa management client for antigravity oauth"
```

### Task 4: 新增 Antigravity OAuth 自动化服务（回调 URL 自动捕获）

**Files:**
- Create: `web/backend/services/cpa_oauth_antigravity.py`
- Create: `web/backend/tests/test_cpa_oauth_callback_parser.py`

**Step 1: 写失败测试（回调 URL 判定与提取）**

```python
# web/backend/tests/test_cpa_oauth_callback_parser.py
from web.backend.services.cpa_oauth_antigravity import is_oauth_callback_url

def test_detect_callback_url_with_code_and_state():
    url = "https://example.com/callback?code=abc&state=xyz"
    assert is_oauth_callback_url(url) is True
```

**Step 2: 运行测试确认失败**

Run: `uv run pytest web/backend/tests/test_cpa_oauth_callback_parser.py -q`  
Expected: FAIL，模块或函数不存在。

**Step 3: 最小实现**
- 封装：
  - `open_and_run_antigravity_oauth(browser_id, auth_url, capture_timeout_seconds, log_callback)`
  - `is_oauth_callback_url(url)`
- 在 Playwright 中通过 `framenavigated/page.url` 监听 URL，捕获首个合法回调。
- 超时返回结构化错误 `callback_not_captured`。

**Step 4: 重跑测试**

Run: `uv run pytest web/backend/tests/test_cpa_oauth_callback_parser.py -q`  
Expected: PASS。

**Step 5: Commit**

```bash
git add web/backend/services/cpa_oauth_antigravity.py web/backend/tests/test_cpa_oauth_callback_parser.py
git commit -m "feat: add antigravity oauth browser automation callback capture"
```

### Task 5: 接入任务执行链路 `cpa_oauth_bind`

**Files:**
- Modify: `web/backend/routers/tasks.py`
- Create: `web/backend/tests/test_tasks_cpa_oauth_bind.py`

**Step 1: 写失败测试（任务路由支持新类型）**

```python
# web/backend/tests/test_tasks_cpa_oauth_bind.py
from fastapi.testclient import TestClient
from web.backend.main import app

def test_create_task_accepts_cpa_oauth_bind():
    c = TestClient(app)
    body = {
        "task_types": ["cpa_oauth_bind"],
        "emails": ["a@example.com"],
        "close_after": False,
        "concurrency": 1,
    }
    r = c.post("/api/tasks", json=body)
    assert r.status_code == 200
```

**Step 2: 运行测试确认失败**

Run: `uv run pytest web/backend/tests/test_tasks_cpa_oauth_bind.py -q`  
Expected: FAIL，枚举或执行分支不支持该任务类型。

**Step 3: 最小实现**
- 在 `run_task_sync` 的任务标签/执行分支中接入 `cpa_oauth_bind`。
- 新增 `execute_cpa_oauth_bind(email, log_callback, close_after)`：
  - 读取 CPA 配置
  - 调 `get_antigravity_auth_url`
  - 调 `open_and_run_antigravity_oauth` 捕获 `callback_url`
  - 调 `submit_oauth_callback`
  - 轮询 `get_auth_status`
  - 返回 `{success, message}`
- 按现有模式更新 DB `status/message` 与 WebSocket 日志。

**Step 4: 重跑测试**

Run: `uv run pytest web/backend/tests/test_tasks_cpa_oauth_bind.py -q`  
Expected: PASS。

**Step 5: Commit**

```bash
git add web/backend/routers/tasks.py web/backend/tests/test_tasks_cpa_oauth_bind.py
git commit -m "feat: wire antigravity oauth bind task into task runner"
```

### Task 6: 前端任务类型与配置面板接入

**Files:**
- Modify: `web/frontend/src/views/TasksView.vue`
- Modify: `web/frontend/src/api/index.js`

**Step 1: 写失败测试/检查点（最小可运行验证）**
- 由于当前项目无前端测试基线，先定义手工失败检查点：
  - 页面未显示“CPA OAuth 绑定（Antigravity）”任务选项。
  - 配置面板无 CPA 字段输入。

**Step 2: 实现最小 UI 变更**
- `taskTypes` 增加：
  - `{ value: 'cpa_oauth_bind', label: 'CPA OAuth 绑定(Antigravity)' }`
- 配置面板增加字段：
  - `cpa_base_url`
  - `cpa_management_token`（密码输入）
  - `cpa_poll_timeout_seconds`
  - `cpa_poll_interval_seconds`
  - `cpa_oauth_capture_timeout_seconds`
- 文案明确“仅支持 Antigravity OAuth”。

**Step 3: 本地运行验证**

Run: `npm --prefix web/frontend run dev`  
Expected: 页面可打开，任务类型与配置字段可见且可保存。

**Step 4: API 联调验证**
- 在 UI 保存配置后，调用 `/api/config` 能读回上述字段。
- 发起 `cpa_oauth_bind` 任务不报参数错误。

**Step 5: Commit**

```bash
git add web/frontend/src/views/TasksView.vue web/frontend/src/api/index.js
git commit -m "feat: add antigravity oauth bind controls in tasks ui"
```

### Task 7: 集成验证与文档收口

**Files:**
- Modify: `docs/plans/2026-03-04-cpa-oauth-binding-design.md`
- Create: `docs/plans/2026-03-05-cpa-antigravity-oauth-binding-verification.md`

**Step 1: 编写验证清单**
- 场景 A：成功绑定（`ok`）
- 场景 B：登录超时（`callback_not_captured`）
- 场景 C：CPA 返回业务错误（`error`）
- 场景 D：重试后成功

**Step 2: 执行后端测试**

Run: `uv run pytest web/backend/tests -q`  
Expected: 全部 PASS。

**Step 3: 执行手工端到端验证**
- 启动后端与前端。
- 配置真实 CPA 参数。
- 对 1 个账号执行 `cpa_oauth_bind`，确认日志出现“capture callback -> submit callback -> status ok/error”。

**Step 4: 补充验证记录文档**
- 写入每个场景结果、失败截图/日志关键片段、最终结论。

**Step 5: Commit**

```bash
git add docs/plans/2026-03-04-cpa-oauth-binding-design.md docs/plans/2026-03-05-cpa-antigravity-oauth-binding-verification.md
git commit -m "docs: add antigravity oauth bind verification report"
```

## 实施约束（必须遵守）
- Provider 不可配置，代码中固定 `antigravity`。
- 全流程不得要求人工复制粘贴 URL。
- 不可记录敏感 token 或完整 callback query 到日志。
- 单账号失败不影响批量其他账号。

## 建议执行顺序
1. Task 1 -> 2 -> 3（后端基础能力）
2. Task 4 -> 5（自动化链路与编排）
3. Task 6（前端接入）
4. Task 7（验证收口）
