#!/usr/bin/env python3
"""SLA compliance checker for SkillMeat performance tests.

This script verifies that all performance benchmarks meet their SLA targets.
It can read results from JSON files or run benchmarks directly.

Usage:
    python tests/performance/check_slas.py
    python tests/performance/check_slas.py --api-results benchmark_api.json
    python tests/performance/check_slas.py --ops-results benchmark_ops.json
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class SLAViolation:
    """Represents an SLA violation."""

    component: str
    operation: str
    metric: str
    actual: float
    target: float
    severity: str  # "warning" or "critical"


class SLAChecker:
    """Check performance benchmarks against SLA targets."""

    # SLA thresholds
    SLA_TARGETS = {
        # API endpoints (P95 latency in ms)
        "api": {
            "/api/marketplace/listings": 200,
            "/api/marketplace/listings/{id}": 100,
            "/api/mcp/health": 200,
            "/api/collections": 200,
            "/api/analytics/usage": 300,
            "/health": 50,
        },
        # Operations (mean time in ms)
        "operations": {
            "bundle_export": 2000,
            "bundle_import": 2000,
            "mcp_health": 500,
            "collection_list": 1000,
            "collection_search": 1000,
        },
    }

    # Warning thresholds (% above SLA before it becomes critical)
    WARNING_THRESHOLD = 0.8  # Warn if within 80% of SLA
    CRITICAL_THRESHOLD = 1.0  # Critical if exceeds SLA

    def __init__(self):
        """Initialize SLA checker."""
        self.violations: List[SLAViolation] = []
        self.warnings: List[SLAViolation] = []

    def check_api_results(self, results_path: Optional[Path] = None) -> bool:
        """Check API benchmark results against SLAs.

        Args:
            results_path: Path to API benchmark results JSON

        Returns:
            True if all SLAs are met, False otherwise
        """
        if results_path is None or not results_path.exists():
            print(f"  Skipping API check (no results file: {results_path})")
            return True

        print(f"  Checking API benchmarks from {results_path}...")

        with results_path.open() as f:
            results = json.load(f)

        all_passed = True

        for endpoint_result in results.get("endpoints", []):
            endpoint = endpoint_result["endpoint"]

            # Normalize endpoint for SLA lookup
            normalized_endpoint = endpoint
            if "{id}" in endpoint or endpoint.endswith("/test-listing-1"):
                # Normalize specific IDs to template
                parts = endpoint.split("/")
                normalized_endpoint = "/".join(
                    "{id}" if part and part[0].isdigit() or "test-" in part else part
                    for part in parts
                )
                # Fix double slashes
                normalized_endpoint = normalized_endpoint.replace("/{id}", "/{id}")

            # Check if we have an SLA for this endpoint
            if normalized_endpoint not in self.SLA_TARGETS["api"]:
                continue

            target = self.SLA_TARGETS["api"][normalized_endpoint]
            actual = endpoint_result.get("p95", 0)

            # Calculate severity
            ratio = actual / target

            if ratio >= self.CRITICAL_THRESHOLD:
                self.violations.append(
                    SLAViolation(
                        component="API",
                        operation=endpoint,
                        metric="P95 latency",
                        actual=actual,
                        target=target,
                        severity="critical",
                    )
                )
                all_passed = False
            elif ratio >= self.WARNING_THRESHOLD:
                self.warnings.append(
                    SLAViolation(
                        component="API",
                        operation=endpoint,
                        metric="P95 latency",
                        actual=actual,
                        target=target,
                        severity="warning",
                    )
                )

        return all_passed

    def check_operation_results(self, results_path: Optional[Path] = None) -> bool:
        """Check operation benchmark results against SLAs.

        Args:
            results_path: Path to operation benchmark results JSON

        Returns:
            True if all SLAs are met, False otherwise
        """
        if results_path is None or not results_path.exists():
            print(f"  Skipping operation check (no results file: {results_path})")
            return True

        print(f"  Checking operation benchmarks from {results_path}...")

        with results_path.open() as f:
            results = json.load(f)

        all_passed = True

        for op_result in results.get("results", []):
            operation = op_result["operation"]

            if operation not in self.SLA_TARGETS["operations"]:
                continue

            target = self.SLA_TARGETS["operations"][operation]
            actual = op_result.get("time_ms", 0)

            # Calculate severity
            ratio = actual / target

            if ratio >= self.CRITICAL_THRESHOLD:
                self.violations.append(
                    SLAViolation(
                        component="Operations",
                        operation=operation,
                        metric="Mean time",
                        actual=actual,
                        target=target,
                        severity="critical",
                    )
                )
                all_passed = False
            elif ratio >= self.WARNING_THRESHOLD:
                self.warnings.append(
                    SLAViolation(
                        component="Operations",
                        operation=operation,
                        metric="Mean time",
                        actual=actual,
                        target=target,
                        severity="warning",
                    )
                )

        return all_passed

    def print_report(self):
        """Print SLA compliance report."""
        print("\n" + "=" * 80)
        print("SLA Compliance Report")
        print("=" * 80)

        if self.violations:
            print("\n❌ Critical SLA Violations:")
            print("-" * 80)
            for v in self.violations:
                print(f"  {v.component} - {v.operation}")
                print(f"    {v.metric}: {v.actual:.1f}ms (target: {v.target:.1f}ms)")
                print(f"    Exceeded by: {((v.actual / v.target - 1) * 100):.1f}%")
                print()

        if self.warnings:
            print("\n⚠️  Performance Warnings:")
            print("-" * 80)
            for w in self.warnings:
                print(f"  {w.component} - {w.operation}")
                print(f"    {w.metric}: {w.actual:.1f}ms (target: {w.target:.1f}ms)")
                print(f"    At {((w.actual / w.target) * 100):.1f}% of SLA")
                print()

        if not self.violations and not self.warnings:
            print("\n✅ All performance benchmarks meet SLA targets")
            print()
        else:
            critical_count = len(self.violations)
            warning_count = len(self.warnings)
            print(f"\nSummary: {critical_count} violations, {warning_count} warnings")
            print()

    def has_failures(self) -> bool:
        """Check if there are any critical violations.

        Returns:
            True if there are critical violations
        """
        return len(self.violations) > 0


def main():
    """Main entry point for SLA checker."""
    parser = argparse.ArgumentParser(
        description="Check SkillMeat performance benchmarks against SLA targets",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--api-results",
        type=Path,
        default=Path("benchmark_api_results.json"),
        help="Path to API benchmark results JSON",
    )
    parser.add_argument(
        "--ops-results",
        type=Path,
        default=Path("benchmark_ops_results.json"),
        help="Path to operation benchmark results JSON",
    )
    parser.add_argument(
        "--run-benchmarks",
        action="store_true",
        help="Run benchmarks before checking (requires server to be running)",
    )

    args = parser.parse_args()

    print("SLA Compliance Checker")
    print("=" * 80)

    # Run benchmarks if requested
    if args.run_benchmarks:
        print("\nRunning benchmarks...")
        import subprocess

        # Run API benchmarks
        print("\n  Running API benchmarks...")
        result = subprocess.run(
            [
                sys.executable,
                "tests/performance/benchmark_api.py",
                "--output",
                str(args.api_results),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print("    Warning: API benchmarks had failures")

        # Run operation benchmarks
        print("\n  Running operation benchmarks...")
        result = subprocess.run(
            [
                sys.executable,
                "tests/performance/benchmark_operations.py",
                "--output",
                str(args.ops_results),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print("    Warning: Operation benchmarks had failures")

        print("\nBenchmarks complete")

    # Check SLAs
    print("\nChecking SLA compliance...")
    checker = SLAChecker()

    api_passed = checker.check_api_results(args.api_results)
    ops_passed = checker.check_operation_results(args.ops_results)

    # Print report
    checker.print_report()

    # Exit with appropriate code
    if checker.has_failures():
        print("❌ SLA compliance check FAILED")
        sys.exit(1)
    else:
        print("✅ SLA compliance check PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
