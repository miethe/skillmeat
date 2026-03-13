"""Unit tests for AttestationScopeResolver.

Covers:
- Role-based visibility (system_admin, enterprise_admin, team_admin, team_member)
- Visibility-level filtering (public, team, private)
- Cross-team isolation (team A cannot see team B records)
- Cross-user isolation (user A cannot see user B's private records)
- filter_visible() returns the correct subset
- build_query_filters() generates correct filter dicts per role/owner type

AttestationRecord objects are simulated via MagicMock instances that expose
only the three attributes the resolver reads: ``owner_type``, ``owner_id``,
and ``visibility``.  This avoids SQLAlchemy ORM instrumentation overhead and
keeps the tests fully in-memory.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from skillmeat.cache.auth_types import OwnerType, Visibility
from skillmeat.cache.models import AttestationRecord
from skillmeat.core.bom.scope import AttestationScopeResolver, OwnershipResolver


# =============================================================================
# Helpers
# =============================================================================


def make_record(
    owner_type: str,
    owner_id: str,
    visibility: str,
    artifact_id: str = "artifact-1",
) -> AttestationRecord:
    """Return a mock object with the same interface as AttestationRecord.

    ``AttestationScopeResolver`` only reads three attributes on the record
    (``owner_type``, ``owner_id``, ``visibility``), so a MagicMock with those
    attributes set satisfies the duck-typing contract without requiring a live
    SQLAlchemy session.

    The return type is annotated as ``AttestationRecord`` so callers benefit
    from type checking; at runtime the object is a ``MagicMock``.
    """
    record = MagicMock(spec=["owner_type", "owner_id", "visibility", "artifact_id"])
    record.owner_type = owner_type
    record.owner_id = owner_id
    record.visibility = visibility
    record.artifact_id = artifact_id
    return record  # type: ignore[return-value]


@pytest.fixture()
def ownership_resolver() -> OwnershipResolver:
    return OwnershipResolver()


@pytest.fixture()
def scope_resolver(ownership_resolver: OwnershipResolver) -> AttestationScopeResolver:
    return AttestationScopeResolver(ownership_resolver)


# =============================================================================
# Test data factories
# =============================================================================


def _user_private(owner_id: str = "u-alice") -> AttestationRecord:
    return make_record(OwnerType.user.value, owner_id, Visibility.private.value)


def _user_public(owner_id: str = "u-alice") -> AttestationRecord:
    return make_record(OwnerType.user.value, owner_id, Visibility.public.value)


def _team_private(owner_id: str = "t-alpha") -> AttestationRecord:
    return make_record(OwnerType.team.value, owner_id, Visibility.private.value)


def _team_team_vis(owner_id: str = "t-alpha") -> AttestationRecord:
    return make_record(OwnerType.team.value, owner_id, Visibility.team.value)


def _team_public(owner_id: str = "t-alpha") -> AttestationRecord:
    return make_record(OwnerType.team.value, owner_id, Visibility.public.value)


def _enterprise_record(owner_id: str = "e-corp") -> AttestationRecord:
    return make_record(OwnerType.enterprise.value, owner_id, Visibility.team.value)


# =============================================================================
# can_view() — system_admin
# =============================================================================


class TestCanViewSystemAdmin:
    """system_admin can see all records regardless of owner or visibility."""

    def test_system_admin_sees_private_user_record(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        record = _user_private("u-alice")
        assert scope_resolver.can_view(
            record, "user", "u-bob", viewer_roles=["system_admin"]
        )

    def test_system_admin_sees_private_team_record(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        record = _team_private("t-alpha")
        assert scope_resolver.can_view(
            record, "user", "u-bob", viewer_roles=["system_admin"]
        )

    def test_system_admin_sees_enterprise_record(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        record = _enterprise_record()
        assert scope_resolver.can_view(
            record, "user", "u-bob", viewer_roles=["system_admin"]
        )

    def test_system_admin_sees_cross_team_record(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        record = _team_private("t-beta")
        assert scope_resolver.can_view(
            record, "team", "t-alpha", viewer_roles=["system_admin"]
        )


# =============================================================================
# can_view() — enterprise_admin
# =============================================================================


class TestCanViewEnterpriseAdmin:
    """enterprise_admin sees all enterprise-owned records."""

    def test_enterprise_admin_sees_enterprise_record(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        record = _enterprise_record()
        assert scope_resolver.can_view(
            record, "enterprise", "e-corp", viewer_roles=["enterprise_admin"]
        )

    def test_enterprise_admin_cannot_see_user_private_record(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        """enterprise_admin role alone does not grant access to user-private records."""
        record = _user_private("u-alice")
        # Enterprise admin is NOT system_admin — cannot see arbitrary user records.
        assert not scope_resolver.can_view(
            record, "enterprise", "e-corp", viewer_roles=["enterprise_admin"]
        )

    def test_enterprise_admin_sees_enterprise_with_team_visibility(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        record = make_record(
            OwnerType.enterprise.value, "e-corp", Visibility.team.value
        )
        assert scope_resolver.can_view(
            record, "enterprise", "e-corp", viewer_roles=["enterprise_admin"]
        )


# =============================================================================
# can_view() — team_admin
# =============================================================================


class TestCanViewTeamAdmin:
    """team_admin sees all records for their own team."""

    def test_team_admin_sees_own_team_private_record(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        record = _team_private("t-alpha")
        assert scope_resolver.can_view(
            record, "team", "t-alpha", viewer_roles=["team_admin"]
        )

    def test_team_admin_sees_own_team_public_record(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        record = _team_public("t-alpha")
        assert scope_resolver.can_view(
            record, "team", "t-alpha", viewer_roles=["team_admin"]
        )

    def test_team_admin_cannot_see_other_team_private_record(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        record = _team_private("t-beta")
        assert not scope_resolver.can_view(
            record, "team", "t-alpha", viewer_roles=["team_admin"]
        )

    def test_team_admin_cannot_see_other_team_even_with_team_visibility(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        record = _team_team_vis("t-beta")
        assert not scope_resolver.can_view(
            record, "team", "t-alpha", viewer_roles=["team_admin"]
        )


# =============================================================================
# can_view() — team_member
# =============================================================================


class TestCanViewTeamMember:
    """team_member sees non-private records for their own team."""

    def test_team_member_sees_own_team_vis_record(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        record = _team_team_vis("t-alpha")
        assert scope_resolver.can_view(
            record, "team", "t-alpha", viewer_roles=["team_member"]
        )

    def test_team_member_sees_own_team_public_record(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        record = _team_public("t-alpha")
        assert scope_resolver.can_view(
            record, "team", "t-alpha", viewer_roles=["team_member"]
        )

    def test_team_member_cannot_see_own_team_private_record(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        record = _team_private("t-alpha")
        assert not scope_resolver.can_view(
            record, "team", "t-alpha", viewer_roles=["team_member"]
        )

    def test_team_member_cannot_see_other_team_record(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        record = _team_team_vis("t-beta")
        assert not scope_resolver.can_view(
            record, "team", "t-alpha", viewer_roles=["team_member"]
        )


# =============================================================================
# can_view() — regular user (no elevated roles)
# =============================================================================


class TestCanViewRegularUser:
    """Regular users can only see their own records or public records."""

    def test_user_sees_own_private_record(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        record = _user_private("u-alice")
        assert scope_resolver.can_view(record, "user", "u-alice", viewer_roles=[])

    def test_user_cannot_see_other_user_private_record(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        record = _user_private("u-alice")
        assert not scope_resolver.can_view(record, "user", "u-bob", viewer_roles=[])

    def test_user_cannot_see_other_user_record_without_roles(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        record = _user_private("u-alice")
        assert not scope_resolver.can_view(record, "user", "u-carol")

    def test_user_sees_public_record_owned_by_other_user(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        record = _user_public("u-alice")
        assert scope_resolver.can_view(record, "user", "u-bob", viewer_roles=[])

    def test_user_sees_public_team_record(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        record = _team_public("t-alpha")
        assert scope_resolver.can_view(record, "user", "u-bob", viewer_roles=[])

    def test_no_roles_no_match_returns_false(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        record = _team_private("t-alpha")
        assert not scope_resolver.can_view(record, "user", "u-bob")


# =============================================================================
# can_view() — public visibility
# =============================================================================


class TestCanViewPublicVisibility:
    """Public records are visible to all authenticated users."""

    def test_public_user_record_visible_to_stranger(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        record = make_record(OwnerType.user.value, "u-alice", Visibility.public.value)
        assert scope_resolver.can_view(record, "user", "u-stranger", viewer_roles=[])

    def test_public_team_record_visible_to_viewer_role(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        record = make_record(OwnerType.team.value, "t-alpha", Visibility.public.value)
        assert scope_resolver.can_view(record, "user", "u-viewer", viewer_roles=["viewer"])

    def test_public_enterprise_record_visible_to_any_user(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        record = make_record(
            OwnerType.enterprise.value, "e-corp", Visibility.public.value
        )
        assert scope_resolver.can_view(record, "user", "u-anyone", viewer_roles=[])


# =============================================================================
# Cross-isolation invariants
# =============================================================================


class TestIsolationInvariants:
    """Cross-team and cross-user isolation must hold."""

    def test_team_a_cannot_see_team_b_private(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        record = _team_private("t-beta")
        assert not scope_resolver.can_view(
            record, "team", "t-alpha", viewer_roles=["team_member"]
        )

    def test_team_a_cannot_see_team_b_team_vis(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        record = _team_team_vis("t-beta")
        assert not scope_resolver.can_view(
            record, "team", "t-alpha", viewer_roles=["team_member"]
        )

    def test_user_a_cannot_see_user_b_private(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        record = _user_private("u-bob")
        assert not scope_resolver.can_view(record, "user", "u-alice", viewer_roles=[])

    def test_team_admin_a_cannot_see_team_b(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        record = _team_private("t-beta")
        assert not scope_resolver.can_view(
            record, "team", "t-alpha", viewer_roles=["team_admin"]
        )


# =============================================================================
# filter_visible()
# =============================================================================


class TestFilterVisible:
    """filter_visible() returns the correct subset from a mixed list."""

    def test_filter_visible_system_admin_sees_all(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        records = [
            _user_private("u-alice"),
            _team_private("t-alpha"),
            _user_public("u-bob"),
            _team_public("t-beta"),
            _enterprise_record(),
        ]
        result = scope_resolver.filter_visible(
            records, "user", "u-admin", viewer_roles=["system_admin"]
        )
        assert result == records

    def test_filter_visible_regular_user_sees_own_and_public(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        own_private = _user_private("u-alice")
        own_public = _user_public("u-alice")
        other_private = _user_private("u-bob")
        other_public = _user_public("u-bob")
        team_private = _team_private("t-alpha")
        team_public = _team_public("t-beta")

        records = [
            own_private,
            own_public,
            other_private,
            other_public,
            team_private,
            team_public,
        ]
        result = scope_resolver.filter_visible(records, "user", "u-alice")
        # own records + all public records
        assert own_private in result
        assert own_public in result
        assert other_private not in result
        assert other_public in result
        assert team_private not in result
        assert team_public in result

    def test_filter_visible_empty_list_returns_empty(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        assert scope_resolver.filter_visible([], "user", "u-1") == []

    def test_filter_visible_preserves_order(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        r1 = _user_public("u-1")
        r2 = _user_public("u-2")
        r3 = _user_public("u-3")
        result = scope_resolver.filter_visible([r1, r2, r3], "user", "u-stranger")
        assert result == [r1, r2, r3]

    def test_filter_visible_team_member_sees_non_private_team_records(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        private_own = _team_private("t-alpha")
        team_vis_own = _team_team_vis("t-alpha")
        public_own = _team_public("t-alpha")
        private_other = _team_private("t-beta")
        team_vis_other = _team_team_vis("t-beta")

        records = [
            private_own,
            team_vis_own,
            public_own,
            private_other,
            team_vis_other,
        ]
        result = scope_resolver.filter_visible(
            records, "team", "t-alpha", viewer_roles=["team_member"]
        )
        assert private_own not in result
        assert team_vis_own in result
        assert public_own in result
        assert private_other not in result
        assert team_vis_other not in result  # different team, not public


# =============================================================================
# build_query_filters()
# =============================================================================


class TestBuildQueryFilters:
    """build_query_filters() produces correct DB filter criteria dicts."""

    def test_system_admin_returns_empty_dict(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        filters = scope_resolver.build_query_filters(
            "user", "u-admin", roles=["system_admin"]
        )
        assert filters == {}

    def test_enterprise_admin_filters_to_enterprise_owner_type(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        filters = scope_resolver.build_query_filters(
            "enterprise", "e-corp", roles=["enterprise_admin"]
        )
        assert filters == {"owner_type": "enterprise"}
        assert "owner_id" not in filters

    def test_team_admin_filters_to_own_team(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        filters = scope_resolver.build_query_filters(
            "team", "t-alpha", roles=["team_admin"]
        )
        assert filters == {"owner_type": "team", "owner_id": "t-alpha"}

    def test_team_member_filters_to_own_team(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        filters = scope_resolver.build_query_filters(
            "team", "t-alpha", roles=["team_member"]
        )
        assert filters == {"owner_type": "team", "owner_id": "t-alpha"}

    def test_regular_user_filters_to_own_records(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        filters = scope_resolver.build_query_filters("user", "u-alice", roles=[])
        assert filters == {"owner_type": "user", "owner_id": "u-alice"}

    def test_no_roles_defaults_to_user_filter(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        filters = scope_resolver.build_query_filters("user", "u-bob")
        assert filters == {"owner_type": "user", "owner_id": "u-bob"}

    def test_none_roles_treated_as_empty(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        filters = scope_resolver.build_query_filters("user", "u-carol", roles=None)
        assert filters == {"owner_type": "user", "owner_id": "u-carol"}

    def test_enterprise_owner_type_without_admin_role_filters_to_own(
        self, scope_resolver: AttestationScopeResolver
    ) -> None:
        """An enterprise-owned principal without admin role uses owner_id filter."""
        filters = scope_resolver.build_query_filters(
            "enterprise", "e-corp", roles=["viewer"]
        )
        assert filters == {"owner_type": "enterprise", "owner_id": "e-corp"}


# =============================================================================
# OwnershipResolver — resolve()
# =============================================================================


class TestOwnershipResolverResolve:
    """OwnershipResolver.resolve() precedence rules."""

    @pytest.fixture()
    def resolver(self) -> OwnershipResolver:
        return OwnershipResolver()

    def test_tenant_id_wins_over_all(self, resolver: OwnershipResolver) -> None:
        owner_type, owner_id = resolver.resolve(
            user_id="u-1", team_id="t-1", tenant_id="e-1"
        )
        assert owner_type == OwnerType.enterprise.value
        assert owner_id == "e-1"

    def test_team_id_wins_over_user(self, resolver: OwnershipResolver) -> None:
        owner_type, owner_id = resolver.resolve(user_id="u-1", team_id="t-1")
        assert owner_type == OwnerType.team.value
        assert owner_id == "t-1"

    def test_user_id_only(self, resolver: OwnershipResolver) -> None:
        owner_type, owner_id = resolver.resolve(user_id="u-42")
        assert owner_type == OwnerType.user.value
        assert owner_id == "u-42"

    def test_no_ids_returns_anonymous(self, resolver: OwnershipResolver) -> None:
        owner_type, owner_id = resolver.resolve()
        assert owner_type == OwnerType.user.value
        assert owner_id == "anonymous"

    def test_none_ids_return_anonymous(self, resolver: OwnershipResolver) -> None:
        owner_type, owner_id = resolver.resolve(
            user_id=None, team_id=None, tenant_id=None
        )
        assert owner_type == OwnerType.user.value
        assert owner_id == "anonymous"

    def test_tenant_id_without_user_or_team(self, resolver: OwnershipResolver) -> None:
        owner_type, owner_id = resolver.resolve(tenant_id="e-99")
        assert owner_type == OwnerType.enterprise.value
        assert owner_id == "e-99"

    def test_team_id_without_user(self, resolver: OwnershipResolver) -> None:
        owner_type, owner_id = resolver.resolve(team_id="t-77")
        assert owner_type == OwnerType.team.value
        assert owner_id == "t-77"


# =============================================================================
# OwnershipResolver — resolve_from_auth_context()
# =============================================================================


class TestOwnershipResolverFromAuthContext:
    """OwnershipResolver.resolve_from_auth_context() uses getattr safely."""

    @pytest.fixture()
    def resolver(self) -> OwnershipResolver:
        return OwnershipResolver()

    def test_extracts_user_id_from_context(self, resolver: OwnershipResolver) -> None:
        from types import SimpleNamespace

        ctx = SimpleNamespace(user_id="u-ctx", team_id=None, tenant_id=None)
        owner_type, owner_id = resolver.resolve_from_auth_context(ctx)
        assert owner_type == OwnerType.user.value
        assert owner_id == "u-ctx"

    def test_extracts_team_id_from_context(self, resolver: OwnershipResolver) -> None:
        from types import SimpleNamespace

        ctx = SimpleNamespace(user_id="u-ctx", team_id="t-ctx", tenant_id=None)
        owner_type, owner_id = resolver.resolve_from_auth_context(ctx)
        assert owner_type == OwnerType.team.value
        assert owner_id == "t-ctx"

    def test_extracts_tenant_id_from_context(self, resolver: OwnershipResolver) -> None:
        from types import SimpleNamespace

        ctx = SimpleNamespace(user_id="u-ctx", team_id="t-ctx", tenant_id="e-ctx")
        owner_type, owner_id = resolver.resolve_from_auth_context(ctx)
        assert owner_type == OwnerType.enterprise.value
        assert owner_id == "e-ctx"

    def test_missing_attributes_fallback_to_anonymous(
        self, resolver: OwnershipResolver
    ) -> None:
        """Objects with none of the expected attributes yield anonymous."""

        class EmptyContext:
            pass

        owner_type, owner_id = resolver.resolve_from_auth_context(EmptyContext())
        assert owner_type == OwnerType.user.value
        assert owner_id == "anonymous"

    def test_uuid_ids_are_converted_to_str(self, resolver: OwnershipResolver) -> None:
        """UUID objects in auth context are stringified before calling resolve()."""
        import uuid
        from types import SimpleNamespace

        uid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        ctx = SimpleNamespace(user_id=uid, team_id=None, tenant_id=None)
        owner_type, owner_id = resolver.resolve_from_auth_context(ctx)
        assert owner_type == OwnerType.user.value
        assert owner_id == str(uid)
