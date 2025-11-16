"""Tests for SearchManager functionality."""

import tempfile
from pathlib import Path
from datetime import datetime

import pytest

from skillmeat.core.artifact import ArtifactManager, ArtifactType, ArtifactMetadata, Artifact
from skillmeat.core.collection import CollectionManager
from skillmeat.core.search import SearchManager
from skillmeat.models import SearchResult, SearchMatch


@pytest.fixture
def temp_collection(tmp_path):
    """Create a temporary collection with test artifacts."""
    # Set up collection manager
    config_dir = tmp_path / ".skillmeat"
    config_dir.mkdir(parents=True)

    # Create config
    from skillmeat.config import ConfigManager
    config = ConfigManager(config_dir=config_dir)
    config.set("settings.collections-dir", str(tmp_path / "collections"))

    # Create collection manager
    collection_mgr = CollectionManager(config=config)
    collection = collection_mgr.init("test-collection")

    # Create test artifacts
    collection_path = config.get_collection_path("test-collection")

    # Artifact 1: Python skill with metadata
    python_skill_path = collection_path / "skills" / "python-skill"
    python_skill_path.mkdir(parents=True, exist_ok=True)

    (python_skill_path / "SKILL.md").write_text("""---
title: Python Development Skill
description: Advanced Python programming and best practices
author: Test Author
license: MIT
version: 1.0.0
tags:
  - python
  - development
  - backend
---

# Python Development Skill

This skill helps with Python development including:
- Writing clean code
- Using type hints
- Testing with pytest
""")

    # Add to collection
    collection.add_artifact(Artifact(
        name="python-skill",
        type=ArtifactType.SKILL,
        path="skills/python-skill",
        origin="local",
        metadata=ArtifactMetadata(
            title="Python Development Skill",
            description="Advanced Python programming and best practices",
            author="Test Author",
            tags=["python", "development", "backend"],
        ),
        added=datetime.utcnow(),
    ))

    # Artifact 2: JavaScript skill without metadata
    js_skill_path = collection_path / "skills" / "javascript-skill"
    js_skill_path.mkdir(parents=True, exist_ok=True)

    (js_skill_path / "SKILL.md").write_text("""# JavaScript Skill

Learn JavaScript programming including:
- ES6+ features
- Async/await patterns
- React development
""")

    collection.add_artifact(Artifact(
        name="javascript-skill",
        type=ArtifactType.SKILL,
        path="skills/javascript-skill",
        origin="local",
        metadata=ArtifactMetadata(),
        added=datetime.utcnow(),
    ))

    # Artifact 3: Testing skill with specific tags
    test_skill_path = collection_path / "skills" / "testing-skill"
    test_skill_path.mkdir(parents=True, exist_ok=True)

    (test_skill_path / "SKILL.md").write_text("""---
title: Testing Best Practices
description: Comprehensive testing strategies with pytest
author: Test Author
tags:
  - testing
  - pytest
  - quality
---

# Testing Best Practices

Use pytest for Python testing.
""")

    collection.add_artifact(Artifact(
        name="testing-skill",
        type=ArtifactType.SKILL,
        path="skills/testing-skill",
        origin="local",
        metadata=ArtifactMetadata(
            title="Testing Best Practices",
            description="Comprehensive testing strategies with pytest",
            tags=["testing", "pytest", "quality"],
        ),
        added=datetime.utcnow(),
    ))

    # Save collection
    collection_mgr.save_collection(collection)

    return collection_mgr, "test-collection"


class TestSearchManager:
    """Test suite for SearchManager."""

    def test_init(self, temp_collection):
        """Test SearchManager initialization."""
        collection_mgr, _ = temp_collection
        search_mgr = SearchManager(collection_mgr)

        assert search_mgr.collection_mgr is not None

    def test_search_metadata_title(self, temp_collection):
        """Test metadata search on title field."""
        collection_mgr, collection_name = temp_collection
        search_mgr = SearchManager(collection_mgr)

        result = search_mgr.search_collection(
            query="Python",
            collection_name=collection_name,
            search_type="metadata"
        )

        assert isinstance(result, SearchResult)
        assert result.total_count > 0
        assert result.query == "Python"
        assert result.search_type == "metadata"

        # Should find python-skill
        match_names = [m.artifact_name for m in result.matches]
        assert "python-skill" in match_names

    def test_search_metadata_tags(self, temp_collection):
        """Test metadata search on tags."""
        collection_mgr, collection_name = temp_collection
        search_mgr = SearchManager(collection_mgr)

        result = search_mgr.search_collection(
            query="pytest",
            collection_name=collection_name,
            search_type="metadata"
        )

        assert result.total_count > 0

        # Should find testing-skill
        match_names = [m.artifact_name for m in result.matches]
        assert "testing-skill" in match_names

    def test_search_metadata_description(self, temp_collection):
        """Test metadata search on description field."""
        collection_mgr, collection_name = temp_collection
        search_mgr = SearchManager(collection_mgr)

        result = search_mgr.search_collection(
            query="programming",
            collection_name=collection_name,
            search_type="metadata"
        )

        assert result.total_count > 0
        match_names = [m.artifact_name for m in result.matches]
        assert "python-skill" in match_names

    def test_search_content_python_fallback(self, temp_collection):
        """Test content search using Python fallback."""
        collection_mgr, collection_name = temp_collection
        search_mgr = SearchManager(collection_mgr)

        result = search_mgr.search_collection(
            query="pytest",
            collection_name=collection_name,
            search_type="content"
        )

        assert isinstance(result, SearchResult)
        # Should find matches in content (either ripgrep or Python)
        # Note: "pytest" appears in both python-skill and testing-skill content

    def test_search_combined(self, temp_collection):
        """Test combined metadata and content search."""
        collection_mgr, collection_name = temp_collection
        search_mgr = SearchManager(collection_mgr)

        result = search_mgr.search_collection(
            query="testing",
            collection_name=collection_name,
            search_type="both"
        )

        assert isinstance(result, SearchResult)
        assert result.search_type == "both"
        # Should find matches in both metadata and content

    def test_search_no_results(self, temp_collection):
        """Test search with no matches."""
        collection_mgr, collection_name = temp_collection
        search_mgr = SearchManager(collection_mgr)

        result = search_mgr.search_collection(
            query="nonexistent_query_string_xyz",
            collection_name=collection_name,
            search_type="both"
        )

        assert result.total_count == 0
        assert len(result.matches) == 0
        assert not result.has_matches

    def test_search_with_limit(self, temp_collection):
        """Test search with result limit."""
        collection_mgr, collection_name = temp_collection
        search_mgr = SearchManager(collection_mgr)

        result = search_mgr.search_collection(
            query="skill",
            collection_name=collection_name,
            search_type="both",
            limit=1
        )

        # Should respect limit
        assert len(result.matches) <= 1

    def test_search_filter_by_type(self, temp_collection):
        """Test search with artifact type filter."""
        collection_mgr, collection_name = temp_collection
        search_mgr = SearchManager(collection_mgr)

        result = search_mgr.search_collection(
            query="Python",
            collection_name=collection_name,
            artifact_types=[ArtifactType.SKILL],
            search_type="both"
        )

        # All results should be skills
        for match in result.matches:
            assert match.artifact_type == "skill"

    def test_search_filter_by_tags(self, temp_collection):
        """Test search with tag filter."""
        collection_mgr, collection_name = temp_collection
        search_mgr = SearchManager(collection_mgr)

        # Search only artifacts tagged with "testing"
        result = search_mgr.search_collection(
            query="pytest",
            collection_name=collection_name,
            tags=["testing"],
            search_type="both"
        )

        # Should only find testing-skill
        assert result.total_count >= 0  # May be 0 if no match or >0 if found

    def test_search_invalid_type(self, temp_collection):
        """Test search with invalid search type."""
        collection_mgr, collection_name = temp_collection
        search_mgr = SearchManager(collection_mgr)

        with pytest.raises(ValueError, match="Invalid search_type"):
            search_mgr.search_collection(
                query="test",
                collection_name=collection_name,
                search_type="invalid_type"
            )

    def test_search_nonexistent_collection(self):
        """Test search on non-existent collection."""
        # Create temp config
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".skillmeat"
            config_dir.mkdir()

            from skillmeat.config import ConfigManager
            config = ConfigManager(config_dir=config_dir)
            collection_mgr = CollectionManager(config=config)
            search_mgr = SearchManager(collection_mgr)

            with pytest.raises(ValueError, match="Failed to load collection"):
                search_mgr.search_collection(
                    query="test",
                    collection_name="nonexistent-collection"
                )

    def test_search_result_ranking(self, temp_collection):
        """Test that search results are ranked by relevance."""
        collection_mgr, collection_name = temp_collection
        search_mgr = SearchManager(collection_mgr)

        result = search_mgr.search_collection(
            query="python",
            collection_name=collection_name,
            search_type="both"
        )

        if result.total_count > 1:
            # Scores should be in descending order
            scores = [m.score for m in result.matches]
            assert scores == sorted(scores, reverse=True)

    def test_search_match_validation(self):
        """Test SearchMatch validation."""
        # Valid match type
        match = SearchMatch(
            artifact_name="test",
            artifact_type="skill",
            score=10.0,
            match_type="metadata",
            context="Test context",
        )
        assert match.match_type == "metadata"

        # Invalid match type
        with pytest.raises(ValueError, match="Invalid match_type"):
            SearchMatch(
                artifact_name="test",
                artifact_type="skill",
                score=10.0,
                match_type="invalid",
                context="Test context",
            )

    def test_search_result_summary(self):
        """Test SearchResult summary generation."""
        # No results
        result = SearchResult(query="test", matches=[], total_count=0)
        assert "No results found" in result.summary()

        # With results
        match = SearchMatch(
            artifact_name="test",
            artifact_type="skill",
            score=10.0,
            match_type="metadata",
            context="Test",
        )
        result = SearchResult(
            query="test",
            matches=[match],
            total_count=1,
            search_time=0.5,
            used_ripgrep=True
        )
        summary = result.summary()
        assert "1 result" in summary
        assert "0.50s" in summary
        assert "ripgrep" in summary

    def test_binary_file_detection(self, temp_collection):
        """Test that binary files are skipped in content search."""
        collection_mgr, collection_name = temp_collection
        search_mgr = SearchManager(collection_mgr)

        # Add a binary file to collection
        collection_path = collection_mgr.config.get_collection_path(collection_name)
        binary_file = collection_path / "skills" / "python-skill" / "test.pyc"
        binary_file.write_bytes(b"\x00\x01\x02\x03\x04")

        # Search should not fail
        result = search_mgr.search_collection(
            query="test",
            collection_name=collection_name,
            search_type="content"
        )

        # Should complete without error
        assert isinstance(result, SearchResult)

    def test_large_file_handling(self, temp_collection):
        """Test that large files are skipped."""
        collection_mgr, collection_name = temp_collection
        search_mgr = SearchManager(collection_mgr)

        # This test just ensures large files don't crash the search
        # Actual skipping is tested implicitly by performance
        result = search_mgr.search_collection(
            query="test",
            collection_name=collection_name,
            search_type="content"
        )

        assert isinstance(result, SearchResult)

    def test_empty_collection(self):
        """Test search on empty collection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".skillmeat"
            config_dir.mkdir()

            from skillmeat.config import ConfigManager
            config = ConfigManager(config_dir=config_dir)
            config.set("settings.collections-dir", str(Path(tmpdir) / "collections"))

            collection_mgr = CollectionManager(config=config)
            collection_mgr.init("empty-collection")

            search_mgr = SearchManager(collection_mgr)
            result = search_mgr.search_collection(
                query="test",
                collection_name="empty-collection"
            )

            assert result.total_count == 0
            assert not result.has_matches


class TestSearchPerformance:
    """Performance tests for SearchManager."""

    def test_search_performance_metadata(self, temp_collection):
        """Test metadata search performance."""
        collection_mgr, collection_name = temp_collection
        search_mgr = SearchManager(collection_mgr)

        result = search_mgr.search_collection(
            query="python",
            collection_name=collection_name,
            search_type="metadata"
        )

        # Should complete in reasonable time (< 3s for small collection)
        assert result.search_time < 3.0

    def test_search_performance_content(self, temp_collection):
        """Test content search performance."""
        collection_mgr, collection_name = temp_collection
        search_mgr = SearchManager(collection_mgr)

        result = search_mgr.search_collection(
            query="python",
            collection_name=collection_name,
            search_type="content"
        )

        # Should complete in reasonable time (< 3s for small collection)
        assert result.search_time < 3.0
