"""Performance benchmarks for Discovery API endpoint.

Tests validate that discovery scan completes in <2 seconds for typical projects:
- Discovery scan with empty project → <1s
- Discovery with 500 artifacts in Collection → <2s
- Discovery with 200 artifacts in Project → <2s
- Discovery with both Collection (500) + Project (200) → <2s
- Skip preference loading overhead → <100ms
- Memory usage profiling during discovery

Performance Target: <2 seconds for typical project (500 artifacts in Collection, 200 in Project)
"""

import sys
import time
from pathlib import Path
from typing import List

import pytest

from skillmeat.core.discovery import ArtifactDiscoveryService, DiscoveryResult
from skillmeat.core.skip_preferences import SkipPreferenceManager, build_artifact_key

# Optional psutil import for memory profiling
try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


# ===========================
# Fixtures for Test Data
# ===========================


@pytest.fixture
def empty_project(tmp_path: Path) -> Path:
    """Create empty project with .claude/ directory.

    Args:
        tmp_path: Pytest temp directory

    Returns:
        Path to project root
    """
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)

    # Create artifact type directories (empty)
    for artifact_type in ["skills", "commands", "agents", "hooks", "mcps"]:
        (claude_dir / artifact_type).mkdir()

    return tmp_path


@pytest.fixture
def large_collection(tmp_path: Path) -> Path:
    """Create collection with 500 artifacts.

    Artifact distribution:
    - 300 skills
    - 100 commands
    - 50 agents
    - 30 hooks
    - 20 mcps

    Args:
        tmp_path: Pytest temp directory

    Returns:
        Path to collection root
    """
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True)

    # Create 300 skills
    skills_dir = artifacts_dir / "skills"
    skills_dir.mkdir()
    for i in range(300):
        skill_dir = skills_dir / f"skill-{i:03d}"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            f"""---
name: skill-{i:03d}
description: Test skill {i}
author: test-author
version: 1.0.0
tags:
  - testing
  - skill-{i % 10}
source: github/test/skill-{i:03d}
---

# Skill {i}

Test skill for performance benchmarking.
"""
        )

    # Create 100 commands
    commands_dir = artifacts_dir / "commands"
    commands_dir.mkdir()
    for i in range(100):
        cmd_dir = commands_dir / f"command-{i:03d}"
        cmd_dir.mkdir()
        (cmd_dir / "COMMAND.md").write_text(
            f"""---
name: command-{i:03d}
description: Test command {i}
---

# Command {i}
"""
        )

    # Create 50 agents
    agents_dir = artifacts_dir / "agents"
    agents_dir.mkdir()
    for i in range(50):
        agent_dir = agents_dir / f"agent-{i:03d}"
        agent_dir.mkdir()
        (agent_dir / "AGENT.md").write_text(
            f"""---
name: agent-{i:03d}
description: Test agent {i}
---

# Agent {i}
"""
        )

    # Create 30 hooks
    hooks_dir = artifacts_dir / "hooks"
    hooks_dir.mkdir()
    for i in range(30):
        hook_dir = hooks_dir / f"hook-{i:03d}"
        hook_dir.mkdir()
        (hook_dir / "HOOK.md").write_text(
            f"""---
name: hook-{i:03d}
description: Test hook {i}
---

# Hook {i}
"""
        )

    # Create 20 mcps
    mcps_dir = artifacts_dir / "mcps"
    mcps_dir.mkdir()
    for i in range(20):
        mcp_dir = mcps_dir / f"mcp-{i:03d}"
        mcp_dir.mkdir()
        (mcp_dir / "MCP.md").write_text(
            f"""---
name: mcp-{i:03d}
description: Test MCP {i}
---

# MCP {i}
"""
        )

    return tmp_path


@pytest.fixture
def large_project(tmp_path: Path) -> Path:
    """Create project with 200 artifacts in .claude/ directory.

    Artifact distribution:
    - 120 skills
    - 40 commands
    - 25 agents
    - 10 hooks
    - 5 mcps

    Args:
        tmp_path: Pytest temp directory

    Returns:
        Path to project root
    """
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)

    # Create 120 skills
    skills_dir = claude_dir / "skills"
    skills_dir.mkdir()
    for i in range(120):
        skill_dir = skills_dir / f"project-skill-{i:03d}"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            f"""---
name: project-skill-{i:03d}
description: Project skill {i}
---

# Project Skill {i}
"""
        )

    # Create 40 commands
    commands_dir = claude_dir / "commands"
    commands_dir.mkdir()
    for i in range(40):
        cmd_dir = commands_dir / f"project-command-{i:03d}"
        cmd_dir.mkdir()
        (cmd_dir / "COMMAND.md").write_text(
            f"""---
name: project-command-{i:03d}
description: Project command {i}
---

# Project Command {i}
"""
        )

    # Create 25 agents
    agents_dir = claude_dir / "agents"
    agents_dir.mkdir()
    for i in range(25):
        agent_dir = agents_dir / f"project-agent-{i:03d}"
        agent_dir.mkdir()
        (agent_dir / "AGENT.md").write_text(
            f"""---
name: project-agent-{i:03d}
description: Project agent {i}
---

# Project Agent {i}
"""
        )

    # Create 10 hooks
    hooks_dir = claude_dir / "hooks"
    hooks_dir.mkdir()
    for i in range(10):
        hook_dir = hooks_dir / f"project-hook-{i:03d}"
        hook_dir.mkdir()
        (hook_dir / "HOOK.md").write_text(
            f"""---
name: project-hook-{i:03d}
description: Project hook {i}
---

# Project Hook {i}
"""
        )

    # Create 5 mcps
    mcps_dir = claude_dir / "mcps"
    mcps_dir.mkdir()
    for i in range(5):
        mcp_dir = mcps_dir / f"project-mcp-{i:03d}"
        mcp_dir.mkdir()
        (mcp_dir / "MCP.md").write_text(
            f"""---
name: project-mcp-{i:03d}
description: Project MCP {i}
---

# Project MCP {i}
"""
        )

    return tmp_path


@pytest.fixture
def project_with_skip_prefs(tmp_path: Path) -> tuple[Path, List[str]]:
    """Create project with skip preferences file containing 50 skipped artifacts.

    Args:
        tmp_path: Pytest temp directory

    Returns:
        Tuple of (project_path, list of skipped artifact keys)
    """
    # Create project structure
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)

    # Create skills directory (will have some artifacts to skip)
    skills_dir = claude_dir / "skills"
    skills_dir.mkdir()
    for i in range(100):
        skill_dir = skills_dir / f"skill-{i:03d}"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            f"""---
name: skill-{i:03d}
description: Skill {i}
---

# Skill {i}
"""
        )

    # Create skip preferences for 50 artifacts
    skip_mgr = SkipPreferenceManager(tmp_path)
    skipped_keys = []
    for i in range(50):
        artifact_key = build_artifact_key("skill", f"skill-{i:03d}")
        skip_mgr.add_skip(artifact_key, f"Skip reason {i}")
        skipped_keys.append(artifact_key)

    return tmp_path, skipped_keys


# ===========================
# Performance Benchmark Tests
# ===========================


class TestDiscoveryPerformance:
    """Performance benchmarks for discovery scan operations.

    All benchmarks verify performance targets:
    - Empty project: <1s
    - 500 artifacts in Collection: <2s
    - 200 artifacts in Project: <2s
    - Both Collection (500) + Project (200): <2s
    - Skip preference overhead: <100ms
    """

    # Performance thresholds (in seconds)
    EMPTY_PROJECT_THRESHOLD = 1.0
    LARGE_COLLECTION_THRESHOLD = 2.0
    LARGE_PROJECT_THRESHOLD = 2.0
    COMBINED_THRESHOLD = 2.0
    SKIP_OVERHEAD_THRESHOLD = 0.1  # 100ms

    def test_benchmark_empty_project(
        self, empty_project: Path, benchmark
    ) -> None:
        """Benchmark discovery scan with empty project.

        Performance Target: <1 second

        Args:
            empty_project: Empty project fixture
            benchmark: pytest-benchmark fixture
        """
        service = ArtifactDiscoveryService(empty_project, scan_mode="project")

        # Run benchmark
        result: DiscoveryResult = benchmark(service.discover_artifacts)

        # Validate result
        assert result.discovered_count == 0
        assert result.importable_count == 0

        # Validate performance
        duration_sec = result.scan_duration_ms / 1000
        assert (
            duration_sec < self.EMPTY_PROJECT_THRESHOLD
        ), f"Empty project scan took {duration_sec:.2f}s (threshold: {self.EMPTY_PROJECT_THRESHOLD}s)"

    def test_benchmark_large_collection(
        self, large_collection: Path, benchmark
    ) -> None:
        """Benchmark discovery scan with 500 artifacts in Collection.

        Performance Target: <2 seconds

        Args:
            large_collection: Collection with 500 artifacts
            benchmark: pytest-benchmark fixture
        """
        service = ArtifactDiscoveryService(large_collection, scan_mode="collection")

        # Run benchmark
        result: DiscoveryResult = benchmark(service.discover_artifacts)

        # Validate result
        assert result.discovered_count == 500
        assert result.importable_count == 500

        # Validate performance
        duration_sec = result.scan_duration_ms / 1000
        assert (
            duration_sec < self.LARGE_COLLECTION_THRESHOLD
        ), f"Collection scan (500 artifacts) took {duration_sec:.2f}s (threshold: {self.LARGE_COLLECTION_THRESHOLD}s)"

    def test_benchmark_large_project(
        self, large_project: Path, benchmark
    ) -> None:
        """Benchmark discovery scan with 200 artifacts in Project.

        Performance Target: <2 seconds

        Args:
            large_project: Project with 200 artifacts
            benchmark: pytest-benchmark fixture
        """
        service = ArtifactDiscoveryService(large_project, scan_mode="project")

        # Run benchmark
        result: DiscoveryResult = benchmark(service.discover_artifacts)

        # Validate result
        assert result.discovered_count == 200
        assert result.importable_count == 200

        # Validate performance
        duration_sec = result.scan_duration_ms / 1000
        assert (
            duration_sec < self.LARGE_PROJECT_THRESHOLD
        ), f"Project scan (200 artifacts) took {duration_sec:.2f}s (threshold: {self.LARGE_PROJECT_THRESHOLD}s)"

    def test_benchmark_combined_collection_and_project(
        self, tmp_path: Path, benchmark
    ) -> None:
        """Benchmark discovery scan with both Collection (500) and Project (200) artifacts.

        This simulates a realistic scenario where user has a large collection
        and a project with deployed artifacts. The discovery should filter
        out artifacts that exist in both locations.

        Performance Target: <2 seconds

        Args:
            tmp_path: Pytest temp directory
            benchmark: pytest-benchmark fixture
        """
        # Create collection with 500 artifacts
        collection_dir = tmp_path / "collection"
        collection_dir.mkdir()
        artifacts_dir = collection_dir / "artifacts"
        artifacts_dir.mkdir()

        # Create 500 skills in collection
        skills_dir = artifacts_dir / "skills"
        skills_dir.mkdir()
        for i in range(500):
            skill_dir = skills_dir / f"skill-{i:03d}"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                f"""---
name: skill-{i:03d}
description: Skill {i}
source: github/test/skill-{i:03d}
---

# Skill {i}
"""
            )

        # Create project with 200 artifacts (overlapping with collection)
        # First 100 skills overlap, next 100 are project-only
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir()

        project_skills_dir = claude_dir / "skills"
        project_skills_dir.mkdir()
        for i in range(100):
            # Overlapping skills (0-99 from collection)
            skill_dir = project_skills_dir / f"skill-{i:03d}"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                f"""---
name: skill-{i:03d}
description: Skill {i}
source: github/test/skill-{i:03d}
---

# Skill {i}
"""
            )

        for i in range(100, 200):
            # Project-only skills
            skill_dir = project_skills_dir / f"project-skill-{i:03d}"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                f"""---
name: project-skill-{i:03d}
description: Project skill {i}
---

# Project Skill {i}
"""
            )

        # Scan collection (baseline)
        service = ArtifactDiscoveryService(collection_dir, scan_mode="collection")

        # Run benchmark
        result: DiscoveryResult = benchmark(service.discover_artifacts)

        # Validate result
        # Should discover 500 in collection
        assert result.discovered_count == 500

        # Validate performance
        duration_sec = result.scan_duration_ms / 1000
        assert (
            duration_sec < self.COMBINED_THRESHOLD
        ), f"Combined scan (500+200 artifacts) took {duration_sec:.2f}s (threshold: {self.COMBINED_THRESHOLD}s)"

    def test_benchmark_skip_preference_overhead(
        self, project_with_skip_prefs: tuple[Path, List[str]], benchmark
    ) -> None:
        """Benchmark skip preference loading overhead.

        Performance Target: <100ms overhead

        Args:
            project_with_skip_prefs: Project with 50 skip preferences
            benchmark: pytest-benchmark fixture
        """
        project_path, skipped_keys = project_with_skip_prefs

        # Benchmark: Scan WITHOUT skip filtering
        service_no_skip = ArtifactDiscoveryService(project_path, scan_mode="project")
        start_time = time.perf_counter()
        result_no_skip = service_no_skip.discover_artifacts()
        duration_no_skip = time.perf_counter() - start_time

        # Benchmark: Scan WITH skip filtering
        result_with_skip: DiscoveryResult = benchmark(
            service_no_skip.discover_artifacts, project_path=project_path
        )

        # Calculate overhead
        skip_overhead = result_with_skip.scan_duration_ms / 1000 - duration_no_skip

        # Validate results
        assert result_no_skip.discovered_count == 100
        assert result_with_skip.discovered_count == 100
        # With skip filtering, 50 artifacts should be filtered out
        assert result_with_skip.importable_count == 50

        # Validate performance
        assert (
            skip_overhead < self.SKIP_OVERHEAD_THRESHOLD
        ), f"Skip preference overhead: {skip_overhead*1000:.2f}ms (threshold: {self.SKIP_OVERHEAD_THRESHOLD*1000:.0f}ms)"

    @pytest.mark.skipif(
        not HAS_PSUTIL or sys.platform == "win32",
        reason="psutil not available or unreliable on Windows",
    )
    def test_memory_usage_large_collection(self, large_collection: Path) -> None:
        """Profile memory usage during discovery scan of 500 artifacts.

        This test measures peak memory usage during discovery to ensure
        memory efficiency. Not a benchmark test, but important for
        understanding resource usage.

        Memory Target: <100MB increase for 500 artifacts

        Args:
            large_collection: Collection with 500 artifacts
        """
        process = psutil.Process()

        # Get baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Run discovery
        service = ArtifactDiscoveryService(large_collection, scan_mode="collection")
        result = service.discover_artifacts()

        # Get peak memory
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - baseline_memory

        # Validate result
        assert result.discovered_count == 500

        # Log memory usage
        print(f"\nMemory Usage for 500 artifacts:")
        print(f"  Baseline: {baseline_memory:.2f} MB")
        print(f"  Peak: {peak_memory:.2f} MB")
        print(f"  Increase: {memory_increase:.2f} MB")

        # Memory usage should be reasonable (<100MB increase)
        assert (
            memory_increase < 100
        ), f"Memory usage too high: {memory_increase:.2f} MB (expected <100 MB)"


# ===========================
# Manual Performance Tests
# ===========================


class TestDiscoveryPerformanceManual:
    """Manual performance tests that use time.perf_counter() instead of pytest-benchmark.

    These tests are useful for CI/CD environments where pytest-benchmark
    might not be available or for quick manual validation.
    """

    def test_manual_empty_project_performance(self, empty_project: Path) -> None:
        """Manual performance test for empty project.

        Performance Target: <1 second
        """
        service = ArtifactDiscoveryService(empty_project, scan_mode="project")

        start_time = time.perf_counter()
        result = service.discover_artifacts()
        duration = time.perf_counter() - start_time

        # Validate
        assert result.discovered_count == 0
        assert (
            duration < 1.0
        ), f"Empty project scan took {duration:.2f}s (threshold: 1.0s)"

        print(f"\nEmpty project scan: {duration*1000:.2f}ms")

    def test_manual_large_collection_performance(self, large_collection: Path) -> None:
        """Manual performance test for large collection (500 artifacts).

        Performance Target: <2 seconds
        """
        service = ArtifactDiscoveryService(large_collection, scan_mode="collection")

        start_time = time.perf_counter()
        result = service.discover_artifacts()
        duration = time.perf_counter() - start_time

        # Validate
        assert result.discovered_count == 500
        assert (
            duration < 2.0
        ), f"Large collection scan took {duration:.2f}s (threshold: 2.0s)"

        print(f"\nLarge collection scan (500 artifacts): {duration*1000:.2f}ms")

    def test_manual_large_project_performance(self, large_project: Path) -> None:
        """Manual performance test for large project (200 artifacts).

        Performance Target: <2 seconds
        """
        service = ArtifactDiscoveryService(large_project, scan_mode="project")

        start_time = time.perf_counter()
        result = service.discover_artifacts()
        duration = time.perf_counter() - start_time

        # Validate
        assert result.discovered_count == 200
        assert (
            duration < 2.0
        ), f"Large project scan took {duration:.2f}s (threshold: 2.0s)"

        print(f"\nLarge project scan (200 artifacts): {duration*1000:.2f}ms")

    def test_manual_skip_preference_overhead(
        self, project_with_skip_prefs: tuple[Path, List[str]]
    ) -> None:
        """Manual test for skip preference loading overhead.

        Performance Target: <100ms overhead
        """
        project_path, skipped_keys = project_with_skip_prefs

        service = ArtifactDiscoveryService(project_path, scan_mode="project")

        # Benchmark: Scan WITHOUT skip filtering
        start_time = time.perf_counter()
        result_no_skip = service.discover_artifacts()
        duration_no_skip = time.perf_counter() - start_time

        # Benchmark: Scan WITH skip filtering
        start_time = time.perf_counter()
        result_with_skip = service.discover_artifacts(project_path=project_path)
        duration_with_skip = time.perf_counter() - start_time

        # Calculate overhead
        skip_overhead = duration_with_skip - duration_no_skip

        # Validate
        assert result_no_skip.discovered_count == 100
        assert result_with_skip.importable_count == 50
        assert (
            skip_overhead < 0.1
        ), f"Skip preference overhead: {skip_overhead*1000:.2f}ms (threshold: 100ms)"

        print(f"\nSkip preference overhead: {skip_overhead*1000:.2f}ms")


# ===========================
# Performance Summary Report
# ===========================


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Custom pytest hook to display performance summary.

    This hook runs after all tests complete and displays a summary
    of performance benchmark results.
    """
    if hasattr(terminalreporter.config, "workerinput"):
        # Skip in xdist worker processes
        return

    terminalreporter.write_sep("=", "Performance Summary")
    terminalreporter.write_line("")
    terminalreporter.write_line("Discovery Performance Targets:")
    terminalreporter.write_line("  - Empty project: <1 second")
    terminalreporter.write_line("  - Large collection (500): <2 seconds")
    terminalreporter.write_line("  - Large project (200): <2 seconds")
    terminalreporter.write_line("  - Combined (500+200): <2 seconds")
    terminalreporter.write_line("  - Skip preference overhead: <100ms")
    terminalreporter.write_line("")
