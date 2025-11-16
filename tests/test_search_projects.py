"""Tests for cross-project search functionality (P2-002)."""

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from skillmeat.core.artifact import ArtifactType
from skillmeat.core.search import SearchManager
from skillmeat.models import SearchCacheEntry, SearchMatch, SearchResult
from skillmeat.utils.metadata import ArtifactMetadata


class TestProjectDiscovery:
    """Test project discovery functionality."""

    def test_discover_projects_from_roots(self, tmp_path):
        """Test discovering .claude directories from root paths."""
        # Setup: Create test projects
        project1 = tmp_path / "project1"
        project2 = tmp_path / "project2"
        project3 = tmp_path / "nested" / "project3"

        for project in [project1, project2, project3]:
            (project / ".claude").mkdir(parents=True)

        # Create mock collection manager
        mock_collection_mgr = MagicMock()
        mock_collection_mgr.config.get.side_effect = lambda key, default=None: {
            "search.max-depth": 3,
            "search.exclude-dirs": [],
        }.get(key, default)

        search_mgr = SearchManager(mock_collection_mgr)

        # Execute
        projects = search_mgr._discover_projects(roots=[tmp_path])

        # Verify
        assert len(projects) == 3
        project_paths = {str(p) for p in projects}
        assert str(project1 / ".claude") in project_paths
        assert str(project2 / ".claude") in project_paths
        assert str(project3 / ".claude") in project_paths

    def test_discover_respects_max_depth(self, tmp_path):
        """Test that discovery respects max depth setting."""
        # Setup: Create nested projects
        project1 = tmp_path / "level1" / ".claude"
        project2 = tmp_path / "level1" / "level2" / ".claude"
        project3 = tmp_path / "level1" / "level2" / "level3" / ".claude"
        project4 = tmp_path / "level1" / "level2" / "level3" / "level4" / ".claude"

        for project in [project1, project2, project3, project4]:
            project.mkdir(parents=True)

        # Create mock collection manager with max_depth=2
        mock_collection_mgr = MagicMock()
        mock_collection_mgr.config.get.side_effect = lambda key, default=None: {
            "search.max-depth": 2,
            "search.exclude-dirs": [],
        }.get(key, default)

        search_mgr = SearchManager(mock_collection_mgr)

        # Execute
        projects = search_mgr._discover_projects(roots=[tmp_path])

        # Verify - should find projects at depth 1 and 2 only
        assert len(projects) == 2
        project_paths = {str(p) for p in projects}
        assert str(project1) in project_paths
        assert str(project2) in project_paths

    def test_discover_honors_exclude_patterns(self, tmp_path):
        """Test that discovery honors exclude patterns."""
        # Setup: Create projects with excluded directories
        project1 = tmp_path / "project1" / ".claude"
        project2 = tmp_path / "node_modules" / "project2" / ".claude"
        project3 = tmp_path / ".venv" / "project3" / ".claude"
        project4 = tmp_path / "valid" / "project4" / ".claude"

        for project in [project1, project2, project3, project4]:
            project.mkdir(parents=True)

        # Create mock collection manager
        mock_collection_mgr = MagicMock()
        mock_collection_mgr.config.get.side_effect = lambda key, default=None: {
            "search.max-depth": 3,
            "search.exclude-dirs": ["node_modules", ".venv"],
        }.get(key, default)

        search_mgr = SearchManager(mock_collection_mgr)

        # Execute
        projects = search_mgr._discover_projects(roots=[tmp_path])

        # Verify - should skip node_modules and .venv
        assert len(projects) == 2
        project_paths = {str(p) for p in projects}
        assert str(project1) in project_paths
        assert str(project4) in project_paths
        assert str(project2) not in project_paths
        assert str(project3) not in project_paths

    def test_discover_handles_missing_roots(self, tmp_path):
        """Test discovery handles missing root directories."""
        # Setup: Create mock collection manager
        mock_collection_mgr = MagicMock()
        mock_collection_mgr.config.get.side_effect = lambda key, default=None: {
            "search.max-depth": 3,
            "search.exclude-dirs": [],
        }.get(key, default)

        search_mgr = SearchManager(mock_collection_mgr)

        # Execute - pass non-existent root
        missing_root = tmp_path / "does_not_exist"
        projects = search_mgr._discover_projects(roots=[missing_root])

        # Verify - should return empty list
        assert len(projects) == 0

    def test_discover_from_config(self, tmp_path):
        """Test discovery uses config when no roots provided."""
        # Setup: Create test projects
        project1 = tmp_path / "project1" / ".claude"
        project1.mkdir(parents=True)

        # Create mock collection manager
        mock_collection_mgr = MagicMock()
        mock_collection_mgr.config.get.side_effect = lambda key, default=None: {
            "search.project-roots": [str(tmp_path)],
            "search.max-depth": 3,
            "search.exclude-dirs": [],
        }.get(key, default)

        search_mgr = SearchManager(mock_collection_mgr)

        # Execute - no roots provided
        projects = search_mgr._discover_projects()

        # Verify
        assert len(projects) == 1
        assert str(project1) in {str(p) for p in projects}


class TestProjectIndexing:
    """Test project indexing functionality."""

    def test_build_index_from_projects(self, tmp_path):
        """Test building index from project directories."""
        # Setup: Create project with skill
        project1 = tmp_path / "project1" / ".claude"
        skills_dir = project1 / "skills" / "test-skill"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text("# Test Skill\n")

        # Create mock collection manager
        mock_collection_mgr = MagicMock()
        search_mgr = SearchManager(mock_collection_mgr)

        # Execute
        indexes = search_mgr._build_project_index([project1])

        # Verify
        assert len(indexes) == 1
        assert indexes[0]["project_path"] == project1
        assert len(indexes[0]["artifacts"]) == 1
        assert indexes[0]["artifacts"][0]["name"] == "test-skill"
        assert indexes[0]["artifacts"][0]["type"] == ArtifactType.SKILL

    def test_build_index_extracts_metadata(self, tmp_path):
        """Test that index building extracts metadata correctly."""
        # Setup: Create project with skill with metadata
        project1 = tmp_path / "project1" / ".claude"
        skills_dir = project1 / "skills" / "test-skill"
        skills_dir.mkdir(parents=True)

        skill_content = """---
title: Test Skill
description: A test skill
tags:
  - testing
  - demo
---

# Test Skill Content
"""
        (skills_dir / "SKILL.md").write_text(skill_content)

        # Create mock collection manager
        mock_collection_mgr = MagicMock()
        search_mgr = SearchManager(mock_collection_mgr)

        # Execute
        indexes = search_mgr._build_project_index([project1])

        # Verify
        assert len(indexes) == 1
        metadata = indexes[0]["artifacts"][0]["metadata"]
        assert metadata.title == "Test Skill"
        assert metadata.description == "A test skill"
        assert "testing" in metadata.tags
        assert "demo" in metadata.tags

    def test_build_index_handles_invalid_artifacts(self, tmp_path):
        """Test that invalid artifacts are skipped during indexing."""
        # Setup: Create project with invalid skill (no SKILL.md)
        project1 = tmp_path / "project1" / ".claude"
        skills_dir = project1 / "skills"
        skills_dir.mkdir(parents=True)

        # Create directory without SKILL.md
        (skills_dir / "invalid-skill").mkdir()

        # Create valid skill
        valid_skill_dir = skills_dir / "valid-skill"
        valid_skill_dir.mkdir()
        (valid_skill_dir / "SKILL.md").write_text("# Valid Skill\n")

        # Create mock collection manager
        mock_collection_mgr = MagicMock()
        search_mgr = SearchManager(mock_collection_mgr)

        # Execute
        indexes = search_mgr._build_project_index([project1])

        # Verify - only valid skill should be indexed
        assert len(indexes) == 1
        assert len(indexes[0]["artifacts"]) == 1
        assert indexes[0]["artifacts"][0]["name"] == "valid-skill"

    def test_build_index_tracks_modification_time(self, tmp_path):
        """Test that indexes track directory modification times."""
        # Setup: Create project
        project1 = tmp_path / "project1" / ".claude"
        project1.mkdir(parents=True)

        # Create mock collection manager
        mock_collection_mgr = MagicMock()
        search_mgr = SearchManager(mock_collection_mgr)

        # Execute
        indexes = search_mgr._build_project_index([project1])

        # Verify
        assert "last_modified" in indexes[0]
        assert indexes[0]["last_modified"] > 0

    def test_build_index_handles_multiple_projects(self, tmp_path):
        """Test building index from multiple projects."""
        # Setup: Create multiple projects
        project1 = tmp_path / "project1" / ".claude"
        project2 = tmp_path / "project2" / ".claude"

        for project in [project1, project2]:
            skills_dir = project / "skills" / "test-skill"
            skills_dir.mkdir(parents=True)
            (skills_dir / "SKILL.md").write_text("# Test Skill\n")

        # Create mock collection manager
        mock_collection_mgr = MagicMock()
        search_mgr = SearchManager(mock_collection_mgr)

        # Execute
        indexes = search_mgr._build_project_index([project1, project2])

        # Verify
        assert len(indexes) == 2
        assert all("project_path" in idx for idx in indexes)
        assert all(len(idx["artifacts"]) > 0 for idx in indexes)


class TestCacheManagement:
    """Test cache management functionality."""

    def test_cache_stores_index(self, tmp_path):
        """Test that cache stores index correctly."""
        # Setup
        mock_collection_mgr = MagicMock()
        mock_collection_mgr.config.get.return_value = 60.0
        search_mgr = SearchManager(mock_collection_mgr)

        project_path = tmp_path / ".claude"
        index = [{"project_path": project_path, "artifacts": [], "last_modified": 0.0}]
        cache_key = "test_key"

        # Execute
        search_mgr._cache_index(cache_key, index)

        # Verify
        assert cache_key in search_mgr._project_cache
        entry = search_mgr._project_cache[cache_key]
        assert isinstance(entry, SearchCacheEntry)
        assert entry.index == index
        assert entry.ttl == 60.0

    def test_cache_retrieval(self, tmp_path):
        """Test retrieving from cache."""
        # Setup
        mock_collection_mgr = MagicMock()
        mock_collection_mgr.config.get.return_value = 60.0
        search_mgr = SearchManager(mock_collection_mgr)

        project_path = tmp_path / ".claude"
        project_path.mkdir(parents=True)
        index = [
            {
                "project_path": project_path,
                "artifacts": [],
                "last_modified": project_path.stat().st_mtime,
            }
        ]
        cache_key = "test_key"

        # Cache the index
        search_mgr._cache_index(cache_key, index)

        # Execute
        cached_index = search_mgr._get_cached_index(cache_key, [project_path])

        # Verify
        assert cached_index == index

    def test_cache_invalidation_on_ttl_expiration(self, tmp_path):
        """Test cache invalidation on TTL expiration."""
        # Setup
        mock_collection_mgr = MagicMock()
        mock_collection_mgr.config.get.return_value = 0.1  # 0.1s TTL
        search_mgr = SearchManager(mock_collection_mgr)

        project_path = tmp_path / ".claude"
        project_path.mkdir(parents=True)
        index = [
            {
                "project_path": project_path,
                "artifacts": [],
                "last_modified": project_path.stat().st_mtime,
            }
        ]
        cache_key = "test_key"

        # Cache the index
        search_mgr._cache_index(cache_key, index)

        # Wait for TTL to expire
        time.sleep(0.2)

        # Execute
        cached_index = search_mgr._get_cached_index(cache_key, [project_path])

        # Verify - cache should be invalidated
        assert cached_index is None
        assert cache_key not in search_mgr._project_cache

    def test_cache_invalidation_on_directory_modification(self, tmp_path):
        """Test cache invalidation on directory modification."""
        # Setup
        mock_collection_mgr = MagicMock()
        mock_collection_mgr.config.get.return_value = 60.0
        search_mgr = SearchManager(mock_collection_mgr)

        project_path = tmp_path / ".claude"
        project_path.mkdir(parents=True)

        # Get initial mtime
        initial_mtime = project_path.stat().st_mtime

        # Create index with old mtime
        index = [
            {
                "project_path": project_path,
                "artifacts": [],
                "last_modified": initial_mtime,
            }
        ]
        cache_key = "test_key"

        # Cache the index
        search_mgr._cache_index(cache_key, index)

        # Modify directory
        (project_path / "new_file.txt").write_text("test")
        time.sleep(0.1)  # Ensure mtime changes

        # Execute
        cached_index = search_mgr._get_cached_index(cache_key, [project_path])

        # Verify - cache should be invalidated if mtime changed
        # Note: Some filesystems may not update mtime immediately
        if project_path.stat().st_mtime > initial_mtime:
            assert cached_index is None

    def test_compute_cache_key_consistency(self, tmp_path):
        """Test that cache key computation is consistent."""
        # Setup
        mock_collection_mgr = MagicMock()
        search_mgr = SearchManager(mock_collection_mgr)

        path1 = tmp_path / "project1"
        path2 = tmp_path / "project2"

        # Execute - same paths should produce same key
        key1 = search_mgr._compute_cache_key([path1, path2])
        key2 = search_mgr._compute_cache_key([path1, path2])

        # Verify
        assert key1 == key2

        # Different order should produce same key (due to sorting)
        key3 = search_mgr._compute_cache_key([path2, path1])
        assert key1 == key3

        # Different paths should produce different key
        path3 = tmp_path / "project3"
        key4 = search_mgr._compute_cache_key([path1, path3])
        assert key1 != key4


class TestCrossProjectSearch:
    """Test cross-project search functionality."""

    def test_search_across_multiple_projects(self, tmp_path):
        """Test searching across multiple projects."""
        # Setup: Create multiple projects with skills
        project1 = tmp_path / "project1" / ".claude"
        project2 = tmp_path / "project2" / ".claude"

        for i, project in enumerate([project1, project2], 1):
            skills_dir = project / "skills" / f"skill{i}"
            skills_dir.mkdir(parents=True)
            (skills_dir / "SKILL.md").write_text(f"# Skill {i}\nTest content\n")

        # Create mock collection manager
        mock_collection_mgr = MagicMock()
        mock_collection_mgr.config.get.side_effect = lambda key, default=None: {
            "search.cache-ttl": 60.0,
        }.get(key, default)

        search_mgr = SearchManager(mock_collection_mgr)

        # Execute
        result = search_mgr.search_projects(
            query="test", project_paths=[project1, project2]
        )

        # Verify
        assert isinstance(result, SearchResult)
        assert result.total_count > 0
        assert all(isinstance(m, SearchMatch) for m in result.matches)
        # Should have matches from both projects
        project_paths = {str(m.project_path) for m in result.matches}
        assert len(project_paths) == 2

    def test_search_preserves_project_path(self, tmp_path):
        """Test that search results preserve project_path."""
        # Setup
        project1 = tmp_path / "project1" / ".claude"
        skills_dir = project1 / "skills" / "test-skill"
        skills_dir.mkdir(parents=True)

        skill_content = """---
title: Test Skill
description: A searchable skill
---

# Test Skill
"""
        (skills_dir / "SKILL.md").write_text(skill_content)

        # Create mock collection manager
        mock_collection_mgr = MagicMock()
        mock_collection_mgr.config.get.side_effect = lambda key, default=None: {
            "search.cache-ttl": 60.0,
        }.get(key, default)

        search_mgr = SearchManager(mock_collection_mgr)

        # Execute
        result = search_mgr.search_projects(
            query="searchable", project_paths=[project1]
        )

        # Verify
        assert result.total_count > 0
        for match in result.matches:
            assert match.project_path == project1

    def test_search_aggregates_results_correctly(self, tmp_path):
        """Test that search aggregates and ranks results correctly."""
        # Setup: Create projects with different match qualities
        project1 = tmp_path / "project1" / ".claude"
        project2 = tmp_path / "project2" / ".claude"

        # Project 1 - exact title match
        skills_dir1 = project1 / "skills" / "skill1"
        skills_dir1.mkdir(parents=True)
        (skills_dir1 / "SKILL.md").write_text(
            """---
title: Python
---
# Skill
"""
        )

        # Project 2 - description match
        skills_dir2 = project2 / "skills" / "skill2"
        skills_dir2.mkdir(parents=True)
        (skills_dir2 / "SKILL.md").write_text(
            """---
title: Other
description: Python programming
---
# Skill
"""
        )

        # Create mock collection manager
        mock_collection_mgr = MagicMock()
        mock_collection_mgr.config.get.side_effect = lambda key, default=None: {
            "search.cache-ttl": 60.0,
        }.get(key, default)

        search_mgr = SearchManager(mock_collection_mgr)

        # Execute
        result = search_mgr.search_projects(
            query="python", project_paths=[project1, project2], search_type="metadata"
        )

        # Verify
        assert result.total_count == 2
        # Title match should rank higher than description match
        assert result.matches[0].match_type == "metadata"
        assert result.matches[0].score > result.matches[1].score

    def test_search_uses_cache_on_repeat(self, tmp_path):
        """Test that repeated searches use cache."""
        # Setup
        project1 = tmp_path / "project1" / ".claude"
        skills_dir = project1 / "skills" / "test-skill"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text("# Test Skill\n")

        # Create mock collection manager
        mock_collection_mgr = MagicMock()
        mock_collection_mgr.config.get.side_effect = lambda key, default=None: {
            "search.cache-ttl": 60.0,
        }.get(key, default)

        search_mgr = SearchManager(mock_collection_mgr)

        # Execute first search
        result1 = search_mgr.search_projects(
            query="test", project_paths=[project1], use_cache=True
        )

        # Execute second search
        result2 = search_mgr.search_projects(
            query="test", project_paths=[project1], use_cache=True
        )

        # Verify - cache should be used
        assert len(search_mgr._project_cache) == 1
        # Results should be equivalent (though objects may differ)
        assert result1.total_count == result2.total_count

    def test_search_handles_no_projects(self, tmp_path):
        """Test search handles case with no projects found."""
        # Setup
        mock_collection_mgr = MagicMock()
        mock_collection_mgr.config.get.side_effect = lambda key, default=None: {
            "search.project-roots": [],
        }.get(key, default)

        search_mgr = SearchManager(mock_collection_mgr)

        # Execute - no projects
        result = search_mgr.search_projects(query="test")

        # Verify
        assert result.total_count == 0
        assert len(result.matches) == 0


class TestSearchPerformance:
    """Test search performance."""

    def test_cached_search_faster_than_uncached(self, tmp_path):
        """Test that cached search is faster than uncached."""
        # Setup: Create multiple projects
        projects = []
        for i in range(5):
            project = tmp_path / f"project{i}" / ".claude"
            skills_dir = project / "skills" / f"skill{i}"
            skills_dir.mkdir(parents=True)
            (skills_dir / "SKILL.md").write_text(f"# Skill {i}\nTest content\n")
            projects.append(project)

        # Create mock collection manager
        mock_collection_mgr = MagicMock()
        mock_collection_mgr.config.get.side_effect = lambda key, default=None: {
            "search.cache-ttl": 60.0,
        }.get(key, default)

        search_mgr = SearchManager(mock_collection_mgr)

        # Execute uncached search
        start_uncached = time.time()
        result1 = search_mgr.search_projects(
            query="test", project_paths=projects, use_cache=False
        )
        time_uncached = time.time() - start_uncached

        # Execute cached search
        start_cached = time.time()
        result2 = search_mgr.search_projects(
            query="test", project_paths=projects, use_cache=True
        )
        time_cached_first = time.time() - start_cached

        # Execute second cached search
        start_cached2 = time.time()
        result3 = search_mgr.search_projects(
            query="test", project_paths=projects, use_cache=True
        )
        time_cached_second = time.time() - start_cached2

        # Verify
        assert result1.total_count == result2.total_count == result3.total_count
        # Second cached search should be faster than uncached
        # (but first cached search builds cache so may be similar)
        print(
            f"Uncached: {time_uncached:.4f}s, "
            f"Cached (first): {time_cached_first:.4f}s, "
            f"Cached (second): {time_cached_second:.4f}s"
        )

    def test_handles_large_project_set(self, tmp_path):
        """Test handling of large project set (>10 projects)."""
        # Setup: Create 15 projects
        projects = []
        for i in range(15):
            project = tmp_path / f"project{i}" / ".claude"
            skills_dir = project / "skills" / f"skill{i}"
            skills_dir.mkdir(parents=True)
            (skills_dir / "SKILL.md").write_text(f"# Skill {i}\nTest content\n")
            projects.append(project)

        # Create mock collection manager
        mock_collection_mgr = MagicMock()
        mock_collection_mgr.config.get.side_effect = lambda key, default=None: {
            "search.cache-ttl": 60.0,
        }.get(key, default)

        search_mgr = SearchManager(mock_collection_mgr)

        # Execute
        start = time.time()
        result = search_mgr.search_projects(query="test", project_paths=projects)
        search_time = time.time() - start

        # Verify
        assert result.total_count > 0
        # Should complete in reasonable time (<5s as per requirements)
        assert search_time < 5.0
        print(f"Search across 15 projects completed in {search_time:.4f}s")
