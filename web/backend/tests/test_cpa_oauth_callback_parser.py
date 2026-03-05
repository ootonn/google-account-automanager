from web.backend.services.cpa_oauth_antigravity import is_oauth_callback_url


def test_detect_callback_url_with_code_and_state():
    url = "https://example.com/callback?code=abc&state=xyz"
    assert is_oauth_callback_url(url) is True


def test_reject_non_callback_url():
    url = "https://example.com/callback?foo=bar"
    assert is_oauth_callback_url(url) is False
