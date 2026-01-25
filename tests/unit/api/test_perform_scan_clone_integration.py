"""Tests for clone-based artifact indexing integration in _perform_scan.

Tests the integration of CloneTarget computation, strategy selection, and
batch manifest extraction in the _perform_scan function.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from skillmeat.api.routers.marketplace_sources import (
    _convert_manifest_to_search_metadata,
    _extract_manifests_via_clone,
)
from skillmeat.api.schemas.marketplace import DetectedArtifact
from skillmeat.core.clone_target import (
    CloneTarget,
    compute_clone_metadata,
    select_indexing_strategy,
    get_sparse_checkout_patterns,
)


class TestConvertManifestToSearchMetadata:
    """Tests for _convert_manifest_to_search_metadata."""

    def test_extracts_all_fields(self):
        """Test that all fields are extracted correctly."""
        extracted = {
            "title": "My Skill",
            "description": "Does useful things",
            "tags": ["automation", "testing"],
        }
        result = _convert_manifest_to_search_metadata(extracted, "my-skill")

        assert result["title"] == "My Skill"
        assert result["description"] == "Does useful things"
        assert result["search_tags"] == ["automation", "testing"]
        assert "my-skill" in result["search_text"]
        assert "My Skill" in result["search_text"]
        assert "automation" in result["search_text"]

    def test_handles_empty_extracted(self):
        """Test handling of empty extracted data."""
        result = _convert_manifest_to_search_metadata({}, "test-artifact")

        assert result["title"] is None
        assert result["description"] is None
        assert result["search_tags"] is None
        assert result["search_text"] is None

    def test_handles_none_extracted(self):
        """Test handling of None extracted data."""
        result = _convert_manifest_to_search_metadata(None, "test-artifact")

        assert result["title"] is None
        assert result["description"] is None
        assert result["search_tags"] is None
        assert result["search_text"] is None

    def test_truncates_long_title(self):
        """Test that long titles are truncated to 200 chars."""
        long_title = "A" * 300
        extracted = {"title": long_title}
        result = _convert_manifest_to_search_metadata(extracted, "test")

        assert len(result["title"]) == 200
        assert result["title"] == "A" * 200

    def test_handles_comma_separated_tags(self):
        """Test parsing comma-separated tag strings."""
        extracted = {"tags": "tag1, tag2, tag3"}
        result = _convert_manifest_to_search_metadata(extracted, "test")

        assert result["search_tags"] == ["tag1", "tag2", "tag3"]

    def test_handles_empty_tags(self):
        """Test handling of empty tags."""
        extracted = {"title": "Test", "tags": []}
        result = _convert_manifest_to_search_metadata(extracted, "test")

        assert result["search_tags"] is None

    def test_builds_search_text_with_all_parts(self):
        """Test that search_text combines all parts."""
        extracted = {
            "title": "Test Title",
            "description": "Test Description",
            "tags": ["tag1", "tag2"],
        }
        result = _convert_manifest_to_search_metadata(extracted, "test-artifact")

        # All parts should be in search_text
        assert "test-artifact" in result["search_text"]
        assert "Test Title" in result["search_text"]
        assert "Test Description" in result["search_text"]
        assert "tag1" in result["search_text"]
        assert "tag2" in result["search_text"]


class TestCloneTargetIntegration:
    """Tests for CloneTarget computation and strategy selection."""

    @pytest.fixture
    def skill_artifacts(self):
        """Create test skill artifacts."""
        return [
            DetectedArtifact(
                artifact_type="skill",
                name="skill1",
                path=".claude/skills/skill1",
                upstream_url="https://github.com/test/repo",
                confidence_score=95,
            ),
            DetectedArtifact(
                artifact_type="skill",
                name="skill2",
                path=".claude/skills/skill2",
                upstream_url="https://github.com/test/repo",
                confidence_score=90,
            ),
        ]

    @pytest.fixture
    def many_skill_artifacts(self):
        """Create many skill artifacts (above sparse_manifest threshold)."""
        return [
            DetectedArtifact(
                artifact_type="skill",
                name=f"skill{i}",
                path=f".claude/skills/skill{i}",
                upstream_url="https://github.com/test/repo",
                confidence_score=95,
            )
            for i in range(10)
        ]

    @pytest.fixture
    def mock_source(self):
        """Create a mock MarketplaceSource."""
        source = MagicMock()
        source.owner = "test-owner"
        source.repo_name = "test-repo"
        source.ref = "main"
        source.clone_target = None
        return source

    def test_strategy_selection_api_for_few_artifacts(self, mock_source, skill_artifacts):
        """Test that API strategy is selected for < 3 artifacts."""
        strategy = select_indexing_strategy(mock_source, skill_artifacts)
        assert strategy == "api"

    def test_strategy_selection_sparse_manifest_for_medium(self, mock_source, many_skill_artifacts):
        """Test that sparse_manifest strategy is selected for 3-20 artifacts."""
        # Take only 5 artifacts
        artifacts = many_skill_artifacts[:5]
        strategy = select_indexing_strategy(mock_source, artifacts)
        assert strategy == "sparse_manifest"

    def test_compute_clone_metadata_extracts_root(self, skill_artifacts):
        """Test that compute_clone_metadata finds the common root."""
        metadata = compute_clone_metadata(skill_artifacts, tree_sha="abc123")

        assert metadata["artifacts_root"] == ".claude/skills"
        assert len(metadata["artifact_paths"]) == 2
        assert ".claude/skills/skill1" in metadata["artifact_paths"]
        assert ".claude/skills/skill2" in metadata["artifact_paths"]

    def test_get_sparse_checkout_patterns_for_manifest(self, skill_artifacts):
        """Test pattern generation for sparse_manifest strategy."""
        patterns = get_sparse_checkout_patterns(
            "sparse_manifest",
            skill_artifacts,
            artifacts_root=".claude/skills",
        )

        # Should get specific SKILL.md file patterns
        assert len(patterns) == 2
        assert ".claude/skills/skill1/SKILL.md" in patterns
        assert ".claude/skills/skill2/SKILL.md" in patterns

    def test_get_sparse_checkout_patterns_for_directory(self, skill_artifacts):
        """Test pattern generation for sparse_directory strategy."""
        patterns = get_sparse_checkout_patterns(
            "sparse_directory",
            skill_artifacts,
            artifacts_root=".claude/skills",
        )

        # Should get directory pattern
        assert len(patterns) == 1
        assert patterns[0] == ".claude/skills/**"

    def test_get_sparse_checkout_patterns_for_api(self, skill_artifacts):
        """Test that API strategy returns empty patterns."""
        patterns = get_sparse_checkout_patterns(
            "api",
            skill_artifacts,
            artifacts_root=".claude/skills",
        )

        assert patterns == []

    def test_clone_target_creation(self, skill_artifacts):
        """Test CloneTarget dataclass creation and serialization."""
        metadata = compute_clone_metadata(skill_artifacts, tree_sha="abc123")
        strategy = select_indexing_strategy(MagicMock(), skill_artifacts)
        patterns = get_sparse_checkout_patterns(strategy, skill_artifacts, metadata["artifacts_root"])

        clone_target = CloneTarget(
            strategy=strategy,
            sparse_patterns=patterns,
            artifacts_root=metadata["artifacts_root"],
            artifact_paths=metadata["artifact_paths"],
            tree_sha="abc123",
            computed_at=datetime.now(timezone.utc),
        )

        # Test serialization round-trip
        json_str = clone_target.to_json()
        restored = CloneTarget.from_json(json_str)

        assert restored.strategy == clone_target.strategy
        assert restored.sparse_patterns == clone_target.sparse_patterns
        assert restored.artifacts_root == clone_target.artifacts_root
        assert restored.artifact_paths == clone_target.artifact_paths
        assert restored.tree_sha == clone_target.tree_sha


class TestExtractManifeststViaClone:
    """Tests for _extract_manifests_via_clone async function."""

    @pytest.fixture
    def mock_source(self):
        """Create a mock MarketplaceSource."""
        source = MagicMock()
        source.owner = "test-owner"
        source.repo_name = "test-repo"
        source.ref = "main"
        return source

    @pytest.fixture
    def skill_artifacts(self):
        """Create test skill artifacts."""
        return [
            DetectedArtifact(
                artifact_type="skill",
                name="test-skill",
                path=".claude/skills/test-skill",
                upstream_url="https://github.com/test/repo",
                confidence_score=95,
            ),
        ]

    @pytest.mark.asyncio
    async def test_returns_empty_for_empty_artifacts(self, mock_source):
        """Test that empty artifacts list returns empty result."""
        clone_target = CloneTarget(
            strategy="sparse_manifest",
            sparse_patterns=[".claude/skills/test/SKILL.md"],
            artifacts_root=".claude/skills",
            artifact_paths=[".claude/skills/test"],
            tree_sha="abc123",
        )

        result = await _extract_manifests_via_clone(mock_source, [], clone_target)
        assert result == {}

    @pytest.mark.asyncio
    async def test_returns_empty_for_empty_patterns(self, mock_source, skill_artifacts):
        """Test that empty patterns list returns empty result."""
        clone_target = CloneTarget(
            strategy="sparse_manifest",
            sparse_patterns=[],  # No patterns
            artifacts_root=".claude/skills",
            artifact_paths=[".claude/skills/test-skill"],
            tree_sha="abc123",
        )

        result = await _extract_manifests_via_clone(mock_source, skill_artifacts, clone_target)
        assert result == {}

    @pytest.mark.asyncio
    async def test_handles_clone_failure_gracefully(self, mock_source, skill_artifacts):
        """Test that clone failures are handled gracefully."""
        clone_target = CloneTarget(
            strategy="sparse_manifest",
            sparse_patterns=[".claude/skills/test-skill/SKILL.md"],
            artifacts_root=".claude/skills",
            artifact_paths=[".claude/skills/test-skill"],
            tree_sha="abc123",
        )

        # Mock _clone_repo_sparse to raise an error
        with patch(
            "skillmeat.api.routers.marketplace_sources._clone_repo_sparse",
            side_effect=RuntimeError("Clone failed"),
        ):
            result = await _extract_manifests_via_clone(
                mock_source, skill_artifacts, clone_target
            )

        # Should return empty dict on failure (caller falls back to API)
        assert result == {}
