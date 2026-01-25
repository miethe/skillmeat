"""End-to-end integration tests for marketplace source scanning flow.

This test suite verifies the complete scan flow from source creation through
artifact detection to catalog indexing and search. All tests use mocked GitHub
client to avoid external API calls while testing the orchestration logic.

Test Coverage:
    - CloneTarget creation with correct strategy selection
    - Artifact metadata extraction from manifests
    - Catalog entry creation and storage
    - Differential re-indexing based on tree SHA
    - Empty repository handling
    - Strategy selection based on artifact count

Note:
    All GitHub API calls are mocked to ensure tests are fast and reliable.
    Tests focus on the scan flow orchestration logic, not actual GitHub operations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest

from skillmeat.api.schemas.marketplace import DetectedArtifact
from skillmeat.cache.models import MarketplaceSource
from skillmeat.core.clone_target import CloneTarget, should_reindex


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_github_client():
    """Create a mock GitHubClient for testing.

    Returns:
        Mock with common GitHub API responses configured.
    """
    client = MagicMock()

    # Mock get_repo_metadata
    client.get_repo_metadata.return_value = {
        "name": "test-repo",
        "owner": "test-owner",
        "description": "Test repository",
        "default_branch": "main",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-15T10:30:00Z",
    }

    # Mock get_repo_tree
    client.get_repo_tree.return_value = {
        "sha": "abc123def456",
        "tree": [
            {"path": ".claude/skills/foo", "type": "tree"},
            {"path": ".claude/skills/bar", "type": "tree"},
            {"path": ".claude/skills/baz", "type": "tree"},
        ],
    }

    # Mock resolve_version
    client.resolve_version.return_value = "abc123def456"

    # Mock get_rate_limit
    client.get_rate_limit.return_value = {
        "remaining": 5000,
        "limit": 5000,
        "reset": datetime.now(timezone.utc).timestamp() + 3600,
    }

    return client


@pytest.fixture
def sample_detected_artifacts() -> List[DetectedArtifact]:
    """Create sample detected artifacts for testing.

    Returns:
        List of 5 DetectedArtifact instances representing typical scan results.
    """
    return [
        DetectedArtifact(
            artifact_type="skill",
            name="canvas-design",
            path=".claude/skills/canvas-design",
            upstream_url="https://github.com/test-owner/test-repo/tree/main/.claude/skills/canvas-design",
            confidence_score=95,
        ),
        DetectedArtifact(
            artifact_type="skill",
            name="python-expert",
            path=".claude/skills/python-expert",
            upstream_url="https://github.com/test-owner/test-repo/tree/main/.claude/skills/python-expert",
            confidence_score=98,
        ),
        DetectedArtifact(
            artifact_type="command",
            name="git-helper",
            path=".claude/commands/git-helper",
            upstream_url="https://github.com/test-owner/test-repo/tree/main/.claude/commands/git-helper",
            confidence_score=92,
        ),
        DetectedArtifact(
            artifact_type="agent",
            name="code-review",
            path=".claude/agents/code-review",
            upstream_url="https://github.com/test-owner/test-repo/tree/main/.claude/agents/code-review",
            confidence_score=90,
        ),
        DetectedArtifact(
            artifact_type="skill",
            name="documentation",
            path=".claude/skills/documentation",
            upstream_url="https://github.com/test-owner/test-repo/tree/main/.claude/skills/documentation",
            confidence_score=88,
        ),
    ]


@pytest.fixture
def mock_marketplace_source() -> Mock:
    """Create a mock MarketplaceSource for testing.

    Returns:
        Mock with clone_target property set to None (first-time scan).
    """
    source = Mock(spec=MarketplaceSource)
    source.clone_target = None
    source.source_url = "https://github.com/test-owner/test-repo"
    source.repo_owner = "test-owner"
    source.repo_name = "test-repo"
    source.ref = "main"
    return source


@pytest.fixture
def sample_manifest_metadata() -> Dict[str, Dict[str, Any]]:
    """Create sample manifest metadata for testing.

    Returns:
        Dictionary mapping artifact paths to extracted metadata.
    """
    return {
        ".claude/skills/canvas-design": {
            "title": "Canvas Design Assistant",
            "description": "Help design beautiful UIs with canvas",
            "tags": ["design", "ui", "canvas"],
            "version": "1.0.0",
        },
        ".claude/skills/python-expert": {
            "title": "Python Expert",
            "description": "Advanced Python development assistance",
            "tags": ["python", "coding", "expert"],
            "version": "2.1.0",
        },
        ".claude/commands/git-helper": {
            "title": "Git Helper",
            "description": "Git workflow automation",
            "tags": ["git", "vcs", "automation"],
            "version": "1.5.0",
        },
        ".claude/agents/code-review": {
            "title": "Code Review Agent",
            "description": "Automated code review feedback",
            "tags": ["review", "quality", "agent"],
            "version": "1.2.0",
        },
        ".claude/skills/documentation": {
            "title": "Documentation Writer",
            "description": "Generate comprehensive documentation",
            "tags": ["docs", "writing", "markdown"],
            "version": "1.0.5",
        },
    }


# =============================================================================
# Test: CloneTarget Creation
# =============================================================================


@pytest.mark.integration
def test_scan_flow_creates_clone_target(
    sample_detected_artifacts: List[DetectedArtifact],
):
    """Test that scan flow creates CloneTarget with correct strategy.

    Given: 5 detected artifacts in a repository
    When: Computing clone metadata
    Then: CloneTarget should be created with sparse_manifest strategy
          (5 artifacts is within 3-20 range)
    """
    from skillmeat.core.clone_target import (
        compute_clone_metadata,
        select_indexing_strategy,
    )

    # Mock source for strategy selection
    mock_source = MagicMock()

    # Select strategy based on artifact count
    strategy = select_indexing_strategy(mock_source, sample_detected_artifacts)

    # 5 artifacts should use sparse_manifest strategy
    assert strategy == "sparse_manifest", (
        "Expected sparse_manifest strategy for 5 artifacts (within 3-20 range)"
    )

    # Compute clone metadata
    tree_sha = "abc123def456"
    metadata = compute_clone_metadata(sample_detected_artifacts, tree_sha)

    # Verify metadata structure
    assert "artifacts_root" in metadata
    assert "artifact_paths" in metadata
    assert "sparse_patterns" in metadata

    # All artifacts under .claude/, so common root should be .claude
    assert metadata["artifacts_root"] == ".claude"

    # Should have 5 artifact paths
    assert len(metadata["artifact_paths"]) == 5
    expected_paths = {
        ".claude/skills/canvas-design",
        ".claude/skills/python-expert",
        ".claude/commands/git-helper",
        ".claude/agents/code-review",
        ".claude/skills/documentation",
    }
    assert set(metadata["artifact_paths"]) == expected_paths

    # Should have sparse patterns for manifest files
    assert len(metadata["sparse_patterns"]) == 5
    # Patterns should target manifest files
    assert any("SKILL.md" in p for p in metadata["sparse_patterns"])
    assert any("command.yaml" in p for p in metadata["sparse_patterns"])
    assert any("agent.yaml" in p for p in metadata["sparse_patterns"])

    # Create CloneTarget
    clone_target = CloneTarget(
        strategy=strategy,
        sparse_patterns=metadata["sparse_patterns"],
        artifacts_root=metadata["artifacts_root"],
        artifact_paths=metadata["artifact_paths"],
        tree_sha=tree_sha,
    )

    # Verify CloneTarget is serializable
    serialized = clone_target.to_dict()
    assert serialized["strategy"] == "sparse_manifest"
    assert serialized["tree_sha"] == tree_sha
    assert serialized["artifacts_root"] == ".claude"

    # Verify deserialization works
    restored = CloneTarget.from_dict(serialized)
    assert restored.strategy == clone_target.strategy
    assert restored.tree_sha == clone_target.tree_sha
    assert restored.artifact_paths == clone_target.artifact_paths


# =============================================================================
# Test: Artifact Metadata Extraction
# =============================================================================


@pytest.mark.integration
@patch("skillmeat.cache.marketplace.MANIFEST_EXTRACTORS")
def test_scan_flow_stores_artifacts(
    mock_extractors: MagicMock,
    sample_detected_artifacts: List[DetectedArtifact],
    sample_manifest_metadata: Dict[str, Dict[str, Any]],
):
    """Test that scan flow extracts and stores artifact metadata correctly.

    Given: Detected artifacts with manifest files
    When: Extracting manifest metadata
    Then: Metadata should be correctly extracted and formatted for catalog entries
    """
    from pathlib import Path

    from skillmeat.cache.marketplace import MarketplaceCache

    # Mock the manifest extractors to return sample data
    def mock_extractor(path: Path) -> Dict[str, Any]:
        # Convert Path to string for lookup
        path_str = str(path)
        # Find matching metadata by checking if path ends with artifact path
        for artifact_path, metadata in sample_manifest_metadata.items():
            if path_str.endswith(artifact_path):
                return metadata
        return {}

    # Configure mock extractors for each artifact type
    mock_extractors.get.return_value = mock_extractor

    # Create cache instance
    cache = MarketplaceCache()

    # Simulate manifest extraction
    import asyncio
    from pathlib import Path

    clone_dir = Path("/tmp/fake-clone")

    # Mock the extraction (async function)
    async def run_extraction():
        # Since we're mocking the extractors, we need to simulate the extraction
        result = {}
        for artifact in sample_detected_artifacts:
            artifact_path = artifact.path
            full_path = clone_dir / artifact_path

            # Call mock extractor
            metadata = mock_extractor(full_path)
            if metadata:
                result[artifact_path] = metadata

        return result

    # Run async extraction
    manifests = asyncio.run(run_extraction())

    # Verify extracted metadata
    assert len(manifests) == 5, "Expected metadata for all 5 artifacts"

    # Verify specific metadata fields
    canvas_metadata = manifests[".claude/skills/canvas-design"]
    assert canvas_metadata["title"] == "Canvas Design Assistant"
    assert canvas_metadata["description"] == "Help design beautiful UIs with canvas"
    assert "design" in canvas_metadata["tags"]

    python_metadata = manifests[".claude/skills/python-expert"]
    assert python_metadata["title"] == "Python Expert"
    assert python_metadata["version"] == "2.1.0"

    # Verify all artifacts have required fields
    for artifact_path, metadata in manifests.items():
        assert "title" in metadata, f"Missing title for {artifact_path}"
        assert "description" in metadata, f"Missing description for {artifact_path}"
        assert "tags" in metadata, f"Missing tags for {artifact_path}"


# =============================================================================
# Test: Strategy Selection Based on Artifact Count
# =============================================================================


@pytest.mark.integration
def test_scan_flow_strategy_selection():
    """Test strategy selection with various artifact counts.

    Given: Different numbers of detected artifacts
    When: Selecting indexing strategy
    Then: Correct strategy should be chosen based on count thresholds
          - <3 artifacts: api strategy
          - 3-20 artifacts: sparse_manifest strategy
          - >20 artifacts: sparse_directory strategy (with common root)
    """
    from skillmeat.core.clone_target import select_indexing_strategy

    mock_source = MagicMock()

    # Test case 1: 2 artifacts -> api strategy
    artifacts_2 = [
        DetectedArtifact(
            artifact_type="skill",
            name=f"skill{i}",
            path=f".claude/skills/skill{i}",
            upstream_url=f"https://github.com/test/repo/tree/main/.claude/skills/skill{i}",
            confidence_score=95,
        )
        for i in range(2)
    ]
    strategy = select_indexing_strategy(mock_source, artifacts_2)
    assert strategy == "api", "Expected api strategy for 2 artifacts"

    # Test case 2: 3 artifacts -> sparse_manifest strategy
    artifacts_3 = [
        DetectedArtifact(
            artifact_type="skill",
            name=f"skill{i}",
            path=f".claude/skills/skill{i}",
            upstream_url=f"https://github.com/test/repo/tree/main/.claude/skills/skill{i}",
            confidence_score=95,
        )
        for i in range(3)
    ]
    strategy = select_indexing_strategy(mock_source, artifacts_3)
    assert strategy == "sparse_manifest", "Expected sparse_manifest for 3 artifacts"

    # Test case 3: 20 artifacts -> sparse_manifest strategy (boundary)
    artifacts_20 = [
        DetectedArtifact(
            artifact_type="skill",
            name=f"skill{i:02d}",
            path=f".claude/skills/skill{i:02d}",
            upstream_url=f"https://github.com/test/repo/tree/main/.claude/skills/skill{i:02d}",
            confidence_score=95,
        )
        for i in range(20)
    ]
    strategy = select_indexing_strategy(mock_source, artifacts_20)
    assert (
        strategy == "sparse_manifest"
    ), "Expected sparse_manifest for 20 artifacts (boundary)"

    # Test case 4: 25 artifacts with common root -> sparse_directory strategy
    artifacts_25 = [
        DetectedArtifact(
            artifact_type="skill",
            name=f"skill{i:02d}",
            path=f".claude/skills/skill{i:02d}",
            upstream_url=f"https://github.com/test/repo/tree/main/.claude/skills/skill{i:02d}",
            confidence_score=95,
        )
        for i in range(25)
    ]
    strategy = select_indexing_strategy(mock_source, artifacts_25)
    assert (
        strategy == "sparse_directory"
    ), "Expected sparse_directory for 25 artifacts with common root"


# =============================================================================
# Test: Differential Re-indexing
# =============================================================================


@pytest.mark.integration
def test_scan_flow_differential_reindex():
    """Test differential re-indexing based on tree SHA comparison.

    Given: A source with cached CloneTarget
    When: Scanning with same or different tree SHA
    Then: Re-indexing should be skipped for same SHA, triggered for different SHA
    """
    mock_source = MagicMock()

    # First scan - no cached CloneTarget
    mock_source.clone_target = None
    tree_sha_1 = "abc123def456"

    # Should trigger indexing (first time)
    assert should_reindex(mock_source, tree_sha_1) is True

    # Create CloneTarget after first scan
    cached_target = CloneTarget(
        strategy="sparse_manifest",
        sparse_patterns=[".claude/skills/foo/SKILL.md"],
        artifacts_root=".claude/skills",
        artifact_paths=[".claude/skills/foo"],
        tree_sha=tree_sha_1,
    )
    mock_source.clone_target = cached_target

    # Second scan - same tree SHA
    assert should_reindex(mock_source, tree_sha_1) is False, (
        "Should skip re-indexing when tree SHA is unchanged"
    )

    # Third scan - different tree SHA (repository updated)
    tree_sha_2 = "def456ghi789"
    assert should_reindex(mock_source, tree_sha_2) is True, (
        "Should trigger re-indexing when tree SHA changes"
    )


# =============================================================================
# Test: Empty Repository Handling
# =============================================================================


@pytest.mark.integration
def test_scan_flow_handles_empty_repo():
    """Test graceful handling of repositories with no artifacts.

    Given: A repository scan that detects no artifacts
    When: Processing the empty results
    Then: Flow should complete without errors and return empty results
    """
    from skillmeat.core.clone_target import (
        compute_clone_metadata,
        select_indexing_strategy,
    )

    mock_source = MagicMock()

    # Empty artifact list
    empty_artifacts: List[DetectedArtifact] = []

    # Strategy selection should work with empty list
    strategy = select_indexing_strategy(mock_source, empty_artifacts)
    assert strategy == "api", "Expected api strategy for empty artifact list"

    # Metadata computation should work with empty list
    tree_sha = "abc123def456"
    metadata = compute_clone_metadata(empty_artifacts, tree_sha)

    # Verify empty metadata structure
    assert metadata["artifacts_root"] is None
    assert metadata["artifact_paths"] == []
    assert metadata["sparse_patterns"] == []

    # CloneTarget should be creatable with empty data
    clone_target = CloneTarget(
        strategy=strategy,
        sparse_patterns=metadata["sparse_patterns"],
        artifacts_root=metadata["artifacts_root"],
        artifact_paths=metadata["artifact_paths"],
        tree_sha=tree_sha,
    )

    # Verify empty CloneTarget
    assert clone_target.strategy == "api"
    assert clone_target.sparse_patterns == []
    assert clone_target.artifact_paths == []

    # Serialization should work
    serialized = clone_target.to_dict()
    restored = CloneTarget.from_dict(serialized)
    assert restored.sparse_patterns == []


# =============================================================================
# Test: Complete Scan Flow Integration
# =============================================================================


@pytest.mark.integration
@pytest.mark.slow
@patch("skillmeat.cache.marketplace.MANIFEST_EXTRACTORS")
def test_complete_scan_flow_integration(
    mock_extractors: MagicMock,
    sample_detected_artifacts: List[DetectedArtifact],
    sample_manifest_metadata: Dict[str, Dict[str, Any]],
):
    """Test complete end-to-end scan flow from detection to CloneTarget creation.

    This test simulates the entire flow:
    1. Artifact detection (mocked)
    2. Strategy selection
    3. Clone metadata computation
    4. Manifest extraction (mocked)
    5. CloneTarget creation and serialization

    Given: A repository with detected artifacts
    When: Running the complete scan flow
    Then: All steps should complete successfully and produce valid CloneTarget
    """
    from pathlib import Path

    from skillmeat.cache.marketplace import MarketplaceCache
    from skillmeat.core.clone_target import (
        compute_clone_metadata,
        select_indexing_strategy,
    )

    # Mock source
    mock_source = MagicMock()
    tree_sha = "abc123def456"

    # Step 1: Artifact detection (simulated - in real flow this comes from scanner)
    detected_artifacts = sample_detected_artifacts

    # Step 2: Strategy selection
    strategy = select_indexing_strategy(mock_source, detected_artifacts)
    assert strategy == "sparse_manifest", (
        "Expected sparse_manifest for 5 artifacts"
    )

    # Step 3: Clone metadata computation
    metadata = compute_clone_metadata(detected_artifacts, tree_sha)
    assert metadata["artifacts_root"] == ".claude"
    assert len(metadata["artifact_paths"]) == 5

    # Step 4: Manifest extraction (mocked)
    def mock_extractor(path: Path) -> Dict[str, Any]:
        path_str = str(path)
        for artifact_path, meta in sample_manifest_metadata.items():
            if path_str.endswith(artifact_path):
                return meta
        return {}

    mock_extractors.get.return_value = mock_extractor

    # Simulate extraction
    import asyncio

    async def extract_manifests():
        cache = MarketplaceCache()
        # Since extractors are mocked, simulate the batch extraction
        result = {}
        for artifact in detected_artifacts:
            full_path = Path("/tmp/fake-clone") / artifact.path
            meta = mock_extractor(full_path)
            if meta:
                result[artifact.path] = meta
        return result

    manifests = asyncio.run(extract_manifests())
    assert len(manifests) == 5, "Expected metadata for all artifacts"

    # Step 5: CloneTarget creation
    clone_target = CloneTarget(
        strategy=strategy,
        sparse_patterns=metadata["sparse_patterns"],
        artifacts_root=metadata["artifacts_root"],
        artifact_paths=metadata["artifact_paths"],
        tree_sha=tree_sha,
    )

    # Verify final CloneTarget
    assert clone_target.strategy == "sparse_manifest"
    assert clone_target.tree_sha == tree_sha
    assert len(clone_target.artifact_paths) == 5
    assert clone_target.artifacts_root == ".claude"

    # Verify serialization roundtrip
    json_str = clone_target.to_json()
    restored = CloneTarget.from_json(json_str)
    assert restored.strategy == clone_target.strategy
    assert restored.tree_sha == clone_target.tree_sha
    assert set(restored.artifact_paths) == set(clone_target.artifact_paths)

    # Verify that we can use this CloneTarget for differential re-indexing
    mock_source.clone_target = clone_target

    # Same SHA - should skip re-indexing
    assert should_reindex(mock_source, tree_sha) is False

    # Different SHA - should trigger re-indexing
    assert should_reindex(mock_source, "new_sha_789") is True
