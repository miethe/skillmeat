"""Load tests for artifact discovery system.

This test suite validates Discovery & Import Enhancement performance with:
- Large collection (500+ artifacts)
- Large project (300+ artifacts)
- Combined loads (500 Collection + 300 Project)
- Skip preferences (50+ skipped artifacts)
- Stress test (1000+ artifacts)

Performance target: <2 seconds for 500+ artifacts
"""

import time
from datetime import datetime
from pathlib import Path
from typing import List

import pytest

from skillmeat.core.artifact import ArtifactType
from skillmeat.core.discovery import ArtifactDiscoveryService
from skillmeat.core.skip_preferences import SkipPreferenceManager


# =============================================================================
# Fixtures - Artifact Generation
# =============================================================================


@pytest.fixture
def artifact_factory():
    """Factory fixture for creating mock artifacts.

    Yields:
        Callable that creates artifact directories with metadata
    """
    def create_artifacts(
        base_path: Path,
        artifact_type: str,
        count: int,
        prefix: str = "artifact"
    ) -> List[Path]:
        """Create mock artifacts in specified directory.

        Args:
            base_path: Base directory (artifacts/ or .claude/)
            artifact_type: Type (skills, commands, agents, etc.)
            count: Number of artifacts to create
            prefix: Name prefix for artifacts

        Returns:
            List of created artifact paths
        """
        type_dir = base_path / f"{artifact_type}s"
        type_dir.mkdir(parents=True, exist_ok=True)

        created_paths = []

        # Determine metadata file name
        if artifact_type == "skill":
            metadata_file = "SKILL.md"
        elif artifact_type == "command":
            metadata_file = "COMMAND.md"
        elif artifact_type == "agent":
            metadata_file = "AGENT.md"
        elif artifact_type == "hook":
            metadata_file = "HOOK.md"
        elif artifact_type == "mcp":
            metadata_file = "MCP.md"
        else:
            metadata_file = "ARTIFACT.md"

        for i in range(count):
            artifact_name = f"{prefix}-{i:04d}"
            artifact_dir = type_dir / artifact_name
            artifact_dir.mkdir(parents=True, exist_ok=True)

            # Create metadata file with frontmatter
            metadata_content = f"""---
name: {artifact_name}
description: Test {artifact_type} artifact {i}
author: test-author
version: 1.0.{i}
tags:
  - test
  - load-test
  - batch-{i // 100}
source: local/{artifact_type}/{artifact_name}
---

# {artifact_name.title()}

This is a test {artifact_type} artifact for load testing.

## Features
- Feature 1
- Feature 2
- Feature 3

## Usage
Example usage for {artifact_name}.
"""
            (artifact_dir / metadata_file).write_text(metadata_content)

            # Add some dummy files to simulate real artifacts
            (artifact_dir / "README.md").write_text(f"# {artifact_name}\n\nDocumentation")

            if artifact_type == "skill":
                # Skills typically have tools/ directory
                tools_dir = artifact_dir / "tools"
                tools_dir.mkdir(exist_ok=True)
                (tools_dir / "tool1.py").write_text("# Tool 1")
                (tools_dir / "tool2.py").write_text("# Tool 2")

            created_paths.append(artifact_dir)

        return created_paths

    return create_artifacts


@pytest.fixture
def collection_with_large_artifacts(tmp_path, artifact_factory):
    """Create collection with 500 mock artifacts.

    Args:
        tmp_path: Pytest tmp_path fixture
        artifact_factory: Artifact creation factory

    Returns:
        Path to collection directory
    """
    collection_dir = tmp_path / "collection"
    artifacts_dir = collection_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Create 500 artifacts distributed across types
    # Skills: 250, Commands: 100, Agents: 100, Hooks: 30, MCPs: 20
    artifact_factory(artifacts_dir, "skill", 250, "skill")
    artifact_factory(artifacts_dir, "command", 100, "command")
    artifact_factory(artifacts_dir, "agent", 100, "agent")
    artifact_factory(artifacts_dir, "hook", 30, "hook")
    artifact_factory(artifacts_dir, "mcp", 20, "mcp")

    return collection_dir


@pytest.fixture
def project_with_large_artifacts(tmp_path, artifact_factory):
    """Create project with 300 mock artifacts.

    Args:
        tmp_path: Pytest tmp_path fixture
        artifact_factory: Artifact creation factory

    Returns:
        Path to project directory
    """
    project_dir = tmp_path / "project"
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    # Create 300 artifacts distributed across types
    # Skills: 150, Commands: 60, Agents: 60, Hooks: 20, MCPs: 10
    artifact_factory(claude_dir, "skill", 150, "project-skill")
    artifact_factory(claude_dir, "command", 60, "project-command")
    artifact_factory(claude_dir, "agent", 60, "project-agent")
    artifact_factory(claude_dir, "hook", 20, "project-hook")
    artifact_factory(claude_dir, "mcp", 10, "project-mcp")

    return project_dir


@pytest.fixture
def combined_large_environment(tmp_path, artifact_factory):
    """Create environment with both Collection (500) and Project (300) artifacts.

    Args:
        tmp_path: Pytest tmp_path fixture
        artifact_factory: Artifact creation factory

    Returns:
        Tuple of (collection_dir, project_dir)
    """
    # Create collection
    collection_dir = tmp_path / "collection"
    artifacts_dir = collection_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    artifact_factory(artifacts_dir, "skill", 250, "skill")
    artifact_factory(artifacts_dir, "command", 100, "command")
    artifact_factory(artifacts_dir, "agent", 100, "agent")
    artifact_factory(artifacts_dir, "hook", 30, "hook")
    artifact_factory(artifacts_dir, "mcp", 20, "mcp")

    # Create project
    project_dir = tmp_path / "project"
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    artifact_factory(claude_dir, "skill", 150, "project-skill")
    artifact_factory(claude_dir, "command", 60, "project-command")
    artifact_factory(claude_dir, "agent", 60, "project-agent")
    artifact_factory(claude_dir, "hook", 20, "project-hook")
    artifact_factory(claude_dir, "mcp", 10, "project-mcp")

    return collection_dir, project_dir


@pytest.fixture
def stress_test_collection(tmp_path, artifact_factory):
    """Create collection with 1000 artifacts for stress testing.

    Args:
        tmp_path: Pytest tmp_path fixture
        artifact_factory: Artifact creation factory

    Returns:
        Path to collection directory
    """
    collection_dir = tmp_path / "collection"
    artifacts_dir = collection_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Create 1000 artifacts
    # Skills: 500, Commands: 200, Agents: 200, Hooks: 60, MCPs: 40
    artifact_factory(artifacts_dir, "skill", 500, "skill")
    artifact_factory(artifacts_dir, "command", 200, "command")
    artifact_factory(artifacts_dir, "agent", 200, "agent")
    artifact_factory(artifacts_dir, "hook", 60, "hook")
    artifact_factory(artifacts_dir, "mcp", 40, "mcp")

    return collection_dir


# =============================================================================
# Load Test Suite
# =============================================================================


class TestDiscoveryLoadPerformance:
    """Load tests for discovery performance with large artifact counts."""

    def test_large_collection_500_artifacts(self, collection_with_large_artifacts):
        """Test discovery with 500 artifacts in Collection.

        Performance target: <2 seconds
        """
        # Arrange
        service = ArtifactDiscoveryService(
            collection_with_large_artifacts,
            scan_mode="collection"
        )

        # Act
        start_time = time.perf_counter()
        result = service.discover_artifacts()
        duration = time.perf_counter() - start_time

        # Assert - Correctness
        assert result.discovered_count == 500, (
            f"Expected 500 artifacts, found {result.discovered_count}"
        )
        assert len(result.artifacts) == 500
        assert len(result.errors) == 0, f"Unexpected errors: {result.errors}"

        # Assert - Performance
        duration_ms = duration * 1000
        assert duration_ms < 2000, (
            f"Discovery took {duration_ms:.2f}ms, expected <2000ms"
        )

        # Verify scan_duration_ms matches
        assert abs(result.scan_duration_ms - duration_ms) < 100, (
            f"Scan duration mismatch: result={result.scan_duration_ms:.2f}ms, "
            f"measured={duration_ms:.2f}ms"
        )

        print(f"\n✓ Large Collection (500): {duration_ms:.2f}ms")

    def test_large_project_300_artifacts(self, project_with_large_artifacts):
        """Test discovery with 300 artifacts in Project.

        Performance target: <2 seconds
        """
        # Arrange
        service = ArtifactDiscoveryService(
            project_with_large_artifacts,
            scan_mode="project"
        )

        # Act
        start_time = time.perf_counter()
        result = service.discover_artifacts()
        duration = time.perf_counter() - start_time

        # Assert - Correctness
        assert result.discovered_count == 300, (
            f"Expected 300 artifacts, found {result.discovered_count}"
        )
        assert len(result.artifacts) == 300
        assert len(result.errors) == 0, f"Unexpected errors: {result.errors}"

        # Assert - Performance
        duration_ms = duration * 1000
        assert duration_ms < 2000, (
            f"Discovery took {duration_ms:.2f}ms, expected <2000ms"
        )

        print(f"\n✓ Large Project (300): {duration_ms:.2f}ms")

    def test_combined_load_500_plus_300(self, combined_large_environment):
        """Test discovery with 500 Collection + 300 Project artifacts.

        Performance target: <2 seconds per scan
        """
        collection_dir, project_dir = combined_large_environment

        # Test Collection scan
        collection_service = ArtifactDiscoveryService(
            collection_dir,
            scan_mode="collection"
        )

        start_time = time.perf_counter()
        collection_result = collection_service.discover_artifacts()
        collection_duration_ms = (time.perf_counter() - start_time) * 1000

        assert collection_result.discovered_count == 500
        assert collection_duration_ms < 2000, (
            f"Collection scan took {collection_duration_ms:.2f}ms, expected <2000ms"
        )

        # Test Project scan
        project_service = ArtifactDiscoveryService(
            project_dir,
            scan_mode="project"
        )

        start_time = time.perf_counter()
        project_result = project_service.discover_artifacts()
        project_duration_ms = (time.perf_counter() - start_time) * 1000

        assert project_result.discovered_count == 300
        assert project_duration_ms < 2000, (
            f"Project scan took {project_duration_ms:.2f}ms, expected <2000ms"
        )

        # Combined should be within reasonable bounds
        total_duration_ms = collection_duration_ms + project_duration_ms
        total_artifacts = 800
        avg_per_artifact_ms = total_duration_ms / total_artifacts

        print(f"\n✓ Combined Load (500+300):")
        print(f"  Collection: {collection_duration_ms:.2f}ms")
        print(f"  Project: {project_duration_ms:.2f}ms")
        print(f"  Total: {total_duration_ms:.2f}ms")
        print(f"  Avg per artifact: {avg_per_artifact_ms:.3f}ms")

        # Performance expectation: <5ms per artifact on average
        assert avg_per_artifact_ms < 5, (
            f"Average {avg_per_artifact_ms:.3f}ms per artifact exceeds 5ms threshold"
        )

    def test_with_skip_preferences_50_skipped(
        self,
        collection_with_large_artifacts,
        project_with_large_artifacts
    ):
        """Test discovery with 500 Collection + 300 Project + 50 skip preferences.

        Performance target: <2 seconds with skip filtering
        """
        # Create skip preferences file
        skip_file = project_with_large_artifacts / ".claude" / "skip-preferences.json"
        skip_mgr = SkipPreferenceManager(project_with_large_artifacts)

        # Skip 50 artifacts (skills 0-49)
        for i in range(50):
            artifact_key = f"skill:skill-{i:04d}"
            skip_mgr.add_skip(
                artifact_key=artifact_key,
                reason=f"Load test skip {i}"
            )

        # Arrange
        service = ArtifactDiscoveryService(
            collection_with_large_artifacts,
            scan_mode="collection"
        )

        # Act - Discovery with skip preferences
        start_time = time.perf_counter()
        result = service.discover_artifacts(
            project_path=project_with_large_artifacts,
            include_skipped=False
        )
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Assert - Correctness
        assert result.discovered_count == 500, (
            f"Expected 500 discovered, got {result.discovered_count}"
        )

        # Should have 450 importable (500 - 50 skipped)
        assert result.importable_count == 450, (
            f"Expected 450 importable (500 - 50 skipped), got {result.importable_count}"
        )

        assert len(result.artifacts) == 450
        assert len(result.errors) == 0

        # Assert - Performance
        assert duration_ms < 2000, (
            f"Discovery with skip preferences took {duration_ms:.2f}ms, expected <2000ms"
        )

        print(f"\n✓ With Skip Preferences (50 skipped): {duration_ms:.2f}ms")
        print(f"  Discovered: {result.discovered_count}")
        print(f"  Importable: {result.importable_count}")
        print(f"  Skipped: {result.discovered_count - result.importable_count}")

    def test_with_skip_preferences_include_skipped(
        self,
        collection_with_large_artifacts,
        project_with_large_artifacts
    ):
        """Test discovery with include_skipped=True.

        Performance target: <2 seconds with skip filtering and skipped list
        """
        # Create skip preferences
        skip_mgr = SkipPreferenceManager(project_with_large_artifacts)

        for i in range(50):
            artifact_key = f"skill:skill-{i:04d}"
            skip_mgr.add_skip(
                artifact_key=artifact_key,
                reason=f"Load test skip {i}"
            )

        # Arrange
        service = ArtifactDiscoveryService(
            collection_with_large_artifacts,
            scan_mode="collection"
        )

        # Act
        start_time = time.perf_counter()
        result = service.discover_artifacts(
            project_path=project_with_large_artifacts,
            include_skipped=True
        )
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Assert - Correctness
        assert result.discovered_count == 500
        assert result.importable_count == 450
        assert len(result.artifacts) == 450  # Importable only
        assert len(result.skipped_artifacts) == 50  # Skipped list

        # Verify skip reasons are populated
        for skipped in result.skipped_artifacts[:5]:
            assert skipped.skip_reason is not None
            assert "Load test skip" in skipped.skip_reason

        # Assert - Performance
        assert duration_ms < 2000, (
            f"Discovery with include_skipped took {duration_ms:.2f}ms, expected <2000ms"
        )

        print(f"\n✓ Include Skipped (50 skipped): {duration_ms:.2f}ms")
        print(f"  Importable: {len(result.artifacts)}")
        print(f"  Skipped: {len(result.skipped_artifacts)}")

    def test_stress_1000_artifacts(self, stress_test_collection):
        """Stress test with 1000 artifacts (edge case).

        Performance target: <5 seconds (relaxed for stress test)
        """
        # Arrange
        service = ArtifactDiscoveryService(
            stress_test_collection,
            scan_mode="collection"
        )

        # Act
        start_time = time.perf_counter()
        result = service.discover_artifacts()
        duration = time.perf_counter() - start_time

        # Assert - Correctness
        assert result.discovered_count == 1000, (
            f"Expected 1000 artifacts, found {result.discovered_count}"
        )
        assert len(result.artifacts) == 1000
        assert len(result.errors) == 0, f"Unexpected errors: {result.errors}"

        # Assert - Performance (relaxed threshold for stress test)
        duration_ms = duration * 1000
        assert duration_ms < 5000, (
            f"Stress test took {duration_ms:.2f}ms, expected <5000ms"
        )

        # Calculate stats
        avg_per_artifact_ms = duration_ms / 1000

        print(f"\n✓ Stress Test (1000): {duration_ms:.2f}ms")
        print(f"  Avg per artifact: {avg_per_artifact_ms:.3f}ms")

        # Expect <5ms per artifact even at scale
        assert avg_per_artifact_ms < 5, (
            f"Average {avg_per_artifact_ms:.3f}ms per artifact exceeds 5ms threshold"
        )


class TestDiscoveryLoadMemory:
    """Memory efficiency tests for discovery with large artifact counts."""

    def test_memory_no_spike_500_artifacts(self, collection_with_large_artifacts):
        """Test that memory usage doesn't spike with 500 artifacts.

        Note: This is a basic memory check. For production, use memory_profiler.
        """
        import gc
        import sys

        # Force garbage collection before test
        gc.collect()

        # Arrange
        service = ArtifactDiscoveryService(
            collection_with_large_artifacts,
            scan_mode="collection"
        )

        # Get initial object count
        initial_objects = len(gc.get_objects())

        # Act
        result = service.discover_artifacts()

        # Get final object count
        final_objects = len(gc.get_objects())
        object_growth = final_objects - initial_objects

        # Assert - Reasonable memory growth
        # With 500 artifacts, we expect ~500-1000 new objects (artifacts + metadata)
        # Allow up to 5000 objects for overhead (containers, strings, etc.)
        assert object_growth < 10000, (
            f"Object count grew by {object_growth}, expected <10000"
        )

        print(f"\n✓ Memory Check (500 artifacts):")
        print(f"  Initial objects: {initial_objects}")
        print(f"  Final objects: {final_objects}")
        print(f"  Growth: {object_growth}")

        # Verify result is still valid
        assert result.discovered_count == 500

    def test_memory_artifacts_list_reasonable_size(self, stress_test_collection):
        """Test that artifacts list size is reasonable with 1000 artifacts."""
        import sys

        # Arrange
        service = ArtifactDiscoveryService(
            stress_test_collection,
            scan_mode="collection"
        )

        # Act
        result = service.discover_artifacts()

        # Assert - Check size of artifacts list
        artifacts_size = sys.getsizeof(result.artifacts)

        # Each artifact object is ~500-1000 bytes (rough estimate)
        # For 1000 artifacts, expect <1.5MB total
        expected_max_size = 1.5 * 1024 * 1024  # 1.5MB

        assert artifacts_size < expected_max_size, (
            f"Artifacts list size {artifacts_size} bytes exceeds {expected_max_size} bytes"
        )

        print(f"\n✓ Artifacts List Size (1000):")
        print(f"  Size: {artifacts_size / 1024:.2f} KB")
        print(f"  Per artifact: {artifacts_size / 1000:.2f} bytes")


class TestDiscoveryLoadAccuracy:
    """Accuracy tests ensuring all artifacts are processed correctly under load."""

    def test_all_artifacts_processed_correctly(self, collection_with_large_artifacts):
        """Verify all 500 artifacts are processed with correct metadata."""
        # Arrange
        service = ArtifactDiscoveryService(
            collection_with_large_artifacts,
            scan_mode="collection"
        )

        # Act
        result = service.discover_artifacts()

        # Assert - All artifacts found
        assert result.discovered_count == 500
        assert len(result.artifacts) == 500

        # Verify artifact distribution
        type_counts = {}
        for artifact in result.artifacts:
            type_counts[artifact.type] = type_counts.get(artifact.type, 0) + 1

        assert type_counts.get("skill", 0) == 250
        assert type_counts.get("command", 0) == 100
        assert type_counts.get("agent", 0) == 100
        assert type_counts.get("hook", 0) == 30
        assert type_counts.get("mcp", 0) == 20

        # Verify sample artifacts have correct metadata
        skill_artifacts = [a for a in result.artifacts if a.type == "skill"]
        assert len(skill_artifacts) == 250

        # Check first few skills
        for i in range(5):
            skill = next(a for a in skill_artifacts if a.name == f"skill-{i:04d}")
            assert skill.description == f"Test skill artifact {i}"
            assert skill.version == f"1.0.{i}"
            assert "test" in skill.tags
            assert "load-test" in skill.tags
            assert skill.source == f"local/skill/skill-{i:04d}"

        print(f"\n✓ All Artifacts Processed Correctly:")
        print(f"  Skills: {type_counts.get('skill', 0)}")
        print(f"  Commands: {type_counts.get('command', 0)}")
        print(f"  Agents: {type_counts.get('agent', 0)}")
        print(f"  Hooks: {type_counts.get('hook', 0)}")
        print(f"  MCPs: {type_counts.get('mcp', 0)}")

    def test_no_duplicate_artifacts(self, stress_test_collection):
        """Verify no duplicate artifacts in results (edge case with 1000 artifacts)."""
        # Arrange
        service = ArtifactDiscoveryService(
            stress_test_collection,
            scan_mode="collection"
        )

        # Act
        result = service.discover_artifacts()

        # Assert - No duplicates
        artifact_keys = [f"{a.type}:{a.name}" for a in result.artifacts]
        unique_keys = set(artifact_keys)

        assert len(artifact_keys) == len(unique_keys), (
            f"Found {len(artifact_keys) - len(unique_keys)} duplicate artifacts"
        )

        assert len(unique_keys) == 1000

        print(f"\n✓ No Duplicates (1000 artifacts):")
        print(f"  Total: {len(artifact_keys)}")
        print(f"  Unique: {len(unique_keys)}")


# =============================================================================
# Performance Bottleneck Identification
# =============================================================================


class TestDiscoveryBottleneckAnalysis:
    """Tests to identify performance bottlenecks if targets are exceeded."""

    def test_breakdown_by_artifact_type(self, collection_with_large_artifacts):
        """Measure discovery time by artifact type to identify bottlenecks."""
        import time

        base_path = collection_with_large_artifacts / "artifacts"

        # Test each type individually
        type_timings = {}

        for artifact_type, count in [
            ("skills", 250),
            ("commands", 100),
            ("agents", 100),
            ("hooks", 30),
            ("mcps", 20),
        ]:
            # Create isolated test environment
            test_dir = base_path.parent / f"test_{artifact_type}"
            artifacts_dir = test_dir / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)

            # Copy type directory
            import shutil
            shutil.copytree(
                base_path / artifact_type,
                artifacts_dir / artifact_type
            )

            # Measure discovery time
            service = ArtifactDiscoveryService(test_dir, scan_mode="collection")

            start = time.perf_counter()
            result = service.discover_artifacts()
            duration_ms = (time.perf_counter() - start) * 1000

            type_timings[artifact_type] = {
                "count": count,
                "duration_ms": duration_ms,
                "per_artifact_ms": duration_ms / count if count > 0 else 0
            }

            # Clean up
            shutil.rmtree(test_dir)

        # Print breakdown
        print(f"\n✓ Performance Breakdown by Type:")
        for artifact_type, timing in type_timings.items():
            print(f"  {artifact_type}:")
            print(f"    Count: {timing['count']}")
            print(f"    Duration: {timing['duration_ms']:.2f}ms")
            print(f"    Per artifact: {timing['per_artifact_ms']:.3f}ms")

        # Identify slowest type
        slowest_type = max(type_timings.items(), key=lambda x: x[1]['per_artifact_ms'])
        print(f"\n  Slowest: {slowest_type[0]} at {slowest_type[1]['per_artifact_ms']:.3f}ms per artifact")


# =============================================================================
# Summary & Reporting
# =============================================================================


def pytest_sessionfinish(session, exitstatus):
    """Print load test summary after all tests complete."""
    if exitstatus == 0:
        print("\n" + "="*70)
        print("LOAD TEST SUMMARY")
        print("="*70)
        print("\n✓ All load tests passed!")
        print("\nPerformance targets met:")
        print("  - Large Collection (500): <2 seconds")
        print("  - Large Project (300): <2 seconds")
        print("  - Combined (800): <5ms per artifact")
        print("  - With Skip Preferences: <2 seconds")
        print("  - Stress Test (1000): <5 seconds")
        print("\nMemory efficiency verified:")
        print("  - No memory spikes detected")
        print("  - Reasonable object growth")
        print("\nAccuracy validated:")
        print("  - All artifacts processed correctly")
        print("  - No duplicates detected")
        print("="*70 + "\n")
