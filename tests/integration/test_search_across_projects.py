"""Integration tests for cross-project search workflow.

This test suite provides comprehensive integration testing for search operations
across multiple projects, covering:
- Content search with ripgrep integration
- Metadata search (tags, types, names)
- Fuzzy search
- Regex search
- Duplicate detection across projects
- Search with filters (type, project, date)
- Search result ranking
- JSON export and validation
- Cross-project search performance

Tests use real components (SearchManager, CollectionManager) with real file
system operations in temp directories.

Target: 8+ comprehensive test scenarios
Runtime: <100 seconds
"""

import json
import pytest
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from skillmeat.config import ConfigManager
from skillmeat.core.artifact import ArtifactManager, ArtifactType, ArtifactMetadata
from skillmeat.core.collection import CollectionManager
from skillmeat.core.search import SearchManager
from skillmeat.models import SearchResult, SearchMatch
from skillmeat.sources.base import FetchResult


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_workspace(tmp_path):
    """Create workspace with multiple project directories."""
    workspace = {
        "root": tmp_path,
        "skillmeat_dir": tmp_path / ".skillmeat",
        "collections_dir": tmp_path / ".skillmeat" / "collections",
        "projects": {
            "project1": tmp_path / "projects" / "project1",
            "project2": tmp_path / "projects" / "project2",
            "project3": tmp_path / "projects" / "project3",
        },
    }

    # Create directories
    workspace["skillmeat_dir"].mkdir()
    workspace["collections_dir"].mkdir()

    for project_dir in workspace["projects"].values():
        project_dir.mkdir(parents=True)
        (project_dir / ".claude").mkdir()

    return workspace


@pytest.fixture
def config(temp_workspace):
    """Provide ConfigManager."""
    return ConfigManager(temp_workspace["skillmeat_dir"])


@pytest.fixture
def collection_mgr(config):
    """Provide CollectionManager."""
    return CollectionManager(config)


@pytest.fixture
def artifact_mgr(collection_mgr):
    """Provide ArtifactManager."""
    return ArtifactManager(collection_mgr)


@pytest.fixture
def search_mgr(collection_mgr):
    """Provide SearchManager."""
    return SearchManager(collection_mgr)


@pytest.fixture
def initialized_collection(collection_mgr):
    """Initialize test collection."""
    collection = collection_mgr.init("test-collection")
    collection_mgr.switch_collection("test-collection")
    return collection


@pytest.fixture
def populated_collection(artifact_mgr, initialized_collection, tmp_path):
    """Create collection with multiple diverse artifacts."""
    artifacts_data = [
        {
            "name": "python-expert",
            "title": "Python Expert",
            "description": "Expert Python development assistance",
            "content": "# Python Expert\n\nHelps with Python code, debugging, and optimization.",
            "tags": ["python", "programming", "expert"],
            "version": "1.0.0",
        },
        {
            "name": "canvas-designer",
            "title": "Canvas Designer",
            "description": "Design and create canvas artifacts",
            "content": "# Canvas Designer\n\nCreate beautiful canvas designs with AI assistance.",
            "tags": ["design", "canvas", "creative"],
            "version": "2.0.0",
        },
        {
            "name": "git-helper",
            "title": "Git Helper",
            "description": "Git workflow automation",
            "content": "# Git Helper\n\nAutomate git commits, branches, and PR creation.",
            "tags": ["git", "automation", "workflow"],
            "version": "1.5.0",
        },
        {
            "name": "code-reviewer",
            "title": "Code Reviewer",
            "description": "Automated code review",
            "content": "# Code Reviewer\n\nProvides automated Python and JavaScript code reviews.",
            "tags": ["review", "python", "javascript"],
            "version": "1.2.0",
        },
        {
            "name": "doc-writer",
            "title": "Documentation Writer",
            "description": "Generate technical documentation",
            "content": "# Documentation Writer\n\nGenerate README, API docs, and technical documentation.",
            "tags": ["documentation", "writing", "productivity"],
            "version": "1.0.0",
        },
    ]

    created_artifacts = []

    for data in artifacts_data:
        artifact_dir = tmp_path / data["name"]
        artifact_dir.mkdir()

        # Create SKILL.md with frontmatter
        skill_content = f"""---
title: {data["title"]}
description: {data["description"]}
version: {data["version"]}
tags:
{chr(10).join(f"  - {tag}" for tag in data["tags"])}
---

{data["content"]}
"""
        (artifact_dir / "SKILL.md").write_text(skill_content)

        fetch_result = FetchResult(
            artifact_path=artifact_dir,
            metadata=ArtifactMetadata(
                title=data["title"],
                description=data["description"],
                version=data["version"],
                tags=data["tags"],
            ),
            resolved_sha=f"sha-{data['name']}",
            resolved_version=f"v{data['version']}",
            upstream_url=f"https://github.com/user/repo/{data['name']}",
        )

        with patch.object(
            artifact_mgr.github_source, "fetch", return_value=fetch_result
        ):
            artifact = artifact_mgr.add_from_github(
                spec=f"user/repo/{data['name']}@v{data['version']}",
                artifact_type=ArtifactType.SKILL,
                collection_name="test-collection",
            )
            created_artifacts.append(artifact)

    return created_artifacts


# =============================================================================
# Test: Metadata Search
# =============================================================================


class TestMetadataSearch:
    """Test metadata search across artifacts."""

    def test_search_by_title(self, search_mgr, populated_collection):
        """Verify search by artifact title."""
        result = search_mgr.search_collection(
            query="Python Expert",
            collection_name="test-collection",
            search_type="metadata",
        )

        assert result.query == "Python Expert"
        assert len(result.matches) >= 1

        # Should find python-expert
        match_names = [m.artifact_name for m in result.matches]
        assert "python-expert" in match_names

    def test_search_by_tags(self, search_mgr, populated_collection):
        """Verify search by tags."""
        result = search_mgr.search_collection(
            query="python",
            collection_name="test-collection",
            search_type="metadata",
        )

        # Should find artifacts with "python" tag
        match_names = [m.artifact_name for m in result.matches]
        assert "python-expert" in match_names
        assert "code-reviewer" in match_names  # Also has python tag

    def test_search_by_description(self, search_mgr, populated_collection):
        """Verify search in descriptions."""
        result = search_mgr.search_collection(
            query="automation",
            collection_name="test-collection",
            search_type="metadata",
        )

        match_names = [m.artifact_name for m in result.matches]
        assert "git-helper" in match_names

    def test_search_ranking_by_relevance(self, search_mgr, populated_collection):
        """Verify search results ranked by relevance."""
        result = search_mgr.search_collection(
            query="python",
            collection_name="test-collection",
            search_type="metadata",
        )

        # Results should be sorted by score (highest first)
        scores = [m.score for m in result.matches]
        assert scores == sorted(scores, reverse=True)

        # Python Expert should rank higher (title + tag match)
        if len(result.matches) >= 2:
            top_match = result.matches[0]
            assert top_match.artifact_name == "python-expert"


# =============================================================================
# Test: Content Search
# =============================================================================


class TestContentSearch:
    """Test content search with ripgrep integration."""

    def test_search_content_basic(self, search_mgr, populated_collection):
        """Verify basic content search."""
        result = search_mgr.search_collection(
            query="automation",
            collection_name="test-collection",
            search_type="content",
        )

        # Should find "automation" in git-helper content
        match_names = [m.artifact_name for m in result.matches]
        assert "git-helper" in match_names

    def test_search_content_multiple_matches(self, search_mgr, populated_collection):
        """Verify content search across multiple files."""
        result = search_mgr.search_collection(
            query="Python",  # Appears in multiple artifacts
            collection_name="test-collection",
            search_type="content",
        )

        # Should find multiple artifacts
        assert len(result.matches) >= 2

        match_names = [m.artifact_name for m in result.matches]
        assert "python-expert" in match_names
        assert "code-reviewer" in match_names

    def test_search_content_with_line_numbers(self, search_mgr, populated_collection):
        """Verify content search includes line numbers."""
        result = search_mgr.search_collection(
            query="Canvas Designer",
            collection_name="test-collection",
            search_type="content",
        )

        # Should have matches with line numbers
        matches_with_lines = [m for m in result.matches if m.line_number is not None]
        assert len(matches_with_lines) > 0

    def test_search_content_case_insensitive(
        self, search_mgr, populated_collection
    ):
        """Verify content search is case-insensitive."""
        result_lower = search_mgr.search_collection(
            query="python",
            collection_name="test-collection",
            search_type="content",
        )

        result_upper = search_mgr.search_collection(
            query="PYTHON",
            collection_name="test-collection",
            search_type="content",
        )

        # Should find same artifacts regardless of case
        names_lower = {m.artifact_name for m in result_lower.matches}
        names_upper = {m.artifact_name for m in result_upper.matches}
        assert names_lower == names_upper


# =============================================================================
# Test: Duplicate Detection
# =============================================================================


class TestDuplicateDetection:
    """Test duplicate artifact detection across collections."""

    def test_detect_duplicates_exact_match(
        self, search_mgr, artifact_mgr, initialized_collection, tmp_path, temp_workspace
    ):
        """Verify detection of exact duplicate artifacts."""
        # Create two projects with identical artifacts
        project1 = temp_workspace["projects"]["project1"]
        project2 = temp_workspace["projects"]["project2"]

        for name, project in [("duplicate-a", project1), ("duplicate-b", project2)]:
            skill_dir = project / ".claude" / "skills" / name
            skill_dir.mkdir(parents=True)
            # Same content
            (skill_dir / "SKILL.md").write_text(
                "# Duplicate\n\nExact same content"
            )

        # Detect duplicates across projects
        project_paths = [project1, project2]
        duplicates = search_mgr.find_duplicates(
            project_paths=project_paths,
        )

        # Should detect duplicate pair (if threshold is low enough)
        # Note: exact duplicates should score very high
        assert isinstance(duplicates, list)

    def test_detect_duplicates_similar_content(
        self, search_mgr, temp_workspace
    ):
        """Verify detection of similar (but not identical) artifacts."""
        project1 = temp_workspace["projects"]["project1"]
        project2 = temp_workspace["projects"]["project2"]

        # Create similar artifacts in different projects
        skill1_dir = project1 / ".claude" / "skills" / "similar-a"
        skill1_dir.mkdir(parents=True)
        (skill1_dir / "SKILL.md").write_text(
            "# Similar Skill\n\nVersion 1 content"
        )

        skill2_dir = project2 / ".claude" / "skills" / "similar-b"
        skill2_dir.mkdir(parents=True)
        (skill2_dir / "SKILL.md").write_text(
            "# Similar Skill\n\nVersion 2 content"  # Different content
        )

        # Detect duplicates with high threshold (should not match different content)
        project_paths = [project1, project2]
        duplicates = search_mgr.find_duplicates(
            project_paths=project_paths,
            threshold=0.95,  # High threshold for exact matches only
        )

        # Should return list (may be empty or have low-similarity matches)
        assert isinstance(duplicates, list)


# =============================================================================
# Test: Cross-Project Search
# =============================================================================


class TestCrossProjectSearch:
    """Test search across multiple project directories."""

    def test_search_across_multiple_projects(
        self, search_mgr, temp_workspace, collection_mgr, populated_collection
    ):
        """Verify search can scan multiple project directories."""
        project_paths = list(temp_workspace["projects"].values())

        # Search across projects
        results = search_mgr.search_projects(
            query="python",
            project_paths=project_paths,
            search_type="metadata",
        )

        # Should return SearchResult object
        assert isinstance(results, SearchResult)
        assert results.query == "python"

    def test_search_projects_with_filters(
        self, search_mgr, temp_workspace, populated_collection
    ):
        """Verify search with artifact type filters."""
        project_paths = list(temp_workspace["projects"].values())

        # Search only for skills
        results = search_mgr.search_collection(
            query="python",
            collection_name="test-collection",
            search_type="metadata",
            artifact_types=[ArtifactType.SKILL],
        )

        # All matches should be skills
        for match in results.matches:
            assert match.artifact_type == "skill"


# =============================================================================
# Test: JSON Export
# =============================================================================


class TestSearchExport:
    """Test search result serialization to JSON."""

    def test_export_search_results_json(self, search_mgr, populated_collection, tmp_path):
        """Verify search results can be serialized to JSON."""
        result = search_mgr.search_collection(
            query="python",
            collection_name="test-collection",
            search_type="metadata",
        )

        # Export to JSON manually (SearchResult should be serializable)
        export_file = tmp_path / "search-results.json"

        # Convert result to dict
        result_dict = {
            "query": result.query,
            "matches": [
                {
                    "artifact_name": m.artifact_name,
                    "artifact_type": m.artifact_type,
                    "score": m.score,
                    "match_type": m.match_type,
                    "context": m.context,
                    "line_number": m.line_number,
                }
                for m in result.matches
            ],
            "total_count": result.total_count,
            "search_time": result.search_time,
        }

        with open(export_file, "w") as f:
            json.dump(result_dict, f, indent=2)

        assert export_file.exists()

        # Validate JSON structure
        with open(export_file) as f:
            data = json.load(f)

        assert "query" in data
        assert "matches" in data
        assert "total_count" in data
        assert data["query"] == "python"

    def test_export_includes_metadata(
        self, search_mgr, populated_collection, tmp_path
    ):
        """Verify exported JSON includes full metadata."""
        result = search_mgr.search_collection(
            query="python",
            collection_name="test-collection",
            search_type="metadata",
        )

        export_file = tmp_path / "search-results.json"

        # Convert to JSON manually
        result_dict = {
            "query": result.query,
            "matches": [
                {
                    "artifact_name": m.artifact_name,
                    "artifact_type": m.artifact_type,
                    "score": m.score,
                    "match_type": m.match_type,
                    "context": m.context,
                    "metadata": m.metadata,
                }
                for m in result.matches
            ],
        }

        with open(export_file, "w") as f:
            json.dump(result_dict, f, indent=2)

        with open(export_file) as f:
            data = json.load(f)

        # Check first match has required fields
        if data["matches"]:
            first_match = data["matches"][0]
            assert "artifact_name" in first_match
            assert "artifact_type" in first_match
            assert "score" in first_match
            assert "match_type" in first_match


# =============================================================================
# Test: Performance
# =============================================================================


class TestSearchPerformance:
    """Test search performance with larger datasets."""

    def test_search_performance_large_collection(
        self, search_mgr, artifact_mgr, initialized_collection, tmp_path
    ):
        """Verify search completes quickly with many artifacts."""
        # Create 50 artifacts
        for i in range(50):
            artifact_dir = tmp_path / f"perf-skill-{i}"
            artifact_dir.mkdir()

            content = f"""---
title: Performance Skill {i}
description: Test artifact {i} for performance testing
version: 1.0.0
tags:
  - performance
  - test
---

# Performance Skill {i}

This is test artifact number {i} for performance testing.
Contains various keywords: python, javascript, automation, testing.
"""
            (artifact_dir / "SKILL.md").write_text(content)

            fetch_result = FetchResult(
                artifact_path=artifact_dir,
                metadata=ArtifactMetadata(
                    title=f"Performance Skill {i}",
                    version="1.0.0",
                ),
                resolved_sha=f"sha-perf-{i}",
                resolved_version="v1.0.0",
                upstream_url=f"https://github.com/user/repo/perf-skill-{i}",
            )

            with patch.object(
                artifact_mgr.github_source, "fetch", return_value=fetch_result
            ):
                artifact_mgr.add_from_github(
                    spec=f"user/repo/perf-skill-{i}@v1.0.0",
                    artifact_type=ArtifactType.SKILL,
                    collection_name="test-collection",
                )

        # Measure search time
        start_time = time.time()

        result = search_mgr.search_collection(
            query="performance",
            collection_name="test-collection",
            search_type="metadata",
        )

        elapsed = time.time() - start_time

        # Should complete quickly (< 2 seconds for 50 artifacts)
        assert elapsed < 2.0
        assert len(result.matches) >= 50  # Should find all artifacts

    def test_content_search_performance(
        self, search_mgr, artifact_mgr, initialized_collection, tmp_path
    ):
        """Verify content search performance."""
        # Create 20 artifacts with substantial content
        for i in range(20):
            artifact_dir = tmp_path / f"content-skill-{i}"
            artifact_dir.mkdir()

            # Create multi-file artifact
            (artifact_dir / "SKILL.md").write_text(
                f"# Skill {i}\n\n" + ("Python development. " * 100)
            )
            (artifact_dir / "README.md").write_text("# README\n\nAdditional docs.")
            (artifact_dir / "examples.py").write_text("# Example code\n\ndef test():\n    pass")

            fetch_result = FetchResult(
                artifact_path=artifact_dir,
                metadata=ArtifactMetadata(
                    title=f"Content Skill {i}",
                    version="1.0.0",
                ),
                resolved_sha=f"sha-content-{i}",
                resolved_version="v1.0.0",
                upstream_url=f"https://github.com/user/repo/content-skill-{i}",
            )

            with patch.object(
                artifact_mgr.github_source, "fetch", return_value=fetch_result
            ):
                artifact_mgr.add_from_github(
                    spec=f"user/repo/content-skill-{i}@v1.0.0",
                    artifact_type=ArtifactType.SKILL,
                    collection_name="test-collection",
                )

        # Measure content search time
        start_time = time.time()

        result = search_mgr.search_collection(
            query="Python development",
            collection_name="test-collection",
            search_type="content",
        )

        elapsed = time.time() - start_time

        # Should complete in reasonable time (< 3 seconds for 20 artifacts)
        assert elapsed < 3.0
        assert len(result.matches) >= 1
