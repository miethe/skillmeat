"""Unit tests for deployment version tracking integration.

Tests the _record_deployment_version method of DeploymentManager.
"""

import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from skillmeat.cache.models import (
    Artifact,
    ArtifactVersion,
    Project,
    create_tables,
    get_session,
    init_session_factory,
)
from skillmeat.core.deployment import DeploymentManager


@pytest.fixture
def test_db(tmp_path):
    """Create test database."""
    db_path = tmp_path / "test_cache.db"
    create_tables(db_path)
    init_session_factory(db_path)
    yield db_path


@pytest.fixture
def test_project(test_db, tmp_path):
    """Create test project in database."""
    project_path = tmp_path / "project"
    project_path.mkdir()

    session = get_session(test_db)
    try:
        project = Project(
            id=uuid.uuid4().hex,
            name="Test Project",
            path=str(project_path),
            status="active",
        )
        session.add(project)
        session.commit()

        # Store the ID before closing session
        project_id = project.id
        return project_id, project_path
    finally:
        session.close()


@pytest.fixture
def test_artifact(test_db, test_project):
    """Create test artifact in database."""
    project_id, project_path = test_project

    session = get_session(test_db)
    try:
        artifact = Artifact(
            id=uuid.uuid4().hex,
            project_id=project_id,
            name="test-skill",
            type="skill",
        )
        session.add(artifact)
        session.commit()

        # Store the ID before closing session
        artifact_id = artifact.id
        return artifact_id, project_id, project_path
    finally:
        session.close()


class TestDeploymentVersionIntegration:
    """Tests for deployment version tracking integration."""

    def test_record_deployment_version_creates_version(
        self, test_db, test_artifact
    ):
        """Test that _record_deployment_version creates an ArtifactVersion record."""
        artifact_id, project_id, project_path = test_artifact

        # Create deployment manager
        deploy_mgr = DeploymentManager()

        # Record deployment version
        content_hash = "abc123def456"
        deploy_mgr._record_deployment_version(
            artifact_name="test-skill",
            artifact_type="skill",
            project_path=project_path,
            content_hash=content_hash,
        )

        # Verify version was created
        session = get_session(test_db)
        try:
            version = (
                session.query(ArtifactVersion)
                .filter_by(artifact_id=artifact_id)
                .first()
            )

            assert version is not None
            assert version.content_hash == content_hash
            assert version.parent_hash is None  # Root version
            assert version.change_origin == "deployment"

            lineage = json.loads(version.version_lineage)
            assert lineage == [content_hash]

        finally:
            session.close()

    def test_record_deployment_version_is_idempotent(
        self, test_db, test_artifact
    ):
        """Test that recording same version twice doesn't create duplicates."""
        artifact_id, project_id, project_path = test_artifact

        deploy_mgr = DeploymentManager()
        content_hash = "abc123def456"

        # Record twice
        deploy_mgr._record_deployment_version(
            artifact_name="test-skill",
            artifact_type="skill",
            project_path=project_path,
            content_hash=content_hash,
        )

        deploy_mgr._record_deployment_version(
            artifact_name="test-skill",
            artifact_type="skill",
            project_path=project_path,
            content_hash=content_hash,
        )

        # Verify only one version exists
        session = get_session(test_db)
        try:
            versions = (
                session.query(ArtifactVersion)
                .filter_by(artifact_id=artifact_id)
                .all()
            )

            assert len(versions) == 1

        finally:
            session.close()

    def test_record_deployment_version_without_cache_artifact(
        self, test_db, test_project, capsys
    ):
        """Test that recording version without cache artifact prints warning."""
        project, project_path = test_project

        deploy_mgr = DeploymentManager()

        # Try to record version for non-existent artifact
        deploy_mgr._record_deployment_version(
            artifact_name="nonexistent-skill",
            artifact_type="skill",
            project_path=project_path,
            content_hash="abc123",
        )

        # Verify no version was created
        session = get_session(test_db)
        try:
            versions = session.query(ArtifactVersion).all()
            assert len(versions) == 0

        finally:
            session.close()

        # Check that warning was printed
        captured = capsys.readouterr()
        assert "not in cache yet" in captured.out

    def test_record_deployment_version_handles_errors_gracefully(
        self, test_db, test_artifact, monkeypatch, capsys
    ):
        """Test that errors in version tracking don't break deployment."""
        artifact_id, project_id, project_path = test_artifact

        deploy_mgr = DeploymentManager()

        # Mock get_session to raise an exception
        def mock_get_session(*args, **kwargs):
            raise RuntimeError("Database connection failed")

        monkeypatch.setattr(
            "skillmeat.cache.models.get_session", mock_get_session
        )

        # Should not raise, just print warning
        deploy_mgr._record_deployment_version(
            artifact_name="test-skill",
            artifact_type="skill",
            project_path=project_path,
            content_hash="abc123",
        )

        # Verify warning was printed
        captured = capsys.readouterr()
        assert "Warning: Failed to record deployment version" in captured.out

    def test_multiple_deployments_create_one_version(
        self, test_db, test_artifact
    ):
        """Test that deploying same content twice only creates one version."""
        artifact_id, project_id, project_path = test_artifact

        deploy_mgr = DeploymentManager()
        content_hash = "same_hash_123"

        # Deploy same content twice
        for _ in range(2):
            deploy_mgr._record_deployment_version(
                artifact_name="test-skill",
                artifact_type="skill",
                project_path=project_path,
                content_hash=content_hash,
            )

        # Verify only one version
        session = get_session(test_db)
        try:
            versions = session.query(ArtifactVersion).all()
            assert len(versions) == 1
            assert versions[0].content_hash == content_hash

        finally:
            session.close()

    def test_different_content_creates_new_versions(
        self, test_db, test_artifact
    ):
        """Test that different content hashes create separate versions."""
        artifact_id, project_id, project_path = test_artifact

        deploy_mgr = DeploymentManager()

        # Deploy different versions
        hash1 = "hash_v1"
        hash2 = "hash_v2"

        deploy_mgr._record_deployment_version(
            artifact_name="test-skill",
            artifact_type="skill",
            project_path=project_path,
            content_hash=hash1,
        )

        deploy_mgr._record_deployment_version(
            artifact_name="test-skill",
            artifact_type="skill",
            project_path=project_path,
            content_hash=hash2,
        )

        # Verify two versions exist
        session = get_session(test_db)
        try:
            versions = session.query(ArtifactVersion).order_by(
                ArtifactVersion.created_at
            ).all()

            assert len(versions) == 2
            assert versions[0].content_hash == hash1
            assert versions[1].content_hash == hash2

            # Both should be root versions (deployment origin)
            assert versions[0].parent_hash is None
            assert versions[1].parent_hash is None

        finally:
            session.close()
