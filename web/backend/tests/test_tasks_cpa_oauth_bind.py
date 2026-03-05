from fastapi.testclient import TestClient

from web.backend.main import app
from web.backend.routers import tasks


def test_create_task_accepts_cpa_oauth_bind():
    client = TestClient(app)
    body = {
        "task_types": ["cpa_oauth_bind"],
        "emails": ["a@example.com"],
        "close_after": False,
        "concurrency": 1,
    }
    response = client.post("/api/tasks", json=body)
    assert response.status_code == 200


def test_execute_cpa_oauth_bind_success(monkeypatch):
    logs = []

    monkeypatch.setattr(
        tasks,
        "_get_cpa_runtime_config",
        lambda: {
            "base_url": "https://cpa.example.com",
            "management_token": "token",
            "poll_timeout_seconds": 5,
            "poll_interval_seconds": 1,
            "oauth_capture_timeout_seconds": 3,
        },
    )
    monkeypatch.setattr(tasks, "ensure_browser_window", lambda email, log_callback=None: "browser-1")

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def get_antigravity_auth_url(self, email):
            return {"url": "https://auth.example.com", "state": "state-1"}

        def submit_oauth_callback(self, callback_url):
            return {"success": True}

        def get_auth_status(self, state):
            return {"status": "ok", "message": "bound"}

    monkeypatch.setattr(tasks, "CpaManagementClient", FakeClient)
    monkeypatch.setattr(
        tasks,
        "open_and_run_antigravity_oauth",
        lambda browser_id, auth_url, capture_timeout_seconds, log_callback: {
            "success": True,
            "callback_url": "https://callback.example.com/?code=abc&state=state-1",
            "state": "state-1",
            "message": "callback_captured",
        },
    )

    result = tasks.execute_cpa_oauth_bind("a@example.com", log_callback=logs.append, close_after=False)
    assert result["success"] is True


def test_execute_cpa_oauth_bind_when_callback_not_captured(monkeypatch):
    monkeypatch.setattr(
        tasks,
        "_get_cpa_runtime_config",
        lambda: {
            "base_url": "https://cpa.example.com",
            "management_token": "token",
            "poll_timeout_seconds": 5,
            "poll_interval_seconds": 1,
            "oauth_capture_timeout_seconds": 3,
        },
    )
    monkeypatch.setattr(tasks, "ensure_browser_window", lambda email, log_callback=None: "browser-1")

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def get_antigravity_auth_url(self, email):
            return {"url": "https://auth.example.com", "state": "state-1"}

    monkeypatch.setattr(tasks, "CpaManagementClient", FakeClient)
    monkeypatch.setattr(
        tasks,
        "open_and_run_antigravity_oauth",
        lambda browser_id, auth_url, capture_timeout_seconds, log_callback: {
            "success": False,
            "error": "callback_not_captured",
            "message": "timeout",
        },
    )

    result = tasks.execute_cpa_oauth_bind("a@example.com", log_callback=None, close_after=False)
    assert result["success"] is False
    assert "callback_not_captured" in result["message"]
