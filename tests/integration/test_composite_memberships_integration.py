"""Integration tests for composite artifact FK constraints, cascades, and UUID resolution.

This module exercises the real database layer (no mocks) to verify:
- FK constraint enforcement for CompositeMembership rows
- Cascading deletes when child artifacts or composite artifacts are deleted
- End-to-end type:name -> UUID resolution via CompositeService
- Migration round-trip: tables present after upgrade, absent after downgrade

Design notes
------------
- FK tests use a bare SQLAlchemy session (``Base.metadata.create_all``) with
  FK enforcement enabled via the SQLite PRAGMA so that IntegrityError is raised
  for bad inserts.
- Cascade tests use raw SQL DELETE (``session.execute(text("DELETE ..."))``).
  This bypasses the SQLAlchemy ORM cascade path (which tries to null-out the
  child PK when the FK references a non-PK column — see the AmbiguousForeignKeysError
  note in CompositeMembership's docstring) and lets SQLite's native CASCADE
  trigger instead.
- Service/repo tests patch ``skillmeat.cache.migrations.run_migrations`` to a
  no-op, following the pattern established in ``tests/test_composite_memberships.py``.
  The repository constructor still calls ``create_tables`` (``Base.metadata.create_all``)
  after the patched no-op, so all ORM tables are present.
- Migration round-trip tests rely on the full Alembic chain.  They are marked
  ``pytest.mark.slow`` so they can be skipped in fast-feedback loops.
"""

from __future__ import annotations

import uuid as uuid_lib
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy import event as sa_event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from skillmeat.cache.models import (
    Artifact,
    Base,
    CompositeArtifact,
    CompositeMembership,
    Project,
    create_db_engine,
    create_tables,
)
from skillmeat.cache.composite_repository import CompositeMembershipRepository
from skillmeat.cache.repositories import ConstraintError
from skillmeat.core.services.composite_service import (
    ArtifactNotFoundError,
    CompositeService,
)


# =============================================================================
# Helpers
# =============================================================================


def _make_project(suffix: str = "1") -> Project:
    """Return a transient Project ORM instance with unique identity."""
    return Project(
        id=f"proj-{suffix}",
        name=f"Test Project {suffix}",
        path=f"/tmp/test-project-{suffix}",
        status="active",
    )


def _make_artifact(
    project_id: str,
    artifact_type: str = "skill",
    name: str = "canvas-design",
) -> Artifact:
    """Return a transient Artifact ORM instance with a freshly-generated UUID."""
    artifact_id = f"{artifact_type}:{name}"
    return Artifact(
        id=artifact_id,
        uuid=uuid_lib.uuid4().hex,
        project_id=project_id,
        name=name,
        type=artifact_type,
    )


def _make_composite(
    collection_id: str = "col-1",
    name: str = "my-plugin",
    composite_type: str = "plugin",
) -> CompositeArtifact:
    """Return a transient CompositeArtifact ORM instance."""
    return CompositeArtifact(
        id=f"composite:{name}",
        collection_id=collection_id,
        composite_type=composite_type,
        display_name=f"My Plugin ({name})",
    )


def _seed_via_repo(
    repo: CompositeMembershipRepository,
    project_suffix: str = "seed",
    artifact_type: str = "skill",
    artifact_name: str = "canvas",
    composite_name: str = "my-plugin",
    collection_id: str = "collection-abc",
) -> tuple[str, str, str]:
    """Seed a Project, Artifact, and CompositeArtifact via the repo's engine.

    Returns (artifact_uuid, composite_id, collection_id) so callers can build
    membership records without an extra query.

    Args:
        repo: Repository whose engine owns the target database.
        project_suffix: Unique suffix for the project id.
        artifact_type: Artifact type prefix (e.g. ``"skill"``).
        artifact_name: Artifact name portion of the type:name id.
        composite_name: Name portion of the composite type:name id.
        collection_id: Collection identifier for the composite.

    Returns:
        Tuple of (artifact.uuid, composite.id, collection_id).
    """
    SessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=repo.engine
    )
    sess = SessionLocal()
    try:
        project = Project(
            id=f"proj-{project_suffix}",
            name=f"Seed Project {project_suffix}",
            path=f"/tmp/seed-{project_suffix}",
            status="active",
        )
        sess.add(project)
        sess.flush()

        artifact = Artifact(
            id=f"{artifact_type}:{artifact_name}",
            project_id=project.id,
            name=artifact_name,
            type=artifact_type,
        )
        sess.add(artifact)

        composite_id = f"composite:{composite_name}"
        existing_composite = (
            sess.query(CompositeArtifact)
            .filter(CompositeArtifact.id == composite_id)
            .first()
        )
        if existing_composite is None:
            composite = CompositeArtifact(
                id=composite_id,
                collection_id=collection_id,
                composite_type="plugin",
            )
            sess.add(composite)

        sess.commit()
        sess.refresh(artifact)
        return artifact.uuid, composite_id, collection_id
    finally:
        sess.close()


# =============================================================================
# Fixtures — bare SQLAlchemy (FK tests and cascade tests)
# =============================================================================


@pytest.fixture
def engine(tmp_path: Path):
    """Create a SQLAlchemy engine backed by a temp SQLite file.

    FK enforcement is enabled on every connection via a listener.
    All ORM tables are created via ``Base.metadata.create_all`` (no Alembic).
    """
    db_path = tmp_path / "test_fk_cascade.db"
    eng = create_db_engine(db_path)

    @sa_event.listens_for(eng, "connect")
    def _set_fk_pragma(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine) -> Generator[Session, None, None]:
    """Yield a database session.  Rolls back on teardown."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    sess = SessionLocal()
    try:
        yield sess
    finally:
        sess.rollback()
        sess.close()


@pytest.fixture
def populated_session(session: Session) -> dict:
    """Session pre-populated with one Project, one Artifact, and one Composite."""
    project = _make_project("base")
    session.add(project)
    session.flush()

    artifact = _make_artifact(project.id, "skill", "canvas-design")
    composite = _make_composite("col-base", "base-plugin")
    session.add(artifact)
    session.add(composite)
    session.commit()

    return {
        "session": session,
        "project": project,
        "artifact": artifact,
        "composite": composite,
    }


# =============================================================================
# Fixtures — repo/service (patch run_migrations to no-op)
# =============================================================================


@pytest.fixture
def repo(tmp_path: Path) -> CompositeMembershipRepository:
    """CompositeMembershipRepository wired to a fresh temp DB.

    Patches ``run_migrations`` so we do not depend on the full Alembic chain
    (which fails against a blank DB due to missing pre-001 state for some
    incremental migrations).  ``create_tables`` still runs via the constructor.
    """
    db_path = tmp_path / "test_repo.db"
    with patch("skillmeat.cache.migrations.run_migrations"):
        return CompositeMembershipRepository(db_path=db_path)


@pytest.fixture
def service(tmp_path: Path) -> CompositeService:
    """CompositeService wired to a fresh temp DB.  Same no-op migration patch."""
    db_path = tmp_path / "test_service.db"
    with patch("skillmeat.cache.migrations.run_migrations"):
        return CompositeService(db_path=db_path)


# =============================================================================
# FK Constraint Tests
# =============================================================================


class TestForeignKeyConstraints:
    """Verify that FK constraints are enforced at the SQLite layer."""

    def test_membership_with_nonexistent_child_uuid_raises(
        self, session: Session
    ) -> None:
        """Inserting a CompositeMembership that references a non-existent
        artifacts.uuid must be rejected with an IntegrityError."""
        composite = _make_composite("col-fk-1", "fk-plugin-1")
        session.add(composite)
        session.commit()

        bad_membership = CompositeMembership(
            collection_id="col-fk-1",
            composite_id=composite.id,
            child_artifact_uuid="ffffffffffffffffffffffffffffffff",  # does not exist
        )
        session.add(bad_membership)

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()

    def test_membership_with_nonexistent_composite_id_raises(
        self, session: Session
    ) -> None:
        """Inserting a CompositeMembership that references a non-existent
        composite_artifacts.id must be rejected with an IntegrityError."""
        project = _make_project("fk-2")
        session.add(project)
        session.flush()

        artifact = _make_artifact(project.id)
        session.add(artifact)
        session.commit()

        bad_membership = CompositeMembership(
            collection_id="col-fk-2",
            composite_id="composite:does-not-exist",  # no such row
            child_artifact_uuid=artifact.uuid,
        )
        session.add(bad_membership)

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()

    def test_membership_with_both_valid_references_succeeds(
        self, populated_session: dict
    ) -> None:
        """A CompositeMembership with valid FK references should persist without error."""
        sess: Session = populated_session["session"]
        artifact: Artifact = populated_session["artifact"]
        composite: CompositeArtifact = populated_session["composite"]

        membership = CompositeMembership(
            collection_id=composite.collection_id,
            composite_id=composite.id,
            child_artifact_uuid=artifact.uuid,
        )
        sess.add(membership)
        sess.commit()  # must not raise

        persisted = (
            sess.query(CompositeMembership)
            .filter(
                CompositeMembership.composite_id == composite.id,
                CompositeMembership.child_artifact_uuid == artifact.uuid,
            )
            .one_or_none()
        )
        assert persisted is not None
        assert persisted.child_artifact_uuid == artifact.uuid


# =============================================================================
# Cascading Delete Tests
# =============================================================================


class TestCascadingDeletes:
    """Verify that deleting a parent row cascades to CompositeMembership rows.

    All deletes use raw SQL (``session.execute(text(...))``) to bypass the
    SQLAlchemy ORM cascade path.  The ORM path fails when the FK references a
    non-PK column (``artifacts.uuid``) because SQLAlchemy tries to null-out
    ``child_artifact_uuid``, which is part of the composite PK.  Raw SQL lets
    SQLite's native ON DELETE CASCADE rule do the work instead.
    """

    def _insert_membership(
        self,
        session: Session,
        artifact: Artifact,
        composite: CompositeArtifact,
    ) -> None:
        """Insert a membership row via ORM and commit."""
        membership = CompositeMembership(
            collection_id=composite.collection_id,
            composite_id=composite.id,
            child_artifact_uuid=artifact.uuid,
        )
        session.add(membership)
        session.commit()

    def _membership_count(
        self,
        session: Session,
        composite_id: str,
        child_uuid: str,
    ) -> int:
        return (
            session.query(CompositeMembership)
            .filter(
                CompositeMembership.composite_id == composite_id,
                CompositeMembership.child_artifact_uuid == child_uuid,
            )
            .count()
        )

    def test_delete_child_artifact_removes_its_memberships(
        self, populated_session: dict
    ) -> None:
        """Deleting the child Artifact (via raw SQL) cascades to CompositeMembership."""
        sess: Session = populated_session["session"]
        artifact: Artifact = populated_session["artifact"]
        composite: CompositeArtifact = populated_session["composite"]

        # Capture string values before the delete so we do not access the
        # expired ORM instance after session.commit() expires the identity map.
        artifact_id_str = artifact.id
        artifact_uuid_str = artifact.uuid
        composite_id_str = composite.id

        self._insert_membership(sess, artifact, composite)
        assert self._membership_count(sess, composite_id_str, artifact_uuid_str) == 1

        # Use raw SQL to let SQLite ON DELETE CASCADE do the work
        sess.execute(
            text("DELETE FROM artifacts WHERE id = :aid"),
            {"aid": artifact_id_str},
        )
        sess.commit()

        assert self._membership_count(sess, composite_id_str, artifact_uuid_str) == 0

    def test_delete_composite_removes_its_memberships(
        self, populated_session: dict
    ) -> None:
        """Deleting the CompositeArtifact (via raw SQL) cascades to CompositeMembership."""
        sess: Session = populated_session["session"]
        artifact: Artifact = populated_session["artifact"]
        composite: CompositeArtifact = populated_session["composite"]

        # Capture string values before the delete
        artifact_uuid_str = artifact.uuid
        composite_id_str = composite.id

        self._insert_membership(sess, artifact, composite)
        assert self._membership_count(sess, composite_id_str, artifact_uuid_str) == 1

        sess.execute(
            text("DELETE FROM composite_artifacts WHERE id = :cid"),
            {"cid": composite_id_str},
        )
        sess.commit()

        assert self._membership_count(sess, composite_id_str, artifact_uuid_str) == 0

    def test_delete_one_artifact_leaves_other_memberships_intact(
        self, session: Session
    ) -> None:
        """Cascading delete for one child must not affect unrelated memberships."""
        project = _make_project("cascade-multi")
        session.add(project)
        session.flush()

        artifact_a = _make_artifact(project.id, "skill", "canvas-design")
        artifact_b = _make_artifact(project.id, "command", "git-helper")
        composite = _make_composite("col-cascade", "multi-plugin")
        session.add_all([artifact_a, artifact_b, composite])
        session.commit()

        session.add_all([
            CompositeMembership(
                collection_id=composite.collection_id,
                composite_id=composite.id,
                child_artifact_uuid=artifact_a.uuid,
            ),
            CompositeMembership(
                collection_id=composite.collection_id,
                composite_id=composite.id,
                child_artifact_uuid=artifact_b.uuid,
            ),
        ])
        session.commit()

        # Capture values before the raw SQL delete expires the ORM instances
        artifact_a_id = artifact_a.id
        artifact_a_uuid = artifact_a.uuid
        artifact_b_uuid = artifact_b.uuid
        composite_id_str = composite.id

        # Delete only artifact_a via raw SQL
        session.execute(
            text("DELETE FROM artifacts WHERE id = :aid"),
            {"aid": artifact_a_id},
        )
        session.commit()

        assert self._membership_count(session, composite_id_str, artifact_a_uuid) == 0
        assert self._membership_count(session, composite_id_str, artifact_b_uuid) == 1

    def test_delete_composite_leaves_unrelated_composite_memberships_intact(
        self, session: Session
    ) -> None:
        """Deleting one composite must not cascade into another composite's memberships."""
        project = _make_project("cascade-iso")
        session.add(project)
        session.flush()

        artifact = _make_artifact(project.id)
        composite_1 = _make_composite("col-cascade-iso", "plugin-1")
        composite_2 = _make_composite("col-cascade-iso", "plugin-2")
        session.add_all([artifact, composite_1, composite_2])
        session.commit()

        # Same child in both composites
        session.add_all([
            CompositeMembership(
                collection_id="col-cascade-iso",
                composite_id=composite_1.id,
                child_artifact_uuid=artifact.uuid,
            ),
            CompositeMembership(
                collection_id="col-cascade-iso",
                composite_id=composite_2.id,
                child_artifact_uuid=artifact.uuid,
            ),
        ])
        session.commit()

        # Capture string values before the raw SQL delete expires ORM instances
        artifact_uuid_str = artifact.uuid
        composite_1_id = composite_1.id
        composite_2_id = composite_2.id

        # Delete composite_1 via raw SQL
        session.execute(
            text("DELETE FROM composite_artifacts WHERE id = :cid"),
            {"cid": composite_1_id},
        )
        session.commit()

        # composite_1's membership gone
        gone = (
            session.query(CompositeMembership)
            .filter(CompositeMembership.composite_id == composite_1_id)
            .all()
        )
        # composite_2's membership intact
        still_there = (
            session.query(CompositeMembership)
            .filter(CompositeMembership.composite_id == composite_2_id)
            .all()
        )
        assert gone == []
        assert len(still_there) == 1
        assert still_there[0].child_artifact_uuid == artifact_uuid_str


# =============================================================================
# type:name -> UUID Resolution Tests (via CompositeService)
# =============================================================================


class TestTypeNameResolution:
    """End-to-end tests exercising the type:name -> UUID resolution path."""

    def test_add_composite_member_resolves_uuid_correctly(
        self, service: CompositeService
    ) -> None:
        """add_composite_member should resolve child type:name to UUID and
        persist a CompositeMembership row whose child_artifact_uuid matches
        the Artifact's actual uuid column."""
        artifact_uuid, composite_id, collection_id = _seed_via_repo(
            service._repo,
            project_suffix="resolve-e2e",
            artifact_type="skill",
            artifact_name="canvas-design",
            composite_name="resolve-plugin",
            collection_id="col-resolve",
        )

        record = service.add_composite_member(
            collection_id=collection_id,
            composite_id=composite_id,
            child_artifact_id="skill:canvas-design",
        )

        assert record["child_artifact_uuid"] == artifact_uuid
        assert record["composite_id"] == composite_id
        assert record["collection_id"] == collection_id

    def test_add_composite_member_membership_queryable_via_repo(
        self, service: CompositeService
    ) -> None:
        """The membership created by add_composite_member must be retrievable
        via get_children_of."""
        artifact_uuid, composite_id, collection_id = _seed_via_repo(
            service._repo,
            project_suffix="query-e2e",
            artifact_name="canvas-design",
            composite_name="query-plugin",
            collection_id="col-query",
        )

        service.add_composite_member(
            collection_id=collection_id,
            composite_id=composite_id,
            child_artifact_id="skill:canvas-design",
        )

        children = service._repo.get_children_of(composite_id, collection_id)
        assert len(children) == 1
        assert children[0]["child_artifact_uuid"] == artifact_uuid

    def test_add_composite_member_unknown_artifact_raises(
        self, service: CompositeService
    ) -> None:
        """Attempting to add a child that does not exist in the artifacts table
        must raise ArtifactNotFoundError."""
        # Seed a composite so the composite FK side is satisfiable
        _seed_via_repo(
            service._repo,
            project_suffix="not-found",
            composite_name="nf-plugin",
            collection_id="col-nf",
        )

        with pytest.raises(ArtifactNotFoundError) as exc_info:
            service.add_composite_member(
                collection_id="col-nf",
                composite_id="composite:nf-plugin",
                child_artifact_id="skill:i-do-not-exist",
            )

        assert "skill:i-do-not-exist" in str(exc_info.value)

    def test_add_composite_member_duplicate_raises_constraint_error(
        self, service: CompositeService
    ) -> None:
        """Adding the same (collection_id, composite_id, child_artifact_uuid)
        triplet twice should raise ConstraintError on the second call."""
        artifact_uuid, composite_id, collection_id = _seed_via_repo(
            service._repo,
            project_suffix="dup-e2e",
            composite_name="dup-plugin",
            collection_id="col-dup",
        )

        service.add_composite_member(
            collection_id=collection_id,
            composite_id=composite_id,
            child_artifact_id="skill:canvas",
        )

        with pytest.raises(ConstraintError):
            service.add_composite_member(
                collection_id=collection_id,
                composite_id=composite_id,
                child_artifact_id="skill:canvas",
            )

    def test_get_associations_returns_correct_parents_and_children(
        self, service: CompositeService
    ) -> None:
        """get_associations returns children when called on a composite
        and parents when called on the child artifact."""
        artifact_uuid, composite_id, collection_id = _seed_via_repo(
            service._repo,
            project_suffix="assoc-e2e",
            composite_name="assoc-plugin",
            collection_id="col-assoc",
        )

        service.add_composite_member(
            collection_id=collection_id,
            composite_id=composite_id,
            child_artifact_id="skill:canvas",
        )

        # From the composite's perspective
        assoc_composite = service.get_associations(composite_id, collection_id)
        assert len(assoc_composite["children"]) == 1
        assert assoc_composite["children"][0]["child_artifact_uuid"] == artifact_uuid
        assert assoc_composite["parents"] == []

        # From the child artifact's perspective
        assoc_child = service.get_associations("skill:canvas", collection_id)
        assert len(assoc_child["parents"]) == 1
        assert assoc_child["parents"][0]["composite_id"] == composite_id
        assert assoc_child["children"] == []


# =============================================================================
# Repository-Level FK Violation (via CompositeMembershipRepository)
# =============================================================================


class TestRepositoryConstraintError:
    """Verify that CompositeMembershipRepository re-raises IntegrityError as
    ConstraintError (domain exception) when FK constraints are violated."""

    def test_create_membership_unknown_composite_raises_constraint_error(
        self, repo: CompositeMembershipRepository
    ) -> None:
        """create_membership with an unknown composite_id must raise ConstraintError."""
        artifact_uuid, _composite_id, collection_id = _seed_via_repo(
            repo, project_suffix="repo-fk-1"
        )

        with pytest.raises(ConstraintError):
            repo.create_membership(
                collection_id=collection_id,
                composite_id="composite:totally-unknown",
                child_artifact_uuid=artifact_uuid,
            )

    def test_create_membership_unknown_child_uuid_raises_constraint_error(
        self, repo: CompositeMembershipRepository
    ) -> None:
        """create_membership with an unknown child_artifact_uuid must raise ConstraintError."""
        _artifact_uuid, composite_id, collection_id = _seed_via_repo(
            repo, project_suffix="repo-fk-2"
        )

        with pytest.raises(ConstraintError):
            repo.create_membership(
                collection_id=collection_id,
                composite_id=composite_id,
                child_artifact_uuid="aaaabbbbccccddddaaaabbbbccccdddd",  # ghost UUID
            )


# =============================================================================
# Migration Round-Trip Tests
# =============================================================================


@pytest.mark.slow
class TestMigrationRoundTrip:
    """Verify that Alembic migrations create and drop the composite tables correctly.

    Marked ``slow`` because these run the full Alembic upgrade from revision 001
    to head, which touches all incremental migrations.  The migration chain
    requires a production-like database state (pre-seeded with the initial
    schema) and therefore these tests use a ``create_tables``-seeded DB that is
    then stamped to the revision just before the composite tables migration,
    allowing a selective upgrade/downgrade of only the composite tables.
    """

    def _prepare_stamped_db(self, db_path: Path) -> None:
        """Create the base schema and stamp the DB at the revision just before
        the composite artifact tables migration.

        Steps:
        1. Create all ORM tables via ``create_tables`` (full schema including
           composite tables — Base.metadata.create_all is schema-complete).
        2. Replace the three join tables (collection_artifacts, group_artifacts,
           artifact_tags) with their pre-UUID schemas so that the UUID migration
           chain (20260219_1000 through 20260219_1300) can run against them as
           intended.  The current ORM schema already has artifact_uuid as the
           PK column; those migrations expect artifact_id instead.
        3. Drop the composite tables that Alembic will re-create, so that the
           migration's ``CREATE TABLE`` statements do not conflict with
           pre-existing tables.
        4. Stamp Alembic at ``20260218_1000_add_artifact_uuid_column`` — the
           revision immediately before the composite tables migration — so that
           a subsequent ``upgrade("head")`` applies the full migration chain
           starting with ``20260218_1100_add_composite_artifact_tables``.

        This simulates a production DB that has all base tables with the
        pre-UUID join-table schema, waiting for the migration chain to add
        composite tables and migrate join tables to UUID-keyed PKs.
        """
        from alembic import command
        from sqlalchemy import create_engine
        from skillmeat.cache.migrations import get_alembic_config

        # Step 1: create the full ORM schema
        create_tables(db_path)

        eng = create_engine(f"sqlite:///{db_path}")
        with eng.connect() as conn:
            # ------------------------------------------------------------------
            # Step 2: Replace join tables with pre-UUID schemas.
            #
            # The ORM (Base.metadata.create_all) creates these tables with
            # artifact_uuid as the PK component.  The migration chain starting
            # at 20260219_1000 expects artifact_id (the old string PK) to be
            # present so it can rename the table, join against artifacts.id, and
            # backfill the new artifact_uuid column.  We drop and recreate each
            # table using the legacy schema that the migrations expect.
            #
            # All three tables are empty at this point (no data was inserted),
            # so no rows are lost by the drop-and-recreate.
            # ------------------------------------------------------------------

            # collection_artifacts: old schema uses artifact_id (not artifact_uuid)
            conn.execute(text("DROP INDEX IF EXISTS idx_collection_artifacts_collection_id"))
            conn.execute(text("DROP INDEX IF EXISTS idx_collection_artifacts_artifact_uuid"))
            conn.execute(text("DROP INDEX IF EXISTS idx_collection_artifacts_added_at"))
            conn.execute(text("DROP INDEX IF EXISTS idx_collection_artifacts_synced_at"))
            conn.execute(text("DROP INDEX IF EXISTS idx_collection_artifacts_tools_json"))
            conn.execute(text("DROP TABLE IF EXISTS collection_artifacts"))
            conn.execute(text(
                """
                CREATE TABLE collection_artifacts (
                    collection_id    VARCHAR NOT NULL,
                    artifact_id      VARCHAR NOT NULL,
                    added_at         DATETIME NOT NULL,
                    description      TEXT,
                    author           VARCHAR,
                    license          VARCHAR,
                    tags_json        TEXT,
                    version          VARCHAR,
                    source           VARCHAR,
                    origin           VARCHAR,
                    origin_source    VARCHAR,
                    resolved_sha     VARCHAR(64),
                    resolved_version VARCHAR,
                    synced_at        DATETIME,
                    tools_json       TEXT,
                    deployments_json TEXT,
                    PRIMARY KEY (collection_id, artifact_id),
                    FOREIGN KEY (collection_id)
                        REFERENCES collections (id)
                        ON DELETE CASCADE
                )
                """
            ))
            conn.execute(text(
                "CREATE INDEX idx_collection_artifacts_collection_id "
                "ON collection_artifacts (collection_id)"
            ))
            conn.execute(text(
                "CREATE INDEX idx_collection_artifacts_artifact_id "
                "ON collection_artifacts (artifact_id)"
            ))
            conn.execute(text(
                "CREATE INDEX idx_collection_artifacts_added_at "
                "ON collection_artifacts (added_at)"
            ))
            conn.execute(text(
                "CREATE INDEX idx_collection_artifacts_synced_at "
                "ON collection_artifacts (synced_at)"
            ))
            conn.execute(text(
                "CREATE INDEX idx_collection_artifacts_tools_json "
                "ON collection_artifacts (tools_json)"
            ))

            # group_artifacts: old schema uses artifact_id (not artifact_uuid)
            conn.execute(text("DROP INDEX IF EXISTS idx_group_artifacts_group_id"))
            conn.execute(text("DROP INDEX IF EXISTS idx_group_artifacts_artifact_uuid"))
            conn.execute(text("DROP INDEX IF EXISTS idx_group_artifacts_group_position"))
            conn.execute(text("DROP INDEX IF EXISTS idx_group_artifacts_added_at"))
            conn.execute(text("DROP TABLE IF EXISTS group_artifacts"))
            conn.execute(text(
                """
                CREATE TABLE group_artifacts (
                    group_id    VARCHAR NOT NULL,
                    artifact_id VARCHAR NOT NULL,
                    position    INTEGER NOT NULL DEFAULT 0,
                    added_at    DATETIME NOT NULL,
                    PRIMARY KEY (group_id, artifact_id),
                    FOREIGN KEY (group_id)
                        REFERENCES groups (id)
                        ON DELETE CASCADE,
                    CONSTRAINT check_group_artifact_position
                        CHECK (position >= 0)
                )
                """
            ))
            conn.execute(text(
                "CREATE INDEX idx_group_artifacts_group_id "
                "ON group_artifacts (group_id)"
            ))
            conn.execute(text(
                "CREATE INDEX idx_group_artifacts_artifact_id "
                "ON group_artifacts (artifact_id)"
            ))
            conn.execute(text(
                "CREATE INDEX idx_group_artifacts_group_position "
                "ON group_artifacts (group_id, position)"
            ))
            conn.execute(text(
                "CREATE INDEX idx_group_artifacts_added_at "
                "ON group_artifacts (added_at)"
            ))

            # artifact_tags: old schema uses artifact_id (not artifact_uuid)
            conn.execute(text("DROP INDEX IF EXISTS idx_artifact_tags_artifact_uuid"))
            conn.execute(text("DROP INDEX IF EXISTS idx_artifact_tags_tag_id"))
            conn.execute(text("DROP INDEX IF EXISTS idx_artifact_tags_created_at"))
            conn.execute(text("DROP TABLE IF EXISTS artifact_tags"))
            conn.execute(text(
                """
                CREATE TABLE artifact_tags (
                    artifact_id VARCHAR NOT NULL,
                    tag_id      VARCHAR NOT NULL,
                    created_at  DATETIME NOT NULL,
                    PRIMARY KEY (artifact_id, tag_id),
                    FOREIGN KEY (tag_id)
                        REFERENCES tags (id)
                        ON DELETE CASCADE
                )
                """
            ))
            conn.execute(text(
                "CREATE INDEX idx_artifact_tags_artifact_id "
                "ON artifact_tags (artifact_id)"
            ))
            conn.execute(text(
                "CREATE INDEX idx_artifact_tags_tag_id "
                "ON artifact_tags (tag_id)"
            ))
            conn.execute(text(
                "CREATE INDEX idx_artifact_tags_created_at "
                "ON artifact_tags (created_at)"
            ))

            # ------------------------------------------------------------------
            # Step 3: Drop composite tables so the migration can re-create them.
            # Drop child table first (FK dependency order).
            # ------------------------------------------------------------------
            conn.execute(text("DROP TABLE IF EXISTS composite_memberships"))
            conn.execute(text("DROP TABLE IF EXISTS composite_artifacts"))

        eng.dispose()

        # Step 4: stamp Alembic at the revision just before composite tables
        alembic_cfg = get_alembic_config(db_path)
        command.stamp(
            alembic_cfg,
            "20260218_1000_add_artifact_uuid_column",
        )

    def test_composite_tables_exist_after_upgrade(self, tmp_path: Path) -> None:
        """Running a targeted upgrade creates composite_artifacts and
        composite_memberships tables."""
        from skillmeat.cache.migrations import run_migrations

        db_path = tmp_path / "migration_upgrade_test.db"
        self._prepare_stamped_db(db_path)
        run_migrations(db_path)

        engine = create_engine(f"sqlite:///{db_path}")
        table_names = inspect(engine).get_table_names()
        engine.dispose()

        assert "composite_artifacts" in table_names, (
            "composite_artifacts table missing after migration upgrade"
        )
        assert "composite_memberships" in table_names, (
            "composite_memberships table missing after migration upgrade"
        )

    def test_composite_tables_absent_after_downgrade(self, tmp_path: Path) -> None:
        """Rolling back to before the composite table migration removes
        composite_artifacts and composite_memberships."""
        from skillmeat.cache.migrations import run_migrations, downgrade_migration

        db_path = tmp_path / "migration_downgrade_test.db"
        self._prepare_stamped_db(db_path)
        run_migrations(db_path)

        # Downgrade to the revision just before composite tables were added.
        # We target the specific revision rather than "-1" because the current
        # HEAD is several revisions ahead of the composite tables migration;
        # "-1" from HEAD would only remove the most recent migration, not the
        # composite tables migration.
        downgrade_migration(
            db_path, revision="20260218_1000_add_artifact_uuid_column"
        )

        engine = create_engine(f"sqlite:///{db_path}")
        table_names = inspect(engine).get_table_names()
        engine.dispose()

        assert "composite_memberships" not in table_names, (
            "composite_memberships should be absent after downgrade"
        )
        assert "composite_artifacts" not in table_names, (
            "composite_artifacts should be absent after downgrade"
        )

    def test_composite_tables_recreated_after_upgrade_downgrade_upgrade(
        self, tmp_path: Path
    ) -> None:
        """Upgrade -> downgrade -> upgrade cycle leaves the tables present."""
        from skillmeat.cache.migrations import run_migrations, downgrade_migration

        db_path = tmp_path / "migration_roundtrip_test.db"
        self._prepare_stamped_db(db_path)

        run_migrations(db_path)
        downgrade_migration(
            db_path, revision="20260218_1000_add_artifact_uuid_column"
        )
        run_migrations(db_path)  # re-apply

        engine = create_engine(f"sqlite:///{db_path}")
        table_names = inspect(engine).get_table_names()
        engine.dispose()

        assert "composite_artifacts" in table_names
        assert "composite_memberships" in table_names
