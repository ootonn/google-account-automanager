# Auto BitBrowser Web UI

基于 FastAPI + Vue 3 的 Web 管理界面。

## 功能

- 账号管理：列表、筛选、导入、导出
- 浏览器窗口管理：创建、同步、恢复、打开
- 任务执行：批量执行自动化任务并实时查看日志
- 实时通信：通过 WebSocket 推送任务进度

## 技术栈

- 后端：FastAPI + SQLite
- 前端：Vue 3 + Vite + Pinia + TailwindCSS
- 自动化：BitBrowser + Playwright CDP

## 快速启动

### 1. 安装依赖

```bash
pip install fastapi uvicorn websockets
npm --prefix web/frontend install
```

### 2. PowerShell 推荐流程：自动选择空闲端口

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File web/select-dev-ports.ps1
```

该脚本会：

- 自动选择空闲后端端口（默认从 `8000` 起）
- 自动选择空闲前端端口（默认从 `5173` 起）
- 写入 `web/frontend/.env.local`
- 输出当前机器可直接执行的启动命令

### 3. Bash 启动脚本

```bash
# 终端 1
BACKEND_PORT=8001 ./web/start_backend.sh

# 终端 2
VITE_BACKEND_TARGET=http://127.0.0.1:8001 FRONTEND_PORT=5173 ./web/start_frontend.sh
```

### 4. 手动启动

```bash
# 终端 1
python -m uvicorn web.backend.main:app --reload --host 0.0.0.0 --port 8001

# 终端 2
cd web/frontend
VITE_BACKEND_TARGET=http://127.0.0.1:8001 npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

### 5. 访问地址

- 前端：`http://127.0.0.1:<frontend-port>`
- 后端 API：`http://127.0.0.1:<backend-port>/api`
- API 文档：`http://127.0.0.1:<backend-port>/docs`

## 前端开发端口说明

前端不再硬编码请求 `http://localhost:8000`。

- Axios 默认使用 `VITE_API_BASE_URL`，默认值为 `/api`
- WebSocket 默认连接同源 `/ws`
- Vite 开发环境通过代理把 `/api` 和 `/ws` 转发到 `VITE_BACKEND_TARGET`

这意味着只要前端和 Vite 代理配置正确，即使本机 `8000` 被其他 `uvicorn` 占用，也不会误连到错误后端。

## 环境变量

可参考 `web/frontend/.env.example`：

- `VITE_BACKEND_TARGET=http://127.0.0.1:8000`
- `VITE_API_BASE_URL=/api`
- `VITE_WS_URL`：仅在不使用同源 `/ws` 代理时才需要覆盖

## 目录结构

```text
web/
├── backend/
│   ├── main.py
│   ├── schemas.py
│   ├── websocket.py
│   ├── routers/
│   └── services/
├── frontend/
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── start_backend.sh
├── start_frontend.sh
├── select-dev-ports.ps1
└── README.md
```

## API 概览

- `/api/accounts`：账号管理
- `/api/browsers`：浏览器窗口管理
- `/api/tasks`：任务创建、查询、取消
- `/api/config`：系统配置读写
- `/ws`：任务日志与进度推送

## 注意事项

- 本地开发时后端端口不是固定值，优先使用 `web/select-dev-ports.ps1`
- 前端开发时优先走同源 `/api`、`/ws`，避免跨端口误连
- 真实环境验证时不要把 CPA token 或完整 callback query 写入日志
