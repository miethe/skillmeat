#!/usr/bin/env python3
"""API endpoint benchmarking with detailed performance metrics.

This script benchmarks API endpoints against defined SLAs, measuring:
- Mean response time
- Median response time
- P95 percentile (95% of requests complete within this time)
- P99 percentile (99% of requests complete within this time)
- Min/max response times

Usage:
    python tests/performance/benchmark_api.py
    python tests/performance/benchmark_api.py --url http://localhost:8000 --samples 100
"""

import argparse
import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional

try:
    import requests
except ImportError:
    print("Error: requests library not installed. Run: pip install requests")
    sys.exit(1)


@dataclass
class EndpointMetrics:
    """Performance metrics for a single endpoint."""

    method: str
    endpoint: str
    mean: float
    median: float
    p95: float
    p99: float
    min_time: float
    max_time: float
    success_rate: float
    total_requests: int
    failed_requests: int


@dataclass
class BenchmarkResults:
    """Complete benchmark results."""

    base_url: str
    timestamp: str
    endpoints: List[EndpointMetrics]
    sla_violations: List[Dict[str, str]]


class APIBenchmark:
    """API benchmarking with comprehensive metrics."""

    # SLA targets (in milliseconds)
    SLA_TARGETS = {
        "/api/marketplace/listings": {"p95": 200, "p99": 500},
        "/api/marketplace/listings/{id}": {"p95": 100, "p99": 300},
        "/api/marketplace/install": {"p95": 3000, "p99": 5000},
        "/api/marketplace/publish": {"p95": 5000, "p99": 10000},
        "/api/mcp/health": {"p95": 200, "p99": 500},
        "/api/sharing/export": {"p95": 1500, "p99": 3000},
        "/api/sharing/import": {"p95": 1500, "p99": 3000},
        "/api/collections": {"p95": 200, "p99": 500},
        "/api/analytics/usage": {"p95": 300, "p99": 800},
        "/health": {"p95": 50, "p99": 100},
    }

    def __init__(self, base_url: str = "http://localhost:8000", samples: int = 100):
        """Initialize API benchmark.

        Args:
            base_url: Base URL of the API server
            samples: Number of requests to make per endpoint
        """
        self.base_url = base_url.rstrip("/")
        self.samples = samples
        self.results: List[EndpointMetrics] = []
        self.sla_violations: List[Dict[str, str]] = []

    def measure_endpoint(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> EndpointMetrics:
        """Measure performance of a single endpoint.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments to pass to requests

        Returns:
            EndpointMetrics with detailed performance data
        """
        url = f"{self.base_url}{endpoint}"
        times: List[float] = []
        failed = 0

        print(f"  Benchmarking {method} {endpoint}... ", end="", flush=True)

        for _ in range(self.samples):
            try:
                start = time.perf_counter()
                response = requests.request(method, url, timeout=30, **kwargs)
                elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
                times.append(elapsed)

                if response.status_code not in (200, 201, 204):
                    failed += 1
                    if failed == 1:  # Print first error
                        print(f"\n    Warning: Status {response.status_code}", end="")

            except requests.RequestException as e:
                failed += 1
                if failed == 1:  # Print first error
                    print(f"\n    Warning: {type(e).__name__}", end="")
                # Add a large penalty time for failed requests
                times.append(30000)  # 30 second penalty

        if not times:
            print("FAILED")
            return EndpointMetrics(
                method=method,
                endpoint=endpoint,
                mean=0,
                median=0,
                p95=0,
                p99=0,
                min_time=0,
                max_time=0,
                success_rate=0.0,
                total_requests=self.samples,
                failed_requests=failed,
            )

        # Calculate metrics
        times.sort()
        metrics = EndpointMetrics(
            method=method,
            endpoint=endpoint,
            mean=statistics.mean(times),
            median=statistics.median(times),
            p95=times[int(len(times) * 0.95)],
            p99=times[int(len(times) * 0.99)],
            min_time=min(times),
            max_time=max(times),
            success_rate=((self.samples - failed) / self.samples) * 100,
            total_requests=self.samples,
            failed_requests=failed,
        )

        print(f"Done (mean: {metrics.mean:.0f}ms)")

        # Check SLA violations
        if endpoint in self.SLA_TARGETS:
            sla = self.SLA_TARGETS[endpoint]
            if metrics.p95 > sla["p95"]:
                self.sla_violations.append({
                    "endpoint": endpoint,
                    "metric": "P95",
                    "actual": f"{metrics.p95:.2f}ms",
                    "target": f"{sla['p95']}ms",
                })
            if metrics.p99 > sla["p99"]:
                self.sla_violations.append({
                    "endpoint": endpoint,
                    "metric": "P99",
                    "actual": f"{metrics.p99:.2f}ms",
                    "target": f"{sla['p99']}ms",
                })

        return metrics

    def run_all_benchmarks(self) -> BenchmarkResults:
        """Run all endpoint benchmarks.

        Returns:
            BenchmarkResults with complete performance data
        """
        print(f"\nAPI Benchmark - {self.base_url}")
        print(f"Samples per endpoint: {self.samples}")
        print("=" * 80)

        # Define endpoints to benchmark
        endpoints = [
            ("GET", "/health"),
            ("GET", "/api/marketplace/listings", {"params": {"limit": 50}}),
            ("GET", "/api/marketplace/listings", {"params": {"query": "test", "limit": 20}}),
            ("GET", "/api/marketplace/listings/test-listing-1", {}),
            ("GET", "/api/mcp/health", {}),
            ("GET", "/api/collections", {}),
            ("GET", "/api/collections/default", {}),
            ("GET", "/api/analytics/usage", {"params": {"days": 30}}),
            ("GET", "/api/analytics/top-artifacts", {"params": {"limit": 20}}),
        ]

        for method, endpoint, *rest in endpoints:
            kwargs = rest[0] if rest else {}
            metrics = self.measure_endpoint(method, endpoint, **kwargs)
            self.results.append(metrics)

        return BenchmarkResults(
            base_url=self.base_url,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            endpoints=self.results,
            sla_violations=self.sla_violations,
        )

    def print_results(self, results: BenchmarkResults):
        """Print benchmark results in a formatted table.

        Args:
            results: BenchmarkResults to display
        """
        print("\n" + "=" * 100)
        print("API Benchmark Results (milliseconds)")
        print("=" * 100)
        print(
            f"{'Endpoint':<45} {'Mean':>8} {'Median':>8} {'P95':>8} {'P99':>8} {'Success':>8}"
        )
        print("-" * 100)

        for metrics in results.endpoints:
            endpoint_display = f"{metrics.method} {metrics.endpoint}"
            if len(endpoint_display) > 44:
                endpoint_display = endpoint_display[:41] + "..."

            print(
                f"{endpoint_display:<45} "
                f"{metrics.mean:>7.1f}  "
                f"{metrics.median:>7.1f}  "
                f"{metrics.p95:>7.1f}  "
                f"{metrics.p99:>7.1f}  "
                f"{metrics.success_rate:>6.1f}%"
            )

        print("=" * 100)

        # Print SLA violations
        if results.sla_violations:
            print("\n⚠ SLA Violations Detected:")
            print("-" * 80)
            for violation in results.sla_violations:
                print(
                    f"  {violation['endpoint']} - {violation['metric']}: "
                    f"{violation['actual']} (target: {violation['target']})"
                )
            print()
        else:
            print("\n✓ All endpoints meet SLA targets")
            print()

    def export_json(self, results: BenchmarkResults, output_path: Optional[Path] = None):
        """Export results to JSON file.

        Args:
            results: BenchmarkResults to export
            output_path: Path to output file (default: benchmark_results.json)
        """
        if output_path is None:
            output_path = Path("benchmark_results.json")

        data = {
            "base_url": results.base_url,
            "timestamp": results.timestamp,
            "endpoints": [asdict(m) for m in results.endpoints],
            "sla_violations": results.sla_violations,
        }

        output_path.write_text(json.dumps(data, indent=2))
        print(f"Results exported to: {output_path}")


def main():
    """Main entry point for benchmark script."""
    parser = argparse.ArgumentParser(
        description="Benchmark SkillMeat API endpoints",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL of the API server",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=100,
        help="Number of requests per endpoint",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSON file path",
    )
    parser.add_argument(
        "--check-server",
        action="store_true",
        help="Check if server is running before benchmarking",
    )

    args = parser.parse_args()

    # Check if server is running
    if args.check_server:
        print(f"Checking if server is available at {args.url}...")
        try:
            response = requests.get(f"{args.url}/health", timeout=5)
            if response.status_code != 200:
                print(f"Error: Server returned status {response.status_code}")
                sys.exit(1)
            print("✓ Server is running")
        except requests.RequestException as e:
            print(f"Error: Cannot connect to server - {e}")
            print("\nTo start the server, run:")
            print("  python -m skillmeat.api.server")
            sys.exit(1)

    # Run benchmarks
    benchmark = APIBenchmark(base_url=args.url, samples=args.samples)
    results = benchmark.run_all_benchmarks()
    benchmark.print_results(results)

    # Export results
    if args.output:
        benchmark.export_json(results, args.output)

    # Exit with error code if there are SLA violations
    if results.sla_violations:
        sys.exit(1)


if __name__ == "__main__":
    main()
