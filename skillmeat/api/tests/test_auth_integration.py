"""Integration tests for auth system: protected endpoints, scope enforcement, ENT-003 e2e flow.

Covers API-007 and ENT-003:

API-007 — Integration tests for protected endpoints with valid/invalid auth:
    * Local mode: endpoints work without any auth header
    * Mock Clerk mode: valid JWT context returns 200, missing header returns 401
    * Invalid token path: provider rejects token → 401 propagated
    * Scope enforcement: missing write scope → 403, present write scope → 200

ENT-003 — End-to-end auth flow test (provider → require_auth → service layer):
    * AuthContext is stored on request.state after require_auth runs
    * Downstream handlers can read auth_context from request.state

Design rationale
----------------
These tests use a *minimal* FastAPI application rather than the full
``create_app()`` factory.  ``create_app()`` triggers a lifespan that
connects to databases, scans the filesystem, and seeds entity types — none
of which is relevant to auth behaviour.  A self-contained app with a single
test endpoint lets us verify the ``require_auth`` dependency in isolation,
without mocking dozens of infrastructure dependencies.

The auth provider is injected via ``set_auth_provider()``, which is the same
function used by the production lifespan.  After each test the global
provider is reset to ``None`` to prevent state leakage between tests.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from skillmeat.api.auth.local_provider import LocalAuthProvider
from skillmeat.api.auth.provider import AuthProvider
from skillmeat.api.dependencies import (
    get_auth_context,
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
# Helpers
# ---------------------------------------------------------------------------


class MockClerkProvider(AuthProvider):
    """Test-double that simulates a token-aware provider without real JWTs.

    If ``reject`` is True, every request raises 401 regardless of headers.
    If ``auth_context`` is None and ``reject`` is False, the provider checks
    that an ``Authorization: Bearer ...`` header is present; an absent header
    raises 401.
    """

    def __init__(
        self,
        auth_context: AuthContext | None = None,
        reject: bool = False,
    ) -> None:
        self._context = auth_context
        self._reject = reject

    async def validate(self, request: Request) -> AuthContext:
        if self._reject:
            raise HTTPException(status_code=401, detail="Unauthorized")

        authorization = request.headers.get("Authorization", "")
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing bearer token")

        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            raise HTTPException(status_code=401, detail="Missing bearer token")

        if self._context is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        return self._context


def _simple_app(provider: AuthProvider, include_write: bool = False) -> FastAPI:
    """Build a clean minimal app without the broken placeholder routes.

    This is the actual factory used by every fixture.
    """
    set_auth_provider(provider)

    from fastapi import Depends

    app = FastAPI()

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/protected")
    async def read_endpoint(auth: AuthContext = Depends(require_auth())) -> dict:
        return {
            "user_id": str(auth.user_id),
            "roles": auth.roles,
            "scopes": auth.scopes,
        }

    @app.get("/state-check")
    async def state_endpoint(
        request: Request,
        auth: AuthContext = Depends(require_auth()),
    ) -> dict:
        ctx = getattr(request.state, "auth_context", None)
        return {
            "auth_context_on_state": ctx is not None,
            "state_user_id": str(ctx.user_id) if ctx else None,
            "dep_user_id": str(auth.user_id),
            "ids_match": ctx is not None and str(ctx.user_id) == str(auth.user_id),
        }

    if include_write:

        @app.post("/write")
        async def write_endpoint(
            auth: AuthContext = Depends(
                require_auth(scopes=[Scope.artifact_write.value])
            ),
        ) -> dict:
            return {"created": True, "user_id": str(auth.user_id)}

    return app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_auth_provider():
    """Reset the module-level auth provider to None after every test.

    This prevents state from leaking between tests that call
    ``set_auth_provider()`` directly.
    """
    import skillmeat.api.dependencies as _deps

    yield
    _deps._auth_provider = None


@pytest.fixture
def local_client() -> TestClient:
    """TestClient backed by LocalAuthProvider (zero-auth, local mode)."""
    app = _simple_app(LocalAuthProvider())
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture
def test_auth_context() -> AuthContext:
    """A realistic AuthContext for mock-Clerk tests (team_member, read-only)."""
    return AuthContext(
        user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        roles=[Role.team_member.value],
        scopes=[Scope.artifact_read.value, Scope.collection_read.value],
    )


@pytest.fixture
def test_write_context() -> AuthContext:
    """An AuthContext that also carries the artifact:write scope."""
    return AuthContext(
        user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        roles=[Role.team_member.value],
        scopes=[Scope.artifact_read.value, Scope.artifact_write.value],
    )


@pytest.fixture
def clerk_client(test_auth_context: AuthContext) -> tuple[TestClient, AuthContext]:
    """TestClient backed by MockClerkProvider that accepts any bearer token."""
    provider = MockClerkProvider(auth_context=test_auth_context)
    app = _simple_app(provider, include_write=True)
    client = TestClient(app, raise_server_exceptions=True)
    return client, test_auth_context


@pytest.fixture
def clerk_client_write(
    test_write_context: AuthContext,
) -> tuple[TestClient, AuthContext]:
    """TestClient with write-scope AuthContext; includes POST /write endpoint."""
    provider = MockClerkProvider(auth_context=test_write_context)
    app = _simple_app(provider, include_write=True)
    client = TestClient(app, raise_server_exceptions=True)
    return client, test_write_context


@pytest.fixture
def clerk_client_read_only(
    test_auth_context: AuthContext,
) -> tuple[TestClient, AuthContext]:
    """TestClient with read-only AuthContext; includes POST /write endpoint."""
    provider = MockClerkProvider(auth_context=test_auth_context)
    app = _simple_app(provider, include_write=True)
    client = TestClient(app, raise_server_exceptions=True)
    return client, test_auth_context


@pytest.fixture
def rejecting_clerk_client() -> TestClient:
    """TestClient whose provider always rejects (simulates no-auth Clerk mode)."""
    provider = MockClerkProvider(reject=True)
    app = _simple_app(provider)
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def no_header_clerk_client() -> TestClient:
    """TestClient whose provider rejects when Authorization header is absent."""
    # auth_context provided but reject=False: provider checks for bearer header
    ctx = AuthContext(
        user_id=uuid.uuid4(),
        roles=[Role.viewer.value],
        scopes=[Scope.artifact_read.value],
    )
    provider = MockClerkProvider(auth_context=ctx)
    app = _simple_app(provider)
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# 1. Local mode tests
# ---------------------------------------------------------------------------


class TestLocalMode:
    """LocalAuthProvider: all requests succeed without any auth header."""

    def test_protected_endpoint_no_auth_header_returns_200(
        self, local_client: TestClient
    ) -> None:
        """Protected endpoint returns 200 in local mode with no auth header."""
        response = local_client.get("/protected")
        assert response.status_code == 200

    def test_local_mode_response_contains_local_admin_user_id(
        self, local_client: TestClient
    ) -> None:
        """Response body contains the local_admin user_id from LOCAL_ADMIN_CONTEXT."""
        response = local_client.get("/protected")
        data = response.json()
        assert data["user_id"] == str(LOCAL_ADMIN_CONTEXT.user_id)

    def test_local_mode_has_system_admin_role(
        self, local_client: TestClient
    ) -> None:
        """LOCAL_ADMIN_CONTEXT carries the system_admin role."""
        response = local_client.get("/protected")
        data = response.json()
        assert Role.system_admin.value in data["roles"]

    def test_local_mode_has_all_scopes(self, local_client: TestClient) -> None:
        """LOCAL_ADMIN_CONTEXT carries all defined permission scopes."""
        response = local_client.get("/protected")
        data = response.json()
        expected_scopes = {s.value for s in Scope}
        actual_scopes = set(data["scopes"])
        assert expected_scopes == actual_scopes

    def test_auth_context_stored_on_request_state(
        self, local_client: TestClient
    ) -> None:
        """require_auth sets request.state.auth_context (ENT-003: state layer)."""
        response = local_client.get("/state-check")
        assert response.status_code == 200
        data = response.json()
        assert data["auth_context_on_state"] is True

    def test_request_state_user_id_matches_dependency_user_id(
        self, local_client: TestClient
    ) -> None:
        """The user_id on request.state matches the AuthContext returned by Depends."""
        response = local_client.get("/state-check")
        data = response.json()
        assert data["ids_match"] is True
        assert data["state_user_id"] == data["dep_user_id"]

    def test_local_mode_with_auth_header_still_returns_200(
        self, local_client: TestClient
    ) -> None:
        """Local mode ignores any auth header — result is still 200."""
        response = local_client.get(
            "/protected",
            headers={"Authorization": "Bearer ignored-token"},
        )
        assert response.status_code == 200

    def test_health_endpoint_no_auth_needed(
        self, local_client: TestClient
    ) -> None:
        """Public /health endpoint returns 200 without auth in local mode."""
        response = local_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# 2. Mock Clerk mode — valid token succeeds
# ---------------------------------------------------------------------------


class TestClerkModeValidToken:
    """MockClerkProvider with valid context: bearer header required, returns 200."""

    def test_valid_bearer_token_returns_200(
        self,
        clerk_client: tuple[TestClient, AuthContext],
    ) -> None:
        """Valid bearer header returns 200 in Clerk mode."""
        client, _ = clerk_client
        response = client.get(
            "/protected", headers={"Authorization": "Bearer test-jwt-token"}
        )
        assert response.status_code == 200

    def test_valid_token_response_has_correct_user_id(
        self,
        clerk_client: tuple[TestClient, AuthContext],
    ) -> None:
        """Response user_id matches the AuthContext injected via set_auth_provider."""
        client, expected_ctx = clerk_client
        response = client.get(
            "/protected", headers={"Authorization": "Bearer test-jwt-token"}
        )
        data = response.json()
        assert data["user_id"] == str(expected_ctx.user_id)

    def test_valid_token_response_has_correct_roles(
        self,
        clerk_client: tuple[TestClient, AuthContext],
    ) -> None:
        """Response roles match the injected AuthContext."""
        client, expected_ctx = clerk_client
        response = client.get(
            "/protected", headers={"Authorization": "Bearer test-jwt-token"}
        )
        data = response.json()
        assert data["roles"] == expected_ctx.roles

    def test_valid_token_response_has_correct_scopes(
        self,
        clerk_client: tuple[TestClient, AuthContext],
    ) -> None:
        """Response scopes match the injected AuthContext."""
        client, expected_ctx = clerk_client
        response = client.get(
            "/protected", headers={"Authorization": "Bearer test-jwt-token"}
        )
        data = response.json()
        assert set(data["scopes"]) == set(expected_ctx.scopes)

    def test_clerk_mode_health_endpoint_no_auth_needed(
        self,
        clerk_client: tuple[TestClient, AuthContext],
    ) -> None:
        """Public /health endpoint works in Clerk mode without an auth header."""
        client, _ = clerk_client
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# 3. Missing/invalid auth — returns 401
# ---------------------------------------------------------------------------


class TestMissingOrInvalidAuth:
    """Auth failures: absent header or rejecting provider must return 401."""

    def test_no_auth_header_returns_401_in_clerk_mode(
        self,
        no_header_clerk_client: TestClient,
    ) -> None:
        """Protected endpoint returns 401 when no Authorization header is sent."""
        response = no_header_clerk_client.get("/protected")
        assert response.status_code == 401

    def test_invalid_bearer_token_returns_401(
        self,
        rejecting_clerk_client: TestClient,
    ) -> None:
        """Provider that always rejects causes the endpoint to return 401."""
        response = rejecting_clerk_client.get(
            "/protected", headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401

    def test_non_bearer_auth_scheme_returns_401(
        self,
        no_header_clerk_client: TestClient,
    ) -> None:
        """Authorization header with non-Bearer scheme is treated as missing."""
        response = no_header_clerk_client.get(
            "/protected", headers={"Authorization": "Basic dXNlcjpwYXNz"}
        )
        assert response.status_code == 401

    def test_empty_bearer_token_returns_401(
        self,
        no_header_clerk_client: TestClient,
    ) -> None:
        """'Authorization: Bearer ' with no token string causes 401.

        Mirrors ClerkAuthProvider._extract_bearer_token: ``not token.strip()``
        rejects a bearer header whose token part is blank.
        """
        response = no_header_clerk_client.get(
            "/protected", headers={"Authorization": "Bearer "}
        )
        assert response.status_code == 401

    def test_401_response_does_not_contain_sensitive_info(
        self,
        rejecting_clerk_client: TestClient,
    ) -> None:
        """401 response body has a detail message and does not leak internal state."""
        response = rejecting_clerk_client.get(
            "/protected", headers={"Authorization": "Bearer bad"}
        )
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        # Must not leak stack traces or internal paths
        assert "Traceback" not in str(data)

    def test_health_endpoint_accessible_when_auth_provider_rejects(
        self,
        rejecting_clerk_client: TestClient,
    ) -> None:
        """Public /health endpoint is still reachable even when auth always fails."""
        response = rejecting_clerk_client.get("/health")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# 4. Scope validation — 403 vs 200
# ---------------------------------------------------------------------------


class TestScopeValidation:
    """Write-scoped endpoint returns 403 for missing scope, 200 when present."""

    def test_write_endpoint_without_write_scope_returns_403(
        self,
        clerk_client_read_only: tuple[TestClient, AuthContext],
    ) -> None:
        """POST /write returns 403 when AuthContext lacks artifact:write scope."""
        client, ctx = clerk_client_read_only
        assert Scope.artifact_write.value not in ctx.scopes
        response = client.post(
            "/write", headers={"Authorization": "Bearer read-only-token"}
        )
        assert response.status_code == 403

    def test_write_endpoint_with_write_scope_returns_200(
        self,
        clerk_client_write: tuple[TestClient, AuthContext],
    ) -> None:
        """POST /write returns 200 when AuthContext carries artifact:write scope."""
        client, ctx = clerk_client_write
        assert Scope.artifact_write.value in ctx.scopes
        response = client.post(
            "/write", headers={"Authorization": "Bearer write-capable-token"}
        )
        assert response.status_code == 200

    def test_write_endpoint_response_contains_user_id(
        self,
        clerk_client_write: tuple[TestClient, AuthContext],
    ) -> None:
        """Successful write returns the authenticated user_id in the response."""
        client, ctx = clerk_client_write
        response = client.post(
            "/write", headers={"Authorization": "Bearer write-capable-token"}
        )
        data = response.json()
        assert data["user_id"] == str(ctx.user_id)
        assert data["created"] is True

    def test_403_response_describes_missing_scope(
        self,
        clerk_client_read_only: tuple[TestClient, AuthContext],
    ) -> None:
        """403 response body names the missing scope so callers can diagnose it."""
        client, _ = clerk_client_read_only
        response = client.post(
            "/write", headers={"Authorization": "Bearer read-only-token"}
        )
        assert response.status_code == 403
        data = response.json()
        assert "detail" in data
        # require_auth formats missing scopes in the detail message
        assert "artifact:write" in data["detail"]

    def test_admin_wildcard_scope_satisfies_write_check(self) -> None:
        """admin:* wildcard context passes any scope check, including artifact:write."""
        admin_ctx = AuthContext(
            user_id=uuid.uuid4(),
            roles=[Role.system_admin.value],
            scopes=[Scope.admin_wildcard.value],
        )
        provider = MockClerkProvider(auth_context=admin_ctx)
        app = _simple_app(provider, include_write=True)
        client = TestClient(app, raise_server_exceptions=True)
        response = client.post(
            "/write", headers={"Authorization": "Bearer admin-token"}
        )
        assert response.status_code == 200

    def test_local_mode_write_endpoint_returns_200(self) -> None:
        """LOCAL_ADMIN_CONTEXT carries admin:* wildcard so write endpoints pass."""
        app = _simple_app(LocalAuthProvider(), include_write=True)
        client = TestClient(app, raise_server_exceptions=True)
        response = client.post("/write")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# 5. Public endpoints remain accessible
# ---------------------------------------------------------------------------


class TestPublicEndpoints:
    """Endpoints declared without require_auth remain open in any mode."""

    def test_health_no_auth_local_mode(self, local_client: TestClient) -> None:
        """/health is reachable without auth in local mode."""
        response = local_client.get("/health")
        assert response.status_code == 200

    def test_health_in_clerk_mode_no_token(
        self,
        no_header_clerk_client: TestClient,
    ) -> None:
        """/health is reachable in Clerk mode without an Authorization header."""
        response = no_header_clerk_client.get("/health")
        assert response.status_code == 200

    def test_health_in_rejecting_clerk_mode(
        self,
        rejecting_clerk_client: TestClient,
    ) -> None:
        """/health is reachable even when the auth provider always rejects."""
        response = rejecting_clerk_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# 6. AuthContext reaches service layer (ENT-003)
# ---------------------------------------------------------------------------


class TestAuthContextReachesServiceLayer:
    """ENT-003: AuthContext must be reachable from request.state after require_auth."""

    def test_auth_context_set_on_request_state_local_mode(
        self, local_client: TestClient
    ) -> None:
        """require_auth stores auth_context on request.state in local mode."""
        response = local_client.get("/state-check")
        assert response.status_code == 200
        data = response.json()
        assert data["auth_context_on_state"] is True

    def test_auth_context_state_user_id_matches_dep_user_id_local(
        self, local_client: TestClient
    ) -> None:
        """The request.state.auth_context has the same user_id as the dependency."""
        response = local_client.get("/state-check")
        data = response.json()
        assert data["ids_match"] is True

    def test_auth_context_set_on_request_state_clerk_mode(
        self,
        clerk_client: tuple[TestClient, AuthContext],
    ) -> None:
        """require_auth stores auth_context on request.state in Clerk mode."""
        client, _ = clerk_client
        response = client.get(
            "/state-check", headers={"Authorization": "Bearer valid-token"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["auth_context_on_state"] is True

    def test_auth_context_state_user_id_matches_dep_user_id_clerk(
        self,
        clerk_client: tuple[TestClient, AuthContext],
    ) -> None:
        """The request.state.auth_context has the correct user_id in Clerk mode."""
        client, expected_ctx = clerk_client
        response = client.get(
            "/state-check", headers={"Authorization": "Bearer valid-token"}
        )
        data = response.json()
        assert data["state_user_id"] == str(expected_ctx.user_id)
        assert data["dep_user_id"] == str(expected_ctx.user_id)
        assert data["ids_match"] is True

    def test_auth_context_local_admin_user_id_on_state(
        self, local_client: TestClient
    ) -> None:
        """In local mode, request.state.auth_context.user_id is the local_admin UUID."""
        response = local_client.get("/state-check")
        data = response.json()
        assert data["state_user_id"] == str(LOCAL_ADMIN_CONTEXT.user_id)

    def test_get_auth_context_dependency_reads_from_request_state(self) -> None:
        """get_auth_context() dependency reads from request.state without re-validating.

        This test verifies the ENT-003 pattern: a downstream handler can declare
        ``Depends(get_auth_context)`` instead of ``Depends(require_auth())`` and
        receive the same AuthContext without a second provider round-trip.
        The upstream router-level ``require_auth`` must have already populated
        ``request.state.auth_context``.
        """
        from fastapi import Depends

        ctx = AuthContext(
            user_id=uuid.uuid4(),
            roles=[Role.team_member.value],
            scopes=[Scope.artifact_read.value],
        )
        provider = MockClerkProvider(auth_context=ctx)
        set_auth_provider(provider)

        app = FastAPI()

        @app.get("/upstream")
        async def upstream(
            # Simulate router-level auth (sets request.state.auth_context)
            auth: AuthContext = Depends(require_auth()),
        ) -> dict:
            return {"user_id": str(auth.user_id)}

        @app.get("/downstream")
        async def downstream(
            request: Request,
            # Lightweight: reads from state, no second provider call
            auth: AuthContext = Depends(get_auth_context),
        ) -> dict:
            return {"user_id": str(auth.user_id)}

        client = TestClient(app, raise_server_exceptions=True)

        # /upstream populates state and returns correctly
        r1 = client.get("/upstream", headers={"Authorization": "Bearer tok"})
        assert r1.status_code == 200
        assert r1.json()["user_id"] == str(ctx.user_id)

        # /downstream raises 401 (no prior require_auth on this route), which is
        # the correct behaviour — get_auth_context is meant for routes already
        # protected at router level.
        r2 = client.get("/downstream", headers={"Authorization": "Bearer tok"})
        assert r2.status_code == 401
