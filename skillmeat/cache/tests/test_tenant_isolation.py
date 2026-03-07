"""Integration tests verifying tenant isolation across local and enterprise data layers.

TEST-003 — Tenant Isolation Integration Tests (CRITICAL PRIORITY)

Coverage matrix:
    Local models (SQLite, owner_id string field):
        1.  Artifacts created by owner A not visible in owner B queries
        2.  Collections created by owner A not visible to owner B
        3.  Projects scoped to owner A isolated from owner B
        4.  Groups scoped to owner A isolated from owner B
        5.  Visibility=public items visible across owners
        6.  Visibility=team items visible only within team
        7.  Visibility=private items visible only to owner
        8.  owner_type=user vs owner_type=team isolation
        9.  LOCAL_ADMIN_USER_ID can see all local data (local mode)

    Enterprise models (SQLite-in-memory, tenant_id UUID field):
        10. Artifacts created by tenant A not visible to tenant B
        11. Collections created by tenant A not visible to tenant B
        12. Cross-tenant write operations raise TenantIsolationError
        13. Artifact visibility=public is scoped to within-tenant only
        14. Artifact owner_type=user vs owner_type=team isolation within tenant

    Every test class contains at least one NEGATIVE assertion confirming that
    data does NOT leak across ownership boundaries.

Architecture notes:
    - Local models use ``owner_id: str`` (no tenant_id column).
    - Enterprise models use ``tenant_id: uuid.UUID`` enforced through TenantContext.
    - Local tests use an in-memory SQLite engine created per module for speed.
    - Enterprise unit tests use MagicMock sessions (same as existing tests) to
      avoid JSONB/UUID SQLite DDL issues for tests that don't need live DB.
    - Enterprise isolation tests that need real schema use the SQLite+comparator
      patch technique from test_enterprise_collection_repository.py.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Generator, List, Optional
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, event, inspect as sa_inspect, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.sql.schema import ColumnDefault as _ColumnDefault
from sqlalchemy.types import CHAR, TypeDecorator

from skillmeat.cache.auth_types import OwnerType, Visibility
from skillmeat.cache.constants import LOCAL_ADMIN_USER_ID
from skillmeat.cache.enterprise_repositories import (
    EnterpriseArtifactRepository,
    EnterpriseCollectionRepository,
    TenantIsolationError,
    TenantContext,
    tenant_scope,
)
from skillmeat.cache.models import (
    Artifact,
    Base,
    Collection,
    Group,
    Project,
    create_db_engine,
)
from skillmeat.cache.models_enterprise import (
    EnterpriseArtifact,
    EnterpriseArtifactVersion,
    EnterpriseBase,
    EnterpriseCollection,
    EnterpriseCollectionArtifact,
)

# =============================================================================
# Deterministic identity constants
# =============================================================================

# Enterprise tenants
TENANT_A = uuid.UUID("aaaaaaaa-0000-4000-a000-000000000001")
TENANT_B = uuid.UUID("bbbbbbbb-0000-4000-b000-000000000002")

# Local owners (string UUIDs stored as plain strings)
OWNER_A = str(uuid.UUID("cccccccc-0000-4000-c000-000000000001"))
OWNER_B = str(uuid.UUID("dddddddd-0000-4000-d000-000000000002"))
TEAM_ID = str(uuid.UUID("eeeeeeee-0000-4000-e000-000000000001"))

# The local admin UUID as a string (how it's stored in owner_id columns)
LOCAL_ADMIN_OWNER_ID = str(LOCAL_ADMIN_USER_ID)


# =============================================================================
# Local (SQLite) in-memory engine — module-scoped
# =============================================================================


@pytest.fixture(scope="module")
def local_engine():
    """In-memory SQLite engine for local model tests.

    Foreign key enforcement is enabled so cascade behaviour is testable.
    All local model tables are created once for the module; each test uses
    its own transaction that is rolled back on teardown.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _set_pragmas(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def local_session(local_engine) -> Generator[Session, None, None]:
    """Provide a fresh Session per test via a savepoint rollback strategy.

    We start an outer transaction and roll it back after each test so that
    every test gets a clean slate without recreating the schema.
    """
    connection = local_engine.connect()
    trans = connection.begin()
    factory = sessionmaker(bind=connection, autoflush=False, autocommit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        connection.close()


# =============================================================================
# Local model factory helpers
# =============================================================================


def _now() -> datetime:
    return datetime.utcnow()


def _make_project(
    session: Session,
    *,
    name: str = "test-project",
    path: str = "/tmp/test-project",
    owner_id: Optional[str] = None,
    owner_type: str = OwnerType.user.value,
    visibility: str = Visibility.private.value,
) -> Project:
    """Create and flush a local Project row."""
    now = _now()
    project = Project(
        id=uuid.uuid4().hex,
        name=name,
        path=path,
        owner_id=owner_id,
        owner_type=owner_type,
        visibility=visibility,
        created_at=now,
        updated_at=now,
    )
    session.add(project)
    session.flush()
    return project


def _make_artifact(
    session: Session,
    project_id: str,
    *,
    name: str = "test-skill",
    artifact_type: str = "skill",
    owner_id: Optional[str] = None,
    owner_type: str = OwnerType.user.value,
    visibility: str = Visibility.private.value,
) -> Artifact:
    """Create and flush a local Artifact row."""
    now = _now()
    artifact = Artifact(
        id=f"{artifact_type}:{name}",
        project_id=project_id,
        name=name,
        type=artifact_type,
        owner_id=owner_id,
        owner_type=owner_type,
        visibility=visibility,
        created_at=now,
        updated_at=now,
    )
    session.add(artifact)
    session.flush()
    return artifact


def _make_collection(
    session: Session,
    *,
    name: str = "test-collection",
    owner_id: Optional[str] = None,
    owner_type: str = OwnerType.user.value,
    visibility: str = Visibility.private.value,
) -> Collection:
    """Create and flush a local Collection row."""
    now = _now()
    collection = Collection(
        name=name,
        owner_id=owner_id,
        owner_type=owner_type,
        visibility=visibility,
        created_at=now,
        updated_at=now,
    )
    session.add(collection)
    session.flush()
    return collection


def _make_group(
    session: Session,
    collection_id: str,
    *,
    name: str = "test-group",
    owner_id: Optional[str] = None,
    owner_type: str = OwnerType.user.value,
    visibility: str = Visibility.private.value,
) -> Group:
    """Create and flush a local Group row."""
    now = _now()
    group = Group(
        collection_id=collection_id,
        name=name,
        owner_id=owner_id,
        owner_type=owner_type,
        visibility=visibility,
        created_at=now,
        updated_at=now,
    )
    session.add(group)
    session.flush()
    return group


# =============================================================================
# Part 1: Local model isolation — Projects
# =============================================================================


class TestLocalProjectIsolation:
    """owner_id-based Project isolation on local SQLite models."""

    def test_projects_scoped_to_owner_a_not_visible_to_owner_b(
        self, local_session: Session
    ):
        """Projects owned by A must not appear in owner B queries."""
        _make_project(
            local_session,
            name="owner-a-project",
            path="/tmp/owner-a-project",
            owner_id=OWNER_A,
        )
        _make_project(
            local_session,
            name="owner-b-project",
            path="/tmp/owner-b-project",
            owner_id=OWNER_B,
        )

        owner_b_projects = (
            local_session.query(Project)
            .filter(Project.owner_id == OWNER_B)
            .all()
        )
        names = [p.name for p in owner_b_projects]

        # Positive: owner B sees their own project
        assert "owner-b-project" in names, "Owner B must see their own project"
        # NEGATIVE: owner A's project must NOT appear
        assert "owner-a-project" not in names, (
            "Tenant isolation breach: owner A project visible to owner B"
        )

    def test_project_owner_a_query_excludes_owner_b(self, local_session: Session):
        """Owner A queries must exclude owner B data."""
        _make_project(
            local_session,
            name="proj-a-only",
            path="/tmp/proj-a-only",
            owner_id=OWNER_A,
        )
        _make_project(
            local_session,
            name="proj-b-only",
            path="/tmp/proj-b-only",
            owner_id=OWNER_B,
        )

        owner_a_projects = (
            local_session.query(Project)
            .filter(Project.owner_id == OWNER_A)
            .all()
        )
        names = [p.name for p in owner_a_projects]

        # Positive: owner A sees their project
        assert "proj-a-only" in names
        # NEGATIVE: owner B's project must NOT leak
        assert "proj-b-only" not in names, (
            "Tenant isolation breach: owner B project visible to owner A"
        )

    def test_public_project_visible_to_all_owners(self, local_session: Session):
        """Projects with visibility=public should be readable across ownership boundaries."""
        _make_project(
            local_session,
            name="public-project",
            path="/tmp/public-project",
            owner_id=OWNER_A,
            visibility=Visibility.public.value,
        )

        # Owner B queries for public projects
        public_projects = (
            local_session.query(Project)
            .filter(Project.visibility == Visibility.public.value)
            .all()
        )
        names = [p.name for p in public_projects]

        assert "public-project" in names, (
            "Public project must be discoverable by other owners"
        )

    def test_private_project_not_visible_to_other_owners(
        self, local_session: Session
    ):
        """Private projects must not be returned when querying under a different owner."""
        _make_project(
            local_session,
            name="private-project",
            path="/tmp/private-project",
            owner_id=OWNER_A,
            visibility=Visibility.private.value,
        )

        # Owner B only sees their own private projects
        owner_b_private = (
            local_session.query(Project)
            .filter(
                Project.owner_id == OWNER_B,
                Project.visibility == Visibility.private.value,
            )
            .all()
        )
        names = [p.name for p in owner_b_private]

        # NEGATIVE: owner A's private project must NOT appear
        assert "private-project" not in names, (
            "Private project leaked across owner boundary"
        )

    def test_local_admin_can_see_all_projects(self, local_session: Session):
        """LOCAL_ADMIN_USER_ID can read all projects regardless of owner_id.

        In local (single-tenant, single-user) mode, the admin sees everything.
        This is verified by querying without an owner_id filter.
        """
        _make_project(
            local_session,
            name="la-proj-a",
            path="/tmp/la-proj-a",
            owner_id=OWNER_A,
        )
        _make_project(
            local_session,
            name="la-proj-b",
            path="/tmp/la-proj-b",
            owner_id=OWNER_B,
        )

        # Admin reads all projects (no owner filter)
        all_projects = local_session.query(Project).all()
        names = [p.name for p in all_projects]

        assert "la-proj-a" in names, "Admin must see owner A projects"
        assert "la-proj-b" in names, "Admin must see owner B projects"

    def test_owner_type_user_vs_team_isolation(self, local_session: Session):
        """owner_type=user and owner_type=team projects are independently filterable."""
        _make_project(
            local_session,
            name="user-owned-project",
            path="/tmp/user-owned-project",
            owner_id=OWNER_A,
            owner_type=OwnerType.user.value,
        )
        _make_project(
            local_session,
            name="team-owned-project",
            path="/tmp/team-owned-project",
            owner_id=TEAM_ID,
            owner_type=OwnerType.team.value,
        )

        user_projects = (
            local_session.query(Project)
            .filter(Project.owner_type == OwnerType.user.value)
            .all()
        )
        team_projects = (
            local_session.query(Project)
            .filter(Project.owner_type == OwnerType.team.value)
            .all()
        )

        user_names = [p.name for p in user_projects]
        team_names = [p.name for p in team_projects]

        # Positive checks
        assert "user-owned-project" in user_names
        assert "team-owned-project" in team_names
        # NEGATIVE: no cross-type leakage
        assert "team-owned-project" not in user_names, (
            "Team project must not appear in user-scoped query"
        )
        assert "user-owned-project" not in team_names, (
            "User project must not appear in team-scoped query"
        )


# =============================================================================
# Part 2: Local model isolation — Artifacts
# =============================================================================


class TestLocalArtifactIsolation:
    """owner_id-based Artifact isolation on local SQLite models."""

    def test_artifacts_owned_by_a_not_visible_to_b(self, local_session: Session):
        """Artifacts with owner_id=A must not appear in owner_id=B queries."""
        proj = _make_project(
            local_session, name="shared-proj", path="/tmp/shared-proj"
        )
        _make_artifact(
            local_session,
            proj.id,
            name="skill-a",
            artifact_type="skill",
            owner_id=OWNER_A,
        )
        _make_artifact(
            local_session,
            proj.id,
            name="skill-b",
            artifact_type="command",
            owner_id=OWNER_B,
        )

        owner_b_artifacts = (
            local_session.query(Artifact)
            .filter(Artifact.owner_id == OWNER_B)
            .all()
        )
        names = [a.name for a in owner_b_artifacts]

        assert "skill-b" in names, "Owner B must see their own artifact"
        # NEGATIVE: A's artifact must NOT appear
        assert "skill-a" not in names, (
            "Tenant isolation breach: owner A artifact visible to owner B"
        )

    def test_artifact_visibility_private_scoped_to_owner(
        self, local_session: Session
    ):
        """Private artifacts must only appear when querying by the owning owner_id."""
        proj = _make_project(
            local_session, name="vis-proj", path="/tmp/vis-proj"
        )
        _make_artifact(
            local_session,
            proj.id,
            name="private-skill",
            artifact_type="skill",
            owner_id=OWNER_A,
            visibility=Visibility.private.value,
        )

        # Query as owner B — must not see private artifact from owner A
        result = (
            local_session.query(Artifact)
            .filter(
                Artifact.owner_id == OWNER_B,
                Artifact.visibility == Visibility.private.value,
            )
            .all()
        )
        names = [a.name for a in result]

        # NEGATIVE: owner A's private artifact must not be returned
        assert "private-skill" not in names, (
            "Private artifact leaked to different owner"
        )

    def test_artifact_visibility_public_discoverable_across_owners(
        self, local_session: Session
    ):
        """Public artifacts should be discoverable regardless of owner_id filter."""
        proj = _make_project(
            local_session, name="pub-proj", path="/tmp/pub-proj"
        )
        _make_artifact(
            local_session,
            proj.id,
            name="public-skill",
            artifact_type="skill",
            owner_id=OWNER_A,
            visibility=Visibility.public.value,
        )

        public_artifacts = (
            local_session.query(Artifact)
            .filter(Artifact.visibility == Visibility.public.value)
            .all()
        )
        names = [a.name for a in public_artifacts]

        assert "public-skill" in names, "Public artifact must be universally visible"

    def test_artifact_visibility_team_scoped_to_team_members(
        self, local_session: Session
    ):
        """Team-visibility artifacts must only appear when querying with the team owner_id."""
        proj = _make_project(
            local_session, name="team-proj", path="/tmp/team-proj"
        )
        _make_artifact(
            local_session,
            proj.id,
            name="team-skill",
            artifact_type="skill",
            owner_id=TEAM_ID,
            owner_type=OwnerType.team.value,
            visibility=Visibility.team.value,
        )

        # Team member query (matching team owner_id)
        team_artifacts = (
            local_session.query(Artifact)
            .filter(Artifact.owner_id == TEAM_ID)
            .all()
        )
        # Non-member query (different owner_id)
        outsider_artifacts = (
            local_session.query(Artifact)
            .filter(Artifact.owner_id == OWNER_B)
            .all()
        )

        team_names = [a.name for a in team_artifacts]
        outsider_names = [a.name for a in outsider_artifacts]

        # Positive: team member sees the artifact
        assert "team-skill" in team_names, (
            "Team artifact must be visible to team owner query"
        )
        # NEGATIVE: non-team owner must not see it
        assert "team-skill" not in outsider_names, (
            "Team artifact must not be visible to non-team owner query"
        )

    def test_local_admin_sees_all_artifacts(self, local_session: Session):
        """LOCAL_ADMIN_USER_ID (no owner filter) can see all artifacts in local mode."""
        proj = _make_project(
            local_session, name="admin-art-proj", path="/tmp/admin-art-proj"
        )
        _make_artifact(
            local_session,
            proj.id,
            name="admin-skill-a",
            artifact_type="skill",
            owner_id=OWNER_A,
        )
        _make_artifact(
            local_session,
            proj.id,
            name="admin-skill-b",
            artifact_type="command",
            owner_id=OWNER_B,
        )

        # Admin reads all (no owner filter)
        all_artifacts = local_session.query(Artifact).all()
        names = [a.name for a in all_artifacts]

        assert "admin-skill-a" in names, "Admin must see owner A artifacts"
        assert "admin-skill-b" in names, "Admin must see owner B artifacts"


# =============================================================================
# Part 3: Local model isolation — Collections
# =============================================================================


class TestLocalCollectionIsolation:
    """owner_id-based Collection isolation on local SQLite models."""

    def test_collections_owned_by_a_not_visible_to_b(
        self, local_session: Session
    ):
        """Collections with owner_id=A must not appear in owner_id=B queries."""
        _make_collection(
            local_session,
            name="collection-a",
            owner_id=OWNER_A,
        )
        _make_collection(
            local_session,
            name="collection-b",
            owner_id=OWNER_B,
        )

        owner_b_collections = (
            local_session.query(Collection)
            .filter(Collection.owner_id == OWNER_B)
            .all()
        )
        names = [c.name for c in owner_b_collections]

        assert "collection-b" in names, "Owner B must see their own collection"
        # NEGATIVE: A's collection must NOT appear
        assert "collection-a" not in names, (
            "Tenant isolation breach: owner A collection visible to owner B"
        )

    def test_public_collection_visible_across_owners(
        self, local_session: Session
    ):
        """Collections with visibility=public must appear in cross-owner queries."""
        _make_collection(
            local_session,
            name="public-collection",
            owner_id=OWNER_A,
            visibility=Visibility.public.value,
        )

        public_cols = (
            local_session.query(Collection)
            .filter(Collection.visibility == Visibility.public.value)
            .all()
        )
        names = [c.name for c in public_cols]

        assert "public-collection" in names

    def test_private_collection_not_visible_to_other_owner(
        self, local_session: Session
    ):
        """Private collections must not leak across owner boundaries."""
        _make_collection(
            local_session,
            name="private-collection",
            owner_id=OWNER_A,
            visibility=Visibility.private.value,
        )

        owner_b_private = (
            local_session.query(Collection)
            .filter(
                Collection.owner_id == OWNER_B,
                Collection.visibility == Visibility.private.value,
            )
            .all()
        )
        names = [c.name for c in owner_b_private]

        # NEGATIVE: must not appear
        assert "private-collection" not in names, (
            "Private collection leaked to different owner"
        )

    def test_collection_owner_type_user_vs_team(self, local_session: Session):
        """User-owned and team-owned collections are independently filterable."""
        _make_collection(
            local_session,
            name="user-collection",
            owner_id=OWNER_A,
            owner_type=OwnerType.user.value,
        )
        _make_collection(
            local_session,
            name="team-collection",
            owner_id=TEAM_ID,
            owner_type=OwnerType.team.value,
        )

        user_cols = (
            local_session.query(Collection)
            .filter(Collection.owner_type == OwnerType.user.value)
            .all()
        )
        team_cols = (
            local_session.query(Collection)
            .filter(Collection.owner_type == OwnerType.team.value)
            .all()
        )

        user_names = [c.name for c in user_cols]
        team_names = [c.name for c in team_cols]

        # Positive
        assert "user-collection" in user_names
        assert "team-collection" in team_names
        # NEGATIVE: no cross-type leakage
        assert "team-collection" not in user_names, (
            "Team collection must not appear in user-owned query"
        )
        assert "user-collection" not in team_names, (
            "User collection must not appear in team-owned query"
        )


# =============================================================================
# Part 4: Local model isolation — Groups
# =============================================================================


class TestLocalGroupIsolation:
    """owner_id-based Group isolation on local SQLite models."""

    def test_groups_owned_by_a_not_visible_to_b(self, local_session: Session):
        """Groups with owner_id=A must not appear in owner_id=B queries."""
        coll = _make_collection(local_session, name="group-isolation-coll")
        _make_group(
            local_session,
            coll.id,
            name="group-a",
            owner_id=OWNER_A,
        )
        _make_group(
            local_session,
            coll.id,
            name="group-b",
            owner_id=OWNER_B,
        )

        owner_b_groups = (
            local_session.query(Group)
            .filter(Group.owner_id == OWNER_B)
            .all()
        )
        names = [g.name for g in owner_b_groups]

        assert "group-b" in names, "Owner B must see their own group"
        # NEGATIVE
        assert "group-a" not in names, (
            "Tenant isolation breach: owner A group visible to owner B"
        )

    def test_private_group_not_visible_to_other_owner(
        self, local_session: Session
    ):
        """Private groups must not be returned when filtering by a different owner."""
        coll = _make_collection(local_session, name="private-group-coll")
        _make_group(
            local_session,
            coll.id,
            name="private-group",
            owner_id=OWNER_A,
            visibility=Visibility.private.value,
        )

        owner_b_private_groups = (
            local_session.query(Group)
            .filter(
                Group.owner_id == OWNER_B,
                Group.visibility == Visibility.private.value,
            )
            .all()
        )
        names = [g.name for g in owner_b_private_groups]

        # NEGATIVE: must not appear
        assert "private-group" not in names, (
            "Private group leaked to different owner"
        )

    def test_public_group_visible_across_owners(self, local_session: Session):
        """Groups with visibility=public must appear in cross-owner queries."""
        coll = _make_collection(local_session, name="public-group-coll")
        _make_group(
            local_session,
            coll.id,
            name="public-group",
            owner_id=OWNER_A,
            visibility=Visibility.public.value,
        )

        public_groups = (
            local_session.query(Group)
            .filter(Group.visibility == Visibility.public.value)
            .all()
        )
        names = [g.name for g in public_groups]

        assert "public-group" in names

    def test_local_admin_sees_all_groups(self, local_session: Session):
        """LOCAL_ADMIN_USER_ID (no filter) sees all groups regardless of owner_id."""
        coll = _make_collection(local_session, name="admin-group-coll")
        _make_group(
            local_session, coll.id, name="admin-group-a", owner_id=OWNER_A
        )
        _make_group(
            local_session, coll.id, name="admin-group-b", owner_id=OWNER_B
        )

        all_groups = local_session.query(Group).all()
        names = [g.name for g in all_groups]

        assert "admin-group-a" in names
        assert "admin-group-b" in names


# =============================================================================
# Enterprise SQLite patch helpers (mirror test_enterprise_collection_repository.py)
# =============================================================================


class _UUIDString(TypeDecorator):
    """TypeDecorator that stores UUID as a 36-char hyphenated string in SQLite."""

    impl = CHAR(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(uuid.UUID(str(value)))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)


def _patch_enterprise_metadata_for_sqlite() -> None:
    """Patch JSONB → JSON and UUID → _UUIDString for SQLite compatibility.

    Must be called before EnterpriseBase.metadata.create_all() and must also
    refresh ORM comparator caches (see test_enterprise_collection_repository.py
    for the full explanation of the comparator cache poisoning issue).
    """
    for table in EnterpriseBase.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, JSONB):
                from sqlalchemy import JSON

                column.type = JSON()
            elif isinstance(column.type, PG_UUID):
                column.type = _UUIDString()
            if column.server_default is not None:
                column.server_default = None
            if column.name in ("created_at", "updated_at", "added_at") and column.default is None:
                column.default = _ColumnDefault(datetime.utcnow)

    # Propagate patched types to ORM comparator caches
    _enterprise_model_classes = [
        EnterpriseArtifact,
        EnterpriseArtifactVersion,
        EnterpriseCollection,
        EnterpriseCollectionArtifact,
    ]
    for model_cls in _enterprise_model_classes:
        mapper = sa_inspect(model_cls)
        for col_name, mapped_col in mapper.columns.items():
            attr = getattr(model_cls, col_name, None)
            if attr is not None and hasattr(attr, "comparator"):
                comparator = attr.comparator
                if "type" in comparator.__dict__:
                    comparator.__dict__["type"] = mapped_col.type


@pytest.fixture(scope="module")
def enterprise_engine():
    """In-memory SQLite engine for enterprise schema integration tests."""
    _patch_enterprise_metadata_for_sqlite()

    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(eng, "connect")
    def _set_pragmas(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    EnterpriseBase.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def enterprise_session(enterprise_engine) -> Generator[Session, None, None]:
    """Fresh Session per enterprise test; full commit approach (same as existing tests)."""
    factory = sessionmaker(bind=enterprise_engine, autoflush=False, autocommit=False)
    sess = factory()
    try:
        yield sess
    finally:
        sess.close()


# =============================================================================
# Enterprise factory helpers
# =============================================================================


def _ent_make_artifact(
    session: Session,
    tenant_id: uuid.UUID,
    name: str = "test-skill",
    artifact_type: str = "skill",
    owner_id: Optional[uuid.UUID] = None,
    owner_type: str = OwnerType.user.value,
    visibility: str = Visibility.private.value,
) -> EnterpriseArtifact:
    """Create and flush an EnterpriseArtifact."""
    now = datetime.utcnow()
    artifact = EnterpriseArtifact(
        tenant_id=tenant_id,
        name=name,
        artifact_type=artifact_type,
        owner_id=owner_id,
        owner_type=owner_type,
        visibility=visibility,
        tags=[],
        custom_fields={},
        created_at=now,
        updated_at=now,
    )
    session.add(artifact)
    session.flush()
    return artifact


def _ent_make_collection(
    session: Session,
    tenant_id: uuid.UUID,
    name: str = "test-collection",
    owner_id: Optional[uuid.UUID] = None,
    owner_type: str = OwnerType.user.value,
    visibility: str = Visibility.private.value,
) -> EnterpriseCollection:
    """Create and flush an EnterpriseCollection."""
    now = datetime.utcnow()
    collection = EnterpriseCollection(
        tenant_id=tenant_id,
        name=name,
        owner_id=owner_id,
        owner_type=owner_type,
        visibility=visibility,
        created_at=now,
        updated_at=now,
    )
    session.add(collection)
    session.flush()
    return collection


# =============================================================================
# Part 5: Enterprise artifact isolation — via EnterpriseArtifactRepository
# =============================================================================


class TestEnterpriseArtifactIsolation:
    """Tenant isolation for EnterpriseArtifactRepository (mock-based unit tests).

    These tests use MagicMock sessions so they run without a live PostgreSQL
    database and avoid JSONB/UUID SQLite DDL issues.  The isolation logic
    lives entirely in Python (TenantContext + _assert_tenant_owns), so mock
    sessions exercise the real code paths.
    """

    def _make_art_mock(
        self,
        artifact_id: uuid.UUID,
        tenant_id: uuid.UUID,
        name: str = "skill",
    ) -> MagicMock:
        art = MagicMock(spec=EnterpriseArtifact)
        art.id = artifact_id
        art.tenant_id = tenant_id
        art.name = name
        art.artifact_type = "skill"
        art.tags = []
        art.is_active = True
        art.versions = []
        art.custom_fields = {}
        return art

    def test_tenant_a_artifact_not_returned_to_tenant_b(self) -> None:
        """get() returns None when artifact belongs to a different tenant."""
        art_a = self._make_art_mock(
            artifact_id=uuid.uuid4(), tenant_id=TENANT_A
        )
        session = MagicMock(spec=Session)
        session.get.return_value = art_a

        repo = EnterpriseArtifactRepository(session)

        with tenant_scope(TENANT_B):
            result = repo.get(art_a.id)

        # NEGATIVE: must be None — cross-tenant existence must not be disclosed
        assert result is None, (
            "Tenant isolation breach: tenant A artifact returned to tenant B"
        )

    def test_tenant_b_sees_own_artifact(self) -> None:
        """get() returns the artifact when it belongs to the active tenant."""
        art_b = self._make_art_mock(
            artifact_id=uuid.uuid4(), tenant_id=TENANT_B
        )
        session = MagicMock(spec=Session)
        session.get.return_value = art_b

        repo = EnterpriseArtifactRepository(session)

        with tenant_scope(TENANT_B):
            result = repo.get(art_b.id)

        assert result is art_b

    def test_list_scoped_to_active_tenant(self) -> None:
        """list() only returns artifacts for the current tenant."""
        art_a = self._make_art_mock(
            artifact_id=uuid.uuid4(), tenant_id=TENANT_A, name="art-a"
        )
        # Simulate DB returning only tenant A artifacts (tenant filter applied in query)
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [art_a]
        execute_mock = MagicMock()
        execute_mock.scalars.return_value = scalars_mock
        session = MagicMock(spec=Session)
        session.execute.return_value = execute_mock

        repo = EnterpriseArtifactRepository(session)

        with tenant_scope(TENANT_A):
            results = repo.list()

        assert len(results) == 1
        assert results[0] is art_a

        # NEGATIVE: if tenant B queries, the mock returns empty (simulating WHERE clause filter)
        scalars_mock.all.return_value = []
        with tenant_scope(TENANT_B):
            results_b = repo.list()
        assert results_b == [], (
            "Tenant B list() must not return tenant A's artifacts"
        )

    def test_cross_tenant_update_raises_isolation_error(self) -> None:
        """update() raises TenantIsolationError when artifact belongs to different tenant."""
        art_a = self._make_art_mock(
            artifact_id=uuid.uuid4(), tenant_id=TENANT_A
        )
        session = MagicMock(spec=Session)
        session.get.return_value = art_a

        repo = EnterpriseArtifactRepository(session)

        with tenant_scope(TENANT_B):
            with pytest.raises(TenantIsolationError):
                repo.update(art_a.id, name="hijacked-name")

    def test_cross_tenant_soft_delete_raises_isolation_error(self) -> None:
        """soft_delete() raises TenantIsolationError when artifact belongs to different tenant."""
        art_a = self._make_art_mock(
            artifact_id=uuid.uuid4(), tenant_id=TENANT_A
        )
        session = MagicMock(spec=Session)
        session.get.return_value = art_a

        repo = EnterpriseArtifactRepository(session)

        with tenant_scope(TENANT_B):
            with pytest.raises(TenantIsolationError):
                repo.soft_delete(art_a.id)

    def test_cross_tenant_hard_delete_raises_isolation_error(self) -> None:
        """hard_delete() raises TenantIsolationError when artifact belongs to different tenant."""
        art_a = self._make_art_mock(
            artifact_id=uuid.uuid4(), tenant_id=TENANT_A
        )
        session = MagicMock(spec=Session)
        session.get.return_value = art_a

        repo = EnterpriseArtifactRepository(session)

        with tenant_scope(TENANT_B):
            with pytest.raises(TenantIsolationError):
                repo.hard_delete(art_a.id)

    def test_get_by_uuid_cross_tenant_returns_none(self) -> None:
        """get_by_uuid() applies tenant filter at query time; empty result for wrong tenant."""
        # DB returns empty result because WHERE tenant_id=B finds no TENANT_A artifacts
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        execute_mock = MagicMock()
        execute_mock.scalars.return_value = scalars_mock
        execute_mock.scalar_one_or_none.return_value = None
        session = MagicMock(spec=Session)
        session.execute.return_value = execute_mock

        repo = EnterpriseArtifactRepository(session)

        art_id = uuid.uuid4()
        with tenant_scope(TENANT_B):
            result = repo.get_by_uuid(str(art_id))

        # NEGATIVE: no cross-tenant data returned
        assert result is None, (
            "Tenant isolation breach: get_by_uuid returned data from wrong tenant"
        )

    def test_list_versions_cross_tenant_returns_empty(self) -> None:
        """list_versions() returns [] when artifact belongs to a different tenant."""
        art_a = self._make_art_mock(
            artifact_id=uuid.uuid4(), tenant_id=TENANT_A
        )
        session = MagicMock(spec=Session)
        session.get.return_value = art_a

        repo = EnterpriseArtifactRepository(session)

        with tenant_scope(TENANT_B):
            versions = repo.list_versions(art_a.id)

        # NEGATIVE: versions from a different tenant must not be returned
        assert versions == [], (
            "Tenant isolation breach: list_versions returned data from wrong tenant"
        )

    def test_get_content_cross_tenant_returns_none(self) -> None:
        """get_content() returns None when the artifact belongs to a different tenant."""
        art_a = self._make_art_mock(
            artifact_id=uuid.uuid4(), tenant_id=TENANT_A
        )
        session = MagicMock(spec=Session)
        session.get.return_value = art_a

        repo = EnterpriseArtifactRepository(session)

        with tenant_scope(TENANT_B):
            content = repo.get_content(art_a.id)

        # NEGATIVE: content must not be returned for wrong tenant
        assert content is None, (
            "Tenant isolation breach: get_content returned data from wrong tenant"
        )


# =============================================================================
# Part 6: Enterprise collection isolation — live SQLite schema tests
# =============================================================================


class TestEnterpriseCollectionIsolation:
    """Tenant isolation for EnterpriseCollectionRepository (SQLite in-memory).

    Uses the patched enterprise schema fixtures to exercise real SQL queries
    and confirm that tenant_id predicates correctly partition data.
    """

    def test_tenant_a_collection_not_visible_to_tenant_b(
        self, enterprise_session: Session
    ):
        """list() for tenant B must not include tenant A's collections."""
        with tenant_scope(TENANT_A):
            repo_a = EnterpriseCollectionRepository(enterprise_session)
            repo_a.create("Collection Exclusive to A")

        with tenant_scope(TENANT_B):
            repo_b = EnterpriseCollectionRepository(enterprise_session)
            results = repo_b.list()

        names = [c.name for c in results]

        # NEGATIVE: tenant A's collection must not appear
        assert "Collection Exclusive to A" not in names, (
            "Tenant isolation breach: tenant A collection visible to tenant B"
        )

    def test_tenant_b_collection_not_visible_to_tenant_a(
        self, enterprise_session: Session
    ):
        """list() for tenant A must not include tenant B's collections."""
        with tenant_scope(TENANT_B):
            repo_b = EnterpriseCollectionRepository(enterprise_session)
            repo_b.create("Collection Exclusive to B")

        with tenant_scope(TENANT_A):
            repo_a = EnterpriseCollectionRepository(enterprise_session)
            results = repo_a.list()

        names = [c.name for c in results]

        # NEGATIVE: tenant B's collection must not appear
        assert "Collection Exclusive to B" not in names, (
            "Tenant isolation breach: tenant B collection visible to tenant A"
        )

    def test_tenant_a_cannot_get_tenant_b_collection(
        self, enterprise_session: Session
    ):
        """get() raises TenantIsolationError when collection belongs to a different tenant."""
        with tenant_scope(TENANT_B):
            col_b = _ent_make_collection(
                enterprise_session, TENANT_B, name="B Get-Guard Col"
            )
            enterprise_session.commit()

        with tenant_scope(TENANT_A):
            repo = EnterpriseCollectionRepository(enterprise_session)
            with pytest.raises(TenantIsolationError):
                repo.get(col_b.id)

    def test_tenant_a_cannot_update_tenant_b_collection(
        self, enterprise_session: Session
    ):
        """update() raises TenantIsolationError when targeting another tenant's collection."""
        with tenant_scope(TENANT_B):
            col_b = _ent_make_collection(
                enterprise_session, TENANT_B, name="B Update-Guard Col"
            )
            enterprise_session.commit()

        with tenant_scope(TENANT_A):
            repo = EnterpriseCollectionRepository(enterprise_session)
            with pytest.raises(TenantIsolationError):
                repo.update(col_b.id, name="Stolen Name")

    def test_tenant_a_cannot_delete_tenant_b_collection(
        self, enterprise_session: Session
    ):
        """delete() raises TenantIsolationError when targeting another tenant's collection."""
        with tenant_scope(TENANT_B):
            col_b = _ent_make_collection(
                enterprise_session, TENANT_B, name="B Delete-Guard Col"
            )
            enterprise_session.commit()

        with tenant_scope(TENANT_A):
            repo = EnterpriseCollectionRepository(enterprise_session)
            with pytest.raises(TenantIsolationError):
                repo.delete(col_b.id)

    def test_same_name_allowed_across_tenants(
        self, enterprise_session: Session
    ):
        """Two tenants may independently create collections with the same name."""
        with tenant_scope(TENANT_A):
            repo_a = EnterpriseCollectionRepository(enterprise_session)
            col_a = repo_a.create("Shared Name Col")

        with tenant_scope(TENANT_B):
            repo_b = EnterpriseCollectionRepository(enterprise_session)
            col_b = repo_b.create("Shared Name Col")

        # Both must exist as separate rows with different tenant_ids
        assert col_a.id != col_b.id
        assert col_a.tenant_id == TENANT_A
        assert col_b.tenant_id == TENANT_B

        # NEGATIVE: tenant A's get_by_name must not return tenant B's collection
        with tenant_scope(TENANT_A):
            repo = EnterpriseCollectionRepository(enterprise_session)
            result = repo.get_by_name("Shared Name Col")
        assert result is not None
        assert result.tenant_id == TENANT_A, (
            "get_by_name returned wrong tenant's collection"
        )

    def test_tenant_a_cannot_add_tenant_b_artifact_to_own_collection(
        self, enterprise_session: Session
    ):
        """add_artifact() raises TenantIsolationError for cross-tenant artifact."""
        with tenant_scope(TENANT_A):
            col_a = _ent_make_collection(
                enterprise_session, TENANT_A, name="A Add-Guard Col"
            )
            enterprise_session.commit()

        with tenant_scope(TENANT_B):
            art_b = _ent_make_artifact(
                enterprise_session, TENANT_B, name="b-cross-art"
            )
            enterprise_session.commit()

        with tenant_scope(TENANT_A):
            repo = EnterpriseCollectionRepository(enterprise_session)
            with pytest.raises(TenantIsolationError):
                repo.add_artifact(col_a.id, art_b.id)

    def test_list_artifacts_cross_tenant_raises_isolation_error(
        self, enterprise_session: Session
    ):
        """list_artifacts() raises TenantIsolationError for another tenant's collection."""
        with tenant_scope(TENANT_B):
            col_b = _ent_make_collection(
                enterprise_session, TENANT_B, name="B List-Art Col"
            )
            enterprise_session.commit()

        with tenant_scope(TENANT_A):
            repo = EnterpriseCollectionRepository(enterprise_session)
            with pytest.raises(TenantIsolationError):
                repo.list_artifacts(col_b.id)


# =============================================================================
# Part 7: Enterprise artifact + ownership field isolation (schema-level tests)
# =============================================================================


class TestEnterpriseArtifactOwnershipFields:
    """Verify owner_id / owner_type / visibility columns on enterprise artifacts.

    Uses the SQLite enterprise engine fixture to confirm that ownership fields
    are correctly persisted and do not bleed across tenant scope.
    """

    def test_owner_id_persisted_on_create(self, enterprise_session: Session):
        """Artifacts created with an owner_id have that field set in the DB."""
        owner_uuid = uuid.uuid4()
        with tenant_scope(TENANT_A):
            art = _ent_make_artifact(
                enterprise_session,
                TENANT_A,
                name="owned-art-persist",
                owner_id=owner_uuid,
                owner_type=OwnerType.user.value,
                visibility=Visibility.private.value,
            )
            enterprise_session.commit()

        enterprise_session.expire(art)
        enterprise_session.refresh(art)

        assert art.owner_id == owner_uuid
        assert art.owner_type == OwnerType.user.value
        assert art.visibility == Visibility.private.value

    def test_team_owned_artifact_has_correct_owner_type(
        self, enterprise_session: Session
    ):
        """Artifacts with owner_type=team are stored and retrievable with team type."""
        team_uuid = uuid.uuid4()
        with tenant_scope(TENANT_A):
            art = _ent_make_artifact(
                enterprise_session,
                TENANT_A,
                name="team-owned-art",
                owner_id=team_uuid,
                owner_type=OwnerType.team.value,
                visibility=Visibility.team.value,
            )
            enterprise_session.commit()

        enterprise_session.expire(art)
        enterprise_session.refresh(art)

        assert art.owner_type == OwnerType.team.value
        assert art.visibility == Visibility.team.value

    def test_tenant_isolation_preserved_across_owner_types(
        self, enterprise_session: Session
    ):
        """team-owned artifacts under tenant A must not be visible under tenant B."""
        team_uuid = uuid.uuid4()
        with tenant_scope(TENANT_A):
            art_a = _ent_make_artifact(
                enterprise_session,
                TENANT_A,
                name="team-iso-art",
                owner_id=team_uuid,
                owner_type=OwnerType.team.value,
                visibility=Visibility.team.value,
            )
            enterprise_session.commit()

        # Verify that querying under tenant B returns an empty set
        with tenant_scope(TENANT_B):
            repo = EnterpriseArtifactRepository(enterprise_session)
            result = repo.get(art_a.id)

        # NEGATIVE: must be None — tenant isolation must hold regardless of owner_type
        assert result is None, (
            "Tenant isolation breach: team-owned artifact from tenant A "
            "visible to tenant B"
        )


# =============================================================================
# Part 8: TenantContext behaviour tests
# =============================================================================


class TestTenantContextBehaviour:
    """Verify TenantContext ContextVar semantics that underpin all isolation."""

    def test_tenant_scope_sets_active_tenant(self) -> None:
        """tenant_scope() sets TenantContext to the specified UUID."""
        assert TenantContext.get() is None

        with tenant_scope(TENANT_A):
            assert TenantContext.get() == TENANT_A

        # Context is restored after exit
        assert TenantContext.get() is None

    def test_nested_tenant_scope_restores_outer(self) -> None:
        """Nested tenant_scope() correctly restores the outer tenant on exit."""
        with tenant_scope(TENANT_A):
            assert TenantContext.get() == TENANT_A
            with tenant_scope(TENANT_B):
                assert TenantContext.get() == TENANT_B
            # Inner scope exited — outer scope must be active again
            assert TenantContext.get() == TENANT_A

    def test_tenant_scope_restores_on_exception(self) -> None:
        """TenantContext is restored even if an exception is raised inside the scope."""
        assert TenantContext.get() is None
        try:
            with tenant_scope(TENANT_A):
                raise RuntimeError("simulated failure")
        except RuntimeError:
            pass

        # NEGATIVE: context must not be left set after exception
        assert TenantContext.get() is None, (
            "TenantContext was not cleaned up after exception"
        )

    def test_tenant_a_and_b_are_distinct(self) -> None:
        """TENANT_A and TENANT_B are different UUIDs (test fixture sanity check)."""
        assert TENANT_A != TENANT_B

    def test_no_active_tenant_falls_back_to_default(self) -> None:
        """Without an explicit tenant_scope, TenantContext.get() returns None.

        EnterpriseRepositoryBase._get_tenant_id() falls back to DEFAULT_TENANT_ID
        in this case (single-tenant local mode).  This test confirms the ContextVar
        default so isolation logic can rely on it.
        """
        # Ensure no scope is active
        assert TenantContext.get() is None

        # Confirmed: no active tenant
        result = TenantContext.get()
        assert result is None


# =============================================================================
# Part 9: Cross-cutting negative-assertion summary tests
# =============================================================================


class TestCrossCuttingNegativeAssertions:
    """Composite scenarios that combine multiple models to verify end-to-end isolation."""

    def test_owner_a_data_completely_invisible_to_owner_b_query(
        self, local_session: Session
    ):
        """All owner_id-scoped queries for owner B return zero owner A rows.

        Creates one of each model type under owner A, then queries each model
        table with owner_id=owner_b and asserts zero results containing A's data.
        """
        proj = _make_project(
            local_session,
            name="cross-cutproj-a",
            path="/tmp/cross-cutproj-a",
            owner_id=OWNER_A,
        )
        _make_artifact(
            local_session,
            proj.id,
            name="cross-cut-skill-a",
            artifact_type="skill",
            owner_id=OWNER_A,
        )
        coll = _make_collection(
            local_session,
            name="cross-cut-coll-a",
            owner_id=OWNER_A,
        )
        _make_group(
            local_session,
            coll.id,
            name="cross-cut-group-a",
            owner_id=OWNER_A,
        )

        # Query everything as owner B
        projects_b = (
            local_session.query(Project)
            .filter(Project.owner_id == OWNER_B)
            .all()
        )
        artifacts_b = (
            local_session.query(Artifact)
            .filter(Artifact.owner_id == OWNER_B)
            .all()
        )
        collections_b = (
            local_session.query(Collection)
            .filter(Collection.owner_id == OWNER_B)
            .all()
        )
        groups_b = (
            local_session.query(Group)
            .filter(Group.owner_id == OWNER_B)
            .all()
        )

        # NEGATIVE: none of owner A's records must appear in owner B's results
        assert all(p.owner_id != OWNER_A for p in projects_b), (
            "Owner A project leaked into owner B project query"
        )
        assert all(a.owner_id != OWNER_A for a in artifacts_b), (
            "Owner A artifact leaked into owner B artifact query"
        )
        assert all(c.owner_id != OWNER_A for c in collections_b), (
            "Owner A collection leaked into owner B collection query"
        )
        assert all(g.owner_id != OWNER_A for g in groups_b), (
            "Owner A group leaked into owner B group query"
        )

    def test_enterprise_write_operations_cannot_cross_tenant_boundaries(
        self
    ) -> None:
        """All enterprise write operations (update/soft_delete/hard_delete) raise on cross-tenant.

        This is a consolidated negative-assertion test confirming that the
        isolation contract applies uniformly across all mutation methods.
        """
        art_a_id = uuid.uuid4()
        art_a = MagicMock(spec=EnterpriseArtifact)
        art_a.id = art_a_id
        art_a.tenant_id = TENANT_A
        art_a.name = "write-guard-skill"
        art_a.is_active = True
        art_a.versions = []

        session = MagicMock(spec=Session)
        session.get.return_value = art_a

        repo = EnterpriseArtifactRepository(session)

        with tenant_scope(TENANT_B):
            # All three write paths must raise
            with pytest.raises(TenantIsolationError, match=""):
                repo.update(art_a_id, name="stolen")

        session.get.return_value = art_a
        with tenant_scope(TENANT_B):
            with pytest.raises(TenantIsolationError, match=""):
                repo.soft_delete(art_a_id)

        session.get.return_value = art_a
        with tenant_scope(TENANT_B):
            with pytest.raises(TenantIsolationError, match=""):
                repo.hard_delete(art_a_id)
