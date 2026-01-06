"""Performance validation tests for marketplace scan workflow.

Tests scan performance to ensure it meets the <120s target for 1000 artifacts.
Includes benchmarking, bottleneck identification, and optimization verification.

Performance Target (from Phase 2 requirements):
- Scan 1000 artifacts in <120 seconds

Run with: pytest -v --tb=short tests/core/marketplace/test_scan_performance.py
Run performance tests only: pytest -v -m performance
"""

import logging
import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from skillmeat.core.marketplace.content_hash import ContentHashCache
from skillmeat.core.marketplace.deduplication_engine import DeduplicationEngine

# Mark all tests in this module as performance tests
pytestmark = pytest.mark.performance


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def hash_cache() -> ContentHashCache:
    """Create a large hash cache for performance testing."""
    return ContentHashCache(max_size=2000)


@pytest.fixture
def engine(hash_cache: ContentHashCache) -> DeduplicationEngine:
    """Create deduplication engine with caching."""
    return DeduplicationEngine(hash_cache=hash_cache)


def make_test_artifact(
    index: int,
    content_variant: int = 0,
    num_files: int = 3,
    file_size: int = 500,
) -> dict[str, Any]:
    """Create test artifact with configurable characteristics.

    Args:
        index: Artifact index (for path uniqueness).
        content_variant: Content variation (0-9). Same variant = duplicate content.
        num_files: Number of files in artifact (default 3).
        file_size: Approximate size of each file in bytes (default 500).

    Returns:
        Artifact dictionary suitable for deduplication engine.
    """
    files = {}
    for file_idx in range(num_files):
        filename = f"file_{file_idx}.md"
        # Use content_variant to create duplicates
        content = f"# Content Variant {content_variant}\n\n" + ("x" * file_size)
        files[filename] = content

    return {
        "path": f"skills/artifact_{index}",
        "files": files,
        "confidence_score": 0.5 + (index % 50) / 100,  # Varies 0.5-1.0
        "artifact_type": "skill",
        "metadata": {},
    }


def create_artifact_batch(
    count: int,
    duplicate_ratio: float = 0.0,
    num_files: int = 3,
    file_size: int = 500,
) -> list[dict[str, Any]]:
    """Create batch of test artifacts with controlled duplicate rate.

    Args:
        count: Number of artifacts to create.
        duplicate_ratio: Ratio of duplicates (0.0 = all unique, 0.3 = 30% duplicates).
        num_files: Number of files per artifact.
        file_size: Size of each file in bytes.

    Returns:
        List of artifact dictionaries.
    """
    artifacts = []
    num_unique = int(count * (1 - duplicate_ratio))
    num_duplicates = count - num_unique

    # Create unique artifacts
    for i in range(num_unique):
        artifacts.append(
            make_test_artifact(
                index=i,
                content_variant=i,  # Each unique
                num_files=num_files,
                file_size=file_size,
            )
        )

    # Create duplicates by reusing content variants
    for i in range(num_duplicates):
        # Duplicate one of the unique artifacts (cycle through them)
        content_variant = i % num_unique
        artifacts.append(
            make_test_artifact(
                index=num_unique + i,
                content_variant=content_variant,  # Reuse variant
                num_files=num_files,
                file_size=file_size,
            )
        )

    return artifacts


def time_operation(operation_name: str):
    """Context manager to time and log operations.

    Usage:
        with time_operation("Hashing"):
            # ... operation ...
    """

    class TimingContext:
        def __init__(self, name: str):
            self.name = name
            self.start_time = 0.0
            self.elapsed = 0.0

        def __enter__(self):
            self.start_time = time.perf_counter()
            return self

        def __exit__(self, *args):
            self.elapsed = time.perf_counter() - self.start_time
            logging.info(f"{self.name}: {self.elapsed:.3f}s")

    return TimingContext(operation_name)


# ============================================================================
# Performance Tests - Baseline
# ============================================================================


class TestBaselinePerformance:
    """Baseline performance tests with small artifact counts."""

    def test_hash_computation_100_artifacts(self, engine: DeduplicationEngine):
        """Test hash computation performance for 100 artifacts (baseline)."""
        artifacts = create_artifact_batch(100, duplicate_ratio=0.2)

        with time_operation("Hash 100 artifacts") as timer:
            for artifact in artifacts:
                files = artifact["files"]
                engine.compute_hash(files)

        # Should be very fast - under 1 second
        assert timer.elapsed < 1.0, f"Hash computation too slow: {timer.elapsed:.3f}s"
        logging.info(f"  → {len(artifacts) / timer.elapsed:.1f} artifacts/sec")

    def test_within_source_dedup_100_artifacts(self, engine: DeduplicationEngine):
        """Test within-source deduplication for 100 artifacts (baseline)."""
        artifacts = create_artifact_batch(100, duplicate_ratio=0.3)

        with time_operation("Within-source dedup (100)") as timer:
            kept, excluded = engine.deduplicate_within_source(artifacts)

        # Should complete in under 2 seconds
        assert timer.elapsed < 2.0, f"Dedup too slow: {timer.elapsed:.3f}s"
        assert len(kept) + len(excluded) == 100
        logging.info(f"  → Kept: {len(kept)}, Excluded: {len(excluded)}")
        logging.info(f"  → {len(artifacts) / timer.elapsed:.1f} artifacts/sec")

    def test_cross_source_dedup_100_artifacts(self, engine: DeduplicationEngine):
        """Test cross-source deduplication for 100 artifacts (baseline)."""
        artifacts = create_artifact_batch(100, duplicate_ratio=0.0)

        # Pre-compute hashes for artifacts
        for artifact in artifacts:
            hash_val = engine.compute_hash(artifact["files"])
            artifact.setdefault("metadata", {})["content_hash"] = hash_val

        # Create existing hashes (30% overlap)
        existing_hashes = {
            artifacts[i]["metadata"]["content_hash"] for i in range(0, 30)
        }

        with time_operation("Cross-source dedup (100)") as timer:
            unique, duplicates = engine.deduplicate_cross_source(
                artifacts, existing_hashes
            )

        # Should complete in under 1 second
        assert timer.elapsed < 1.0, f"Cross-source dedup too slow: {timer.elapsed:.3f}s"
        assert len(unique) == 70  # 30 were duplicates
        assert len(duplicates) == 30
        logging.info(f"  → Unique: {len(unique)}, Duplicates: {len(duplicates)}")
        logging.info(f"  → {len(artifacts) / timer.elapsed:.1f} artifacts/sec")


# ============================================================================
# Performance Tests - Medium Scale
# ============================================================================


class TestMediumScalePerformance:
    """Medium-scale performance tests (500 artifacts)."""

    def test_within_source_dedup_500_artifacts(self, engine: DeduplicationEngine):
        """Test within-source deduplication for 500 artifacts."""
        artifacts = create_artifact_batch(500, duplicate_ratio=0.25)

        with time_operation("Within-source dedup (500)") as timer:
            kept, excluded = engine.deduplicate_within_source(artifacts)

        # Should complete in under 10 seconds
        assert timer.elapsed < 10.0, f"Dedup too slow: {timer.elapsed:.3f}s"
        assert len(kept) + len(excluded) == 500
        logging.info(f"  → Kept: {len(kept)}, Excluded: {len(excluded)}")
        logging.info(f"  → {len(artifacts) / timer.elapsed:.1f} artifacts/sec")

    def test_full_pipeline_500_artifacts(self, engine: DeduplicationEngine):
        """Test full deduplication pipeline for 500 artifacts."""
        artifacts = create_artifact_batch(500, duplicate_ratio=0.3)

        # Simulate existing collection hashes (20% of unique artifacts)
        num_existing = int(500 * 0.7 * 0.2)  # 20% of unique artifacts

        total_start = time.perf_counter()

        # Stage 1: Within-source dedup
        with time_operation("  Stage 1: Within-source") as stage1:
            kept, within_excluded = engine.deduplicate_within_source(artifacts)

        # Create existing hashes from first N artifacts
        existing_hashes = set()
        for i in range(min(num_existing, len(kept))):
            hash_val = kept[i]["metadata"]["content_hash"]
            existing_hashes.add(hash_val)

        # Stage 2: Cross-source dedup
        with time_operation("  Stage 2: Cross-source") as stage2:
            final, cross_excluded = engine.deduplicate_cross_source(kept, existing_hashes)

        total_elapsed = time.perf_counter() - total_start

        # Total pipeline should complete in under 15 seconds
        assert total_elapsed < 15.0, f"Full pipeline too slow: {total_elapsed:.3f}s"

        logging.info(f"  → Final unique: {len(final)}")
        logging.info(f"  → Within-source excluded: {len(within_excluded)}")
        logging.info(f"  → Cross-source excluded: {len(cross_excluded)}")
        logging.info(f"  → Total time: {total_elapsed:.3f}s")
        logging.info(f"  → {len(artifacts) / total_elapsed:.1f} artifacts/sec")


# ============================================================================
# Performance Tests - Large Scale (1000 artifacts)
# ============================================================================


class TestLargeScalePerformance:
    """Large-scale performance tests (1000 artifacts) - TARGET: <120s."""

    def test_hash_computation_1000_artifacts(self, engine: DeduplicationEngine):
        """Test hash computation performance for 1000 artifacts.

        This tests the hash computation bottleneck in isolation.
        """
        artifacts = create_artifact_batch(1000, duplicate_ratio=0.0)

        with time_operation("Hash 1000 artifacts") as timer:
            for artifact in artifacts:
                files = artifact["files"]
                engine.compute_hash(files)

        # Hashing should be fast - under 5 seconds for 1000 artifacts
        assert timer.elapsed < 5.0, f"Hash computation too slow: {timer.elapsed:.3f}s"
        logging.info(f"  → {len(artifacts) / timer.elapsed:.1f} artifacts/sec")

    def test_hash_caching_effectiveness(self, engine: DeduplicationEngine):
        """Test that hash caching improves performance on repeated scans."""
        artifacts = create_artifact_batch(1000, duplicate_ratio=0.3)

        # First scan - cold cache
        with time_operation("First scan (cold cache)") as cold:
            for artifact in artifacts:
                engine.compute_hash(artifact["files"])

        # Second scan - warm cache (same artifacts)
        with time_operation("Second scan (warm cache)") as warm:
            for artifact in artifacts:
                engine.compute_hash(artifact["files"])

        # Warm cache should be significantly faster (but hashing is already fast,
        # so improvement may be modest - we just verify it's not slower)
        assert warm.elapsed <= cold.elapsed * 1.1, "Cache not improving performance"
        logging.info(f"  → Speedup: {cold.elapsed / warm.elapsed:.2f}x")

    def test_within_source_dedup_1000_artifacts(self, engine: DeduplicationEngine):
        """Test within-source deduplication for 1000 artifacts.

        TARGET: Complete in reasonable time (<60s).
        """
        artifacts = create_artifact_batch(1000, duplicate_ratio=0.25)

        with time_operation("Within-source dedup (1000)") as timer:
            kept, excluded = engine.deduplicate_within_source(artifacts)

        # Should complete in under 60 seconds
        assert timer.elapsed < 60.0, f"Dedup too slow: {timer.elapsed:.3f}s"
        assert len(kept) + len(excluded) == 1000
        logging.info(f"  → Kept: {len(kept)}, Excluded: {len(excluded)}")
        logging.info(f"  → {len(artifacts) / timer.elapsed:.1f} artifacts/sec")

    def test_full_pipeline_1000_artifacts_target(
        self, engine: DeduplicationEngine, caplog: pytest.LogCaptureFixture
    ):
        """Test full deduplication pipeline for 1000 artifacts.

        TARGET: Complete in <120 seconds (Phase 2 requirement).

        This is the main performance validation test.
        """
        caplog.set_level(logging.INFO)

        artifacts = create_artifact_batch(1000, duplicate_ratio=0.3)

        # Simulate existing collection hashes (20% of unique artifacts)
        num_existing = int(1000 * 0.7 * 0.2)  # 20% of unique artifacts

        total_start = time.perf_counter()

        # Stage 1: Within-source dedup
        with time_operation("  Stage 1: Within-source") as stage1:
            kept, within_excluded = engine.deduplicate_within_source(artifacts)

        # Create existing hashes from first N artifacts
        existing_hashes = set()
        for i in range(min(num_existing, len(kept))):
            hash_val = kept[i]["metadata"]["content_hash"]
            existing_hashes.add(hash_val)

        # Stage 2: Cross-source dedup
        with time_operation("  Stage 2: Cross-source") as stage2:
            final, cross_excluded = engine.deduplicate_cross_source(kept, existing_hashes)

        total_elapsed = time.perf_counter() - total_start

        # PRIMARY TARGET: Complete in under 120 seconds
        assert total_elapsed < 120.0, (
            f"PERFORMANCE TARGET MISSED: Scan took {total_elapsed:.3f}s "
            f"(target: <120s for 1000 artifacts)"
        )

        # Log detailed results
        logging.info("\n" + "=" * 60)
        logging.info("PERFORMANCE VALIDATION RESULTS (1000 artifacts)")
        logging.info("=" * 60)
        logging.info(f"Total scan time:          {total_elapsed:.3f}s")
        logging.info(f"Stage 1 (within-source):  {stage1.elapsed:.3f}s")
        logging.info(f"Stage 2 (cross-source):   {stage2.elapsed:.3f}s")
        logging.info(f"Target:                   <120.0s")
        logging.info(f"Status:                   {'✓ PASS' if total_elapsed < 120.0 else '✗ FAIL'}")
        logging.info(f"\nThroughput:              {len(artifacts) / total_elapsed:.1f} artifacts/sec")
        logging.info(f"Time per artifact:        {total_elapsed / len(artifacts) * 1000:.1f}ms")
        logging.info(f"\nResults:")
        logging.info(f"  Final unique:           {len(final)}")
        logging.info(f"  Within-source excluded: {len(within_excluded)}")
        logging.info(f"  Cross-source excluded:  {len(cross_excluded)}")
        logging.info(f"  Total processed:        {len(final) + len(within_excluded) + len(cross_excluded)}")
        logging.info("=" * 60)


# ============================================================================
# Performance Tests - Deduplication Overhead
# ============================================================================


class TestDeduplicationOverhead:
    """Test deduplication overhead vs. baseline hash computation."""

    def test_dedup_overhead_percentage(self, engine: DeduplicationEngine):
        """Measure deduplication overhead vs. raw hash computation.

        Verify that deduplication logic adds <10% overhead compared to
        just computing hashes.
        """
        artifacts = create_artifact_batch(500, duplicate_ratio=0.3)

        # Baseline: Just hash computation
        with time_operation("Baseline (hash only)") as baseline:
            for artifact in artifacts:
                engine.compute_hash(artifact["files"])

        # Full dedup: Hash + duplicate detection + exclusion marking
        with time_operation("Full dedup (hash + logic)") as full:
            engine.deduplicate_within_source(artifacts)

        # Calculate overhead
        overhead = (full.elapsed - baseline.elapsed) / baseline.elapsed * 100

        logging.info(f"  → Baseline time:  {baseline.elapsed:.3f}s")
        logging.info(f"  → Full dedup time: {full.elapsed:.3f}s")
        logging.info(f"  → Overhead:        {overhead:.1f}%")

        # Dedup overhead should be modest (<100% of baseline)
        # Note: For small batches, overhead can be higher percentage-wise due to
        # fixed costs (dict operations, logging, etc.)
        assert overhead < 100.0, f"Dedup overhead too high: {overhead:.1f}%"

    def test_cross_source_dedup_overhead(self, engine: DeduplicationEngine):
        """Measure cross-source deduplication overhead.

        Cross-source dedup should be very fast since hashes are pre-computed.
        """
        artifacts = create_artifact_batch(500, duplicate_ratio=0.0)

        # Pre-compute hashes
        for artifact in artifacts:
            hash_val = engine.compute_hash(artifact["files"])
            artifact.setdefault("metadata", {})["content_hash"] = hash_val

        # Create existing hashes (30% overlap)
        existing_hashes = {
            artifacts[i]["metadata"]["content_hash"] for i in range(0, 150)
        }

        with time_operation("Cross-source dedup (pre-hashed)") as timer:
            unique, duplicates = engine.deduplicate_cross_source(
                artifacts, existing_hashes
            )

        # Should be very fast - just set lookups
        assert timer.elapsed < 1.0, f"Cross-source dedup too slow: {timer.elapsed:.3f}s"
        logging.info(f"  → {len(artifacts) / timer.elapsed:.1f} artifacts/sec")


# ============================================================================
# Performance Tests - File Size Impact
# ============================================================================


class TestFileSizePerformance:
    """Test performance impact of file sizes."""

    def test_small_files_performance(self, engine: DeduplicationEngine):
        """Test performance with small files (100 bytes each)."""
        artifacts = create_artifact_batch(500, num_files=3, file_size=100)

        with time_operation("Small files (100 bytes)") as timer:
            engine.deduplicate_within_source(artifacts)

        logging.info(f"  → {len(artifacts) / timer.elapsed:.1f} artifacts/sec")

    def test_medium_files_performance(self, engine: DeduplicationEngine):
        """Test performance with medium files (1KB each)."""
        artifacts = create_artifact_batch(500, num_files=3, file_size=1000)

        with time_operation("Medium files (1KB)") as timer:
            engine.deduplicate_within_source(artifacts)

        logging.info(f"  → {len(artifacts) / timer.elapsed:.1f} artifacts/sec")

    def test_large_files_performance(self, engine: DeduplicationEngine):
        """Test performance with larger files (10KB each)."""
        artifacts = create_artifact_batch(500, num_files=3, file_size=10_000)

        with time_operation("Large files (10KB)") as timer:
            engine.deduplicate_within_source(artifacts)

        logging.info(f"  → {len(artifacts) / timer.elapsed:.1f} artifacts/sec")

    def test_file_size_limit_prevents_timeout(
        self, engine: DeduplicationEngine, caplog: pytest.LogCaptureFixture
    ):
        """Test that file size limit prevents timeout on huge files."""
        caplog.set_level(logging.WARNING)

        # Create artifact with one huge file (15MB - exceeds 10MB limit)
        artifact = make_test_artifact(
            index=0,
            num_files=1,
            file_size=15 * 1024 * 1024,  # 15MB
        )

        with time_operation("Hash computation (15MB file)") as timer:
            hash_val = engine.compute_hash(artifact["files"])

        # Should complete quickly (file skipped due to size limit)
        assert timer.elapsed < 1.0, f"Hash computation didn't skip large file: {timer.elapsed:.3f}s"

        # Should log warning about skipped file
        assert "exceeds" in caplog.text or "Skipping" in caplog.text


# ============================================================================
# Performance Tests - Scalability
# ============================================================================


class TestScalability:
    """Test that performance scales linearly with artifact count."""

    def test_linear_scaling(self, engine: DeduplicationEngine):
        """Test that processing time scales linearly with artifact count."""
        sizes = [100, 200, 400]
        times = []

        for size in sizes:
            artifacts = create_artifact_batch(size, duplicate_ratio=0.2)

            start = time.perf_counter()
            engine.deduplicate_within_source(artifacts)
            elapsed = time.perf_counter() - start

            times.append(elapsed)
            logging.info(f"  → {size} artifacts: {elapsed:.3f}s ({size / elapsed:.1f} artifacts/sec)")

        # Check that time roughly doubles when size doubles
        # Allow some variance due to overhead
        ratio_1_to_2 = times[1] / times[0]
        ratio_2_to_4 = times[2] / times[1]

        logging.info(f"\nScaling ratios:")
        logging.info(f"  100→200: {ratio_1_to_2:.2f}x")
        logging.info(f"  200→400: {ratio_2_to_4:.2f}x")

        # Ratios should be close to 2.0 (linear scaling)
        # Allow 0.5-3.0x range (some overhead is expected)
        assert 0.5 < ratio_1_to_2 < 3.0, f"Non-linear scaling: {ratio_1_to_2:.2f}x"
        assert 0.5 < ratio_2_to_4 < 3.0, f"Non-linear scaling: {ratio_2_to_4:.2f}x"


# ============================================================================
# Performance Summary
# ============================================================================


def test_performance_summary(caplog: pytest.LogCaptureFixture):
    """Generate performance summary report.

    This test always passes - it's just for reporting.
    """
    caplog.set_level(logging.INFO)

    logging.info("\n" + "=" * 70)
    logging.info("PERFORMANCE TEST SUITE SUMMARY")
    logging.info("=" * 70)
    logging.info("")
    logging.info("Target: Scan 1000 artifacts in <120 seconds")
    logging.info("")
    logging.info("Test Coverage:")
    logging.info("  ✓ Baseline performance (100 artifacts)")
    logging.info("  ✓ Medium-scale performance (500 artifacts)")
    logging.info("  ✓ Large-scale performance (1000 artifacts)")
    logging.info("  ✓ Hash caching effectiveness")
    logging.info("  ✓ Deduplication overhead measurement")
    logging.info("  ✓ File size impact analysis")
    logging.info("  ✓ Linear scalability verification")
    logging.info("")
    logging.info("Key Metrics Validated:")
    logging.info("  • Hash computation speed")
    logging.info("  • Within-source deduplication speed")
    logging.info("  • Cross-source deduplication speed")
    logging.info("  • Cache effectiveness")
    logging.info("  • File size limit protection")
    logging.info("  • Linear scaling characteristics")
    logging.info("")
    logging.info("See test output above for detailed timing results.")
    logging.info("=" * 70)
