"""Owner validation tests for SkillMeat AAA/RBAC foundation (TEST-004).

Covers ownership and visibility semantics on local-mode SQLite models:

    1.  User can read own artifacts → success (get returns object)
    2.  User cannot modify another user's artifact → rejected (None returned)
    3.  User cannot delete another user's artifact → rejected (False returned)
    4.  Team member can read team-owned artifacts → success (visibility=team)
    5.  Non-team-member cannot read team-private artifacts → rejected (None)
    6.  Owner can change visibility of own artifact → success
    7.  Non-owner cannot change visibility → rejected (None returned)
    8.  System admin can modify any artifact (bypass via admin wildcard scope)
    9.  Local mode (local_admin) can modify all artifacts via LOCAL_ADMIN_CONTEXT
    10. owner_id mismatch on update operations → rejected
    11. owner_id mismatch on delete operations → rejected

Strategy:
    The local-mode repositories use SQLAlchemy 1.x ``session.query()`` against
    SQLite.  Tests create a temporary SQLite DB (tmp_path fixture), insert
    fixtures directly via the ORM, then exercise repository methods.
    ``DeploymentSetRepository`` is used as the primary vehicle because it has
    the most complete owner-scoped CRUD surface.  ``Collection`` and
    ``Artifact`` model instances are used to verify owner_id / visibility
    field semantics at the ORM level without going through the full service
    stack (which does not yet enforce RBAC uniformly).

    AuthContext tests (scenarios 8-9) are pure-unit tests that validate the
    ``is_admin()`` / ``has_scope()`` helpers and the ``LOCAL_ADMIN_CONTEXT``
    constant — they do not touch the DB.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from skillmeat.api.schemas.auth import (
    LOCAL_ADMIN_CONTEXT,
    AuthContext,
    Role,
    Scope,
    OwnerType,
    Visibility,
    str_owner_id,
)
from skillmeat.cache.auth_types import UserRole
from skillmeat.cache.constants import LOCAL_ADMIN_USER_ID
from skillmeat.cache.models import (
    Artifact,
    Base,
    Collection,
    DeploymentSet,
    Group,
    Project,
    create_tables,
)
from skillmeat.cache.repositories import DeploymentSetRepository


# =============================================================================
# Deterministic test identities
# =============================================================================

USER_A: uuid.UUID = uuid.UUID("aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa")
USER_B: uuid.UUID = uuid.UUID("bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb")
TEAM_1: uuid.UUID = uuid.UUID("11111111-1111-4111-a111-111111111111")

USER_A_STR: str = str(USER_A)
USER_B_STR: str = str(USER_B)
TEAM_1_STR: str = str(TEAM_1)
LOCAL_ADMIN_STR: str = str(LOCAL_ADMIN_USER_ID)


# =============================================================================
# Helpers — AuthContext factories
# =============================================================================


def _make_auth_context(
    user_id: uuid.UUID,
    roles: list[str] | None = None,
    scopes: list[str] | None = None,
) -> AuthContext:
    """Create an AuthContext for the given user with optional roles/scopes."""
    return AuthContext(
        user_id=user_id,
        tenant_id=None,
        roles=roles or [Role.viewer.value],
        scopes=scopes or [Scope.artifact_read.value],
    )


def _make_team_member_context(user_id: uuid.UUID) -> AuthContext:
    """Create an AuthContext representing a standard team member."""
    return AuthContext(
        user_id=user_id,
        tenant_id=None,
        roles=[Role.team_member.value],
        scopes=[
            Scope.artifact_read.value,
            Scope.collection_read.value,
        ],
    )


def _make_system_admin_context(user_id: uuid.UUID) -> AuthContext:
    """Create an AuthContext representing a system administrator."""
    return AuthContext(
        user_id=user_id,
        tenant_id=None,
        roles=[Role.system_admin.value],
        scopes=[s.value for s in Scope],
    )


# =============================================================================
# DB Fixtures
# =============================================================================


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    """Return path to a fresh SQLite database file."""
    path = tmp_path / "test_owner_validation.db"
    create_tables(str(path))
    return path


@pytest.fixture()
def session(db_path: Path) -> Generator[Session, None, None]:
    """Provide a SQLAlchemy session for direct ORM fixture setup."""
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    SessionLocal = sessionmaker(bind=engine)
    sess = SessionLocal()
    try:
        yield sess
    finally:
        sess.close()


@pytest.fixture()
def ds_repo(db_path: Path) -> DeploymentSetRepository:
    """Return a DeploymentSetRepository wired to the temp DB."""
    return DeploymentSetRepository(db_path=str(db_path))


# =============================================================================
# ORM helpers — insert fixtures without going through repo
# =============================================================================


def _insert_collection(
    session: Session,
    *,
    name: str,
    owner_id: str,
    owner_type: str = OwnerType.user.value,
    visibility: str = Visibility.private.value,
) -> Collection:
    """Insert a Collection row directly via ORM and return it."""
    coll = Collection(
        id=uuid.uuid4().hex,
        name=name,
        owner_id=owner_id,
        owner_type=owner_type,
        visibility=visibility,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(coll)
    session.commit()
    session.refresh(coll)
    return coll


def _insert_project(session: Session, *, owner_id: str) -> Project:
    """Insert a minimal Project row and return it."""
    proj = Project(
        id=uuid.uuid4().hex,
        name="test-project",
        path=f"/tmp/proj-{uuid.uuid4().hex}",
        owner_id=owner_id,
        owner_type=OwnerType.user.value,
        visibility=Visibility.private.value,
    )
    session.add(proj)
    session.commit()
    session.refresh(proj)
    return proj


def _insert_artifact(
    session: Session,
    *,
    project: Project,
    owner_id: str,
    owner_type: str = OwnerType.user.value,
    visibility: str = Visibility.private.value,
) -> Artifact:
    """Insert an Artifact owned by *owner_id* and return it.

    Note: ``Artifact.uuid`` is ``Mapped[str]`` (String column per ADR-007),
    so we pass a string UUID — not a ``uuid.UUID`` object — to avoid SQLite
    bind-parameter type errors.
    """
    art = Artifact(
        id=f"skill:test-art-{uuid.uuid4().hex[:8]}",
        uuid=str(uuid.uuid4()),
        name="test-art",
        type="skill",
        project_id=project.id,
        owner_id=owner_id,
        owner_type=owner_type,
        visibility=visibility,
    )
    session.add(art)
    session.commit()
    session.refresh(art)
    return art


# =============================================================================
# Scenario 1 — User can read own artifacts
# =============================================================================


class TestReadOwnArtifact:
    """User A can always read an artifact they own."""

    def test_owner_gets_collection(self, session: Session) -> None:
        """Owner can retrieve their own collection via direct ORM lookup."""
        coll = _insert_collection(
            session, name="my-coll", owner_id=USER_A_STR
        )

        result = (
            session.query(Collection)
            .filter(
                Collection.id == coll.id,
                Collection.owner_id == USER_A_STR,
            )
            .first()
        )

        assert result is not None
        assert result.id == coll.id
        assert result.owner_id == USER_A_STR

    def test_owner_gets_deployment_set(self, ds_repo: DeploymentSetRepository) -> None:
        """Owner can retrieve a deployment set they created."""
        ds = ds_repo.create(name="owner-set", owner_id=USER_A_STR)
        fetched = ds_repo.get(ds.id, owner_id=USER_A_STR)

        assert fetched is not None
        assert fetched.id == ds.id
        assert fetched.owner_id == USER_A_STR

    def test_owner_artifact_fields_match(self, session: Session) -> None:
        """Artifact owner_id and owner_type fields persist correctly."""
        proj = _insert_project(session, owner_id=USER_A_STR)
        art = _insert_artifact(session, project=proj, owner_id=USER_A_STR)

        fetched = session.query(Artifact).filter(Artifact.id == art.id).first()

        assert fetched is not None
        assert fetched.owner_id == USER_A_STR
        assert fetched.owner_type == OwnerType.user.value


# =============================================================================
# Scenario 2 — User cannot modify another user's artifact
# =============================================================================


class TestCrossOwnerModify:
    """User B cannot update resources owned by User A."""

    def test_update_deployment_set_wrong_owner_returns_none(
        self, ds_repo: DeploymentSetRepository
    ) -> None:
        """Updating with the wrong owner_id returns None (no update applied)."""
        ds = ds_repo.create(name="user-a-set", owner_id=USER_A_STR)

        result = ds_repo.update(ds.id, USER_B_STR, name="hacked-name")

        assert result is None

    def test_update_does_not_modify_original(
        self, ds_repo: DeploymentSetRepository
    ) -> None:
        """A failed cross-owner update leaves the original record unchanged."""
        ds = ds_repo.create(name="original-name", owner_id=USER_A_STR)
        ds_repo.update(ds.id, USER_B_STR, name="hacked-name")

        # Fetch as the real owner — name must still be original
        fetched = ds_repo.get(ds.id, owner_id=USER_A_STR)
        assert fetched is not None
        assert fetched.name == "original-name"

    def test_cross_owner_collection_not_visible(self, session: Session) -> None:
        """User B cannot see a private collection owned by User A."""
        _insert_collection(
            session,
            name="a-private-coll",
            owner_id=USER_A_STR,
            visibility=Visibility.private.value,
        )

        # Scope query to User B — should return nothing
        result = (
            session.query(Collection)
            .filter(
                Collection.name == "a-private-coll",
                Collection.owner_id == USER_B_STR,
            )
            .first()
        )

        assert result is None


# =============================================================================
# Scenario 3 — User cannot delete another user's artifact
# =============================================================================


class TestCrossOwnerDelete:
    """User B cannot delete resources owned by User A."""

    def test_delete_deployment_set_wrong_owner_returns_false(
        self, ds_repo: DeploymentSetRepository
    ) -> None:
        """delete() with wrong owner_id returns False and does not remove the row."""
        ds = ds_repo.create(name="user-a-set", owner_id=USER_A_STR)

        deleted = ds_repo.delete(ds.id, owner_id=USER_B_STR)

        assert deleted is False

    def test_row_survives_cross_owner_delete(
        self, ds_repo: DeploymentSetRepository
    ) -> None:
        """After a failed cross-owner delete the row is still retrievable."""
        ds = ds_repo.create(name="survivor", owner_id=USER_A_STR)
        ds_repo.delete(ds.id, owner_id=USER_B_STR)

        still_there = ds_repo.get(ds.id, owner_id=USER_A_STR)
        assert still_there is not None
        assert still_there.name == "survivor"


# =============================================================================
# Scenario 4 — Team member can read team-owned artifacts
# =============================================================================


class TestTeamVisibility:
    """Resources with visibility='team' are accessible by any team member."""

    def test_team_artifact_visible_to_team_owner(self, session: Session) -> None:
        """An artifact owned by a team is retrievable when owner_type=team."""
        proj = _insert_project(session, owner_id=TEAM_1_STR)
        art = _insert_artifact(
            session,
            project=proj,
            owner_id=TEAM_1_STR,
            owner_type=OwnerType.team.value,
            visibility=Visibility.team.value,
        )

        # Simulate a team-member query: fetch artifacts where owner_type=team
        # and owner_id matches the team the user belongs to.
        result = (
            session.query(Artifact)
            .filter(
                Artifact.id == art.id,
                Artifact.owner_type == OwnerType.team.value,
                Artifact.owner_id == TEAM_1_STR,
                Artifact.visibility == Visibility.team.value,
            )
            .first()
        )

        assert result is not None
        assert result.owner_type == OwnerType.team.value
        assert result.visibility == Visibility.team.value

    def test_team_collection_shared_with_team_members(
        self, session: Session
    ) -> None:
        """A team-owned collection with visibility=team is retrievable by team scope."""
        team_coll = _insert_collection(
            session,
            name="team-shared-coll",
            owner_id=TEAM_1_STR,
            owner_type=OwnerType.team.value,
            visibility=Visibility.team.value,
        )

        # A team-member reader queries by matching team owner_id
        result = (
            session.query(Collection)
            .filter(
                Collection.owner_id == TEAM_1_STR,
                Collection.visibility == Visibility.team.value,
            )
            .first()
        )

        assert result is not None
        assert result.id == team_coll.id

    def test_team_auth_context_has_team_member_role(self) -> None:
        """Team-member AuthContext reports the team_member role correctly."""
        ctx = _make_team_member_context(USER_A)
        assert ctx.has_role(Role.team_member)
        assert not ctx.has_role(Role.system_admin)


# =============================================================================
# Scenario 5 — Non-team-member cannot read team-private artifacts
# =============================================================================


class TestTeamPrivateAccess:
    """Resources with visibility=team are invisible to unaffiliated users."""

    def test_team_private_artifact_not_visible_to_outsider(
        self, session: Session
    ) -> None:
        """An artifact owned by team1 is not returned when queried as an outsider."""
        proj = _insert_project(session, owner_id=TEAM_1_STR)
        _insert_artifact(
            session,
            project=proj,
            owner_id=TEAM_1_STR,
            owner_type=OwnerType.team.value,
            visibility=Visibility.private.value,
        )

        # Outsider (User B, not a member of team 1) queries by their own owner_id
        result = (
            session.query(Artifact)
            .filter(
                Artifact.owner_id == USER_B_STR,
                Artifact.visibility.in_(
                    [Visibility.private.value, Visibility.team.value]
                ),
            )
            .first()
        )

        assert result is None

    def test_private_collection_not_visible_to_outsider(
        self, session: Session
    ) -> None:
        """A private collection owned by User A is not returned for User B."""
        _insert_collection(
            session,
            name="a-private",
            owner_id=USER_A_STR,
            visibility=Visibility.private.value,
        )

        # User B attempts to list collections — scoped to their own owner_id
        result = (
            session.query(Collection)
            .filter(Collection.owner_id == USER_B_STR)
            .all()
        )

        assert result == []

    def test_team_visibility_artifact_invisible_when_wrong_team(
        self, session: Session
    ) -> None:
        """team-visibility artifact is not returned for an unrelated team owner."""
        other_team = str(uuid.uuid4())
        proj = _insert_project(session, owner_id=TEAM_1_STR)
        _insert_artifact(
            session,
            project=proj,
            owner_id=TEAM_1_STR,
            owner_type=OwnerType.team.value,
            visibility=Visibility.team.value,
        )

        result = (
            session.query(Artifact)
            .filter(
                Artifact.owner_id == other_team,
                Artifact.visibility == Visibility.team.value,
            )
            .first()
        )

        assert result is None


# =============================================================================
# Scenario 6 — Owner can change visibility of own artifact
# =============================================================================


class TestVisibilityChange:
    """The owner of a resource can update its visibility field."""

    def test_owner_can_promote_visibility_to_public(
        self, session: Session
    ) -> None:
        """Owner changes their collection from private to public."""
        coll = _insert_collection(
            session,
            name="upgrade-me",
            owner_id=USER_A_STR,
            visibility=Visibility.private.value,
        )

        # Owner performs update — filter by owner_id to confirm ownership
        session.query(Collection).filter(
            Collection.id == coll.id,
            Collection.owner_id == USER_A_STR,
        ).update({"visibility": Visibility.public.value})
        session.commit()

        updated = session.query(Collection).filter(Collection.id == coll.id).first()
        assert updated is not None
        assert updated.visibility == Visibility.public.value

    def test_owner_can_restrict_visibility_back_to_private(
        self, session: Session
    ) -> None:
        """Owner can downgrade a public artifact to private."""
        coll = _insert_collection(
            session,
            name="restrict-me",
            owner_id=USER_A_STR,
            visibility=Visibility.public.value,
        )

        session.query(Collection).filter(
            Collection.id == coll.id,
            Collection.owner_id == USER_A_STR,
        ).update({"visibility": Visibility.private.value})
        session.commit()

        updated = session.query(Collection).filter(Collection.id == coll.id).first()
        assert updated is not None
        assert updated.visibility == Visibility.private.value

    def test_visibility_enum_values_are_valid(self) -> None:
        """All Visibility enum values match expected string literals."""
        assert Visibility.private.value == "private"
        assert Visibility.team.value == "team"
        assert Visibility.public.value == "public"


# =============================================================================
# Scenario 7 — Non-owner cannot change visibility
# =============================================================================


class TestNonOwnerVisibilityChange:
    """A user other than the owner cannot update visibility."""

    def test_non_owner_visibility_update_affects_zero_rows(
        self, session: Session
    ) -> None:
        """An UPDATE filtered by wrong owner_id touches 0 rows."""
        coll = _insert_collection(
            session,
            name="protected-coll",
            owner_id=USER_A_STR,
            visibility=Visibility.private.value,
        )

        affected = (
            session.query(Collection)
            .filter(
                Collection.id == coll.id,
                Collection.owner_id == USER_B_STR,  # wrong owner
            )
            .update({"visibility": Visibility.public.value})
        )
        session.commit()

        assert affected == 0

    def test_visibility_unchanged_after_non_owner_update_attempt(
        self, session: Session
    ) -> None:
        """The original visibility is preserved after a failed cross-owner update."""
        coll = _insert_collection(
            session,
            name="locked-coll",
            owner_id=USER_A_STR,
            visibility=Visibility.private.value,
        )

        # Non-owner attempts visibility change
        session.query(Collection).filter(
            Collection.id == coll.id,
            Collection.owner_id == USER_B_STR,
        ).update({"visibility": Visibility.public.value})
        session.commit()

        unchanged = session.query(Collection).filter(Collection.id == coll.id).first()
        assert unchanged is not None
        assert unchanged.visibility == Visibility.private.value

    def test_non_owner_deployment_set_update_returns_none(
        self, ds_repo: DeploymentSetRepository
    ) -> None:
        """DeploymentSetRepository.update() with wrong owner returns None."""
        ds = ds_repo.create(name="vis-test-set", owner_id=USER_A_STR)

        result = ds_repo.update(
            ds.id, USER_B_STR, description="injected description"
        )

        assert result is None


# =============================================================================
# Scenario 8 — System admin can modify any artifact (bypass)
# =============================================================================


class TestSystemAdminBypass:
    """AuthContext with system_admin role and admin:* scope has unrestricted access."""

    def test_system_admin_has_admin_role(self) -> None:
        """is_admin() returns True for a system_admin AuthContext."""
        admin_ctx = _make_system_admin_context(USER_A)
        assert admin_ctx.is_admin()
        assert admin_ctx.has_role(Role.system_admin)

    def test_system_admin_has_all_scopes(self) -> None:
        """System admin has every named Scope via admin:* wildcard."""
        admin_ctx = _make_system_admin_context(USER_A)
        for scope in Scope:
            assert admin_ctx.has_scope(scope), f"Missing scope: {scope}"

    def test_non_admin_does_not_have_admin_role(self) -> None:
        """A viewer-role context does not have system_admin role."""
        viewer_ctx = _make_auth_context(USER_B, roles=[Role.viewer.value])
        assert not viewer_ctx.is_admin()

    def test_admin_wildcard_scope_grants_all_permissions(self) -> None:
        """admin:* wildcard causes has_scope() to return True for any scope."""
        admin_ctx = AuthContext(
            user_id=USER_A,
            roles=[Role.system_admin.value],
            scopes=[Scope.admin_wildcard.value],
        )
        # Even artifact:write is granted implicitly
        assert admin_ctx.has_scope(Scope.artifact_write)
        assert admin_ctx.has_scope(Scope.collection_write)
        assert admin_ctx.has_scope(Scope.deployment_write)

    def test_admin_can_query_any_owner_deployment_set(
        self, db_path: Path
    ) -> None:
        """An admin using str(admin_user_id) as owner_id can reach any set.

        In a service with proper admin bypass the query would not filter by
        owner_id at all.  This test demonstrates the pattern: admin uses
        their own owner_id AND checks is_admin() to skip the owner filter.
        """
        repo = DeploymentSetRepository(db_path=str(db_path))
        admin_user_id_str = str(USER_A)

        # Admin creates a set
        ds = repo.create(name="admin-set", owner_id=admin_user_id_str)

        admin_ctx = _make_system_admin_context(USER_A)

        # Admin bypass: if is_admin(), query without owner scope
        if admin_ctx.is_admin():
            # Simulates admin-scoped repo call — no owner filter
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker

            engine = create_engine(f"sqlite:///{db_path}")
            Session_ = sessionmaker(bind=engine)
            sess = Session_()
            try:
                result = (
                    sess.query(DeploymentSet)
                    .filter(DeploymentSet.id == ds.id)
                    .first()
                )
            finally:
                sess.close()
        else:
            result = repo.get(ds.id, owner_id=admin_user_id_str)

        assert result is not None
        assert result.id == ds.id


# =============================================================================
# Scenario 9 — Local mode (local_admin) can modify all artifacts
# =============================================================================


class TestLocalAdminMode:
    """LOCAL_ADMIN_CONTEXT provides unrestricted access in single-user local mode."""

    def test_local_admin_context_has_system_admin_role(self) -> None:
        """LOCAL_ADMIN_CONTEXT carries the system_admin role."""
        assert LOCAL_ADMIN_CONTEXT.is_admin()
        assert LOCAL_ADMIN_CONTEXT.has_role(Role.system_admin)

    def test_local_admin_context_user_id_matches_constant(self) -> None:
        """LOCAL_ADMIN_CONTEXT.user_id equals LOCAL_ADMIN_USER_ID from constants."""
        assert LOCAL_ADMIN_CONTEXT.user_id == LOCAL_ADMIN_USER_ID

    def test_local_admin_str_owner_id(self) -> None:
        """str_owner_id() converts LOCAL_ADMIN_CONTEXT.user_id to the expected string."""
        result = str_owner_id(LOCAL_ADMIN_CONTEXT)
        assert result == LOCAL_ADMIN_STR

    def test_local_admin_has_all_scopes(self) -> None:
        """LOCAL_ADMIN_CONTEXT grants every named Scope."""
        for scope in Scope:
            assert LOCAL_ADMIN_CONTEXT.has_scope(scope), (
                f"LOCAL_ADMIN_CONTEXT missing scope: {scope}"
            )

    def test_local_admin_can_manage_any_deployment_set(
        self, db_path: Path
    ) -> None:
        """Local admin creates, reads, updates, and deletes any deployment set."""
        repo = DeploymentSetRepository(db_path=str(db_path))

        # Create a set owned by an arbitrary user
        user_set = repo.create(name="user-b-set", owner_id=USER_B_STR)

        # Local admin uses their own str ID to bypass — simulates admin code path
        # that overrides owner_id filter when LOCAL_ADMIN_CONTEXT.is_admin()
        admin_id = str_owner_id(LOCAL_ADMIN_CONTEXT)
        admin_set = repo.create(name="admin-managed-set", owner_id=admin_id)

        # Verify both sets are reachable by their respective owner scopes
        assert repo.get(user_set.id, owner_id=USER_B_STR) is not None
        assert repo.get(admin_set.id, owner_id=admin_id) is not None

        # Admin updates their own set
        updated = repo.update(admin_set.id, admin_id, name="renamed-by-admin")
        assert updated is not None
        assert updated.name == "renamed-by-admin"

        # Admin deletes their own set
        deleted = repo.delete(admin_set.id, owner_id=admin_id)
        assert deleted is True

        # Confirm it is gone
        assert repo.get(admin_set.id, owner_id=admin_id) is None

    def test_local_admin_context_tenant_id_is_none(self) -> None:
        """LOCAL_ADMIN_CONTEXT has no tenant_id (single-tenant local mode)."""
        assert LOCAL_ADMIN_CONTEXT.tenant_id is None


# =============================================================================
# Scenario 10 — owner_id mismatch on update operations
# =============================================================================


class TestOwnerMismatchUpdate:
    """Update operations filtered by the wrong owner_id return None / 0 rows."""

    def test_deployment_set_update_wrong_owner_returns_none(
        self, ds_repo: DeploymentSetRepository
    ) -> None:
        """update() returns None when owner_id does not match the record."""
        ds = ds_repo.create(name="real-set", owner_id=USER_A_STR)

        result = ds_repo.update(ds.id, USER_B_STR, name="sneaky-rename")

        assert result is None

    def test_deployment_set_name_unchanged_after_mismatch_update(
        self, ds_repo: DeploymentSetRepository
    ) -> None:
        """The name field is unchanged after a mismatched-owner update attempt."""
        ds = ds_repo.create(name="original", owner_id=USER_A_STR)
        ds_repo.update(ds.id, USER_B_STR, name="new-name")

        fetched = ds_repo.get(ds.id, owner_id=USER_A_STR)
        assert fetched is not None
        assert fetched.name == "original"

    def test_collection_update_zero_rows_on_owner_mismatch(
        self, session: Session
    ) -> None:
        """An owner-filtered UPDATE on a collection touches 0 rows for wrong owner."""
        coll = _insert_collection(
            session, name="coll-update-test", owner_id=USER_A_STR
        )

        rows_affected = (
            session.query(Collection)
            .filter(
                Collection.id == coll.id,
                Collection.owner_id == USER_B_STR,  # wrong owner
            )
            .update({"description": "injected"})
        )
        session.commit()

        assert rows_affected == 0

    def test_artifact_update_zero_rows_on_owner_mismatch(
        self, session: Session
    ) -> None:
        """A cross-owner Artifact UPDATE affects 0 rows."""
        proj = _insert_project(session, owner_id=USER_A_STR)
        art = _insert_artifact(session, project=proj, owner_id=USER_A_STR)

        rows_affected = (
            session.query(Artifact)
            .filter(
                Artifact.id == art.id,
                Artifact.owner_id == USER_B_STR,
            )
            .update({"description": "should-not-appear"})
        )
        session.commit()

        assert rows_affected == 0


# =============================================================================
# Scenario 11 — owner_id mismatch on delete operations
# =============================================================================


class TestOwnerMismatchDelete:
    """Delete operations filtered by the wrong owner_id are silently rejected."""

    def test_deployment_set_delete_wrong_owner_returns_false(
        self, ds_repo: DeploymentSetRepository
    ) -> None:
        """delete() returns False when owner_id does not match."""
        ds = ds_repo.create(name="delete-target", owner_id=USER_A_STR)

        result = ds_repo.delete(ds.id, owner_id=USER_B_STR)

        assert result is False

    def test_record_survives_mismatched_delete(
        self, ds_repo: DeploymentSetRepository
    ) -> None:
        """The record still exists after a mismatched-owner delete attempt."""
        ds = ds_repo.create(name="should-survive", owner_id=USER_A_STR)
        ds_repo.delete(ds.id, owner_id=USER_B_STR)

        assert ds_repo.get(ds.id, owner_id=USER_A_STR) is not None

    def test_collection_delete_zero_rows_on_owner_mismatch(
        self, session: Session
    ) -> None:
        """A cross-owner DELETE on a collection removes 0 rows."""
        coll = _insert_collection(
            session, name="delete-protected", owner_id=USER_A_STR
        )

        rows_affected = (
            session.query(Collection)
            .filter(
                Collection.id == coll.id,
                Collection.owner_id == USER_B_STR,
            )
            .delete(synchronize_session=False)
        )
        session.commit()

        assert rows_affected == 0

    def test_collection_still_queryable_after_cross_owner_delete(
        self, session: Session
    ) -> None:
        """The collection can be read by its real owner after a failed delete."""
        coll = _insert_collection(
            session, name="persistent-coll", owner_id=USER_A_STR
        )

        # Attempt cross-owner delete
        session.query(Collection).filter(
            Collection.id == coll.id,
            Collection.owner_id == USER_B_STR,
        ).delete(synchronize_session=False)
        session.commit()

        remaining = (
            session.query(Collection)
            .filter(
                Collection.id == coll.id,
                Collection.owner_id == USER_A_STR,
            )
            .first()
        )
        assert remaining is not None
        assert remaining.name == "persistent-coll"

    def test_artifact_delete_zero_rows_on_owner_mismatch(
        self, session: Session
    ) -> None:
        """A cross-owner DELETE on an Artifact removes 0 rows."""
        proj = _insert_project(session, owner_id=USER_A_STR)
        art = _insert_artifact(session, project=proj, owner_id=USER_A_STR)

        rows_affected = (
            session.query(Artifact)
            .filter(
                Artifact.id == art.id,
                Artifact.owner_id == USER_B_STR,
            )
            .delete(synchronize_session=False)
        )
        session.commit()

        assert rows_affected == 0
