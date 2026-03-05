from fastapi.testclient import TestClient

from web.backend.main import app


def test_config_get_contains_cpa_fields():
    client = TestClient(app)
    data = client.get("/api/config").json()
    assert "cpa_base_url" in data
    assert "cpa_management_token" in data
    assert "cpa_poll_timeout_seconds" in data
    assert "cpa_poll_interval_seconds" in data
    assert "cpa_oauth_capture_timeout_seconds" in data
    assert isinstance(data["cpa_base_url"], str)
    assert isinstance(data["cpa_management_token"], str)
    assert isinstance(data["cpa_poll_timeout_seconds"], int)
    assert isinstance(data["cpa_poll_interval_seconds"], int)
    assert isinstance(data["cpa_oauth_capture_timeout_seconds"], int)


def test_config_put_and_get_cpa_fields_roundtrip():
    client = TestClient(app)
    payload = {
        "cpa_base_url": "https://cpa.example.com",
        "cpa_management_token": "token-xyz",
        "cpa_poll_timeout_seconds": 310,
        "cpa_poll_interval_seconds": 3,
        "cpa_oauth_capture_timeout_seconds": 190,
    }
    put_resp = client.put("/api/config", json=payload)
    assert put_resp.status_code == 200
    data = client.get("/api/config").json()
    assert data["cpa_base_url"] == "https://cpa.example.com"
    assert data["cpa_management_token"] == "token-xyz"
    assert data["cpa_poll_timeout_seconds"] == 310
    assert data["cpa_poll_interval_seconds"] == 3
    assert data["cpa_oauth_capture_timeout_seconds"] == 190
