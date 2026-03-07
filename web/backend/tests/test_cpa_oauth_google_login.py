from types import SimpleNamespace

import pytest

from web.backend.services import cpa_oauth_antigravity as oauth


class FakeLocator:
    def __init__(self, page, kind, selector):
        self.page = page
        self.kind = kind
        self.selector = selector

    @property
    def first(self):
        return self

    async def count(self):
        if self.kind == "text" and self.selector in self.page.visible_text_targets:
            return 1
        if self.kind == "css" and self.selector in self.page.visible_locators:
            return 1
        return 0

    async def is_visible(self):
        return (await self.count()) > 0

    async def click(self, force=False):
        self.page.clicks.append((self.kind, self.selector))
        if self.kind == "text" and self.selector == self.page.account_email:
            self.page.password_visible = True
            self.page.body_text = "Enter your password"
        elif self.kind == "text" and self.selector == "Allow":
            self.page.url = self.page.callback_url
        elif self.kind == "text" and self.selector == "Sign in":
            self.page.url = self.page.callback_url
        elif self.kind == "text" and self.selector == "Sign in":
            self.page.url = self.page.callback_url


class FakeInput:
    def __init__(self, page, selector):
        self.page = page
        self.selector = selector

    async def is_visible(self):
        return True

    async def fill(self, value):
        self.page.fills.append((self.selector, value))
        if self.selector == 'input[type="password"]':
            self.page.totp_visible = True
            self.page.body_text = "Authenticator app"
        elif self.selector in ('input[name="totpPin"]', 'input[id="totpPin"]', 'input[type="tel"]'):
            self.page.allow_visible = True
            self.page.body_text = "Allow Google Antigravity to access your account"


class FakePage:
    def __init__(self):
        self.url = 'https://accounts.google.com/v3/signin/accountchooser'
        self.account_email = 'user@example.com'
        self.callback_url = 'http://localhost:51121/oauth-callback?code=abc&state=state-1'
        self.body_text = 'Choose an account\nuser@example.com\nUse another account'
        self.visible_text_targets = {'user@example.com'}
        self.visible_locators = set()
        self.password_visible = False
        self.totp_visible = False
        self.allow_visible = False
        self.fills = []
        self.clicks = []

    async def inner_text(self, selector):
        return self.body_text

    def locator(self, selector):
        if selector.startswith('text=') or selector.startswith('text="'):
            raw = selector.split('text=', 1)[1].strip('"')
            return FakeLocator(self, 'text', raw)
        if selector.startswith(':text('):
            raw = selector.split(':text(', 1)[1].rstrip(')').strip('"')
            return FakeLocator(self, 'text', raw)
        return FakeLocator(self, 'css', selector)

    async def wait_for_selector(self, selector, timeout=None, state=None):
        if selector == 'input[type="email"]':
            raise TimeoutError('email input absent')
        if selector == 'input[type="password"]' and self.password_visible:
            return FakeInput(self, selector)
        if selector == 'input[type="password"]':
            raise TimeoutError('password absent')
        if selector == 'input[name="totpPin"], input[id="totpPin"], input[type="tel"]' and self.totp_visible:
            return FakeInput(self, 'input[name="totpPin"]')
        raise TimeoutError(selector)

    async def fill(self, selector, value):
        self.fills.append((selector, value))

    async def click(self, selector):
        self.clicks.append(('css', selector))
        if selector == '#passwordNext >> button':
            self.totp_visible = True
            self.body_text = 'Authenticator app'
        elif selector == '#totpNext >> button':
            self.allow_visible = True
            self.body_text = 'Allow Google Antigravity to access your account'
        elif selector == '#identifierNext >> button':
            self.password_visible = True
            self.body_text = 'Enter your password'


@pytest.mark.asyncio
async def test_complete_google_oauth_login_uses_account_chooser_password_and_totp(monkeypatch):
    page = FakePage()

    async def fake_ensure_authenticator_method(page, log_callback=None):
        return True

    async def fake_handle_recovery_email_challenge(page, backup_email, log_callback=None):
        return False

    async def fake_detect_manual_verification(page):
        return False

    class FakeTotp:
        def __init__(self, secret):
            self.secret = secret

        def now(self):
            return '654321'

    monkeypatch.setattr(oauth, 'ensure_authenticator_method', fake_ensure_authenticator_method)
    monkeypatch.setattr(oauth, 'handle_recovery_email_challenge', fake_handle_recovery_email_challenge)
    monkeypatch.setattr(oauth, 'detect_manual_verification', fake_detect_manual_verification)
    monkeypatch.setattr(oauth.pyotp, 'TOTP', FakeTotp)

    result = await oauth._complete_google_oauth_login(
        page,
        {
            'email': 'user@example.com',
            'password': 'secret-pass',
            'secret_key': 'ABC DEF GHI',
            'recovery_email': 'recovery@example.com',
        },
        log_callback=None,
    )

    assert result['success'] is True
    assert ('input[type="password"]', 'secret-pass') in page.fills
    assert ('input[name="totpPin"]', '654321') in page.fills
    assert any(item[1] == 'user@example.com' for item in page.clicks)


@pytest.mark.asyncio
async def test_complete_google_oauth_login_switches_authenticator_before_totp_input(monkeypatch):
    page = FakePage()
    page.url = 'https://accounts.google.com/signin/v2/challenge'
    page.body_text = 'Try another way'
    page.visible_text_targets = set()
    page.password_visible = False
    page.totp_visible = False

    called = {'value': False}

    async def fake_ensure_authenticator_method(page, log_callback=None):
        called['value'] = True
        page.totp_visible = True
        page.body_text = 'Authenticator app'
        return True

    async def fake_handle_recovery_email_challenge(page, backup_email, log_callback=None):
        return False

    async def fake_detect_manual_verification(page):
        return False

    class FakeTotp:
        def __init__(self, secret):
            self.secret = secret

        def now(self):
            return '654321'

    monkeypatch.setattr(oauth, 'ensure_authenticator_method', fake_ensure_authenticator_method)
    monkeypatch.setattr(oauth, 'handle_recovery_email_challenge', fake_handle_recovery_email_challenge)
    monkeypatch.setattr(oauth, 'detect_manual_verification', fake_detect_manual_verification)
    monkeypatch.setattr(oauth.pyotp, 'TOTP', FakeTotp)

    result = await oauth._complete_google_oauth_login(
        page,
        {
            'email': 'user@example.com',
            'password': '',
            'secret_key': 'ABC DEF GHI',
            'recovery_email': 'recovery@example.com',
        },
        log_callback=None,
    )

    assert result['success'] is True
    assert called['value'] is True
    assert ('input[name="totpPin"]', '654321') in page.fills


@pytest.mark.asyncio
async def test_complete_google_oauth_login_handles_nativeapp_sign_in_confirmation(monkeypatch):
    page = FakePage()
    page.url = 'https://accounts.google.com/signin/oauth/firstparty/nativeapp'
    page.body_text = 'Make sure that you downloaded this app from Google\nSign in'
    page.visible_text_targets = {'Sign in'}
    page.password_visible = False
    page.totp_visible = False

    async def fake_ensure_authenticator_method(page, log_callback=None):
        return False

    async def fake_handle_recovery_email_challenge(page, backup_email, log_callback=None):
        return False

    async def fake_detect_manual_verification(page):
        return False

    monkeypatch.setattr(oauth, 'ensure_authenticator_method', fake_ensure_authenticator_method)
    monkeypatch.setattr(oauth, 'handle_recovery_email_challenge', fake_handle_recovery_email_challenge)
    monkeypatch.setattr(oauth, 'detect_manual_verification', fake_detect_manual_verification)

    result = await oauth._complete_google_oauth_login(
        page,
        {
            'email': 'user@example.com',
            'password': '',
            'secret_key': '',
            'recovery_email': '',
        },
        log_callback=None,
    )

    assert result['success'] is True
    assert any(item[1] == 'Sign in' for item in page.clicks)


def test_pick_active_page_prefers_google_auth_page_over_devtools():
    fallback = SimpleNamespace(url='https://fallback.example.com', is_closed=lambda: False)
    context = SimpleNamespace(
        pages=[
            SimpleNamespace(url='https://console.bitbrowser.net/workbench', is_closed=lambda: False),
            SimpleNamespace(url='https://accounts.google.com/v3/signin/accountchooser', is_closed=lambda: False),
            SimpleNamespace(url='devtools://devtools/bundled/devtools_app.html', is_closed=lambda: False),
        ]
    )

    selected = oauth._pick_active_page(context, fallback)
    assert selected.url.startswith('https://accounts.google.com')


@pytest.mark.asyncio
async def test_complete_google_oauth_login_clicks_native_app_sign_in_prompt(monkeypatch):
    page = FakePage()
    page.url = 'https://accounts.google.com/signin/oauth/firstparty/nativeapp'
    page.body_text = 'Make sure that you downloaded this app from Google\nSign in'
    page.visible_text_targets = {'Sign in'}
    page.password_visible = False
    page.totp_visible = False

    async def fake_ensure_authenticator_method(page, log_callback=None):
        return False

    async def fake_handle_recovery_email_challenge(page, backup_email, log_callback=None):
        return False

    async def fake_detect_manual_verification(page):
        return False

    monkeypatch.setattr(oauth, 'ensure_authenticator_method', fake_ensure_authenticator_method)
    monkeypatch.setattr(oauth, 'handle_recovery_email_challenge', fake_handle_recovery_email_challenge)
    monkeypatch.setattr(oauth, 'detect_manual_verification', fake_detect_manual_verification)

    result = await oauth._complete_google_oauth_login(
        page,
        {'email': 'user@example.com'},
        log_callback=None,
    )

    assert result['success'] is True
    assert any(item[1] == 'Sign in' for item in page.clicks)
