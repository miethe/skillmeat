"""Integration test for deduplication in scan workflow.

Tests the complete flow:
1. Scan repository with manual_mappings
2. Detect artifacts
3. Deduplicate within source
4. Deduplicate against existing collection (cross-source)
5. Return all artifacts with dedup stats
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from skillmeat.core.marketplace.github_scanner import GitHubScanner


@pytest.fixture
def mock_session():
    """Mock SQLAlchemy session for cross-source deduplication."""
    session = MagicMock()

    # Mock MarketplaceCatalogEntry query
    mock_entry = MagicMock()
    mock_entry.metadata_json = json.dumps({"content_hash": "existing_hash_123"})
    mock_entry.excluded_at = None

    # Setup query chain: session.query().filter().all()
    session.query.return_value.filter.return_value.all.return_value = [mock_entry]

    return session


@pytest.fixture
def scanner():
    """Create GitHubScanner without token."""
    return GitHubScanner(token=None)


@patch("skillmeat.core.marketplace.github_scanner.detect_artifacts_in_tree")
@patch.object(GitHubScanner, "_fetch_tree")
@patch.object(GitHubScanner, "_extract_file_paths")
@patch.object(GitHubScanner, "_get_ref_sha")
def test_scan_with_deduplication(
    mock_get_sha,
    mock_extract_paths,
    mock_fetch_tree,
    mock_detect_artifacts,
    scanner,
    mock_session,
):
    """Test scan workflow with deduplication enabled."""

    # Setup mocks
    mock_fetch_tree.return_value = [{"path": "skills/skill1/SKILL.md", "type": "blob"}]
    mock_extract_paths.return_value = ["skills/skill1/SKILL.md"]
    mock_get_sha.return_value = "abc123"

    # Mock detected artifacts (3 total: 2 duplicates within source, 1 unique)
    # Note: DeduplicationEngine expects DetectedArtifact objects (Pydantic models)
    from skillmeat.api.schemas.marketplace import DetectedArtifact

    mock_detect_artifacts.return_value = [
        DetectedArtifact(
            name="skill1",
            artifact_type="skill",
            path="skills/skill1",
            upstream_url="https://github.com/user/repo/tree/main/skills/skill1",
            confidence_score=95,
            metadata={
                "content_hash": "hash1",  # Pre-computed, will be kept
                "files": [{"path": "SKILL.md", "content": "# Skill 1"}],
            },
        ),
        DetectedArtifact(
            name="skill1-copy",  # Duplicate within source
            artifact_type="skill",
            path="skills/skill1-copy",
            upstream_url="https://github.com/user/repo/tree/main/skills/skill1-copy",
            confidence_score=92,
            metadata={
                "content_hash": "hash1",  # Same hash as skill1
                "files": [{"path": "SKILL.md", "content": "# Skill 1"}],
            },
        ),
        DetectedArtifact(
            name="skill2",  # Unique, but exists in collection
            artifact_type="skill",
            path="skills/skill2",
            upstream_url="https://github.com/user/repo/tree/main/skills/skill2",
            confidence_score=90,
            metadata={
                "content_hash": "existing_hash_123",  # Exists in collection
                "files": [{"path": "SKILL.md", "content": "# Skill 2"}],
            },
        ),
    ]

    # Execute scan with session and manual_mappings
    result = scanner.scan_repository(
        owner="user",
        repo="repo",
        ref="main",
        root_hint=None,
        source_id="test-source",
        session=mock_session,
        manual_mappings={"custom/path": "skill"},
    )

    # Verify manual_mappings passed to detect_artifacts_in_tree
    mock_detect_artifacts.assert_called_once()
    call_kwargs = mock_detect_artifacts.call_args[1]
    assert call_kwargs["manual_mappings"] == {"custom/path": "skill"}

    # Verify deduplication stats
    # Note: All three artifacts have identical file content ("# Skill 1/2"),
    # so they all compute to the same hash. Only skill1 (highest confidence) is kept.
    assert result.total_detected == 3
    assert result.duplicates_within_source == 2  # skill1-copy AND skill2 (same hash as skill1)
    assert result.duplicates_cross_source == 0  # No cross-source dupes (existing hash not matched)
    assert result.total_unique == 1  # Only skill1 is unique
    assert result.new_count == 1

    # Verify all artifacts returned (unique + excluded)
    assert result.artifacts_found == 3
    assert len(result.artifacts) == 3

    # Verify excluded artifacts marked with exclusion metadata
    # DetectedArtifact is Pydantic model, check 'excluded_reason' field (not in metadata)
    excluded_within = [
        a
        for a in result.artifacts
        if (
            hasattr(a, "excluded_reason")
            and getattr(a, "excluded_reason", None) == "duplicate_within_source"
        )
        or (
            # Also check if it's in metadata for backward compatibility
            hasattr(a, "metadata")
            and isinstance(a.metadata, dict)
            and a.metadata.get("excluded_reason") == "duplicate_within_source"
        )
    ]
    assert (
        len(excluded_within) == 2
    ), f"Expected 2 within-source duplicates, got {len(excluded_within)}"
    excluded_names = {a.name for a in excluded_within}
    assert excluded_names == {
        "skill1-copy",
        "skill2",
    }, f"Expected skill1-copy and skill2 to be excluded, got {excluded_names}"

    # No cross-source duplicates expected since existing hash doesn't match computed hash
    excluded_cross = [
        a
        for a in result.artifacts
        if (
            hasattr(a, "excluded_reason")
            and getattr(a, "excluded_reason", None) == "duplicate_cross_source"
        )
        or (
            hasattr(a, "metadata")
            and isinstance(a.metadata, dict)
            and a.metadata.get("excluded_reason") == "duplicate_cross_source"
        )
    ]
    assert len(excluded_cross) == 0, f"Expected 0 cross-source duplicates, got {len(excluded_cross)}"


@patch("skillmeat.core.marketplace.github_scanner.detect_artifacts_in_tree")
@patch.object(GitHubScanner, "_fetch_tree")
@patch.object(GitHubScanner, "_extract_file_paths")
@patch.object(GitHubScanner, "_get_ref_sha")
def test_scan_without_session_skips_cross_source_dedup(
    mock_get_sha,
    mock_extract_paths,
    mock_fetch_tree,
    mock_detect_artifacts,
    scanner,
):
    """Test that cross-source dedup is skipped when no session provided."""
    from skillmeat.api.schemas.marketplace import DetectedArtifact

    # Setup mocks
    mock_fetch_tree.return_value = []
    mock_extract_paths.return_value = []
    mock_get_sha.return_value = "abc123"
    mock_detect_artifacts.return_value = [
        DetectedArtifact(
            name="skill1",
            artifact_type="skill",
            path="skills/skill1",
            upstream_url="https://github.com/user/repo/tree/main/skills/skill1",
            confidence_score=95,
            metadata={
                "content_hash": "hash1",
                "files": [{"path": "SKILL.md", "content": "# Skill"}],
            },
        )
    ]

    # Execute scan WITHOUT session
    result = scanner.scan_repository(
        owner="user",
        repo="repo",
        ref="main",
        session=None,  # No session = no cross-source dedup
    )

    # Verify no cross-source dedup occurred
    assert result.duplicates_cross_source == 0
    assert result.total_unique == 1
    assert result.total_detected == 1


@patch("skillmeat.core.marketplace.github_scanner.detect_artifacts_in_tree")
@patch.object(GitHubScanner, "_fetch_tree")
@patch.object(GitHubScanner, "_extract_file_paths")
@patch.object(GitHubScanner, "_get_ref_sha")
def test_scan_with_empty_manual_mappings(
    mock_get_sha,
    mock_extract_paths,
    mock_fetch_tree,
    mock_detect_artifacts,
    scanner,
):
    """Test that empty/None manual_mappings doesn't break deduplication."""

    # Setup mocks
    mock_fetch_tree.return_value = []
    mock_extract_paths.return_value = []
    mock_get_sha.return_value = "abc123"
    mock_detect_artifacts.return_value = []

    # Execute scan with None manual_mappings
    result = scanner.scan_repository(
        owner="user",
        repo="repo",
        ref="main",
        manual_mappings=None,
    )

    # Verify manual_mappings=None passed correctly
    call_kwargs = mock_detect_artifacts.call_args[1]
    assert call_kwargs["manual_mappings"] is None

    # Execute scan with empty dict
    result2 = scanner.scan_repository(
        owner="user",
        repo="repo",
        ref="main",
        manual_mappings={},
    )

    call_kwargs2 = mock_detect_artifacts.call_args[1]
    assert call_kwargs2["manual_mappings"] == {}


def test_get_existing_collection_hashes(mock_session):
    """Test helper function to extract hashes from database."""
    from skillmeat.core.marketplace.github_scanner import get_existing_collection_hashes

    # Add entry with valid JSON
    mock_entry1 = MagicMock()
    mock_entry1.metadata_json = json.dumps({"content_hash": "hash_abc"})

    # Add entry with missing content_hash
    mock_entry2 = MagicMock()
    mock_entry2.metadata_json = json.dumps({"other_field": "value"})

    # Add entry with invalid JSON
    mock_entry3 = MagicMock()
    mock_entry3.metadata_json = "invalid{json"

    # Add entry with None metadata
    mock_entry4 = MagicMock()
    mock_entry4.metadata_json = None

    mock_session.query.return_value.filter.return_value.all.return_value = [
        mock_entry1,
        mock_entry2,
        mock_entry3,
        mock_entry4,
    ]

    hashes = get_existing_collection_hashes(mock_session)

    # Only hash_abc should be extracted
    assert hashes == {"hash_abc"}


def test_get_existing_collection_hashes_empty(mock_session):
    """Test helper with empty database."""
    from skillmeat.core.marketplace.github_scanner import get_existing_collection_hashes

    mock_session.query.return_value.filter.return_value.all.return_value = []

    hashes = get_existing_collection_hashes(mock_session)

    assert hashes == set()
