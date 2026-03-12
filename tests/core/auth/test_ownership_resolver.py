"""Tests for OwnerTarget, ResolvedOwnership DTOs and OwnershipResolver service.

Covers:
  - OwnerTarget immutability (frozen dataclass), equality, hashing, and str owner_id
  - ResolvedOwnership default values and can_read_from / can_write_to helpers
  - OwnershipResolver.resolve() for all meaningful AuthContext configurations:
      * Local mode (no tenant, no teams)
      * User with team memberships (mix of writable and read-only team roles)
      * Enterprise admin (system_admin with tenant_id → enterprise scope in both read+write)
      * Enterprise non-admin (tenant_id present, no admin role → enterprise in read only)
      * LOCAL_ADMIN_CONTEXT (system_admin, no tenant → user-owned only, no enterprise scope)

All tests use MagicMock(spec=IMembershipRepository) — no database or filesystem I/O.
"""

from __future__ import annotations

import uuid
from dataclasses import FrozenInstanceError
from unittest.mock import MagicMock

import pytest

from skillmeat.api.schemas.auth import AuthContext, LOCAL_ADMIN_CONTEXT, Role
from skillmeat.cache.auth_types import OwnerType
from skillmeat.core.interfaces.repositories import IMembershipRepository
from skillmeat.core.ownership import OwnerTarget, ResolvedOwnership
from skillmeat.core.services.ownership_resolver import OwnershipResolver


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_repo(
    *,
    team_ids: list[uuid.UUID] | None = None,
    roles: dict[uuid.UUID, str] | None = None,
) -> MagicMock:
    """Return a mock IMembershipRepository.

    Args:
        team_ids: Team UUIDs returned by get_team_ids_for_user.
        roles:    Mapping of team_id → role string returned by get_team_role.
    """
    repo = MagicMock(spec=IMembershipRepository)
    repo.get_team_ids_for_user.return_value = team_ids or []
    if roles:
        repo.get_team_role.side_effect = lambda _user_id, team_id: roles.get(team_id)
    else:
        repo.get_team_role.return_value = None
    return repo


def _make_auth(
    *,
    tenant_id: uuid.UUID | None = None,
    roles: list[str] | None = None,
    user_id: uuid.UUID | None = None,
) -> AuthContext:
    """Return an AuthContext with sensible defaults."""
    return AuthContext(
        user_id=user_id or uuid.uuid4(),
        tenant_id=tenant_id,
        roles=roles or [],
    )


# =============================================================================
# OwnerTarget
# =============================================================================


class TestOwnerTarget:
    """Tests for the OwnerTarget frozen dataclass."""

    def test_frozen_rejects_attribute_mutation(self):
        """OwnerTarget is immutable; setting an attribute raises FrozenInstanceError."""
        target = OwnerTarget(owner_type=OwnerType.user, owner_id="abc")
        with pytest.raises(FrozenInstanceError):
            target.owner_id = "other"  # type: ignore[misc]

    def test_frozen_rejects_type_mutation(self):
        """OwnerType attribute is also immutable on a frozen instance."""
        target = OwnerTarget(owner_type=OwnerType.team, owner_id="t1")
        with pytest.raises(FrozenInstanceError):
            target.owner_type = OwnerType.user  # type: ignore[misc]

    def test_equality_same_values(self):
        """Two OwnerTargets with identical fields are equal."""
        a = OwnerTarget(owner_type=OwnerType.user, owner_id="uid-1")
        b = OwnerTarget(owner_type=OwnerType.user, owner_id="uid-1")
        assert a == b

    def test_equality_different_owner_id(self):
        """Different owner_id → not equal."""
        a = OwnerTarget(owner_type=OwnerType.user, owner_id="uid-1")
        b = OwnerTarget(owner_type=OwnerType.user, owner_id="uid-2")
        assert a != b

    def test_equality_different_owner_type(self):
        """Different owner_type → not equal even with same owner_id."""
        a = OwnerTarget(owner_type=OwnerType.user, owner_id="same")
        b = OwnerTarget(owner_type=OwnerType.team, owner_id="same")
        assert a != b

    def test_hashable_and_usable_in_set(self):
        """Frozen dataclasses must be hashable so OwnerTarget can live in sets/dicts."""
        a = OwnerTarget(owner_type=OwnerType.user, owner_id="uid-1")
        b = OwnerTarget(owner_type=OwnerType.user, owner_id="uid-1")
        c = OwnerTarget(owner_type=OwnerType.team, owner_id="uid-1")
        s = {a, b, c}
        assert len(s) == 2  # a and b are the same

    def test_owner_id_is_str(self):
        """owner_id is stored as a plain string (no UUID coercion)."""
        raw = str(uuid.uuid4())
        target = OwnerTarget(owner_type=OwnerType.enterprise, owner_id=raw)
        assert isinstance(target.owner_id, str)
        assert target.owner_id == raw

    def test_owner_id_accepts_non_uuid_string(self):
        """owner_id is a plain string — any string value is valid (no UUID parsing)."""
        target = OwnerTarget(owner_type=OwnerType.user, owner_id="local_admin")
        assert target.owner_id == "local_admin"


# =============================================================================
# ResolvedOwnership
# =============================================================================


class TestResolvedOwnership:
    """Tests for the ResolvedOwnership frozen dataclass and its helper methods."""

    def _make_ownership(self) -> ResolvedOwnership:
        user = OwnerTarget(OwnerType.user, "user-abc")
        team = OwnerTarget(OwnerType.team, "team-xyz")
        enterprise = OwnerTarget(OwnerType.enterprise, "tenant-1")
        return ResolvedOwnership(
            default_owner=user,
            readable_scopes=[user, team, enterprise],
            writable_scopes=[user, team],
        )

    # ------------------------------------------------------------------
    # Default values
    # ------------------------------------------------------------------

    def test_default_readable_scopes_is_empty_list(self):
        """readable_scopes defaults to an empty list."""
        user = OwnerTarget(OwnerType.user, "u1")
        ownership = ResolvedOwnership(default_owner=user)
        assert ownership.readable_scopes == []

    def test_default_writable_scopes_is_empty_list(self):
        """writable_scopes defaults to an empty list."""
        user = OwnerTarget(OwnerType.user, "u1")
        ownership = ResolvedOwnership(default_owner=user)
        assert ownership.writable_scopes == []

    def test_default_has_enterprise_scope_is_false(self):
        """has_enterprise_scope defaults to False."""
        user = OwnerTarget(OwnerType.user, "u1")
        ownership = ResolvedOwnership(default_owner=user)
        assert ownership.has_enterprise_scope is False

    def test_default_tenant_id_is_none(self):
        """tenant_id defaults to None."""
        user = OwnerTarget(OwnerType.user, "u1")
        ownership = ResolvedOwnership(default_owner=user)
        assert ownership.tenant_id is None

    # ------------------------------------------------------------------
    # can_read_from
    # ------------------------------------------------------------------

    def test_can_read_from_user_in_readable(self):
        """can_read_from returns True for a user scope that is in readable_scopes."""
        ownership = self._make_ownership()
        assert ownership.can_read_from(OwnerType.user, "user-abc") is True

    def test_can_read_from_team_in_readable(self):
        """can_read_from returns True for a team scope that is in readable_scopes."""
        ownership = self._make_ownership()
        assert ownership.can_read_from(OwnerType.team, "team-xyz") is True

    def test_can_read_from_enterprise_in_readable(self):
        """can_read_from returns True for an enterprise scope in readable_scopes."""
        ownership = self._make_ownership()
        assert ownership.can_read_from(OwnerType.enterprise, "tenant-1") is True

    def test_can_read_from_unknown_owner_id_returns_false(self):
        """can_read_from returns False when owner_id is not in readable_scopes."""
        ownership = self._make_ownership()
        assert ownership.can_read_from(OwnerType.user, "other-user") is False

    def test_can_read_from_wrong_type_returns_false(self):
        """can_read_from returns False when owner_type doesn't match."""
        ownership = self._make_ownership()
        # "team-xyz" is in readable as OwnerType.team, not OwnerType.user
        assert ownership.can_read_from(OwnerType.user, "team-xyz") is False

    # ------------------------------------------------------------------
    # can_write_to
    # ------------------------------------------------------------------

    def test_can_write_to_user_in_writable(self):
        """can_write_to returns True for a scope that is in writable_scopes."""
        ownership = self._make_ownership()
        assert ownership.can_write_to(OwnerType.user, "user-abc") is True

    def test_can_write_to_team_in_writable(self):
        """can_write_to returns True for a team scope in writable_scopes."""
        ownership = self._make_ownership()
        assert ownership.can_write_to(OwnerType.team, "team-xyz") is True

    def test_can_write_to_enterprise_not_in_writable(self):
        """can_write_to returns False for a scope that is only in readable_scopes."""
        ownership = self._make_ownership()
        # enterprise is readable but not writable in _make_ownership()
        assert ownership.can_write_to(OwnerType.enterprise, "tenant-1") is False

    def test_can_write_to_unknown_returns_false(self):
        """can_write_to returns False for unknown owner."""
        ownership = self._make_ownership()
        assert ownership.can_write_to(OwnerType.team, "team-unknown") is False


# =============================================================================
# OwnershipResolver
# =============================================================================


class TestOwnershipResolverLocalMode:
    """Local mode: no tenant, no team memberships."""

    def test_default_owner_is_user(self):
        """default_owner.owner_type is user and owner_id matches auth user_id."""
        user_id = uuid.uuid4()
        repo = _make_repo()
        ctx = _make_auth(user_id=user_id)

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert ownership.default_owner.owner_type == OwnerType.user
        assert ownership.default_owner.owner_id == str(user_id)

    def test_readable_contains_only_user(self):
        """Without teams or tenant, only the user scope is readable."""
        user_id = uuid.uuid4()
        repo = _make_repo()
        ctx = _make_auth(user_id=user_id)

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert len(ownership.readable_scopes) == 1
        assert ownership.readable_scopes[0] == OwnerTarget(OwnerType.user, str(user_id))

    def test_writable_contains_only_user(self):
        """Without teams or tenant, only the user scope is writable."""
        user_id = uuid.uuid4()
        repo = _make_repo()
        ctx = _make_auth(user_id=user_id)

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert len(ownership.writable_scopes) == 1
        assert ownership.writable_scopes[0] == OwnerTarget(OwnerType.user, str(user_id))

    def test_has_enterprise_scope_is_false(self):
        """Local mode never sets has_enterprise_scope."""
        repo = _make_repo()
        ctx = _make_auth()

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert ownership.has_enterprise_scope is False

    def test_tenant_id_is_none(self):
        """ResolvedOwnership.tenant_id mirrors AuthContext.tenant_id (None here)."""
        repo = _make_repo()
        ctx = _make_auth()

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert ownership.tenant_id is None

    def test_membership_repo_is_called_with_user_id(self):
        """get_team_ids_for_user is always called, even in local mode."""
        user_id = uuid.uuid4()
        repo = _make_repo()
        ctx = _make_auth(user_id=user_id)

        OwnershipResolver(repo).resolve(ctx)

        repo.get_team_ids_for_user.assert_called_once_with(user_id)


class TestOwnershipResolverWithTeams:
    """User belongs to two teams with different roles."""

    def _setup(self) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, MagicMock, AuthContext]:
        user_id = uuid.uuid4()
        team1_id = uuid.uuid4()
        team2_id = uuid.uuid4()
        repo = _make_repo(
            team_ids=[team1_id, team2_id],
            roles={team1_id: "team_member", team2_id: "viewer"},
        )
        ctx = _make_auth(user_id=user_id)
        return user_id, team1_id, team2_id, repo, ctx

    def test_readable_includes_user_and_both_teams(self):
        """readable_scopes includes the user target plus both team targets."""
        user_id, team1_id, team2_id, repo, ctx = self._setup()

        ownership = OwnershipResolver(repo).resolve(ctx)

        readable_types_ids = {
            (s.owner_type, s.owner_id) for s in ownership.readable_scopes
        }
        assert (OwnerType.user, str(user_id)) in readable_types_ids
        assert (OwnerType.team, str(team1_id)) in readable_types_ids
        assert (OwnerType.team, str(team2_id)) in readable_types_ids
        assert len(ownership.readable_scopes) == 3

    def test_writable_includes_user_and_team_member_only(self):
        """writable_scopes includes user + team_member team; viewer team is excluded."""
        user_id, team1_id, team2_id, repo, ctx = self._setup()

        ownership = OwnershipResolver(repo).resolve(ctx)

        writable_ids = {s.owner_id for s in ownership.writable_scopes}
        assert str(user_id) in writable_ids
        assert str(team1_id) in writable_ids   # team_member role → writable
        assert str(team2_id) not in writable_ids  # viewer role → read-only

    def test_viewer_team_is_readable_not_writable(self):
        """can_read_from returns True for viewer team; can_write_to returns False."""
        user_id, team1_id, team2_id, repo, ctx = self._setup()

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert ownership.can_read_from(OwnerType.team, str(team2_id)) is True
        assert ownership.can_write_to(OwnerType.team, str(team2_id)) is False

    def test_team_member_team_is_both_readable_and_writable(self):
        """can_read_from and can_write_to both return True for team_member role."""
        user_id, team1_id, team2_id, repo, ctx = self._setup()

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert ownership.can_read_from(OwnerType.team, str(team1_id)) is True
        assert ownership.can_write_to(OwnerType.team, str(team1_id)) is True

    def test_no_enterprise_scope_without_tenant(self):
        """Team membership does not produce an enterprise scope."""
        _, _, _, repo, ctx = self._setup()

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert ownership.has_enterprise_scope is False
        enterprise_scopes = [
            s for s in ownership.readable_scopes if s.owner_type == OwnerType.enterprise
        ]
        assert enterprise_scopes == []

    def test_writable_roles_owner_and_team_admin(self):
        """'owner' and 'team_admin' roles also grant write access."""
        user_id = uuid.uuid4()
        team_owner = uuid.uuid4()
        team_admin = uuid.uuid4()
        repo = _make_repo(
            team_ids=[team_owner, team_admin],
            roles={team_owner: "owner", team_admin: "team_admin"},
        )
        ctx = _make_auth(user_id=user_id)

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert ownership.can_write_to(OwnerType.team, str(team_owner)) is True
        assert ownership.can_write_to(OwnerType.team, str(team_admin)) is True


class TestOwnershipResolverEnterpriseAdmin:
    """Enterprise mode: tenant_id present, user holds system_admin role."""

    def test_enterprise_target_in_readable_scopes(self):
        """Enterprise target is added to readable_scopes when tenant_id is set."""
        tenant_id = uuid.uuid4()
        repo = _make_repo()
        ctx = _make_auth(tenant_id=tenant_id, roles=[Role.system_admin.value])

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert ownership.can_read_from(OwnerType.enterprise, str(tenant_id)) is True

    def test_enterprise_target_in_writable_scopes(self):
        """system_admin with tenant_id gets enterprise in writable_scopes."""
        tenant_id = uuid.uuid4()
        repo = _make_repo()
        ctx = _make_auth(tenant_id=tenant_id, roles=[Role.system_admin.value])

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert ownership.can_write_to(OwnerType.enterprise, str(tenant_id)) is True

    def test_has_enterprise_scope_is_true(self):
        """system_admin in enterprise mode sets has_enterprise_scope=True."""
        tenant_id = uuid.uuid4()
        repo = _make_repo()
        ctx = _make_auth(tenant_id=tenant_id, roles=[Role.system_admin.value])

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert ownership.has_enterprise_scope is True

    def test_tenant_id_propagated(self):
        """ResolvedOwnership.tenant_id matches AuthContext.tenant_id."""
        tenant_id = uuid.uuid4()
        repo = _make_repo()
        ctx = _make_auth(tenant_id=tenant_id, roles=[Role.system_admin.value])

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert ownership.tenant_id == tenant_id

    def test_user_still_default_owner(self):
        """default_owner is always the user target, even for enterprise admins."""
        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        repo = _make_repo()
        ctx = _make_auth(user_id=user_id, tenant_id=tenant_id, roles=[Role.system_admin.value])

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert ownership.default_owner.owner_type == OwnerType.user
        assert ownership.default_owner.owner_id == str(user_id)

    def test_readable_has_user_and_enterprise(self):
        """readable_scopes contains both the user target and the enterprise target."""
        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        repo = _make_repo()
        ctx = _make_auth(user_id=user_id, tenant_id=tenant_id, roles=[Role.system_admin.value])

        ownership = OwnershipResolver(repo).resolve(ctx)

        readable_types = {s.owner_type for s in ownership.readable_scopes}
        assert OwnerType.user in readable_types
        assert OwnerType.enterprise in readable_types


class TestOwnershipResolverEnterpriseNonAdmin:
    """Enterprise mode: tenant_id present, user is NOT system_admin."""

    def test_enterprise_in_readable_not_writable(self):
        """Non-admin enterprise users can read but not write the enterprise scope."""
        tenant_id = uuid.uuid4()
        repo = _make_repo()
        ctx = _make_auth(tenant_id=tenant_id, roles=[Role.team_member.value])

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert ownership.can_read_from(OwnerType.enterprise, str(tenant_id)) is True
        assert ownership.can_write_to(OwnerType.enterprise, str(tenant_id)) is False

    def test_has_enterprise_scope_is_false(self):
        """Non-admin enterprise users do NOT get has_enterprise_scope=True."""
        tenant_id = uuid.uuid4()
        repo = _make_repo()
        ctx = _make_auth(tenant_id=tenant_id, roles=[Role.team_member.value])

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert ownership.has_enterprise_scope is False

    def test_tenant_id_propagated(self):
        """tenant_id is still propagated even for non-admin users."""
        tenant_id = uuid.uuid4()
        repo = _make_repo()
        ctx = _make_auth(tenant_id=tenant_id, roles=[Role.viewer.value])

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert ownership.tenant_id == tenant_id

    def test_viewer_role_non_admin(self):
        """viewer role in enterprise mode: enterprise readable only, user writable."""
        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        repo = _make_repo()
        ctx = _make_auth(user_id=user_id, tenant_id=tenant_id, roles=[Role.viewer.value])

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert ownership.can_write_to(OwnerType.user, str(user_id)) is True
        assert ownership.can_write_to(OwnerType.enterprise, str(tenant_id)) is False
        assert ownership.can_read_from(OwnerType.enterprise, str(tenant_id)) is True

    def test_no_roles_in_enterprise_mode(self):
        """A user with no roles and a tenant_id gets enterprise in readable only."""
        tenant_id = uuid.uuid4()
        repo = _make_repo()
        ctx = _make_auth(tenant_id=tenant_id, roles=[])

        ownership = OwnershipResolver(repo).resolve(ctx)

        assert ownership.can_read_from(OwnerType.enterprise, str(tenant_id)) is True
        assert ownership.can_write_to(OwnerType.enterprise, str(tenant_id)) is False
        assert ownership.has_enterprise_scope is False


class TestOwnershipResolverLocalAdmin:
    """LOCAL_ADMIN_CONTEXT: system_admin role, no tenant_id."""

    def test_local_admin_default_owner_is_user(self):
        """LOCAL_ADMIN_CONTEXT resolves to user-owned default (no enterprise)."""
        repo = _make_repo()

        ownership = OwnershipResolver(repo).resolve(LOCAL_ADMIN_CONTEXT)

        assert ownership.default_owner.owner_type == OwnerType.user
        assert ownership.default_owner.owner_id == str(LOCAL_ADMIN_CONTEXT.user_id)

    def test_local_admin_has_no_enterprise_scope(self):
        """Despite system_admin role, no enterprise scope exists without tenant_id."""
        repo = _make_repo()

        ownership = OwnershipResolver(repo).resolve(LOCAL_ADMIN_CONTEXT)

        assert ownership.has_enterprise_scope is False

    def test_local_admin_no_enterprise_in_readable(self):
        """Without tenant_id, no enterprise target appears in readable_scopes."""
        repo = _make_repo()

        ownership = OwnershipResolver(repo).resolve(LOCAL_ADMIN_CONTEXT)

        enterprise_scopes = [
            s for s in ownership.readable_scopes if s.owner_type == OwnerType.enterprise
        ]
        assert enterprise_scopes == []

    def test_local_admin_tenant_id_is_none(self):
        """LOCAL_ADMIN_CONTEXT has no tenant; ownership reflects that."""
        repo = _make_repo()

        ownership = OwnershipResolver(repo).resolve(LOCAL_ADMIN_CONTEXT)

        assert ownership.tenant_id is None

    def test_local_admin_user_is_readable_and_writable(self):
        """Local admin can read and write their own user scope."""
        repo = _make_repo()

        ownership = OwnershipResolver(repo).resolve(LOCAL_ADMIN_CONTEXT)

        user_id_str = str(LOCAL_ADMIN_CONTEXT.user_id)
        assert ownership.can_read_from(OwnerType.user, user_id_str) is True
        assert ownership.can_write_to(OwnerType.user, user_id_str) is True
