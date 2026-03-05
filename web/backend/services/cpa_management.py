"""CPA management API client for Antigravity OAuth."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
import time

import requests


class CpaManagementError(Exception):
    """Base exception for CPA management client."""


class CpaNetworkError(CpaManagementError):
    """Network-level errors."""


class CpaHttpError(CpaManagementError):
    """Unexpected HTTP status errors."""


class CpaBusinessError(CpaManagementError):
    """Business-level response errors."""


@dataclass
class _RequestConfig:
    method: str
    path: str
    params: Optional[Dict[str, Any]] = None
    json: Optional[Dict[str, Any]] = None


class CpaManagementClient:
    """Client for CPA management endpoints (provider fixed to antigravity)."""

    PROVIDER = "antigravity"

    def __init__(
        self,
        base_url: str,
        management_token: str,
        timeout_seconds: int = 15,
        max_retries: int = 2,
        retry_interval_seconds: float = 0.5,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.base_url = (base_url or "").rstrip("/")
        self.management_token = management_token or ""
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_interval_seconds = retry_interval_seconds
        self.session = session or requests.Session()

    def _headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.management_token:
            headers["Authorization"] = f"Bearer {self.management_token}"
        return headers

    def _build_auth_url_request(self, email: str) -> Dict[str, Any]:
        req = _RequestConfig(
            method="GET",
            path="/api/management/oauth/antigravity/auth-url",
            params={
                "provider": self.PROVIDER,
                "email": email,
            },
        )
        return {
            "method": req.method,
            "path": req.path,
            "params": req.params,
            "json": req.json,
        }

    def _build_submit_callback_request(self, callback_url: str) -> Dict[str, Any]:
        req = _RequestConfig(
            method="POST",
            path="/api/management/oauth/antigravity/callback",
            json={
                "provider": self.PROVIDER,
                "callback_url": callback_url,
            },
        )
        return {
            "method": req.method,
            "path": req.path,
            "params": req.params,
            "json": req.json,
        }

    def _build_status_request(self, state: str) -> Dict[str, Any]:
        req = _RequestConfig(
            method="GET",
            path="/api/management/oauth/antigravity/status",
            params={
                "provider": self.PROVIDER,
                "state": state,
            },
        )
        return {
            "method": req.method,
            "path": req.path,
            "params": req.params,
            "json": req.json,
        }

    def _call(self, request_cfg: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{request_cfg['path']}"
        attempts = self.max_retries + 1
        last_network_error: Optional[Exception] = None

        for idx in range(attempts):
            try:
                response = self.session.request(
                    method=request_cfg["method"],
                    url=url,
                    headers=self._headers(),
                    params=request_cfg.get("params"),
                    json=request_cfg.get("json"),
                    timeout=self.timeout_seconds,
                )
            except requests.RequestException as exc:
                last_network_error = exc
                if idx < attempts - 1:
                    time.sleep(self.retry_interval_seconds)
                    continue
                raise CpaNetworkError(str(exc)) from exc

            if response.status_code >= 400:
                raise CpaHttpError(f"HTTP {response.status_code}: {getattr(response, 'text', '')}")

            try:
                payload = response.json()
            except ValueError as exc:
                raise CpaBusinessError("invalid_json_response") from exc

            if isinstance(payload, dict):
                if payload.get("success") is False:
                    error_message = payload.get("error") or payload.get("message") or "business_error"
                    raise CpaBusinessError(str(error_message))
                if payload.get("status") == "error":
                    error_message = payload.get("error") or payload.get("message") or "status_error"
                    raise CpaBusinessError(str(error_message))
                return payload

            raise CpaBusinessError("invalid_response_format")

        if last_network_error is not None:
            raise CpaNetworkError(str(last_network_error)) from last_network_error
        raise CpaNetworkError("unknown_network_error")

    def get_antigravity_auth_url(self, email: str) -> Dict[str, Any]:
        return self._call(self._build_auth_url_request(email))

    def submit_oauth_callback(self, callback_url: str) -> Dict[str, Any]:
        return self._call(self._build_submit_callback_request(callback_url))

    def get_auth_status(self, state: str) -> Dict[str, Any]:
        return self._call(self._build_status_request(state))
