"""Integration tests for deployment version tracking.

Tests that ArtifactVersion records are created when artifacts are deployed.
"""

import json
import uuid
from pathlib import Path

import pytest

from skillmeat.cache.models import (
    Artifact,
    ArtifactVersion,
    Project,
    create_tables,
    get_session,
    init_session_factory,
)
from skillmeat.core.artifact import Artifact as CoreArtifact
from skillmeat.core.artifact import ArtifactType
from skillmeat.core.collection import Collection, CollectionManager
from skillmeat.core.deployment import DeploymentManager


@pytest.fixture
def test_db(tmp_path):
    """Create test database."""
    db_path = tmp_path / "test_cache.db"
    create_tables(db_path)
    init_session_factory(db_path)
    yield db_path


@pytest.fixture
def collection_dir(tmp_path):
    """Create test collection directory."""
    coll_dir = tmp_path / "collection"
    coll_dir.mkdir()

    # Create skills directory
    skills_dir = coll_dir / "artifacts" / "skills"
    skills_dir.mkdir(parents=True)

    # Create minimal skill
    skill_dir = skills_dir / "test-skill"
    skill_dir.mkdir()

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        """---
name: test-skill
description: Test skill for deployment
version: 1.0.0
---

# Test Skill

This is a test skill.
"""
    )

    # Create collection manifest
    manifest = coll_dir / "manifest.toml"
    manifest.write_text(
        """[tool.skillmeat]
version = "1.0.0"
name = "test-collection"

[[artifacts]]
name = "test-skill"
type = "skill"
path = "artifacts/skills/test-skill"
"""
    )

    yield coll_dir


@pytest.fixture
def project_dir(tmp_path):
    """Create test project directory."""
    proj_dir = tmp_path / "project"
    proj_dir.mkdir()
    (proj_dir / ".claude").mkdir()
    yield proj_dir


@pytest.fixture
def populated_cache(test_db, project_dir):
    """Populate cache with project and artifact."""
    session = get_session(test_db)
    try:
        # Create project
        project = Project(
            id=uuid.uuid4().hex,
            name="Test Project",
            path=str(project_dir),
            status="active",
        )
        session.add(project)

        # Create artifact
        artifact = Artifact(
            id=uuid.uuid4().hex,
            project_id=project.id,
            name="test-skill",
            type="skill",
        )
        session.add(artifact)
        session.commit()

        return project, artifact

    finally:
        session.close()


class TestDeploymentVersionTracking:
    """Integration tests for deployment version tracking."""

    def test_deployment_creates_version_record(
        self, test_db, collection_dir, project_dir, populated_cache, monkeypatch
    ):
        """Test that deploying an artifact creates an ArtifactVersion record."""
        project, artifact = populated_cache

        # Setup collection manager
        from skillmeat.config import ConfigManager
        from skillmeat.core.artifact import Artifact as CoreArtifact

        config_dir = collection_dir.parent / "config"
        config_dir.mkdir()

        config = ConfigManager(config_dir=config_dir)
        config.set("settings.active-collection", "test-collection")

        # Create collection
        coll_mgr = CollectionManager(config=config)
        collection = coll_mgr.init("test-collection")

        # Copy collection files to the right location
        collection_path = config.get_collection_path("test-collection")
        import shutil
        shutil.copytree(collection_dir, collection_path, dirs_exist_ok=True)

        # Add artifact to collection
        from skillmeat.core.artifact import Artifact, ArtifactMetadata, ArtifactType
        from datetime import datetime

        test_artifact = Artifact(
            name="test-skill",
            type=ArtifactType.SKILL,
            path="artifacts/skills/test-skill",
            origin="local",
            metadata=ArtifactMetadata(title="Test Skill", version="1.0.0"),
            added=datetime.now(),
        )
        collection.add_artifact(test_artifact)
        coll_mgr.save_collection(collection)

        # Deploy artifact
        deploy_mgr = DeploymentManager(collection_mgr=coll_mgr)
        deployments = deploy_mgr.deploy_artifacts(
            artifact_names=["test-skill"],
            collection_name="test-collection",
            project_path=project_dir,
        )

        assert len(deployments) == 1
        deployment = deployments[0]

        # Check that version record was created
        session = get_session(test_db)
        try:
            version = (
                session.query(ArtifactVersion)
                .filter_by(artifact_id=artifact.id)
                .first()
            )

            assert version is not None, "Version record should be created"
            assert version.content_hash == deployment.content_hash
            assert version.parent_hash is None  # Root version
            assert version.change_origin == "deployment"

            # Check version lineage
            lineage = json.loads(version.version_lineage)
            assert lineage == [deployment.content_hash]

        finally:
            session.close()

    def test_deployment_version_is_idempotent(
        self, test_db, collection_dir, project_dir, populated_cache, monkeypatch
    ):
        """Test that deploying same artifact twice doesn't create duplicate versions."""
        project, artifact = populated_cache

        # Setup collection manager
        config_dir = collection_dir.parent / "config"
        config_dir.mkdir()
        monkeypatch.setenv("SKILLMEAT_CONFIG_DIR", str(config_dir))

        # Create collection
        coll_mgr = CollectionManager()
        coll_mgr.config.create_collection("test-collection", str(collection_dir))

        # Deploy artifact twice
        deploy_mgr = DeploymentManager(collection_mgr=coll_mgr)

        deploy_mgr.deploy_artifacts(
            artifact_names=["test-skill"],
            collection_name="test-collection",
            project_path=project_dir,
        )

        # Deploy again (overwrite)
        deploy_mgr.deploy_artifacts(
            artifact_names=["test-skill"],
            collection_name="test-collection",
            project_path=project_dir,
        )

        # Check that only one version record exists
        session = get_session(test_db)
        try:
            versions = (
                session.query(ArtifactVersion)
                .filter_by(artifact_id=artifact.id)
                .all()
            )

            # Should have exactly one version (same content hash)
            assert len(versions) == 1

        finally:
            session.close()

    def test_deployment_without_cache_artifact_skips_version(
        self, test_db, collection_dir, project_dir, monkeypatch
    ):
        """Test that deployment without cache artifact skips version tracking."""
        # Setup collection manager
        config_dir = collection_dir.parent / "config"
        config_dir.mkdir()
        monkeypatch.setenv("SKILLMEAT_CONFIG_DIR", str(config_dir))

        # Create collection
        coll_mgr = CollectionManager()
        coll_mgr.config.create_collection("test-collection", str(collection_dir))

        # Deploy artifact WITHOUT creating cache entry first
        deploy_mgr = DeploymentManager(collection_mgr=coll_mgr)
        deployments = deploy_mgr.deploy_artifacts(
            artifact_names=["test-skill"],
            collection_name="test-collection",
            project_path=project_dir,
        )

        assert len(deployments) == 1

        # Check that no version record was created (no cache artifact)
        session = get_session(test_db)
        try:
            versions = session.query(ArtifactVersion).all()
            assert len(versions) == 0

        finally:
            session.close()
