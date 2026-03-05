import requests
import pytest

from web.backend.services.cpa_management import (
    CpaBusinessError,
    CpaHttpError,
    CpaManagementClient,
    CpaNetworkError,
)


def test_build_auth_url_request_contains_antigravity_provider():
    client = CpaManagementClient("https://cpa.example.com", "token")
    req = client._build_auth_url_request("a@example.com")
    assert req["method"] == "GET"
    assert req["path"] == "/api/management/oauth/antigravity/auth-url"
    assert req["params"]["provider"] == "antigravity"
    assert req["params"]["email"] == "a@example.com"


def test_submit_callback_request_contains_antigravity_provider():
    client = CpaManagementClient("https://cpa.example.com", "token")
    req = client._build_submit_callback_request("https://callback.example.com/?code=1&state=2")
    assert req["method"] == "POST"
    assert req["path"] == "/api/management/oauth/antigravity/callback"
    assert req["json"]["provider"] == "antigravity"


def test_get_antigravity_auth_url_maps_network_error(monkeypatch):
    client = CpaManagementClient("https://cpa.example.com", "token")

    def raise_conn_error(*args, **kwargs):
        raise requests.ConnectionError("boom")

    monkeypatch.setattr(client.session, "request", raise_conn_error)
    with pytest.raises(CpaNetworkError):
        client.get_antigravity_auth_url("a@example.com")


def test_get_auth_status_maps_http_error(monkeypatch):
    client = CpaManagementClient("https://cpa.example.com", "token")

    class FakeResponse:
        status_code = 500
        text = "server error"

        def json(self):
            return {"message": "server error"}

    monkeypatch.setattr(client.session, "request", lambda *a, **k: FakeResponse())
    with pytest.raises(CpaHttpError):
        client.get_auth_status("state-1")


def test_submit_callback_maps_business_error(monkeypatch):
    client = CpaManagementClient("https://cpa.example.com", "token")

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"success": False, "error": "invalid state"}

    monkeypatch.setattr(client.session, "request", lambda *a, **k: FakeResponse())
    with pytest.raises(CpaBusinessError):
        client.submit_oauth_callback("https://callback.example.com/?code=1&state=2")
