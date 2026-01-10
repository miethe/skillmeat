"""Unit tests for collection membership checking.

This test suite covers:
- CollectionManager.artifact_in_collection() method
- CollectionManager.get_collection_membership_index() method
- CollectionManager.check_membership_batch() method
- Edge cases: case sensitivity, special characters, empty collections
- Performance requirements: <500ms for 100+ artifacts
"""

import time
from datetime import datetime
from pathlib import Path

import pytest

from skillmeat.core.artifact import Artifact, ArtifactMetadata, ArtifactType
from skillmeat.core.collection import Collection, CollectionManager
from skillmeat.storage.lockfile import LockEntry, LockManager


class TestArtifactInCollection:
    """Test suite for artifact_in_collection method."""

    @pytest.fixture
    def collection_with_artifacts(self, tmp_path):
        """Create a collection with various artifacts for testing.

        Creates artifacts with different match criteria:
        - canvas-design: Has GitHub source (for exact match testing)
        - local-skill: No source, only name+type match possible
        - imported-agent: Different type for type matching tests
        """
        collection_path = tmp_path / "collection"
        artifacts_path = collection_path / "artifacts"
        skills_path = artifacts_path / "skills"
        agents_path = artifacts_path / "agents"

        skills_path.mkdir(parents=True)
        agents_path.mkdir(parents=True)

        # Create manifest.toml
        manifest_content = """
[collection]
name = "test-collection"
version = "1.0.0"

[[artifacts]]
name = "canvas-design"
type = "skill"
path = "skills/canvas-design"
origin = "github"
upstream = "anthropics/skills/canvas-design"

[[artifacts]]
name = "local-skill"
type = "skill"
path = "skills/local-skill"
origin = "local"

[[artifacts]]
name = "imported-agent"
type = "agent"
path = "agents/imported-agent"
origin = "github"
upstream = "someone/agents/helper"
"""
        (collection_path / "manifest.toml").write_text(manifest_content)

        # Create artifact directories
        (skills_path / "canvas-design").mkdir()
        (skills_path / "canvas-design" / "SKILL.md").write_text(
            "---\nname: canvas-design\n---\n"
        )
        (skills_path / "local-skill").mkdir()
        (skills_path / "local-skill" / "SKILL.md").write_text(
            "---\nname: local-skill\n---\n"
        )
        (agents_path / "imported-agent").mkdir()
        (agents_path / "imported-agent" / "AGENT.md").write_text(
            "---\nname: imported-agent\n---\n"
        )

        return collection_path

    @pytest.fixture
    def collection_manager(self, collection_with_artifacts, monkeypatch):
        """Create CollectionManager pointing to test collection."""
        # Monkeypatch the config to use our test collection
        collection_path = collection_with_artifacts

        class MockConfig:
            def __init__(self):
                self.active_collection = "test-collection"
                self.base_path = collection_path.parent

            def get_collection_path(self, name=None):
                return collection_path

            def get_active_collection_name(self):
                return "test-collection"

            def get_active_collection(self):
                return "test-collection"

        mgr = CollectionManager.__new__(CollectionManager)
        mgr.config = MockConfig()
        mgr.lock_mgr = LockManager()
        mgr.manifest_mgr = None  # Not needed for these tests

        # Monkeypatch load_collection to return our test collection
        def mock_load_collection(name=None):
            return Collection(
                name="test-collection",
                version="1.0.0",
                artifacts=[
                    Artifact(
                        name="canvas-design",
                        type=ArtifactType.SKILL,
                        path="skills/canvas-design",
                        origin="github",
                        metadata=ArtifactMetadata(),
                        added=datetime.utcnow(),
                        upstream="anthropics/skills/canvas-design",
                    ),
                    Artifact(
                        name="local-skill",
                        type=ArtifactType.SKILL,
                        path="skills/local-skill",
                        origin="local",
                        metadata=ArtifactMetadata(),
                        added=datetime.utcnow(),
                        upstream=None,
                    ),
                    Artifact(
                        name="imported-agent",
                        type=ArtifactType.AGENT,
                        path="agents/imported-agent",
                        origin="github",
                        metadata=ArtifactMetadata(),
                        added=datetime.utcnow(),
                        upstream="someone/agents/helper",
                    ),
                ],
                created=datetime.utcnow(),
                updated=datetime.utcnow(),
            )

        mgr.load_collection = mock_load_collection
        return mgr

    def test_exact_source_match(self, collection_manager):
        """Test finding artifact by exact source_link match."""
        in_coll, matched_id, match_type = collection_manager.artifact_in_collection(
            name="canvas-design",
            artifact_type="skill",
            source_link="anthropics/skills/canvas-design",
        )

        assert in_coll is True
        assert matched_id == "skill:canvas-design"
        assert match_type == "exact"

    def test_source_match_case_insensitive(self, collection_manager):
        """Test source matching is case-insensitive."""
        in_coll, matched_id, match_type = collection_manager.artifact_in_collection(
            name="canvas-design",
            artifact_type="skill",
            source_link="ANTHROPICS/SKILLS/CANVAS-DESIGN",
        )

        assert in_coll is True
        assert matched_id == "skill:canvas-design"
        assert match_type == "exact"

    def test_name_type_match_when_no_source(self, collection_manager):
        """Test falling back to name+type match when no source provided."""
        in_coll, matched_id, match_type = collection_manager.artifact_in_collection(
            name="local-skill",
            artifact_type="skill",
        )

        assert in_coll is True
        assert matched_id == "skill:local-skill"
        assert match_type == "name_type"

    def test_name_type_match_case_insensitive(self, collection_manager):
        """Test name+type matching is case-insensitive."""
        in_coll, matched_id, match_type = collection_manager.artifact_in_collection(
            name="LOCAL-SKILL",
            artifact_type="SKILL",
        )

        assert in_coll is True
        assert matched_id == "skill:local-skill"
        assert match_type == "name_type"

    def test_not_in_collection(self, collection_manager):
        """Test artifact not found returns appropriate result."""
        in_coll, matched_id, match_type = collection_manager.artifact_in_collection(
            name="nonexistent-skill",
            artifact_type="skill",
        )

        assert in_coll is False
        assert matched_id is None
        assert match_type == "none"

    def test_same_name_different_type(self, collection_manager):
        """Test same name with different type is not matched."""
        # canvas-design exists as skill, not as command
        in_coll, matched_id, match_type = collection_manager.artifact_in_collection(
            name="canvas-design",
            artifact_type="command",
        )

        assert in_coll is False
        assert matched_id is None
        assert match_type == "none"

    def test_agent_type_matching(self, collection_manager):
        """Test matching works for different artifact types."""
        in_coll, matched_id, match_type = collection_manager.artifact_in_collection(
            name="imported-agent",
            artifact_type="agent",
        )

        assert in_coll is True
        assert matched_id == "agent:imported-agent"
        assert match_type == "name_type"

    def test_source_match_priority_over_name_type(self, collection_manager):
        """Test source match takes priority over name+type match."""
        # Even if name+type would match, source match should win
        in_coll, matched_id, match_type = collection_manager.artifact_in_collection(
            name="canvas-design",
            artifact_type="skill",
            source_link="anthropics/skills/canvas-design",
        )

        assert in_coll is True
        assert match_type == "exact"  # Not "name_type"


class TestCollectionMembershipIndex:
    """Test suite for get_collection_membership_index method."""

    @pytest.fixture
    def collection_manager_with_index(self, tmp_path):
        """Create CollectionManager with mock collection for index testing."""
        collection_path = tmp_path / "collection"
        collection_path.mkdir()

        class MockConfig:
            def __init__(self):
                self.active_collection = "test-collection"
                self.base_path = collection_path.parent

            def get_collection_path(self, name=None):
                return collection_path

            def get_active_collection_name(self):
                return "test-collection"

            def get_active_collection(self):
                return "test-collection"

        mgr = CollectionManager.__new__(CollectionManager)
        mgr.config = MockConfig()
        mgr.lock_mgr = LockManager()

        def mock_load_collection(name=None):
            return Collection(
                name="test-collection",
                version="1.0.0",
                artifacts=[
                    Artifact(
                        name="skill-1",
                        type=ArtifactType.SKILL,
                        path="skills/skill-1",
                        origin="github",
                        metadata=ArtifactMetadata(),
                        added=datetime.utcnow(),
                        upstream="user/repo/skill-1",
                    ),
                    Artifact(
                        name="skill-2",
                        type=ArtifactType.SKILL,
                        path="skills/skill-2",
                        origin="local",
                        metadata=ArtifactMetadata(),
                        added=datetime.utcnow(),
                        upstream=None,
                    ),
                    Artifact(
                        name="command-1",
                        type=ArtifactType.COMMAND,
                        path="commands/command-1",
                        origin="github",
                        metadata=ArtifactMetadata(),
                        added=datetime.utcnow(),
                        upstream="user/repo/command-1",
                    ),
                ],
                created=datetime.utcnow(),
                updated=datetime.utcnow(),
            )

        mgr.load_collection = mock_load_collection
        return mgr

    def test_index_contains_sources(self, collection_manager_with_index):
        """Test index has by_source entries for artifacts with upstream."""
        index = collection_manager_with_index.get_collection_membership_index()

        assert "by_source" in index
        assert "user/repo/skill-1" in index["by_source"]
        assert "user/repo/command-1" in index["by_source"]
        # skill-2 has no upstream, should not be in by_source
        assert len(index["by_source"]) == 2

    def test_index_contains_name_type_entries(self, collection_manager_with_index):
        """Test index has by_name_type entries for all artifacts."""
        index = collection_manager_with_index.get_collection_membership_index()

        assert "by_name_type" in index
        assert ("skill-1", "skill") in index["by_name_type"]
        assert ("skill-2", "skill") in index["by_name_type"]
        assert ("command-1", "command") in index["by_name_type"]
        assert len(index["by_name_type"]) == 3

    def test_index_sources_normalized_lowercase(self, collection_manager_with_index):
        """Test source links are normalized to lowercase in index."""
        index = collection_manager_with_index.get_collection_membership_index()

        # All source keys should be lowercase
        for source_key in index["by_source"].keys():
            assert source_key == source_key.lower()

    def test_empty_collection_returns_empty_index(self, tmp_path):
        """Test empty collection returns empty index."""
        collection_path = tmp_path / "empty-collection"
        collection_path.mkdir()

        class MockConfig:
            def get_collection_path(self, name=None):
                return collection_path

            def get_active_collection_name(self):
                return "empty"

            def get_active_collection(self):
                return "empty"

        mgr = CollectionManager.__new__(CollectionManager)
        mgr.config = MockConfig()
        mgr.lock_mgr = LockManager()

        def mock_load_collection(name=None):
            return Collection(
                name="empty",
                version="1.0.0",
                artifacts=[],
                created=datetime.utcnow(),
                updated=datetime.utcnow(),
            )

        mgr.load_collection = mock_load_collection
        index = mgr.get_collection_membership_index()

        assert index["by_source"] == {}
        assert index["by_name_type"] == {}
        assert index["artifacts"] == []


class TestCheckMembershipBatch:
    """Test suite for check_membership_batch method."""

    @pytest.fixture
    def batch_collection_manager(self, tmp_path):
        """Create CollectionManager for batch testing."""
        collection_path = tmp_path / "collection"
        collection_path.mkdir()

        class MockConfig:
            def get_collection_path(self, name=None):
                return collection_path

            def get_active_collection_name(self):
                return "batch-test"

            def get_active_collection(self):
                return "batch-test"

        mgr = CollectionManager.__new__(CollectionManager)
        mgr.config = MockConfig()
        mgr.lock_mgr = LockManager()

        def mock_load_collection(name=None):
            return Collection(
                name="batch-test",
                version="1.0.0",
                artifacts=[
                    Artifact(
                        name=f"skill-{i}",
                        type=ArtifactType.SKILL,
                        path=f"skills/skill-{i}",
                        origin="github",
                        metadata=ArtifactMetadata(),
                        added=datetime.utcnow(),
                        upstream=f"user/repo/skill-{i}" if i % 2 == 0 else None,
                    )
                    for i in range(10)
                ],
                created=datetime.utcnow(),
                updated=datetime.utcnow(),
            )

        mgr.load_collection = mock_load_collection
        return mgr

    def test_batch_finds_all_matching(self, batch_collection_manager):
        """Test batch check finds matching artifacts."""
        artifacts = [
            {"name": "skill-0", "artifact_type": "skill", "source_link": "user/repo/skill-0"},
            {"name": "skill-1", "artifact_type": "skill"},  # No source, name+type match
            {"name": "skill-999", "artifact_type": "skill"},  # Not in collection
        ]

        results = batch_collection_manager.check_membership_batch(artifacts)

        assert len(results) == 3
        # skill-0: exact source match
        assert results[0] == (True, "skill:skill-0", "exact")
        # skill-1: name+type match (no source)
        assert results[1] == (True, "skill:skill-1", "name_type")
        # skill-999: not found
        assert results[2] == (False, None, "none")

    def test_batch_preserves_order(self, batch_collection_manager):
        """Test batch results are in same order as input."""
        artifacts = [
            {"name": "skill-9", "artifact_type": "skill"},
            {"name": "not-found", "artifact_type": "skill"},
            {"name": "skill-0", "artifact_type": "skill", "source_link": "user/repo/skill-0"},
        ]

        results = batch_collection_manager.check_membership_batch(artifacts)

        assert len(results) == 3
        assert results[0][1] == "skill:skill-9"  # First input
        assert results[1][0] is False  # Second input
        assert results[2][1] == "skill:skill-0"  # Third input


class TestPerformance:
    """Test suite for performance requirements."""

    @pytest.fixture
    def large_collection_manager(self, tmp_path):
        """Create CollectionManager with large collection for performance testing."""
        collection_path = tmp_path / "large-collection"
        collection_path.mkdir()

        class MockConfig:
            def get_collection_path(self, name=None):
                return collection_path

            def get_active_collection_name(self):
                return "large"

            def get_active_collection(self):
                return "large"

        mgr = CollectionManager.__new__(CollectionManager)
        mgr.config = MockConfig()
        mgr.lock_mgr = LockManager()

        # Create 500 artifacts for performance testing
        def mock_load_collection(name=None):
            artifacts = []
            for i in range(500):
                artifacts.append(
                    Artifact(
                        name=f"artifact-{i:04d}",
                        type=ArtifactType.SKILL if i % 5 != 0 else ArtifactType.COMMAND,
                        path=f"artifacts/artifact-{i:04d}",
                        origin="github",
                        metadata=ArtifactMetadata(),
                        added=datetime.utcnow(),
                        upstream=f"user/repo/artifact-{i:04d}",
                    )
                )
            return Collection(
                name="large",
                version="1.0.0",
                artifacts=artifacts,
                created=datetime.utcnow(),
                updated=datetime.utcnow(),
            )

        mgr.load_collection = mock_load_collection
        return mgr

    def test_batch_check_performance_100_artifacts(self, large_collection_manager):
        """Test batch membership check completes in <500ms for 100+ artifacts.

        Performance requirement: <500ms total for 100+ artifacts.
        """
        # Create 150 test artifacts to check (mix of in/not in collection)
        artifacts_to_check = []
        for i in range(150):
            if i < 100:
                # In collection (even/odd mix of source/name+type match)
                artifacts_to_check.append({
                    "name": f"artifact-{i:04d}",
                    "artifact_type": "skill" if i % 5 != 0 else "command",
                    "source_link": f"user/repo/artifact-{i:04d}" if i % 2 == 0 else None,
                })
            else:
                # Not in collection
                artifacts_to_check.append({
                    "name": f"not-found-{i}",
                    "artifact_type": "skill",
                })

        start = time.perf_counter()
        results = large_collection_manager.check_membership_batch(artifacts_to_check)
        duration_ms = (time.perf_counter() - start) * 1000

        assert len(results) == 150
        assert duration_ms < 500, f"Batch check took {duration_ms:.2f}ms (expected <500ms)"
        print(f"\n  Performance: Checked {len(artifacts_to_check)} artifacts in {duration_ms:.3f}ms")

    def test_index_build_performance(self, large_collection_manager):
        """Test index building is efficient for large collections."""
        start = time.perf_counter()
        index = large_collection_manager.get_collection_membership_index()
        duration_ms = (time.perf_counter() - start) * 1000

        assert len(index["by_source"]) == 500
        assert len(index["by_name_type"]) == 500
        assert duration_ms < 200, f"Index build took {duration_ms:.2f}ms (expected <200ms)"
        print(f"\n  Performance: Built index for 500 artifacts in {duration_ms:.3f}ms")


class TestEdgeCases:
    """Test suite for edge cases."""

    @pytest.fixture
    def edge_case_manager(self, tmp_path):
        """Create CollectionManager for edge case testing."""
        collection_path = tmp_path / "edge-collection"
        collection_path.mkdir()

        class MockConfig:
            def get_collection_path(self, name=None):
                return collection_path

            def get_active_collection_name(self):
                return "edge"

            def get_active_collection(self):
                return "edge"

        mgr = CollectionManager.__new__(CollectionManager)
        mgr.config = MockConfig()
        mgr.lock_mgr = LockManager()

        def mock_load_collection(name=None):
            return Collection(
                name="edge",
                version="1.0.0",
                artifacts=[
                    # Artifact with special characters in name
                    Artifact(
                        name="my-skill_v2.0",
                        type=ArtifactType.SKILL,
                        path="skills/my-skill_v2.0",
                        origin="github",
                        metadata=ArtifactMetadata(),
                        added=datetime.utcnow(),
                        upstream="user/repo/my-skill_v2.0",
                    ),
                    # Artifact with unicode in name
                    Artifact(
                        name="skill-日本語",
                        type=ArtifactType.SKILL,
                        path="skills/skill-japanese",
                        origin="local",
                        metadata=ArtifactMetadata(),
                        added=datetime.utcnow(),
                        upstream=None,
                    ),
                    # Artifact with leading/trailing whitespace in source
                    Artifact(
                        name="whitespace-skill",
                        type=ArtifactType.SKILL,
                        path="skills/whitespace-skill",
                        origin="github",
                        metadata=ArtifactMetadata(),
                        added=datetime.utcnow(),
                        upstream="  user/repo/whitespace  ",  # Has whitespace
                    ),
                ],
                created=datetime.utcnow(),
                updated=datetime.utcnow(),
            )

        mgr.load_collection = mock_load_collection
        return mgr

    def test_special_characters_in_name(self, edge_case_manager):
        """Test matching works with special characters in artifact name."""
        in_coll, matched_id, match_type = edge_case_manager.artifact_in_collection(
            name="my-skill_v2.0",
            artifact_type="skill",
        )

        assert in_coll is True
        assert matched_id == "skill:my-skill_v2.0"

    def test_unicode_in_name(self, edge_case_manager):
        """Test matching works with unicode characters in artifact name."""
        in_coll, matched_id, match_type = edge_case_manager.artifact_in_collection(
            name="skill-日本語",
            artifact_type="skill",
        )

        assert in_coll is True
        assert matched_id == "skill:skill-日本語"

    def test_whitespace_in_source_normalized(self, edge_case_manager):
        """Test source with whitespace is properly normalized."""
        # Query with trimmed source should still match
        in_coll, matched_id, match_type = edge_case_manager.artifact_in_collection(
            name="whitespace-skill",
            artifact_type="skill",
            source_link="user/repo/whitespace",
        )

        assert in_coll is True
        assert match_type == "exact"

    def test_empty_name_handled(self, edge_case_manager):
        """Test empty name is handled gracefully."""
        in_coll, matched_id, match_type = edge_case_manager.artifact_in_collection(
            name="",
            artifact_type="skill",
        )

        assert in_coll is False
        assert match_type == "none"

    def test_none_source_handled(self, edge_case_manager):
        """Test None source doesn't cause issues."""
        in_coll, matched_id, match_type = edge_case_manager.artifact_in_collection(
            name="my-skill_v2.0",
            artifact_type="skill",
            source_link=None,
        )

        # Should fall back to name+type match
        assert in_coll is True
        assert match_type == "name_type"


class TestEmptyCollection:
    """Test suite for empty collection scenarios."""

    @pytest.fixture
    def empty_collection_manager(self, tmp_path):
        """Create CollectionManager with empty collection."""
        collection_path = tmp_path / "empty-collection"
        collection_path.mkdir()

        class MockConfig:
            def get_collection_path(self, name=None):
                return collection_path

            def get_active_collection_name(self):
                return "empty"

            def get_active_collection(self):
                return "empty"

        mgr = CollectionManager.__new__(CollectionManager)
        mgr.config = MockConfig()
        mgr.lock_mgr = LockManager()

        def mock_load_collection(name=None):
            return Collection(
                name="empty",
                version="1.0.0",
                artifacts=[],
                created=datetime.utcnow(),
                updated=datetime.utcnow(),
            )

        mgr.load_collection = mock_load_collection
        return mgr

    def test_empty_collection_returns_not_in_collection(self, empty_collection_manager):
        """Test all discovered artifacts show not in collection."""
        in_coll, matched_id, match_type = empty_collection_manager.artifact_in_collection(
            name="any-artifact",
            artifact_type="skill",
        )

        assert in_coll is False
        assert matched_id is None
        assert match_type == "none"

    def test_empty_collection_batch_all_not_found(self, empty_collection_manager):
        """Test batch check returns all not found for empty collection."""
        artifacts = [
            {"name": f"skill-{i}", "artifact_type": "skill"}
            for i in range(10)
        ]

        results = empty_collection_manager.check_membership_batch(artifacts)

        assert all(r == (False, None, "none") for r in results)
