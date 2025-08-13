import os
from backend.routes import oauth as oauth_mod


def test_is_allowed_default_allows_same_origin_none():
    os.environ.pop('OAUTH_ALLOWED_REDIRECT_HOSTS', None)
    assert oauth_mod._is_allowed(None) is True
    assert oauth_mod._is_allowed('http://localhost:5173') is True


def test_is_allowed_respects_allowlist():
    os.environ['OAUTH_ALLOWED_REDIRECT_HOSTS'] = 'example.com,localhost:5173'
    assert oauth_mod._is_allowed('http://example.com/path') is True
    assert oauth_mod._is_allowed('http://localhost:5173/cb') is True
    assert oauth_mod._is_allowed('http://evil.com/') is False 