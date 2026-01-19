"""Performance tests for Marketplace Sources API endpoints.

TEST-009: Performance Testing for marketplace-sources-enhancement-v1 feature.

This module tests performance characteristics:
- GET /marketplace/sources with 500+ sources returns in <200ms
- Detail fetch (repo description/README) completes in <5s
- Filter queries don't degrade significantly with scale
- Tag filtering performance with many tags
"""

import json
import time
import uuid
from datetime import datetime
from typing import Dict, List
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app
from skillmeat.cache.models import MarketplaceCatalogEntry, MarketplaceSource


# =============================================================================
# Fixtures
# =============================================================================


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


def generate_mock_source(
    index: int,
    tags: List[str] | None = None,
    counts_by_type: Dict[str, int] | None = None,
) -> MarketplaceSource:
    """Generate a mock MarketplaceSource with specified index.

    Args:
        index: Unique index for the source
        tags: Optional list of tags
        counts_by_type: Optional artifact type counts

    Returns:
        MarketplaceSource instance
    """
    source = MarketplaceSource(
        id=f"src_test_{index:06d}",
        repo_url=f"https://github.com/test/repo-{index}",
        owner="test",
        repo_name=f"repo-{index}",
        ref="main",
        root_hint=None,
        trust_level="basic",
        visibility="public",
        scan_status="success",
        artifact_count=index % 20,
        last_sync_at=datetime(2025, 12, 6, 10, 30, 0),
        created_at=datetime(2025, 12, 5, 9, 0, 0),
        updated_at=datetime(2025, 12, 6, 10, 30, 0),
        enable_frontmatter_detection=False,
    )

    if tags is not None:
        source.tags = json.dumps(tags)
    else:
        # Generate some default tags based on index
        default_tags = []
        if index % 2 == 0:
            default_tags.append("python")
        if index % 3 == 0:
            default_tags.append("backend")
        if index % 5 == 0:
            default_tags.append("frontend")
        if index % 7 == 0:
            default_tags.append("devops")
        source.tags = json.dumps(default_tags) if default_tags else None

    if counts_by_type is not None:
        source.counts_by_type = json.dumps(counts_by_type)
    else:
        # Generate default counts based on index
        source.counts_by_type = json.dumps(
            {
                "skill": index % 10,
                "command": (index + 1) % 5,
                "agent": (index + 2) % 3,
            }
        )

    return source


def generate_mock_catalog_entry(source_id: str, index: int) -> MarketplaceCatalogEntry:
    """Generate a mock catalog entry.

    Args:
        source_id: Parent source ID
        index: Unique index for the entry

    Returns:
        MarketplaceCatalogEntry instance
    """
    artifact_types = ["skill", "command", "agent", "hook", "mcp_server"]
    return MarketplaceCatalogEntry(
        id=f"cat_{source_id}_{index:06d}",
        source_id=source_id,
        artifact_type=artifact_types[index % len(artifact_types)],
        name=f"artifact-{index}",
        path=f"artifacts/artifact-{index}",
        upstream_url=f"https://github.com/test/repo/tree/main/artifacts/artifact-{index}",
        detected_version="1.0.0",
        detected_sha=f"sha{index:040d}",
        detected_at=datetime(2025, 12, 6, 10, 30, 0),
        confidence_score=80 + (index % 20),
        status="new",
    )


@pytest.fixture
def many_sources():
    """Generate 500+ mock sources for performance testing."""
    return [generate_mock_source(i) for i in range(550)]


@pytest.fixture
def many_catalog_entries():
    """Generate many catalog entries for a source."""
    source_id = "src_test_000001"
    return [generate_mock_catalog_entry(source_id, i) for i in range(500)]


@pytest.fixture
def mock_source_repo_large(many_sources):
    """Create mock repository returning many sources."""
    mock = MagicMock()
    mock.list_all.return_value = many_sources
    mock.list_paginated.return_value = MagicMock(
        items=many_sources[:50], has_more=True
    )
    mock.get_by_id.return_value = many_sources[0] if many_sources else None
    return mock


@pytest.fixture
def mock_catalog_repo_large(many_catalog_entries):
    """Create mock catalog repository with many entries."""
    mock = MagicMock()
    mock.get_source_catalog.return_value = many_catalog_entries
    mock.list_paginated.return_value = MagicMock(
        items=many_catalog_entries[:50], has_more=True
    )
    mock.count_by_status.return_value = {"new": 450, "imported": 50}
    mock.count_by_type.return_value = {
        "skill": 200,
        "command": 150,
        "agent": 100,
        "hook": 30,
        "mcp_server": 20,
    }
    return mock


# =============================================================================
# TEST-009: Performance Tests
# =============================================================================


class TestListSourcesPerformance:
    """Test GET /marketplace/sources performance with many sources."""

    def test_list_sources_500_returns_under_200ms(
        self, client, mock_source_repo_large, many_sources
    ):
        """Test listing 500+ sources completes in under 200ms.

        Performance requirement: Response time should be <200ms even with
        500+ sources in the database.
        """
        mock_source_repo_large.list_paginated.return_value = MagicMock(
            items=many_sources[:50], has_more=True
        )

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo_large,
        ):
            start = time.perf_counter()
            response = client.get("/api/v1/marketplace/sources")
            duration = time.perf_counter() - start

        assert response.status_code == status.HTTP_200_OK
        assert duration < 0.2, f"Response took {duration:.3f}s, expected <200ms"

    def test_list_sources_performance_scales_linearly(
        self, client, mock_source_repo_large
    ):
        """Test that performance scales reasonably with data size.

        Verifies that pagination helps maintain consistent response times
        regardless of total dataset size.
        """
        # Test with small page (default pagination)
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo_large,
        ):
            # First request
            start1 = time.perf_counter()
            response1 = client.get("/api/v1/marketplace/sources?limit=20")
            duration1 = time.perf_counter() - start1

            # Second request (should be similar time with caching/optimization)
            start2 = time.perf_counter()
            response2 = client.get("/api/v1/marketplace/sources?limit=20")
            duration2 = time.perf_counter() - start2

        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK

        # Both requests should be under 200ms
        assert duration1 < 0.2, f"First request took {duration1:.3f}s"
        assert duration2 < 0.2, f"Second request took {duration2:.3f}s"

    def test_list_sources_pagination_performance(
        self, client, mock_source_repo_large, many_sources
    ):
        """Test paginated queries maintain consistent performance."""
        page_times = []

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo_large,
        ):
            # Simulate multiple page requests
            for offset in [0, 50, 100, 150, 200]:
                mock_source_repo_large.list_paginated.return_value = MagicMock(
                    items=many_sources[offset : offset + 50],
                    has_more=offset + 50 < len(many_sources),
                )

                start = time.perf_counter()
                response = client.get(
                    f"/api/v1/marketplace/sources?limit=50&offset={offset}"
                )
                duration = time.perf_counter() - start
                page_times.append(duration)

                assert response.status_code == status.HTTP_200_OK

        # All pages should load in under 200ms
        for i, duration in enumerate(page_times):
            assert (
                duration < 0.2
            ), f"Page {i} (offset {i*50}) took {duration:.3f}s, expected <200ms"

        # Check that variance between pages is reasonable
        avg_time = sum(page_times) / len(page_times)
        max_variance = max(abs(t - avg_time) for t in page_times)
        assert max_variance < 0.1, f"Page time variance too high: {max_variance:.3f}s"


class TestFilterPerformance:
    """Test filter query performance."""

    def test_tag_filter_performance_500_sources(
        self, client, mock_source_repo_large, many_sources
    ):
        """Test tag filtering with 500+ sources completes quickly."""
        # Filter for sources with 'python' tag (should be ~half)
        filtered_sources = [
            s
            for s in many_sources
            if s.tags and "python" in json.loads(s.tags or "[]")
        ]

        mock_source_repo_large.list_paginated.return_value = MagicMock(
            items=filtered_sources[:50], has_more=len(filtered_sources) > 50
        )

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo_large,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.SourceManager"
        ) as MockSourceManager:
            manager_instance = MagicMock()
            manager_instance.apply_filters.return_value = filtered_sources
            MockSourceManager.return_value = manager_instance

            start = time.perf_counter()
            response = client.get("/api/v1/marketplace/sources?tags=python")
            duration = time.perf_counter() - start

        assert response.status_code == status.HTTP_200_OK
        # Tag filtering should still be fast
        assert (
            duration < 0.2
        ), f"Tag filter took {duration:.3f}s, expected <200ms with 500+ sources"

    def test_artifact_type_filter_performance(
        self, client, mock_source_repo_large, many_sources
    ):
        """Test artifact_type filtering performance."""
        # Filter for sources with skills
        filtered_sources = [
            s
            for s in many_sources
            if s.counts_by_type
            and json.loads(s.counts_by_type or "{}").get("skill", 0) > 0
        ]

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo_large,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.SourceManager"
        ) as MockSourceManager:
            manager_instance = MagicMock()
            manager_instance.apply_filters.return_value = filtered_sources
            MockSourceManager.return_value = manager_instance

            start = time.perf_counter()
            response = client.get("/api/v1/marketplace/sources?artifact_type=skill")
            duration = time.perf_counter() - start

        assert response.status_code == status.HTTP_200_OK
        assert duration < 0.2, f"Artifact type filter took {duration:.3f}s"

    def test_combined_filter_performance(
        self, client, mock_source_repo_large, many_sources
    ):
        """Test combined tag + artifact_type filter performance."""
        # Combined filter should still be fast
        filtered_sources = [
            s
            for s in many_sources
            if (s.tags and "python" in json.loads(s.tags or "[]"))
            and (
                s.counts_by_type
                and json.loads(s.counts_by_type or "{}").get("skill", 0) > 0
            )
        ]

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo_large,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.SourceManager"
        ) as MockSourceManager:
            manager_instance = MagicMock()
            manager_instance.apply_filters.return_value = filtered_sources
            MockSourceManager.return_value = manager_instance

            start = time.perf_counter()
            response = client.get(
                "/api/v1/marketplace/sources?artifact_type=skill&tags=python"
            )
            duration = time.perf_counter() - start

        assert response.status_code == status.HTTP_200_OK
        assert duration < 0.2, f"Combined filter took {duration:.3f}s"

    def test_multiple_tags_filter_performance(
        self, client, mock_source_repo_large, many_sources
    ):
        """Test filtering with multiple tags."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo_large,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.SourceManager"
        ) as MockSourceManager:
            manager_instance = MagicMock()
            manager_instance.apply_filters.return_value = many_sources[:10]
            MockSourceManager.return_value = manager_instance

            start = time.perf_counter()
            response = client.get(
                "/api/v1/marketplace/sources?tags=python,backend,frontend"
            )
            duration = time.perf_counter() - start

        assert response.status_code == status.HTTP_200_OK
        assert duration < 0.2, f"Multiple tags filter took {duration:.3f}s"


class TestDetailFetchPerformance:
    """Test detail fetch performance (repo description/README)."""

    def test_get_source_detail_under_5_seconds(
        self, client, mock_source_repo_large, many_sources
    ):
        """Test fetching source details completes in <5s.

        This includes fetching repo description and README content
        which may involve external API calls.
        """
        source_with_details = many_sources[0]
        source_with_details.repo_description = "A test repository with detailed description " * 50
        source_with_details.repo_readme = "# README\n\n" + ("Content line\n" * 1000)

        mock_source_repo_large.get_by_id.return_value = source_with_details

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo_large,
        ):
            start = time.perf_counter()
            response = client.get(f"/api/v1/marketplace/sources/{source_with_details.id}")
            duration = time.perf_counter() - start

        assert response.status_code == status.HTTP_200_OK
        assert duration < 5.0, f"Detail fetch took {duration:.3f}s, expected <5s"

    def test_get_source_artifacts_pagination_performance(
        self, client, mock_source_repo_large, mock_catalog_repo_large, many_sources
    ):
        """Test listing source artifacts with pagination performs well."""
        source = many_sources[0]
        mock_source_repo_large.get_by_id.return_value = source

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo_large,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo_large,
        ):
            start = time.perf_counter()
            response = client.get(
                f"/api/v1/marketplace/sources/{source.id}/artifacts?limit=50"
            )
            duration = time.perf_counter() - start

        assert response.status_code == status.HTTP_200_OK
        assert duration < 0.5, f"Artifacts list took {duration:.3f}s, expected <500ms"


class TestTagPerformanceWithManyTags:
    """Test tag-related operations with sources having many tags."""

    def test_source_with_max_tags_serialization_performance(self, client):
        """Test that sources with maximum tags (20) serialize quickly.

        Note: The current source_to_response function doesn't fully populate
        tags from the ORM model. This test verifies response time only.
        When tag population is implemented, extend this test to verify tag count.
        """
        # Create source with max tags
        source = generate_mock_source(
            1, tags=[f"tag{i}" for i in range(20)]  # Max 20 tags
        )

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = source

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_repo,
        ):
            start = time.perf_counter()
            response = client.get(f"/api/v1/marketplace/sources/{source.id}")
            duration = time.perf_counter() - start

        assert response.status_code == status.HTTP_200_OK
        assert duration < 0.1, f"Max tags source took {duration:.3f}s"

        # Verify response structure is valid
        data = response.json()
        assert "tags" in data
        # Note: Tags population from ORM may need implementation
        # When implemented: assert len(data.get("tags", [])) == 20

    def test_filter_sources_with_many_tags_each(
        self, client, mock_source_repo_large
    ):
        """Test filtering when sources have many tags each."""
        # Generate sources with more tags
        sources_many_tags = [
            generate_mock_source(i, tags=[f"tag{j}" for j in range(min(i % 20 + 1, 20))])
            for i in range(100)
        ]

        mock_source_repo_large.list_all.return_value = sources_many_tags
        mock_source_repo_large.list_paginated.return_value = MagicMock(
            items=sources_many_tags[:50], has_more=True
        )

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo_large,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.SourceManager"
        ) as MockSourceManager:
            manager_instance = MagicMock()
            manager_instance.apply_filters.return_value = sources_many_tags[:25]
            MockSourceManager.return_value = manager_instance

            start = time.perf_counter()
            response = client.get("/api/v1/marketplace/sources?tags=tag5")
            duration = time.perf_counter() - start

        assert response.status_code == status.HTTP_200_OK
        assert duration < 0.2, f"Filter with many tags took {duration:.3f}s"


class TestConcurrentRequestPerformance:
    """Test performance under simulated concurrent load."""

    def test_multiple_sequential_requests_consistent_performance(
        self, client, mock_source_repo_large, many_sources
    ):
        """Test that multiple sequential requests maintain consistent performance."""
        request_times = []

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo_large,
        ):
            for i in range(10):
                start = time.perf_counter()
                response = client.get("/api/v1/marketplace/sources")
                duration = time.perf_counter() - start
                request_times.append(duration)

                assert response.status_code == status.HTTP_200_OK

        # All requests should be under 200ms
        for i, duration in enumerate(request_times):
            assert duration < 0.2, f"Request {i+1} took {duration:.3f}s"

        # Average should be reasonable
        avg_time = sum(request_times) / len(request_times)
        assert avg_time < 0.15, f"Average request time {avg_time:.3f}s exceeds 150ms"


class TestDataSizeScaling:
    """Test performance scaling with different data sizes."""

    @pytest.mark.parametrize("source_count", [100, 250, 500])
    def test_list_sources_scales_with_count(
        self, client, source_count
    ):
        """Test listing sources scales appropriately with different counts."""
        sources = [generate_mock_source(i) for i in range(source_count)]

        mock_repo = MagicMock()
        mock_repo.list_paginated.return_value = MagicMock(
            items=sources[:50], has_more=source_count > 50
        )
        mock_repo.list_all.return_value = sources

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_repo,
        ):
            start = time.perf_counter()
            response = client.get("/api/v1/marketplace/sources")
            duration = time.perf_counter() - start

        assert response.status_code == status.HTTP_200_OK
        # Should always be under 200ms regardless of total count due to pagination
        assert (
            duration < 0.2
        ), f"List {source_count} sources took {duration:.3f}s, expected <200ms"

    @pytest.mark.parametrize("artifact_count", [100, 250, 500])
    def test_list_artifacts_scales_with_count(
        self, client, artifact_count
    ):
        """Test listing artifacts scales appropriately with different counts."""
        source_id = "src_test_000001"
        source = generate_mock_source(1)
        source.id = source_id
        source.artifact_count = artifact_count

        entries = [generate_mock_catalog_entry(source_id, i) for i in range(artifact_count)]

        mock_source_repo = MagicMock()
        mock_source_repo.get_by_id.return_value = source

        mock_catalog_repo = MagicMock()
        mock_catalog_repo.list_paginated.return_value = MagicMock(
            items=entries[:50], has_more=artifact_count > 50
        )
        mock_catalog_repo.count_by_status.return_value = {"new": artifact_count}
        mock_catalog_repo.count_by_type.return_value = {"skill": artifact_count}

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            start = time.perf_counter()
            response = client.get(f"/api/v1/marketplace/sources/{source_id}/artifacts")
            duration = time.perf_counter() - start

        assert response.status_code == status.HTTP_200_OK
        # Should always be under 500ms due to pagination
        assert (
            duration < 0.5
        ), f"List {artifact_count} artifacts took {duration:.3f}s, expected <500ms"
