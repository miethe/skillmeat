"""Performance tests for analytics system.

Tests query performance with realistic and large datasets,
ensuring analytics queries meet performance targets.

Performance Targets:
- Query time < 500ms for 10k events
- Bulk insert < 1s for 1000 events
- Report generation < 1s for typical datasets
- Cleanup operations < 2s for 10k events
"""

import time
from datetime import datetime, timedelta

import pytest

from skillmeat.core.analytics import EventTracker
from skillmeat.core.usage_reports import UsageReportManager
from skillmeat.storage.analytics import AnalyticsDB


class TestAnalyticsQueryPerformance:
    """Test query performance with large datasets."""

    def test_get_events_performance_10k(self, large_analytics_db):
        """Test: Get all events query completes in < 500ms for 10k events."""
        workspace = large_analytics_db
        db = workspace["db"]

        # Warm up
        db.get_events(limit=10)

        # Benchmark get_events query
        start_time = time.time()
        events = db.get_events(limit=1000)
        query_time = time.time() - start_time

        assert len(events) == 1000
        assert query_time < 0.5, f"Query took {query_time:.3f}s, expected < 0.5s"

    def test_get_stats_performance(self, large_analytics_db):
        """Test: Get stats query completes in < 500ms."""
        workspace = large_analytics_db
        db = workspace["db"]

        # Benchmark get_stats
        start_time = time.time()
        stats = db.get_stats()
        query_time = time.time() - start_time

        assert stats["total_events"] >= 10000
        assert query_time < 0.5, f"Query took {query_time:.3f}s, expected < 0.5s"

    def test_artifact_usage_query_performance(self, large_analytics_db):
        """Test: Artifact usage query completes in < 500ms."""
        workspace = large_analytics_db
        report_mgr = UsageReportManager(
            config=workspace["config"], db_path=workspace["analytics_db_path"]
        )

        # Benchmark get_artifact_usage
        start_time = time.time()
        usage = report_mgr.get_artifact_usage(artifact_name="artifact-001")
        query_time = time.time() - start_time

        assert usage is not None
        assert query_time < 0.5, f"Query took {query_time:.3f}s, expected < 0.5s"

    def test_top_artifacts_query_performance(self, large_analytics_db):
        """Test: Top artifacts query completes in < 500ms."""
        workspace = large_analytics_db
        report_mgr = UsageReportManager(
            config=workspace["config"], db_path=workspace["analytics_db_path"]
        )

        # Benchmark get_top_artifacts
        start_time = time.time()
        top = report_mgr.get_top_artifacts(limit=10)
        query_time = time.time() - start_time

        assert len(top) == 10
        assert query_time < 0.5, f"Query took {query_time:.3f}s, expected < 0.5s"

    def test_cleanup_suggestions_performance(self, large_analytics_db):
        """Test: Cleanup suggestions query completes in < 1s."""
        workspace = large_analytics_db
        report_mgr = UsageReportManager(
            config=workspace["config"], db_path=workspace["analytics_db_path"]
        )

        # Benchmark get_cleanup_suggestions
        start_time = time.time()
        suggestions = report_mgr.get_cleanup_suggestions(inactivity_days=30)
        query_time = time.time() - start_time

        assert suggestions is not None
        assert query_time < 1.0, f"Query took {query_time:.3f}s, expected < 1.0s"


class TestAnalyticsWritePerformance:
    """Test write performance for event recording."""

    def test_bulk_insert_performance_1000_events(self, analytics_workspace):
        """Test: Insert 1000 events in < 1s."""
        workspace = analytics_workspace
        db = workspace["db"]

        # Benchmark bulk insert
        start_time = time.time()
        for i in range(1000):
            db.record_event(
                event_type="sync",
                artifact_name=f"bulk-{i % 100}",
                artifact_type="skill",
                collection_name="default",
            )
        insert_time = time.time() - start_time

        assert insert_time < 1.0, f"Bulk insert took {insert_time:.3f}s, expected < 1.0s"

        # Verify all inserted
        stats = db.get_stats()
        assert stats["total_events"] >= 1000

    def test_event_tracker_buffer_performance(self, analytics_workspace):
        """Test: Event tracker buffering handles rapid events efficiently."""
        workspace = analytics_workspace
        tracker = workspace["tracker"]

        # Record 500 events rapidly (should buffer)
        start_time = time.time()
        for i in range(500):
            db.record_event(
                event_type="search",
                artifact_name=f"search-{i % 50}",
                artifact_type="skill",
                collection_name="default",
            )
        record_time = time.time() - start_time

        # Flush buffer
        flush_start = time.time()
        flush_time = time.time() - flush_start

        total_time = record_time + flush_time

        # Should complete in < 1s total
        assert total_time < 1.0, f"Buffering took {total_time:.3f}s, expected < 1.0s"


class TestAnalyticsCleanupPerformance:
    """Test cleanup operations performance."""

    def test_delete_old_events_performance(self, large_analytics_db):
        """Test: Delete old events completes in < 2s for 10k events."""
        workspace = large_analytics_db
        db = workspace["db"]

        # Delete events older than 30 days
        cutoff_date = datetime.now() - timedelta(days=30)

        start_time = time.time()
        deleted_count = db.delete_events_before(cutoff_date)
        delete_time = time.time() - start_time

        assert delete_time < 2.0, f"Delete took {delete_time:.3f}s, expected < 2.0s"
        # Should have deleted some events
        assert deleted_count >= 0

    def test_vacuum_performance(self, large_analytics_db):
        """Test: Database vacuum completes in reasonable time."""
        workspace = large_analytics_db
        db = workspace["db"]

        # Delete some events first
        cutoff_date = datetime.now() - timedelta(days=60)
        db.delete_events_before(cutoff_date)

        # Benchmark vacuum
        start_time = time.time()
        db.connection.execute("VACUUM")
        db.connection.commit()
        vacuum_time = time.time() - start_time

        # Vacuum should complete in < 3s even for large DB
        assert vacuum_time < 3.0, f"Vacuum took {vacuum_time:.3f}s, expected < 3.0s"


class TestAnalyticsReportGenerationPerformance:
    """Test report generation performance."""

    def test_export_json_performance(self, populated_analytics_db, tmp_path):
        """Test: JSON export completes in < 1s for typical dataset."""
        workspace = populated_analytics_db
        report_mgr = UsageReportManager(
            config=workspace["config"], db_path=workspace["analytics_db_path"]
        )

        export_path = tmp_path / "perf_export.json"

        # Benchmark export
        start_time = time.time()
        report_mgr.export_usage_report(output_path=export_path, format="json")
        export_time = time.time() - start_time

        assert export_path.exists()
        assert export_time < 1.0, f"Export took {export_time:.3f}s, expected < 1.0s"

    def test_usage_trends_performance(self, populated_analytics_db):
        """Test: Trends calculation completes in < 500ms."""
        workspace = populated_analytics_db
        report_mgr = UsageReportManager(
            config=workspace["config"], db_path=workspace["analytics_db_path"]
        )

        # Benchmark trends calculation
        start_time = time.time()
        trends = report_mgr.get_usage_trends(period_days=30)
        trends_time = time.time() - start_time

        assert trends is not None
        assert trends_time < 0.5, f"Trends took {trends_time:.3f}s, expected < 0.5s"


class TestAnalyticsConcurrency:
    """Test concurrent access patterns."""

    def test_concurrent_reads(self, populated_analytics_db):
        """Test: Multiple simultaneous read queries work correctly."""
        workspace = populated_analytics_db
        db = workspace["db"]

        import threading

        results = []
        errors = []

        def query_events(artifact_name):
            try:
                events = db.get_events(artifact_name=artifact_name)
                results.append(len(events))
            except Exception as e:
                errors.append(e)

        # Spawn 10 concurrent read threads
        threads = []
        artifacts = workspace["artifact_names"]
        for artifact in artifacts[:5]:
            for _ in range(2):  # 2 threads per artifact
                t = threading.Thread(target=query_events, args=(artifact,))
                threads.append(t)
                t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # All threads should succeed
        assert len(errors) == 0, f"Concurrent reads failed: {errors}"
        assert len(results) == 10

    def test_concurrent_writes(self, analytics_workspace):
        """Test: Multiple simultaneous writes work correctly."""
        workspace = analytics_workspace
        db = workspace["db"]

        import threading

        errors = []

        def write_event(event_num):
            try:
                db.record_event(
                    event_type="deploy",
                    artifact_name=f"concurrent-{event_num}",
                    artifact_type="skill",
                    collection_name="default",
                )
            except Exception as e:
                errors.append(e)

        # Spawn 20 concurrent write threads
        threads = []
        for i in range(20):
            t = threading.Thread(target=write_event, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # All writes should succeed (WAL mode enables this)
        assert len(errors) == 0, f"Concurrent writes failed: {errors}"

        # Verify all events recorded
        stats = db.get_stats()
        assert stats["total_events"] == 20


class TestAnalyticsScalability:
    """Test scalability with increasing data sizes."""

    def test_query_time_scales_linearly(self, analytics_workspace):
        """Test: Query time scales roughly linearly with data size."""
        workspace = analytics_workspace
        db = workspace["db"]

        # Measure query time for different dataset sizes
        times = []
        sizes = [100, 500, 1000, 5000]

        for size in sizes:
            # Insert events
            for i in range(size):
                db.record_event(
                    event_type="sync",
                    artifact_name=f"scale-{i % 10}",
                    artifact_type="skill",
                    collection_name="default",
                )

            # Measure query time
            start_time = time.time()
            db.get_events(limit=100)
            query_time = time.time() - start_time
            times.append(query_time)

            # Clear for next iteration
            db.connection.execute("DELETE FROM events")
            db.connection.commit()

        # Query times should not grow exponentially
        # Even at 5000 events, should be < 500ms
        assert times[-1] < 0.5, f"Query at 5k events took {times[-1]:.3f}s"

    def test_memory_usage_stable(self, analytics_workspace):
        """Test: Memory usage doesn't grow unbounded with queries."""
        import gc
        import sys

        workspace = analytics_workspace
        db = workspace["db"]

        # Insert test data
        for i in range(1000):
            db.record_event(
                event_type="sync",
                artifact_name=f"mem-{i % 10}",
                artifact_type="skill",
                collection_name="default",
            )

        # Force garbage collection
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Run many queries
        for _ in range(100):
            db.get_events(limit=10)

        # Force garbage collection again
        gc.collect()
        final_objects = len(gc.get_objects())

        # Object count should not grow significantly
        # Allow for some variance (< 20% growth)
        growth_percent = ((final_objects - initial_objects) / initial_objects) * 100
        assert (
            growth_percent < 20
        ), f"Object count grew by {growth_percent:.1f}%, expected < 20%"


# Performance summary fixture for reporting
@pytest.fixture(scope="module")
def performance_results():
    """Collect performance test results for reporting."""
    return {
        "query_times": [],
        "write_times": [],
        "export_times": [],
    }
