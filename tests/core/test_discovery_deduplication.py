"""Tests for hash-based deduplication in artifact discovery.

Tests the integration of content hash matching with the discovery service
to detect duplicate and similar artifacts in the collection.
"""

import hashlib
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from skillmeat.core.discovery import (
    ArtifactDiscoveryService,
    CollectionMatchInfo,
    CollectionStatusInfo,
    DiscoveredArtifact,
    DiscoveryResult,
)


def compute_test_hash(content: str) -> str:
    """Compute SHA256 hash for test content."""
    return hashlib.sha256(content.encode()).hexdigest()


def create_skill_directory(base_path: Path, name: str, content: str = None) -> Path:
    """Create a mock skill directory with SKILL.md file.

    Args:
        base_path: Base directory for skills
        name: Skill name
        content: Optional custom content for SKILL.md

    Returns:
        Path to the created skill directory
    """
    skill_dir = base_path / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)

    skill_content = content or f"""---
name: {name}
description: Test skill {name}
version: "1.0.0"
---

# {name}

This is a test skill for deduplication testing.
"""
    (skill_dir / "SKILL.md").write_text(skill_content)
    return skill_dir


@pytest.fixture
def temp_project():
    """Create a temporary project directory structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        claude_dir = project_path / ".claude"
        claude_dir.mkdir(parents=True)
        (claude_dir / "skills").mkdir()
        (claude_dir / "commands").mkdir()
        (claude_dir / "agents").mkdir()
        yield project_path


@pytest.fixture
def mock_collection_index():
    """Create a mock collection membership index with sample artifacts."""
    # Sample hashes for testing
    canvas_hash = compute_test_hash("canvas content")
    pdf_hash = compute_test_hash("pdf content")

    return {
        "by_source": {
            "anthropics/skills/canvas-design": "skill:canvas-design",
            "anthropics/skills/pdf": "skill:pdf",
        },
        "by_hash": {
            canvas_hash: "skill:canvas-design",
            pdf_hash: "skill:pdf",
        },
        "by_name_type": {
            ("canvas-design", "skill"): "skill:canvas-design",
            ("pdf", "skill"): "skill:pdf",
            ("local-skill", "skill"): "skill:local-skill",
        },
        "artifacts": [
            ("skill:canvas-design", MagicMock(name="canvas-design")),
            ("skill:pdf", MagicMock(name="pdf")),
            ("skill:local-skill", MagicMock(name="local-skill")),
        ],
    }


class TestCollectionMatchInfo:
    """Tests for CollectionMatchInfo model."""

    def test_exact_hash_match(self):
        """Test exact hash match with confidence 1.0."""
        match = CollectionMatchInfo(
            type="exact",
            matched_artifact_id="skill:canvas-design",
            matched_name="canvas-design",
            confidence=1.0,
        )
        assert match.type == "exact"
        assert match.confidence == 1.0
        assert match.matched_artifact_id == "skill:canvas-design"
        assert match.matched_name == "canvas-design"

    def test_name_type_match(self):
        """Test name+type match with confidence 0.85."""
        match = CollectionMatchInfo(
            type="name_type",
            matched_artifact_id="skill:pdf",
            matched_name="pdf",
            confidence=0.85,
        )
        assert match.type == "name_type"
        assert match.confidence == 0.85

    def test_no_match(self):
        """Test no match with confidence 0.0."""
        match = CollectionMatchInfo(
            type="none",
            matched_artifact_id=None,
            matched_name=None,
            confidence=0.0,
        )
        assert match.type == "none"
        assert match.confidence == 0.0
        assert match.matched_artifact_id is None


class TestDiscoveryServiceHashMatching:
    """Tests for hash-based matching in ArtifactDiscoveryService."""

    def test_compute_collection_match_exact_hash(self, temp_project, mock_collection_index):
        """Test exact hash match returns confidence 1.0."""
        service = ArtifactDiscoveryService(temp_project, scan_mode="project")

        # Use hash that exists in index
        canvas_hash = compute_test_hash("canvas content")

        match = service._compute_collection_match(
            content_hash=canvas_hash,
            name="different-name",  # Even with different name, hash match wins
            artifact_type="skill",
            membership_index=mock_collection_index,
        )

        assert match.type == "exact"
        assert match.confidence == 1.0
        assert match.matched_artifact_id == "skill:canvas-design"
        assert match.matched_name == "canvas-design"

    def test_compute_collection_match_name_type(self, temp_project, mock_collection_index):
        """Test name+type match returns confidence 0.85."""
        service = ArtifactDiscoveryService(temp_project, scan_mode="project")

        # Use hash that doesn't exist in index, but name+type matches
        unknown_hash = compute_test_hash("completely different content")

        match = service._compute_collection_match(
            content_hash=unknown_hash,
            name="local-skill",  # Exists in by_name_type
            artifact_type="skill",
            membership_index=mock_collection_index,
        )

        assert match.type == "name_type"
        assert match.confidence == 0.85
        assert match.matched_artifact_id == "skill:local-skill"
        assert match.matched_name == "local-skill"

    def test_compute_collection_match_no_match(self, temp_project, mock_collection_index):
        """Test no match returns confidence 0.0."""
        service = ArtifactDiscoveryService(temp_project, scan_mode="project")

        # Use hash and name that don't exist
        unknown_hash = compute_test_hash("brand new content")

        match = service._compute_collection_match(
            content_hash=unknown_hash,
            name="brand-new-skill",
            artifact_type="skill",
            membership_index=mock_collection_index,
        )

        assert match.type == "none"
        assert match.confidence == 0.0
        assert match.matched_artifact_id is None
        assert match.matched_name is None

    def test_hash_takes_priority_over_name_type(self, temp_project, mock_collection_index):
        """Test that hash match takes priority over name+type match."""
        service = ArtifactDiscoveryService(temp_project, scan_mode="project")

        # Hash matches canvas-design but name matches pdf
        canvas_hash = compute_test_hash("canvas content")

        match = service._compute_collection_match(
            content_hash=canvas_hash,
            name="pdf",  # Would match pdf by name+type
            artifact_type="skill",
            membership_index=mock_collection_index,
        )

        # Hash match should win
        assert match.type == "exact"
        assert match.confidence == 1.0
        assert match.matched_artifact_id == "skill:canvas-design"

    def test_no_hash_falls_back_to_name_type(self, temp_project, mock_collection_index):
        """Test that missing hash falls back to name+type matching."""
        service = ArtifactDiscoveryService(temp_project, scan_mode="project")

        # No hash provided, should fall back to name+type
        match = service._compute_collection_match(
            content_hash=None,
            name="canvas-design",
            artifact_type="skill",
            membership_index=mock_collection_index,
        )

        assert match.type == "name_type"
        assert match.confidence == 0.85
        assert match.matched_artifact_id == "skill:canvas-design"


class TestDiscoveryWithDeduplication:
    """Integration tests for discovery with hash-based deduplication."""

    def test_discovered_artifact_includes_content_hash(self, temp_project):
        """Test that discovered artifacts include content_hash field."""
        # Create a skill
        create_skill_directory(temp_project / ".claude", "test-skill")

        service = ArtifactDiscoveryService(temp_project, scan_mode="project")
        result = service.discover_artifacts(include_collection_status=False)

        assert result.discovered_count >= 1

        # Find the test skill
        test_skill = next(
            (a for a in result.artifacts if a.name == "test-skill"), None
        )
        assert test_skill is not None
        assert test_skill.content_hash is not None
        assert len(test_skill.content_hash) == 64  # SHA256 hex string

    def test_discovered_artifact_includes_collection_match(self, temp_project):
        """Test that discovered artifacts include collection_match when index provided."""
        # Create a skill
        create_skill_directory(temp_project / ".claude", "test-skill")

        # Mock the collection manager to return our test index
        mock_index = {
            "by_source": {},
            "by_hash": {},
            "by_name_type": {},
            "artifacts": [],
        }

        with patch(
            "skillmeat.core.collection.CollectionManager"
        ) as MockCollectionManager:
            mock_mgr = MagicMock()
            mock_mgr.get_collection_membership_index.return_value = mock_index
            MockCollectionManager.return_value = mock_mgr

            service = ArtifactDiscoveryService(temp_project, scan_mode="project")
            result = service.discover_artifacts(include_collection_status=True)

        assert result.discovered_count >= 1

        # Find the test skill
        test_skill = next(
            (a for a in result.artifacts if a.name == "test-skill"), None
        )
        assert test_skill is not None
        # collection_match should be populated (even if no match)
        assert test_skill.collection_match is not None
        assert test_skill.collection_match.type == "none"
        assert test_skill.collection_match.confidence == 0.0

    def test_exact_hash_match_scenario(self, temp_project):
        """Test discovery with exact hash match against collection."""
        # Create skill content
        skill_content = """---
name: canvas
description: Canvas skill
version: "1.0.0"
---

# Canvas

Identical content to collection.
"""
        skill_dir = create_skill_directory(
            temp_project / ".claude", "canvas", skill_content
        )

        # Compute hash of the skill directory
        from skillmeat.utils.filesystem import compute_content_hash
        actual_hash = compute_content_hash(skill_dir)

        # Mock collection index with matching hash
        mock_index = {
            "by_source": {},
            "by_hash": {
                actual_hash: "skill:canvas-design",  # Same content in collection
            },
            "by_name_type": {},
            "artifacts": [],
        }

        with patch(
            "skillmeat.core.collection.CollectionManager"
        ) as MockCollectionManager:
            mock_mgr = MagicMock()
            mock_mgr.get_collection_membership_index.return_value = mock_index
            MockCollectionManager.return_value = mock_mgr

            service = ArtifactDiscoveryService(temp_project, scan_mode="project")
            result = service.discover_artifacts(include_collection_status=True)

        # Find the canvas skill
        canvas_skill = next(
            (a for a in result.artifacts if a.name == "canvas"), None
        )
        assert canvas_skill is not None
        assert canvas_skill.collection_match is not None
        assert canvas_skill.collection_match.type == "exact"
        assert canvas_skill.collection_match.confidence == 1.0
        assert canvas_skill.collection_match.matched_artifact_id == "skill:canvas-design"

    def test_partial_name_type_match_scenario(self, temp_project):
        """Test discovery with name+type match (different content)."""
        # Create skill with same name but different content
        skill_content = """---
name: canvas-design
description: Different canvas skill
version: "2.0.0"
---

# Canvas Design v2

This is different content than the collection version.
"""
        create_skill_directory(
            temp_project / ".claude", "canvas-design", skill_content
        )

        # Mock collection index with name+type match but no hash match
        mock_index = {
            "by_source": {},
            "by_hash": {
                "different_hash_123": "skill:canvas-design",  # Different hash
            },
            "by_name_type": {
                ("canvas-design", "skill"): "skill:canvas-design",
            },
            "artifacts": [],
        }

        with patch(
            "skillmeat.core.collection.CollectionManager"
        ) as MockCollectionManager:
            mock_mgr = MagicMock()
            mock_mgr.get_collection_membership_index.return_value = mock_index
            MockCollectionManager.return_value = mock_mgr

            service = ArtifactDiscoveryService(temp_project, scan_mode="project")
            result = service.discover_artifacts(include_collection_status=True)

        # Find the canvas-design skill
        canvas_skill = next(
            (a for a in result.artifacts if a.name == "canvas-design"), None
        )
        assert canvas_skill is not None
        assert canvas_skill.collection_match is not None
        assert canvas_skill.collection_match.type == "name_type"
        assert canvas_skill.collection_match.confidence == 0.85
        assert canvas_skill.collection_match.matched_artifact_id == "skill:canvas-design"

    def test_no_match_scenario(self, temp_project):
        """Test discovery with no match in collection."""
        # Create a completely new skill
        skill_content = """---
name: brand-new-skill
description: A brand new skill
version: "1.0.0"
---

# Brand New Skill

This skill doesn't exist in the collection.
"""
        create_skill_directory(
            temp_project / ".claude", "brand-new-skill", skill_content
        )

        # Mock collection index with no matches
        mock_index = {
            "by_source": {},
            "by_hash": {},
            "by_name_type": {},
            "artifacts": [],
        }

        with patch(
            "skillmeat.core.collection.CollectionManager"
        ) as MockCollectionManager:
            mock_mgr = MagicMock()
            mock_mgr.get_collection_membership_index.return_value = mock_index
            MockCollectionManager.return_value = mock_mgr

            service = ArtifactDiscoveryService(temp_project, scan_mode="project")
            result = service.discover_artifacts(include_collection_status=True)

        # Find the new skill
        new_skill = next(
            (a for a in result.artifacts if a.name == "brand-new-skill"), None
        )
        assert new_skill is not None
        assert new_skill.collection_match is not None
        assert new_skill.collection_match.type == "none"
        assert new_skill.collection_match.confidence == 0.0
        assert new_skill.collection_match.matched_artifact_id is None

    def test_mixed_match_scenario(self, temp_project):
        """Test discovery with mixed matches: 3 exact, 2 partial, 5 new."""
        # Create 10 skills with different match scenarios

        # 3 skills with exact hash matches
        exact_hashes = {}
        for i in range(3):
            content = f"""---
name: exact-{i}
description: Exact match skill {i}
---
# Exact {i}
Content for exact match {i}
"""
            skill_dir = create_skill_directory(
                temp_project / ".claude", f"exact-{i}", content
            )
            from skillmeat.utils.filesystem import compute_content_hash
            exact_hashes[compute_content_hash(skill_dir)] = f"skill:exact-{i}"

        # 2 skills with name+type matches (different content)
        partial_names = {}
        for i in range(2):
            content = f"""---
name: partial-{i}
description: Partial match skill {i}
---
# Partial {i}
Different content from collection
"""
            create_skill_directory(
                temp_project / ".claude", f"partial-{i}", content
            )
            partial_names[(f"partial-{i}", "skill")] = f"skill:partial-{i}"

        # 5 completely new skills
        for i in range(5):
            content = f"""---
name: new-{i}
description: New skill {i}
---
# New {i}
Brand new content
"""
            create_skill_directory(
                temp_project / ".claude", f"new-{i}", content
            )

        # Mock collection index
        mock_index = {
            "by_source": {},
            "by_hash": exact_hashes,
            "by_name_type": partial_names,
            "artifacts": [],
        }

        with patch(
            "skillmeat.core.collection.CollectionManager"
        ) as MockCollectionManager:
            mock_mgr = MagicMock()
            mock_mgr.get_collection_membership_index.return_value = mock_index
            MockCollectionManager.return_value = mock_mgr

            service = ArtifactDiscoveryService(temp_project, scan_mode="project")
            result = service.discover_artifacts(include_collection_status=True)

        # Count match types
        exact_count = sum(
            1 for a in result.artifacts
            if a.collection_match and a.collection_match.type == "exact"
        )
        partial_count = sum(
            1 for a in result.artifacts
            if a.collection_match and a.collection_match.type == "name_type"
        )
        new_count = sum(
            1 for a in result.artifacts
            if a.collection_match and a.collection_match.type == "none"
        )

        assert exact_count == 3, f"Expected 3 exact matches, got {exact_count}"
        assert partial_count == 2, f"Expected 2 partial matches, got {partial_count}"
        assert new_count == 5, f"Expected 5 new matches, got {new_count}"


class TestPerformance:
    """Performance tests for hash-based deduplication."""

    def test_hash_matching_performance_100_artifacts(self, temp_project):
        """Test that hash matching completes in <500ms for 100+ artifacts."""
        import time

        # Create 100 skills
        for i in range(100):
            content = f"""---
name: perf-test-{i}
description: Performance test skill {i}
---
# Performance Test {i}
Content for testing
"""
            create_skill_directory(
                temp_project / ".claude", f"perf-test-{i}", content
            )

        # Mock collection index with 50 hash matches
        mock_index = {
            "by_source": {},
            "by_hash": {},  # No hash matches for simplicity
            "by_name_type": {},  # No name matches for simplicity
            "artifacts": [],
        }

        with patch(
            "skillmeat.core.collection.CollectionManager"
        ) as MockCollectionManager:
            mock_mgr = MagicMock()
            mock_mgr.get_collection_membership_index.return_value = mock_index
            MockCollectionManager.return_value = mock_mgr

            service = ArtifactDiscoveryService(temp_project, scan_mode="project")

            start_time = time.time()
            result = service.discover_artifacts(include_collection_status=True)
            duration_ms = (time.time() - start_time) * 1000

        assert result.discovered_count >= 100
        assert duration_ms < 500, (
            f"Hash matching took {duration_ms:.2f}ms, expected <500ms"
        )
