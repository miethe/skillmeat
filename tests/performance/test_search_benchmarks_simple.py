"""Simplified performance benchmarks for search operations.

Tests core search functionality performance with 500 artifact collections.
Target: <3 seconds for search operations.
"""

import pytest
import subprocess
from pathlib import Path
from typing import List

from skillmeat.utils.metadata import extract_artifact_metadata, find_metadata_file


class TestSearchPerformanceSimple:
    """Benchmark core search operations on large datasets."""

    def test_metadata_extraction_500_artifacts(self, benchmark, large_collection_500: Path):
        """Benchmark metadata extraction from all artifacts.

        Target: <3 seconds
        """
        # Get all metadata files
        metadata_files = (
            list(large_collection_500.rglob("*/SKILL.md")) +
            list(large_collection_500.rglob("*/COMMAND.md")) +
            list(large_collection_500.rglob("*/AGENT.md"))
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

    def test_grep_content_search_500_artifacts(self, benchmark, large_collection_500: Path):
        """Benchmark grep-based content search across 500 artifacts.

        Target: <1 second (using optimized grep)
        """

        def grep_search():
            """Search content using grep."""
            try:
                result = subprocess.run(
                    ["grep", "-r", "-l", "testing", str(large_collection_500)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                return result.stdout.splitlines()
            except (subprocess.TimeoutExpired, FileNotFoundError):
                # Fallback to Python search
                matches = []
                for file in large_collection_500.rglob("*"):
                    if file.is_file():
                        try:
                            content = file.read_text(errors="ignore")
                            if "testing" in content:
                                matches.append(str(file))
                        except Exception:
                            pass
                return matches

        # Run benchmark
        result = benchmark(grep_search)

        # Verify results
        assert isinstance(result, list)

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 1.0, f"Grep search took {mean_time:.2f}s, expected <1s"

    def test_file_listing_500_artifacts(self, benchmark, large_collection_500: Path):
        """Benchmark artifact file listing.

        Target: <500ms
        """

        def list_all_artifacts():
            """List all artifact directories."""
            artifacts = []
            for artifact_type in ["skill", "command", "agent"]:
                type_dir = large_collection_500 / artifact_type
                if type_dir.exists():
                    for artifact_dir in type_dir.iterdir():
                        if artifact_dir.is_dir():
                            artifacts.append(artifact_dir)
            return artifacts

        # Run benchmark
        result = benchmark(list_all_artifacts)

        # Verify results
        assert isinstance(result, list)
        assert len(result) > 0

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 0.5, f"File listing took {mean_time:.2f}s, expected <0.5s"

    def test_metadata_filtering_500_artifacts(self, benchmark, large_collection_500: Path):
        """Benchmark metadata filtering by tags.

        Target: <2 seconds
        """
        # First, extract all metadata (not benchmarked)
        metadata_files = (
            list(large_collection_500.rglob("*/SKILL.md")) +
            list(large_collection_500.rglob("*/COMMAND.md")) +
            list(large_collection_500.rglob("*/AGENT.md"))
        )

        all_metadata = []
        for file in metadata_files:
            try:
                metadata = extract_artifact_metadata(file)
                if metadata:
                    all_metadata.append((file, metadata))
            except Exception:
                pass

        # Benchmark filtering
        def filter_by_tag():
            """Filter metadata by tag."""
            results = []
            for file, metadata in all_metadata:
                if metadata.tags and "python" in [t.lower() for t in metadata.tags]:
                    results.append(file)
            return results

        result = benchmark(filter_by_tag)

        # Verify results
        assert isinstance(result, list)

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 2.0, f"Metadata filtering took {mean_time:.2f}s, expected <2s"

    def test_simple_text_search_500_artifacts(self, benchmark, large_collection_500: Path):
        """Benchmark simple in-memory text search.

        Target: <4 seconds
        """
        # Get all metadata files
        metadata_files = (
            list(large_collection_500.rglob("*/SKILL.md")) +
            list(large_collection_500.rglob("*/COMMAND.md")) +
            list(large_collection_500.rglob("*/AGENT.md"))
        )

        def search_in_files():
            """Search for term in all files."""
            matches = []
            search_term = "automation"

            for file in metadata_files:
                try:
                    content = file.read_text(errors="ignore")
                    if search_term.lower() in content.lower():
                        matches.append(file)
                except Exception:
                    pass

            return matches

        # Run benchmark
        result = benchmark(search_in_files)

        # Verify results
        assert isinstance(result, list)

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 4.0, f"Text search took {mean_time:.2f}s, expected <4s"

    def test_duplicate_hash_computation(self, benchmark, large_collection_500: Path):
        """Benchmark hash computation for duplicate detection.

        Target: <5 seconds
        """
        import hashlib

        # Get all metadata files
        metadata_files = (
            list(large_collection_500.rglob("*/SKILL.md")) +
            list(large_collection_500.rglob("*/COMMAND.md")) +
            list(large_collection_500.rglob("*/AGENT.md"))
        )

        def compute_hashes():
            """Compute content hashes for all files."""
            hashes = {}
            for file in metadata_files:
                try:
                    content = file.read_bytes()
                    file_hash = hashlib.sha256(content).hexdigest()
                    hashes[str(file)] = file_hash
                except Exception:
                    pass
            return hashes

        # Run benchmark
        result = benchmark(compute_hashes)

        # Verify results
        assert isinstance(result, dict)
        assert len(result) > 0

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 5.0, f"Hash computation took {mean_time:.2f}s, expected <5s"
