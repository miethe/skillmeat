"""Unit tests for deduplication engine.

Tests content-based deduplication for marketplace artifacts, including
within-source and cross-source duplicate detection, exclusion marking,
and best artifact selection.
"""

import logging
from datetime import datetime, timezone
from typing import Any

import pytest

from skillmeat.core.marketplace.deduplication_engine import (
    EXCLUDED_DUPLICATE_CROSS_SOURCE,
    EXCLUDED_DUPLICATE_WITHIN_SOURCE,
    EXCLUDED_USER_MANUAL,
    DeduplicationEngine,
    mark_as_excluded,
    mark_for_restore,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def engine() -> DeduplicationEngine:
    """Create a fresh DeduplicationEngine instance."""
    return DeduplicationEngine()


@pytest.fixture
def sample_files() -> dict[str, dict[str, str]]:
    """Provide sample file dictionaries for testing.

    Returns:
        Dictionary of named file sets for various test scenarios.
    """
    return {
        "skill_a": {"SKILL.md": "# Canvas Design\n\nA skill for design tasks."},
        "skill_b": {"SKILL.md": "# Document Analysis\n\nA skill for documents."},
        "skill_a_copy": {"SKILL.md": "# Canvas Design\n\nA skill for design tasks."},
        "multi_file": {
            "SKILL.md": "# Multi File Skill",
            "README.md": "Documentation",
            "config.toml": "[skill]\nname = 'multi'",
        },
        "empty": {},
    }


def make_artifact(
    path: str,
    files: dict[str, str],
    confidence_score: float = 0.8,
    artifact_type: str = "skill",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Factory function to create artifact dictionaries.

    Args:
        path: Artifact path (e.g., "skills/canvas").
        files: Dictionary mapping filenames to content.
        confidence_score: Detection confidence (0.0 to 1.0).
        artifact_type: Type of artifact (e.g., "skill", "command").
        metadata: Optional metadata dictionary.

    Returns:
        Artifact dictionary suitable for deduplication engine.
    """
    artifact: dict[str, Any] = {
        "path": path,
        "files": files,
        "confidence_score": confidence_score,
        "artifact_type": artifact_type,
    }
    if metadata is not None:
        artifact["metadata"] = metadata
    return artifact


# ============================================================================
# Test: Exclusion Reason Constants
# ============================================================================


class TestExclusionConstants:
    """Test suite for exclusion reason constants."""

    def test_within_source_constant_defined(self):
        """Test EXCLUDED_DUPLICATE_WITHIN_SOURCE constant is defined correctly."""
        assert EXCLUDED_DUPLICATE_WITHIN_SOURCE == "duplicate_within_source"

    def test_cross_source_constant_defined(self):
        """Test EXCLUDED_DUPLICATE_CROSS_SOURCE constant is defined correctly."""
        assert EXCLUDED_DUPLICATE_CROSS_SOURCE == "duplicate_cross_source"

    def test_user_manual_constant_defined(self):
        """Test EXCLUDED_USER_MANUAL constant is defined correctly."""
        assert EXCLUDED_USER_MANUAL == "user_excluded"

    def test_constants_are_strings(self):
        """Test all constants are string type."""
        assert isinstance(EXCLUDED_DUPLICATE_WITHIN_SOURCE, str)
        assert isinstance(EXCLUDED_DUPLICATE_CROSS_SOURCE, str)
        assert isinstance(EXCLUDED_USER_MANUAL, str)

    def test_constants_are_unique(self):
        """Test all constants have unique values."""
        constants = {
            EXCLUDED_DUPLICATE_WITHIN_SOURCE,
            EXCLUDED_DUPLICATE_CROSS_SOURCE,
            EXCLUDED_USER_MANUAL,
        }
        assert len(constants) == 3


# ============================================================================
# Test: compute_hash()
# ============================================================================


class TestComputeHash:
    """Test suite for DeduplicationEngine.compute_hash method."""

    def test_single_file_returns_valid_hash(self, engine: DeduplicationEngine):
        """Test hashing single file artifact returns valid SHA256 hash."""
        files = {"SKILL.md": "# Canvas Design"}

        result = engine.compute_hash(files)

        assert result is not None
        assert len(result) == 64  # SHA256 hex digest length
        assert result.islower()
        assert all(c in "0123456789abcdef" for c in result)

    def test_multiple_files_returns_valid_hash(self, engine: DeduplicationEngine):
        """Test hashing multiple file artifact returns valid hash."""
        files = {
            "SKILL.md": "# My Skill",
            "README.md": "Documentation",
            "config.toml": "[config]\nvalue = 1",
        }

        result = engine.compute_hash(files)

        assert result is not None
        assert len(result) == 64

    def test_empty_files_returns_hash(self, engine: DeduplicationEngine):
        """Test hashing empty files dict returns consistent hash."""
        empty_files: dict[str, str] = {}

        result = engine.compute_hash(empty_files)

        # Empty dict should return hash of empty string
        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert result == expected

    def test_deterministic_same_input_same_hash(self, engine: DeduplicationEngine):
        """Test same input always produces same hash (deterministic)."""
        files = {"SKILL.md": "# Test Content\n\nWith multiple lines."}

        hash1 = engine.compute_hash(files)
        hash2 = engine.compute_hash(files)
        hash3 = engine.compute_hash(files)

        assert hash1 == hash2 == hash3

    def test_order_independence(self, engine: DeduplicationEngine):
        """Test file dict order doesn't affect hash."""
        files_order1 = {
            "a.txt": "Content A",
            "b.txt": "Content B",
            "c.txt": "Content C",
        }
        files_order2 = {
            "c.txt": "Content C",
            "a.txt": "Content A",
            "b.txt": "Content B",
        }
        files_order3 = {
            "b.txt": "Content B",
            "c.txt": "Content C",
            "a.txt": "Content A",
        }

        hash1 = engine.compute_hash(files_order1)
        hash2 = engine.compute_hash(files_order2)
        hash3 = engine.compute_hash(files_order3)

        assert hash1 == hash2 == hash3

    def test_different_content_different_hash(self, engine: DeduplicationEngine):
        """Test different content produces different hashes."""
        files_a = {"SKILL.md": "Content A"}
        files_b = {"SKILL.md": "Content B"}

        hash_a = engine.compute_hash(files_a)
        hash_b = engine.compute_hash(files_b)

        assert hash_a != hash_b

    def test_different_filename_different_hash(self, engine: DeduplicationEngine):
        """Test different filename produces different hash (even with same content)."""
        files_a = {"file_a.txt": "Same content"}
        files_b = {"file_b.txt": "Same content"}

        hash_a = engine.compute_hash(files_a)
        hash_b = engine.compute_hash(files_b)

        assert hash_a != hash_b

    def test_unicode_content(self, engine: DeduplicationEngine):
        """Test handling of Unicode content."""
        files = {"SKILL.md": "# Skill with Unicode: World!"}

        result = engine.compute_hash(files)

        assert result is not None
        assert len(result) == 64


# ============================================================================
# Test: find_duplicates()
# ============================================================================


class TestFindDuplicates:
    """Test suite for DeduplicationEngine.find_duplicates method."""

    def test_no_duplicates_returns_empty_dict(
        self, engine: DeduplicationEngine, sample_files: dict
    ):
        """Test no duplicates returns empty dictionary."""
        artifacts = [
            make_artifact("skills/a", sample_files["skill_a"]),
            make_artifact("skills/b", sample_files["skill_b"]),
            make_artifact("skills/c", sample_files["multi_file"]),
        ]

        duplicates = engine.find_duplicates(artifacts)

        assert duplicates == {}
        assert len(duplicates) == 0

    def test_one_duplicate_pair(
        self, engine: DeduplicationEngine, sample_files: dict
    ):
        """Test finding single pair of duplicates."""
        artifacts = [
            make_artifact("skills/a", sample_files["skill_a"], confidence_score=0.9),
            make_artifact("other/a-copy", sample_files["skill_a_copy"], confidence_score=0.8),
            make_artifact("skills/unique", sample_files["skill_b"], confidence_score=0.7),
        ]

        duplicates = engine.find_duplicates(artifacts)

        assert len(duplicates) == 1
        # Get the duplicate group
        dup_group = list(duplicates.values())[0]
        assert len(dup_group) == 2
        dup_paths = {a["path"] for a in dup_group}
        assert dup_paths == {"skills/a", "other/a-copy"}

    def test_multiple_duplicate_groups(self, engine: DeduplicationEngine):
        """Test finding multiple distinct duplicate groups."""
        artifacts = [
            make_artifact("a1", {"f.md": "content A"}),
            make_artifact("a2", {"f.md": "content A"}),  # Dup of a1
            make_artifact("b1", {"f.md": "content B"}),
            make_artifact("b2", {"f.md": "content B"}),  # Dup of b1
            make_artifact("b3", {"f.md": "content B"}),  # Dup of b1
            make_artifact("unique", {"f.md": "unique content"}),
        ]

        duplicates = engine.find_duplicates(artifacts)

        assert len(duplicates) == 2  # Two duplicate groups

        # Find each group by size
        group_sizes = sorted([len(g) for g in duplicates.values()])
        assert group_sizes == [2, 3]  # One group of 2, one group of 3

    def test_hash_stored_in_metadata(self, engine: DeduplicationEngine):
        """Test that computed hash is stored in artifact metadata."""
        artifacts = [
            make_artifact("skills/a", {"SKILL.md": "content"}),
            make_artifact("skills/b", {"SKILL.md": "different"}),
        ]

        engine.find_duplicates(artifacts)

        for artifact in artifacts:
            assert "metadata" in artifact
            assert "content_hash" in artifact["metadata"]
            assert len(artifact["metadata"]["content_hash"]) == 64

    def test_empty_input_returns_empty_dict(self, engine: DeduplicationEngine):
        """Test empty artifact list returns empty dict."""
        duplicates = engine.find_duplicates([])

        assert duplicates == {}

    def test_single_artifact_returns_empty_dict(self, engine: DeduplicationEngine):
        """Test single artifact (no possible duplicates) returns empty dict."""
        artifacts = [make_artifact("skills/only", {"SKILL.md": "content"})]

        duplicates = engine.find_duplicates(artifacts)

        assert duplicates == {}

    def test_missing_files_key_handled(self, engine: DeduplicationEngine):
        """Test artifact without files key is handled gracefully."""
        artifacts = [
            {"path": "a", "confidence_score": 0.9},  # Missing files
            {"path": "b", "confidence_score": 0.8},  # Missing files
        ]

        # Should not raise, treats missing files as empty dict
        duplicates = engine.find_duplicates(artifacts)

        # Both have same hash (empty files) -> duplicates
        assert len(duplicates) == 1

    def test_logs_duplicate_detection(
        self, engine: DeduplicationEngine, caplog: pytest.LogCaptureFixture
    ):
        """Test that duplicate detection logs info message."""
        artifacts = [
            make_artifact("a", {"f.md": "same"}),
            make_artifact("b", {"f.md": "same"}),
        ]

        with caplog.at_level(logging.INFO):
            engine.find_duplicates(artifacts)

        assert "Found 1 duplicate group(s)" in caplog.text


# ============================================================================
# Test: get_best_artifact()
# ============================================================================


class TestGetBestArtifact:
    """Test suite for DeduplicationEngine.get_best_artifact method."""

    def test_highest_confidence_wins(self, engine: DeduplicationEngine):
        """Test artifact with highest confidence score is selected."""
        duplicates = [
            make_artifact("low", {"f.md": "same"}, confidence_score=0.7),
            make_artifact("high", {"f.md": "same"}, confidence_score=0.95),
            make_artifact("medium", {"f.md": "same"}, confidence_score=0.85),
        ]

        best = engine.get_best_artifact(duplicates)

        assert best["path"] == "high"
        assert best["confidence_score"] == 0.95

    def test_manual_mapping_preference_on_tie(self, engine: DeduplicationEngine):
        """Test manual mapping wins on confidence tie."""
        duplicates = [
            make_artifact("auto", {"f.md": "same"}, confidence_score=0.9, metadata={}),
            make_artifact(
                "manual",
                {"f.md": "same"},
                confidence_score=0.9,
                metadata={"is_manual_mapping": True},
            ),
        ]

        best = engine.get_best_artifact(duplicates)

        assert best["path"] == "manual"

    def test_shorter_path_preference_on_tie(self, engine: DeduplicationEngine):
        """Test shorter path wins when confidence and manual flag tie."""
        duplicates = [
            make_artifact(
                "very/long/nested/path", {"f.md": "same"}, confidence_score=0.9
            ),
            make_artifact("short", {"f.md": "same"}, confidence_score=0.9),
            make_artifact("medium/path", {"f.md": "same"}, confidence_score=0.9),
        ]

        best = engine.get_best_artifact(duplicates)

        assert best["path"] == "short"

    def test_single_artifact_returns_itself(self, engine: DeduplicationEngine):
        """Test single artifact returns itself."""
        artifact = make_artifact("only", {"f.md": "content"}, confidence_score=0.5)
        duplicates = [artifact]

        best = engine.get_best_artifact(duplicates)

        assert best is artifact
        assert best["path"] == "only"

    def test_empty_list_raises_value_error(self, engine: DeduplicationEngine):
        """Test empty list raises ValueError."""
        with pytest.raises(ValueError, match="Cannot select best artifact from empty list"):
            engine.get_best_artifact([])

    def test_tie_breaking_full_cascade(self, engine: DeduplicationEngine):
        """Test full tie-breaking cascade: confidence -> manual -> path length."""
        # All same confidence, none manual, different path lengths
        duplicates = [
            make_artifact("a/b/c/d", {"f.md": "same"}, confidence_score=0.85),
            make_artifact("x", {"f.md": "same"}, confidence_score=0.85),
            make_artifact("m/n", {"f.md": "same"}, confidence_score=0.85),
        ]

        best = engine.get_best_artifact(duplicates)

        assert best["path"] == "x"  # Shortest path wins

    def test_missing_confidence_treated_as_zero(self, engine: DeduplicationEngine):
        """Test missing confidence_score is treated as 0.0."""
        duplicates = [
            {"path": "no-conf", "files": {"f.md": "same"}},  # No confidence_score
            make_artifact("has-conf", {"f.md": "same"}, confidence_score=0.5),
        ]

        best = engine.get_best_artifact(duplicates)

        assert best["path"] == "has-conf"

    def test_missing_metadata_handled(self, engine: DeduplicationEngine):
        """Test missing metadata is handled gracefully."""
        duplicates = [
            {"path": "no-meta", "files": {"f.md": "same"}, "confidence_score": 0.9},
            make_artifact(
                "has-meta",
                {"f.md": "same"},
                confidence_score=0.9,
                metadata={"other": "data"},
            ),
        ]

        # Should not raise
        best = engine.get_best_artifact(duplicates)

        # Both have same confidence, neither has is_manual_mapping
        # Shorter path wins
        assert best["path"] == "no-meta"


# ============================================================================
# Test: deduplicate_within_source()
# ============================================================================


class TestDeduplicateWithinSource:
    """Test suite for DeduplicationEngine.deduplicate_within_source method."""

    def test_duplicates_identified_and_excluded(self, engine: DeduplicationEngine):
        """Test duplicates are identified and excluded correctly."""
        artifacts = [
            make_artifact("skills/a", {"SKILL.md": "same"}, confidence_score=0.8),
            make_artifact("skills/b", {"SKILL.md": "same"}, confidence_score=0.9),  # Best
            make_artifact("skills/c", {"SKILL.md": "same"}, confidence_score=0.7),
        ]

        kept, excluded = engine.deduplicate_within_source(artifacts)

        assert len(kept) == 1
        assert len(excluded) == 2
        assert kept[0]["path"] == "skills/b"  # Highest confidence kept

    def test_best_artifact_kept(self, engine: DeduplicationEngine):
        """Test best artifact from duplicate group is kept."""
        artifacts = [
            make_artifact("low", {"f.md": "same"}, confidence_score=0.7),
            make_artifact("high", {"f.md": "same"}, confidence_score=0.95),
        ]

        kept, excluded = engine.deduplicate_within_source(artifacts)

        kept_paths = [a["path"] for a in kept]
        excluded_paths = [a["path"] for a in excluded]

        assert "high" in kept_paths
        assert "low" in excluded_paths

    def test_exclusion_metadata_correct(self, engine: DeduplicationEngine):
        """Test exclusion metadata fields are set correctly."""
        artifacts = [
            make_artifact("winner", {"f.md": "same"}, confidence_score=0.9),
            make_artifact("loser", {"f.md": "same"}, confidence_score=0.7),
        ]

        _, excluded = engine.deduplicate_within_source(artifacts)

        assert len(excluded) == 1
        excl = excluded[0]

        assert excl["excluded"] is True
        assert excl["excluded_reason"] == EXCLUDED_DUPLICATE_WITHIN_SOURCE
        assert excl["duplicate_of"] == "winner"
        assert excl["status"] == "excluded"
        assert "excluded_at" in excl
        assert "content_hash" in excl

    def test_unique_artifacts_unchanged(self, engine: DeduplicationEngine):
        """Test unique artifacts are kept without modification."""
        artifacts = [
            make_artifact("unique1", {"f.md": "content 1"}, confidence_score=0.9),
            make_artifact("unique2", {"f.md": "content 2"}, confidence_score=0.8),
            make_artifact("unique3", {"f.md": "content 3"}, confidence_score=0.7),
        ]

        kept, excluded = engine.deduplicate_within_source(artifacts)

        assert len(kept) == 3
        assert len(excluded) == 0

        for artifact in kept:
            assert artifact.get("excluded") is not True
            assert "excluded_reason" not in artifact

    def test_empty_input_handling(self, engine: DeduplicationEngine):
        """Test empty input returns empty lists."""
        kept, excluded = engine.deduplicate_within_source([])

        assert kept == []
        assert excluded == []

    def test_single_artifact_kept(self, engine: DeduplicationEngine):
        """Test single artifact is kept without exclusion."""
        artifacts = [make_artifact("only", {"f.md": "content"})]

        kept, excluded = engine.deduplicate_within_source(artifacts)

        assert len(kept) == 1
        assert len(excluded) == 0
        assert kept[0]["path"] == "only"

    def test_hash_stored_in_metadata(self, engine: DeduplicationEngine):
        """Test content hash is stored in metadata for all artifacts."""
        artifacts = [
            make_artifact("a", {"f.md": "content"}),
            make_artifact("b", {"f.md": "content"}),
        ]

        kept, excluded = engine.deduplicate_within_source(artifacts)

        # Check kept artifact
        assert "metadata" in kept[0]
        assert "content_hash" in kept[0]["metadata"]

        # Check excluded artifact
        assert "content_hash" in excluded[0]

    def test_mixed_unique_and_duplicates(self, engine: DeduplicationEngine):
        """Test handling mix of unique and duplicate artifacts."""
        artifacts = [
            make_artifact("dup1", {"f.md": "same"}, confidence_score=0.8),
            make_artifact("dup2", {"f.md": "same"}, confidence_score=0.9),
            make_artifact("unique", {"f.md": "different"}, confidence_score=0.7),
        ]

        kept, excluded = engine.deduplicate_within_source(artifacts)

        kept_paths = {a["path"] for a in kept}
        excluded_paths = {a["path"] for a in excluded}

        assert kept_paths == {"dup2", "unique"}
        assert excluded_paths == {"dup1"}

    def test_logs_summary(
        self, engine: DeduplicationEngine, caplog: pytest.LogCaptureFixture
    ):
        """Test that deduplication logs summary info."""
        artifacts = [
            make_artifact("a", {"f.md": "same"}),
            make_artifact("b", {"f.md": "same"}),
        ]

        with caplog.at_level(logging.INFO):
            engine.deduplicate_within_source(artifacts)

        assert "Deduplicated" in caplog.text
        assert "kept" in caplog.text
        assert "excluded" in caplog.text


# ============================================================================
# Test: deduplicate_cross_source()
# ============================================================================


class TestDeduplicateCrossSource:
    """Test suite for DeduplicationEngine.deduplicate_cross_source method."""

    def test_match_against_existing_hashes(self, engine: DeduplicationEngine):
        """Test artifacts matching existing hashes are excluded."""
        # Compute hash for existing content
        existing_hash = engine.compute_hash({"f.md": "existing content"})
        existing_hashes = {existing_hash}

        new_artifacts = [
            make_artifact("match", {"f.md": "existing content"}),  # Should be excluded
            make_artifact("unique", {"f.md": "new content"}),  # Should be kept
        ]

        unique, duplicates = engine.deduplicate_cross_source(
            new_artifacts, existing_hashes
        )

        assert len(unique) == 1
        assert len(duplicates) == 1
        assert unique[0]["path"] == "unique"
        assert duplicates[0]["path"] == "match"

    def test_non_matching_artifacts_kept(self, engine: DeduplicationEngine):
        """Test artifacts not matching existing hashes are kept."""
        existing_hashes = {"abc123", "def456", "ghi789"}  # No matching hashes

        new_artifacts = [
            make_artifact("a", {"f.md": "content A"}),
            make_artifact("b", {"f.md": "content B"}),
        ]

        unique, duplicates = engine.deduplicate_cross_source(
            new_artifacts, existing_hashes
        )

        assert len(unique) == 2
        assert len(duplicates) == 0

    def test_exclusion_metadata_correct(self, engine: DeduplicationEngine):
        """Test exclusion metadata for cross-source duplicates."""
        existing_hash = engine.compute_hash({"f.md": "content"})
        existing_hashes = {existing_hash}

        new_artifacts = [make_artifact("dupe", {"f.md": "content"})]

        _, duplicates = engine.deduplicate_cross_source(new_artifacts, existing_hashes)

        assert len(duplicates) == 1
        dupe = duplicates[0]

        assert dupe["excluded"] is True
        assert dupe["excluded_reason"] == EXCLUDED_DUPLICATE_CROSS_SOURCE
        assert dupe["status"] == "excluded"
        assert "excluded_at" in dupe
        assert "content_hash" in dupe
        # Note: duplicate_of is NOT set for cross-source duplicates
        assert "duplicate_of" not in dupe

    def test_empty_existing_hashes_keeps_all(self, engine: DeduplicationEngine):
        """Test empty existing_hashes keeps all artifacts."""
        new_artifacts = [
            make_artifact("a", {"f.md": "content A"}),
            make_artifact("b", {"f.md": "content B"}),
        ]

        unique, duplicates = engine.deduplicate_cross_source(new_artifacts, set())

        assert len(unique) == 2
        assert len(duplicates) == 0

    def test_empty_new_artifacts(self, engine: DeduplicationEngine):
        """Test empty new artifacts list returns empty results."""
        existing_hashes = {"hash1", "hash2"}

        unique, duplicates = engine.deduplicate_cross_source([], existing_hashes)

        assert unique == []
        assert duplicates == []

    def test_uses_pre_computed_hash(self, engine: DeduplicationEngine):
        """Test uses hash from metadata if already computed."""
        pre_computed_hash = "abc123def456789012345678901234567890123456789012345678901234"
        existing_hashes = {pre_computed_hash}

        new_artifacts = [
            {
                "path": "pre-hashed",
                "files": {"f.md": "different content"},  # Content doesn't match hash
                "confidence_score": 0.9,
                "metadata": {"content_hash": pre_computed_hash},  # But hash matches
            }
        ]

        unique, duplicates = engine.deduplicate_cross_source(
            new_artifacts, existing_hashes
        )

        # Should use pre-computed hash, not compute from files
        assert len(duplicates) == 1
        assert duplicates[0]["path"] == "pre-hashed"

    def test_computes_hash_if_not_present(self, engine: DeduplicationEngine):
        """Test computes hash if not in metadata."""
        content_hash = engine.compute_hash({"f.md": "content"})
        existing_hashes = {content_hash}

        new_artifacts = [
            make_artifact("no-hash", {"f.md": "content"})  # No metadata.content_hash
        ]

        _, duplicates = engine.deduplicate_cross_source(new_artifacts, existing_hashes)

        assert len(duplicates) == 1
        # Hash should now be computed and stored
        assert duplicates[0]["metadata"]["content_hash"] == content_hash

    def test_all_duplicates(self, engine: DeduplicationEngine):
        """Test all artifacts matching existing collection."""
        hash_a = engine.compute_hash({"f.md": "A"})
        hash_b = engine.compute_hash({"f.md": "B"})
        existing_hashes = {hash_a, hash_b}

        new_artifacts = [
            make_artifact("a", {"f.md": "A"}),
            make_artifact("b", {"f.md": "B"}),
        ]

        unique, duplicates = engine.deduplicate_cross_source(
            new_artifacts, existing_hashes
        )

        assert len(unique) == 0
        assert len(duplicates) == 2

    def test_logs_summary(
        self, engine: DeduplicationEngine, caplog: pytest.LogCaptureFixture
    ):
        """Test that cross-source dedup logs summary."""
        existing_hash = engine.compute_hash({"f.md": "content"})

        new_artifacts = [
            make_artifact("a", {"f.md": "content"}),
            make_artifact("b", {"f.md": "unique"}),
        ]

        with caplog.at_level(logging.INFO):
            engine.deduplicate_cross_source(new_artifacts, {existing_hash})

        assert "Cross-source dedup" in caplog.text


# ============================================================================
# Test: mark_as_excluded()
# ============================================================================


class TestMarkAsExcluded:
    """Test suite for mark_as_excluded helper function."""

    def test_all_fields_set_correctly(self):
        """Test all exclusion fields are set correctly."""
        artifact = {
            "path": "skills/test",
            "files": {"SKILL.md": "content"},
            "confidence_score": 0.9,
        }

        result = mark_as_excluded(
            artifact,
            reason=EXCLUDED_DUPLICATE_WITHIN_SOURCE,
            duplicate_of="skills/original",
        )

        assert result["excluded"] is True
        assert result["excluded_reason"] == EXCLUDED_DUPLICATE_WITHIN_SOURCE
        assert result["duplicate_of"] == "skills/original"
        assert result["status"] == "excluded"
        assert "excluded_at" in result

    def test_timestamp_format_iso8601(self):
        """Test excluded_at is ISO 8601 format."""
        artifact = {"path": "test"}

        result = mark_as_excluded(artifact, reason=EXCLUDED_USER_MANUAL)

        excluded_at = result["excluded_at"]
        # Should be parseable as ISO 8601
        parsed = datetime.fromisoformat(excluded_at.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None  # Should have timezone

    def test_modifies_in_place(self):
        """Test artifact is modified in place and returned."""
        artifact = {"path": "test"}

        result = mark_as_excluded(artifact, reason=EXCLUDED_USER_MANUAL)

        assert result is artifact  # Same object

    def test_creates_metadata_if_missing(self):
        """Test metadata dict is created if not present."""
        artifact = {"path": "test"}  # No metadata

        result = mark_as_excluded(artifact, reason=EXCLUDED_USER_MANUAL)

        assert "metadata" in result

    def test_preserves_existing_metadata(self):
        """Test existing metadata is preserved."""
        artifact = {
            "path": "test",
            "metadata": {"existing_key": "existing_value"},
        }

        result = mark_as_excluded(artifact, reason=EXCLUDED_USER_MANUAL)

        assert result["metadata"]["existing_key"] == "existing_value"

    def test_content_hash_copied_from_metadata(self):
        """Test content_hash is copied from metadata to top level."""
        artifact = {
            "path": "test",
            "metadata": {"content_hash": "abc123"},
        }

        result = mark_as_excluded(artifact, reason=EXCLUDED_USER_MANUAL)

        assert result["content_hash"] == "abc123"

    def test_content_hash_preserved_if_exists(self):
        """Test content_hash at top level is not overwritten."""
        artifact = {
            "path": "test",
            "content_hash": "top_level_hash",
            "metadata": {"content_hash": "metadata_hash"},
        }

        result = mark_as_excluded(artifact, reason=EXCLUDED_USER_MANUAL)

        # Top level should remain unchanged
        assert result["content_hash"] == "top_level_hash"

    def test_without_duplicate_of(self):
        """Test marking without duplicate_of (cross-source case)."""
        artifact = {"path": "test"}

        result = mark_as_excluded(artifact, reason=EXCLUDED_DUPLICATE_CROSS_SOURCE)

        assert result["excluded"] is True
        assert result["excluded_reason"] == EXCLUDED_DUPLICATE_CROSS_SOURCE
        assert "duplicate_of" not in result

    def test_with_different_reasons(self):
        """Test with all different exclusion reasons."""
        for reason in [
            EXCLUDED_DUPLICATE_WITHIN_SOURCE,
            EXCLUDED_DUPLICATE_CROSS_SOURCE,
            EXCLUDED_USER_MANUAL,
        ]:
            artifact = {"path": "test"}
            result = mark_as_excluded(artifact, reason=reason)
            assert result["excluded_reason"] == reason


# ============================================================================
# Test: mark_for_restore()
# ============================================================================


class TestMarkForRestore:
    """Test suite for mark_for_restore helper function."""

    def test_clears_exclusion_fields(self):
        """Test all exclusion fields are cleared."""
        artifact = {
            "path": "skills/restore",
            "excluded": True,
            "excluded_reason": EXCLUDED_DUPLICATE_WITHIN_SOURCE,
            "excluded_at": "2024-01-01T00:00:00Z",
            "duplicate_of": "skills/original",
            "status": "excluded",
        }

        result = mark_for_restore(artifact)

        assert "excluded" not in result
        assert "excluded_reason" not in result
        assert "excluded_at" not in result
        assert "duplicate_of" not in result

    def test_sets_status_to_new(self):
        """Test status is reset to 'new'."""
        artifact = {
            "path": "test",
            "excluded": True,
            "status": "excluded",
        }

        result = mark_for_restore(artifact)

        assert result["status"] == "new"

    def test_preserves_content_hash_in_metadata(self):
        """Test content_hash is preserved in metadata."""
        artifact = {
            "path": "test",
            "excluded": True,
            "content_hash": "abc123",
            "metadata": {},
        }

        result = mark_for_restore(artifact)

        # Should be in metadata, not at top level
        assert "content_hash" not in result
        assert result["metadata"]["content_hash"] == "abc123"

    def test_clears_top_level_content_hash(self):
        """Test content_hash at top level is cleared."""
        artifact = {
            "path": "test",
            "content_hash": "abc123",
            "metadata": {"content_hash": "abc123"},
        }

        result = mark_for_restore(artifact)

        assert "content_hash" not in result

    def test_modifies_in_place(self):
        """Test artifact is modified in place and returned."""
        artifact = {"path": "test", "excluded": True}

        result = mark_for_restore(artifact)

        assert result is artifact

    def test_creates_metadata_if_missing(self):
        """Test metadata dict is created if needed for content_hash."""
        artifact = {
            "path": "test",
            "excluded": True,
            "content_hash": "abc123",
        }

        result = mark_for_restore(artifact)

        assert "metadata" in result
        assert result["metadata"]["content_hash"] == "abc123"

    def test_preserves_other_metadata(self):
        """Test other metadata fields are preserved."""
        artifact = {
            "path": "test",
            "excluded": True,
            "metadata": {
                "content_hash": "abc123",
                "other_field": "preserved",
                "nested": {"data": "kept"},
            },
        }

        result = mark_for_restore(artifact)

        assert result["metadata"]["other_field"] == "preserved"
        assert result["metadata"]["nested"]["data"] == "kept"

    def test_handles_missing_exclusion_fields(self):
        """Test handles artifacts without some exclusion fields."""
        artifact = {
            "path": "test",
            "excluded": True,
            # Missing: excluded_reason, excluded_at, duplicate_of
        }

        # Should not raise
        result = mark_for_restore(artifact)

        assert "excluded" not in result

    def test_preserves_content_hash_from_metadata(self):
        """Test content_hash from metadata is preserved even without top-level hash."""
        artifact = {
            "path": "test",
            "excluded": True,
            "metadata": {"content_hash": "meta_hash"},
        }

        result = mark_for_restore(artifact)

        assert result["metadata"]["content_hash"] == "meta_hash"


# ============================================================================
# Test: Full Pipeline Integration
# ============================================================================


class TestFullPipeline:
    """Integration tests for complete deduplication pipeline."""

    def test_within_then_cross_source(self, engine: DeduplicationEngine):
        """Test full pipeline: within-source then cross-source dedup."""
        # Raw scan with internal duplicates
        raw_scan = [
            make_artifact("a", {"f.md": "content1"}, confidence_score=0.9),
            make_artifact("b", {"f.md": "content1"}, confidence_score=0.8),  # Dup of a
            make_artifact("c", {"f.md": "content2"}, confidence_score=0.85),
            make_artifact("d", {"f.md": "content3"}, confidence_score=0.7),
        ]

        # Existing collection has content2
        existing_hash = engine.compute_hash({"f.md": "content2"})
        existing_hashes = {existing_hash}

        # Stage 1: Within-source
        kept, within_excluded = engine.deduplicate_within_source(raw_scan)

        assert len(kept) == 3  # a, c, d (b excluded as dup of a)
        assert len(within_excluded) == 1

        # Stage 2: Cross-source
        final, cross_excluded = engine.deduplicate_cross_source(kept, existing_hashes)

        assert len(final) == 2  # a, d (c excluded as cross-source dup)
        assert len(cross_excluded) == 1

        final_paths = {a["path"] for a in final}
        assert final_paths == {"a", "d"}

    def test_pipeline_with_empty_existing(self, engine: DeduplicationEngine):
        """Test pipeline with no existing collection hashes."""
        artifacts = [
            make_artifact("a", {"f.md": "same"}, confidence_score=0.9),
            make_artifact("b", {"f.md": "same"}, confidence_score=0.8),
            make_artifact("c", {"f.md": "unique"}, confidence_score=0.7),
        ]

        kept, within_excluded = engine.deduplicate_within_source(artifacts)
        final, cross_excluded = engine.deduplicate_cross_source(kept, set())

        assert len(final) == 2  # a (best dup) + c (unique)
        assert len(cross_excluded) == 0
        assert len(within_excluded) == 1

    def test_pipeline_preserves_best_selection(self, engine: DeduplicationEngine):
        """Test pipeline correctly preserves best artifact through stages."""
        artifacts = [
            make_artifact("low", {"f.md": "dup"}, confidence_score=0.5),
            make_artifact(
                "high",
                {"f.md": "dup"},
                confidence_score=0.95,
                metadata={"is_manual_mapping": True},
            ),
            make_artifact("mid", {"f.md": "dup"}, confidence_score=0.8),
        ]

        kept, _ = engine.deduplicate_within_source(artifacts)

        # Best (high) should be kept
        assert len(kept) == 1
        assert kept[0]["path"] == "high"
        assert kept[0]["confidence_score"] == 0.95


# ============================================================================
# Test: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_artifact_with_none_files(self, engine: DeduplicationEngine):
        """Test handling artifacts with None files (treated as empty)."""
        artifacts = [
            {
                "path": "test1",
                "files": None,  # type: ignore
                "confidence_score": 0.8,
            },
            {
                "path": "test2",
                "files": None,  # type: ignore
                "confidence_score": 0.7,
            },
        ]

        # Implementation treats None as empty dict via .get("files", {})
        # Both artifacts have same hash (empty files) -> duplicates
        duplicates = engine.find_duplicates(artifacts)

        # Should find them as duplicates (both have empty hash)
        assert len(duplicates) == 1

    def test_very_long_paths(self, engine: DeduplicationEngine):
        """Test handling very long paths in best artifact selection."""
        long_path = "a/" * 100 + "file"
        short_path = "x"

        duplicates = [
            make_artifact(long_path, {"f.md": "same"}, confidence_score=0.9),
            make_artifact(short_path, {"f.md": "same"}, confidence_score=0.9),
        ]

        best = engine.get_best_artifact(duplicates)

        assert best["path"] == short_path

    def test_unicode_paths(self, engine: DeduplicationEngine):
        """Test handling Unicode in paths."""
        artifacts = [
            make_artifact("skills/test", {"f.md": "same"}, confidence_score=0.9),
            make_artifact("skills/other", {"f.md": "same"}, confidence_score=0.8),
        ]

        kept, excluded = engine.deduplicate_within_source(artifacts)

        assert len(kept) == 1
        assert len(excluded) == 1

    def test_special_characters_in_content(self, engine: DeduplicationEngine):
        """Test handling special characters in file content."""
        artifacts = [
            make_artifact("a", {"f.md": "Content with\x00null\x01bytes"}),
            make_artifact("b", {"f.md": "Content with\x00null\x01bytes"}),
        ]

        kept, excluded = engine.deduplicate_within_source(artifacts)

        assert len(kept) == 1
        assert len(excluded) == 1

    def test_confidence_score_boundaries(self, engine: DeduplicationEngine):
        """Test confidence score at boundaries (0.0 and 1.0)."""
        duplicates = [
            make_artifact("zero", {"f.md": "same"}, confidence_score=0.0),
            make_artifact("one", {"f.md": "same"}, confidence_score=1.0),
        ]

        best = engine.get_best_artifact(duplicates)

        assert best["path"] == "one"
        assert best["confidence_score"] == 1.0

    def test_negative_confidence_score(self, engine: DeduplicationEngine):
        """Test handling negative confidence scores."""
        duplicates = [
            make_artifact("neg", {"f.md": "same"}, confidence_score=-0.5),
            make_artifact("pos", {"f.md": "same"}, confidence_score=0.5),
        ]

        best = engine.get_best_artifact(duplicates)

        assert best["path"] == "pos"

    def test_many_duplicates(self, engine: DeduplicationEngine):
        """Test handling many duplicates of same content."""
        artifacts = [
            make_artifact(f"artifact_{i}", {"f.md": "same content"}, confidence_score=i / 100)
            for i in range(100)
        ]

        kept, excluded = engine.deduplicate_within_source(artifacts)

        assert len(kept) == 1
        assert len(excluded) == 99
        assert kept[0]["path"] == "artifact_99"  # Highest confidence
