"""Integration tests for the ownership resolution DI chain.

Tests the API-level wiring of ownership resolution:
  - DI chain: get_membership_repository → get_ownership_resolver → get_resolved_ownership
  - OwnerScopeFilter enum values and defaults
  - OwnerTargetInput schema validation and round-trips
  - Semantic contract invariants (local mode, enterprise mode, team membership)

All tests are mock-based — no database or filesystem I/O is required.

Design
------
For DI chain tests we spin up a minimal FastAPI app with test routes injecting
``ResolvedOwnershipDep``.  We override ``get_auth_context`` to inject a known
``AuthContext``, and we override ``get_membership_repository`` to inject a mock
``IMembershipRepository``.  This exercises the full DI graph (resolver +
resolved_ownership) without hitting the real DB layer.

For schema tests we directly instantiate / validate the Pydantic models.
For semantic tests we call ``OwnershipResolver.resolve()`` directly with
controlled mock repos, matching the pattern established in
``tests/core/auth/test_ownership_resolver.py``.
"""

from __future__ import annotations

import uuid
from typing import Annotated
from unittest.mock import MagicMock

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from skillmeat.api.dependencies import (
    get_auth_context,
    get_membership_repository,
    get_ownership_resolver,
    get_resolved_ownership,
    ResolvedOwnershipDep,
    set_auth_provider,
)
from skillmeat.api.schemas.auth import (
    AuthContext,
    LOCAL_ADMIN_CONTEXT,
    OwnerScopeFilter,
    OwnerTargetInput,
    Role,
    Scope,
)
from skillmeat.cache.auth_types import OwnerType
from skillmeat.core.interfaces.repositories import IMembershipRepository
from skillmeat.core.ownership import OwnerTarget, ResolvedOwnership
from skillmeat.core.services.ownership_resolver import OwnershipResolver


# =============================================================================
# Helpers
# =============================================================================


def _make_repo(
    *,
    team_ids: list[uuid.UUID] | None = None,
    roles: dict[uuid.UUID, str] | None = None,
) -> MagicMock:
    """Return a mock IMembershipRepository."""
    repo = MagicMock(spec=IMembershipRepository)
    repo.get_team_ids_for_user.return_value = team_ids or []
    if roles:
        repo.get_team_role.side_effect = lambda _user_id, team_id: roles.get(team_id)
    else:
        repo.get_team_role.return_value = None
    return repo


def _make_auth(
    *,
    user_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID | None = None,
    roles: list[str] | None = None,
) -> AuthContext:
    """Return an AuthContext with sensible defaults."""
    return AuthContext(
        user_id=user_id or uuid.uuid4(),
        tenant_id=tenant_id,
        roles=roles or [],
    )


def _make_test_app(auth_ctx: AuthContext, repo: MagicMock) -> FastAPI:
    """Return a minimal FastAPI app with one ownership endpoint.

    The app overrides:
    - ``get_auth_context`` → returns the given ``auth_ctx``
    - ``get_membership_repository`` → returns the given mock ``repo``

    This exercises the ``get_ownership_resolver`` → ``get_resolved_ownership``
    chain in full.
    """
    from skillmeat.api.auth.local_provider import LocalAuthProvider

    mini_app = FastAPI()

    # Register a no-op auth provider so ``require_auth`` doesn't 503.
    set_auth_provider(LocalAuthProvider())

    @mini_app.get("/test-ownership")
    async def _endpoint(ownership: ResolvedOwnershipDep):  # type: ignore[valid-type]
        return {
            "default_owner_type": ownership.default_owner.owner_type,
            "default_owner_id": ownership.default_owner.owner_id,
            "readable_count": len(ownership.readable_scopes),
            "writable_count": len(ownership.writable_scopes),
            "has_enterprise_scope": ownership.has_enterprise_scope,
            "tenant_id": str(ownership.tenant_id) if ownership.tenant_id else None,
            "readable_types": [s.owner_type for s in ownership.readable_scopes],
        }

    # Override auth context so no real token validation is required.
    mini_app.dependency_overrides[get_auth_context] = lambda: auth_ctx

    # Override membership repository so no real DB is touched.
    mini_app.dependency_overrides[get_membership_repository] = lambda: repo

    return mini_app


# =============================================================================
# 1. DI Chain Tests
# =============================================================================


class TestDiChainMembershipRepository:
    """get_membership_repository selects the correct implementation."""

    def test_no_tenant_returns_local_membership_repository(self):
        """Without tenant_id get_membership_repository returns LocalMembershipRepository.

        Calls the dependency function directly (avoids wiring a real session).
        """
        from skillmeat.api.dependencies import get_membership_repository as _gm_repo
        from skillmeat.core.repositories.local_membership import LocalMembershipRepository

        auth_ctx_no_tenant = _make_auth(tenant_id=None)

        class _FakeRequest:
            class state:
                pass

        req = _FakeRequest()
        req.state.auth_context = auth_ctx_no_tenant  # type: ignore[attr-defined]
        fake_session = MagicMock()

        result = _gm_repo(req, fake_session)  # type: ignore[arg-type]
        assert isinstance(result, LocalMembershipRepository)

    def test_with_tenant_would_use_enterprise_branch(self):
        """When tenant_id is set, the dependency returns EnterpriseMembershipRepository.

        We verify the routing logic of get_membership_repository directly rather
        than through a full HTTP cycle, because wiring a real SQLAlchemy session
        is out of scope for these mock-based tests.
        """
        from skillmeat.api.dependencies import get_membership_repository as _gm_repo
        from skillmeat.core.repositories.enterprise_membership import (
            EnterpriseMembershipRepository,
        )

        tenant_id = uuid.uuid4()
        auth_ctx_with_tenant = _make_auth(tenant_id=tenant_id)

        # Build a minimal Request-like object so we can call the dep directly.
        class _FakeRequest:
            class state:
                pass

        req = _FakeRequest()
        req.state.auth_context = auth_ctx_with_tenant  # type: ignore[attr-defined]
        fake_session = MagicMock()

        result = _gm_repo(req, fake_session)  # type: ignore[arg-type]
        assert isinstance(result, EnterpriseMembershipRepository)

    def test_get_ownership_resolver_wraps_repo(self):
        """get_ownership_resolver returns an OwnershipResolver wrapping the given repo."""
        repo = _make_repo()
        resolver = get_ownership_resolver(repo)
        assert isinstance(resolver, OwnershipResolver)

    def test_get_resolved_ownership_calls_resolver(self):
        """get_resolved_ownership delegates to OwnershipResolver.resolve()."""
        user_id = uuid.uuid4()
        auth_ctx = _make_auth(user_id=user_id)
        repo = _make_repo()
        resolver = OwnershipResolver(repo)

        import asyncio

        ownership = asyncio.get_event_loop().run_until_complete(
            get_resolved_ownership(auth_ctx, resolver)
        )

        assert isinstance(ownership, ResolvedOwnership)
        assert ownership.default_owner.owner_id == str(user_id)

    def test_di_chain_end_to_end_via_test_route(self):
        """Full DI chain resolves correctly through a real test route."""
        user_id = uuid.uuid4()
        auth_ctx = _make_auth(user_id=user_id)
        repo = _make_repo()  # no teams

        mini_app = _make_test_app(auth_ctx, repo)

        with TestClient(mini_app) as client:
            resp = client.get("/test-ownership")

        assert resp.status_code == 200
        data = resp.json()
        assert data["default_owner_id"] == str(user_id)
        assert data["default_owner_type"] == OwnerType.user.value
        assert data["readable_count"] == 1
        assert data["writable_count"] == 1
        assert data["has_enterprise_scope"] is False
        assert data["tenant_id"] is None


# =============================================================================
# 2. OwnerScopeFilter Schema Tests
# =============================================================================


class TestOwnerScopeFilter:
    """OwnerScopeFilter enum values and semantics."""

    def test_all_expected_values_exist(self):
        """The enum must expose user / team / enterprise / all values."""
        values = {m.value for m in OwnerScopeFilter}
        assert values == {"user", "team", "enterprise", "all"}

    def test_default_value_is_all(self):
        """The 'all' member is the expected default for list endpoints."""
        assert OwnerScopeFilter.all.value == "all"

    def test_user_value(self):
        assert OwnerScopeFilter.user.value == "user"

    def test_team_value(self):
        assert OwnerScopeFilter.team.value == "team"

    def test_enterprise_value(self):
        assert OwnerScopeFilter.enterprise.value == "enterprise"

    def test_is_string_enum(self):
        """OwnerScopeFilter inherits from str so it can be used directly in URLs."""
        assert isinstance(OwnerScopeFilter.all, str)

    def test_invalid_value_raises_value_error(self):
        """Constructing the enum with an unknown value raises ValueError."""
        with pytest.raises(ValueError):
            OwnerScopeFilter("unknown_scope")

    def test_enum_member_count(self):
        """There are exactly four scope filter variants."""
        assert len(list(OwnerScopeFilter)) == 4


# =============================================================================
# 3. OwnerTargetInput Schema Tests
# =============================================================================


class TestOwnerTargetInput:
    """OwnerTargetInput Pydantic model validation and defaults."""

    def test_default_construction_gives_user_type(self):
        """OwnerTargetInput() defaults to user ownership."""
        target = OwnerTargetInput()
        assert target.owner_type == OwnerType.user.value

    def test_default_owner_id_is_none(self):
        """owner_id is None by default (auto-filled by service layer for user type)."""
        target = OwnerTargetInput()
        assert target.owner_id is None

    def test_explicit_user_type(self):
        """Explicit user type is accepted."""
        target = OwnerTargetInput(owner_type=OwnerType.user, owner_id="uid-abc")
        assert target.owner_type == OwnerType.user.value
        assert target.owner_id == "uid-abc"

    def test_team_ownership_with_owner_id(self):
        """Team ownership requires owner_id; explicit construction succeeds."""
        team_id = str(uuid.uuid4())
        target = OwnerTargetInput(owner_type=OwnerType.team, owner_id=team_id)
        assert target.owner_type == OwnerType.team.value
        assert target.owner_id == team_id

    def test_enterprise_ownership_with_owner_id(self):
        """Enterprise ownership requires owner_id; explicit construction succeeds."""
        tenant_id = str(uuid.uuid4())
        target = OwnerTargetInput(owner_type=OwnerType.enterprise, owner_id=tenant_id)
        assert target.owner_type == OwnerType.enterprise.value
        assert target.owner_id == tenant_id

    def test_model_dump_round_trip(self):
        """model_dump / model_validate round-trip preserves all fields."""
        team_id = str(uuid.uuid4())
        original = OwnerTargetInput(owner_type=OwnerType.team, owner_id=team_id)
        dumped = original.model_dump()
        restored = OwnerTargetInput.model_validate(dumped)
        assert restored.owner_type == original.owner_type
        assert restored.owner_id == original.owner_id

    def test_model_dump_uses_enum_values(self):
        """use_enum_values=True means model_dump returns plain strings."""
        target = OwnerTargetInput(owner_type=OwnerType.user)
        dumped = target.model_dump()
        # With use_enum_values the value stored is the primitive string.
        assert isinstance(dumped["owner_type"], str)

    def test_model_validate_from_dict(self):
        """OwnerTargetInput can be constructed from a plain dict."""
        data = {"owner_type": "team", "owner_id": "team-123"}
        target = OwnerTargetInput.model_validate(data)
        assert target.owner_type == "team"
        assert target.owner_id == "team-123"

    def test_none_owner_id_accepted(self):
        """None owner_id is explicitly allowed (user type auto-fill contract)."""
        target = OwnerTargetInput(owner_type=OwnerType.user, owner_id=None)
        assert target.owner_id is None

    def test_string_owner_type_accepted(self):
        """Plain string values for owner_type are accepted (Pydantic coercion)."""
        target = OwnerTargetInput(owner_type="enterprise", owner_id="t-1")
        assert target.owner_type == "enterprise"


# =============================================================================
# 4. Semantic Contract Tests
# =============================================================================


class TestLocalModeSemantics:
    """Local mode (no tenant_id) ownership resolution invariants."""

    def test_local_mode_default_is_user_owned(self):
        """Local mode resolves to user-owned default regardless of roles."""
        user_id = uuid.uuid4()
        repo = _make_repo()
        ctx = _make_auth(user_id=user_id)

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert ownership.default_owner.owner_type == OwnerType.user
        assert ownership.default_owner.owner_id == str(user_id)

    def test_local_mode_no_enterprise_in_readable_scopes(self):
        """Enterprise scope must NEVER appear in local mode."""
        repo = _make_repo()
        ctx = _make_auth()

        ownership = OwnershipResolver(repo).resolve(ctx)

        enterprise_scopes = [
            s for s in ownership.readable_scopes if s.owner_type == OwnerType.enterprise
        ]
        assert enterprise_scopes == []

    def test_local_mode_has_enterprise_scope_is_false(self):
        """has_enterprise_scope is always False in local mode."""
        repo = _make_repo()
        ctx = _make_auth()

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert ownership.has_enterprise_scope is False

    def test_local_admin_context_stays_user_owned(self):
        """LOCAL_ADMIN_CONTEXT (system_admin, no tenant) resolves to user-owned only."""
        repo = _make_repo()

        ownership = OwnershipResolver(repo).resolve(LOCAL_ADMIN_CONTEXT)

        assert ownership.default_owner.owner_type == OwnerType.user
        assert ownership.has_enterprise_scope is False
        enterprise_scopes = [
            s for s in ownership.readable_scopes if s.owner_type == OwnerType.enterprise
        ]
        assert enterprise_scopes == []

    def test_local_admin_context_tenant_id_is_none(self):
        """LOCAL_ADMIN_CONTEXT has no tenant — ownership.tenant_id must be None."""
        repo = _make_repo()

        ownership = OwnershipResolver(repo).resolve(LOCAL_ADMIN_CONTEXT)

        assert ownership.tenant_id is None

    def test_local_mode_via_di_chain(self):
        """Full DI chain in local mode returns user-owned, no enterprise scope."""
        user_id = uuid.uuid4()
        auth_ctx = _make_auth(user_id=user_id)
        repo = _make_repo()

        mini_app = _make_test_app(auth_ctx, repo)

        with TestClient(mini_app) as client:
            resp = client.get("/test-ownership")

        assert resp.status_code == 200
        data = resp.json()
        assert data["has_enterprise_scope"] is False
        assert data["tenant_id"] is None
        assert OwnerType.enterprise.value not in data["readable_types"]


class TestEnterpriseModeSemantics:
    """Enterprise mode (tenant_id present) ownership resolution invariants."""

    def test_enterprise_adds_enterprise_to_readable_scopes(self):
        """Any user with a tenant_id sees enterprise in readable_scopes."""
        tenant_id = uuid.uuid4()
        repo = _make_repo()
        ctx = _make_auth(tenant_id=tenant_id, roles=[Role.viewer.value])

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert ownership.can_read_from(OwnerType.enterprise, str(tenant_id)) is True

    def test_enterprise_non_admin_excludes_enterprise_from_writable_scopes(self):
        """Non-admin enterprise user cannot write to the enterprise scope."""
        tenant_id = uuid.uuid4()
        repo = _make_repo()
        ctx = _make_auth(tenant_id=tenant_id, roles=[Role.team_member.value])

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert ownership.can_write_to(OwnerType.enterprise, str(tenant_id)) is False

    def test_enterprise_admin_gets_enterprise_in_writable_scopes(self):
        """system_admin with tenant_id may write to the enterprise scope."""
        tenant_id = uuid.uuid4()
        repo = _make_repo()
        ctx = _make_auth(tenant_id=tenant_id, roles=[Role.system_admin.value])

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert ownership.can_write_to(OwnerType.enterprise, str(tenant_id)) is True

    def test_enterprise_admin_has_enterprise_scope_flag(self):
        """system_admin in enterprise mode sets has_enterprise_scope=True."""
        tenant_id = uuid.uuid4()
        repo = _make_repo()
        ctx = _make_auth(tenant_id=tenant_id, roles=[Role.system_admin.value])

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert ownership.has_enterprise_scope is True

    def test_enterprise_non_admin_has_enterprise_scope_false(self):
        """Non-admin enterprise user does not set has_enterprise_scope=True."""
        tenant_id = uuid.uuid4()
        repo = _make_repo()
        ctx = _make_auth(tenant_id=tenant_id, roles=[Role.team_member.value])

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert ownership.has_enterprise_scope is False

    def test_enterprise_tenant_id_propagated(self):
        """ownership.tenant_id mirrors the auth context tenant_id."""
        tenant_id = uuid.uuid4()
        repo = _make_repo()
        ctx = _make_auth(tenant_id=tenant_id, roles=[])

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert ownership.tenant_id == tenant_id

    def test_enterprise_default_owner_is_still_user(self):
        """Even in enterprise mode the default_owner is the user, not the tenant."""
        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        repo = _make_repo()
        ctx = _make_auth(user_id=user_id, tenant_id=tenant_id, roles=[Role.system_admin.value])

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert ownership.default_owner.owner_type == OwnerType.user
        assert ownership.default_owner.owner_id == str(user_id)

    def test_enterprise_mode_via_di_chain(self):
        """DI chain in enterprise mode exposes enterprise in readable_types."""
        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        auth_ctx = _make_auth(
            user_id=user_id,
            tenant_id=tenant_id,
            roles=[Role.system_admin.value],
        )
        repo = _make_repo()

        mini_app = _make_test_app(auth_ctx, repo)

        with TestClient(mini_app) as client:
            resp = client.get("/test-ownership")

        assert resp.status_code == 200
        data = resp.json()
        assert data["has_enterprise_scope"] is True
        assert data["tenant_id"] == str(tenant_id)
        assert OwnerType.enterprise.value in data["readable_types"]


class TestTeamMembershipSemantics:
    """Team membership expands readable scopes without changing default owner."""

    def test_team_membership_expands_readable_scopes(self):
        """Team membership adds team targets to readable_scopes."""
        user_id = uuid.uuid4()
        team_id = uuid.uuid4()
        repo = _make_repo(
            team_ids=[team_id],
            roles={team_id: "team_member"},
        )
        ctx = _make_auth(user_id=user_id)

        ownership = OwnershipResolver(repo).resolve(ctx)

        readable_types = {s.owner_type for s in ownership.readable_scopes}
        assert OwnerType.team in readable_types
        assert ownership.can_read_from(OwnerType.team, str(team_id)) is True

    def test_team_is_not_default_owner(self):
        """Team membership does not change the default_owner to team."""
        user_id = uuid.uuid4()
        team_id = uuid.uuid4()
        repo = _make_repo(
            team_ids=[team_id],
            roles={team_id: "team_member"},
        )
        ctx = _make_auth(user_id=user_id)

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert ownership.default_owner.owner_type == OwnerType.user
        assert ownership.default_owner.owner_id == str(user_id)

    def test_viewer_role_team_readable_not_writable(self):
        """A viewer-role team membership is readable but not writable."""
        user_id = uuid.uuid4()
        team_id = uuid.uuid4()
        repo = _make_repo(
            team_ids=[team_id],
            roles={team_id: "viewer"},
        )
        ctx = _make_auth(user_id=user_id)

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert ownership.can_read_from(OwnerType.team, str(team_id)) is True
        assert ownership.can_write_to(OwnerType.team, str(team_id)) is False

    def test_team_member_role_is_writable(self):
        """A team_member-role membership grants write access."""
        user_id = uuid.uuid4()
        team_id = uuid.uuid4()
        repo = _make_repo(
            team_ids=[team_id],
            roles={team_id: "team_member"},
        )
        ctx = _make_auth(user_id=user_id)

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert ownership.can_write_to(OwnerType.team, str(team_id)) is True

    def test_multi_team_user_sees_union_of_readable_scopes(self):
        """A user belonging to two teams sees all teams in readable_scopes."""
        user_id = uuid.uuid4()
        team_a = uuid.uuid4()
        team_b = uuid.uuid4()
        repo = _make_repo(
            team_ids=[team_a, team_b],
            roles={team_a: "team_member", team_b: "viewer"},
        )
        ctx = _make_auth(user_id=user_id)

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert ownership.can_read_from(OwnerType.team, str(team_a)) is True
        assert ownership.can_read_from(OwnerType.team, str(team_b)) is True
        # user + 2 teams = 3 readable scopes
        assert len(ownership.readable_scopes) == 3

    def test_multi_team_writable_respects_roles(self):
        """Only teams with write-capable roles appear in writable_scopes."""
        user_id = uuid.uuid4()
        team_a = uuid.uuid4()
        team_b = uuid.uuid4()
        repo = _make_repo(
            team_ids=[team_a, team_b],
            roles={team_a: "team_member", team_b: "viewer"},
        )
        ctx = _make_auth(user_id=user_id)

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert ownership.can_write_to(OwnerType.team, str(team_a)) is True
        assert ownership.can_write_to(OwnerType.team, str(team_b)) is False

    def test_team_membership_does_not_add_enterprise_scope(self):
        """Team membership without a tenant does not produce enterprise access."""
        user_id = uuid.uuid4()
        team_id = uuid.uuid4()
        repo = _make_repo(
            team_ids=[team_id],
            roles={team_id: "team_member"},
        )
        ctx = _make_auth(user_id=user_id)  # no tenant_id

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert ownership.has_enterprise_scope is False
        enterprise_scopes = [
            s for s in ownership.readable_scopes if s.owner_type == OwnerType.enterprise
        ]
        assert enterprise_scopes == []

    def test_team_membership_via_di_chain(self):
        """DI chain with team membership exposes team in readable_types."""
        user_id = uuid.uuid4()
        team_id = uuid.uuid4()
        auth_ctx = _make_auth(user_id=user_id)
        repo = _make_repo(
            team_ids=[team_id],
            roles={team_id: "team_member"},
        )

        mini_app = _make_test_app(auth_ctx, repo)

        with TestClient(mini_app) as client:
            resp = client.get("/test-ownership")

        assert resp.status_code == 200
        data = resp.json()
        assert OwnerType.team.value in data["readable_types"]
        assert data["readable_count"] == 2  # user + team


class TestOwnerTargetInputMutationSemantics:
    """OwnerTargetInput defaults and explicit selection semantics for writes."""

    def test_omitted_owner_target_defaults_to_user_owned(self):
        """OwnerTargetInput() with no args signals user ownership (service must auto-fill)."""
        target = OwnerTargetInput()
        assert target.owner_type == OwnerType.user.value
        assert target.owner_id is None

    def test_explicit_team_selection_retains_owner_id(self):
        """Explicit team selection preserves the supplied owner_id."""
        team_id = str(uuid.uuid4())
        target = OwnerTargetInput(owner_type=OwnerType.team, owner_id=team_id)
        assert target.owner_type == OwnerType.team.value
        assert target.owner_id == team_id

    def test_explicit_enterprise_selection_retains_owner_id(self):
        """Explicit enterprise selection preserves the supplied owner_id."""
        tenant_id = str(uuid.uuid4())
        target = OwnerTargetInput(owner_type=OwnerType.enterprise, owner_id=tenant_id)
        assert target.owner_type == OwnerType.enterprise.value
        assert target.owner_id == tenant_id

    def test_team_target_validate_against_writable_scopes_pass(self):
        """A team OwnerTarget in writable_scopes passes validate_write_target."""
        from skillmeat.core.repositories.filters import validate_write_target

        team_id = str(uuid.uuid4())
        team_target = OwnerTarget(owner_type=OwnerType.team, owner_id=team_id)
        ownership = ResolvedOwnership(
            default_owner=OwnerTarget(OwnerType.user, "user-1"),
            readable_scopes=[team_target],
            writable_scopes=[team_target],
        )
        assert validate_write_target(team_target, ownership) is True

    def test_team_target_validate_against_writable_scopes_fail(self):
        """A team OwnerTarget NOT in writable_scopes fails validate_write_target."""
        from skillmeat.core.repositories.filters import validate_write_target

        team_id = str(uuid.uuid4())
        other_team_id = str(uuid.uuid4())
        team_target = OwnerTarget(owner_type=OwnerType.team, owner_id=team_id)
        other_target = OwnerTarget(owner_type=OwnerType.team, owner_id=other_team_id)
        ownership = ResolvedOwnership(
            default_owner=OwnerTarget(OwnerType.user, "user-1"),
            readable_scopes=[team_target],
            writable_scopes=[team_target],
        )
        # other_team is not in writable_scopes
        assert validate_write_target(other_target, ownership) is False

    def test_enterprise_target_only_valid_for_admin(self):
        """Enterprise write target passes only when writable_scopes include enterprise."""
        from skillmeat.core.repositories.filters import validate_write_target

        tenant_id = str(uuid.uuid4())
        user_id = uuid.uuid4()
        user_target = OwnerTarget(OwnerType.user, str(user_id))
        ent_target = OwnerTarget(OwnerType.enterprise, tenant_id)

        # Non-admin: enterprise not in writable_scopes
        non_admin_ownership = ResolvedOwnership(
            default_owner=user_target,
            readable_scopes=[user_target, ent_target],
            writable_scopes=[user_target],  # enterprise excluded
        )
        assert validate_write_target(ent_target, non_admin_ownership) is False

        # Admin: enterprise in writable_scopes
        admin_ownership = ResolvedOwnership(
            default_owner=user_target,
            readable_scopes=[user_target, ent_target],
            writable_scopes=[user_target, ent_target],
        )
        assert validate_write_target(ent_target, admin_ownership) is True
