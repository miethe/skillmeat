"""Unit tests for sync version creation functionality.

Tests the _create_sync_version method in SyncManager to ensure proper
version tracking during sync operations.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from skillmeat.core.sync import SyncManager


class TestSyncVersionCreation:
    """Test sync version creation."""

    @pytest.fixture
    def sync_manager(self):
        """Create SyncManager instance for testing."""
        return SyncManager()

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = MagicMock()
        return session

    @pytest.fixture
    def mock_artifact_version_class(self):
        """Create mock ArtifactVersion class."""
        return MagicMock()

    def test_create_sync_version_with_parent(
        self, sync_manager, mock_session, mock_artifact_version_class
    ):
        """Test creating sync version with parent hash."""
        # Setup
        artifact_id = "test-skill"
        new_hash = "abc123def456" + "0" * 52  # 64-char SHA-256
        parent_hash = "def789abc012" + "0" * 52

        # Mock parent version with lineage
        mock_parent = MagicMock()
        mock_parent.version_lineage = json.dumps([parent_hash])

        # Configure session query to return parent
        mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            None,  # First call: check for existing version (returns None)
            mock_parent,  # Second call: get parent version
        ]

        with (
            patch("skillmeat.cache.models.get_session", return_value=mock_session),
            patch(
                "skillmeat.cache.models.ArtifactVersion", mock_artifact_version_class
            ),
        ):
            # Execute
            sync_manager._create_sync_version(artifact_id, new_hash, parent_hash)

            # Verify version was created
            assert mock_artifact_version_class.call_count == 1
            call_kwargs = mock_artifact_version_class.call_args[1]

            assert call_kwargs["artifact_id"] == artifact_id
            assert call_kwargs["content_hash"] == new_hash
            assert call_kwargs["parent_hash"] == parent_hash
            assert call_kwargs["change_origin"] == "sync"

            # Verify lineage was extended
            lineage = json.loads(call_kwargs["version_lineage"])
            assert lineage == [parent_hash, new_hash]

            # Verify session was committed and closed
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()

    def test_create_sync_version_without_parent(
        self, sync_manager, mock_session, mock_artifact_version_class
    ):
        """Test creating sync version without parent (root version)."""
        # Setup
        artifact_id = "test-skill"
        new_hash = "abc123def456" + "0" * 52
        parent_hash = None  # No parent - root version

        # Configure session query to return no existing version
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        with (
            patch("skillmeat.cache.models.get_session", return_value=mock_session),
            patch(
                "skillmeat.cache.models.ArtifactVersion", mock_artifact_version_class
            ),
        ):
            # Execute
            sync_manager._create_sync_version(artifact_id, new_hash, parent_hash)

            # Verify version was created
            call_kwargs = mock_artifact_version_class.call_args[1]

            assert call_kwargs["artifact_id"] == artifact_id
            assert call_kwargs["content_hash"] == new_hash
            assert call_kwargs["parent_hash"] is None
            assert call_kwargs["change_origin"] == "sync"

            # Verify lineage contains only new hash
            lineage = json.loads(call_kwargs["version_lineage"])
            assert lineage == [new_hash]

    def test_create_sync_version_legacy_parent(
        self, sync_manager, mock_session, mock_artifact_version_class
    ):
        """Test creating sync version when parent doesn't exist in version table."""
        # Setup - legacy deployment scenario
        artifact_id = "test-skill"
        new_hash = "abc123def456" + "0" * 52
        parent_hash = (
            "def789abc012" + "0" * 52
        )  # Parent exists but not in version table

        # Configure session query to return None for parent version lookup
        mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            None,  # First call: check for existing version
            None,  # Second call: get parent version (not found - legacy)
        ]

        with (
            patch("skillmeat.cache.models.get_session", return_value=mock_session),
            patch(
                "skillmeat.cache.models.ArtifactVersion", mock_artifact_version_class
            ),
        ):
            # Execute
            sync_manager._create_sync_version(artifact_id, new_hash, parent_hash)

            # Verify version was created with lineage starting from parent
            call_kwargs = mock_artifact_version_class.call_args[1]

            assert call_kwargs["parent_hash"] == parent_hash
            assert call_kwargs["change_origin"] == "sync"

            # Verify lineage starts with parent hash (legacy case)
            lineage = json.loads(call_kwargs["version_lineage"])
            assert lineage == [parent_hash, new_hash]

    def test_create_sync_version_deduplication(
        self, sync_manager, mock_session, mock_artifact_version_class
    ):
        """Test that duplicate versions are not created."""
        # Setup
        artifact_id = "test-skill"
        new_hash = "abc123def456" + "0" * 52
        parent_hash = "def789abc012" + "0" * 52

        # Mock existing version with same content hash
        mock_existing = MagicMock()
        mock_existing.content_hash = new_hash

        # Configure session to return existing version
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            mock_existing
        )

        with (
            patch("skillmeat.cache.models.get_session", return_value=mock_session),
            patch(
                "skillmeat.cache.models.ArtifactVersion", mock_artifact_version_class
            ),
        ):
            # Execute
            sync_manager._create_sync_version(artifact_id, new_hash, parent_hash)

            # Verify no new version was created (deduplication)
            mock_artifact_version_class.assert_not_called()
            mock_session.add.assert_not_called()
            mock_session.commit.assert_not_called()

    def test_create_sync_version_handles_errors(self, sync_manager):
        """Test that version creation errors don't crash sync."""
        # Setup
        artifact_id = "test-skill"
        new_hash = "abc123def456" + "0" * 52
        parent_hash = "def789abc012" + "0" * 52

        # Mock session to raise exception
        mock_session = MagicMock()
        mock_session.query.side_effect = Exception("Database error")

        with patch("skillmeat.cache.models.get_session", return_value=mock_session):
            # Execute - should not raise exception
            try:
                sync_manager._create_sync_version(artifact_id, new_hash, parent_hash)
            except Exception as e:
                pytest.fail(f"_create_sync_version should not raise: {e}")

            # Verify session was still closed
            mock_session.close.assert_called_once()
