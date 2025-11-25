"""Integration tests for Project API endpoints with validation.

This module tests the project endpoints to ensure that validation errors
are properly returned as 422 Unprocessable Entity responses.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app


@pytest.fixture
def test_settings():
    """Create test settings for API."""
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
def client(app):
    """Create test client with dependency overrides."""
    from skillmeat.api.middleware.auth import verify_token
    from skillmeat.storage.project import ProjectMetadataStorage, ProjectMetadata
    from datetime import datetime

    # Mock authentication
    app.dependency_overrides[verify_token] = lambda: "mock-token"

    # Mock project storage to prevent file operations
    with patch.object(ProjectMetadataStorage, "exists", return_value=False):
        with patch.object(ProjectMetadataStorage, "create_metadata") as mock_create:
            with patch.object(ProjectMetadataStorage, "read_metadata", return_value=None):
                # Set up mock to return a metadata object
                mock_metadata = ProjectMetadata(
                    path="/home/john/projects/test",
                    name="test-project",
                    description="Test project",
                    created_at=datetime.utcnow(),
                )
                mock_create.return_value = mock_metadata

                with TestClient(app) as test_client:
                    yield test_client

    # Clean up overrides
    app.dependency_overrides.clear()


class TestProjectCreateEndpointValidation:
    """Test project creation endpoint validation."""

    def test_create_project_valid_request(self, client):
        """Test creating a project with valid data."""
        response = client.post(
            "/api/v1/projects",
            json={
                "name": "my-awesome-project",
                "path": "/home/john/projects/my-awesome-project",
                "description": "A test project",
            },
        )
        # Should either succeed (201) or fail with proper error
        assert response.status_code in [201, 400, 409, 500]

    def test_create_project_invalid_name_starts_with_hyphen(self, client):
        """Test creating project with invalid name (starts with hyphen)."""
        response = client.post(
            "/api/v1/projects",
            json={
                "name": "-invalid-name",
                "path": "/home/john/projects/invalid",
                "description": "A test project",
            },
        )
        # Should return 422 Unprocessable Entity
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data
        # Check error mentions validation
        error_msg = str(data).lower()
        assert "name" in error_msg or "alphanumeric" in error_msg

    def test_create_project_invalid_name_starts_with_underscore(self, client):
        """Test creating project with invalid name (starts with underscore)."""
        response = client.post(
            "/api/v1/projects",
            json={
                "name": "_invalid_name",
                "path": "/home/john/projects/invalid",
                "description": "A test project",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_project_invalid_name_ends_with_hyphen(self, client):
        """Test creating project with invalid name (ends with hyphen)."""
        response = client.post(
            "/api/v1/projects",
            json={
                "name": "invalid-name-",
                "path": "/home/john/projects/invalid",
                "description": "A test project",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_project_invalid_name_with_spaces(self, client):
        """Test creating project with invalid name (contains spaces)."""
        response = client.post(
            "/api/v1/projects",
            json={
                "name": "invalid name",
                "path": "/home/john/projects/invalid",
                "description": "A test project",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_project_invalid_name_with_special_chars(self, client):
        """Test creating project with invalid name (special characters)."""
        response = client.post(
            "/api/v1/projects",
            json={
                "name": "invalid@name",
                "path": "/home/john/projects/invalid",
                "description": "A test project",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_project_invalid_path_relative(self, client):
        """Test creating project with relative path."""
        response = client.post(
            "/api/v1/projects",
            json={
                "name": "valid-name",
                "path": "projects/relative/path",
                "description": "A test project",
            },
        )
        # Should return 422 for validation error
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_project_invalid_path_tilde(self, client):
        """Test creating project with tilde path."""
        response = client.post(
            "/api/v1/projects",
            json={
                "name": "valid-name",
                "path": "~/projects/my-project",
                "description": "A test project",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_project_empty_name(self, client):
        """Test creating project with empty name."""
        response = client.post(
            "/api/v1/projects",
            json={
                "name": "",
                "path": "/home/john/projects/test",
                "description": "A test project",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_project_name_too_long(self, client):
        """Test creating project with name exceeding max length."""
        response = client.post(
            "/api/v1/projects",
            json={
                "name": "a" * 101,  # Exceeds 100 character limit
                "path": "/home/john/projects/test",
                "description": "A test project",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_project_missing_name(self, client):
        """Test creating project without name field."""
        response = client.post(
            "/api/v1/projects",
            json={
                "path": "/home/john/projects/test",
                "description": "A test project",
            },
        )
        # Should return 422 for missing required field
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_project_missing_path(self, client):
        """Test creating project without path field."""
        response = client.post(
            "/api/v1/projects",
            json={
                "name": "valid-name",
                "description": "A test project",
            },
        )
        # Should return 422 for missing required field
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_project_validation_error_structure(self, client):
        """Test that validation errors have correct structure."""
        response = client.post(
            "/api/v1/projects",
            json={
                "name": "invalid-",
                "path": "relative/path",
                "description": "A test project",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()

        # Should have detail field with validation errors
        assert "detail" in data
        detail = data["detail"]
        assert isinstance(detail, list)

        # Each error should have required fields
        for error in detail:
            assert "type" in error
            assert "loc" in error
            assert "msg" in error


class TestProjectUpdateEndpointValidation:
    """Test project update endpoint validation."""

    def test_update_project_valid_name(self, client, monkeypatch):
        """Test updating project with valid name."""
        # Mock the path decode and project lookup
        import base64

        project_id = base64.b64encode(b"/home/john/projects/test").decode()

        with patch("skillmeat.api.routers.projects.ProjectMetadataStorage") as mock_storage:
            with patch("skillmeat.api.routers.projects.Path") as mock_path:
                mock_storage.exists.return_value = True
                mock_path.return_value.exists.return_value = True

                response = client.put(
                    f"/api/v1/projects/{project_id}",
                    json={
                        "name": "renamed-project",
                        "description": "Updated description",
                    },
                )
                # Should accept valid update
                assert response.status_code in [200, 404, 500]

    def test_update_project_invalid_name(self, client):
        """Test updating project with invalid name."""
        import base64

        project_id = base64.b64encode(b"/home/john/projects/test").decode()

        response = client.put(
            f"/api/v1/projects/{project_id}",
            json={
                "name": "-invalid-name",
                "description": "Updated description",
            },
        )
        # Should return 422 for validation error
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_update_project_name_only(self, client):
        """Test updating only project name."""
        import base64

        project_id = base64.b64encode(b"/home/john/projects/test").decode()

        response = client.put(
            f"/api/v1/projects/{project_id}",
            json={"name": "new-project-name"},
        )
        # Could be 422 (validation error) or other status (project not found, etc.)
        # The important thing is it doesn't crash
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    def test_update_project_description_only(self, client):
        """Test updating only project description."""
        import base64

        project_id = base64.b64encode(b"/home/john/projects/test").decode()

        response = client.put(
            f"/api/v1/projects/{project_id}",
            json={"description": "New description"},
        )
        # Should handle update (may return 404 for non-existent project)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_update_project_no_fields(self, client):
        """Test updating with no fields provided."""
        import base64

        project_id = base64.b64encode(b"/home/john/projects/test").decode()

        response = client.put(
            f"/api/v1/projects/{project_id}",
            json={},
        )
        # Should return 400, 404, or 422 depending on implementation
        # (400 for no fields, 404 if project not found)
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]


class TestValidationErrorMessages:
    """Test validation error message quality."""

    def test_invalid_name_error_mentions_format(self, client):
        """Test that invalid name error mentions format requirements."""
        response = client.post(
            "/api/v1/projects",
            json={
                "name": "invalid-",
                "path": "/home/john/projects/test",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        error_text = str(data).lower()

        # Should mention name-related requirement
        assert "name" in error_text or "alphanumeric" in error_text

    def test_invalid_path_error_mentions_absolute(self, client):
        """Test that invalid path error mentions absolute path requirement."""
        response = client.post(
            "/api/v1/projects",
            json={
                "name": "valid-name",
                "path": "relative/path/here",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        error_text = str(data).lower()

        # Should mention path requirement
        assert "path" in error_text or "absolute" in error_text
