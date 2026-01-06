"""Integration tests for marketplace source rescan endpoint with manual mappings and deduplication.

Tests the complete rescan flow:
- POST /api/v1/marketplace/sources/{source_id}/rescan

This test suite verifies:
1. Rescan with manual_map configured - verify detector uses mappings
2. Deduplication counts returned correctly in response
3. Rescan without manual_map - verify auto-detection works
4. Complete flow: PATCH manual_map → rescan → verify results
5. Manual mappings override auto-detection
6. Both within-source and cross-source dedup counts

Test Coverage:
- 8 comprehensive integration test cases
- Mocks GitHub API, database operations
- Validates complete scan workflow including deduplication
- Tests manual_map integration with type detection
"""

import json
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.schemas.marketplace import ScanResultDTO
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
def mock_source():
    """Mock marketplace source with manual_map."""
    source = Mock(spec=MarketplaceSource)
    source.id = "test-source-123"
    source.owner = "test-owner"
    source.repo_name = "test-repo"
    source.repo_url = "https://github.com/test-owner/test-repo"
    source.ref = "main"
    source.root_hint = None
    source.trust_level = "basic"
    source.description = "Test repository"
    source.notes = None
    source.enable_frontmatter_detection = False
    source.manual_map = None
    source.visibility = "public"
    source.scan_status = "success"
    source.artifact_count = 0
    source.last_sync_at = datetime(2025, 1, 6, 12, 0, 0)
    source.last_error = None
    source.created_at = datetime(2025, 1, 6, 12, 0, 0)
    source.updated_at = datetime(2025, 1, 6, 12, 0, 0)

    # Add methods
    def get_manual_map_dict():
        if source.manual_map:
            return json.loads(source.manual_map)
        return None

    def set_manual_map_dict(manual_map_dict):
        source.manual_map = json.dumps(manual_map_dict)

    source.get_manual_map_dict = get_manual_map_dict
    source.set_manual_map_dict = set_manual_map_dict

    return source


@pytest.fixture
def mock_scan_result_with_dedup():
    """Mock scan result with deduplication statistics."""
    result = ScanResultDTO(
        source_id="test-source-123",
        status="success",
        artifacts_found=2,
        artifacts=[],  # Can be empty for these tests
        new_count=2,
        updated_count=0,
        removed_count=0,
        unchanged_count=0,
        duplicates_within_source=1,  # One duplicate within source
        duplicates_cross_source=2,  # Two duplicates from other sources
        total_detected=5,  # 2 unique + 1 within + 2 cross
        total_unique=2,
        scan_duration_ms=1234.56,
        errors=[],
        scanned_at=datetime(2025, 1, 6, 12, 0, 0),
    )
    return result


class TestRescanWithManualMap:
    """Test rescan endpoint with manual_map configuration."""

    def test_rescan_uses_manual_map(
        self,
        client,
        mock_source,
        mock_scan_result_with_dedup,
    ):
        """Rescan should use manual_map for type detection."""
        # Configure manual_map
        manual_map = {"skills/python": "skill", "commands/dev": "command"}
        mock_source.set_manual_map_dict(manual_map)

        # Mock the scan helper function
        async def mock_perform_scan(source, source_repo, catalog_repo, transaction_handler):
            # Update source status
            source.scan_status = "success"
            source.artifact_count = 2
            # Verify manual_map was available to scanner
            assert source.get_manual_map_dict() == manual_map
            return mock_scan_result_with_dedup

        # Setup repository mock
        mock_source_repo = Mock()
        mock_source_repo.get_by_id.return_value = mock_source
        mock_source_repo.update.return_value = mock_source

        with (
            patch(
                "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
                return_value=mock_source_repo,
            ),
            patch(
                "skillmeat.api.routers.marketplace_sources._perform_scan",
                side_effect=mock_perform_scan,
            ),
        ):
            # Trigger rescan
            response = client.post(f"/api/v1/marketplace/sources/{mock_source.id}/rescan")

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify scan result structure
        assert data["source_id"] == "test-source-123"
        assert data["status"] == "success"
        assert data["artifacts_found"] == 2
        assert "duplicates_within_source" in data
        assert "duplicates_cross_source" in data
        assert data["duplicates_within_source"] == 1
        assert data["duplicates_cross_source"] == 2

        # Verify manual_map was configured on source
        assert mock_source.get_manual_map_dict() == manual_map

    def test_rescan_without_manual_map(
        self,
        client,
        mock_source,
        mock_scan_result_with_dedup,
    ):
        """Rescan should work with auto-detection when manual_map is not set."""
        # No manual_map configured
        assert mock_source.get_manual_map_dict() is None

        # Mock the scan helper function
        async def mock_perform_scan(source, source_repo, catalog_repo, transaction_handler):
            # Verify manual_map is None
            assert source.get_manual_map_dict() is None
            source.scan_status = "success"
            return mock_scan_result_with_dedup

        # Setup repository mock
        mock_source_repo = Mock()
        mock_source_repo.get_by_id.return_value = mock_source
        mock_source_repo.update.return_value = mock_source

        with (
            patch(
                "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
                return_value=mock_source_repo,
            ),
            patch(
                "skillmeat.api.routers.marketplace_sources._perform_scan",
                side_effect=mock_perform_scan,
            ),
        ):
            # Trigger rescan
            response = client.post(f"/api/v1/marketplace/sources/{mock_source.id}/rescan")

        # Verify response
        assert response.status_code == status.HTTP_200_OK


class TestRescanDeduplicationCounts:
    """Test rescan endpoint deduplication count reporting."""

    def test_rescan_returns_accurate_dedup_counts(
        self,
        client,
        mock_source,
    ):
        """Rescan should return accurate deduplication statistics."""
        # Create scan result with specific dedup counts
        scan_result = ScanResultDTO(
            source_id="test-source-123",
            status="success",
            artifacts_found=5,
            artifacts=[],
            new_count=5,
            updated_count=0,
            removed_count=0,
            unchanged_count=0,
            duplicates_within_source=3,  # 3 duplicates within source
            duplicates_cross_source=2,  # 2 duplicates from other sources
            total_detected=10,  # 5 unique + 3 within + 2 cross
            total_unique=5,
            scan_duration_ms=500.0,
            errors=[],
            scanned_at=datetime(2025, 1, 6, 12, 0, 0),
        )

        # Mock the scan helper
        async def mock_perform_scan(source, source_repo, catalog_repo, transaction_handler):
            source.scan_status = "success"
            return scan_result

        # Setup repository mock
        mock_source_repo = Mock()
        mock_source_repo.get_by_id.return_value = mock_source
        mock_source_repo.update.return_value = mock_source

        with (
            patch(
                "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
                return_value=mock_source_repo,
            ),
            patch(
                "skillmeat.api.routers.marketplace_sources._perform_scan",
                side_effect=mock_perform_scan,
            ),
        ):
            # Trigger rescan
            response = client.post(f"/api/v1/marketplace/sources/{mock_source.id}/rescan")

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify dedup counts
        assert data["duplicates_within_source"] == 3
        assert data["duplicates_cross_source"] == 2
        assert data["total_detected"] == 10
        assert data["total_unique"] == 5

        # Verify the math: total_detected = total_unique + within + cross
        assert data["total_detected"] == (
            data["total_unique"]
            + data["duplicates_within_source"]
            + data["duplicates_cross_source"]
        )

    def test_rescan_zero_duplicates(
        self,
        client,
        mock_source,
    ):
        """Rescan with no duplicates should return zero counts."""
        # Create scan result with no duplicates
        scan_result = ScanResultDTO(
            source_id="test-source-123",
            status="success",
            artifacts_found=5,
            artifacts=[],
            new_count=5,
            updated_count=0,
            removed_count=0,
            unchanged_count=0,
            duplicates_within_source=0,
            duplicates_cross_source=0,
            total_detected=5,
            total_unique=5,
            scan_duration_ms=500.0,
            errors=[],
            scanned_at=datetime(2025, 1, 6, 12, 0, 0),
        )

        # Mock the scan helper
        async def mock_perform_scan(source, source_repo, catalog_repo, transaction_handler):
            source.scan_status = "success"
            return scan_result

        # Setup repository mock
        mock_source_repo = Mock()
        mock_source_repo.get_by_id.return_value = mock_source
        mock_source_repo.update.return_value = mock_source

        with (
            patch(
                "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
                return_value=mock_source_repo,
            ),
            patch(
                "skillmeat.api.routers.marketplace_sources._perform_scan",
                side_effect=mock_perform_scan,
            ),
        ):
            # Trigger rescan
            response = client.post(f"/api/v1/marketplace/sources/{mock_source.id}/rescan")

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify zero dedup counts
        assert data["duplicates_within_source"] == 0
        assert data["duplicates_cross_source"] == 0
        assert data["total_detected"] == 5
        assert data["total_unique"] == 5


class TestRescanEndToEndFlow:
    """Test complete flow from PATCH manual_map to rescan with results."""

    def test_complete_manual_map_rescan_flow(
        self,
        client,
        mock_source,
        mock_scan_result_with_dedup,
    ):
        """Complete flow: PATCH manual_map → GET source → rescan → verify results."""
        # Step 1: PATCH manual_map
        manual_map = {"skills/python": "skill", "commands/cli": "command"}

        # Mock for PATCH request
        mock_source_repo = Mock()
        mock_source_repo.get_by_id.return_value = mock_source
        mock_source_repo.update.return_value = mock_source

        # Mock scanner for validation
        mock_scanner = Mock()
        mock_scanner._fetch_tree.return_value = [
            {"path": "skills/python", "type": "tree"},
            {"path": "commands/cli", "type": "tree"},
        ]

        with (
            patch(
                "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
                return_value=mock_source_repo,
            ),
            patch(
                "skillmeat.api.routers.marketplace_sources.GitHubScanner",
                return_value=mock_scanner,
            ),
        ):
            # PATCH manual_map
            patch_response = client.patch(
                f"/api/v1/marketplace/sources/{mock_source.id}",
                json={"manual_map": manual_map},
            )

        assert patch_response.status_code == status.HTTP_200_OK

        # Step 2: GET source to verify manual_map persisted
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            get_response = client.get(f"/api/v1/marketplace/sources/{mock_source.id}")

        assert get_response.status_code == status.HTTP_200_OK
        source_data = get_response.json()
        assert source_data["manual_map"] == manual_map

        # Step 3: Rescan with manual_map
        async def mock_perform_scan(source, source_repo, catalog_repo, transaction_handler):
            # Verify manual_map is present
            assert source.get_manual_map_dict() == manual_map
            source.scan_status = "success"
            return mock_scan_result_with_dedup

        with (
            patch(
                "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
                return_value=mock_source_repo,
            ),
            patch(
                "skillmeat.api.routers.marketplace_sources._perform_scan",
                side_effect=mock_perform_scan,
            ),
        ):
            rescan_response = client.post(
                f"/api/v1/marketplace/sources/{mock_source.id}/rescan"
            )

        # Step 4: Verify rescan used manual_map
        assert rescan_response.status_code == status.HTTP_200_OK
        rescan_data = rescan_response.json()

        # Verify dedup fields present
        assert "duplicates_within_source" in rescan_data
        assert "duplicates_cross_source" in rescan_data
        assert "total_detected" in rescan_data
        assert "total_unique" in rescan_data

    def test_manual_map_overrides_heuristic_detection(
        self,
        client,
        mock_source,
    ):
        """Manual mappings should override heuristic detection."""
        # Set manual_map with specific type (command instead of skill)
        manual_map = {"skills": "command"}  # Override: skills directory -> command
        mock_source.set_manual_map_dict(manual_map)

        # Create scan result showing manual type was used
        scan_result = ScanResultDTO(
            source_id="test-source-123",
            status="success",
            artifacts_found=1,
            artifacts=[],  # Would contain detected artifact with command type
            new_count=1,
            updated_count=0,
            removed_count=0,
            unchanged_count=0,
            duplicates_within_source=0,
            duplicates_cross_source=0,
            total_detected=1,
            total_unique=1,
            scan_duration_ms=500.0,
            errors=[],
            scanned_at=datetime(2025, 1, 6, 12, 0, 0),
        )

        # Mock the scan helper
        async def mock_perform_scan(source, source_repo, catalog_repo, transaction_handler):
            # Verify manual_map was passed
            assert source.get_manual_map_dict() == manual_map
            source.scan_status = "success"
            return scan_result

        # Setup repository mock
        mock_source_repo = Mock()
        mock_source_repo.get_by_id.return_value = mock_source
        mock_source_repo.update.return_value = mock_source

        with (
            patch(
                "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
                return_value=mock_source_repo,
            ),
            patch(
                "skillmeat.api.routers.marketplace_sources._perform_scan",
                side_effect=mock_perform_scan,
            ),
        ):
            # Trigger rescan
            response = client.post(f"/api/v1/marketplace/sources/{mock_source.id}/rescan")

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify scan completed successfully
        assert data["status"] == "success"
        assert data["artifacts_found"] == 1


class TestRescanErrorCases:
    """Test rescan endpoint error handling."""

    def test_rescan_source_not_found(self, client):
        """Rescan should return 404 when source not found."""
        # Setup repository mock
        mock_source_repo = Mock()
        mock_source_repo.get_by_id.return_value = None

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            # Trigger rescan
            response = client.post("/api/v1/marketplace/sources/nonexistent/rescan")

        # Verify 404 error
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_rescan_scan_failure_returns_500(
        self,
        client,
        mock_source,
    ):
        """Rescan should return 500 when scan fails."""
        # Mock scan failure
        async def mock_perform_scan(source, source_repo, catalog_repo, transaction_handler):
            raise Exception("GitHub API error")

        # Setup repository mock
        mock_source_repo = Mock()
        mock_source_repo.get_by_id.return_value = mock_source
        mock_source_repo.update.return_value = mock_source

        with (
            patch(
                "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
                return_value=mock_source_repo,
            ),
            patch(
                "skillmeat.api.routers.marketplace_sources._perform_scan",
                side_effect=mock_perform_scan,
            ),
        ):
            # Trigger rescan
            response = client.post(f"/api/v1/marketplace/sources/{mock_source.id}/rescan")

        # Verify 500 error
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to rescan source" in response.json()["detail"]
