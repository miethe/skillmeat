"""Unit tests for marketplace path tags API endpoints.

Tests the GET and PATCH path tags API endpoints:
- GET /marketplace/sources/{source_id}/catalog/{entry_id}/path-tags
- PATCH /marketplace/sources/{source_id}/catalog/{entry_id}/path-tags

These endpoints manage the approval workflow for path-based tag suggestions
extracted from artifact paths in the marketplace catalog.

Test Coverage:
- 23 test cases covering all major code paths
- GET endpoint: success, source not found, entry not found, no path_segments,
  malformed JSON, missing extracted key
- PATCH endpoint: approve success, reject success, segment not found,
  already approved/rejected, excluded segment, source/entry not found,
  no path_segments, malformed JSON
- Schema validation: valid/invalid statuses, empty segment, response construction

Note: Coverage metrics show ~24% of marketplace_sources.py because this file
contains many other endpoints. These tests achieve comprehensive coverage of
the path tags endpoints (lines 1695-2007).
"""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.schemas.marketplace import (
    ExtractedSegmentResponse,
    PathSegmentsResponse,
    UpdateSegmentStatusRequest,
    UpdateSegmentStatusResponse,
)
from skillmeat.api.server import create_app
from skillmeat.cache.models import MarketplaceCatalogEntry, MarketplaceSource


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


@pytest.fixture
def sample_path_segments():
    """Sample path_segments JSON for testing."""
    return json.dumps(
        {
            "raw_path": "categories/05-data-ai/ai-engineer.md",
            "extracted": [
                {
                    "segment": "categories",
                    "normalized": "categories",
                    "status": "pending",
                    "reason": None,
                },
                {
                    "segment": "05-data-ai",
                    "normalized": "data-ai",
                    "status": "pending",
                    "reason": None,
                },
            ],
            "extracted_at": "2024-01-01T00:00:00",
        }
    )


@pytest.fixture
def sample_path_segments_with_excluded():
    """Sample path_segments JSON with excluded segment."""
    return json.dumps(
        {
            "raw_path": "src/lib/utils.ts",
            "extracted": [
                {
                    "segment": "src",
                    "normalized": "src",
                    "status": "excluded",
                    "reason": "matches exclude_patterns",
                },
                {
                    "segment": "lib",
                    "normalized": "lib",
                    "status": "pending",
                    "reason": None,
                },
            ],
            "extracted_at": "2024-01-01T00:00:00",
        }
    )


@pytest.fixture
def mock_source():
    """Create a mock MarketplaceSource."""
    return MarketplaceSource(
        id="src_test_123",
        repo_url="https://github.com/test/repo",
        owner="test",
        repo_name="repo",
        ref="main",
        root_hint="skills",
        trust_level="verified",
        visibility="public",
        scan_status="success",
        artifact_count=5,
        last_sync_at=datetime(2025, 12, 6, 10, 30, 0),
        created_at=datetime(2025, 12, 5, 9, 0, 0),
        updated_at=datetime(2025, 12, 6, 10, 30, 0),
    )


@pytest.fixture
def mock_catalog_entry(sample_path_segments):
    """Create a mock MarketplaceCatalogEntry with path_segments."""
    entry = MarketplaceCatalogEntry(
        id="cat_test_456",
        source_id="src_test_123",
        artifact_type="skill",
        name="ai-engineer",
        path="categories/05-data-ai/ai-engineer.md",
        upstream_url="https://github.com/test/repo/tree/main/categories/05-data-ai/ai-engineer.md",
        detected_version="1.0.0",
        detected_sha="abc123",
        detected_at=datetime(2025, 12, 6, 10, 30, 0),
        confidence_score=95,
        status="new",
        path_segments=sample_path_segments,
    )
    return entry


@pytest.fixture
def mock_catalog_entry_excluded(sample_path_segments_with_excluded):
    """Create a mock MarketplaceCatalogEntry with excluded segment."""
    entry = MarketplaceCatalogEntry(
        id="cat_test_789",
        source_id="src_test_123",
        artifact_type="skill",
        name="utils",
        path="src/lib/utils.ts",
        upstream_url="https://github.com/test/repo/tree/main/src/lib/utils.ts",
        detected_version="1.0.0",
        detected_sha="def456",
        detected_at=datetime(2025, 12, 6, 10, 30, 0),
        confidence_score=90,
        status="new",
        path_segments=sample_path_segments_with_excluded,
    )
    return entry


class TestGetPathTags:
    """Tests for GET path-tags endpoint."""

    def test_get_success(self, client, mock_source, mock_catalog_entry):
        """GET returns 200 with PathSegmentsResponse for valid entry."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as mock_source_repo_class, patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository"
        ) as mock_catalog_repo_class:
            # Mock source repo
            mock_source_repo = MagicMock()
            mock_source_repo.get_by_id.return_value = mock_source
            mock_source_repo_class.return_value = mock_source_repo

            # Mock catalog repo and session
            mock_catalog_repo = MagicMock()
            mock_session = MagicMock()
            mock_session.query.return_value.filter.return_value.first.return_value = (
                mock_catalog_entry
            )
            mock_catalog_repo._get_session.return_value = mock_session
            mock_catalog_repo_class.return_value = mock_catalog_repo

            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/catalog/cat_test_456/path-tags"
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # Validate response structure
            assert data["entry_id"] == "cat_test_456"
            assert (
                data["raw_path"] == "categories/05-data-ai/ai-engineer.md"
            )
            assert len(data["extracted"]) == 2
            assert data["extracted"][0]["segment"] == "categories"
            assert data["extracted"][0]["status"] == "pending"
            assert data["extracted"][1]["segment"] == "05-data-ai"
            assert data["extracted"][1]["normalized"] == "data-ai"

    def test_get_source_not_found(self, client):
        """GET returns 404 if source not found."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as mock_source_repo_class:
            # Mock source repo to return None
            mock_source_repo = MagicMock()
            mock_source_repo.get_by_id.return_value = None
            mock_source_repo_class.return_value = mock_source_repo

            response = client.get(
                "/api/v1/marketplace/sources/nonexistent/catalog/cat_test_456/path-tags"
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Source with ID 'nonexistent' not found" in response.json()["detail"]

    def test_get_entry_not_found(self, client, mock_source):
        """GET returns 404 if catalog entry not found."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as mock_source_repo_class, patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository"
        ) as mock_catalog_repo_class:
            # Mock source repo
            mock_source_repo = MagicMock()
            mock_source_repo.get_by_id.return_value = mock_source
            mock_source_repo_class.return_value = mock_source_repo

            # Mock catalog repo to return no entry
            mock_catalog_repo = MagicMock()
            mock_session = MagicMock()
            mock_session.query.return_value.filter.return_value.first.return_value = None
            mock_catalog_repo._get_session.return_value = mock_session
            mock_catalog_repo_class.return_value = mock_catalog_repo

            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/catalog/nonexistent/path-tags"
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "not found in source" in response.json()["detail"]

    def test_get_no_path_segments(self, client, mock_source, mock_catalog_entry):
        """GET returns 400 if entry has no path_segments."""
        # Clear path_segments
        mock_catalog_entry.path_segments = None

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as mock_source_repo_class, patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository"
        ) as mock_catalog_repo_class:
            # Mock source repo
            mock_source_repo = MagicMock()
            mock_source_repo.get_by_id.return_value = mock_source
            mock_source_repo_class.return_value = mock_source_repo

            # Mock catalog repo
            mock_catalog_repo = MagicMock()
            mock_session = MagicMock()
            mock_session.query.return_value.filter.return_value.first.return_value = (
                mock_catalog_entry
            )
            mock_catalog_repo._get_session.return_value = mock_session
            mock_catalog_repo_class.return_value = mock_catalog_repo

            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/catalog/cat_test_456/path-tags"
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "has no path_segments" in response.json()["detail"]

    def test_get_malformed_json(self, client, mock_source, mock_catalog_entry):
        """GET returns 500 if path_segments JSON is malformed."""
        # Set malformed JSON
        mock_catalog_entry.path_segments = "not valid json"

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as mock_source_repo_class, patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository"
        ) as mock_catalog_repo_class:
            # Mock source repo
            mock_source_repo = MagicMock()
            mock_source_repo.get_by_id.return_value = mock_source
            mock_source_repo_class.return_value = mock_source_repo

            # Mock catalog repo
            mock_catalog_repo = MagicMock()
            mock_session = MagicMock()
            mock_session.query.return_value.filter.return_value.first.return_value = (
                mock_catalog_entry
            )
            mock_catalog_repo._get_session.return_value = mock_session
            mock_catalog_repo_class.return_value = mock_catalog_repo

            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/catalog/cat_test_456/path-tags"
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "parsing path_segments" in response.json()["detail"]

    def test_get_missing_extracted_key(self, client, mock_source, mock_catalog_entry):
        """GET returns 500 if 'extracted' key is missing from JSON."""
        # Set JSON without 'extracted' key
        mock_catalog_entry.path_segments = json.dumps(
            {"raw_path": "/a/b.md", "extracted_at": "2024-01-01T00:00:00"}
        )

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as mock_source_repo_class, patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository"
        ) as mock_catalog_repo_class:
            # Mock source repo
            mock_source_repo = MagicMock()
            mock_source_repo.get_by_id.return_value = mock_source
            mock_source_repo_class.return_value = mock_source_repo

            # Mock catalog repo
            mock_catalog_repo = MagicMock()
            mock_session = MagicMock()
            mock_session.query.return_value.filter.return_value.first.return_value = (
                mock_catalog_entry
            )
            mock_catalog_repo._get_session.return_value = mock_session
            mock_catalog_repo_class.return_value = mock_catalog_repo

            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/catalog/cat_test_456/path-tags"
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "parsing path_segments" in response.json()["detail"]


class TestPatchPathTags:
    """Tests for PATCH path-tags endpoint."""

    def test_patch_approve_success(self, client, mock_source, mock_catalog_entry):
        """PATCH successfully updates status from pending to approved."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as mock_source_repo_class, patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository"
        ) as mock_catalog_repo_class:
            # Mock source repo
            mock_source_repo = MagicMock()
            mock_source_repo.get_by_id.return_value = mock_source
            mock_source_repo_class.return_value = mock_source_repo

            # Mock catalog repo and session
            mock_catalog_repo = MagicMock()
            mock_session = MagicMock()
            mock_session.query.return_value.filter.return_value.first.return_value = (
                mock_catalog_entry
            )
            mock_catalog_repo._get_session.return_value = mock_session
            mock_catalog_repo_class.return_value = mock_catalog_repo

            response = client.patch(
                "/api/v1/marketplace/sources/src_test_123/catalog/cat_test_456/path-tags",
                json={"segment": "categories", "status": "approved"},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # Verify the segment was updated
            categories_segment = next(
                s for s in data["extracted"] if s["segment"] == "categories"
            )
            assert categories_segment["status"] == "approved"

            # Verify commit was called
            mock_session.commit.assert_called_once()

    def test_patch_reject_success(self, client, mock_source, mock_catalog_entry):
        """PATCH successfully updates status from pending to rejected."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as mock_source_repo_class, patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository"
        ) as mock_catalog_repo_class:
            # Mock source repo
            mock_source_repo = MagicMock()
            mock_source_repo.get_by_id.return_value = mock_source
            mock_source_repo_class.return_value = mock_source_repo

            # Mock catalog repo and session
            mock_catalog_repo = MagicMock()
            mock_session = MagicMock()
            mock_session.query.return_value.filter.return_value.first.return_value = (
                mock_catalog_entry
            )
            mock_catalog_repo._get_session.return_value = mock_session
            mock_catalog_repo_class.return_value = mock_catalog_repo

            response = client.patch(
                "/api/v1/marketplace/sources/src_test_123/catalog/cat_test_456/path-tags",
                json={"segment": "05-data-ai", "status": "rejected"},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # Verify the segment was updated
            data_ai_segment = next(
                s for s in data["extracted"] if s["segment"] == "05-data-ai"
            )
            assert data_ai_segment["status"] == "rejected"

    def test_patch_segment_not_found(self, client, mock_source, mock_catalog_entry):
        """PATCH returns 404 if segment not found in entry."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as mock_source_repo_class, patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository"
        ) as mock_catalog_repo_class:
            # Mock source repo
            mock_source_repo = MagicMock()
            mock_source_repo.get_by_id.return_value = mock_source
            mock_source_repo_class.return_value = mock_source_repo

            # Mock catalog repo and session
            mock_catalog_repo = MagicMock()
            mock_session = MagicMock()
            mock_session.query.return_value.filter.return_value.first.return_value = (
                mock_catalog_entry
            )
            mock_catalog_repo._get_session.return_value = mock_session
            mock_catalog_repo_class.return_value = mock_catalog_repo

            response = client.patch(
                "/api/v1/marketplace/sources/src_test_123/catalog/cat_test_456/path-tags",
                json={"segment": "nonexistent", "status": "approved"},
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Segment 'nonexistent' not found" in response.json()["detail"]

            # Verify rollback was called
            mock_session.rollback.assert_called()

    def test_patch_already_approved(self, client, mock_source, mock_catalog_entry):
        """PATCH returns 409 if segment already approved."""
        # Pre-approve a segment
        segments_data = json.loads(mock_catalog_entry.path_segments)
        segments_data["extracted"][0]["status"] = "approved"
        mock_catalog_entry.path_segments = json.dumps(segments_data)

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as mock_source_repo_class, patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository"
        ) as mock_catalog_repo_class:
            # Mock source repo
            mock_source_repo = MagicMock()
            mock_source_repo.get_by_id.return_value = mock_source
            mock_source_repo_class.return_value = mock_source_repo

            # Mock catalog repo and session
            mock_catalog_repo = MagicMock()
            mock_session = MagicMock()
            mock_session.query.return_value.filter.return_value.first.return_value = (
                mock_catalog_entry
            )
            mock_catalog_repo._get_session.return_value = mock_session
            mock_catalog_repo_class.return_value = mock_catalog_repo

            response = client.patch(
                "/api/v1/marketplace/sources/src_test_123/catalog/cat_test_456/path-tags",
                json={"segment": "categories", "status": "approved"},
            )

            assert response.status_code == status.HTTP_409_CONFLICT
            assert "already has status 'approved'" in response.json()["detail"]

    def test_patch_already_rejected(self, client, mock_source, mock_catalog_entry):
        """PATCH returns 409 if segment already rejected."""
        # Pre-reject a segment
        segments_data = json.loads(mock_catalog_entry.path_segments)
        segments_data["extracted"][1]["status"] = "rejected"
        mock_catalog_entry.path_segments = json.dumps(segments_data)

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as mock_source_repo_class, patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository"
        ) as mock_catalog_repo_class:
            # Mock source repo
            mock_source_repo = MagicMock()
            mock_source_repo.get_by_id.return_value = mock_source
            mock_source_repo_class.return_value = mock_source_repo

            # Mock catalog repo and session
            mock_catalog_repo = MagicMock()
            mock_session = MagicMock()
            mock_session.query.return_value.filter.return_value.first.return_value = (
                mock_catalog_entry
            )
            mock_catalog_repo._get_session.return_value = mock_session
            mock_catalog_repo_class.return_value = mock_catalog_repo

            response = client.patch(
                "/api/v1/marketplace/sources/src_test_123/catalog/cat_test_456/path-tags",
                json={"segment": "05-data-ai", "status": "rejected"},
            )

            assert response.status_code == status.HTTP_409_CONFLICT
            assert "already has status 'rejected'" in response.json()["detail"]

    def test_patch_excluded_segment(
        self, client, mock_source, mock_catalog_entry_excluded
    ):
        """PATCH returns 409 for excluded segments."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as mock_source_repo_class, patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository"
        ) as mock_catalog_repo_class:
            # Mock source repo
            mock_source_repo = MagicMock()
            mock_source_repo.get_by_id.return_value = mock_source
            mock_source_repo_class.return_value = mock_source_repo

            # Mock catalog repo and session
            mock_catalog_repo = MagicMock()
            mock_session = MagicMock()
            mock_session.query.return_value.filter.return_value.first.return_value = (
                mock_catalog_entry_excluded
            )
            mock_catalog_repo._get_session.return_value = mock_session
            mock_catalog_repo_class.return_value = mock_catalog_repo

            response = client.patch(
                "/api/v1/marketplace/sources/src_test_123/catalog/cat_test_789/path-tags",
                json={"segment": "src", "status": "approved"},
            )

            assert response.status_code == status.HTTP_409_CONFLICT
            assert (
                "Cannot change status of excluded segment"
                in response.json()["detail"]
            )

    def test_patch_source_not_found(self, client):
        """PATCH returns 404 if source not found."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as mock_source_repo_class:
            # Mock source repo to return None
            mock_source_repo = MagicMock()
            mock_source_repo.get_by_id.return_value = None
            mock_source_repo_class.return_value = mock_source_repo

            response = client.patch(
                "/api/v1/marketplace/sources/nonexistent/catalog/cat_test_456/path-tags",
                json={"segment": "test", "status": "approved"},
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Source with ID 'nonexistent' not found" in response.json()["detail"]

    def test_patch_entry_not_found(self, client, mock_source):
        """PATCH returns 404 if catalog entry not found."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as mock_source_repo_class, patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository"
        ) as mock_catalog_repo_class:
            # Mock source repo
            mock_source_repo = MagicMock()
            mock_source_repo.get_by_id.return_value = mock_source
            mock_source_repo_class.return_value = mock_source_repo

            # Mock catalog repo to return no entry
            mock_catalog_repo = MagicMock()
            mock_session = MagicMock()
            mock_session.query.return_value.filter.return_value.first.return_value = None
            mock_catalog_repo._get_session.return_value = mock_session
            mock_catalog_repo_class.return_value = mock_catalog_repo

            response = client.patch(
                "/api/v1/marketplace/sources/src_test_123/catalog/nonexistent/path-tags",
                json={"segment": "test", "status": "approved"},
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "not found in source" in response.json()["detail"]

    def test_patch_no_path_segments(self, client, mock_source, mock_catalog_entry):
        """PATCH returns 400 if entry has no path_segments."""
        # Clear path_segments
        mock_catalog_entry.path_segments = None

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as mock_source_repo_class, patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository"
        ) as mock_catalog_repo_class:
            # Mock source repo
            mock_source_repo = MagicMock()
            mock_source_repo.get_by_id.return_value = mock_source
            mock_source_repo_class.return_value = mock_source_repo

            # Mock catalog repo
            mock_catalog_repo = MagicMock()
            mock_session = MagicMock()
            mock_session.query.return_value.filter.return_value.first.return_value = (
                mock_catalog_entry
            )
            mock_catalog_repo._get_session.return_value = mock_session
            mock_catalog_repo_class.return_value = mock_catalog_repo

            response = client.patch(
                "/api/v1/marketplace/sources/src_test_123/catalog/cat_test_456/path-tags",
                json={"segment": "test", "status": "approved"},
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "has no path_segments" in response.json()["detail"]

    def test_patch_malformed_json(self, client, mock_source, mock_catalog_entry):
        """PATCH returns 500 if path_segments JSON is malformed."""
        # Set malformed JSON
        mock_catalog_entry.path_segments = "not valid json"

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as mock_source_repo_class, patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository"
        ) as mock_catalog_repo_class:
            # Mock source repo
            mock_source_repo = MagicMock()
            mock_source_repo.get_by_id.return_value = mock_source
            mock_source_repo_class.return_value = mock_source_repo

            # Mock catalog repo
            mock_catalog_repo = MagicMock()
            mock_session = MagicMock()
            mock_session.query.return_value.filter.return_value.first.return_value = (
                mock_catalog_entry
            )
            mock_catalog_repo._get_session.return_value = mock_session
            mock_catalog_repo_class.return_value = mock_catalog_repo

            response = client.patch(
                "/api/v1/marketplace/sources/src_test_123/catalog/cat_test_456/path-tags",
                json={"segment": "test", "status": "approved"},
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "malformed path_segments" in response.json()["detail"]


class TestSchemaValidation:
    """Tests for Pydantic schema validation."""

    def test_update_request_valid_approved(self):
        """UpdateSegmentStatusRequest accepts 'approved' status."""
        req = UpdateSegmentStatusRequest(segment="test", status="approved")
        assert req.status == "approved"
        assert req.segment == "test"

    def test_update_request_valid_rejected(self):
        """UpdateSegmentStatusRequest accepts 'rejected' status."""
        req = UpdateSegmentStatusRequest(segment="test", status="rejected")
        assert req.status == "rejected"

    def test_update_request_invalid_status(self):
        """UpdateSegmentStatusRequest rejects invalid status."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            UpdateSegmentStatusRequest(segment="test", status="invalid")

    def test_update_request_empty_segment(self):
        """UpdateSegmentStatusRequest rejects empty segment."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            UpdateSegmentStatusRequest(segment="", status="approved")

    def test_extracted_segment_response(self):
        """ExtractedSegmentResponse constructs correctly."""
        seg = ExtractedSegmentResponse(
            segment="05-data-ai",
            normalized="data-ai",
            status="pending",
            reason=None,
        )
        assert seg.segment == "05-data-ai"
        assert seg.normalized == "data-ai"
        assert seg.status == "pending"
        assert seg.reason is None

    def test_path_segments_response(self):
        """PathSegmentsResponse constructs correctly."""
        resp = PathSegmentsResponse(
            entry_id="cat_123",
            raw_path="categories/05-data-ai/ai-engineer.md",
            extracted=[
                ExtractedSegmentResponse(
                    segment="categories",
                    normalized="categories",
                    status="pending",
                    reason=None,
                )
            ],
            extracted_at=datetime(2024, 1, 1, 0, 0, 0),
        )
        assert resp.entry_id == "cat_123"
        assert resp.raw_path == "categories/05-data-ai/ai-engineer.md"
        assert len(resp.extracted) == 1

    def test_update_segment_status_response(self):
        """UpdateSegmentStatusResponse constructs correctly."""
        resp = UpdateSegmentStatusResponse(
            entry_id="cat_123",
            raw_path="categories/05-data-ai/ai-engineer.md",
            extracted=[
                ExtractedSegmentResponse(
                    segment="categories",
                    normalized="categories",
                    status="approved",
                    reason=None,
                )
            ],
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
        )
        assert resp.entry_id == "cat_123"
        assert resp.extracted[0].status == "approved"
        assert isinstance(resp.updated_at, datetime)
