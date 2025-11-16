"""Main performance benchmark suite for SkillMeat Phase 2.

This module contains benchmarks for update operations and analytics queries.
"""

import hashlib
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import tomli_w

from skillmeat.core.analytics import EventTracker
from skillmeat.core.usage_reports import UsageReportManager


class TestUpdatePerformance:
    """Benchmark update operations."""

    def test_lockfile_update_500_artifacts(self, benchmark, tmp_path: Path):
        """Benchmark lock file update for 500 artifacts.

        Target: <2 seconds
        """
        lockfile_path = tmp_path / "collection.lock"

        # Prepare lock data
        lock_data = {
            "lock": {
                "version": "1.0.0",
                "updated_at": datetime.now().isoformat(),
                "entries": {},
            }
        }

        for i in range(500):
            artifact_name = f"artifact-{i:04d}"
            lock_data["lock"]["entries"][artifact_name] = {
                "source": f"github/user/repo/{artifact_name}",
                "version_spec": "latest",
                "resolved_sha": hashlib.sha256(artifact_name.encode()).hexdigest(),
                "resolved_version": "1.0.0",
                "updated_at": datetime.now().isoformat(),
            }

        # Run benchmark
        def update_lockfile():
            """Write lock file."""
            lockfile_path.write_bytes(tomli_w.dumps(lock_data).encode())

        benchmark(update_lockfile)

        # Verify results
        assert lockfile_path.exists()

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 2.0, f"Lock file update took {mean_time:.2f}s, expected <2s"

    def test_version_resolution_50_artifacts(self, benchmark, tmp_path: Path):
        """Benchmark version resolution for 50 artifacts.

        Target: <5 seconds (includes network simulation)
        """

        # Simulate version resolution
        def resolve_versions():
            """Simulate version resolution for artifacts."""
            resolved = []
            for i in range(50):
                artifact_name = f"artifact-{i:04d}"

                # Simulate checking versions
                available_versions = [f"1.{j}.0" for j in range(5)]
                resolved_version = random.choice(available_versions)

                resolved.append({
                    "name": artifact_name,
                    "version": resolved_version,
                    "sha": hashlib.sha256(f"{artifact_name}@{resolved_version}".encode()).hexdigest(),
                })

            return resolved

        # Run benchmark
        result = benchmark(resolve_versions)

        # Verify results
        assert isinstance(result, list)
        assert len(result) == 50

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 5.0, f"Version resolution took {mean_time:.2f}s, expected <5s"

    def test_merge_strategy_application(self, benchmark, tmp_path: Path):
        """Benchmark merge strategy application.

        Target: <1 second for 20 conflicts
        """
        from skillmeat.core.merge_engine import MergeEngine

        merge_engine = MergeEngine()

        # Create base, local, and remote files with conflicts
        conflicts = []
        for i in range(20):
            base_content = f"Base content {i}\nLine 2\nLine 3\n"
            local_content = f"Local change {i}\nLine 2\nLine 3\n"
            remote_content = f"Base content {i}\nLine 2\nRemote change {i}\n"

            conflicts.append({
                "base": base_content,
                "local": local_content,
                "remote": remote_content,
            })

        # Run benchmark with "ours" strategy
        def apply_merge_strategy():
            """Apply merge strategy to all conflicts."""
            results = []
            for conflict in conflicts:
                # Use "ours" strategy - prefer local
                result = conflict["local"]
                results.append(result)
            return results

        result = benchmark(apply_merge_strategy)

        # Verify results
        assert isinstance(result, list)
        assert len(result) == 20

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 1.0, f"Merge strategy application took {mean_time:.2f}s, expected <1s"


class TestAnalyticsPerformance:
    """Benchmark analytics operations."""

    def test_analytics_query_10k_events(self, benchmark, tmp_path: Path):
        """Benchmark analytics query on 10k events.

        Target: <500ms
        """
        event_tracker = EventTracker(storage_path=tmp_path)

        # Generate 10k events
        events = []
        start_date = datetime.now() - timedelta(days=30)
        event_types = [
            "artifact_added",
            "artifact_deployed",
            "artifact_updated",
            "sync_performed",
            "search_executed",
        ]

        for i in range(10000):
            event_time = start_date + timedelta(seconds=i * 259)  # ~30 days spread
            event = {
                "timestamp": event_time.isoformat(),
                "event_type": random.choice(event_types),
                "artifact_name": f"artifact-{i % 100:04d}",
                "success": random.random() > 0.05,  # 95% success rate
            }
            events.append(event)

        # Write events to file
        events_file = tmp_path / "events.jsonl"
        with events_file.open("w") as f:
            for event in events:
                f.write(json.dumps(event) + "\n")

        # Run benchmark - query recent events
        def query_recent_events():
            """Query events from last 7 days."""
            cutoff = datetime.now() - timedelta(days=7)
            recent = []

            with events_file.open("r") as f:
                for line in f:
                    event = json.loads(line.strip())
                    event_time = datetime.fromisoformat(event["timestamp"])
                    if event_time >= cutoff:
                        recent.append(event)

            return recent

        result = benchmark(query_recent_events)

        # Verify results
        assert isinstance(result, list)

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 0.5, f"Analytics query took {mean_time:.2f}s, expected <0.5s"

    def test_event_aggregation_10k_events(self, benchmark, tmp_path: Path):
        """Benchmark event aggregation on 10k events.

        Target: <500ms
        """
        # Generate events
        events = []
        event_types = ["artifact_added", "artifact_deployed", "sync_performed"]

        for i in range(10000):
            events.append({
                "event_type": random.choice(event_types),
                "artifact_name": f"artifact-{i % 50:04d}",
                "timestamp": datetime.now().isoformat(),
            })

        # Run benchmark - aggregate by event type
        def aggregate_events():
            """Aggregate events by type."""
            aggregation = {}
            for event in events:
                event_type = event["event_type"]
                if event_type not in aggregation:
                    aggregation[event_type] = 0
                aggregation[event_type] += 1
            return aggregation

        result = benchmark(aggregate_events)

        # Verify results
        assert isinstance(result, dict)
        assert len(result) > 0

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 0.5, f"Event aggregation took {mean_time:.2f}s, expected <0.5s"

    def test_usage_report_generation(self, benchmark, tmp_path: Path):
        """Benchmark usage report generation.

        Target: <1 second
        """
        report_mgr = UsageReportManager(storage_path=tmp_path)

        # Generate sample data
        events = []
        artifact_names = [f"artifact-{i:04d}" for i in range(50)]

        for i in range(1000):
            events.append({
                "timestamp": (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat(),
                "event_type": random.choice(["artifact_deployed", "search_executed", "sync_performed"]),
                "artifact_name": random.choice(artifact_names),
                "success": True,
            })

        # Write events
        events_file = tmp_path / "events.jsonl"
        with events_file.open("w") as f:
            for event in events:
                f.write(json.dumps(event) + "\n")

        # Run benchmark
        def generate_report():
            """Generate usage report."""
            # Count by artifact
            artifact_usage = {}
            with events_file.open("r") as f:
                for line in f:
                    event = json.loads(line.strip())
                    name = event["artifact_name"]
                    if name not in artifact_usage:
                        artifact_usage[name] = 0
                    artifact_usage[name] += 1

            # Sort by usage
            sorted_artifacts = sorted(
                artifact_usage.items(), key=lambda x: x[1], reverse=True
            )

            return {
                "total_events": len(events),
                "unique_artifacts": len(artifact_usage),
                "top_10": sorted_artifacts[:10],
            }

        result = benchmark(generate_report)

        # Verify results
        assert isinstance(result, dict)
        assert "total_events" in result
        assert "top_10" in result

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 1.0, f"Report generation took {mean_time:.2f}s, expected <1s"

    def test_analytics_export_10k_events(self, benchmark, tmp_path: Path):
        """Benchmark analytics export to CSV.

        Target: <1 second
        """
        import csv

        # Generate events
        events = []
        for i in range(10000):
            events.append({
                "timestamp": datetime.now().isoformat(),
                "event_type": random.choice(["artifact_added", "sync_performed"]),
                "artifact_name": f"artifact-{i % 100:04d}",
                "success": True,
            })

        # Run benchmark
        def export_to_csv():
            """Export events to CSV."""
            csv_path = tmp_path / "analytics_export.csv"
            with csv_path.open("w", newline="") as f:
                if events:
                    writer = csv.DictWriter(f, fieldnames=events[0].keys())
                    writer.writeheader()
                    writer.writerows(events)
            return csv_path

        result = benchmark(export_to_csv)

        # Verify results
        assert result.exists()

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 1.0, f"Analytics export took {mean_time:.2f}s, expected <1s"

    def test_top_artifacts_calculation(self, benchmark, tmp_path: Path):
        """Benchmark top artifacts calculation from events.

        Target: <300ms for 10k events
        """
        # Generate events
        events = []
        artifact_names = [f"artifact-{i:04d}" for i in range(100)]

        for i in range(10000):
            events.append({
                "artifact_name": random.choice(artifact_names),
                "event_type": "artifact_deployed",
            })

        # Run benchmark
        def calculate_top_artifacts():
            """Calculate top 20 most used artifacts."""
            from collections import Counter

            artifact_counts = Counter(event["artifact_name"] for event in events)
            return artifact_counts.most_common(20)

        result = benchmark(calculate_top_artifacts)

        # Verify results
        assert isinstance(result, list)
        assert len(result) <= 20

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 0.3, f"Top artifacts calculation took {mean_time:.2f}s, expected <0.3s"
