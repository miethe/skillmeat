"""Integration tests for Projects API endpoints.

Tests CRUD operations for projects including creation, updates, deletion,
and modification detection.
"""

import base64
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings
from skillmeat.api.server import create_app
from skillmeat.core.deployment import Deployment


@pytest.fixture
def api_settings():
    """Create test API settings with auth disabled."""
    return APISettings(
        env="testing",
        api_key_enabled=False,  # Disable auth for testing
        cors_enabled=True,
    )


@pytest.fixture
def client(api_settings):
    """Create test client with mocked dependencies."""
    app = create_app(api_settings)
    return TestClient(app)


@pytest.fixture
def sample_project_path(tmp_path):
    """Create a temporary project directory."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir(parents=True)
    (project_dir / ".claude").mkdir(parents=True)
    return project_dir


@pytest.fixture
def encode_project_id():
    """Helper to encode project paths to IDs."""

    def _encode(path: str) -> str:
        return base64.b64encode(path.encode()).decode()

    return _encode


class TestListProjects:
    """Test GET /api/v1/projects endpoint."""

    def test_list_projects_empty(self, client):
        """Test listing projects when no projects exist."""
        with patch("skillmeat.api.routers.projects.discover_projects") as mock_discover:
            mock_discover.return_value = []

            response = client.get("/api/v1/projects")

            assert response.status_code == 200
            data = response.json()
            assert data["items"] == []
            assert data["page_info"]["total_count"] == 0
            assert data["page_info"]["has_next_page"] is False

    def test_list_projects_with_data(self, client, tmp_path):
        """Test listing projects with existing projects."""
        # Create test projects
        project1 = tmp_path / "project1"
        project1.mkdir(parents=True)
        (project1 / ".claude").mkdir(parents=True)

        project2 = tmp_path / "project2"
        project2.mkdir(parents=True)
        (project2 / ".claude").mkdir(parents=True)

        # Create deployment files
        from skillmeat.storage.deployment import DeploymentTracker

        from pathlib import Path

        deployment1 = Deployment(
            artifact_name="test-skill",
            artifact_type="skill",
            from_collection="default",
            deployed_at=datetime.utcnow(),
            artifact_path=Path("skills/test-skill"),
            content_hash="abc123",
            collection_sha="abc123",
            local_modifications=False,
        )

        DeploymentTracker.write_deployments(project1, [deployment1])
        DeploymentTracker.write_deployments(project2, [deployment1])

        with patch("skillmeat.api.routers.projects.discover_projects") as mock_discover:
            mock_discover.return_value = [project1, project2]

            response = client.get("/api/v1/projects")

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 2
            assert data["page_info"]["total_count"] == 2

    def test_list_projects_pagination(self, client, tmp_path):
        """Test project listing with pagination."""
        # Create 3 test projects
        projects = []
        for i in range(3):
            project = tmp_path / f"project{i}"
            project.mkdir(parents=True)
            (project / ".claude").mkdir(parents=True)

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

            DeploymentTracker.write_deployments(project, [deployment])
            projects.append(project)

        with patch("skillmeat.api.routers.projects.discover_projects") as mock_discover:
            mock_discover.return_value = projects

            # Get first page
            response = client.get("/api/v1/projects?limit=2")
            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 2
            assert data["page_info"]["has_next_page"] is True

            # Get second page
            cursor = data["page_info"]["end_cursor"]
            response = client.get(f"/api/v1/projects?limit=2&after={cursor}")
            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 1
            assert data["page_info"]["has_next_page"] is False

    def test_list_projects_invalid_cursor(self, client):
        """Test listing with invalid pagination cursor."""
        with patch("skillmeat.api.routers.projects.discover_projects") as mock_discover:
            mock_discover.return_value = []

            response = client.get("/api/v1/projects?after=invalid-cursor")

            # Should return 400 for invalid cursor format
            assert response.status_code == 400


class TestCreateProject:
    """Test POST /api/v1/projects endpoint."""

    def test_create_project_success(self, client, tmp_path):
        """Test successful project creation."""
        project_path = tmp_path / "new-project"

        with patch(
            "skillmeat.storage.project.ProjectMetadataStorage.exists"
        ) as mock_exists:
            with patch(
                "skillmeat.storage.project.ProjectMetadataStorage.create_metadata"
            ) as mock_create:
                mock_exists.return_value = False

                mock_metadata = Mock()
                mock_metadata.name = "new-project"
                mock_metadata.description = "Test project"
                mock_metadata.created_at = datetime.utcnow()
                mock_create.return_value = mock_metadata

                request_data = {
                    "name": "new-project",
                    "path": str(project_path),
                    "description": "Test project",
                }

                response = client.post("/api/v1/projects", json=request_data)

                assert response.status_code == 201
                data = response.json()
                assert data["name"] == "new-project"
                assert data["path"] == str(project_path)
                assert data["description"] == "Test project"
                assert "id" in data
                assert "created_at" in data

    def test_create_project_invalid_name(self, client, tmp_path):
        """Test creating project with invalid name."""
        project_path = tmp_path / "invalid-project"

        invalid_names = [
            "",  # Empty name
            "-invalid",  # Starts with hyphen
            "invalid-",  # Ends with hyphen
            "_invalid",  # Starts with underscore
            "invalid_",  # Ends with underscore
            "invalid name",  # Contains space
            "invalid!name",  # Contains special char
        ]

        for invalid_name in invalid_names:
            request_data = {
                "name": invalid_name,
                "path": str(project_path),
            }

            response = client.post("/api/v1/projects", json=request_data)

            assert (
                response.status_code == 422 or response.status_code == 400
            ), f"Expected validation error for name: {invalid_name}"

    def test_create_project_invalid_path(self, client):
        """Test creating project with invalid path."""
        # Relative path (not absolute)
        request_data = {
            "name": "test-project",
            "path": "relative/path",
        }

        response = client.post("/api/v1/projects", json=request_data)
        assert response.status_code == 422  # Validation error

    def test_create_project_already_exists(self, client, tmp_path):
        """Test creating project that already exists."""
        project_path = tmp_path / "existing-project"

        with patch(
            "skillmeat.storage.project.ProjectMetadataStorage.exists"
        ) as mock_exists:
            mock_exists.return_value = True

            request_data = {
                "name": "existing-project",
                "path": str(project_path),
            }

            response = client.post("/api/v1/projects", json=request_data)

            assert response.status_code == 400
            assert "already exists" in response.json()["detail"].lower()

    def test_create_project_valid_names(self, client, tmp_path):
        """Test creating projects with valid names."""
        valid_names = [
            "a",  # Single character
            "project123",  # Alphanumeric
            "my-project",  # With hyphen
            "my_project",  # With underscore
            "Project-123_Test",  # Mixed
        ]

        with patch(
            "skillmeat.storage.project.ProjectMetadataStorage.exists"
        ) as mock_exists:
            with patch(
                "skillmeat.storage.project.ProjectMetadataStorage.create_metadata"
            ) as mock_create:
                mock_exists.return_value = False

                for valid_name in valid_names:
                    project_path = tmp_path / valid_name

                    mock_metadata = Mock()
                    mock_metadata.name = valid_name
                    mock_metadata.description = None
                    mock_metadata.created_at = datetime.utcnow()
                    mock_create.return_value = mock_metadata

                    request_data = {
                        "name": valid_name,
                        "path": str(project_path),
                    }

                    response = client.post("/api/v1/projects", json=request_data)

                    assert (
                        response.status_code == 201
                    ), f"Failed for valid name: {valid_name}"


class TestGetProject:
    """Test GET /api/v1/projects/{id} endpoint."""

    def test_get_project_success(self, client, sample_project_path, encode_project_id):
        """Test getting project details."""
        project_id = encode_project_id(str(sample_project_path))

        # Create deployment file
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

        DeploymentTracker.write_deployments(sample_project_path, [deployment])

        with patch(
            "skillmeat.storage.project.ProjectMetadataStorage.read_metadata"
        ) as mock_read:
            mock_metadata = Mock()
            mock_metadata.name = "test-project"
            mock_read.return_value = mock_metadata

            response = client.get(f"/api/v1/projects/{project_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "test-project"
            assert data["id"] == project_id
            assert data["deployment_count"] == 1
            assert len(data["deployments"]) == 1
            assert "stats" in data

    def test_get_project_not_found(self, client, encode_project_id):
        """Test getting non-existent project."""
        fake_path = "/nonexistent/project"
        project_id = encode_project_id(fake_path)

        response = client.get(f"/api/v1/projects/{project_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_project_invalid_id(self, client):
        """Test getting project with invalid ID format."""
        response = client.get("/api/v1/projects/invalid-id-format")

        assert response.status_code == 400


class TestUpdateProject:
    """Test PUT /api/v1/projects/{id} endpoint."""

    def test_update_project_name(self, client, sample_project_path, encode_project_id):
        """Test updating project name."""
        project_id = encode_project_id(str(sample_project_path))

        # Create deployment file so project exists
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

        DeploymentTracker.write_deployments(sample_project_path, [deployment])

        with patch(
            "skillmeat.storage.project.ProjectMetadataStorage.exists"
        ) as mock_exists:
            with patch(
                "skillmeat.storage.project.ProjectMetadataStorage.update_metadata"
            ) as mock_update:
                with patch(
                    "skillmeat.storage.project.ProjectMetadataStorage.read_metadata"
                ) as mock_read:
                    mock_exists.return_value = True

                    mock_metadata = Mock()
                    mock_metadata.name = "test-project"
                    mock_metadata.description = "New description"
                    mock_update.return_value = mock_metadata
                    mock_read.return_value = mock_metadata

                    request_data = {
                        "description": "New description",
                    }

                    response = client.put(
                        f"/api/v1/projects/{project_id}", json=request_data
                    )

                    assert response.status_code == 200

    def test_update_project_empty_request(
        self, client, sample_project_path, encode_project_id
    ):
        """Test updating project with no fields provided."""
        project_id = encode_project_id(str(sample_project_path))

        with patch(
            "skillmeat.storage.project.ProjectMetadataStorage.exists"
        ) as mock_exists:
            mock_exists.return_value = True

            request_data = {}

            response = client.put(f"/api/v1/projects/{project_id}", json=request_data)

            # Should fail - at least one field required
            assert response.status_code == 400
            assert "at least one field" in response.json()["detail"].lower()

    def test_update_project_not_found(self, client, encode_project_id):
        """Test updating non-existent project."""
        fake_path = "/nonexistent/project"
        project_id = encode_project_id(fake_path)

        request_data = {
            "name": "new-name",
        }

        response = client.put(f"/api/v1/projects/{project_id}", json=request_data)

        assert response.status_code == 404


class TestDeleteProject:
    """Test DELETE /api/v1/projects/{id} endpoint."""

    def test_delete_project_metadata_only(
        self, client, sample_project_path, encode_project_id
    ):
        """Test deleting project metadata without files."""
        project_id = encode_project_id(str(sample_project_path))

        with patch(
            "skillmeat.storage.project.ProjectMetadataStorage.exists"
        ) as mock_exists:
            with patch(
                "skillmeat.storage.project.ProjectMetadataStorage.delete_metadata"
            ) as mock_delete:
                mock_exists.return_value = True
                mock_delete.return_value = True

                response = client.delete(
                    f"/api/v1/projects/{project_id}?delete_files=false"
                )

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["deleted_files"] is False
                assert "tracking" in data["message"].lower()

    def test_delete_project_with_files(
        self, client, sample_project_path, encode_project_id
    ):
        """Test deleting project including files."""
        project_id = encode_project_id(str(sample_project_path))

        with patch(
            "skillmeat.storage.project.ProjectMetadataStorage.exists"
        ) as mock_exists:
            with patch(
                "skillmeat.storage.project.ProjectMetadataStorage.delete_metadata"
            ) as mock_delete:
                mock_exists.return_value = True
                mock_delete.return_value = True

                response = client.delete(
                    f"/api/v1/projects/{project_id}?delete_files=true"
                )

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["deleted_files"] is True

    def test_delete_project_not_found(self, client, encode_project_id):
        """Test deleting non-existent project."""
        fake_path = "/nonexistent/project"
        project_id = encode_project_id(fake_path)

        response = client.delete(f"/api/v1/projects/{project_id}")

        assert response.status_code == 404


class TestRemoveProjectDeployment:
    """Test DELETE /api/v1/projects/{id}/deployments/{artifact_name} endpoint."""

    def test_remove_deployment_success_with_files(
        self, client, sample_project_path, encode_project_id
    ):
        """Test successful deployment removal with files."""
        project_id = encode_project_id(str(sample_project_path))
        artifact_name = "test-skill"

        # Mock deployment exists
        mock_deployment = Deployment(
            artifact_name=artifact_name,
            artifact_type="skill",
            from_collection="default",
            deployed_at=datetime.utcnow(),
            artifact_path=Path("skills/test-skill"),
            content_hash="abc123def",
            local_modifications=False,
        )

        with patch(
            "skillmeat.storage.deployment.DeploymentTracker.get_deployment"
        ) as mock_get_deployment:
            with patch(
                "skillmeat.storage.deployment.DeploymentTracker.remove_deployment"
            ) as mock_remove_deployment:
                with patch(
                    "skillmeat.utils.filesystem.FilesystemManager.remove_artifact"
                ) as mock_remove_artifact:
                    with patch(
                        "skillmeat.api.routers.projects.get_project_registry"
                    ) as mock_get_registry:
                        with patch(
                            "skillmeat.core.analytics.EventTracker"
                        ) as mock_event_tracker:
                            mock_get_deployment.return_value = mock_deployment

                            # Create async mock for get_project_registry
                            mock_registry = AsyncMock()
                            mock_registry.refresh_entry = AsyncMock(return_value=None)
                            mock_get_registry.return_value = mock_registry

                            # Create artifact file
                            artifact_path = (
                                sample_project_path / ".claude" / "skills" / "test-skill"
                            )
                            artifact_path.mkdir(parents=True, exist_ok=True)
                            (artifact_path / "SKILL.md").touch()

                            response = client.delete(
                                f"/api/v1/projects/{project_id}/deployments/{artifact_name}?artifact_type=skill&remove_files=true"
                            )

                            assert response.status_code == 200
                            data = response.json()
                            assert data["success"] is True
                            assert data["artifact_name"] == artifact_name
                            assert data["artifact_type"] == "skill"
                            assert data["files_removed"] is True

                            # Verify tracking removal was called
                            mock_remove_deployment.assert_called_once_with(
                                sample_project_path, artifact_name, "skill"
                            )

    def test_remove_deployment_tracking_only(
        self, client, sample_project_path, encode_project_id
    ):
        """Test deployment removal without removing files."""
        project_id = encode_project_id(str(sample_project_path))
        artifact_name = "test-skill"

        # Mock deployment exists
        mock_deployment = Deployment(
            artifact_name=artifact_name,
            artifact_type="skill",
            from_collection="default",
            deployed_at=datetime.utcnow(),
            artifact_path=Path("skills/test-skill"),
            content_hash="abc123def",
            local_modifications=False,
        )

        with patch(
            "skillmeat.storage.deployment.DeploymentTracker.get_deployment"
        ) as mock_get_deployment:
            with patch(
                "skillmeat.storage.deployment.DeploymentTracker.remove_deployment"
            ) as mock_remove_deployment:
                with patch(
                    "skillmeat.utils.filesystem.FilesystemManager.remove_artifact"
                ) as mock_remove_artifact:
                    with patch(
                        "skillmeat.api.routers.projects.get_project_registry"
                    ) as mock_get_registry:
                        mock_get_deployment.return_value = mock_deployment

                        # Create async mock for get_project_registry
                        mock_registry = AsyncMock()
                        mock_registry.refresh_entry = AsyncMock(return_value=None)
                        mock_get_registry.return_value = mock_registry

                        # Create artifact file
                        artifact_path = (
                            sample_project_path / ".claude" / "skills" / "test-skill"
                        )
                        artifact_path.mkdir(parents=True, exist_ok=True)
                        (artifact_path / "SKILL.md").touch()

                        response = client.delete(
                            f"/api/v1/projects/{project_id}/deployments/{artifact_name}?artifact_type=skill&remove_files=false"
                        )

                        assert response.status_code == 200
                        data = response.json()
                        assert data["success"] is True
                        assert data["files_removed"] is False

                        # Verify only tracking removal was called, not file removal
                        mock_remove_deployment.assert_called_once()
                        mock_remove_artifact.assert_not_called()

    def test_remove_deployment_not_found(
        self, client, sample_project_path, encode_project_id
    ):
        """Test removing deployment that doesn't exist."""
        project_id = encode_project_id(str(sample_project_path))
        artifact_name = "nonexistent-skill"

        with patch(
            "skillmeat.storage.deployment.DeploymentTracker.get_deployment"
        ) as mock_get_deployment:
            mock_get_deployment.return_value = None

            response = client.delete(
                f"/api/v1/projects/{project_id}/deployments/{artifact_name}?artifact_type=skill&remove_files=true"
            )

            assert response.status_code == 404
            assert "not found in project" in response.json()["detail"]

    def test_remove_deployment_artifact_name_mismatch(
        self, client, sample_project_path, encode_project_id
    ):
        """Test removing deployment with mismatched artifact names."""
        # This test is no longer applicable since artifact name comes only from URL path now
        # The test would be testing invalid artifact types instead
        pass

    def test_remove_deployment_invalid_artifact_type(
        self, client, sample_project_path, encode_project_id
    ):
        """Test removing deployment with invalid artifact type."""
        project_id = encode_project_id(str(sample_project_path))
        artifact_name = "test-skill"

        response = client.delete(
            f"/api/v1/projects/{project_id}/deployments/{artifact_name}?artifact_type=invalid-type&remove_files=true"
        )

        assert response.status_code == 400
        assert "Invalid artifact type" in response.json()["detail"]

    def test_remove_deployment_project_not_found(self, client, encode_project_id):
        """Test removing deployment from non-existent project."""
        fake_path = "/nonexistent/project"
        project_id = encode_project_id(fake_path)
        artifact_name = "test-skill"

        response = client.delete(
            f"/api/v1/projects/{project_id}/deployments/{artifact_name}?artifact_type=skill&remove_files=true"
        )

        assert response.status_code == 404
        assert "Project not found" in response.json()["detail"]
