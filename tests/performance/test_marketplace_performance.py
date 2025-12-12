"""Performance benchmarks for marketplace GitHub ingestion feature.

Tests scan performance, API response times, heuristic scoring, diff engine,
and memory usage to ensure the feature meets performance targets.

Performance Targets:
- Scan <30s for typical repo (100-500 files)
- API responses <200ms (p95)
- UI renders <1s
- No memory leaks in async scan jobs
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from unittest.mock import Mock, patch

import pytest

from skillmeat.api.schemas.marketplace import (
    DetectedArtifact,
    HeuristicMatch,
    ScanResultDTO,
)
from skillmeat.core.marketplace.diff_engine import CatalogDiffEngine, DiffEntry
from skillmeat.core.marketplace.github_scanner import GitHubScanner, ScanConfig
from skillmeat.core.marketplace.heuristic_detector import (
    ArtifactType,
    HeuristicDetector,
)


# =============================================================================
# Fixtures - Mock Data Generators
# =============================================================================


@pytest.fixture
def mock_small_repo_tree() -> List[Dict]:
    """Generate mock GitHub tree for small repo (50 files)."""
    files = []
    for i in range(50):
        artifact_type = "skill" if i % 3 == 0 else "command" if i % 3 == 1 else "agent"
        files.append({
            "path": f".claude/{artifact_type}s/artifact-{i:03d}/SKILL.md"
            if artifact_type == "skill"
            else f".claude/{artifact_type}s/artifact-{i:03d}/COMMAND.md"
            if artifact_type == "command"
            else f".claude/{artifact_type}s/artifact-{i:03d}/AGENT.md",
            "mode": "100644",
            "type": "blob",
            "sha": f"abc{i:06d}",
            "size": 1024 + i * 10,
            "url": f"https://api.github.com/repos/test/repo/git/blobs/abc{i:06d}",
        })
    return files


@pytest.fixture
def mock_medium_repo_tree() -> List[Dict]:
    """Generate mock GitHub tree for medium repo (500 files)."""
    files = []
    for i in range(500):
        # 60% skills, 20% commands, 20% agents
        if i % 5 < 3:
            artifact_type = "skill"
            manifest = "SKILL.md"
        elif i % 5 == 3:
            artifact_type = "command"
            manifest = "COMMAND.md"
        else:
            artifact_type = "agent"
            manifest = "AGENT.md"

        files.append({
            "path": f".claude/{artifact_type}s/artifact-{i:04d}/{manifest}",
            "mode": "100644",
            "type": "blob",
            "sha": f"abc{i:06d}",
            "size": 2048 + i * 5,
            "url": f"https://api.github.com/repos/test/repo/git/blobs/abc{i:06d}",
        })

        # Add supplementary files (30% of artifacts)
        if i % 3 == 0:
            files.append({
                "path": f".claude/{artifact_type}s/artifact-{i:04d}/README.md",
                "mode": "100644",
                "type": "blob",
                "sha": f"readme{i:06d}",
                "size": 512,
                "url": f"https://api.github.com/repos/test/repo/git/blobs/readme{i:06d}",
            })

    return files


@pytest.fixture
def mock_large_repo_tree() -> List[Dict]:
    """Generate mock GitHub tree for large repo (2000 files)."""
    files = []
    for i in range(2000):
        artifact_type = ["skill", "command", "agent"][i % 3]
        manifest = f"{artifact_type.upper()}.md"

        files.append({
            "path": f".claude/{artifact_type}s/category-{i // 100}/artifact-{i:05d}/{manifest}",
            "mode": "100644",
            "type": "blob",
            "sha": f"abc{i:07d}",
            "size": 1024 + i,
            "url": f"https://api.github.com/repos/test/repo/git/blobs/abc{i:07d}",
        })

    return files


@pytest.fixture
def mock_very_large_repo_tree() -> List[Dict]:
    """Generate mock GitHub tree for very large repo (5000 files)."""
    files = []
    for i in range(5000):
        # Mix of artifacts and non-artifact files
        if i % 2 == 0:
            # Artifact files
            artifact_type = ["skill", "command", "agent", "mcp_server", "hook"][i % 5]
            manifest = f"{artifact_type.replace('_', '-').upper()}.md"
            files.append({
                "path": f".claude/{artifact_type}s/group-{i // 500}/artifact-{i:05d}/{manifest}",
                "mode": "100644",
                "type": "blob",
                "sha": f"abc{i:07d}",
                "size": 2048,
                "url": f"https://api.github.com/repos/test/repo/git/blobs/abc{i:07d}",
            })
        else:
            # Non-artifact files (source code, docs, etc.)
            files.append({
                "path": f"src/module_{i // 100}/file_{i}.py",
                "mode": "100644",
                "type": "blob",
                "sha": f"src{i:07d}",
                "size": 512,
                "url": f"https://api.github.com/repos/test/repo/git/blobs/src{i:07d}",
            })

    return files


@pytest.fixture
def mock_detected_artifacts_small() -> List[DetectedArtifact]:
    """Generate mock detected artifacts for small repo."""
    artifacts = []
    for i in range(17):  # ~50 files / 3 files per artifact
        artifact_type = ["skill", "command", "agent"][i % 3]
        artifacts.append(
            DetectedArtifact(
                upstream_url=f"https://github.com/test/repo/{artifact_type}s/artifact-{i:03d}",
                name=f"artifact-{i:03d}",
                artifact_type=artifact_type,
                detected_sha=f"abc{i:06d}",
                detected_version=f"1.{i}.0",
                path=f".claude/{artifact_type}s/artifact-{i:03d}",
                confidence_score=85,
            )
        )
    return artifacts


@pytest.fixture
def mock_detected_artifacts_medium() -> List[DetectedArtifact]:
    """Generate mock detected artifacts for medium repo."""
    artifacts = []
    for i in range(100):  # ~500 files / 5 files per artifact
        artifact_type = ["skill", "command", "agent"][i % 3]
        artifacts.append(
            DetectedArtifact(
                upstream_url=f"https://github.com/test/repo/{artifact_type}s/artifact-{i:04d}",
                name=f"artifact-{i:04d}",
                artifact_type=artifact_type,
                detected_sha=f"abc{i:06d}",
                detected_version=f"1.{i}.0",
                path=f".claude/{artifact_type}s/artifact-{i:04d}",
                confidence_score=80 + (i % 20),
            )
        )
    return artifacts


@pytest.fixture
def mock_detected_artifacts_large() -> List[DetectedArtifact]:
    """Generate mock detected artifacts for large repo."""
    artifacts = []
    for i in range(400):  # ~2000 files / 5 files per artifact
        artifact_type = ["skill", "command", "agent"][i % 3]
        artifacts.append(
            DetectedArtifact(
                upstream_url=f"https://github.com/test/repo/{artifact_type}s/artifact-{i:05d}",
                name=f"artifact-{i:05d}",
                artifact_type=artifact_type,
                detected_sha=f"abc{i:07d}",
                detected_version=f"2.{i % 10}.0",
                path=f".claude/{artifact_type}s/category-{i // 100}/artifact-{i:05d}",
                confidence_score=75 + (i % 25),
            )
        )
    return artifacts


# =============================================================================
# Test Class: Scan Performance
# =============================================================================


@pytest.mark.slow
class TestScanPerformance:
    """Benchmark GitHub repository scanning performance."""

    def test_scan_small_repo_performance(
        self, benchmark, mock_small_repo_tree, mock_detected_artifacts_small
    ):
        """Benchmark scan time for small repo (50 files).

        Target: <5s
        """
        scanner = GitHubScanner(token=None)

        def run_scan():
            """Simulate scanning small repo."""
            with patch.object(scanner, "_fetch_tree", return_value=mock_small_repo_tree):
                with patch.object(scanner, "_get_ref_sha", return_value="abc123"):
                    with patch(
                        "skillmeat.core.marketplace.github_scanner.detect_artifacts_in_tree",
                        return_value=mock_detected_artifacts_small,
                    ):
                        result = scanner.scan_repository(
                            owner="test",
                            repo="repo",
                            ref="main",
                        )
            return result

        result = benchmark(run_scan)

        # Verify results
        assert result.status == "success"
        assert result.artifacts_found > 0

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert mean_time < 5.0, f"Small repo scan took {mean_time:.2f}s, expected <5s"

    def test_scan_medium_repo_performance(
        self, benchmark, mock_medium_repo_tree, mock_detected_artifacts_medium
    ):
        """Benchmark scan time for medium repo (500 files).

        Target: <15s
        """
        scanner = GitHubScanner(token=None)

        def run_scan():
            """Simulate scanning medium repo."""
            with patch.object(scanner, "_fetch_tree", return_value=mock_medium_repo_tree):
                with patch.object(scanner, "_get_ref_sha", return_value="abc123456"):
                    with patch(
                        "skillmeat.core.marketplace.github_scanner.detect_artifacts_in_tree",
                        return_value=mock_detected_artifacts_medium,
                    ):
                        result = scanner.scan_repository(
                            owner="test",
                            repo="repo",
                            ref="main",
                        )
            return result

        result = benchmark(run_scan)

        # Verify results
        assert result.status == "success"
        assert result.artifacts_found >= 50

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert (
            mean_time < 15.0
        ), f"Medium repo scan took {mean_time:.2f}s, expected <15s"

    def test_scan_large_repo_performance(
        self, benchmark, mock_large_repo_tree, mock_detected_artifacts_large
    ):
        """Benchmark scan time for large repo (2000 files).

        Target: <30s
        """
        scanner = GitHubScanner(token=None)

        def run_scan():
            """Simulate scanning large repo."""
            with patch.object(scanner, "_fetch_tree", return_value=mock_large_repo_tree):
                with patch.object(scanner, "_get_ref_sha", return_value="abc1234567"):
                    with patch(
                        "skillmeat.core.marketplace.github_scanner.detect_artifacts_in_tree",
                        return_value=mock_detected_artifacts_large,
                    ):
                        result = scanner.scan_repository(
                            owner="test",
                            repo="repo",
                            ref="main",
                        )
            return result

        result = benchmark(run_scan)

        # Verify results
        assert result.status == "success"
        assert result.artifacts_found >= 100

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert mean_time < 30.0, f"Large repo scan took {mean_time:.2f}s, expected <30s"

    def test_scan_very_large_repo_with_pagination(
        self, benchmark, mock_very_large_repo_tree
    ):
        """Benchmark scan time for very large repo (5000+ files) with pagination.

        Target: <60s
        """
        scanner = GitHubScanner(token=None, config=ScanConfig(max_files=5000))

        def run_scan():
            """Simulate scanning very large repo with pagination."""
            # Simulate paginated response
            with patch.object(scanner, "_fetch_tree", return_value=mock_very_large_repo_tree):
                with patch.object(scanner, "_get_ref_sha", return_value="abc12345678"):
                    # Mock empty artifacts for performance test
                    with patch(
                        "skillmeat.core.marketplace.github_scanner.detect_artifacts_in_tree",
                        return_value=[],
                    ):
                        result = scanner.scan_repository(
                            owner="test",
                            repo="repo",
                            ref="main",
                        )
            return result

        result = benchmark(run_scan)

        # Verify results
        assert result.status == "success"

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert (
            mean_time < 60.0
        ), f"Very large repo scan took {mean_time:.2f}s, expected <60s"


# =============================================================================
# Test Class: API Response Times
# =============================================================================


@pytest.mark.slow
class TestAPIPerformance:
    """Benchmark API endpoint response times."""

    @patch("skillmeat.api.routers.marketplace.GitHubSourceRepository")
    def test_list_sources_performance(self, mock_repo, benchmark):
        """Benchmark GET /sources endpoint.

        Target: <100ms
        """
        from fastapi.testclient import TestClient

        from skillmeat.api.server import create_app

        # Setup mock repository
        mock_sources = [
            Mock(
                id=f"source-{i}",
                owner="test",
                repo=f"repo-{i}",
                display_name=f"Test Repo {i}",
                created_at=datetime.now(),
                last_scan_at=datetime.now(),
            )
            for i in range(20)
        ]
        mock_repo.return_value.list_all.return_value = mock_sources

        app = create_app()
        client = TestClient(app)

        def call_api():
            """Call list sources endpoint."""
            response = client.get("/api/v1/marketplace/sources")
            return response

        response = benchmark(call_api)

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert (
            mean_time < 0.1
        ), f"GET /sources took {mean_time * 1000:.0f}ms, expected <100ms"

    @patch("skillmeat.api.routers.marketplace.GitHubSourceRepository")
    @patch("skillmeat.api.routers.marketplace.CatalogRepository")
    def test_list_artifacts_with_100_items_performance(
        self, mock_catalog, mock_source, benchmark
    ):
        """Benchmark GET /sources/{id}/artifacts with 100 items.

        Target: <150ms
        """
        from fastapi.testclient import TestClient

        from skillmeat.api.server import create_app

        # Setup mock data
        mock_source_obj = Mock(id="source-1", owner="test", repo="repo")
        mock_source.return_value.get_by_id.return_value = mock_source_obj

        mock_catalog_entries = [
            {
                "upstream_url": f"https://github.com/test/repo/skills/artifact-{i:04d}",
                "name": f"artifact-{i:04d}",
                "artifact_type": "skill",
                "detected_sha": f"abc{i:06d}",
                "detected_version": f"1.{i % 10}.0",
                "path": f".claude/skills/artifact-{i:04d}",
                "confidence_score": 80 + (i % 20),
            }
            for i in range(100)
        ]
        mock_catalog.return_value.get_by_source_id.return_value = mock_catalog_entries

        app = create_app()
        client = TestClient(app)

        def call_api():
            """Call list artifacts endpoint."""
            response = client.get("/api/v1/marketplace/sources/source-1/artifacts")
            return response

        response = benchmark(call_api)

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert (
            mean_time < 0.15
        ), f"GET /artifacts took {mean_time * 1000:.0f}ms, expected <150ms"

    @patch("skillmeat.api.routers.marketplace.GitHubSourceRepository")
    @patch("skillmeat.api.routers.marketplace.CatalogRepository")
    def test_list_artifacts_with_filters_performance(
        self, mock_catalog, mock_source, benchmark
    ):
        """Benchmark GET /sources/{id}/artifacts with filters.

        Target: <200ms
        """
        from fastapi.testclient import TestClient

        from skillmeat.api.server import create_app

        # Setup mock data
        mock_source_obj = Mock(id="source-1", owner="test", repo="repo")
        mock_source.return_value.get_by_id.return_value = mock_source_obj

        mock_catalog_entries = [
            {
                "upstream_url": f"https://github.com/test/repo/skills/artifact-{i:04d}",
                "name": f"artifact-{i:04d}",
                "artifact_type": ["skill", "command", "agent"][i % 3],
                "detected_sha": f"abc{i:06d}",
                "detected_version": f"1.{i % 10}.0",
                "path": f".claude/skills/artifact-{i:04d}",
                "confidence_score": 80 + (i % 20),
            }
            for i in range(200)
        ]

        # Mock filtering
        def filter_entries(source_id, artifact_type=None, min_confidence=None):
            entries = mock_catalog_entries
            if artifact_type:
                entries = [e for e in entries if e["artifact_type"] == artifact_type]
            if min_confidence:
                entries = [e for e in entries if e["confidence_score"] >= min_confidence]
            return entries

        mock_catalog.return_value.get_by_source_id.side_effect = filter_entries

        app = create_app()
        client = TestClient(app)

        def call_api():
            """Call list artifacts endpoint with filters."""
            response = client.get(
                "/api/v1/marketplace/sources/source-1/artifacts",
                params={"artifact_type": "skill", "min_confidence": 85},
            )
            return response

        response = benchmark(call_api)

        # Verify response
        assert response.status_code == 200

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert (
            mean_time < 0.2
        ), f"GET /artifacts with filters took {mean_time * 1000:.0f}ms, expected <200ms"


# =============================================================================
# Test Class: Heuristic Scoring Performance
# =============================================================================


@pytest.mark.slow
class TestHeuristicPerformance:
    """Benchmark heuristic detector performance."""

    def test_score_1000_paths_performance(self, benchmark):
        """Benchmark scoring 1000 paths.

        Target: <100ms
        """
        detector = HeuristicDetector()

        # Generate 1000 realistic paths
        paths = []
        for i in range(1000):
            artifact_type = ["skills", "commands", "agents", "mcp-servers"][i % 4]
            paths.append(f".claude/{artifact_type}/artifact-{i:04d}/SKILL.md")

        def run_detection():
            """Run heuristic detection on paths."""
            matches = detector.analyze_paths(
                paths=paths,
                base_url="https://github.com/test/repo",
            )
            return matches

        matches = benchmark(run_detection)

        # Verify results
        assert isinstance(matches, list)
        assert len(matches) > 0

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert (
            mean_time < 0.1
        ), f"Scoring 1000 paths took {mean_time * 1000:.0f}ms, expected <100ms"

    def test_score_10000_paths_performance(self, benchmark):
        """Benchmark scoring 10000 paths.

        Target: <1s
        """
        detector = HeuristicDetector()

        # Generate 10000 mixed paths (artifacts + noise)
        paths = []
        for i in range(10000):
            if i % 2 == 0:
                # Artifact paths
                artifact_type = ["skills", "commands", "agents"][i % 3]
                paths.append(f".claude/{artifact_type}/artifact-{i:05d}/SKILL.md")
            else:
                # Non-artifact paths (noise)
                paths.append(f"src/module_{i // 100}/file_{i}.py")

        def run_detection():
            """Run heuristic detection on large path set."""
            matches = detector.analyze_paths(
                paths=paths,
                base_url="https://github.com/test/repo",
            )
            return matches

        matches = benchmark(run_detection)

        # Verify results
        assert isinstance(matches, list)

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert (
            mean_time < 1.0
        ), f"Scoring 10000 paths took {mean_time:.2f}s, expected <1s"

    def test_no_n_plus_1_in_scoring(self):
        """Ensure heuristic scoring doesn't have N+1 query issues.

        This test verifies that scoring complexity is O(n), not O(n^2).
        """
        detector = HeuristicDetector()

        # Test with increasing path counts
        timings = []
        for path_count in [100, 1000, 5000]:
            paths = [
                f".claude/skills/artifact-{i:05d}/SKILL.md" for i in range(path_count)
            ]

            start = time.time()
            detector.analyze_paths(paths=paths, base_url="https://github.com/test/repo")
            duration = time.time() - start
            timings.append((path_count, duration))

        # Check that time scales linearly (not quadratically)
        # Ratio of (time_5000 / time_100) should be ~50x, not 2500x
        ratio = timings[2][1] / timings[0][1]
        expected_ratio = timings[2][0] / timings[0][0]  # 50

        # Allow 2x variance for linear scaling
        assert (
            ratio < expected_ratio * 2
        ), f"Scaling ratio {ratio:.1f}x suggests O(n^2) complexity, expected ~{expected_ratio}x"


# =============================================================================
# Test Class: Diff Engine Performance
# =============================================================================


@pytest.mark.slow
class TestDiffEnginePerformance:
    """Benchmark catalog diff engine performance."""

    def test_diff_1000_entries_performance(
        self, benchmark, mock_detected_artifacts_medium
    ):
        """Benchmark comparing catalogs with 1000 entries.

        Target: <500ms
        """
        engine = CatalogDiffEngine()

        # Create old catalog (1000 entries)
        old_catalog = []
        for i in range(1000):
            old_catalog.append({
                "upstream_url": f"https://github.com/test/repo/skills/artifact-{i:04d}",
                "name": f"artifact-{i:04d}",
                "artifact_type": "skill",
                "detected_sha": f"old-sha-{i:06d}",
                "detected_version": "1.0.0",
                "path": f".claude/skills/artifact-{i:04d}",
                "confidence_score": 85,
            })

        # Create new catalog (1000 entries, 10% changed)
        new_catalog = []
        for i in range(1000):
            if i % 10 == 0:
                # Updated (new SHA)
                new_catalog.append({
                    "upstream_url": f"https://github.com/test/repo/skills/artifact-{i:04d}",
                    "name": f"artifact-{i:04d}",
                    "artifact_type": "skill",
                    "detected_sha": f"new-sha-{i:06d}",
                    "detected_version": "1.1.0",
                    "path": f".claude/skills/artifact-{i:04d}",
                    "confidence_score": 90,
                })
            else:
                # Unchanged
                new_catalog.append(old_catalog[i])

        def run_diff():
            """Run catalog diff."""
            diff_result = engine.compare_catalogs(
                old_entries=old_catalog,
                new_artifacts=new_catalog,
            )
            return diff_result

        result = benchmark(run_diff)

        # Verify results
        assert result.total_changes > 0

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert (
            mean_time < 0.5
        ), f"Diff 1000 entries took {mean_time * 1000:.0f}ms, expected <500ms"

    def test_diff_10000_entries_performance(self, benchmark):
        """Benchmark comparing catalogs with 10000 entries.

        Target: <2s
        """
        engine = CatalogDiffEngine()

        # Create old catalog (10000 entries)
        old_catalog = []
        for i in range(10000):
            old_catalog.append({
                "upstream_url": f"https://github.com/test/repo/skills/artifact-{i:05d}",
                "name": f"artifact-{i:05d}",
                "artifact_type": ["skill", "command", "agent"][i % 3],
                "detected_sha": f"old-sha-{i:07d}",
                "detected_version": "2.0.0",
                "path": f".claude/skills/artifact-{i:05d}",
                "confidence_score": 80,
            })

        # Create new catalog (10000 entries, 5% changed)
        new_catalog = []
        for i in range(10000):
            if i % 20 == 0:
                # Updated
                new_catalog.append({
                    "upstream_url": f"https://github.com/test/repo/skills/artifact-{i:05d}",
                    "name": f"artifact-{i:05d}",
                    "artifact_type": ["skill", "command", "agent"][i % 3],
                    "detected_sha": f"new-sha-{i:07d}",
                    "detected_version": "2.1.0",
                    "path": f".claude/skills/artifact-{i:05d}",
                    "confidence_score": 85,
                })
            else:
                # Unchanged
                new_catalog.append(old_catalog[i])

        def run_diff():
            """Run catalog diff on large dataset."""
            diff_result = engine.compare_catalogs(
                old_entries=old_catalog,
                new_artifacts=new_catalog,
            )
            return diff_result

        result = benchmark(run_diff)

        # Verify results
        assert result.total_changes > 0

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert (
            mean_time < 2.0
        ), f"Diff 10000 entries took {mean_time:.2f}s, expected <2s"


# =============================================================================
# Test Class: Memory Usage
# =============================================================================


@pytest.mark.slow
class TestMemoryUsage:
    """Test memory usage and leak detection."""

    def test_scan_memory_stays_bounded(self, mock_medium_repo_tree):
        """Verify scan job memory usage stays bounded.

        Multiple scans should not leak memory.
        """
        pytest.importorskip("psutil", reason="psutil required for memory tests")
        import psutil

        process = psutil.Process()

        scanner = GitHubScanner(token=None)

        # Get baseline memory
        baseline_mb = process.memory_info().rss / 1024 / 1024

        # Run 10 scans
        for i in range(10):
            with patch.object(scanner, "_fetch_tree", return_value=mock_medium_repo_tree):
                with patch.object(scanner, "_get_ref_sha", return_value=f"sha-{i}"):
                    with patch(
                        "skillmeat.core.marketplace.github_scanner.detect_artifacts_in_tree",
                        return_value=[],
                    ):
                        scanner.scan_repository(
                            owner="test",
                            repo=f"repo-{i}",
                            ref="main",
                        )

        # Check final memory
        final_mb = process.memory_info().rss / 1024 / 1024
        memory_increase_mb = final_mb - baseline_mb

        # Memory should not increase by more than 50MB for 10 scans
        assert (
            memory_increase_mb < 50
        ), f"Memory increased by {memory_increase_mb:.1f}MB after 10 scans, possible leak"

    def test_heuristic_detector_memory_efficiency(self):
        """Verify heuristic detector doesn't leak memory with large path sets."""
        pytest.importorskip("psutil", reason="psutil required for memory tests")
        import psutil

        process = psutil.Process()
        detector = HeuristicDetector()

        # Get baseline memory
        baseline_mb = process.memory_info().rss / 1024 / 1024

        # Run detection on large path sets multiple times
        for iteration in range(5):
            paths = [
                f".claude/skills/artifact-{i:05d}/SKILL.md"
                for i in range(iteration * 1000, (iteration + 1) * 1000)
            ]
            detector.analyze_paths(paths=paths, base_url="https://github.com/test/repo")

        # Check final memory
        final_mb = process.memory_info().rss / 1024 / 1024
        memory_increase_mb = final_mb - baseline_mb

        # Memory should not increase by more than 20MB
        assert (
            memory_increase_mb < 20
        ), f"Memory increased by {memory_increase_mb:.1f}MB, possible leak in detector"

    def test_diff_engine_memory_efficiency(self):
        """Verify diff engine doesn't leak memory with large catalogs."""
        pytest.importorskip("psutil", reason="psutil required for memory tests")
        import psutil

        process = psutil.Process()
        engine = CatalogDiffEngine()

        # Get baseline memory
        baseline_mb = process.memory_info().rss / 1024 / 1024

        # Run diffs on large catalogs multiple times
        for iteration in range(5):
            old_catalog = [
                {
                    "upstream_url": f"https://github.com/test/repo/skills/artifact-{i:05d}",
                    "name": f"artifact-{i:05d}",
                    "artifact_type": "skill",
                    "detected_sha": f"old-sha-{i:07d}",
                    "detected_version": "1.0.0",
                }
                for i in range(1000)
            ]

            new_catalog = old_catalog.copy()

            engine.compare_catalogs(old_entries=old_catalog, new_artifacts=new_catalog)

        # Check final memory
        final_mb = process.memory_info().rss / 1024 / 1024
        memory_increase_mb = final_mb - baseline_mb

        # Memory should not increase by more than 20MB
        assert (
            memory_increase_mb < 20
        ), f"Memory increased by {memory_increase_mb:.1f}MB, possible leak in diff engine"


# =============================================================================
# Performance Summary Report
# =============================================================================


def test_performance_summary(pytestconfig):
    """Generate performance summary report.

    This test always passes but logs a summary of all performance targets.
    """
    print("\n" + "=" * 80)
    print("MARKETPLACE GITHUB INGESTION - PERFORMANCE TARGETS")
    print("=" * 80)
    print("\nSCAN PERFORMANCE:")
    print("  - Small repo (50 files):       <5s")
    print("  - Medium repo (500 files):     <15s")
    print("  - Large repo (2000 files):     <30s")
    print("  - Very large repo (5000 files): <60s")
    print("\nAPI RESPONSE TIMES:")
    print("  - GET /sources:                <100ms")
    print("  - GET /sources/{id}/artifacts: <150ms (100 items)")
    print("  - GET /artifacts (filtered):   <200ms")
    print("\nHEURISTIC SCORING:")
    print("  - Score 1000 paths:            <100ms")
    print("  - Score 10000 paths:           <1s")
    print("  - No N+1 issues:               Linear O(n) scaling")
    print("\nDIFF ENGINE:")
    print("  - Compare 1000 entries:        <500ms")
    print("  - Compare 10000 entries:       <2s")
    print("\nMEMORY USAGE:")
    print("  - Scan jobs stay bounded:      <50MB increase over 10 scans")
    print("  - Heuristic detector:          <20MB increase over 5 runs")
    print("  - Diff engine:                 <20MB increase over 5 runs")
    print("=" * 80 + "\n")
