"""Performance benchmarks for search operations.

Tests search functionality performance with 500 artifact collections.
Target: <3 seconds for search operations.
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
        """
        search_mgr = SearchManager()

        # Run benchmark with a common search term
        result = benchmark(
            search_mgr.search_metadata,
            large_collection_500,
            query="python",
        )

        # Verify results
        assert isinstance(result, list)

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 3.0, f"Metadata search took {mean_time:.2f}s, expected <3s"

    def test_content_search_500_artifacts(self, benchmark, large_collection_500: Path):
        """Benchmark content search across 500 artifacts using ripgrep.

        Target: <3 seconds
        """
        search_mgr = SearchManager()

        # Run benchmark
        result = benchmark(
            search_mgr.search_content,
            large_collection_500,
            pattern="testing",
        )

        # Verify results
        assert isinstance(result, list)

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 3.0, f"Content search took {mean_time:.2f}s, expected <3s"

    def test_fuzzy_search_500_artifacts(self, benchmark, large_collection_500: Path):
        """Benchmark fuzzy search across 500 artifacts.

        Target: <4 seconds (more complex than exact match)
        """
        search_mgr = SearchManager()

        # Run benchmark with fuzzy search
        result = benchmark(
            search_mgr.fuzzy_search,
            large_collection_500,
            query="analyss",  # Intentional typo
            threshold=0.8,
        )

        # Verify results
        assert isinstance(result, list)

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 4.0, f"Fuzzy search took {mean_time:.2f}s, expected <4s"

    def test_duplicate_detection_500_artifacts(self, benchmark, large_collection_500: Path):
        """Benchmark duplicate detection across 500 artifacts.

        Target: <5 seconds (complex operation with hashing)
        """
        search_mgr = SearchManager()

        # Run benchmark
        result = benchmark(
            search_mgr.find_duplicates,
            large_collection_500,
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
            results = []
            for project in projects:
                matches = search_mgr.search_metadata(project, query="automation")
                results.extend(matches)
            return results

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
        """
        search_mgr = SearchManager()

        # Run benchmark searching for a specific tag
        result = benchmark(
            search_mgr.search_by_tag,
            large_collection_500,
            tag="python",
        )

        # Verify results
        assert isinstance(result, list)

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 2.0, f"Tag-based search took {mean_time:.2f}s, expected <2s"

    def test_combined_metadata_and_content_search(self, benchmark, large_collection_500: Path):
        """Benchmark combined metadata and content search.

        Target: <5 seconds
        """
        search_mgr = SearchManager()

        def combined_search():
            """Perform both metadata and content search."""
            metadata_results = search_mgr.search_metadata(
                large_collection_500, query="automation"
            )
            content_results = search_mgr.search_content(
                large_collection_500, pattern="automation"
            )

            # Combine and deduplicate results
            all_results = {}
            for result in metadata_results + content_results:
                key = str(result.artifact_path)
                if key not in all_results:
                    all_results[key] = result

            return list(all_results.values())

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
        """
        search_mgr = SearchManager()

        # Run benchmark with artifact type filter
        def filtered_search():
            """Search only skill artifacts."""
            all_results = search_mgr.search_metadata(
                large_collection_500, query="process"
            )
            # Filter to only skills
            return [r for r in all_results if r.artifact_type == "skill"]

        result = benchmark(filtered_search)

        # Verify results
        assert isinstance(result, list)

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
        results = search_mgr.search_metadata(large_collection_500, query="testing")

        # Benchmark ranking
        def rank_results():
            """Rank search results by relevance score."""
            # Simple relevance scoring
            scored_results = []
            for result in results:
                score = 0
                # Score based on query matches
                if result.title and "testing" in result.title.lower():
                    score += 10
                if result.description and "testing" in result.description.lower():
                    score += 5
                if result.tags and "testing" in [t.lower() for t in result.tags]:
                    score += 7

                scored_results.append((score, result))

            # Sort by score descending
            scored_results.sort(key=lambda x: x[0], reverse=True)
            return [r for _, r in scored_results]

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
        """
        from skillmeat.utils.metadata import extract_artifact_metadata

        # Get all metadata files
        metadata_files = (
            list(large_collection_500.rglob("*SKILL.md")) +
            list(large_collection_500.rglob("*COMMAND.md")) +
            list(large_collection_500.rglob("*AGENT.md"))
        )

        # Run benchmark
        def extract_all_metadata():
            """Extract metadata from all artifacts."""
            metadata_list = []
            for file in metadata_files:
                try:
                    metadata = extract_artifact_metadata(file)
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
