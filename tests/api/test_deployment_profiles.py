"""Tests for Deployment Profiles API endpoints.

This module tests the /api/v1/projects/{project_id}/profiles endpoints:
- Create a deployment profile (POST)
- List profiles for a project (GET)
- Get a single profile (GET)
- Update a profile (PUT)
- Delete a profile (DELETE)

The router is nested under the /projects prefix and uses verify_api_key +
TokenDep dependencies; both are bypassed in tests by overriding dependencies.
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app
from skillmeat.core.enums import Platform


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_settings():
    """Create test API settings with auth and API key disabled."""
    return APISettings(
        env=Environment.TESTING,
        host="127.0.0.1",
        port=8000,
        log_level="DEBUG",
        api_key_enabled=False,
        auth_enabled=False,
    )


@pytest.fixture
def app(test_settings):
    """Create FastAPI test application with dependency overrides."""
    from skillmeat.api.config import get_settings
    from skillmeat.api.dependencies import verify_api_key
    from skillmeat.api.middleware.auth import verify_token

    application = create_app(test_settings)
    application.dependency_overrides[get_settings] = lambda: test_settings
    # Bypass API key and token auth for tests
    application.dependency_overrides[verify_api_key] = lambda: None
    application.dependency_overrides[verify_token] = lambda: "test-token"
    return application


@pytest.fixture
def client(app):
    """Create test client."""
    with TestClient(app) as test_client:
        yield test_client


def _make_profile_orm(
    id="profile-db-id-001",
    project_id="project-db-id-001",
    profile_id="default",
    platform="claude_code",
    root_dir="/home/user/.claude",
    description="Default Claude Code profile",
    artifact_path_map=None,
    config_filenames=None,
    context_prefixes=None,
    supported_types=None,
    created_at=None,
    updated_at=None,
):
    """Build a mock DeploymentProfile ORM-like object."""
    p = MagicMock()
    p.id = id
    p.project_id = project_id
    p.profile_id = profile_id
    p.platform = platform
    p.root_dir = root_dir
    p.description = description
    p.artifact_path_map = artifact_path_map or {}
    p.config_filenames = config_filenames or []
    p.context_prefixes = context_prefixes or []
    p.supported_types = supported_types or []
    p.created_at = created_at or datetime(2026, 1, 1, 0, 0, 0)
    p.updated_at = updated_at or datetime(2026, 1, 2, 0, 0, 0)
    return p


def _make_mock_session(project_id="project-db-id-001"):
    """Build a mock SQLAlchemy session that resolves project_id directly."""
    mock_project = MagicMock()
    mock_project.id = project_id
    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.first.return_value = mock_project
    return mock_session


# Minimal valid create payload
VALID_CREATE_PAYLOAD = {
    "profile_id": "default",
    "platform": "claude_code",
    "root_dir": "/home/user/.claude",
    "description": "Default Claude Code profile",
}

# Base URL pattern
_BASE = "/api/v1/projects/{project_id}/profiles"


def _url(project_id="test-project-001", profile_id=None):
    base = _BASE.format(project_id=project_id)
    if profile_id is not None:
        return f"{base}/{profile_id}"
    return base


# ---------------------------------------------------------------------------
# POST /api/v1/projects/{project_id}/profiles — create_profile
# ---------------------------------------------------------------------------


class TestCreateProfile:
    """Tests for POST /api/v1/projects/{project_id}/profiles."""

    def test_create_profile_success(self, app, client):
        """Creating a deployment profile returns 201 with profile data."""
        from skillmeat.api.dependencies import get_deployment_profile_repository
        from skillmeat.cache.session import get_db_session

        profile = _make_profile_orm()
        mock_repo = MagicMock()
        mock_repo.create.return_value = profile
        mock_session = _make_mock_session()

        app.dependency_overrides[get_deployment_profile_repository] = lambda: mock_repo
        app.dependency_overrides[get_db_session] = lambda: mock_session
        try:
            response = client.post(_url("test-project-001"), json=VALID_CREATE_PAYLOAD)
        finally:
            app.dependency_overrides.pop(get_deployment_profile_repository, None)
            app.dependency_overrides.pop(get_db_session, None)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["profile_id"] == "default"
        assert data["platform"] == "claude_code"

    def test_create_profile_duplicate_returns_409(self, app, client):
        """Creating a duplicate profile returns 409 Conflict."""
        from skillmeat.api.dependencies import get_deployment_profile_repository
        from skillmeat.cache.session import get_db_session

        mock_repo = MagicMock()
        mock_repo.create.side_effect = Exception(
            "UNIQUE constraint failed: deployment_profiles.project_id"
        )
        mock_session = _make_mock_session()

        app.dependency_overrides[get_deployment_profile_repository] = lambda: mock_repo
        app.dependency_overrides[get_db_session] = lambda: mock_session
        try:
            response = client.post(_url("test-project-001"), json=VALID_CREATE_PAYLOAD)
        finally:
            app.dependency_overrides.pop(get_deployment_profile_repository, None)
            app.dependency_overrides.pop(get_db_session, None)

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_create_profile_missing_required_fields_returns_422(self, client):
        """Missing required fields (profile_id, platform, root_dir) returns 422."""
        response = client.post(_url("test-project-001"), json={"description": "incomplete"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_profile_invalid_platform_returns_422(self, client):
        """Invalid platform value returns 422."""
        payload = {**VALID_CREATE_PAYLOAD, "platform": "not_a_real_platform"}
        response = client.post(_url("test-project-001"), json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# GET /api/v1/projects/{project_id}/profiles — list_profiles
# ---------------------------------------------------------------------------


class TestListProfiles:
    """Tests for GET /api/v1/projects/{project_id}/profiles."""

    def test_list_profiles_empty(self, app, client):
        """Listing profiles for a project with none returns 200 empty list."""
        from skillmeat.api.dependencies import get_deployment_profile_repository
        from skillmeat.cache.session import get_db_session

        mock_repo = MagicMock()
        mock_repo.list_by_project.return_value = []
        mock_session = _make_mock_session()

        app.dependency_overrides[get_deployment_profile_repository] = lambda: mock_repo
        app.dependency_overrides[get_db_session] = lambda: mock_session
        try:
            response = client.get(_url("test-project-001"))
        finally:
            app.dependency_overrides.pop(get_deployment_profile_repository, None)
            app.dependency_overrides.pop(get_db_session, None)

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_list_profiles_returns_all_profiles(self, app, client):
        """Listing profiles returns all profiles for the project."""
        from skillmeat.api.dependencies import get_deployment_profile_repository
        from skillmeat.cache.session import get_db_session

        p1 = _make_profile_orm(profile_id="default")
        p2 = _make_profile_orm(id="prof-002", profile_id="staging", platform="cursor")

        mock_repo = MagicMock()
        mock_repo.list_by_project.return_value = [p1, p2]
        mock_session = _make_mock_session()

        app.dependency_overrides[get_deployment_profile_repository] = lambda: mock_repo
        app.dependency_overrides[get_db_session] = lambda: mock_session
        try:
            response = client.get(_url("test-project-001"))
        finally:
            app.dependency_overrides.pop(get_deployment_profile_repository, None)
            app.dependency_overrides.pop(get_db_session, None)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["profile_id"] == "default"
        assert data[1]["profile_id"] == "staging"


# ---------------------------------------------------------------------------
# GET /api/v1/projects/{project_id}/profiles/{profile_id} — get_profile
# ---------------------------------------------------------------------------


class TestGetProfile:
    """Tests for GET /api/v1/projects/{project_id}/profiles/{profile_id}."""

    def test_get_profile_success(self, app, client):
        """Fetching an existing profile returns 200 with profile data."""
        from skillmeat.api.dependencies import get_deployment_profile_repository
        from skillmeat.cache.session import get_db_session

        profile = _make_profile_orm(profile_id="default")
        mock_repo = MagicMock()
        mock_repo.read_by_project_and_profile_id.return_value = profile
        mock_session = _make_mock_session()

        app.dependency_overrides[get_deployment_profile_repository] = lambda: mock_repo
        app.dependency_overrides[get_db_session] = lambda: mock_session
        try:
            response = client.get(_url("test-project-001", "default"))
        finally:
            app.dependency_overrides.pop(get_deployment_profile_repository, None)
            app.dependency_overrides.pop(get_db_session, None)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["profile_id"] == "default"

    def test_get_profile_not_found(self, app, client):
        """Fetching a non-existent profile returns 404."""
        from skillmeat.api.dependencies import get_deployment_profile_repository
        from skillmeat.cache.session import get_db_session

        mock_repo = MagicMock()
        mock_repo.read_by_project_and_profile_id.return_value = None
        mock_session = _make_mock_session()

        app.dependency_overrides[get_deployment_profile_repository] = lambda: mock_repo
        app.dependency_overrides[get_db_session] = lambda: mock_session
        try:
            response = client.get(_url("test-project-001", "ghost-profile"))
        finally:
            app.dependency_overrides.pop(get_deployment_profile_repository, None)
            app.dependency_overrides.pop(get_db_session, None)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "ghost-profile" in response.json()["detail"]


# ---------------------------------------------------------------------------
# PUT /api/v1/projects/{project_id}/profiles/{profile_id} — update_profile
# ---------------------------------------------------------------------------


class TestUpdateProfile:
    """Tests for PUT /api/v1/projects/{project_id}/profiles/{profile_id}."""

    def test_update_profile_success(self, app, client):
        """Updating an existing profile returns 200 with updated data."""
        from skillmeat.api.dependencies import get_deployment_profile_repository
        from skillmeat.cache.session import get_db_session

        updated_profile = _make_profile_orm(description="Updated description")
        mock_repo = MagicMock()
        mock_repo.update.return_value = updated_profile
        mock_session = _make_mock_session()

        app.dependency_overrides[get_deployment_profile_repository] = lambda: mock_repo
        app.dependency_overrides[get_db_session] = lambda: mock_session
        try:
            response = client.put(
                _url("test-project-001", "default"),
                json={"description": "Updated description"},
            )
        finally:
            app.dependency_overrides.pop(get_deployment_profile_repository, None)
            app.dependency_overrides.pop(get_db_session, None)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["description"] == "Updated description"

    def test_update_profile_not_found(self, app, client):
        """Updating a non-existent profile returns 404."""
        from skillmeat.api.dependencies import get_deployment_profile_repository
        from skillmeat.cache.session import get_db_session

        mock_repo = MagicMock()
        mock_repo.update.return_value = None
        mock_session = _make_mock_session()

        app.dependency_overrides[get_deployment_profile_repository] = lambda: mock_repo
        app.dependency_overrides[get_db_session] = lambda: mock_session
        try:
            response = client.put(
                _url("test-project-001", "ghost-profile"),
                json={"description": "This does not exist"},
            )
        finally:
            app.dependency_overrides.pop(get_deployment_profile_repository, None)
            app.dependency_overrides.pop(get_db_session, None)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_profile_with_platform_change(self, app, client):
        """Updating the platform field is accepted and forwarded to repository."""
        from skillmeat.api.dependencies import get_deployment_profile_repository
        from skillmeat.cache.session import get_db_session

        updated_profile = _make_profile_orm(platform="cursor")
        mock_repo = MagicMock()
        mock_repo.update.return_value = updated_profile
        mock_session = _make_mock_session()

        app.dependency_overrides[get_deployment_profile_repository] = lambda: mock_repo
        app.dependency_overrides[get_db_session] = lambda: mock_session
        try:
            response = client.put(
                _url("test-project-001", "default"),
                json={"platform": "cursor"},
            )
        finally:
            app.dependency_overrides.pop(get_deployment_profile_repository, None)
            app.dependency_overrides.pop(get_db_session, None)

        assert response.status_code == status.HTTP_200_OK
        # Verify platform was forwarded to update call
        call_kwargs = mock_repo.update.call_args[1]
        assert call_kwargs.get("platform") == "cursor"

    def test_update_profile_invalid_platform_returns_422(self, client):
        """Providing an invalid platform enum value returns 422."""
        response = client.put(
            _url("test-project-001", "default"),
            json={"platform": "not_a_valid_platform"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# DELETE /api/v1/projects/{project_id}/profiles/{profile_id} — delete_profile
# ---------------------------------------------------------------------------


class TestDeleteProfile:
    """Tests for DELETE /api/v1/projects/{project_id}/profiles/{profile_id}."""

    def test_delete_profile_success(self, app, client):
        """Deleting an existing profile returns 204 with no content."""
        from skillmeat.api.dependencies import get_deployment_profile_repository
        from skillmeat.cache.session import get_db_session

        mock_repo = MagicMock()
        mock_repo.delete.return_value = True
        mock_session = _make_mock_session()

        app.dependency_overrides[get_deployment_profile_repository] = lambda: mock_repo
        app.dependency_overrides[get_db_session] = lambda: mock_session
        try:
            response = client.delete(_url("test-project-001", "default"))
        finally:
            app.dependency_overrides.pop(get_deployment_profile_repository, None)
            app.dependency_overrides.pop(get_db_session, None)

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_profile_not_found(self, app, client):
        """Deleting a non-existent profile returns 404."""
        from skillmeat.api.dependencies import get_deployment_profile_repository
        from skillmeat.cache.session import get_db_session

        mock_repo = MagicMock()
        mock_repo.delete.return_value = False
        mock_session = _make_mock_session()

        app.dependency_overrides[get_deployment_profile_repository] = lambda: mock_repo
        app.dependency_overrides[get_db_session] = lambda: mock_session
        try:
            response = client.delete(_url("test-project-001", "ghost-profile"))
        finally:
            app.dependency_overrides.pop(get_deployment_profile_repository, None)
            app.dependency_overrides.pop(get_db_session, None)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "ghost-profile" in response.json()["detail"]
