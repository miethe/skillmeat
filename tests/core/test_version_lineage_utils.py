"""Tests for version lineage utilities.

Tests build_version_lineage, find_common_ancestor, and other lineage functions.
"""

import json
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from skillmeat.cache.models import Base, Artifact, ArtifactVersion
from skillmeat.core.version_lineage import (
    build_version_lineage,
    find_common_ancestor,
    get_version_chain,
    get_latest_version,
    version_exists,
    get_version_by_hash,
    get_lineage_depth,
    get_root_version,
    trace_lineage_path,
)


@pytest.fixture
def session():
    """Create in-memory database session for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    session.close()


@pytest.fixture
def sample_artifact(session):
    """Create sample artifact for testing."""
    artifact = Artifact(
        id="artifact_test123",
        project_id="project_test123",
        name="test-skill",
        type="skill",
        source="github:test/repo",
    )
    session.add(artifact)
    session.commit()
    return artifact


class TestBuildVersionLineage:
    """Test build_version_lineage function."""

    def test_root_version_no_parent(self, session):
        """Root version (deployment) should have lineage = [current_hash]."""
        lineage = build_version_lineage(session, None, "abc123")
        assert lineage == ["abc123"]

    def test_child_version_with_parent_lineage(self, session, sample_artifact):
        """Child version should extend parent's lineage."""
        # Create parent version with lineage
        parent = ArtifactVersion(
            artifact_id=sample_artifact.id,
            content_hash="parent_hash",
            parent_hash=None,
            change_origin="deployment",
            version_lineage=json.dumps(["root_hash", "parent_hash"]),
        )
        session.add(parent)
        session.commit()

        # Build child lineage
        lineage = build_version_lineage(session, "parent_hash", "child_hash")
        assert lineage == ["root_hash", "parent_hash", "child_hash"]

    def test_child_version_parent_without_lineage(self, session, sample_artifact):
        """Legacy parent without lineage should create minimal chain."""
        # Create parent without lineage (legacy)
        parent = ArtifactVersion(
            artifact_id=sample_artifact.id,
            content_hash="parent_hash",
            parent_hash=None,
            change_origin="deployment",
            version_lineage=None,
        )
        session.add(parent)
        session.commit()

        # Build child lineage
        lineage = build_version_lineage(session, "parent_hash", "child_hash")
        assert lineage == ["parent_hash", "child_hash"]

    def test_orphaned_child_missing_parent(self, session):
        """Child with missing parent should be treated as orphan."""
        lineage = build_version_lineage(session, "missing_parent", "child_hash")
        assert lineage == ["child_hash"]


class TestFindCommonAncestor:
    """Test find_common_ancestor function."""

    def test_common_ancestor_shared_history(self, session, sample_artifact):
        """Should find most recent common ancestor."""
        # Create version tree:
        #   root -> v1 -> v2-local
        #            \--> v2-remote
        root = ArtifactVersion(
            artifact_id=sample_artifact.id,
            content_hash="root",
            parent_hash=None,
            change_origin="deployment",
            version_lineage=json.dumps(["root"]),
        )
        v1 = ArtifactVersion(
            artifact_id=sample_artifact.id,
            content_hash="v1",
            parent_hash="root",
            change_origin="sync",
            version_lineage=json.dumps(["root", "v1"]),
        )
        v2_local = ArtifactVersion(
            artifact_id=sample_artifact.id,
            content_hash="v2-local",
            parent_hash="v1",
            change_origin="local_modification",
            version_lineage=json.dumps(["root", "v1", "v2-local"]),
        )
        v2_remote = ArtifactVersion(
            artifact_id=sample_artifact.id,
            content_hash="v2-remote",
            parent_hash="v1",
            change_origin="sync",
            version_lineage=json.dumps(["root", "v1", "v2-remote"]),
        )
        session.add_all([root, v1, v2_local, v2_remote])
        session.commit()

        # Find common ancestor
        ancestor = find_common_ancestor(session, "v2-local", "v2-remote")
        assert ancestor == "v1"

    def test_unrelated_versions_no_ancestor(self, session, sample_artifact):
        """Unrelated versions should return None."""
        v1 = ArtifactVersion(
            artifact_id=sample_artifact.id,
            content_hash="orphan-a",
            parent_hash=None,
            change_origin="deployment",
            version_lineage=json.dumps(["orphan-a"]),
        )
        v2 = ArtifactVersion(
            artifact_id=sample_artifact.id,
            content_hash="orphan-b",
            parent_hash=None,
            change_origin="deployment",
            version_lineage=json.dumps(["orphan-b"]),
        )
        session.add_all([v1, v2])
        session.commit()

        ancestor = find_common_ancestor(session, "orphan-a", "orphan-b")
        assert ancestor is None

    def test_missing_version_returns_none(self, session):
        """Missing version should return None."""
        ancestor = find_common_ancestor(session, "missing-a", "missing-b")
        assert ancestor is None

    def test_empty_lineage_returns_none(self, session, sample_artifact):
        """Empty lineage should return None."""
        v1 = ArtifactVersion(
            artifact_id=sample_artifact.id,
            content_hash="no-lineage",
            parent_hash=None,
            change_origin="deployment",
            version_lineage=None,
        )
        session.add(v1)
        session.commit()

        ancestor = find_common_ancestor(session, "no-lineage", "no-lineage")
        assert ancestor is None


class TestGetVersionChain:
    """Test get_version_chain function."""

    def test_returns_versions_chronologically(self, session, sample_artifact):
        """Should return versions ordered by creation time."""
        # Create versions with different timestamps
        v1 = ArtifactVersion(
            artifact_id=sample_artifact.id,
            content_hash="v1",
            parent_hash=None,
            change_origin="deployment",
            created_at=datetime(2025, 1, 1, 10, 0),
        )
        v2 = ArtifactVersion(
            artifact_id=sample_artifact.id,
            content_hash="v2",
            parent_hash="v1",
            change_origin="sync",
            created_at=datetime(2025, 1, 1, 11, 0),
        )
        v3 = ArtifactVersion(
            artifact_id=sample_artifact.id,
            content_hash="v3",
            parent_hash="v2",
            change_origin="local_modification",
            created_at=datetime(2025, 1, 1, 12, 0),
        )
        session.add_all([v3, v1, v2])  # Add out of order
        session.commit()

        chain = get_version_chain(session, sample_artifact.id)
        assert len(chain) == 3
        assert [v.content_hash for v in chain] == ["v1", "v2", "v3"]

    def test_empty_chain_for_no_versions(self, session, sample_artifact):
        """Should return empty list if no versions exist."""
        chain = get_version_chain(session, sample_artifact.id)
        assert chain == []


class TestGetLatestVersion:
    """Test get_latest_version function."""

    def test_returns_most_recent_version(self, session, sample_artifact):
        """Should return version with latest timestamp."""
        v1 = ArtifactVersion(
            artifact_id=sample_artifact.id,
            content_hash="v1",
            parent_hash=None,
            change_origin="deployment",
            created_at=datetime(2025, 1, 1, 10, 0),
        )
        v2 = ArtifactVersion(
            artifact_id=sample_artifact.id,
            content_hash="v2",
            parent_hash="v1",
            change_origin="sync",
            created_at=datetime(2025, 1, 1, 11, 0),
        )
        session.add_all([v1, v2])
        session.commit()

        latest = get_latest_version(session, sample_artifact.id)
        assert latest is not None
        assert latest.content_hash == "v2"

    def test_returns_none_for_no_versions(self, session, sample_artifact):
        """Should return None if no versions exist."""
        latest = get_latest_version(session, sample_artifact.id)
        assert latest is None


class TestVersionExists:
    """Test version_exists function."""

    def test_returns_true_for_existing_version(self, session, sample_artifact):
        """Should return True if version exists."""
        version = ArtifactVersion(
            artifact_id=sample_artifact.id,
            content_hash="exists",
            parent_hash=None,
            change_origin="deployment",
        )
        session.add(version)
        session.commit()

        assert version_exists(session, "exists") is True

    def test_returns_false_for_missing_version(self, session):
        """Should return False if version doesn't exist."""
        assert version_exists(session, "missing") is False


class TestGetVersionByHash:
    """Test get_version_by_hash function."""

    def test_returns_version_by_hash(self, session, sample_artifact):
        """Should retrieve version by content hash."""
        version = ArtifactVersion(
            artifact_id=sample_artifact.id,
            content_hash="test-hash",
            parent_hash=None,
            change_origin="deployment",
        )
        session.add(version)
        session.commit()

        retrieved = get_version_by_hash(session, "test-hash")
        assert retrieved is not None
        assert retrieved.content_hash == "test-hash"

    def test_returns_none_for_missing_hash(self, session):
        """Should return None for missing hash."""
        retrieved = get_version_by_hash(session, "missing-hash")
        assert retrieved is None


class TestGetLineageDepth:
    """Test get_lineage_depth function."""

    def test_root_has_depth_zero(self, session, sample_artifact):
        """Root version should have depth 0."""
        root = ArtifactVersion(
            artifact_id=sample_artifact.id,
            content_hash="root",
            parent_hash=None,
            change_origin="deployment",
            version_lineage=json.dumps(["root"]),
        )
        session.add(root)
        session.commit()

        depth = get_lineage_depth(session, "root")
        assert depth == 0

    def test_child_has_correct_depth(self, session, sample_artifact):
        """Child version should have depth = generations from root."""
        v1 = ArtifactVersion(
            artifact_id=sample_artifact.id,
            content_hash="v1",
            parent_hash=None,
            change_origin="deployment",
            version_lineage=json.dumps(["root", "v1"]),
        )
        session.add(v1)
        session.commit()

        depth = get_lineage_depth(session, "v1")
        assert depth == 1


class TestGetRootVersion:
    """Test get_root_version function."""

    def test_returns_earliest_version(self, session, sample_artifact):
        """Should return version with earliest timestamp."""
        v1 = ArtifactVersion(
            artifact_id=sample_artifact.id,
            content_hash="v1",
            parent_hash=None,
            change_origin="deployment",
            created_at=datetime(2025, 1, 1, 10, 0),
        )
        v2 = ArtifactVersion(
            artifact_id=sample_artifact.id,
            content_hash="v2",
            parent_hash="v1",
            change_origin="sync",
            created_at=datetime(2025, 1, 1, 11, 0),
        )
        session.add_all([v2, v1])  # Add out of order
        session.commit()

        root = get_root_version(session, sample_artifact.id)
        assert root is not None
        assert root.content_hash == "v1"


class TestTraceLineagePath:
    """Test trace_lineage_path function."""

    def test_forward_path(self, session, sample_artifact):
        """Should trace path from ancestor to descendant."""
        # Create all versions in the chain
        root = ArtifactVersion(
            artifact_id=sample_artifact.id,
            content_hash="root",
            parent_hash=None,
            change_origin="deployment",
            version_lineage=json.dumps(["root"]),
        )
        v1 = ArtifactVersion(
            artifact_id=sample_artifact.id,
            content_hash="v1",
            parent_hash="root",
            change_origin="sync",
            version_lineage=json.dumps(["root", "v1"]),
        )
        v2 = ArtifactVersion(
            artifact_id=sample_artifact.id,
            content_hash="v2",
            parent_hash="v1",
            change_origin="sync",
            version_lineage=json.dumps(["root", "v1", "v2"]),
        )
        current = ArtifactVersion(
            artifact_id=sample_artifact.id,
            content_hash="current",
            parent_hash="v2",
            change_origin="sync",
            version_lineage=json.dumps(["root", "v1", "v2", "current"]),
        )
        session.add_all([root, v1, v2, current])
        session.commit()

        path = trace_lineage_path(session, "root", "current")
        assert path == ["root", "v1", "v2", "current"]

    def test_backward_path(self, session, sample_artifact):
        """Should trace path from descendant to ancestor."""
        # Create all versions in the chain
        root = ArtifactVersion(
            artifact_id=sample_artifact.id,
            content_hash="root",
            parent_hash=None,
            change_origin="deployment",
            version_lineage=json.dumps(["root"]),
        )
        v1 = ArtifactVersion(
            artifact_id=sample_artifact.id,
            content_hash="v1",
            parent_hash="root",
            change_origin="sync",
            version_lineage=json.dumps(["root", "v1"]),
        )
        v2 = ArtifactVersion(
            artifact_id=sample_artifact.id,
            content_hash="v2",
            parent_hash="v1",
            change_origin="sync",
            version_lineage=json.dumps(["root", "v1", "v2"]),
        )
        current = ArtifactVersion(
            artifact_id=sample_artifact.id,
            content_hash="current",
            parent_hash="v2",
            change_origin="sync",
            version_lineage=json.dumps(["root", "v1", "v2", "current"]),
        )
        session.add_all([root, v1, v2, current])
        session.commit()

        path = trace_lineage_path(session, "current", "root")
        assert path == ["current", "v2", "v1", "root"]

    def test_no_path_for_unrelated_versions(self, session, sample_artifact):
        """Should return None for unrelated versions."""
        version = ArtifactVersion(
            artifact_id=sample_artifact.id,
            content_hash="current",
            parent_hash="v1",
            change_origin="sync",
            version_lineage=json.dumps(["root", "v1", "current"]),
        )
        session.add(version)
        session.commit()

        path = trace_lineage_path(session, "unrelated", "current")
        assert path is None
