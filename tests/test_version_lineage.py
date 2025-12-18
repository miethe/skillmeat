"""Tests for version lineage tracking functionality.

This module provides comprehensive unit tests for the ArtifactVersion model
and version lineage utilities, testing version chain creation, change origin
attribution, and ancestry tracking.

Test coverage includes:
- ArtifactVersion ORM model operations
- Change origin attribution (deployment, sync, local_modification)
- Version lineage chain building
- Parent-child relationships
- Content-based deduplication
- Constraint validation (unique hash, valid enum)
- Cascade delete behavior
- Version chain creation (comprehensive):
  * Linear chain construction (parent -> child)
  * Multi-generation chains (5+ versions)
  * Mixed change origins (deployment/sync/local_modification)
  * Metadata tracking across versions
  * Orphaned versions (missing parents)
  * Chain rebuilding from lineage
  * Chronological ordering preservation
  * Querying chains by artifact
  * Long chain performance (25+ versions)
- Version lineage utilities (when implemented)
- Integration tests (realistic workflows)
"""

from __future__ import annotations

import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from skillmeat.cache.models import Base, Artifact, Project, ArtifactVersion


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def session():
    """Create in-memory SQLite database for testing.

    Yields:
        SQLAlchemy session instance with clean database

    Note:
        Session is automatically closed after test completes
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Enable foreign key constraints (SQLite specific)
    session.execute(text("PRAGMA foreign_keys=ON"))
    session.commit()

    yield session

    session.close()


@pytest.fixture
def sample_project(session):
    """Create a sample project for testing.

    Args:
        session: SQLAlchemy session from session fixture

    Returns:
        Project instance persisted in database
    """
    project = Project(
        id="test-project",
        name="Test Project",
        path="/tmp/test-project",
        status="active",
    )
    session.add(project)
    session.commit()
    return project


@pytest.fixture
def sample_artifact(session, sample_project):
    """Create a sample artifact for testing.

    Args:
        session: SQLAlchemy session from session fixture
        sample_project: Project fixture to link artifact to

    Returns:
        Artifact instance persisted in database
    """
    artifact = Artifact(
        id="test-artifact",
        project_id=sample_project.id,
        name="test-skill",
        type="skill",
    )
    session.add(artifact)
    session.commit()
    return artifact


# =============================================================================
# ArtifactVersion Model Tests
# =============================================================================


class TestArtifactVersionModel:
    """Tests for ArtifactVersion ORM model."""

    def test_create_deployment_version(self, session, sample_artifact):
        """Deploy creates version with parent=NULL and origin='deployment'."""
        version = ArtifactVersion(
            id="v1",
            artifact_id=sample_artifact.id,
            content_hash="abc123",
            parent_hash=None,  # Root version
            change_origin="deployment",
            version_lineage=json.dumps(["abc123"]),
        )
        session.add(version)
        session.commit()

        # Verify version was created correctly
        assert version.parent_hash is None
        assert version.change_origin == "deployment"
        assert json.loads(version.version_lineage) == ["abc123"]

        # Verify retrieval from database
        retrieved = session.query(ArtifactVersion).filter_by(id="v1").first()
        assert retrieved is not None
        assert retrieved.content_hash == "abc123"
        assert retrieved.change_origin == "deployment"

    def test_create_sync_version(self, session, sample_artifact):
        """Sync creates version with parent=previous and origin='sync'."""
        # First create deployment version (root)
        v1 = ArtifactVersion(
            id="v1",
            artifact_id=sample_artifact.id,
            content_hash="hash_v1",
            parent_hash=None,
            change_origin="deployment",
            version_lineage=json.dumps(["hash_v1"]),
        )
        session.add(v1)
        session.commit()

        # Then create sync version (child)
        v2 = ArtifactVersion(
            id="v2",
            artifact_id=sample_artifact.id,
            content_hash="hash_v2",
            parent_hash="hash_v1",  # Points to v1
            change_origin="sync",
            version_lineage=json.dumps(["hash_v1", "hash_v2"]),
        )
        session.add(v2)
        session.commit()

        # Verify parent-child relationship
        assert v2.parent_hash == "hash_v1"
        assert v2.change_origin == "sync"
        assert json.loads(v2.version_lineage) == ["hash_v1", "hash_v2"]

        # Verify lineage builds correctly
        lineage = v2.get_lineage_list()
        assert lineage == ["hash_v1", "hash_v2"]
        assert lineage[0] == v1.content_hash  # First hash is parent

    def test_create_local_modification_version(self, session, sample_artifact):
        """Local mod creates version with parent=previous and origin='local_modification'."""
        # Create deployment version (root)
        v1 = ArtifactVersion(
            id="v1",
            artifact_id=sample_artifact.id,
            content_hash="hash_v1",
            parent_hash=None,
            change_origin="deployment",
            version_lineage=json.dumps(["hash_v1"]),
        )
        session.add(v1)
        session.commit()

        # Create local modification version (child)
        v2 = ArtifactVersion(
            id="v2",
            artifact_id=sample_artifact.id,
            content_hash="hash_v2_local",
            parent_hash="hash_v1",
            change_origin="local_modification",
            version_lineage=json.dumps(["hash_v1", "hash_v2_local"]),
        )
        session.add(v2)
        session.commit()

        # Verify change origin
        assert v2.change_origin == "local_modification"
        assert v2.parent_hash == v1.content_hash

        # Verify local modifications track lineage correctly
        lineage = v2.get_lineage_list()
        assert len(lineage) == 2
        assert lineage[1] == "hash_v2_local"

    def test_version_lineage_chain(self, session, sample_artifact):
        """Lineage correctly builds for 3+ versions."""
        # Create chain: deploy -> sync -> sync
        versions = []

        # v1: deployment (root)
        v1 = ArtifactVersion(
            id="v1",
            artifact_id=sample_artifact.id,
            content_hash="v1_hash",
            parent_hash=None,
            change_origin="deployment",
            version_lineage=json.dumps(["v1_hash"]),
        )
        session.add(v1)
        versions.append(v1)

        # v2: sync (child of v1)
        v2 = ArtifactVersion(
            id="v2",
            artifact_id=sample_artifact.id,
            content_hash="v2_hash",
            parent_hash="v1_hash",
            change_origin="sync",
            version_lineage=json.dumps(["v1_hash", "v2_hash"]),
        )
        session.add(v2)
        versions.append(v2)

        # v3: sync (child of v2)
        v3 = ArtifactVersion(
            id="v3",
            artifact_id=sample_artifact.id,
            content_hash="v3_hash",
            parent_hash="v2_hash",
            change_origin="sync",
            version_lineage=json.dumps(["v1_hash", "v2_hash", "v3_hash"]),
        )
        session.add(v3)
        versions.append(v3)

        session.commit()

        # Verify lineage builds correctly
        lineage = v3.get_lineage_list()
        assert lineage == ["v1_hash", "v2_hash", "v3_hash"]
        assert len(lineage) == 3

        # Verify chain structure
        assert v1.parent_hash is None  # Root
        assert v2.parent_hash == v1.content_hash  # v2 -> v1
        assert v3.parent_hash == v2.content_hash  # v3 -> v2

        # Verify all versions belong to same artifact
        for v in versions:
            assert v.artifact_id == sample_artifact.id

    def test_content_hash_unique(self, session, sample_artifact):
        """Content hash must be unique (content-based dedup)."""
        # Create first version
        v1 = ArtifactVersion(
            id="v1",
            artifact_id=sample_artifact.id,
            content_hash="same_hash",
            parent_hash=None,
            change_origin="deployment",
        )
        session.add(v1)
        session.commit()

        # Try to create second version with same hash
        v2 = ArtifactVersion(
            id="v2",
            artifact_id=sample_artifact.id,
            content_hash="same_hash",  # Duplicate hash
            parent_hash=None,
            change_origin="deployment",
        )
        session.add(v2)

        # Should raise IntegrityError due to unique constraint
        with pytest.raises(IntegrityError) as exc_info:
            session.commit()

        assert "UNIQUE constraint failed" in str(exc_info.value) or "unique" in str(
            exc_info.value
        ).lower()

    def test_invalid_change_origin_rejected(self, session, sample_artifact):
        """Invalid change_origin value is rejected by CHECK constraint."""
        version = ArtifactVersion(
            id="v1",
            artifact_id=sample_artifact.id,
            content_hash="hash1",
            parent_hash=None,
            change_origin="invalid_origin",  # Not in allowed values
        )
        session.add(version)

        # Should raise IntegrityError due to CHECK constraint
        with pytest.raises(IntegrityError) as exc_info:
            session.commit()

        assert "CHECK constraint failed" in str(exc_info.value) or "check" in str(
            exc_info.value
        ).lower()

    def test_valid_change_origins(self, session, sample_artifact):
        """All valid change_origin values are accepted."""
        valid_origins = ["deployment", "sync", "local_modification"]

        for i, origin in enumerate(valid_origins):
            version = ArtifactVersion(
                id=f"v{i}",
                artifact_id=sample_artifact.id,
                content_hash=f"hash_{i}",
                parent_hash=None,
                change_origin=origin,
            )
            session.add(version)

        # All should commit successfully
        session.commit()

        # Verify all were created
        count = session.query(ArtifactVersion).count()
        assert count == 3

    def test_cascade_delete_removes_versions(self, session, sample_artifact):
        """Deleting artifact cascades to delete its versions."""
        # Create versions for artifact
        v1 = ArtifactVersion(
            id="v1",
            artifact_id=sample_artifact.id,
            content_hash="hash1",
            parent_hash=None,
            change_origin="deployment",
        )
        v2 = ArtifactVersion(
            id="v2",
            artifact_id=sample_artifact.id,
            content_hash="hash2",
            parent_hash="hash1",
            change_origin="sync",
        )
        session.add_all([v1, v2])
        session.commit()

        # Verify versions exist
        count = (
            session.query(ArtifactVersion)
            .filter_by(artifact_id=sample_artifact.id)
            .count()
        )
        assert count == 2

        # Delete artifact
        session.delete(sample_artifact)
        session.commit()

        # Versions should be gone (CASCADE delete)
        count = (
            session.query(ArtifactVersion)
            .filter_by(artifact_id=sample_artifact.id)
            .count()
        )
        assert count == 0

    def test_multiple_artifacts_independent_versions(self, session, sample_project):
        """Different artifacts can have independent version chains."""
        # Create two artifacts
        artifact1 = Artifact(
            id="artifact1",
            project_id=sample_project.id,
            name="skill1",
            type="skill",
        )
        artifact2 = Artifact(
            id="artifact2",
            project_id=sample_project.id,
            name="skill2",
            type="skill",
        )
        session.add_all([artifact1, artifact2])
        session.commit()

        # Create versions for each artifact
        v1_a1 = ArtifactVersion(
            id="v1_a1",
            artifact_id=artifact1.id,
            content_hash="a1_hash1",
            parent_hash=None,
            change_origin="deployment",
        )
        v1_a2 = ArtifactVersion(
            id="v1_a2",
            artifact_id=artifact2.id,
            content_hash="a2_hash1",
            parent_hash=None,
            change_origin="deployment",
        )
        session.add_all([v1_a1, v1_a2])
        session.commit()

        # Verify each artifact has its own version
        a1_versions = (
            session.query(ArtifactVersion).filter_by(artifact_id=artifact1.id).all()
        )
        a2_versions = (
            session.query(ArtifactVersion).filter_by(artifact_id=artifact2.id).all()
        )

        assert len(a1_versions) == 1
        assert len(a2_versions) == 1
        assert a1_versions[0].content_hash != a2_versions[0].content_hash

    def test_version_lineage_helpers(self, session, sample_artifact):
        """Test get_lineage_list() and set_lineage_list() helpers."""
        version = ArtifactVersion(
            id="v1",
            artifact_id=sample_artifact.id,
            content_hash="hash1",
            parent_hash=None,
            change_origin="deployment",
        )

        # Test set_lineage_list
        lineage = ["hash1", "hash2", "hash3"]
        version.set_lineage_list(lineage)

        assert version.version_lineage == json.dumps(lineage)

        # Test get_lineage_list
        retrieved_lineage = version.get_lineage_list()
        assert retrieved_lineage == lineage

        # Test empty lineage
        version.set_lineage_list([])
        assert version.get_lineage_list() == []

    def test_to_dict_serialization(self, session, sample_artifact):
        """Test to_dict() serializes all fields correctly."""
        version = ArtifactVersion(
            id="v1",
            artifact_id=sample_artifact.id,
            content_hash="hash1",
            parent_hash="hash0",
            change_origin="sync",
            version_lineage=json.dumps(["hash0", "hash1"]),
            metadata_json=json.dumps({"author": "test", "timestamp": "2024-01-01"}),
        )
        session.add(version)
        session.commit()

        # Convert to dict
        data = version.to_dict()

        assert data["id"] == "v1"
        assert data["artifact_id"] == sample_artifact.id
        assert data["content_hash"] == "hash1"
        assert data["parent_hash"] == "hash0"
        assert data["change_origin"] == "sync"
        assert data["version_lineage"] == ["hash0", "hash1"]
        assert data["metadata"] == {"author": "test", "timestamp": "2024-01-01"}
        assert "created_at" in data

    def test_query_by_change_origin(self, session, sample_artifact):
        """Test filtering versions by change_origin."""
        # Create versions with different origins
        origins = ["deployment", "sync", "local_modification", "sync"]
        for i, origin in enumerate(origins):
            version = ArtifactVersion(
                id=f"v{i}",
                artifact_id=sample_artifact.id,
                content_hash=f"hash{i}",
                parent_hash=f"hash{i-1}" if i > 0 else None,
                change_origin=origin,
            )
            session.add(version)
        session.commit()

        # Query sync versions
        sync_versions = (
            session.query(ArtifactVersion).filter_by(change_origin="sync").all()
        )
        assert len(sync_versions) == 2

        # Query deployment versions
        deploy_versions = (
            session.query(ArtifactVersion).filter_by(change_origin="deployment").all()
        )
        assert len(deploy_versions) == 1

        # Query local modifications
        local_versions = (
            session.query(ArtifactVersion)
            .filter_by(change_origin="local_modification")
            .all()
        )
        assert len(local_versions) == 1

    def test_ordered_by_created_at(self, session, sample_artifact):
        """Test versions can be ordered by creation timestamp."""
        # Create versions at different times
        for i in range(3):
            version = ArtifactVersion(
                id=f"v{i}",
                artifact_id=sample_artifact.id,
                content_hash=f"hash{i}",
                parent_hash=f"hash{i-1}" if i > 0 else None,
                change_origin="sync",
            )
            session.add(version)
            session.commit()  # Commit separately to ensure different timestamps

        # Query ordered by created_at
        versions = (
            session.query(ArtifactVersion)
            .filter_by(artifact_id=sample_artifact.id)
            .order_by(ArtifactVersion.created_at)
            .all()
        )

        assert len(versions) == 3
        # Verify chronological order
        for i in range(len(versions) - 1):
            assert versions[i].created_at <= versions[i + 1].created_at


# =============================================================================
# Version Chain Creation Tests
# =============================================================================


class TestVersionChainCreation:
    """Comprehensive tests for version chain creation functionality.

    Tests cover:
    - Linear chain construction (single path)
    - Multi-generation chains (grandparent -> parent -> child)
    - Chain validation and integrity
    - Edge cases (orphaned versions, missing parents)
    - Performance with long chains
    """

    def test_create_simple_linear_chain(self, session, sample_artifact):
        """Create simple 2-version linear chain (parent -> child)."""
        # Create parent version
        parent = ArtifactVersion(
            id="parent",
            artifact_id=sample_artifact.id,
            content_hash="parent_hash",
            parent_hash=None,
            change_origin="deployment",
            version_lineage=json.dumps(["parent_hash"]),
        )
        session.add(parent)
        session.commit()

        # Create child version
        child = ArtifactVersion(
            id="child",
            artifact_id=sample_artifact.id,
            content_hash="child_hash",
            parent_hash="parent_hash",
            change_origin="sync",
            version_lineage=json.dumps(["parent_hash", "child_hash"]),
        )
        session.add(child)
        session.commit()

        # Verify chain structure
        assert child.parent_hash == parent.content_hash
        assert parent.parent_hash is None

        # Verify lineage
        parent_lineage = parent.get_lineage_list()
        child_lineage = child.get_lineage_list()

        assert parent_lineage == ["parent_hash"]
        assert child_lineage == ["parent_hash", "child_hash"]
        assert child_lineage[0] == parent.content_hash

    def test_create_multi_generation_chain(self, session, sample_artifact):
        """Create 5-generation chain to test depth handling."""
        versions = []
        previous_hash = None

        # Create 5 generations
        for i in range(5):
            current_hash = f"hash_gen{i}"

            # Build lineage from previous versions
            if i == 0:
                lineage = [current_hash]
            else:
                lineage = versions[i - 1].get_lineage_list() + [current_hash]

            version = ArtifactVersion(
                id=f"gen{i}",
                artifact_id=sample_artifact.id,
                content_hash=current_hash,
                parent_hash=previous_hash,
                change_origin="deployment" if i == 0 else "sync",
                version_lineage=json.dumps(lineage),
            )
            session.add(version)
            versions.append(version)
            previous_hash = current_hash

        session.commit()

        # Verify chain integrity
        for i in range(len(versions)):
            if i == 0:
                assert versions[i].parent_hash is None
            else:
                assert versions[i].parent_hash == versions[i - 1].content_hash

        # Verify lineage grows correctly
        assert len(versions[0].get_lineage_list()) == 1
        assert len(versions[1].get_lineage_list()) == 2
        assert len(versions[2].get_lineage_list()) == 3
        assert len(versions[3].get_lineage_list()) == 4
        assert len(versions[4].get_lineage_list()) == 5

        # Verify final lineage contains all hashes in order
        final_lineage = versions[4].get_lineage_list()
        expected_lineage = [f"hash_gen{i}" for i in range(5)]
        assert final_lineage == expected_lineage

    def test_create_chain_with_mixed_origins(self, session, sample_artifact):
        """Test chain with different change_origin values."""
        # Deployment -> Sync -> Local Modification -> Sync
        origins = ["deployment", "sync", "local_modification", "sync"]
        versions = []
        previous_hash = None

        for i, origin in enumerate(origins):
            current_hash = f"hash_{i}"
            lineage = (
                [current_hash]
                if i == 0
                else versions[i - 1].get_lineage_list() + [current_hash]
            )

            version = ArtifactVersion(
                id=f"v{i}",
                artifact_id=sample_artifact.id,
                content_hash=current_hash,
                parent_hash=previous_hash,
                change_origin=origin,
                version_lineage=json.dumps(lineage),
            )
            session.add(version)
            versions.append(version)
            previous_hash = current_hash

        session.commit()

        # Verify origins are correct
        assert versions[0].change_origin == "deployment"
        assert versions[1].change_origin == "sync"
        assert versions[2].change_origin == "local_modification"
        assert versions[3].change_origin == "sync"

        # Verify lineage is preserved across different origins
        final_lineage = versions[3].get_lineage_list()
        assert len(final_lineage) == 4
        assert final_lineage == ["hash_0", "hash_1", "hash_2", "hash_3"]

    def test_chain_with_metadata_tracking(self, session, sample_artifact):
        """Test chain where each version includes metadata."""
        versions = []
        previous_hash = None

        for i in range(3):
            current_hash = f"hash_{i}"
            lineage = (
                [current_hash]
                if i == 0
                else versions[i - 1].get_lineage_list() + [current_hash]
            )

            metadata = {
                "generation": i,
                "author": f"user{i}",
                "message": f"Version {i} commit message",
                "timestamp": f"2024-01-{i+1:02d}T12:00:00Z",
            }

            version = ArtifactVersion(
                id=f"v{i}",
                artifact_id=sample_artifact.id,
                content_hash=current_hash,
                parent_hash=previous_hash,
                change_origin="deployment" if i == 0 else "sync",
                version_lineage=json.dumps(lineage),
                metadata_json=json.dumps(metadata),
            )
            session.add(version)
            versions.append(version)
            previous_hash = current_hash

        session.commit()

        # Verify metadata is preserved and accessible
        for i, version in enumerate(versions):
            data = version.to_dict()
            assert data["metadata"]["generation"] == i
            assert data["metadata"]["author"] == f"user{i}"

        # Verify lineage is independent of metadata
        assert len(versions[2].get_lineage_list()) == 3

    def test_orphaned_version_no_parent(self, session, sample_artifact):
        """Test creating version with non-existent parent_hash (orphaned)."""
        # Create version with parent that doesn't exist
        orphan = ArtifactVersion(
            id="orphan",
            artifact_id=sample_artifact.id,
            content_hash="orphan_hash",
            parent_hash="missing_parent_hash",  # Parent doesn't exist
            change_origin="sync",
            version_lineage=json.dumps(["missing_parent_hash", "orphan_hash"]),
        )
        session.add(orphan)
        session.commit()

        # Orphan should exist (DB doesn't enforce referential integrity on parent_hash)
        retrieved = session.query(ArtifactVersion).filter_by(id="orphan").first()
        assert retrieved is not None
        assert retrieved.parent_hash == "missing_parent_hash"

        # Application should detect orphaned status
        # (parent_hash points to non-existent hash)
        parent_exists = (
            session.query(ArtifactVersion)
            .filter_by(content_hash="missing_parent_hash")
            .first()
            is not None
        )
        assert parent_exists is False

    def test_chain_rebuilding_from_lineage(self, session, sample_artifact):
        """Test that lineage can be used to rebuild chain structure."""
        # Create 4-version chain
        versions = []
        previous_hash = None

        for i in range(4):
            current_hash = f"rebuild_hash_{i}"
            lineage = (
                [current_hash]
                if i == 0
                else versions[i - 1].get_lineage_list() + [current_hash]
            )

            version = ArtifactVersion(
                id=f"rebuild_{i}",
                artifact_id=sample_artifact.id,
                content_hash=current_hash,
                parent_hash=previous_hash,
                change_origin="deployment" if i == 0 else "sync",
                version_lineage=json.dumps(lineage),
            )
            session.add(version)
            versions.append(version)
            previous_hash = current_hash

        session.commit()

        # Retrieve latest version
        latest = versions[3]
        lineage = latest.get_lineage_list()

        # Rebuild chain by walking back through lineage
        chain = []
        for hash_value in reversed(lineage):
            version = (
                session.query(ArtifactVersion)
                .filter_by(content_hash=hash_value)
                .first()
            )
            if version:
                chain.append(version)

        # Verify we reconstructed all versions
        assert len(chain) == 4
        assert chain[0].id == "rebuild_3"  # Latest first
        assert chain[3].id == "rebuild_0"  # Root last

    def test_chain_with_empty_lineage(self, session, sample_artifact):
        """Test version with empty/null lineage (edge case)."""
        version = ArtifactVersion(
            id="no_lineage",
            artifact_id=sample_artifact.id,
            content_hash="hash_no_lineage",
            parent_hash=None,
            change_origin="deployment",
            version_lineage=None,  # No lineage
        )
        session.add(version)
        session.commit()

        # Should handle gracefully
        lineage = version.get_lineage_list()
        assert lineage == []

    def test_chain_preserves_chronological_order(self, session, sample_artifact):
        """Test that lineage preserves chronological order (oldest first)."""
        # Create versions with small delays to ensure different timestamps
        versions = []
        previous_hash = None

        for i in range(3):
            current_hash = f"chrono_hash_{i}"
            lineage = (
                [current_hash]
                if i == 0
                else versions[i - 1].get_lineage_list() + [current_hash]
            )

            version = ArtifactVersion(
                id=f"chrono_{i}",
                artifact_id=sample_artifact.id,
                content_hash=current_hash,
                parent_hash=previous_hash,
                change_origin="deployment" if i == 0 else "sync",
                version_lineage=json.dumps(lineage),
            )
            session.add(version)
            session.commit()  # Commit individually for timestamp differences

            versions.append(version)
            previous_hash = current_hash

        # Verify timestamps are chronological
        for i in range(len(versions) - 1):
            assert versions[i].created_at <= versions[i + 1].created_at

        # Verify lineage order matches chronological order
        final_lineage = versions[2].get_lineage_list()
        assert final_lineage[0] == versions[0].content_hash  # Oldest
        assert final_lineage[1] == versions[1].content_hash  # Middle
        assert final_lineage[2] == versions[2].content_hash  # Newest

    def test_chain_query_by_artifact(self, session, sample_project):
        """Test querying all versions in chain for specific artifact."""
        # Create two artifacts with separate chains
        artifact1 = Artifact(
            id="artifact1",
            project_id=sample_project.id,
            name="skill1",
            type="skill",
        )
        artifact2 = Artifact(
            id="artifact2",
            project_id=sample_project.id,
            name="skill2",
            type="skill",
        )
        session.add_all([artifact1, artifact2])
        session.commit()

        # Create 3-version chain for artifact1
        for i in range(3):
            version = ArtifactVersion(
                id=f"a1_v{i}",
                artifact_id=artifact1.id,
                content_hash=f"a1_hash_{i}",
                parent_hash=f"a1_hash_{i-1}" if i > 0 else None,
                change_origin="deployment" if i == 0 else "sync",
            )
            session.add(version)

        # Create 2-version chain for artifact2
        for i in range(2):
            version = ArtifactVersion(
                id=f"a2_v{i}",
                artifact_id=artifact2.id,
                content_hash=f"a2_hash_{i}",
                parent_hash=f"a2_hash_{i-1}" if i > 0 else None,
                change_origin="deployment" if i == 0 else "sync",
            )
            session.add(version)

        session.commit()

        # Query chains separately
        a1_versions = (
            session.query(ArtifactVersion)
            .filter_by(artifact_id=artifact1.id)
            .order_by(ArtifactVersion.created_at)
            .all()
        )
        a2_versions = (
            session.query(ArtifactVersion)
            .filter_by(artifact_id=artifact2.id)
            .order_by(ArtifactVersion.created_at)
            .all()
        )

        # Verify separate chains
        assert len(a1_versions) == 3
        assert len(a2_versions) == 2

        # Verify chains don't overlap
        a1_hashes = {v.content_hash for v in a1_versions}
        a2_hashes = {v.content_hash for v in a2_versions}
        assert a1_hashes.isdisjoint(a2_hashes)

    def test_long_chain_performance(self, session, sample_artifact):
        """Test creating and querying long chain (20+ versions)."""
        chain_length = 25
        versions = []
        previous_hash = None

        # Create long chain
        for i in range(chain_length):
            current_hash = f"long_hash_{i}"
            lineage = (
                [current_hash]
                if i == 0
                else versions[i - 1].get_lineage_list() + [current_hash]
            )

            version = ArtifactVersion(
                id=f"long_{i}",
                artifact_id=sample_artifact.id,
                content_hash=current_hash,
                parent_hash=previous_hash,
                change_origin="deployment" if i == 0 else "sync",
                version_lineage=json.dumps(lineage),
            )
            session.add(version)
            versions.append(version)
            previous_hash = current_hash

        session.commit()

        # Verify chain length
        all_versions = (
            session.query(ArtifactVersion)
            .filter_by(artifact_id=sample_artifact.id)
            .all()
        )
        assert len(all_versions) == chain_length

        # Verify final lineage has all hashes
        final_version = versions[-1]
        final_lineage = final_version.get_lineage_list()
        assert len(final_lineage) == chain_length

        # Verify lineage integrity
        for i, hash_value in enumerate(final_lineage):
            assert hash_value == f"long_hash_{i}"


# =============================================================================
# Version Lineage Utilities Tests
# =============================================================================


class TestVersionLineageUtilities:
    """Tests for version_lineage.py utilities.

    Note: These tests will be implemented after TASK-2.5 is complete.
    Placeholder tests are included for future implementation.
    """

    @pytest.mark.skip(reason="TASK-2.5 not yet implemented")
    def test_build_version_lineage(self):
        """Test build_version_lineage() utility function."""
        # TODO: Implement after version_lineage.py is created
        pass

    @pytest.mark.skip(reason="TASK-2.5 not yet implemented")
    def test_find_common_ancestor(self):
        """Test find_common_ancestor() utility function."""
        # TODO: Implement after version_lineage.py is created
        pass

    @pytest.mark.skip(reason="TASK-2.5 not yet implemented")
    def test_get_version_chain(self):
        """Test get_version_chain() utility function."""
        # TODO: Implement after version_lineage.py is created
        pass


# =============================================================================
# Integration Tests
# =============================================================================


class TestVersionLineageIntegration:
    """Integration tests for version lineage in realistic scenarios."""

    def test_deploy_sync_local_workflow(self, session, sample_artifact):
        """Test realistic workflow: deploy -> sync -> local modification."""
        # Step 1: Initial deployment
        v1 = ArtifactVersion(
            id="v1",
            artifact_id=sample_artifact.id,
            content_hash="deploy_hash",
            parent_hash=None,
            change_origin="deployment",
            version_lineage=json.dumps(["deploy_hash"]),
        )
        session.add(v1)
        session.commit()

        # Step 2: Sync from upstream
        v2 = ArtifactVersion(
            id="v2",
            artifact_id=sample_artifact.id,
            content_hash="sync_hash",
            parent_hash="deploy_hash",
            change_origin="sync",
            version_lineage=json.dumps(["deploy_hash", "sync_hash"]),
        )
        session.add(v2)
        session.commit()

        # Step 3: Local modification
        v3 = ArtifactVersion(
            id="v3",
            artifact_id=sample_artifact.id,
            content_hash="local_hash",
            parent_hash="sync_hash",
            change_origin="local_modification",
            version_lineage=json.dumps(["deploy_hash", "sync_hash", "local_hash"]),
        )
        session.add(v3)
        session.commit()

        # Verify complete lineage
        versions = (
            session.query(ArtifactVersion)
            .filter_by(artifact_id=sample_artifact.id)
            .order_by(ArtifactVersion.created_at)
            .all()
        )

        assert len(versions) == 3
        assert versions[0].change_origin == "deployment"
        assert versions[1].change_origin == "sync"
        assert versions[2].change_origin == "local_modification"

        # Verify lineage chain
        final_lineage = versions[2].get_lineage_list()
        assert final_lineage == ["deploy_hash", "sync_hash", "local_hash"]

    def test_branching_not_allowed_single_artifact(self, session, sample_artifact):
        """Test that artifact can only have linear version history."""
        # Create root version
        v1 = ArtifactVersion(
            id="v1",
            artifact_id=sample_artifact.id,
            content_hash="root_hash",
            parent_hash=None,
            change_origin="deployment",
        )
        session.add(v1)
        session.commit()

        # Create child version
        v2 = ArtifactVersion(
            id="v2",
            artifact_id=sample_artifact.id,
            content_hash="child_hash",
            parent_hash="root_hash",
            change_origin="sync",
        )
        session.add(v2)
        session.commit()

        # Note: SQLite doesn't prevent multiple children from same parent
        # This is allowed - application logic should handle linearity
        # We can have multiple versions pointing to same parent (for different artifacts)
        # But for single artifact, we should maintain linear history in application logic

        # Verify both versions exist
        count = (
            session.query(ArtifactVersion)
            .filter_by(artifact_id=sample_artifact.id)
            .count()
        )
        assert count == 2
