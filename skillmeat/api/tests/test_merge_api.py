"""Integration tests for Merge Operation API endpoints.

Tests merge safety analysis, preview, execution, and conflict resolution.
"""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings
from skillmeat.api.server import create_app
from skillmeat.models import ConflictMetadata, MergeSafetyAnalysis, VersionMergeResult


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
def mock_merge_service():
    """Create a mock VersionMergeService."""
    with patch("skillmeat.api.routers.merge.get_version_merge_service") as mock:
        service = Mock()
        mock.return_value = service
        yield service


@pytest.fixture
def sample_conflict():
    """Create a sample conflict for testing."""
    return ConflictMetadata(
        file_path=".claude/skills/pdf/SKILL.md",
        conflict_type="both_modified",
        auto_mergeable=False,
        is_binary=False,
    )


# ====================
# Analyze Merge Tests
# ====================


class TestAnalyzeMerge:
    """Test POST /api/v1/merge/analyze endpoint."""

    def test_analyze_merge_success_no_conflicts(self, client, mock_merge_service):
        """Test merge analysis with no conflicts."""
        analysis = MergeSafetyAnalysis(
            can_auto_merge=True,
            auto_mergeable_count=5,
            conflict_count=0,
            conflicts=[],
            warnings=[],
        )
        mock_merge_service.analyze_merge_safety.return_value = analysis

        request_data = {
            "base_snapshot_id": "snap_base",
            "local_collection": "default",
            "remote_snapshot_id": "snap_remote",
        }

        response = client.post("/api/v1/merge/analyze", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["can_auto_merge"] is True
        assert data["auto_mergeable_count"] == 5
        assert data["conflict_count"] == 0
        assert len(data["conflicts"]) == 0
        assert len(data["warnings"]) == 0

        mock_merge_service.analyze_merge_safety.assert_called_once_with(
            base_snapshot_id="snap_base",
            local_collection="default",
            remote_snapshot_id="snap_remote",
            remote_collection=None,
        )

    def test_analyze_merge_with_conflicts(
        self, client, mock_merge_service, sample_conflict
    ):
        """Test merge analysis with conflicts."""
        analysis = MergeSafetyAnalysis(
            can_auto_merge=False,
            auto_mergeable_count=3,
            conflict_count=2,
            conflicts=[sample_conflict],
            warnings=["Binary file conflict detected"],
        )
        mock_merge_service.analyze_merge_safety.return_value = analysis

        request_data = {
            "base_snapshot_id": "snap_base",
            "local_collection": "default",
            "remote_snapshot_id": "snap_remote",
        }

        response = client.post("/api/v1/merge/analyze", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["can_auto_merge"] is False
        assert data["auto_mergeable_count"] == 3
        assert data["conflict_count"] == 2
        assert len(data["conflicts"]) == 1
        assert data["conflicts"][0]["file_path"] == ".claude/skills/pdf/SKILL.md"
        assert data["conflicts"][0]["conflict_type"] == "both_modified"
        assert data["conflicts"][0]["auto_mergeable"] is False
        assert len(data["warnings"]) == 1

    def test_analyze_merge_with_remote_collection(self, client, mock_merge_service):
        """Test merge analysis with remote collection specified."""
        analysis = MergeSafetyAnalysis(
            can_auto_merge=True,
            auto_mergeable_count=0,
            conflict_count=0,
            conflicts=[],
            warnings=[],
        )
        mock_merge_service.analyze_merge_safety.return_value = analysis

        request_data = {
            "base_snapshot_id": "snap_base",
            "local_collection": "default",
            "remote_snapshot_id": "snap_remote",
            "remote_collection": "upstream",
        }

        response = client.post("/api/v1/merge/analyze", json=request_data)

        assert response.status_code == 200
        mock_merge_service.analyze_merge_safety.assert_called_once_with(
            base_snapshot_id="snap_base",
            local_collection="default",
            remote_snapshot_id="snap_remote",
            remote_collection="upstream",
        )

    def test_analyze_merge_snapshot_not_found(self, client, mock_merge_service):
        """Test merge analysis with non-existent snapshot."""
        mock_merge_service.analyze_merge_safety.side_effect = ValueError(
            "Snapshot 'snap_base' not found"
        )

        request_data = {
            "base_snapshot_id": "snap_base",
            "local_collection": "default",
            "remote_snapshot_id": "snap_remote",
        }

        response = client.post("/api/v1/merge/analyze", json=request_data)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_analyze_merge_collection_not_found(self, client, mock_merge_service):
        """Test merge analysis with non-existent collection."""
        mock_merge_service.analyze_merge_safety.side_effect = ValueError(
            "Collection 'nonexistent' not found"
        )

        request_data = {
            "base_snapshot_id": "snap_base",
            "local_collection": "nonexistent",
            "remote_snapshot_id": "snap_remote",
        }

        response = client.post("/api/v1/merge/analyze", json=request_data)

        assert response.status_code == 404

    def test_analyze_merge_internal_error(self, client, mock_merge_service):
        """Test merge analysis with internal error."""
        mock_merge_service.analyze_merge_safety.side_effect = Exception(
            "Unexpected error"
        )

        request_data = {
            "base_snapshot_id": "snap_base",
            "local_collection": "default",
            "remote_snapshot_id": "snap_remote",
        }

        response = client.post("/api/v1/merge/analyze", json=request_data)

        assert response.status_code == 500
        assert "failed to analyze merge" in response.json()["detail"].lower()


# ====================
# Preview Merge Tests
# ====================


class TestPreviewMerge:
    """Test POST /api/v1/merge/preview endpoint."""

    def test_preview_merge_success(self, client, mock_merge_service):
        """Test merge preview with changes."""
        from skillmeat.models import MergePreviewResult

        preview = MergePreviewResult(
            files_added=[".claude/skills/new/SKILL.md"],
            files_removed=[".claude/skills/old/SKILL.md"],
            files_changed=[
                ".claude/skills/pdf/SKILL.md",
                ".claude/skills/canvas/main.py",
            ],
            potential_conflicts=[],
            can_auto_merge=True,
        )
        mock_merge_service.get_merge_preview.return_value = preview

        request_data = {
            "base_snapshot_id": "snap_base",
            "local_collection": "default",
            "remote_snapshot_id": "snap_remote",
        }

        response = client.post("/api/v1/merge/preview", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert len(data["files_added"]) == 1
        assert len(data["files_removed"]) == 1
        assert len(data["files_changed"]) == 2
        assert len(data["potential_conflicts"]) == 0
        assert data["can_auto_merge"] is True

    def test_preview_merge_with_conflicts(
        self, client, mock_merge_service, sample_conflict
    ):
        """Test merge preview with potential conflicts."""
        from skillmeat.models import MergePreviewResult

        preview = MergePreviewResult(
            files_added=[],
            files_removed=[],
            files_changed=[".claude/skills/pdf/SKILL.md"],
            potential_conflicts=[sample_conflict],
            can_auto_merge=False,
        )
        mock_merge_service.get_merge_preview.return_value = preview

        request_data = {
            "base_snapshot_id": "snap_base",
            "local_collection": "default",
            "remote_snapshot_id": "snap_remote",
        }

        response = client.post("/api/v1/merge/preview", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert len(data["potential_conflicts"]) == 1
        assert (
            data["potential_conflicts"][0]["file_path"] == ".claude/skills/pdf/SKILL.md"
        )
        assert data["can_auto_merge"] is False

    def test_preview_merge_no_changes(self, client, mock_merge_service):
        """Test merge preview with no changes."""
        from skillmeat.models import MergePreviewResult

        preview = MergePreviewResult(
            files_added=[],
            files_removed=[],
            files_changed=[],
            potential_conflicts=[],
            can_auto_merge=True,
        )
        mock_merge_service.get_merge_preview.return_value = preview

        request_data = {
            "base_snapshot_id": "snap_base",
            "local_collection": "default",
            "remote_snapshot_id": "snap_remote",
        }

        response = client.post("/api/v1/merge/preview", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert len(data["files_added"]) == 0
        assert len(data["files_removed"]) == 0
        assert len(data["files_changed"]) == 0

    def test_preview_merge_snapshot_not_found(self, client, mock_merge_service):
        """Test merge preview with non-existent snapshot."""
        mock_merge_service.get_merge_preview.side_effect = ValueError(
            "Snapshot not found"
        )

        request_data = {
            "base_snapshot_id": "nonexistent",
            "local_collection": "default",
            "remote_snapshot_id": "snap_remote",
        }

        response = client.post("/api/v1/merge/preview", json=request_data)

        assert response.status_code == 404

    def test_preview_merge_internal_error(self, client, mock_merge_service):
        """Test merge preview with internal error."""
        mock_merge_service.get_merge_preview.side_effect = Exception("IO error")

        request_data = {
            "base_snapshot_id": "snap_base",
            "local_collection": "default",
            "remote_snapshot_id": "snap_remote",
        }

        response = client.post("/api/v1/merge/preview", json=request_data)

        assert response.status_code == 500
        assert "failed to generate merge preview" in response.json()["detail"].lower()


# ====================
# Execute Merge Tests
# ====================


class TestExecuteMerge:
    """Test POST /api/v1/merge/execute endpoint."""

    def test_execute_merge_success(self, client, mock_merge_service):
        """Test successful merge execution."""
        result = VersionMergeResult(
            success=True,
            files_merged=[
                ".claude/skills/pdf/SKILL.md",
                ".claude/skills/canvas/main.py",
            ],
            conflicts=[],
            pre_merge_snapshot_id="snap_safety",
            error=None,
        )
        mock_merge_service.merge_with_conflict_detection.return_value = result

        request_data = {
            "base_snapshot_id": "snap_base",
            "local_collection": "default",
            "remote_snapshot_id": "snap_remote",
            "auto_snapshot": True,
        }

        response = client.post("/api/v1/merge/execute", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["files_merged"]) == 2
        assert len(data["conflicts"]) == 0
        assert data["pre_merge_snapshot_id"] == "snap_safety"
        assert data["error"] is None

        mock_merge_service.merge_with_conflict_detection.assert_called_once_with(
            base_snapshot_id="snap_base",
            local_collection="default",
            remote_snapshot_id="snap_remote",
            remote_collection=None,
            auto_snapshot=True,
        )

    def test_execute_merge_with_conflicts(
        self, client, mock_merge_service, sample_conflict
    ):
        """Test merge execution with unresolved conflicts."""
        result = VersionMergeResult(
            success=False,
            files_merged=[],
            conflicts=[sample_conflict],
            pre_merge_snapshot_id="snap_safety",
            error=None,
        )
        mock_merge_service.merge_with_conflict_detection.return_value = result

        request_data = {
            "base_snapshot_id": "snap_base",
            "local_collection": "default",
            "remote_snapshot_id": "snap_remote",
        }

        response = client.post("/api/v1/merge/execute", json=request_data)

        # Should return 409 Conflict when there are unresolved conflicts
        assert response.status_code == 409
        assert "unresolved conflicts" in response.json()["detail"].lower()

    def test_execute_merge_without_auto_snapshot(self, client, mock_merge_service):
        """Test merge execution without automatic snapshot."""
        result = VersionMergeResult(
            success=True,
            files_merged=[".claude/skills/pdf/SKILL.md"],
            conflicts=[],
            pre_merge_snapshot_id=None,
            error=None,
        )
        mock_merge_service.merge_with_conflict_detection.return_value = result

        request_data = {
            "base_snapshot_id": "snap_base",
            "local_collection": "default",
            "remote_snapshot_id": "snap_remote",
            "auto_snapshot": False,
        }

        response = client.post("/api/v1/merge/execute", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["pre_merge_snapshot_id"] is None

        mock_merge_service.merge_with_conflict_detection.assert_called_once()
        call_kwargs = mock_merge_service.merge_with_conflict_detection.call_args[1]
        assert call_kwargs["auto_snapshot"] is False

    def test_execute_merge_with_remote_collection(self, client, mock_merge_service):
        """Test merge execution with remote collection."""
        result = VersionMergeResult(
            success=True,
            files_merged=[],
            conflicts=[],
            pre_merge_snapshot_id="snap_safety",
            error=None,
        )
        mock_merge_service.merge_with_conflict_detection.return_value = result

        request_data = {
            "base_snapshot_id": "snap_base",
            "local_collection": "default",
            "remote_snapshot_id": "snap_remote",
            "remote_collection": "upstream",
        }

        response = client.post("/api/v1/merge/execute", json=request_data)

        assert response.status_code == 200
        mock_merge_service.merge_with_conflict_detection.assert_called_once()
        call_kwargs = mock_merge_service.merge_with_conflict_detection.call_args[1]
        assert call_kwargs["remote_collection"] == "upstream"

    def test_execute_merge_snapshot_not_found(self, client, mock_merge_service):
        """Test merge execution with non-existent snapshot."""
        mock_merge_service.merge_with_conflict_detection.side_effect = ValueError(
            "Snapshot not found"
        )

        request_data = {
            "base_snapshot_id": "nonexistent",
            "local_collection": "default",
            "remote_snapshot_id": "snap_remote",
        }

        response = client.post("/api/v1/merge/execute", json=request_data)

        assert response.status_code == 404

    def test_execute_merge_internal_error(self, client, mock_merge_service):
        """Test merge execution with internal error."""
        mock_merge_service.merge_with_conflict_detection.side_effect = Exception(
            "Disk full"
        )

        request_data = {
            "base_snapshot_id": "snap_base",
            "local_collection": "default",
            "remote_snapshot_id": "snap_remote",
        }

        response = client.post("/api/v1/merge/execute", json=request_data)

        assert response.status_code == 500
        assert "failed to execute merge" in response.json()["detail"].lower()

    def test_execute_merge_with_error_message(self, client, mock_merge_service):
        """Test merge execution that returns error message."""
        result = VersionMergeResult(
            success=False,
            files_merged=[],
            conflicts=[],
            pre_merge_snapshot_id=None,
            error="Base snapshot not found",
        )
        mock_merge_service.merge_with_conflict_detection.return_value = result

        request_data = {
            "base_snapshot_id": "snap_base",
            "local_collection": "default",
            "remote_snapshot_id": "snap_remote",
        }

        response = client.post("/api/v1/merge/execute", json=request_data)

        # Success=False but no conflicts means HTTP 200 with error field
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error"] == "Base snapshot not found"


# ====================
# Resolve Conflict Tests
# ====================


class TestResolveConflict:
    """Test POST /api/v1/merge/resolve endpoint."""

    def test_resolve_conflict_use_local(self, client, mock_merge_service):
        """Test resolving conflict with use_local strategy."""
        mock_merge_service.resolve_conflict.return_value = True

        request_data = {
            "file_path": ".claude/skills/pdf/SKILL.md",
            "resolution": "use_local",
        }

        response = client.post("/api/v1/merge/resolve", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["file_path"] == ".claude/skills/pdf/SKILL.md"
        assert data["resolution_applied"] == "use_local"

        mock_merge_service.resolve_conflict.assert_called_once()

    def test_resolve_conflict_use_remote(self, client, mock_merge_service):
        """Test resolving conflict with use_remote strategy."""
        mock_merge_service.resolve_conflict.return_value = True

        request_data = {
            "file_path": ".claude/skills/pdf/SKILL.md",
            "resolution": "use_remote",
        }

        response = client.post("/api/v1/merge/resolve", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["resolution_applied"] == "use_remote"

    def test_resolve_conflict_use_base(self, client, mock_merge_service):
        """Test resolving conflict with use_base strategy."""
        mock_merge_service.resolve_conflict.return_value = True

        request_data = {
            "file_path": ".claude/skills/pdf/SKILL.md",
            "resolution": "use_base",
        }

        response = client.post("/api/v1/merge/resolve", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["resolution_applied"] == "use_base"

    def test_resolve_conflict_custom_content(self, client, mock_merge_service):
        """Test resolving conflict with custom content."""
        mock_merge_service.resolve_conflict.return_value = True

        request_data = {
            "file_path": ".claude/skills/pdf/SKILL.md",
            "resolution": "custom",
            "custom_content": "# Manually merged content\nCombined changes...",
        }

        response = client.post("/api/v1/merge/resolve", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["resolution_applied"] == "custom"

        mock_merge_service.resolve_conflict.assert_called_once()
        call_kwargs = mock_merge_service.resolve_conflict.call_args[1]
        assert (
            call_kwargs["custom_content"]
            == "# Manually merged content\nCombined changes..."
        )

    def test_resolve_conflict_custom_without_content(self, client, mock_merge_service):
        """Test resolving conflict with custom but no content provided."""
        request_data = {
            "file_path": ".claude/skills/pdf/SKILL.md",
            "resolution": "custom",
            # Missing custom_content
        }

        response = client.post("/api/v1/merge/resolve", json=request_data)

        assert response.status_code == 422
        assert "custom_content required" in response.json()["detail"].lower()

    def test_resolve_conflict_invalid_resolution(self, client, mock_merge_service):
        """Test resolving conflict with invalid resolution strategy."""
        request_data = {
            "file_path": ".claude/skills/pdf/SKILL.md",
            "resolution": "invalid_strategy",
        }

        response = client.post("/api/v1/merge/resolve", json=request_data)

        # Pydantic validation error for invalid Literal value
        assert response.status_code == 422

    def test_resolve_conflict_failure(self, client, mock_merge_service):
        """Test conflict resolution failure."""
        mock_merge_service.resolve_conflict.return_value = False

        request_data = {
            "file_path": ".claude/skills/pdf/SKILL.md",
            "resolution": "use_local",
        }

        response = client.post("/api/v1/merge/resolve", json=request_data)

        assert response.status_code == 500
        assert "failed to resolve conflict" in response.json()["detail"].lower()

    def test_resolve_conflict_invalid_parameters(self, client, mock_merge_service):
        """Test conflict resolution with invalid parameters."""
        mock_merge_service.resolve_conflict.side_effect = ValueError(
            "Invalid file path"
        )

        request_data = {
            "file_path": "../../../etc/passwd",
            "resolution": "use_local",
        }

        response = client.post("/api/v1/merge/resolve", json=request_data)

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_resolve_conflict_internal_error(self, client, mock_merge_service):
        """Test conflict resolution with internal error."""
        mock_merge_service.resolve_conflict.side_effect = Exception("IO error")

        request_data = {
            "file_path": ".claude/skills/pdf/SKILL.md",
            "resolution": "use_local",
        }

        response = client.post("/api/v1/merge/resolve", json=request_data)

        assert response.status_code == 500
        assert "failed to resolve conflict" in response.json()["detail"].lower()


# ====================
# Integration Tests
# ====================


class TestMergeWorkflow:
    """Test complete merge workflow scenarios."""

    def test_full_merge_workflow_success(self, client, mock_merge_service):
        """Test complete merge workflow from analysis to execution."""
        from skillmeat.models import MergePreviewResult

        # Step 1: Analyze merge safety
        analysis = MergeSafetyAnalysis(
            can_auto_merge=True,
            auto_mergeable_count=5,
            conflict_count=0,
            conflicts=[],
            warnings=[],
        )
        mock_merge_service.analyze_merge_safety.return_value = analysis

        response = client.post(
            "/api/v1/merge/analyze",
            json={
                "base_snapshot_id": "snap_base",
                "local_collection": "default",
                "remote_snapshot_id": "snap_remote",
            },
        )
        assert response.status_code == 200
        assert response.json()["can_auto_merge"] is True

        # Step 2: Preview merge
        preview = MergePreviewResult(
            files_added=["new.py"],
            files_removed=["old.py"],
            files_changed=["SKILL.md"],
            potential_conflicts=[],
            can_auto_merge=True,
        )
        mock_merge_service.get_merge_preview.return_value = preview

        response = client.post(
            "/api/v1/merge/preview",
            json={
                "base_snapshot_id": "snap_base",
                "local_collection": "default",
                "remote_snapshot_id": "snap_remote",
            },
        )
        assert response.status_code == 200

        # Step 3: Execute merge
        result = VersionMergeResult(
            success=True,
            files_merged=["SKILL.md"],
            conflicts=[],
            pre_merge_snapshot_id="snap_safety",
            error=None,
        )
        mock_merge_service.merge_with_conflict_detection.return_value = result

        response = client.post(
            "/api/v1/merge/execute",
            json={
                "base_snapshot_id": "snap_base",
                "local_collection": "default",
                "remote_snapshot_id": "snap_remote",
                "auto_snapshot": True,
            },
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_merge_workflow_with_conflict_resolution(
        self, client, mock_merge_service, sample_conflict
    ):
        """Test merge workflow with conflict detection and resolution."""
        from skillmeat.models import MergePreviewResult

        # Step 1: Analyze - detect conflicts
        analysis = MergeSafetyAnalysis(
            can_auto_merge=False,
            auto_mergeable_count=3,
            conflict_count=1,
            conflicts=[sample_conflict],
            warnings=[],
        )
        mock_merge_service.analyze_merge_safety.return_value = analysis

        response = client.post(
            "/api/v1/merge/analyze",
            json={
                "base_snapshot_id": "snap_base",
                "local_collection": "default",
                "remote_snapshot_id": "snap_remote",
            },
        )
        assert response.status_code == 200
        assert response.json()["can_auto_merge"] is False
        assert len(response.json()["conflicts"]) == 1

        # Step 2: Try to execute - should fail with conflicts
        result = VersionMergeResult(
            success=False,
            files_merged=[],
            conflicts=[sample_conflict],
            pre_merge_snapshot_id="snap_safety",
            error=None,
        )
        mock_merge_service.merge_with_conflict_detection.return_value = result

        response = client.post(
            "/api/v1/merge/execute",
            json={
                "base_snapshot_id": "snap_base",
                "local_collection": "default",
                "remote_snapshot_id": "snap_remote",
            },
        )
        assert response.status_code == 409

        # Step 3: Resolve conflict
        mock_merge_service.resolve_conflict.return_value = True

        response = client.post(
            "/api/v1/merge/resolve",
            json={
                "file_path": ".claude/skills/pdf/SKILL.md",
                "resolution": "use_local",
            },
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
