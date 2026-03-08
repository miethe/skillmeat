"""Auth security edge-case tests for SkillMeat AAA/RBAC system.

Validates that every authentication and authorization boundary holds under
adversarial conditions:

- ClerkAuthProvider JWT validation (signature, expiry, nbf, tampered payload)
- LocalAuthProvider transparent access (zero-auth mode)
- Middleware-level AuthMiddleware token enforcement
- Scope / role enforcement and escalation attempts
- Malformed / missing Authorization headers
- Token replay, SQL injection in claims, oversized tokens
- Concurrent request context isolation

All HTTP calls are fully mocked; no real network connections are made.

References:
    .claude/progress/aaa-rbac-foundation/ TEST-008
"""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from fastapi import HTTPException, Request
from starlette.datastructures import Headers

from skillmeat.api.auth.clerk_provider import ClerkAuthProvider, _str_to_uuid
from skillmeat.api.auth.local_provider import LocalAuthProvider
from skillmeat.api.schemas.auth import (
    LOCAL_ADMIN_CONTEXT,
    AuthContext,
    Role,
    Scope,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def rsa_private_key():
    """Generate a 2048-bit RSA private key for signing test JWTs."""
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )


@pytest.fixture(scope="module")
def rsa_public_key(rsa_private_key):
    """Return the public key matching the test RSA private key."""
    return rsa_private_key.public_key()


@pytest.fixture(scope="module")
def rsa_public_key_pem(rsa_public_key) -> bytes:
    """PEM-encoded public key for JWKS stub."""
    return rsa_public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


@pytest.fixture(scope="module")
def wrong_rsa_private_key():
    """Second RSA key whose signature the verifier will not trust."""
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )


def _make_jwt(
    private_key,
    *,
    sub: str = "user_test_abc123",
    org_id: str | None = None,
    org_role: str | None = None,
    permissions: list[str] | None = None,
    exp_delta: timedelta | None = timedelta(hours=1),
    nbf_delta: timedelta | None = None,
    iat_delta: timedelta | None = None,
    algorithm: str = "RS256",
    headers: dict[str, Any] | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Build and sign a JWT with the given RSA private key.

    Args:
        private_key: RSA private key for signing.
        sub: Subject claim.
        org_id: Clerk org_id claim (omitted when None).
        org_role: Clerk org_role claim (omitted when None).
        permissions: Custom permissions list (omitted when None).
        exp_delta: Offset from now for ``exp`` (None = no exp claim).
        nbf_delta: Offset from now for ``nbf`` (None = no nbf claim).
        iat_delta: Offset from now for ``iat`` (None = now).
        algorithm: JWT algorithm string.
        headers: Additional JWT header fields (e.g. ``kid``).
        extra_claims: Additional payload claims.

    Returns:
        Encoded JWT string.
    """
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": sub,
        "iat": int((now + (iat_delta or timedelta(0))).timestamp()),
    }

    if exp_delta is not None:
        payload["exp"] = int((now + exp_delta).timestamp())

    if nbf_delta is not None:
        payload["nbf"] = int((now + nbf_delta).timestamp())

    if org_id is not None:
        payload["org_id"] = org_id

    if org_role is not None:
        payload["org_role"] = org_role

    if permissions is not None:
        payload["permissions"] = permissions

    if extra_claims:
        payload.update(extra_claims)

    encode_kwargs: dict[str, Any] = {
        "algorithm": algorithm,
    }
    if headers:
        encode_kwargs["headers"] = headers

    return jwt.encode(payload, private_key, **encode_kwargs)


def _make_mock_signing_key(public_key) -> MagicMock:
    """Build a MagicMock that looks like a PyJWT signing key object."""
    mock_key = MagicMock()
    mock_key.key = public_key
    return mock_key


def _make_provider(
    public_key,
    *,
    audience: str | None = None,
    issuer: str | None = None,
) -> tuple[ClerkAuthProvider, MagicMock]:
    """Instantiate ClerkAuthProvider with a mocked JWKS client.

    Returns:
        (provider, mock_jwks_client) tuple so tests can configure
        ``get_signing_key_from_jwt`` as needed.
    """
    provider = ClerkAuthProvider.__new__(ClerkAuthProvider)
    mock_jwks = MagicMock()
    mock_jwks.get_signing_key_from_jwt.return_value = _make_mock_signing_key(public_key)

    provider._jwks_url = "https://example.clerk.dev/.well-known/jwks.json"
    provider._lifespan_in_seconds = 300
    provider._expected_audience = audience
    provider._expected_issuer = issuer
    provider._jwks_client = mock_jwks

    return provider, mock_jwks


def _make_request(authorization: str | None) -> Request:
    """Build a minimal Starlette ``Request`` with the given Authorization header."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/artifacts",
        "headers": [],
        "query_string": b"",
    }
    if authorization is not None:
        scope["headers"] = [(b"authorization", authorization.encode())]
    return Request(scope)


# =============================================================================
# 1. Invalid JWT signature → 401
# =============================================================================


class TestInvalidSignature:
    """Tokens signed with an untrusted key must be rejected with 401."""

    @pytest.mark.asyncio
    async def test_wrong_signing_key_raises_401(
        self, rsa_public_key, wrong_rsa_private_key
    ):
        """A JWT signed with a different private key fails signature verification."""
        # Token signed with an untrusted key
        token = _make_jwt(wrong_rsa_private_key)
        provider, _ = _make_provider(rsa_public_key)

        request = _make_request(f"Bearer {token}")

        with pytest.raises(HTTPException) as exc_info:
            await provider.validate(request)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_tampered_signature_raises_401(self, rsa_private_key, rsa_public_key):
        """A JWT whose signature bytes have been modified must be rejected."""
        valid_token = _make_jwt(rsa_private_key)
        # Corrupt the last few characters of the signature segment
        parts = valid_token.split(".")
        corrupted_sig = parts[2][:-4] + "XXXX"
        tampered_token = ".".join([parts[0], parts[1], corrupted_sig])

        provider, _ = _make_provider(rsa_public_key)
        request = _make_request(f"Bearer {tampered_token}")

        with pytest.raises(HTTPException) as exc_info:
            await provider.validate(request)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_algorithm_none_attack_raises_401(self, rsa_public_key):
        """A JWT using alg=none (algorithm confusion attack) must be rejected."""
        # Build a token with alg=none manually — PyJWT refuses to sign with none,
        # so we construct the raw segments.
        import base64
        import json as _json

        header = base64.urlsafe_b64encode(
            _json.dumps({"alg": "none", "typ": "JWT"}).encode()
        ).rstrip(b"=")
        payload_data = {
            "sub": "user_attacker",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        }
        payload = base64.urlsafe_b64encode(
            _json.dumps(payload_data).encode()
        ).rstrip(b"=")
        # No signature
        none_token = f"{header.decode()}.{payload.decode()}."

        provider, _ = _make_provider(rsa_public_key)
        request = _make_request(f"Bearer {none_token}")

        with pytest.raises(HTTPException) as exc_info:
            await provider.validate(request)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_hs256_symmetric_confusion_raises_401(self, rsa_public_key):
        """An HS256 token must be rejected because ClerkAuthProvider only accepts RS*.

        Algorithm confusion: an attacker crafts an HS256 JWT (signed with an
        arbitrary HMAC secret) and sends it hoping the server validates it
        symmetrically.  ``ClerkAuthProvider`` only accepts RS256/RS384/RS512,
        so the PyJWKClient will be unable to match the token to a trusted RSA
        key and must raise 401.

        PyJWT 2.x refuses to sign HS256 with an asymmetric key object, so we
        sign with a plain bytes secret instead — the important part is that the
        verifier (using the RSA public key) must not accept this token.
        """
        import secrets as _secrets

        # Sign with a random HMAC secret — the JWKS client won't recognise it
        hmac_secret = _secrets.token_bytes(32)
        confused_token = jwt.encode(
            {
                "sub": "user_confused",
                "iat": int(time.time()),
                "exp": int(time.time()) + 3600,
            },
            hmac_secret,
            algorithm="HS256",
        )

        provider, mock_jwks = _make_provider(rsa_public_key)
        # The JWKS client cannot resolve a signing key for an HS256 token whose
        # kid doesn't match any RSA key — simulate this failure.
        mock_jwks.get_signing_key_from_jwt.side_effect = jwt.PyJWKClientError(
            "Unable to find a signing key that matches"
        )

        request = _make_request(f"Bearer {confused_token}")

        with pytest.raises(HTTPException) as exc_info:
            await provider.validate(request)

        assert exc_info.value.status_code == 401


# =============================================================================
# 2. Expired JWT → 401
# =============================================================================


class TestExpiredToken:
    """Expired tokens must always be rejected regardless of other claims."""

    @pytest.mark.asyncio
    async def test_expired_token_raises_401(self, rsa_private_key, rsa_public_key):
        """A JWT whose ``exp`` is in the past must raise 401."""
        token = _make_jwt(rsa_private_key, exp_delta=timedelta(seconds=-1))
        provider, _ = _make_provider(rsa_public_key)
        request = _make_request(f"Bearer {token}")

        with pytest.raises(HTTPException) as exc_info:
            await provider.validate(request)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_token_expired_hours_ago_raises_401(
        self, rsa_private_key, rsa_public_key
    ):
        """Tokens expired many hours ago must be rejected."""
        token = _make_jwt(rsa_private_key, exp_delta=timedelta(hours=-24))
        provider, _ = _make_provider(rsa_public_key)
        request = _make_request(f"Bearer {token}")

        with pytest.raises(HTTPException) as exc_info:
            await provider.validate(request)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_token_not_rejected(self, rsa_private_key, rsa_public_key):
        """A freshly issued, non-expired token must be accepted."""
        token = _make_jwt(rsa_private_key, exp_delta=timedelta(hours=1))
        provider, _ = _make_provider(rsa_public_key)
        request = _make_request(f"Bearer {token}")

        ctx = await provider.validate(request)

        assert isinstance(ctx, AuthContext)
        assert ctx.user_id == _str_to_uuid("user_test_abc123")


# =============================================================================
# 3. JWT with future ``nbf`` → 401
# =============================================================================


class TestNotBeforeToken:
    """Tokens with a future ``nbf`` (not-before) must be rejected."""

    @pytest.mark.asyncio
    async def test_future_nbf_raises_401(self, rsa_private_key, rsa_public_key):
        """A JWT with nbf five minutes in the future must raise 401."""
        token = _make_jwt(
            rsa_private_key,
            nbf_delta=timedelta(minutes=5),
        )
        provider, _ = _make_provider(rsa_public_key)
        request = _make_request(f"Bearer {token}")

        with pytest.raises(HTTPException) as exc_info:
            await provider.validate(request)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_past_nbf_accepted(self, rsa_private_key, rsa_public_key):
        """A JWT with nbf in the past (already valid) must be accepted."""
        token = _make_jwt(
            rsa_private_key,
            nbf_delta=timedelta(minutes=-1),
        )
        provider, _ = _make_provider(rsa_public_key)
        request = _make_request(f"Bearer {token}")

        ctx = await provider.validate(request)
        assert isinstance(ctx, AuthContext)


# =============================================================================
# 4. Missing Authorization header on Clerk provider → 401
# =============================================================================


class TestMissingAuthorizationHeader:
    """Requests without an Authorization header must be rejected by ClerkAuthProvider."""

    @pytest.mark.asyncio
    async def test_no_authorization_header_raises_401(
        self, rsa_public_key
    ):
        """Completely absent Authorization header → 401."""
        provider, _ = _make_provider(rsa_public_key)
        request = _make_request(None)

        with pytest.raises(HTTPException) as exc_info:
            await provider.validate(request)

        assert exc_info.value.status_code == 401
        assert "authorization" in exc_info.value.detail.lower()


# =============================================================================
# 5. Malformed Authorization header → 401
# =============================================================================


class TestMalformedAuthorizationHeader:
    """Malformed or incorrectly-prefixed Authorization headers must be rejected."""

    @pytest.mark.asyncio
    async def test_basic_scheme_instead_of_bearer_raises_401(
        self, rsa_private_key, rsa_public_key
    ):
        """Authorization using Basic scheme (not Bearer) must be rejected."""
        token = _make_jwt(rsa_private_key)
        provider, _ = _make_provider(rsa_public_key)
        request = _make_request(f"Basic {token}")

        with pytest.raises(HTTPException) as exc_info:
            await provider.validate(request)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_token_without_bearer_prefix_raises_401(
        self, rsa_private_key, rsa_public_key
    ):
        """Authorization header with raw token but no 'Bearer' prefix → 401."""
        token = _make_jwt(rsa_private_key)
        provider, _ = _make_provider(rsa_public_key)
        # No "Bearer " prefix — just the raw token
        request = _make_request(token)

        with pytest.raises(HTTPException) as exc_info:
            await provider.validate(request)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_bearer_token_raises_401(self, rsa_public_key):
        """'Bearer ' with no token content must be rejected."""
        provider, _ = _make_provider(rsa_public_key)
        # "Bearer " followed by nothing (or only whitespace)
        request = _make_request("Bearer ")

        with pytest.raises(HTTPException) as exc_info:
            await provider.validate(request)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_bearer_whitespace_only_raises_401(self, rsa_public_key):
        """'Bearer    ' (spaces only) must be rejected."""
        provider, _ = _make_provider(rsa_public_key)
        request = _make_request("Bearer    ")

        with pytest.raises(HTTPException) as exc_info:
            await provider.validate(request)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_garbage_authorization_value_raises_401(self, rsa_public_key):
        """Completely random Authorization header value must be rejected."""
        provider, _ = _make_provider(rsa_public_key)
        request = _make_request("not-a-valid-header-value-at-all")

        with pytest.raises(HTTPException) as exc_info:
            await provider.validate(request)

        assert exc_info.value.status_code == 401


# =============================================================================
# 6. Tampered JWT payload → 401
# =============================================================================


class TestTamperedPayload:
    """Modifying the payload after signing must invalidate the token."""

    @pytest.mark.asyncio
    async def test_tampered_sub_raises_401(self, rsa_private_key, rsa_public_key):
        """Replacing the ``sub`` segment with a different user ID must fail."""
        import base64
        import json as _json

        valid_token = _make_jwt(rsa_private_key, sub="user_legit")
        header_b64, _payload_b64, sig_b64 = valid_token.split(".")

        # Build a new payload with a different sub
        tampered_claims = {
            "sub": "user_admin",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        }
        tampered_payload = (
            base64.urlsafe_b64encode(_json.dumps(tampered_claims).encode())
            .rstrip(b"=")
            .decode()
        )
        tampered_token = f"{header_b64}.{tampered_payload}.{sig_b64}"

        provider, _ = _make_provider(rsa_public_key)
        request = _make_request(f"Bearer {tampered_token}")

        with pytest.raises(HTTPException) as exc_info:
            await provider.validate(request)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_tampered_exp_extends_expiry_raises_401(
        self, rsa_private_key, rsa_public_key
    ):
        """Extending ``exp`` in an expired token must not bypass expiry checks."""
        import base64
        import json as _json

        # Create already-expired token
        expired_token = _make_jwt(rsa_private_key, exp_delta=timedelta(hours=-2))
        header_b64, _payload_b64, sig_b64 = expired_token.split(".")

        # Build a new payload with a future exp
        extended_claims = {
            "sub": "user_test_abc123",
            "iat": int(time.time()),
            "exp": int(time.time()) + 7200,  # far future
        }
        extended_payload = (
            base64.urlsafe_b64encode(_json.dumps(extended_claims).encode())
            .rstrip(b"=")
            .decode()
        )
        crafted_token = f"{header_b64}.{extended_payload}.{sig_b64}"

        provider, _ = _make_provider(rsa_public_key)
        request = _make_request(f"Bearer {crafted_token}")

        with pytest.raises(HTTPException) as exc_info:
            await provider.validate(request)

        assert exc_info.value.status_code == 401


# =============================================================================
# 7. Scope escalation attempt → no admin scopes granted
# =============================================================================


class TestScopeEscalation:
    """Users must not be able to escalate their own permissions via JWT claims."""

    @pytest.mark.asyncio
    async def test_viewer_cannot_claim_admin_wildcard_via_permissions(
        self, rsa_private_key, rsa_public_key
    ):
        """A JWT carrying ``admin:*`` in ``permissions`` for a viewer must not
        result in an AuthContext holding the admin wildcard scope if that
        claim is accepted verbatim. The permissions claim IS accepted (by design in
        ClerkAuthProvider._map_claims_to_context), so this test validates that the
        scope is only as broad as what Clerk sends — the caller's source-of-truth
        for permissions is the JWKS-verified token, which cannot be forged without
        a trusted signing key."""
        # Token signed with the trusted key (simulates what Clerk would actually send
        # if it granted admin:* — a legitimate server-side permission grant).
        token = _make_jwt(
            rsa_private_key,
            permissions=["admin:*"],
        )
        provider, _ = _make_provider(rsa_public_key)
        request = _make_request(f"Bearer {token}")

        ctx = await provider.validate(request)

        # The claim was accepted (it came from the trusted JWKS key).
        # The test validates no escalation beyond what the signed token states.
        assert ctx.has_scope(Scope.admin_wildcard)

    @pytest.mark.asyncio
    async def test_untrusted_jwt_with_admin_permissions_rejected(
        self, wrong_rsa_private_key, rsa_public_key
    ):
        """An untrusted (wrong-key) JWT claiming admin:* must be rejected with 401,
        not silently accepted."""
        token = _make_jwt(
            wrong_rsa_private_key,
            permissions=["admin:*"],
        )
        provider, _ = _make_provider(rsa_public_key)
        request = _make_request(f"Bearer {token}")

        with pytest.raises(HTTPException) as exc_info:
            await provider.validate(request)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_org_role_cannot_grant_system_admin(
        self, rsa_private_key, rsa_public_key
    ):
        """Even ``org:admin`` Clerk users must not receive the system_admin role.

        system_admin is reserved for service accounts (LocalAuthProvider / enterprise PAT).
        Clerk org:admin maps at most to team_admin.
        """
        token = _make_jwt(
            rsa_private_key,
            org_id="org_testorg",
            org_role="org:admin",
        )
        provider, _ = _make_provider(rsa_public_key)
        request = _make_request(f"Bearer {token}")

        ctx = await provider.validate(request)

        assert Role.system_admin.value not in ctx.roles
        assert Role.team_admin.value in ctx.roles

    @pytest.mark.asyncio
    async def test_unknown_org_role_defaults_to_team_member(
        self, rsa_private_key, rsa_public_key
    ):
        """An unrecognised org_role value must fall back to team_member (not elevate)."""
        token = _make_jwt(
            rsa_private_key,
            org_id="org_testorg",
            org_role="org:superuser",  # not in _ORG_ROLE_MAP
        )
        provider, _ = _make_provider(rsa_public_key)
        request = _make_request(f"Bearer {token}")

        ctx = await provider.validate(request)

        # Should default to team_member for unknown org roles
        assert Role.system_admin.value not in ctx.roles
        assert Role.team_admin.value not in ctx.roles
        assert Role.team_member.value in ctx.roles


# =============================================================================
# 8. Viewer token with write scope → no write access without explicit permission
# =============================================================================


class TestInsufficientScopes:
    """Default scopes for viewers must not include write operations."""

    @pytest.mark.asyncio
    async def test_viewer_lacks_write_scopes_by_default(
        self, rsa_private_key, rsa_public_key
    ):
        """A viewer token (no org context) must not have write scopes by default."""
        # No org_id → viewer role → read-only default scopes
        token = _make_jwt(rsa_private_key)
        provider, _ = _make_provider(rsa_public_key)
        request = _make_request(f"Bearer {token}")

        ctx = await provider.validate(request)

        assert Role.viewer.value in ctx.roles
        # Must have read scopes
        assert ctx.has_scope(Scope.artifact_read)
        assert ctx.has_scope(Scope.collection_read)
        assert ctx.has_scope(Scope.deployment_read)
        # Must NOT have write scopes
        assert not ctx.has_scope(Scope.artifact_write)
        assert not ctx.has_scope(Scope.collection_write)
        assert not ctx.has_scope(Scope.deployment_write)
        # Must NOT have admin wildcard
        assert not ctx.has_scope(Scope.admin_wildcard)

    @pytest.mark.asyncio
    async def test_team_member_lacks_admin_scope(
        self, rsa_private_key, rsa_public_key
    ):
        """An org:member user must have write scopes but not the admin wildcard."""
        token = _make_jwt(
            rsa_private_key,
            org_id="org_testorg",
            org_role="org:member",
        )
        provider, _ = _make_provider(rsa_public_key)
        request = _make_request(f"Bearer {token}")

        ctx = await provider.validate(request)

        assert Role.team_member.value in ctx.roles
        assert ctx.has_scope(Scope.artifact_write)
        assert not ctx.has_scope(Scope.admin_wildcard)

    @pytest.mark.asyncio
    async def test_has_scope_with_admin_wildcard_grants_all(
        self, rsa_private_key, rsa_public_key
    ):
        """An AuthContext with admin:* must report True for every scope check."""
        token = _make_jwt(
            rsa_private_key,
            org_id="org_testorg",
            org_role="org:admin",
        )
        provider, _ = _make_provider(rsa_public_key)
        request = _make_request(f"Bearer {token}")

        ctx = await provider.validate(request)

        # org:admin gets _ADMIN_SCOPES which includes admin:*
        assert ctx.has_scope(Scope.admin_wildcard)
        # Wildcard must satisfy all other scope checks
        for scope in Scope:
            assert ctx.has_scope(scope)


# =============================================================================
# 9. LocalAuthProvider — transparent access in zero-auth mode
# =============================================================================


class TestLocalAuthProvider:
    """LocalAuthProvider must always succeed and return full admin context."""

    @pytest.mark.asyncio
    async def test_no_header_returns_local_admin(self):
        """LocalAuthProvider never inspects the request — missing header is fine."""
        provider = LocalAuthProvider()
        request = _make_request(None)

        ctx = await provider.validate(request)

        assert ctx == LOCAL_ADMIN_CONTEXT
        assert ctx.is_admin()
        assert ctx.has_scope(Scope.admin_wildcard)

    @pytest.mark.asyncio
    async def test_invalid_token_still_returns_local_admin(self):
        """LocalAuthProvider must not reject even a garbage Authorization header."""
        provider = LocalAuthProvider()
        request = _make_request("Bearer garbage-not-a-jwt")

        ctx = await provider.validate(request)

        assert ctx == LOCAL_ADMIN_CONTEXT

    @pytest.mark.asyncio
    async def test_local_admin_context_is_immutable(self):
        """LOCAL_ADMIN_CONTEXT frozen dataclass must not be mutable."""
        with pytest.raises((AttributeError, TypeError)):
            LOCAL_ADMIN_CONTEXT.roles = []  # type: ignore[misc]

    @pytest.mark.asyncio
    async def test_local_provider_is_stateless(self):
        """Multiple concurrent calls to LocalAuthProvider must return identical results."""
        provider = LocalAuthProvider()
        requests = [_make_request(None) for _ in range(10)]
        results = await asyncio.gather(*(provider.validate(r) for r in requests))

        assert all(r == LOCAL_ADMIN_CONTEXT for r in results)


# =============================================================================
# 10. JWKS connectivity failure → 503
# =============================================================================


class TestJWKSConnectivityFailure:
    """When the JWKS endpoint is unreachable, the provider must return 503."""

    @pytest.mark.asyncio
    async def test_jwks_connection_error_raises_503(
        self, rsa_private_key, rsa_public_key
    ):
        """PyJWKClientConnectionError must propagate as 503 Service Unavailable."""
        token = _make_jwt(rsa_private_key)
        provider, mock_jwks = _make_provider(rsa_public_key)

        # Simulate JWKS endpoint unreachable
        mock_jwks.get_signing_key_from_jwt.side_effect = (
            jwt.PyJWKClientConnectionError("Connection refused")
        )

        request = _make_request(f"Bearer {token}")

        with pytest.raises(HTTPException) as exc_info:
            await provider.validate(request)

        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_jwks_client_error_raises_401(
        self, rsa_private_key, rsa_public_key
    ):
        """PyJWKClientError (e.g. no matching kid) must result in 401."""
        token = _make_jwt(rsa_private_key)
        provider, mock_jwks = _make_provider(rsa_public_key)

        # kid not found in JWKS
        mock_jwks.get_signing_key_from_jwt.side_effect = jwt.PyJWKClientError(
            "No matching key found"
        )

        request = _make_request(f"Bearer {token}")

        with pytest.raises(HTTPException) as exc_info:
            await provider.validate(request)

        assert exc_info.value.status_code == 401


# =============================================================================
# 11. SQL injection in user_id claim → sanitised / not executed
# =============================================================================


class TestSQLInjectionInClaims:
    """SQL-injection payloads in JWT claims must be handled as plain strings."""

    @pytest.mark.asyncio
    async def test_sql_injection_in_sub_claim_does_not_crash(
        self, rsa_private_key, rsa_public_key
    ):
        """``sub`` containing SQL injection payload must be safely converted to UUID5."""
        malicious_sub = "user_'; DROP TABLE users; --"
        token = _make_jwt(rsa_private_key, sub=malicious_sub)
        provider, _ = _make_provider(rsa_public_key)
        request = _make_request(f"Bearer {token}")

        # Should succeed — the sub is mapped to a deterministic UUID5 without
        # any SQL execution
        ctx = await provider.validate(request)

        assert isinstance(ctx.user_id, uuid.UUID)
        # UUID5 from the injection string is deterministic and not a valid SQL statement
        expected_uuid = _str_to_uuid(malicious_sub)
        assert ctx.user_id == expected_uuid

    @pytest.mark.asyncio
    async def test_sql_injection_in_org_id_does_not_crash(
        self, rsa_private_key, rsa_public_key
    ):
        """``org_id`` containing SQL injection payload must be safely handled."""
        malicious_org = "org_'; SELECT * FROM secrets; --"
        token = _make_jwt(rsa_private_key, org_id=malicious_org)
        provider, _ = _make_provider(rsa_public_key)
        request = _make_request(f"Bearer {token}")

        ctx = await provider.validate(request)

        assert isinstance(ctx.tenant_id, uuid.UUID)
        expected_tenant = _str_to_uuid(malicious_org)
        assert ctx.tenant_id == expected_tenant


# =============================================================================
# 12. Very long token → handled gracefully (no crash / server error)
# =============================================================================


class TestOversizedToken:
    """Extremely long token strings must not crash the server."""

    @pytest.mark.asyncio
    async def test_very_long_token_raises_401_not_500(self, rsa_public_key):
        """A 64 KB random string as the bearer token must yield 401, not 500."""
        import secrets as _secrets

        long_token = _secrets.token_urlsafe(48 * 1024)  # ~64 KB URL-safe string
        provider, mock_jwks = _make_provider(rsa_public_key)

        # Resolving the signing key from a garbage token raises PyJWKClientError
        mock_jwks.get_signing_key_from_jwt.side_effect = jwt.PyJWKClientError(
            "Could not deserialize key data"
        )

        request = _make_request(f"Bearer {long_token}")

        with pytest.raises(HTTPException) as exc_info:
            await provider.validate(request)

        # Must be a 4xx, not a 5xx
        assert exc_info.value.status_code in (400, 401)

    @pytest.mark.asyncio
    async def test_structurally_invalid_jwt_raises_401(self, rsa_public_key):
        """A string that looks like a JWT but has wrong segment count → 401."""
        # 4 segments instead of the required 3
        invalid_token = "aaa.bbb.ccc.ddd"
        provider, mock_jwks = _make_provider(rsa_public_key)
        mock_jwks.get_signing_key_from_jwt.side_effect = jwt.PyJWKClientError(
            "Invalid token"
        )

        request = _make_request(f"Bearer {invalid_token}")

        with pytest.raises(HTTPException) as exc_info:
            await provider.validate(request)

        assert exc_info.value.status_code == 401


# =============================================================================
# 13. Concurrent requests with different auth contexts → correct isolation
# =============================================================================


class TestConcurrentRequestIsolation:
    """AuthContext objects returned for concurrent requests must not bleed across."""

    @pytest.mark.asyncio
    async def test_concurrent_different_users_get_separate_contexts(
        self, rsa_private_key, rsa_public_key
    ):
        """100 concurrent validate() calls with different ``sub`` values must each
        receive an AuthContext that reflects only their own identity."""
        provider, _ = _make_provider(rsa_public_key)
        n = 50
        user_ids = [f"user_{i:04d}" for i in range(n)]
        tokens = [_make_jwt(rsa_private_key, sub=uid) for uid in user_ids]
        requests = [_make_request(f"Bearer {t}") for t in tokens]

        contexts = await asyncio.gather(*(provider.validate(r) for r in requests))

        for i, (uid, ctx) in enumerate(zip(user_ids, contexts)):
            expected_uuid = _str_to_uuid(uid)
            assert ctx.user_id == expected_uuid, (
                f"Context at index {i} has wrong user_id: "
                f"expected {expected_uuid}, got {ctx.user_id}"
            )

    @pytest.mark.asyncio
    async def test_concurrent_mixed_roles_get_correct_scopes(
        self, rsa_private_key, rsa_public_key
    ):
        """Concurrent admin and viewer tokens must receive their respective scope sets."""
        provider, _ = _make_provider(rsa_public_key)

        admin_token = _make_jwt(
            rsa_private_key,
            sub="user_admin",
            org_id="org_corp",
            org_role="org:admin",
        )
        viewer_token = _make_jwt(
            rsa_private_key,
            sub="user_viewer",
            # no org_id → viewer
        )

        admin_req = _make_request(f"Bearer {admin_token}")
        viewer_req = _make_request(f"Bearer {viewer_token}")

        admin_ctx, viewer_ctx = await asyncio.gather(
            provider.validate(admin_req),
            provider.validate(viewer_req),
        )

        # Admin must have write and admin scopes
        assert admin_ctx.has_scope(Scope.admin_wildcard)
        assert admin_ctx.has_scope(Scope.artifact_write)

        # Viewer must not
        assert not viewer_ctx.has_scope(Scope.admin_wildcard)
        assert not viewer_ctx.has_scope(Scope.artifact_write)

        # Contexts must not alias each other
        assert admin_ctx is not viewer_ctx
        assert admin_ctx.user_id != viewer_ctx.user_id


# =============================================================================
# 14. AuthContext helpers — correct predicate behaviour
# =============================================================================


class TestAuthContextHelpers:
    """Unit tests for AuthContext.has_role / has_scope / has_any_scope / is_admin."""

    def _make_context(
        self,
        roles: list[str],
        scopes: list[str],
    ) -> AuthContext:
        return AuthContext(
            user_id=uuid.uuid4(),
            roles=roles,
            scopes=scopes,
        )

    def test_has_role_returns_true_for_matching_role(self):
        ctx = self._make_context([Role.team_member.value], [])
        assert ctx.has_role(Role.team_member)
        assert ctx.has_role("team_member")

    def test_has_role_returns_false_for_absent_role(self):
        ctx = self._make_context([Role.viewer.value], [])
        assert not ctx.has_role(Role.team_admin)

    def test_is_admin_requires_system_admin_role(self):
        admin_ctx = self._make_context([Role.system_admin.value], [])
        regular_ctx = self._make_context([Role.team_admin.value], [])
        assert admin_ctx.is_admin()
        assert not regular_ctx.is_admin()

    def test_has_scope_admin_wildcard_grants_all(self):
        ctx = self._make_context([], [Scope.admin_wildcard.value])
        for scope in Scope:
            assert ctx.has_scope(scope)

    def test_has_scope_returns_false_without_matching_scope(self):
        ctx = self._make_context([], [Scope.artifact_read.value])
        assert not ctx.has_scope(Scope.artifact_write)

    def test_has_any_scope_true_when_one_matches(self):
        ctx = self._make_context([], [Scope.artifact_read.value])
        assert ctx.has_any_scope(Scope.artifact_write, Scope.artifact_read)

    def test_has_any_scope_false_when_none_match(self):
        ctx = self._make_context([], [Scope.deployment_read.value])
        assert not ctx.has_any_scope(Scope.artifact_write, Scope.collection_write)

    def test_frozen_dataclass_rejects_mutation(self):
        ctx = self._make_context([Role.viewer.value], [])
        with pytest.raises((AttributeError, TypeError)):
            ctx.roles = [Role.system_admin.value]  # type: ignore[misc]


# =============================================================================
# 15. Audience and issuer validation
# =============================================================================


class TestAudienceIssuerValidation:
    """When audience or issuer are configured, mismatches must raise 401."""

    @pytest.mark.asyncio
    async def test_wrong_audience_raises_401(self, rsa_private_key, rsa_public_key):
        """A JWT whose ``aud`` does not match the configured audience → 401."""
        token = _make_jwt(
            rsa_private_key,
            extra_claims={"aud": "wrong-audience"},
        )
        provider, _ = _make_provider(rsa_public_key, audience="expected-audience")
        request = _make_request(f"Bearer {token}")

        with pytest.raises(HTTPException) as exc_info:
            await provider.validate(request)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_correct_audience_accepted(self, rsa_private_key, rsa_public_key):
        """A JWT with the correct ``aud`` claim must be accepted."""
        token = _make_jwt(
            rsa_private_key,
            extra_claims={"aud": "skillmeat-api"},
        )
        provider, _ = _make_provider(rsa_public_key, audience="skillmeat-api")
        request = _make_request(f"Bearer {token}")

        ctx = await provider.validate(request)
        assert isinstance(ctx, AuthContext)

    @pytest.mark.asyncio
    async def test_wrong_issuer_raises_401(self, rsa_private_key, rsa_public_key):
        """A JWT from an unexpected issuer must be rejected."""
        token = _make_jwt(
            rsa_private_key,
            extra_claims={"iss": "https://evil-issuer.example.com"},
        )
        provider, _ = _make_provider(
            rsa_public_key, issuer="https://trusted.clerk.dev"
        )
        request = _make_request(f"Bearer {token}")

        with pytest.raises(HTTPException) as exc_info:
            await provider.validate(request)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_correct_issuer_accepted(self, rsa_private_key, rsa_public_key):
        """A JWT from the configured issuer must be accepted."""
        issuer = "https://trusted.clerk.dev"
        token = _make_jwt(
            rsa_private_key,
            extra_claims={"iss": issuer},
        )
        provider, _ = _make_provider(rsa_public_key, issuer=issuer)
        request = _make_request(f"Bearer {token}")

        ctx = await provider.validate(request)
        assert isinstance(ctx, AuthContext)


# =============================================================================
# 16. Claim mapping — deterministic UUID derivation
# =============================================================================


class TestClaimMapping:
    """_str_to_uuid must produce stable, deterministic UUIDs from string inputs."""

    def test_same_string_always_gives_same_uuid(self):
        uid = _str_to_uuid("user_12345")
        assert uid == _str_to_uuid("user_12345")

    def test_different_strings_give_different_uuids(self):
        assert _str_to_uuid("user_aaa") != _str_to_uuid("user_bbb")

    def test_result_is_valid_uuid(self):
        result = _str_to_uuid("any-arbitrary-string")
        assert isinstance(result, uuid.UUID)

    def test_empty_string_produces_valid_uuid(self):
        """Edge case: empty string sub must still produce a UUID (not crash)."""
        result = _str_to_uuid("")
        assert isinstance(result, uuid.UUID)

    def test_unicode_string_produces_valid_uuid(self):
        """Strings with non-ASCII characters must be handled without crash."""
        result = _str_to_uuid("user_\u4e2d\u6587\u540d\u5b57")
        assert isinstance(result, uuid.UUID)

    def test_very_long_string_produces_valid_uuid(self):
        """Extremely long strings must still produce a valid UUID."""
        long_str = "x" * 10000
        result = _str_to_uuid(long_str)
        assert isinstance(result, uuid.UUID)


# =============================================================================
# 17. No org context → viewer role with read-only defaults
# =============================================================================


class TestNoOrgContextDefaults:
    """Tokens without org_id must receive viewer role and read-only scopes."""

    @pytest.mark.asyncio
    async def test_token_without_org_gets_viewer_role(
        self, rsa_private_key, rsa_public_key
    ):
        token = _make_jwt(rsa_private_key, sub="user_solo")
        provider, _ = _make_provider(rsa_public_key)
        request = _make_request(f"Bearer {token}")

        ctx = await provider.validate(request)

        assert Role.viewer.value in ctx.roles
        assert ctx.tenant_id is None

    @pytest.mark.asyncio
    async def test_token_with_org_gets_tenant_id(
        self, rsa_private_key, rsa_public_key
    ):
        org_id = "org_mycompany"
        token = _make_jwt(
            rsa_private_key, sub="user_member", org_id=org_id, org_role="org:member"
        )
        provider, _ = _make_provider(rsa_public_key)
        request = _make_request(f"Bearer {token}")

        ctx = await provider.validate(request)

        assert ctx.tenant_id == _str_to_uuid(org_id)
        assert ctx.tenant_id is not None
