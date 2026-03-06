"""Antigravity OAuth automation with callback auto-capture."""

from __future__ import annotations

import asyncio
import threading
from typing import Any, Callable, Dict, Optional, Set
from urllib.parse import parse_qs, urlparse

from playwright.async_api import BrowserContext, Page, async_playwright

from bit_api import openBrowser


def _safe_log(log_callback: Optional[Callable[[str], None]], message: str) -> None:
    if log_callback:
        log_callback(message)


def _sanitize_callback_url(url: str) -> str:
    """Avoid logging query secrets; keep only scheme/netloc/path."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def is_oauth_callback_url(url: str) -> bool:
    """Return True when URL looks like an OAuth callback URL."""
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    query = parse_qs(parsed.query)
    state = (query.get("state") or [""])[0]
    code = (query.get("code") or [""])[0]
    oauth_error = (query.get("error") or [""])[0]
    return bool(state and (code or oauth_error))


def _extract_state(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    return (query.get("state") or [""])[0]


def _run_async_safely(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: Dict[str, Any] = {}
    error: Dict[str, BaseException] = {}

    def _runner() -> None:
        try:
            result["value"] = asyncio.run(coro)
        except BaseException as exc:  # pragma: no cover - defensive
            error["value"] = exc

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()

    if "value" in error:
        raise error["value"]
    return result.get("value")


def open_and_run_antigravity_oauth(
    browser_id: str,
    auth_url: str,
    capture_timeout_seconds: int = 180,
    log_callback: Optional[Callable[[str], None]] = None,
    expected_state: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Open BitBrowser window and capture callback URL automatically.
    Provider is implicitly fixed to Antigravity by API/task orchestration.
    """
    try:
        open_result = openBrowser(browser_id)
    except Exception as exc:
        return {
            "success": False,
            "error": "browser_open_failed",
            "message": str(exc),
        }

    if not open_result or not open_result.get("success"):
        return {
            "success": False,
            "error": "browser_open_failed",
            "message": "failed to open browser window",
        }

    ws_endpoint = (open_result.get("data") or {}).get("ws")
    if not ws_endpoint:
        return {
            "success": False,
            "error": "ws_endpoint_missing",
            "message": "no websocket endpoint from browser api",
        }

    try:
        result = _run_async_safely(
            _capture_callback_from_browser(
                ws_endpoint=ws_endpoint,
                auth_url=auth_url,
                capture_timeout_seconds=capture_timeout_seconds,
                log_callback=log_callback,
                expected_state=expected_state,
            )
        )
        return result
    except Exception as exc:
        return {
            "success": False,
            "error": "automation_error",
            "message": str(exc),
        }


async def _capture_callback_from_browser(
    ws_endpoint: str,
    auth_url: str,
    capture_timeout_seconds: int,
    log_callback: Optional[Callable[[str], None]] = None,
    expected_state: Optional[str] = None,
) -> Dict[str, Any]:
    captured: Dict[str, Optional[str]] = {"callback_url": None}
    mismatch_seen = {"value": False}
    done_event = asyncio.Event()
    attached_pages: Set[int] = set()

    def _capture_if_callback(url: str) -> None:
        if captured["callback_url"] is not None:
            return
        if not is_oauth_callback_url(url):
            return
        callback_state = _extract_state(url)
        if expected_state and callback_state != expected_state:
            mismatch_seen["value"] = True
            _safe_log(
                log_callback,
                "检测到 state 不匹配回调，已忽略并继续等待目标回调。",
            )
            return
        captured["callback_url"] = url
        _safe_log(log_callback, f"已捕获 OAuth 回调: {_sanitize_callback_url(url)}")
        done_event.set()

    def _attach_page(page: Page) -> None:
        page_id = id(page)
        if page_id in attached_pages:
            return
        attached_pages.add(page_id)
        page.on("framenavigated", lambda frame: _capture_if_callback(frame.url))
        page.on("domcontentloaded", lambda: _capture_if_callback(page.url))
        _capture_if_callback(page.url)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.connect_over_cdp(ws_endpoint)
        context: BrowserContext
        if browser.contexts:
            context = browser.contexts[0]
        else:
            context = await browser.new_context()

        context.on("page", _attach_page)
        # Always use a fresh page to avoid stale callback URLs from pre-existing tabs.
        page = await context.new_page()
        _attach_page(page)

        _safe_log(log_callback, "正在打开 Antigravity OAuth 授权页...")
        try:
            await page.goto(auth_url, wait_until="domcontentloaded", timeout=60000)
        except Exception:
            # Keep waiting for callback; auth page may still continue loading.
            _safe_log(log_callback, "授权页打开超时，继续等待 OAuth 回调...")

        _capture_if_callback(page.url)

        try:
            await asyncio.wait_for(done_event.wait(), timeout=capture_timeout_seconds)
        except asyncio.TimeoutError:
            if mismatch_seen["value"]:
                return {
                    "success": False,
                    "error": "state_mismatch",
                    "message": "callback state mismatch with expected state",
                }
            return {
                "success": False,
                "error": "callback_not_captured",
                "message": f"callback not captured within {capture_timeout_seconds}s",
            }

        callback_url = captured["callback_url"] or ""
        return {
            "success": True,
            "callback_url": callback_url,
            "state": _extract_state(callback_url),
            "message": "callback_captured",
        }
