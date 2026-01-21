"""Comprehensive unit tests for the CollectionRefresher module.

Tests cover all public methods of the CollectionRefresher class including:
- Source specification parsing (BE-113)
- Change detection (BE-114)
- Update application (BE-115)
- Single artifact metadata refresh (BE-116)
- Collection-wide refresh operations (BE-117)
- GitHub API error handling (BE-118)

Tasks: BE-113, BE-114, BE-115, BE-116, BE-117, BE-118
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from skillmeat.core.artifact import Artifact, ArtifactMetadata
from skillmeat.core.artifact_detection import ArtifactType
from skillmeat.core.collection import Collection
from skillmeat.core.github_client import (
    GitHubClientError,
    GitHubNotFoundError,
    GitHubRateLimitError,
)
from skillmeat.core.github_metadata import GitHubMetadata, GitHubSourceSpec
from skillmeat.core.refresher import (
    CollectionRefresher,
    REFRESH_FIELD_MAPPING,
    RefreshEntryResult,
    RefreshMode,
    RefreshResult,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_artifact():
    """Create a sample artifact for testing."""
    return Artifact(
        name="test-skill",
        type=ArtifactType.SKILL,
        path="skills/test-skill",
        origin="github",
        metadata=ArtifactMetadata(
            title="Test Skill",
            description="Original description",
            tags=["old-tag"],
        ),
        added=datetime.now(),
        upstream="https://github.com/user/repo/tree/main/path/to/skill",
        tags=["old-tag"],
        origin_source=None,
    )


@pytest.fixture
def sample_marketplace_artifact():
    """Create a sample marketplace artifact with GitHub origin."""
    return Artifact(
        name="marketplace-skill",
        type=ArtifactType.SKILL,
        path="skills/marketplace-skill",
        origin="marketplace",
        origin_source="github",
        metadata=ArtifactMetadata(
            title="Marketplace Skill",
            description="Marketplace description",
        ),
        added=datetime.now(),
        upstream="https://github.com/marketplace/skills/tree/main/popular-skill",
        tags=["marketplace"],
    )


@pytest.fixture
def sample_local_artifact():
    """Create a sample local artifact (no GitHub source)."""
    return Artifact(
        name="local-skill",
        type=ArtifactType.SKILL,
        path="skills/local-skill",
        origin="local",
        metadata=ArtifactMetadata(
            title="Local Skill",
            description="Local description",
        ),
        added=datetime.now(),
        tags=["local"],
    )


@pytest.fixture
def sample_github_metadata():
    """Create sample GitHub metadata for testing."""
    return GitHubMetadata(
        title="Test Skill",
        description="New description from GitHub",
        author="test-author",
        license="MIT",
        topics=["new-tag", "another-tag"],
        url="https://github.com/user/repo/tree/main/path/to/skill",
        fetched_at=datetime.now(),
    )


@pytest.fixture
def mock_collection():
    """Create a mock collection with artifacts."""
    return Collection(
        name="test-collection",
        version="1.0.0",
        artifacts=[],
        created=datetime.now(),
        updated=datetime.now(),
    )


@pytest.fixture
def mock_collection_manager(mock_collection):
    """Create mock collection manager."""
    mock = MagicMock()
    mock.load_collection.return_value = mock_collection
    mock.save_collection.return_value = None
    return mock


@pytest.fixture
def mock_metadata_extractor():
    """Create mock metadata extractor."""
    mock = MagicMock()
    return mock


@pytest.fixture
def refresher(mock_collection_manager, mock_metadata_extractor):
    """Create refresher with mock dependencies."""
    return CollectionRefresher(
        collection_manager=mock_collection_manager,
        metadata_extractor=mock_metadata_extractor,
    )


# =============================================================================
# BE-113: TestParseSourceSpec
# =============================================================================


class TestParseSourceSpec:
    """Tests for _parse_source_spec() method (BE-113).

    Note: These tests use a refresher with real metadata_extractor to test
    the actual parsing logic.
    """

    @pytest.fixture
    def real_refresher(self, mock_collection_manager):
        """Create refresher with real metadata extractor for parsing tests."""
        return CollectionRefresher(
            collection_manager=mock_collection_manager,
            metadata_extractor=None,  # Will use lazy initialization
        )

    def test_parse_standard_format(self, real_refresher):
        """Test parsing standard owner/repo/path format."""
        spec = real_refresher._parse_source_spec("anthropics/skills/canvas-design")

        assert spec is not None
        assert spec.owner == "anthropics"
        assert spec.repo == "skills"
        assert spec.path == "canvas-design"
        assert spec.version == "latest"

    def test_parse_with_version_tag(self, real_refresher):
        """Test parsing owner/repo/path@v1.0.0 format."""
        spec = real_refresher._parse_source_spec("user/repo/skill@v1.0.0")

        assert spec is not None
        assert spec.owner == "user"
        assert spec.repo == "repo"
        assert spec.path == "skill"
        assert spec.version == "v1.0.0"

    def test_parse_with_sha(self, real_refresher):
        """Test parsing owner/repo/path@abc123 (SHA ref) format."""
        spec = real_refresher._parse_source_spec("user/repo/skill@abc123def456")

        assert spec is not None
        assert spec.owner == "user"
        assert spec.repo == "repo"
        assert spec.path == "skill"
        assert spec.version == "abc123def456"

    def test_parse_https_url(self, real_refresher):
        """Test parsing full GitHub URL."""
        spec = real_refresher._parse_source_spec(
            "https://github.com/anthropics/skills/tree/main/canvas-design"
        )

        assert spec is not None
        assert spec.owner == "anthropics"
        assert spec.repo == "skills"
        assert spec.path == "canvas-design"

    def test_parse_https_url_nested_path(self, real_refresher):
        """Test parsing HTTPS URL with deeply nested path."""
        spec = real_refresher._parse_source_spec(
            "https://github.com/user/repo/tree/main/path/to/deep/artifact"
        )

        assert spec is not None
        assert spec.owner == "user"
        assert spec.repo == "repo"
        assert spec.path == "path/to/deep/artifact"

    def test_parse_invalid_too_few_segments(self, real_refresher):
        """Test that single segment without slashes returns None (doesn't look like GitHub)."""
        # A single segment without slashes doesn't look like a GitHub reference
        # so it returns None instead of raising an error
        result = real_refresher._parse_source_spec("onlyone")
        assert result is None

    def test_parse_invalid_https_url_too_short(self, real_refresher):
        """Test that invalid HTTPS URL raises ValueError."""
        # An HTTPS GitHub URL with too few segments IS an error
        # because it explicitly claims to be a GitHub URL but is malformed
        with pytest.raises(ValueError, match="Invalid GitHub"):
            real_refresher._parse_source_spec("https://github.com/onlyone")

    def test_parse_empty_string(self, real_refresher):
        """Test that empty string returns None."""
        result = real_refresher._parse_source_spec("")
        assert result is None

    def test_parse_whitespace_only(self, real_refresher):
        """Test that whitespace-only string returns None."""
        result = real_refresher._parse_source_spec("   ")
        assert result is None

    def test_parse_local_path_absolute(self, real_refresher):
        """Test that absolute local path returns None."""
        result = real_refresher._parse_source_spec("/path/to/local/skill")
        assert result is None

    def test_parse_local_path_relative_current(self, real_refresher):
        """Test that relative current path returns None."""
        result = real_refresher._parse_source_spec("./local/skill")
        assert result is None

    def test_parse_local_path_relative_parent(self, real_refresher):
        """Test that relative parent path returns None."""
        result = real_refresher._parse_source_spec("../parent/skill")
        assert result is None

    def test_parse_minimal_owner_repo(self, real_refresher):
        """Test parsing minimal owner/repo format."""
        spec = real_refresher._parse_source_spec("anthropics/skills")

        assert spec is not None
        assert spec.owner == "anthropics"
        assert spec.repo == "skills"
        assert spec.path == ""
        assert spec.version == "latest"


# =============================================================================
# BE-114: TestDetectChanges
# =============================================================================


class TestDetectChanges:
    """Tests for _detect_changes() method (BE-114)."""

    def test_detect_description_change(self, refresher, sample_artifact):
        """Test detecting description change between old and new metadata."""
        upstream = GitHubMetadata(
            description="New description from upstream",
            url="https://github.com/test",
            fetched_at=datetime.now(),
            topics=[],
        )

        old_values, new_values = refresher._detect_changes(
            sample_artifact, upstream, fields=["description"]
        )

        assert "description" in new_values
        assert old_values["description"] == "Original description"
        assert new_values["description"] == "New description from upstream"

    def test_detect_tags_change(self, refresher, sample_artifact):
        """Test detecting tags/topics change."""
        upstream = GitHubMetadata(
            topics=["new-tag", "another-tag"],
            url="https://github.com/test",
            fetched_at=datetime.now(),
        )

        old_values, new_values = refresher._detect_changes(
            sample_artifact, upstream, fields=["tags"]
        )

        assert "tags" in new_values
        assert old_values["tags"] == ["old-tag"]
        assert set(new_values["tags"]) == {"new-tag", "another-tag"}

    def test_detect_license_change(self, refresher, sample_artifact):
        """Test detecting license field change."""
        # Set initial license
        sample_artifact.metadata.license = "Apache-2.0"

        upstream = GitHubMetadata(
            license="MIT",
            url="https://github.com/test",
            fetched_at=datetime.now(),
            topics=[],
        )

        old_values, new_values = refresher._detect_changes(
            sample_artifact, upstream, fields=["license"]
        )

        assert "license" in new_values
        assert old_values["license"] == "Apache-2.0"
        assert new_values["license"] == "MIT"

    def test_detect_no_changes(self, refresher, sample_artifact):
        """Test that identical metadata returns no changes."""
        upstream = GitHubMetadata(
            description="Original description",  # Same as artifact
            topics=["old-tag"],  # Same as artifact
            url="https://github.com/test",
            fetched_at=datetime.now(),
        )

        old_values, new_values = refresher._detect_changes(
            sample_artifact, upstream, fields=["description", "tags"]
        )

        assert old_values == {}
        assert new_values == {}

    def test_detect_multiple_changes(self, refresher, sample_artifact):
        """Test detecting multiple field changes at once."""
        sample_artifact.metadata.license = "Apache-2.0"

        upstream = GitHubMetadata(
            description="New description",
            license="MIT",
            topics=["new-tag"],
            url="https://github.com/test",
            fetched_at=datetime.now(),
        )

        old_values, new_values = refresher._detect_changes(
            sample_artifact, upstream, fields=["description", "license", "tags"]
        )

        assert len(new_values) == 3
        assert "description" in new_values
        assert "license" in new_values
        assert "tags" in new_values

    def test_handle_none_values(self, refresher, sample_artifact):
        """Test handling None values in either current or upstream."""
        # Set description to None
        sample_artifact.metadata.description = None

        upstream = GitHubMetadata(
            description="New description",
            url="https://github.com/test",
            fetched_at=datetime.now(),
            topics=[],
        )

        old_values, new_values = refresher._detect_changes(
            sample_artifact, upstream, fields=["description"]
        )

        assert "description" in new_values
        assert old_values["description"] is None
        assert new_values["description"] == "New description"

    def test_handle_both_none_values(self, refresher, sample_artifact):
        """Test that both None values are considered equal."""
        sample_artifact.metadata.license = None

        upstream = GitHubMetadata(
            license=None,
            url="https://github.com/test",
            fetched_at=datetime.now(),
            topics=[],
        )

        old_values, new_values = refresher._detect_changes(
            sample_artifact, upstream, fields=["license"]
        )

        # No change since both are None
        assert "license" not in new_values

    def test_handle_empty_lists(self, refresher, sample_artifact):
        """Test handling empty list vs populated list."""
        sample_artifact.tags = []

        upstream = GitHubMetadata(
            topics=["new-tag"],
            url="https://github.com/test",
            fetched_at=datetime.now(),
        )

        old_values, new_values = refresher._detect_changes(
            sample_artifact, upstream, fields=["tags"]
        )

        assert "tags" in new_values
        assert old_values["tags"] == []
        assert new_values["tags"] == ["new-tag"]

    def test_field_filtering_only_specified_fields(self, refresher, sample_artifact):
        """Test that only specified fields are checked."""
        upstream = GitHubMetadata(
            description="New description",
            license="MIT",
            topics=["new-tag"],
            url="https://github.com/test",
            fetched_at=datetime.now(),
        )

        # Only check description
        old_values, new_values = refresher._detect_changes(
            sample_artifact, upstream, fields=["description"]
        )

        assert len(new_values) == 1
        assert "description" in new_values
        assert "license" not in new_values
        assert "tags" not in new_values

    def test_field_filtering_all_fields_default(self, refresher, sample_artifact):
        """Test that all REFRESH_FIELD_MAPPING fields are checked when fields=None."""
        sample_artifact.metadata.license = "Apache-2.0"
        sample_artifact.metadata.author = "old-author"

        upstream = GitHubMetadata(
            description="New description",
            license="MIT",
            author="new-author",
            topics=["new-tag"],
            url="https://github.com/test",
            fetched_at=datetime.now(),
        )

        old_values, new_values = refresher._detect_changes(
            sample_artifact, upstream, fields=None
        )

        # Should check all fields in REFRESH_FIELD_MAPPING
        assert len(new_values) >= 3  # At least description, tags, license changed

    def test_license_case_insensitive(self, refresher, sample_artifact):
        """Test that license comparison is case-insensitive."""
        sample_artifact.metadata.license = "MIT"

        upstream = GitHubMetadata(
            license="mit",  # Lowercase
            url="https://github.com/test",
            fetched_at=datetime.now(),
            topics=[],
        )

        old_values, new_values = refresher._detect_changes(
            sample_artifact, upstream, fields=["license"]
        )

        # Should be no change due to case-insensitive comparison
        assert "license" not in new_values

    def test_tags_order_independent(self, refresher, sample_artifact):
        """Test that tag comparison is order-independent."""
        sample_artifact.tags = ["tag-b", "tag-a"]

        upstream = GitHubMetadata(
            topics=["tag-a", "tag-b"],  # Same tags, different order
            url="https://github.com/test",
            fetched_at=datetime.now(),
        )

        old_values, new_values = refresher._detect_changes(
            sample_artifact, upstream, fields=["tags"]
        )

        # Should be no change since tags are the same (just different order)
        assert "tags" not in new_values


# =============================================================================
# BE-115: TestApplyUpdates
# =============================================================================


class TestApplyUpdates:
    """Tests for _apply_updates() method (BE-115)."""

    def test_apply_description_update(self, refresher, sample_artifact):
        """Test applying description update."""
        old_values = {"description": "Original description"}
        new_values = {"description": "New description"}

        updated = refresher._apply_updates(sample_artifact, old_values, new_values)

        assert updated.metadata.description == "New description"

    def test_apply_tags_update(self, refresher, sample_artifact):
        """Test applying tags update."""
        old_values = {"tags": ["old-tag"]}
        new_values = {"tags": ["new-tag", "another-tag"]}

        updated = refresher._apply_updates(sample_artifact, old_values, new_values)

        assert updated.tags == ["new-tag", "another-tag"]

    def test_apply_multiple_updates(self, refresher, sample_artifact):
        """Test applying multiple field updates at once."""
        sample_artifact.metadata.license = "Apache-2.0"

        old_values = {
            "description": "Original description",
            "tags": ["old-tag"],
            "license": "Apache-2.0",
        }
        new_values = {
            "description": "New description",
            "tags": ["new-tag"],
            "license": "MIT",
        }

        updated = refresher._apply_updates(sample_artifact, old_values, new_values)

        assert updated.metadata.description == "New description"
        assert updated.tags == ["new-tag"]
        assert updated.metadata.license == "MIT"

    def test_apply_preserves_unchanged_fields(self, refresher, sample_artifact):
        """Test that unchanged fields are preserved."""
        original_title = sample_artifact.metadata.title
        original_path = sample_artifact.path

        old_values = {"description": "Original description"}
        new_values = {"description": "New description"}

        updated = refresher._apply_updates(sample_artifact, old_values, new_values)

        # Unchanged fields should remain the same
        assert updated.metadata.title == original_title
        assert updated.path == original_path

    def test_apply_author_update(self, refresher, sample_artifact):
        """Test applying author update."""
        sample_artifact.metadata.author = "old-author"

        old_values = {"author": "old-author"}
        new_values = {"author": "new-author"}

        updated = refresher._apply_updates(sample_artifact, old_values, new_values)

        assert updated.metadata.author == "new-author"

    def test_apply_origin_source_marketplace_only(
        self, refresher, sample_marketplace_artifact
    ):
        """Test that origin_source update only applies to marketplace artifacts."""
        old_values = {"origin_source": "github"}
        new_values = {"origin_source": "https://github.com/new/url"}

        updated = refresher._apply_updates(
            sample_marketplace_artifact, old_values, new_values
        )

        assert updated.origin_source == "https://github.com/new/url"

    def test_apply_origin_source_ignored_for_github(self, refresher, sample_artifact):
        """Test that origin_source update is ignored for non-marketplace artifacts."""
        # sample_artifact has origin="github", not "marketplace"
        original_origin_source = sample_artifact.origin_source

        old_values = {"origin_source": None}
        new_values = {"origin_source": "https://github.com/new/url"}

        updated = refresher._apply_updates(sample_artifact, old_values, new_values)

        # Should remain unchanged
        assert updated.origin_source == original_origin_source

    def test_apply_empty_tags_list(self, refresher, sample_artifact):
        """Test applying empty tags list update."""
        old_values = {"tags": ["old-tag"]}
        new_values = {"tags": []}

        updated = refresher._apply_updates(sample_artifact, old_values, new_values)

        assert updated.tags == []

    def test_apply_none_tags(self, refresher, sample_artifact):
        """Test applying None tags (should become empty list)."""
        old_values = {"tags": ["old-tag"]}
        new_values = {"tags": None}

        updated = refresher._apply_updates(sample_artifact, old_values, new_values)

        assert updated.tags == []


# =============================================================================
# BE-116: TestRefreshMetadata
# =============================================================================


class TestRefreshMetadata:
    """Tests for refresh_metadata() method (BE-116)."""

    def test_refresh_success(self, refresher, sample_artifact, sample_github_metadata):
        """Test full refresh flow with changes detected and applied."""
        # Mock the metadata extractor
        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path/to/skill"
        )
        refresher._metadata_extractor.fetch_metadata.return_value = sample_github_metadata

        result = refresher.refresh_metadata(
            sample_artifact, mode=RefreshMode.METADATA_ONLY
        )

        assert result.status == "refreshed"
        assert len(result.changes) > 0
        assert "description" in result.changes
        assert result.old_values is not None
        assert result.new_values is not None

    def test_refresh_no_changes(self, refresher, sample_artifact):
        """Test refresh when upstream metadata matches current."""
        # Create matching metadata - matching the artifact's current values
        matching_metadata = GitHubMetadata(
            description="Original description",  # Same as sample_artifact
            topics=["old-tag"],  # Same as sample_artifact.tags
            author=None,  # Same as sample_artifact.metadata.author
            license=None,  # Same as sample_artifact.metadata.license
            url="https://github.com/user/repo/tree/main/path/to/skill",  # Same as upstream
            fetched_at=datetime.now(),
        )

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path/to/skill"
        )
        refresher._metadata_extractor.fetch_metadata.return_value = matching_metadata

        # Only check fields that we've matched to avoid origin_source comparison
        result = refresher.refresh_metadata(
            sample_artifact,
            mode=RefreshMode.METADATA_ONLY,
            fields=["description", "tags", "author", "license"],  # Exclude origin_source
        )

        assert result.status == "unchanged"
        assert result.changes == []

    def test_refresh_dry_run(self, refresher, sample_artifact, sample_github_metadata):
        """Test dry run mode - changes detected but not applied."""
        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path/to/skill"
        )
        refresher._metadata_extractor.fetch_metadata.return_value = sample_github_metadata

        original_description = sample_artifact.metadata.description

        result = refresher.refresh_metadata(
            sample_artifact, mode=RefreshMode.METADATA_ONLY, dry_run=True
        )

        assert result.status == "refreshed"
        assert len(result.changes) > 0
        assert result.reason == "Dry run - changes not applied"
        # Verify artifact was NOT modified
        assert sample_artifact.metadata.description == original_description

    def test_refresh_check_only_mode(
        self, refresher, sample_artifact, sample_github_metadata
    ):
        """Test CHECK_ONLY mode prevents changes from being applied."""
        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path/to/skill"
        )
        refresher._metadata_extractor.fetch_metadata.return_value = sample_github_metadata

        original_description = sample_artifact.metadata.description

        result = refresher.refresh_metadata(
            sample_artifact, mode=RefreshMode.CHECK_ONLY
        )

        assert result.status == "refreshed"
        assert len(result.changes) > 0
        assert result.reason == "Check only"
        # Verify artifact was NOT modified
        assert sample_artifact.metadata.description == original_description

    def test_refresh_skip_no_github_source(self, refresher, sample_local_artifact):
        """Test that local artifacts are skipped (no GitHub source)."""
        result = refresher.refresh_metadata(
            sample_local_artifact, mode=RefreshMode.METADATA_ONLY
        )

        assert result.status == "skipped"
        assert result.reason == "No GitHub source"
        assert result.changes == []

    def test_refresh_error_invalid_spec(self, refresher, sample_artifact):
        """Test error handling when source spec parsing fails."""
        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.side_effect = ValueError(
            "Invalid spec"
        )

        result = refresher.refresh_metadata(
            sample_artifact, mode=RefreshMode.METADATA_ONLY
        )

        assert result.status == "error"
        assert "Invalid" in result.error

    def test_refresh_error_fetch_failed(self, refresher, sample_artifact):
        """Test error handling when GitHub fetch fails."""
        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path/to/skill"
        )
        refresher._metadata_extractor.fetch_metadata.return_value = None

        result = refresher.refresh_metadata(
            sample_artifact, mode=RefreshMode.METADATA_ONLY
        )

        assert result.status == "error"
        assert "upstream metadata" in result.error.lower()

    def test_refresh_marketplace_github_artifact(
        self, refresher, sample_marketplace_artifact, sample_github_metadata
    ):
        """Test refreshing marketplace artifact with GitHub origin_source."""
        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="marketplace", repo="skills", path="popular-skill"
        )
        refresher._metadata_extractor.fetch_metadata.return_value = sample_github_metadata

        result = refresher.refresh_metadata(
            sample_marketplace_artifact, mode=RefreshMode.METADATA_ONLY
        )

        assert result.status == "refreshed"

    def test_refresh_with_specific_fields(
        self, refresher, sample_artifact, sample_github_metadata
    ):
        """Test refresh with specific fields only."""
        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path/to/skill"
        )
        refresher._metadata_extractor.fetch_metadata.return_value = sample_github_metadata

        result = refresher.refresh_metadata(
            sample_artifact, mode=RefreshMode.METADATA_ONLY, fields=["description"]
        )

        assert result.status == "refreshed"
        # Only description should be in changes
        assert "description" in result.changes

    def test_refresh_result_duration_tracked(
        self, refresher, sample_artifact, sample_github_metadata
    ):
        """Test that refresh operation duration is tracked."""
        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path/to/skill"
        )
        refresher._metadata_extractor.fetch_metadata.return_value = sample_github_metadata

        result = refresher.refresh_metadata(
            sample_artifact, mode=RefreshMode.METADATA_ONLY
        )

        assert result.duration_ms >= 0


# =============================================================================
# BE-117: TestRefreshCollection
# =============================================================================


class TestRefreshCollection:
    """Tests for refresh_collection() method (BE-117)."""

    def test_refresh_collection_all_artifacts(
        self, refresher, mock_collection, sample_artifact, sample_github_metadata
    ):
        """Test refreshing all artifacts in collection."""
        # Add artifacts to collection
        mock_collection.artifacts = [sample_artifact]

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path/to/skill"
        )
        refresher._metadata_extractor.fetch_metadata.return_value = sample_github_metadata

        result = refresher.refresh_collection()

        assert result.total_processed == 1
        assert result.refreshed_count == 1
        assert len(result.entries) == 1

    def test_refresh_collection_type_filter(
        self, refresher, mock_collection, sample_artifact
    ):
        """Test filtering by artifact type."""
        # Create command artifact
        command_artifact = Artifact(
            name="test-command",
            type=ArtifactType.COMMAND,
            path="commands/test-command.md",
            origin="github",
            metadata=ArtifactMetadata(title="Test Command"),
            added=datetime.now(),
            upstream="https://github.com/user/repo/tree/main/command",
        )

        mock_collection.artifacts = [sample_artifact, command_artifact]

        # Mock for skill only
        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path"
        )
        refresher._metadata_extractor.fetch_metadata.return_value = GitHubMetadata(
            description="New",
            url="https://github.com/test",
            fetched_at=datetime.now(),
            topics=[],
        )

        # Filter by skill type only
        result = refresher.refresh_collection(artifact_filter={"type": "skill"})

        # Only skill should be processed
        assert result.total_processed == 1
        assert result.entries[0].artifact_id == "skill:test-skill"

    def test_refresh_collection_name_filter(
        self, refresher, mock_collection, sample_artifact
    ):
        """Test filtering by name pattern (glob)."""
        # Create another artifact
        another_artifact = Artifact(
            name="other-skill",
            type=ArtifactType.SKILL,
            path="skills/other-skill",
            origin="github",
            metadata=ArtifactMetadata(title="Other Skill"),
            added=datetime.now(),
            upstream="https://github.com/user/repo/tree/main/other",
        )

        mock_collection.artifacts = [sample_artifact, another_artifact]

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path"
        )
        refresher._metadata_extractor.fetch_metadata.return_value = GitHubMetadata(
            description="New",
            url="https://github.com/test",
            fetched_at=datetime.now(),
            topics=[],
        )

        # Filter by name pattern
        result = refresher.refresh_collection(artifact_filter={"name": "test-*"})

        # Only test-skill should be processed
        assert result.total_processed == 1
        assert result.entries[0].artifact_id == "skill:test-skill"

    def test_refresh_collection_dry_run(
        self, refresher, mock_collection, sample_artifact, sample_github_metadata
    ):
        """Test dry run mode - collection not saved."""
        mock_collection.artifacts = [sample_artifact]

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path"
        )
        refresher._metadata_extractor.fetch_metadata.return_value = sample_github_metadata

        result = refresher.refresh_collection(dry_run=True)

        assert result.refreshed_count == 1
        # Verify save was NOT called
        refresher._collection_manager.save_collection.assert_not_called()

    def test_refresh_collection_aggregates_counts(
        self, refresher, mock_collection, sample_artifact, sample_local_artifact
    ):
        """Test that counts are correctly aggregated."""
        mock_collection.artifacts = [sample_artifact, sample_local_artifact]

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path"
        )
        refresher._metadata_extractor.fetch_metadata.return_value = GitHubMetadata(
            description="New",
            url="https://github.com/test",
            fetched_at=datetime.now(),
            topics=[],
        )

        result = refresher.refresh_collection()

        # sample_artifact should be refreshed, sample_local_artifact should be skipped
        assert result.total_processed == 2
        assert result.refreshed_count == 1  # GitHub artifact
        assert result.skipped_count == 1  # Local artifact
        assert len(result.entries) == 2

    def test_refresh_collection_continues_on_error(
        self, refresher, mock_collection, sample_artifact
    ):
        """Test that processing continues even if one artifact has an error."""
        # Create two GitHub artifacts
        another_artifact = Artifact(
            name="another-skill",
            type=ArtifactType.SKILL,
            path="skills/another-skill",
            origin="github",
            metadata=ArtifactMetadata(title="Another Skill"),
            added=datetime.now(),
            upstream="https://github.com/user/repo/tree/main/another",
        )

        mock_collection.artifacts = [sample_artifact, another_artifact]

        # Make first artifact fail, second succeed
        call_count = [0]

        def mock_fetch_metadata(source):
            call_count[0] += 1
            if call_count[0] == 1:
                return None  # First call fails
            return GitHubMetadata(
                description="New",
                url="https://github.com/test",
                fetched_at=datetime.now(),
                topics=[],
            )

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path"
        )
        refresher._metadata_extractor.fetch_metadata.side_effect = mock_fetch_metadata

        result = refresher.refresh_collection()

        # Both should be processed (one error, one refreshed)
        assert result.total_processed == 2
        assert result.error_count == 1
        assert result.refreshed_count == 1

    def test_refresh_collection_empty(self, refresher, mock_collection):
        """Test refreshing empty collection."""
        mock_collection.artifacts = []

        result = refresher.refresh_collection()

        assert result.total_processed == 0
        assert result.refreshed_count == 0
        assert result.entries == []

    def test_refresh_collection_saves_on_changes(
        self, refresher, mock_collection, sample_artifact, sample_github_metadata
    ):
        """Test that collection is saved when changes are made."""
        mock_collection.artifacts = [sample_artifact]

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path"
        )
        refresher._metadata_extractor.fetch_metadata.return_value = sample_github_metadata

        result = refresher.refresh_collection(mode=RefreshMode.METADATA_ONLY)

        assert result.refreshed_count == 1
        # Verify save WAS called
        refresher._collection_manager.save_collection.assert_called_once()


# =============================================================================
# BE-118: TestGitHubApiMocking
# =============================================================================


class TestGitHubApiMocking:
    """Tests for GitHub API error handling (BE-118)."""

    def test_rate_limit_error(self, refresher, sample_artifact):
        """Test that GitHubRateLimitError is handled gracefully."""
        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path"
        )

        # Simulate rate limit error in fetch_metadata
        error = GitHubRateLimitError("Rate limit exceeded")
        error.reset_at = datetime.now()
        refresher._metadata_extractor.fetch_metadata.side_effect = error

        # The _fetch_upstream_metadata method catches this and returns None
        result = refresher.refresh_metadata(sample_artifact)

        assert result.status == "error"

    def test_not_found_error(self, refresher, sample_artifact):
        """Test that GitHubNotFoundError returns error status."""
        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path"
        )

        # Simulate not found error
        refresher._metadata_extractor.fetch_metadata.side_effect = GitHubNotFoundError(
            "Repository not found"
        )

        result = refresher.refresh_metadata(sample_artifact)

        assert result.status == "error"

    def test_generic_github_error(self, refresher, sample_artifact):
        """Test that GitHubClientError is handled gracefully."""
        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path"
        )

        # Simulate generic GitHub error
        refresher._metadata_extractor.fetch_metadata.side_effect = GitHubClientError(
            "API error"
        )

        result = refresher.refresh_metadata(sample_artifact)

        assert result.status == "error"

    def test_network_error(self, refresher, sample_artifact):
        """Test that network exceptions are caught and logged."""
        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path"
        )

        # Simulate network error
        refresher._metadata_extractor.fetch_metadata.side_effect = Exception(
            "Connection timeout"
        )

        result = refresher.refresh_metadata(sample_artifact)

        assert result.status == "error"

    def test_rate_limit_in_collection_refresh(
        self, refresher, mock_collection, sample_artifact
    ):
        """Test rate limit error during collection refresh."""
        mock_collection.artifacts = [sample_artifact]

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path"
        )

        # Simulate rate limit in _fetch_upstream_metadata (returns None)
        refresher._metadata_extractor.fetch_metadata.return_value = None

        result = refresher.refresh_collection()

        assert result.error_count == 1
        assert result.entries[0].status == "error"


# =============================================================================
# Additional Test Classes for Data Models
# =============================================================================


class TestRefreshEntryResult:
    """Tests for RefreshEntryResult data class."""

    def test_to_dict(self):
        """Test converting RefreshEntryResult to dictionary."""
        result = RefreshEntryResult(
            artifact_id="skill:test",
            status="refreshed",
            changes=["description", "tags"],
            old_values={"description": "old"},
            new_values={"description": "new"},
            duration_ms=150.5,
        )

        data = result.to_dict()

        assert data["artifact_id"] == "skill:test"
        assert data["status"] == "refreshed"
        assert data["changes"] == ["description", "tags"]
        assert data["old_values"] == {"description": "old"}
        assert data["new_values"] == {"description": "new"}
        assert data["duration_ms"] == 150.5

    def test_from_dict(self):
        """Test creating RefreshEntryResult from dictionary."""
        data = {
            "artifact_id": "skill:test",
            "status": "refreshed",
            "changes": ["description"],
            "old_values": {"description": "old"},
            "new_values": {"description": "new"},
            "duration_ms": 100.0,
        }

        result = RefreshEntryResult.from_dict(data)

        assert result.artifact_id == "skill:test"
        assert result.status == "refreshed"
        assert result.changes == ["description"]

    def test_default_values(self):
        """Test default values for RefreshEntryResult."""
        result = RefreshEntryResult(artifact_id="skill:test", status="unchanged")

        assert result.changes == []
        assert result.old_values is None
        assert result.new_values is None
        assert result.error is None
        assert result.reason is None
        assert result.duration_ms == 0.0


class TestRefreshResult:
    """Tests for RefreshResult data class."""

    def test_total_processed(self):
        """Test total_processed property."""
        result = RefreshResult(
            refreshed_count=5,
            unchanged_count=10,
            skipped_count=2,
            error_count=1,
        )

        assert result.total_processed == 18

    def test_success_rate(self):
        """Test success_rate calculation."""
        result = RefreshResult(
            refreshed_count=5,
            unchanged_count=10,
            skipped_count=2,
            error_count=1,
        )

        # (5 + 10) / 18 * 100 = 83.33
        assert result.success_rate == 83.33

    def test_success_rate_zero_processed(self):
        """Test success_rate when no artifacts processed."""
        result = RefreshResult()

        assert result.success_rate == 0.0

    def test_to_dict(self):
        """Test converting RefreshResult to dictionary."""
        entry = RefreshEntryResult(artifact_id="skill:test", status="refreshed")
        result = RefreshResult(
            refreshed_count=1,
            entries=[entry],
            duration_ms=500.0,
        )

        data = result.to_dict()

        assert data["refreshed_count"] == 1
        assert data["total_processed"] == 1
        assert data["success_rate"] == 100.0
        assert len(data["entries"]) == 1

    def test_from_dict(self):
        """Test creating RefreshResult from dictionary."""
        data = {
            "refreshed_count": 2,
            "unchanged_count": 3,
            "skipped_count": 1,
            "error_count": 0,
            "entries": [{"artifact_id": "skill:test", "status": "refreshed"}],
            "duration_ms": 250.0,
        }

        result = RefreshResult.from_dict(data)

        assert result.refreshed_count == 2
        assert result.unchanged_count == 3
        assert result.total_processed == 6
        assert len(result.entries) == 1


class TestRefreshMode:
    """Tests for RefreshMode enum."""

    def test_metadata_only_value(self):
        """Test METADATA_ONLY enum value."""
        assert RefreshMode.METADATA_ONLY.value == "metadata_only"

    def test_check_only_value(self):
        """Test CHECK_ONLY enum value."""
        assert RefreshMode.CHECK_ONLY.value == "check_only"

    def test_sync_value(self):
        """Test SYNC enum value."""
        assert RefreshMode.SYNC.value == "sync"


class TestRefreshFieldMapping:
    """Tests for REFRESH_FIELD_MAPPING constant."""

    def test_required_fields_present(self):
        """Test that required field mappings are present."""
        assert "description" in REFRESH_FIELD_MAPPING
        assert "tags" in REFRESH_FIELD_MAPPING
        assert "author" in REFRESH_FIELD_MAPPING
        assert "license" in REFRESH_FIELD_MAPPING
        assert "origin_source" in REFRESH_FIELD_MAPPING

    def test_field_mapping_values(self):
        """Test field mapping values are correct."""
        assert REFRESH_FIELD_MAPPING["description"] == "description"
        assert REFRESH_FIELD_MAPPING["tags"] == "topics"
        assert REFRESH_FIELD_MAPPING["license"] == "license"


# =============================================================================
# Additional Edge Case Tests for Better Coverage
# =============================================================================


class TestCollectionErrorHandling:
    """Tests for collection loading and error handling."""

    def test_refresh_collection_load_error_value_error(
        self, mock_collection_manager, mock_metadata_extractor
    ):
        """Test handling of ValueError when loading collection."""
        mock_collection_manager.load_collection.side_effect = ValueError(
            "Collection not found"
        )

        refresher = CollectionRefresher(
            collection_manager=mock_collection_manager,
            metadata_extractor=mock_metadata_extractor,
        )

        with pytest.raises(ValueError, match="Collection not found"):
            refresher.refresh_collection()

    def test_refresh_collection_load_error_generic(
        self, mock_collection_manager, mock_metadata_extractor
    ):
        """Test handling of generic Exception when loading collection."""
        mock_collection_manager.load_collection.side_effect = RuntimeError(
            "Database connection failed"
        )

        refresher = CollectionRefresher(
            collection_manager=mock_collection_manager,
            metadata_extractor=mock_metadata_extractor,
        )

        with pytest.raises(ValueError, match="Failed to load collection"):
            refresher.refresh_collection()


class TestRefreshCollectionExceptionHandling:
    """Tests for exception handling during collection refresh iteration."""

    def test_rate_limit_error_during_iteration(
        self, refresher, mock_collection, sample_artifact
    ):
        """Test GitHubRateLimitError is caught during refresh_metadata call."""
        mock_collection.artifacts = [sample_artifact]

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path"
        )

        # Simulate rate limit error being raised from refresh_metadata
        error = GitHubRateLimitError("API rate limit exceeded")
        error.message = "API rate limit exceeded"

        # Make refresh_metadata itself raise the error (not via fetch_metadata)
        original_refresh_metadata = refresher.refresh_metadata

        def raise_rate_limit(*args, **kwargs):
            raise error

        refresher.refresh_metadata = raise_rate_limit

        result = refresher.refresh_collection()

        assert result.error_count == 1
        assert len(result.entries) == 1
        assert result.entries[0].status == "error"
        assert "rate limit" in result.entries[0].reason.lower()

    def test_unexpected_error_during_iteration(
        self, refresher, mock_collection, sample_artifact
    ):
        """Test generic Exception is caught during iteration."""
        mock_collection.artifacts = [sample_artifact]

        # Make refresh_metadata raise an unexpected error
        def raise_unexpected(*args, **kwargs):
            raise RuntimeError("Unexpected processing error")

        refresher.refresh_metadata = raise_unexpected

        result = refresher.refresh_collection()

        assert result.error_count == 1
        assert len(result.entries) == 1
        assert result.entries[0].status == "error"
        assert "Unexpected processing error" in result.entries[0].error

    def test_save_collection_error_does_not_raise(
        self, refresher, mock_collection, sample_artifact, sample_github_metadata
    ):
        """Test that collection save error is logged but doesn't raise."""
        mock_collection.artifacts = [sample_artifact]

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path"
        )
        refresher._metadata_extractor.fetch_metadata.return_value = sample_github_metadata

        # Make save_collection fail
        refresher._collection_manager.save_collection.side_effect = IOError(
            "Disk full"
        )

        # Should NOT raise, just log the error
        result = refresher.refresh_collection()

        # The refresh should still report success for the artifact
        assert result.refreshed_count == 1


class TestFetchUpstreamMetadataEdgeCases:
    """Additional tests for _fetch_upstream_metadata edge cases."""

    def test_fetch_metadata_returns_none_on_value_error(
        self, mock_collection_manager, mock_metadata_extractor
    ):
        """Test that ValueError from fetch_metadata returns None."""
        refresher = CollectionRefresher(
            collection_manager=mock_collection_manager,
            metadata_extractor=mock_metadata_extractor,
        )

        mock_metadata_extractor.fetch_metadata.side_effect = ValueError(
            "Invalid source"
        )

        spec = GitHubSourceSpec(owner="user", repo="repo", path="path")
        result = refresher._fetch_upstream_metadata(spec)

        assert result is None


class TestDetectChangesEdgeCases:
    """Additional edge case tests for _detect_changes."""

    def test_detect_changes_with_unknown_field(
        self, refresher, sample_artifact, sample_github_metadata
    ):
        """Test that unknown fields are skipped with warning."""
        old_values, new_values = refresher._detect_changes(
            sample_artifact,
            sample_github_metadata,
            fields=["description", "unknown_field"],
        )

        # Should have processed description but skipped unknown_field
        assert "unknown_field" not in new_values

    def test_detect_changes_empty_string_vs_none(self, refresher, sample_artifact):
        """Test that empty string is treated as equivalent to None."""
        sample_artifact.metadata.description = ""

        upstream = GitHubMetadata(
            description=None,
            url="https://github.com/test",
            fetched_at=datetime.now(),
            topics=[],
        )

        old_values, new_values = refresher._detect_changes(
            sample_artifact, upstream, fields=["description"]
        )

        # Empty string and None should be considered equivalent
        assert "description" not in new_values


class TestGetArtifactFieldValue:
    """Tests for _get_artifact_field_value helper."""

    def test_get_unknown_field_returns_none(self, refresher, sample_artifact):
        """Test that unknown fields return None."""
        result = refresher._get_artifact_field_value(sample_artifact, "nonexistent")
        assert result is None


class TestGetUpstreamFieldValue:
    """Tests for _get_upstream_field_value helper."""

    def test_get_unknown_upstream_field_returns_none(
        self, refresher, sample_github_metadata
    ):
        """Test that unknown upstream fields return None."""
        result = refresher._get_upstream_field_value(
            sample_github_metadata, "nonexistent"
        )
        assert result is None


class TestApplyUpdatesEdgeCases:
    """Additional edge case tests for _apply_updates."""

    def test_apply_unknown_field_skipped(self, refresher, sample_artifact):
        """Test that unknown fields in updates are skipped with warning."""
        old_values = {"unknown_field": "old"}
        new_values = {"unknown_field": "new"}

        # Should not raise, just log warning and skip
        updated = refresher._apply_updates(sample_artifact, old_values, new_values)

        # Artifact should be unchanged for known fields
        assert updated.name == sample_artifact.name


class TestFilterArtifactsEdgeCases:
    """Tests for _filter_artifacts edge cases."""

    def test_filter_by_invalid_type_string(
        self, refresher, mock_collection, sample_artifact
    ):
        """Test filtering with invalid type string is handled gracefully.

        When an invalid type string is provided, the filter becomes None
        (after logging a warning), so artifacts are not filtered by type.
        """
        mock_collection.artifacts = [sample_artifact]

        # Invalid type string - should log warning and not filter
        filtered = refresher._filter_artifacts(
            mock_collection.artifacts, {"type": "invalid_type"}
        )

        # Invalid type is treated as no type filter, so all artifacts returned
        assert filtered == [sample_artifact]

    def test_filter_by_glob_pattern(
        self, refresher, mock_collection, sample_artifact
    ):
        """Test filtering with glob wildcard pattern."""
        another = Artifact(
            name="test-other",
            type=ArtifactType.SKILL,
            path="skills/test-other",
            origin="github",
            metadata=ArtifactMetadata(title="Other"),
            added=datetime.now(),
            upstream="https://github.com/user/repo/tree/main/other",
        )
        mock_collection.artifacts = [sample_artifact, another]

        # Glob pattern with * wildcard
        filtered = refresher._filter_artifacts(
            mock_collection.artifacts, {"name": "*-skill"}
        )

        # Should match test-skill only
        assert len(filtered) == 1
        assert filtered[0].name == "test-skill"


class TestLazyInitialization:
    """Tests for lazy initialization of dependencies."""

    def test_metadata_extractor_lazy_init(self, mock_collection_manager):
        """Test that metadata_extractor is lazily initialized."""
        from skillmeat.core.github_metadata import GitHubMetadataExtractor

        refresher = CollectionRefresher(
            collection_manager=mock_collection_manager,
            metadata_extractor=None,  # Not provided
        )

        # Accessing the property should create the extractor
        extractor = refresher.metadata_extractor

        assert extractor is not None
        assert isinstance(extractor, GitHubMetadataExtractor)

    def test_github_client_lazy_init(self, mock_collection_manager):
        """Test that github_client is lazily initialized."""
        from skillmeat.core.github_client import GitHubClient

        refresher = CollectionRefresher(
            collection_manager=mock_collection_manager,
            github_client=None,  # Not provided
        )

        # Accessing the property should create the client
        client = refresher.github_client

        assert client is not None
        assert isinstance(client, GitHubClient)
