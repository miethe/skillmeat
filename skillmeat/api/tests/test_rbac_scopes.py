"""RBAC scope validation tests for SkillMeat AAA/RBAC system.

Covers TEST-002: require_auth dependency injection with scope enforcement.

Scope coverage (complements test_auth_integration.py which covers basic 401/403
flows):

    1. Matching scopes → request proceeds (200)
    2. Insufficient scopes → 403 Forbidden
    3. No auth header in non-local mode → 401 Unauthorized
    4. No scopes required → any authenticated user passes
    5. Multiple scopes required → user must have ALL required scopes
    6. System admin bypasses scope requirements (admin:* wildcard)
    7. Team admin has team-level scope access
    8. Viewer role has read-only scopes only
    9. Invalid/unrecognized scope format handling
   10. AuthContext unit-level helper methods (has_scope, has_any_scope, has_role,
       is_admin)

Design rationale
----------------
Tests use a minimal FastAPI app (not the full create_app factory) to isolate
require_auth dependency behaviour from database/filesystem infrastructure.
The MockScopedProvider is a thin wrapper that returns a caller-controlled
AuthContext after validating that a Bearer token header is present.

The ``_reset_auth_provider`` autouse fixture ensures module-level provider state
never leaks between tests.
"""

from __future__ import annotations

import uuid
from typing import Sequence

import pytest
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from skillmeat.api.auth.provider import AuthProvider
from skillmeat.api.dependencies import require_auth, set_auth_provider
from skillmeat.api.schemas.auth import (
    LOCAL_ADMIN_CONTEXT,
    AuthContext,
    Role,
    Scope,
)


# ---------------------------------------------------------------------------
# Test double
# ---------------------------------------------------------------------------


class MockScopedProvider(AuthProvider):
    """Minimal test-double that gates on bearer-header presence.

    If ``auth_context`` is provided the provider returns it for any request
    that carries an ``Authorization: Bearer <token>`` header.  Missing or
    malformed headers raise 401, mirroring a real JWT provider.

    Args:
        auth_context: The context to return on success.  Pass ``None`` to
            simulate a provider that always rejects (invalid token).
    """

    def __init__(self, auth_context: AuthContext | None) -> None:
        self._context = auth_context

    async def validate(self, request: Request) -> AuthContext:
        authorization = request.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")

        if not authorization or scheme.lower() != "bearer" or not token.strip():
            raise HTTPException(status_code=401, detail="Missing bearer token")

        if self._context is None:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        return self._context


# ---------------------------------------------------------------------------
# App factory helpers
# ---------------------------------------------------------------------------


def _build_app(
    provider: AuthProvider,
    *,
    required_scopes: list[str] | None = None,
    multi_scope_endpoint_scopes: list[str] | None = None,
    include_no_scope_endpoint: bool = False,
) -> FastAPI:
    """Build a minimal FastAPI app wired to *provider*.

    Routes created:
        GET  /health              — always public, no auth
        GET  /read                — protected, requires ``required_scopes``
        GET  /no-scope            — protected but no scope list (any auth passes)
        GET  /multi-scope         — protected with ``multi_scope_endpoint_scopes``

    Args:
        provider: Auth provider to register.
        required_scopes: Scopes enforced on ``GET /read``.
        multi_scope_endpoint_scopes: Scopes enforced on ``GET /multi-scope``.
        include_no_scope_endpoint: Whether to add the ``/no-scope`` route.
    """
    set_auth_provider(provider)
    app = FastAPI()

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.get("/read")
    async def read_resource(
        auth: AuthContext = Depends(require_auth(scopes=required_scopes)),
    ) -> dict:
        return {
            "user_id": str(auth.user_id),
            "roles": auth.roles,
            "scopes": auth.scopes,
            "is_admin": auth.is_admin(),
        }

    if include_no_scope_endpoint:

        @app.get("/no-scope")
        async def no_scope_resource(
            auth: AuthContext = Depends(require_auth()),
        ) -> dict:
            return {"user_id": str(auth.user_id)}

    if multi_scope_endpoint_scopes is not None:

        @app.get("/multi-scope")
        async def multi_scope_resource(
            auth: AuthContext = Depends(
                require_auth(scopes=multi_scope_endpoint_scopes)
            ),
        ) -> dict:
            return {
                "user_id": str(auth.user_id),
                "scopes": auth.scopes,
            }

    return app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_auth_provider():
    """Reset module-level auth provider to None after every test."""
    import skillmeat.api.dependencies as _deps

    yield
    _deps._auth_provider = None


@pytest.fixture
def system_admin_context() -> AuthContext:
    """AuthContext carrying system_admin role and admin:* wildcard scope."""
    return AuthContext(
        user_id=uuid.uuid4(),
        roles=[Role.system_admin.value],
        scopes=[Scope.admin_wildcard.value],
    )


@pytest.fixture
def team_admin_context() -> AuthContext:
    """AuthContext carrying team_admin role with collection and artifact scopes."""
    return AuthContext(
        user_id=uuid.uuid4(),
        roles=[Role.team_admin.value],
        scopes=[
            Scope.artifact_read.value,
            Scope.artifact_write.value,
            Scope.collection_read.value,
            Scope.collection_write.value,
        ],
    )


@pytest.fixture
def team_member_context() -> AuthContext:
    """AuthContext carrying team_member role with read + deployment_read scopes."""
    return AuthContext(
        user_id=uuid.uuid4(),
        roles=[Role.team_member.value],
        scopes=[
            Scope.artifact_read.value,
            Scope.collection_read.value,
            Scope.deployment_read.value,
        ],
    )


@pytest.fixture
def viewer_context() -> AuthContext:
    """AuthContext carrying viewer role with artifact_read scope only."""
    return AuthContext(
        user_id=uuid.uuid4(),
        roles=[Role.viewer.value],
        scopes=[Scope.artifact_read.value],
    )


# ---------------------------------------------------------------------------
# 1. Matching scopes → 200
# ---------------------------------------------------------------------------


class TestMatchingScopes:
    """Requests with sufficient scopes are allowed through (HTTP 200)."""

    def test_user_with_exact_required_scope_gets_200(
        self, team_member_context: AuthContext
    ) -> None:
        """User holding artifact:read can reach an artifact:read-gated endpoint."""
        provider = MockScopedProvider(team_member_context)
        app = _build_app(
            provider,
            required_scopes=[Scope.artifact_read.value],
        )
        client = TestClient(app, raise_server_exceptions=True)
        response = client.get("/read", headers={"Authorization": "Bearer tok"})
        assert response.status_code == 200

    def test_user_with_superset_of_required_scopes_gets_200(
        self, team_admin_context: AuthContext
    ) -> None:
        """User with more scopes than required still passes the scope check."""
        provider = MockScopedProvider(team_admin_context)
        # Only artifact:read required; context holds many scopes
        app = _build_app(
            provider,
            required_scopes=[Scope.artifact_read.value],
        )
        client = TestClient(app, raise_server_exceptions=True)
        response = client.get("/read", headers={"Authorization": "Bearer tok"})
        assert response.status_code == 200

    def test_response_includes_user_id_on_success(
        self, team_member_context: AuthContext
    ) -> None:
        """Successful response body contains the authenticated user's UUID."""
        provider = MockScopedProvider(team_member_context)
        app = _build_app(
            provider,
            required_scopes=[Scope.artifact_read.value],
        )
        client = TestClient(app, raise_server_exceptions=True)
        response = client.get("/read", headers={"Authorization": "Bearer tok"})
        assert response.json()["user_id"] == str(team_member_context.user_id)

    def test_response_includes_roles_and_scopes_on_success(
        self, team_member_context: AuthContext
    ) -> None:
        """Successful response body carries role and scope lists from AuthContext."""
        provider = MockScopedProvider(team_member_context)
        app = _build_app(
            provider,
            required_scopes=[Scope.artifact_read.value],
        )
        client = TestClient(app, raise_server_exceptions=True)
        response = client.get("/read", headers={"Authorization": "Bearer tok"})
        data = response.json()
        assert data["roles"] == team_member_context.roles
        assert set(data["scopes"]) == set(team_member_context.scopes)


# ---------------------------------------------------------------------------
# 2. Insufficient scopes → 403
# ---------------------------------------------------------------------------


class TestInsufficientScopes:
    """Requests where the authenticated context lacks required scopes return 403."""

    def test_viewer_without_write_scope_gets_403(
        self, viewer_context: AuthContext
    ) -> None:
        """Viewer (read-only) cannot reach an artifact:write-gated endpoint."""
        provider = MockScopedProvider(viewer_context)
        app = _build_app(
            provider,
            required_scopes=[Scope.artifact_write.value],
        )
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/read", headers={"Authorization": "Bearer tok"})
        assert response.status_code == 403

    def test_team_member_without_collection_write_gets_403(
        self, team_member_context: AuthContext
    ) -> None:
        """team_member lacks collection:write; the gated endpoint returns 403."""
        assert Scope.collection_write.value not in team_member_context.scopes
        provider = MockScopedProvider(team_member_context)
        app = _build_app(
            provider,
            required_scopes=[Scope.collection_write.value],
        )
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/read", headers={"Authorization": "Bearer tok"})
        assert response.status_code == 403

    def test_403_response_has_detail_field(
        self, viewer_context: AuthContext
    ) -> None:
        """403 response JSON body contains a 'detail' key."""
        provider = MockScopedProvider(viewer_context)
        app = _build_app(
            provider,
            required_scopes=[Scope.artifact_write.value],
        )
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/read", headers={"Authorization": "Bearer tok"})
        assert "detail" in response.json()

    def test_403_detail_names_the_missing_scope(
        self, viewer_context: AuthContext
    ) -> None:
        """403 detail message includes the missing scope string for diagnostics."""
        provider = MockScopedProvider(viewer_context)
        app = _build_app(
            provider,
            required_scopes=[Scope.artifact_write.value],
        )
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/read", headers={"Authorization": "Bearer tok"})
        detail = response.json()["detail"]
        assert Scope.artifact_write.value in detail

    def test_403_detail_names_all_missing_scopes(
        self, viewer_context: AuthContext
    ) -> None:
        """When multiple scopes are missing the detail lists all of them."""
        provider = MockScopedProvider(viewer_context)
        app = _build_app(
            provider,
            required_scopes=[
                Scope.artifact_write.value,
                Scope.collection_write.value,
                Scope.deployment_write.value,
            ],
        )
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/read", headers={"Authorization": "Bearer tok"})
        detail = response.json()["detail"]
        assert Scope.artifact_write.value in detail
        assert Scope.collection_write.value in detail
        assert Scope.deployment_write.value in detail


# ---------------------------------------------------------------------------
# 3. No auth header in non-local mode → 401
# ---------------------------------------------------------------------------


class TestMissingAuthHeader:
    """Non-local providers raise 401 when the Authorization header is absent."""

    def test_no_header_returns_401(self, viewer_context: AuthContext) -> None:
        """Missing Authorization header results in 401, not 403."""
        provider = MockScopedProvider(viewer_context)
        app = _build_app(
            provider,
            required_scopes=[Scope.artifact_read.value],
        )
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/read")
        assert response.status_code == 401

    def test_non_bearer_scheme_returns_401(self, viewer_context: AuthContext) -> None:
        """Basic-auth or other schemes are rejected with 401."""
        provider = MockScopedProvider(viewer_context)
        app = _build_app(
            provider,
            required_scopes=[Scope.artifact_read.value],
        )
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get(
            "/read", headers={"Authorization": "Basic dXNlcjpwYXNz"}
        )
        assert response.status_code == 401

    def test_empty_bearer_token_returns_401(self, viewer_context: AuthContext) -> None:
        """'Authorization: Bearer ' with blank token string returns 401."""
        provider = MockScopedProvider(viewer_context)
        app = _build_app(
            provider,
            required_scopes=[Scope.artifact_read.value],
        )
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/read", headers={"Authorization": "Bearer "})
        assert response.status_code == 401

    def test_401_takes_priority_over_scope_check(self) -> None:
        """Provider raises 401 (unauthenticated) before scope check runs.

        A missing header must return 401 even on a scope-gated endpoint —
        the 403 scope check only fires after successful authentication.
        """
        provider = MockScopedProvider(auth_context=None)
        app = _build_app(
            provider,
            required_scopes=[Scope.artifact_write.value],
        )
        client = TestClient(app, raise_server_exceptions=False)
        # No header — provider raises 401 before require_auth checks scopes
        response = client.get("/read")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# 4. No scopes required → any authenticated user passes
# ---------------------------------------------------------------------------


class TestNoScopesRequired:
    """When require_auth() is called without scopes, any valid auth passes."""

    def test_viewer_passes_no_scope_endpoint(
        self, viewer_context: AuthContext
    ) -> None:
        """Viewer (minimal scopes) reaches an endpoint with no scope requirement."""
        provider = MockScopedProvider(viewer_context)
        app = _build_app(provider, include_no_scope_endpoint=True)
        client = TestClient(app, raise_server_exceptions=True)
        response = client.get("/no-scope", headers={"Authorization": "Bearer tok"})
        assert response.status_code == 200

    def test_team_member_passes_no_scope_endpoint(
        self, team_member_context: AuthContext
    ) -> None:
        """team_member context also passes a no-scope-required endpoint."""
        provider = MockScopedProvider(team_member_context)
        app = _build_app(provider, include_no_scope_endpoint=True)
        client = TestClient(app, raise_server_exceptions=True)
        response = client.get("/no-scope", headers={"Authorization": "Bearer tok"})
        assert response.status_code == 200

    def test_no_scope_endpoint_returns_user_id(
        self, viewer_context: AuthContext
    ) -> None:
        """No-scope-required endpoint returns the authenticated user's ID."""
        provider = MockScopedProvider(viewer_context)
        app = _build_app(provider, include_no_scope_endpoint=True)
        client = TestClient(app, raise_server_exceptions=True)
        response = client.get("/no-scope", headers={"Authorization": "Bearer tok"})
        assert response.json()["user_id"] == str(viewer_context.user_id)

    def test_require_auth_empty_list_is_same_as_no_scopes(self) -> None:
        """Passing scopes=[] to require_auth() is equivalent to no scope check."""
        ctx = AuthContext(
            user_id=uuid.uuid4(),
            roles=[Role.viewer.value],
            scopes=[Scope.artifact_read.value],
        )
        provider = MockScopedProvider(ctx)
        # scopes=[] should not trigger any 403
        app = _build_app(provider, required_scopes=[])
        client = TestClient(app, raise_server_exceptions=True)
        response = client.get("/read", headers={"Authorization": "Bearer tok"})
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# 5. Multiple scopes required — ALL must be present
# ---------------------------------------------------------------------------


class TestMultipleScopesRequired:
    """When multiple scopes are listed, the user must carry every one of them."""

    def test_user_with_all_required_scopes_gets_200(
        self, team_admin_context: AuthContext
    ) -> None:
        """team_admin carrying artifact:read + collection:write → 200."""
        assert Scope.artifact_read.value in team_admin_context.scopes
        assert Scope.collection_write.value in team_admin_context.scopes
        provider = MockScopedProvider(team_admin_context)
        app = _build_app(
            provider,
            multi_scope_endpoint_scopes=[
                Scope.artifact_read.value,
                Scope.collection_write.value,
            ],
        )
        client = TestClient(app, raise_server_exceptions=True)
        response = client.get(
            "/multi-scope", headers={"Authorization": "Bearer tok"}
        )
        assert response.status_code == 200

    def test_user_missing_one_of_two_required_scopes_gets_403(
        self, team_member_context: AuthContext
    ) -> None:
        """team_member has artifact:read but not collection:write → 403."""
        assert Scope.artifact_read.value in team_member_context.scopes
        assert Scope.collection_write.value not in team_member_context.scopes
        provider = MockScopedProvider(team_member_context)
        app = _build_app(
            provider,
            multi_scope_endpoint_scopes=[
                Scope.artifact_read.value,
                Scope.collection_write.value,
            ],
        )
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get(
            "/multi-scope", headers={"Authorization": "Bearer tok"}
        )
        assert response.status_code == 403

    def test_user_missing_all_required_scopes_gets_403(
        self, viewer_context: AuthContext
    ) -> None:
        """Viewer missing both write scopes gets 403 when both are required."""
        assert Scope.artifact_write.value not in viewer_context.scopes
        assert Scope.collection_write.value not in viewer_context.scopes
        provider = MockScopedProvider(viewer_context)
        app = _build_app(
            provider,
            multi_scope_endpoint_scopes=[
                Scope.artifact_write.value,
                Scope.collection_write.value,
            ],
        )
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get(
            "/multi-scope", headers={"Authorization": "Bearer tok"}
        )
        assert response.status_code == 403

    def test_403_detail_lists_only_missing_scopes_not_present_ones(
        self, team_member_context: AuthContext
    ) -> None:
        """403 detail names only the absent scopes; held scopes are not listed."""
        # team_member has artifact:read but not collection:write
        assert Scope.artifact_read.value in team_member_context.scopes
        assert Scope.collection_write.value not in team_member_context.scopes
        provider = MockScopedProvider(team_member_context)
        app = _build_app(
            provider,
            multi_scope_endpoint_scopes=[
                Scope.artifact_read.value,
                Scope.collection_write.value,
            ],
        )
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get(
            "/multi-scope", headers={"Authorization": "Bearer tok"}
        )
        detail = response.json()["detail"]
        assert Scope.collection_write.value in detail
        assert Scope.artifact_read.value not in detail

    def test_three_scopes_all_present_gets_200(
        self, team_admin_context: AuthContext
    ) -> None:
        """Three-scope requirement satisfied by team_admin context → 200."""
        required = [
            Scope.artifact_read.value,
            Scope.artifact_write.value,
            Scope.collection_read.value,
        ]
        for s in required:
            assert s in team_admin_context.scopes
        provider = MockScopedProvider(team_admin_context)
        app = _build_app(provider, multi_scope_endpoint_scopes=required)
        client = TestClient(app, raise_server_exceptions=True)
        response = client.get(
            "/multi-scope", headers={"Authorization": "Bearer tok"}
        )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# 6. System admin bypasses scope requirements (admin:* wildcard)
# ---------------------------------------------------------------------------


class TestSystemAdminBypass:
    """system_admin with admin:* wildcard passes any scope-gated endpoint."""

    def test_admin_wildcard_satisfies_artifact_write(
        self, system_admin_context: AuthContext
    ) -> None:
        """admin:* wildcard allows artifact:write-gated access."""
        assert Scope.artifact_write.value not in system_admin_context.scopes
        assert Scope.admin_wildcard.value in system_admin_context.scopes
        provider = MockScopedProvider(system_admin_context)
        app = _build_app(
            provider,
            required_scopes=[Scope.artifact_write.value],
        )
        client = TestClient(app, raise_server_exceptions=True)
        response = client.get("/read", headers={"Authorization": "Bearer admin-tok"})
        assert response.status_code == 200

    def test_admin_wildcard_satisfies_collection_write(
        self, system_admin_context: AuthContext
    ) -> None:
        """admin:* wildcard allows collection:write-gated access."""
        provider = MockScopedProvider(system_admin_context)
        app = _build_app(
            provider,
            required_scopes=[Scope.collection_write.value],
        )
        client = TestClient(app, raise_server_exceptions=True)
        response = client.get("/read", headers={"Authorization": "Bearer admin-tok"})
        assert response.status_code == 200

    def test_admin_wildcard_satisfies_multi_scope_requirement(
        self, system_admin_context: AuthContext
    ) -> None:
        """admin:* wildcard satisfies a three-scope requirement in one go."""
        provider = MockScopedProvider(system_admin_context)
        app = _build_app(
            provider,
            multi_scope_endpoint_scopes=[
                Scope.artifact_write.value,
                Scope.collection_write.value,
                Scope.deployment_write.value,
            ],
        )
        client = TestClient(app, raise_server_exceptions=True)
        response = client.get(
            "/multi-scope", headers={"Authorization": "Bearer admin-tok"}
        )
        assert response.status_code == 200

    def test_local_admin_context_has_admin_wildcard(self) -> None:
        """LOCAL_ADMIN_CONTEXT carries admin:* scope (verified without HTTP)."""
        assert LOCAL_ADMIN_CONTEXT.is_admin()
        assert LOCAL_ADMIN_CONTEXT.has_scope(Scope.admin_wildcard)

    def test_local_admin_has_all_defined_scopes_via_wildcard(self) -> None:
        """LOCAL_ADMIN_CONTEXT.has_scope returns True for every Scope member."""
        for scope in Scope:
            assert LOCAL_ADMIN_CONTEXT.has_scope(scope), (
                f"LOCAL_ADMIN_CONTEXT.has_scope({scope!r}) returned False"
            )

    def test_response_is_admin_field_true_for_system_admin(
        self, system_admin_context: AuthContext
    ) -> None:
        """Response body ``is_admin`` field is True for system_admin context."""
        provider = MockScopedProvider(system_admin_context)
        app = _build_app(
            provider,
            required_scopes=[Scope.artifact_read.value],
        )
        client = TestClient(app, raise_server_exceptions=True)
        response = client.get("/read", headers={"Authorization": "Bearer admin-tok"})
        assert response.json()["is_admin"] is True


# ---------------------------------------------------------------------------
# 7. Team admin has team-level scope access
# ---------------------------------------------------------------------------


class TestTeamAdminScopeAccess:
    """team_admin carries write scopes for artifacts and collections."""

    def test_team_admin_can_write_artifacts(
        self, team_admin_context: AuthContext
    ) -> None:
        """team_admin holds artifact:write and can access write-gated endpoint."""
        assert Scope.artifact_write.value in team_admin_context.scopes
        provider = MockScopedProvider(team_admin_context)
        app = _build_app(
            provider,
            required_scopes=[Scope.artifact_write.value],
        )
        client = TestClient(app, raise_server_exceptions=True)
        response = client.get("/read", headers={"Authorization": "Bearer tok"})
        assert response.status_code == 200

    def test_team_admin_can_write_collections(
        self, team_admin_context: AuthContext
    ) -> None:
        """team_admin holds collection:write and can access collection write endpoint."""
        assert Scope.collection_write.value in team_admin_context.scopes
        provider = MockScopedProvider(team_admin_context)
        app = _build_app(
            provider,
            required_scopes=[Scope.collection_write.value],
        )
        client = TestClient(app, raise_server_exceptions=True)
        response = client.get("/read", headers={"Authorization": "Bearer tok"})
        assert response.status_code == 200

    def test_team_admin_does_not_have_admin_wildcard(
        self, team_admin_context: AuthContext
    ) -> None:
        """team_admin must not carry the admin:* wildcard — only system_admin does."""
        assert Scope.admin_wildcard.value not in team_admin_context.scopes
        assert not team_admin_context.is_admin()

    def test_team_admin_can_reach_read_write_multi_scope_endpoint(
        self, team_admin_context: AuthContext
    ) -> None:
        """Endpoint requiring artifact:read + artifact:write is reachable by team_admin."""
        provider = MockScopedProvider(team_admin_context)
        app = _build_app(
            provider,
            multi_scope_endpoint_scopes=[
                Scope.artifact_read.value,
                Scope.artifact_write.value,
            ],
        )
        client = TestClient(app, raise_server_exceptions=True)
        response = client.get(
            "/multi-scope", headers={"Authorization": "Bearer tok"}
        )
        assert response.status_code == 200

    def test_team_admin_cannot_reach_deployment_write_endpoint(
        self, team_admin_context: AuthContext
    ) -> None:
        """team_admin context (as defined by fixture) lacks deployment:write → 403."""
        assert Scope.deployment_write.value not in team_admin_context.scopes
        provider = MockScopedProvider(team_admin_context)
        app = _build_app(
            provider,
            required_scopes=[Scope.deployment_write.value],
        )
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/read", headers={"Authorization": "Bearer tok"})
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# 8. Viewer role has read-only scopes
# ---------------------------------------------------------------------------


class TestViewerRole:
    """viewer role is restricted to read-only operations."""

    def test_viewer_can_read_artifacts(self, viewer_context: AuthContext) -> None:
        """Viewer holds artifact:read and can access a read-gated endpoint."""
        assert Scope.artifact_read.value in viewer_context.scopes
        provider = MockScopedProvider(viewer_context)
        app = _build_app(
            provider,
            required_scopes=[Scope.artifact_read.value],
        )
        client = TestClient(app, raise_server_exceptions=True)
        response = client.get("/read", headers={"Authorization": "Bearer tok"})
        assert response.status_code == 200

    def test_viewer_cannot_write_artifacts(self, viewer_context: AuthContext) -> None:
        """Viewer lacks artifact:write and gets 403 on write-gated endpoint."""
        assert Scope.artifact_write.value not in viewer_context.scopes
        provider = MockScopedProvider(viewer_context)
        app = _build_app(
            provider,
            required_scopes=[Scope.artifact_write.value],
        )
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/read", headers={"Authorization": "Bearer tok"})
        assert response.status_code == 403

    def test_viewer_cannot_write_collections(self, viewer_context: AuthContext) -> None:
        """Viewer lacks collection:write and gets 403 on collection write endpoint."""
        assert Scope.collection_write.value not in viewer_context.scopes
        provider = MockScopedProvider(viewer_context)
        app = _build_app(
            provider,
            required_scopes=[Scope.collection_write.value],
        )
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/read", headers={"Authorization": "Bearer tok"})
        assert response.status_code == 403

    def test_viewer_cannot_write_deployments(self, viewer_context: AuthContext) -> None:
        """Viewer lacks deployment:write and gets 403."""
        assert Scope.deployment_write.value not in viewer_context.scopes
        provider = MockScopedProvider(viewer_context)
        app = _build_app(
            provider,
            required_scopes=[Scope.deployment_write.value],
        )
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/read", headers={"Authorization": "Bearer tok"})
        assert response.status_code == 403

    def test_viewer_is_not_admin(self, viewer_context: AuthContext) -> None:
        """Viewer role does not carry system_admin privileges."""
        assert not viewer_context.is_admin()
        assert not viewer_context.has_role(Role.system_admin)


# ---------------------------------------------------------------------------
# 9. Invalid / unrecognized scope format handling
# ---------------------------------------------------------------------------


class TestInvalidScopeFormat:
    """Unrecognized scope strings in AuthContext and require_auth() are handled safely.

    The AuthContext.has_scope() method works on plain strings so that custom
    or future scope values do not require enum changes.  The HTTP layer must
    not crash when it encounters an unrecognized scope — it should simply
    treat it as missing.
    """

    def test_unrecognized_scope_in_required_list_causes_403(self) -> None:
        """A scope string not held by the context (even if unrecognized) → 403."""
        ctx = AuthContext(
            user_id=uuid.uuid4(),
            roles=[Role.viewer.value],
            scopes=[Scope.artifact_read.value],
        )
        provider = MockScopedProvider(ctx)
        # Pass a raw string not defined in the Scope enum
        app = _build_app(provider, required_scopes=["custom:superpower"])
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/read", headers={"Authorization": "Bearer tok"})
        assert response.status_code == 403

    def test_unrecognized_scope_in_context_does_not_cause_error(self) -> None:
        """AuthContext can carry unknown scope strings without raising exceptions."""
        ctx = AuthContext(
            user_id=uuid.uuid4(),
            roles=[Role.viewer.value],
            scopes=["custom:future-scope", Scope.artifact_read.value],
        )
        # has_scope on a known scope still works correctly
        assert ctx.has_scope(Scope.artifact_read)
        assert not ctx.has_scope(Scope.artifact_write)

    def test_unrecognized_scope_in_context_can_be_matched_as_string(self) -> None:
        """has_scope() accepts raw strings and matches unknown scopes correctly."""
        ctx = AuthContext(
            user_id=uuid.uuid4(),
            roles=[Role.viewer.value],
            scopes=["custom:future-scope"],
        )
        assert ctx.has_scope("custom:future-scope")
        assert not ctx.has_scope("custom:other")

    def test_empty_string_scope_does_not_grant_access(self) -> None:
        """An empty-string scope in the required list is treated as absent → 403."""
        ctx = AuthContext(
            user_id=uuid.uuid4(),
            roles=[Role.viewer.value],
            scopes=[Scope.artifact_read.value],
        )
        provider = MockScopedProvider(ctx)
        app = _build_app(provider, required_scopes=[""])
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/read", headers={"Authorization": "Bearer tok"})
        # Empty string not in scopes → 403
        assert response.status_code == 403

    def test_unrecognized_required_scope_named_in_403_detail(self) -> None:
        """The 403 detail names the unrecognized scope so callers can diagnose it."""
        ctx = AuthContext(
            user_id=uuid.uuid4(),
            roles=[Role.viewer.value],
            scopes=[Scope.artifact_read.value],
        )
        provider = MockScopedProvider(ctx)
        app = _build_app(provider, required_scopes=["custom:superpower"])
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/read", headers={"Authorization": "Bearer tok"})
        detail = response.json()["detail"]
        assert "custom:superpower" in detail


# ---------------------------------------------------------------------------
# 10. AuthContext unit-level helper methods
# ---------------------------------------------------------------------------


class TestAuthContextHelpers:
    """Unit tests for AuthContext.has_role, has_scope, has_any_scope, is_admin."""

    # has_role -----------------------------------------------------------

    def test_has_role_returns_true_for_held_role(self) -> None:
        ctx = AuthContext(
            user_id=uuid.uuid4(),
            roles=[Role.team_member.value],
            scopes=[],
        )
        assert ctx.has_role(Role.team_member)

    def test_has_role_accepts_string_value(self) -> None:
        ctx = AuthContext(
            user_id=uuid.uuid4(),
            roles=[Role.team_admin.value],
            scopes=[],
        )
        assert ctx.has_role("team_admin")

    def test_has_role_returns_false_for_absent_role(self) -> None:
        ctx = AuthContext(
            user_id=uuid.uuid4(),
            roles=[Role.viewer.value],
            scopes=[],
        )
        assert not ctx.has_role(Role.system_admin)

    def test_has_role_returns_false_for_empty_roles(self) -> None:
        ctx = AuthContext(user_id=uuid.uuid4(), roles=[], scopes=[])
        assert not ctx.has_role(Role.viewer)

    # is_admin -----------------------------------------------------------

    def test_is_admin_true_for_system_admin_role(self) -> None:
        ctx = AuthContext(
            user_id=uuid.uuid4(),
            roles=[Role.system_admin.value],
            scopes=[],
        )
        assert ctx.is_admin()

    def test_is_admin_false_for_team_admin_role(self) -> None:
        ctx = AuthContext(
            user_id=uuid.uuid4(),
            roles=[Role.team_admin.value],
            scopes=[],
        )
        assert not ctx.is_admin()

    def test_is_admin_false_for_viewer_role(self) -> None:
        ctx = AuthContext(
            user_id=uuid.uuid4(),
            roles=[Role.viewer.value],
            scopes=[],
        )
        assert not ctx.is_admin()

    # has_scope ----------------------------------------------------------

    def test_has_scope_returns_true_for_held_scope(self) -> None:
        ctx = AuthContext(
            user_id=uuid.uuid4(),
            roles=[],
            scopes=[Scope.artifact_read.value],
        )
        assert ctx.has_scope(Scope.artifact_read)

    def test_has_scope_accepts_string_value(self) -> None:
        ctx = AuthContext(
            user_id=uuid.uuid4(),
            roles=[],
            scopes=[Scope.collection_read.value],
        )
        assert ctx.has_scope("collection:read")

    def test_has_scope_returns_false_for_absent_scope(self) -> None:
        ctx = AuthContext(
            user_id=uuid.uuid4(),
            roles=[],
            scopes=[Scope.artifact_read.value],
        )
        assert not ctx.has_scope(Scope.artifact_write)

    def test_has_scope_admin_wildcard_returns_true_for_any_scope(self) -> None:
        ctx = AuthContext(
            user_id=uuid.uuid4(),
            roles=[],
            scopes=[Scope.admin_wildcard.value],
        )
        for scope in Scope:
            assert ctx.has_scope(scope), (
                f"admin wildcard context should satisfy {scope!r}"
            )

    def test_has_scope_returns_false_for_empty_scopes(self) -> None:
        ctx = AuthContext(user_id=uuid.uuid4(), roles=[], scopes=[])
        assert not ctx.has_scope(Scope.artifact_read)

    # has_any_scope ------------------------------------------------------

    def test_has_any_scope_true_when_one_matches(self) -> None:
        ctx = AuthContext(
            user_id=uuid.uuid4(),
            roles=[],
            scopes=[Scope.artifact_read.value],
        )
        assert ctx.has_any_scope(Scope.artifact_read, Scope.artifact_write)

    def test_has_any_scope_false_when_none_match(self) -> None:
        ctx = AuthContext(
            user_id=uuid.uuid4(),
            roles=[],
            scopes=[Scope.artifact_read.value],
        )
        assert not ctx.has_any_scope(Scope.artifact_write, Scope.collection_write)

    def test_has_any_scope_true_for_admin_wildcard(self) -> None:
        ctx = AuthContext(
            user_id=uuid.uuid4(),
            roles=[],
            scopes=[Scope.admin_wildcard.value],
        )
        assert ctx.has_any_scope(Scope.deployment_write, Scope.collection_write)

    def test_has_any_scope_with_single_scope_behaves_like_has_scope(self) -> None:
        ctx = AuthContext(
            user_id=uuid.uuid4(),
            roles=[],
            scopes=[Scope.artifact_read.value],
        )
        assert ctx.has_any_scope(Scope.artifact_read)
        assert not ctx.has_any_scope(Scope.artifact_write)

    # Frozen / immutability ----------------------------------------------

    def test_auth_context_is_immutable(self) -> None:
        """AuthContext is a frozen dataclass; attribute assignment must raise."""
        ctx = AuthContext(
            user_id=uuid.uuid4(),
            roles=[Role.viewer.value],
            scopes=[Scope.artifact_read.value],
        )
        with pytest.raises((AttributeError, TypeError)):
            ctx.roles = [Role.system_admin.value]  # type: ignore[misc]
