"""Unit tests for version tracking utilities."""

import json
import uuid
from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from skillmeat.cache.models import Artifact, ArtifactVersion, Project, get_session
from skillmeat.core.version_tracking import (
    create_deployment_version,
    create_local_modification_version,
    create_sync_version,
    get_latest_version,
    get_version_by_hash,
)


@pytest.fixture
def db_session(tmp_path):
    """Create temporary test database session."""
    from skillmeat.cache.models import create_tables, init_session_factory

    db_path = tmp_path / "test.db"
    create_tables(db_path)
    init_session_factory(db_path)
    session = get_session(db_path)
    yield session
    session.close()


@pytest.fixture
def test_project(db_session: Session):
    """Create test project in database."""
    project = Project(
        id=uuid.uuid4().hex,
        name="Test Project",
        path="/test/project",
        status="active",
    )
    db_session.add(project)
    db_session.commit()
    return project


@pytest.fixture
def test_artifact(db_session: Session, test_project: Project):
    """Create test artifact in database."""
    artifact = Artifact(
        id=uuid.uuid4().hex,
        project_id=test_project.id,
        name="test-skill",
        type="skill",
    )
    db_session.add(artifact)
    db_session.commit()
    return artifact


class TestCreateDeploymentVersion:
    """Tests for create_deployment_version function."""

    def test_creates_deployment_version(self, db_session: Session, test_artifact: Artifact):
        """Test creating a deployment version record."""
        content_hash = "abc123def456"

        version = create_deployment_version(
            session=db_session,
            artifact_id=test_artifact.id,
            content_hash=content_hash,
        )

        assert version.artifact_id == test_artifact.id
        assert version.content_hash == content_hash
        assert version.parent_hash is None  # Root version
        assert version.change_origin == "deployment"
        assert version.version_lineage == json.dumps([content_hash])

    def test_idempotent_on_same_hash(self, db_session: Session, test_artifact: Artifact):
        """Test that creating version with same hash returns existing record."""
        content_hash = "abc123def456"

        version1 = create_deployment_version(
            session=db_session,
            artifact_id=test_artifact.id,
            content_hash=content_hash,
        )
        db_session.commit()

        version2 = create_deployment_version(
            session=db_session,
            artifact_id=test_artifact.id,
            content_hash=content_hash,
        )

        assert version1.id == version2.id
        assert version1.content_hash == version2.content_hash

    def test_generates_unique_id(self, db_session: Session, test_artifact: Artifact):
        """Test that each version gets a unique ID."""
        version1 = create_deployment_version(
            session=db_session,
            artifact_id=test_artifact.id,
            content_hash="hash1",
        )
        db_session.commit()

        version2 = create_deployment_version(
            session=db_session,
            artifact_id=test_artifact.id,
            content_hash="hash2",
        )
        db_session.commit()

        assert version1.id != version2.id


class TestCreateSyncVersion:
    """Tests for create_sync_version function."""

    def test_creates_sync_version_with_parent(
        self, db_session: Session, test_artifact: Artifact
    ):
        """Test creating a sync version with parent hash."""
        parent_hash = "parent123"
        content_hash = "child456"

        # Create parent version first
        parent_version = create_deployment_version(
            session=db_session,
            artifact_id=test_artifact.id,
            content_hash=parent_hash,
        )
        db_session.commit()

        # Create sync version
        sync_version = create_sync_version(
            session=db_session,
            artifact_id=test_artifact.id,
            content_hash=content_hash,
            parent_hash=parent_hash,
        )

        assert sync_version.artifact_id == test_artifact.id
        assert sync_version.content_hash == content_hash
        assert sync_version.parent_hash == parent_hash
        assert sync_version.change_origin == "sync"

        # Check lineage includes both parent and current
        lineage = json.loads(sync_version.version_lineage)
        assert content_hash in lineage
        assert parent_hash in lineage

    def test_builds_lineage_from_parent(
        self, db_session: Session, test_artifact: Artifact
    ):
        """Test that version lineage is built from parent's lineage."""
        hash1 = "hash1"
        hash2 = "hash2"
        hash3 = "hash3"

        # Create chain: deployment -> sync -> sync
        v1 = create_deployment_version(
            session=db_session,
            artifact_id=test_artifact.id,
            content_hash=hash1,
        )
        db_session.commit()

        v2 = create_sync_version(
            session=db_session,
            artifact_id=test_artifact.id,
            content_hash=hash2,
            parent_hash=hash1,
        )
        db_session.commit()

        v3 = create_sync_version(
            session=db_session,
            artifact_id=test_artifact.id,
            content_hash=hash3,
            parent_hash=hash2,
        )

        lineage = json.loads(v3.version_lineage)
        assert lineage == [hash3, hash2, hash1]


class TestCreateLocalModificationVersion:
    """Tests for create_local_modification_version function."""

    def test_creates_local_modification_version(
        self, db_session: Session, test_artifact: Artifact
    ):
        """Test creating a local modification version."""
        parent_hash = "parent123"
        content_hash = "modified456"

        # Create parent version first
        create_deployment_version(
            session=db_session,
            artifact_id=test_artifact.id,
            content_hash=parent_hash,
        )
        db_session.commit()

        # Create local modification
        mod_version = create_local_modification_version(
            session=db_session,
            artifact_id=test_artifact.id,
            content_hash=content_hash,
            parent_hash=parent_hash,
        )

        assert mod_version.artifact_id == test_artifact.id
        assert mod_version.content_hash == content_hash
        assert mod_version.parent_hash == parent_hash
        assert mod_version.change_origin == "local_modification"


class TestGetLatestVersion:
    """Tests for get_latest_version function."""

    def test_returns_most_recent_version(
        self, db_session: Session, test_artifact: Artifact
    ):
        """Test getting the most recent version for an artifact."""
        # Create multiple versions
        v1 = create_deployment_version(
            session=db_session,
            artifact_id=test_artifact.id,
            content_hash="hash1",
        )
        db_session.commit()

        v2 = create_sync_version(
            session=db_session,
            artifact_id=test_artifact.id,
            content_hash="hash2",
            parent_hash="hash1",
        )
        db_session.commit()

        latest = get_latest_version(db_session, test_artifact.id)

        assert latest.id == v2.id
        assert latest.content_hash == "hash2"

    def test_returns_none_when_no_versions(
        self, db_session: Session, test_artifact: Artifact
    ):
        """Test that None is returned when no versions exist."""
        latest = get_latest_version(db_session, test_artifact.id)
        assert latest is None


class TestGetVersionByHash:
    """Tests for get_version_by_hash function."""

    def test_finds_version_by_content_hash(
        self, db_session: Session, test_artifact: Artifact
    ):
        """Test finding a version by its content hash."""
        content_hash = "unique123"

        version = create_deployment_version(
            session=db_session,
            artifact_id=test_artifact.id,
            content_hash=content_hash,
        )
        db_session.commit()

        found = get_version_by_hash(db_session, content_hash)

        assert found.id == version.id
        assert found.content_hash == content_hash

    def test_returns_none_when_not_found(self, db_session: Session):
        """Test that None is returned when hash not found."""
        found = get_version_by_hash(db_session, "nonexistent")
        assert found is None
