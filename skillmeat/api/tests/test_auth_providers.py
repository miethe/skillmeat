"""Unit tests for LocalAuthProvider, ClerkAuthProvider, and require_auth dependency.

Coverage targets:
- LocalAuthProvider: zero-auth pass-through returning LOCAL_ADMIN_CONTEXT
- ClerkAuthProvider: JWT validation, claim mapping, error paths
- require_auth: context injection, scope enforcement, dual usage patterns

No external network calls are made; jwt.PyJWKClient is always mocked.

References:
    .claude/progress/aaa-rbac-foundation/  AUTH-008
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.testclient import TestClient as StarletteTestClient

from skillmeat.api.auth.clerk_provider import (
    ClerkAuthProvider,
    _CLERK_NAMESPACE,
    _str_to_uuid,
)
from skillmeat.api.auth.local_provider import LocalAuthProvider
from skillmeat.api.schemas.auth import (
    LOCAL_ADMIN_CONTEXT,
    AuthContext,
    Role,
    Scope,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request(headers: dict[str, str] | None = None) -> Request:
    """Build a minimal Starlette Request with the given headers."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [
            (k.lower().encode(), v.encode())
            for k, v in (headers or {}).items()
        ],
        "query_string": b"",
    }
    return Request(scope)


def _make_mock_signing_key(public_key: Any = "mock-public-key") -> MagicMock:
    """Return a mock signing key object as returned by PyJWKClient."""
    mock_key = MagicMock()
    mock_key.key = public_key
    return mock_key


def _minimal_valid_claims(sub: str = "user_abc123") -> dict[str, Any]:
    """Return the minimal decoded JWT payload for a valid Clerk token."""
    return {
        "sub": sub,
        "exp": 9999999999,
        "iat": 1_700_000_000,
    }


# ---------------------------------------------------------------------------
# LocalAuthProvider tests
# ---------------------------------------------------------------------------


class TestLocalAuthProvider:
    """LocalAuthProvider always grants local admin access with no inspection."""

    @pytest.fixture
    def provider(self) -> LocalAuthProvider:
        return LocalAuthProvider()

    @pytest.mark.asyncio
    async def test_local_provider_always_returns_auth_context(self, provider):
        """validate() returns an AuthContext regardless of request content."""
        request = _make_request()
        result = await provider.validate(request)
        assert isinstance(result, AuthContext)

    @pytest.mark.asyncio
    async def test_local_provider_returns_local_admin_context_singleton(self, provider):
        """validate() returns the pre-built LOCAL_ADMIN_CONTEXT singleton."""
        request = _make_request()
        result = await provider.validate(request)
        assert result is LOCAL_ADMIN_CONTEXT

    @pytest.mark.asyncio
    async def test_local_provider_returns_system_admin_role(self, provider):
        """AuthContext must carry the system_admin role."""
        request = _make_request()
        result = await provider.validate(request)
        assert result.has_role(Role.system_admin)

    @pytest.mark.asyncio
    async def test_local_provider_returns_all_scopes(self, provider):
        """AuthContext must carry all defined Scope values (or admin wildcard)."""
        request = _make_request()
        result = await provider.validate(request)
        for scope in Scope:
            assert result.has_scope(scope), f"Missing scope: {scope}"

    @pytest.mark.asyncio
    async def test_local_provider_ignores_auth_header(self, provider):
        """validate() succeeds even when no Authorization header is present."""
        request = _make_request(headers={})
        # Must not raise
        result = await provider.validate(request)
        assert result is LOCAL_ADMIN_CONTEXT

    @pytest.mark.asyncio
    async def test_local_provider_ignores_malformed_auth_header(self, provider):
        """validate() succeeds even when the Authorization header is garbage."""
        request = _make_request(headers={"Authorization": "not-a-real-token"})
        result = await provider.validate(request)
        assert result is LOCAL_ADMIN_CONTEXT

    @pytest.mark.asyncio
    async def test_local_provider_never_raises(self, provider):
        """validate() must never raise any exception."""
        request = _make_request(headers={"Authorization": "Bearer invalid.jwt.here"})
        try:
            await provider.validate(request)
        except Exception as exc:  # noqa: BLE001
            pytest.fail(f"LocalAuthProvider.validate raised unexpectedly: {exc}")

    @pytest.mark.asyncio
    async def test_local_provider_tenant_id_is_none(self, provider):
        """Local mode operates in single-tenant mode; tenant_id must be None."""
        request = _make_request()
        result = await provider.validate(request)
        assert result.tenant_id is None

    @pytest.mark.asyncio
    async def test_local_provider_is_admin(self, provider):
        """AuthContext.is_admin() must return True for the local admin context."""
        request = _make_request()
        result = await provider.validate(request)
        assert result.is_admin()


# ---------------------------------------------------------------------------
# ClerkAuthProvider tests
# ---------------------------------------------------------------------------


class TestClerkAuthProvider:
    """ClerkAuthProvider validates JWTs and maps Clerk claims to AuthContext."""

    # ------------------------------------------------------------------
    # Fixtures
    # ------------------------------------------------------------------

    @pytest.fixture
    def mock_jwks_client(self):
        """Patch jwt.PyJWKClient so no HTTP calls are made during construction."""
        with patch("skillmeat.api.auth.clerk_provider.jwt.PyJWKClient") as mock_cls:
            instance = MagicMock()
            mock_cls.return_value = instance
            yield instance

    @pytest.fixture
    def provider(self, mock_jwks_client) -> ClerkAuthProvider:
        """ClerkAuthProvider with a mocked JWKS client."""
        return ClerkAuthProvider(jwks_url="https://example.clerk.dev/.well-known/jwks.json")

    # ------------------------------------------------------------------
    # Missing / malformed Authorization header
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_clerk_provider_rejects_missing_auth_header(self, provider):
        """validate() raises 401 when Authorization header is absent."""
        request = _make_request()
        with pytest.raises(HTTPException) as exc_info:
            await provider.validate(request)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_clerk_provider_rejects_non_bearer_scheme(self, provider):
        """validate() raises 401 when Authorization header is not Bearer."""
        request = _make_request(headers={"Authorization": "Basic dXNlcjpwYXNz"})
        with pytest.raises(HTTPException) as exc_info:
            await provider.validate(request)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_clerk_provider_rejects_bearer_with_empty_token(self, provider):
        """validate() raises 401 when Bearer scheme has no token body."""
        request = _make_request(headers={"Authorization": "Bearer "})
        with pytest.raises(HTTPException) as exc_info:
            await provider.validate(request)
        assert exc_info.value.status_code == 401

    # ------------------------------------------------------------------
    # Invalid JWT signatures / decode failures
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_clerk_provider_rejects_invalid_jwt(self, provider, mock_jwks_client):
        """validate() raises 401 when JWT signature is invalid."""
        import jwt as pyjwt

        mock_jwks_client.get_signing_key_from_jwt.return_value = _make_mock_signing_key()

        with patch("skillmeat.api.auth.clerk_provider.jwt.decode") as mock_decode:
            mock_decode.side_effect = pyjwt.InvalidTokenError("bad signature")
            request = _make_request(headers={"Authorization": "Bearer malformed.jwt.token"})
            with pytest.raises(HTTPException) as exc_info:
                await provider.validate(request)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_clerk_provider_rejects_expired_jwt(self, provider, mock_jwks_client):
        """validate() raises 401 with detail about expiry for expired tokens."""
        import jwt as pyjwt

        mock_jwks_client.get_signing_key_from_jwt.return_value = _make_mock_signing_key()

        with patch("skillmeat.api.auth.clerk_provider.jwt.decode") as mock_decode:
            mock_decode.side_effect = pyjwt.ExpiredSignatureError("expired")
            request = _make_request(headers={"Authorization": "Bearer expired.jwt.token"})
            with pytest.raises(HTTPException) as exc_info:
                await provider.validate(request)
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_clerk_provider_raises_503_on_jwks_connection_error(
        self, provider, mock_jwks_client
    ):
        """validate() raises 503 when the JWKS endpoint is unreachable."""
        import jwt as pyjwt

        mock_jwks_client.get_signing_key_from_jwt.side_effect = (
            pyjwt.PyJWKClientConnectionError("timeout")
        )
        request = _make_request(headers={"Authorization": "Bearer some.jwt.token"})
        with pytest.raises(HTTPException) as exc_info:
            await provider.validate(request)
        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_clerk_provider_raises_401_on_jwks_key_error(
        self, provider, mock_jwks_client
    ):
        """validate() raises 401 when JWKS client cannot resolve the signing key."""
        import jwt as pyjwt

        mock_jwks_client.get_signing_key_from_jwt.side_effect = (
            pyjwt.PyJWKClientError("unknown kid")
        )
        request = _make_request(headers={"Authorization": "Bearer some.jwt.token"})
        with pytest.raises(HTTPException) as exc_info:
            await provider.validate(request)
        assert exc_info.value.status_code == 401

    # ------------------------------------------------------------------
    # Successful validation — claim mapping
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_clerk_provider_validates_valid_jwt(self, provider, mock_jwks_client):
        """validate() returns AuthContext for a well-formed Clerk JWT."""
        mock_jwks_client.get_signing_key_from_jwt.return_value = _make_mock_signing_key()
        claims = _minimal_valid_claims(sub="user_abc")

        with patch("skillmeat.api.auth.clerk_provider.jwt.decode", return_value=claims):
            request = _make_request(headers={"Authorization": "Bearer valid.jwt.token"})
            result = await provider.validate(request)

        assert isinstance(result, AuthContext)

    @pytest.mark.asyncio
    async def test_clerk_provider_maps_sub_to_user_id(self, provider, mock_jwks_client):
        """sub claim is converted to a deterministic UUID5 user_id."""
        sub = "user_uniquestring"
        expected_uuid = uuid.uuid5(_CLERK_NAMESPACE, sub)

        mock_jwks_client.get_signing_key_from_jwt.return_value = _make_mock_signing_key()
        claims = _minimal_valid_claims(sub=sub)

        with patch("skillmeat.api.auth.clerk_provider.jwt.decode", return_value=claims):
            request = _make_request(headers={"Authorization": "Bearer valid.jwt"})
            result = await provider.validate(request)

        assert result.user_id == expected_uuid

    @pytest.mark.asyncio
    async def test_clerk_provider_maps_org_admin_to_team_admin_role(
        self, provider, mock_jwks_client
    ):
        """org:admin role in the JWT maps to team_admin in AuthContext."""
        mock_jwks_client.get_signing_key_from_jwt.return_value = _make_mock_signing_key()
        claims = {
            **_minimal_valid_claims(),
            "org_id": "org_admin123",
            "org_role": "org:admin",
        }

        with patch("skillmeat.api.auth.clerk_provider.jwt.decode", return_value=claims):
            request = _make_request(headers={"Authorization": "Bearer valid.jwt"})
            result = await provider.validate(request)

        assert result.has_role(Role.team_admin)
        assert not result.has_role(Role.team_member)

    @pytest.mark.asyncio
    async def test_clerk_provider_maps_org_member_to_team_member_role(
        self, provider, mock_jwks_client
    ):
        """org:member role in the JWT maps to team_member in AuthContext."""
        mock_jwks_client.get_signing_key_from_jwt.return_value = _make_mock_signing_key()
        claims = {
            **_minimal_valid_claims(),
            "org_id": "org_member456",
            "org_role": "org:member",
        }

        with patch("skillmeat.api.auth.clerk_provider.jwt.decode", return_value=claims):
            request = _make_request(headers={"Authorization": "Bearer valid.jwt"})
            result = await provider.validate(request)

        assert result.has_role(Role.team_member)
        assert not result.has_role(Role.team_admin)

    @pytest.mark.asyncio
    async def test_clerk_provider_no_org_defaults_to_viewer(
        self, provider, mock_jwks_client
    ):
        """Missing org context grants the viewer (read-only) role."""
        mock_jwks_client.get_signing_key_from_jwt.return_value = _make_mock_signing_key()
        claims = _minimal_valid_claims()  # no org_id

        with patch("skillmeat.api.auth.clerk_provider.jwt.decode", return_value=claims):
            request = _make_request(headers={"Authorization": "Bearer valid.jwt"})
            result = await provider.validate(request)

        assert result.has_role(Role.viewer)
        assert not result.has_role(Role.team_member)
        assert not result.has_role(Role.team_admin)

    @pytest.mark.asyncio
    async def test_clerk_provider_no_org_sets_tenant_id_none(
        self, provider, mock_jwks_client
    ):
        """Without an org_id claim tenant_id must be None."""
        mock_jwks_client.get_signing_key_from_jwt.return_value = _make_mock_signing_key()
        claims = _minimal_valid_claims()

        with patch("skillmeat.api.auth.clerk_provider.jwt.decode", return_value=claims):
            request = _make_request(headers={"Authorization": "Bearer valid.jwt"})
            result = await provider.validate(request)

        assert result.tenant_id is None

    @pytest.mark.asyncio
    async def test_clerk_provider_org_id_maps_to_tenant_id(
        self, provider, mock_jwks_client
    ):
        """org_id claim is converted to a deterministic UUID5 tenant_id."""
        org_id = "org_deterministic"
        expected_tenant = uuid.uuid5(_CLERK_NAMESPACE, org_id)

        mock_jwks_client.get_signing_key_from_jwt.return_value = _make_mock_signing_key()
        claims = {**_minimal_valid_claims(), "org_id": org_id, "org_role": "org:member"}

        with patch("skillmeat.api.auth.clerk_provider.jwt.decode", return_value=claims):
            request = _make_request(headers={"Authorization": "Bearer valid.jwt"})
            result = await provider.validate(request)

        assert result.tenant_id == expected_tenant

    @pytest.mark.asyncio
    async def test_clerk_provider_explicit_permissions_used_as_scopes(
        self, provider, mock_jwks_client
    ):
        """Explicit ``permissions`` list in JWT overrides role-default scopes."""
        custom_scopes = ["artifact:read", "collection:read"]
        mock_jwks_client.get_signing_key_from_jwt.return_value = _make_mock_signing_key()
        claims = {
            **_minimal_valid_claims(),
            "org_id": "org_x",
            "org_role": "org:admin",
            "permissions": custom_scopes,
        }

        with patch("skillmeat.api.auth.clerk_provider.jwt.decode", return_value=claims):
            request = _make_request(headers={"Authorization": "Bearer valid.jwt"})
            result = await provider.validate(request)

        # Only the explicitly listed scopes should be present
        assert "artifact:read" in result.scopes
        assert "collection:read" in result.scopes
        # admin:* should NOT be present (it was not in the permissions list)
        assert Scope.admin_wildcard.value not in result.scopes

    @pytest.mark.asyncio
    async def test_clerk_provider_viewer_role_gets_read_only_scopes(
        self, provider, mock_jwks_client
    ):
        """viewer role must not receive write scopes."""
        mock_jwks_client.get_signing_key_from_jwt.return_value = _make_mock_signing_key()
        claims = _minimal_valid_claims()  # no org → viewer

        with patch("skillmeat.api.auth.clerk_provider.jwt.decode", return_value=claims):
            request = _make_request(headers={"Authorization": "Bearer valid.jwt"})
            result = await provider.validate(request)

        assert Scope.artifact_read.value in result.scopes
        assert Scope.artifact_write.value not in result.scopes
        assert Scope.admin_wildcard.value not in result.scopes

    @pytest.mark.asyncio
    async def test_clerk_provider_admin_role_gets_admin_wildcard(
        self, provider, mock_jwks_client
    ):
        """team_admin role must include the admin:* wildcard scope."""
        mock_jwks_client.get_signing_key_from_jwt.return_value = _make_mock_signing_key()
        claims = {
            **_minimal_valid_claims(),
            "org_id": "org_admin",
            "org_role": "org:admin",
        }

        with patch("skillmeat.api.auth.clerk_provider.jwt.decode", return_value=claims):
            request = _make_request(headers={"Authorization": "Bearer valid.jwt"})
            result = await provider.validate(request)

        assert result.has_scope(Scope.admin_wildcard)

    @pytest.mark.asyncio
    async def test_clerk_provider_unknown_org_role_defaults_to_team_member(
        self, provider, mock_jwks_client
    ):
        """Unknown org_role values fall back to team_member (defensive default)."""
        mock_jwks_client.get_signing_key_from_jwt.return_value = _make_mock_signing_key()
        claims = {
            **_minimal_valid_claims(),
            "org_id": "org_x",
            "org_role": "org:owner",  # not in the role map
        }

        with patch("skillmeat.api.auth.clerk_provider.jwt.decode", return_value=claims):
            request = _make_request(headers={"Authorization": "Bearer valid.jwt"})
            result = await provider.validate(request)

        assert result.has_role(Role.team_member)

    # ------------------------------------------------------------------
    # SEC-001: Audience claim validation
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_clerk_provider_rejects_wrong_audience(self, mock_jwks_client):
        """validate() raises 401 when the token aud claim does not match the configured audience."""
        import jwt as pyjwt

        provider = ClerkAuthProvider(
            jwks_url="https://example.clerk.dev/.well-known/jwks.json",
            audience="https://expected-app.example.com",
        )
        mock_jwks_client.get_signing_key_from_jwt.return_value = _make_mock_signing_key()

        with patch("skillmeat.api.auth.clerk_provider.jwt.decode") as mock_decode:
            mock_decode.side_effect = pyjwt.InvalidAudienceError("audience mismatch")
            request = _make_request(headers={"Authorization": "Bearer valid.jwt.token"})
            with pytest.raises(HTTPException) as exc_info:
                await provider.validate(request)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_clerk_provider_passes_audience_to_decode(self, mock_jwks_client):
        """jwt.decode is called with the configured audience value."""
        provider = ClerkAuthProvider(
            jwks_url="https://example.clerk.dev/.well-known/jwks.json",
            audience="https://my-audience.example.com",
        )
        mock_jwks_client.get_signing_key_from_jwt.return_value = _make_mock_signing_key()
        claims = _minimal_valid_claims()

        with patch("skillmeat.api.auth.clerk_provider.jwt.decode", return_value=claims) as mock_decode:
            request = _make_request(headers={"Authorization": "Bearer valid.jwt"})
            await provider.validate(request)

        call_kwargs = mock_decode.call_args.kwargs
        assert call_kwargs.get("audience") == "https://my-audience.example.com"
        assert "aud" in call_kwargs["options"]["require"]

    @pytest.mark.asyncio
    async def test_clerk_provider_no_audience_configured_skips_aud_require(
        self, provider, mock_jwks_client
    ):
        """When no audience is configured aud is not added to required claims."""
        mock_jwks_client.get_signing_key_from_jwt.return_value = _make_mock_signing_key()
        claims = _minimal_valid_claims()

        with patch("skillmeat.api.auth.clerk_provider.jwt.decode", return_value=claims) as mock_decode:
            request = _make_request(headers={"Authorization": "Bearer valid.jwt"})
            await provider.validate(request)

        call_kwargs = mock_decode.call_args.kwargs
        assert "audience" not in call_kwargs
        assert "aud" not in call_kwargs["options"]["require"]

    # ------------------------------------------------------------------
    # SEC-002: Issuer claim validation
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_clerk_provider_rejects_wrong_issuer(self, mock_jwks_client):
        """validate() raises 401 when the token iss claim does not match the configured issuer."""
        import jwt as pyjwt

        provider = ClerkAuthProvider(
            jwks_url="https://example.clerk.dev/.well-known/jwks.json",
            issuer="https://clerk.expected-app.example.com",
        )
        mock_jwks_client.get_signing_key_from_jwt.return_value = _make_mock_signing_key()

        with patch("skillmeat.api.auth.clerk_provider.jwt.decode") as mock_decode:
            mock_decode.side_effect = pyjwt.InvalidIssuerError("issuer mismatch")
            request = _make_request(headers={"Authorization": "Bearer valid.jwt.token"})
            with pytest.raises(HTTPException) as exc_info:
                await provider.validate(request)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_clerk_provider_passes_issuer_to_decode(self, mock_jwks_client):
        """jwt.decode is called with the configured issuer value."""
        provider = ClerkAuthProvider(
            jwks_url="https://example.clerk.dev/.well-known/jwks.json",
            issuer="https://clerk.my-app.example.com",
        )
        mock_jwks_client.get_signing_key_from_jwt.return_value = _make_mock_signing_key()
        claims = _minimal_valid_claims()

        with patch("skillmeat.api.auth.clerk_provider.jwt.decode", return_value=claims) as mock_decode:
            request = _make_request(headers={"Authorization": "Bearer valid.jwt"})
            await provider.validate(request)

        call_kwargs = mock_decode.call_args.kwargs
        assert call_kwargs.get("issuer") == "https://clerk.my-app.example.com"
        assert "iss" in call_kwargs["options"]["require"]

    @pytest.mark.asyncio
    async def test_clerk_provider_no_issuer_configured_skips_iss_require(
        self, provider, mock_jwks_client
    ):
        """When no issuer is configured iss is not added to required claims."""
        mock_jwks_client.get_signing_key_from_jwt.return_value = _make_mock_signing_key()
        claims = _minimal_valid_claims()

        with patch("skillmeat.api.auth.clerk_provider.jwt.decode", return_value=claims) as mock_decode:
            request = _make_request(headers={"Authorization": "Bearer valid.jwt"})
            await provider.validate(request)

        call_kwargs = mock_decode.call_args.kwargs
        assert "issuer" not in call_kwargs
        assert "iss" not in call_kwargs["options"]["require"]


# ---------------------------------------------------------------------------
# ClerkAuthProvider construction tests
# ---------------------------------------------------------------------------


class TestClerkAuthProviderConstruction:
    """Test construction-time behaviour of ClerkAuthProvider."""

    def test_construction_with_explicit_jwks_url(self):
        """Explicit jwks_url bypasses environment variable lookup."""
        with patch("skillmeat.api.auth.clerk_provider.jwt.PyJWKClient"):
            provider = ClerkAuthProvider(jwks_url="https://example.com/jwks.json")
        assert provider._jwks_url == "https://example.com/jwks.json"

    def test_construction_reads_env_var_when_url_omitted(self, monkeypatch):
        """Without explicit URL, CLERK_JWKS_URL environment variable is used."""
        monkeypatch.setenv("CLERK_JWKS_URL", "https://env.example.com/.well-known/jwks.json")
        with patch("skillmeat.api.auth.clerk_provider.jwt.PyJWKClient"):
            provider = ClerkAuthProvider()
        assert provider._jwks_url == "https://env.example.com/.well-known/jwks.json"

    def test_construction_raises_when_env_var_missing(self, monkeypatch):
        """RuntimeError raised at construction when CLERK_JWKS_URL is not set."""
        monkeypatch.delenv("CLERK_JWKS_URL", raising=False)
        with patch("skillmeat.api.auth.clerk_provider.jwt.PyJWKClient"):
            with pytest.raises(RuntimeError, match="CLERK_JWKS_URL"):
                ClerkAuthProvider()

    def test_construction_stores_audience_and_issuer(self):
        """audience and issuer parameters are stored on the instance."""
        with patch("skillmeat.api.auth.clerk_provider.jwt.PyJWKClient"):
            provider = ClerkAuthProvider(
                jwks_url="https://example.com/jwks.json",
                audience="https://my-app.example.com",
                issuer="https://clerk.my-app.example.com",
            )
        assert provider._expected_audience == "https://my-app.example.com"
        assert provider._expected_issuer == "https://clerk.my-app.example.com"

    def test_construction_defaults_audience_and_issuer_to_none(self):
        """audience and issuer default to None when not supplied."""
        with patch("skillmeat.api.auth.clerk_provider.jwt.PyJWKClient"):
            provider = ClerkAuthProvider(jwks_url="https://example.com/jwks.json")
        assert provider._expected_audience is None
        assert provider._expected_issuer is None


# ---------------------------------------------------------------------------
# _str_to_uuid helper tests
# ---------------------------------------------------------------------------


class TestStrToUuid:
    """The _str_to_uuid helper must produce stable UUID5 values."""

    def test_deterministic_output(self):
        """Same input always produces the same UUID."""
        result1 = _str_to_uuid("user_stable")
        result2 = _str_to_uuid("user_stable")
        assert result1 == result2

    def test_different_inputs_produce_different_uuids(self):
        """Different inputs must not collide."""
        assert _str_to_uuid("user_a") != _str_to_uuid("user_b")

    def test_returns_uuid_instance(self):
        """Return type must be uuid.UUID."""
        result = _str_to_uuid("user_check")
        assert isinstance(result, uuid.UUID)


# ---------------------------------------------------------------------------
# require_auth tests
# ---------------------------------------------------------------------------


class TestRequireAuth:
    """require_auth dependency factory: authentication + scope enforcement."""

    # ------------------------------------------------------------------
    # Minimal FastAPI app for integration-style dependency testing
    # ------------------------------------------------------------------

    @pytest.fixture(autouse=True)
    def reset_auth_provider(self):
        """Reset the global auth provider between tests to avoid state leakage."""
        import skillmeat.api.dependencies as deps

        original = deps._auth_provider
        yield
        deps._auth_provider = original

    @pytest.fixture
    def local_provider(self) -> LocalAuthProvider:
        return LocalAuthProvider()

    @pytest.fixture
    def app_with_local_auth(self, local_provider) -> FastAPI:
        """Minimal FastAPI app with LocalAuthProvider for basic auth tests."""
        from skillmeat.api.dependencies import require_auth, set_auth_provider

        set_auth_provider(local_provider)
        test_app = FastAPI()

        @test_app.get("/no-scope")
        async def no_scope_endpoint(
            auth: AuthContext = pytest.importorskip("fastapi").Depends(require_auth()),
        ):
            return {"user_id": str(auth.user_id)}

        @test_app.get("/with-scope")
        async def with_scope_endpoint(
            auth: AuthContext = pytest.importorskip("fastapi").Depends(
                require_auth(scopes=[Scope.artifact_read.value])
            ),
        ):
            return {"user_id": str(auth.user_id), "scope_ok": True}

        return test_app

    @pytest.fixture
    def app_with_restricted_auth(self) -> FastAPI:
        """Minimal FastAPI app with a read-only provider for scope-rejection tests.

        LocalAuthProvider always holds admin:* and therefore never triggers a
        403.  This fixture installs a narrow-scope provider so that a required
        write scope correctly produces a 403.
        """
        from skillmeat.api.auth.provider import AuthProvider
        from skillmeat.api.dependencies import require_auth, set_auth_provider

        read_only_ctx = AuthContext(
            user_id=uuid.uuid4(),
            tenant_id=None,
            roles=[Role.viewer.value],
            scopes=[Scope.artifact_read.value],  # write scopes intentionally absent
        )

        class _ReadOnlyProvider(AuthProvider):
            async def validate(self, request: Request) -> AuthContext:
                return read_only_ctx

        set_auth_provider(_ReadOnlyProvider())
        scoped_app = FastAPI()

        @scoped_app.get("/requires-write")
        async def requires_write(
            auth: AuthContext = pytest.importorskip("fastapi").Depends(
                require_auth(scopes=[Scope.artifact_write.value])
            ),
        ):
            return {"user_id": str(auth.user_id)}

        return scoped_app

    @pytest.fixture
    def test_client(self, app_with_local_auth) -> TestClient:
        return TestClient(app_with_local_auth, raise_server_exceptions=False)

    @pytest.fixture
    def restricted_client(self, app_with_restricted_auth) -> TestClient:
        return TestClient(app_with_restricted_auth, raise_server_exceptions=False)

    # ------------------------------------------------------------------
    # No-scope usage pattern
    # ------------------------------------------------------------------

    def test_require_auth_returns_auth_context(self, test_client):
        """require_auth() with no scopes injects an AuthContext."""
        response = test_client.get("/no-scope")
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data

    def test_require_auth_no_scopes_passes(self, test_client):
        """require_auth() with no scopes never raises 403."""
        response = test_client.get("/no-scope")
        assert response.status_code != 403

    # ------------------------------------------------------------------
    # Scope validation
    # ------------------------------------------------------------------

    def test_require_auth_validates_scopes_pass(self, test_client):
        """require_auth(scopes=[...]) passes when the context holds the scope."""
        response = test_client.get("/with-scope")
        assert response.status_code == 200
        assert response.json()["scope_ok"] is True

    def test_require_auth_validates_scopes_fail(self, restricted_client):
        """require_auth(scopes=[...]) returns 403 when a required scope is missing.

        Uses a read-only provider (viewer context) that does not hold the
        artifact:write scope.  LocalAuthProvider always carries admin:* so it
        cannot be used to trigger 403 — a restricted provider is required.
        """
        response = restricted_client.get("/requires-write")
        assert response.status_code == 403

    # ------------------------------------------------------------------
    # 503 when no provider configured
    # ------------------------------------------------------------------

    def test_require_auth_503_when_no_provider_configured(self):
        """require_auth raises 503 when no auth provider has been registered."""
        import skillmeat.api.dependencies as deps
        from skillmeat.api.dependencies import require_auth

        deps._auth_provider = None
        minimal_app = FastAPI()

        @minimal_app.get("/protected")
        async def protected(
            auth: AuthContext = pytest.importorskip("fastapi").Depends(require_auth()),
        ):
            return {"ok": True}

        client = TestClient(minimal_app, raise_server_exceptions=False)
        response = client.get("/protected")
        assert response.status_code == 503

    # ------------------------------------------------------------------
    # Works with a mock Clerk provider
    # ------------------------------------------------------------------

    def test_require_auth_works_with_clerk_provider(self):
        """require_auth resolves correctly when backed by a mock Clerk-like provider."""
        import skillmeat.api.dependencies as deps
        from skillmeat.api.auth.provider import AuthProvider
        from skillmeat.api.dependencies import require_auth, set_auth_provider

        expected_ctx = AuthContext(
            user_id=uuid.uuid4(),
            tenant_id=None,
            roles=[Role.team_member.value],
            scopes=[Scope.artifact_read.value],
        )

        class _MockClerkProvider(AuthProvider):
            async def validate(self, request: Request) -> AuthContext:
                return expected_ctx

        set_auth_provider(_MockClerkProvider())
        mock_app = FastAPI()

        @mock_app.get("/guarded")
        async def guarded(
            auth: AuthContext = pytest.importorskip("fastapi").Depends(require_auth()),
        ):
            return {"user_id": str(auth.user_id)}

        client = TestClient(mock_app, raise_server_exceptions=False)
        response = client.get("/guarded")
        assert response.status_code == 200
        assert response.json()["user_id"] == str(expected_ctx.user_id)

    def test_require_auth_with_clerk_provider_scope_fail_returns_403(self):
        """require_auth raises 403 when the Clerk context lacks the required scope."""
        import skillmeat.api.dependencies as deps
        from skillmeat.api.auth.provider import AuthProvider
        from skillmeat.api.dependencies import require_auth, set_auth_provider

        # Viewer context: no write scopes
        viewer_ctx = AuthContext(
            user_id=uuid.uuid4(),
            tenant_id=None,
            roles=[Role.viewer.value],
            scopes=[Scope.artifact_read.value],
        )

        class _ViewerProvider(AuthProvider):
            async def validate(self, request: Request) -> AuthContext:
                return viewer_ctx

        set_auth_provider(_ViewerProvider())
        mock_app = FastAPI()

        @mock_app.post("/write-only")
        async def write_only(
            auth: AuthContext = pytest.importorskip("fastapi").Depends(
                require_auth(scopes=[Scope.artifact_write.value])
            ),
        ):
            return {"ok": True}

        client = TestClient(mock_app, raise_server_exceptions=False)
        response = client.post("/write-only")
        assert response.status_code == 403

    # ------------------------------------------------------------------
    # WIRE-003: request.state.auth_context is populated
    # ------------------------------------------------------------------

    def test_require_auth_sets_request_state_auth_context(self):
        """require_auth stores the AuthContext on request.state.auth_context."""
        from skillmeat.api.auth.provider import AuthProvider
        from skillmeat.api.dependencies import require_auth, set_auth_provider

        expected_ctx = AuthContext(
            user_id=uuid.uuid4(),
            tenant_id=None,
            roles=[Role.team_member.value],
            scopes=[Scope.artifact_read.value],
        )
        captured: dict = {}

        class _CapturingProvider(AuthProvider):
            async def validate(self, request: Request) -> AuthContext:
                return expected_ctx

        set_auth_provider(_CapturingProvider())
        state_app = FastAPI()

        @state_app.get("/check-state")
        async def check_state(
            request: Request,
            auth: AuthContext = pytest.importorskip("fastapi").Depends(require_auth()),
        ):
            # Capture whatever was stored on request.state
            captured["auth_context"] = getattr(request.state, "auth_context", None)
            return {"user_id": str(auth.user_id)}

        client = TestClient(state_app, raise_server_exceptions=False)
        response = client.get("/check-state")
        assert response.status_code == 200
        assert captured["auth_context"] is expected_ctx


# ---------------------------------------------------------------------------
# AuthContext helper method tests (indirect via provider output)
# ---------------------------------------------------------------------------


class TestAuthContextHelpers:
    """Verify AuthContext helper methods via real instances."""

    def test_has_role_with_enum(self):
        ctx = AuthContext(
            user_id=uuid.uuid4(),
            roles=[Role.team_admin.value],
            scopes=[],
        )
        assert ctx.has_role(Role.team_admin)
        assert not ctx.has_role(Role.system_admin)

    def test_has_role_with_string(self):
        ctx = AuthContext(
            user_id=uuid.uuid4(),
            roles=["team_member"],
            scopes=[],
        )
        assert ctx.has_role("team_member")
        assert not ctx.has_role("system_admin")

    def test_has_scope_with_enum(self):
        ctx = AuthContext(
            user_id=uuid.uuid4(),
            roles=[],
            scopes=[Scope.artifact_read.value],
        )
        assert ctx.has_scope(Scope.artifact_read)
        assert not ctx.has_scope(Scope.artifact_write)

    def test_has_scope_admin_wildcard_grants_all(self):
        ctx = AuthContext(
            user_id=uuid.uuid4(),
            roles=[Role.system_admin.value],
            scopes=[Scope.admin_wildcard.value],
        )
        for scope in Scope:
            assert ctx.has_scope(scope), f"admin wildcard should grant {scope}"

    def test_has_any_scope_returns_true_on_partial_match(self):
        ctx = AuthContext(
            user_id=uuid.uuid4(),
            roles=[],
            scopes=[Scope.artifact_read.value],
        )
        assert ctx.has_any_scope(Scope.artifact_read, Scope.artifact_write)

    def test_has_any_scope_returns_false_when_none_match(self):
        ctx = AuthContext(
            user_id=uuid.uuid4(),
            roles=[],
            scopes=[Scope.deployment_read.value],
        )
        assert not ctx.has_any_scope(Scope.artifact_read, Scope.artifact_write)

    def test_is_admin_true_for_system_admin(self):
        ctx = AuthContext(
            user_id=uuid.uuid4(),
            roles=[Role.system_admin.value],
            scopes=[],
        )
        assert ctx.is_admin()

    def test_is_admin_false_for_team_admin(self):
        ctx = AuthContext(
            user_id=uuid.uuid4(),
            roles=[Role.team_admin.value],
            scopes=[],
        )
        assert not ctx.is_admin()
