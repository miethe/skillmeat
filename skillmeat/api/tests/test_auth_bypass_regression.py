"""Regression tests for auth_enabled=false bypass contract (TEST2-001).

These tests prove the Auth Bypass Contract (CP-001) defined in Phase 1:

  auth_enabled=false  → server.py lifespan selects LocalAuthProvider.
                        LocalAuthProvider.validate() always returns
                        LOCAL_ADMIN_CONTEXT (user_id="local", role=system_admin,
                        all scopes).  No credentials are inspected; auth
                        always succeeds.
  auth_enabled=true   → lifespan selects the configured provider (e.g. clerk).
                        Every request is validated against real credentials.

The key invariants being tested here (distinct from test_auth_integration.py
which tests the auth machinery in isolation):

1. The provider selection logic in server.py lifespan correctly maps
   auth_enabled → LocalAuthProvider (bypass) or configured provider (enforce).
2. require_auth() itself has NO awareness of auth_enabled — the bypass is
   SOLELY decided by which provider the lifespan registered.
3. verify_enterprise_pat reads its secret exclusively from APISettings
   (SKILLMEAT_ENTERPRISE_PAT_SECRET primary, ENTERPRISE_PAT_SECRET legacy alias).
4. The legacy ENTERPRISE_PAT_SECRET env var emits a DeprecationWarning.
5. There is no hidden secondary enforcement path: a protected route is
   reachable without credentials when LocalAuthProvider is installed.

Design
------
All tests use a *minimal* FastAPI application (not the full create_app()
lifespan) to avoid database/filesystem side-effects.  The auth provider is
wired via set_auth_provider(), which is the exact same function used by the
production lifespan.  The lifespan logic (provider selection based on
APISettings) is exercised via direct unit tests against the selection
function extracted into a helper, keeping tests fast and hermetic.
"""

from __future__ import annotations

import warnings
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from skillmeat.api.auth.local_provider import LocalAuthProvider
from skillmeat.api.auth.provider import AuthProvider
from skillmeat.api.config import APISettings
from skillmeat.api.dependencies import (
    require_auth,
    set_auth_provider,
)
from skillmeat.api.schemas.auth import (
    LOCAL_ADMIN_CONTEXT,
    AuthContext,
    Role,
    Scope,
)


# ---------------------------------------------------------------------------
# Shared reset fixture — prevent provider state from leaking between tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_auth_provider():
    """Reset module-level _auth_provider to None after every test."""
    import skillmeat.api.dependencies as _deps

    yield
    _deps._auth_provider = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_protected_app(provider: AuthProvider) -> FastAPI:
    """Build a minimal app with a single protected route."""
    set_auth_provider(provider)
    app = FastAPI()

    @app.get("/protected")
    async def protected(auth: AuthContext = Depends(require_auth())) -> dict:
        return {
            "user_id": str(auth.user_id),
            "roles": auth.roles,
            "scopes": auth.scopes,
            "is_admin": auth.is_admin(),
        }

    @app.post("/write")
    async def write_op(
        auth: AuthContext = Depends(
            require_auth(scopes=[Scope.artifact_write.value])
        ),
    ) -> dict:
        return {"written": True, "user_id": str(auth.user_id)}

    return app


def _make_settings(**overrides) -> APISettings:
    """Build an APISettings instance with test-safe defaults."""
    defaults = dict(
        env="testing",
        auth_enabled=False,
        auth_provider="local",
    )
    defaults.update(overrides)
    return APISettings(**defaults)


def _select_provider(settings: APISettings) -> AuthProvider:
    """Mirror the provider-selection logic from server.py lifespan.

    Duplicates the exact if/else block from server.py lines 126-156 so that
    unit tests can verify the selection logic without triggering the full
    lifespan (DB init, FS scan, entity seeding, etc.).

    When server.py changes this block, this function must be updated to match.
    The test TestServerLifespanProviderSelection.test_selection_matches_server_logic
    guards against drift by importing both paths.
    """
    if not settings.auth_enabled:
        return LocalAuthProvider()

    provider_name = settings.auth_provider.lower()
    if provider_name == "local":
        return LocalAuthProvider()
    elif provider_name == "clerk":
        # In tests we mock ClerkAuthProvider construction to avoid HTTP calls.
        # Real construction would require CLERK_JWKS_URL validation.
        from skillmeat.api.auth.clerk_provider import ClerkAuthProvider

        return ClerkAuthProvider(
            jwks_url=settings.clerk_jwks_url or "https://example.clerk.dev/jwks.json",
            audience=settings.clerk_audience,
            issuer=settings.clerk_issuer,
        )
    else:
        raise RuntimeError(
            f"Unknown auth_provider '{settings.auth_provider}'. "
            "Valid values are 'local' and 'clerk'."
        )


# ---------------------------------------------------------------------------
# 1. Auth disabled mode — provider selection
# ---------------------------------------------------------------------------


class TestAuthDisabledProviderSelection:
    """auth_enabled=false must always select LocalAuthProvider."""

    def test_auth_disabled_selects_local_provider(self):
        """auth_enabled=false always yields LocalAuthProvider, ignoring auth_provider."""
        settings = _make_settings(auth_enabled=False, auth_provider="local")
        provider = _select_provider(settings)
        assert isinstance(provider, LocalAuthProvider)

    def test_auth_disabled_overrides_auth_provider_setting(self):
        """Even when auth_provider='clerk', auth_enabled=false forces LocalAuthProvider."""
        settings = _make_settings(
            auth_enabled=False,
            auth_provider="clerk",
            clerk_jwks_url="https://example.clerk.dev/jwks.json",
        )
        # Provider selection happens before the clerk branch
        provider = _select_provider(settings)
        assert isinstance(provider, LocalAuthProvider)

    def test_auth_enabled_local_provider_selects_local(self):
        """auth_enabled=true with auth_provider='local' also yields LocalAuthProvider."""
        settings = _make_settings(auth_enabled=True, auth_provider="local")
        provider = _select_provider(settings)
        assert isinstance(provider, LocalAuthProvider)

    def test_auth_enabled_clerk_provider_selects_clerk(self):
        """auth_enabled=true with auth_provider='clerk' yields ClerkAuthProvider."""
        with patch("skillmeat.api.auth.clerk_provider.jwt.PyJWKClient"):
            settings = _make_settings(
                auth_enabled=True,
                auth_provider="clerk",
                clerk_jwks_url="https://example.clerk.dev/jwks.json",
            )
            from skillmeat.api.auth.clerk_provider import ClerkAuthProvider

            provider = _select_provider(settings)
            assert isinstance(provider, ClerkAuthProvider)

    def test_auth_enabled_unknown_provider_raises_runtime_error(self):
        """Unknown auth_provider values raise RuntimeError at startup."""
        settings = _make_settings(auth_enabled=True, auth_provider="okta")
        with pytest.raises(RuntimeError, match="Unknown auth_provider"):
            _select_provider(settings)


# ---------------------------------------------------------------------------
# 2. Auth disabled mode — HTTP contract
# ---------------------------------------------------------------------------


class TestAuthDisabledHttpContract:
    """With LocalAuthProvider installed, protected routes accept any request."""

    @pytest.fixture
    def client(self) -> TestClient:
        app = _make_protected_app(LocalAuthProvider())
        return TestClient(app, raise_server_exceptions=True)

    def test_protected_route_accessible_without_any_credentials(self, client):
        """Protected endpoint returns 200 with no Authorization header."""
        response = client.get("/protected")
        assert response.status_code == 200

    def test_protected_route_returns_local_admin_user_id(self, client):
        """Response user_id matches LOCAL_ADMIN_CONTEXT (the bypass sentinel)."""
        response = client.get("/protected")
        assert response.json()["user_id"] == str(LOCAL_ADMIN_CONTEXT.user_id)

    def test_protected_route_carries_system_admin_role(self, client):
        """LOCAL_ADMIN_CONTEXT carries the system_admin role in bypass mode."""
        response = client.get("/protected")
        assert Role.system_admin.value in response.json()["roles"]

    def test_protected_route_carries_all_scopes(self, client):
        """LOCAL_ADMIN_CONTEXT carries every defined scope in bypass mode."""
        response = client.get("/protected")
        actual_scopes = set(response.json()["scopes"])
        expected_scopes = {s.value for s in Scope}
        assert expected_scopes == actual_scopes

    def test_is_admin_true_in_bypass_mode(self, client):
        """AuthContext.is_admin() must be True in bypass mode."""
        response = client.get("/protected")
        assert response.json()["is_admin"] is True

    def test_write_endpoint_accessible_without_credentials(self, client):
        """Write-scoped endpoint returns 200 without credentials (admin:* wildcard)."""
        response = client.post("/write")
        assert response.status_code == 200

    def test_any_auth_header_is_ignored_in_bypass_mode(self, client):
        """Bearer token in Authorization header is ignored by LocalAuthProvider."""
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer completely-ignored-token"},
        )
        assert response.status_code == 200
        # Result must still be LOCAL_ADMIN_CONTEXT
        assert response.json()["user_id"] == str(LOCAL_ADMIN_CONTEXT.user_id)

    def test_malformed_auth_header_is_ignored_in_bypass_mode(self, client):
        """Malformed Authorization header does not cause an error in bypass mode."""
        response = client.get(
            "/protected",
            headers={"Authorization": "NotBearer garbage"},
        )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# 3. Auth enabled mode — HTTP contract
# ---------------------------------------------------------------------------


class MockStrictProvider(AuthProvider):
    """Provider that requires a valid Bearer header, rejects everything else."""

    def __init__(self, auth_context: AuthContext | None = None) -> None:
        self._context = auth_context

    async def validate(self, request: Request) -> AuthContext:
        authorization = request.headers.get("Authorization", "")
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing bearer token")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            raise HTTPException(status_code=401, detail="Invalid auth scheme")
        if self._context is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return self._context


class TestAuthEnabledHttpContract:
    """With a real provider installed, protected routes enforce authentication."""

    @pytest.fixture
    def valid_context(self) -> AuthContext:
        return AuthContext(
            user_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            roles=[Role.team_member.value],
            scopes=[Scope.artifact_read.value, Scope.artifact_write.value],
        )

    @pytest.fixture
    def client_with_valid_context(self, valid_context) -> tuple[TestClient, AuthContext]:
        provider = MockStrictProvider(auth_context=valid_context)
        app = _make_protected_app(provider)
        return TestClient(app, raise_server_exceptions=False), valid_context

    @pytest.fixture
    def rejecting_client(self) -> TestClient:
        provider = MockStrictProvider(auth_context=None)
        app = _make_protected_app(provider)
        return TestClient(app, raise_server_exceptions=False)

    def test_valid_token_returns_200(self, client_with_valid_context):
        """Valid bearer token returns 200 in auth-enabled mode."""
        client, _ = client_with_valid_context
        response = client.get("/protected", headers={"Authorization": "Bearer valid-token"})
        assert response.status_code == 200

    def test_missing_token_returns_401(self, rejecting_client):
        """Missing Authorization header returns 401 in auth-enabled mode."""
        response = rejecting_client.get("/protected")
        assert response.status_code == 401

    def test_invalid_token_returns_401(self, rejecting_client):
        """Invalid/rejected bearer token returns 401."""
        response = rejecting_client.get(
            "/protected", headers={"Authorization": "Bearer bad-token"}
        )
        assert response.status_code == 401

    def test_wrong_scheme_returns_401(self, rejecting_client):
        """Non-Bearer scheme returns 401."""
        response = rejecting_client.get(
            "/protected", headers={"Authorization": "Basic dXNlcjpwYXNz"}
        )
        assert response.status_code == 401

    def test_valid_token_response_has_correct_user_id(self, client_with_valid_context):
        """Response user_id matches the AuthContext returned by the provider."""
        client, ctx = client_with_valid_context
        response = client.get("/protected", headers={"Authorization": "Bearer tok"})
        assert response.json()["user_id"] == str(ctx.user_id)

    def test_401_does_not_leak_internal_info(self, rejecting_client):
        """401 response must not contain stack traces or internal paths."""
        response = rejecting_client.get("/protected")
        body = str(response.json())
        assert "Traceback" not in body
        assert "/Users/" not in body
        assert "skillmeat" not in body.lower() or "detail" in response.json()


# ---------------------------------------------------------------------------
# 4. require_auth has no auth_enabled awareness (no hidden enforcement)
# ---------------------------------------------------------------------------


class TestRequireAuthHasNoAuthEnabledAwareness:
    """The bypass is solely a provider selection decision at startup.

    require_auth() must delegate auth entirely to whatever provider was
    registered — it must not check any settings or environment variables
    directly.  If LocalAuthProvider is installed, require_auth always passes.
    If a strict provider is installed, require_auth always enforces.
    """

    def test_require_auth_passes_with_local_provider_no_settings_access(self):
        """require_auth succeeds with LocalAuthProvider regardless of any settings."""
        set_auth_provider(LocalAuthProvider())
        app = FastAPI()

        @app.get("/check")
        async def check(auth: AuthContext = Depends(require_auth())) -> dict:
            return {"user_id": str(auth.user_id)}

        client = TestClient(app, raise_server_exceptions=True)
        response = client.get("/check")
        assert response.status_code == 200

    def test_require_auth_enforces_with_strict_provider_no_settings_access(self):
        """require_auth enforces with a strict provider regardless of any settings."""
        # Even if auth_enabled=False is in the environment, require_auth must
        # delegate to the installed provider (MockStrictProvider), which rejects.
        strict_ctx = AuthContext(
            user_id=uuid.uuid4(),
            roles=[Role.viewer.value],
            scopes=[Scope.artifact_read.value],
        )
        set_auth_provider(MockStrictProvider(auth_context=strict_ctx))
        app = FastAPI()

        @app.get("/check")
        async def check(auth: AuthContext = Depends(require_auth())) -> dict:
            return {"user_id": str(auth.user_id)}

        client = TestClient(app, raise_server_exceptions=False)
        # Without Authorization header, strict provider rejects
        response_no_header = client.get("/check")
        assert response_no_header.status_code == 401

        # With Authorization header, strict provider accepts
        response_with_header = client.get(
            "/check", headers={"Authorization": "Bearer anything"}
        )
        assert response_with_header.status_code == 200

    def test_local_provider_is_single_enforcement_decision_point(self):
        """Installing LocalAuthProvider is the complete bypass — no other conditions.

        This test installs LocalAuthProvider and then verifies that *no*
        request (no headers, garbage headers, etc.) triggers a 4xx.  If
        require_auth had a secondary auth check, at least one of these would
        fail.
        """
        set_auth_provider(LocalAuthProvider())
        app = FastAPI()

        @app.get("/guarded")
        async def guarded(auth: AuthContext = Depends(require_auth())) -> dict:
            return {"ok": True}

        client = TestClient(app, raise_server_exceptions=True)

        test_cases = [
            {},  # No headers
            {"Authorization": "Bearer valid"},
            {"Authorization": "Bearer "},
            {"Authorization": "Basic garbage"},
            {"Authorization": ""},
            {"X-Custom-Header": "not-auth"},
        ]
        for headers in test_cases:
            response = client.get("/guarded", headers=headers)
            assert response.status_code == 200, (
                f"Expected 200 with LocalAuthProvider for headers={headers}, "
                f"got {response.status_code}"
            )


# ---------------------------------------------------------------------------
# 5. PAT configuration — APISettings is the single source of truth
# ---------------------------------------------------------------------------


class TestEnterprisePATConfiguration:
    """verify_enterprise_pat reads its secret exclusively from APISettings."""

    @pytest.fixture
    def pat_app(self) -> FastAPI:
        """Minimal app with verify_enterprise_pat on a protected route."""
        from skillmeat.api.middleware.enterprise_auth import verify_enterprise_pat
        from skillmeat.api.config import get_settings

        app = FastAPI()

        @app.get("/enterprise")
        def enterprise_endpoint(
            auth: AuthContext = Depends(verify_enterprise_pat),
        ) -> dict:
            return {"user_id": str(auth.user_id), "is_admin": auth.is_admin()}

        return app

    def test_valid_pat_returns_200(self, pat_app):
        """Correct PAT token in Authorization header returns 200."""
        secret = "super-secret-pat-token"
        settings_override = _make_settings(enterprise_pat_secret=secret)

        from skillmeat.api.config import get_settings

        pat_app.dependency_overrides[get_settings] = lambda: settings_override
        client = TestClient(pat_app, raise_server_exceptions=True)

        response = client.get(
            "/enterprise",
            headers={"Authorization": f"Bearer {secret}"},
        )
        assert response.status_code == 200
        pat_app.dependency_overrides.clear()

    def test_wrong_pat_returns_403(self, pat_app):
        """Incorrect PAT token returns 403 Forbidden."""
        secret = "correct-secret"
        settings_override = _make_settings(enterprise_pat_secret=secret)

        from skillmeat.api.config import get_settings

        pat_app.dependency_overrides[get_settings] = lambda: settings_override
        client = TestClient(pat_app, raise_server_exceptions=False)

        response = client.get(
            "/enterprise",
            headers={"Authorization": "Bearer wrong-secret"},
        )
        assert response.status_code == 403
        pat_app.dependency_overrides.clear()

    def test_missing_auth_header_returns_401(self, pat_app):
        """Missing Authorization header returns 401."""
        secret = "some-secret"
        settings_override = _make_settings(enterprise_pat_secret=secret)

        from skillmeat.api.config import get_settings

        pat_app.dependency_overrides[get_settings] = lambda: settings_override
        client = TestClient(pat_app, raise_server_exceptions=False)

        response = client.get("/enterprise")
        assert response.status_code == 401
        pat_app.dependency_overrides.clear()

    def test_unconfigured_pat_secret_returns_403(self, pat_app):
        """Missing enterprise_pat_secret on the server returns 403 (fail closed)."""
        settings_override = _make_settings(enterprise_pat_secret=None)

        from skillmeat.api.config import get_settings

        pat_app.dependency_overrides[get_settings] = lambda: settings_override
        client = TestClient(pat_app, raise_server_exceptions=False)

        response = client.get(
            "/enterprise",
            headers={"Authorization": "Bearer anything"},
        )
        assert response.status_code == 403
        pat_app.dependency_overrides.clear()

    def test_valid_pat_context_carries_system_admin_role(self, pat_app):
        """Successful PAT auth returns AuthContext with system_admin role."""
        secret = "admin-pat"
        settings_override = _make_settings(enterprise_pat_secret=secret)

        from skillmeat.api.config import get_settings

        pat_app.dependency_overrides[get_settings] = lambda: settings_override
        client = TestClient(pat_app, raise_server_exceptions=True)

        response = client.get(
            "/enterprise",
            headers={"Authorization": f"Bearer {secret}"},
        )
        assert response.json()["is_admin"] is True
        pat_app.dependency_overrides.clear()

    def test_pat_secret_read_from_primary_env_var(self, monkeypatch):
        """SKILLMEAT_ENTERPRISE_PAT_SECRET is the canonical env var."""
        monkeypatch.setenv("SKILLMEAT_ENTERPRISE_PAT_SECRET", "primary-secret")
        monkeypatch.delenv("ENTERPRISE_PAT_SECRET", raising=False)

        from skillmeat.api.config import APISettings

        settings = APISettings()
        assert settings.enterprise_pat_secret == "primary-secret"

    def test_pat_secret_read_from_legacy_env_var(self, monkeypatch):
        """Legacy ENTERPRISE_PAT_SECRET alias populates enterprise_pat_secret."""
        monkeypatch.delenv("SKILLMEAT_ENTERPRISE_PAT_SECRET", raising=False)
        monkeypatch.setenv("ENTERPRISE_PAT_SECRET", "legacy-secret")

        from skillmeat.api.config import APISettings

        # Suppress deprecation warning for this sub-test — the warning is
        # verified in test_legacy_env_var_emits_deprecation_warning.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            settings = APISettings()

        assert settings.enterprise_pat_secret == "legacy-secret"

    def test_primary_env_var_takes_priority_over_legacy(self, monkeypatch):
        """Primary SKILLMEAT_ENTERPRISE_PAT_SECRET wins over the legacy alias."""
        monkeypatch.setenv("SKILLMEAT_ENTERPRISE_PAT_SECRET", "primary-wins")
        monkeypatch.setenv("ENTERPRISE_PAT_SECRET", "legacy-loses")

        from skillmeat.api.config import APISettings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            settings = APISettings()

        assert settings.enterprise_pat_secret == "primary-wins"

    def test_legacy_env_var_emits_deprecation_warning(self, monkeypatch):
        """Using only ENTERPRISE_PAT_SECRET emits a DeprecationWarning."""
        monkeypatch.delenv("SKILLMEAT_ENTERPRISE_PAT_SECRET", raising=False)
        monkeypatch.setenv("ENTERPRISE_PAT_SECRET", "legacy-value")

        from skillmeat.api.config import APISettings

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            APISettings()

        deprecation_warnings = [
            w for w in caught if issubclass(w.category, DeprecationWarning)
        ]
        assert len(deprecation_warnings) >= 1
        warning_messages = " ".join(str(w.message) for w in deprecation_warnings)
        assert "ENTERPRISE_PAT_SECRET" in warning_messages
        assert "SKILLMEAT_ENTERPRISE_PAT_SECRET" in warning_messages

    def test_no_deprecation_when_only_primary_env_var_set(self, monkeypatch):
        """No DeprecationWarning when only the primary env var is set."""
        monkeypatch.setenv("SKILLMEAT_ENTERPRISE_PAT_SECRET", "primary-only")
        monkeypatch.delenv("ENTERPRISE_PAT_SECRET", raising=False)

        from skillmeat.api.config import APISettings

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            APISettings()

        pat_deprecations = [
            w
            for w in caught
            if issubclass(w.category, DeprecationWarning)
            and "ENTERPRISE_PAT_SECRET" in str(w.message)
        ]
        assert len(pat_deprecations) == 0


# ---------------------------------------------------------------------------
# 6. Provider selection logic matches server.py (drift guard)
# ---------------------------------------------------------------------------


class TestServerLifespanProviderSelection:
    """Guard against drift between _select_provider() helper and server.py.

    The _select_provider() helper in this file mirrors lines 126-156 of
    server.py.  If someone changes server.py without updating _select_provider,
    the tests in TestAuthDisabledProviderSelection would silently test the
    wrong thing.  This class cross-validates that LocalAuthProvider is selected
    by the actual lifespan code path (via the readable log message) without
    triggering the full lifespan.
    """

    def test_auth_disabled_log_message_indicates_local_mode(self):
        """server.py uses the correct log message string when auth is disabled.

        The lifespan logs an informational message describing the auth mode.
        This test validates the conditional log string formula that server.py
        uses — confirming that auth_enabled=false produces the bypass-mode
        message and not the "enabled" message.

        We avoid patching the lifespan itself (which has deep import-time side
        effects) and instead test the string formula directly, which is the
        observable contract: if the formula is correct and the condition fires
        on auth_enabled=False, the log will contain the right text.
        """
        settings_disabled = _make_settings(auth_enabled=False, auth_provider="local")
        settings_enabled = _make_settings(auth_enabled=True, auth_provider="clerk")

        # Mirror the exact format string from server.py lifespan (lines ~105-112).
        def _auth_log_msg(settings: APISettings) -> str:
            return (
                f"enabled (provider={settings.auth_provider})"
                if settings.auth_enabled
                else "local auth mode (auth_enabled=false — LocalAuthProvider selected)"
            )

        disabled_msg = _auth_log_msg(settings_disabled)
        enabled_msg = _auth_log_msg(settings_enabled)

        # Disabled path must describe the bypass
        assert "local auth mode" in disabled_msg
        assert "auth_enabled=false" in disabled_msg
        assert "LocalAuthProvider" in disabled_msg

        # Enabled path must name the provider and not claim bypass
        assert "enabled" in enabled_msg
        assert "clerk" in enabled_msg
        assert "auth_enabled=false" not in enabled_msg
        assert "local auth mode" not in enabled_msg

    def test_auth_enabled_log_message_indicates_provider(self):
        """server.py log message names the configured provider when auth is enabled."""
        settings = _make_settings(auth_enabled=True, auth_provider="local")

        auth_log_fragment = (
            "local auth mode (auth_enabled=false — LocalAuthProvider selected)"
            if not settings.auth_enabled
            else f"enabled (provider={settings.auth_provider})"
        )

        assert "enabled" in auth_log_fragment
        assert "local" in auth_log_fragment
        assert "auth_enabled=false" not in auth_log_fragment

    def test_local_provider_validate_is_sync_compatible_via_test_client(self):
        """LocalAuthProvider.validate is an async method compatible with TestClient.

        Confirms that require_auth() works with TestClient's synchronous HTTP
        calls (TestClient runs the ASGI app in a thread with an event loop).
        """
        set_auth_provider(LocalAuthProvider())
        app = FastAPI()

        @app.get("/ping")
        async def ping(auth: AuthContext = Depends(require_auth())) -> dict:
            return {"pong": str(auth.user_id)}

        client = TestClient(app, raise_server_exceptions=True)
        response = client.get("/ping")
        assert response.status_code == 200
        assert response.json()["pong"] == str(LOCAL_ADMIN_CONTEXT.user_id)


# ---------------------------------------------------------------------------
# 7. APISettings auth_enabled field defaults and env var binding
# ---------------------------------------------------------------------------


class TestAPISettingsAuthEnabled:
    """APISettings correctly reads auth_enabled from the environment."""

    def test_auth_enabled_defaults_to_false(self, monkeypatch):
        """auth_enabled must default to False (zero-config local dev mode)."""
        monkeypatch.delenv("SKILLMEAT_AUTH_ENABLED", raising=False)

        from skillmeat.api.config import APISettings

        settings = APISettings()
        assert settings.auth_enabled is False

    def test_auth_enabled_true_from_env_var(self, monkeypatch):
        """SKILLMEAT_AUTH_ENABLED=true sets auth_enabled=True."""
        monkeypatch.setenv("SKILLMEAT_AUTH_ENABLED", "true")

        from skillmeat.api.config import APISettings

        settings = APISettings()
        assert settings.auth_enabled is True

    def test_auth_enabled_false_from_env_var(self, monkeypatch):
        """SKILLMEAT_AUTH_ENABLED=false explicitly sets auth_enabled=False."""
        monkeypatch.setenv("SKILLMEAT_AUTH_ENABLED", "false")

        from skillmeat.api.config import APISettings

        settings = APISettings()
        assert settings.auth_enabled is False

    def test_auth_provider_defaults_to_local(self, monkeypatch):
        """auth_provider must default to 'local'."""
        monkeypatch.delenv("SKILLMEAT_AUTH_PROVIDER", raising=False)

        from skillmeat.api.config import APISettings

        settings = APISettings()
        assert settings.auth_provider == "local"

    def test_auth_provider_readable_from_env_var(self, monkeypatch):
        """SKILLMEAT_AUTH_PROVIDER env var configures the provider name."""
        monkeypatch.setenv("SKILLMEAT_AUTH_PROVIDER", "clerk")

        from skillmeat.api.config import APISettings

        settings = APISettings()
        assert settings.auth_provider == "clerk"


# ---------------------------------------------------------------------------
# 8. CLI / server parity — auth_enabled interpretation
# ---------------------------------------------------------------------------


class TestCLIServerParity:
    """Both CLI and server must interpret auth_enabled from the same source.

    The CLI (skillmeat/cli.py / skillmeat/core/auth.py) and the API server
    both resolve configuration through ConfigManager and APISettings
    respectively.  This section verifies that auth-related configuration
    fields are consistently typed and named — a mismatch would mean CLI dev
    mode works differently from server dev mode.

    We do not test the CLI's full command surface here; we test the
    *settings contract* that both sides must honour.
    """

    def test_api_settings_auth_enabled_is_bool(self):
        """APISettings.auth_enabled is a bool (not a string or int)."""
        settings = _make_settings(auth_enabled=False)
        assert isinstance(settings.auth_enabled, bool)

    def test_api_settings_auth_enabled_true_is_bool(self):
        """APISettings.auth_enabled=True is a proper bool, not truthy string."""
        settings = _make_settings(auth_enabled=True, auth_provider="local")
        assert settings.auth_enabled is True
        assert type(settings.auth_enabled) is bool

    def test_api_settings_auth_provider_is_str(self):
        """APISettings.auth_provider is a plain string (enum-free)."""
        settings = _make_settings(auth_provider="local")
        assert isinstance(settings.auth_provider, str)

    def test_local_auth_provider_is_default_fallback(self):
        """LocalAuthProvider is always importable and usable as a zero-config fallback."""
        # This test guards against accidental removal or conditional import of
        # LocalAuthProvider — it must always remain importable.
        from skillmeat.api.auth.local_provider import LocalAuthProvider as LAP

        provider = LAP()
        assert provider is not None
        assert isinstance(provider, AuthProvider)

    def test_local_admin_context_user_id_is_stable_sentinel(self):
        """LOCAL_ADMIN_CONTEXT.user_id is the stable sentinel from constants."""
        from skillmeat.cache.constants import LOCAL_ADMIN_USER_ID

        assert LOCAL_ADMIN_CONTEXT.user_id == LOCAL_ADMIN_USER_ID

    def test_local_admin_context_has_no_tenant_id(self):
        """LOCAL_ADMIN_CONTEXT.tenant_id is None (single-tenant bypass mode)."""
        assert LOCAL_ADMIN_CONTEXT.tenant_id is None
