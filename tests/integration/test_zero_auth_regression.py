"""Zero-auth regression tests — local (single-user) mode.

Verifies that **every** call succeeds without an ``Authorization`` header when
the application is running in local mode (``LocalAuthProvider``).  These tests
act as a regression guard: if a future change accidentally makes any path
require authentication in local mode, these tests will catch it immediately.

Scenarios covered
-----------------
1. API endpoints accessible without Authorization header in local mode.
2. LocalAuthProvider returns LOCAL_ADMIN_CONTEXT automatically.
3. CRUD operations (create / read / update / delete) work without auth.
4. List endpoints return data without auth.
5. Search endpoints work without auth.
6. Collection operations work without auth.
7. No 401/403 errors for any endpoint in local mode.
8. AuthContext in local mode carries admin-level scopes.
9. Existing functionality is unchanged (pre-auth feature parity).
10. Settings/config endpoints accessible without auth.

Design notes
------------
Tests use a self-contained FastAPI application rather than the full
``create_app()`` factory.  The full factory triggers a lifespan that connects
to databases, scans the filesystem, and seeds entity types, none of which is
relevant to auth behaviour.  A minimal app with realistic endpoint shapes lets
us verify the ``require_auth`` dependency in isolation without mocking dozens
of infrastructure dependencies.

``set_auth_provider(LocalAuthProvider())`` is called inside each fixture's
app factory — the same call the production lifespan makes.

References
----------
* AUTH-002  LocalAuthProvider implementation
* SVR-001   AuthContext dataclass
* SVR-002   Role / Scope enums
* TEST-009  Zero-auth regression test task
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

import pytest
from fastapi import Depends, FastAPI, Request, status
from fastapi.testclient import TestClient

from skillmeat.api.auth.local_provider import LocalAuthProvider
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
# Shared helpers
# ---------------------------------------------------------------------------

_ALL_SCOPES = {s.value for s in Scope}


def _build_local_app() -> FastAPI:
    """Create a minimal FastAPI application wired to LocalAuthProvider.

    The app exposes a realistic set of endpoint shapes that mirror common
    SkillMeat API patterns — list, get, create, update, delete, search,
    collection ops, and settings/config — all protected via ``require_auth``.
    """
    set_auth_provider(LocalAuthProvider())

    app = FastAPI()

    # ------------------------------------------------------------------
    # Public endpoint (sanity reference — always open)
    # ------------------------------------------------------------------

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    # ------------------------------------------------------------------
    # Scenario 1, 4: List endpoint
    # ------------------------------------------------------------------

    @app.get("/api/v1/artifacts")
    async def list_artifacts(
        auth: AuthContext = Depends(require_auth()),
    ) -> dict:
        return {
            "items": [
                {"id": "skill:canvas", "type": "skill", "name": "canvas"},
                {"id": "command:git-helper", "type": "command", "name": "git-helper"},
            ],
            "total": 2,
            "user_id": str(auth.user_id),
        }

    # ------------------------------------------------------------------
    # Scenario 5: Search endpoint
    # NOTE: Must be registered BEFORE the /{artifact_id} wildcard route
    #       to avoid FastAPI capturing "search" as an artifact_id.
    # ------------------------------------------------------------------

    @app.get("/api/v1/artifacts/search")
    async def search_artifacts(
        q: str = "",
        auth: AuthContext = Depends(require_auth()),
    ) -> dict:
        return {
            "results": [{"id": "skill:canvas", "score": 0.95}],
            "query": q,
            "user_id": str(auth.user_id),
        }

    # ------------------------------------------------------------------
    # Scenario 3: Read (GET single item)
    # ------------------------------------------------------------------

    @app.get("/api/v1/artifacts/{artifact_id}")
    async def get_artifact(
        artifact_id: str,
        auth: AuthContext = Depends(require_auth()),
    ) -> dict:
        return {
            "id": artifact_id,
            "type": "skill",
            "name": "canvas",
            "user_id": str(auth.user_id),
        }

    # ------------------------------------------------------------------
    # Scenario 3: Create (POST)
    # ------------------------------------------------------------------

    @app.post("/api/v1/artifacts", status_code=status.HTTP_201_CREATED)
    async def create_artifact(
        auth: AuthContext = Depends(
            require_auth(scopes=[Scope.artifact_write.value])
        ),
    ) -> dict:
        return {
            "id": f"skill:{uuid.uuid4().hex[:8]}",
            "created": True,
            "user_id": str(auth.user_id),
        }

    # ------------------------------------------------------------------
    # Scenario 3: Update (PUT)
    # ------------------------------------------------------------------

    @app.put("/api/v1/artifacts/{artifact_id}")
    async def update_artifact(
        artifact_id: str,
        auth: AuthContext = Depends(
            require_auth(scopes=[Scope.artifact_write.value])
        ),
    ) -> dict:
        return {
            "id": artifact_id,
            "updated": True,
            "user_id": str(auth.user_id),
        }

    # ------------------------------------------------------------------
    # Scenario 3: Delete (DELETE)
    # ------------------------------------------------------------------

    @app.delete("/api/v1/artifacts/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_artifact(
        artifact_id: str,
        auth: AuthContext = Depends(
            require_auth(scopes=[Scope.artifact_write.value])
        ),
    ) -> None:
        return None

    # ------------------------------------------------------------------
    # Scenario 6: Collection operations
    # ------------------------------------------------------------------

    @app.get("/api/v1/collections")
    async def list_collections(
        auth: AuthContext = Depends(require_auth()),
    ) -> dict:
        return {
            "items": [{"id": "col-1", "name": "default"}],
            "user_id": str(auth.user_id),
        }

    @app.post("/api/v1/collections", status_code=status.HTTP_201_CREATED)
    async def create_collection(
        auth: AuthContext = Depends(
            require_auth(scopes=[Scope.collection_write.value])
        ),
    ) -> dict:
        return {
            "id": f"col-{uuid.uuid4().hex[:6]}",
            "created": True,
            "user_id": str(auth.user_id),
        }

    @app.get("/api/v1/collections/{collection_id}")
    async def get_collection(
        collection_id: str,
        auth: AuthContext = Depends(
            require_auth(scopes=[Scope.collection_read.value])
        ),
    ) -> dict:
        return {
            "id": collection_id,
            "name": "my-collection",
            "user_id": str(auth.user_id),
        }

    @app.delete(
        "/api/v1/collections/{collection_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    async def delete_collection(
        collection_id: str,
        auth: AuthContext = Depends(
            require_auth(scopes=[Scope.collection_write.value])
        ),
    ) -> None:
        return None

    # ------------------------------------------------------------------
    # Scenario 10: Settings / config endpoints
    # ------------------------------------------------------------------

    @app.get("/api/v1/settings")
    async def get_settings(
        auth: AuthContext = Depends(require_auth()),
    ) -> dict:
        return {
            "theme": "dark",
            "notifications_enabled": True,
            "user_id": str(auth.user_id),
        }

    @app.get("/api/v1/config")
    async def get_config(
        auth: AuthContext = Depends(require_auth()),
    ) -> dict:
        return {
            "edition": "local",
            "auth_provider": "local",
            "user_id": str(auth.user_id),
        }

    # ------------------------------------------------------------------
    # Scenario 2, 8: AuthContext inspection endpoint
    # ------------------------------------------------------------------

    @app.get("/api/v1/me")
    async def get_me(
        request: Request,
        auth: AuthContext = Depends(require_auth()),
    ) -> dict:
        state_ctx: Optional[AuthContext] = getattr(
            request.state, "auth_context", None
        )
        return {
            "user_id": str(auth.user_id),
            "tenant_id": str(auth.tenant_id) if auth.tenant_id else None,
            "roles": auth.roles,
            "scopes": auth.scopes,
            "is_admin": auth.is_admin(),
            "has_admin_wildcard": auth.has_scope(Scope.admin_wildcard),
            "auth_context_on_state": state_ctx is not None,
            "state_user_id": str(state_ctx.user_id) if state_ctx else None,
        }

    # ------------------------------------------------------------------
    # Scenario 5 (extended): Deployment read endpoint
    # ------------------------------------------------------------------

    @app.get("/api/v1/deployments")
    async def list_deployments(
        auth: AuthContext = Depends(
            require_auth(scopes=[Scope.deployment_read.value])
        ),
    ) -> dict:
        return {
            "items": [{"id": "dep-1", "artifact": "skill:canvas", "status": "active"}],
            "user_id": str(auth.user_id),
        }

    # ------------------------------------------------------------------
    # Scenario 9: Pre-auth feature parity — multiple reads in sequence
    # ------------------------------------------------------------------

    @app.get("/api/v1/tags")
    async def list_tags(
        auth: AuthContext = Depends(require_auth()),
    ) -> dict:
        return {"tags": ["python", "cli", "ai"], "user_id": str(auth.user_id)}

    @app.get("/api/v1/projects")
    async def list_projects(
        auth: AuthContext = Depends(require_auth()),
    ) -> dict:
        return {
            "items": [{"path": "/home/user/my-project", "name": "my-project"}],
            "user_id": str(auth.user_id),
        }

    return app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_auth_provider():
    """Reset the module-level auth provider to None after every test.

    Prevents state leakage between tests that call ``set_auth_provider()``.
    """
    import skillmeat.api.dependencies as _deps

    yield
    _deps._auth_provider = None


@pytest.fixture
def local_app() -> FastAPI:
    """Function-scoped local-mode FastAPI app.

    Built fresh per test so that each call to ``set_auth_provider`` inside
    ``_build_local_app()`` is consistent with the ``_reset_auth_provider``
    autouse fixture (which runs at the same function scope and resets the
    module-level provider to ``None`` after every test).
    """
    return _build_local_app()


@pytest.fixture
def client(local_app: FastAPI) -> TestClient:
    """Function-scoped TestClient — no Authorization header is ever attached."""
    return TestClient(local_app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# 1. API endpoints accessible without Authorization header in local mode
# ---------------------------------------------------------------------------


class TestEndpointsAccessibleWithoutAuthHeader:
    """Every protected endpoint returns 2xx without an Authorization header."""

    def test_list_artifacts_no_auth_header(self, client: TestClient) -> None:
        """GET /api/v1/artifacts returns 200 without Authorization."""
        response = client.get("/api/v1/artifacts")
        assert response.status_code == 200

    def test_get_artifact_no_auth_header(self, client: TestClient) -> None:
        """GET /api/v1/artifacts/{id} returns 200 without Authorization."""
        response = client.get("/api/v1/artifacts/skill:canvas")
        assert response.status_code == 200

    def test_search_no_auth_header(self, client: TestClient) -> None:
        """GET /api/v1/artifacts/search returns 200 without Authorization."""
        response = client.get("/api/v1/artifacts/search?q=canvas")
        assert response.status_code == 200

    def test_list_collections_no_auth_header(self, client: TestClient) -> None:
        """GET /api/v1/collections returns 200 without Authorization."""
        response = client.get("/api/v1/collections")
        assert response.status_code == 200

    def test_list_deployments_no_auth_header(self, client: TestClient) -> None:
        """GET /api/v1/deployments returns 200 without Authorization."""
        response = client.get("/api/v1/deployments")
        assert response.status_code == 200

    def test_settings_no_auth_header(self, client: TestClient) -> None:
        """GET /api/v1/settings returns 200 without Authorization."""
        response = client.get("/api/v1/settings")
        assert response.status_code == 200

    def test_config_no_auth_header(self, client: TestClient) -> None:
        """GET /api/v1/config returns 200 without Authorization."""
        response = client.get("/api/v1/config")
        assert response.status_code == 200

    def test_me_no_auth_header(self, client: TestClient) -> None:
        """GET /api/v1/me returns 200 without Authorization."""
        response = client.get("/api/v1/me")
        assert response.status_code == 200

    def test_tags_no_auth_header(self, client: TestClient) -> None:
        """GET /api/v1/tags returns 200 without Authorization."""
        response = client.get("/api/v1/tags")
        assert response.status_code == 200

    def test_projects_no_auth_header(self, client: TestClient) -> None:
        """GET /api/v1/projects returns 200 without Authorization."""
        response = client.get("/api/v1/projects")
        assert response.status_code == 200

    def test_health_no_auth_header(self, client: TestClient) -> None:
        """Public /health returns 200 without Authorization."""
        response = client.get("/health")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# 2. LocalAuthProvider returns LOCAL_ADMIN_CONTEXT automatically
# ---------------------------------------------------------------------------


class TestLocalAdminContextAutoInjected:
    """LocalAuthProvider injects LOCAL_ADMIN_CONTEXT on every request."""

    def test_user_id_matches_local_admin(self, client: TestClient) -> None:
        """Response user_id equals LOCAL_ADMIN_CONTEXT.user_id."""
        response = client.get("/api/v1/me")
        assert response.json()["user_id"] == str(LOCAL_ADMIN_CONTEXT.user_id)

    def test_tenant_id_is_none_for_local_mode(self, client: TestClient) -> None:
        """LOCAL_ADMIN_CONTEXT has no tenant (local single-user mode)."""
        response = client.get("/api/v1/me")
        assert response.json()["tenant_id"] is None

    def test_local_admin_has_system_admin_role(self, client: TestClient) -> None:
        """LOCAL_ADMIN_CONTEXT carries the system_admin role."""
        response = client.get("/api/v1/me")
        assert Role.system_admin.value in response.json()["roles"]

    def test_auth_context_stored_on_request_state(self, client: TestClient) -> None:
        """require_auth stores auth_context on request.state in local mode."""
        response = client.get("/api/v1/me")
        data = response.json()
        assert data["auth_context_on_state"] is True

    def test_state_user_id_matches_dep_user_id(self, client: TestClient) -> None:
        """request.state.auth_context.user_id matches the Depends() auth_context."""
        response = client.get("/api/v1/me")
        data = response.json()
        assert data["state_user_id"] == data["user_id"]

    def test_list_endpoint_embeds_local_admin_user_id(
        self, client: TestClient
    ) -> None:
        """List endpoint user_id field equals LOCAL_ADMIN_CONTEXT.user_id."""
        response = client.get("/api/v1/artifacts")
        assert response.json()["user_id"] == str(LOCAL_ADMIN_CONTEXT.user_id)


# ---------------------------------------------------------------------------
# 3. CRUD operations work without auth
# ---------------------------------------------------------------------------


class TestCRUDWithoutAuth:
    """Create, read, update, delete — all succeed without Authorization."""

    def test_create_artifact_returns_201(self, client: TestClient) -> None:
        """POST /api/v1/artifacts returns 201 Created without auth header."""
        response = client.post("/api/v1/artifacts")
        assert response.status_code == 201

    def test_create_artifact_returns_created_flag(self, client: TestClient) -> None:
        """Response body for artifact creation contains created=True."""
        response = client.post("/api/v1/artifacts")
        assert response.json()["created"] is True

    def test_create_artifact_embeds_user_id(self, client: TestClient) -> None:
        """Created artifact response embeds the local_admin user_id."""
        response = client.post("/api/v1/artifacts")
        assert response.json()["user_id"] == str(LOCAL_ADMIN_CONTEXT.user_id)

    def test_read_artifact_returns_200(self, client: TestClient) -> None:
        """GET /api/v1/artifacts/{id} returns 200 without auth header."""
        response = client.get("/api/v1/artifacts/skill:canvas")
        assert response.status_code == 200

    def test_read_artifact_returns_correct_id(self, client: TestClient) -> None:
        """GET response contains the requested artifact_id."""
        response = client.get("/api/v1/artifacts/skill:canvas")
        assert response.json()["id"] == "skill:canvas"

    def test_update_artifact_returns_200(self, client: TestClient) -> None:
        """PUT /api/v1/artifacts/{id} returns 200 without auth header."""
        response = client.put("/api/v1/artifacts/skill:canvas")
        assert response.status_code == 200

    def test_update_artifact_returns_updated_flag(self, client: TestClient) -> None:
        """Response body for artifact update contains updated=True."""
        response = client.put("/api/v1/artifacts/skill:canvas")
        assert response.json()["updated"] is True

    def test_delete_artifact_returns_204(self, client: TestClient) -> None:
        """DELETE /api/v1/artifacts/{id} returns 204 No Content without auth."""
        response = client.delete("/api/v1/artifacts/skill:canvas")
        assert response.status_code == 204

    def test_delete_collection_returns_204(self, client: TestClient) -> None:
        """DELETE /api/v1/collections/{id} returns 204 No Content without auth."""
        response = client.delete("/api/v1/collections/col-1")
        assert response.status_code == 204

    def test_create_collection_returns_201(self, client: TestClient) -> None:
        """POST /api/v1/collections returns 201 Created without auth header."""
        response = client.post("/api/v1/collections")
        assert response.status_code == 201


# ---------------------------------------------------------------------------
# 4. List endpoints return data without auth
# ---------------------------------------------------------------------------


class TestListEndpointsReturnData:
    """List endpoints return non-empty, well-formed responses without auth."""

    def test_artifacts_list_has_items_key(self, client: TestClient) -> None:
        """Artifact list response contains an 'items' key."""
        response = client.get("/api/v1/artifacts")
        assert "items" in response.json()

    def test_artifacts_list_returns_expected_count(
        self, client: TestClient
    ) -> None:
        """Artifact list returns the expected total count."""
        data = client.get("/api/v1/artifacts").json()
        assert data["total"] == 2

    def test_collections_list_has_items_key(self, client: TestClient) -> None:
        """Collections list response contains an 'items' key."""
        response = client.get("/api/v1/collections")
        assert "items" in response.json()

    def test_deployments_list_has_items_key(self, client: TestClient) -> None:
        """Deployments list response contains an 'items' key."""
        response = client.get("/api/v1/deployments")
        assert "items" in response.json()

    def test_tags_list_has_tags_key(self, client: TestClient) -> None:
        """Tags list response contains a 'tags' key."""
        response = client.get("/api/v1/tags")
        assert "tags" in response.json()

    def test_projects_list_has_items_key(self, client: TestClient) -> None:
        """Projects list response contains an 'items' key."""
        response = client.get("/api/v1/projects")
        assert "items" in response.json()

    def test_all_list_responses_are_200(self, client: TestClient) -> None:
        """All list endpoints return HTTP 200."""
        endpoints = [
            "/api/v1/artifacts",
            "/api/v1/collections",
            "/api/v1/deployments",
            "/api/v1/tags",
            "/api/v1/projects",
        ]
        for path in endpoints:
            response = client.get(path)
            assert response.status_code == 200, (
                f"{path} returned {response.status_code}, expected 200"
            )


# ---------------------------------------------------------------------------
# 5. Search endpoints work without auth
# ---------------------------------------------------------------------------


class TestSearchEndpointsWithoutAuth:
    """Search endpoints return 200 and results without Authorization."""

    def test_search_with_query_returns_200(self, client: TestClient) -> None:
        """GET /api/v1/artifacts/search?q=canvas returns 200."""
        response = client.get("/api/v1/artifacts/search?q=canvas")
        assert response.status_code == 200

    def test_search_echoes_query_string(self, client: TestClient) -> None:
        """Search response echoes the query parameter."""
        response = client.get("/api/v1/artifacts/search?q=canvas")
        assert response.json()["query"] == "canvas"

    def test_search_has_results_key(self, client: TestClient) -> None:
        """Search response contains a 'results' key."""
        response = client.get("/api/v1/artifacts/search?q=canvas")
        assert "results" in response.json()

    def test_search_with_empty_query_returns_200(self, client: TestClient) -> None:
        """Search without a query string still returns 200."""
        response = client.get("/api/v1/artifacts/search")
        assert response.status_code == 200

    def test_search_embeds_user_id(self, client: TestClient) -> None:
        """Search response embeds the local_admin user_id."""
        response = client.get("/api/v1/artifacts/search?q=test")
        assert response.json()["user_id"] == str(LOCAL_ADMIN_CONTEXT.user_id)


# ---------------------------------------------------------------------------
# 6. Collection operations work without auth
# ---------------------------------------------------------------------------


class TestCollectionOperationsWithoutAuth:
    """All collection CRUD and membership operations succeed without auth."""

    def test_list_collections_returns_200(self, client: TestClient) -> None:
        """GET /api/v1/collections returns 200 without auth."""
        response = client.get("/api/v1/collections")
        assert response.status_code == 200

    def test_get_single_collection_returns_200(self, client: TestClient) -> None:
        """GET /api/v1/collections/{id} returns 200 without auth."""
        response = client.get("/api/v1/collections/col-1")
        assert response.status_code == 200

    def test_get_single_collection_returns_id(self, client: TestClient) -> None:
        """GET single collection response contains the requested id."""
        response = client.get("/api/v1/collections/col-1")
        assert response.json()["id"] == "col-1"

    def test_create_collection_returns_201(self, client: TestClient) -> None:
        """POST /api/v1/collections returns 201 without auth."""
        response = client.post("/api/v1/collections")
        assert response.status_code == 201

    def test_create_collection_has_created_flag(self, client: TestClient) -> None:
        """Collection creation response includes created=True."""
        response = client.post("/api/v1/collections")
        assert response.json()["created"] is True

    def test_delete_collection_returns_204(self, client: TestClient) -> None:
        """DELETE /api/v1/collections/{id} returns 204 without auth."""
        response = client.delete("/api/v1/collections/col-1")
        assert response.status_code == 204

    def test_collection_read_requires_read_scope_satisfied_by_admin(
        self, client: TestClient
    ) -> None:
        """collection:read scope endpoint passes because admin:* satisfies all scopes."""
        response = client.get("/api/v1/collections/col-1")
        assert response.status_code == 200

    def test_collection_write_requires_write_scope_satisfied_by_admin(
        self, client: TestClient
    ) -> None:
        """collection:write scope endpoint passes because admin:* satisfies all scopes."""
        response = client.post("/api/v1/collections")
        assert response.status_code == 201


# ---------------------------------------------------------------------------
# 7. No 401/403 errors for any endpoint in local mode
# ---------------------------------------------------------------------------


class TestNo401Or403InLocalMode:
    """No endpoint may return 401 or 403 when running in local mode."""

    _ALL_ENDPOINTS: list[tuple[str, str]] = [
        ("GET", "/health"),
        ("GET", "/api/v1/artifacts"),
        ("GET", "/api/v1/artifacts/skill:canvas"),
        ("GET", "/api/v1/artifacts/search"),
        ("POST", "/api/v1/artifacts"),
        ("PUT", "/api/v1/artifacts/skill:canvas"),
        ("DELETE", "/api/v1/artifacts/skill:canvas"),
        ("GET", "/api/v1/collections"),
        ("GET", "/api/v1/collections/col-1"),
        ("POST", "/api/v1/collections"),
        ("DELETE", "/api/v1/collections/col-1"),
        ("GET", "/api/v1/deployments"),
        ("GET", "/api/v1/settings"),
        ("GET", "/api/v1/config"),
        ("GET", "/api/v1/me"),
        ("GET", "/api/v1/tags"),
        ("GET", "/api/v1/projects"),
    ]

    @pytest.mark.parametrize("method,path", _ALL_ENDPOINTS)
    def test_endpoint_does_not_return_401(
        self, client: TestClient, method: str, path: str
    ) -> None:
        """Endpoint must not return 401 in local mode (no auth header sent)."""
        response = client.request(method, path)
        assert response.status_code != 401, (
            f"{method} {path} returned 401 in local mode — "
            "LocalAuthProvider must never reject requests."
        )

    @pytest.mark.parametrize("method,path", _ALL_ENDPOINTS)
    def test_endpoint_does_not_return_403(
        self, client: TestClient, method: str, path: str
    ) -> None:
        """Endpoint must not return 403 in local mode (admin:* satisfies all scopes)."""
        response = client.request(method, path)
        assert response.status_code != 403, (
            f"{method} {path} returned 403 in local mode — "
            "LOCAL_ADMIN_CONTEXT carries admin:* and must satisfy every scope check."
        )


# ---------------------------------------------------------------------------
# 8. AuthContext in local mode has admin-level scopes
# ---------------------------------------------------------------------------


class TestLocalModeAdminScopes:
    """LOCAL_ADMIN_CONTEXT carries all defined scopes and admin:* wildcard."""

    def test_local_admin_has_admin_wildcard_scope(
        self, client: TestClient
    ) -> None:
        """LOCAL_ADMIN_CONTEXT carries the admin:* wildcard scope."""
        response = client.get("/api/v1/me")
        assert response.json()["has_admin_wildcard"] is True

    def test_local_admin_is_admin(self, client: TestClient) -> None:
        """is_admin() returns True for LOCAL_ADMIN_CONTEXT."""
        response = client.get("/api/v1/me")
        assert response.json()["is_admin"] is True

    def test_local_admin_has_all_defined_scopes(
        self, client: TestClient
    ) -> None:
        """LOCAL_ADMIN_CONTEXT scopes set equals all Scope enum values."""
        response = client.get("/api/v1/me")
        actual_scopes = set(response.json()["scopes"])
        assert actual_scopes == _ALL_SCOPES

    def test_local_admin_has_artifact_read_scope(
        self, client: TestClient
    ) -> None:
        """LOCAL_ADMIN_CONTEXT explicitly carries artifact:read."""
        response = client.get("/api/v1/me")
        assert Scope.artifact_read.value in response.json()["scopes"]

    def test_local_admin_has_artifact_write_scope(
        self, client: TestClient
    ) -> None:
        """LOCAL_ADMIN_CONTEXT explicitly carries artifact:write."""
        response = client.get("/api/v1/me")
        assert Scope.artifact_write.value in response.json()["scopes"]

    def test_local_admin_has_collection_read_scope(
        self, client: TestClient
    ) -> None:
        """LOCAL_ADMIN_CONTEXT explicitly carries collection:read."""
        response = client.get("/api/v1/me")
        assert Scope.collection_read.value in response.json()["scopes"]

    def test_local_admin_has_collection_write_scope(
        self, client: TestClient
    ) -> None:
        """LOCAL_ADMIN_CONTEXT explicitly carries collection:write."""
        response = client.get("/api/v1/me")
        assert Scope.collection_write.value in response.json()["scopes"]

    def test_local_admin_has_deployment_read_scope(
        self, client: TestClient
    ) -> None:
        """LOCAL_ADMIN_CONTEXT explicitly carries deployment:read."""
        response = client.get("/api/v1/me")
        assert Scope.deployment_read.value in response.json()["scopes"]

    def test_local_admin_has_deployment_write_scope(
        self, client: TestClient
    ) -> None:
        """LOCAL_ADMIN_CONTEXT explicitly carries deployment:write."""
        response = client.get("/api/v1/me")
        assert Scope.deployment_write.value in response.json()["scopes"]

    def test_write_scope_endpoint_passes_without_extra_token(
        self, client: TestClient
    ) -> None:
        """Endpoints scoped to artifact:write pass because admin:* covers all scopes."""
        response = client.post("/api/v1/artifacts")
        assert response.status_code == 201

    def test_deployment_read_scoped_endpoint_passes(
        self, client: TestClient
    ) -> None:
        """Deployment:read scoped endpoint passes via admin:* wildcard."""
        response = client.get("/api/v1/deployments")
        assert response.status_code == 200

    def test_local_admin_context_is_singleton(self) -> None:
        """LocalAuthProvider always returns the exact LOCAL_ADMIN_CONTEXT singleton."""
        import asyncio

        provider = LocalAuthProvider()

        # Create a minimal request stub — validate() ignores it entirely
        from unittest.mock import MagicMock

        fake_request = MagicMock()

        ctx = asyncio.get_event_loop().run_until_complete(
            provider.validate(fake_request)
        )
        assert ctx is LOCAL_ADMIN_CONTEXT


# ---------------------------------------------------------------------------
# 9. Existing functionality unchanged (pre-auth feature parity)
# ---------------------------------------------------------------------------


class TestPreAuthFeatureParity:
    """Pre-auth functionality is not broken by the auth system in local mode.

    These tests simulate the exact same reads that SkillMeat performed before
    the AAA/RBAC system was introduced — proving the auth layer is transparent.
    """

    def test_sequential_reads_all_succeed(self, client: TestClient) -> None:
        """Multiple sequential reads across different endpoints all return 2xx."""
        responses = {
            "artifacts": client.get("/api/v1/artifacts"),
            "collections": client.get("/api/v1/collections"),
            "tags": client.get("/api/v1/tags"),
            "projects": client.get("/api/v1/projects"),
            "settings": client.get("/api/v1/settings"),
        }
        for name, resp in responses.items():
            assert resp.status_code == 200, (
                f"{name} returned {resp.status_code}, expected 200"
            )

    def test_read_then_create_then_delete_workflow(
        self, client: TestClient
    ) -> None:
        """Simulated CRUD workflow: list → create → read → delete."""
        # List (was always open)
        r_list = client.get("/api/v1/artifacts")
        assert r_list.status_code == 200

        # Create (new write path, must work without auth in local mode)
        r_create = client.post("/api/v1/artifacts")
        assert r_create.status_code == 201

        artifact_id = r_create.json()["id"]

        # Read the new artifact
        r_get = client.get(f"/api/v1/artifacts/{artifact_id}")
        assert r_get.status_code == 200

        # Delete it
        r_delete = client.delete(f"/api/v1/artifacts/{artifact_id}")
        assert r_delete.status_code == 204

    def test_collection_workflow_without_auth(self, client: TestClient) -> None:
        """Simulated collection workflow: list → create → read → delete."""
        r_list = client.get("/api/v1/collections")
        assert r_list.status_code == 200

        r_create = client.post("/api/v1/collections")
        assert r_create.status_code == 201
        col_id = r_create.json()["id"]

        r_get = client.get(f"/api/v1/collections/{col_id}")
        assert r_get.status_code == 200

        r_delete = client.delete(f"/api/v1/collections/{col_id}")
        assert r_delete.status_code == 204

    def test_ignoring_auth_header_does_not_break_response(
        self, client: TestClient
    ) -> None:
        """Adding an Authorization header in local mode still returns 200 (not 401/400).

        LocalAuthProvider ignores all request headers, so an accidental or
        legacy auth header must not cause a failure.
        """
        response = client.get(
            "/api/v1/artifacts",
            headers={"Authorization": "Bearer legacy-or-accidental-token"},
        )
        assert response.status_code == 200

    def test_response_body_structure_unchanged(self, client: TestClient) -> None:
        """Artifact list response has the same top-level shape as before auth."""
        data = client.get("/api/v1/artifacts").json()
        assert "items" in data
        assert "total" in data
        # user_id is a new addition — must be present but must not break old keys
        assert "user_id" in data

    def test_multiple_concurrent_like_calls_return_consistent_user_id(
        self, client: TestClient
    ) -> None:
        """Repeated calls from the same session all carry the same local_admin user_id.

        Simulates what would happen in a multi-request frontend session.
        """
        ids = {
            client.get("/api/v1/artifacts").json()["user_id"],
            client.get("/api/v1/collections").json()["user_id"],
            client.get("/api/v1/tags").json()["user_id"],
            client.get("/api/v1/projects").json()["user_id"],
        }
        # All calls must return the same local_admin UUID
        assert ids == {str(LOCAL_ADMIN_CONTEXT.user_id)}


# ---------------------------------------------------------------------------
# 10. Settings / config endpoints accessible without auth
# ---------------------------------------------------------------------------


class TestSettingsAndConfigEndpointsWithoutAuth:
    """Settings and config endpoints return 200 without Authorization."""

    def test_settings_endpoint_returns_200(self, client: TestClient) -> None:
        """GET /api/v1/settings returns 200 without auth."""
        response = client.get("/api/v1/settings")
        assert response.status_code == 200

    def test_settings_response_has_expected_keys(
        self, client: TestClient
    ) -> None:
        """Settings response contains expected configuration keys."""
        data = client.get("/api/v1/settings").json()
        assert "theme" in data
        assert "notifications_enabled" in data

    def test_settings_embeds_user_id(self, client: TestClient) -> None:
        """Settings response embeds local_admin user_id."""
        data = client.get("/api/v1/settings").json()
        assert data["user_id"] == str(LOCAL_ADMIN_CONTEXT.user_id)

    def test_config_endpoint_returns_200(self, client: TestClient) -> None:
        """GET /api/v1/config returns 200 without auth."""
        response = client.get("/api/v1/config")
        assert response.status_code == 200

    def test_config_response_has_edition_field(self, client: TestClient) -> None:
        """Config response includes the edition field."""
        data = client.get("/api/v1/config").json()
        assert "edition" in data

    def test_config_shows_local_auth_provider(self, client: TestClient) -> None:
        """Config response reports auth_provider='local'."""
        data = client.get("/api/v1/config").json()
        assert data["auth_provider"] == "local"

    def test_config_embeds_user_id(self, client: TestClient) -> None:
        """Config response embeds local_admin user_id."""
        data = client.get("/api/v1/config").json()
        assert data["user_id"] == str(LOCAL_ADMIN_CONTEXT.user_id)

    def test_settings_and_config_consistent_user_id(
        self, client: TestClient
    ) -> None:
        """Both settings and config endpoints return the same user_id."""
        settings_uid = client.get("/api/v1/settings").json()["user_id"]
        config_uid = client.get("/api/v1/config").json()["user_id"]
        assert settings_uid == config_uid == str(LOCAL_ADMIN_CONTEXT.user_id)
