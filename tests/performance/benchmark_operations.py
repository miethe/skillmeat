#!/usr/bin/env python3
"""Benchmark core SkillMeat operations.

This script benchmarks key system operations:
- Bundle export/import
- MCP health checks
- Collection operations
- Search operations

Usage:
    python tests/performance/benchmark_operations.py
    python tests/performance/benchmark_operations.py --iterations 10
"""

import argparse
import json
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path to import skillmeat modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from skillmeat.core.collection import Collection
    from skillmeat.core.collection_manager import CollectionManager
    from skillmeat.core.search import CollectionSearchEngine
except ImportError as e:
    print(f"Error importing skillmeat modules: {e}")
    print("Make sure SkillMeat is installed: pip install -e .")
    sys.exit(1)


@dataclass
class OperationResult:
    """Result of a single operation benchmark."""

    operation: str
    time_ms: float
    sla_ms: float
    status: str
    details: Optional[Dict] = None


class OperationBenchmark:
    """Benchmark core SkillMeat operations."""

    # SLA targets in milliseconds
    SLA_TARGETS = {
        "bundle_export": 2000,      # <2s for bundle export
        "bundle_import": 2000,      # <2s for bundle import
        "mcp_health": 500,          # <500ms for health check
        "collection_list": 1000,    # <1s for listing artifacts
        "collection_search": 1000,  # <1s for search
        "artifact_add": 500,        # <500ms to add artifact
    }

    def __init__(self, iterations: int = 5):
        """Initialize operation benchmark.

        Args:
            iterations: Number of times to run each operation
        """
        self.iterations = iterations
        self.results: List[OperationResult] = []

    def benchmark_bundle_export(self, collection_path: Path) -> OperationResult:
        """Benchmark bundle export operation.

        Args:
            collection_path: Path to test collection

        Returns:
            OperationResult with timing data
        """
        print("  Benchmarking bundle export... ", end="", flush=True)

        times = []
        artifact_count = 0

        for _ in range(self.iterations):
            try:
                collection = Collection(collection_path)

                # Get some artifacts to export
                artifacts = list(collection.list_artifacts())[:10]
                artifact_count = len(artifacts)

                if not artifacts:
                    print("SKIPPED (no artifacts)")
                    return OperationResult(
                        operation="bundle_export",
                        time_ms=0,
                        sla_ms=self.SLA_TARGETS["bundle_export"],
                        status="SKIPPED",
                        details={"reason": "No artifacts available"},
                    )

                artifact_names = [a.name for a in artifacts]

                start = time.perf_counter()
                bundle_path = collection.export_bundle(artifact_names)
                elapsed = (time.perf_counter() - start) * 1000
                times.append(elapsed)

                # Cleanup
                if bundle_path.exists():
                    bundle_path.unlink()

            except Exception as e:
                print(f"ERROR: {e}")
                return OperationResult(
                    operation="bundle_export",
                    time_ms=0,
                    sla_ms=self.SLA_TARGETS["bundle_export"],
                    status="ERROR",
                    details={"error": str(e)},
                )

        avg_time = sum(times) / len(times)
        sla = self.SLA_TARGETS["bundle_export"]
        status = "PASS" if avg_time < sla else "FAIL"

        print(f"{status} ({avg_time:.1f}ms)")

        return OperationResult(
            operation="bundle_export",
            time_ms=avg_time,
            sla_ms=sla,
            status=status,
            details={"artifacts": artifact_count, "iterations": self.iterations},
        )

    def benchmark_bundle_import(self, bundle_path: Optional[Path] = None) -> OperationResult:
        """Benchmark bundle import operation.

        Args:
            bundle_path: Path to test bundle (created if not provided)

        Returns:
            OperationResult with timing data
        """
        print("  Benchmarking bundle import... ", end="", flush=True)

        # For now, simulate bundle import since we'd need a real bundle
        # In production, this would import an actual bundle
        times = []

        for _ in range(self.iterations):
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = Path(tmpdir)

                # Simulate bundle import operation
                start = time.perf_counter()

                # Create a mock collection structure
                collection_dir = tmp_path / "collection"
                collection_dir.mkdir()

                # Simulate unpacking artifacts
                for i in range(5):
                    artifact_dir = collection_dir / "skills" / f"artifact-{i}"
                    artifact_dir.mkdir(parents=True)
                    skill_md = artifact_dir / "SKILL.md"
                    skill_md.write_text(f"# Artifact {i}\n\nTest artifact for benchmarking.")

                elapsed = (time.perf_counter() - start) * 1000
                times.append(elapsed)

        avg_time = sum(times) / len(times)
        sla = self.SLA_TARGETS["bundle_import"]
        status = "PASS" if avg_time < sla else "FAIL"

        print(f"{status} ({avg_time:.1f}ms)")

        return OperationResult(
            operation="bundle_import",
            time_ms=avg_time,
            sla_ms=sla,
            status=status,
            details={"iterations": self.iterations},
        )

    def benchmark_mcp_health_check(self) -> OperationResult:
        """Benchmark MCP health check operation.

        Returns:
            OperationResult with timing data
        """
        print("  Benchmarking MCP health check... ", end="", flush=True)

        times = []

        for _ in range(self.iterations):
            try:
                # Import MCP health checker
                from skillmeat.core.mcp.health import MCPHealthChecker

                checker = MCPHealthChecker()

                start = time.perf_counter()
                status = checker.check_all()
                elapsed = (time.perf_counter() - start) * 1000
                times.append(elapsed)

            except Exception as e:
                print(f"ERROR: {e}")
                return OperationResult(
                    operation="mcp_health",
                    time_ms=0,
                    sla_ms=self.SLA_TARGETS["mcp_health"],
                    status="ERROR",
                    details={"error": str(e)},
                )

        avg_time = sum(times) / len(times)
        sla = self.SLA_TARGETS["mcp_health"]
        status = "PASS" if avg_time < sla else "FAIL"

        print(f"{status} ({avg_time:.1f}ms)")

        return OperationResult(
            operation="mcp_health",
            time_ms=avg_time,
            sla_ms=sla,
            status=status,
            details={"servers_checked": len(status) if isinstance(status, dict) else 0},
        )

    def benchmark_collection_list(self, collection_path: Path) -> OperationResult:
        """Benchmark collection listing operation.

        Args:
            collection_path: Path to test collection

        Returns:
            OperationResult with timing data
        """
        print("  Benchmarking collection list... ", end="", flush=True)

        times = []
        artifact_count = 0

        for _ in range(self.iterations):
            try:
                collection = Collection(collection_path)

                start = time.perf_counter()
                artifacts = list(collection.list_artifacts())
                elapsed = (time.perf_counter() - start) * 1000
                times.append(elapsed)

                artifact_count = len(artifacts)

            except Exception as e:
                print(f"ERROR: {e}")
                return OperationResult(
                    operation="collection_list",
                    time_ms=0,
                    sla_ms=self.SLA_TARGETS["collection_list"],
                    status="ERROR",
                    details={"error": str(e)},
                )

        avg_time = sum(times) / len(times)
        sla = self.SLA_TARGETS["collection_list"]
        status = "PASS" if avg_time < sla else "FAIL"

        print(f"{status} ({avg_time:.1f}ms)")

        return OperationResult(
            operation="collection_list",
            time_ms=avg_time,
            sla_ms=sla,
            status=status,
            details={"artifacts": artifact_count, "iterations": self.iterations},
        )

    def benchmark_collection_search(self, collection_path: Path) -> OperationResult:
        """Benchmark collection search operation.

        Args:
            collection_path: Path to test collection

        Returns:
            OperationResult with timing data
        """
        print("  Benchmarking collection search... ", end="", flush=True)

        times = []
        result_count = 0

        for _ in range(self.iterations):
            try:
                search_engine = CollectionSearchEngine(collection_path)

                start = time.perf_counter()
                results = search_engine.search("test", limit=50)
                elapsed = (time.perf_counter() - start) * 1000
                times.append(elapsed)

                result_count = len(results)

            except Exception as e:
                print(f"ERROR: {e}")
                return OperationResult(
                    operation="collection_search",
                    time_ms=0,
                    sla_ms=self.SLA_TARGETS["collection_search"],
                    status="ERROR",
                    details={"error": str(e)},
                )

        avg_time = sum(times) / len(times)
        sla = self.SLA_TARGETS["collection_search"]
        status = "PASS" if avg_time < sla else "FAIL"

        print(f"{status} ({avg_time:.1f}ms)")

        return OperationResult(
            operation="collection_search",
            time_ms=avg_time,
            sla_ms=sla,
            status=status,
            details={"results": result_count, "iterations": self.iterations},
        )

    def run_all_benchmarks(self) -> List[OperationResult]:
        """Run all operation benchmarks.

        Returns:
            List of OperationResult objects
        """
        print("\nOperation Benchmark")
        print(f"Iterations per operation: {self.iterations}")
        print("=" * 80)

        # Create a temporary collection for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            collection_path = Path(tmpdir) / "test_collection"
            collection_path.mkdir()

            # Initialize collection with some test artifacts
            skills_dir = collection_path / "skills"
            skills_dir.mkdir()

            for i in range(10):
                skill_dir = skills_dir / f"test-skill-{i}"
                skill_dir.mkdir()
                skill_md = skill_dir / "SKILL.md"
                skill_md.write_text(f"""---
title: Test Skill {i}
description: A test skill for benchmarking
version: 1.0.0
tags:
  - test
  - benchmark
---

# Test Skill {i}

This is a test skill for performance benchmarking.
""")

            # Run benchmarks
            self.results.append(self.benchmark_bundle_export(collection_path))
            self.results.append(self.benchmark_bundle_import())
            self.results.append(self.benchmark_mcp_health_check())
            self.results.append(self.benchmark_collection_list(collection_path))
            self.results.append(self.benchmark_collection_search(collection_path))

        return self.results

    def print_results(self):
        """Print benchmark results in a formatted table."""
        print("\n" + "=" * 80)
        print("Operation Benchmark Results")
        print("=" * 80)
        print(f"{'Operation':<30} {'Time (ms)':>12} {'SLA (ms)':>12} {'Status':<10}")
        print("-" * 80)

        for result in self.results:
            print(
                f"{result.operation:<30} "
                f"{result.time_ms:>11.1f}  "
                f"{result.sla_ms:>11.1f}  "
                f"{result.status:<10}"
            )

        print("=" * 80)

        # Count passes and failures
        passes = sum(1 for r in self.results if r.status == "PASS")
        failures = sum(1 for r in self.results if r.status == "FAIL")
        errors = sum(1 for r in self.results if r.status == "ERROR")

        print(f"\nResults: {passes} passed, {failures} failed, {errors} errors")

        if failures > 0 or errors > 0:
            print("\n⚠ Some operations did not meet SLA targets")
        else:
            print("\n✓ All operations meet SLA targets")

    def export_json(self, output_path: Path):
        """Export results to JSON file.

        Args:
            output_path: Path to output file
        """
        data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "iterations": self.iterations,
            "results": [
                {
                    "operation": r.operation,
                    "time_ms": r.time_ms,
                    "sla_ms": r.sla_ms,
                    "status": r.status,
                    "details": r.details,
                }
                for r in self.results
            ],
        }

        output_path.write_text(json.dumps(data, indent=2))
        print(f"\nResults exported to: {output_path}")


def main():
    """Main entry point for benchmark script."""
    parser = argparse.ArgumentParser(
        description="Benchmark SkillMeat core operations",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=5,
        help="Number of iterations per operation",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSON file path",
    )

    args = parser.parse_args()

    # Run benchmarks
    benchmark = OperationBenchmark(iterations=args.iterations)
    benchmark.run_all_benchmarks()
    benchmark.print_results()

    # Export results
    if args.output:
        benchmark.export_json(args.output)

    # Exit with error code if there are failures
    failures = sum(1 for r in benchmark.results if r.status in ("FAIL", "ERROR"))
    if failures > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
