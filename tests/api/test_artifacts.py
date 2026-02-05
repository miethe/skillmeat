"""Tests for Artifacts API endpoints.

This module tests the /api/v1/artifacts endpoints, including:
- List artifacts with pagination and filters
- Get artifact details
- Check upstream status
"""

import pytest
from datetime import datetime
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app
from skillmeat.core.artifact import (
    Artifact,
    ArtifactType,
    ArtifactMetadata,
    UpdateFetchResult,
)


@pytest.fixture
def test_settings():
    """Create test settings."""
    return APISettings(
        env=Environment.TESTING,
        host="127.0.0.1",
        port=8000,
        log_level="DEBUG",
        api_key_enabled=False,
    )


@pytest.fixture
def app(test_settings):
    """Create FastAPI app for testing."""
    from skillmeat.api.config import get_settings

    app = create_app(test_settings)
    app.dependency_overrides[get_settings] = lambda: test_settings

    return app


@pytest.fixture
def client(app):
    """Create test client with lifespan context."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_artifact():
    """Create a mock artifact."""
    return Artifact(
        name="pdf-skill",
        type=ArtifactType.SKILL,
        path="skills/pdf-skill",
        origin="github",
        metadata=ArtifactMetadata(
            title="PDF Skill",
            description="Process PDF files",
            author="Anthropic",
            license="MIT",
            version="1.0.0",
            tags=["pdf", "document"],
            dependencies=["pypdf2"],
        ),
        added=datetime(2024, 11, 1, 12, 0, 0),
        upstream="anthropics/skills/pdf",
        version_spec="latest",
        resolved_sha="abc123def456",
        resolved_version="v1.0.0",
        last_updated=datetime(2024, 11, 16, 12, 0, 0),
    )


@pytest.fixture
def mock_artifact_manager(mock_artifact):
    """Create mock ArtifactManager."""
    mock_mgr = MagicMock()
    mock_mgr.list_artifacts.return_value = [mock_artifact]
    mock_mgr.show.return_value = mock_artifact

    return mock_mgr


@pytest.fixture
def mock_collection_manager():
    """Create mock CollectionManager."""
    mock_mgr = MagicMock()
    mock_mgr.list_collections.return_value = ["default"]

    return mock_mgr


class TestListArtifacts:
    """Test GET /api/v1/artifacts endpoint."""

    def test_list_artifacts_success(
        self, client, mock_artifact_manager, mock_collection_manager
    ):
        """Test listing artifacts returns paginated results."""
        with patch(
            "skillmeat.api.routers.artifacts.ArtifactManagerDep",
            return_value=mock_artifact_manager,
        ), patch(
            "skillmeat.api.routers.artifacts.CollectionManagerDep",
            return_value=mock_collection_manager,
        ):
            response = client.get("/api/v1/artifacts")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check response structure
        assert "items" in data
        assert "page_info" in data

        # Check items
        items = data["items"]
        assert len(items) > 0

        # Check artifact structure
        artifact = items[0]
        assert "id" in artifact
        assert "name" in artifact
        assert "type" in artifact
        assert "source" in artifact
        assert "version" in artifact
        assert "metadata" in artifact

    def test_list_artifacts_with_type_filter(
        self, client, mock_artifact_manager, mock_collection_manager
    ):
        """Test filtering artifacts by type."""
        with patch(
            "skillmeat.api.routers.artifacts.ArtifactManagerDep",
            return_value=mock_artifact_manager,
        ), patch(
            "skillmeat.api.routers.artifacts.CollectionManagerDep",
            return_value=mock_collection_manager,
        ):
            response = client.get("/api/v1/artifacts?artifact_type=skill")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # All items should be skills
        for item in data["items"]:
            assert item["type"] == "skill"

    def test_list_artifacts_with_collection_filter(
        self, client, mock_artifact_manager, mock_collection_manager
    ):
        """Test filtering artifacts by collection."""
        with patch(
            "skillmeat.api.routers.artifacts.ArtifactManagerDep",
            return_value=mock_artifact_manager,
        ), patch(
            "skillmeat.api.routers.artifacts.CollectionManagerDep",
            return_value=mock_collection_manager,
        ):
            response = client.get("/api/v1/artifacts?collection=default")

        assert response.status_code == status.HTTP_200_OK

    def test_list_artifacts_with_tags_filter(
        self, client, mock_artifact_manager, mock_collection_manager
    ):
        """Test filtering artifacts by tags."""
        with patch(
            "skillmeat.api.routers.artifacts.ArtifactManagerDep",
            return_value=mock_artifact_manager,
        ), patch(
            "skillmeat.api.routers.artifacts.CollectionManagerDep",
            return_value=mock_collection_manager,
        ):
            response = client.get("/api/v1/artifacts?tags=pdf,document")

        assert response.status_code == status.HTTP_200_OK

    def test_list_artifacts_pagination(
        self, client, mock_artifact_manager, mock_collection_manager
    ):
        """Test pagination with limit parameter."""
        # Create multiple artifacts
        artifacts = [
            Artifact(
                name=f"skill-{i}",
                type=ArtifactType.SKILL,
                path=f"skills/skill-{i}",
                origin="github",
                metadata=ArtifactMetadata(),
                added=datetime(2024, 11, i, 12, 0, 0),
            )
            for i in range(1, 6)
        ]
        mock_artifact_manager.list_artifacts.return_value = artifacts

        with patch(
            "skillmeat.api.routers.artifacts.ArtifactManagerDep",
            return_value=mock_artifact_manager,
        ), patch(
            "skillmeat.api.routers.artifacts.CollectionManagerDep",
            return_value=mock_collection_manager,
        ):
            response = client.get("/api/v1/artifacts?limit=2")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should return only 2 items
        assert len(data["items"]) == 2

        # Should indicate there's a next page
        assert data["page_info"]["has_next_page"] is True

    def test_list_artifacts_invalid_type(
        self, client, mock_artifact_manager, mock_collection_manager
    ):
        """Test invalid artifact type filter."""
        with patch(
            "skillmeat.api.routers.artifacts.ArtifactManagerDep",
            return_value=mock_artifact_manager,
        ), patch(
            "skillmeat.api.routers.artifacts.CollectionManagerDep",
            return_value=mock_collection_manager,
        ):
            response = client.get("/api/v1/artifacts?artifact_type=invalid")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_artifacts_collection_not_found(
        self, client, mock_artifact_manager
    ):
        """Test filtering by non-existent collection."""
        mock_coll_mgr = MagicMock()
        mock_coll_mgr.list_collections.return_value = []

        with patch(
            "skillmeat.api.routers.artifacts.ArtifactManagerDep",
            return_value=mock_artifact_manager,
        ), patch(
            "skillmeat.api.routers.artifacts.CollectionManagerDep",
            return_value=mock_coll_mgr,
        ):
            response = client.get("/api/v1/artifacts?collection=nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestGetArtifact:
    """Test GET /api/v1/artifacts/{artifact_id} endpoint."""

    def test_get_artifact_success(
        self, client, mock_artifact_manager, mock_collection_manager
    ):
        """Test getting a specific artifact."""
        with patch(
            "skillmeat.api.routers.artifacts.ArtifactManagerDep",
            return_value=mock_artifact_manager,
        ), patch(
            "skillmeat.api.routers.artifacts.CollectionManagerDep",
            return_value=mock_collection_manager,
        ):
            response = client.get("/api/v1/artifacts/skill:pdf-skill")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check response structure
        assert data["id"] == "skill:pdf-skill"
        assert data["name"] == "pdf-skill"
        assert data["type"] == "skill"
        assert "metadata" in data
        assert "upstream" in data

        # Check metadata
        metadata = data["metadata"]
        assert metadata["title"] == "PDF Skill"
        assert metadata["description"] == "Process PDF files"
        assert "tags" in metadata

    def test_get_artifact_not_found(self, client, mock_collection_manager):
        """Test getting a non-existent artifact."""
        mock_art_mgr = MagicMock()
        mock_art_mgr.show.side_effect = ValueError("Artifact not found")

        with patch(
            "skillmeat.api.routers.artifacts.ArtifactManagerDep",
            return_value=mock_art_mgr,
        ), patch(
            "skillmeat.api.routers.artifacts.CollectionManagerDep",
            return_value=mock_collection_manager,
        ):
            response = client.get("/api/v1/artifacts/skill:nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_artifact_invalid_id(self, client):
        """Test getting artifact with invalid ID format."""
        response = client.get("/api/v1/artifacts/invalid-id")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_artifact_with_collection_filter(
        self, client, mock_artifact_manager, mock_collection_manager
    ):
        """Test getting artifact with collection filter."""
        with patch(
            "skillmeat.api.routers.artifacts.ArtifactManagerDep",
            return_value=mock_artifact_manager,
        ), patch(
            "skillmeat.api.routers.artifacts.CollectionManagerDep",
            return_value=mock_collection_manager,
        ):
            response = client.get("/api/v1/artifacts/skill:pdf-skill?collection=default")

        assert response.status_code == status.HTTP_200_OK


class TestCheckArtifactUpstream:
    """Test GET /api/v1/artifacts/{artifact_id}/upstream endpoint."""

    def test_check_upstream_success(
        self, client, mock_artifact, mock_artifact_manager, mock_collection_manager
    ):
        """Test checking upstream status for an artifact."""
        # Mock fetch_update result
        from skillmeat.sources.base import UpdateInfo

        update_info = UpdateInfo(
            has_update=True,
            upstream_version="v1.1.0",
            upstream_sha="def789ghi012",
            current_sha="abc123def456",
            has_local_modifications=False,
        )

        fetch_result = UpdateFetchResult(
            artifact=mock_artifact,
            has_update=True,
            update_info=update_info,
        )

        mock_artifact_manager.fetch_update.return_value = fetch_result

        with patch(
            "skillmeat.api.routers.artifacts.ArtifactManagerDep",
            return_value=mock_artifact_manager,
        ), patch(
            "skillmeat.api.routers.artifacts.CollectionManagerDep",
            return_value=mock_collection_manager,
        ):
            response = client.get("/api/v1/artifacts/skill:pdf-skill/upstream")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check response structure
        assert data["artifact_id"] == "skill:pdf-skill"
        assert data["tracking_enabled"] is True
        assert data["current_sha"] == "abc123def456"
        assert data["upstream_sha"] == "def789ghi012"
        assert data["update_available"] is True
        assert "last_checked" in data

    def test_check_upstream_no_update(
        self, client, mock_artifact, mock_artifact_manager, mock_collection_manager
    ):
        """Test checking upstream when no update available."""
        fetch_result = UpdateFetchResult(
            artifact=mock_artifact,
            has_update=False,
        )

        mock_artifact_manager.fetch_update.return_value = fetch_result

        with patch(
            "skillmeat.api.routers.artifacts.ArtifactManagerDep",
            return_value=mock_artifact_manager,
        ), patch(
            "skillmeat.api.routers.artifacts.CollectionManagerDep",
            return_value=mock_collection_manager,
        ):
            response = client.get("/api/v1/artifacts/skill:pdf-skill/upstream")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["update_available"] is False

    def test_check_upstream_local_artifact(
        self, client, mock_collection_manager
    ):
        """Test checking upstream for local artifact (not supported)."""
        # Create local artifact (no upstream tracking)
        local_artifact = Artifact(
            name="local-skill",
            type=ArtifactType.SKILL,
            path="skills/local-skill",
            origin="local",
            metadata=ArtifactMetadata(),
            added=datetime(2024, 11, 1, 12, 0, 0),
        )

        mock_art_mgr = MagicMock()
        mock_art_mgr.show.return_value = local_artifact

        with patch(
            "skillmeat.api.routers.artifacts.ArtifactManagerDep",
            return_value=mock_art_mgr,
        ), patch(
            "skillmeat.api.routers.artifacts.CollectionManagerDep",
            return_value=mock_collection_manager,
        ):
            response = client.get("/api/v1/artifacts/skill:local-skill/upstream")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_check_upstream_artifact_not_found(self, client, mock_collection_manager):
        """Test checking upstream for non-existent artifact."""
        mock_art_mgr = MagicMock()
        mock_art_mgr.show.side_effect = ValueError("Artifact not found")

        with patch(
            "skillmeat.api.routers.artifacts.ArtifactManagerDep",
            return_value=mock_art_mgr,
        ), patch(
            "skillmeat.api.routers.artifacts.CollectionManagerDep",
            return_value=mock_collection_manager,
        ):
            response = client.get("/api/v1/artifacts/skill:nonexistent/upstream")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUpdateArtifact:
    """Test PUT /api/v1/artifacts/{artifact_id} endpoint."""

    def test_update_artifact_tags_success(
        self, client, mock_artifact, mock_artifact_manager, mock_collection_manager
    ):
        """Test updating artifact tags."""
        # Mock collection loading
        mock_collection = MagicMock()
        mock_collection.name = "default"
        mock_collection.find_artifact.return_value = mock_artifact
        mock_collection_manager.load_collection.return_value = mock_collection
        mock_collection_manager.config.get_collection_path.return_value = "/path/to/collection"

        # Mock save
        mock_collection_manager.save_collection.return_value = None
        mock_collection_manager.lock_mgr.update_entry.return_value = None

        with patch(
            "skillmeat.api.routers.artifacts.ArtifactManagerDep",
            return_value=mock_artifact_manager,
        ), patch(
            "skillmeat.api.routers.artifacts.CollectionManagerDep",
            return_value=mock_collection_manager,
        ), patch(
            "skillmeat.api.routers.artifacts.compute_content_hash",
            return_value="abc123hash",
        ):
            response = client.put(
                "/api/v1/artifacts/skill:pdf-skill",
                json={"tags": ["updated", "tags"]},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "pdf-skill"

    def test_update_artifact_metadata_success(
        self, client, mock_artifact, mock_artifact_manager, mock_collection_manager
    ):
        """Test updating artifact metadata."""
        # Mock collection loading
        mock_collection = MagicMock()
        mock_collection.name = "default"
        mock_collection.find_artifact.return_value = mock_artifact
        mock_collection_manager.load_collection.return_value = mock_collection
        mock_collection_manager.config.get_collection_path.return_value = "/path/to/collection"

        with patch(
            "skillmeat.api.routers.artifacts.ArtifactManagerDep",
            return_value=mock_artifact_manager,
        ), patch(
            "skillmeat.api.routers.artifacts.CollectionManagerDep",
            return_value=mock_collection_manager,
        ), patch(
            "skillmeat.api.routers.artifacts.compute_content_hash",
            return_value="abc123hash",
        ):
            response = client.put(
                "/api/v1/artifacts/skill:pdf-skill",
                json={
                    "metadata": {
                        "title": "Updated PDF Skill",
                        "description": "Updated description",
                    }
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "pdf-skill"

    def test_update_artifact_not_found(self, client, mock_collection_manager):
        """Test updating a non-existent artifact."""
        mock_collection = MagicMock()
        mock_collection.find_artifact.return_value = None
        mock_collection_manager.load_collection.return_value = mock_collection

        mock_art_mgr = MagicMock()

        with patch(
            "skillmeat.api.routers.artifacts.ArtifactManagerDep",
            return_value=mock_art_mgr,
        ), patch(
            "skillmeat.api.routers.artifacts.CollectionManagerDep",
            return_value=mock_collection_manager,
        ):
            response = client.put(
                "/api/v1/artifacts/skill:nonexistent",
                json={"tags": ["test"]},
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_artifact_invalid_id(self, client):
        """Test updating artifact with invalid ID format."""
        response = client.put(
            "/api/v1/artifacts/invalid-id",
            json={"tags": ["test"]},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_artifact_with_aliases_warning(
        self, client, mock_artifact, mock_artifact_manager, mock_collection_manager
    ):
        """Test updating artifact aliases logs warning (not implemented yet)."""
        # Mock collection loading
        mock_collection = MagicMock()
        mock_collection.name = "default"
        mock_collection.find_artifact.return_value = mock_artifact
        mock_collection_manager.load_collection.return_value = mock_collection
        mock_collection_manager.config.get_collection_path.return_value = "/path/to/collection"

        with patch(
            "skillmeat.api.routers.artifacts.ArtifactManagerDep",
            return_value=mock_artifact_manager,
        ), patch(
            "skillmeat.api.routers.artifacts.CollectionManagerDep",
            return_value=mock_collection_manager,
        ), patch(
            "skillmeat.api.routers.artifacts.compute_content_hash",
            return_value="abc123hash",
        ):
            # Aliases should be accepted but not applied (logged warning)
            response = client.put(
                "/api/v1/artifacts/skill:pdf-skill",
                json={"aliases": ["pdf-processor"]},
            )

        # Should succeed but aliases not applied
        assert response.status_code == status.HTTP_200_OK


class TestDeleteArtifact:
    """Test DELETE /api/v1/artifacts/{artifact_id} endpoint."""

    def test_delete_artifact_success(
        self, client, mock_artifact, mock_artifact_manager, mock_collection_manager
    ):
        """Test deleting an artifact."""
        # Mock collection loading
        mock_collection = MagicMock()
        mock_collection.name = "default"
        mock_collection.find_artifact.return_value = mock_artifact
        mock_collection_manager.load_collection.return_value = mock_collection

        # Mock remove operation
        mock_artifact_manager.remove.return_value = None

        with patch(
            "skillmeat.api.routers.artifacts.ArtifactManagerDep",
            return_value=mock_artifact_manager,
        ), patch(
            "skillmeat.api.routers.artifacts.CollectionManagerDep",
            return_value=mock_collection_manager,
        ):
            response = client.delete("/api/v1/artifacts/skill:pdf-skill")

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_artifact_not_found(self, client, mock_collection_manager):
        """Test deleting a non-existent artifact."""
        # Mock collection loading with no artifact found
        mock_collection = MagicMock()
        mock_collection.find_artifact.return_value = None
        mock_collection_manager.load_collection.return_value = mock_collection

        mock_art_mgr = MagicMock()

        with patch(
            "skillmeat.api.routers.artifacts.ArtifactManagerDep",
            return_value=mock_art_mgr,
        ), patch(
            "skillmeat.api.routers.artifacts.CollectionManagerDep",
            return_value=mock_collection_manager,
        ):
            response = client.delete("/api/v1/artifacts/skill:nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_artifact_invalid_id(self, client):
        """Test deleting artifact with invalid ID format."""
        response = client.delete("/api/v1/artifacts/invalid-id")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_artifact_with_collection_filter(
        self, client, mock_artifact, mock_artifact_manager, mock_collection_manager
    ):
        """Test deleting artifact with collection filter."""
        # Mock collection loading
        mock_collection = MagicMock()
        mock_collection.name = "default"
        mock_collection.find_artifact.return_value = mock_artifact
        mock_collection_manager.load_collection.return_value = mock_collection

        # Mock remove operation
        mock_artifact_manager.remove.return_value = None

        with patch(
            "skillmeat.api.routers.artifacts.ArtifactManagerDep",
            return_value=mock_artifact_manager,
        ), patch(
            "skillmeat.api.routers.artifacts.CollectionManagerDep",
            return_value=mock_collection_manager,
        ):
            response = client.delete(
                "/api/v1/artifacts/skill:pdf-skill?collection=default"
            )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_artifact_manager_error(
        self, client, mock_artifact, mock_artifact_manager, mock_collection_manager
    ):
        """Test delete when artifact manager raises error."""
        # Mock collection loading
        mock_collection = MagicMock()
        mock_collection.name = "default"
        mock_collection.find_artifact.return_value = mock_artifact
        mock_collection_manager.load_collection.return_value = mock_collection

        # Mock remove operation to raise ValueError
        mock_artifact_manager.remove.side_effect = ValueError("Artifact not found")

        with patch(
            "skillmeat.api.routers.artifacts.ArtifactManagerDep",
            return_value=mock_artifact_manager,
        ), patch(
            "skillmeat.api.routers.artifacts.CollectionManagerDep",
            return_value=mock_collection_manager,
        ):
            response = client.delete("/api/v1/artifacts/skill:pdf-skill")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestSourceProjectDiff:
    """Test GET /api/v1/artifacts/{artifact_id}/source-project-diff endpoint."""

    def test_source_project_diff_missing_project_path(self, client):
        """Test source-project diff without project_path parameter."""
        response = client.get("/api/v1/artifacts/skill:pdf-skill/source-project-diff")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_source_project_diff_invalid_project_path(self, client):
        """Test source-project diff with non-existent project path."""
        response = client.get(
            "/api/v1/artifacts/skill:pdf-skill/source-project-diff?project_path=/nonexistent/path"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_source_project_diff_invalid_artifact_id(self, client, tmp_path):
        """Test source-project diff with invalid artifact ID format."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        response = client.get(
            f"/api/v1/artifacts/invalid-id/source-project-diff?project_path={project_path}"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid artifact ID format" in response.json()["detail"]


class TestDeployWithMergeStrategy:
    """Test POST /api/v1/artifacts/{artifact_id}/deploy with merge strategy."""

    def test_deploy_invalid_artifact_id(self, client, tmp_path):
        """Test deploy with invalid artifact ID format."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        response = client.post(
            "/api/v1/artifacts/invalid-id/deploy",
            json={
                "project_path": str(project_path),
                "strategy": "merge",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid artifact ID format" in response.json()["detail"]

    def test_deploy_invalid_project_path(self, client):
        """Test deploy with non-existent project path."""
        response = client.post(
            "/api/v1/artifacts/skill:test/deploy",
            json={
                "project_path": "/nonexistent/path",
                "strategy": "merge",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestDeploySchemaValidation:
    """Test schema validation for deploy endpoint."""

    def test_artifact_deploy_request_default_strategy(self):
        """Test ArtifactDeployRequest default strategy is 'overwrite'."""
        from skillmeat.api.schemas.artifacts import ArtifactDeployRequest

        request = ArtifactDeployRequest(project_path="/tmp/test")
        assert request.strategy == "overwrite"

    def test_artifact_deploy_request_invalid_strategy(self):
        """Test invalid strategy value is rejected."""
        from skillmeat.api.schemas.artifacts import ArtifactDeployRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ArtifactDeployRequest(
                project_path="/tmp/test",
                strategy="invalid",
            )

    def test_artifact_deploy_response_backward_compatibility(self):
        """Test ArtifactDeployResponse backward compatibility (no strategy field)."""
        from skillmeat.api.schemas.artifacts import ArtifactDeployResponse

        response = ArtifactDeployResponse(
            success=True,
            message="Deployed",
            artifact_name="test",
            artifact_type="skill",
        )
        assert response.strategy is None
        assert response.merge_details is None

    def test_merge_deploy_details_serialization(self):
        """Test MergeDeployDetails serialization."""
        from skillmeat.api.schemas.artifacts import MergeDeployDetails, MergeFileAction

        details = MergeDeployDetails(
            files_copied=2,
            files_skipped=1,
            files_preserved=1,
            conflicts=1,
            file_actions=[
                MergeFileAction(file_path="test.md", action="copied"),
                MergeFileAction(file_path="same.md", action="skipped"),
                MergeFileAction(
                    file_path="conflict.md",
                    action="conflict",
                    detail="Modified on both sides",
                ),
            ],
        )

        data = details.model_dump()
        assert data["files_copied"] == 2
        assert data["conflicts"] == 1
        assert len(data["file_actions"]) == 3


class TestArtifactsAuth:
    """Test authentication for artifacts endpoints."""

    def test_artifacts_with_api_key_enabled(self):
        """Test that API key is required when enabled."""
        test_settings = APISettings(
            env=Environment.TESTING,
            api_key_enabled=True,
            api_key="test-api-key",
        )

        from skillmeat.api.config import get_settings

        app = create_app(test_settings)
        app.dependency_overrides[get_settings] = lambda: test_settings

        with TestClient(app) as client:
            # Request without API key should fail
            response = client.get("/api/v1/artifacts")
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

            # Request with valid API key should succeed
            response = client.get(
                "/api/v1/artifacts", headers={"X-API-Key": "test-api-key"}
            )
            # May fail for other reasons, but not auth
            assert response.status_code != status.HTTP_401_UNAUTHORIZED
