"""Tests for sync merge fallback logic for old deployments.

Tests that the SyncManager properly handles old deployment records
that don't have the merge_base_snapshot field.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from skillmeat.core.sync import SyncManager
from skillmeat.models import (
    DeploymentMetadata,
    DeploymentRecord,
    ArtifactSyncResult,
)


class TestSyncMergeFallback:
    """Tests for merge fallback logic with old deployments."""

    def test_sync_merge_without_merge_base_snapshot(self, tmp_path, caplog):
        """Test merge uses fallback when merge_base_snapshot is missing."""
        # Setup
        sync_mgr = SyncManager()
        project_artifact_path = tmp_path / "project" / ".claude" / "skills" / "test-skill"
        collection_artifact_path = tmp_path / "collection" / "skills" / "test-skill"

        project_artifact_path.mkdir(parents=True)
        collection_artifact_path.mkdir(parents=True)

        # Create test files
        (project_artifact_path / "SKILL.md").write_text("# Project version")
        (collection_artifact_path / "SKILL.md").write_text("# Collection version")

        # Create old deployment record (without merge_base_snapshot)
        old_deployment = DeploymentRecord(
            name="test-skill",
            artifact_type="skill",
            source="local:/collection",
            version="1.0.0",
            sha="abc123",
            deployed_at=datetime.now().isoformat(),
            deployed_from=str(tmp_path / "collection"),
        )

        metadata = DeploymentMetadata(
            collection="default",
            deployed_at=datetime.now().isoformat(),
            skillmeat_version="0.2.0-alpha",
            artifacts=[old_deployment],
        )

        # Mock _load_deployment_metadata to return old deployment
        with patch.object(sync_mgr, '_load_deployment_metadata', return_value=metadata):
            # Mock merge_engine to verify it was called
            mock_merge_engine = MagicMock()
            mock_merge_result = MagicMock()
            mock_merge_result.has_conflicts = False
            mock_merge_result.success = True
            mock_merge_result.conflicts = []
            mock_merge_engine.merge.return_value = mock_merge_result

            with patch('skillmeat.core.merge_engine.MergeEngine', return_value=mock_merge_engine):
                # Execute
                result = sync_mgr._sync_merge(
                    project_artifact_path,
                    collection_artifact_path,
                    "test-skill"
                )

        # Verify
        assert result.success is True
        assert result.has_conflict is False

        # Verify merge was called with collection as base (fallback)
        mock_merge_engine.merge.assert_called_once()
        call_kwargs = mock_merge_engine.merge.call_args[1]
        assert call_kwargs['base_path'] == collection_artifact_path
        assert call_kwargs['local_path'] == collection_artifact_path
        assert call_kwargs['remote_path'] == project_artifact_path

        # Verify warning was logged
        assert "missing merge_base_snapshot" in caplog.text
        assert "Using fallback" in caplog.text

    def test_sync_merge_with_merge_base_snapshot(self, tmp_path, caplog):
        """Test merge uses snapshot when merge_base_snapshot is present."""
        # Setup
        sync_mgr = SyncManager()

        # Create mock snapshot manager
        mock_snapshot_mgr = MagicMock()
        mock_snapshot = MagicMock()
        mock_snapshot.tarball_path = tmp_path / "snapshots" / "test-snapshot.tar.gz"
        mock_snapshot_mgr.get_snapshot.return_value = mock_snapshot
        sync_mgr.snapshot_mgr = mock_snapshot_mgr

        project_artifact_path = tmp_path / "project" / ".claude" / "skills" / "test-skill"
        collection_artifact_path = tmp_path / "collection" / "skills" / "test-skill"

        project_artifact_path.mkdir(parents=True)
        collection_artifact_path.mkdir(parents=True)

        # Create test files
        (project_artifact_path / "SKILL.md").write_text("# Project version")
        (collection_artifact_path / "SKILL.md").write_text("# Collection version")

        # Create deployment record WITH merge_base_snapshot
        new_deployment = MagicMock()
        new_deployment.name = "test-skill"
        new_deployment.artifact_type = "skill"
        new_deployment.merge_base_snapshot = "snapshot-123"

        metadata = MagicMock()
        metadata.collection = "default"
        metadata.artifacts = [new_deployment]

        # Mock extraction to return temp path
        extracted_base = tmp_path / "temp-base" / "skills" / "test-skill"
        extracted_base.mkdir(parents=True)
        (extracted_base / "SKILL.md").write_text("# Base version")

        # Mock _load_deployment_metadata
        with patch.object(sync_mgr, '_load_deployment_metadata', return_value=metadata):
            # Mock _extract_base_from_snapshot
            with patch.object(
                sync_mgr,
                '_extract_base_from_snapshot',
                return_value=extracted_base
            ) as mock_extract:
                # Mock merge_engine
                mock_merge_engine = MagicMock()
                mock_merge_result = MagicMock()
                mock_merge_result.has_conflicts = False
                mock_merge_result.success = True
                mock_merge_result.conflicts = []
                mock_merge_engine.merge.return_value = mock_merge_result

                with patch('skillmeat.core.merge_engine.MergeEngine', return_value=mock_merge_engine):
                    # Execute
                    result = sync_mgr._sync_merge(
                        project_artifact_path,
                        collection_artifact_path,
                        "test-skill"
                    )

        # Verify
        assert result.success is True

        # Verify extract was called with snapshot ID and collection name
        mock_extract.assert_called_once_with("snapshot-123", "test-skill", "skill", "default")

        # Verify merge was called with extracted base
        mock_merge_engine.merge.assert_called_once()
        call_kwargs = mock_merge_engine.merge.call_args[1]
        assert call_kwargs['base_path'] == extracted_base

        # Verify no warning about missing snapshot
        assert "missing merge_base_snapshot" not in caplog.text

    def test_extract_base_from_snapshot_not_found(self, tmp_path, caplog):
        """Test _extract_base_from_snapshot handles missing snapshot gracefully."""
        # Setup
        sync_mgr = SyncManager()

        # Create mock snapshot manager that returns None
        mock_snapshot_mgr = MagicMock()
        mock_snapshot_mgr.get_snapshot.return_value = None
        sync_mgr.snapshot_mgr = mock_snapshot_mgr

        # Execute
        result = sync_mgr._extract_base_from_snapshot(
            "nonexistent-snapshot",
            "test-skill",
            "skill"
        )

        # Verify
        assert result is None
        assert "not found" in caplog.text

    def test_extract_base_from_snapshot_no_manager(self, tmp_path):
        """Test _extract_base_from_snapshot handles missing snapshot manager."""
        # Setup
        sync_mgr = SyncManager()
        sync_mgr.snapshot_mgr = None

        # Execute
        result = sync_mgr._extract_base_from_snapshot(
            "snapshot-123",
            "test-skill",
            "skill"
        )

        # Verify
        assert result is None
