"""Enterprise DI regression tests — TEST2-002.

End-to-end tests that verify:

1. Enterprise edition provider resolution
   - ``get_artifact_repository()`` returns EnterpriseArtifactRepository when
     ``edition="enterprise"``.
   - ``get_collection_repository()`` returns EnterpriseCollectionRepository
     when ``edition="enterprise"``.
   - Unsupported providers raise HTTP 503 with a helpful message (deliberate
     gate, not accidental 503).

2. Local edition unchanged
   - ``edition="local"`` still returns local implementations.
   - No regression in local-mode dependency resolution.

3. Tenant context propagation
   - ``set_tenant_context_dep`` fires correctly in enterprise mode, setting
     TenantContext from AuthContext.tenant_id.
   - TenantContext is cleared after the request completes (no leakage).
   - When ``tenant_id`` is None (local mode) TenantContext is not mutated.

4. DB session lifecycle
   - Enterprise providers receive an injected Session from the request.
   - Sessions created in enterprise mode are distinct per request (no sharing).

5. Route-level integration
   - Supported enterprise routes resolve dependencies and do NOT return 503.
   - Unsupported routes return deliberate 503 with clear error message.

Design rationale
----------------
Tests use a *minimal* FastAPI application rather than the full ``create_app()``
factory — the full lifespan touches filesystems, databases, and GitHub APIs
that are irrelevant to DI routing logic.  Where routes are needed the minimal
app registers one endpoint per scenario so we can exercise ``get_app_state``
and ``get_db_session`` through real FastAPI DI without the rest of the server.

The auth provider is always ``LocalAuthProvider`` (zero-auth) to keep these
tests focused on edition routing rather than auth behaviour.  Auth-specific
behaviour is covered by ``test_auth_integration.py`` and ``test_rbac_scopes.py``.

References
----------
ENT2-001 — provider routing matrix
ENT2-002 — get_artifact_repository / get_collection_repository
ENT2-003 — unsupported provider gating
ENT2-004 — tenant wiring, DB session lifecycle
"""

from __future__ import annotations

import uuid
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import skillmeat.api.dependencies as _deps_module
from skillmeat.api.auth.local_provider import LocalAuthProvider
from skillmeat.api.dependencies import (
    AppState,
    get_artifact_repository,
    get_collection_repository,
    get_context_entity_repository,
    get_deployment_repository,
    get_group_repository,
    get_marketplace_source_repository,
    get_project_repository,
    get_project_template_repository,
    get_settings_repository,
    get_tag_repository,
    set_auth_provider,
)
from skillmeat.api.schemas.auth import (
    LOCAL_ADMIN_CONTEXT,
    AuthContext,
    Role,
    Scope,
)
from skillmeat.cache.enterprise_repositories import (
    TenantContext,
    tenant_scope,
)


# ---------------------------------------------------------------------------
# Helpers & fixtures
# ---------------------------------------------------------------------------


def _make_app_state(edition: str = "local") -> AppState:
    """Return a minimal AppState with settings.edition set."""
    state = AppState()
    mock_settings = MagicMock()
    mock_settings.edition = edition
    state.settings = mock_settings
    # Provide stub managers so manager-dependent providers don't raise on None
    state.artifact_manager = MagicMock()
    state.collection_manager = MagicMock()
    state.path_resolver = MagicMock()
    state.cache_manager = MagicMock()
    state.config_manager = MagicMock()
    return state


def _make_session() -> Session:
    """Return a MagicMock with spec=Session for DI injection."""
    return MagicMock(spec=Session)


@pytest.fixture(autouse=True)
def _reset_auth_provider():
    """Reset the module-level auth provider to None after every test."""
    yield
    _deps_module._auth_provider = None


# ---------------------------------------------------------------------------
# 1. Provider resolution — enterprise edition
# ---------------------------------------------------------------------------


class TestEnterpriseProviderResolution:
    """get_artifact_repository / get_collection_repository return enterprise
    implementations when edition='enterprise'."""

    def test_artifact_repository_returns_enterprise_impl(self):
        """get_artifact_repository returns EnterpriseArtifactRepository for enterprise."""
        from skillmeat.cache.enterprise_repositories import EnterpriseArtifactRepository

        state = _make_app_state(edition="enterprise")
        session = _make_session()

        repo = get_artifact_repository(state=state, session=session)

        assert isinstance(repo, EnterpriseArtifactRepository), (
            f"Expected EnterpriseArtifactRepository, got {type(repo).__name__}"
        )

    def test_collection_repository_returns_enterprise_impl(self):
        """get_collection_repository returns EnterpriseCollectionRepository for enterprise."""
        from skillmeat.cache.enterprise_repositories import EnterpriseCollectionRepository

        state = _make_app_state(edition="enterprise")
        session = _make_session()

        repo = get_collection_repository(state=state, session=session)

        assert isinstance(repo, EnterpriseCollectionRepository), (
            f"Expected EnterpriseCollectionRepository, got {type(repo).__name__}"
        )

    def test_enterprise_artifact_repo_receives_injected_session(self):
        """EnterpriseArtifactRepository is wired with the per-request session."""
        state = _make_app_state(edition="enterprise")
        session = _make_session()

        repo = get_artifact_repository(state=state, session=session)

        assert repo.session is session, (
            "EnterpriseArtifactRepository.session must be the injected Session instance"
        )

    def test_enterprise_collection_repo_receives_injected_session(self):
        """EnterpriseCollectionRepository is wired with the per-request session."""
        state = _make_app_state(edition="enterprise")
        session = _make_session()

        repo = get_collection_repository(state=state, session=session)

        assert repo.session is session, (
            "EnterpriseCollectionRepository.session must be the injected Session instance"
        )

    def test_unknown_edition_raises_503(self):
        """An unrecognised edition string raises HTTP 503."""
        state = _make_app_state(edition="invalid_edition")
        session = _make_session()

        with pytest.raises(HTTPException) as exc_info:
            get_artifact_repository(state=state, session=session)

        assert exc_info.value.status_code == 503
        assert "invalid_edition" in exc_info.value.detail

    def test_unknown_edition_collection_raises_503(self):
        """An unrecognised edition string raises HTTP 503 on collection provider."""
        state = _make_app_state(edition="community")  # not a real edition
        session = _make_session()

        with pytest.raises(HTTPException) as exc_info:
            get_collection_repository(state=state, session=session)

        assert exc_info.value.status_code == 503
        assert "community" in exc_info.value.detail


# ---------------------------------------------------------------------------
# 2. Local edition unchanged
# ---------------------------------------------------------------------------


class TestLocalProviderResolution:
    """Local edition continues to return local implementations (regression)."""

    def test_artifact_repository_returns_local_impl(self):
        """get_artifact_repository returns LocalArtifactRepository for local edition."""
        from skillmeat.core.repositories import LocalArtifactRepository

        state = _make_app_state(edition="local")
        session = _make_session()

        repo = get_artifact_repository(state=state, session=session)

        assert isinstance(repo, LocalArtifactRepository), (
            f"Expected LocalArtifactRepository, got {type(repo).__name__}"
        )

    def test_collection_repository_returns_local_impl(self):
        """get_collection_repository returns LocalCollectionRepository for local edition."""
        from skillmeat.core.repositories import LocalCollectionRepository

        state = _make_app_state(edition="local")
        session = _make_session()

        repo = get_collection_repository(state=state, session=session)

        assert isinstance(repo, LocalCollectionRepository), (
            f"Expected LocalCollectionRepository, got {type(repo).__name__}"
        )

    def test_project_repository_returns_local_impl(self):
        """get_project_repository returns LocalProjectRepository for local edition."""
        from skillmeat.core.repositories import LocalProjectRepository

        state = _make_app_state(edition="local")

        repo = get_project_repository(state=state)

        assert isinstance(repo, LocalProjectRepository)

    def test_deployment_repository_returns_local_impl(self):
        """get_deployment_repository returns LocalDeploymentRepository for local edition."""
        from skillmeat.core.repositories import LocalDeploymentRepository

        state = _make_app_state(edition="local")

        repo = get_deployment_repository(state=state)

        assert isinstance(repo, LocalDeploymentRepository)

    def test_tag_repository_returns_local_impl(self):
        """get_tag_repository returns LocalTagRepository for local edition."""
        from skillmeat.core.repositories import LocalTagRepository

        state = _make_app_state(edition="local")

        repo = get_tag_repository(state=state)

        assert isinstance(repo, LocalTagRepository)

    def test_settings_repository_returns_local_impl(self):
        """get_settings_repository returns LocalSettingsRepository for local edition."""
        from skillmeat.core.repositories import LocalSettingsRepository

        state = _make_app_state(edition="local")

        repo = get_settings_repository(state=state)

        assert isinstance(repo, LocalSettingsRepository)

    def test_group_repository_returns_local_impl(self):
        """get_group_repository returns LocalGroupRepository for local edition."""
        from skillmeat.core.repositories import LocalGroupRepository

        state = _make_app_state(edition="local")

        repo = get_group_repository(state=state)

        assert isinstance(repo, LocalGroupRepository)

    def test_context_entity_repository_returns_local_impl(self):
        """get_context_entity_repository returns LocalContextEntityRepository for local edition."""
        from skillmeat.core.repositories import LocalContextEntityRepository

        state = _make_app_state(edition="local")

        repo = get_context_entity_repository(state=state)

        assert isinstance(repo, LocalContextEntityRepository)

    def test_marketplace_source_repository_returns_local_impl(self):
        """get_marketplace_source_repository returns LocalMarketplaceSourceRepository."""
        from skillmeat.core.repositories import LocalMarketplaceSourceRepository

        state = _make_app_state(edition="local")

        repo = get_marketplace_source_repository(state=state)

        assert isinstance(repo, LocalMarketplaceSourceRepository)

    def test_project_template_repository_returns_local_impl(self):
        """get_project_template_repository returns LocalProjectTemplateRepository."""
        from skillmeat.core.repositories import LocalProjectTemplateRepository

        state = _make_app_state(edition="local")

        repo = get_project_template_repository(state=state)

        assert isinstance(repo, LocalProjectTemplateRepository)


# ---------------------------------------------------------------------------
# 3. Unsupported enterprise providers raise deliberate 503
# ---------------------------------------------------------------------------


class TestUnsupportedEnterpriseProviders:
    """Non-supported providers raise HTTP 503 with a descriptive message when
    edition='enterprise', proving the gate is intentional (not accidental)."""

    _UNSUPPORTED = [
        ("project", get_project_repository, {}),
        ("deployment", get_deployment_repository, {}),
        ("tag", get_tag_repository, {}),
        ("settings", get_settings_repository, {}),
        ("group", get_group_repository, {}),
        ("context_entity", get_context_entity_repository, {}),
        ("marketplace_source", get_marketplace_source_repository, {}),
        ("project_template", get_project_template_repository, {}),
    ]

    @pytest.mark.parametrize("name,factory,extra_kwargs", _UNSUPPORTED)
    def test_raises_503_not_500(self, name, factory, extra_kwargs):
        """Unsupported enterprise provider raises 503 (not 500 / AttributeError)."""
        state = _make_app_state(edition="enterprise")

        with pytest.raises(HTTPException) as exc_info:
            factory(state=state, **extra_kwargs)

        assert exc_info.value.status_code == 503, (
            f"Provider '{name}' should raise HTTP 503, got {exc_info.value.status_code}"
        )

    @pytest.mark.parametrize("name,factory,extra_kwargs", _UNSUPPORTED)
    def test_error_message_names_supported_providers(self, name, factory, extra_kwargs):
        """503 detail mentions that artifact and collection are supported."""
        state = _make_app_state(edition="enterprise")

        with pytest.raises(HTTPException) as exc_info:
            factory(state=state, **extra_kwargs)

        detail = exc_info.value.detail
        # Each unsupported provider's message should name supported alternatives
        assert "artifact" in detail or "collection" in detail or "enterprise" in detail, (
            f"Provider '{name}' 503 detail should mention supported providers, got: {detail!r}"
        )


# ---------------------------------------------------------------------------
# 4. Tenant context propagation
# ---------------------------------------------------------------------------


class TestTenantContextPropagation:
    """set_tenant_context_dep correctly sets and clears TenantContext."""

    def test_tenant_context_set_from_auth_context(self):
        """When auth_context has a tenant_id, TenantContext is set within the dependency."""
        from skillmeat.api.middleware.tenant_context import set_tenant_context_dep

        tenant_id = uuid.uuid4()
        auth_ctx = AuthContext(
            user_id=uuid.uuid4(),
            tenant_id=tenant_id,
            roles=[Role.team_member.value],
            scopes=[Scope.artifact_read.value],
        )

        observed_tenant_ids: list[Optional[uuid.UUID]] = []

        async def _run():
            gen = set_tenant_context_dep(auth_context=auth_ctx)
            await gen.__anext__()
            observed_tenant_ids.append(TenantContext.get(None))
            try:
                await gen.__anext__()
            except StopAsyncIteration:
                pass

        import asyncio
        asyncio.get_event_loop().run_until_complete(_run())

        assert observed_tenant_ids == [tenant_id], (
            f"TenantContext should be {tenant_id} during dependency, "
            f"got {observed_tenant_ids}"
        )

    def test_tenant_context_cleared_after_dependency(self):
        """TenantContext is reset to None after set_tenant_context_dep completes."""
        from skillmeat.api.middleware.tenant_context import set_tenant_context_dep

        tenant_id = uuid.uuid4()
        auth_ctx = AuthContext(
            user_id=uuid.uuid4(),
            tenant_id=tenant_id,
            roles=[Role.team_member.value],
            scopes=[Scope.artifact_read.value],
        )

        async def _run():
            gen = set_tenant_context_dep(auth_context=auth_ctx)
            await gen.__anext__()
            try:
                await gen.__anext__()
            except StopAsyncIteration:
                pass

        import asyncio
        asyncio.get_event_loop().run_until_complete(_run())

        # After the dependency generator is exhausted, TenantContext must be None
        assert TenantContext.get(None) is None, (
            "TenantContext must be cleared after set_tenant_context_dep completes"
        )

    def test_tenant_context_not_set_when_tenant_id_is_none(self):
        """When auth_context.tenant_id is None (local mode), TenantContext is untouched."""
        from skillmeat.api.middleware.tenant_context import set_tenant_context_dep

        # LOCAL_ADMIN_CONTEXT has tenant_id=None
        auth_ctx = LOCAL_ADMIN_CONTEXT

        sentinel = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

        async def _run():
            # Set a sentinel first to confirm it is not mutated
            with tenant_scope(sentinel):
                inside_scope: list[Optional[uuid.UUID]] = []
                gen = set_tenant_context_dep(auth_context=auth_ctx)
                await gen.__anext__()
                inside_scope.append(TenantContext.get(None))
                try:
                    await gen.__anext__()
                except StopAsyncIteration:
                    pass
                # After dependency completes, still inside tenant_scope
                inside_scope.append(TenantContext.get(None))
            return inside_scope

        import asyncio
        results = asyncio.get_event_loop().run_until_complete(_run())

        # Both observations should be the sentinel, not None or something else
        assert results == [sentinel, sentinel], (
            f"TenantContext should remain {sentinel} when tenant_id is None, got {results}"
        )

    def test_tenant_context_cleared_on_exception(self):
        """TenantContext is still cleared when the route handler raises an exception."""
        from skillmeat.api.middleware.tenant_context import set_tenant_context_dep

        tenant_id = uuid.uuid4()
        auth_ctx = AuthContext(
            user_id=uuid.uuid4(),
            tenant_id=tenant_id,
            roles=[Role.team_member.value],
            scopes=[Scope.artifact_read.value],
        )

        async def _run():
            gen = set_tenant_context_dep(auth_context=auth_ctx)
            await gen.__anext__()
            try:
                await gen.athrow(RuntimeError("simulated handler failure"))
            except (RuntimeError, StopAsyncIteration):
                pass

        import asyncio
        asyncio.get_event_loop().run_until_complete(_run())

        assert TenantContext.get(None) is None, (
            "TenantContext must be cleared even after a handler exception"
        )

    def test_no_tenant_context_leakage_between_requests(self):
        """Two consecutive dependency invocations do not share TenantContext state."""
        from skillmeat.api.middleware.tenant_context import set_tenant_context_dep

        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()

        auth_a = AuthContext(
            user_id=uuid.uuid4(),
            tenant_id=tenant_a,
            roles=[Role.team_member.value],
            scopes=[Scope.artifact_read.value],
        )
        auth_b = AuthContext(
            user_id=uuid.uuid4(),
            tenant_id=tenant_b,
            roles=[Role.team_member.value],
            scopes=[Scope.artifact_read.value],
        )

        observations: list[Optional[uuid.UUID]] = []

        async def _run():
            # Request A
            gen_a = set_tenant_context_dep(auth_context=auth_a)
            await gen_a.__anext__()
            observations.append(TenantContext.get(None))
            try:
                await gen_a.__anext__()
            except StopAsyncIteration:
                pass

            # After request A completes, TenantContext should be None
            observations.append(TenantContext.get(None))

            # Request B
            gen_b = set_tenant_context_dep(auth_context=auth_b)
            await gen_b.__anext__()
            observations.append(TenantContext.get(None))
            try:
                await gen_b.__anext__()
            except StopAsyncIteration:
                pass

            observations.append(TenantContext.get(None))

        import asyncio
        asyncio.get_event_loop().run_until_complete(_run())

        assert observations == [tenant_a, None, tenant_b, None], (
            f"Expected [tenant_a, None, tenant_b, None], got {observations}"
        )


# ---------------------------------------------------------------------------
# 5. DB session lifecycle
# ---------------------------------------------------------------------------


class TestDbSessionLifecycle:
    """Enterprise providers receive a session from get_db_session; sessions are
    distinct per request."""

    def test_two_enterprise_repos_from_same_session_share_session(self):
        """artifact and collection repos built from the same session share it."""
        state = _make_app_state(edition="enterprise")
        session = _make_session()

        artifact_repo = get_artifact_repository(state=state, session=session)
        collection_repo = get_collection_repository(state=state, session=session)

        assert artifact_repo.session is session
        assert collection_repo.session is session
        assert artifact_repo.session is collection_repo.session

    def test_distinct_sessions_produce_distinct_repo_instances(self):
        """Different sessions produce different repository instances."""
        state = _make_app_state(edition="enterprise")
        session_1 = _make_session()
        session_2 = _make_session()

        repo_1 = get_artifact_repository(state=state, session=session_1)
        repo_2 = get_artifact_repository(state=state, session=session_2)

        assert repo_1 is not repo_2
        assert repo_1.session is session_1
        assert repo_2.session is session_2


# ---------------------------------------------------------------------------
# 6. Route-level integration via minimal FastAPI app
# ---------------------------------------------------------------------------


def _make_enterprise_app(
    edition: str = "enterprise",
    auth_context: Optional[AuthContext] = None,
) -> FastAPI:
    """Build a minimal FastAPI app that exercises edition-aware DI providers.

    Two routes are registered:
    - GET /artifact-repo-type  — returns the class name of the injected repository
    - GET /collection-repo-type — returns the class name of the injected repository

    The ``AppState`` is patched directly onto ``app_state`` so no lifespan is needed.
    The session dependency is overridden with a MagicMock to avoid a real DB.
    """
    from skillmeat.api.dependencies import (
        get_app_state,
        get_artifact_repository,
        get_collection_repository,
    )
    from skillmeat.cache.session import get_db_session

    # Build and wire the state
    state = _make_app_state(edition=edition)

    # Auth provider — LocalAuthProvider for all DI integration tests
    provider = LocalAuthProvider()
    set_auth_provider(provider)

    # Use the supplied auth_context or default to LOCAL_ADMIN_CONTEXT
    effective_auth = auth_context or LOCAL_ADMIN_CONTEXT

    app = FastAPI()

    # Override the app_state dependency to return our controlled state
    app.dependency_overrides[get_app_state] = lambda: state
    # Override get_db_session to avoid needing a real SQLite/PG database
    mock_session = _make_session()
    app.dependency_overrides[get_db_session] = lambda: mock_session

    @app.get("/artifact-repo-type")
    async def artifact_repo_type(
        repo=Depends(get_artifact_repository),
    ) -> dict:
        return {"repo_class": type(repo).__name__}

    @app.get("/collection-repo-type")
    async def collection_repo_type(
        repo=Depends(get_collection_repository),
    ) -> dict:
        return {"repo_class": type(repo).__name__}

    return app


class TestRouteLevelIntegration:
    """Minimal app routes return correct repo types and do NOT return 503 for
    supported surfaces."""

    def test_enterprise_artifact_route_does_not_return_503(self):
        """Enterprise artifact route resolves without raising 503."""
        app = _make_enterprise_app(edition="enterprise")
        client = TestClient(app, raise_server_exceptions=True)

        response = client.get("/artifact-repo-type")

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )

    def test_enterprise_artifact_route_returns_enterprise_class(self):
        """Enterprise artifact route reports EnterpriseArtifactRepository."""
        app = _make_enterprise_app(edition="enterprise")
        client = TestClient(app, raise_server_exceptions=True)

        response = client.get("/artifact-repo-type")

        assert response.json()["repo_class"] == "EnterpriseArtifactRepository"

    def test_enterprise_collection_route_does_not_return_503(self):
        """Enterprise collection route resolves without raising 503."""
        app = _make_enterprise_app(edition="enterprise")
        client = TestClient(app, raise_server_exceptions=True)

        response = client.get("/collection-repo-type")

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )

    def test_enterprise_collection_route_returns_enterprise_class(self):
        """Enterprise collection route reports EnterpriseCollectionRepository."""
        app = _make_enterprise_app(edition="enterprise")
        client = TestClient(app, raise_server_exceptions=True)

        response = client.get("/collection-repo-type")

        assert response.json()["repo_class"] == "EnterpriseCollectionRepository"

    def test_local_artifact_route_returns_local_class(self):
        """Local artifact route reports LocalArtifactRepository (regression guard)."""
        app = _make_enterprise_app(edition="local")
        client = TestClient(app, raise_server_exceptions=True)

        response = client.get("/artifact-repo-type")

        assert response.status_code == 200
        assert response.json()["repo_class"] == "LocalArtifactRepository"

    def test_local_collection_route_returns_local_class(self):
        """Local collection route reports LocalCollectionRepository (regression guard)."""
        app = _make_enterprise_app(edition="local")
        client = TestClient(app, raise_server_exceptions=True)

        response = client.get("/collection-repo-type")

        assert response.status_code == 200
        assert response.json()["repo_class"] == "LocalCollectionRepository"

    def test_unsupported_edition_returns_503_from_route(self):
        """An unknown edition string causes the route to return 503 (not 500)."""
        app = _make_enterprise_app(edition="unknown_edition")
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/artifact-repo-type")

        assert response.status_code == 503

    def test_enterprise_artifact_repo_session_is_from_override(self):
        """The session injected into the enterprise repo is the override session."""
        from skillmeat.api.dependencies import (
            get_app_state,
            get_artifact_repository,
        )
        from skillmeat.cache.session import get_db_session

        state = _make_app_state(edition="enterprise")
        mock_session = _make_session()

        set_auth_provider(LocalAuthProvider())
        app = FastAPI()
        app.dependency_overrides[get_app_state] = lambda: state
        app.dependency_overrides[get_db_session] = lambda: mock_session

        captured_session_id: list[int] = []

        @app.get("/session-check")
        async def session_check(
            repo=Depends(get_artifact_repository),
        ) -> dict:
            captured_session_id.append(id(repo.session))
            return {"session_id": id(repo.session), "expected_id": id(mock_session)}

        client = TestClient(app, raise_server_exceptions=True)
        response = client.get("/session-check")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == data["expected_id"], (
            "repo.session must be the session returned by get_db_session override"
        )


# ---------------------------------------------------------------------------
# 7. Auth context reaches service layer (ENT2-004)
# ---------------------------------------------------------------------------


class TestAuthContextReachesServiceLayer:
    """Auth context injected by require_auth is visible to the route handler,
    proving the dependency chain wires correctly in enterprise mode."""

    def _make_auth_context_echo_app(self, edition: str = "enterprise") -> FastAPI:
        """Build an app with a route that echoes the authenticated user_id."""
        from skillmeat.api.dependencies import require_auth, get_app_state
        from skillmeat.cache.session import get_db_session

        state = _make_app_state(edition=edition)
        set_auth_provider(LocalAuthProvider())

        app = FastAPI()
        app.dependency_overrides[get_app_state] = lambda: state
        app.dependency_overrides[get_db_session] = lambda: _make_session()

        @app.get("/whoami")
        async def whoami(
            auth: AuthContext = Depends(require_auth()),
        ) -> dict:
            return {
                "user_id": str(auth.user_id),
                "tenant_id": str(auth.tenant_id) if auth.tenant_id else None,
                "roles": auth.roles,
            }

        return app

    def test_auth_context_returned_in_enterprise_mode(self):
        """require_auth returns a populated AuthContext in enterprise-mode app."""
        app = self._make_auth_context_echo_app(edition="enterprise")
        client = TestClient(app, raise_server_exceptions=True)

        response = client.get("/whoami")

        assert response.status_code == 200
        data = response.json()
        # LocalAuthProvider returns LOCAL_ADMIN_CONTEXT; user_id is stable
        assert "user_id" in data
        assert data["user_id"] is not None

    def test_auth_context_returned_in_local_mode(self):
        """require_auth returns a populated AuthContext in local-mode app."""
        app = self._make_auth_context_echo_app(edition="local")
        client = TestClient(app, raise_server_exceptions=True)

        response = client.get("/whoami")

        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data

    def test_both_editions_return_same_local_admin_user(self):
        """LocalAuthProvider returns LOCAL_ADMIN_CONTEXT in both editions."""
        app_ent = self._make_auth_context_echo_app(edition="enterprise")
        app_loc = self._make_auth_context_echo_app(edition="local")

        resp_ent = TestClient(app_ent, raise_server_exceptions=True).get("/whoami")
        resp_loc = TestClient(app_loc, raise_server_exceptions=True).get("/whoami")

        assert resp_ent.status_code == 200
        assert resp_loc.status_code == 200
        # Both use LocalAuthProvider → same user_id
        assert resp_ent.json()["user_id"] == resp_loc.json()["user_id"]

    def test_tenant_context_dep_clears_on_local_admin_request(self):
        """set_tenant_context_dep is a no-op when LOCAL_ADMIN_CONTEXT has no tenant_id."""
        from skillmeat.api.middleware.tenant_context import set_tenant_context_dep
        from skillmeat.api.dependencies import require_auth, get_app_state
        from skillmeat.cache.session import get_db_session

        state = _make_app_state(edition="enterprise")
        set_auth_provider(LocalAuthProvider())

        app = FastAPI()
        app.dependency_overrides[get_app_state] = lambda: state
        app.dependency_overrides[get_db_session] = lambda: _make_session()

        tenant_during_request: list[Optional[uuid.UUID]] = []

        @app.get("/tenant-check")
        async def tenant_check(
            _: None = Depends(set_tenant_context_dep),
        ) -> dict:
            tenant_during_request.append(TenantContext.get(None))
            return {"tenant": str(TenantContext.get(None))}

        client = TestClient(app, raise_server_exceptions=True)
        response = client.get("/tenant-check")

        assert response.status_code == 200
        # LOCAL_ADMIN_CONTEXT.tenant_id is None → TenantContext not set
        assert tenant_during_request == [None], (
            f"TenantContext should remain None for LOCAL_ADMIN_CONTEXT, got {tenant_during_request}"
        )
