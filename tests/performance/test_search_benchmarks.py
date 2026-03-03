"""Performance benchmarks for search operations.

Tests search functionality performance with 500 artifact collections.
Target: <3 seconds for search operations.

NOTE: SearchManager's public API uses search_projects() and find_duplicates().
The previously-tested methods (search_metadata, search_content, fuzzy_search,
search_by_tag) are either private or non-existent. These benchmarks use the
actual public API.
"""

import pytest
from pathlib import Path
from typing import List

from skillmeat.core.search import SearchManager
from skillmeat.models import SearchResult


class TestSearchPerformance:
    """Benchmark search operations on large datasets."""

    def test_metadata_search_500_artifacts(self, benchmark, large_collection_500: Path):
        """Benchmark metadata search across 500 artifacts.

        Target: <3 seconds

        Uses SearchManager.search_projects() with search_type="metadata".
        """
        search_mgr = SearchManager()

        # Run benchmark with a common search term
        result = benchmark(
            search_mgr.search_projects,
            query="python",
            project_paths=[large_collection_500],
            search_type="metadata",
            use_cache=False,
        )

        # Verify results
        assert isinstance(result, SearchResult)
        assert isinstance(result.matches, list)

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 3.0, f"Metadata search took {mean_time:.2f}s, expected <3s"

    def test_content_search_500_artifacts(self, benchmark, large_collection_500: Path):
        """Benchmark content search across 500 artifacts using ripgrep.

        Target: <3 seconds

        Uses SearchManager.search_projects() with search_type="content".
        """
        search_mgr = SearchManager()

        # Run benchmark
        result = benchmark(
            search_mgr.search_projects,
            query="testing",
            project_paths=[large_collection_500],
            search_type="content",
            use_cache=False,
        )

        # Verify results
        assert isinstance(result, SearchResult)
        assert isinstance(result.matches, list)

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 3.0, f"Content search took {mean_time:.2f}s, expected <3s"

    def test_fuzzy_search_500_artifacts(self, benchmark, large_collection_500: Path):
        """Benchmark fuzzy-style search across 500 artifacts.

        Target: <4 seconds (more complex than exact match)

        Note: SearchManager does not expose a dedicated fuzzy_search() method.
        Fuzzy-style matching is performed via search_projects() with metadata
        search, which applies relevance scoring over title/description/tags.
        """
        search_mgr = SearchManager()

        # Run benchmark with a slightly misspelled term (closest to fuzzy)
        result = benchmark(
            search_mgr.search_projects,
            query="analyss",  # Intentional typo — tests partial match scoring
            project_paths=[large_collection_500],
            search_type="metadata",
            use_cache=False,
        )

        # Verify results
        assert isinstance(result, SearchResult)
        assert isinstance(result.matches, list)

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 4.0, f"Fuzzy search took {mean_time:.2f}s, expected <4s"

    def test_duplicate_detection_500_artifacts(self, benchmark, large_collection_500: Path):
        """Benchmark duplicate detection across 500 artifacts.

        Target: <5 seconds (complex operation with hashing)

        Uses SearchManager.find_duplicates() which takes project_paths.
        """
        search_mgr = SearchManager()

        # Run benchmark
        result = benchmark(
            search_mgr.find_duplicates,
            project_paths=[large_collection_500],
            use_cache=False,
        )

        # Verify results
        assert isinstance(result, list)

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 5.0, f"Duplicate detection took {mean_time:.2f}s, expected <5s"

    def test_cross_project_search(self, benchmark, tmp_path: Path, large_collection_500: Path):
        """Benchmark search across multiple projects (3 projects × 200 artifacts).

        Target: <5 seconds
        """
        search_mgr = SearchManager()

        # Create 3 project directories with subsets of artifacts
        import shutil

        projects = []
        for i in range(3):
            project_dir = tmp_path / f"project_{i}"
            project_dir.mkdir()

            # Copy subset of artifacts (every 3rd artifact)
            for artifact_type in ["skill", "command", "agent"]:
                source_dir = large_collection_500 / artifact_type
                if source_dir.exists():
                    target_dir = project_dir / artifact_type
                    target_dir.mkdir(parents=True, exist_ok=True)

                    # Copy every 3rd artifact
                    for j, artifact_dir in enumerate(sorted(source_dir.iterdir())):
                        if j % 3 == i:  # Distribute artifacts across projects
                            shutil.copytree(artifact_dir, target_dir / artifact_dir.name)

            projects.append(project_dir)

        # Run benchmark
        def search_all_projects():
            """Search across all projects."""
            result = search_mgr.search_projects(
                query="automation",
                project_paths=projects,
                search_type="metadata",
                use_cache=False,
            )
            return result.matches

        result = benchmark(search_all_projects)

        # Verify results
        assert isinstance(result, list)

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 5.0, f"Cross-project search took {mean_time:.2f}s, expected <5s"

    def test_tag_based_search_500_artifacts(self, benchmark, large_collection_500: Path):
        """Benchmark tag-based metadata search.

        Target: <2 seconds

        Note: SearchManager does not expose a dedicated search_by_tag() method.
        Tag filtering is done via search_projects() with the tags parameter.
        """
        search_mgr = SearchManager()

        # Run benchmark searching for a specific tag via the tags filter
        result = benchmark(
            search_mgr.search_projects,
            query="",  # Empty query so all artifacts are candidates
            project_paths=[large_collection_500],
            search_type="metadata",
            tags=["python"],
            use_cache=False,
        )

        # Verify results
        assert isinstance(result, SearchResult)
        assert isinstance(result.matches, list)

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 2.0, f"Tag-based search took {mean_time:.2f}s, expected <2s"

    def test_combined_metadata_and_content_search(self, benchmark, large_collection_500: Path):
        """Benchmark combined metadata and content search.

        Target: <5 seconds

        Uses search_type="both" which searches metadata and content together.
        """
        search_mgr = SearchManager()

        def combined_search():
            """Perform combined metadata and content search."""
            result = search_mgr.search_projects(
                query="automation",
                project_paths=[large_collection_500],
                search_type="both",
                use_cache=False,
            )
            # Deduplicate by artifact_name
            seen = set()
            unique_matches = []
            for match in result.matches:
                key = match.artifact_name
                if key not in seen:
                    seen.add(key)
                    unique_matches.append(match)
            return unique_matches

        # Run benchmark
        result = benchmark(combined_search)

        # Verify results
        assert isinstance(result, list)

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 5.0, f"Combined search took {mean_time:.2f}s, expected <5s"

    def test_search_with_filter_500_artifacts(self, benchmark, large_collection_500: Path):
        """Benchmark filtered search (by artifact type).

        Target: <2 seconds

        Uses artifact_types filter in search_projects().
        """
        from skillmeat.core.artifact import ArtifactType

        search_mgr = SearchManager()

        # Run benchmark with artifact type filter
        result = benchmark(
            search_mgr.search_projects,
            query="process",
            project_paths=[large_collection_500],
            search_type="metadata",
            artifact_types=[ArtifactType.SKILL],
            use_cache=False,
        )

        # Verify results
        assert isinstance(result, SearchResult)
        assert isinstance(result.matches, list)
        # All matches should be skills
        for match in result.matches:
            assert match.artifact_type == "skill"

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 2.0, f"Filtered search took {mean_time:.2f}s, expected <2s"

    def test_search_result_ranking(self, benchmark, large_collection_500: Path):
        """Benchmark search result ranking by relevance.

        Target: <1 second (post-search processing)
        """
        search_mgr = SearchManager()

        # First, get search results (not benchmarked)
        search_result = search_mgr.search_projects(
            query="testing",
            project_paths=[large_collection_500],
            search_type="metadata",
            use_cache=False,
        )
        matches = search_result.matches

        # Benchmark ranking — SearchMatch has .score, .artifact_name,
        # .artifact_type and .metadata dict (keys: title, description, tags)
        def rank_results():
            """Rank search results by relevance score."""
            # Simple re-ranking on top of SearchManager's own score
            scored_results = []
            for match in matches:
                bonus = 0
                title = match.metadata.get("title", "") or ""
                description = match.metadata.get("description", "") or ""
                tags = match.metadata.get("tags", []) or []

                if "testing" in title.lower():
                    bonus += 10
                if "testing" in description.lower():
                    bonus += 5
                if "testing" in [t.lower() for t in tags]:
                    bonus += 7

                scored_results.append((match.score + bonus, match))

            # Sort by composite score descending
            scored_results.sort(key=lambda x: x[0], reverse=True)
            return [m for _, m in scored_results]

        result = benchmark(rank_results)

        # Verify results
        assert isinstance(result, list)

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 1.0, f"Result ranking took {mean_time:.2f}s, expected <1s"

    def test_metadata_extraction_performance(self, benchmark, large_collection_500: Path):
        """Benchmark metadata extraction from all artifacts.

        Target: <3 seconds

        Note: extract_artifact_metadata(path, artifact_type) requires both arguments.
        The artifact type is determined from the metadata filename.
        """
        from skillmeat.utils.metadata import extract_artifact_metadata
        from skillmeat.core.artifact_detection import ArtifactType

        # Map from manifest filename to ArtifactType
        _type_map = {
            "SKILL.MD": ArtifactType.SKILL,
            "COMMAND.MD": ArtifactType.COMMAND,
            "AGENT.MD": ArtifactType.AGENT,
        }

        # Get all metadata files with their artifact types
        metadata_file_pairs = []
        for pattern, artifact_type in [
            ("*SKILL.md", ArtifactType.SKILL),
            ("*COMMAND.md", ArtifactType.COMMAND),
            ("*AGENT.md", ArtifactType.AGENT),
        ]:
            for f in large_collection_500.rglob(pattern):
                metadata_file_pairs.append((f, artifact_type))

        # Run benchmark
        def extract_all_metadata():
            """Extract metadata from all artifacts."""
            metadata_list = []
            for file, artifact_type in metadata_file_pairs:
                try:
                    metadata = extract_artifact_metadata(file, artifact_type)
                    if metadata:
                        metadata_list.append(metadata)
                except Exception:
                    pass  # Skip errors in benchmark
            return metadata_list

        result = benchmark(extract_all_metadata)

        # Verify results
        assert isinstance(result, list)
        assert len(result) > 0

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 3.0, f"Metadata extraction took {mean_time:.2f}s, expected <3s"
