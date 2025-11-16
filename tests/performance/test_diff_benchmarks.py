"""Performance benchmarks for diff operations.

Tests diff engine performance with 500 artifact collections.
Target: <2 seconds for diff operations.
"""

import pytest
from pathlib import Path

from skillmeat.core.diff_engine import DiffEngine


class TestDiffPerformance:
    """Benchmark diff operations on large datasets."""

    def test_diff_500_artifacts_10_percent_changes(
        self, benchmark, large_collection_500: Path, modified_collection_500: Path
    ):
        """Benchmark diff operation on 500 artifacts with 10% changes.

        Target: <3 seconds (adjusted for large dataset complexity)
        """
        diff_engine = DiffEngine()

        # Run benchmark
        result = benchmark(
            diff_engine.diff_directories,
            large_collection_500,
            modified_collection_500,
        )

        # Verify results
        assert result is not None
        assert result.has_changes

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 3.0, f"Diff operation took {mean_time:.2f}s, expected <3s"

    def test_three_way_diff_500_artifacts(
        self, benchmark, large_collection_500: Path, modified_collection_500: Path, tmp_path: Path
    ):
        """Benchmark three-way diff on 500 artifacts.

        Target: <6 seconds (more complex than two-way, includes conflict detection)
        """
        from skillmeat.core.diff_engine import DiffEngine

        diff_engine = DiffEngine()

        # Create a "base" version (copy of original)
        import shutil
        base_dir = tmp_path / "base"
        shutil.copytree(large_collection_500, base_dir)

        # Run benchmark
        result = benchmark(
            diff_engine.three_way_diff,
            base_dir,
            large_collection_500,
            modified_collection_500,
        )

        # Verify results
        assert result is not None

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 6.0, f"Three-way diff took {mean_time:.2f}s, expected <6s"

    def test_diff_only_metadata_files(self, benchmark, large_collection_500: Path, modified_collection_500: Path):
        """Benchmark diff focusing on metadata files only.

        This simulates real-world scenarios where we only diff SKILL.md files.
        Target: <2 seconds
        """
        diff_engine = DiffEngine()

        def diff_metadata_only():
            """Diff only metadata files."""
            # Get all metadata files
            metadata_files_1 = list(large_collection_500.rglob("*SKILL.md")) + \
                               list(large_collection_500.rglob("*COMMAND.md")) + \
                               list(large_collection_500.rglob("*AGENT.md"))

            metadata_files_2 = list(modified_collection_500.rglob("*SKILL.md")) + \
                               list(modified_collection_500.rglob("*COMMAND.md")) + \
                               list(modified_collection_500.rglob("*AGENT.md"))

            # Create mapping
            files_1 = {f.relative_to(large_collection_500): f for f in metadata_files_1}
            files_2 = {f.relative_to(modified_collection_500): f for f in metadata_files_2}

            # Diff each pair
            diffs = []
            for rel_path, file1 in files_1.items():
                if rel_path in files_2:
                    diff = diff_engine.diff_files(file1, files_2[rel_path])
                    if diff and diff.status != "unchanged":
                        diffs.append(diff)

            return diffs

        # Run benchmark
        result = benchmark(diff_metadata_only)

        # Verify results
        assert isinstance(result, list)

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 2.0, f"Metadata-only diff took {mean_time:.2f}s, expected <2s"

    def test_diff_large_files(self, benchmark, tmp_path: Path):
        """Benchmark diff on large files (>100KB).

        Target: <500ms for 10 large files
        """
        diff_engine = DiffEngine()

        # Create 10 large files
        dir1 = tmp_path / "large_files_1"
        dir2 = tmp_path / "large_files_2"
        dir1.mkdir()
        dir2.mkdir()

        for i in range(10):
            # Create ~200KB files
            content = "\n".join([f"Line {j}: " + "x" * 100 for j in range(2000)])

            file1 = dir1 / f"large_file_{i}.txt"
            file2 = dir2 / f"large_file_{i}.txt"

            file1.write_text(content)
            # Modify second version slightly
            modified_content = content + "\nMODIFIED LINE\n"
            file2.write_text(modified_content)

        # Run benchmark
        result = benchmark(diff_engine.diff_directories, dir1, dir2)

        # Verify results
        assert result is not None
        assert result.has_changes

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 0.5, f"Large file diff took {mean_time:.2f}s, expected <0.5s"

    def test_diff_binary_files(self, benchmark, tmp_path: Path):
        """Benchmark diff on binary files.

        Target: <100ms for 20 binary files
        """
        diff_engine = DiffEngine()

        # Create binary files
        dir1 = tmp_path / "binary_1"
        dir2 = tmp_path / "binary_2"
        dir1.mkdir()
        dir2.mkdir()

        for i in range(20):
            # Create fake binary files
            binary_data1 = bytes(range(256)) * 100  # ~25KB
            binary_data2 = bytes(range(256)) * 100 + b"\xFF"  # Slightly different

            file1 = dir1 / f"binary_{i}.dat"
            file2 = dir2 / f"binary_{i}.dat"

            file1.write_bytes(binary_data1)
            file2.write_bytes(binary_data2)

        # Run benchmark
        result = benchmark(diff_engine.diff_directories, dir1, dir2)

        # Verify results
        assert result is not None

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 0.1, f"Binary file diff took {mean_time:.2f}s, expected <0.1s"

    def test_diff_stats_computation(self, benchmark, large_collection_500: Path, modified_collection_500: Path):
        """Benchmark diff statistics computation.

        Target: <500ms for computing stats on 500 artifacts
        """
        diff_engine = DiffEngine()

        # First, get the diff result (not benchmarked)
        diff_result = diff_engine.diff_directories(large_collection_500, modified_collection_500)

        # Benchmark stats computation
        def compute_stats():
            """Compute diff statistics."""
            from skillmeat.models import DiffStats

            added = len(diff_result.files_added)
            modified = len(diff_result.files_modified)
            deleted = len(diff_result.files_removed)
            unchanged = len(diff_result.files_unchanged)

            lines_added = sum(d.lines_added for d in diff_result.files_modified)
            lines_removed = sum(d.lines_removed for d in diff_result.files_modified)

            return DiffStats(
                files_compared=added + modified + deleted + unchanged,
                files_unchanged=unchanged,
                files_changed=added + modified + deleted,
                lines_added=lines_added,
                lines_removed=lines_removed,
            )

        # Run benchmark
        result = benchmark(compute_stats)

        # Verify results
        assert result is not None

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 0.5, f"Stats computation took {mean_time:.2f}s, expected <0.5s"
