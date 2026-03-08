"""Tests verifying the CLI works without authentication in local (zero-auth) mode.

Covers:
- ``skillmeat auth login`` in explicit local mode (SKILLMEAT_AUTH_MODE=local)
- ``skillmeat auth login`` with no auth env vars configured (implicit local mode)
- General CLI commands work without any auth context
- SKILLMEAT_AUTH_MODE=local overrides issuer/client-id env vars
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner
from rich.console import Console

from skillmeat.cli import main
from skillmeat.cli.commands.auth import auth_cli, _is_local_mode


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_LOCAL_MODE_KEYWORDS = ("zero-auth", "local", "not required")


def _output_indicates_local_mode(output: str) -> bool:
    """Return True when the output signals zero-auth / local mode."""
    lowered = output.lower()
    return any(kw in lowered for kw in _LOCAL_MODE_KEYWORDS)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def runner(tmp_path, monkeypatch):
    """Isolated CliRunner with patched HOME and a plain Rich console."""
    home_dir = tmp_path / "home"
    home_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home_dir))

    # Patch class-level DEFAULT_CONFIG_DIR (evaluated at import time).
    from skillmeat.config import ConfigManager
    monkeypatch.setattr(ConfigManager, "DEFAULT_CONFIG_DIR", home_dir / ".skillmeat")

    # Replace module-level Rich console so ANSI codes don't pollute assertions.
    import skillmeat.cli as cli_module
    monkeypatch.setattr(cli_module, "console", Console(no_color=True, highlight=False))

    return CliRunner()


@pytest.fixture()
def clean_auth_env(monkeypatch):
    """Remove all auth-related environment variables from the process."""
    for var in (
        "SKILLMEAT_AUTH_MODE",
        "SKILLMEAT_AUTH_ISSUER_URL",
        "SKILLMEAT_AUTH_CLIENT_ID",
    ):
        monkeypatch.delenv(var, raising=False)


# ---------------------------------------------------------------------------
# Tests: _is_local_mode() unit tests
# ---------------------------------------------------------------------------


class TestIsLocalModeHelper:
    """Unit tests for the _is_local_mode() helper (no CLI invocation needed)."""

    def test_returns_true_when_auth_mode_is_local(self, monkeypatch):
        monkeypatch.setenv("SKILLMEAT_AUTH_MODE", "local")
        assert _is_local_mode() is True

    def test_returns_true_when_auth_mode_is_local_uppercase(self, monkeypatch):
        monkeypatch.setenv("SKILLMEAT_AUTH_MODE", "LOCAL")
        assert _is_local_mode() is True

    def test_returns_true_for_unknown_auth_mode(self, monkeypatch):
        monkeypatch.setenv("SKILLMEAT_AUTH_MODE", "magic_sso")
        assert _is_local_mode() is True

    def test_returns_false_when_auth_mode_is_clerk_with_vars(self, monkeypatch):
        monkeypatch.setenv("SKILLMEAT_AUTH_MODE", "clerk")
        monkeypatch.setenv("SKILLMEAT_AUTH_ISSUER_URL", "https://example.clerk.accounts.dev")
        monkeypatch.setenv("SKILLMEAT_AUTH_CLIENT_ID", "client_abc123")
        # clerk mode with both vars set — settings also reflects auth enabled
        mock_settings = MagicMock()
        mock_settings.auth_enabled = True
        mock_settings.auth_provider = "clerk"
        with patch("skillmeat.api.config.get_settings", return_value=mock_settings):
            assert _is_local_mode() is False

    def test_returns_true_when_no_issuer_or_client_id(self, monkeypatch, clean_auth_env):
        """No auth env vars at all and no reachable APISettings → local mode."""
        with patch("skillmeat.api.config.get_settings", side_effect=ImportError):
            assert _is_local_mode() is True

    def test_returns_true_when_settings_auth_disabled(self, monkeypatch, clean_auth_env):
        mock_settings = MagicMock()
        mock_settings.auth_enabled = False
        mock_settings.auth_provider = "local"
        with patch("skillmeat.api.config.get_settings", return_value=mock_settings):
            assert _is_local_mode() is True

    def test_returns_false_when_settings_auth_enabled(self, monkeypatch, clean_auth_env):
        mock_settings = MagicMock()
        mock_settings.auth_enabled = True
        mock_settings.auth_provider = "clerk"
        with patch("skillmeat.api.config.get_settings", return_value=mock_settings):
            assert _is_local_mode() is False

    def test_local_mode_overrides_issuer_and_client_id(self, monkeypatch):
        """SKILLMEAT_AUTH_MODE=local wins even when Clerk vars are present."""
        monkeypatch.setenv("SKILLMEAT_AUTH_MODE", "local")
        monkeypatch.setenv("SKILLMEAT_AUTH_ISSUER_URL", "https://example.clerk.accounts.dev")
        monkeypatch.setenv("SKILLMEAT_AUTH_CLIENT_ID", "client_abc123")
        assert _is_local_mode() is True


# ---------------------------------------------------------------------------
# Tests: auth login in local mode
# ---------------------------------------------------------------------------


class TestAuthLoginLocalMode:
    """Test ``skillmeat auth login`` behaviour in zero-auth / local mode."""

    def test_explicit_local_mode_via_env_var(self, runner, monkeypatch, clean_auth_env):
        """SKILLMEAT_AUTH_MODE=local prints local-mode message and exits 0."""
        monkeypatch.setenv("SKILLMEAT_AUTH_MODE", "local")

        result = runner.invoke(auth_cli, ["login"])

        assert result.exit_code == 0, result.output
        assert _output_indicates_local_mode(result.output), (
            f"Expected local-mode indication in output, got:\n{result.output}"
        )

    def test_explicit_local_mode_via_main_entrypoint(self, runner, monkeypatch, clean_auth_env):
        """``skillmeat auth login`` through the main CLI group also exits 0."""
        monkeypatch.setenv("SKILLMEAT_AUTH_MODE", "local")

        result = runner.invoke(main, ["auth", "login"])

        assert result.exit_code == 0, result.output
        assert _output_indicates_local_mode(result.output), (
            f"Expected local-mode indication in output, got:\n{result.output}"
        )

    def test_implicit_local_mode_no_auth_vars_settings_disabled(
        self, runner, monkeypatch, clean_auth_env
    ):
        """No auth env vars + settings.auth_enabled=False → local mode, exit 0."""
        mock_settings = MagicMock()
        mock_settings.auth_enabled = False
        mock_settings.auth_provider = "local"

        with patch("skillmeat.api.config.get_settings", return_value=mock_settings):
            result = runner.invoke(auth_cli, ["login"])

        assert result.exit_code == 0, result.output
        assert _output_indicates_local_mode(result.output), (
            f"Expected local-mode indication in output, got:\n{result.output}"
        )

    def test_implicit_local_mode_no_env_vars_settings_unreachable(
        self, runner, monkeypatch, clean_auth_env
    ):
        """When APISettings is not importable, absence of Clerk vars means local."""
        with patch("skillmeat.api.config.get_settings", side_effect=Exception("not installed")):
            result = runner.invoke(auth_cli, ["login"])

        assert result.exit_code == 0, result.output
        assert _output_indicates_local_mode(result.output), (
            f"Expected local-mode indication in output, got:\n{result.output}"
        )

    def test_no_network_calls_in_local_mode(self, runner, monkeypatch, clean_auth_env):
        """Confirm that login in local mode makes no outbound HTTP requests."""
        monkeypatch.setenv("SKILLMEAT_AUTH_MODE", "local")

        # Patch the device-code flow so any accidental call raises immediately.
        with patch(
            "skillmeat.cli.commands.auth.DeviceCodeFlow",
            side_effect=AssertionError("DeviceCodeFlow should not be instantiated in local mode"),
        ):
            result = runner.invoke(auth_cli, ["login"])

        assert result.exit_code == 0, result.output

    def test_local_mode_overrides_clerk_env_vars(self, runner, monkeypatch):
        """SKILLMEAT_AUTH_MODE=local beats SKILLMEAT_AUTH_ISSUER_URL + CLIENT_ID."""
        monkeypatch.setenv("SKILLMEAT_AUTH_MODE", "local")
        monkeypatch.setenv("SKILLMEAT_AUTH_ISSUER_URL", "https://example.clerk.accounts.dev")
        monkeypatch.setenv("SKILLMEAT_AUTH_CLIENT_ID", "client_abc123")

        result = runner.invoke(auth_cli, ["login"])

        assert result.exit_code == 0, result.output
        assert _output_indicates_local_mode(result.output), (
            f"Expected local-mode indication in output, got:\n{result.output}"
        )


# ---------------------------------------------------------------------------
# Tests: general CLI commands work without any auth context
# ---------------------------------------------------------------------------


class TestCliCommandsWithoutAuth:
    """Verify that common CLI commands are usable without any auth configuration."""

    def test_main_help(self, runner, clean_auth_env):
        """``skillmeat --help`` prints help text and exits 0."""
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0, result.output
        assert "usage" in result.output.lower() or "commands" in result.output.lower(), (
            f"Expected help text, got:\n{result.output}"
        )

    def test_auth_help(self, runner, clean_auth_env):
        """``skillmeat auth --help`` works without auth configured."""
        result = runner.invoke(main, ["auth", "--help"])

        assert result.exit_code == 0, result.output
        assert "login" in result.output.lower(), (
            f"Expected 'login' sub-command in help output, got:\n{result.output}"
        )

    def test_auth_login_help(self, runner, clean_auth_env):
        """``skillmeat auth login --help`` shows option docs, exits 0."""
        result = runner.invoke(main, ["auth", "login", "--help"])

        assert result.exit_code == 0, result.output
        assert "--timeout" in result.output, (
            f"Expected --timeout option in help output, got:\n{result.output}"
        )

    def test_list_help(self, runner, clean_auth_env):
        """``skillmeat list --help`` is available without auth."""
        result = runner.invoke(main, ["list", "--help"])

        assert result.exit_code == 0, result.output

    def test_search_help(self, runner, clean_auth_env):
        """``skillmeat search --help`` is available without auth."""
        result = runner.invoke(main, ["search", "--help"])

        assert result.exit_code == 0, result.output
