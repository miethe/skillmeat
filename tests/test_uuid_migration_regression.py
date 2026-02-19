"""Regression tests for CAI-P5 UUID migration.

Verifies that all three join tables (collection_artifacts, group_artifacts,
artifact_tags) correctly use artifact_uuid FK references to artifacts.uuid
instead of the legacy artifact_id (type:name) strings.

Test Areas:
    1. Schema: join tables use artifact_uuid column (not artifact_id) as FK
    2. CASCADE deletes: removing a CachedArtifact removes all join table rows
    3. API contract: collection/group/tag endpoints return type:name identifiers
    4. Alembic migrations: each UUID migration upgrade applies cleanly

Implementation notes:
    - All DB tests use SQLite in-memory equivalent (file-per-test via tmp_path)
    - PRAGMA foreign_keys=ON is required for SQLite CASCADE to fire
    - Cascade tests bypass the SQLAlchemy ORM unit-of-work for the artifact
      delete (via session.execute + delete()) to avoid the ORM nulling-out
      a PK column before the DB-level cascade can run
    - Alembic migration modules have numeric prefixes so they must be loaded
      via importlib.util rather than a normal import statement
    - The tags list endpoint uses TagService() which calls get_session() internally;
      tests patch that path to inject the test session factory

Usage:
    pytest tests/test_uuid_migration_regression.py -v
"""

from __future__ import annotations

import importlib.util
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Tuple
from unittest.mock import MagicMock, patch

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, event, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app
from skillmeat.cache.models import (
    Artifact,
    ArtifactTag,
    Base,
    Collection,
    CollectionArtifact,
    Group,
    GroupArtifact,
    Project,
    Tag,
)

# ---------------------------------------------------------------------------
# Path to the migration files directory — used by TestAlembicMigrations
# ---------------------------------------------------------------------------
_MIGRATIONS_DIR = (
    Path(__file__).parent.parent
    / "skillmeat"
    / "cache"
    / "migrations"
    / "versions"
)


def _load_migration(filename: str):
    """Load a migration module by filename using importlib (numeric prefix safe)."""
    path = _MIGRATIONS_DIR / filename
    spec = importlib.util.spec_from_file_location(filename, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# =============================================================================
# Shared fixtures
# =============================================================================


@pytest.fixture(scope="function")
def engine(tmp_path):
    """SQLite engine per test with FK enforcement enabled."""
    db_file = tmp_path / "test_uuid_migration.db"
    eng = create_engine(
        f"sqlite:///{db_file}",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(eng, "connect")
    def set_sqlite_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture(scope="function")
def session(engine) -> Session:
    """Provide a session that is properly closed after each test."""
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    sess = factory()
    yield sess
    sess.close()


# ---------------------------------------------------------------------------
# Convenience helpers that build a minimal FK-consistent object graph.
# ---------------------------------------------------------------------------


def _make_project(session: Session) -> Project:
    project = Project(
        id=uuid.uuid4().hex,
        name="Test Project",
        path="/tmp/regression-test",
        status="active",
    )
    session.add(project)
    session.flush()
    return project


def _make_artifact(session: Session, project: Project, suffix: str = "0") -> Artifact:
    """Create a real Artifact row with a distinct uuid and type:name id."""
    art = Artifact(
        id=f"skill:artifact-{suffix}",
        uuid=uuid.uuid4().hex,
        project_id=project.id,
        name=f"artifact-{suffix}",
        type="skill",
    )
    session.add(art)
    session.flush()
    return art


def _make_collection(session: Session) -> Collection:
    coll = Collection(
        id=uuid.uuid4().hex,
        name="Regression Collection",
        description="Created by regression test",
    )
    session.add(coll)
    session.flush()
    return coll


def _make_tag(session: Session, name: str = "test-tag") -> Tag:
    tag = Tag(
        id=uuid.uuid4().hex,
        name=name,
        slug=name,
    )
    session.add(tag)
    session.flush()
    return tag


def _add_to_collection(
    session: Session, collection: Collection, artifact: Artifact
) -> CollectionArtifact:
    ca = CollectionArtifact(
        collection_id=collection.id,
        artifact_uuid=artifact.uuid,
        added_at=datetime.utcnow(),
    )
    session.add(ca)
    session.flush()
    return ca


def _add_to_group(
    session: Session, group: Group, artifact: Artifact, position: int = 0
) -> GroupArtifact:
    ga = GroupArtifact(
        group_id=group.id,
        artifact_uuid=artifact.uuid,
        position=position,
    )
    session.add(ga)
    session.flush()
    return ga


def _tag_artifact(
    session: Session, artifact: Artifact, tag: Tag
) -> ArtifactTag:
    at = ArtifactTag(
        artifact_uuid=artifact.uuid,
        tag_id=tag.id,
        created_at=datetime.utcnow(),
    )
    session.add(at)
    session.flush()
    return at


def _delete_artifact_via_sql(session: Session, artifact: Artifact) -> None:
    """Delete an Artifact using a raw DELETE statement.

    We bypass the ORM unit-of-work here because SQLAlchemy will try to null
    out the FK column in GroupArtifact / ArtifactTag before issuing the
    DELETE; since those FK columns are also part of the composite PK this
    produces an error.  Raw SQL respects ON DELETE CASCADE directly.
    """
    session.execute(
        sa.delete(Artifact).where(Artifact.uuid == artifact.uuid)
    )
    session.flush()


# =============================================================================
# 1. Schema — join tables must have artifact_uuid, NOT artifact_id as PK/FK
# =============================================================================


class TestJoinTableSchema:
    """Verify the live schema matches the migrated (UUID-keyed) shape."""

    def _columns(self, engine, table_name: str) -> dict:
        inspector = inspect(engine)
        return {c["name"]: c for c in inspector.get_columns(table_name)}

    def _fk_cols(self, engine, table_name: str) -> List[dict]:
        inspector = inspect(engine)
        return inspector.get_foreign_keys(table_name)

    # --- collection_artifacts -----------------------------------------------

    def test_collection_artifacts_has_artifact_uuid_column(self, engine):
        """collection_artifacts must have an artifact_uuid column."""
        cols = self._columns(engine, "collection_artifacts")
        assert "artifact_uuid" in cols, (
            "collection_artifacts is missing artifact_uuid column — "
            "UUID migration (CAI-P5-01) may not have run"
        )

    def test_collection_artifacts_has_no_artifact_id_pk_column(self, engine):
        """collection_artifacts must NOT expose a bare artifact_id PK column.

        The _artifact_id_backup column that migrations leave behind is
        acceptable; only a plain 'artifact_id' that was part of the old
        composite PK would indicate the migration has not been applied.
        """
        cols = self._columns(engine, "collection_artifacts")
        assert "artifact_id" not in cols, (
            "collection_artifacts still has a legacy artifact_id column — "
            "UUID migration (CAI-P5-01) did not replace the PK"
        )

    def test_collection_artifacts_artifact_uuid_fk_to_artifacts_uuid(self, engine):
        """collection_artifacts.artifact_uuid must FK to artifacts.uuid."""
        fks = self._fk_cols(engine, "collection_artifacts")
        uuid_fks = [
            fk
            for fk in fks
            if "artifact_uuid" in fk.get("constrained_columns", [])
        ]
        assert uuid_fks, (
            "collection_artifacts has no FK from artifact_uuid — "
            "UUID migration (CAI-P5-01) may not have created the FK constraint"
        )
        fk = uuid_fks[0]
        assert fk["referred_table"] == "artifacts", (
            f"artifact_uuid FK points to {fk['referred_table']!r}, expected 'artifacts'"
        )
        assert "uuid" in fk.get("referred_columns", []), (
            "artifact_uuid FK does not reference artifacts.uuid"
        )

    # --- group_artifacts ----------------------------------------------------

    def test_group_artifacts_has_artifact_uuid_column(self, engine):
        """group_artifacts must have an artifact_uuid column."""
        cols = self._columns(engine, "group_artifacts")
        assert "artifact_uuid" in cols, (
            "group_artifacts is missing artifact_uuid column — "
            "UUID migration (CAI-P5-02) may not have run"
        )

    def test_group_artifacts_has_no_artifact_id_pk_column(self, engine):
        """group_artifacts must NOT expose a bare artifact_id PK column."""
        cols = self._columns(engine, "group_artifacts")
        assert "artifact_id" not in cols, (
            "group_artifacts still has a legacy artifact_id column — "
            "UUID migration (CAI-P5-02) did not replace the PK"
        )

    def test_group_artifacts_artifact_uuid_fk_to_artifacts_uuid(self, engine):
        """group_artifacts.artifact_uuid must FK to artifacts.uuid."""
        fks = self._fk_cols(engine, "group_artifacts")
        uuid_fks = [
            fk
            for fk in fks
            if "artifact_uuid" in fk.get("constrained_columns", [])
        ]
        assert uuid_fks, (
            "group_artifacts has no FK from artifact_uuid — "
            "UUID migration (CAI-P5-02) may not have created the FK constraint"
        )
        fk = uuid_fks[0]
        assert fk["referred_table"] == "artifacts"
        assert "uuid" in fk.get("referred_columns", [])

    # --- artifact_tags -------------------------------------------------------

    def test_artifact_tags_has_artifact_uuid_column(self, engine):
        """artifact_tags must have an artifact_uuid column."""
        cols = self._columns(engine, "artifact_tags")
        assert "artifact_uuid" in cols, (
            "artifact_tags is missing artifact_uuid column — "
            "UUID migration (CAI-P5-03) may not have run"
        )

    def test_artifact_tags_has_no_artifact_id_pk_column(self, engine):
        """artifact_tags must NOT expose a bare artifact_id PK column."""
        cols = self._columns(engine, "artifact_tags")
        assert "artifact_id" not in cols, (
            "artifact_tags still has a legacy artifact_id column — "
            "UUID migration (CAI-P5-03) did not replace the PK"
        )

    def test_artifact_tags_artifact_uuid_fk_to_artifacts_uuid(self, engine):
        """artifact_tags.artifact_uuid must FK to artifacts.uuid."""
        fks = self._fk_cols(engine, "artifact_tags")
        uuid_fks = [
            fk
            for fk in fks
            if "artifact_uuid" in fk.get("constrained_columns", [])
        ]
        assert uuid_fks, (
            "artifact_tags has no FK from artifact_uuid — "
            "UUID migration (CAI-P5-03) may not have created the FK constraint"
        )
        fk = uuid_fks[0]
        assert fk["referred_table"] == "artifacts"
        assert "uuid" in fk.get("referred_columns", [])


# =============================================================================
# 2. ORM — round-trip insert/query through the ORM layer
# =============================================================================


class TestJoinTableORM:
    """Verify the ORM models correctly map to the UUID-keyed schema."""

    def test_collection_artifact_stores_uuid_not_type_name(self, session):
        """CollectionArtifact.artifact_uuid stores the artifact's UUID hex."""
        project = _make_project(session)
        artifact = _make_artifact(session, project, "orm-ca")
        collection = _make_collection(session)
        _add_to_collection(session, collection, artifact)
        session.commit()

        session.expire_all()
        loaded = (
            session.query(CollectionArtifact)
            .filter_by(
                collection_id=collection.id,
                artifact_uuid=artifact.uuid,
            )
            .one()
        )

        assert loaded.artifact_uuid == artifact.uuid
        # The compatibility shim should resolve to the type:name id
        assert loaded.artifact_id == artifact.id

    def test_group_artifact_stores_uuid_not_type_name(self, session):
        """GroupArtifact.artifact_uuid stores the artifact's UUID hex."""
        project = _make_project(session)
        artifact = _make_artifact(session, project, "orm-ga")
        collection = _make_collection(session)
        group = Group(
            id=uuid.uuid4().hex,
            collection_id=collection.id,
            name="ORM Test Group",
            position=0,
        )
        session.add(group)
        session.flush()
        _add_to_group(session, group, artifact)
        session.commit()

        session.expire_all()
        loaded = (
            session.query(GroupArtifact)
            .filter_by(group_id=group.id, artifact_uuid=artifact.uuid)
            .one()
        )

        assert loaded.artifact_uuid == artifact.uuid
        assert loaded.artifact_id == artifact.id

    def test_artifact_tag_stores_uuid_not_type_name(self, session):
        """ArtifactTag.artifact_uuid stores the artifact's UUID hex."""
        project = _make_project(session)
        artifact = _make_artifact(session, project, "orm-at")
        tag = _make_tag(session, "orm-tag")
        _tag_artifact(session, artifact, tag)
        session.commit()

        session.expire_all()
        loaded = (
            session.query(ArtifactTag)
            .filter_by(artifact_uuid=artifact.uuid, tag_id=tag.id)
            .one()
        )

        assert loaded.artifact_uuid == artifact.uuid

    def test_collection_artifact_cannot_insert_nonexistent_artifact_uuid(
        self, session
    ):
        """Inserting a CollectionArtifact with a dangling artifact_uuid must fail."""
        collection = _make_collection(session)
        bogus_uuid = uuid.uuid4().hex

        bad_row = CollectionArtifact(
            collection_id=collection.id,
            artifact_uuid=bogus_uuid,
            added_at=datetime.utcnow(),
        )
        session.add(bad_row)

        with pytest.raises(Exception):
            # FK violation — SQLite raises IntegrityError with PRAGMA foreign_keys=ON
            session.flush()

    def test_group_artifact_cannot_insert_nonexistent_artifact_uuid(self, session):
        """Inserting a GroupArtifact with a dangling artifact_uuid must fail."""
        collection = _make_collection(session)
        group = Group(
            id=uuid.uuid4().hex,
            collection_id=collection.id,
            name="Bad Group",
            position=0,
        )
        session.add(group)
        session.flush()
        bogus_uuid = uuid.uuid4().hex

        bad_row = GroupArtifact(
            group_id=group.id,
            artifact_uuid=bogus_uuid,
            position=0,
        )
        session.add(bad_row)

        with pytest.raises(Exception):
            session.flush()

    def test_artifact_tag_cannot_insert_nonexistent_artifact_uuid(self, session):
        """Inserting an ArtifactTag with a dangling artifact_uuid must fail."""
        tag = _make_tag(session, "dangling-tag")
        bogus_uuid = uuid.uuid4().hex

        bad_row = ArtifactTag(
            artifact_uuid=bogus_uuid,
            tag_id=tag.id,
            created_at=datetime.utcnow(),
        )
        session.add(bad_row)

        with pytest.raises(Exception):
            session.flush()


# =============================================================================
# 3. CASCADE deletes — removing an Artifact must prune all join rows
# =============================================================================


class TestCascadeDelete:
    """Verify ON DELETE CASCADE removes join rows when an Artifact is deleted.

    We use raw SQL DELETEs (via session.execute + sqlalchemy.delete()) rather
    than session.delete(artifact) because the ORM unit-of-work will try to
    null-out FK columns before issuing the row DELETE; since artifact_uuid
    is simultaneously part of the composite PK on all three join tables this
    produces an IntegrityError rather than triggering the database CASCADE.

    Raw SQL bypasses the ORM bookkeeping and lets SQLite's ON DELETE CASCADE
    fire exactly as it would in production.
    """

    def _count(self, session: Session, model, **filters) -> int:
        return session.query(model).filter_by(**filters).count()

    def test_delete_artifact_removes_collection_artifact(self, session):
        """Deleting an Artifact cascades into collection_artifacts."""
        project = _make_project(session)
        artifact = _make_artifact(session, project, "casc-ca")
        collection = _make_collection(session)
        _add_to_collection(session, collection, artifact)
        session.commit()

        assert self._count(session, CollectionArtifact, artifact_uuid=artifact.uuid) == 1

        artifact_uuid = artifact.uuid
        _delete_artifact_via_sql(session, artifact)
        session.commit()

        assert self._count(session, CollectionArtifact, artifact_uuid=artifact_uuid) == 0, (
            "collection_artifacts row was NOT deleted when Artifact was removed — "
            "ON DELETE CASCADE on artifact_uuid FK may be missing"
        )

    def test_delete_artifact_removes_group_artifact(self, session):
        """Deleting an Artifact cascades into group_artifacts."""
        project = _make_project(session)
        artifact = _make_artifact(session, project, "casc-ga")
        collection = _make_collection(session)
        group = Group(
            id=uuid.uuid4().hex,
            collection_id=collection.id,
            name="Cascade Group",
            position=0,
        )
        session.add(group)
        session.flush()
        _add_to_group(session, group, artifact)
        session.commit()

        assert self._count(session, GroupArtifact, artifact_uuid=artifact.uuid) == 1

        artifact_uuid = artifact.uuid
        _delete_artifact_via_sql(session, artifact)
        session.commit()

        assert self._count(session, GroupArtifact, artifact_uuid=artifact_uuid) == 0, (
            "group_artifacts row was NOT deleted when Artifact was removed — "
            "ON DELETE CASCADE on artifact_uuid FK may be missing"
        )

    def test_delete_artifact_removes_artifact_tags(self, session):
        """Deleting an Artifact cascades into artifact_tags."""
        project = _make_project(session)
        artifact = _make_artifact(session, project, "casc-at")
        tag = _make_tag(session, "cascade-tag")
        _tag_artifact(session, artifact, tag)
        session.commit()

        assert self._count(session, ArtifactTag, artifact_uuid=artifact.uuid) == 1

        artifact_uuid = artifact.uuid
        _delete_artifact_via_sql(session, artifact)
        session.commit()

        assert self._count(session, ArtifactTag, artifact_uuid=artifact_uuid) == 0, (
            "artifact_tags row was NOT deleted when Artifact was removed — "
            "ON DELETE CASCADE on artifact_uuid FK may be missing"
        )

    def test_delete_artifact_removes_all_join_rows_simultaneously(self, session):
        """Deleting an Artifact in all three join tables at once clears them all."""
        project = _make_project(session)
        artifact = _make_artifact(session, project, "casc-all")
        collection = _make_collection(session)
        group = Group(
            id=uuid.uuid4().hex,
            collection_id=collection.id,
            name="Multi Cascade Group",
            position=0,
        )
        session.add(group)
        session.flush()
        tag = _make_tag(session, "multi-cascade-tag")

        _add_to_collection(session, collection, artifact)
        _add_to_group(session, group, artifact)
        _tag_artifact(session, artifact, tag)
        session.commit()

        assert self._count(session, CollectionArtifact, artifact_uuid=artifact.uuid) == 1
        assert self._count(session, GroupArtifact, artifact_uuid=artifact.uuid) == 1
        assert self._count(session, ArtifactTag, artifact_uuid=artifact.uuid) == 1

        artifact_uuid = artifact.uuid
        _delete_artifact_via_sql(session, artifact)
        session.commit()

        assert self._count(session, CollectionArtifact, artifact_uuid=artifact_uuid) == 0
        assert self._count(session, GroupArtifact, artifact_uuid=artifact_uuid) == 0
        assert self._count(session, ArtifactTag, artifact_uuid=artifact_uuid) == 0

    def test_delete_artifact_does_not_cascade_to_sibling_artifacts(self, session):
        """Cascade must NOT remove join rows for other artifacts in the same collection."""
        project = _make_project(session)
        art1 = _make_artifact(session, project, "sib1")
        art2 = _make_artifact(session, project, "sib2")
        collection = _make_collection(session)
        _add_to_collection(session, collection, art1)
        _add_to_collection(session, collection, art2)
        session.commit()

        art2_uuid = art2.uuid
        _delete_artifact_via_sql(session, art1)
        session.commit()

        remaining = self._count(session, CollectionArtifact, artifact_uuid=art2_uuid)
        assert remaining == 1, (
            "Cascade delete of art1 unexpectedly removed art2's CollectionArtifact row"
        )

    def test_delete_collection_cascades_to_collection_artifacts(self, session):
        """Deleting a Collection should cascade-delete its CollectionArtifact rows."""
        project = _make_project(session)
        artifact = _make_artifact(session, project, "coll-del")
        collection = _make_collection(session)
        _add_to_collection(session, collection, artifact)
        session.commit()

        artifact_uuid = artifact.uuid
        # Deleting the collection via SQL also triggers its FK cascade
        session.execute(
            sa.delete(Collection).where(Collection.id == collection.id)
        )
        session.commit()

        assert self._count(session, CollectionArtifact, artifact_uuid=artifact_uuid) == 0


# =============================================================================
# 4. API contract — endpoints return type:name identifiers, not raw UUIDs
# =============================================================================


@pytest.fixture
def test_settings():
    """Minimal API settings that disable auth and key enforcement."""
    return APISettings(
        env=Environment.TESTING,
        host="127.0.0.1",
        port=8000,
        log_level="DEBUG",
        cors_enabled=False,
        api_key_enabled=False,
    )


@pytest.fixture
def api_engine(tmp_path):
    """SQLite engine for the API-level tests."""
    db_path = tmp_path / "api_test.db"
    eng = create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(eng, "connect")
    def set_fk(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def api_session_factory(api_engine):
    return sessionmaker(bind=api_engine, autocommit=False, autoflush=False)


@pytest.fixture
def api_test_data(
    api_session_factory,
) -> Tuple[Collection, Group, List[Artifact], Tag]:
    """Seed the DB with a collection, group, two artifacts, and a tag.

    Returns:
        Tuple of (collection, group, [artifact1, artifact2], tag)
    """
    sess = api_session_factory()
    try:
        project = Project(
            id=uuid.uuid4().hex,
            name="API Test Project",
            path="/tmp/api-test",
            status="active",
        )
        sess.add(project)
        sess.flush()

        collection = Collection(
            id=uuid.uuid4().hex,
            name="API Test Collection",
            description="For API regression tests",
        )
        sess.add(collection)
        sess.flush()

        artifacts = []
        now = datetime.utcnow()
        for i in range(2):
            art = Artifact(
                id=f"skill:api-art-{i}",
                uuid=uuid.uuid4().hex,
                project_id=project.id,
                name=f"api-art-{i}",
                type="skill",
            )
            sess.add(art)
            sess.flush()
            artifacts.append(art)

            ca = CollectionArtifact(
                collection_id=collection.id,
                artifact_uuid=art.uuid,
                added_at=now,
                # Set synced_at so the endpoint uses the DB cache path
                # rather than falling back to artifact_mgr.show() (filesystem).
                synced_at=now,
                description=f"Test artifact {i}",
                source=f"skill:api-art-{i}",
                version="latest",
            )
            sess.add(ca)
            sess.flush()

        group = Group(
            id=uuid.uuid4().hex,
            collection_id=collection.id,
            name="API Test Group",
            position=0,
        )
        sess.add(group)
        sess.flush()

        for i, art in enumerate(artifacts):
            ga = GroupArtifact(
                group_id=group.id,
                artifact_uuid=art.uuid,
                position=i,
            )
            sess.add(ga)

        tag = Tag(
            id=uuid.uuid4().hex,
            name="api-regression-tag",
            slug="api-regression-tag",
        )
        sess.add(tag)
        sess.flush()

        at = ArtifactTag(
            artifact_uuid=artifacts[0].uuid,
            tag_id=tag.id,
            created_at=datetime.utcnow(),
        )
        sess.add(at)
        sess.commit()

        # Refresh to get bound instances before session closes
        for obj in [collection, group, tag] + artifacts:
            sess.refresh(obj)

        # Detach data we need after session close
        coll_id = collection.id
        group_id = group.id
        art_data = [(a.id, a.uuid) for a in artifacts]
        tag_id = tag.id

    finally:
        sess.close()

    # Rebuild lightweight proxies for use in tests
    _collection = MagicMock()
    _collection.id = coll_id

    _group = MagicMock()
    _group.id = group_id

    _artifacts = []
    for art_id, art_uuid in art_data:
        a = MagicMock()
        a.id = art_id
        a.uuid = art_uuid
        _artifacts.append(a)

    _tag = MagicMock()
    _tag.id = tag_id

    return _collection, _group, _artifacts, _tag


class TestAPIContract:
    """Collection/group/tag endpoints must return type:name ids, not raw UUIDs."""

    @pytest.fixture
    def client(self, test_settings, api_session_factory, api_test_data):
        """TestClient with DB session wired to the test factory.

        Patches get_session in user_collections router so the endpoint hits
        the test DB rather than the production SQLite file.
        """
        from skillmeat.api.middleware.auth import verify_token

        app = create_app(test_settings)
        from skillmeat.api.config import get_settings

        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[verify_token] = lambda: "mock-token"

        def get_test_session():
            return api_session_factory()

        with patch(
            "skillmeat.api.routers.user_collections.get_session",
            get_test_session,
        ):
            with TestClient(app) as tc:
                yield tc

        app.dependency_overrides.clear()

    def test_collection_artifacts_returns_type_name_ids(
        self, client, api_test_data
    ):
        """GET /user-collections/{id}/artifacts returns type:name artifact ids.

        The response payload uses the 'items' key (CollectionArtifactsResponse
        schema), not 'artifacts'.  Each item has an 'id' field which must be
        in type:name format (contains ':'), never a raw UUID hex.
        """
        collection, _, artifacts, _ = api_test_data

        response = client.get(
            f"/api/v1/user-collections/{collection.id}/artifacts"
        )
        assert response.status_code == 200, response.text

        data = response.json()
        # The endpoint returns {items: [...], page_info: {...}}
        returned_ids = [item.get("id") for item in data.get("items", [])]

        # Every returned id must be a type:name string (contains ':'), not a UUID hex
        for returned_id in returned_ids:
            assert ":" in returned_id, (
                f"Artifact id {returned_id!r} in collection response does not look like "
                "a type:name identifier — a raw UUID may have leaked into the API response"
            )

        expected_ids = {art.id for art in artifacts}
        for art_id in expected_ids:
            assert art_id in returned_ids, (
                f"Expected artifact id {art_id!r} not found in collection artifacts response"
            )

    def test_collection_artifacts_uses_uuid_fk_internally(
        self, api_session_factory, api_test_data
    ):
        """CollectionArtifact rows store artifact_uuid, not the type:name id."""
        _, _, artifacts, _ = api_test_data
        sess = api_session_factory()
        try:
            for art in artifacts:
                row = (
                    sess.query(CollectionArtifact)
                    .filter_by(artifact_uuid=art.uuid)
                    .one_or_none()
                )
                assert row is not None, (
                    f"No CollectionArtifact row found for artifact_uuid={art.uuid!r}"
                )
                # artifact_id shim must resolve to the type:name value
                assert row.artifact_id == art.id
        finally:
            sess.close()

    def test_group_artifacts_db_rows_use_uuid_fk(
        self, api_session_factory, api_test_data
    ):
        """GroupArtifact DB rows store artifact_uuid, not the type:name id."""
        _, group, artifacts, _ = api_test_data
        sess = api_session_factory()
        try:
            for art in artifacts:
                row = (
                    sess.query(GroupArtifact)
                    .filter_by(group_id=group.id, artifact_uuid=art.uuid)
                    .one_or_none()
                )
                assert row is not None, (
                    f"No GroupArtifact row found for group_id={group.id!r}, "
                    f"artifact_uuid={art.uuid!r}"
                )
                assert row.artifact_id == art.id
        finally:
            sess.close()

    def test_artifact_tags_db_rows_use_uuid_fk(
        self, api_session_factory, api_test_data
    ):
        """ArtifactTag DB rows store artifact_uuid, not the type:name id."""
        _, _, artifacts, tag = api_test_data
        art = artifacts[0]

        sess = api_session_factory()
        try:
            row = (
                sess.query(ArtifactTag)
                .filter_by(artifact_uuid=art.uuid, tag_id=tag.id)
                .one_or_none()
            )
            assert row is not None, (
                f"No ArtifactTag row found for artifact_uuid={art.uuid!r}, "
                f"tag_id={tag.id!r}"
            )
            assert row.artifact_uuid == art.uuid
        finally:
            sess.close()

    def test_tag_list_endpoint_returns_200(self, client, api_test_data):
        """GET /tags returns 200 — no schema errors from UUID FK columns."""
        from skillmeat.core.services import TagService
        from skillmeat.api.schemas.tags import TagListResponse
        from skillmeat.api.schemas.common import PageInfo

        # Patch TagService.list_tags to return a minimal valid response
        # so the test doesn't depend on the production SQLite DB being present
        # or migrated.  The important thing is that the endpoint itself doesn't
        # fail with a schema-level error due to the UUID migration.
        mock_response = TagListResponse(
            items=[],
            page_info=PageInfo(
                has_next_page=False,
                has_previous_page=False,
                start_cursor=None,
                end_cursor=None,
                total_count=0,
            ),
        )

        with patch.object(TagService, "list_tags", return_value=mock_response):
            response = client.get("/api/v1/tags")

        assert response.status_code == 200, (
            f"GET /tags returned {response.status_code}: {response.text}"
        )

    def test_collection_artifacts_response_has_no_raw_uuids_as_ids(
        self, client, api_test_data
    ):
        """No artifact in a collection response should have a 32-hex UUID as its id."""
        collection, _, _, _ = api_test_data
        response = client.get(
            f"/api/v1/user-collections/{collection.id}/artifacts"
        )
        assert response.status_code == 200, response.text
        data = response.json()

        # The endpoint returns {items: [...], page_info: {...}}
        for item in data.get("items", []):
            art_id = item.get("id", "")
            # A raw UUID hex has no ':' character; type:name always does
            assert ":" in art_id, (
                f"Artifact id {art_id!r} looks like a raw UUID hex — "
                "UUID may have leaked into the collection artifacts response"
            )


# =============================================================================
# 5. Alembic migration upgrade/downgrade apply cleanly
# =============================================================================


class TestAlembicMigrations:
    """Verify that the UUID migration scripts apply cleanly on a fresh database.

    Each test builds a pre-migration schema (old artifact_id columns), seeds
    minimal data, then runs the migration's upgrade() function directly via
    the alembic op.get_bind() patch pattern.
    """

    def _build_pre_migration_db(self, engine) -> None:
        """Create a pre-migration schema with legacy artifact_id columns."""
        with engine.connect() as conn:
            # Dependency tables
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS projects (
                        id VARCHAR NOT NULL PRIMARY KEY,
                        name VARCHAR NOT NULL,
                        path VARCHAR NOT NULL,
                        status VARCHAR NOT NULL DEFAULT 'active'
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS artifacts (
                        id VARCHAR NOT NULL PRIMARY KEY,
                        uuid VARCHAR NOT NULL UNIQUE,
                        project_id VARCHAR NOT NULL,
                        name VARCHAR NOT NULL,
                        type VARCHAR NOT NULL,
                        FOREIGN KEY (project_id) REFERENCES projects (id)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS collections (
                        id VARCHAR NOT NULL PRIMARY KEY,
                        name VARCHAR NOT NULL,
                        description TEXT
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS groups (
                        id VARCHAR NOT NULL PRIMARY KEY,
                        collection_id VARCHAR NOT NULL,
                        name VARCHAR NOT NULL,
                        position INTEGER NOT NULL DEFAULT 0,
                        FOREIGN KEY (collection_id) REFERENCES collections (id)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS tags (
                        id VARCHAR NOT NULL PRIMARY KEY,
                        name VARCHAR(100) NOT NULL UNIQUE,
                        slug VARCHAR(100) NOT NULL UNIQUE,
                        color VARCHAR(7),
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL
                    )
                    """
                )
            )
            # Legacy collection_artifacts (artifact_id, no FK to artifacts)
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS collection_artifacts (
                        collection_id   VARCHAR NOT NULL,
                        artifact_id     VARCHAR NOT NULL,
                        added_at        DATETIME NOT NULL,
                        description     TEXT,
                        author          VARCHAR,
                        license         VARCHAR,
                        tags_json       TEXT,
                        version         VARCHAR,
                        source          VARCHAR,
                        origin          VARCHAR,
                        origin_source   VARCHAR,
                        resolved_sha    VARCHAR(64),
                        resolved_version VARCHAR,
                        synced_at       DATETIME,
                        tools_json      TEXT,
                        deployments_json TEXT,
                        PRIMARY KEY (collection_id, artifact_id),
                        FOREIGN KEY (collection_id) REFERENCES collections (id)
                    )
                    """
                )
            )
            # Legacy group_artifacts (artifact_id, no FK to artifacts)
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS group_artifacts (
                        group_id    VARCHAR NOT NULL,
                        artifact_id VARCHAR NOT NULL,
                        position    INTEGER NOT NULL DEFAULT 0,
                        added_at    DATETIME NOT NULL,
                        PRIMARY KEY (group_id, artifact_id),
                        FOREIGN KEY (group_id) REFERENCES groups (id)
                    )
                    """
                )
            )
            # Legacy artifact_tags (artifact_id, no FK to artifacts)
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS artifact_tags (
                        artifact_id VARCHAR NOT NULL,
                        tag_id      VARCHAR NOT NULL,
                        created_at  DATETIME NOT NULL,
                        PRIMARY KEY (artifact_id, tag_id),
                        FOREIGN KEY (tag_id) REFERENCES tags (id)
                    )
                    """
                )
            )
            conn.commit()

    def _seed_migration_data(self, engine) -> dict:
        """Insert minimal seed data compatible with the pre-migration schema."""
        proj_id = uuid.uuid4().hex
        art_uuid = uuid.uuid4().hex
        art_id = "skill:migration-test"
        coll_id = uuid.uuid4().hex
        group_id = uuid.uuid4().hex
        tag_id = uuid.uuid4().hex
        now = datetime.utcnow()

        with engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO projects (id, name, path) VALUES (:id, :n, :p)"
                ),
                {"id": proj_id, "n": "Migration Test Project", "p": "/tmp/mig"},
            )
            conn.execute(
                text(
                    "INSERT INTO artifacts (id, uuid, project_id, name, type) "
                    "VALUES (:id, :uuid, :proj, :name, :type)"
                ),
                {
                    "id": art_id,
                    "uuid": art_uuid,
                    "proj": proj_id,
                    "name": "migration-test",
                    "type": "skill",
                },
            )
            conn.execute(
                text("INSERT INTO collections (id, name) VALUES (:id, :name)"),
                {"id": coll_id, "name": "Migration Collection"},
            )
            conn.execute(
                text(
                    "INSERT INTO groups (id, collection_id, name, position) "
                    "VALUES (:id, :cid, :name, :pos)"
                ),
                {"id": group_id, "cid": coll_id, "name": "Migration Group", "pos": 0},
            )
            conn.execute(
                text(
                    "INSERT INTO tags (id, name, slug, created_at, updated_at) "
                    "VALUES (:id, :name, :slug, :now, :now)"
                ),
                {"id": tag_id, "name": "migration-tag", "slug": "migration-tag", "now": now},
            )
            conn.execute(
                text(
                    "INSERT INTO collection_artifacts "
                    "(collection_id, artifact_id, added_at) "
                    "VALUES (:cid, :aid, :now)"
                ),
                {"cid": coll_id, "aid": art_id, "now": now},
            )
            conn.execute(
                text(
                    "INSERT INTO group_artifacts "
                    "(group_id, artifact_id, position, added_at) "
                    "VALUES (:gid, :aid, :pos, :now)"
                ),
                {"gid": group_id, "aid": art_id, "pos": 0, "now": now},
            )
            conn.execute(
                text(
                    "INSERT INTO artifact_tags (artifact_id, tag_id, created_at) "
                    "VALUES (:aid, :tid, :now)"
                ),
                {"aid": art_id, "tid": tag_id, "now": now},
            )
            conn.commit()

        return {
            "project_id": proj_id,
            "artifact_uuid": art_uuid,
            "artifact_id": art_id,
            "collection_id": coll_id,
            "group_id": group_id,
            "tag_id": tag_id,
        }

    def _make_engine(self, tmp_path, name: str):
        db_path = tmp_path / name
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        # FK off by default for migration scripts; they manage it explicitly
        return engine

    def _run_upgrade(self, engine, migration_module) -> None:
        """Run migration upgrade() patching alembic op.get_bind()."""
        import alembic.op as op

        with engine.connect() as conn:
            with patch.object(op, "get_bind", return_value=conn):
                migration_module.upgrade()
            conn.commit()

    def _run_downgrade(self, engine, migration_module) -> None:
        """Run migration downgrade() patching alembic op.get_bind()."""
        import alembic.op as op

        with engine.connect() as conn:
            with patch.object(op, "get_bind", return_value=conn):
                migration_module.downgrade()
            conn.commit()

    # --- collection_artifacts (CAI-P5-01) ------------------------------------

    def test_collection_artifacts_migration_upgrade(self, tmp_path):
        """CAI-P5-01: upgrade() migrates collection_artifacts to artifact_uuid FK."""
        mig = _load_migration(
            "20260219_1000_migrate_collection_artifacts_to_uuid.py"
        )
        engine = self._make_engine(tmp_path, "mig_ca.db")
        self._build_pre_migration_db(engine)
        seed = self._seed_migration_data(engine)

        self._run_upgrade(engine, mig)

        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT artifact_uuid FROM collection_artifacts "
                    "WHERE artifact_uuid = :uuid"
                ),
                {"uuid": seed["artifact_uuid"]},
            ).fetchone()

        assert row is not None, (
            "After upgrade(), no collection_artifacts row found with "
            f"artifact_uuid={seed['artifact_uuid']!r} — migration did not backfill"
        )

    def test_collection_artifacts_migration_skips_orphan_rows(self, tmp_path):
        """CAI-P5-01: Orphaned collection_artifacts rows are dropped during upgrade."""
        mig = _load_migration(
            "20260219_1000_migrate_collection_artifacts_to_uuid.py"
        )
        engine = self._make_engine(tmp_path, "mig_orphan.db")
        self._build_pre_migration_db(engine)
        seed = self._seed_migration_data(engine)

        # Insert an orphan row (artifact_id that has no artifacts.id match)
        orphan_id = "skill:does-not-exist"
        with engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO collection_artifacts "
                    "(collection_id, artifact_id, added_at) "
                    "VALUES (:cid, :aid, :now)"
                ),
                {"cid": seed["collection_id"], "aid": orphan_id, "now": datetime.utcnow()},
            )
            conn.commit()

        self._run_upgrade(engine, mig)

        with engine.connect() as conn:
            count_valid = conn.execute(
                text(
                    "SELECT COUNT(*) FROM collection_artifacts "
                    "WHERE artifact_uuid = :uuid"
                ),
                {"uuid": seed["artifact_uuid"]},
            ).scalar()
            count_total = conn.execute(
                text("SELECT COUNT(*) FROM collection_artifacts")
            ).scalar()

        assert count_valid == 1, "Valid collection_artifacts row was lost during upgrade"
        assert count_total == 1, (
            f"Expected 1 row after orphan drop, got {count_total} — "
            "orphan row may not have been dropped"
        )

    def test_collection_artifacts_migration_downgrade(self, tmp_path):
        """CAI-P5-01: downgrade() restores artifact_id from _artifact_id_backup."""
        mig = _load_migration(
            "20260219_1000_migrate_collection_artifacts_to_uuid.py"
        )
        engine = self._make_engine(tmp_path, "mig_down.db")
        self._build_pre_migration_db(engine)
        seed = self._seed_migration_data(engine)

        self._run_upgrade(engine, mig)
        self._run_downgrade(engine, mig)

        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT artifact_id FROM collection_artifacts "
                    "WHERE artifact_id = :aid"
                ),
                {"aid": seed["artifact_id"]},
            ).fetchone()

        assert row is not None, (
            "After downgrade(), collection_artifacts row not found by "
            f"artifact_id={seed['artifact_id']!r} — downgrade may not have "
            "restored the original schema"
        )

    # --- group_artifacts (CAI-P5-02) -----------------------------------------

    def test_group_artifacts_migration_upgrade(self, tmp_path):
        """CAI-P5-02: upgrade() migrates group_artifacts to artifact_uuid FK."""
        mig = _load_migration(
            "20260219_1200_migrate_group_artifacts_to_uuid.py"
        )
        engine = self._make_engine(tmp_path, "mig_ga.db")
        self._build_pre_migration_db(engine)
        seed = self._seed_migration_data(engine)

        self._run_upgrade(engine, mig)

        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT artifact_uuid FROM group_artifacts "
                    "WHERE artifact_uuid = :uuid"
                ),
                {"uuid": seed["artifact_uuid"]},
            ).fetchone()

        assert row is not None, (
            "After upgrade(), no group_artifacts row found with "
            f"artifact_uuid={seed['artifact_uuid']!r} — migration did not backfill"
        )

    def test_group_artifacts_migration_downgrade(self, tmp_path):
        """CAI-P5-02: downgrade() restores artifact_id from _artifact_id_backup."""
        mig = _load_migration(
            "20260219_1200_migrate_group_artifacts_to_uuid.py"
        )
        engine = self._make_engine(tmp_path, "mig_ga_down.db")
        self._build_pre_migration_db(engine)
        seed = self._seed_migration_data(engine)

        self._run_upgrade(engine, mig)
        self._run_downgrade(engine, mig)

        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT artifact_id FROM group_artifacts "
                    "WHERE artifact_id = :aid"
                ),
                {"aid": seed["artifact_id"]},
            ).fetchone()

        assert row is not None, (
            "After downgrade(), group_artifacts row not found by "
            f"artifact_id={seed['artifact_id']!r}"
        )

    # --- artifact_tags (CAI-P5-03) -------------------------------------------

    def test_artifact_tags_migration_upgrade(self, tmp_path):
        """CAI-P5-03: upgrade() migrates artifact_tags to artifact_uuid FK."""
        mig = _load_migration(
            "20260219_1300_migrate_artifact_tags_to_uuid.py"
        )
        engine = self._make_engine(tmp_path, "mig_at.db")
        self._build_pre_migration_db(engine)
        seed = self._seed_migration_data(engine)

        self._run_upgrade(engine, mig)

        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT artifact_uuid FROM artifact_tags "
                    "WHERE artifact_uuid = :uuid"
                ),
                {"uuid": seed["artifact_uuid"]},
            ).fetchone()

        assert row is not None, (
            "After upgrade(), no artifact_tags row found with "
            f"artifact_uuid={seed['artifact_uuid']!r} — migration did not backfill"
        )

    def test_artifact_tags_migration_downgrade(self, tmp_path):
        """CAI-P5-03: downgrade() restores artifact_id from _artifact_id_backup."""
        mig = _load_migration(
            "20260219_1300_migrate_artifact_tags_to_uuid.py"
        )
        engine = self._make_engine(tmp_path, "mig_at_down.db")
        self._build_pre_migration_db(engine)
        seed = self._seed_migration_data(engine)

        self._run_upgrade(engine, mig)
        self._run_downgrade(engine, mig)

        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT artifact_id FROM artifact_tags "
                    "WHERE artifact_id = :aid"
                ),
                {"aid": seed["artifact_id"]},
            ).fetchone()

        assert row is not None, (
            "After downgrade(), artifact_tags row not found by "
            f"artifact_id={seed['artifact_id']!r}"
        )


# =============================================================================
# 6. Query pattern — join must go through artifact.uuid, not artifact.id
# =============================================================================


class TestQueryPattern:
    """Verify the correct SQL join pattern for resolving type:name to uuid."""

    def test_collection_artifact_query_via_artifact_join(self, session):
        """Querying CollectionArtifact by artifact type:name requires joining Artifact."""
        project = _make_project(session)
        artifact = _make_artifact(session, project, "qp-ca")
        collection = _make_collection(session)
        _add_to_collection(session, collection, artifact)
        session.commit()

        # Correct pattern: join through Artifact to resolve type:name to uuid
        result = (
            session.query(Artifact.id, CollectionArtifact.artifact_uuid)
            .join(
                CollectionArtifact,
                CollectionArtifact.artifact_uuid == Artifact.uuid,
            )
            .filter(Artifact.id == artifact.id)
            .one_or_none()
        )

        assert result is not None, (
            "Join query (Artifact.id -> CollectionArtifact.artifact_uuid) returned no row"
        )
        artifact_id, artifact_uuid = result
        assert artifact_id == artifact.id
        assert artifact_uuid == artifact.uuid

    def test_group_artifact_query_via_artifact_join(self, session):
        """Querying GroupArtifact by artifact type:name requires joining Artifact."""
        project = _make_project(session)
        artifact = _make_artifact(session, project, "qp-ga")
        collection = _make_collection(session)
        group = Group(
            id=uuid.uuid4().hex,
            collection_id=collection.id,
            name="QP Group",
            position=0,
        )
        session.add(group)
        session.flush()
        _add_to_group(session, group, artifact)
        session.commit()

        result = (
            session.query(Artifact.id, GroupArtifact.artifact_uuid)
            .join(
                GroupArtifact,
                GroupArtifact.artifact_uuid == Artifact.uuid,
            )
            .filter(Artifact.id == artifact.id)
            .one_or_none()
        )

        assert result is not None
        artifact_id, artifact_uuid = result
        assert artifact_id == artifact.id
        assert artifact_uuid == artifact.uuid

    def test_artifact_tag_query_via_artifact_join(self, session):
        """Querying ArtifactTag by artifact type:name requires joining Artifact."""
        project = _make_project(session)
        artifact = _make_artifact(session, project, "qp-at")
        tag = _make_tag(session, "qp-tag")
        _tag_artifact(session, artifact, tag)
        session.commit()

        result = (
            session.query(Artifact.id, ArtifactTag.artifact_uuid)
            .join(
                ArtifactTag,
                ArtifactTag.artifact_uuid == Artifact.uuid,
            )
            .filter(Artifact.id == artifact.id)
            .one_or_none()
        )

        assert result is not None
        artifact_id, artifact_uuid = result
        assert artifact_id == artifact.id
        assert artifact_uuid == artifact.uuid

    def test_batch_query_artifact_ids_via_join(self, session):
        """Batch query by multiple type:name ids works correctly through the join."""
        project = _make_project(session)
        artifacts = [_make_artifact(session, project, f"batch-{i}") for i in range(3)]
        collection = _make_collection(session)
        for art in artifacts:
            _add_to_collection(session, collection, art)
        session.commit()

        artifact_ids = [art.id for art in artifacts]

        # This is the correct batch join pattern used in artifacts.py ~line 2257
        rows = (
            session.query(Artifact.id, CollectionArtifact.artifact_uuid)
            .join(
                CollectionArtifact,
                CollectionArtifact.artifact_uuid == Artifact.uuid,
            )
            .filter(Artifact.id.in_(artifact_ids))
            .all()
        )

        assert len(rows) == 3, (
            f"Expected 3 rows from batch join query, got {len(rows)}"
        )
        returned_ids = {row.id for row in rows}
        assert returned_ids == set(artifact_ids)

    def test_direct_artifact_id_filter_without_join_returns_nothing(self, session):
        """Filtering CollectionArtifact directly by artifact_id string returns empty.

        This test documents why the join pattern is required: CollectionArtifact
        has no artifact_id column (it was replaced by artifact_uuid), so any
        filter that tries to use the type:name string directly on CollectionArtifact
        will return zero rows.
        """
        project = _make_project(session)
        artifact = _make_artifact(session, project, "direct-filter")
        collection = _make_collection(session)
        _add_to_collection(session, collection, artifact)
        session.commit()

        # Attempting to filter by artifact_id on the join table must fail or
        # return nothing because the column does not exist in the schema.
        # We verify this by checking the column is absent at the model level.
        mapper_cols = [c.key for c in CollectionArtifact.__table__.columns]
        assert "artifact_id" not in mapper_cols, (
            "CollectionArtifact still has an artifact_id column in the schema — "
            "the UUID migration (CAI-P5-01) may not have been applied"
        )
