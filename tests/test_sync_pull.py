"""Tests for sync pull functionality.

Tests the SyncManager.sync_from_project() method and associated
sync strategies (overwrite, merge, fork).
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from skillmeat.core.sync import SyncManager
from skillmeat.models import (
    SyncResult,
    ArtifactSyncResult,
    DriftDetectionResult,
    DeploymentMetadata,
    DeploymentRecord,
)


class TestSyncFromProject:
    """Tests for sync_from_project method."""

    def test_sync_from_project_invalid_path(self, tmp_path):
        """Test sync_from_project raises error for invalid path."""
        sync_mgr = SyncManager()

        invalid_path = tmp_path / "nonexistent"

        with pytest.raises(ValueError, match="Project path does not exist"):
            sync_mgr.sync_from_project(invalid_path)

    def test_sync_from_project_invalid_strategy(self, tmp_path):
        """Test sync_from_project raises error for invalid strategy."""
        sync_mgr = SyncManager()
        project_path = tmp_path / "project"
        project_path.mkdir()

        with pytest.raises(ValueError, match="Invalid strategy"):
            sync_mgr.sync_from_project(project_path, strategy="invalid")

    def test_sync_from_project_no_drift(self, tmp_path):
        """Test sync_from_project with no drift detected."""
        sync_mgr = SyncManager()
        project_path = tmp_path / "project"
        project_path.mkdir()

        # Mock check_drift to return empty list
        with patch.object(sync_mgr, "check_drift", return_value=[]):
            result = sync_mgr.sync_from_project(project_path)

        assert result.status == "no_changes"
        assert len(result.artifacts_synced) == 0
        assert "No artifacts to pull" in result.message

    def test_sync_from_project_dry_run(self, tmp_path):
        """Test sync_from_project with dry-run mode."""
        sync_mgr = SyncManager()
        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".claude").mkdir()
        (project_path / ".claude" / "skills" / "test-skill").mkdir(parents=True)

        # Create mock drift (project_sha is the deployed SHA, collection has different SHA)
        drift = DriftDetectionResult(
            artifact_name="test-skill",
            artifact_type="skill",
            drift_type="modified",
            collection_sha="abc123",
            project_sha="def456",  # Deployed SHA
            recommendation="pull_from_project",
        )

        # Mock methods
        with patch.object(sync_mgr, "check_drift", return_value=[drift]):
            # Return path that exists
            artifact_path = project_path / ".claude" / "skills" / "test-skill"
            with patch.object(
                sync_mgr, "_get_project_artifact_path", return_value=artifact_path
            ):
                # Current project SHA differs from deployed SHA (local modifications)
                with patch.object(
                    sync_mgr, "_compute_artifact_hash", return_value="xyz789"
                ):
                    result = sync_mgr.sync_from_project(project_path, dry_run=True)

        assert result.status == "dry_run"
        assert "test-skill" in result.artifacts_synced
        assert "Would sync 1" in result.message

    def test_sync_from_project_cancelled(self, tmp_path):
        """Test sync_from_project when user cancels."""
        sync_mgr = SyncManager()
        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".claude").mkdir()
        (project_path / ".claude" / "skills" / "test-skill").mkdir(parents=True)

        # Create mock drift
        drift = DriftDetectionResult(
            artifact_name="test-skill",
            artifact_type="skill",
            drift_type="modified",
            collection_sha="abc123",
            project_sha="def456",
            recommendation="pull_from_project",
        )

        # Mock methods
        with patch.object(sync_mgr, "check_drift", return_value=[drift]):
            artifact_path = project_path / ".claude" / "skills" / "test-skill"
            with patch.object(
                sync_mgr, "_get_project_artifact_path", return_value=artifact_path
            ):
                with patch.object(
                    sync_mgr, "_compute_artifact_hash", return_value="xyz789"
                ):
                    with patch.object(sync_mgr, "_show_sync_preview"):
                        with patch.object(
                            sync_mgr, "_confirm_sync", return_value=False
                        ):
                            result = sync_mgr.sync_from_project(project_path)

        assert result.status == "cancelled"
        assert len(result.artifacts_synced) == 0
        assert "cancelled by user" in result.message

    def test_sync_from_project_artifact_filtering(self, tmp_path):
        """Test sync_from_project with artifact name filtering."""
        sync_mgr = SyncManager()
        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".claude" / "skills" / "skill1").mkdir(parents=True)
        (project_path / ".claude" / "skills" / "skill2").mkdir(parents=True)

        # Create mock drifts for multiple artifacts
        drift1 = DriftDetectionResult(
            artifact_name="skill1",
            artifact_type="skill",
            drift_type="modified",
            collection_sha="abc123",
            project_sha="def456",
        )
        drift2 = DriftDetectionResult(
            artifact_name="skill2",
            artifact_type="skill",
            drift_type="modified",
            collection_sha="ghi789",
            project_sha="jkl012",
        )

        # Create a mock that returns the right path based on artifact name
        def mock_get_path(path, name, type):
            return path / ".claude" / "skills" / name

        # Mock check_drift to return both drifts
        with patch.object(sync_mgr, "check_drift", return_value=[drift1, drift2]):
            with patch.object(
                sync_mgr, "_get_project_artifact_path", side_effect=mock_get_path
            ):
                with patch.object(
                    sync_mgr, "_compute_artifact_hash", return_value="xyz789"
                ):
                    result = sync_mgr.sync_from_project(
                        project_path, artifact_names=["skill1"], dry_run=True
                    )

        # Should only include skill1
        assert len(result.artifacts_synced) == 1
        assert "skill1" in result.artifacts_synced


class TestSyncStrategies:
    """Tests for sync strategies (overwrite, merge, fork)."""

    def test_sync_overwrite_strategy(self, tmp_path):
        """Test overwrite strategy replaces collection artifact."""
        sync_mgr = SyncManager()

        # Create project and collection artifacts
        project_path = tmp_path / "project" / "artifact"
        collection_path = tmp_path / "collection" / "artifact"

        project_path.mkdir(parents=True)
        collection_path.mkdir(parents=True)

        # Add files to both
        (project_path / "file1.txt").write_text("project content")
        (collection_path / "old_file.txt").write_text("old content")

        # Execute overwrite
        sync_mgr._sync_overwrite(project_path, collection_path)

        # Verify collection was replaced
        assert (collection_path / "file1.txt").exists()
        assert not (collection_path / "old_file.txt").exists()
        assert (collection_path / "file1.txt").read_text() == "project content"

    def test_sync_merge_strategy(self, tmp_path):
        """Test merge strategy merges changes."""
        sync_mgr = SyncManager()

        # Create project and collection artifacts
        project_path = tmp_path / "project" / "artifact"
        collection_path = tmp_path / "collection" / "artifact"

        project_path.mkdir(parents=True)
        collection_path.mkdir(parents=True)

        # Add files
        (project_path / "file1.txt").write_text("project content")
        (collection_path / "file1.txt").write_text("collection content")

        # Execute merge
        result = sync_mgr._sync_merge(project_path, collection_path, "test-artifact")

        # Verify result
        assert isinstance(result, ArtifactSyncResult)
        assert result.artifact_name == "test-artifact"

    def test_sync_merge_with_conflicts(self, tmp_path):
        """Test merge strategy with conflicts."""
        from skillmeat.core.merge_engine import MergeEngine
        from skillmeat.models import MergeResult, MergeStats, ConflictMetadata

        sync_mgr = SyncManager()

        # Create project and collection artifacts with conflicting changes
        project_path = tmp_path / "project" / "artifact"
        collection_path = tmp_path / "collection" / "artifact"

        project_path.mkdir(parents=True)
        collection_path.mkdir(parents=True)

        # Add conflicting files
        (project_path / "file1.txt").write_text("project version\nline 2\nline 3")
        (collection_path / "file1.txt").write_text("collection version\nline 2\nline 3")

        # Mock MergeEngine to return conflicts
        mock_conflict = ConflictMetadata(
            file_path="file1.txt",
            conflict_type="both_modified",
            base_content="base content",
            local_content="local content",
            remote_content="remote content",
            auto_mergeable=False,
        )
        mock_merge_result = MergeResult(
            success=False,
            conflicts=[mock_conflict],
            stats=MergeStats(total_files=1, conflicts=1),
        )

        with patch.object(MergeEngine, "merge", return_value=mock_merge_result):
            result = sync_mgr._sync_merge(
                project_path, collection_path, "test-artifact"
            )

        assert result.has_conflict
        assert "file1.txt" in result.conflict_files

    def test_sync_fork_strategy(self, tmp_path):
        """Test fork strategy creates new artifact."""
        sync_mgr = SyncManager()

        # Create project artifact
        project_path = tmp_path / "project" / "artifact"
        collection_path = tmp_path / "collection"

        project_path.mkdir(parents=True)
        (collection_path / "skills").mkdir(parents=True)

        (project_path / "file1.txt").write_text("content")

        # Execute fork
        forked_path = sync_mgr._sync_fork(
            project_path, collection_path, "test-artifact", "skill"
        )

        # Verify fork was created
        assert forked_path.exists()
        assert forked_path.name == "test-artifact-fork"
        assert (forked_path / "file1.txt").exists()


class TestSyncHelpers:
    """Tests for sync helper methods."""

    def test_get_project_artifact_path(self, tmp_path):
        """Test _get_project_artifact_path finds artifact."""
        sync_mgr = SyncManager()

        # Create project structure
        project_path = tmp_path / "project"
        (project_path / ".claude" / "skills" / "my-skill").mkdir(parents=True)

        result = sync_mgr._get_project_artifact_path(project_path, "my-skill", "skill")

        assert result is not None
        assert result.name == "my-skill"

    def test_get_project_artifact_path_not_found(self, tmp_path):
        """Test _get_project_artifact_path returns None if not found."""
        sync_mgr = SyncManager()

        project_path = tmp_path / "project"
        project_path.mkdir()

        result = sync_mgr._get_project_artifact_path(
            project_path, "nonexistent", "skill"
        )

        assert result is None

    def test_show_sync_preview(self, tmp_path, capsys):
        """Test _show_sync_preview displays preview."""
        sync_mgr = SyncManager()

        drift = DriftDetectionResult(
            artifact_name="test-skill",
            artifact_type="skill",
            drift_type="modified",
            collection_sha="abc123",
            project_sha="def456",
        )

        # Mock Rich console (imported inside the method)
        with patch("rich.console.Console") as MockConsole:
            mock_console = MockConsole.return_value
            sync_mgr._show_sync_preview([drift], "overwrite")

            # Verify preview was shown
            assert mock_console.print.called

    def test_confirm_sync_accepted(self):
        """Test _confirm_sync returns True when confirmed."""
        sync_mgr = SyncManager()

        with patch("rich.prompt.Confirm") as MockConfirm:
            MockConfirm.ask.return_value = True
            result = sync_mgr._confirm_sync()

        assert result is True

    def test_confirm_sync_rejected(self):
        """Test _confirm_sync returns False when rejected."""
        sync_mgr = SyncManager()

        with patch("rich.prompt.Confirm") as MockConfirm:
            MockConfirm.ask.return_value = False
            result = sync_mgr._confirm_sync()

        assert result is False

    def test_record_sync_event(self, caplog):
        """Test _record_sync_event logs event."""
        import logging

        sync_mgr = SyncManager()

        with caplog.at_level(logging.INFO):
            sync_mgr._record_sync_event("pull", ["skill1", "skill2"])

        assert "Sync pull: 2 artifacts" in caplog.text


class TestSyncArtifact:
    """Tests for _sync_artifact method."""

    def test_sync_artifact_not_found(self, tmp_path):
        """Test _sync_artifact when artifact not found in project."""
        sync_mgr = SyncManager()

        project_path = tmp_path / "project"
        project_path.mkdir()

        drift = DriftDetectionResult(
            artifact_name="missing",
            artifact_type="skill",
            drift_type="modified",
        )

        result = sync_mgr._sync_artifact(project_path, drift, "overwrite", True)

        assert not result.success
        assert "not found" in result.error

    def test_sync_artifact_no_collection_manager(self, tmp_path):
        """Test _sync_artifact without collection manager."""
        sync_mgr = SyncManager(collection_manager=None)

        project_path = tmp_path / "project"
        (project_path / ".claude" / "skills" / "test").mkdir(parents=True)

        drift = DriftDetectionResult(
            artifact_name="test",
            artifact_type="skill",
            drift_type="modified",
        )

        with patch.object(
            sync_mgr,
            "_get_project_artifact_path",
            return_value=project_path / ".claude" / "skills" / "test",
        ):
            result = sync_mgr._sync_artifact(project_path, drift, "overwrite", True)

        assert not result.success
        assert "Collection manager not available" in result.error

    def test_sync_artifact_skip_strategy(self, tmp_path):
        """Test _sync_artifact with skip in prompt mode."""
        collection_mgr = Mock()
        collection_mgr.get_collection.return_value = Mock(path=tmp_path / "collection")
        sync_mgr = SyncManager(collection_manager=collection_mgr)

        project_path = tmp_path / "project"
        (project_path / ".claude" / "skills" / "test").mkdir(parents=True)
        (tmp_path / "collection" / "skills").mkdir(parents=True)

        drift = DriftDetectionResult(
            artifact_name="test",
            artifact_type="skill",
            drift_type="modified",
        )

        # Mock prompts to return skip
        with patch.object(
            sync_mgr,
            "_get_project_artifact_path",
            return_value=project_path / ".claude" / "skills" / "test",
        ):
            with patch.object(sync_mgr, "_load_deployment_metadata", return_value=None):
                with patch("rich.console.Console"):
                    with patch("rich.prompt.Prompt") as MockPrompt:
                        MockPrompt.ask.return_value = "4"  # Skip
                        result = sync_mgr._sync_artifact(
                            project_path, drift, "prompt", True
                        )

        assert not result.success
        assert "Skipped by user" in result.error


class TestDataModels:
    """Tests for SyncResult and ArtifactSyncResult data models."""

    def test_sync_result_creation(self):
        """Test SyncResult creation."""
        result = SyncResult(
            status="success",
            artifacts_synced=["skill1", "skill2"],
            message="Synced 2 artifacts",
        )

        assert result.status == "success"
        assert len(result.artifacts_synced) == 2
        assert result.message == "Synced 2 artifacts"

    def test_sync_result_validation(self):
        """Test SyncResult validates status."""
        with pytest.raises(ValueError, match="Invalid status"):
            SyncResult(status="invalid")

    def test_artifact_sync_result_creation(self):
        """Test ArtifactSyncResult creation."""
        result = ArtifactSyncResult(
            artifact_name="test-skill",
            success=True,
            has_conflict=False,
        )

        assert result.artifact_name == "test-skill"
        assert result.success is True
        assert result.has_conflict is False

    def test_artifact_sync_result_with_conflicts(self):
        """Test ArtifactSyncResult with conflicts."""
        result = ArtifactSyncResult(
            artifact_name="test-skill",
            success=True,
            has_conflict=True,
            conflict_files=["file1.txt", "file2.txt"],
        )

        assert result.has_conflict is True
        assert len(result.conflict_files) == 2


class TestIntegration:
    """Integration tests for complete sync flow."""

    def test_complete_sync_flow_overwrite(self, tmp_path):
        """Test complete sync flow with overwrite strategy."""
        # Create mock collection manager
        collection_mgr = Mock()
        mock_collection = Mock()
        mock_collection.path = tmp_path / "collection"
        collection_mgr.get_collection.return_value = mock_collection

        # Create sync manager
        sync_mgr = SyncManager(collection_manager=collection_mgr)

        # Create project structure
        project_path = tmp_path / "project"
        (project_path / ".claude" / "skills" / "test-skill").mkdir(parents=True)
        (project_path / ".claude" / "skills" / "test-skill" / "file.txt").write_text(
            "project content"
        )

        # Create collection structure
        (tmp_path / "collection" / "skills" / "test-skill").mkdir(parents=True)
        (tmp_path / "collection" / "skills" / "test-skill" / "old.txt").write_text(
            "old content"
        )

        # Mock methods
        drift = DriftDetectionResult(
            artifact_name="test-skill",
            artifact_type="skill",
            drift_type="modified",
            collection_sha="abc123",
            project_sha="def456",
        )

        with patch.object(sync_mgr, "check_drift", return_value=[drift]):
            with patch.object(
                sync_mgr,
                "_get_project_artifact_path",
                return_value=project_path / ".claude" / "skills" / "test-skill",
            ):
                with patch.object(
                    sync_mgr, "_compute_artifact_hash", return_value="xyz789"
                ):
                    with patch.object(
                        sync_mgr, "_load_deployment_metadata", return_value=None
                    ):
                        result = sync_mgr.sync_from_project(
                            project_path,
                            strategy="overwrite",
                            interactive=False,
                        )

        assert result.status == "success"
        assert "test-skill" in result.artifacts_synced

    def test_complete_sync_flow_no_modifications(self, tmp_path):
        """Test sync flow when project has no modifications."""
        sync_mgr = SyncManager()

        project_path = tmp_path / "project"
        (project_path / ".claude" / "skills" / "test-skill").mkdir(parents=True)

        # Mock drift with same SHA (no modifications)
        drift = DriftDetectionResult(
            artifact_name="test-skill",
            artifact_type="skill",
            drift_type="modified",
            collection_sha="abc123",
            project_sha="abc123",  # Same SHA = no modifications
        )

        with patch.object(sync_mgr, "check_drift", return_value=[drift]):
            with patch.object(
                sync_mgr,
                "_get_project_artifact_path",
                return_value=project_path / ".claude" / "skills" / "test-skill",
            ):
                with patch.object(
                    sync_mgr, "_compute_artifact_hash", return_value="abc123"
                ):
                    result = sync_mgr.sync_from_project(project_path)

        assert result.status == "no_changes"
        assert len(result.artifacts_synced) == 0
