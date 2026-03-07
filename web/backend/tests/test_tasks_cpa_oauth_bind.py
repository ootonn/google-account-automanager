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
    monkeypatch.setattr(tasks.DBManager, "get_account_by_email", lambda email: {"password": "secret-pass", "recovery_email": "recovery@example.com", "secret_key": "ABC DEF"})

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
    captured = {}

    def fake_open(browser_id, auth_url, capture_timeout_seconds, log_callback, expected_state=None, account_context=None):
        captured["account_context"] = account_context
        return {
            "success": True,
            "callback_url": "https://callback.example.com/?code=abc&state=state-1",
            "state": "state-1",
            "message": "callback_captured",
        }

    monkeypatch.setattr(tasks, "open_and_run_antigravity_oauth", fake_open)

    result = tasks.execute_cpa_oauth_bind("a@example.com", log_callback=logs.append, close_after=False)
    assert result["success"] is True
    assert captured["account_context"]["email"] == "a@example.com"


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
    monkeypatch.setattr(tasks.DBManager, "get_account_by_email", lambda email: {})

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def get_antigravity_auth_url(self, email):
            return {"url": "https://auth.example.com", "state": "state-1"}

    monkeypatch.setattr(tasks, "CpaManagementClient", FakeClient)
    monkeypatch.setattr(
        tasks,
        "open_and_run_antigravity_oauth",
        lambda browser_id, auth_url, capture_timeout_seconds, log_callback, expected_state=None, account_context=None: {
            "success": False,
            "error": "callback_not_captured",
            "message": "timeout",
        },
    )

    result = tasks.execute_cpa_oauth_bind("a@example.com", log_callback=None, close_after=False)
    assert result["success"] is False
    assert "callback_not_captured" in result["message"]


def test_execute_cpa_oauth_bind_when_state_mismatch(monkeypatch):
    submit_called = {"value": False}

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
    monkeypatch.setattr(tasks.DBManager, "get_account_by_email", lambda email: {})

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def get_antigravity_auth_url(self, email):
            return {"url": "https://auth.example.com", "state": "state-expected"}

        def submit_oauth_callback(self, callback_url):
            submit_called["value"] = True
            return {"success": True}

        def get_auth_status(self, state):
            return {"status": "ok", "message": "bound"}

    monkeypatch.setattr(tasks, "CpaManagementClient", FakeClient)
    monkeypatch.setattr(
        tasks,
        "open_and_run_antigravity_oauth",
        lambda browser_id, auth_url, capture_timeout_seconds, log_callback, expected_state=None, account_context=None: {
            "success": True,
            "callback_url": "https://callback.example.com/?code=abc&state=state-unexpected",
            "state": "state-unexpected",
            "message": "callback_captured",
        },
    )

    result = tasks.execute_cpa_oauth_bind("a@example.com", log_callback=None, close_after=False)
    assert result["success"] is False
    assert "state_mismatch" in result["message"]
    assert submit_called["value"] is False


def test_ensure_browser_window_reuses_existing_android_window(monkeypatch):
    import browser_manager
    import create_window

    email = "a@example.com"
    saved = {}

    monkeypatch.setattr(
        tasks.DBManager,
        "get_account_by_email",
        lambda target_email: {
            "email": target_email,
            "browser_id": None,
            "password": "secret-pass",
            "recovery_email": "recovery@example.com",
            "secret_key": "ABC DEF",
        },
    )
    monkeypatch.setattr(tasks.DBManager, "clear_browser_id", lambda email: None)
    monkeypatch.setattr(browser_manager, "restore_browser", lambda email: None)
    monkeypatch.setattr(
        browser_manager,
        "save_browser_to_db",
        lambda target_email, browser_id: saved.update({"email": target_email, "browser_id": browser_id}) or True,
    )
    monkeypatch.setattr(
        create_window,
        "get_browser_list",
        lambda page=0, pageSize=1000: [
            {"id": "browser-1", "userName": email, "ostype": "Android", "seq": 1}
        ],
    )
    monkeypatch.setattr(
        create_window,
        "get_browser_info",
        lambda browser_id: {"id": browser_id, "userName": email, "ostype": "Android", "seq": 1},
    )
    monkeypatch.setattr(
        create_window,
        "create_browser_window",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not create browser")),
    )
    monkeypatch.setattr(create_window, "delete_browser_by_id", lambda browser_id: True)

    browser_id = tasks.ensure_browser_window(email)

    assert browser_id == "browser-1"
    assert saved == {"email": email, "browser_id": "browser-1"}
