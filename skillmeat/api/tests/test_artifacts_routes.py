"""Integration tests for Artifacts API endpoints.

Tests artifact CRUD operations, deployment, sync, and diff functionality.
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings
from skillmeat.api.server import create_app
from skillmeat.core.artifact import Artifact, ArtifactMetadata, ArtifactType
from skillmeat.core.deployment import Deployment


@pytest.fixture
def api_settings():
    """Create test API settings with auth disabled."""
    return APISettings(
        env="testing",
        api_key_enabled=False,
        cors_enabled=True,
    )


@pytest.fixture
def client(api_settings):
    """Create test client with initialized app state."""
    from skillmeat.api.dependencies import app_state

    # Initialize app state before creating client
    app = create_app(api_settings)

    # Initialize app_state manually for tests
    app_state.initialize(api_settings)

    client = TestClient(app)

    yield client

    # Clean up
    app_state.shutdown()


@pytest.fixture
def sample_artifact():
    """Create a sample artifact for testing."""
    metadata = ArtifactMetadata(
        title="Test Skill",
        description="A test skill",
        author="Test Author",
        license="MIT",
        version="1.0.0",
        tags=["test", "skill"],
    )

    return Artifact(
        name="test-skill",
        type=ArtifactType.SKILL,
        path="skills/test-skill",
        origin="github",
        upstream="anthropics/skills/test-skill",
        version_spec="latest",
        resolved_sha="abc123",
        resolved_version="v1.0.0",
        added=datetime.utcnow(),
        last_updated=datetime.utcnow(),
        metadata=metadata,
        tags=["test"],
    )


class TestCreateArtifact:
    """Test POST /api/v1/artifacts endpoint."""

    def test_create_artifact_from_github(self, client, sample_artifact):
        """Test creating artifact from GitHub source."""
        with patch("skillmeat.api.dependencies.app_state.collection_manager") as mock_coll_mgr:
            with patch("skillmeat.api.dependencies.app_state.artifact_manager") as mock_art_mgr:
                mock_coll_mgr.list_collections.return_value = ["default"]
                mock_art_mgr.add_from_github.return_value = sample_artifact

                request_data = {
                    "source_type": "github",
                    "source": "anthropics/skills/test-skill",
                    "artifact_type": "skill",
                    "name": "test-skill",
                    "collection": "default",
                }

                response = client.post("/api/v1/artifacts", json=request_data)

                assert response.status_code == 201
                data = response.json()
                assert data["success"] is True
                assert data["artifact_name"] == "test-skill"
                assert data["artifact_type"] == "skill"
                assert data["source_type"] == "github"

    def test_create_artifact_from_local(self, client, sample_artifact, tmp_path):
        """Test creating artifact from local path."""
        local_path = tmp_path / "test-skill"
        local_path.mkdir(parents=True)
        (local_path / "SKILL.md").write_text("# Test Skill")

        with patch("skillmeat.api.dependencies.app_state.collection_manager") as mock_coll_mgr:
            with patch("skillmeat.api.dependencies.app_state.artifact_manager") as mock_art_mgr:
                mock_coll_mgr.list_collections.return_value = ["default"]
                mock_art_mgr.add_from_local.return_value = sample_artifact

                request_data = {
                    "source_type": "local",
                    "source": str(local_path),
                    "artifact_type": "skill",
                    "collection": "default",
                }

                response = client.post("/api/v1/artifacts", json=request_data)

                assert response.status_code == 201
                data = response.json()
                assert data["success"] is True
                assert data["source_type"] == "local"

    def test_create_artifact_local_not_found(self, client):
        """Test creating artifact from non-existent local path."""
        with patch("skillmeat.api.dependencies.app_state.collection_manager") as mock_coll_mgr:
            mock_coll_mgr.list_collections.return_value = ["default"]

            request_data = {
                "source_type": "local",
                "source": "/nonexistent/path",
                "artifact_type": "skill",
            }

            response = client.post("/api/v1/artifacts", json=request_data)

            assert response.status_code == 404
            assert "does not exist" in response.json()["detail"].lower()

    def test_create_artifact_invalid_type(self, client):
        """Test creating artifact with invalid type."""
        with patch("skillmeat.api.dependencies.app_state.collection_manager") as mock_coll_mgr:
            mock_coll_mgr.list_collections.return_value = ["default"]

            request_data = {
                "source_type": "github",
                "source": "user/repo",
                "artifact_type": "invalid-type",
            }

            response = client.post("/api/v1/artifacts", json=request_data)

            assert response.status_code == 400
            assert "invalid artifact type" in response.json()["detail"].lower()

    def test_create_artifact_duplicate(self, client, sample_artifact):
        """Test creating artifact that already exists."""
        with patch("skillmeat.api.dependencies.app_state.collection_manager") as mock_coll_mgr:
            with patch("skillmeat.api.dependencies.app_state.artifact_manager") as mock_art_mgr:
                mock_coll_mgr.list_collections.return_value = ["default"]
                mock_art_mgr.add_from_github.side_effect = ValueError("Artifact already exists")

                request_data = {
                    "source_type": "github",
                    "source": "user/repo/skill",
                    "artifact_type": "skill",
                }

                response = client.post("/api/v1/artifacts", json=request_data)

                assert response.status_code == 409
                assert "already exists" in response.json()["detail"].lower()

    def test_create_artifact_no_collection(self, client):
        """Test creating artifact when no collections exist."""
        with patch("skillmeat.api.dependencies.app_state.collection_manager") as mock_coll_mgr:
            mock_coll_mgr.list_collections.return_value = []

            request_data = {
                "source_type": "github",
                "source": "user/repo/skill",
                "artifact_type": "skill",
            }

            response = client.post("/api/v1/artifacts", json=request_data)

            assert response.status_code == 404
            assert "no collections found" in response.json()["detail"].lower()


class TestUpdateArtifact:
    """Test PUT /api/v1/artifacts/{id} endpoint."""

    def test_update_artifact_tags(self, client, sample_artifact):
        """Test updating artifact tags."""
        with patch("skillmeat.api.dependencies.app_state.collection_manager") as mock_coll_mgr:
            with patch("skillmeat.api.dependencies.app_state.artifact_manager") as mock_art_mgr:
                mock_coll = Mock()
                mock_coll.find_artifact.return_value = sample_artifact

                mock_coll_mgr.list_collections.return_value = ["default"]
                mock_coll_mgr.load_collection.return_value = mock_coll
                mock_art_mgr.show.return_value = sample_artifact

                request_data = {
                    "tags": ["new", "updated"],
                }

                response = client.put("/api/v1/artifacts/skill:test-skill", json=request_data)

                assert response.status_code == 200

    def test_update_artifact_metadata(self, client, sample_artifact):
        """Test updating artifact metadata."""
        with patch("skillmeat.api.dependencies.app_state.collection_manager") as mock_coll_mgr:
            with patch("skillmeat.api.dependencies.app_state.artifact_manager") as mock_art_mgr:
                mock_coll = Mock()
                mock_coll.find_artifact.return_value = sample_artifact

                mock_coll_mgr.list_collections.return_value = ["default"]
                mock_coll_mgr.load_collection.return_value = mock_coll
                mock_coll_mgr.config.get_collection_path.return_value = Path("/tmp/collection")

                request_data = {
                    "metadata": {
                        "title": "Updated Title",
                        "description": "Updated description",
                    }
                }

                with patch("skillmeat.utils.filesystem.compute_content_hash") as mock_hash:
                    mock_hash.return_value = "newhash123"

                    response = client.put("/api/v1/artifacts/skill:test-skill", json=request_data)

                    assert response.status_code == 200

    def test_update_artifact_not_found(self, client):
        """Test updating non-existent artifact."""
        with patch("skillmeat.api.dependencies.app_state.collection_manager") as mock_coll_mgr:
            mock_coll = Mock()
            mock_coll.find_artifact.return_value = None

            mock_coll_mgr.list_collections.return_value = ["default"]
            mock_coll_mgr.load_collection.return_value = mock_coll

            request_data = {
                "tags": ["test"],
            }

            response = client.put("/api/v1/artifacts/skill:nonexistent", json=request_data)

            assert response.status_code == 404

    def test_update_artifact_invalid_id_format(self, client):
        """Test updating artifact with invalid ID format."""
        request_data = {"tags": ["test"]}

        response = client.put("/api/v1/artifacts/invalid-id-format", json=request_data)

        assert response.status_code == 400
        assert "invalid artifact id format" in response.json()["detail"].lower()


class TestGetArtifactDiff:
    """Test GET /api/v1/artifacts/{id}/diff endpoint."""

    def test_get_diff_with_changes(self, client, sample_artifact, tmp_path):
        """Test getting diff when changes exist."""
        # Create test directories
        collection_path = tmp_path / "collection"
        collection_path.mkdir(parents=True)
        artifact_path = collection_path / "skills" / "test-skill"
        artifact_path.mkdir(parents=True)
        (artifact_path / "SKILL.md").write_text("Collection version")

        project_path = tmp_path / "project"
        project_path.mkdir(parents=True)
        project_artifact = project_path / ".claude" / "skills" / "test-skill"
        project_artifact.mkdir(parents=True)
        (project_artifact / "SKILL.md").write_text("Modified version")

        # Create deployment
        deployment = Deployment(
            artifact_name="test-skill",
            artifact_type="skill",
            from_collection="default",
            deployed_at=datetime.utcnow(),
            artifact_path=Path("skills/test-skill"),
            content_hash="abc123",
                    collection_sha="abc123",
            local_modifications=False,
        )

        from skillmeat.storage.deployment import DeploymentTracker
        DeploymentTracker.write_deployments(project_path, [deployment])

        with patch("skillmeat.api.dependencies.app_state.collection_manager") as mock_coll_mgr:
            mock_coll = Mock()
            mock_coll.find_artifact.return_value = sample_artifact

            mock_coll_mgr.list_collections.return_value = ["default"]
            mock_coll_mgr.load_collection.return_value = mock_coll
            mock_coll_mgr.config.get_collection_path.return_value = collection_path

            response = client.get(
                f"/api/v1/artifacts/skill:test-skill/diff?project_path={project_path}"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["artifact_name"] == "test-skill"
            assert data["has_changes"] is True
            assert len(data["files"]) > 0
            assert data["summary"]["modified"] >= 0

    def test_get_diff_no_changes(self, client, sample_artifact, tmp_path):
        """Test getting diff when no changes exist."""
        # Create identical files
        collection_path = tmp_path / "collection"
        collection_path.mkdir(parents=True)
        artifact_path = collection_path / "skills" / "test-skill"
        artifact_path.mkdir(parents=True)
        (artifact_path / "SKILL.md").write_text("Same content")

        project_path = tmp_path / "project"
        project_path.mkdir(parents=True)
        project_artifact = project_path / ".claude" / "skills" / "test-skill"
        project_artifact.mkdir(parents=True)
        (project_artifact / "SKILL.md").write_text("Same content")

        deployment = Deployment(
            artifact_name="test-skill",
            artifact_type="skill",
            from_collection="default",
            deployed_at=datetime.utcnow(),
            artifact_path=Path("skills/test-skill"),
            content_hash="abc123",
                    collection_sha="abc123",
            local_modifications=False,
        )

        from skillmeat.storage.deployment import DeploymentTracker
        DeploymentTracker.write_deployments(project_path, [deployment])

        with patch("skillmeat.api.dependencies.app_state.collection_manager") as mock_coll_mgr:
            mock_coll = Mock()
            mock_coll.find_artifact.return_value = sample_artifact

            mock_coll_mgr.list_collections.return_value = ["default"]
            mock_coll_mgr.load_collection.return_value = mock_coll
            mock_coll_mgr.config.get_collection_path.return_value = collection_path

            response = client.get(
                f"/api/v1/artifacts/skill:test-skill/diff?project_path={project_path}"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["has_changes"] is False
            assert data["summary"]["unchanged"] > 0
            assert data["summary"]["modified"] == 0

    def test_get_diff_artifact_not_deployed(self, client, tmp_path):
        """Test getting diff for artifact not deployed in project."""
        project_path = tmp_path / "project"
        project_path.mkdir(parents=True)
        (project_path / ".claude").mkdir(parents=True)

        response = client.get(
            f"/api/v1/artifacts/skill:test-skill/diff?project_path={project_path}"
        )

        assert response.status_code == 404
        assert "not deployed" in response.json()["detail"].lower()

    def test_get_diff_missing_project_path(self, client):
        """Test getting diff without providing project_path."""
        response = client.get("/api/v1/artifacts/skill:test-skill/diff")

        assert response.status_code == 422  # Validation error - missing required query param

    def test_get_diff_invalid_project_path(self, client):
        """Test getting diff with invalid project path."""
        response = client.get(
            "/api/v1/artifacts/skill:test-skill/diff?project_path=/nonexistent/path"
        )

        assert response.status_code == 400
        assert "does not exist" in response.json()["detail"].lower()


class TestSyncArtifact:
    """Test POST /api/v1/artifacts/{id}/sync endpoint."""

    def test_sync_artifact_from_project(self, client, sample_artifact, tmp_path):
        """Test syncing artifact from project to collection."""
        project_path = tmp_path / "project"
        project_path.mkdir(parents=True)
        (project_path / ".claude").mkdir(parents=True)

        with patch("skillmeat.api.dependencies.app_state.collection_manager") as mock_coll_mgr:
            with patch("skillmeat.api.dependencies.app_state.sync_manager") as mock_sync_mgr:
                mock_coll = Mock()
                mock_coll.find_artifact.return_value = sample_artifact

                mock_coll_mgr.list_collections.return_value = ["default"]
                mock_coll_mgr.load_collection.return_value = mock_coll

                # Mock deployment metadata
                mock_deployment_metadata = Mock()
                mock_deployment_metadata.collection = "default"

                mock_deployed = Mock()
                mock_deployed.name = "test-skill"
                mock_deployed.artifact_type = "skill"
                mock_deployment_metadata.artifacts = [mock_deployed]

                mock_sync_mgr._load_deployment_metadata.return_value = mock_deployment_metadata

                # Mock sync result
                mock_sync_result = Mock()
                mock_sync_result.status = "success"
                mock_sync_result.message = "Sync completed successfully"
                mock_sync_result.conflicts = []
                mock_sync_result.artifacts_synced = ["test-skill"]

                mock_sync_mgr.sync_from_project.return_value = mock_sync_result

                request_data = {
                    "project_path": str(project_path),
                    "strategy": "theirs",
                }

                with patch("skillmeat.utils.filesystem.compute_content_hash") as mock_hash:
                    mock_hash.return_value = "hash123"

                    response = client.post(
                        "/api/v1/artifacts/skill:test-skill/sync",
                        json=request_data
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert data["artifact_name"] == "test-skill"

    def test_sync_artifact_upstream_not_implemented(self, client):
        """Test syncing artifact from upstream (not yet implemented)."""
        request_data = {
            "strategy": "theirs",
        }

        response = client.post(
            "/api/v1/artifacts/skill:test-skill/sync",
            json=request_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "not yet implemented" in data["message"].lower()

    def test_sync_artifact_invalid_strategy(self, client, tmp_path):
        """Test syncing with invalid strategy."""
        project_path = tmp_path / "project"

        request_data = {
            "project_path": str(project_path),
            "strategy": "invalid-strategy",
        }

        response = client.post(
            "/api/v1/artifacts/skill:test-skill/sync",
            json=request_data
        )

        assert response.status_code == 422  # Validation error

    def test_sync_artifact_project_not_found(self, client):
        """Test syncing with non-existent project path."""
        request_data = {
            "project_path": "/nonexistent/path",
            "strategy": "theirs",
        }

        response = client.post(
            "/api/v1/artifacts/skill:test-skill/sync",
            json=request_data
        )

        assert response.status_code == 400
        assert "does not exist" in response.json()["detail"].lower()


class TestDeployArtifact:
    """Test POST /api/v1/artifacts/{id}/deploy endpoint."""

    def test_deploy_artifact_success(self, client, sample_artifact, tmp_path):
        """Test successful artifact deployment."""
        project_path = tmp_path / "project"
        project_path.mkdir(parents=True)

        with patch("skillmeat.api.dependencies.app_state.collection_manager") as mock_coll_mgr:
            with patch("skillmeat.api.dependencies.app_state.artifact_manager") as mock_art_mgr:
                with patch("skillmeat.core.deployment.DeploymentManager") as mock_deploy_mgr:
                    mock_coll = Mock()
                    mock_coll.find_artifact.return_value = sample_artifact

                    mock_coll_mgr.list_collections.return_value = ["default"]
                    mock_coll_mgr.load_collection.return_value = mock_coll

                    # Mock deployment
                    mock_deployment = Deployment(
                        artifact_name="test-skill",
                        artifact_type="skill",
                        from_collection="default",
                        deployed_at=datetime.utcnow(),
                        artifact_path=Path("skills/test-skill"),
                        content_hash="abc123",
                    collection_sha="abc123",
                        local_modifications=False,
                    )

                    mock_deploy_instance = Mock()
                    mock_deploy_instance.deploy_artifacts.return_value = [mock_deployment]
                    mock_deploy_mgr.return_value = mock_deploy_instance

                    request_data = {
                        "project_path": str(project_path),
                        "overwrite": False,
                    }

                    response = client.post(
                        "/api/v1/artifacts/skill:test-skill/deploy",
                        json=request_data
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert data["artifact_name"] == "test-skill"
                    assert "deployed_path" in data

    def test_deploy_artifact_project_not_found(self, client):
        """Test deploying to non-existent project."""
        request_data = {
            "project_path": "/nonexistent/path",
        }

        response = client.post(
            "/api/v1/artifacts/skill:test-skill/deploy",
            json=request_data
        )

        assert response.status_code == 400
        assert "does not exist" in response.json()["detail"].lower()

    def test_deploy_artifact_not_found(self, client, tmp_path):
        """Test deploying non-existent artifact."""
        project_path = tmp_path / "project"
        project_path.mkdir(parents=True)

        with patch("skillmeat.api.dependencies.app_state.collection_manager") as mock_coll_mgr:
            mock_coll = Mock()
            mock_coll.find_artifact.return_value = None

            mock_coll_mgr.list_collections.return_value = ["default"]
            mock_coll_mgr.load_collection.return_value = mock_coll

            request_data = {
                "project_path": str(project_path),
            }

            response = client.post(
                "/api/v1/artifacts/skill:nonexistent/deploy",
                json=request_data
            )

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


class TestListArtifacts:
    """Test GET /api/v1/artifacts endpoint (existing, ensure still working)."""

    def test_list_artifacts_empty(self, client):
        """Test listing artifacts when collection is empty."""
        with patch("skillmeat.api.dependencies.app_state.collection_manager") as mock_coll_mgr:
            with patch("skillmeat.api.dependencies.app_state.artifact_manager") as mock_art_mgr:
                mock_coll_mgr.list_collections.return_value = ["default"]
                mock_art_mgr.list_artifacts.return_value = []

                response = client.get("/api/v1/artifacts")

                assert response.status_code == 200
                data = response.json()
                assert data["items"] == []
                assert data["page_info"]["total_count"] == 0

    def test_list_artifacts_with_data(self, client, sample_artifact):
        """Test listing artifacts with data."""
        with patch("skillmeat.api.dependencies.app_state.collection_manager") as mock_coll_mgr:
            with patch("skillmeat.api.dependencies.app_state.artifact_manager") as mock_art_mgr:
                with patch("skillmeat.api.dependencies.app_state.sync_manager"):
                    mock_coll_mgr.list_collections.return_value = ["default"]
                    mock_art_mgr.list_artifacts.return_value = [sample_artifact]

                    response = client.get("/api/v1/artifacts")

                    assert response.status_code == 200
                    data = response.json()
                    assert len(data["items"]) == 1
                    assert data["items"][0]["name"] == "test-skill"

    def test_list_artifacts_with_filters(self, client, sample_artifact):
        """Test listing artifacts with type and tag filters."""
        with patch("skillmeat.api.dependencies.app_state.collection_manager") as mock_coll_mgr:
            with patch("skillmeat.api.dependencies.app_state.artifact_manager") as mock_art_mgr:
                with patch("skillmeat.api.dependencies.app_state.sync_manager"):
                    mock_coll_mgr.list_collections.return_value = ["default"]
                    mock_art_mgr.list_artifacts.return_value = [sample_artifact]

                    response = client.get(
                        "/api/v1/artifacts?artifact_type=skill&tags=test"
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert len(data["items"]) == 1
