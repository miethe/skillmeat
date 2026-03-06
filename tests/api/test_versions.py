"""Tests for version management API endpoints.

Covers all routes in skillmeat/api/routers/versions.py:
- GET  /api/v1/versions/snapshots
- GET  /api/v1/versions/snapshots/{snapshot_id}
- POST /api/v1/versions/snapshots
- DELETE /api/v1/versions/snapshots/{snapshot_id}
- GET  /api/v1/versions/snapshots/{snapshot_id}/rollback-analysis
- POST /api/v1/versions/snapshots/{snapshot_id}/rollback
- POST /api/v1/versions/snapshots/diff
"""

import base64
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.routers.versions import get_diff_engine, get_version_manager
from skillmeat.api.server import create_app


@pytest.fixture
def test_settings():
    return APISettings(
        env=Environment.TESTING,
        host="127.0.0.1",
        port=8000,
        log_level="DEBUG",
        api_key_enabled=False,
    )


@pytest.fixture
def app(test_settings):
    from skillmeat.api.config import get_settings

    _app = create_app(test_settings)
    _app.dependency_overrides[get_settings] = lambda: test_settings
    return _app


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


def _make_snapshot(snapshot_id="snap-001", collection_name="default", count=5):
    snap = MagicMock()
    snap.id = snapshot_id
    snap.timestamp = datetime.now(timezone.utc)
    snap.message = "test snapshot"
    snap.collection_name = collection_name
    snap.artifact_count = count
    snap.tarball_path = "/fake/snapshot.tar.gz"
    return snap


def _encode(value: str) -> str:
    return base64.b64encode(value.encode()).decode()


# ---------------------------------------------------------------------------
# GET /api/v1/versions/snapshots
# ---------------------------------------------------------------------------


class TestListSnapshots:
    def test_list_snapshots_success(self, app, client):
        """Returns 200 with paginated snapshot list."""
        snap = _make_snapshot()
        version_mgr = MagicMock()
        version_mgr.list_snapshots.return_value = ([snap], None)

        app.dependency_overrides[get_version_manager] = lambda: version_mgr
        try:
            response = client.get("/api/v1/versions/snapshots")
        finally:
            app.dependency_overrides.pop(get_version_manager, None)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "page_info" in data
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == "snap-001"

    def test_list_snapshots_empty(self, app, client):
        """No snapshots in collection → empty items list."""
        version_mgr = MagicMock()
        version_mgr.list_snapshots.return_value = ([], None)

        app.dependency_overrides[get_version_manager] = lambda: version_mgr
        try:
            response = client.get("/api/v1/versions/snapshots")
        finally:
            app.dependency_overrides.pop(get_version_manager, None)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["items"] == []

    def test_list_snapshots_with_cursor_pagination(self, app, client):
        """Cursor forwarded to version manager for pagination."""
        snap = _make_snapshot()
        next_snap_id = "snap-002"
        version_mgr = MagicMock()
        version_mgr.list_snapshots.return_value = ([snap], next_snap_id)

        cursor = _encode("snap-001")
        app.dependency_overrides[get_version_manager] = lambda: version_mgr
        try:
            response = client.get(f"/api/v1/versions/snapshots?after={cursor}")
        finally:
            app.dependency_overrides.pop(get_version_manager, None)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page_info"]["has_previous_page"] is True
        assert data["page_info"]["has_next_page"] is True

    def test_list_snapshots_invalid_cursor_returns_400(self, client):
        """Malformed base64 cursor → 400 Bad Request."""
        response = client.get("/api/v1/versions/snapshots?after=!!!invalid!!!")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_snapshots_error_returns_500(self, app, client):
        """VersionManager exception → 500."""
        version_mgr = MagicMock()
        version_mgr.list_snapshots.side_effect = RuntimeError("disk error")

        app.dependency_overrides[get_version_manager] = lambda: version_mgr
        try:
            response = client.get("/api/v1/versions/snapshots")
        finally:
            app.dependency_overrides.pop(get_version_manager, None)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_list_snapshots_collection_name_forwarded(self, app, client):
        """collection_name query param is passed to manager."""
        version_mgr = MagicMock()
        version_mgr.list_snapshots.return_value = ([], None)

        app.dependency_overrides[get_version_manager] = lambda: version_mgr
        try:
            response = client.get(
                "/api/v1/versions/snapshots?collection_name=my-collection"
            )
        finally:
            app.dependency_overrides.pop(get_version_manager, None)

        assert response.status_code == status.HTTP_200_OK
        version_mgr.list_snapshots.assert_called_once_with(
            collection_name="my-collection",
            limit=20,
            cursor=None,
        )


# ---------------------------------------------------------------------------
# GET /api/v1/versions/snapshots/{snapshot_id}
# ---------------------------------------------------------------------------


class TestGetSnapshot:
    def test_get_snapshot_success(self, app, client):
        """Known snapshot is returned with 200."""
        snap = _make_snapshot("snap-001")
        version_mgr = MagicMock()
        version_mgr.get_snapshot.return_value = snap

        app.dependency_overrides[get_version_manager] = lambda: version_mgr
        try:
            response = client.get("/api/v1/versions/snapshots/snap-001")
        finally:
            app.dependency_overrides.pop(get_version_manager, None)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == "snap-001"

    def test_get_snapshot_not_found_returns_404(self, app, client):
        """Unknown snapshot → None from manager → 404."""
        version_mgr = MagicMock()
        version_mgr.get_snapshot.return_value = None

        app.dependency_overrides[get_version_manager] = lambda: version_mgr
        try:
            response = client.get("/api/v1/versions/snapshots/ghost-snap")
        finally:
            app.dependency_overrides.pop(get_version_manager, None)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_snapshot_error_returns_500(self, app, client):
        """Manager exception → 500."""
        version_mgr = MagicMock()
        version_mgr.get_snapshot.side_effect = RuntimeError("read error")

        app.dependency_overrides[get_version_manager] = lambda: version_mgr
        try:
            response = client.get("/api/v1/versions/snapshots/snap-001")
        finally:
            app.dependency_overrides.pop(get_version_manager, None)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ---------------------------------------------------------------------------
# POST /api/v1/versions/snapshots
# ---------------------------------------------------------------------------


class TestCreateSnapshot:
    def test_create_snapshot_success(self, app, client):
        """Valid request creates snapshot and returns 201."""
        snap = _make_snapshot("new-snap")
        version_mgr = MagicMock()
        version_mgr.create_snapshot.return_value = snap

        app.dependency_overrides[get_version_manager] = lambda: version_mgr
        try:
            response = client.post(
                "/api/v1/versions/snapshots",
                json={
                    "collection_name": "default",
                    "message": "before upgrade",
                },
            )
        finally:
            app.dependency_overrides.pop(get_version_manager, None)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["created"] is True
        assert data["snapshot"]["id"] == "new-snap"

    def test_create_snapshot_collection_not_found_returns_404(self, app, client):
        """ValueError from manager (collection not found) → 404."""
        version_mgr = MagicMock()
        version_mgr.create_snapshot.side_effect = ValueError(
            "collection 'missing' not found"
        )

        app.dependency_overrides[get_version_manager] = lambda: version_mgr
        try:
            response = client.post(
                "/api/v1/versions/snapshots",
                json={"collection_name": "missing", "message": "test"},
            )
        finally:
            app.dependency_overrides.pop(get_version_manager, None)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_snapshot_error_returns_500(self, app, client):
        """Unexpected manager exception → 500."""
        version_mgr = MagicMock()
        version_mgr.create_snapshot.side_effect = RuntimeError("disk full")

        app.dependency_overrides[get_version_manager] = lambda: version_mgr
        try:
            response = client.post(
                "/api/v1/versions/snapshots",
                json={"collection_name": "default", "message": "test"},
            )
        finally:
            app.dependency_overrides.pop(get_version_manager, None)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ---------------------------------------------------------------------------
# DELETE /api/v1/versions/snapshots/{snapshot_id}
# ---------------------------------------------------------------------------


class TestDeleteSnapshot:
    def test_delete_snapshot_success(self, app, client):
        """Existing snapshot is deleted → 204 No Content."""
        version_mgr = MagicMock()
        version_mgr.delete_snapshot.return_value = None

        app.dependency_overrides[get_version_manager] = lambda: version_mgr
        try:
            response = client.delete("/api/v1/versions/snapshots/snap-001")
        finally:
            app.dependency_overrides.pop(get_version_manager, None)

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_snapshot_not_found_returns_404(self, app, client):
        """ValueError from manager → 404."""
        version_mgr = MagicMock()
        version_mgr.delete_snapshot.side_effect = ValueError("snapshot not found")

        app.dependency_overrides[get_version_manager] = lambda: version_mgr
        try:
            response = client.delete("/api/v1/versions/snapshots/ghost-snap")
        finally:
            app.dependency_overrides.pop(get_version_manager, None)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_snapshot_error_returns_500(self, app, client):
        """Unexpected manager exception → 500."""
        version_mgr = MagicMock()
        version_mgr.delete_snapshot.side_effect = RuntimeError("io error")

        app.dependency_overrides[get_version_manager] = lambda: version_mgr
        try:
            response = client.delete("/api/v1/versions/snapshots/snap-001")
        finally:
            app.dependency_overrides.pop(get_version_manager, None)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ---------------------------------------------------------------------------
# GET /api/v1/versions/snapshots/{snapshot_id}/rollback-analysis
# ---------------------------------------------------------------------------


class TestAnalyzeRollbackSafety:
    def test_analyze_rollback_safety_safe(self, app, client):
        """Safe rollback analysis returns 200 with is_safe=True."""
        analysis = MagicMock()
        analysis.is_safe = True
        analysis.files_with_conflicts = []
        analysis.files_safe_to_restore = ["SKILL.md"]
        analysis.warnings = []

        version_mgr = MagicMock()
        version_mgr.analyze_rollback_safety.return_value = analysis

        app.dependency_overrides[get_version_manager] = lambda: version_mgr
        try:
            response = client.get(
                "/api/v1/versions/snapshots/snap-001/rollback-analysis"
            )
        finally:
            app.dependency_overrides.pop(get_version_manager, None)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_safe"] is True
        assert data["files_with_conflicts"] == []

    def test_analyze_rollback_safety_with_conflicts(self, app, client):
        """Analysis with conflicts returns is_safe=False."""
        analysis = MagicMock()
        analysis.is_safe = False
        analysis.files_with_conflicts = ["commands/test.md"]
        analysis.files_safe_to_restore = []
        analysis.warnings = ["File has local changes"]

        version_mgr = MagicMock()
        version_mgr.analyze_rollback_safety.return_value = analysis

        app.dependency_overrides[get_version_manager] = lambda: version_mgr
        try:
            response = client.get(
                "/api/v1/versions/snapshots/snap-001/rollback-analysis"
            )
        finally:
            app.dependency_overrides.pop(get_version_manager, None)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["is_safe"] is False

    def test_analyze_rollback_safety_snapshot_not_found_returns_404(self, app, client):
        """ValueError from manager → 404."""
        version_mgr = MagicMock()
        version_mgr.analyze_rollback_safety.side_effect = ValueError("not found")

        app.dependency_overrides[get_version_manager] = lambda: version_mgr
        try:
            response = client.get(
                "/api/v1/versions/snapshots/ghost/rollback-analysis"
            )
        finally:
            app.dependency_overrides.pop(get_version_manager, None)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_analyze_rollback_safety_error_returns_500(self, app, client):
        """Unexpected manager exception → 500."""
        version_mgr = MagicMock()
        version_mgr.analyze_rollback_safety.side_effect = RuntimeError("io error")

        app.dependency_overrides[get_version_manager] = lambda: version_mgr
        try:
            response = client.get(
                "/api/v1/versions/snapshots/snap-001/rollback-analysis"
            )
        finally:
            app.dependency_overrides.pop(get_version_manager, None)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ---------------------------------------------------------------------------
# POST /api/v1/versions/snapshots/{snapshot_id}/rollback
# ---------------------------------------------------------------------------


class TestRollback:
    def test_rollback_success(self, app, client):
        """Successful rollback returns 200 with success=True."""
        result = MagicMock()
        result.success = True
        result.files_merged = ["SKILL.md"]
        result.files_restored = ["commands/test.md"]
        result.conflicts = []
        result.safety_snapshot_id = "backup-snap"

        version_mgr = MagicMock()
        version_mgr.intelligent_rollback.return_value = result

        app.dependency_overrides[get_version_manager] = lambda: version_mgr
        try:
            response = client.post(
                "/api/v1/versions/snapshots/snap-001/rollback",
                json={
                    "snapshot_id": "snap-001",
                    "collection_name": "default",
                    "preserve_changes": False,
                    "selective_paths": None,
                },
            )
        finally:
            app.dependency_overrides.pop(get_version_manager, None)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["safety_snapshot_id"] == "backup-snap"

    def test_rollback_with_conflicts(self, app, client):
        """Rollback with conflicts returns 200 with conflicts list populated."""
        conflict = MagicMock()
        conflict.file_path = "commands/cmd.md"
        conflict.conflict_type = "content_conflict"
        conflict.auto_mergeable = False
        conflict.is_binary = False

        result = MagicMock()
        result.success = False
        result.files_merged = []
        result.files_restored = []
        result.conflicts = [conflict]
        result.safety_snapshot_id = None

        version_mgr = MagicMock()
        version_mgr.intelligent_rollback.return_value = result

        app.dependency_overrides[get_version_manager] = lambda: version_mgr
        try:
            response = client.post(
                "/api/v1/versions/snapshots/snap-001/rollback",
                json={
                    "snapshot_id": "snap-001",
                    "collection_name": None,
                    "preserve_changes": True,
                    "selective_paths": None,
                },
            )
        finally:
            app.dependency_overrides.pop(get_version_manager, None)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["conflicts"]) == 1

    def test_rollback_snapshot_not_found_returns_404(self, app, client):
        """ValueError from intelligent_rollback → 404."""
        version_mgr = MagicMock()
        version_mgr.intelligent_rollback.side_effect = ValueError("snapshot not found")

        app.dependency_overrides[get_version_manager] = lambda: version_mgr
        try:
            response = client.post(
                "/api/v1/versions/snapshots/ghost/rollback",
                json={
                    "snapshot_id": "ghost",
                    "collection_name": None,
                    "preserve_changes": False,
                    "selective_paths": None,
                },
            )
        finally:
            app.dependency_overrides.pop(get_version_manager, None)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_rollback_error_returns_500(self, app, client):
        """Unexpected exception from rollback → 500."""
        version_mgr = MagicMock()
        version_mgr.intelligent_rollback.side_effect = RuntimeError("rollback failed")

        app.dependency_overrides[get_version_manager] = lambda: version_mgr
        try:
            response = client.post(
                "/api/v1/versions/snapshots/snap-001/rollback",
                json={
                    "snapshot_id": "snap-001",
                    "collection_name": None,
                    "preserve_changes": False,
                    "selective_paths": None,
                },
            )
        finally:
            app.dependency_overrides.pop(get_version_manager, None)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ---------------------------------------------------------------------------
# POST /api/v1/versions/snapshots/diff
# ---------------------------------------------------------------------------


class TestDiffSnapshots:
    def test_diff_snapshots_success(self, app, client):
        """Diff between two valid snapshots returns 200 with change summary."""
        snap1 = _make_snapshot("snap-001")
        snap2 = _make_snapshot("snap-002")

        diff_result = MagicMock()
        diff_result.files_added = ["agents/new-agent/AGENT.md"]
        diff_result.files_removed = []
        # files_modified is a list of FileDiff objects with .path attribute
        fd = MagicMock()
        fd.path = "SKILL.md"
        diff_result.files_modified = [fd]
        diff_result.total_lines_added = 20
        diff_result.total_lines_removed = 0

        version_mgr = MagicMock()
        version_mgr.get_snapshot.side_effect = lambda sid, coll: (
            snap1 if sid == "snap-001" else snap2
        )

        diff_engine = MagicMock()
        diff_engine.diff_directories.return_value = diff_result

        app.dependency_overrides[get_version_manager] = lambda: version_mgr
        app.dependency_overrides[get_diff_engine] = lambda: diff_engine
        try:
            with patch(
                "skillmeat.api.routers.versions.tempfile.TemporaryDirectory"
            ) as mock_tmpdir_cls, patch(
                "skillmeat.api.routers.versions.tarfile.open"
            ) as mock_tar_open:
                mock_tmpdir = MagicMock()
                mock_tmpdir.__enter__ = MagicMock(return_value="/tmp/fake")
                mock_tmpdir.__exit__ = MagicMock(return_value=False)
                mock_tmpdir_cls.return_value = mock_tmpdir

                mock_tar_ctx = MagicMock()
                mock_tar_ctx.__enter__ = MagicMock(return_value=MagicMock())
                mock_tar_ctx.__exit__ = MagicMock(return_value=False)
                mock_tar_open.return_value = mock_tar_ctx

                response = client.post(
                    "/api/v1/versions/snapshots/diff",
                    json={
                        "snapshot_id_1": "snap-001",
                        "snapshot_id_2": "snap-002",
                        "collection_name": "default",
                    },
                )
        finally:
            app.dependency_overrides.pop(get_version_manager, None)
            app.dependency_overrides.pop(get_diff_engine, None)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "files_added" in data
        assert "files_removed" in data
        assert "files_modified" in data
        assert "total_lines_added" in data

    def test_diff_snapshots_first_not_found_returns_404(self, app, client):
        """First snapshot not found → 404."""
        version_mgr = MagicMock()
        version_mgr.get_snapshot.side_effect = lambda sid, coll: (
            None if sid == "snap-001" else _make_snapshot("snap-002")
        )

        app.dependency_overrides[get_version_manager] = lambda: version_mgr
        app.dependency_overrides[get_diff_engine] = lambda: MagicMock()
        try:
            response = client.post(
                "/api/v1/versions/snapshots/diff",
                json={
                    "snapshot_id_1": "snap-001",
                    "snapshot_id_2": "snap-002",
                    "collection_name": None,
                },
            )
        finally:
            app.dependency_overrides.pop(get_version_manager, None)
            app.dependency_overrides.pop(get_diff_engine, None)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_diff_snapshots_second_not_found_returns_404(self, app, client):
        """Second snapshot not found → 404."""
        version_mgr = MagicMock()
        version_mgr.get_snapshot.side_effect = lambda sid, coll: (
            _make_snapshot("snap-001") if sid == "snap-001" else None
        )

        app.dependency_overrides[get_version_manager] = lambda: version_mgr
        app.dependency_overrides[get_diff_engine] = lambda: MagicMock()
        try:
            response = client.post(
                "/api/v1/versions/snapshots/diff",
                json={
                    "snapshot_id_1": "snap-001",
                    "snapshot_id_2": "snap-002",
                    "collection_name": None,
                },
            )
        finally:
            app.dependency_overrides.pop(get_version_manager, None)
            app.dependency_overrides.pop(get_diff_engine, None)

        assert response.status_code == status.HTTP_404_NOT_FOUND
