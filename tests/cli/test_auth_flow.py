"""Integration tests for CLI auth flow: device code, PAT token, and credential storage.

Covers:
1. Device code flow initiation (mocked HTTP) → returns user code and URL
2. Device code polling → successful token exchange
3. Device code flow timeout → appropriate error
4. PAT token command → stores token correctly
5. PAT token with invalid format → error message (local-mode guard)
6. Logout command → clears stored credentials
7. Token refresh flow (mocked) → updates stored token
8. Credentials stored securely (file permissions / backend)
9. Token retrieval after storage → correct token returned
10. Auth status via is_authenticated() after store/clear lifecycle
"""

from __future__ import annotations

import json
import re
import stat
import time
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from skillmeat.cli.auth_flow import (
    AuthConfig,
    DeviceAuthResponse,
    DeviceCodeAccessDeniedError,
    DeviceCodeExpiredError,
    DeviceCodeFlow,
    DeviceCodeFlowError,
    DeviceCodeResult,
    DeviceCodeTimeoutError,
)
from skillmeat.cli.commands.auth import _run_device_code_flow, auth_cli
from skillmeat.cli.credential_store import (
    CredentialStore,
    StoredCredentials,
    _FileBackend,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes so assertions work on plain strings."""
    return re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])").sub("", text)


def _make_device_auth_response(**overrides) -> DeviceAuthResponse:
    defaults = dict(
        device_code="dev-code-abc",
        user_code="ABCD-1234",
        verification_uri="https://auth.example.com/activate",
        expires_in=300,
        interval=1,
        verification_uri_complete="https://auth.example.com/activate?user_code=ABCD-1234",
    )
    defaults.update(overrides)
    return DeviceAuthResponse(**defaults)


def _make_token_result(**overrides) -> DeviceCodeResult:
    defaults = dict(
        access_token="access-tok-xyz",
        refresh_token="refresh-tok-xyz",
        expires_in=3600,
        token_type="Bearer",
        id_token=None,
    )
    defaults.update(overrides)
    return DeviceCodeResult(**defaults)


def _make_auth_config() -> AuthConfig:
    return AuthConfig(
        issuer_url="https://auth.example.com",
        client_id="test-client-id",
        audience=None,
    )


def _make_mock_http_client(
    *,
    device_auth_data: Optional[dict] = None,
    token_data: Optional[dict] = None,
    token_pending_first: bool = False,
) -> MagicMock:
    """Build an httpx-compatible mock that handles both POST endpoints."""
    client = MagicMock()

    _device_auth_data = device_auth_data or {
        "device_code": "dev-code-abc",
        "user_code": "ABCD-1234",
        "verification_uri": "https://auth.example.com/activate",
        "expires_in": 300,
        "interval": 1,
    }

    _token_data = token_data or {
        "access_token": "access-tok-xyz",
        "refresh_token": "refresh-tok-xyz",
        "expires_in": 3600,
        "token_type": "Bearer",
    }

    # Device-authorization response
    device_resp = MagicMock()
    device_resp.status_code = 200
    device_resp.is_success = True
    device_resp.json.return_value = _device_auth_data
    device_resp.raise_for_status.return_value = None

    # Token-poll responses
    if token_pending_first:
        pending_resp = MagicMock()
        pending_resp.status_code = 400
        pending_resp.is_success = False
        pending_resp.json.return_value = {"error": "authorization_pending"}

        success_resp = MagicMock()
        success_resp.status_code = 200
        success_resp.is_success = True
        success_resp.json.return_value = _token_data

        token_responses = [pending_resp, success_resp]
    else:
        success_resp = MagicMock()
        success_resp.status_code = 200
        success_resp.is_success = True
        success_resp.json.return_value = _token_data
        token_responses = [success_resp]

    call_count = {"n": 0}

    def _post(url, **kwargs):
        if "device/authorize" in url:
            return device_resp
        # Token endpoint — return responses in sequence
        idx = min(call_count["n"], len(token_responses) - 1)
        call_count["n"] += 1
        return token_responses[idx]

    client.post.side_effect = _post
    return client


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def file_backend(tmp_path) -> _FileBackend:
    """Return a _FileBackend pointed at a temp dir, isolated from real ~/.skillmeat."""
    creds_path = tmp_path / ".skillmeat" / "credentials.json"
    return _FileBackend(credentials_path=creds_path)


@pytest.fixture
def credential_store(file_backend) -> CredentialStore:
    return CredentialStore(backend=file_backend)


@pytest.fixture
def auth_config() -> AuthConfig:
    return _make_auth_config()


# ===========================================================================
# 1. Device code flow initiation
# ===========================================================================


class TestDeviceCodeFlowStart:
    """DeviceCodeFlow.start() — initiation, config validation, response parsing."""

    def test_start_returns_device_auth_response(self, auth_config):
        """start() returns a correctly populated DeviceAuthResponse."""
        http = _make_mock_http_client()
        flow = DeviceCodeFlow(config=auth_config, http_client=http)
        result = flow.start()

        assert result.user_code == "ABCD-1234"
        assert result.verification_uri == "https://auth.example.com/activate"
        assert result.device_code == "dev-code-abc"
        assert result.expires_in == 300
        assert result.interval == 1

    def test_start_posts_to_device_authorization_endpoint(self, auth_config):
        """start() POSTs to the correct endpoint derived from issuer_url."""
        http = _make_mock_http_client()
        flow = DeviceCodeFlow(config=auth_config, http_client=http)
        flow.start()

        call_args = http.post.call_args
        assert "https://auth.example.com/oauth/device/authorize" in str(call_args)

    def test_start_includes_client_id_and_scope(self, auth_config):
        """start() sends client_id and scope in the POST body."""
        http = _make_mock_http_client()
        flow = DeviceCodeFlow(config=auth_config, http_client=http)
        flow.start()

        call_kwargs = http.post.call_args[1]
        data = call_kwargs.get("data", {})
        assert data.get("client_id") == "test-client-id"
        assert "openid" in data.get("scope", "")

    def test_start_includes_audience_when_configured(self):
        """start() sends audience when AuthConfig.audience is set."""
        config = AuthConfig(
            issuer_url="https://auth.example.com",
            client_id="test-client-id",
            audience="https://api.skillmeat.io",
        )
        http = _make_mock_http_client()
        flow = DeviceCodeFlow(config=config, http_client=http)
        flow.start()

        call_kwargs = http.post.call_args[1]
        data = call_kwargs.get("data", {})
        assert data.get("audience") == "https://api.skillmeat.io"

    def test_start_raises_config_error_when_not_configured(self):
        """start() raises DeviceCodeConfigError when issuer_url or client_id missing."""
        from skillmeat.cli.auth_flow import DeviceCodeConfigError

        config = AuthConfig(issuer_url="", client_id="")
        flow = DeviceCodeFlow(config=config, http_client=MagicMock())
        with pytest.raises(DeviceCodeConfigError, match="SKILLMEAT_AUTH_ISSUER_URL"):
            flow.start()

    def test_start_parses_verification_uri_complete(self, auth_config):
        """start() captures verification_uri_complete when present."""
        http = _make_mock_http_client(
            device_auth_data={
                "device_code": "dc",
                "user_code": "CODE-99",
                "verification_uri": "https://auth.example.com/activate",
                "verification_uri_complete": "https://auth.example.com/activate?user_code=CODE-99",
                "expires_in": 60,
                "interval": 5,
            }
        )
        flow = DeviceCodeFlow(config=auth_config, http_client=http)
        result = flow.start()
        assert result.verification_uri_complete == "https://auth.example.com/activate?user_code=CODE-99"

    def test_start_defaults_interval_to_5_when_missing(self, auth_config):
        """start() defaults interval to 5 when server omits the field."""
        http = _make_mock_http_client(
            device_auth_data={
                "device_code": "dc",
                "user_code": "ZZZZ",
                "verification_uri": "https://auth.example.com/activate",
                "expires_in": 300,
                # no "interval" key
            }
        )
        flow = DeviceCodeFlow(config=auth_config, http_client=http)
        result = flow.start()
        assert result.interval == 5


# ===========================================================================
# 2. Device code polling — successful token exchange
# ===========================================================================


class TestDeviceCodeFlowPoll:
    """DeviceCodeFlow.poll() — happy path and error paths."""

    def test_poll_returns_device_code_result_on_success(self, auth_config):
        """poll() returns DeviceCodeResult when token endpoint responds with success."""
        http = _make_mock_http_client()
        flow = DeviceCodeFlow(config=auth_config, http_client=http)
        device_auth = _make_device_auth_response()
        result = flow.poll(device_auth, timeout=30.0)

        assert result.access_token == "access-tok-xyz"
        assert result.refresh_token == "refresh-tok-xyz"
        assert result.expires_in == 3600
        assert result.token_type == "Bearer"

    def test_poll_retries_on_authorization_pending(self, auth_config):
        """poll() continues polling when server returns authorization_pending."""
        http = _make_mock_http_client(token_pending_first=True)
        flow = DeviceCodeFlow(config=auth_config, http_client=http)
        device_auth = _make_device_auth_response(interval=0)

        result = flow.poll(device_auth, timeout=30.0)
        assert result.access_token == "access-tok-xyz"
        # Token endpoint was called at least twice (pending + success)
        token_calls = [c for c in http.post.call_args_list if "oauth/token" in str(c)]
        assert len(token_calls) >= 2

    def test_poll_raises_expired_on_expired_token_error(self, auth_config):
        """poll() raises DeviceCodeExpiredError when server returns expired_token."""
        expired_resp = MagicMock()
        expired_resp.status_code = 400
        expired_resp.is_success = False
        expired_resp.json.return_value = {"error": "expired_token"}

        http = MagicMock()
        http.post.return_value = expired_resp

        flow = DeviceCodeFlow(config=auth_config, http_client=http)
        device_auth = _make_device_auth_response(interval=0)

        with pytest.raises(DeviceCodeExpiredError):
            flow.poll(device_auth, timeout=30.0)

    def test_poll_raises_access_denied(self, auth_config):
        """poll() raises DeviceCodeAccessDeniedError when user declines."""
        denied_resp = MagicMock()
        denied_resp.status_code = 400
        denied_resp.is_success = False
        denied_resp.json.return_value = {"error": "access_denied"}

        http = MagicMock()
        http.post.return_value = denied_resp

        flow = DeviceCodeFlow(config=auth_config, http_client=http)
        device_auth = _make_device_auth_response(interval=0)

        with pytest.raises(DeviceCodeAccessDeniedError):
            flow.poll(device_auth, timeout=30.0)

    def test_poll_raises_generic_flow_error_on_unknown_error(self, auth_config):
        """poll() raises DeviceCodeFlowError for unrecognised server errors."""
        error_resp = MagicMock()
        error_resp.status_code = 400
        error_resp.is_success = False
        error_resp.json.return_value = {"error": "server_error", "error_description": "boom"}

        http = MagicMock()
        http.post.return_value = error_resp

        flow = DeviceCodeFlow(config=auth_config, http_client=http)
        device_auth = _make_device_auth_response(interval=0)

        with pytest.raises(DeviceCodeFlowError, match="server_error"):
            flow.poll(device_auth, timeout=30.0)

    def test_poll_backs_off_on_slow_down(self, auth_config):
        """poll() increases the polling interval by 5 seconds on slow_down."""
        slow_down_resp = MagicMock()
        slow_down_resp.status_code = 400
        slow_down_resp.is_success = False
        slow_down_resp.json.return_value = {"error": "slow_down"}

        success_resp = MagicMock()
        success_resp.status_code = 200
        success_resp.is_success = True
        success_resp.json.return_value = {
            "access_token": "tok",
            "token_type": "Bearer",
        }

        responses = iter([slow_down_resp, success_resp])
        http = MagicMock()
        http.post.side_effect = lambda url, **kw: next(responses)

        device_auth = _make_device_auth_response(interval=0)

        with patch("skillmeat.cli.auth_flow.time.sleep") as mock_sleep:
            flow = DeviceCodeFlow(config=auth_config, http_client=http)
            result = flow.poll(device_auth, timeout=60.0)

        assert result.access_token == "tok"
        # After slow_down, interval becomes 5; sleep was called with ≥5 on second call
        sleep_calls = [c.args[0] for c in mock_sleep.call_args_list]
        assert any(s >= 5.0 for s in sleep_calls)


# ===========================================================================
# 3. Device code flow timeout
# ===========================================================================


class TestDeviceCodeFlowTimeout:
    """DeviceCodeFlow.poll() timeout behaviour."""

    def test_poll_raises_timeout_when_deadline_exceeded(self, auth_config):
        """poll() raises DeviceCodeTimeoutError when timeout elapses."""
        pending_resp = MagicMock()
        pending_resp.status_code = 400
        pending_resp.is_success = False
        pending_resp.json.return_value = {"error": "authorization_pending"}

        http = MagicMock()
        http.post.return_value = pending_resp

        device_auth = _make_device_auth_response(interval=0)

        # Use a very short timeout so the loop exceeds it quickly without sleeping
        with patch("skillmeat.cli.auth_flow.time.sleep"):
            with patch("skillmeat.cli.auth_flow.time.monotonic") as mock_mono:
                # First call: before loop (deadline calc); rest: advance past deadline
                mock_mono.side_effect = [0.0, 100.0, 100.0, 100.0]
                flow = DeviceCodeFlow(config=auth_config, http_client=http)
                with pytest.raises(DeviceCodeTimeoutError):
                    flow.poll(device_auth, timeout=10.0)


# ===========================================================================
# 4. PAT token command
# ===========================================================================


class TestPATTokenCommand:
    """``skillmeat auth token <PAT>`` stores the PAT via CredentialStore."""

    def test_token_command_stores_pat(self, runner, tmp_path):
        """token command stores the PAT and reports success."""
        creds_path = tmp_path / ".skillmeat" / "credentials.json"
        file_be = _FileBackend(credentials_path=creds_path)
        store = CredentialStore(backend=file_be)

        with patch("skillmeat.cli.commands.auth._is_local_mode", return_value=False):
            with patch("skillmeat.cli.commands.auth.CredentialStore", return_value=store):
                result = runner.invoke(auth_cli, ["token", "sk_live_abc123def456"])

        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "stored" in output.lower()

        creds = store.load()
        assert creds is not None
        assert creds.access_token == "sk_live_abc123def456"

    def test_token_command_stores_bearer_type(self, runner, tmp_path):
        """PAT stored via token command uses Bearer token_type."""
        creds_path = tmp_path / ".skillmeat" / "credentials.json"
        file_be = _FileBackend(credentials_path=creds_path)
        store = CredentialStore(backend=file_be)

        with patch("skillmeat.cli.commands.auth._is_local_mode", return_value=False):
            with patch("skillmeat.cli.commands.auth.CredentialStore", return_value=store):
                runner.invoke(auth_cli, ["token", "sk_live_mytoken"])

        creds = store.load()
        assert creds.token_type == "Bearer"
        assert creds.refresh_token is None
        assert creds.expires_at is None

    def test_token_command_shows_local_mode_message(self, runner):
        """token command prints informational message in local mode."""
        with patch("skillmeat.cli.commands.auth._is_local_mode", return_value=True):
            result = runner.invoke(auth_cli, ["token", "sk_live_whatever"])

        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "local" in output.lower()

    def test_token_command_with_validate_flag_warns(self, runner, tmp_path):
        """token --validate flag prints a warning about unimplemented validation."""
        creds_path = tmp_path / ".skillmeat" / "credentials.json"
        file_be = _FileBackend(credentials_path=creds_path)
        store = CredentialStore(backend=file_be)

        with patch("skillmeat.cli.commands.auth._is_local_mode", return_value=False):
            with patch("skillmeat.cli.commands.auth.CredentialStore", return_value=store):
                result = runner.invoke(
                    auth_cli, ["token", "sk_live_abc123", "--validate"]
                )

        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "warning" in output.lower() or "not yet implemented" in output.lower()


# ===========================================================================
# 5. Login command — device code CLI integration
# ===========================================================================


class TestLoginCommand:
    """``skillmeat auth login`` end-to-end through the CLI."""

    def test_login_shows_user_code_and_url(self, runner):
        """login command displays the user_code and verification_uri."""
        http = _make_mock_http_client()

        mock_flow = MagicMock()
        mock_flow.start.return_value = _make_device_auth_response()
        mock_flow.poll.return_value = _make_token_result()

        mock_store = MagicMock()
        mock_store.backend_name = "file"

        with patch("skillmeat.cli.commands.auth._is_local_mode", return_value=False):
            with patch(
                "skillmeat.cli.commands.auth.DeviceCodeFlow", return_value=mock_flow
            ):
                with patch(
                    "skillmeat.cli.commands.auth.CredentialStore", return_value=mock_store
                ):
                    with patch("webbrowser.open", return_value=True):
                        result = runner.invoke(auth_cli, ["login", "--no-browser"])

        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "ABCD-1234" in output
        assert "https://auth.example.com/activate" in output

    def test_login_reports_success(self, runner):
        """login command reports successful authentication."""
        mock_flow = MagicMock()
        mock_flow.start.return_value = _make_device_auth_response()
        mock_flow.poll.return_value = _make_token_result()

        mock_store = MagicMock()
        mock_store.backend_name = "file"

        with patch("skillmeat.cli.commands.auth._is_local_mode", return_value=False):
            with patch(
                "skillmeat.cli.commands.auth.DeviceCodeFlow", return_value=mock_flow
            ):
                with patch(
                    "skillmeat.cli.commands.auth.CredentialStore", return_value=mock_store
                ):
                    result = runner.invoke(auth_cli, ["login", "--no-browser"])

        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "success" in output.lower() or "logged in" in output.lower()

    def test_login_persists_credentials(self, runner, tmp_path):
        """login command calls CredentialStore.store() with the token result."""
        mock_flow = MagicMock()
        mock_flow.start.return_value = _make_device_auth_response()
        token_result = _make_token_result()
        mock_flow.poll.return_value = token_result

        mock_store = MagicMock()
        mock_store.backend_name = "file"

        with patch("skillmeat.cli.commands.auth._is_local_mode", return_value=False):
            with patch(
                "skillmeat.cli.commands.auth.DeviceCodeFlow", return_value=mock_flow
            ):
                with patch(
                    "skillmeat.cli.commands.auth.CredentialStore", return_value=mock_store
                ):
                    runner.invoke(auth_cli, ["login", "--no-browser"])

        mock_store.store.assert_called_once_with(token_result)

    def test_login_local_mode_prints_info_and_exits_cleanly(self, runner):
        """login in local mode prints informational message, exit 0."""
        with patch("skillmeat.cli.commands.auth._is_local_mode", return_value=True):
            result = runner.invoke(auth_cli, ["login"])

        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "local" in output.lower()

    def test_login_access_denied_exits_nonzero(self, runner):
        """login exits 1 when user denies the authorization request."""
        mock_flow = MagicMock()
        mock_flow.start.return_value = _make_device_auth_response()
        mock_flow.poll.side_effect = DeviceCodeAccessDeniedError("denied")

        with patch("skillmeat.cli.commands.auth._is_local_mode", return_value=False):
            with patch(
                "skillmeat.cli.commands.auth.DeviceCodeFlow", return_value=mock_flow
            ):
                result = runner.invoke(auth_cli, ["login", "--no-browser"])

        assert result.exit_code == 1
        output = strip_ansi(result.output)
        assert "denied" in output.lower()

    def test_login_expired_device_code_exits_nonzero(self, runner):
        """login exits 1 when the device code expires before authorization."""
        mock_flow = MagicMock()
        mock_flow.start.return_value = _make_device_auth_response()
        mock_flow.poll.side_effect = DeviceCodeExpiredError("expired")

        with patch("skillmeat.cli.commands.auth._is_local_mode", return_value=False):
            with patch(
                "skillmeat.cli.commands.auth.DeviceCodeFlow", return_value=mock_flow
            ):
                result = runner.invoke(auth_cli, ["login", "--no-browser"])

        assert result.exit_code == 1
        output = strip_ansi(result.output)
        assert "expired" in output.lower()

    def test_login_timeout_exits_nonzero(self, runner):
        """login exits 1 when the polling timeout elapses."""
        mock_flow = MagicMock()
        mock_flow.start.return_value = _make_device_auth_response()
        mock_flow.poll.side_effect = DeviceCodeTimeoutError("timed out")

        with patch("skillmeat.cli.commands.auth._is_local_mode", return_value=False):
            with patch(
                "skillmeat.cli.commands.auth.DeviceCodeFlow", return_value=mock_flow
            ):
                result = runner.invoke(auth_cli, ["login", "--no-browser"])

        assert result.exit_code == 1
        output = strip_ansi(result.output)
        assert "timed out" in output.lower() or "timeout" in output.lower()

    def test_login_config_error_propagates_as_click_exception(self, runner):
        """login wraps DeviceCodeConfigError in ClickException (exit 1, error in output)."""
        from skillmeat.cli.auth_flow import DeviceCodeConfigError

        mock_flow = MagicMock()
        mock_flow.start.side_effect = DeviceCodeConfigError("SKILLMEAT_AUTH_ISSUER_URL not set")

        with patch("skillmeat.cli.commands.auth._is_local_mode", return_value=False):
            with patch(
                "skillmeat.cli.commands.auth.DeviceCodeFlow", return_value=mock_flow
            ):
                result = runner.invoke(auth_cli, ["login", "--no-browser"])

        assert result.exit_code != 0
        output = strip_ansi(result.output)
        assert "auth_issuer_url" in output.lower() or "issuer" in output.lower()


# ===========================================================================
# 6. Logout command
# ===========================================================================


class TestLogoutCommand:
    """``skillmeat auth logout`` clears stored credentials."""

    def test_logout_clears_credentials(self, runner, tmp_path):
        """logout command removes stored credentials from the backend."""
        creds_path = tmp_path / ".skillmeat" / "credentials.json"
        file_be = _FileBackend(credentials_path=creds_path)
        store = CredentialStore(backend=file_be)

        # Pre-populate credentials
        store.store(_make_token_result())
        assert store.is_authenticated()

        with patch("skillmeat.cli.commands.auth.CredentialStore", return_value=store):
            result = runner.invoke(auth_cli, ["logout"])

        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "logout" in output.lower() or "logged out" in output.lower()
        assert not store.is_authenticated()

    def test_logout_succeeds_when_no_credentials_stored(self, runner, tmp_path):
        """logout exits cleanly even when no credentials are stored."""
        creds_path = tmp_path / ".skillmeat" / "credentials.json"
        file_be = _FileBackend(credentials_path=creds_path)
        store = CredentialStore(backend=file_be)

        with patch("skillmeat.cli.commands.auth.CredentialStore", return_value=store):
            result = runner.invoke(auth_cli, ["logout"])

        assert result.exit_code == 0

    def test_logout_calls_store_clear(self, runner):
        """logout delegates to CredentialStore.clear()."""
        mock_store = MagicMock()

        with patch("skillmeat.cli.commands.auth.CredentialStore", return_value=mock_store):
            runner.invoke(auth_cli, ["logout"])

        mock_store.clear.assert_called_once()


# ===========================================================================
# 7. Token refresh flow
# ===========================================================================


class TestTokenRefreshFlow:
    """CredentialStore.refresh_if_needed() — updates stored token via HTTP."""

    def _expired_creds(self, tmp_path, refresh_token: str = "old-refresh-tok"):
        """Store credentials that are already expired (expires_at in the past)."""
        creds_path = tmp_path / ".skillmeat" / "credentials.json"
        file_be = _FileBackend(credentials_path=creds_path)
        store = CredentialStore(backend=file_be)

        expired_creds = StoredCredentials(
            access_token="old-access-tok",
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_at=time.time() - 1000,  # expired 1000s ago
            stored_at=time.time() - 2000,
        )
        file_be.save(expired_creds)
        return store

    def test_refresh_updates_access_token(self, tmp_path):
        """refresh_if_needed() replaces the access token when it has expired."""
        store = self._expired_creds(tmp_path)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "access_token": "new-access-tok",
            "refresh_token": "new-refresh-tok",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        mock_http = MagicMock()
        mock_http.post.return_value = mock_response

        env = {
            "SKILLMEAT_AUTH_ISSUER_URL": "https://auth.example.com",
            "SKILLMEAT_AUTH_CLIENT_ID": "test-client-id",
        }
        with patch.dict("os.environ", env, clear=False):
            new_creds = store.refresh_if_needed(http_client=mock_http)

        assert new_creds is not None
        assert new_creds.access_token == "new-access-tok"
        assert new_creds.refresh_token == "new-refresh-tok"

    def test_refresh_persists_new_credentials(self, tmp_path):
        """refresh_if_needed() writes the refreshed credentials to storage."""
        store = self._expired_creds(tmp_path)

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "access_token": "persisted-tok",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        mock_http = MagicMock()
        mock_http.post.return_value = mock_response

        env = {
            "SKILLMEAT_AUTH_ISSUER_URL": "https://auth.example.com",
            "SKILLMEAT_AUTH_CLIENT_ID": "test-client-id",
        }
        with patch.dict("os.environ", env, clear=False):
            store.refresh_if_needed(http_client=mock_http)

        # Reload from backend to verify persistence
        stored = store.load()
        assert stored is not None
        assert stored.access_token == "persisted-tok"

    def test_refresh_returns_existing_when_not_expired(self, tmp_path):
        """refresh_if_needed() returns existing credentials untouched when still valid."""
        creds_path = tmp_path / ".skillmeat" / "credentials.json"
        file_be = _FileBackend(credentials_path=creds_path)
        store = CredentialStore(backend=file_be)

        valid_creds = StoredCredentials(
            access_token="still-valid-tok",
            token_type="Bearer",
            expires_at=time.time() + 7200,  # expires in 2 hours
            stored_at=time.time(),
        )
        file_be.save(valid_creds)

        mock_http = MagicMock()
        result = store.refresh_if_needed(http_client=mock_http)

        assert result is not None
        assert result.access_token == "still-valid-tok"
        mock_http.post.assert_not_called()

    def test_refresh_returns_none_when_no_credentials(self, tmp_path):
        """refresh_if_needed() returns None when nothing is stored."""
        creds_path = tmp_path / ".skillmeat" / "credentials.json"
        file_be = _FileBackend(credentials_path=creds_path)
        store = CredentialStore(backend=file_be)

        result = store.refresh_if_needed(http_client=MagicMock())
        assert result is None

    def test_refresh_returns_none_when_no_refresh_token(self, tmp_path):
        """refresh_if_needed() returns None when expired but no refresh_token."""
        creds_path = tmp_path / ".skillmeat" / "credentials.json"
        file_be = _FileBackend(credentials_path=creds_path)
        store = CredentialStore(backend=file_be)

        expired_creds = StoredCredentials(
            access_token="expired-tok",
            token_type="Bearer",
            refresh_token=None,  # no refresh token
            expires_at=time.time() - 1000,
            stored_at=time.time() - 2000,
        )
        file_be.save(expired_creds)

        result = store.refresh_if_needed(http_client=MagicMock())
        assert result is None

    def test_refresh_returns_none_when_http_fails(self, tmp_path):
        """refresh_if_needed() returns None when the refresh request fails."""
        store = self._expired_creds(tmp_path)

        mock_http = MagicMock()
        mock_http.post.side_effect = Exception("connection refused")

        env = {
            "SKILLMEAT_AUTH_ISSUER_URL": "https://auth.example.com",
            "SKILLMEAT_AUTH_CLIENT_ID": "test-client-id",
        }
        with patch.dict("os.environ", env, clear=False):
            result = store.refresh_if_needed(http_client=mock_http)

        assert result is None

    def test_refresh_keeps_old_refresh_token_when_server_does_not_rotate(self, tmp_path):
        """refresh_if_needed() retains the original refresh_token when server omits a new one."""
        store = self._expired_creds(tmp_path, refresh_token="original-refresh-tok")

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "access_token": "new-access",
            "token_type": "Bearer",
            # no refresh_token in response
        }
        mock_http = MagicMock()
        mock_http.post.return_value = mock_response

        env = {
            "SKILLMEAT_AUTH_ISSUER_URL": "https://auth.example.com",
            "SKILLMEAT_AUTH_CLIENT_ID": "test-client-id",
        }
        with patch.dict("os.environ", env, clear=False):
            new_creds = store.refresh_if_needed(http_client=mock_http)

        assert new_creds.refresh_token == "original-refresh-tok"


# ===========================================================================
# 8. Credential storage security
# ===========================================================================


class TestCredentialStorageSecurity:
    """Verify credentials file is written with secure permissions (mode 0600)."""

    def test_credentials_file_has_0600_permissions(self, tmp_path):
        """Stored credentials file should only be readable by the owner."""
        creds_path = tmp_path / ".skillmeat" / "credentials.json"
        file_be = _FileBackend(credentials_path=creds_path)
        store = CredentialStore(backend=file_be)

        store.store(_make_token_result())

        assert creds_path.exists()
        file_mode = creds_path.stat().st_mode
        # Only owner read/write (0o600); group and other must have no permissions
        assert not (file_mode & stat.S_IRGRP), "group read bit must not be set"
        assert not (file_mode & stat.S_IWGRP), "group write bit must not be set"
        assert not (file_mode & stat.S_IROTH), "other read bit must not be set"
        assert not (file_mode & stat.S_IWOTH), "other write bit must not be set"

    def test_credentials_file_is_valid_json(self, tmp_path):
        """Stored credentials file is a parseable JSON document."""
        creds_path = tmp_path / ".skillmeat" / "credentials.json"
        file_be = _FileBackend(credentials_path=creds_path)
        store = CredentialStore(backend=file_be)

        store.store(_make_token_result())

        raw = creds_path.read_text(encoding="utf-8")
        data = json.loads(raw)
        assert "access_token" in data
        assert data["access_token"] == "access-tok-xyz"

    def test_credentials_not_leaked_to_test_home(self, tmp_path):
        """CredentialStore with file backend writes only to the injected path."""
        creds_path = tmp_path / "isolated" / "credentials.json"
        file_be = _FileBackend(credentials_path=creds_path)
        store = CredentialStore(backend=file_be)

        store.store(_make_token_result())

        # Verify the file exists at the injected path
        assert creds_path.exists()

        # Verify nothing was written to the real ~/.skillmeat
        # (CliRunner's isolated_filesystem or tmp_path guarantees this)
        real_home_creds = Path.home() / ".skillmeat" / "credentials.json"
        # We cannot guarantee the real path doesn't exist (pre-existing),
        # but if it exists its content should not contain our test token.
        if real_home_creds.exists():
            content = real_home_creds.read_text(encoding="utf-8")
            assert "access-tok-xyz" not in content


# ===========================================================================
# 9. Token retrieval after storage
# ===========================================================================


class TestTokenRetrievalAfterStorage:
    """Round-trip: store credentials, load them back, verify correctness."""

    def test_store_and_load_access_token(self, file_backend, credential_store):
        """Stored access token is retrievable via load()."""
        credential_store.store(_make_token_result(access_token="my-access-token"))
        creds = credential_store.load()

        assert creds is not None
        assert creds.access_token == "my-access-token"

    def test_store_and_load_refresh_token(self, file_backend, credential_store):
        """Stored refresh token is retrievable via load()."""
        credential_store.store(_make_token_result(refresh_token="my-refresh-token"))
        creds = credential_store.load()

        assert creds.refresh_token == "my-refresh-token"

    def test_store_calculates_expires_at_from_expires_in(self, file_backend, credential_store):
        """expires_at is computed from expires_in at storage time."""
        before = time.time()
        credential_store.store(_make_token_result(expires_in=3600))
        after = time.time()

        creds = credential_store.load()
        assert creds.expires_at is not None
        assert before + 3600 <= creds.expires_at <= after + 3600

    def test_store_without_expires_in_sets_expires_at_none(self, file_backend, credential_store):
        """When DeviceCodeResult.expires_in is None, expires_at stays None."""
        credential_store.store(_make_token_result(expires_in=None))
        creds = credential_store.load()

        assert creds.expires_at is None

    def test_load_returns_none_before_any_store(self, file_backend, credential_store):
        """load() returns None when no credentials have been stored."""
        assert credential_store.load() is None

    def test_load_after_clear_returns_none(self, file_backend, credential_store):
        """load() returns None after clear() removes stored credentials."""
        credential_store.store(_make_token_result())
        credential_store.clear()
        assert credential_store.load() is None

    def test_token_type_is_preserved(self, file_backend, credential_store):
        """token_type stored in DeviceCodeResult is round-tripped correctly."""
        credential_store.store(_make_token_result(token_type="Bearer"))
        creds = credential_store.load()
        assert creds.token_type == "Bearer"


# ===========================================================================
# 10. Auth status
# ===========================================================================


class TestAuthStatus:
    """CredentialStore.is_authenticated() lifecycle behaviour."""

    def test_not_authenticated_when_nothing_stored(self, credential_store):
        """is_authenticated() returns False before any credentials are stored."""
        assert credential_store.is_authenticated() is False

    def test_authenticated_after_storing_valid_token(self, credential_store):
        """is_authenticated() returns True after storing non-expired credentials."""
        credential_store.store(_make_token_result(expires_in=3600))
        assert credential_store.is_authenticated() is True

    def test_authenticated_when_no_expiry_set(self, credential_store):
        """is_authenticated() returns True when expires_at is None (no expiry)."""
        credential_store.store(_make_token_result(expires_in=None))
        assert credential_store.is_authenticated() is True

    def test_not_authenticated_after_logout(self, credential_store):
        """is_authenticated() returns False after credentials are cleared."""
        credential_store.store(_make_token_result(expires_in=3600))
        credential_store.clear()
        assert credential_store.is_authenticated() is False

    def test_not_authenticated_when_token_expired(self, file_backend):
        """is_authenticated() returns False when the stored access token has expired."""
        store = CredentialStore(backend=file_backend)
        expired_creds = StoredCredentials(
            access_token="expired-tok",
            token_type="Bearer",
            expires_at=time.time() - 1000,  # expired 1000s ago
            stored_at=time.time() - 2000,
        )
        file_backend.save(expired_creds)
        assert store.is_authenticated() is False

    def test_is_authenticated_respects_expiry_buffer(self, file_backend):
        """is_authenticated() returns False when within the 30s expiry buffer."""
        store = CredentialStore(backend=file_backend)
        # expires_at is 20s in the future but within the 30s buffer
        near_expiry_creds = StoredCredentials(
            access_token="almost-expired",
            token_type="Bearer",
            expires_at=time.time() + 20,  # 20s left (< 30s buffer)
            stored_at=time.time() - 3600,
        )
        file_backend.save(near_expiry_creds)
        assert store.is_authenticated() is False


# ===========================================================================
# Internal helpers — _run_device_code_flow
# ===========================================================================


class TestRunDeviceCodeFlowHelper:
    """Tests for the internal _run_device_code_flow helper (separated for testability)."""

    def test_run_device_code_flow_calls_flow_start_and_poll(self, tmp_path):
        """_run_device_code_flow calls DeviceCodeFlow.start() then poll()."""
        config = _make_auth_config()

        mock_flow = MagicMock()
        mock_flow.start.return_value = _make_device_auth_response()
        mock_flow.poll.return_value = _make_token_result()

        mock_store = MagicMock()
        mock_store.backend_name = "file"

        with patch(
            "skillmeat.cli.commands.auth.DeviceCodeFlow", return_value=mock_flow
        ):
            _run_device_code_flow(
                config,
                no_browser=True,
                timeout=60,
                credential_store=mock_store,
            )

        mock_flow.start.assert_called_once()
        mock_flow.poll.assert_called_once()
        mock_store.store.assert_called_once()

    def test_run_device_code_flow_stores_token_result(self, tmp_path):
        """_run_device_code_flow passes the DeviceCodeResult to CredentialStore.store()."""
        config = _make_auth_config()
        token = _make_token_result(access_token="injected-access-token")

        mock_flow = MagicMock()
        mock_flow.start.return_value = _make_device_auth_response()
        mock_flow.poll.return_value = token

        mock_store = MagicMock()
        mock_store.backend_name = "file"

        with patch(
            "skillmeat.cli.commands.auth.DeviceCodeFlow", return_value=mock_flow
        ):
            _run_device_code_flow(
                config,
                no_browser=True,
                timeout=60,
                credential_store=mock_store,
            )

        mock_store.store.assert_called_once_with(token)

    def test_run_device_code_flow_skips_browser_when_no_browser(self):
        """_run_device_code_flow does not call webbrowser.open when no_browser=True."""
        config = _make_auth_config()

        mock_flow = MagicMock()
        mock_flow.start.return_value = _make_device_auth_response()
        mock_flow.poll.return_value = _make_token_result()

        mock_store = MagicMock()
        mock_store.backend_name = "file"

        with patch("skillmeat.cli.commands.auth.DeviceCodeFlow", return_value=mock_flow):
            with patch("webbrowser.open") as mock_browser:
                _run_device_code_flow(
                    config,
                    no_browser=True,
                    timeout=60,
                    credential_store=mock_store,
                )

        mock_browser.assert_not_called()

    def test_run_device_code_flow_attempts_browser_when_no_browser_false(self):
        """_run_device_code_flow attempts webbrowser.open when no_browser=False."""
        config = _make_auth_config()

        mock_flow = MagicMock()
        mock_flow.start.return_value = _make_device_auth_response()
        mock_flow.poll.return_value = _make_token_result()

        mock_store = MagicMock()
        mock_store.backend_name = "file"

        with patch("skillmeat.cli.commands.auth.DeviceCodeFlow", return_value=mock_flow):
            with patch("webbrowser.open", return_value=True) as mock_browser:
                _run_device_code_flow(
                    config,
                    no_browser=False,
                    timeout=60,
                    credential_store=mock_store,
                )

        mock_browser.assert_called_once()
