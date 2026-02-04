"""Integration tests for Tags API endpoints.

This module tests the /api/v1/tags endpoints, including:
- Create tag (POST /tags)
- Get tag by ID (GET /tags/{tag_id})
- Get tag by slug (GET /tags/slug/{slug})
- Update tag (PUT /tags/{tag_id})
- Delete tag (DELETE /tags/{tag_id})
- List tags with pagination (GET /tags)
- Search tags (GET /tags/search)
"""

import pytest
from datetime import datetime
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, Mock

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app


# =============================================================================
# Fixtures
# =============================================================================


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
def mock_tag():
    """Create a mock tag response."""
    return {
        "id": "tag-123",
        "name": "Python",
        "slug": "python",
        "color": "#3776AB",
        "created_at": "2025-01-01T00:00:00",
        "updated_at": "2025-01-01T00:00:00",
        "artifact_count": 5,
    }


@pytest.fixture(autouse=True)
def mock_collection_manager(app):
    """Override CollectionManagerDep for all tests."""
    from skillmeat.api.dependencies import get_collection_manager

    mock_mgr = MagicMock()
    app.dependency_overrides[get_collection_manager] = lambda: mock_mgr
    yield mock_mgr
    app.dependency_overrides.pop(get_collection_manager, None)


@pytest.fixture(autouse=True)
def mock_tag_write_service():
    """Mock TagWriteService for all tests."""
    with patch(
        "skillmeat.core.services.tag_write_service.TagWriteService"
    ) as MockWriteService:
        mock_ws = MockWriteService.return_value
        mock_ws.rename_tag.return_value = {
            "affected_artifacts": [],
            "files_updated": 0,
        }
        mock_ws.delete_tag.return_value = {
            "affected_artifacts": [],
            "files_updated": 0,
        }
        mock_ws.update_tags_json_cache.return_value = 0
        yield mock_ws


@pytest.fixture
def mock_tag_service(mock_tag):
    """Create mock TagService."""
    with patch("skillmeat.core.services.TagService") as MockService:
        mock_service = MockService.return_value

        # Create a proper Mock that will work with Pydantic validation
        # The router accesses .id, .name, etc. properties directly
        tag_mock = Mock()
        tag_mock.id = mock_tag["id"]
        tag_mock.name = mock_tag["name"]
        tag_mock.slug = mock_tag["slug"]
        tag_mock.color = mock_tag["color"]
        tag_mock.created_at = datetime.fromisoformat(mock_tag["created_at"])
        tag_mock.updated_at = datetime.fromisoformat(mock_tag["updated_at"])
        tag_mock.artifact_count = mock_tag["artifact_count"]

        # Set up mock methods - note router calls get_tag_by_id, not get_tag
        mock_service.create_tag.return_value = tag_mock
        mock_service.get_tag_by_id.return_value = tag_mock  # Router uses this
        mock_service.get_tag.return_value = tag_mock  # For completeness
        mock_service.get_tag_by_slug.return_value = tag_mock
        mock_service.update_tag.return_value = tag_mock
        mock_service.delete_tag.return_value = True
        mock_service.get_tag_artifact_count.return_value = 5

        # Mock list_tags to return list of tag mocks (router expects this format)
        mock_service.list_tags.return_value = [tag_mock]

        # Mock search response
        mock_service.search_tags.return_value = [tag_mock]

        yield mock_service


# =============================================================================
# Test: Create Tag
# =============================================================================


class TestCreateTag:
    """Tests for POST /tags endpoint."""

    def test_create_tag_success(self, client, mock_tag_service):
        """Test creating a tag successfully."""
        response = client.post(
            "/api/v1/tags",
            json={
                "name": "Python",
                "slug": "python",
                "color": "#3776AB",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Python"
        assert data["slug"] == "python"
        assert data["color"] == "#3776AB"
        assert "id" in data
        assert "created_at" in data

    def test_create_tag_without_color(self, client, mock_tag_service):
        """Test creating tag without color (optional field)."""
        response = client.post(
            "/api/v1/tags",
            json={
                "name": "JavaScript",
                "slug": "javascript",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_create_tag_duplicate_name(self, client, mock_tag_service):
        """Test creating tag with duplicate name returns 409."""
        mock_tag_service.create_tag.side_effect = ValueError(
            "Tag with name 'Python' already exists"
        )

        response = client.post(
            "/api/v1/tags",
            json={
                "name": "Python",
                "slug": "python-2",
            },
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in response.json()["detail"]

    def test_create_tag_duplicate_slug(self, client, mock_tag_service):
        """Test creating tag with duplicate slug returns 409."""
        mock_tag_service.create_tag.side_effect = ValueError(
            "Tag with slug 'python' already exists"
        )

        response = client.post(
            "/api/v1/tags",
            json={
                "name": "Python 2",
                "slug": "python",
            },
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_create_tag_invalid_request(self, client):
        """Test creating tag with missing required fields returns 422."""
        response = client.post(
            "/api/v1/tags",
            json={
                "name": "Python",
                # Missing 'slug'
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_tag_service_error(self, client, mock_tag_service):
        """Test creating tag with service error returns 500."""
        mock_tag_service.create_tag.side_effect = Exception("Database error")

        response = client.post(
            "/api/v1/tags",
            json={
                "name": "Python",
                "slug": "python",
            },
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# =============================================================================
# Test: Get Tag
# =============================================================================


class TestGetTag:
    """Tests for GET /tags/{tag_id} endpoint."""

    def test_get_tag_success(self, client, mock_tag_service):
        """Test getting tag by ID successfully."""
        response = client.get("/api/v1/tags/tag-123")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "tag-123"
        assert data["name"] == "Python"
        assert data["artifact_count"] == 5

    def test_get_tag_not_found(self, client, mock_tag_service):
        """Test getting non-existent tag returns 404."""
        mock_tag_service.get_tag.return_value = None

        response = client.get("/api/v1/tags/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestGetTagBySlug:
    """Tests for GET /tags/slug/{slug} endpoint."""

    def test_get_tag_by_slug_success(self, client, mock_tag_service):
        """Test getting tag by slug successfully."""
        response = client.get("/api/v1/tags/slug/python")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["slug"] == "python"
        assert data["name"] == "Python"

    def test_get_tag_by_slug_not_found(self, client, mock_tag_service):
        """Test getting tag by non-existent slug returns 404."""
        mock_tag_service.get_tag_by_slug.return_value = None

        response = client.get("/api/v1/tags/slug/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Test: Update Tag
# =============================================================================


class TestUpdateTag:
    """Tests for PUT /tags/{tag_id} endpoint."""

    def test_update_tag_success(self, client, mock_tag_service):
        """Test updating tag successfully."""
        response = client.put(
            "/api/v1/tags/tag-123",
            json={
                "color": "#FF0000",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "tag-123"

    def test_update_tag_name(self, client, mock_tag_service):
        """Test updating tag name."""
        response = client.put(
            "/api/v1/tags/tag-123",
            json={
                "name": "Python 3",
            },
        )

        assert response.status_code == status.HTTP_200_OK

    def test_update_tag_not_found(self, client, mock_tag_service):
        """Test updating non-existent tag returns 404."""
        mock_tag_service.update_tag.return_value = None

        response = client.put(
            "/api/v1/tags/nonexistent",
            json={
                "color": "#FF0000",
            },
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_tag_duplicate_name(self, client, mock_tag_service):
        """Test updating tag to duplicate name returns 409."""
        mock_tag_service.update_tag.side_effect = ValueError(
            "Tag with name 'JavaScript' already exists"
        )

        response = client.put(
            "/api/v1/tags/tag-123",
            json={
                "name": "JavaScript",
            },
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_update_tag_empty_request(self, client, mock_tag_service):
        """Test updating tag with empty request (no fields to update)."""
        response = client.put("/api/v1/tags/tag-123", json={})

        # Should still succeed (no-op update)
        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# Test: Delete Tag
# =============================================================================


class TestDeleteTag:
    """Tests for DELETE /tags/{tag_id} endpoint."""

    def test_delete_tag_success(self, client, mock_tag_service):
        """Test deleting tag successfully."""
        response = client.delete("/api/v1/tags/tag-123")

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_tag_not_found(self, client, mock_tag_service):
        """Test deleting non-existent tag returns 404."""
        mock_tag_service.get_tag.return_value = None

        response = client.delete("/api/v1/tags/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Test: List Tags
# =============================================================================


class TestListTags:
    """Tests for GET /tags endpoint."""

    def test_list_tags_success(self, client, mock_tag_service):
        """Test listing tags successfully."""
        response = client.get("/api/v1/tags")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "page_info" in data
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Python"

    def test_list_tags_with_limit(self, client, mock_tag_service):
        """Test listing tags with limit parameter."""
        response = client.get("/api/v1/tags?limit=10")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data

    def test_list_tags_with_cursor(self, client, mock_tag_service):
        """Test listing tags with pagination cursor."""
        import base64

        cursor = base64.b64encode(b"tag-123").decode()
        response = client.get(f"/api/v1/tags?after={cursor}")

        assert response.status_code == status.HTTP_200_OK

    def test_list_tags_invalid_cursor(self, client, mock_tag_service):
        """Test listing tags with invalid cursor returns 400."""
        response = client.get("/api/v1/tags?after=invalid-cursor")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_tags_invalid_limit(self, client, mock_tag_service):
        """Test listing tags with invalid limit returns 422."""
        response = client.get("/api/v1/tags?limit=0")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_list_tags_empty(self, client, mock_tag_service):
        """Test listing tags when no tags exist."""
        from skillmeat.api.schemas.tags import TagListResponse
        from skillmeat.api.schemas.common import PageInfo

        mock_tag_service.list_tags.return_value = TagListResponse(
            items=[],
            page_info=PageInfo(
                has_next_page=False,
                has_previous_page=False,
                start_cursor=None,
                end_cursor=None,
                total_count=None,
            ),
        )

        response = client.get("/api/v1/tags")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 0


# =============================================================================
# Test: Search Tags
# =============================================================================


class TestSearchTags:
    """Tests for GET /tags/search endpoint."""

    def test_search_tags_success(self, client, mock_tag_service):
        """Test searching tags successfully."""
        response = client.get("/api/v1/tags/search?q=python")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "Python"

    def test_search_tags_missing_query(self, client):
        """Test searching tags without query parameter returns 422."""
        response = client.get("/api/v1/tags/search")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_search_tags_empty_query(self, client, mock_tag_service):
        """Test searching tags with empty query."""
        mock_tag_service.search_tags.return_value = []

        response = client.get("/api/v1/tags/search?q=")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 0

    def test_search_tags_with_limit(self, client, mock_tag_service):
        """Test searching tags with limit parameter."""
        response = client.get("/api/v1/tags/search?q=py&limit=5")

        assert response.status_code == status.HTTP_200_OK

    def test_search_tags_no_results(self, client, mock_tag_service):
        """Test searching tags with no results."""
        mock_tag_service.search_tags.return_value = []

        response = client.get("/api/v1/tags/search?q=nonexistent")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 0


# =============================================================================
# Test: Cursor Encoding/Decoding
# =============================================================================


class TestCursorUtils:
    """Tests for cursor encoding/decoding utilities."""

    def test_encode_cursor(self):
        """Test encoding cursor to base64."""
        from skillmeat.api.routers.tags import encode_cursor

        cursor = encode_cursor("tag-123")
        assert cursor == "dGFnLTEyMw=="

    def test_decode_cursor(self):
        """Test decoding cursor from base64."""
        from skillmeat.api.routers.tags import decode_cursor

        cursor = decode_cursor("dGFnLTEyMw==")
        assert cursor == "tag-123"

    def test_decode_invalid_cursor(self):
        """Test decoding invalid cursor raises HTTPException."""
        from skillmeat.api.routers.tags import decode_cursor
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as excinfo:
            decode_cursor("invalid-cursor!!!")

        assert excinfo.value.status_code == status.HTTP_400_BAD_REQUEST
