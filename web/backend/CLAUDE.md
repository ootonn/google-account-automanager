[根目录](../../CLAUDE.md) > [web](..) > **backend**

# Web Backend 模块

FastAPI 后端服务，提供 REST API、任务调度和 WebSocket 实时通信。

## 模块职责

- 提供账号管理 API
- 提供浏览器窗口管理 API
- 提供任务创建、执行、取消与状态查询 API
- 通过 WebSocket 推送任务日志和进度
- 承载 CPA Antigravity OAuth 绑定链路

## 启动

```bash
BACKEND_PORT=8001 uv run python -m uvicorn web.backend.main:app --reload --port 8001
```

访问地址：

- API：`http://localhost:<backend-port>`
- Swagger：`http://localhost:<backend-port>/docs`
- ReDoc：`http://localhost:<backend-port>/redoc`

本地开发时不要假设后端一定运行在 `8000`。前端 Vite 开发服务器会通过 `VITE_BACKEND_TARGET` 把同源 `/api` 与 `/ws` 转发到当前选中的后端端口。

## 对外接口

| 路由前缀 | 文件 | 职责 |
| --- | --- | --- |
| `/api/accounts` | `routers/accounts.py` | 账号 CRUD、导入导出 |
| `/api/browsers` | `routers/browsers.py` | 浏览器窗口管理 |
| `/api/tasks` | `routers/tasks.py` | 任务创建、执行、取消、查询 |
| `/api/config` | `routers/config.py` | 系统配置读写 |
| `/ws` | `websocket.py` | WebSocket 实时推送 |

## 关键文件

- `web/backend/main.py`：应用入口
- `web/backend/schemas.py`：Pydantic 模型
- `web/backend/websocket.py`：WebSocket 连接管理
- `web/backend/routers/tasks.py`：任务主执行链路
- `web/backend/services/cpa_management.py`：CPA 管理 API 客户端
- `web/backend/services/cpa_oauth_antigravity.py`：Antigravity OAuth 浏览器自动化与 callback 捕获

## WebSocket

连接地址：`ws://localhost:<backend-port>/ws`

前端开发环境中，优先使用同源 `/ws`，由 Vite 代理转发到 `VITE_BACKEND_TARGET`，避免因 `8000` 端口被其他进程占用而连错后端。

典型消息类型：

```json
{
  "type": "task_progress",
  "data": {
    "task_id": "abc123",
    "status": "running"
  }
}
```

```json
{
  "type": "account_progress",
  "data": {
    "email": "user@example.com",
    "status": "completed"
  }
}
```

```json
{
  "type": "log",
  "data": {
    "level": "info",
    "message": "task log"
  }
}
```

## 开发约束

- CPA OAuth provider 固定为 `antigravity`
- 不要引入人工复制粘贴 callback URL 的流程
- 不要把 CPA token 或完整 callback query 写入日志

## 验证

```bash
python -m pytest web/backend/tests -q -W error::pydantic.warnings.PydanticDeprecatedSince20
```
