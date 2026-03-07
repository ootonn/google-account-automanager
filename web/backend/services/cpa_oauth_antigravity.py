"""Antigravity OAuth automation with callback auto-capture."""

from __future__ import annotations

import asyncio
import threading
import time
from typing import Any, Callable, Dict, Optional, Set
from urllib.parse import parse_qs, urlparse

import pyotp
from playwright.async_api import BrowserContext, Page, async_playwright

from bit_api import openBrowser
from google_recovery import detect_manual_verification, handle_recovery_email_challenge

TOTP_INPUT_SELECTOR = 'input[name="totpPin"], input[id="totpPin"], input[type="tel"]'
WRONG_PASSWORD_MARKERS = (
    'wrong password',
    'incorrect password',
    '????',
)
TRY_ANOTHER_WAY_KEYWORDS = [
    'Try another way',
    'More ways to verify',
]
AUTHENTICATOR_KEYWORDS = [
    'Google Authenticator',
    'Authenticator app',
    'Authenticator',
]
USE_ANOTHER_ACCOUNT_KEYWORDS = [
    'Use another account',
    '??????',
    '??????',
]
CONSENT_KEYWORDS = [
    'Allow',
    'Continue',
    'Yes',
    '??',
    '??',
]


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
    if parsed.scheme not in ('http', 'https'):
        return False
    query = parse_qs(parsed.query)
    state = (query.get('state') or [''])[0]
    code = (query.get('code') or [''])[0]
    oauth_error = (query.get('error') or [''])[0]
    return bool(state and (code or oauth_error))


def _extract_state(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    return (query.get('state') or [''])[0]


def _run_async_safely(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: Dict[str, Any] = {}
    error: Dict[str, BaseException] = {}

    def _runner() -> None:
        try:
            result['value'] = asyncio.run(coro)
        except BaseException as exc:  # pragma: no cover - defensive
            error['value'] = exc

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()

    if 'value' in error:
        raise error['value']
    return result.get('value')


def _page_url(page: Page) -> str:
    return str(getattr(page, 'url', '') or '')


async def _body_text(page: Page) -> str:
    try:
        return await page.inner_text('body')
    except Exception:
        return ''


def _keyword_selectors(keyword: str) -> list[str]:
    return [
        f'text="{keyword}"',
        f'text={keyword}',
        f':text("{keyword}")',
        f'button:has-text("{keyword}")',
        f'[role="button"]:has-text("{keyword}")',
        f'a:has-text("{keyword}")',
        f'li:has-text("{keyword}")',
        f'div:has-text("{keyword}")',
        f'span:has-text("{keyword}")',
    ]


async def _count_visible(locator) -> bool:
    try:
        return await locator.count() > 0 and await locator.is_visible()
    except Exception:
        return False


async def _click_by_keywords(
    page: Page,
    keywords: list[str],
    log_callback: Optional[Callable[[str], None]] = None,
    log_message: Optional[str] = None,
    body_fallback: bool = False,
) -> bool:
    body_text = (await _body_text(page)).lower()
    for keyword in keywords:
        for selector in _keyword_selectors(keyword):
            try:
                locator = page.locator(selector).first
                if await _count_visible(locator):
                    await locator.click(force=True)
                    if log_message:
                        _safe_log(log_callback, log_message)
                    await asyncio.sleep(2)
                    return True
            except Exception:
                continue

        if body_fallback and keyword.lower() in body_text:
            try:
                await page.locator(f'text="{keyword}"').first.click(force=True)
                if log_message:
                    _safe_log(log_callback, log_message)
                await asyncio.sleep(2)
                return True
            except Exception:
                continue

    return False


async def _wait_for_visible_selector(page: Page, selector: str, timeout: int = 5000):
    try:
        return await page.wait_for_selector(selector, timeout=timeout, state='visible')
    except Exception:
        return None


async def ensure_authenticator_method(page: Page, log_callback: Optional[Callable[[str], None]] = None) -> bool:
    await asyncio.sleep(1)
    page_text = (await _body_text(page)).lower()
    if 'authenticator' in page_text:
        return True

    switched = await _click_by_keywords(
        page,
        TRY_ANOTHER_WAY_KEYWORDS,
        log_callback=log_callback,
        log_message='Switching to Authenticator verification...',
        body_fallback=True,
    )
    if not switched:
        return False

    selected = await _click_by_keywords(
        page,
        AUTHENTICATOR_KEYWORDS,
        log_callback=log_callback,
        log_message='Selected Authenticator challenge',
        body_fallback=True,
    )
    if selected:
        await asyncio.sleep(2)
    return selected


async def _handle_account_chooser(page: Page, email: str, log_callback: Optional[Callable[[str], None]] = None) -> bool:
    body_text = (await _body_text(page)).lower()
    page_url = _page_url(page).lower()
    if 'choose an account' not in body_text and 'accountchooser' not in page_url:
        return False

    _safe_log(log_callback, 'Checking Google account chooser...')
    email_keywords = []
    if email:
        email_keywords.append(email)
        lowered_email = email.lower()
        if lowered_email != email:
            email_keywords.append(lowered_email)
    if email_keywords and await _click_by_keywords(
        page,
        email_keywords,
        log_callback=log_callback,
        log_message='Selected existing Google account',
        body_fallback=True,
    ):
        return True

    return await _click_by_keywords(
        page,
        USE_ANOTHER_ACCOUNT_KEYWORDS,
        log_callback=log_callback,
        log_message='Switching to manual Google account entry',
        body_fallback=True,
    )


async def _fill_email_if_needed(page: Page, email: str, log_callback: Optional[Callable[[str], None]] = None) -> bool:
    if not email:
        return False

    email_input = await _wait_for_visible_selector(page, 'input[type="email"]', timeout=3000)
    if not email_input:
        return False

    await email_input.fill(email)
    _safe_log(log_callback, 'Entering Google password...')
    try:
        await page.click('#identifierNext >> button')
    except Exception:
        pass
    await asyncio.sleep(1)
    return True


async def _fill_password_if_needed(page: Page, password: str, log_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
    if not password:
        return {'success': True, 'acted': False}

    password_input = await _wait_for_visible_selector(page, 'input[type="password"]', timeout=3000)
    if not password_input:
        return {'success': True, 'acted': False}

    await password_input.fill(password)
    _safe_log(log_callback, 'Entering Google password...')
    try:
        await page.click('#passwordNext >> button')
    except Exception:
        pass
    await asyncio.sleep(2)

    body_text = (await _body_text(page)).lower()
    if any(marker in body_text for marker in WRONG_PASSWORD_MARKERS):
        return {
            'success': False,
            'error': 'wrong_password',
            'message': 'google login reported wrong password',
            'acted': True,
        }

    return {'success': True, 'acted': True}


async def _submit_totp_if_needed(
    page: Page,
    secret_key: str,
    recovery_email: str,
    log_callback: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    if not secret_key and not recovery_email:
        return {'success': True, 'acted': False}

    if secret_key:
        await ensure_authenticator_method(page, log_callback)

    totp_input = await _wait_for_visible_selector(page, TOTP_INPUT_SELECTOR, timeout=5000)
    if not totp_input:
        if not secret_key:
            try:
                handled = await handle_recovery_email_challenge(page, recovery_email, log_callback)
            except Exception:
                handled = False
            return {'success': True, 'acted': bool(handled)}
        return {'success': True, 'acted': False}

    if secret_key:
        normalized_secret = secret_key.replace(' ', '').strip()
        try:
            code = pyotp.TOTP(normalized_secret).now()
        except Exception as exc:
            return {
                'success': False,
                'error': 'totp_generation_failed',
                'message': str(exc),
                'acted': True,
            }

        await totp_input.fill(code)
        _safe_log(log_callback, 'Submitting Google Authenticator code...')
        try:
            await page.click('#totpNext >> button')
        except Exception:
            pass
        await asyncio.sleep(2)
        return {'success': True, 'acted': True}

    try:
        handled = await handle_recovery_email_challenge(page, recovery_email, log_callback)
    except Exception:
        handled = False
    if handled:
        return {'success': True, 'acted': True}

    return {
        'success': False,
        'error': 'totp_secret_missing',
        'message': 'totp secret missing for authenticator challenge',
        'acted': True,
    }


async def _handle_consent_if_needed(page: Page, log_callback: Optional[Callable[[str], None]] = None) -> bool:
    body_text = (await _body_text(page)).lower()
    if 'make sure that you downloaded this app from google' in body_text:
        return await _click_by_keywords(
            page,
            ['Sign in'],
            log_callback=log_callback,
            log_message='Confirming Google native app sign-in',
            body_fallback=True,
        )

    if not any(marker in body_text for marker in ('allow', 'continue', 'google antigravity')):
        return False

    return await _click_by_keywords(
        page,
        CONSENT_KEYWORDS,
        log_callback=log_callback,
        log_message='Confirming Google OAuth consent',
        body_fallback=True,
    )


async def _complete_google_oauth_login(
    page: Page,
    account_context: Optional[Dict[str, Any]],
    log_callback: Optional[Callable[[str], None]] = None,
    max_wait_seconds: int = 60,
    capture_ready: Optional[Callable[[], bool]] = None,
    page_supplier: Optional[Callable[[], Page]] = None,
) -> Dict[str, Any]:
    account_context = account_context or {}
    email = str(account_context.get('email') or '').strip()
    password = str(account_context.get('password') or '').strip()
    recovery_email = str(
        account_context.get('recovery_email')
        or account_context.get('backup_email')
        or ''
    ).strip()
    secret_key = str(
        account_context.get('secret_key')
        or account_context.get('2fa_secret')
        or account_context.get('secret')
        or ''
    ).strip()

    if capture_ready and capture_ready():
        return {'success': True, 'message': 'callback_ready'}
    if is_oauth_callback_url(_page_url(page)):
        return {'success': True, 'message': 'callback_ready'}
    if not any([email, password, recovery_email, secret_key]):
        return {'success': True, 'message': 'no_account_context'}

    deadline = time.monotonic() + max(5, max_wait_seconds)
    idle_rounds = 0
    active_page = page
    while time.monotonic() < deadline:
        if page_supplier:
            try:
                supplied_page = page_supplier()
                if supplied_page is not None:
                    active_page = supplied_page
            except Exception:
                pass

        if capture_ready and capture_ready():
            return {'success': True, 'message': 'callback_ready'}
        if is_oauth_callback_url(_page_url(active_page)):
            return {'success': True, 'message': 'callback_ready'}
        if await detect_manual_verification(active_page):
            return {
                'success': False,
                'error': 'manual_verification_required',
                'message': 'manual verification required',
            }

        progressed = False

        if await _handle_account_chooser(active_page, email, log_callback):
            progressed = True

        if await _fill_email_if_needed(active_page, email, log_callback):
            progressed = True

        password_result = await _fill_password_if_needed(active_page, password, log_callback)
        if not password_result.get('success'):
            return password_result
        progressed = progressed or bool(password_result.get('acted'))

        totp_result = await _submit_totp_if_needed(active_page, secret_key, recovery_email, log_callback)
        if not totp_result.get('success'):
            return totp_result
        progressed = progressed or bool(totp_result.get('acted'))

        if recovery_email:
            try:
                recovery_handled = await handle_recovery_email_challenge(active_page, recovery_email, log_callback)
            except Exception:
                recovery_handled = False
            progressed = progressed or bool(recovery_handled)

        if await _handle_consent_if_needed(active_page, log_callback):
            progressed = True

        if capture_ready and capture_ready():
            return {'success': True, 'message': 'callback_ready'}
        if is_oauth_callback_url(_page_url(active_page)):
            return {'success': True, 'message': 'callback_ready'}

        if progressed:
            idle_rounds = 0
        else:
            idle_rounds += 1
            if idle_rounds >= 6:
                break

        await asyncio.sleep(2)

    return {'success': True, 'message': 'login_flow_attempted'}


def open_and_run_antigravity_oauth(
    browser_id: str,
    auth_url: str,
    capture_timeout_seconds: int = 180,
    log_callback: Optional[Callable[[str], None]] = None,
    expected_state: Optional[str] = None,
    account_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Open BitBrowser window and capture callback URL automatically.
    Provider is implicitly fixed to Antigravity by API/task orchestration.
    """
    try:
        open_result = openBrowser(browser_id)
    except Exception as exc:
        return {
            'success': False,
            'error': 'browser_open_failed',
            'message': str(exc),
        }

    if not open_result or not open_result.get('success'):
        return {
            'success': False,
            'error': 'browser_open_failed',
            'message': 'failed to open browser window',
        }

    ws_endpoint = (open_result.get('data') or {}).get('ws')
    if not ws_endpoint:
        return {
            'success': False,
            'error': 'ws_endpoint_missing',
            'message': 'no websocket endpoint from browser api',
        }

    try:
        result = _run_async_safely(
            _capture_callback_from_browser(
                ws_endpoint=ws_endpoint,
                auth_url=auth_url,
                capture_timeout_seconds=capture_timeout_seconds,
                log_callback=log_callback,
                expected_state=expected_state,
                account_context=account_context,
            )
        )
        return result
    except Exception as exc:
        return {
            'success': False,
            'error': 'automation_error',
            'message': str(exc),
        }


def _pick_active_page(context: BrowserContext, fallback_page: Page) -> Page:
    preferred_fragments = (
        'accounts.google.com',
        '/signin/oauth/',
        'localhost:51121/oauth-callback',
    )
    ignored_prefixes = (
        'devtools://',
        'https://console.bitbrowser.net',
        'chrome-error://',
    )

    try:
        candidates = []
        for page in context.pages:
            try:
                if page.is_closed():
                    continue
            except Exception:
                pass
            candidates.append(page)

        for page in reversed(candidates):
            page_url = _page_url(page)
            if page_url.startswith(ignored_prefixes):
                continue
            if any(fragment in page_url for fragment in preferred_fragments):
                return page

        for page in reversed(candidates):
            page_url = _page_url(page)
            if not page_url.startswith(ignored_prefixes):
                return page
    except Exception:
        pass

    return fallback_page


async def _capture_callback_from_browser(
    ws_endpoint: str,
    auth_url: str,
    capture_timeout_seconds: int,
    log_callback: Optional[Callable[[str], None]] = None,
    expected_state: Optional[str] = None,
    account_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    captured: Dict[str, Optional[str]] = {'callback_url': None}
    mismatch_seen = {'value': False}
    done_event = asyncio.Event()
    attached_pages: Set[int] = set()
    capture_deadline = time.monotonic() + max(1, capture_timeout_seconds)

    def _capture_if_callback(url: str) -> None:
        if captured['callback_url'] is not None:
            return
        if not is_oauth_callback_url(url):
            return
        callback_state = _extract_state(url)
        if expected_state and callback_state != expected_state:
            mismatch_seen['value'] = True
            _safe_log(log_callback, 'Detected mismatched callback state; continuing to wait for the expected callback.')
            return
        captured['callback_url'] = url
        _safe_log(log_callback, f'Captured OAuth callback: {_sanitize_callback_url(url)}')
        done_event.set()

    def _attach_page(page: Page) -> None:
        page_id = id(page)
        if page_id in attached_pages:
            return
        attached_pages.add(page_id)
        page.on('framenavigated', lambda frame: _capture_if_callback(frame.url))
        page.on('domcontentloaded', lambda: _capture_if_callback(_page_url(page)))
        page.on('request', lambda request: _capture_if_callback(request.url))
        page.on('requestfailed', lambda request: _capture_if_callback(request.url))
        _capture_if_callback(_page_url(page))

    async with async_playwright() as playwright:
        browser = await playwright.chromium.connect_over_cdp(ws_endpoint)
        context: BrowserContext
        if browser.contexts:
            context = browser.contexts[0]
        else:
            context = await browser.new_context()

        for existing_page in context.pages:
            _attach_page(existing_page)
        context.on('page', _attach_page)
        context.on('request', lambda request: _capture_if_callback(request.url))
        context.on('requestfailed', lambda request: _capture_if_callback(request.url))

        page = await context.new_page()
        _attach_page(page)

        _safe_log(log_callback, 'Opening Antigravity OAuth authorization page...')
        try:
            await page.goto(auth_url, wait_until='domcontentloaded', timeout=60000)
        except Exception:
            _safe_log(log_callback, 'Authorization page load timed out; continuing to wait for OAuth callback...')

        _capture_if_callback(_page_url(page))

        interactive_page = _pick_active_page(context, page)
        remaining_for_login = max(1, int(capture_deadline - time.monotonic()))
        if account_context and remaining_for_login > 0:
            login_result = await _complete_google_oauth_login(
                interactive_page,
                account_context,
                log_callback=log_callback,
                max_wait_seconds=min(90, remaining_for_login),
                capture_ready=done_event.is_set,
                page_supplier=lambda: _pick_active_page(context, page),
            )
            if not login_result.get('success'):
                return login_result

        if captured['callback_url'] is not None:
            callback_url = captured['callback_url'] or ''
            return {
                'success': True,
                'callback_url': callback_url,
                'state': _extract_state(callback_url),
                'message': 'callback_captured',
            }

        remaining_seconds = max(0.1, capture_deadline - time.monotonic())
        try:
            await asyncio.wait_for(done_event.wait(), timeout=remaining_seconds)
        except asyncio.TimeoutError:
            if mismatch_seen['value']:
                return {
                    'success': False,
                    'error': 'state_mismatch',
                    'message': 'callback state mismatch with expected state',
                }
            return {
                'success': False,
                'error': 'callback_not_captured',
                'message': f'callback not captured within {capture_timeout_seconds}s',
            }

        callback_url = captured['callback_url'] or ''
        return {
            'success': True,
            'callback_url': callback_url,
            'state': _extract_state(callback_url),
            'message': 'callback_captured',
        }
