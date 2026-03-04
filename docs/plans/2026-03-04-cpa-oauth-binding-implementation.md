# CPA OAuth 批量绑定 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在当前 BitBrowser 任务系统中新增 CPA OAuth 批量绑定任务，确保 OAuth 全流程都在 BitBrowser 内执行，并且支持失败重试与清晰日志。

**Architecture:** 后端先向 CPA 管理 API 申请 `codex-auth-url`，再通过 BitBrowser+Playwright 打开授权页完成登录；随后轮询 CPA 的 `get-auth-status` 确认完成。任务编排继续复用现有 `TaskExecutor` 并发模型，前端只新增任务类型与 CPA 配置字段。

**Tech Stack:** Python 3.11, FastAPI, requests, Playwright (CDP), BitBrowser API, Vue 3

---

### Task 1: 扩展配置模型与任务枚举

**Files:**
- Modify: `web/backend/schemas.py`
- Modify: `web/backend/routers/config.py`
- Modify: `web/frontend/src/views/ConfigView.vue`
- Modify: `web/frontend/src/views/TasksView.vue`

**Step 1: 写失败用例（配置字段完整性）**

```python
# tests/test_cpa_config_schema.py
def test_config_response_contains_cpa_fields():
    from web.backend.schemas import ConfigResponse
    data = ConfigResponse()
    assert hasattr(data, "cpa_base_url")
    assert hasattr(data, "cpa_management_token")
```

**Step 2: 运行测试确认失败**

Run: `python -m unittest discover -s tests -p "test_cpa_config_schema.py" -v`  
Expected: FAIL（缺少 `cpa_*` 字段）

**Step 3: 最小实现**

```python
class TaskType(str, Enum):
    cpa_bind_codex = "cpa_bind_codex"

class ConfigUpdate(BaseModel):
    cpa_base_url: Optional[str] = None
    cpa_management_token: Optional[str] = None
```

**Step 4: 运行测试确认通过**

Run: `python -m unittest discover -s tests -p "test_cpa_config_schema.py" -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add web/backend/schemas.py web/backend/routers/config.py web/frontend/src/views/ConfigView.vue web/frontend/src/views/TasksView.vue tests/test_cpa_config_schema.py
git commit -m "feat: add CPA config fields and task type enum"
```

### Task 2: 新建 CPA 管理 API 客户端

**Files:**
- Create: `cpa_client.py`
- Test: `tests/test_cpa_client.py`

**Step 1: 写失败用例（URL 标准化、响应解析、重试分支）**

```python
def test_normalize_base_url():
    from cpa_client import normalize_base_url
    assert normalize_base_url("https://x.com/") == "https://x.com"
```

**Step 2: 运行测试确认失败**

Run: `python -m unittest discover -s tests -p "test_cpa_client.py" -v`  
Expected: FAIL（模块不存在）

**Step 3: 写最小实现**

```python
def request_codex_auth_url(base_url, token, is_webui=True):
    # GET /v0/management/codex-auth-url
    # return {"url": "...", "state": "..."}
```

需包含：
- `request_codex_auth_url`
- `get_auth_status`
- `post_oauth_callback`（兜底）
- `list_auth_files`
- 统一 headers 与重试封装（指数退避）

**Step 4: 运行测试确认通过**

Run: `python -m unittest discover -s tests -p "test_cpa_client.py" -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add cpa_client.py tests/test_cpa_client.py
git commit -m "feat: add CPA management API client with retry"
```

### Task 3: 新建 BitBrowser OAuth 绑定执行器

**Files:**
- Create: `cpa_oauth_bind.py`
- Test: `tests/test_cpa_oauth_bind.py`

**Step 1: 写失败用例（回调 URL 提取、状态机超时）**

```python
def test_extract_state_and_code_from_callback_url():
    from cpa_oauth_bind import extract_oauth_params
    d = extract_oauth_params("http://localhost:1455/codex/callback?code=abc&state=xyz")
    assert d["code"] == "abc"
    assert d["state"] == "xyz"
```

**Step 2: 运行测试确认失败**

Run: `python -m unittest discover -s tests -p "test_cpa_oauth_bind.py" -v`  
Expected: FAIL

**Step 3: 写最小实现**

```python
def bind_cpa_codex_sync(browser_id, email, cpa_conf, log_callback=None, close_after=True):
    # 1) openBrowser(browser_id)
    # 2) request_codex_auth_url(...)
    # 3) page.goto(auth_url)
    # 4) poll get_auth_status(state)
    # 5) fallback post_oauth_callback if needed
    # 6) return (success, message)
```

关键点：
- 全 OAuth 页面行为在 BitBrowser 中完成。
- 只做必要自动化，不在本地直接交换 token。
- 标准化 timeout 与错误消息，便于任务日志显示。

**Step 4: 运行测试确认通过**

Run: `python -m unittest discover -s tests -p "test_cpa_oauth_bind.py" -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add cpa_oauth_bind.py tests/test_cpa_oauth_bind.py
git commit -m "feat: add BitBrowser-based CPA OAuth binding executor"
```

### Task 4: 接入后端任务编排

**Files:**
- Modify: `web/backend/routers/tasks.py`

**Step 1: 写失败用例（任务路由分发）**

```python
def test_task_type_cpa_bind_codex_dispatched():
    # 模拟 task_type == cpa_bind_codex 分支进入 execute_cpa_bind
    assert True
```

**Step 2: 运行测试确认失败**

Run: `python -m unittest discover -s tests -p "test_tasks_cpa_dispatch.py" -v`  
Expected: FAIL

**Step 3: 写最小实现**

```python
def execute_cpa_bind(email: str, log_callback=None, close_after: bool = True) -> dict:
    # ensure_browser_window -> get_cpa_config -> bind_cpa_codex_sync
```

同时修改：
- `task_priority`
- `task_label` 映射
- `if/elif` 任务分发

**Step 4: 运行测试确认通过**

Run: `python -m unittest discover -s tests -p "test_tasks_cpa_dispatch.py" -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add web/backend/routers/tasks.py tests/test_tasks_cpa_dispatch.py
git commit -m "feat: wire CPA binding into task executor"
```

### Task 5: 前端任务与配置接入

**Files:**
- Modify: `web/frontend/src/views/TasksView.vue`
- Modify: `web/frontend/src/views/ConfigView.vue`

**Step 1: 写失败检查（静态检查）**

```bash
npm run build
```

Expected: FAIL（字段/任务类型不一致）

**Step 2: 最小实现**

```javascript
// TasksView taskTypes
{ value: 'cpa_bind_codex', label: 'CPA OAuth绑定' }
```

新增配置输入：
- CPA Base URL
- CPA Management Token（密码态）
- Provider（默认 codex，可只读）
- Poll Timeout / Poll Interval

**Step 3: 运行构建验证**

Run: `cd web/frontend && npm run build`  
Expected: PASS

**Step 4: 手工验证**

Run:
- 启动后端：`uvicorn web.backend.main:app --reload --port 8000`
- 启动前端：`cd web/frontend && npm run dev`
- 页面确认可选择 `CPA OAuth绑定` 且配置项可保存。

**Step 5: Commit**

```bash
git add web/frontend/src/views/TasksView.vue web/frontend/src/views/ConfigView.vue
git commit -m "feat: add CPA binding task and config fields to frontend"
```

### Task 6: 端到端验证与回归

**Files:**
- Modify: `docs/zh/task-system.md`
- Modify: `docs/zh/configuration.md`
- Modify: `docs/en/task-system.md`
- Modify: `docs/en/configuration.md`

**Step 1: 本地端到端验证（单账号）**

Run:
1. 在配置中填入 `cpa_base_url` 和 `cpa_management_token`。
2. 选择 1 个账号执行 `cpa_bind_codex`。
3. 验证日志出现 `auth-url -> wait -> ok`。
4. CPA 端验证 `GET /v0/management/auth-files` 出现新增凭据。

Expected: 单账号成功绑定。

**Step 2: 批量回归验证（多账号）**

Run:
1. 选择 5 个账号，并发 2。
2. 观察失败账号不影响其他账号。
3. 重跑失败账号应可恢复。

Expected: 批量执行稳定，失败可重试。

**Step 3: 文档更新**

补充新任务类型、配置说明、失败恢复说明。

**Step 4: 最终验证**

Run:
- `python -m unittest discover -s tests -p "test_*.py" -v`
- `cd web/frontend && npm run build`

Expected: 全部通过。

**Step 5: Commit**

```bash
git add docs/zh/task-system.md docs/zh/configuration.md docs/en/task-system.md docs/en/configuration.md
git commit -m "docs: add CPA OAuth binding task and configuration guide"
```

