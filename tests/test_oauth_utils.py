import sys
import types

# Stub missing legacy onyx import before importing oauth module
if 'onyx' not in sys.modules:
	onyx = types.ModuleType('onyx')
	onyx.__path__ = []  # mark as package
	configs = types.ModuleType('onyx.configs')
	configs.__path__ = []  # mark as package
	app_configs = types.ModuleType('onyx.configs.app_configs')
	setattr(app_configs, 'INTEGRATION_TESTS_MODE', True)
	configs.app_configs = app_configs  # type: ignore[attr-defined]
	onyx.configs = configs  # type: ignore[attr-defined]
	sys.modules['onyx'] = onyx
	sys.modules['onyx.configs'] = configs
	sys.modules['onyx.configs.app_configs'] = app_configs

from backend.routes import oauth as oauth_mod  # noqa: E402


def test_is_allowed_same_origin():
	assert oauth_mod._is_allowed(None) is True


def test_is_allowed_with_env(monkeypatch):
	monkeypatch.setenv("OAUTH_ALLOWED_REDIRECT_HOSTS", "example.com,foo.bar")
	assert oauth_mod._is_allowed("https://example.com/cb") is True
	assert oauth_mod._is_allowed("https://foo.bar/x") is True
	assert oauth_mod._is_allowed("https://nope.invalid") is False 