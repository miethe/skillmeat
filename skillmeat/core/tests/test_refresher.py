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
    UpdateAvailableResult,
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
def sample_artifact_with_sha():
    """Create a sample artifact with a resolved SHA."""
    return Artifact(
        name="versioned-skill",
        type=ArtifactType.SKILL,
        path="skills/versioned-skill",
        origin="github",
        metadata=ArtifactMetadata(
            title="Versioned Skill",
            description="A skill with version tracking",
        ),
        added=datetime.now(),
        upstream="https://github.com/user/repo/tree/main/path/to/skill",
        resolved_sha="abc123def456789012345678901234567890abcd",
        version_spec="latest",
        tags=["versioned"],
        origin_source=None,
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

    def test_tags_not_detected_as_change(self, refresher, sample_artifact):
        """Test that tags/topics changes are NOT detected.

        GitHub repository topics are SOURCE-level metadata, not artifact-level.
        Artifact tags should come from path-based segments or manual tagging.
        """
        upstream = GitHubMetadata(
            topics=["new-tag", "another-tag"],
            url="https://github.com/test",
            fetched_at=datetime.now(),
        )

        old_values, new_values = refresher._detect_changes(
            sample_artifact, upstream, fields=["description"]  # tags not valid
        )

        # Tags should NOT be in the changes since it's not in REFRESH_FIELD_MAPPING
        assert "tags" not in new_values
        assert "tags" not in old_values

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
        """Test that identical metadata returns no changes.

        Note: _detect_changes() now always checks ALL fields in REFRESH_FIELD_MAPPING
        regardless of the fields parameter. The fields parameter is used later by
        _apply_updates() to filter which changes get applied.
        """
        upstream = GitHubMetadata(
            description="Original description",  # Same as artifact
            topics=["old-tag"],  # topics are NOT in REFRESH_FIELD_MAPPING
            url="https://github.com/test",
            fetched_at=datetime.now(),
        )

        old_values, new_values = refresher._detect_changes(
            sample_artifact, upstream, fields=["description"]
        )

        # When all refreshable fields match, no changes should be detected
        # Note: tags/topics are NOT checked since they're not in REFRESH_FIELD_MAPPING
        assert old_values == {}
        assert new_values == {}

    def test_detect_multiple_changes(self, refresher, sample_artifact):
        """Test detecting multiple field changes at once.

        Note: _detect_changes() checks ALL fields in REFRESH_FIELD_MAPPING.
        The fields parameter is used later by _apply_updates() to filter which
        changes get applied. Tags/topics are NOT checked since they're not in
        REFRESH_FIELD_MAPPING (GitHub topics are source-level, not artifact-level).
        """
        sample_artifact.metadata.license = "Apache-2.0"

        upstream = GitHubMetadata(
            description="New description",
            license="MIT",
            topics=["new-tag"],  # topics NOT in REFRESH_FIELD_MAPPING
            url="https://github.com/test",
            fetched_at=datetime.now(),
        )

        old_values, new_values = refresher._detect_changes(
            sample_artifact, upstream, fields=["description", "license"]
        )

        # Only fields in REFRESH_FIELD_MAPPING are detected
        # (description, author, license - NOT tags)
        assert len(new_values) == 2  # description, license
        assert "description" in new_values
        assert "license" in new_values
        assert "tags" not in new_values  # tags NOT in REFRESH_FIELD_MAPPING

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

    def test_handle_empty_lists_not_for_tags(self, refresher, sample_artifact):
        """Test that tags/topics are NOT detected even with empty vs populated list.

        GitHub repository topics are SOURCE-level metadata, not artifact-level.
        Tags should come from path-based segments or manual tagging.
        """
        sample_artifact.tags = []

        upstream = GitHubMetadata(
            topics=["new-tag"],  # topics NOT in REFRESH_FIELD_MAPPING
            url="https://github.com/test",
            fetched_at=datetime.now(),
        )

        old_values, new_values = refresher._detect_changes(
            sample_artifact, upstream, fields=["description"]
        )

        # Tags should NOT be detected since they're not in REFRESH_FIELD_MAPPING
        assert "tags" not in new_values
        assert "tags" not in old_values

    def test_field_filtering_only_specified_fields(self, refresher, sample_artifact):
        """Test that changed fields in REFRESH_FIELD_MAPPING are detected.

        Note: Only fields in REFRESH_FIELD_MAPPING are checked for changes.
        Tags/topics are NOT in the mapping since GitHub repo topics are
        source-level metadata, not artifact-level.
        """
        upstream = GitHubMetadata(
            description="New description",
            license="MIT",
            topics=["new-tag"],  # topics NOT in REFRESH_FIELD_MAPPING
            url="https://github.com/test",
            fetched_at=datetime.now(),
        )

        # Specify only description, but all REFRESH_FIELD_MAPPING fields are checked
        old_values, new_values = refresher._detect_changes(
            sample_artifact, upstream, fields=["description"]
        )

        # Only fields in REFRESH_FIELD_MAPPING are detected (NOT tags)
        # description + license (None->MIT) = 2 fields
        assert len(new_values) == 2  # description, license
        assert "description" in new_values
        assert "license" in new_values  # License changes from None to MIT
        assert "tags" not in new_values  # tags NOT in REFRESH_FIELD_MAPPING

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
        """Test refresh when upstream metadata matches current.

        Note: _detect_changes() checks ALL fields in REFRESH_FIELD_MAPPING.
        Tags/topics are NOT in the mapping (they're source-level metadata).
        """
        # Create matching metadata - matching the artifact's current values
        matching_metadata = GitHubMetadata(
            description="Original description",  # Same as sample_artifact
            topics=["old-tag"],  # topics NOT in REFRESH_FIELD_MAPPING
            author=None,  # Same as sample_artifact.metadata.author
            license=None,  # Same as sample_artifact.metadata.license
            url="https://github.com/user/repo/tree/main/path/to/skill",
            fetched_at=datetime.now(),
        )

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path/to/skill"
        )
        refresher._metadata_extractor.fetch_metadata.return_value = matching_metadata

        # All REFRESH_FIELD_MAPPING fields checked, but since they match, no changes
        # Note: "tags" is NOT in REFRESH_FIELD_MAPPING
        result = refresher.refresh_metadata(
            sample_artifact,
            mode=RefreshMode.METADATA_ONLY,
            fields=["description", "author", "license"],  # Valid fields only
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
        assert "author" in REFRESH_FIELD_MAPPING
        assert "license" in REFRESH_FIELD_MAPPING
        # NOTE: "tags" is intentionally EXCLUDED from REFRESH_FIELD_MAPPING
        # GitHub repository topics are SOURCE-level metadata, not artifact-level.
        # Artifact tags should come from path-based segments or manual tagging.
        assert "tags" not in REFRESH_FIELD_MAPPING

    def test_field_mapping_values(self):
        """Test field mapping values are correct."""
        assert REFRESH_FIELD_MAPPING["description"] == "description"
        assert REFRESH_FIELD_MAPPING["author"] == "author"
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


# =============================================================================
# BE-401: TestUpdateAvailableResult
# =============================================================================


class TestUpdateAvailableResult:
    """Tests for UpdateAvailableResult data class."""

    def test_to_dict(self):
        """Test converting UpdateAvailableResult to dictionary."""
        result = UpdateAvailableResult(
            artifact_id="skill:test",
            artifact_name="test",
            current_sha="abc123",
            upstream_sha="def456",
            update_available=True,
            reason="SHA mismatch",
            merge_strategy="safe_update",
        )

        data = result.to_dict()

        assert data["artifact_id"] == "skill:test"
        assert data["artifact_name"] == "test"
        assert data["current_sha"] == "abc123"
        assert data["upstream_sha"] == "def456"
        assert data["update_available"] is True
        assert data["reason"] == "SHA mismatch"
        assert data["merge_strategy"] == "safe_update"
        assert data["has_local_changes"] is False

    def test_from_dict(self):
        """Test creating UpdateAvailableResult from dictionary."""
        data = {
            "artifact_id": "skill:test",
            "artifact_name": "test",
            "current_sha": "abc123",
            "upstream_sha": "def456",
            "update_available": True,
            "reason": "SHA mismatch",
            "merge_strategy": "safe_update",
        }

        result = UpdateAvailableResult.from_dict(data)

        assert result.artifact_id == "skill:test"
        assert result.artifact_name == "test"
        assert result.current_sha == "abc123"
        assert result.upstream_sha == "def456"
        assert result.update_available is True
        assert result.reason == "SHA mismatch"
        assert result.merge_strategy == "safe_update"

    def test_default_values(self):
        """Test default values for UpdateAvailableResult."""
        result = UpdateAvailableResult(
            artifact_id="skill:test",
            artifact_name="test",
        )

        assert result.current_sha is None
        assert result.upstream_sha is None
        assert result.update_available is False
        assert result.reason is None
        assert result.drift_info is None
        assert result.has_local_changes is False
        assert result.merge_strategy == "no_update"

    def test_from_dict_missing_optional_fields(self):
        """Test creating from dict with missing optional fields."""
        data = {
            "artifact_id": "skill:test",
            "artifact_name": "test",
        }

        result = UpdateAvailableResult.from_dict(data)

        assert result.current_sha is None
        assert result.upstream_sha is None
        assert result.update_available is False
        assert result.reason is None
        assert result.merge_strategy == "no_update"

    def test_invalid_merge_strategy_raises_error(self):
        """Test that invalid merge_strategy raises ValueError."""
        with pytest.raises(ValueError, match="Invalid merge_strategy"):
            UpdateAvailableResult(
                artifact_id="skill:test",
                artifact_name="test",
                merge_strategy="invalid_strategy",
            )

    def test_valid_merge_strategies(self):
        """Test all valid merge strategies."""
        valid_strategies = ["safe_update", "review_required", "conflict", "no_update"]

        for strategy in valid_strategies:
            result = UpdateAvailableResult(
                artifact_id="skill:test",
                artifact_name="test",
                merge_strategy=strategy,
            )
            assert result.merge_strategy == strategy


# =============================================================================
# BE-401: TestCheckUpdates
# =============================================================================


class TestCheckUpdates:
    """Tests for check_updates() method (BE-401)."""

    def test_check_updates_no_update_available(
        self, refresher, mock_collection, sample_artifact_with_sha
    ):
        """Test checking updates when artifact is up to date."""
        mock_collection.artifacts = [sample_artifact_with_sha]

        # Mock the metadata extractor and github_client
        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path/to/skill"
        )

        mock_github_client = MagicMock()
        # Return the same SHA as the artifact has
        mock_github_client.resolve_version.return_value = (
            "abc123def456789012345678901234567890abcd"
        )
        refresher._github_client = mock_github_client

        results = refresher.check_updates()

        assert len(results) == 1
        assert results[0].artifact_id == "skill:versioned-skill"
        assert results[0].update_available is False
        assert results[0].reason == "Up to date"

    def test_check_updates_update_available(
        self, refresher, mock_collection, sample_artifact_with_sha
    ):
        """Test checking updates when an update is available."""
        mock_collection.artifacts = [sample_artifact_with_sha]

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path/to/skill"
        )

        mock_github_client = MagicMock()
        # Return a different SHA
        mock_github_client.resolve_version.return_value = (
            "new789sha456789012345678901234567890new1"
        )
        refresher._github_client = mock_github_client

        results = refresher.check_updates()

        assert len(results) == 1
        assert results[0].artifact_id == "skill:versioned-skill"
        assert results[0].update_available is True
        assert results[0].reason == "SHA mismatch"
        assert results[0].current_sha == "abc123def456789012345678901234567890abcd"
        assert results[0].upstream_sha == "new789sha456789012345678901234567890new1"

    def test_check_updates_skips_local_artifacts(
        self, refresher, mock_collection, sample_local_artifact
    ):
        """Test that local artifacts are skipped with reason."""
        mock_collection.artifacts = [sample_local_artifact]

        results = refresher.check_updates()

        assert len(results) == 1
        assert results[0].artifact_id == "skill:local-skill"
        assert results[0].update_available is False
        assert results[0].reason == "No GitHub source"

    def test_check_updates_no_current_sha(
        self, refresher, mock_collection, sample_artifact
    ):
        """Test checking updates when artifact has no resolved_sha."""
        # sample_artifact doesn't have a resolved_sha
        mock_collection.artifacts = [sample_artifact]

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path/to/skill"
        )

        mock_github_client = MagicMock()
        mock_github_client.resolve_version.return_value = (
            "upstream123456789012345678901234567890ab"
        )
        refresher._github_client = mock_github_client

        results = refresher.check_updates()

        assert len(results) == 1
        assert results[0].update_available is True
        assert results[0].reason == "No current SHA stored"

    def test_check_updates_rate_limit_error(
        self, refresher, mock_collection, sample_artifact_with_sha
    ):
        """Test handling of rate limit errors during update check."""
        mock_collection.artifacts = [sample_artifact_with_sha]

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path"
        )

        mock_github_client = MagicMock()
        error = GitHubRateLimitError("Rate limit exceeded")
        error.message = "Rate limit exceeded"
        mock_github_client.resolve_version.side_effect = error
        refresher._github_client = mock_github_client

        results = refresher.check_updates()

        assert len(results) == 1
        assert results[0].update_available is False
        assert "Rate limit exceeded" in results[0].reason

    def test_check_updates_not_found_error(
        self, refresher, mock_collection, sample_artifact_with_sha
    ):
        """Test handling of not found errors during update check."""
        mock_collection.artifacts = [sample_artifact_with_sha]

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path"
        )

        mock_github_client = MagicMock()
        error = GitHubNotFoundError("Resource not found")
        error.message = "Resource not found"
        mock_github_client.resolve_version.side_effect = error
        refresher._github_client = mock_github_client

        results = refresher.check_updates()

        assert len(results) == 1
        assert results[0].update_available is False
        assert "Upstream not found" in results[0].reason

    def test_check_updates_generic_github_error(
        self, refresher, mock_collection, sample_artifact_with_sha
    ):
        """Test handling of generic GitHub errors during update check."""
        mock_collection.artifacts = [sample_artifact_with_sha]

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path"
        )

        mock_github_client = MagicMock()
        error = GitHubClientError("API error")
        error.message = "API error"
        mock_github_client.resolve_version.side_effect = error
        refresher._github_client = mock_github_client

        results = refresher.check_updates()

        assert len(results) == 1
        assert results[0].update_available is False
        assert "Error" in results[0].reason

    def test_check_updates_with_type_filter(
        self, refresher, mock_collection, sample_artifact_with_sha
    ):
        """Test filtering check_updates by artifact type."""
        # Create a command artifact
        command_artifact = Artifact(
            name="test-command",
            type=ArtifactType.COMMAND,
            path="commands/test-command.md",
            origin="github",
            metadata=ArtifactMetadata(title="Test Command"),
            added=datetime.now(),
            upstream="https://github.com/user/repo/tree/main/command",
            resolved_sha="cmd123456789012345678901234567890abcdef",
        )

        mock_collection.artifacts = [sample_artifact_with_sha, command_artifact]

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path"
        )

        mock_github_client = MagicMock()
        mock_github_client.resolve_version.return_value = (
            "abc123def456789012345678901234567890abcd"
        )
        refresher._github_client = mock_github_client

        # Filter by skill type only
        results = refresher.check_updates(artifact_filter={"type": "skill"})

        assert len(results) == 1
        assert results[0].artifact_id == "skill:versioned-skill"

    def test_check_updates_with_name_filter(
        self, refresher, mock_collection, sample_artifact_with_sha
    ):
        """Test filtering check_updates by name pattern."""
        another_artifact = Artifact(
            name="other-skill",
            type=ArtifactType.SKILL,
            path="skills/other-skill",
            origin="github",
            metadata=ArtifactMetadata(title="Other Skill"),
            added=datetime.now(),
            upstream="https://github.com/user/repo/tree/main/other",
            resolved_sha="other23456789012345678901234567890abcdef",
        )

        mock_collection.artifacts = [sample_artifact_with_sha, another_artifact]

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path"
        )

        mock_github_client = MagicMock()
        mock_github_client.resolve_version.return_value = (
            "abc123def456789012345678901234567890abcd"
        )
        refresher._github_client = mock_github_client

        # Filter by name pattern
        results = refresher.check_updates(artifact_filter={"name": "versioned-*"})

        assert len(results) == 1
        assert results[0].artifact_id == "skill:versioned-skill"

    def test_check_updates_empty_collection(self, refresher, mock_collection):
        """Test check_updates with empty collection."""
        mock_collection.artifacts = []

        results = refresher.check_updates()

        assert results == []

    def test_check_updates_short_sha_comparison(
        self, refresher, mock_collection
    ):
        """Test that short SHA is properly compared against full SHA."""
        artifact = Artifact(
            name="short-sha-skill",
            type=ArtifactType.SKILL,
            path="skills/short-sha-skill",
            origin="github",
            metadata=ArtifactMetadata(title="Short SHA Skill"),
            added=datetime.now(),
            upstream="https://github.com/user/repo/tree/main/skill",
            resolved_sha="abc1234",  # Short SHA (7 chars)
            version_spec="latest",
        )

        mock_collection.artifacts = [artifact]

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="skill"
        )

        mock_github_client = MagicMock()
        # Return full SHA (40 chars) that starts with same prefix
        mock_github_client.resolve_version.return_value = (
            "abc1234def456789012345678901234567890abc"  # Exactly 40 chars
        )
        refresher._github_client = mock_github_client

        results = refresher.check_updates()

        assert len(results) == 1
        assert results[0].update_available is False  # Should match prefix
        assert results[0].reason == "Up to date"

    def test_check_updates_short_sha_mismatch(
        self, refresher, mock_collection
    ):
        """Test that short SHA mismatch is detected."""
        artifact = Artifact(
            name="short-sha-skill",
            type=ArtifactType.SKILL,
            path="skills/short-sha-skill",
            origin="github",
            metadata=ArtifactMetadata(title="Short SHA Skill"),
            added=datetime.now(),
            upstream="https://github.com/user/repo/tree/main/skill",
            resolved_sha="abc1234",  # Short SHA (7 chars)
            version_spec="latest",
        )

        mock_collection.artifacts = [artifact]

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="skill"
        )

        mock_github_client = MagicMock()
        # Return full SHA that does NOT start with same prefix
        mock_github_client.resolve_version.return_value = (
            "def5678def456789012345678901234567890ab"
        )
        refresher._github_client = mock_github_client

        results = refresher.check_updates()

        assert len(results) == 1
        assert results[0].update_available is True
        assert results[0].reason == "SHA mismatch"

    def test_check_updates_marketplace_artifact(
        self, refresher, mock_collection, sample_marketplace_artifact
    ):
        """Test check_updates with marketplace artifact (has origin_source=github)."""
        # Add resolved_sha to marketplace artifact
        sample_marketplace_artifact.resolved_sha = "mkt123456789012345678901234567890abcdef"
        mock_collection.artifacts = [sample_marketplace_artifact]

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="marketplace", repo="skills", path="popular-skill"
        )

        mock_github_client = MagicMock()
        # Return different SHA to simulate update
        mock_github_client.resolve_version.return_value = (
            "newupstream789012345678901234567890abcd"
        )
        refresher._github_client = mock_github_client

        results = refresher.check_updates()

        assert len(results) == 1
        assert results[0].artifact_id == "skill:marketplace-skill"
        assert results[0].update_available is True

    def test_check_updates_invalid_source_format(
        self, refresher, mock_collection, sample_artifact_with_sha
    ):
        """Test handling of invalid source format."""
        mock_collection.artifacts = [sample_artifact_with_sha]

        refresher._metadata_extractor = MagicMock()
        # Return None to simulate invalid source format
        refresher._metadata_extractor.parse_github_url.return_value = None

        results = refresher.check_updates()

        assert len(results) == 1
        assert results[0].update_available is False
        assert "Invalid source format" in results[0].reason

    def test_check_updates_parse_source_error(
        self, refresher, mock_collection, sample_artifact_with_sha
    ):
        """Test handling of source parsing errors."""
        mock_collection.artifacts = [sample_artifact_with_sha]

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.side_effect = ValueError(
            "Malformed URL"
        )

        results = refresher.check_updates()

        assert len(results) == 1
        assert results[0].update_available is False
        assert "Error parsing source" in results[0].reason

    def test_check_updates_collection_load_error(
        self, mock_collection_manager, mock_metadata_extractor
    ):
        """Test handling of collection load errors."""
        mock_collection_manager.load_collection.side_effect = ValueError(
            "Collection not found"
        )

        refresher = CollectionRefresher(
            collection_manager=mock_collection_manager,
            metadata_extractor=mock_metadata_extractor,
        )

        with pytest.raises(ValueError, match="Collection not found"):
            refresher.check_updates()

    def test_check_updates_both_short_sha_match(self, refresher, mock_collection):
        """Test that two short SHAs (both <40 chars) are compared correctly when matching."""
        artifact = Artifact(
            name="short-sha-skill",
            type=ArtifactType.SKILL,
            path="skills/short-sha-skill",
            origin="github",
            metadata=ArtifactMetadata(title="Short SHA Skill"),
            added=datetime.now(),
            upstream="https://github.com/user/repo/tree/main/skill",
            resolved_sha="abc1234",  # Short SHA (7 chars)
            version_spec="latest",
        )

        mock_collection.artifacts = [artifact]

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="skill"
        )

        mock_github_client = MagicMock()
        # Return a different short SHA (7 chars)
        mock_github_client.resolve_version.return_value = "abc1234"  # Matches current
        refresher._github_client = mock_github_client

        results = refresher.check_updates()

        assert len(results) == 1
        assert results[0].update_available is False  # Should match
        assert results[0].reason == "Up to date"

    def test_check_updates_both_short_sha_mismatch(self, refresher, mock_collection):
        """Test that two short SHAs (both <40 chars) are compared correctly when different."""
        artifact = Artifact(
            name="short-sha-skill",
            type=ArtifactType.SKILL,
            path="skills/short-sha-skill",
            origin="github",
            metadata=ArtifactMetadata(title="Short SHA Skill"),
            added=datetime.now(),
            upstream="https://github.com/user/repo/tree/main/skill",
            resolved_sha="abc1234",  # Short SHA (7 chars)
            version_spec="latest",
        )

        mock_collection.artifacts = [artifact]

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="skill"
        )

        mock_github_client = MagicMock()
        # Return a different short SHA (7 chars)
        mock_github_client.resolve_version.return_value = "def5678"  # Different prefix
        refresher._github_client = mock_github_client

        results = refresher.check_updates()

        assert len(results) == 1
        assert results[0].update_available is True  # Should detect mismatch
        assert results[0].reason == "SHA mismatch"

    def test_check_updates_unexpected_exception(
        self, refresher, mock_collection, sample_artifact_with_sha
    ):
        """Test handling of unexpected exceptions during update check."""
        mock_collection.artifacts = [sample_artifact_with_sha]

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path"
        )

        mock_github_client = MagicMock()
        # Simulate unexpected exception (not a GitHub-specific error)
        mock_github_client.resolve_version.side_effect = RuntimeError(
            "Unexpected network issue"
        )
        refresher._github_client = mock_github_client

        results = refresher.check_updates()

        assert len(results) == 1
        assert results[0].update_available is False
        assert "Error" in results[0].reason
        assert "Unexpected network issue" in results[0].reason

    def test_check_updates_marketplace_artifact_no_origin_source(
        self, refresher, mock_collection
    ):
        """Test that marketplace artifact without origin_source is skipped."""
        artifact = Artifact(
            name="marketplace-no-source",
            type=ArtifactType.SKILL,
            path="skills/marketplace-no-source",
            origin="marketplace",
            origin_source=None,  # No origin_source specified
            metadata=ArtifactMetadata(title="Marketplace Skill No Source"),
            added=datetime.now(),
            upstream="https://some-marketplace-url.com/skill",
            resolved_sha="mkt123456789012345678901234567890abcdef",
        )

        mock_collection.artifacts = [artifact]

        results = refresher.check_updates()

        assert len(results) == 1
        assert results[0].update_available is False
        assert results[0].reason == "No GitHub source"
        # Should be skipped because origin=marketplace but origin_source != "github"

    def test_check_updates_multiple_artifacts_mixed_results(
        self, refresher, mock_collection, sample_artifact_with_sha, sample_local_artifact
    ):
        """Test check_updates with multiple artifacts having different statuses."""
        # Create another GitHub artifact that will have an update
        updated_artifact = Artifact(
            name="needs-update-skill",
            type=ArtifactType.SKILL,
            path="skills/needs-update-skill",
            origin="github",
            metadata=ArtifactMetadata(title="Needs Update"),
            added=datetime.now(),
            upstream="https://github.com/user/repo/tree/main/needs-update",
            resolved_sha="old123456789012345678901234567890abcdef",
        )

        mock_collection.artifacts = [
            sample_artifact_with_sha,
            sample_local_artifact,
            updated_artifact,
        ]

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="skill"
        )

        mock_github_client = MagicMock()

        def resolve_version_mock(owner_repo, version):
            # First call (versioned-skill) - return same SHA (up to date)
            # Second call (needs-update-skill) - return different SHA (update available)
            if resolve_version_mock.call_count == 1:
                return "abc123def456789012345678901234567890abcd"
            else:
                return "new456789012345678901234567890abcdefgh"

        resolve_version_mock.call_count = 0

        def side_effect_wrapper(*args, **kwargs):
            resolve_version_mock.call_count += 1
            return resolve_version_mock(*args, **kwargs)

        mock_github_client.resolve_version.side_effect = side_effect_wrapper
        refresher._github_client = mock_github_client

        results = refresher.check_updates()

        assert len(results) == 3

        # Find each result by artifact name
        result_map = {r.artifact_name: r for r in results}

        # versioned-skill should be up to date
        assert result_map["versioned-skill"].update_available is False

        # local-skill should be skipped
        assert result_map["local-skill"].update_available is False
        assert "No GitHub source" in result_map["local-skill"].reason

        # needs-update-skill should have an update
        assert result_map["needs-update-skill"].update_available is True


# =============================================================================
# BE-402: TestCheckUpdatesDriftIntegration
# =============================================================================


class TestCheckUpdatesDriftIntegration:
    """Tests for check_updates() integration with SyncManager.check_drift() (BE-402).

    These tests verify that check_updates() correctly enriches UpdateAvailableResult
    with drift detection information when project_path is provided.
    """

    def test_check_updates_with_project_path_no_drift(
        self, refresher, mock_collection, sample_artifact_with_sha
    ):
        """Test check_updates with project_path when no drift detected."""
        mock_collection.artifacts = [sample_artifact_with_sha]

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path/to/skill"
        )

        mock_github_client = MagicMock()
        # Return different SHA to simulate update available
        mock_github_client.resolve_version.return_value = (
            "new789sha456789012345678901234567890new1"
        )
        refresher._github_client = mock_github_client

        # Mock SyncManager to return empty drift results (no drift)
        with patch("skillmeat.core.sync.SyncManager") as MockSyncManager:
            mock_sync_manager = MagicMock()
            mock_sync_manager.check_drift.return_value = []  # No drift
            MockSyncManager.return_value = mock_sync_manager

            from pathlib import Path

            results = refresher.check_updates(project_path=Path("/tmp/test-project"))

        assert len(results) == 1
        assert results[0].update_available is True
        assert results[0].drift_info is None
        assert results[0].has_local_changes is False
        assert results[0].merge_strategy == "safe_update"

    def test_check_updates_with_drift_modified(
        self, refresher, mock_collection, sample_artifact_with_sha
    ):
        """Test check_updates with drift detection showing local modifications."""
        from skillmeat.models import DriftDetectionResult

        mock_collection.artifacts = [sample_artifact_with_sha]

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path/to/skill"
        )

        mock_github_client = MagicMock()
        mock_github_client.resolve_version.return_value = (
            "new789sha456789012345678901234567890new1"
        )
        refresher._github_client = mock_github_client

        # Create drift result indicating local modifications
        drift_result = DriftDetectionResult(
            artifact_name="versioned-skill",
            artifact_type="skill",
            drift_type="modified",  # Local changes
            collection_sha="abc123def456789012345678901234567890abcd",
            project_sha="local123456789012345678901234567890ab",
            recommendation="review_manually",
            change_origin="local_modification",
        )

        with patch("skillmeat.core.sync.SyncManager") as MockSyncManager:
            mock_sync_manager = MagicMock()
            mock_sync_manager.check_drift.return_value = [drift_result]
            MockSyncManager.return_value = mock_sync_manager

            from pathlib import Path

            results = refresher.check_updates(project_path=Path("/tmp/test-project"))

        assert len(results) == 1
        assert results[0].update_available is True
        assert results[0].drift_info is not None
        assert results[0].drift_info.drift_type == "modified"
        assert results[0].has_local_changes is True
        assert results[0].merge_strategy == "review_required"

    def test_check_updates_with_drift_conflict(
        self, refresher, mock_collection, sample_artifact_with_sha
    ):
        """Test check_updates with drift detection showing conflict."""
        from skillmeat.models import DriftDetectionResult

        mock_collection.artifacts = [sample_artifact_with_sha]

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path/to/skill"
        )

        mock_github_client = MagicMock()
        mock_github_client.resolve_version.return_value = (
            "new789sha456789012345678901234567890new1"
        )
        refresher._github_client = mock_github_client

        # Create drift result indicating conflict
        drift_result = DriftDetectionResult(
            artifact_name="versioned-skill",
            artifact_type="skill",
            drift_type="conflict",  # Both local and upstream changed
            collection_sha="coll123456789012345678901234567890ab",
            project_sha="proj123456789012345678901234567890ab",
            recommendation="manual_merge_required",
        )

        with patch("skillmeat.core.sync.SyncManager") as MockSyncManager:
            mock_sync_manager = MagicMock()
            mock_sync_manager.check_drift.return_value = [drift_result]
            MockSyncManager.return_value = mock_sync_manager

            from pathlib import Path

            results = refresher.check_updates(project_path=Path("/tmp/test-project"))

        assert len(results) == 1
        assert results[0].update_available is True
        assert results[0].drift_info.drift_type == "conflict"
        assert results[0].has_local_changes is True
        assert results[0].merge_strategy == "conflict"

    def test_check_updates_with_drift_outdated(
        self, refresher, mock_collection, sample_artifact_with_sha
    ):
        """Test check_updates with drift detection showing outdated (collection changed)."""
        from skillmeat.models import DriftDetectionResult

        mock_collection.artifacts = [sample_artifact_with_sha]

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path/to/skill"
        )

        mock_github_client = MagicMock()
        mock_github_client.resolve_version.return_value = (
            "new789sha456789012345678901234567890new1"
        )
        refresher._github_client = mock_github_client

        # Create drift result indicating outdated (collection changed, project unchanged)
        drift_result = DriftDetectionResult(
            artifact_name="versioned-skill",
            artifact_type="skill",
            drift_type="outdated",
            collection_sha="newcoll3456789012345678901234567890ab",
            project_sha="abc123def456789012345678901234567890abcd",
            recommendation="update_from_collection",
        )

        with patch("skillmeat.core.sync.SyncManager") as MockSyncManager:
            mock_sync_manager = MagicMock()
            mock_sync_manager.check_drift.return_value = [drift_result]
            MockSyncManager.return_value = mock_sync_manager

            from pathlib import Path

            results = refresher.check_updates(project_path=Path("/tmp/test-project"))

        assert len(results) == 1
        assert results[0].update_available is True
        assert results[0].drift_info.drift_type == "outdated"
        assert results[0].has_local_changes is False
        assert results[0].merge_strategy == "safe_update"

    def test_check_updates_sync_manager_not_available(
        self, refresher, mock_collection, sample_artifact_with_sha
    ):
        """Test check_updates gracefully handles SyncManager import failure."""
        mock_collection.artifacts = [sample_artifact_with_sha]

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path/to/skill"
        )

        mock_github_client = MagicMock()
        mock_github_client.resolve_version.return_value = (
            "new789sha456789012345678901234567890new1"
        )
        refresher._github_client = mock_github_client

        # Mock SyncManager import to fail
        with patch("skillmeat.core.sync.SyncManager") as MockSyncManager:
            MockSyncManager.side_effect = ImportError("SyncManager not available")

            from pathlib import Path

            results = refresher.check_updates(project_path=Path("/tmp/test-project"))

        # Should still work but without drift info
        assert len(results) == 1
        assert results[0].update_available is True
        assert results[0].drift_info is None
        assert results[0].has_local_changes is False
        assert results[0].merge_strategy == "safe_update"

    def test_check_updates_check_drift_failure(
        self, refresher, mock_collection, sample_artifact_with_sha
    ):
        """Test check_updates gracefully handles check_drift() failure."""
        mock_collection.artifacts = [sample_artifact_with_sha]

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path/to/skill"
        )

        mock_github_client = MagicMock()
        mock_github_client.resolve_version.return_value = (
            "new789sha456789012345678901234567890new1"
        )
        refresher._github_client = mock_github_client

        # Mock SyncManager.check_drift to fail
        with patch("skillmeat.core.sync.SyncManager") as MockSyncManager:
            mock_sync_manager = MagicMock()
            mock_sync_manager.check_drift.side_effect = ValueError("Project not found")
            MockSyncManager.return_value = mock_sync_manager

            from pathlib import Path

            results = refresher.check_updates(project_path=Path("/tmp/test-project"))

        # Should still work but without drift info
        assert len(results) == 1
        assert results[0].update_available is True
        assert results[0].drift_info is None
        assert results[0].has_local_changes is False
        assert results[0].merge_strategy == "safe_update"

    def test_check_updates_artifact_not_in_drift_results(
        self, refresher, mock_collection, sample_artifact_with_sha
    ):
        """Test check_updates when artifact is not in drift results (not deployed)."""
        from skillmeat.models import DriftDetectionResult

        mock_collection.artifacts = [sample_artifact_with_sha]

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path/to/skill"
        )

        mock_github_client = MagicMock()
        mock_github_client.resolve_version.return_value = (
            "new789sha456789012345678901234567890new1"
        )
        refresher._github_client = mock_github_client

        # Create drift result for a different artifact
        other_drift = DriftDetectionResult(
            artifact_name="other-skill",
            artifact_type="skill",
            drift_type="modified",
        )

        with patch("skillmeat.core.sync.SyncManager") as MockSyncManager:
            mock_sync_manager = MagicMock()
            mock_sync_manager.check_drift.return_value = [other_drift]
            MockSyncManager.return_value = mock_sync_manager

            from pathlib import Path

            results = refresher.check_updates(project_path=Path("/tmp/test-project"))

        # Artifact not in drift results - assume safe update
        assert len(results) == 1
        assert results[0].update_available is True
        assert results[0].drift_info is None
        assert results[0].has_local_changes is False
        assert results[0].merge_strategy == "safe_update"

    def test_check_updates_no_update_available_with_project_path(
        self, refresher, mock_collection, sample_artifact_with_sha
    ):
        """Test that drift check is skipped when no update is available."""
        mock_collection.artifacts = [sample_artifact_with_sha]

        refresher._metadata_extractor = MagicMock()
        refresher._metadata_extractor.parse_github_url.return_value = GitHubSourceSpec(
            owner="user", repo="repo", path="path/to/skill"
        )

        mock_github_client = MagicMock()
        # Same SHA - no update
        mock_github_client.resolve_version.return_value = (
            "abc123def456789012345678901234567890abcd"
        )
        refresher._github_client = mock_github_client

        with patch("skillmeat.core.sync.SyncManager") as MockSyncManager:
            mock_sync_manager = MagicMock()
            MockSyncManager.return_value = mock_sync_manager

            from pathlib import Path

            results = refresher.check_updates(project_path=Path("/tmp/test-project"))

        # No update available - merge_strategy should be no_update
        assert len(results) == 1
        assert results[0].update_available is False
        assert results[0].merge_strategy == "no_update"
        # check_drift should still be called for pre-fetching
        mock_sync_manager.check_drift.assert_called_once()


class TestDetermineMergeStrategy:
    """Tests for _determine_merge_strategy() method (BE-402)."""

    def test_strategy_outdated(self, refresher):
        """Test that outdated drift type maps to safe_update."""
        from skillmeat.models import DriftDetectionResult

        drift = DriftDetectionResult(
            artifact_name="test",
            artifact_type="skill",
            drift_type="outdated",
        )

        strategy = refresher._determine_merge_strategy(drift)

        assert strategy == "safe_update"

    def test_strategy_modified(self, refresher):
        """Test that modified drift type maps to review_required."""
        from skillmeat.models import DriftDetectionResult

        drift = DriftDetectionResult(
            artifact_name="test",
            artifact_type="skill",
            drift_type="modified",
        )

        strategy = refresher._determine_merge_strategy(drift)

        assert strategy == "review_required"

    def test_strategy_conflict(self, refresher):
        """Test that conflict drift type maps to conflict."""
        from skillmeat.models import DriftDetectionResult

        drift = DriftDetectionResult(
            artifact_name="test",
            artifact_type="skill",
            drift_type="conflict",
        )

        strategy = refresher._determine_merge_strategy(drift)

        assert strategy == "conflict"

    def test_strategy_added(self, refresher):
        """Test that added drift type maps to safe_update."""
        from skillmeat.models import DriftDetectionResult

        drift = DriftDetectionResult(
            artifact_name="test",
            artifact_type="skill",
            drift_type="added",
        )

        strategy = refresher._determine_merge_strategy(drift)

        assert strategy == "safe_update"

    def test_strategy_removed(self, refresher):
        """Test that removed drift type maps to no_update."""
        from skillmeat.models import DriftDetectionResult

        drift = DriftDetectionResult(
            artifact_name="test",
            artifact_type="skill",
            drift_type="removed",
        )

        strategy = refresher._determine_merge_strategy(drift)

        assert strategy == "no_update"

    def test_strategy_version_mismatch(self, refresher):
        """Test that version_mismatch drift type maps to review_required."""
        from skillmeat.models import DriftDetectionResult

        drift = DriftDetectionResult(
            artifact_name="test",
            artifact_type="skill",
            drift_type="version_mismatch",
        )

        strategy = refresher._determine_merge_strategy(drift)

        assert strategy == "review_required"

    def test_strategy_unknown_defaults_to_review_required(self, refresher):
        """Test that unknown drift types default to review_required.

        Since DriftDetectionResult validates drift_type, we use a MagicMock
        to simulate an unknown/unexpected drift_type that isn't in our strategy map.
        """
        # Create a mock with an unknown drift_type to test fallback behavior
        mock_drift = MagicMock()
        mock_drift.drift_type = "future_unknown_type"  # Not in strategy_map

        strategy = refresher._determine_merge_strategy(mock_drift)

        assert strategy == "review_required"


class TestUpdateAvailableResultDriftFields:
    """Tests for UpdateAvailableResult drift-related fields (BE-402)."""

    def test_default_drift_fields(self):
        """Test default values for new drift-related fields."""
        result = UpdateAvailableResult(
            artifact_id="skill:test",
            artifact_name="test",
        )

        assert result.drift_info is None
        assert result.has_local_changes is False
        assert result.merge_strategy == "no_update"

    def test_valid_merge_strategies(self):
        """Test that all valid merge strategies are accepted."""
        valid_strategies = ["safe_update", "review_required", "conflict", "no_update"]

        for strategy in valid_strategies:
            result = UpdateAvailableResult(
                artifact_id="skill:test",
                artifact_name="test",
                merge_strategy=strategy,
            )
            assert result.merge_strategy == strategy

    def test_invalid_merge_strategy_raises(self):
        """Test that invalid merge strategy raises ValueError."""
        with pytest.raises(ValueError, match="Invalid merge_strategy"):
            UpdateAvailableResult(
                artifact_id="skill:test",
                artifact_name="test",
                merge_strategy="invalid_strategy",
            )

    def test_to_dict_with_drift_info(self):
        """Test to_dict() includes drift_info when present."""
        from skillmeat.models import DriftDetectionResult

        drift = DriftDetectionResult(
            artifact_name="test",
            artifact_type="skill",
            drift_type="modified",
            collection_sha="coll123",
            project_sha="proj456",
            recommendation="review_manually",
            change_origin="local_modification",
        )

        result = UpdateAvailableResult(
            artifact_id="skill:test",
            artifact_name="test",
            current_sha="abc123",
            upstream_sha="def456",
            update_available=True,
            reason="SHA mismatch",
            drift_info=drift,
            has_local_changes=True,
            merge_strategy="review_required",
        )

        data = result.to_dict()

        assert data["has_local_changes"] is True
        assert data["merge_strategy"] == "review_required"
        assert "drift_info" in data
        assert data["drift_info"]["drift_type"] == "modified"
        assert data["drift_info"]["artifact_name"] == "test"
        assert data["drift_info"]["collection_sha"] == "coll123"
        assert data["drift_info"]["project_sha"] == "proj456"

    def test_to_dict_without_drift_info(self):
        """Test to_dict() excludes drift_info when None."""
        result = UpdateAvailableResult(
            artifact_id="skill:test",
            artifact_name="test",
            update_available=False,
            merge_strategy="no_update",
        )

        data = result.to_dict()

        assert "drift_info" not in data
        assert data["has_local_changes"] is False
        assert data["merge_strategy"] == "no_update"

    def test_from_dict_with_drift_info(self):
        """Test from_dict() reconstructs drift_info correctly."""
        data = {
            "artifact_id": "skill:test",
            "artifact_name": "test",
            "current_sha": "abc123",
            "upstream_sha": "def456",
            "update_available": True,
            "reason": "SHA mismatch",
            "drift_info": {
                "artifact_name": "test",
                "artifact_type": "skill",
                "drift_type": "conflict",
                "collection_sha": "coll123",
                "project_sha": "proj456",
                "recommendation": "manual_merge_required",
                "change_origin": "local_modification",
            },
            "has_local_changes": True,
            "merge_strategy": "conflict",
        }

        result = UpdateAvailableResult.from_dict(data)

        assert result.has_local_changes is True
        assert result.merge_strategy == "conflict"
        assert result.drift_info is not None
        assert result.drift_info.drift_type == "conflict"
        assert result.drift_info.artifact_name == "test"
        assert result.drift_info.collection_sha == "coll123"

    def test_from_dict_without_drift_info(self):
        """Test from_dict() handles missing drift_info."""
        data = {
            "artifact_id": "skill:test",
            "artifact_name": "test",
            "update_available": False,
        }

        result = UpdateAvailableResult.from_dict(data)

        assert result.drift_info is None
        assert result.has_local_changes is False
        assert result.merge_strategy == "no_update"
