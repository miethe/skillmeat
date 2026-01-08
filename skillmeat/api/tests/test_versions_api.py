"""Integration tests for Version Management API endpoints.

Tests snapshot CRUD, rollback operations, and diff functionality.
"""

from datetime import datetime
from unittest.mock import Mock, patch
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings
from skillmeat.api.server import create_app
from skillmeat.storage.snapshot import Snapshot
from skillmeat.models import ConflictMetadata


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
def sample_snapshot():
    """Create a sample snapshot for testing."""
    return Snapshot(
        id="abc123def456",
        timestamp=datetime(2025, 12, 17, 12, 0, 0),
        message="Test snapshot",
        collection_name="default",
        tarball_path=Path("/tmp/snapshots/abc123def456.tar.gz"),
        artifact_count=5,
    )


# ====================
# Snapshot List Tests
# ====================


class TestListSnapshots:
    """Test GET /api/v1/versions/snapshots endpoint."""

    def test_list_snapshots_success(self, client, sample_snapshot):
        """Test listing snapshots successfully."""
        from skillmeat.api.routers.versions import get_version_manager

        mock_mgr = Mock()
        mock_mgr.list_snapshots.return_value = ([sample_snapshot], None)

        # Use FastAPI dependency override
        client.app.dependency_overrides[get_version_manager] = lambda: mock_mgr

        try:
            response = client.get("/api/v1/versions/snapshots")

            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert "page_info" in data
            assert len(data["items"]) == 1
            assert data["items"][0]["id"] == "abc123def456"
            assert data["items"][0]["message"] == "Test snapshot"
            assert data["items"][0]["artifact_count"] == 5

            # Verify pagination info
            assert data["page_info"]["has_next_page"] is False
            assert data["page_info"]["has_previous_page"] is False
        finally:
            # Clean up override
            client.app.dependency_overrides.clear()

    def test_list_snapshots_with_pagination(self, client, sample_snapshot):
        """Test listing snapshots with pagination."""
        mock_mgr = Mock()

        # Create second snapshot
        snapshot2 = Snapshot(
            id="def789ghi012",
            timestamp=datetime(2025, 12, 17, 13, 0, 0),
            message="Second snapshot",
            collection_name="default",
            tarball_path=Path("/tmp/snapshots/def789ghi012.tar.gz"),
            artifact_count=6,
        )

        # First page
        mock_mgr.list_snapshots.return_value = (
            [sample_snapshot],
            "def789ghi012",  # next cursor
        )

        with patch(
            "skillmeat.api.routers.versions.get_version_manager", return_value=mock_mgr
        ):
            response = client.get("/api/v1/versions/snapshots?limit=1")

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 1
            assert data["page_info"]["has_next_page"] is True
            assert data["page_info"]["end_cursor"] is not None

    def test_list_snapshots_with_cursor(self, client, sample_snapshot):
        """Test listing snapshots with cursor pagination."""
        import base64

        mock_mgr = Mock()
        cursor = base64.b64encode("abc123def456".encode()).decode()
        mock_mgr.list_snapshots.return_value = ([sample_snapshot], None)

        with patch(
            "skillmeat.api.routers.versions.get_version_manager", return_value=mock_mgr
        ):
            response = client.get(f"/api/v1/versions/snapshots?after={cursor}")

            assert response.status_code == 200
            # Verify cursor was decoded and passed to manager
            mock_mgr.list_snapshots.assert_called_once()
            call_kwargs = mock_mgr.list_snapshots.call_args[1]
            assert call_kwargs["cursor"] == "abc123def456"

    def test_list_snapshots_invalid_cursor(self, client):
        """Test listing with invalid cursor format."""
        mock_mgr = Mock()

        with patch(
            "skillmeat.api.routers.versions.get_version_manager", return_value=mock_mgr
        ):
            response = client.get("/api/v1/versions/snapshots?after=invalid-base64!")

            assert response.status_code == 400
            assert "invalid cursor format" in response.json()["detail"].lower()

    def test_list_snapshots_with_collection_filter(self, client, sample_snapshot):
        """Test listing snapshots filtered by collection."""
        mock_mgr = Mock()
        mock_mgr.list_snapshots.return_value = ([sample_snapshot], None)

        with patch(
            "skillmeat.api.routers.versions.get_version_manager", return_value=mock_mgr
        ):
            response = client.get("/api/v1/versions/snapshots?collection_name=default")

            assert response.status_code == 200
            mock_mgr.list_snapshots.assert_called_once()
            call_kwargs = mock_mgr.list_snapshots.call_args[1]
            assert call_kwargs["collection_name"] == "default"

    def test_list_snapshots_empty(self, client):
        """Test listing when no snapshots exist."""
        mock_mgr = Mock()
        mock_mgr.list_snapshots.return_value = ([], None)

        with patch(
            "skillmeat.api.routers.versions.get_version_manager", return_value=mock_mgr
        ):
            response = client.get("/api/v1/versions/snapshots")

            assert response.status_code == 200
            data = response.json()
            assert data["items"] == []
            assert data["page_info"]["has_next_page"] is False

    def test_list_snapshots_limit_boundaries(self, client):
        """Test pagination limit boundaries."""
        mock_mgr = Mock()
        mock_mgr.list_snapshots.return_value = ([], None)

        with patch(
            "skillmeat.api.routers.versions.get_version_manager", return_value=mock_mgr
        ):
            # Test minimum limit
            response = client.get("/api/v1/versions/snapshots?limit=1")
            assert response.status_code == 200

            # Test maximum limit
            response = client.get("/api/v1/versions/snapshots?limit=100")
            assert response.status_code == 200

            # Test exceeding maximum limit
            response = client.get("/api/v1/versions/snapshots?limit=101")
            assert response.status_code == 422  # Validation error

            # Test below minimum limit
            response = client.get("/api/v1/versions/snapshots?limit=0")
            assert response.status_code == 422

    def test_list_snapshots_error(self, client):
        """Test error handling during listing."""
        mock_mgr = Mock()
        mock_mgr.list_snapshots.side_effect = Exception("Database error")

        with patch(
            "skillmeat.api.routers.versions.get_version_manager", return_value=mock_mgr
        ):
            response = client.get("/api/v1/versions/snapshots")

            assert response.status_code == 500
            assert "failed to list snapshots" in response.json()["detail"].lower()


# ====================
# Get Snapshot Tests
# ====================


class TestGetSnapshot:
    """Test GET /api/v1/versions/snapshots/{snapshot_id} endpoint."""

    def test_get_snapshot_success(self, client, sample_snapshot):
        """Test getting a single snapshot successfully."""
        mock_mgr = Mock()
        mock_mgr.get_snapshot.return_value = sample_snapshot

        with patch(
            "skillmeat.api.routers.versions.get_version_manager", return_value=mock_mgr
        ):
            response = client.get("/api/v1/versions/snapshots/abc123def456")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "abc123def456"
            assert data["message"] == "Test snapshot"
            assert data["collection_name"] == "default"
            assert data["artifact_count"] == 5

    def test_get_snapshot_not_found(self, client):
        """Test getting non-existent snapshot."""
        mock_mgr = Mock()
        mock_mgr.get_snapshot.return_value = None

        with patch(
            "skillmeat.api.routers.versions.get_version_manager", return_value=mock_mgr
        ):
            response = client.get("/api/v1/versions/snapshots/nonexistent")

            assert response.status_code == 404
            assert (
                "snapshot 'nonexistent' not found" in response.json()["detail"].lower()
            )

    def test_get_snapshot_with_collection(self, client, sample_snapshot):
        """Test getting snapshot with collection name specified."""
        mock_mgr = Mock()
        mock_mgr.get_snapshot.return_value = sample_snapshot

        with patch(
            "skillmeat.api.routers.versions.get_version_manager", return_value=mock_mgr
        ):
            response = client.get(
                "/api/v1/versions/snapshots/abc123def456?collection_name=default"
            )

            assert response.status_code == 200
            mock_mgr.get_snapshot.assert_called_once_with("abc123def456", "default")

    def test_get_snapshot_error(self, client):
        """Test error handling when getting snapshot."""
        mock_mgr = Mock()
        mock_mgr.get_snapshot.side_effect = Exception("IO error")

        with patch(
            "skillmeat.api.routers.versions.get_version_manager", return_value=mock_mgr
        ):
            response = client.get("/api/v1/versions/snapshots/abc123def456")

            assert response.status_code == 500
            assert "failed to get snapshot" in response.json()["detail"].lower()


# ====================
# Create Snapshot Tests
# ====================


class TestCreateSnapshot:
    """Test POST /api/v1/versions/snapshots endpoint."""

    def test_create_snapshot_success(self, client, sample_snapshot):
        """Test creating a snapshot successfully."""
        mock_mgr = Mock()
        mock_mgr.create_snapshot.return_value = sample_snapshot

        with patch(
            "skillmeat.api.routers.versions.get_version_manager", return_value=mock_mgr
        ):
            request_data = {
                "collection_name": "default",
                "message": "Test snapshot",
            }

            response = client.post("/api/v1/versions/snapshots", json=request_data)

            assert response.status_code == 201
            data = response.json()
            assert data["created"] is True
            assert data["snapshot"]["id"] == "abc123def456"
            assert data["snapshot"]["message"] == "Test snapshot"

            mock_mgr.create_snapshot.assert_called_once_with(
                collection_name="default",
                message="Test snapshot",
            )

    def test_create_snapshot_default_message(self, client, sample_snapshot):
        """Test creating snapshot with default message."""
        mock_mgr = Mock()
        mock_mgr.create_snapshot.return_value = sample_snapshot

        with patch(
            "skillmeat.api.routers.versions.get_version_manager", return_value=mock_mgr
        ):
            request_data = {
                "collection_name": "default",
            }

            response = client.post("/api/v1/versions/snapshots", json=request_data)

            assert response.status_code == 201

    def test_create_snapshot_collection_not_found(self, client):
        """Test creating snapshot for non-existent collection."""
        mock_mgr = Mock()
        mock_mgr.create_snapshot.side_effect = ValueError(
            "Collection 'nonexistent' not found"
        )

        with patch(
            "skillmeat.api.routers.versions.get_version_manager", return_value=mock_mgr
        ):
            request_data = {
                "collection_name": "nonexistent",
                "message": "Test",
            }

            response = client.post("/api/v1/versions/snapshots", json=request_data)

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_create_snapshot_no_collection(self, client, sample_snapshot):
        """Test creating snapshot without specifying collection."""
        mock_mgr = Mock()
        mock_mgr.create_snapshot.return_value = sample_snapshot

        with patch(
            "skillmeat.api.routers.versions.get_version_manager", return_value=mock_mgr
        ):
            request_data = {
                "message": "Test snapshot",
            }

            response = client.post("/api/v1/versions/snapshots", json=request_data)

            assert response.status_code == 201

    def test_create_snapshot_message_too_long(self, client):
        """Test creating snapshot with message exceeding max length."""
        mock_mgr = Mock()

        with patch(
            "skillmeat.api.routers.versions.get_version_manager", return_value=mock_mgr
        ):
            request_data = {
                "message": "x" * 501,  # Max is 500
            }

            response = client.post("/api/v1/versions/snapshots", json=request_data)

            assert response.status_code == 422  # Validation error

    def test_create_snapshot_error(self, client):
        """Test error handling during snapshot creation."""
        mock_mgr = Mock()
        mock_mgr.create_snapshot.side_effect = Exception("Disk full")

        with patch(
            "skillmeat.api.routers.versions.get_version_manager", return_value=mock_mgr
        ):
            request_data = {
                "message": "Test",
            }

            response = client.post("/api/v1/versions/snapshots", json=request_data)

            assert response.status_code == 500
            assert "failed to create snapshot" in response.json()["detail"].lower()


# ====================
# Delete Snapshot Tests
# ====================


class TestDeleteSnapshot:
    """Test DELETE /api/v1/versions/snapshots/{snapshot_id} endpoint."""

    def test_delete_snapshot_success(self, client):
        """Test deleting a snapshot successfully."""
        mock_mgr = Mock()
        mock_mgr.delete_snapshot.return_value = None

        with patch(
            "skillmeat.api.routers.versions.get_version_manager", return_value=mock_mgr
        ):
            response = client.delete("/api/v1/versions/snapshots/abc123def456")

            assert response.status_code == 204
            assert response.content == b""

            mock_mgr.delete_snapshot.assert_called_once_with("abc123def456", None)

    def test_delete_snapshot_with_collection(self, client):
        """Test deleting snapshot with collection specified."""
        mock_mgr = Mock()
        mock_mgr.delete_snapshot.return_value = None

        with patch(
            "skillmeat.api.routers.versions.get_version_manager", return_value=mock_mgr
        ):
            response = client.delete(
                "/api/v1/versions/snapshots/abc123def456?collection_name=default"
            )

            assert response.status_code == 204
            mock_mgr.delete_snapshot.assert_called_once_with("abc123def456", "default")

    def test_delete_snapshot_not_found(self, client):
        """Test deleting non-existent snapshot."""
        mock_mgr = Mock()
        mock_mgr.delete_snapshot.side_effect = ValueError("Snapshot not found")

        with patch(
            "skillmeat.api.routers.versions.get_version_manager", return_value=mock_mgr
        ):
            response = client.delete("/api/v1/versions/snapshots/nonexistent")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_delete_snapshot_error(self, client):
        """Test error handling during deletion."""
        mock_mgr = Mock()
        mock_mgr.delete_snapshot.side_effect = Exception("Permission denied")

        with patch(
            "skillmeat.api.routers.versions.get_version_manager", return_value=mock_mgr
        ):
            response = client.delete("/api/v1/versions/snapshots/abc123def456")

            assert response.status_code == 500
            assert "failed to delete snapshot" in response.json()["detail"].lower()


# ====================
# Rollback Analysis Tests
# ====================


class TestAnalyzeRollbackSafety:
    """Test GET /api/v1/versions/snapshots/{snapshot_id}/rollback-analysis endpoint."""

    def test_analyze_rollback_safe(self, client):
        """Test rollback analysis when safe."""
        from skillmeat.models import MergeSafetyAnalysis

        mock_mgr = Mock()
        analysis = MergeSafetyAnalysis(
            is_safe=True,
            files_with_conflicts=[],
            files_safe_to_restore=[".claude/skills/pdf/SKILL.md"],
            warnings=[],
        )
        mock_mgr.analyze_rollback_safety.return_value = analysis

        with patch(
            "skillmeat.api.routers.versions.get_version_manager", return_value=mock_mgr
        ):
            response = client.get(
                "/api/v1/versions/snapshots/abc123def456/rollback-analysis"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["is_safe"] is True
            assert len(data["files_safe_to_restore"]) == 1
            assert len(data["files_with_conflicts"]) == 0
            assert len(data["warnings"]) == 0

    def test_analyze_rollback_unsafe(self, client):
        """Test rollback analysis when unsafe."""
        from skillmeat.models import MergeSafetyAnalysis

        mock_mgr = Mock()
        analysis = MergeSafetyAnalysis(
            is_safe=False,
            files_with_conflicts=[".claude/skills/pdf/SKILL.md"],
            files_safe_to_restore=[],
            warnings=["File has been modified since snapshot"],
        )
        mock_mgr.analyze_rollback_safety.return_value = analysis

        with patch(
            "skillmeat.api.routers.versions.get_version_manager", return_value=mock_mgr
        ):
            response = client.get(
                "/api/v1/versions/snapshots/abc123def456/rollback-analysis"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["is_safe"] is False
            assert len(data["files_with_conflicts"]) == 1
            assert len(data["warnings"]) == 1

    def test_analyze_rollback_snapshot_not_found(self, client):
        """Test rollback analysis for non-existent snapshot."""
        mock_mgr = Mock()
        mock_mgr.analyze_rollback_safety.side_effect = ValueError("Snapshot not found")

        with patch(
            "skillmeat.api.routers.versions.get_version_manager", return_value=mock_mgr
        ):
            response = client.get(
                "/api/v1/versions/snapshots/nonexistent/rollback-analysis"
            )

            assert response.status_code == 404

    def test_analyze_rollback_with_collection(self, client):
        """Test rollback analysis with collection specified."""
        from skillmeat.models import MergeSafetyAnalysis

        mock_mgr = Mock()
        analysis = MergeSafetyAnalysis(
            is_safe=True,
            files_with_conflicts=[],
            files_safe_to_restore=[],
            warnings=[],
        )
        mock_mgr.analyze_rollback_safety.return_value = analysis

        with patch(
            "skillmeat.api.routers.versions.get_version_manager", return_value=mock_mgr
        ):
            response = client.get(
                "/api/v1/versions/snapshots/abc123def456/rollback-analysis?collection_name=default"
            )

            assert response.status_code == 200
            mock_mgr.analyze_rollback_safety.assert_called_once_with(
                "abc123def456", "default"
            )


# ====================
# Rollback Execution Tests
# ====================


class TestRollback:
    """Test POST /api/v1/versions/snapshots/{snapshot_id}/rollback endpoint."""

    def test_rollback_success(self, client):
        """Test successful rollback execution."""
        from skillmeat.models import VersionMergeResult

        mock_mgr = Mock()
        result = VersionMergeResult(
            success=True,
            files_merged=[".claude/skills/pdf/SKILL.md"],
            files_restored=[".claude/skills/canvas/SKILL.md"],
            conflicts=[],
            pre_merge_snapshot_id="safety123",
        )
        mock_mgr.intelligent_rollback.return_value = result

        with patch(
            "skillmeat.api.routers.versions.get_version_manager", return_value=mock_mgr
        ):
            request_data = {
                "snapshot_id": "abc123def456",
                "collection_name": "default",
                "preserve_changes": True,
            }

            response = client.post(
                "/api/v1/versions/snapshots/abc123def456/rollback",
                json=request_data,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["files_merged"]) == 1
            assert len(data["files_restored"]) == 1
            assert len(data["conflicts"]) == 0
            assert data["safety_snapshot_id"] == "safety123"

    def test_rollback_with_conflicts(self, client):
        """Test rollback with conflicts."""
        from skillmeat.models import VersionMergeResult

        mock_mgr = Mock()
        conflict = ConflictMetadata(
            file_path=".claude/skills/pdf/SKILL.md",
            conflict_type="content",
            auto_mergeable=False,
            is_binary=False,
        )

        result = VersionMergeResult(
            success=True,
            files_merged=[],
            files_restored=[],
            conflicts=[conflict],
            pre_merge_snapshot_id="safety123",
        )
        mock_mgr.intelligent_rollback.return_value = result

        with patch(
            "skillmeat.api.routers.versions.get_version_manager", return_value=mock_mgr
        ):
            request_data = {
                "snapshot_id": "abc123def456",
                "preserve_changes": True,
            }

            response = client.post(
                "/api/v1/versions/snapshots/abc123def456/rollback",
                json=request_data,
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["conflicts"]) == 1
            assert data["conflicts"][0]["file_path"] == ".claude/skills/pdf/SKILL.md"
            assert data["conflicts"][0]["conflict_type"] == "content"

    def test_rollback_selective_paths(self, client):
        """Test rollback with selective paths."""
        from skillmeat.models import VersionMergeResult

        mock_mgr = Mock()
        result = VersionMergeResult(
            success=True,
            files_merged=[],
            files_restored=[".claude/skills/pdf/SKILL.md"],
            conflicts=[],
            pre_merge_snapshot_id=None,
        )
        mock_mgr.intelligent_rollback.return_value = result

        with patch(
            "skillmeat.api.routers.versions.get_version_manager", return_value=mock_mgr
        ):
            request_data = {
                "snapshot_id": "abc123def456",
                "preserve_changes": False,
                "selective_paths": [".claude/skills/pdf/"],
            }

            response = client.post(
                "/api/v1/versions/snapshots/abc123def456/rollback",
                json=request_data,
            )

            assert response.status_code == 200
            mock_mgr.intelligent_rollback.assert_called_once()
            call_kwargs = mock_mgr.intelligent_rollback.call_args[1]
            assert call_kwargs["selective_paths"] == [".claude/skills/pdf/"]

    def test_rollback_snapshot_not_found(self, client):
        """Test rollback with non-existent snapshot."""
        mock_mgr = Mock()
        mock_mgr.intelligent_rollback.side_effect = ValueError("Snapshot not found")

        with patch(
            "skillmeat.api.routers.versions.get_version_manager", return_value=mock_mgr
        ):
            request_data = {
                "snapshot_id": "nonexistent",
            }

            response = client.post(
                "/api/v1/versions/snapshots/nonexistent/rollback",
                json=request_data,
            )

            assert response.status_code == 404


# ====================
# Diff Snapshot Tests
# ====================


class TestDiffSnapshots:
    """Test POST /api/v1/versions/snapshots/diff endpoint."""

    def test_diff_snapshots_success(self, client, sample_snapshot, tmp_path):
        """Test successful snapshot diff."""
        from skillmeat.models import DiffResult, FileDiff

        mock_mgr = Mock()
        mock_diff_engine = Mock()

        # Create second snapshot
        snapshot2 = Snapshot(
            id="def789ghi012",
            timestamp=datetime(2025, 12, 17, 13, 0, 0),
            message="Second snapshot",
            collection_name="default",
            tarball_path=tmp_path / "def789ghi012.tar.gz",
            artifact_count=6,
        )

        # Setup tarball paths
        sample_snapshot.tarball_path = tmp_path / "abc123def456.tar.gz"

        # Create mock tarballs
        import tarfile

        for snapshot in [sample_snapshot, snapshot2]:
            with tarfile.open(snapshot.tarball_path, "w:gz") as tar:
                # Add empty directory
                (tmp_path / snapshot.collection_name).mkdir(exist_ok=True)
                tar.add(
                    tmp_path / snapshot.collection_name,
                    arcname=snapshot.collection_name,
                )

        mock_mgr.get_snapshot.side_effect = [sample_snapshot, snapshot2]

        # Mock diff result
        file_diff = FileDiff(
            path=".claude/skills/pdf/SKILL.md",
            status="modified",
            lines_added=10,
            lines_removed=5,
            hunks=[],
        )
        diff_result = DiffResult(
            files_added=[".claude/skills/new/SKILL.md"],
            files_removed=[".claude/skills/old/SKILL.md"],
            files_modified=[file_diff],
            total_lines_added=10,
            total_lines_removed=5,
        )
        mock_diff_engine.diff_directories.return_value = diff_result

        with patch(
            "skillmeat.api.routers.versions.get_version_manager", return_value=mock_mgr
        ):
            with patch(
                "skillmeat.api.routers.versions.get_diff_engine",
                return_value=mock_diff_engine,
            ):
                request_data = {
                    "snapshot_id_1": "abc123def456",
                    "snapshot_id_2": "def789ghi012",
                    "collection_name": "default",
                }

                response = client.post(
                    "/api/v1/versions/snapshots/diff", json=request_data
                )

                assert response.status_code == 200
                data = response.json()
                assert len(data["files_added"]) == 1
                assert len(data["files_removed"]) == 1
                assert len(data["files_modified"]) == 1
                assert data["total_lines_added"] == 10
                assert data["total_lines_removed"] == 5

    def test_diff_first_snapshot_not_found(self, client):
        """Test diff when first snapshot not found."""
        mock_mgr = Mock()
        mock_mgr.get_snapshot.side_effect = [None, Mock()]

        with patch(
            "skillmeat.api.routers.versions.get_version_manager", return_value=mock_mgr
        ):
            request_data = {
                "snapshot_id_1": "nonexistent",
                "snapshot_id_2": "def789ghi012",
            }

            response = client.post("/api/v1/versions/snapshots/diff", json=request_data)

            assert response.status_code == 404
            assert (
                "snapshot 'nonexistent' not found" in response.json()["detail"].lower()
            )

    def test_diff_second_snapshot_not_found(self, client, sample_snapshot):
        """Test diff when second snapshot not found."""
        mock_mgr = Mock()
        mock_mgr.get_snapshot.side_effect = [sample_snapshot, None]

        with patch(
            "skillmeat.api.routers.versions.get_version_manager", return_value=mock_mgr
        ):
            request_data = {
                "snapshot_id_1": "abc123def456",
                "snapshot_id_2": "nonexistent",
            }

            response = client.post("/api/v1/versions/snapshots/diff", json=request_data)

            assert response.status_code == 404
            assert (
                "snapshot 'nonexistent' not found" in response.json()["detail"].lower()
            )
