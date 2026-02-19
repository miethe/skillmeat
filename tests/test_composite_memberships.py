"""Unit tests for UUID generation and CompositeMembership CRUD.

This module tests:
- Artifact UUID auto-generation (length, uniqueness, constraint)
- CompositeMembership ORM model creation and constraints
- CompositeMembershipRepository CRUD methods
- CompositeService type:name → UUID resolution

Tests use an in-memory SQLite database (temp file approach) consistent with
the pattern established in test_cache_repository.py.
"""

from __future__ import annotations

import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Generator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from skillmeat.cache.composite_repository import CompositeMembershipRepository
from skillmeat.cache.models import (
    Artifact,
    Base,
    CompositeArtifact,
    CompositeMembership,
    Project,
    create_db_engine,
    create_tables,
)
from skillmeat.cache.repositories import ConstraintError, NotFoundError
from skillmeat.core.services.composite_service import (
    ArtifactNotFoundError,
    CompositeService,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_db() -> Generator[str, None, None]:
    """Create a temporary SQLite database file.

    Uses a temp-file (not :memory:) to match existing test patterns and
    properly exercise file-based SQLite behaviour including WAL mode.

    Yields:
        Absolute path to the temp database file.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    yield db_path

    try:
        Path(db_path).unlink()
    except FileNotFoundError:
        pass


@pytest.fixture
def engine(temp_db: str):
    """Create a SQLAlchemy engine and ensure all tables exist.

    Args:
        temp_db: Path provided by the temp_db fixture.

    Returns:
        Configured SQLAlchemy Engine.
    """
    eng = create_db_engine(temp_db)
    # Bypass Alembic — create all ORM-declared tables directly so tests have no
    # migration dependency.
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def session(engine) -> Generator[Session, None, None]:
    """Provide a transactional session that rolls back after each test.

    Using rollback-on-teardown keeps tests hermetic without deleting the DB.

    Yields:
        Active SQLAlchemy Session.
    """
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    sess = SessionLocal()
    try:
        yield sess
    finally:
        sess.close()


@pytest.fixture
def composite_repo(temp_db: str) -> CompositeMembershipRepository:
    """Return a CompositeMembershipRepository wired to the temp database.

    Patches ``skillmeat.cache.migrations.run_migrations`` to a no-op so that
    tests don't depend on the full Alembic migration chain.  The repository
    constructor still calls ``create_tables`` (``Base.metadata.create_all``)
    after the patched no-op, so all ORM-declared tables are present.

    Args:
        temp_db: Path to the temp database file.

    Returns:
        CompositeMembershipRepository instance with all ORM tables present.
    """
    from unittest.mock import patch

    with patch("skillmeat.cache.migrations.run_migrations"):
        repo = CompositeMembershipRepository(db_path=temp_db)
    return repo


@pytest.fixture
def composite_service(temp_db: str) -> CompositeService:
    """Return a CompositeService wired to the temp database.

    Patches ``skillmeat.cache.migrations.run_migrations`` to a no-op for the
    same reason as ``composite_repo``.

    Args:
        temp_db: Path to the temp database file.

    Returns:
        CompositeService instance.
    """
    from unittest.mock import patch

    with patch("skillmeat.cache.migrations.run_migrations"):
        svc = CompositeService(db_path=temp_db)
    return svc


@pytest.fixture
def sample_project(session: Session) -> Project:
    """Insert and return a minimal Project row.

    Args:
        session: Active session from the session fixture.

    Returns:
        Persisted Project instance.
    """
    project = Project(
        id="proj-test-001",
        name="Test Project",
        path="/tmp/test-project-001",
        status="active",
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@pytest.fixture
def sample_artifact(session: Session, sample_project: Project) -> Artifact:
    """Insert and return an Artifact belonging to sample_project.

    UUID is intentionally omitted so that the default lambda fires during
    insert, verifying auto-generation behaviour.

    Args:
        session: Active session.
        sample_project: Parent project.

    Returns:
        Persisted Artifact instance.
    """
    artifact = Artifact(
        id="skill:test-canvas",
        project_id=sample_project.id,
        name="test-canvas",
        type="skill",
    )
    session.add(artifact)
    session.commit()
    session.refresh(artifact)
    return artifact


@pytest.fixture
def second_artifact(session: Session, sample_project: Project) -> Artifact:
    """Insert and return a second Artifact (distinct from sample_artifact).

    Args:
        session: Active session.
        sample_project: Parent project.

    Returns:
        Persisted Artifact instance.
    """
    artifact = Artifact(
        id="command:test-deploy",
        project_id=sample_project.id,
        name="test-deploy",
        type="command",
    )
    session.add(artifact)
    session.commit()
    session.refresh(artifact)
    return artifact


@pytest.fixture
def sample_composite(session: Session) -> CompositeArtifact:
    """Insert and return a CompositeArtifact row.

    Args:
        session: Active session.

    Returns:
        Persisted CompositeArtifact instance.
    """
    composite = CompositeArtifact(
        id="composite:my-plugin",
        collection_id="collection-abc",
        composite_type="plugin",
        display_name="My Plugin",
    )
    session.add(composite)
    session.commit()
    session.refresh(composite)
    return composite


# Helper: persist a project + artifact + composite via the repo's own engine
# (used for repository/service-layer tests that go through the repository
# interface rather than a bare SQLAlchemy session).


def _seed_project_and_artifact(
    repo: CompositeMembershipRepository,
    project_id: str = "proj-seed-001",
    artifact_id: str = "skill:canvas",
    artifact_name: str = "canvas",
) -> str:
    """Seed a Project, Artifact, and CompositeArtifact via the repo engine.

    Returns the auto-generated artifact UUID so callers can construct
    membership records without a second query.

    Args:
        repo: Repository instance whose engine owns the target database.
        project_id: Unique project identifier.
        artifact_id: ``type:name`` artifact primary key.
        artifact_name: Human-readable artifact name.

    Returns:
        32-character hex UUID assigned to the new Artifact.
    """
    SessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=repo.engine
    )
    sess = SessionLocal()
    try:
        project = Project(
            id=project_id,
            name="Seed Project",
            path=f"/tmp/seed-{project_id}",
            status="active",
        )
        sess.add(project)
        sess.flush()

        artifact = Artifact(
            id=artifact_id,
            project_id=project_id,
            name=artifact_name,
            type=artifact_id.split(":")[0],
        )
        sess.add(artifact)
        sess.flush()

        composite = CompositeArtifact(
            id="composite:my-plugin",
            collection_id="collection-abc",
            composite_type="plugin",
        )
        # Only add if it doesn't already exist
        existing = (
            sess.query(CompositeArtifact)
            .filter(CompositeArtifact.id == "composite:my-plugin")
            .first()
        )
        if existing is None:
            sess.add(composite)

        sess.commit()
        sess.refresh(artifact)
        return artifact.uuid
    finally:
        sess.close()


# =============================================================================
# UUID Generation Tests
# =============================================================================


class TestArtifactUUIDGeneration:
    """Tests that Artifact.uuid is auto-generated correctly on insert."""

    def test_cached_artifact_uuid_generation(
        self, session: Session, sample_artifact: Artifact
    ) -> None:
        """Artifact inserted without explicit UUID gets a 32-char hex UUID.

        The default lambda ``lambda: uuid.uuid4().hex`` must fire during
        the INSERT and persist a non-null, 32-character hexadecimal string.
        """
        assert sample_artifact.uuid is not None, "uuid must not be None after insert"
        assert isinstance(sample_artifact.uuid, str), "uuid must be a string"
        assert len(sample_artifact.uuid) == 32, (
            f"uuid.hex produces 32 chars; got {len(sample_artifact.uuid)!r}"
        )
        # Must be valid hexadecimal (no hyphens — uuid4().hex, not str(uuid4()))
        int(sample_artifact.uuid, 16)  # raises ValueError if not valid hex

    def test_uuid_uniqueness(
        self,
        session: Session,
        sample_artifact: Artifact,
        second_artifact: Artifact,
    ) -> None:
        """Two independently inserted Artifacts receive distinct UUIDs."""
        assert sample_artifact.uuid != second_artifact.uuid, (
            "Each Artifact must receive a unique UUID; got duplicate "
            f"{sample_artifact.uuid!r}"
        )

    def test_uuid_unique_constraint(
        self, session: Session, sample_project: Project, sample_artifact: Artifact
    ) -> None:
        """Inserting an Artifact with a duplicate UUID raises IntegrityError.

        The ``UNIQUE`` constraint on ``artifacts.uuid`` (declared via
        ``mapped_column(String, unique=True, ...)``) must reject duplicates.
        """
        duplicate = Artifact(
            id="skill:another-skill",
            project_id=sample_project.id,
            name="another-skill",
            type="skill",
            uuid=sample_artifact.uuid,  # force the same UUID
        )
        session.add(duplicate)

        with pytest.raises(IntegrityError):
            session.flush()

        session.rollback()

    def test_explicit_uuid_is_preserved(
        self, session: Session, sample_project: Project
    ) -> None:
        """An Artifact with an explicitly set UUID keeps that value after insert."""
        custom_uuid = uuid.uuid4().hex
        artifact = Artifact(
            id="skill:explicit-uuid-skill",
            project_id=sample_project.id,
            name="explicit-uuid-skill",
            type="skill",
            uuid=custom_uuid,
        )
        session.add(artifact)
        session.commit()
        session.refresh(artifact)

        assert artifact.uuid == custom_uuid


# =============================================================================
# CompositeMembership Model Tests
# =============================================================================


class TestCompositeMembershipModel:
    """Direct ORM-level tests for CompositeMembership creation and constraints."""

    def test_valid_membership_creates_correctly(
        self,
        session: Session,
        sample_artifact: Artifact,
        sample_composite: CompositeArtifact,
    ) -> None:
        """A CompositeMembership row is created with correct FK values."""
        membership = CompositeMembership(
            collection_id="collection-abc",
            composite_id=sample_composite.id,
            child_artifact_uuid=sample_artifact.uuid,
        )
        session.add(membership)
        session.commit()
        session.refresh(membership)

        assert membership.composite_id == sample_composite.id
        assert membership.child_artifact_uuid == sample_artifact.uuid
        assert membership.collection_id == "collection-abc"

    def test_relationship_type_defaults_to_contains(
        self,
        session: Session,
        sample_artifact: Artifact,
        sample_composite: CompositeArtifact,
    ) -> None:
        """CompositeMembership.relationship_type defaults to 'contains'."""
        membership = CompositeMembership(
            collection_id="collection-abc",
            composite_id=sample_composite.id,
            child_artifact_uuid=sample_artifact.uuid,
        )
        session.add(membership)
        session.commit()
        session.refresh(membership)

        assert membership.relationship_type == "contains"

    def test_created_at_auto_set_on_creation(
        self,
        session: Session,
        sample_artifact: Artifact,
        sample_composite: CompositeArtifact,
    ) -> None:
        """CompositeMembership.created_at is populated automatically on insert."""
        before = datetime.utcnow()
        membership = CompositeMembership(
            collection_id="collection-abc",
            composite_id=sample_composite.id,
            child_artifact_uuid=sample_artifact.uuid,
        )
        session.add(membership)
        session.commit()
        session.refresh(membership)
        after = datetime.utcnow()

        assert membership.created_at is not None
        assert before <= membership.created_at <= after

    def test_composite_pk_prevents_duplicate_parent_child_pairs(
        self,
        engine,
        sample_artifact: Artifact,
        sample_composite: CompositeArtifact,
    ) -> None:
        """Inserting the same (collection_id, composite_id, child_uuid) twice raises IntegrityError.

        A fresh session is used for each insert so that SQLAlchemy's identity
        map does not short-circuit the duplicate detection before the DB-level
        UNIQUE constraint fires.
        """
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        def _insert_membership():
            sess = SessionLocal()
            try:
                membership = CompositeMembership(
                    collection_id="collection-abc",
                    composite_id=sample_composite.id,
                    child_artifact_uuid=sample_artifact.uuid,
                )
                sess.add(membership)
                sess.commit()
            finally:
                sess.close()

        _insert_membership()  # first insert: must succeed

        with pytest.raises(IntegrityError):
            _insert_membership()  # second insert: must fail

    def test_custom_relationship_type_is_persisted(
        self,
        session: Session,
        sample_artifact: Artifact,
        sample_composite: CompositeArtifact,
    ) -> None:
        """A non-default relationship_type value is stored and retrieved correctly."""
        membership = CompositeMembership(
            collection_id="collection-abc",
            composite_id=sample_composite.id,
            child_artifact_uuid=sample_artifact.uuid,
            relationship_type="extends",
        )
        session.add(membership)
        session.commit()
        session.refresh(membership)

        assert membership.relationship_type == "extends"

    def test_pinned_version_hash_is_nullable(
        self,
        session: Session,
        sample_artifact: Artifact,
        sample_composite: CompositeArtifact,
    ) -> None:
        """pinned_version_hash defaults to None (track-latest semantics)."""
        membership = CompositeMembership(
            collection_id="collection-abc",
            composite_id=sample_composite.id,
            child_artifact_uuid=sample_artifact.uuid,
        )
        session.add(membership)
        session.commit()
        session.refresh(membership)

        assert membership.pinned_version_hash is None

    def test_to_dict_includes_expected_keys(
        self,
        session: Session,
        sample_artifact: Artifact,
        sample_composite: CompositeArtifact,
    ) -> None:
        """CompositeMembership.to_dict() includes all required serialisation keys."""
        membership = CompositeMembership(
            collection_id="collection-abc",
            composite_id=sample_composite.id,
            child_artifact_uuid=sample_artifact.uuid,
        )
        session.add(membership)
        session.commit()
        session.refresh(membership)

        result = membership.to_dict()

        expected_keys = {
            "collection_id",
            "composite_id",
            "child_artifact_uuid",
            "relationship_type",
            "pinned_version_hash",
            "membership_metadata",
            "created_at",
        }
        assert expected_keys.issubset(result.keys())
        assert result["composite_id"] == sample_composite.id
        assert result["child_artifact_uuid"] == sample_artifact.uuid


# =============================================================================
# CompositeMembershipRepository Tests
# =============================================================================


class TestCompositeMembershipRepository:
    """Tests for CompositeMembershipRepository CRUD methods."""

    def test_create_membership_returns_correct_record(
        self, composite_repo: CompositeMembershipRepository
    ) -> None:
        """create_membership() returns a MembershipRecord with correct field values."""
        child_uuid = _seed_project_and_artifact(composite_repo)

        record = composite_repo.create_membership(
            collection_id="collection-abc",
            composite_id="composite:my-plugin",
            child_artifact_uuid=child_uuid,
        )

        assert record["collection_id"] == "collection-abc"
        assert record["composite_id"] == "composite:my-plugin"
        assert record["child_artifact_uuid"] == child_uuid
        assert record["relationship_type"] == "contains"

    def test_create_membership_raises_constraint_error_on_duplicate(
        self, composite_repo: CompositeMembershipRepository
    ) -> None:
        """create_membership() raises ConstraintError on duplicate (collection, composite, child)."""
        child_uuid = _seed_project_and_artifact(composite_repo)

        composite_repo.create_membership(
            collection_id="collection-abc",
            composite_id="composite:my-plugin",
            child_artifact_uuid=child_uuid,
        )

        with pytest.raises(ConstraintError):
            composite_repo.create_membership(
                collection_id="collection-abc",
                composite_id="composite:my-plugin",
                child_artifact_uuid=child_uuid,
            )

    def test_get_children_of_returns_correct_children(
        self, composite_repo: CompositeMembershipRepository
    ) -> None:
        """get_children_of() returns membership records for the given composite."""
        child_uuid = _seed_project_and_artifact(composite_repo)

        composite_repo.create_membership(
            collection_id="collection-abc",
            composite_id="composite:my-plugin",
            child_artifact_uuid=child_uuid,
        )

        children = composite_repo.get_children_of(
            "composite:my-plugin", "collection-abc"
        )

        assert len(children) == 1
        assert children[0]["child_artifact_uuid"] == child_uuid
        assert children[0]["composite_id"] == "composite:my-plugin"

    def test_get_children_of_returns_empty_list_when_none(
        self, composite_repo: CompositeMembershipRepository
    ) -> None:
        """get_children_of() returns [] when the composite has no members."""
        # Seed the composite row so it exists, but don't add any members
        _seed_project_and_artifact(composite_repo)

        children = composite_repo.get_children_of(
            "composite:my-plugin", "collection-abc"
        )

        assert children == []

    def test_get_children_of_filters_by_collection_id(
        self, composite_repo: CompositeMembershipRepository
    ) -> None:
        """get_children_of() only returns members from the specified collection."""
        child_uuid = _seed_project_and_artifact(composite_repo)

        composite_repo.create_membership(
            collection_id="collection-abc",
            composite_id="composite:my-plugin",
            child_artifact_uuid=child_uuid,
        )

        # Query for a different collection — should return empty list
        children = composite_repo.get_children_of(
            "composite:my-plugin", "collection-xyz"
        )

        assert children == []

    def test_get_parents_of_returns_correct_parents(
        self, composite_repo: CompositeMembershipRepository
    ) -> None:
        """get_parents_of() returns composites that contain the given child UUID."""
        child_uuid = _seed_project_and_artifact(composite_repo)

        composite_repo.create_membership(
            collection_id="collection-abc",
            composite_id="composite:my-plugin",
            child_artifact_uuid=child_uuid,
        )

        parents = composite_repo.get_parents_of(child_uuid, "collection-abc")

        assert len(parents) == 1
        assert parents[0]["composite_id"] == "composite:my-plugin"
        assert parents[0]["child_artifact_uuid"] == child_uuid

    def test_get_parents_of_returns_empty_list_when_not_member(
        self, composite_repo: CompositeMembershipRepository
    ) -> None:
        """get_parents_of() returns [] for a UUID that belongs to no composite."""
        child_uuid = _seed_project_and_artifact(composite_repo)

        parents = composite_repo.get_parents_of(child_uuid, "collection-abc")

        assert parents == []

    def test_get_parents_of_filters_by_collection_id(
        self, composite_repo: CompositeMembershipRepository
    ) -> None:
        """get_parents_of() only returns parents from the specified collection."""
        child_uuid = _seed_project_and_artifact(composite_repo)

        composite_repo.create_membership(
            collection_id="collection-abc",
            composite_id="composite:my-plugin",
            child_artifact_uuid=child_uuid,
        )

        # Wrong collection
        parents = composite_repo.get_parents_of(child_uuid, "collection-xyz")

        assert parents == []

    def test_delete_membership_removes_record_and_returns_true(
        self, composite_repo: CompositeMembershipRepository
    ) -> None:
        """delete_membership() removes the row and returns True."""
        child_uuid = _seed_project_and_artifact(composite_repo)

        composite_repo.create_membership(
            collection_id="collection-abc",
            composite_id="composite:my-plugin",
            child_artifact_uuid=child_uuid,
        )

        result = composite_repo.delete_membership(
            "composite:my-plugin", child_uuid
        )

        assert result is True

        # Verify the row is gone
        children = composite_repo.get_children_of(
            "composite:my-plugin", "collection-abc"
        )
        assert children == []

    def test_delete_membership_returns_false_when_not_found(
        self, composite_repo: CompositeMembershipRepository
    ) -> None:
        """delete_membership() returns False when no matching row exists."""
        non_existent_uuid = uuid.uuid4().hex

        result = composite_repo.delete_membership(
            "composite:my-plugin", non_existent_uuid
        )

        assert result is False

    def test_get_associations_returns_both_parents_and_children(
        self, composite_repo: CompositeMembershipRepository
    ) -> None:
        """get_associations() returns a dict with 'parents' and 'children' keys."""
        child_uuid = _seed_project_and_artifact(composite_repo)

        composite_repo.create_membership(
            collection_id="collection-abc",
            composite_id="composite:my-plugin",
            child_artifact_uuid=child_uuid,
        )

        # Query for the composite — it should have children but no parents
        associations = composite_repo.get_associations(
            "composite:my-plugin", "collection-abc"
        )

        assert "parents" in associations
        assert "children" in associations
        assert len(associations["children"]) == 1
        assert associations["children"][0]["child_artifact_uuid"] == child_uuid

    def test_create_membership_with_pinned_version_hash(
        self, composite_repo: CompositeMembershipRepository
    ) -> None:
        """create_membership() stores a pinned_version_hash when supplied."""
        child_uuid = _seed_project_and_artifact(composite_repo)
        pin_hash = "abc123def456"

        record = composite_repo.create_membership(
            collection_id="collection-abc",
            composite_id="composite:my-plugin",
            child_artifact_uuid=child_uuid,
            pinned_version_hash=pin_hash,
        )

        assert record["pinned_version_hash"] == pin_hash

    def test_create_membership_custom_relationship_type(
        self, composite_repo: CompositeMembershipRepository
    ) -> None:
        """create_membership() stores a custom relationship_type value."""
        child_uuid = _seed_project_and_artifact(composite_repo)

        record = composite_repo.create_membership(
            collection_id="collection-abc",
            composite_id="composite:my-plugin",
            child_artifact_uuid=child_uuid,
            relationship_type="extends",
        )

        assert record["relationship_type"] == "extends"

    def test_multiple_children_returned_by_get_children_of(
        self, composite_repo: CompositeMembershipRepository
    ) -> None:
        """get_children_of() returns all children when multiple exist."""
        uuid_1 = _seed_project_and_artifact(
            composite_repo,
            project_id="proj-multi-1",
            artifact_id="skill:canvas",
            artifact_name="canvas",
        )
        uuid_2 = _seed_project_and_artifact(
            composite_repo,
            project_id="proj-multi-2",
            artifact_id="command:deploy",
            artifact_name="deploy",
        )

        composite_repo.create_membership(
            collection_id="collection-abc",
            composite_id="composite:my-plugin",
            child_artifact_uuid=uuid_1,
        )
        composite_repo.create_membership(
            collection_id="collection-abc",
            composite_id="composite:my-plugin",
            child_artifact_uuid=uuid_2,
        )

        children = composite_repo.get_children_of(
            "composite:my-plugin", "collection-abc"
        )

        returned_uuids = {c["child_artifact_uuid"] for c in children}
        assert returned_uuids == {uuid_1, uuid_2}


# =============================================================================
# CompositeService Tests
# =============================================================================


class TestCompositeService:
    """Tests for CompositeService — type:name → UUID resolution and delegation."""

    def test_add_composite_member_resolves_type_name_to_uuid(
        self, composite_service: CompositeService
    ) -> None:
        """add_composite_member() resolves child_artifact_id to UUID before write."""
        # Seed via the underlying repo so the artifact exists in the same DB
        repo = composite_service._repo
        child_uuid = _seed_project_and_artifact(
            repo,
            project_id="proj-svc-001",
            artifact_id="skill:canvas",
            artifact_name="canvas",
        )

        record = composite_service.add_composite_member(
            collection_id="collection-abc",
            composite_id="composite:my-plugin",
            child_artifact_id="skill:canvas",
        )

        # Service must have resolved "skill:canvas" to its UUID
        assert record["child_artifact_uuid"] == child_uuid
        assert record["collection_id"] == "collection-abc"
        assert record["composite_id"] == "composite:my-plugin"

    def test_add_composite_member_raises_for_unknown_artifact(
        self, composite_service: CompositeService
    ) -> None:
        """add_composite_member() raises ArtifactNotFoundError for unknown type:name."""
        with pytest.raises(ArtifactNotFoundError) as exc_info:
            composite_service.add_composite_member(
                collection_id="collection-abc",
                composite_id="composite:my-plugin",
                child_artifact_id="skill:does-not-exist",
            )

        assert "skill:does-not-exist" in str(exc_info.value)

    def test_add_composite_member_raises_constraint_error_on_duplicate(
        self, composite_service: CompositeService
    ) -> None:
        """add_composite_member() raises ConstraintError on second identical call."""
        repo = composite_service._repo
        _seed_project_and_artifact(
            repo,
            project_id="proj-svc-dup",
            artifact_id="skill:canvas",
            artifact_name="canvas",
        )

        composite_service.add_composite_member(
            collection_id="collection-abc",
            composite_id="composite:my-plugin",
            child_artifact_id="skill:canvas",
        )

        with pytest.raises(ConstraintError):
            composite_service.add_composite_member(
                collection_id="collection-abc",
                composite_id="composite:my-plugin",
                child_artifact_id="skill:canvas",
            )

    def test_get_associations_delegates_to_repository(
        self, composite_service: CompositeService
    ) -> None:
        """get_associations() returns the same structure as the repository method."""
        repo = composite_service._repo
        child_uuid = _seed_project_and_artifact(
            repo,
            project_id="proj-svc-assoc",
            artifact_id="skill:canvas",
            artifact_name="canvas",
        )

        composite_service.add_composite_member(
            collection_id="collection-abc",
            composite_id="composite:my-plugin",
            child_artifact_id="skill:canvas",
        )

        associations = composite_service.get_associations(
            "composite:my-plugin", "collection-abc"
        )

        assert "parents" in associations
        assert "children" in associations
        assert len(associations["children"]) == 1
        assert associations["children"][0]["child_artifact_uuid"] == child_uuid

    def test_artifact_not_found_error_message_contains_artifact_id(
        self,
    ) -> None:
        """ArtifactNotFoundError includes the missing artifact id in its message."""
        error = ArtifactNotFoundError("skill:missing")

        assert "skill:missing" in str(error)
        assert error.artifact_id == "skill:missing"

    def test_add_composite_member_with_custom_relationship_type(
        self, composite_service: CompositeService
    ) -> None:
        """add_composite_member() passes custom relationship_type through to repo."""
        repo = composite_service._repo
        _seed_project_and_artifact(
            repo,
            project_id="proj-svc-reltype",
            artifact_id="skill:canvas",
            artifact_name="canvas",
        )

        record = composite_service.add_composite_member(
            collection_id="collection-abc",
            composite_id="composite:my-plugin",
            child_artifact_id="skill:canvas",
            relationship_type="extends",
        )

        assert record["relationship_type"] == "extends"
