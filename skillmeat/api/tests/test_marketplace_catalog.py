"""Integration tests for Marketplace Catalog API endpoints.

Tests for:
- GET /api/v1/marketplace/catalog/search - Cross-source artifact search
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings
from skillmeat.api.server import create_app
from skillmeat.cache.models import MarketplaceCatalogEntry, MarketplaceSource
from skillmeat.cache.repositories import MarketplaceCatalogRepository, PaginatedResult


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

    app = create_app(api_settings)
    app_state.initialize(api_settings)

    client = TestClient(app)

    yield client

    app_state.shutdown()


@pytest.fixture
def mock_source():
    """Create a mock MarketplaceSource."""
    source = MagicMock(spec=MarketplaceSource)
    source.id = "src_test_123"
    source.owner = "anthropics"
    source.repo_name = "quickstarts"
    source.repo_url = "https://github.com/anthropics/quickstarts"
    source.ref = "main"
    return source


@pytest.fixture
def mock_catalog_entries(mock_source):
    """Create mock catalog entries with source relationship."""
    entries = []
    for i in range(3):
        entry = MagicMock(spec=MarketplaceCatalogEntry)
        entry.id = f"cat_{uuid.uuid4().hex[:8]}"
        entry.name = f"test-skill-{i}"
        entry.artifact_type = "skill"
        entry.title = f"Test Skill {i}"
        entry.description = f"A test skill number {i}"
        entry.confidence_score = 95 - (i * 5)
        entry.source_id = mock_source.id
        entry.source = mock_source
        entry.path = f"skills/test-skill-{i}"
        entry.upstream_url = (
            f"https://github.com/anthropics/quickstarts/tree/main/skills/test-skill-{i}"
        )
        entry.status = "new"
        entry.search_tags = '["testing", "automation"]'
        entries.append(entry)
    return entries


class TestCatalogSearch:
    """Tests for GET /api/v1/marketplace/catalog/search endpoint."""

    def test_search_catalog_empty(self, client):
        """Test search with no results."""
        with patch.object(
            MarketplaceCatalogRepository,
            "search",
            return_value=PaginatedResult(items=[], next_cursor=None, has_more=False),
        ):
            response = client.get("/api/v1/marketplace/catalog/search")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["next_cursor"] is None
        assert data["has_more"] is False

    def test_search_catalog_with_results(self, client, mock_catalog_entries):
        """Test search returns properly formatted results."""
        with patch.object(
            MarketplaceCatalogRepository,
            "search",
            return_value=PaginatedResult(
                items=mock_catalog_entries, next_cursor=None, has_more=False
            ),
        ):
            response = client.get("/api/v1/marketplace/catalog/search")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3

        # Verify first item structure
        item = data["items"][0]
        assert "id" in item
        assert item["name"] == "test-skill-0"
        assert item["artifact_type"] == "skill"
        assert item["title"] == "Test Skill 0"
        assert item["confidence_score"] == 95
        assert item["source_owner"] == "anthropics"
        assert item["source_repo"] == "quickstarts"
        assert item["path"] == "skills/test-skill-0"
        assert item["status"] == "new"
        assert item["search_tags"] == ["testing", "automation"]

    def test_search_catalog_with_query(self, client, mock_catalog_entries):
        """Test search with query parameter."""
        with patch.object(MarketplaceCatalogRepository, "search") as mock_search:
            mock_search.return_value = PaginatedResult(
                items=mock_catalog_entries[:1], next_cursor=None, has_more=False
            )

            response = client.get("/api/v1/marketplace/catalog/search?q=canvas")

        assert response.status_code == 200
        mock_search.assert_called_once()
        call_kwargs = mock_search.call_args.kwargs
        assert call_kwargs["query"] == "canvas"

    def test_search_catalog_with_type_filter(self, client, mock_catalog_entries):
        """Test search with type filter."""
        with patch.object(MarketplaceCatalogRepository, "search") as mock_search:
            mock_search.return_value = PaginatedResult(
                items=mock_catalog_entries, next_cursor=None, has_more=False
            )

            response = client.get("/api/v1/marketplace/catalog/search?type=skill")

        assert response.status_code == 200
        call_kwargs = mock_search.call_args.kwargs
        assert call_kwargs["artifact_type"] == "skill"

    def test_search_catalog_with_source_filter(self, client, mock_catalog_entries):
        """Test search with source_id filter."""
        with patch.object(MarketplaceCatalogRepository, "search") as mock_search:
            mock_search.return_value = PaginatedResult(
                items=mock_catalog_entries, next_cursor=None, has_more=False
            )

            response = client.get(
                "/api/v1/marketplace/catalog/search?source_id=src_test_123"
            )

        assert response.status_code == 200
        call_kwargs = mock_search.call_args.kwargs
        assert call_kwargs["source_ids"] == ["src_test_123"]

    def test_search_catalog_with_min_confidence(self, client, mock_catalog_entries):
        """Test search with min_confidence filter."""
        with patch.object(MarketplaceCatalogRepository, "search") as mock_search:
            mock_search.return_value = PaginatedResult(
                items=mock_catalog_entries[:1], next_cursor=None, has_more=False
            )

            response = client.get(
                "/api/v1/marketplace/catalog/search?min_confidence=90"
            )

        assert response.status_code == 200
        call_kwargs = mock_search.call_args.kwargs
        assert call_kwargs["min_confidence"] == 90

    def test_search_catalog_with_tags(self, client, mock_catalog_entries):
        """Test search with tags filter."""
        with patch.object(MarketplaceCatalogRepository, "search") as mock_search:
            mock_search.return_value = PaginatedResult(
                items=mock_catalog_entries, next_cursor=None, has_more=False
            )

            response = client.get(
                "/api/v1/marketplace/catalog/search?tags=testing,automation"
            )

        assert response.status_code == 200
        call_kwargs = mock_search.call_args.kwargs
        assert call_kwargs["tags"] == ["testing", "automation"]

    def test_search_catalog_pagination(self, client, mock_catalog_entries):
        """Test search with pagination parameters."""
        with patch.object(MarketplaceCatalogRepository, "search") as mock_search:
            mock_search.return_value = PaginatedResult(
                items=mock_catalog_entries,
                next_cursor="90:cat_xyz789",
                has_more=True,
            )

            response = client.get(
                "/api/v1/marketplace/catalog/search?limit=10&cursor=95:cat_abc123"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["next_cursor"] == "90:cat_xyz789"
        assert data["has_more"] is True

        call_kwargs = mock_search.call_args.kwargs
        assert call_kwargs["limit"] == 10
        assert call_kwargs["cursor"] == "95:cat_abc123"

    def test_search_catalog_combined_filters(self, client, mock_catalog_entries):
        """Test search with multiple filters combined."""
        with patch.object(MarketplaceCatalogRepository, "search") as mock_search:
            mock_search.return_value = PaginatedResult(
                items=mock_catalog_entries[:1], next_cursor=None, has_more=False
            )

            response = client.get(
                "/api/v1/marketplace/catalog/search"
                "?q=canvas"
                "&type=skill"
                "&source_id=src_test"
                "&min_confidence=80"
                "&tags=design,ui"
                "&limit=20"
            )

        assert response.status_code == 200
        call_kwargs = mock_search.call_args.kwargs
        assert call_kwargs["query"] == "canvas"
        assert call_kwargs["artifact_type"] == "skill"
        assert call_kwargs["source_ids"] == ["src_test"]
        assert call_kwargs["min_confidence"] == 80
        assert call_kwargs["tags"] == ["design", "ui"]
        assert call_kwargs["limit"] == 20

    def test_search_catalog_limit_validation(self, client):
        """Test that limit parameter is validated."""
        # Test limit too high
        response = client.get("/api/v1/marketplace/catalog/search?limit=500")
        assert response.status_code == 422  # Validation error

        # Test limit too low
        response = client.get("/api/v1/marketplace/catalog/search?limit=0")
        assert response.status_code == 422

    def test_search_catalog_min_confidence_validation(self, client):
        """Test that min_confidence parameter is validated."""
        # Test min_confidence too high
        response = client.get("/api/v1/marketplace/catalog/search?min_confidence=150")
        assert response.status_code == 422

        # Test min_confidence negative
        response = client.get("/api/v1/marketplace/catalog/search?min_confidence=-10")
        assert response.status_code == 422

    def test_search_catalog_handles_null_source(self, client):
        """Test search handles entries with missing source gracefully."""
        entry = MagicMock(spec=MarketplaceCatalogEntry)
        entry.id = "cat_test"
        entry.name = "orphan-skill"
        entry.artifact_type = "skill"
        entry.title = None
        entry.description = None
        entry.confidence_score = 50
        entry.source_id = "src_deleted"
        entry.source = None  # Source was deleted
        entry.path = "skills/orphan"
        entry.upstream_url = None
        entry.status = "new"
        entry.search_tags = None

        with patch.object(
            MarketplaceCatalogRepository,
            "search",
            return_value=PaginatedResult(
                items=[entry], next_cursor=None, has_more=False
            ),
        ):
            response = client.get("/api/v1/marketplace/catalog/search")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        item = data["items"][0]
        assert item["source_owner"] == ""
        assert item["source_repo"] == ""
        assert item["search_tags"] is None

    def test_search_catalog_error_handling(self, client):
        """Test search handles database errors gracefully."""
        with patch.object(
            MarketplaceCatalogRepository,
            "search",
            side_effect=Exception("Database connection failed"),
        ):
            response = client.get("/api/v1/marketplace/catalog/search")

        assert response.status_code == 500
        assert "Search operation failed" in response.json()["detail"]

    def test_search_catalog_returns_snippets_from_fts5(
        self, client, mock_catalog_entries
    ):
        """Test search returns snippets when FTS5 search returns them."""
        # Create snippets mapping for FTS5 results
        snippets = {
            mock_catalog_entries[0].id: {
                "title_snippet": "<mark>Test</mark> Skill 0",
                "description_snippet": "A <mark>test</mark> skill number 0",
            },
            mock_catalog_entries[1].id: {
                "title_snippet": "<mark>Test</mark> Skill 1",
                "description_snippet": "A <mark>test</mark> skill number 1",
            },
            mock_catalog_entries[2].id: {
                "title_snippet": "<mark>Test</mark> Skill 2",
                "description_snippet": "A <mark>test</mark> skill number 2",
            },
        }

        with patch.object(
            MarketplaceCatalogRepository,
            "search",
            return_value=PaginatedResult(
                items=mock_catalog_entries,
                next_cursor=None,
                has_more=False,
                snippets=snippets,
            ),
        ):
            response = client.get("/api/v1/marketplace/catalog/search?q=test")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3

        # Verify snippets are included in response
        item = data["items"][0]
        assert item["title_snippet"] == "<mark>Test</mark> Skill 0"
        assert item["description_snippet"] == "A <mark>test</mark> skill number 0"

    def test_search_catalog_snippets_null_for_like_search(
        self, client, mock_catalog_entries
    ):
        """Test search returns null snippets when using LIKE search (no FTS5)."""
        with patch.object(
            MarketplaceCatalogRepository,
            "search",
            return_value=PaginatedResult(
                items=mock_catalog_entries,
                next_cursor=None,
                has_more=False,
                snippets=None,  # LIKE search returns no snippets
            ),
        ):
            response = client.get("/api/v1/marketplace/catalog/search?q=test")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3

        # Verify snippets are null when LIKE search is used
        for item in data["items"]:
            assert item["title_snippet"] is None
            assert item["description_snippet"] is None
