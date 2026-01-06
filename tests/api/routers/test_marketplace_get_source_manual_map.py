"""Tests for GET /marketplace/sources/{source_id} manual_map field.

This module verifies that the GET endpoint correctly returns manual_map from the database,
including:
- Returning manual_map when configured
- Returning None when not configured
- Proper JSON deserialization from database
- Response schema validation
"""

import json
from datetime import datetime
from typing import Dict, Optional
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app
from skillmeat.cache.models import MarketplaceSource


@pytest.fixture
def test_settings():
    """Create test settings with API key disabled."""
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


def create_mock_source(manual_map: Optional[Dict[str, str]] = None) -> MarketplaceSource:
    """Create a mock MarketplaceSource with optional manual_map.

    Args:
        manual_map: Optional manual directory-to-type mappings (will be JSON-serialized)

    Returns:
        MarketplaceSource instance with manual_map stored as JSON string
    """
    # Convert dict to JSON string to match database storage format
    manual_map_json = json.dumps(manual_map) if manual_map is not None else None

    return MarketplaceSource(
        id="src_test_manual_map",
        repo_url="https://github.com/test/repo",
        owner="test",
        repo_name="repo",
        ref="main",
        root_hint=None,
        trust_level="unverified",
        visibility="public",
        scan_status="pending",
        artifact_count=0,
        last_sync_at=None,
        created_at=datetime(2025, 12, 13, 10, 0, 0),
        updated_at=datetime(2025, 12, 13, 10, 0, 0),
        enable_frontmatter_detection=False,
        manual_map=manual_map_json,
    )


class TestGetSourceManualMap:
    """Test GET /marketplace/sources/{source_id} manual_map field."""

    def test_get_source_with_manual_map(self, client):
        """GET should return manual_map when source has mapping configured."""
        # Arrange: Create source with manual_map
        manual_map = {
            "skills/python": "skill",
            "commands/dev": "command",
            "agents/helper": "agent",
        }
        mock_source = create_mock_source(manual_map=manual_map)

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = mock_source

        # Act: GET source
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_repo,
        ):
            response = client.get("/api/v1/marketplace/sources/src_test_manual_map")

        # Assert: manual_map in response matches database value
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "manual_map" in data
        assert data["manual_map"] is not None
        assert isinstance(data["manual_map"], dict)
        assert data["manual_map"] == manual_map
        assert data["manual_map"]["skills/python"] == "skill"
        assert data["manual_map"]["commands/dev"] == "command"
        assert data["manual_map"]["agents/helper"] == "agent"

    def test_get_source_without_manual_map(self, client):
        """GET should return None for manual_map when not configured."""
        # Arrange: Create source without manual_map (None)
        mock_source = create_mock_source(manual_map=None)

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = mock_source

        # Act: GET source
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_repo,
        ):
            response = client.get("/api/v1/marketplace/sources/src_test_manual_map")

        # Assert: manual_map is None
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "manual_map" in data
        assert data["manual_map"] is None

    def test_get_source_with_empty_manual_map(self, client):
        """GET should return empty dict when manual_map is empty."""
        # Arrange: Create source with empty manual_map
        mock_source = create_mock_source(manual_map={})

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = mock_source

        # Act: GET source
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_repo,
        ):
            response = client.get("/api/v1/marketplace/sources/src_test_manual_map")

        # Assert: manual_map is empty dict, not None
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "manual_map" in data
        assert data["manual_map"] is not None
        assert isinstance(data["manual_map"], dict)
        assert len(data["manual_map"]) == 0

    def test_get_source_manual_map_deserialization(self, client):
        """manual_map should be properly deserialized from JSON as Dict, not string."""
        # Arrange: Create source with complex manual_map
        complex_map = {
            "deep/nested/path/skills": "skill",
            "commands/build": "command",
            "path/with-special_chars": "agent",
            "single": "skill",
        }
        mock_source = create_mock_source(manual_map=complex_map)

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = mock_source

        # Act: GET source
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_repo,
        ):
            response = client.get("/api/v1/marketplace/sources/src_test_manual_map")

        # Assert: Dict structure is correct, not JSON string
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "manual_map" in data
        assert isinstance(data["manual_map"], dict), "manual_map should be dict, not string"
        assert data["manual_map"] == complex_map

        # Verify all keys and values are preserved
        assert data["manual_map"]["deep/nested/path/skills"] == "skill"
        assert data["manual_map"]["commands/build"] == "command"
        assert data["manual_map"]["path/with-special_chars"] == "agent"
        assert data["manual_map"]["single"] == "skill"
        assert len(data["manual_map"]) == 4

    def test_get_source_manual_map_with_special_characters(self, client):
        """manual_map should handle paths with special characters correctly."""
        # Arrange: Create source with special character paths
        special_map = {
            "path/with spaces": "skill",
            "path/with-dashes": "command",
            "path/with_underscores": "agent",
            "path/with.dots": "skill",
            "path/@special/chars": "command",
        }
        mock_source = create_mock_source(manual_map=special_map)

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = mock_source

        # Act: GET source
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_repo,
        ):
            response = client.get("/api/v1/marketplace/sources/src_test_manual_map")

        # Assert: Special characters are preserved
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["manual_map"] == special_map
        assert "path/with spaces" in data["manual_map"]
        assert "path/@special/chars" in data["manual_map"]

    def test_get_source_manual_map_type_validation(self, client):
        """Response schema should validate manual_map as Optional[Dict[str, str]]."""
        # Arrange: Create source with valid manual_map
        valid_map = {"path/one": "skill", "path/two": "command"}
        mock_source = create_mock_source(manual_map=valid_map)

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = mock_source

        # Act: GET source
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_repo,
        ):
            response = client.get("/api/v1/marketplace/sources/src_test_manual_map")

        # Assert: Schema validation passes
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify type constraints
        assert isinstance(data["manual_map"], dict)
        for key, value in data["manual_map"].items():
            assert isinstance(key, str), f"Key {key} should be string"
            assert isinstance(value, str), f"Value {value} should be string"

    def test_get_source_response_includes_all_fields(self, client):
        """GET should return all fields including manual_map alongside other metadata."""
        # Arrange: Create source with manual_map and other fields
        manual_map = {"skills": "skill"}
        mock_source = create_mock_source(manual_map=manual_map)

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = mock_source

        # Act: GET source
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_repo,
        ):
            response = client.get("/api/v1/marketplace/sources/src_test_manual_map")

        # Assert: All expected fields present
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify manual_map is included
        assert "manual_map" in data
        assert data["manual_map"] == manual_map

        # Verify other standard fields are present
        assert "id" in data
        assert "repo_url" in data
        assert "owner" in data
        assert "repo_name" in data
        assert "ref" in data
        assert "trust_level" in data
        assert "scan_status" in data
        assert "enable_frontmatter_detection" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_get_source_not_found_with_manual_map_query(self, client):
        """GET should still return 404 when source not found, regardless of manual_map."""
        # Arrange: Mock repository returns None (source not found)
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = None

        # Act: GET non-existent source
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_repo,
        ):
            response = client.get("/api/v1/marketplace/sources/nonexistent")

        # Assert: 404 error
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]


class TestGetSourceManualMapEdgeCases:
    """Test edge cases for manual_map in GET response."""

    def test_manual_map_with_single_entry(self, client):
        """manual_map should handle single entry correctly."""
        single_map = {"skills": "skill"}
        mock_source = create_mock_source(manual_map=single_map)

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = mock_source

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_repo,
        ):
            response = client.get("/api/v1/marketplace/sources/src_test_manual_map")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["manual_map"] == single_map
        assert len(data["manual_map"]) == 1

    def test_manual_map_with_many_entries(self, client):
        """manual_map should handle many entries correctly."""
        large_map = {f"path/{i}": "skill" if i % 2 == 0 else "command" for i in range(100)}
        mock_source = create_mock_source(manual_map=large_map)

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = mock_source

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_repo,
        ):
            response = client.get("/api/v1/marketplace/sources/src_test_manual_map")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["manual_map"] == large_map
        assert len(data["manual_map"]) == 100

    def test_manual_map_with_long_paths(self, client):
        """manual_map should handle very long directory paths."""
        long_path_map = {
            "very/deeply/nested/directory/structure/with/many/levels/skills": "skill",
            "a" * 200: "command",  # 200 character path
        }
        mock_source = create_mock_source(manual_map=long_path_map)

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = mock_source

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_repo,
        ):
            response = client.get("/api/v1/marketplace/sources/src_test_manual_map")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["manual_map"] == long_path_map

    def test_manual_map_preserves_order(self, client):
        """manual_map should preserve insertion order (Python 3.7+)."""
        ordered_map = {
            "z_last": "skill",
            "a_first": "command",
            "m_middle": "agent",
        }
        mock_source = create_mock_source(manual_map=ordered_map)

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = mock_source

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_repo,
        ):
            response = client.get("/api/v1/marketplace/sources/src_test_manual_map")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify order is preserved (dict insertion order)
        keys = list(data["manual_map"].keys())
        assert keys == ["z_last", "a_first", "m_middle"]
