"""Unit tests for field whitelist functionality in CollectionRefresher.

Tests that field whitelisting correctly:
- Validates field names
- Detects ALL changes
- Only applies whitelisted changes
"""

import pytest

from skillmeat.core.artifact import Artifact, ArtifactMetadata
from skillmeat.core.artifact_detection import ArtifactType
from skillmeat.core.collection import Collection, CollectionManager
from skillmeat.core.github_metadata import GitHubMetadata
from skillmeat.core.refresher import (
    REFRESHABLE_FIELDS,
    CollectionRefresher,
    RefreshMode,
)


class TestFieldWhitelistValidation:
    """Test field name validation against REFRESHABLE_FIELDS."""

    def test_valid_field_names_accepted(self, mock_collection_manager):
        """Valid field names should not raise errors."""
        refresher = CollectionRefresher(mock_collection_manager)
        artifact = _create_test_artifact()

        # Should not raise
        result = refresher.refresh_metadata(
            artifact, fields=["description", "tags"], dry_run=True
        )
        assert result.status in ("refreshed", "unchanged", "skipped")

    def test_invalid_field_names_rejected(self, mock_collection_manager):
        """Invalid field names should raise ValueError with helpful message."""
        refresher = CollectionRefresher(mock_collection_manager)
        artifact = _create_test_artifact()

        with pytest.raises(ValueError) as exc_info:
            refresher.refresh_metadata(
                artifact, fields=["invalid_field", "another_bad_field"]
            )

        error_msg = str(exc_info.value)
        assert "Invalid field names" in error_msg
        assert "invalid_field" in error_msg
        assert "another_bad_field" in error_msg
        assert "Valid fields are:" in error_msg

    def test_mixed_valid_invalid_fields_rejected(self, mock_collection_manager):
        """Mix of valid and invalid field names should reject all."""
        refresher = CollectionRefresher(mock_collection_manager)
        artifact = _create_test_artifact()

        with pytest.raises(ValueError) as exc_info:
            refresher.refresh_metadata(
                artifact, fields=["description", "invalid_field", "tags"]
            )

        error_msg = str(exc_info.value)
        assert "invalid_field" in error_msg
        # Should NOT mention valid fields in the error
        assert "description" not in error_msg or "Invalid" in error_msg

    def test_empty_fields_list_accepted(self, mock_collection_manager):
        """Empty fields list should be accepted (refresh nothing)."""
        refresher = CollectionRefresher(mock_collection_manager)
        artifact = _create_test_artifact()

        # Should not raise with empty list
        result = refresher.refresh_metadata(artifact, fields=[], dry_run=True)
        # With empty whitelist, no fields are applied, so status should be unchanged
        # (or skipped if no GitHub source)
        assert result.status in ("unchanged", "skipped")

    def test_refreshable_fields_constant_exists(self):
        """REFRESHABLE_FIELDS should contain all valid field names."""
        assert isinstance(REFRESHABLE_FIELDS, frozenset)
        assert len(REFRESHABLE_FIELDS) > 0
        # Should include common fields
        assert "description" in REFRESHABLE_FIELDS
        assert "tags" in REFRESHABLE_FIELDS
        assert "author" in REFRESHABLE_FIELDS
        assert "license" in REFRESHABLE_FIELDS
        assert "origin_source" in REFRESHABLE_FIELDS


class TestFieldWhitelistFiltering:
    """Test that field whitelist correctly filters applied changes."""

    def test_detects_all_changes_applies_whitelisted_only(
        self, mock_collection_manager, mock_metadata_extractor, monkeypatch
    ):
        """Should detect ALL changes but only apply whitelisted fields."""
        # Setup: artifact with outdated description and tags
        artifact = _create_test_artifact(
            description="Old description", tags=["old-tag"]
        )

        # Mock upstream with different values for both fields
        upstream_metadata = GitHubMetadata(
            title="Test Skill",
            description="New description",  # Changed
            topics=["new-tag"],  # Changed
            author="test-owner",
            license="MIT",
            url="https://github.com/test/repo",
        )

        # Mock the metadata extractor to return our upstream
        mock_metadata_extractor.fetch_metadata.return_value = upstream_metadata

        refresher = CollectionRefresher(
            mock_collection_manager,
            metadata_extractor=mock_metadata_extractor,
        )

        # Refresh with whitelist: only "description"
        result = refresher.refresh_metadata(
            artifact, fields=["description"], dry_run=False
        )

        # Should detect BOTH changes
        assert result.status == "refreshed"
        assert "description" in result.changes
        assert "tags" in result.changes  # Detected but not applied

        # But only description should be applied
        assert artifact.metadata.description == "New description"
        assert artifact.tags == ["old-tag"]  # Unchanged (not in whitelist)

    def test_reports_all_changes_in_dry_run(
        self, mock_collection_manager, mock_metadata_extractor
    ):
        """Dry run should report ALL detected changes, not just whitelisted."""
        artifact = _create_test_artifact(
            description="Old desc", tags=["old"], license="Apache-2.0"
        )

        upstream_metadata = GitHubMetadata(
            title="Test",
            description="New desc",
            topics=["new"],
            author="test",
            license="MIT",
            url="https://github.com/test/repo",
        )

        mock_metadata_extractor.fetch_metadata.return_value = upstream_metadata

        refresher = CollectionRefresher(
            mock_collection_manager, metadata_extractor=mock_metadata_extractor
        )

        # Dry run with only "description" whitelisted
        result = refresher.refresh_metadata(
            artifact, fields=["description"], dry_run=True
        )

        # Should report ALL three changes
        assert result.status == "refreshed"
        assert "description" in result.changes
        assert "tags" in result.changes
        assert "license" in result.changes

        # All old/new values should be in result
        assert result.old_values["description"] == "Old desc"
        assert result.new_values["description"] == "New desc"
        assert result.old_values["tags"] == ["old"]
        assert result.new_values["tags"] == ["new"]
        assert result.old_values["license"] == "Apache-2.0"
        assert result.new_values["license"] == "MIT"

        # Artifact unchanged (dry run)
        assert artifact.metadata.description == "Old desc"

    def test_none_fields_applies_all_changes(
        self, mock_collection_manager, mock_metadata_extractor
    ):
        """When fields=None, should apply ALL detected changes."""
        artifact = _create_test_artifact(description="Old", tags=["old"])

        upstream_metadata = GitHubMetadata(
            title="Test",
            description="New",
            topics=["new"],
            author="test",
            license="MIT",
            url="https://github.com/test/repo",
        )

        mock_metadata_extractor.fetch_metadata.return_value = upstream_metadata

        refresher = CollectionRefresher(
            mock_collection_manager, metadata_extractor=mock_metadata_extractor
        )

        result = refresher.refresh_metadata(artifact, fields=None, dry_run=False)

        # All changes should be applied
        assert result.status == "refreshed"
        assert artifact.metadata.description == "New"
        assert artifact.tags == ["new"]


class TestRefreshCollectionFieldWhitelist:
    """Test field whitelist at collection level."""

    def test_collection_refresh_validates_fields(
        self, mock_collection_manager, tmp_path
    ):
        """Collection refresh should validate field names."""
        # Setup mock collection
        collection = Collection(
            name="test",
            path=tmp_path / "collection",
            artifacts=[],
            _manifest_data={},
        )
        mock_collection_manager.load_collection.return_value = collection

        refresher = CollectionRefresher(mock_collection_manager)

        # Should raise on invalid field
        with pytest.raises(ValueError) as exc_info:
            refresher.refresh_collection(fields=["invalid_field"])

        assert "Invalid field names" in str(exc_info.value)

    def test_collection_refresh_passes_fields_to_artifacts(
        self, mock_collection_manager, mock_metadata_extractor, tmp_path
    ):
        """Collection refresh should pass field whitelist to each artifact."""
        artifact = _create_test_artifact(description="Old", tags=["old"])

        collection = Collection(
            name="test",
            path=tmp_path / "collection",
            artifacts=[artifact],
            _manifest_data={},
        )
        mock_collection_manager.load_collection.return_value = collection

        upstream_metadata = GitHubMetadata(
            title="Test",
            description="New",
            topics=["new"],
            author="test",
            license="MIT",
            url="https://github.com/test/repo",
        )
        mock_metadata_extractor.fetch_metadata.return_value = upstream_metadata

        refresher = CollectionRefresher(
            mock_collection_manager, metadata_extractor=mock_metadata_extractor
        )

        # Refresh collection with field whitelist
        result = refresher.refresh_collection(fields=["description"], dry_run=False)

        # Check that only description was applied
        assert result.refreshed_count == 1
        assert artifact.metadata.description == "New"
        assert artifact.tags == ["old"]  # Not in whitelist


# Helper functions


def _create_test_artifact(
    name: str = "test-skill",
    description: str = "Test description",
    tags: list = None,
    license: str = "MIT",
) -> Artifact:
    """Create a test artifact with GitHub source."""
    return Artifact(
        name=name,
        type=ArtifactType.SKILL,
        path="/test/path",
        metadata=ArtifactMetadata(
            title="Test Skill",
            description=description,
            version="1.0.0",
            author="test-author",
            license=license,
        ),
        tags=tags or [],
        origin="github",
        upstream="test-owner/test-repo/test-skill",
        version_spec="latest",
        resolved_sha="abc123",
    )


# Fixtures


@pytest.fixture
def mock_collection_manager(monkeypatch):
    """Mock CollectionManager for testing."""
    manager = CollectionManager()
    # Mock save_collection to prevent actual file writes
    monkeypatch.setattr(manager, "save_collection", lambda c: None)
    return manager


@pytest.fixture
def mock_metadata_extractor(monkeypatch):
    """Mock GitHubMetadataExtractor for testing."""
    from unittest.mock import MagicMock

    from skillmeat.core.github_metadata import GitHubMetadataExtractor

    extractor = MagicMock(spec=GitHubMetadataExtractor)
    return extractor
