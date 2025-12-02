"""Performance benchmarks for SkillMeat cache system (CACHE-6.1).

This module contains comprehensive performance benchmarks for the cache layer,
validating that all cache operations meet the performance targets defined in
the persistent-project-cache PRD.

Performance Targets:
- Cache read latency: <10ms
- Cache write latency: <50ms
- Bulk write (100 projects): <500ms
- Search query latency: <100ms (proven at 2-7ms)
- Cache invalidation: <10ms
- Cache status: <10ms
- Database size: <10MB for 100 projects

Test Strategy:
- Use pytest-benchmark for consistent measurement
- Test both cold and warm cache scenarios
- Measure memory usage for critical operations
- Validate SQLite query performance
- Assert performance targets are met
"""

from __future__ import annotations

import hashlib
import random
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import pytest

from skillmeat.cache.manager import CacheManager
from skillmeat.cache.models import Artifact, Project
from skillmeat.cache.repository import CacheRepository


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_db():
    """Create temporary database for isolated benchmarks."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    yield db_path

    # Cleanup
    try:
        Path(db_path).unlink()
    except FileNotFoundError:
        pass


@pytest.fixture
def cache_manager(temp_db):
    """Create CacheManager instance for benchmarks."""
    manager = CacheManager(db_path=temp_db, ttl_minutes=360)
    manager.initialize_cache()
    return manager


@pytest.fixture
def cache_repository(temp_db):
    """Create CacheRepository instance for benchmarks."""
    from skillmeat.cache.models import create_tables

    create_tables(temp_db)
    return CacheRepository(db_path=temp_db)


@pytest.fixture
def sample_projects_10() -> List[Dict[str, Any]]:
    """Generate 10 sample projects for benchmarks."""
    return _generate_projects(10, artifacts_per_project=10)


@pytest.fixture
def sample_projects_100() -> List[Dict[str, Any]]:
    """Generate 100 sample projects for benchmarks."""
    return _generate_projects(100, artifacts_per_project=10)


@pytest.fixture
def populated_cache(cache_manager, sample_projects_100):
    """Create a cache pre-populated with 100 projects."""
    cache_manager.populate_projects(sample_projects_100)
    return cache_manager


# =============================================================================
# Helper Functions
# =============================================================================


def _generate_projects(
    count: int, artifacts_per_project: int = 10
) -> List[Dict[str, Any]]:
    """Generate realistic project data for benchmarks.

    Args:
        count: Number of projects to generate
        artifacts_per_project: Number of artifacts per project

    Returns:
        List of project dictionaries
    """
    projects = []

    for i in range(count):
        project_id = f"proj-{i:04d}"
        artifacts = []

        for j in range(artifacts_per_project):
            artifact_id = f"art-{i:04d}-{j:04d}"
            deployed_version = f"{random.randint(1, 3)}.{random.randint(0, 10)}.0"
            upstream_version = (
                f"{random.randint(1, 3)}.{random.randint(0, 12)}.0"
                if random.random() > 0.7
                else deployed_version
            )

            artifacts.append(
                {
                    "id": artifact_id,
                    "name": f"artifact-{j:04d}",
                    "type": random.choice(["skill", "command", "agent"]),
                    "source": f"github/user/repo/artifact-{j:04d}",
                    "deployed_version": deployed_version,
                    "upstream_version": upstream_version,
                    "local_modified": random.random() < 0.1,
                }
            )

        projects.append(
            {
                "id": project_id,
                "name": f"Project {i:04d}",
                "path": f"/test/projects/project-{i:04d}",
                "description": f"Test project {i} for benchmarking",
                "artifacts": artifacts,
            }
        )

    return projects


# =============================================================================
# Benchmark: Cache Read Operations
# =============================================================================


class TestCacheReadPerformance:
    """Benchmark cache read operations."""

    def test_cache_read_single_project(self, benchmark, populated_cache):
        """Benchmark: Read single project from cache.

        Target: <10ms
        """
        project_id = "proj-0050"

        # Run benchmark
        result = benchmark(populated_cache.get_project, project_id)

        # Verify results
        assert result is not None
        assert result.id == project_id

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert (
            mean_time < 0.010
        ), f"Cache read took {mean_time*1000:.2f}ms, expected <10ms"

    def test_cache_read_all_projects(self, benchmark, populated_cache):
        """Benchmark: Read all cached projects.

        Target: <10ms for up to 100 projects
        """
        # Run benchmark
        result = benchmark(populated_cache.get_projects)

        # Verify results
        assert len(result) == 100

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert (
            mean_time < 0.010
        ), f"Cache read all took {mean_time*1000:.2f}ms, expected <10ms"

    def test_cache_read_project_by_path(self, benchmark, populated_cache):
        """Benchmark: Read project by filesystem path.

        Target: <10ms
        """
        project_path = "/test/projects/project-0050"

        # Run benchmark
        result = benchmark(populated_cache.get_project_by_path, project_path)

        # Verify results
        assert result is not None
        assert result.path == project_path

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert (
            mean_time < 0.010
        ), f"Cache read by path took {mean_time*1000:.2f}ms, expected <10ms"

    def test_cache_read_artifacts_for_project(self, benchmark, populated_cache):
        """Benchmark: Read all artifacts for a project.

        Target: <10ms
        """
        project_id = "proj-0050"

        # Run benchmark
        result = benchmark(populated_cache.get_artifacts, project_id)

        # Verify results
        assert len(result) == 10

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert (
            mean_time < 0.010
        ), f"Cache read artifacts took {mean_time*1000:.2f}ms, expected <10ms"

    def test_cache_read_with_filter_fresh_only(self, benchmark, populated_cache):
        """Benchmark: Read projects with staleness filter.

        Target: <10ms
        """
        # Run benchmark
        result = benchmark(populated_cache.get_projects, include_stale=False)

        # Verify results
        assert len(result) > 0

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert (
            mean_time < 0.010
        ), f"Cache read with filter took {mean_time*1000:.2f}ms, expected <10ms"


# =============================================================================
# Benchmark: Cache Write Operations
# =============================================================================


class TestCacheWritePerformance:
    """Benchmark cache write operations."""

    def test_cache_write_single_project(self, benchmark, cache_manager):
        """Benchmark: Write single project to cache.

        Target: <50ms
        """
        project_data = _generate_projects(1, artifacts_per_project=10)[0]

        # Run benchmark
        result = benchmark(cache_manager.populate_projects, [project_data])

        # Verify results
        assert result == 1

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert (
            mean_time < 0.050
        ), f"Cache write took {mean_time*1000:.2f}ms, expected <50ms"

    def test_cache_write_bulk_100_projects(self, benchmark, cache_manager, sample_projects_100):
        """Benchmark: Bulk write 100 projects.

        Target: <500ms for 100 projects
        """
        # Run benchmark
        result = benchmark(cache_manager.populate_projects, sample_projects_100)

        # Verify results
        assert result == 100

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert (
            mean_time < 0.500
        ), f"Bulk write took {mean_time*1000:.2f}ms, expected <500ms"

    def test_cache_write_artifacts_only(self, benchmark, cache_manager, sample_projects_10):
        """Benchmark: Write artifacts for a project.

        Target: <50ms for 10 artifacts
        """
        # First create a project
        project_data = sample_projects_10[0]
        artifacts = project_data.pop("artifacts", [])
        cache_manager.populate_projects([project_data])

        # Benchmark artifact population
        result = benchmark(
            cache_manager.populate_artifacts, project_data["id"], artifacts
        )

        # Verify results
        assert result == len(artifacts)

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert (
            mean_time < 0.050
        ), f"Write artifacts took {mean_time*1000:.2f}ms, expected <50ms"

    def test_cache_update_project(self, benchmark, populated_cache):
        """Benchmark: Update existing project.

        Target: <50ms
        """
        project_id = "proj-0050"

        def update_operation():
            return populated_cache.mark_project_refreshed(project_id)

        # Run benchmark
        result = benchmark(update_operation)

        # Verify results
        assert result is True

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert (
            mean_time < 0.050
        ), f"Update project took {mean_time*1000:.2f}ms, expected <50ms"

    def test_cache_batch_update_upstream_versions(self, benchmark, populated_cache):
        """Benchmark: Batch update upstream versions.

        Target: <100ms for 50 artifacts
        """
        # Build version map for 50 artifacts
        version_map = {}
        for i in range(50):
            artifact_id = f"art-{i//10:04d}-{i%10:04d}"
            version_map[artifact_id] = f"2.{random.randint(0, 20)}.0"

        # Run benchmark
        result = benchmark(populated_cache.update_upstream_versions, version_map)

        # Verify results (some may not exist, that's ok)
        assert result >= 0

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert (
            mean_time < 0.100
        ), f"Batch update took {mean_time*1000:.2f}ms, expected <100ms"


# =============================================================================
# Benchmark: Cache Search & Query Operations
# =============================================================================


class TestCacheSearchPerformance:
    """Benchmark cache search and query operations."""

    def test_cache_search_artifacts(self, benchmark, populated_cache):
        """Benchmark: Search artifacts by name.

        Target: <100ms (proven at 2-7ms in production)
        Expected: <10ms in practice
        """
        query = "artifact"

        # Run benchmark
        results, total = benchmark(populated_cache.search_artifacts, query)

        # Verify results
        assert total > 0
        assert len(results) > 0

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert (
            mean_time < 0.100
        ), f"Search took {mean_time*1000:.2f}ms, expected <100ms"

        # Log actual performance (should be much better)
        print(f"\nActual search latency: {mean_time*1000:.2f}ms")

    def test_cache_search_with_filters(self, benchmark, populated_cache):
        """Benchmark: Search with type filter.

        Target: <100ms
        """
        query = "artifact"
        artifact_type = "skill"

        # Run benchmark
        results, total = benchmark(
            populated_cache.search_artifacts, query, artifact_type=artifact_type
        )

        # Verify results
        assert total >= 0

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert (
            mean_time < 0.100
        ), f"Filtered search took {mean_time*1000:.2f}ms, expected <100ms"

    def test_cache_search_with_pagination(self, benchmark, populated_cache):
        """Benchmark: Search with pagination.

        Target: <100ms
        """
        query = "artifact"

        # Run benchmark
        results, total = benchmark(
            populated_cache.search_artifacts, query, skip=10, limit=20
        )

        # Verify results
        assert len(results) <= 20

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert (
            mean_time < 0.100
        ), f"Paginated search took {mean_time*1000:.2f}ms, expected <100ms"

    def test_cache_get_outdated_artifacts(self, benchmark, populated_cache):
        """Benchmark: Get outdated artifacts list.

        Target: <50ms
        """
        # Run benchmark
        result = benchmark(populated_cache.get_outdated_artifacts)

        # Verify results
        assert isinstance(result, list)

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert (
            mean_time < 0.050
        ), f"Get outdated took {mean_time*1000:.2f}ms, expected <50ms"


# =============================================================================
# Benchmark: Cache Management Operations
# =============================================================================


class TestCacheManagementPerformance:
    """Benchmark cache management operations."""

    def test_cache_invalidation_single_project(self, benchmark, populated_cache):
        """Benchmark: Cache invalidation for single project.

        Target: <10ms
        """
        project_id = "proj-0050"

        # Run benchmark
        result = benchmark(populated_cache.invalidate_cache, project_id)

        # Verify results
        assert result == 1

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert (
            mean_time < 0.010
        ), f"Invalidation took {mean_time*1000:.2f}ms, expected <10ms"

    def test_cache_invalidation_all_projects(self, benchmark, populated_cache):
        """Benchmark: Cache invalidation for all projects.

        Target: <100ms for 100 projects
        """
        # Run benchmark
        result = benchmark(populated_cache.invalidate_cache)

        # Verify results
        assert result == 100

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert (
            mean_time < 0.100
        ), f"Full invalidation took {mean_time*1000:.2f}ms, expected <100ms"

    def test_cache_status(self, benchmark, populated_cache):
        """Benchmark: Get cache status/statistics.

        Target: <10ms
        """
        # Run benchmark
        result = benchmark(populated_cache.get_cache_status)

        # Verify results
        assert "total_projects" in result
        assert result["total_projects"] == 100

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert (
            mean_time < 0.010
        ), f"Cache status took {mean_time*1000:.2f}ms, expected <10ms"

    def test_cache_staleness_check_single(self, benchmark, populated_cache):
        """Benchmark: Check if single project is stale.

        Target: <10ms
        """
        project_id = "proj-0050"

        # Run benchmark
        result = benchmark(populated_cache.is_cache_stale, project_id)

        # Verify results
        assert isinstance(result, bool)

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert (
            mean_time < 0.010
        ), f"Staleness check took {mean_time*1000:.2f}ms, expected <10ms"

    def test_cache_clear_all(self, benchmark, cache_manager, sample_projects_100):
        """Benchmark: Clear entire cache.

        Target: <200ms for 100 projects
        """
        # Populate cache first
        cache_manager.populate_projects(sample_projects_100)

        # Run benchmark
        result = benchmark(cache_manager.clear_cache)

        # Verify results
        assert result is True

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert (
            mean_time < 0.200
        ), f"Clear cache took {mean_time*1000:.2f}ms, expected <200ms"


# =============================================================================
# Benchmark: Database Size & Storage
# =============================================================================


class TestCacheDatabaseSize:
    """Benchmark database file size and storage efficiency."""

    def test_database_size_100_projects(self, cache_manager, sample_projects_100, temp_db):
        """Benchmark: Database size with 100 projects.

        Target: <10MB for 100 projects (10,000 artifacts total)
        """
        # Populate cache
        cache_manager.populate_projects(sample_projects_100)

        # Get database file size
        db_path = Path(temp_db)
        db_size = db_path.stat().st_size

        # Convert to MB
        db_size_mb = db_size / (1024 * 1024)

        # Log size
        print(f"\nDatabase size: {db_size_mb:.2f} MB for 100 projects (1000 artifacts)")

        # Performance assertion
        assert db_size_mb < 10.0, f"Database size {db_size_mb:.2f}MB exceeds 10MB limit"

    def test_database_size_growth_linear(self, cache_manager, temp_db):
        """Benchmark: Verify database size grows linearly.

        Ensures no exponential growth or memory leaks.
        """
        sizes = []

        for batch_size in [10, 50, 100]:
            # Clear and repopulate
            cache_manager.clear_cache()
            projects = _generate_projects(batch_size, artifacts_per_project=10)
            cache_manager.populate_projects(projects)

            # Get size
            db_path = Path(temp_db)
            db_size = db_path.stat().st_size
            sizes.append((batch_size, db_size))

            print(f"\n{batch_size} projects: {db_size / 1024:.1f} KB")

        # Verify linear growth (within 50% margin)
        # Size should roughly double when projects double
        size_10, size_50, size_100 = [s[1] for s in sizes]

        growth_10_to_50 = size_50 / size_10
        growth_50_to_100 = size_100 / size_50

        print(f"\nGrowth 10->50: {growth_10_to_50:.2f}x")
        print(f"Growth 50->100: {growth_50_to_100:.2f}x")

        # Should be close to linear (5x and 2x respectively)
        assert 3.0 < growth_10_to_50 < 7.0, "Non-linear growth detected (10->50)"
        assert 1.5 < growth_50_to_100 < 2.5, "Non-linear growth detected (50->100)"


# =============================================================================
# Benchmark: Repository Layer Performance
# =============================================================================


class TestRepositoryPerformance:
    """Benchmark low-level repository operations."""

    def test_repository_create_project(self, benchmark, cache_repository):
        """Benchmark: Repository create project.

        Target: <10ms
        """
        project = Project(
            id="test-proj-001",
            name="Test Project",
            path="/test/path",
            status="active",
        )

        # Run benchmark
        result = benchmark(cache_repository.create_project, project)

        # Verify results
        assert result.id == "test-proj-001"

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert (
            mean_time < 0.010
        ), f"Repository create took {mean_time*1000:.2f}ms, expected <10ms"

    def test_repository_list_projects(self, benchmark, cache_repository):
        """Benchmark: Repository list all projects.

        Target: <10ms for 100 projects
        """
        # Create 100 projects
        for i in range(100):
            project = Project(
                id=f"test-proj-{i:04d}",
                name=f"Test Project {i}",
                path=f"/test/path/{i}",
                status="active",
            )
            cache_repository.create_project(project)

        # Run benchmark
        result = benchmark(cache_repository.list_projects)

        # Verify results
        assert len(result) == 100

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert (
            mean_time < 0.010
        ), f"Repository list took {mean_time*1000:.2f}ms, expected <10ms"

    def test_repository_search_artifacts(self, benchmark, cache_repository):
        """Benchmark: Repository artifact search with SQL.

        Target: <50ms for 1000 artifacts
        """
        # Create a project with 100 artifacts
        project = Project(
            id="search-test-proj",
            name="Search Test Project",
            path="/test/search",
            status="active",
        )
        cache_repository.create_project(project)

        # Create 100 artifacts with various names
        for i in range(100):
            artifact = Artifact(
                id=f"search-art-{i:04d}",
                project_id="search-test-proj",
                name=f"test-artifact-{i:04d}",
                type="skill",
                source="github/test/repo",
                deployed_version="1.0.0",
                upstream_version="1.0.0",
                is_outdated=False,
            )
            cache_repository.create_artifact(artifact)

        # Run benchmark
        results, total = benchmark(
            cache_repository.search_artifacts, "artifact", skip=0, limit=100
        )

        # Verify results
        assert total > 0

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert (
            mean_time < 0.050
        ), f"Repository search took {mean_time*1000:.2f}ms, expected <50ms"


# =============================================================================
# Benchmark: Cold vs Warm Cache
# =============================================================================


class TestColdWarmCachePerformance:
    """Benchmark cold vs warm cache performance."""

    def test_cold_cache_first_read(self, cache_manager, sample_projects_10):
        """Benchmark: First read after cache population (cold).

        Documents cold cache performance.
        """
        # Populate cache
        cache_manager.populate_projects(sample_projects_10)

        # Cold read (first access)
        start = datetime.utcnow()
        result = cache_manager.get_projects()
        cold_time = (datetime.utcnow() - start).total_seconds()

        # Verify
        assert len(result) == 10

        print(f"\nCold cache read: {cold_time*1000:.2f}ms")

        # Should still be fast even when cold
        assert cold_time < 0.050, f"Cold cache too slow: {cold_time*1000:.2f}ms"

    def test_warm_cache_repeated_reads(self, benchmark, populated_cache):
        """Benchmark: Repeated reads from warm cache.

        Target: <5ms (should be even faster than cold)
        """
        # Warm up
        populated_cache.get_projects()
        populated_cache.get_projects()

        # Run benchmark
        result = benchmark(populated_cache.get_projects)

        # Verify results
        assert len(result) == 100

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats["mean"]
        assert (
            mean_time < 0.010
        ), f"Warm cache read took {mean_time*1000:.2f}ms, expected <10ms"

        # Log actual performance
        print(f"\nWarm cache read: {mean_time*1000:.2f}ms")


# =============================================================================
# Benchmark: Memory Usage
# =============================================================================


class TestCacheMemoryUsage:
    """Benchmark memory usage during cache operations.

    Note: These tests use approximate memory tracking.
    For detailed profiling, use memory_profiler separately.
    """

    def test_memory_during_bulk_write(self, cache_manager, sample_projects_100):
        """Benchmark: Memory usage during bulk write.

        Documents memory usage (informational, not strict assertion).
        """
        import sys

        # Get baseline
        baseline = sys.getsizeof(sample_projects_100)

        # Perform operation
        cache_manager.populate_projects(sample_projects_100)

        # Calculate approximate memory used
        # (This is simplified - actual profiling would use memory_profiler)
        print(f"\nInput data size: {baseline / 1024:.1f} KB")
        print("Note: Use memory_profiler for detailed memory analysis")

        # No strict assertion - this is informational
        # Actual memory profiling should be done with dedicated tools

    def test_memory_during_search(self, populated_cache):
        """Benchmark: Memory usage during search.

        Documents memory usage for search operations.
        """
        # Perform search
        results, total = populated_cache.search_artifacts("artifact", limit=100)

        print(f"\nSearch returned {len(results)} results (total: {total})")
        print("Note: Use memory_profiler for detailed memory analysis")

        # No strict assertion - this is informational


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--benchmark-only"])
