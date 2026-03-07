"""Integration tests for the SkillMeat CLI auth system.

Covers:
- DeviceCodeFlow: start() and poll() with mocked HTTP responses
- CredentialStore: file-backend round-trips, expiry, permissions
- StoredCredentials.is_expired property
- CredentialStore.refresh_if_needed(): valid, expired+refresh, no-refresh-token, HTTP error
- AuthenticatedClient: auth header injection, local mode, expired token refresh
- Click commands: ``auth token`` and ``auth logout``

These tests make NO real network calls.  All HTTP is mocked via
``unittest.mock`` or ``httpx`` transports.

NOTE: Zero-auth / local-mode scenarios are already covered in
``tests/test_cli_zero_auth.py`` — they are not duplicated here.
"""

from __future__ import annotations

import json
import os
import platform
import stat
import time
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

import httpx
import pytest
from click.testing import CliRunner
from rich.console import Console

from skillmeat.cli.auth_flow import (
    AuthConfig,
    DeviceAuthResponse,
    DeviceCodeAccessDeniedError,
    DeviceCodeConfigError,
    DeviceCodeExpiredError,
    DeviceCodeFlow,
    DeviceCodeFlowError,
    DeviceCodeResult,
    DeviceCodeTimeoutError,
)
from skillmeat.cli.commands.auth import auth_cli
from skillmeat.cli.credential_store import (
    CredentialStore,
    StoredCredentials,
    _FileBackend,
)
from skillmeat.cli.http_client import AuthenticatedClient


# ---------------------------------------------------------------------------
# Helpers / shared fixtures
# ---------------------------------------------------------------------------


def _make_http_response(status_code: int, body: dict) -> MagicMock:
    """Build a MagicMock that looks like an httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.is_success = 200 <= status_code < 300
    resp.json.return_value = body
    # raise_for_status only raises when status >= 400
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status_code}",
            request=MagicMock(),
            response=resp,
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


def _make_device_auth_response(**kwargs) -> DeviceAuthResponse:
    defaults = dict(
        device_code="device-code-abc",
        user_code="WXYZ-1234",
        verification_uri="https://example.com/activate",
        expires_in=300,
        interval=5,
    )
    defaults.update(kwargs)
    return DeviceAuthResponse(**defaults)


def _make_device_code_result(**kwargs) -> DeviceCodeResult:
    defaults = dict(
        access_token="at-token-xyz",
        refresh_token="rt-token-abc",
        expires_in=3600,
        token_type="Bearer",
    )
    defaults.update(kwargs)
    return DeviceCodeResult(**defaults)


def _make_stored_credentials(**kwargs) -> StoredCredentials:
    defaults = dict(
        access_token="at-stored",
        token_type="Bearer",
        stored_at=time.time(),
        refresh_token="rt-stored",
        expires_at=time.time() + 3600,
    )
    defaults.update(kwargs)
    return StoredCredentials(**defaults)


@pytest.fixture()
def auth_config() -> AuthConfig:
    """A fully configured AuthConfig pointing at a fake issuer."""
    return AuthConfig(
        issuer_url="https://auth.example.com",
        client_id="client-test-id",
        audience=None,
        scope="openid profile email",
    )


@pytest.fixture()
def mock_http() -> MagicMock:
    """A mock httpx.Client-compatible object."""
    return MagicMock()


@pytest.fixture()
def cli_runner(tmp_path, monkeypatch) -> CliRunner:
    """Isolated CliRunner with patched HOME and plain Rich console."""
    home_dir = tmp_path / "home"
    home_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home_dir))

    from skillmeat.config import ConfigManager
    monkeypatch.setattr(ConfigManager, "DEFAULT_CONFIG_DIR", home_dir / ".skillmeat")

    import skillmeat.cli as cli_module
    monkeypatch.setattr(cli_module, "console", Console(no_color=True, highlight=False))

    # Patch the auth module's console too so ANSI doesn't pollute assertions.
    import skillmeat.cli.commands.auth as auth_module
    monkeypatch.setattr(auth_module, "console", Console(no_color=True, highlight=False))

    return CliRunner()


@pytest.fixture()
def file_backend(tmp_path) -> _FileBackend:
    """A _FileBackend pointing at a tmp directory."""
    creds_file = tmp_path / ".skillmeat" / "credentials.json"
    return _FileBackend(credentials_path=creds_file)


@pytest.fixture()
def file_store(file_backend) -> CredentialStore:
    """A CredentialStore backed by the file_backend fixture."""
    return CredentialStore(backend=file_backend)


# ---------------------------------------------------------------------------
# Section 1: DeviceCodeFlow.start()
# ---------------------------------------------------------------------------


class TestDeviceCodeFlowStart:
    """Tests for DeviceCodeFlow.start()."""

    def test_start_returns_device_auth_response(self, auth_config, mock_http):
        body = {
            "device_code": "dev-code-1",
            "user_code": "ABCD-5678",
            "verification_uri": "https://auth.example.com/activate",
            "verification_uri_complete": "https://auth.example.com/activate?code=ABCD-5678",
            "expires_in": 600,
            "interval": 10,
        }
        mock_http.post.return_value = _make_http_response(200, body)

        flow = DeviceCodeFlow(auth_config, http_client=mock_http)
        result = flow.start()

        assert result.device_code == "dev-code-1"
        assert result.user_code == "ABCD-5678"
        assert result.verification_uri == "https://auth.example.com/activate"
        assert result.verification_uri_complete == "https://auth.example.com/activate?code=ABCD-5678"
        assert result.expires_in == 600
        assert result.interval == 10

    def test_start_posts_to_device_authorization_endpoint(self, auth_config, mock_http):
        body = {
            "device_code": "dc",
            "user_code": "UC",
            "verification_uri": "https://auth.example.com/activate",
            "expires_in": 300,
            "interval": 5,
        }
        mock_http.post.return_value = _make_http_response(200, body)

        flow = DeviceCodeFlow(auth_config, http_client=mock_http)
        flow.start()

        call_args = mock_http.post.call_args
        assert call_args[0][0] == "https://auth.example.com/oauth/device/authorize"

    def test_start_includes_scope_in_payload(self, auth_config, mock_http):
        body = {
            "device_code": "dc",
            "user_code": "UC",
            "verification_uri": "https://auth.example.com/activate",
            "expires_in": 300,
            "interval": 5,
        }
        mock_http.post.return_value = _make_http_response(200, body)

        flow = DeviceCodeFlow(auth_config, http_client=mock_http)
        flow.start()

        call_kwargs = mock_http.post.call_args[1]
        payload = call_kwargs["data"]
        assert payload["client_id"] == "client-test-id"
        assert "openid" in payload["scope"]

    def test_start_includes_audience_when_set(self, mock_http):
        config = AuthConfig(
            issuer_url="https://auth.example.com",
            client_id="cid",
            audience="https://api.example.com",
        )
        body = {
            "device_code": "dc",
            "user_code": "UC",
            "verification_uri": "https://auth.example.com/activate",
            "expires_in": 300,
            "interval": 5,
        }
        mock_http.post.return_value = _make_http_response(200, body)

        flow = DeviceCodeFlow(config, http_client=mock_http)
        flow.start()

        payload = mock_http.post.call_args[1]["data"]
        assert payload.get("audience") == "https://api.example.com"

    def test_start_raises_config_error_when_not_configured(self, mock_http):
        config = AuthConfig(issuer_url="", client_id="")

        flow = DeviceCodeFlow(config, http_client=mock_http)

        with pytest.raises(DeviceCodeConfigError) as exc_info:
            flow.start()

        assert "SKILLMEAT_AUTH_ISSUER_URL" in str(exc_info.value)
        mock_http.post.assert_not_called()

    def test_start_raises_config_error_when_client_id_missing(self, mock_http):
        config = AuthConfig(issuer_url="https://auth.example.com", client_id="")

        flow = DeviceCodeFlow(config, http_client=mock_http)

        with pytest.raises(DeviceCodeConfigError):
            flow.start()

    def test_start_uses_default_interval_when_absent(self, auth_config, mock_http):
        body = {
            "device_code": "dc",
            "user_code": "UC",
            "verification_uri": "https://v.example.com",
            "expires_in": 300,
            # no "interval" key
        }
        mock_http.post.return_value = _make_http_response(200, body)

        flow = DeviceCodeFlow(auth_config, http_client=mock_http)
        result = flow.start()

        assert result.interval == 5  # default


# ---------------------------------------------------------------------------
# Section 2: DeviceCodeFlow.poll()
# ---------------------------------------------------------------------------


class TestDeviceCodeFlowPoll:
    """Tests for DeviceCodeFlow.poll() covering all RFC 8628 outcomes."""

    def _make_flow(self, auth_config, mock_http):
        return DeviceCodeFlow(auth_config, http_client=mock_http)

    def test_immediate_success(self, auth_config, mock_http):
        """First poll returns tokens — flow completes immediately."""
        token_body = {
            "access_token": "at-success",
            "refresh_token": "rt-success",
            "expires_in": 3600,
            "token_type": "Bearer",
            "id_token": "idt-success",
        }
        mock_http.post.return_value = _make_http_response(200, token_body)

        flow = self._make_flow(auth_config, mock_http)
        device_auth = _make_device_auth_response()

        with patch("time.sleep"), patch("time.monotonic", side_effect=[0.0, 0.0, 0.0, 0.0]):
            result = flow.poll(device_auth, timeout=60.0)

        assert result.access_token == "at-success"
        assert result.refresh_token == "rt-success"
        assert result.expires_in == 3600
        assert result.id_token == "idt-success"

    def test_success_after_authorization_pending(self, auth_config, mock_http):
        """Two ``authorization_pending`` responses, then success."""
        pending_resp = _make_http_response(400, {"error": "authorization_pending"})
        success_resp = _make_http_response(200, {
            "access_token": "at-ok",
            "token_type": "Bearer",
        })
        mock_http.post.side_effect = [pending_resp, pending_resp, success_resp]

        flow = self._make_flow(auth_config, mock_http)
        device_auth = _make_device_auth_response(interval=1)

        # Monotonic: each loop checks deadline twice + once before sleep.
        # Provide enough values so no timeout fires during the 3-poll sequence.
        monotonic_vals = [0.0] * 20
        with patch("time.sleep") as mock_sleep, patch("time.monotonic", side_effect=monotonic_vals):
            result = flow.poll(device_auth, timeout=300.0)

        assert result.access_token == "at-ok"
        assert mock_sleep.call_count == 3

    def test_slow_down_increases_interval(self, auth_config, mock_http):
        """``slow_down`` response causes the polling interval to increase by 5s."""
        slow_down_resp = _make_http_response(400, {"error": "slow_down"})
        success_resp = _make_http_response(200, {
            "access_token": "at-after-slowdown",
            "token_type": "Bearer",
        })
        mock_http.post.side_effect = [slow_down_resp, success_resp]

        flow = self._make_flow(auth_config, mock_http)
        device_auth = _make_device_auth_response(interval=5)

        sleep_calls = []
        monotonic_vals = [0.0] * 20

        with patch("time.sleep", side_effect=lambda s: sleep_calls.append(s)), \
             patch("time.monotonic", side_effect=monotonic_vals):
            result = flow.poll(device_auth, timeout=300.0)

        assert result.access_token == "at-after-slowdown"
        # First sleep: original interval (5s); second sleep: 5 + 5 = 10s.
        assert len(sleep_calls) == 2
        assert sleep_calls[0] == 5.0
        assert sleep_calls[1] == 10.0

    def test_expired_token_raises(self, auth_config, mock_http):
        """``expired_token`` error raises DeviceCodeExpiredError."""
        mock_http.post.return_value = _make_http_response(400, {"error": "expired_token"})

        flow = self._make_flow(auth_config, mock_http)
        device_auth = _make_device_auth_response()

        with pytest.raises(DeviceCodeExpiredError):
            with patch("time.sleep"), patch("time.monotonic", side_effect=[0.0] * 20):
                flow.poll(device_auth, timeout=60.0)

    def test_access_denied_raises(self, auth_config, mock_http):
        """``access_denied`` error raises DeviceCodeAccessDeniedError."""
        mock_http.post.return_value = _make_http_response(400, {"error": "access_denied"})

        flow = self._make_flow(auth_config, mock_http)
        device_auth = _make_device_auth_response()

        with pytest.raises(DeviceCodeAccessDeniedError):
            with patch("time.sleep"), patch("time.monotonic", side_effect=[0.0] * 20):
                flow.poll(device_auth, timeout=60.0)

    def test_timeout_raises_before_first_poll(self, auth_config, mock_http):
        """When deadline has already passed at the first loop check, raises DeviceCodeTimeoutError."""
        flow = self._make_flow(auth_config, mock_http)
        device_auth = _make_device_auth_response()

        # deadline = monotonic()[0] + timeout = 0.0 + 1.0 = 1.0
        # First loop check: monotonic()[1] = 5.0 >= 1.0 → raises immediately.
        monotonic_vals = [0.0, 5.0]
        with pytest.raises(DeviceCodeTimeoutError):
            with patch("time.sleep"), patch("time.monotonic", side_effect=monotonic_vals):
                flow.poll(device_auth, timeout=1.0)

        # No token poll should have been made.
        mock_http.post.assert_not_called()

    def test_timeout_raises_after_sleep(self, auth_config, mock_http):
        """Deadline expires after the sleep but before polling → DeviceCodeTimeoutError."""
        flow = self._make_flow(auth_config, mock_http)
        device_auth = _make_device_auth_response(interval=5)

        # First deadline check (before sleep): not expired.
        # Second deadline check (after sleep): expired.
        monotonic_vals = [0.0, 9999.0]

        with pytest.raises(DeviceCodeTimeoutError):
            with patch("time.sleep"), patch("time.monotonic", side_effect=monotonic_vals):
                flow.poll(device_auth, timeout=1.0)

        mock_http.post.assert_not_called()

    def test_unknown_error_raises_flow_error(self, auth_config, mock_http):
        """An unrecognised error string from the token endpoint raises DeviceCodeFlowError."""
        mock_http.post.return_value = _make_http_response(400, {"error": "some_other_error"})

        flow = self._make_flow(auth_config, mock_http)
        device_auth = _make_device_auth_response()

        with pytest.raises(DeviceCodeFlowError) as exc_info:
            with patch("time.sleep"), patch("time.monotonic", side_effect=[0.0] * 20):
                flow.poll(device_auth, timeout=60.0)

        assert "some_other_error" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Section 3: StoredCredentials.is_expired
# ---------------------------------------------------------------------------


class TestStoredCredentialsIsExpired:
    """Unit tests for the is_expired property."""

    def test_not_expired_when_expires_at_in_future(self):
        creds = _make_stored_credentials(expires_at=time.time() + 7200)
        assert creds.is_expired is False

    def test_expired_when_expires_at_in_past(self):
        creds = _make_stored_credentials(expires_at=time.time() - 1.0)
        assert creds.is_expired is True

    def test_expired_includes_buffer(self):
        # expires_at is 20 seconds in the future but within the 30s buffer.
        creds = _make_stored_credentials(expires_at=time.time() + 20)
        assert creds.is_expired is True

    def test_not_expired_when_expires_at_is_none(self):
        """PATs have no expiry — is_expired is always False."""
        creds = _make_stored_credentials(expires_at=None)
        assert creds.is_expired is False


# ---------------------------------------------------------------------------
# Section 4: CredentialStore with file backend
# ---------------------------------------------------------------------------


class TestCredentialStoreFileBackend:
    """Integration tests for CredentialStore using the _FileBackend."""

    def test_store_and_load_round_trip(self, file_store):
        result = _make_device_code_result()
        file_store.store(result)

        loaded = file_store.load()
        assert loaded is not None
        assert loaded.access_token == "at-token-xyz"
        assert loaded.refresh_token == "rt-token-abc"
        assert loaded.token_type == "Bearer"

    def test_is_authenticated_true_after_store(self, file_store):
        file_store.store(_make_device_code_result(expires_in=3600))
        assert file_store.is_authenticated() is True

    def test_is_authenticated_false_before_store(self, file_store):
        assert file_store.is_authenticated() is False

    def test_clear_removes_credentials(self, file_store):
        file_store.store(_make_device_code_result())
        assert file_store.is_authenticated() is True

        file_store.clear()
        assert file_store.is_authenticated() is False

    def test_load_returns_none_after_clear(self, file_store):
        file_store.store(_make_device_code_result())
        file_store.clear()
        assert file_store.load() is None

    def test_is_authenticated_false_for_expired_credentials(self, file_store):
        """Storing a result with expires_in=0 results in an immediately-expired credential."""
        # Use a negative expires_in equivalent: manually set stored_at far in the past.
        result = _make_device_code_result(expires_in=1)  # 1 second

        # Store credentials first.
        file_store.store(result)

        # Now patch time.time so the credential appears expired.
        with patch("time.time", return_value=time.time() + 10000):
            assert file_store.is_authenticated() is False

    @pytest.mark.skipif(platform.system() == "Windows", reason="File permissions not applicable on Windows")
    def test_credentials_file_has_0600_permissions(self, file_backend, file_store):
        file_store.store(_make_device_code_result())

        mode = file_backend._path.stat().st_mode
        permissions = stat.S_IMODE(mode)
        assert permissions == 0o600, f"Expected 0600, got {oct(permissions)}"

    def test_expires_at_calculated_from_expires_in(self, file_store):
        before = time.time()
        file_store.store(_make_device_code_result(expires_in=3600))
        after = time.time()

        loaded = file_store.load()
        assert loaded is not None
        assert loaded.expires_at is not None
        # expires_at should be approximately now + 3600.
        assert before + 3600 <= loaded.expires_at <= after + 3600

    def test_expires_at_is_none_when_no_expires_in(self, file_store):
        file_store.store(_make_device_code_result(expires_in=None))
        loaded = file_store.load()
        assert loaded is not None
        assert loaded.expires_at is None

    def test_stored_at_is_set(self, file_store):
        before = time.time()
        file_store.store(_make_device_code_result())
        after = time.time()

        loaded = file_store.load()
        assert loaded is not None
        assert before <= loaded.stored_at <= after


# ---------------------------------------------------------------------------
# Section 5: CredentialStore.refresh_if_needed()
# ---------------------------------------------------------------------------


class TestRefreshIfNeeded:
    """Tests for the refresh_if_needed() logic."""

    def test_returns_valid_credentials_unchanged(self, file_store):
        """When credentials are still valid, they are returned without a refresh call."""
        file_store.store(_make_device_code_result(expires_in=3600))

        mock_http = MagicMock()
        result = file_store.refresh_if_needed(http_client=mock_http)

        assert result is not None
        assert result.access_token == "at-token-xyz"
        mock_http.post.assert_not_called()

    def test_returns_none_when_no_credentials(self, file_store):
        result = file_store.refresh_if_needed(http_client=MagicMock())
        assert result is None

    def test_returns_none_when_expired_and_no_refresh_token(self, file_store):
        """Expired credential without a refresh_token → None, no HTTP call."""
        # Manually save expired credentials with no refresh_token.
        expired_creds = _make_stored_credentials(
            expires_at=time.time() - 100,
            refresh_token=None,
        )
        file_store._backend.save(expired_creds)

        mock_http = MagicMock()
        result = file_store.refresh_if_needed(http_client=mock_http)

        assert result is None
        mock_http.post.assert_not_called()

    def test_refreshes_expired_token_and_stores_new_credentials(self, file_store, monkeypatch):
        """Expired token + refresh_token → HTTP refresh → new credentials stored."""
        # Save expired credentials with a refresh token.
        expired_creds = _make_stored_credentials(
            access_token="old-at",
            refresh_token="rt-valid",
            expires_at=time.time() - 100,
        )
        file_store._backend.save(expired_creds)

        new_token_body = {
            "access_token": "new-at",
            "refresh_token": "new-rt",
            "expires_in": 7200,
            "token_type": "Bearer",
        }
        mock_http = MagicMock()
        mock_http.post.return_value = _make_http_response(200, new_token_body)

        # Provide issuer/client env vars so AuthConfig is configured.
        monkeypatch.setenv("SKILLMEAT_AUTH_ISSUER_URL", "https://auth.example.com")
        monkeypatch.setenv("SKILLMEAT_AUTH_CLIENT_ID", "client-id")

        result = file_store.refresh_if_needed(http_client=mock_http)

        assert result is not None
        assert result.access_token == "new-at"
        assert result.refresh_token == "new-rt"

        # Persisted credentials should reflect the new token.
        persisted = file_store.load()
        assert persisted is not None
        assert persisted.access_token == "new-at"

    def test_returns_none_on_http_error_during_refresh(self, file_store, monkeypatch):
        """HTTP failure during refresh is caught and None is returned (graceful)."""
        expired_creds = _make_stored_credentials(
            access_token="old-at",
            refresh_token="rt-valid",
            expires_at=time.time() - 100,
        )
        file_store._backend.save(expired_creds)

        mock_http = MagicMock()
        mock_http.post.side_effect = httpx.ConnectError("network unreachable")

        monkeypatch.setenv("SKILLMEAT_AUTH_ISSUER_URL", "https://auth.example.com")
        monkeypatch.setenv("SKILLMEAT_AUTH_CLIENT_ID", "client-id")

        result = file_store.refresh_if_needed(http_client=mock_http)

        assert result is None

    def test_returns_none_when_auth_not_configured_for_refresh(self, file_store, monkeypatch):
        """Expired token but no auth config → None (cannot call token endpoint)."""
        expired_creds = _make_stored_credentials(
            refresh_token="rt-valid",
            expires_at=time.time() - 100,
        )
        file_store._backend.save(expired_creds)

        # No issuer/client vars.
        monkeypatch.delenv("SKILLMEAT_AUTH_ISSUER_URL", raising=False)
        monkeypatch.delenv("SKILLMEAT_AUTH_CLIENT_ID", raising=False)

        with patch("skillmeat.api.config.get_settings", side_effect=Exception("not available")):
            result = file_store.refresh_if_needed(http_client=MagicMock())

        assert result is None


# ---------------------------------------------------------------------------
# Section 6: AuthenticatedClient
# ---------------------------------------------------------------------------


class TestAuthenticatedClient:
    """Tests for AuthenticatedClient request behaviour."""

    def _make_client(self, store: CredentialStore, local_mode: bool = False) -> AuthenticatedClient:
        inner_http = MagicMock(spec=httpx.Client)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        inner_http.request.return_value = mock_response

        with patch("skillmeat.cli.http_client.is_local_mode", return_value=local_mode):
            client = AuthenticatedClient(
                base_url="http://localhost:8080",
                credential_store=store,
                http_client=inner_http,
            )
        client._inner_http = inner_http
        client._local_mode_flag = local_mode
        return client

    def test_adds_authorization_header_when_credentials_exist(self, file_store):
        """Requests include Authorization: Bearer when valid credentials are stored."""
        file_store.store(_make_device_code_result(expires_in=3600))

        inner_http = MagicMock(spec=httpx.Client)
        inner_http.request.return_value = MagicMock(spec=httpx.Response)

        with patch("skillmeat.cli.http_client.is_local_mode", return_value=False):
            client = AuthenticatedClient(
                base_url="http://localhost:8080",
                credential_store=file_store,
                http_client=inner_http,
            )
            client.get("/api/v1/health")

        call_kwargs = inner_http.request.call_args[1]
        headers = call_kwargs.get("headers", {})
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Bearer ")

    def test_no_auth_header_in_local_mode(self, file_store):
        """In local mode, no Authorization header is added even with stored credentials."""
        file_store.store(_make_device_code_result(expires_in=3600))

        inner_http = MagicMock(spec=httpx.Client)
        inner_http.request.return_value = MagicMock(spec=httpx.Response)

        with patch("skillmeat.cli.http_client.is_local_mode", return_value=True):
            client = AuthenticatedClient(
                base_url="http://localhost:8080",
                credential_store=file_store,
                http_client=inner_http,
            )
            client.get("/api/v1/health")

        call_kwargs = inner_http.request.call_args[1]
        headers = call_kwargs.get("headers", {})
        assert "Authorization" not in headers

    def test_no_auth_header_when_no_credentials_stored(self, file_store):
        """Requests have no Authorization header when credential store is empty."""
        inner_http = MagicMock(spec=httpx.Client)
        inner_http.request.return_value = MagicMock(spec=httpx.Response)

        with patch("skillmeat.cli.http_client.is_local_mode", return_value=False):
            client = AuthenticatedClient(
                base_url="http://localhost:8080",
                credential_store=file_store,
                http_client=inner_http,
            )
            client.get("/api/v1/health")

        call_kwargs = inner_http.request.call_args[1]
        headers = call_kwargs.get("headers", {})
        assert "Authorization" not in headers

    def test_refreshes_expired_token_before_request(self, file_store, monkeypatch):
        """Expired access token is refreshed transparently before the request is sent."""
        expired_creds = _make_stored_credentials(
            access_token="old-at",
            refresh_token="rt-valid",
            expires_at=time.time() - 100,
        )
        file_store._backend.save(expired_creds)

        new_token_body = {
            "access_token": "refreshed-at",
            "refresh_token": "rt-new",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        refresh_http = MagicMock()
        refresh_http.post.return_value = _make_http_response(200, new_token_body)

        monkeypatch.setenv("SKILLMEAT_AUTH_ISSUER_URL", "https://auth.example.com")
        monkeypatch.setenv("SKILLMEAT_AUTH_CLIENT_ID", "client-id")

        inner_http = MagicMock(spec=httpx.Client)
        inner_http.request.return_value = MagicMock(spec=httpx.Response)

        # Patch CredentialStore.refresh_if_needed to use our controlled http client.
        original_refresh = CredentialStore.refresh_if_needed

        def controlled_refresh(self_store, http_client=None):
            return original_refresh(self_store, http_client=refresh_http)

        with patch("skillmeat.cli.http_client.is_local_mode", return_value=False), \
             patch.object(CredentialStore, "refresh_if_needed", controlled_refresh):
            client = AuthenticatedClient(
                base_url="http://localhost:8080",
                credential_store=file_store,
                http_client=inner_http,
            )
            client.get("/api/v1/artifacts")

        call_kwargs = inner_http.request.call_args[1]
        headers = call_kwargs.get("headers", {})
        assert "Authorization" in headers
        assert "refreshed-at" in headers["Authorization"]

    def test_build_url_prepends_base_url(self, file_store):
        inner_http = MagicMock(spec=httpx.Client)
        inner_http.request.return_value = MagicMock(spec=httpx.Response)

        with patch("skillmeat.cli.http_client.is_local_mode", return_value=True):
            client = AuthenticatedClient(
                base_url="http://localhost:9090",
                credential_store=file_store,
                http_client=inner_http,
            )
            client.get("/api/v1/health")

        call_args = inner_http.request.call_args
        url = call_args[0][1]
        assert url == "http://localhost:9090/api/v1/health"

    def test_absolute_url_not_prepended(self, file_store):
        inner_http = MagicMock(spec=httpx.Client)
        inner_http.request.return_value = MagicMock(spec=httpx.Response)

        with patch("skillmeat.cli.http_client.is_local_mode", return_value=True):
            client = AuthenticatedClient(
                base_url="http://localhost:9090",
                credential_store=file_store,
                http_client=inner_http,
            )
            client.get("https://other.example.com/api")

        call_args = inner_http.request.call_args
        url = call_args[0][1]
        assert url == "https://other.example.com/api"


# ---------------------------------------------------------------------------
# Section 7: Click command: auth token
# ---------------------------------------------------------------------------


class TestAuthTokenCommand:
    """Tests for ``skillmeat auth token <PAT>``."""

    def test_stores_pat_successfully(self, cli_runner, tmp_path, monkeypatch):
        """auth token <PAT> stores credentials and prints success."""
        creds_file = tmp_path / "home" / ".skillmeat" / "credentials.json"
        file_be = _FileBackend(credentials_path=creds_file)
        mock_store = CredentialStore(backend=file_be)

        monkeypatch.setenv("SKILLMEAT_AUTH_MODE", "clerk")
        monkeypatch.setenv("SKILLMEAT_AUTH_ISSUER_URL", "https://auth.example.com")
        monkeypatch.setenv("SKILLMEAT_AUTH_CLIENT_ID", "client-id")

        with patch("skillmeat.cli.commands.auth.CredentialStore", return_value=mock_store), \
             patch("skillmeat.cli.commands.auth._is_local_mode", return_value=False):
            result = cli_runner.invoke(auth_cli, ["token", "sk_test_my_personal_token"])

        assert result.exit_code == 0, result.output
        loaded = mock_store.load()
        assert loaded is not None
        assert loaded.access_token == "sk_test_my_personal_token"

    def test_token_prints_success_message(self, cli_runner, tmp_path, monkeypatch):
        """auth token prints a success panel."""
        creds_file = tmp_path / "home" / ".skillmeat" / "credentials.json"
        mock_store = CredentialStore(backend=_FileBackend(credentials_path=creds_file))

        with patch("skillmeat.cli.commands.auth.CredentialStore", return_value=mock_store), \
             patch("skillmeat.cli.commands.auth._is_local_mode", return_value=False):
            result = cli_runner.invoke(auth_cli, ["token", "sk_test_abc"])

        assert result.exit_code == 0
        assert "stored" in result.output.lower() or "success" in result.output.lower(), (
            f"Expected success message in output, got:\n{result.output}"
        )

    def test_token_in_local_mode_prints_info_and_exits_0(self, cli_runner, monkeypatch):
        """In local mode, auth token prints info message and exits 0 without storing."""
        mock_store = MagicMock(spec=CredentialStore)

        with patch("skillmeat.cli.commands.auth.CredentialStore", return_value=mock_store), \
             patch("skillmeat.cli.commands.auth._is_local_mode", return_value=True):
            result = cli_runner.invoke(auth_cli, ["token", "sk_test_abc"])

        assert result.exit_code == 0
        output_lower = result.output.lower()
        assert "local" in output_lower or "not required" in output_lower or "zero-auth" in output_lower, (
            f"Expected local-mode info in output, got:\n{result.output}"
        )
        mock_store.store.assert_not_called()

    def test_stored_pat_has_no_expires_at(self, cli_runner, tmp_path, monkeypatch):
        """PATs stored via auth token should have no expiry (expires_at=None)."""
        creds_file = tmp_path / "home" / ".skillmeat" / "credentials.json"
        mock_store = CredentialStore(backend=_FileBackend(credentials_path=creds_file))

        with patch("skillmeat.cli.commands.auth.CredentialStore", return_value=mock_store), \
             patch("skillmeat.cli.commands.auth._is_local_mode", return_value=False):
            cli_runner.invoke(auth_cli, ["token", "sk_test_neverexpires"])

        loaded = mock_store.load()
        assert loaded is not None
        assert loaded.expires_at is None


# ---------------------------------------------------------------------------
# Section 8: Click command: auth logout
# ---------------------------------------------------------------------------


class TestAuthLogoutCommand:
    """Tests for ``skillmeat auth logout``."""

    def test_logout_clears_credentials(self, cli_runner, tmp_path):
        """auth logout removes stored credentials."""
        creds_file = tmp_path / "home" / ".skillmeat" / "credentials.json"
        mock_store = CredentialStore(backend=_FileBackend(credentials_path=creds_file))

        # Pre-store credentials.
        mock_store.store(_make_device_code_result(expires_in=3600))
        assert mock_store.is_authenticated() is True

        with patch("skillmeat.cli.commands.auth.CredentialStore", return_value=mock_store):
            result = cli_runner.invoke(auth_cli, ["logout"])

        assert result.exit_code == 0, result.output
        assert mock_store.is_authenticated() is False

    def test_logout_prints_success_message(self, cli_runner, tmp_path):
        """auth logout prints a success/logout panel."""
        creds_file = tmp_path / "home" / ".skillmeat" / "credentials.json"
        mock_store = CredentialStore(backend=_FileBackend(credentials_path=creds_file))

        with patch("skillmeat.cli.commands.auth.CredentialStore", return_value=mock_store):
            result = cli_runner.invoke(auth_cli, ["logout"])

        assert result.exit_code == 0
        output_lower = result.output.lower()
        assert "logout" in output_lower or "logged out" in output_lower or "cleared" in output_lower, (
            f"Expected logout message in output, got:\n{result.output}"
        )

    def test_logout_succeeds_when_not_logged_in(self, cli_runner, tmp_path):
        """auth logout is safe to call when no credentials are stored."""
        creds_file = tmp_path / "home" / ".skillmeat" / "credentials.json"
        mock_store = CredentialStore(backend=_FileBackend(credentials_path=creds_file))

        # No credentials stored — clear() should still succeed.
        assert mock_store.is_authenticated() is False

        with patch("skillmeat.cli.commands.auth.CredentialStore", return_value=mock_store):
            result = cli_runner.invoke(auth_cli, ["logout"])

        assert result.exit_code == 0, result.output

    def test_logout_then_is_authenticated_false(self, cli_runner, tmp_path):
        """After logout, is_authenticated() always returns False."""
        creds_file = tmp_path / "home" / ".skillmeat" / "credentials.json"
        mock_store = CredentialStore(backend=_FileBackend(credentials_path=creds_file))
        mock_store.store(_make_device_code_result(expires_in=3600))

        with patch("skillmeat.cli.commands.auth.CredentialStore", return_value=mock_store):
            cli_runner.invoke(auth_cli, ["logout"])

        assert mock_store.is_authenticated() is False
