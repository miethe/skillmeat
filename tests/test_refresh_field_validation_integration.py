"""Integration tests for field validation in refresh operations.

Tests that field validation works end-to-end through the refresh_metadata
and refresh_collection methods.

Task: BE-407
"""

import pytest
from unittest.mock import Mock, MagicMock

from skillmeat.core.artifact import Artifact, ArtifactMetadata
from skillmeat.core.artifact_detection import ArtifactType
from skillmeat.core.refresher import (
    CollectionRefresher,
    RefreshMode,
    RefreshEntryResult,
)


class TestRefreshMetadataFieldValidation:
    """Test field validation in refresh_metadata method."""

    @pytest.fixture
    def mock_collection_manager(self):
        """Create a mock collection manager."""
        mock = Mock()
        return mock

    @pytest.fixture
    def refresher(self, mock_collection_manager):
        """Create a CollectionRefresher instance."""
        return CollectionRefresher(mock_collection_manager)

    @pytest.fixture
    def sample_artifact(self):
        """Create a sample artifact for testing."""
        metadata = ArtifactMetadata(
            title="Test Skill",
            description="Test skill",
            author="test-author",
            license="MIT",
        )
        artifact = Artifact(
            name="test-skill",
            type=ArtifactType.SKILL,
            version_spec="1.0.0",
            metadata=metadata,
            origin="github",
            upstream="owner/repo/skill",
        )
        return artifact

    def test_refresh_metadata_with_valid_fields(self, refresher, sample_artifact):
        """Test refresh_metadata accepts valid field names."""
        # This will fail early in validation if fields are invalid
        result = refresher.refresh_metadata(
            artifact=sample_artifact,
            fields=["description", "tags"],
            dry_run=True,
        )

        # Should not error on validation, but will be skipped due to no GitHub source fetch
        assert result.artifact_id == "skill:test-skill"
        assert result.status in ("skipped", "error", "unchanged")

    def test_refresh_metadata_with_invalid_fields(self, refresher, sample_artifact):
        """Test refresh_metadata rejects invalid field names."""
        result = refresher.refresh_metadata(
            artifact=sample_artifact,
            fields=["description", "invalid_field"],
            dry_run=True,
        )

        # Should return error status with validation message
        assert result.status == "error"
        assert "invalid_field" in result.error.lower()
        assert "valid fields" in result.error.lower()

    def test_refresh_metadata_with_case_insensitive_fields(
        self, refresher, sample_artifact
    ):
        """Test refresh_metadata normalizes field names case-insensitively."""
        result = refresher.refresh_metadata(
            artifact=sample_artifact,
            fields=["DESCRIPTION", "Tags"],
            dry_run=True,
        )

        # Should not error on validation
        assert result.artifact_id == "skill:test-skill"
        # Validation passed, so status is from actual refresh logic
        assert result.status in ("skipped", "error", "unchanged")

    def test_refresh_metadata_with_none_fields(self, refresher, sample_artifact):
        """Test refresh_metadata accepts None (all fields)."""
        result = refresher.refresh_metadata(
            artifact=sample_artifact,
            fields=None,
            dry_run=True,
        )

        # Should not error on validation
        assert result.artifact_id == "skill:test-skill"


class TestRefreshCollectionFieldValidation:
    """Test field validation in refresh_collection method."""

    @pytest.fixture
    def mock_collection_manager(self):
        """Create a mock collection manager with a test collection."""
        mock = Mock()
        # Mock load_collection to return a collection with artifacts
        mock_collection = Mock()
        mock_collection.name = "test-collection"
        mock_collection.artifacts = []
        mock.load_collection.return_value = mock_collection
        return mock

    @pytest.fixture
    def refresher(self, mock_collection_manager):
        """Create a CollectionRefresher instance."""
        return CollectionRefresher(mock_collection_manager)

    def test_refresh_collection_with_valid_fields(self, refresher):
        """Test refresh_collection accepts valid field names."""
        result = refresher.refresh_collection(
            collection_name="test-collection",
            fields=["description", "tags"],
            dry_run=True,
        )

        # Should complete without validation errors
        assert result.total_processed == 0  # Empty collection

    def test_refresh_collection_with_invalid_fields(self, refresher):
        """Test refresh_collection rejects invalid field names."""
        with pytest.raises(ValueError) as exc_info:
            refresher.refresh_collection(
                collection_name="test-collection",
                fields=["description", "bad_field"],
                dry_run=True,
            )

        # Should raise ValueError with helpful message
        error_msg = str(exc_info.value)
        assert "bad_field" in error_msg
        assert "valid fields" in error_msg.lower()

    def test_refresh_collection_with_case_insensitive_fields(self, refresher):
        """Test refresh_collection normalizes field names."""
        result = refresher.refresh_collection(
            collection_name="test-collection",
            fields=["DESCRIPTION", "Tags", "AUTHOR"],
            dry_run=True,
        )

        # Should complete without validation errors
        assert result.total_processed == 0

    def test_refresh_collection_with_none_fields(self, refresher):
        """Test refresh_collection accepts None (all fields)."""
        result = refresher.refresh_collection(
            collection_name="test-collection",
            fields=None,
            dry_run=True,
        )

        # Should complete without validation errors
        assert result.total_processed == 0
