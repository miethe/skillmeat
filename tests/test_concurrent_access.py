"""Tests for concurrent cache access and thread safety.

Verifies that the cache system handles:
- Multiple concurrent readers
- Multiple concurrent writers
- Mixed read/write operations
- CLI + web simultaneous access
- Database-level locking and WAL mode
- Transaction isolation
"""

from __future__ import annotations

import concurrent.futures
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pytest

from skillmeat.cache.manager import CacheManager


class TestConcurrentAccess:
    """Test suite for concurrent cache operations."""

    # =========================================================================
    # Fixtures
    # =========================================================================

    @pytest.fixture
    def cache_manager(self, temp_home):
        """Create a CacheManager with isolated database.

        Args:
            temp_home: Pytest fixture providing temporary home directory

        Returns:
            CacheManager: Initialized cache manager instance
        """
        db_path = temp_home / ".skillmeat" / "cache" / "cache.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        manager = CacheManager(db_path=str(db_path), ttl_minutes=360)
        manager.initialize_cache()

        yield manager

        # Cleanup
        if db_path.exists():
            db_path.unlink()

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _create_test_projects(self, count: int, prefix: str) -> List[Dict[str, Any]]:
        """Helper to create test project data.

        Args:
            count: Number of projects to create
            prefix: Prefix for project IDs to ensure uniqueness

        Returns:
            List of project dictionaries ready for populate_projects()
        """
        projects = []
        for i in range(count):
            projects.append(
                {
                    "id": f"{prefix}-proj-{i}",
                    "name": f"Project {prefix}-{i}",
                    "path": f"/test/{prefix}/{i}",
                    "description": f"Test project {prefix}-{i}",
                    "artifacts": [
                        {
                            "id": f"{prefix}-art-{i}-{j}",
                            "name": f"artifact-{j}",
                            "type": "skill",
                            "deployed_version": "1.0.0",
                            "upstream_version": "1.0.0",
                        }
                        for j in range(10)  # 10 artifacts per project
                    ],
                }
            )
        return projects

    def _verify_data_integrity(
        self, manager: CacheManager, expected_min_count: int = 0
    ) -> None:
        """Helper to verify cache data integrity.

        Args:
            manager: CacheManager instance to verify
            expected_min_count: Minimum expected number of projects

        Raises:
            AssertionError: If data integrity checks fail
        """
        projects = manager.get_projects()

        if expected_min_count > 0:
            assert (
                len(projects) >= expected_min_count
            ), f"Expected at least {expected_min_count} projects, got {len(projects)}"

        # Verify no duplicate IDs
        project_ids = [p.id for p in projects]
        assert len(project_ids) == len(set(project_ids)), "Found duplicate project IDs"

        # Verify artifacts loaded correctly
        for project in projects:
            artifact_ids = [a.id for a in project.artifacts]
            assert len(artifact_ids) == len(
                set(artifact_ids)
            ), f"Found duplicate artifact IDs in project {project.id}"

    # =========================================================================
    # Test Cases
    # =========================================================================

    def test_concurrent_reads_no_deadlock(self, cache_manager):
        """Verify multiple readers don't deadlock.

        Spawns 10 threads all reading simultaneously, each performing
        100 read operations. Verifies all operations complete within
        timeout with no exceptions.
        """
        # Populate with initial data
        projects = self._create_test_projects(10, "initial")
        cache_manager.populate_projects(projects)

        errors = []

        def reader_worker(thread_id: int) -> None:
            """Worker function that performs multiple reads.

            Args:
                thread_id: Unique identifier for this thread
            """
            try:
                for i in range(100):
                    result = cache_manager.get_projects()
                    if len(result) != 10:
                        errors.append(
                            f"Thread {thread_id} iteration {i}: "
                            f"Expected 10 projects, got {len(result)}"
                        )
            except Exception as e:
                errors.append(f"Thread {thread_id} error: {e}")

        # Use ThreadPoolExecutor for cleaner thread management
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(reader_worker, i) for i in range(10)]

            # Wait for all to complete with timeout
            done, not_done = concurrent.futures.wait(
                futures, timeout=10, return_when=concurrent.futures.ALL_COMPLETED
            )

            # Verify all completed
            assert len(not_done) == 0, f"Timeout: {len(not_done)} threads didn't finish"

        # Verify no errors occurred
        assert len(errors) == 0, f"Reader errors: {errors}"

        # Verify data integrity
        self._verify_data_integrity(cache_manager, expected_min_count=10)

    def test_concurrent_writes_no_corruption(self, cache_manager):
        """Verify concurrent writes don't corrupt data.

        Spawns 5 threads, each writing 10 different projects.
        Verifies all 50 projects are saved correctly with no
        duplicate IDs or missing data.
        """
        errors = []

        def writer_worker(thread_id: int) -> None:
            """Worker function that performs multiple writes.

            Args:
                thread_id: Unique identifier for this thread
            """
            try:
                projects = self._create_test_projects(10, f"thread{thread_id}")
                count = cache_manager.populate_projects(projects)
                if count != 10:
                    errors.append(
                        f"Thread {thread_id}: Expected to write 10 projects, wrote {count}"
                    )
            except Exception as e:
                errors.append(f"Thread {thread_id} error: {e}")

        # Launch 5 writer threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(writer_worker, i) for i in range(5)]

            # Wait for all to complete with timeout
            done, not_done = concurrent.futures.wait(
                futures, timeout=10, return_when=concurrent.futures.ALL_COMPLETED
            )

            # Verify all completed
            assert len(not_done) == 0, f"Timeout: {len(not_done)} threads didn't finish"

        # Verify no errors occurred
        assert len(errors) == 0, f"Writer errors: {errors}"

        # Verify all 50 projects saved correctly
        self._verify_data_integrity(cache_manager, expected_min_count=50)

        projects = cache_manager.get_projects()
        assert len(projects) == 50, f"Expected exactly 50 projects, got {len(projects)}"

    def test_concurrent_read_write(self, cache_manager):
        """Verify readers and writers can operate simultaneously.

        Runs a mix of 5 reader threads and 5 writer threads
        concurrently for 5 seconds. Verifies no exceptions occur
        and data integrity is maintained.
        """
        # Populate initial data
        initial_projects = self._create_test_projects(5, "initial")
        cache_manager.populate_projects(initial_projects)

        errors = []
        stop_event = threading.Event()
        write_counter = {"count": 0, "iteration": 0}
        lock = threading.Lock()

        def reader_worker(thread_id: int) -> None:
            """Continuously read while stop_event is not set.

            Args:
                thread_id: Unique identifier for this thread
            """
            try:
                while not stop_event.is_set():
                    projects = cache_manager.get_projects()
                    # Just verify we got some data
                    if len(projects) < 5:
                        errors.append(
                            f"Reader {thread_id}: Expected at least 5 projects, "
                            f"got {len(projects)}"
                        )
                    time.sleep(0.01)  # Small delay to avoid tight loop
            except Exception as e:
                errors.append(f"Reader {thread_id} error: {e}")

        def writer_worker(thread_id: int) -> None:
            """Continuously write while stop_event is not set.

            Args:
                thread_id: Unique identifier for this thread
            """
            try:
                while not stop_event.is_set():
                    # Get unique iteration counter
                    with lock:
                        iteration = write_counter["iteration"]
                        write_counter["iteration"] += 1

                    # Use unique IDs for each write
                    projects = self._create_test_projects(
                        2, f"writer{thread_id}-iter{iteration}"
                    )
                    count = cache_manager.populate_projects(projects)
                    if count != 2:
                        errors.append(
                            f"Writer {thread_id} iteration {iteration}: "
                            f"Expected to write 2 projects, wrote {count}"
                        )
                    with lock:
                        write_counter["count"] += count
                    time.sleep(0.02)  # Small delay between writes
            except Exception as e:
                errors.append(f"Writer {thread_id} error: {e}")

        # Launch readers and writers
        threads = []
        for i in range(5):
            threads.append(threading.Thread(target=reader_worker, args=(i,)))
            threads.append(threading.Thread(target=writer_worker, args=(i,)))

        for t in threads:
            t.start()

        # Run for 5 seconds
        time.sleep(5)
        stop_event.set()

        # Wait for all threads to complete
        for t in threads:
            t.join(timeout=2)

        # Verify no errors occurred
        assert len(errors) == 0, f"Concurrent read/write errors: {errors}"

        # Verify data integrity
        self._verify_data_integrity(cache_manager)

        # Verify we have at least the initial projects plus some written projects
        # Note: get_projects() has default limit of 100, so we expect either
        # the full count or 100 (whichever is smaller)
        all_projects = cache_manager.repository.list_projects(limit=1000)
        total_count = len(all_projects)
        expected_count = 5 + write_counter["count"]
        assert (
            total_count == expected_count
        ), f"Expected {expected_count} projects, got {total_count}"

        # Verify pagination works (default limit is 100)
        default_page = cache_manager.get_projects()
        assert len(default_page) <= 100, "Default pagination should limit to 100"

    def test_cli_web_simultaneous_access(self, cache_manager):
        """Simulate CLI and web accessing cache simultaneously.

        One thread simulates CLI operations (list, add, invalidate).
        Another simulates web operations (status, search).
        Verifies no conflicts occur.
        """
        errors = []
        stop_event = threading.Event()

        def cli_simulator() -> None:
            """Simulate CLI operations."""
            try:
                iteration = 0
                while not stop_event.is_set():
                    # List operation
                    cache_manager.get_projects()

                    # Add operation
                    projects = self._create_test_projects(1, f"cli-{iteration}")
                    cache_manager.populate_projects(projects)

                    # Invalidate operation (occasionally)
                    if iteration % 5 == 0:
                        cache_manager.invalidate_cache()

                    iteration += 1
                    time.sleep(0.1)
            except Exception as e:
                errors.append(f"CLI simulator error: {e}")

        def web_simulator() -> None:
            """Simulate web operations."""
            try:
                while not stop_event.is_set():
                    # Status check
                    status = cache_manager.get_cache_status()
                    if not isinstance(status, dict):
                        errors.append(f"Invalid status response: {type(status)}")

                    # List projects
                    cache_manager.get_projects()

                    # Search (via get_artifacts)
                    projects = cache_manager.get_projects()
                    if projects:
                        cache_manager.get_artifacts(projects[0].id)

                    time.sleep(0.05)
            except Exception as e:
                errors.append(f"Web simulator error: {e}")

        # Start both simulators
        cli_thread = threading.Thread(target=cli_simulator)
        web_thread = threading.Thread(target=web_simulator)

        cli_thread.start()
        web_thread.start()

        # Run for 5 seconds
        time.sleep(5)
        stop_event.set()

        # Wait for threads to complete
        cli_thread.join(timeout=2)
        web_thread.join(timeout=2)

        # Verify no errors occurred
        assert len(errors) == 0, f"CLI/Web simulation errors: {errors}"

        # Verify data integrity
        self._verify_data_integrity(cache_manager)

    def test_transaction_isolation(self, cache_manager):
        """Verify transaction isolation between operations.

        Starts a write operation in one thread. While write is in
        progress, verifies reads in another thread see consistent state
        (either old or new state, but not partial writes).

        Note: This test verifies that readers don't crash during writes,
        but SQLite's isolation level means readers may see intermediate
        states during a transaction. This is expected behavior.
        """
        errors = []

        # Populate initial data
        initial_projects = self._create_test_projects(5, "initial")
        cache_manager.populate_projects(initial_projects)

        write_started = threading.Event()
        write_completed = threading.Event()

        def writer() -> None:
            """Perform a large write operation."""
            try:
                write_started.set()
                # Write a large batch of projects with unique IDs
                projects = self._create_test_projects(100, "batch")
                cache_manager.populate_projects(projects)
                write_completed.set()
            except Exception as e:
                errors.append(f"Writer error: {e}")
                write_completed.set()

        def reader() -> None:
            """Read while write is in progress."""
            try:
                # Wait for write to start
                write_started.wait(timeout=2)

                # Read multiple times while write is happening
                for i in range(10):
                    projects = cache_manager.get_projects()
                    count = len(projects)

                    # Verify we get some data (at least initial 5)
                    if count < 5:
                        errors.append(
                            f"Reader iteration {i}: "
                            f"Got fewer than initial projects: {count}"
                        )

                    time.sleep(0.01)
            except Exception as e:
                errors.append(f"Reader error: {e}")

        # Start writer and reader
        writer_thread = threading.Thread(target=writer)
        reader_thread = threading.Thread(target=reader)

        writer_thread.start()
        reader_thread.start()

        # Wait for both to complete
        writer_thread.join(timeout=5)
        reader_thread.join(timeout=5)

        # Verify no errors occurred
        assert len(errors) == 0, f"Transaction isolation errors: {errors}"

        # Verify final state has all projects (use high limit to get all)
        all_projects = cache_manager.repository.list_projects(limit=200)
        final_count = len(all_projects)
        assert final_count == 105, f"Expected 105 projects, got {final_count}"

    def test_database_lock_behavior(self, temp_home):
        """Test SQLite locking under concurrent access.

        Creates multiple CacheManager instances (simulating different
        processes) all writing to the same database. Verifies WAL mode
        handles contention gracefully with no "database is locked" errors.
        """
        db_path = temp_home / ".skillmeat" / "cache" / "concurrent.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database with first manager
        manager1 = CacheManager(db_path=str(db_path), ttl_minutes=360)
        manager1.initialize_cache()

        errors = []

        def worker_with_own_manager(thread_id: int) -> None:
            """Worker that creates its own CacheManager instance.

            Args:
                thread_id: Unique identifier for this thread
            """
            try:
                # Each thread gets its own CacheManager instance
                manager = CacheManager(db_path=str(db_path), ttl_minutes=360)

                # Perform multiple writes
                for i in range(10):
                    projects = self._create_test_projects(
                        5, f"worker{thread_id}-batch{i}"
                    )
                    count = manager.populate_projects(projects)
                    if count != 5:
                        errors.append(
                            f"Worker {thread_id} batch {i}: "
                            f"Expected to write 5 projects, wrote {count}"
                        )
                    time.sleep(0.01)  # Small delay between writes
            except Exception as e:
                errors.append(f"Worker {thread_id} error: {e}")

        # Launch multiple workers, each with own manager instance
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker_with_own_manager, i) for i in range(5)]

            # Wait for all to complete
            done, not_done = concurrent.futures.wait(
                futures, timeout=15, return_when=concurrent.futures.ALL_COMPLETED
            )

            # Verify all completed
            assert len(not_done) == 0, f"Timeout: {len(not_done)} workers didn't finish"

        # Verify no errors occurred (especially no "database is locked" errors)
        assert len(errors) == 0, f"Database lock errors: {errors}"

        # Verify final data integrity using a fresh manager
        final_manager = CacheManager(db_path=str(db_path), ttl_minutes=360)

        # Verify we have the expected number of projects (5 workers * 10 batches * 5 projects)
        # Use high limit to get all projects (default is 100)
        all_projects = final_manager.repository.list_projects(limit=300)
        final_count = len(all_projects)
        expected = 5 * 10 * 5
        assert (
            final_count == expected
        ), f"Expected {expected} projects, got {final_count}"

        # Verify data integrity on a subset
        self._verify_data_integrity(final_manager, expected_min_count=0)

        # Cleanup
        if db_path.exists():
            db_path.unlink()
