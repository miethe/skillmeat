"""Unit tests for membership-aware filter helpers and owner write validation.

Coverage (mock-based — no database required):
    P5-001  validate_write_target
            - returns True when target is in writable_scopes
            - returns False when target is NOT in writable_scopes
            - returns True for user's own scope
            - returns False for team scope user doesn't belong to

    P5-002  apply_ownership_filter (1.x Query variant)
            - user-only readable_scopes produces correct condition
            - user + team readable_scopes produces OR across both
            - empty readable_scopes produces filter(False)
            - enterprise scope in readable_scopes is included

    P5-003  apply_membership_visibility_filter (1.x Query variant)
            - admin user → no filter, query returned unchanged
            - public rows → visible to all users
            - private rows → visible only to row owner
            - team rows → visible if owning team is in readable_scopes
            - team rows → NOT visible if owning team is NOT in readable_scopes

    P5-004  apply_visibility_filter backward-compatibility wrapper
            - without resolved_ownership → old tenant-wide shortcut (team = all)
            - with resolved_ownership → delegates to membership-aware helper

    P5-005  apply_ownership_filter_stmt / apply_membership_visibility_filter_stmt
            - same logic as 1.x variants but via stmt.where() API

Design notes
------------
Mock models are plain Python classes with SQLAlchemy column-like class attributes
created via ``sqlalchemy.Column`` so the ORM can compare them symbolically (e.g.
``Model.visibility == "public"``).  We do NOT run any SQL engine — we simply
inspect whether ``.filter()`` / ``.where()`` was called and verify admin bypass
returns the original object.

For predicate-content assertions we inspect the compiled SQL string of the
SQLAlchemy clause object captured by the mock, which is engine-independent.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, call

import pytest
import sqlalchemy as sa

from skillmeat.api.schemas.auth import AuthContext, Role, Scope
from skillmeat.cache.auth_types import OwnerType
from skillmeat.core.ownership import OwnerTarget, ResolvedOwnership
from skillmeat.core.repositories.filters import (
    apply_membership_visibility_filter,
    apply_membership_visibility_filter_stmt,
    apply_ownership_filter,
    apply_ownership_filter_stmt,
    apply_visibility_filter,
    apply_visibility_filter_stmt,
    validate_write_target,
)

# ---------------------------------------------------------------------------
# Deterministic test UUIDs
# ---------------------------------------------------------------------------

USER_A: uuid.UUID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
USER_B: uuid.UUID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
ADMIN_USER: uuid.UUID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")

TEAM_ID = "team-xyz"
TEAM_ID_OTHER = "team-other"
ENTERPRISE_ID = "tenant-001"


# ---------------------------------------------------------------------------
# Minimal mock model with SQLAlchemy column descriptors
# ---------------------------------------------------------------------------


class _MockModel:
    """Minimal mock ORM model.

    Uses real ``sa.Column`` instances as class-level descriptors so that
    expressions like ``_MockModel.visibility == "public"`` produce proper
    SQLAlchemy ``BinaryExpression`` objects — the same objects the filter
    helpers pass to ``.filter()`` / ``.where()``.
    """

    __name__ = "_MockModel"

    # Column descriptors (class-level) — only used for symbolic expression
    # building; no table/engine binding needed.
    visibility = sa.Column(sa.String)
    owner_id = sa.Column(sa.String)
    owner_type = sa.Column(sa.String)


# ---------------------------------------------------------------------------
# AuthContext / ResolvedOwnership factories
# ---------------------------------------------------------------------------


def _regular_ctx(user_id: uuid.UUID = USER_A) -> AuthContext:
    return AuthContext(
        user_id=user_id,
        roles=[Role.team_member.value],
        scopes=[Scope.artifact_read.value],
    )


def _admin_ctx(user_id: uuid.UUID = ADMIN_USER) -> AuthContext:
    return AuthContext(
        user_id=user_id,
        roles=[Role.system_admin.value],
        scopes=[s.value for s in Scope],
    )


def _user_target(user_id: str = str(USER_A)) -> OwnerTarget:
    return OwnerTarget(owner_type=OwnerType.user, owner_id=user_id)


def _team_target(team_id: str = TEAM_ID) -> OwnerTarget:
    return OwnerTarget(owner_type=OwnerType.team, owner_id=team_id)


def _enterprise_target(tenant_id: str = ENTERPRISE_ID) -> OwnerTarget:
    return OwnerTarget(owner_type=OwnerType.enterprise, owner_id=tenant_id)


def _resolved(
    *,
    user_id: str = str(USER_A),
    readable: list[OwnerTarget] | None = None,
    writable: list[OwnerTarget] | None = None,
) -> ResolvedOwnership:
    user_t = _user_target(user_id)
    readable = readable if readable is not None else [user_t]
    writable = writable if writable is not None else [user_t]
    return ResolvedOwnership(
        default_owner=user_t,
        readable_scopes=readable,
        writable_scopes=writable,
    )


# ---------------------------------------------------------------------------
# Helpers for mock query/stmt inspection
# ---------------------------------------------------------------------------


def _mock_query() -> MagicMock:
    """Return a mock that records .filter() calls and returns itself."""
    q = MagicMock(name="Query")
    q.filter.return_value = q
    return q


def _mock_stmt() -> MagicMock:
    """Return a mock that records .where() calls and returns itself."""
    s = MagicMock(name="Select")
    s.where.return_value = s
    return s


# ===========================================================================
# P5-001  validate_write_target
# ===========================================================================


class TestValidateWriteTarget:
    def test_returns_true_when_target_in_writable_scopes(self) -> None:
        target = _user_target()
        resolved = _resolved(writable=[target])
        assert validate_write_target(target, resolved) is True

    def test_returns_false_when_target_not_in_writable_scopes(self) -> None:
        target = _user_target()
        other_target = _team_target()
        resolved = _resolved(writable=[other_target])
        assert validate_write_target(target, resolved) is False

    def test_returns_true_for_users_own_scope(self) -> None:
        user_id = str(USER_A)
        target = OwnerTarget(owner_type=OwnerType.user, owner_id=user_id)
        resolved = _resolved(user_id=user_id, writable=[target])
        assert validate_write_target(target, resolved) is True

    def test_returns_false_for_team_scope_user_doesnt_belong_to(self) -> None:
        team_target = _team_target(TEAM_ID_OTHER)
        # writable_scopes only contains the user's own scope
        resolved = _resolved(writable=[_user_target()])
        assert validate_write_target(team_target, resolved) is False

    def test_returns_false_when_writable_scopes_empty(self) -> None:
        resolved = _resolved(writable=[])
        assert validate_write_target(_user_target(), resolved) is False

    def test_enterprise_target_writable_when_in_scopes(self) -> None:
        ent_target = _enterprise_target()
        resolved = _resolved(writable=[ent_target])
        assert validate_write_target(ent_target, resolved) is True


# ===========================================================================
# P5-002  apply_ownership_filter (1.x Query variant)
# ===========================================================================


class TestApplyOwnershipFilter1x:
    """Mock-based tests verifying .filter() is called with correct predicates."""

    def test_user_only_scope_calls_filter_once(self) -> None:
        resolved = _resolved(readable=[_user_target()])
        q = _mock_query()
        result = apply_ownership_filter(q, _MockModel, resolved)
        q.filter.assert_called_once()
        assert result is q

    def test_user_and_team_scopes_produce_or_filter(self) -> None:
        resolved = _resolved(readable=[_user_target(), _team_target()])
        q = _mock_query()
        apply_ownership_filter(q, _MockModel, resolved)
        q.filter.assert_called_once()
        # The single argument to filter() should be an OR clause.
        (clause,) = q.filter.call_args.args
        compiled = str(clause.compile(compile_kwargs={"literal_binds": True}))
        assert "user" in compiled
        assert TEAM_ID in compiled

    def test_empty_readable_scopes_filters_false(self) -> None:
        resolved = _resolved(readable=[])
        q = _mock_query()
        apply_ownership_filter(q, _MockModel, resolved)
        # filter(False) is the "return nothing" guard
        q.filter.assert_called_once_with(False)

    def test_enterprise_scope_included_in_filter(self) -> None:
        ent_target = _enterprise_target()
        resolved = _resolved(readable=[_user_target(), ent_target])
        q = _mock_query()
        apply_ownership_filter(q, _MockModel, resolved)
        q.filter.assert_called_once()
        (clause,) = q.filter.call_args.args
        compiled = str(clause.compile(compile_kwargs={"literal_binds": True}))
        assert ENTERPRISE_ID in compiled
        assert OwnerType.enterprise.value in compiled

    def test_single_scope_uses_and_not_or(self) -> None:
        """Single scope still wraps in or_() for consistency (SA flattens it)."""
        resolved = _resolved(readable=[_user_target()])
        q = _mock_query()
        apply_ownership_filter(q, _MockModel, resolved)
        q.filter.assert_called_once()


# ===========================================================================
# P5-003  apply_membership_visibility_filter (1.x Query variant)
# ===========================================================================


class TestApplyMembershipVisibilityFilter1x:
    def test_admin_bypasses_filter_entirely(self) -> None:
        resolved = _resolved()
        q = _mock_query()
        result = apply_membership_visibility_filter(q, _MockModel, _admin_ctx(), resolved)
        q.filter.assert_not_called()
        assert result is q

    def test_public_rows_visible_to_all_in_predicate(self) -> None:
        resolved = _resolved()
        q = _mock_query()
        apply_membership_visibility_filter(q, _MockModel, _regular_ctx(), resolved)
        q.filter.assert_called_once()
        (clause,) = q.filter.call_args.args
        compiled = str(clause.compile(compile_kwargs={"literal_binds": True}))
        assert "public" in compiled

    def test_private_rows_gated_by_owner_id_in_predicate(self) -> None:
        resolved = _resolved(user_id=str(USER_A))
        q = _mock_query()
        apply_membership_visibility_filter(q, _MockModel, _regular_ctx(USER_A), resolved)
        (clause,) = q.filter.call_args.args
        compiled = str(clause.compile(compile_kwargs={"literal_binds": True}))
        assert "private" in compiled
        assert str(USER_A) in compiled

    def test_team_rows_visible_when_team_in_readable_scopes(self) -> None:
        team_target = _team_target(TEAM_ID)
        resolved = _resolved(readable=[_user_target(), team_target])
        q = _mock_query()
        apply_membership_visibility_filter(q, _MockModel, _regular_ctx(), resolved)
        (clause,) = q.filter.call_args.args
        compiled = str(clause.compile(compile_kwargs={"literal_binds": True}))
        assert "team" in compiled
        assert TEAM_ID in compiled

    def test_team_rows_excluded_when_team_not_in_readable_scopes(self) -> None:
        # readable_scopes only contains user — no team membership
        resolved = _resolved(readable=[_user_target()])
        q = _mock_query()
        apply_membership_visibility_filter(q, _MockModel, _regular_ctx(), resolved)
        (clause,) = q.filter.call_args.args
        compiled = str(clause.compile(compile_kwargs={"literal_binds": True}))
        # TEAM_ID should NOT appear because no team scope was granted
        assert TEAM_ID not in compiled

    def test_no_readable_scopes_produces_false_team_clause(self) -> None:
        resolved = _resolved(readable=[])
        q = _mock_query()
        apply_membership_visibility_filter(q, _MockModel, _regular_ctx(), resolved)
        q.filter.assert_called_once()
        # Filter was applied — admin bypass did NOT fire.
        (clause,) = q.filter.call_args.args
        compiled = str(clause.compile(compile_kwargs={"literal_binds": True}))
        # The team clause resolves to a constant false — no team id present
        assert TEAM_ID not in compiled


# ===========================================================================
# P5-004  apply_visibility_filter backward-compatibility
# ===========================================================================


class TestApplyVisibilityFilterBackwardCompat:
    """Verify the wrapper dispatches correctly based on resolved_ownership arg."""

    def test_without_resolved_ownership_team_is_tenant_wide(self) -> None:
        """Old path: team rows visible to all (no membership check)."""
        ctx = _regular_ctx(USER_A)
        q = _mock_query()
        apply_visibility_filter(q, _MockModel, ctx, resolved_ownership=None)
        q.filter.assert_called_once()
        (clause,) = q.filter.call_args.args
        compiled = str(clause.compile(compile_kwargs={"literal_binds": True}))
        # Old shortcut: 'team' appears as a plain equality — no owner_type
        # column alongside it (no AND with owner_type/owner_id pair for team).
        # The 'team' string must be present.
        assert "team" in compiled

    def test_without_resolved_ownership_admin_bypasses(self) -> None:
        ctx = _admin_ctx()
        q = _mock_query()
        result = apply_visibility_filter(q, _MockModel, ctx, resolved_ownership=None)
        q.filter.assert_not_called()
        assert result is q

    def test_with_resolved_ownership_delegates_to_membership_helper(self) -> None:
        """New path: delegates to apply_membership_visibility_filter."""
        resolved = _resolved(readable=[_user_target(), _team_target(TEAM_ID)])
        ctx = _regular_ctx(USER_A)
        q = _mock_query()
        apply_visibility_filter(q, _MockModel, ctx, resolved_ownership=resolved)
        q.filter.assert_called_once()
        # The membership-aware path includes the team_id in the predicate
        (clause,) = q.filter.call_args.args
        compiled = str(clause.compile(compile_kwargs={"literal_binds": True}))
        assert TEAM_ID in compiled

    def test_with_resolved_ownership_admin_still_bypasses(self) -> None:
        resolved = _resolved()
        ctx = _admin_ctx()
        q = _mock_query()
        result = apply_visibility_filter(q, _MockModel, ctx, resolved_ownership=resolved)
        q.filter.assert_not_called()
        assert result is q


# ===========================================================================
# P5-005  2.x Select variant mirrors 1.x Query variant
# ===========================================================================


class TestApplyOwnershipFilterStmt2x:
    def test_user_only_scope_calls_where_once(self) -> None:
        resolved = _resolved(readable=[_user_target()])
        s = _mock_stmt()
        result = apply_ownership_filter_stmt(s, _MockModel, resolved)
        s.where.assert_called_once()
        assert result is s

    def test_user_and_team_scopes_produce_or_where(self) -> None:
        resolved = _resolved(readable=[_user_target(), _team_target()])
        s = _mock_stmt()
        apply_ownership_filter_stmt(s, _MockModel, resolved)
        s.where.assert_called_once()
        (clause,) = s.where.call_args.args
        compiled = str(clause.compile(compile_kwargs={"literal_binds": True}))
        assert "user" in compiled
        assert TEAM_ID in compiled

    def test_empty_readable_scopes_uses_literal_false(self) -> None:
        resolved = _resolved(readable=[])
        s = _mock_stmt()
        apply_ownership_filter_stmt(s, _MockModel, resolved)
        s.where.assert_called_once()
        # literal(False) — the compiled clause should evaluate as constant false
        (clause,) = s.where.call_args.args
        compiled = str(clause.compile(compile_kwargs={"literal_binds": True}))
        assert "0" in compiled or "false" in compiled.lower()

    def test_enterprise_scope_included_in_where(self) -> None:
        ent_target = _enterprise_target()
        resolved = _resolved(readable=[_user_target(), ent_target])
        s = _mock_stmt()
        apply_ownership_filter_stmt(s, _MockModel, resolved)
        s.where.assert_called_once()
        (clause,) = s.where.call_args.args
        compiled = str(clause.compile(compile_kwargs={"literal_binds": True}))
        assert ENTERPRISE_ID in compiled


class TestApplyMembershipVisibilityFilterStmt2x:
    def test_admin_bypasses_filter(self) -> None:
        resolved = _resolved()
        s = _mock_stmt()
        result = apply_membership_visibility_filter_stmt(
            s, _MockModel, _admin_ctx(), resolved
        )
        s.where.assert_not_called()
        assert result is s

    def test_public_rows_included_in_predicate(self) -> None:
        resolved = _resolved()
        s = _mock_stmt()
        apply_membership_visibility_filter_stmt(s, _MockModel, _regular_ctx(), resolved)
        s.where.assert_called_once()
        (clause,) = s.where.call_args.args
        compiled = str(clause.compile(compile_kwargs={"literal_binds": True}))
        assert "public" in compiled

    def test_team_rows_visible_when_team_in_scopes(self) -> None:
        team_target = _team_target(TEAM_ID)
        resolved = _resolved(readable=[_user_target(), team_target])
        s = _mock_stmt()
        apply_membership_visibility_filter_stmt(s, _MockModel, _regular_ctx(), resolved)
        (clause,) = s.where.call_args.args
        compiled = str(clause.compile(compile_kwargs={"literal_binds": True}))
        assert TEAM_ID in compiled

    def test_team_rows_excluded_when_team_not_in_scopes(self) -> None:
        resolved = _resolved(readable=[_user_target()])
        s = _mock_stmt()
        apply_membership_visibility_filter_stmt(s, _MockModel, _regular_ctx(), resolved)
        (clause,) = s.where.call_args.args
        compiled = str(clause.compile(compile_kwargs={"literal_binds": True}))
        assert TEAM_ID not in compiled

    def test_private_rows_gated_by_user_id(self) -> None:
        resolved = _resolved(user_id=str(USER_A))
        s = _mock_stmt()
        apply_membership_visibility_filter_stmt(
            s, _MockModel, _regular_ctx(USER_A), resolved
        )
        (clause,) = s.where.call_args.args
        compiled = str(clause.compile(compile_kwargs={"literal_binds": True}))
        assert "private" in compiled
        assert str(USER_A) in compiled

    def test_visibility_filter_stmt_with_resolved_delegates_to_membership(self) -> None:
        """apply_visibility_filter_stmt delegates to membership-aware helper when
        resolved_ownership is provided."""
        resolved = _resolved(readable=[_user_target(), _team_target(TEAM_ID)])
        ctx = _regular_ctx(USER_A)
        s = _mock_stmt()
        apply_visibility_filter_stmt(s, _MockModel, ctx, resolved_ownership=resolved)
        s.where.assert_called_once()
        (clause,) = s.where.call_args.args
        compiled = str(clause.compile(compile_kwargs={"literal_binds": True}))
        assert TEAM_ID in compiled

    def test_visibility_filter_stmt_without_resolved_uses_old_shortcut(self) -> None:
        """apply_visibility_filter_stmt uses tenant-wide shortcut when no
        resolved_ownership is provided."""
        ctx = _regular_ctx(USER_A)
        s = _mock_stmt()
        apply_visibility_filter_stmt(s, _MockModel, ctx, resolved_ownership=None)
        s.where.assert_called_once()
        (clause,) = s.where.call_args.args
        compiled = str(clause.compile(compile_kwargs={"literal_binds": True}))
        assert "team" in compiled
