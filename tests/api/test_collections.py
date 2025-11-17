"""Tests for Collections API endpoints.

This module tests the /api/v1/collections endpoints, including:
- List collections with pagination
- Get collection details
- List artifacts in collection with pagination
"""

import pytest
from datetime import datetime
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app
from skillmeat.core.artifact import Artifact, ArtifactType, ArtifactMetadata
from skillmeat.core.collection import Collection


@pytest.fixture
def test_settings():
    """Create test settings."""
    return APISettings(
        env=Environment.TESTING,
        host="127.0.0.1",
        port=8000,
        log_level="DEBUG",
        cors_enabled=True,
        cors_origins=["http://localhost:3000"],
        api_key_enabled=False,  # Disable API key for testing
    )


@pytest.fixture
def app(test_settings):
    """Create FastAPI app for testing."""
    from skillmeat.api.config import get_settings

    app = create_app(test_settings)
    app.dependency_overrides[get_settings] = lambda: test_settings

    return app


@pytest.fixture
def client(app, mock_collection_manager):
    """Create test client with lifespan context and dependency overrides."""
    from skillmeat.api.dependencies import get_collection_manager
    from skillmeat.api.middleware.auth import verify_token

    # Override dependencies
    app.dependency_overrides[get_collection_manager] = lambda: mock_collection_manager
    app.dependency_overrides[verify_token] = lambda: "mock-token"

    with TestClient(app) as test_client:
        yield test_client

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
def mock_collection_manager():
    """Create mock CollectionManager."""
    mock_mgr = MagicMock()

    # Mock collection
    mock_collection = Collection(
        name="default",
        version="1.0.0",
        artifacts=[],
        created=datetime(2024, 11, 1, 12, 0, 0),
        updated=datetime(2024, 11, 16, 12, 0, 0),
    )

    # Add some test artifacts
    mock_collection.artifacts = [
        Artifact(
            name="pdf-skill",
            type=ArtifactType.SKILL,
            path="skills/pdf-skill",
            origin="github",
            metadata=ArtifactMetadata(
                title="PDF Skill",
                description="Process PDF files",
                tags=["pdf", "document"],
            ),
            added=datetime(2024, 11, 1, 12, 0, 0),
            upstream="anthropics/skills/pdf",
            version_spec="latest",
            resolved_sha="abc123",
        ),
        Artifact(
            name="excel-skill",
            type=ArtifactType.SKILL,
            path="skills/excel-skill",
            origin="github",
            metadata=ArtifactMetadata(
                title="Excel Skill",
                description="Process Excel files",
                tags=["excel", "spreadsheet"],
            ),
            added=datetime(2024, 11, 2, 12, 0, 0),
            upstream="anthropics/skills/excel",
            version_spec="latest",
        ),
    ]

    mock_mgr.list_collections.return_value = ["default", "work"]
    mock_mgr.load_collection.return_value = mock_collection

    return mock_mgr


class TestListCollections:
    """Test GET /api/v1/collections endpoint."""

    def test_list_collections_success(self, client, mock_collection_manager):
        """Test listing collections returns paginated results."""
        response = client.get("/api/v1/collections")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check response structure
        assert "items" in data
        assert "page_info" in data

        # Check page info
        page_info = data["page_info"]
        assert "has_next_page" in page_info
        assert "has_previous_page" in page_info
        assert "total_count" in page_info

    def test_list_collections_pagination(self, client, mock_collection_manager):
        """Test pagination with limit parameter."""
        with patch(
            "skillmeat.api.routers.collections.CollectionManagerDep",
            return_value=mock_collection_manager,
        ):
            response = client.get("/api/v1/collections?limit=1")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should return only 1 item
        assert len(data["items"]) == 1

        # Should indicate there's a next page
        assert data["page_info"]["has_next_page"] is True

    def test_list_collections_with_cursor(self, client, mock_collection_manager):
        """Test pagination with cursor."""
        import base64

        # Create cursor for second page
        cursor = base64.b64encode("default".encode()).decode()

        with patch(
            "skillmeat.api.routers.collections.CollectionManagerDep",
            return_value=mock_collection_manager,
        ):
            response = client.get(f"/api/v1/collections?after={cursor}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should have previous page
        assert data["page_info"]["has_previous_page"] is True

    def test_list_collections_empty(self, client):
        """Test listing collections when none exist."""
        mock_mgr = MagicMock()
        mock_mgr.list_collections.return_value = []

        with patch(
            "skillmeat.api.routers.collections.CollectionManagerDep",
            return_value=mock_mgr,
        ):
            response = client.get("/api/v1/collections")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 0
        assert data["page_info"]["total_count"] == 0


class TestGetCollection:
    """Test GET /api/v1/collections/{collection_id} endpoint."""

    def test_get_collection_success(self, client, mock_collection_manager):
        """Test getting a specific collection."""
        with patch(
            "skillmeat.api.routers.collections.CollectionManagerDep",
            return_value=mock_collection_manager,
        ):
            response = client.get("/api/v1/collections/default")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check response structure
        assert data["id"] == "default"
        assert data["name"] == "default"
        assert data["version"] == "1.0.0"
        assert "artifact_count" in data
        assert "created" in data
        assert "updated" in data

    def test_get_collection_not_found(self, client):
        """Test getting a non-existent collection."""
        mock_mgr = MagicMock()
        mock_mgr.list_collections.return_value = []

        with patch(
            "skillmeat.api.routers.collections.CollectionManagerDep",
            return_value=mock_mgr,
        ):
            response = client.get("/api/v1/collections/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data


class TestListCollectionArtifacts:
    """Test GET /api/v1/collections/{collection_id}/artifacts endpoint."""

    def test_list_artifacts_success(self, client, mock_collection_manager):
        """Test listing artifacts in a collection."""
        with patch(
            "skillmeat.api.routers.collections.CollectionManagerDep",
            return_value=mock_collection_manager,
        ):
            response = client.get("/api/v1/collections/default/artifacts")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check response structure
        assert "items" in data
        assert "page_info" in data

        # Check artifacts
        items = data["items"]
        assert len(items) > 0

        # Check artifact structure
        artifact = items[0]
        assert "name" in artifact
        assert "type" in artifact
        assert "source" in artifact
        assert "version" in artifact

    def test_list_artifacts_with_type_filter(self, client, mock_collection_manager):
        """Test filtering artifacts by type."""
        with patch(
            "skillmeat.api.routers.collections.CollectionManagerDep",
            return_value=mock_collection_manager,
        ):
            response = client.get(
                "/api/v1/collections/default/artifacts?artifact_type=skill"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # All items should be skills
        for item in data["items"]:
            assert item["type"] == "skill"

    def test_list_artifacts_pagination(self, client, mock_collection_manager):
        """Test pagination for artifact listing."""
        with patch(
            "skillmeat.api.routers.collections.CollectionManagerDep",
            return_value=mock_collection_manager,
        ):
            response = client.get("/api/v1/collections/default/artifacts?limit=1")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should return only 1 item
        assert len(data["items"]) == 1

        # Should have pagination cursors
        assert data["page_info"]["start_cursor"] is not None
        assert data["page_info"]["end_cursor"] is not None

    def test_list_artifacts_collection_not_found(self, client):
        """Test listing artifacts for non-existent collection."""
        mock_mgr = MagicMock()
        mock_mgr.list_collections.return_value = []

        with patch(
            "skillmeat.api.routers.collections.CollectionManagerDep",
            return_value=mock_mgr,
        ):
            response = client.get("/api/v1/collections/nonexistent/artifacts")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_artifacts_invalid_type(self, client, mock_collection_manager):
        """Test invalid artifact type filter."""
        with patch(
            "skillmeat.api.routers.collections.CollectionManagerDep",
            return_value=mock_collection_manager,
        ):
            response = client.get(
                "/api/v1/collections/default/artifacts?artifact_type=invalid"
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestCollectionsAuth:
    """Test authentication for collections endpoints."""

    def test_collections_with_api_key_enabled(self):
        """Test that API key is required when enabled."""
        # Create settings with API key enabled
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
            response = client.get("/api/v1/collections")
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

            # Request with valid API key should succeed
            response = client.get(
                "/api/v1/collections", headers={"X-API-Key": "test-api-key"}
            )
            # May fail for other reasons, but not auth
            assert response.status_code != status.HTTP_401_UNAUTHORIZED
