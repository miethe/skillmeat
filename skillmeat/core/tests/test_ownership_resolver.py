"""Unit tests for OwnershipResolver.

Covers all resolution paths including:
- Single-field resolution (user, team, enterprise)
- Precedence ordering (enterprise > team > user)
- Anonymous fallback when no identifiers are provided
- Resolution from a mock AuthContext object
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from skillmeat.core.bom.scope import OwnershipResolver


@pytest.fixture()
def resolver() -> OwnershipResolver:
    """Return a fresh OwnershipResolver for each test."""
    return OwnershipResolver()


# =============================================================================
# resolve() — explicit kwargs
# =============================================================================


class TestResolveExplicitKwargs:
    """Tests for OwnershipResolver.resolve() with explicit keyword arguments."""

    def test_user_id_only_returns_user_type(self, resolver: OwnershipResolver) -> None:
        owner_type, owner_id = resolver.resolve(user_id="u-abc")
        assert owner_type == "user"
        assert owner_id == "u-abc"

    def test_team_id_only_returns_team_type(self, resolver: OwnershipResolver) -> None:
        owner_type, owner_id = resolver.resolve(team_id="t-xyz")
        assert owner_type == "team"
        assert owner_id == "t-xyz"

    def test_tenant_id_only_returns_enterprise_type(self, resolver: OwnershipResolver) -> None:
        owner_type, owner_id = resolver.resolve(tenant_id="e-org1")
        assert owner_type == "enterprise"
        assert owner_id == "e-org1"

    def test_no_args_returns_anonymous_user(self, resolver: OwnershipResolver) -> None:
        owner_type, owner_id = resolver.resolve()
        assert owner_type == "user"
        assert owner_id == "anonymous"

    def test_none_args_returns_anonymous_user(self, resolver: OwnershipResolver) -> None:
        owner_type, owner_id = resolver.resolve(
            user_id=None, team_id=None, tenant_id=None
        )
        assert owner_type == "user"
        assert owner_id == "anonymous"


# =============================================================================
# resolve() — precedence ordering
# =============================================================================


class TestResolvePrecedence:
    """Precedence rules: enterprise > team > user."""

    def test_tenant_id_wins_over_team_id(self, resolver: OwnershipResolver) -> None:
        owner_type, owner_id = resolver.resolve(team_id="t-1", tenant_id="e-1")
        assert owner_type == "enterprise"
        assert owner_id == "e-1"

    def test_tenant_id_wins_over_user_id(self, resolver: OwnershipResolver) -> None:
        owner_type, owner_id = resolver.resolve(user_id="u-1", tenant_id="e-1")
        assert owner_type == "enterprise"
        assert owner_id == "e-1"

    def test_tenant_id_wins_over_all_three(self, resolver: OwnershipResolver) -> None:
        owner_type, owner_id = resolver.resolve(
            user_id="u-1", team_id="t-1", tenant_id="e-1"
        )
        assert owner_type == "enterprise"
        assert owner_id == "e-1"

    def test_team_id_wins_over_user_id(self, resolver: OwnershipResolver) -> None:
        owner_type, owner_id = resolver.resolve(user_id="u-1", team_id="t-1")
        assert owner_type == "team"
        assert owner_id == "t-1"

    def test_user_id_beats_anonymous_when_team_absent(
        self, resolver: OwnershipResolver
    ) -> None:
        owner_type, owner_id = resolver.resolve(user_id="u-99")
        assert owner_type == "user"
        assert owner_id == "u-99"


# =============================================================================
# resolve() — identity preservation
# =============================================================================


class TestResolveIdentityPreservation:
    """Ensure owner_id is returned verbatim (string conversion only)."""

    def test_owner_id_preserved_as_string_for_user(
        self, resolver: OwnershipResolver
    ) -> None:
        uid = "550e8400-e29b-41d4-a716-446655440000"
        _, owner_id = resolver.resolve(user_id=uid)
        assert owner_id == uid

    def test_owner_id_preserved_as_string_for_team(
        self, resolver: OwnershipResolver
    ) -> None:
        tid = "team-alpha-42"
        _, owner_id = resolver.resolve(team_id=tid)
        assert owner_id == tid

    def test_owner_id_preserved_as_string_for_enterprise(
        self, resolver: OwnershipResolver
    ) -> None:
        eid = "acme-corp"
        _, owner_id = resolver.resolve(tenant_id=eid)
        assert owner_id == eid


# =============================================================================
# resolve_from_auth_context()
# =============================================================================


class TestResolveFromAuthContext:
    """Tests for OwnershipResolver.resolve_from_auth_context()."""

    def _make_ctx(self, **attrs: object) -> MagicMock:
        """Return a MagicMock with only the provided attributes set."""
        ctx = MagicMock(spec=list(attrs.keys()))
        for key, value in attrs.items():
            setattr(ctx, key, value)
        return ctx

    def test_auth_context_user_id_only(self, resolver: OwnershipResolver) -> None:
        ctx = MagicMock()
        ctx.user_id = "u-abc"
        ctx.team_id = None
        ctx.tenant_id = None

        owner_type, owner_id = resolver.resolve_from_auth_context(ctx)
        assert owner_type == "user"
        assert owner_id == "u-abc"

    def test_auth_context_team_id_beats_user(self, resolver: OwnershipResolver) -> None:
        ctx = MagicMock()
        ctx.user_id = "u-abc"
        ctx.team_id = "t-xyz"
        ctx.tenant_id = None

        owner_type, owner_id = resolver.resolve_from_auth_context(ctx)
        assert owner_type == "team"
        assert owner_id == "t-xyz"

    def test_auth_context_tenant_id_wins_all(self, resolver: OwnershipResolver) -> None:
        ctx = MagicMock()
        ctx.user_id = "u-abc"
        ctx.team_id = "t-xyz"
        ctx.tenant_id = "e-org"

        owner_type, owner_id = resolver.resolve_from_auth_context(ctx)
        assert owner_type == "enterprise"
        assert owner_id == "e-org"

    def test_auth_context_missing_optional_attrs_uses_getattr_default(
        self, resolver: OwnershipResolver
    ) -> None:
        """AuthContext without team_id/tenant_id attributes should not raise."""

        class MinimalContext:
            user_id = "u-min"

        ctx = MinimalContext()
        owner_type, owner_id = resolver.resolve_from_auth_context(ctx)
        assert owner_type == "user"
        assert owner_id == "u-min"

    def test_auth_context_all_none_returns_anonymous(
        self, resolver: OwnershipResolver
    ) -> None:
        ctx = MagicMock()
        ctx.user_id = None
        ctx.team_id = None
        ctx.tenant_id = None

        owner_type, owner_id = resolver.resolve_from_auth_context(ctx)
        assert owner_type == "user"
        assert owner_id == "anonymous"

    def test_auth_context_uuid_objects_are_stringified(
        self, resolver: OwnershipResolver
    ) -> None:
        """UUID objects from the real AuthContext must be converted to str."""
        import uuid

        ctx = MagicMock()
        uid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        ctx.user_id = uid
        ctx.team_id = None
        ctx.tenant_id = None

        owner_type, owner_id = resolver.resolve_from_auth_context(ctx)
        assert owner_type == "user"
        assert owner_id == str(uid)

    def test_auth_context_local_admin_context_structure(
        self, resolver: OwnershipResolver
    ) -> None:
        """Simulate the LOCAL_ADMIN_CONTEXT that has no team_id/tenant_id."""

        class LocalAdminContext:
            user_id = "local"
            # Intentionally no team_id or tenant_id attributes

        ctx = LocalAdminContext()
        owner_type, owner_id = resolver.resolve_from_auth_context(ctx)
        assert owner_type == "user"
        assert owner_id == "local"
