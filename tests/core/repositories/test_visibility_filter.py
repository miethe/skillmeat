"""Unit tests for skillmeat.core.repositories.filters visibility filter.

Coverage:
    ENT-002  apply_visibility_filter_stmt / apply_visibility_filter
             - public items visible to all authenticated users
             - team items visible to all within the tenant (simplified)
             - private items visible only to the owner
             - admin bypass (system_admin sees all rows)
             - 1.x Query variant mirrors 2.x Select variant behaviour

Tests use a lightweight in-memory SQLite database with a simple table that
has ``visibility`` and ``owner_id`` String columns — the same column types
used in ``cache/models.py``.  This lets us exercise the real SQLAlchemy
predicate without importing enterprise ORM models that require PostgreSQL.
"""

from __future__ import annotations

import uuid
from typing import List, Optional

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from skillmeat.api.schemas.auth import AuthContext, Role, Scope
from skillmeat.core.repositories.filters import (
    apply_visibility_filter,
    apply_visibility_filter_stmt,
)


# ---------------------------------------------------------------------------
# Deterministic test UUIDs
# ---------------------------------------------------------------------------

USER_A: uuid.UUID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
USER_B: uuid.UUID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
ADMIN_USER: uuid.UUID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


# ---------------------------------------------------------------------------
# Minimal ORM model for testing (no JSONB, no UUID columns — pure SQLite)
# ---------------------------------------------------------------------------


class _TestBase(DeclarativeBase):
    pass


class _Item(_TestBase):
    """Simple model with visibility + owner_id columns matching models.py."""

    __tablename__ = "test_items"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(sa.String, nullable=False)
    visibility: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True, default="private")
    owner_id: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)


# ---------------------------------------------------------------------------
# AuthContext factories
# ---------------------------------------------------------------------------


def _regular_context(user_id: uuid.UUID = USER_A) -> AuthContext:
    return AuthContext(
        user_id=user_id,
        roles=[Role.team_member.value],
        scopes=[Scope.artifact_read.value],
    )


def _admin_context(user_id: uuid.UUID = ADMIN_USER) -> AuthContext:
    return AuthContext(
        user_id=user_id,
        roles=[Role.system_admin.value],
        scopes=[s.value for s in Scope],
    )


# ---------------------------------------------------------------------------
# Per-test in-memory database fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_session() -> Session:
    """Create a fresh in-memory SQLite database with the test schema."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    _TestBase.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()
    yield session
    session.close()
    engine.dispose()


def _seed(session: Session, rows: list[dict]) -> None:
    """Insert rows into test_items for querying."""
    for row in rows:
        session.execute(
            text(
                "INSERT INTO test_items (name, visibility, owner_id)"
                " VALUES (:name, :visibility, :owner_id)"
            ),
            row,
        )
    session.flush()


# ===========================================================================
# apply_visibility_filter_stmt  (SQLAlchemy 2.x Select variant)
# ===========================================================================


class TestApplyVisibilityFilterStmtWithDb:
    """Tests run against a real SQLite DB so predicate evaluation is verified."""

    def _query(
        self,
        session: Session,
        ctx: AuthContext,
        *,
        use_2x: bool = True,
    ) -> List[_Item]:
        if use_2x:
            stmt = sa.select(_Item)
            stmt = apply_visibility_filter_stmt(stmt, _Item, ctx)
            return list(session.execute(stmt).scalars().all())
        else:
            q = session.query(_Item)
            q = apply_visibility_filter(q, _Item, ctx)
            return q.all()

    def test_public_item_visible_to_all(self, db_session: Session) -> None:
        """Public items are visible regardless of who is asking."""
        _seed(
            db_session,
            [{"name": "pub", "visibility": "public", "owner_id": str(USER_B)}],
        )
        results = self._query(db_session, _regular_context(USER_A))
        assert any(r.name == "pub" for r in results)

    def test_team_item_visible_to_tenant_members(self, db_session: Session) -> None:
        """Team-visibility items are visible to all tenant members (simplified)."""
        _seed(
            db_session,
            [{"name": "team_item", "visibility": "team", "owner_id": str(USER_B)}],
        )
        # USER_A is not the owner but shares the same tenant → should be visible
        results = self._query(db_session, _regular_context(USER_A))
        assert any(r.name == "team_item" for r in results)

    def test_private_item_visible_to_owner(self, db_session: Session) -> None:
        """Private items are visible only to their owner."""
        _seed(
            db_session,
            [{"name": "priv", "visibility": "private", "owner_id": str(USER_A)}],
        )
        results = self._query(db_session, _regular_context(USER_A))
        assert any(r.name == "priv" for r in results)

    def test_private_item_not_visible_to_other_user(self, db_session: Session) -> None:
        """Private items owned by USER_A must not be returned for USER_B."""
        _seed(
            db_session,
            [{"name": "priv", "visibility": "private", "owner_id": str(USER_A)}],
        )
        results = self._query(db_session, _regular_context(USER_B))
        assert not any(r.name == "priv" for r in results)

    def test_admin_sees_all_visibility_levels(self, db_session: Session) -> None:
        """Admin bypass: system_admin sees public, team, and private items."""
        _seed(
            db_session,
            [
                {"name": "pub", "visibility": "public", "owner_id": str(USER_A)},
                {"name": "team_item", "visibility": "team", "owner_id": str(USER_A)},
                {"name": "priv", "visibility": "private", "owner_id": str(USER_A)},
            ],
        )
        results = self._query(db_session, _admin_context())
        names = {r.name for r in results}
        assert names == {"pub", "team_item", "priv"}

    def test_admin_sees_other_users_private_items(self, db_session: Session) -> None:
        """Admin must see private items not owned by the admin user."""
        _seed(
            db_session,
            [{"name": "other_priv", "visibility": "private", "owner_id": str(USER_A)}],
        )
        # ADMIN_USER != USER_A; without bypass this would be hidden
        results = self._query(db_session, _admin_context(ADMIN_USER))
        assert any(r.name == "other_priv" for r in results)

    def test_team_admin_not_bypassed(self, db_session: Session) -> None:
        """team_admin is NOT a system_admin; visibility filter must still apply."""
        _seed(
            db_session,
            [{"name": "other_priv", "visibility": "private", "owner_id": str(USER_A)}],
        )
        team_admin_ctx = AuthContext(
            user_id=USER_B,
            roles=[Role.team_admin.value],
            scopes=[s.value for s in Scope],
        )
        results = self._query(db_session, team_admin_ctx)
        # USER_B does not own this private item → must not see it
        assert not any(r.name == "other_priv" for r in results)

    def test_mixed_visibility_returns_correct_subset(self, db_session: Session) -> None:
        """Only pub, team, and own private items appear; other private items do not."""
        _seed(
            db_session,
            [
                {"name": "pub", "visibility": "public", "owner_id": str(USER_B)},
                {"name": "team_item", "visibility": "team", "owner_id": str(USER_B)},
                {"name": "my_priv", "visibility": "private", "owner_id": str(USER_A)},
                {"name": "other_priv", "visibility": "private", "owner_id": str(USER_B)},
            ],
        )
        results = self._query(db_session, _regular_context(USER_A))
        names = {r.name for r in results}
        assert names == {"pub", "team_item", "my_priv"}
        assert "other_priv" not in names

    def test_owner_id_string_comparison(self, db_session: Session) -> None:
        """DES-001: owner_id DB column is String; UUID must be str()-converted."""
        # Store owner as hyphenated UUID string (standard str(UUID) format)
        owner_str = str(USER_A)
        _seed(
            db_session,
            [{"name": "priv", "visibility": "private", "owner_id": owner_str}],
        )
        # AuthContext carries uuid.UUID — filter must convert to string
        results = self._query(db_session, _regular_context(USER_A))
        assert any(r.name == "priv" for r in results)

    def test_no_items_returns_empty_list(self, db_session: Session) -> None:
        """Empty table returns empty list (no crash)."""
        results = self._query(db_session, _regular_context(USER_A))
        assert results == []


# ===========================================================================
# apply_visibility_filter  (SQLAlchemy 1.x Query variant)
# ===========================================================================


class TestApplyVisibilityFilter1xWithDb:
    """Same test scenarios using the 1.x Query variant."""

    def _query(self, session: Session, ctx: AuthContext) -> List[_Item]:
        q = session.query(_Item)
        q = apply_visibility_filter(q, _Item, ctx)
        return q.all()

    def test_public_item_visible(self, db_session: Session) -> None:
        _seed(db_session, [{"name": "pub", "visibility": "public", "owner_id": str(USER_B)}])
        assert any(r.name == "pub" for r in self._query(db_session, _regular_context(USER_A)))

    def test_private_item_own(self, db_session: Session) -> None:
        _seed(db_session, [{"name": "priv", "visibility": "private", "owner_id": str(USER_A)}])
        assert any(r.name == "priv" for r in self._query(db_session, _regular_context(USER_A)))

    def test_private_item_other(self, db_session: Session) -> None:
        _seed(db_session, [{"name": "priv", "visibility": "private", "owner_id": str(USER_A)}])
        assert not any(r.name == "priv" for r in self._query(db_session, _regular_context(USER_B)))

    def test_admin_bypass(self, db_session: Session) -> None:
        _seed(
            db_session,
            [
                {"name": "pub", "visibility": "public", "owner_id": str(USER_A)},
                {"name": "priv", "visibility": "private", "owner_id": str(USER_A)},
            ],
        )
        results = self._query(db_session, _admin_context())
        names = {r.name for r in results}
        assert names == {"pub", "priv"}

    def test_mirrors_2x_variant(self, db_session: Session) -> None:
        """Both variants must return identical result sets for the same context."""
        _seed(
            db_session,
            [
                {"name": "pub", "visibility": "public", "owner_id": str(USER_B)},
                {"name": "team_item", "visibility": "team", "owner_id": str(USER_B)},
                {"name": "my_priv", "visibility": "private", "owner_id": str(USER_A)},
                {"name": "other_priv", "visibility": "private", "owner_id": str(USER_B)},
            ],
        )
        ctx = _regular_context(USER_A)

        stmt = sa.select(_Item)
        stmt = apply_visibility_filter_stmt(stmt, _Item, ctx)
        results_2x = {r.name for r in db_session.execute(stmt).scalars().all()}

        q = db_session.query(_Item)
        q = apply_visibility_filter(q, _Item, ctx)
        results_1x = {r.name for r in q.all()}

        assert results_2x == results_1x
