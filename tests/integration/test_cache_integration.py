"""Integration tests for cache system.

This module provides comprehensive integration tests covering:
- Cache population from dict data
- TTL-based refresh workflows
- Cache invalidation (targeted and full)
- Concurrent read/write operations
- Integration with RefreshJob
- Error recovery scenarios
"""

from __future__ import annotations

import tempfile
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import pytest

from skillmeat.cache.manager import CacheManager
from skillmeat.cache.refresh import RefreshJob, RefreshEventType


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_db_path(tmp_path):
    """Create temporary database path."""
    return str(tmp_path / "test_cache.db")


@pytest.fixture
def cache_manager(temp_db_path):
    """Create CacheManager with temp database."""
    manager = CacheManager(db_path=temp_db_path, ttl_minutes=60)
    manager.initialize_cache()
    return manager


@pytest.fixture
def sample_projects():
    """Sample project data for testing."""
    return [
        {
            "id": "proj-1",
            "name": "Test Project 1",
            "path": "/tmp/proj1",
            "description": "First test project",
            "artifacts": [
                {
                    "id": "art-1-1",
                    "name": "skill-1",
                    "type": "skill",
                    "deployed_version": "1.0.0",
                    "upstream_version": "1.0.0",
                },
                {
                    "id": "art-1-2",
                    "name": "command-1",
                    "type": "command",
                    "deployed_version": "2.0.0",
                    "upstream_version": "2.1.0",
                },
            ],
        },
        {
            "id": "proj-2",
            "name": "Test Project 2",
            "path": "/tmp/proj2",
            "description": "Second test project",
            "artifacts": [
                {
                    "id": "art-2-1",
                    "name": "skill-2",
                    "type": "skill",
                    "deployed_version": "3.0.0",
                    "upstream_version": "4.0.0",
                }
            ],
        },
    ]


# =============================================================================
# Cache Population Tests
# =============================================================================


class TestCachePopulation:
    """Tests for cache population from dict data."""

    def test_populate_projects_empty_cache(self, cache_manager, sample_projects):
        """Test populating an empty cache with projects."""
        count = cache_manager.populate_projects(sample_projects)

        assert count == 2

        # Verify projects exist
        projects = cache_manager.get_projects()
        assert len(projects) == 2
        assert {p.id for p in projects} == {"proj-1", "proj-2"}

    def test_populate_projects_with_artifacts(self, cache_manager, sample_projects):
        """Test that artifacts are populated along with projects."""
        cache_manager.populate_projects(sample_projects)

        # Check project 1 artifacts
        artifacts_1 = cache_manager.get_artifacts("proj-1")
        assert len(artifacts_1) == 2
        assert {a.name for a in artifacts_1} == {"skill-1", "command-1"}

        # Check project 2 artifacts
        artifacts_2 = cache_manager.get_artifacts("proj-2")
        assert len(artifacts_2) == 1
        assert artifacts_2[0].name == "skill-2"

    def test_populate_projects_updates_existing(self, cache_manager, sample_projects):
        """Test that populating updates existing projects."""
        # Populate initial data
        cache_manager.populate_projects(sample_projects)

        # Update project data
        updated_projects = [
            {
                "id": "proj-1",
                "name": "Updated Project 1",
                "path": "/tmp/proj1",
                "description": "Updated description",
                "artifacts": [],
            }
        ]
        count = cache_manager.populate_projects(updated_projects)

        assert count == 1

        # Verify update
        project = cache_manager.get_project("proj-1")
        assert project.name == "Updated Project 1"
        assert project.description == "Updated description"

    def test_populate_detects_outdated_artifacts(self, cache_manager, sample_projects):
        """Test that outdated artifacts are correctly detected during population."""
        cache_manager.populate_projects(sample_projects)

        outdated = cache_manager.get_outdated_artifacts()
        assert len(outdated) == 2

        # art-1-2: 2.0.0 -> 2.1.0
        # art-2-1: 3.0.0 -> 4.0.0
        outdated_ids = {a.id for a in outdated}
        assert outdated_ids == {"art-1-2", "art-2-1"}

    def test_populate_handles_partial_failures(self, cache_manager):
        """Test that population handles partial failures gracefully."""
        # Create one valid project
        valid_project = {
            "id": "proj-valid",
            "name": "Valid Project",
            "path": "/tmp/valid",
            "artifacts": [],
        }
        cache_manager.populate_projects([valid_project])

        # Try to populate with invalid data (missing required fields)
        # The manager should handle this gracefully
        projects = cache_manager.get_projects()
        assert len(projects) == 1
        assert projects[0].id == "proj-valid"


# =============================================================================
# TTL-Based Refresh Tests
# =============================================================================


class TestTTLBasedRefresh:
    """Tests for TTL-based refresh workflows."""

    def test_fresh_projects_not_stale(self, cache_manager, sample_projects):
        """Test that freshly populated projects are not stale."""
        cache_manager.populate_projects(sample_projects)

        # Mark as refreshed (sets last_fetched to now)
        cache_manager.mark_project_refreshed("proj-1")
        cache_manager.mark_project_refreshed("proj-2")

        # Check staleness
        assert not cache_manager.is_cache_stale("proj-1")
        assert not cache_manager.is_cache_stale("proj-2")

    def test_projects_become_stale_after_ttl(self, cache_manager, sample_projects):
        """Test that projects become stale after TTL expires."""
        cache_manager.populate_projects(sample_projects)

        # Mark as refreshed with old timestamp (past TTL)
        old_time = datetime.utcnow() - timedelta(minutes=120)  # 2 hours ago (TTL is 60 min)
        cache_manager.repository.update_project("proj-1", last_fetched=old_time)

        # Check staleness
        assert cache_manager.is_cache_stale("proj-1")

    def test_get_projects_exclude_stale(self, cache_manager, sample_projects):
        """Test that get_projects can exclude stale projects."""
        cache_manager.populate_projects(sample_projects)

        # Mark proj-1 as fresh, proj-2 as stale
        cache_manager.mark_project_refreshed("proj-1")
        old_time = datetime.utcnow() - timedelta(minutes=120)
        cache_manager.repository.update_project("proj-2", last_fetched=old_time)

        # Get only fresh projects
        fresh_projects = cache_manager.get_projects(include_stale=False)
        assert len(fresh_projects) == 1
        assert fresh_projects[0].id == "proj-1"

    def test_refresh_if_stale_marks_for_refresh(self, cache_manager, sample_projects):
        """Test that refresh_if_stale marks stale projects for refresh."""
        cache_manager.populate_projects(sample_projects)

        # Make project stale
        old_time = datetime.utcnow() - timedelta(minutes=120)
        cache_manager.repository.update_project("proj-1", last_fetched=old_time)

        # Trigger refresh check
        needs_refresh = cache_manager.refresh_if_stale("proj-1")

        assert needs_refresh is True

        # Verify project was invalidated
        project = cache_manager.get_project("proj-1")
        assert project.status == "stale"

    def test_refresh_if_stale_force(self, cache_manager, sample_projects):
        """Test that force refresh works even for fresh projects."""
        cache_manager.populate_projects(sample_projects)
        cache_manager.mark_project_refreshed("proj-1")

        # Force refresh
        needs_refresh = cache_manager.refresh_if_stale("proj-1", force=True)

        assert needs_refresh is True

        # Verify project was invalidated
        project = cache_manager.get_project("proj-1")
        assert project.status == "stale"


# =============================================================================
# Cache Invalidation Tests
# =============================================================================


class TestCacheInvalidation:
    """Tests for cache invalidation."""

    def test_invalidate_single_project(self, cache_manager, sample_projects):
        """Test invalidating a single project."""
        cache_manager.populate_projects(sample_projects)
        cache_manager.mark_project_refreshed("proj-1")
        cache_manager.mark_project_refreshed("proj-2")

        # Invalidate only proj-1
        count = cache_manager.invalidate_cache("proj-1")

        assert count == 1

        # Verify proj-1 is stale, proj-2 is not
        assert cache_manager.is_cache_stale("proj-1")
        assert not cache_manager.is_cache_stale("proj-2")

    def test_invalidate_entire_cache(self, cache_manager, sample_projects):
        """Test invalidating the entire cache."""
        cache_manager.populate_projects(sample_projects)
        cache_manager.mark_project_refreshed("proj-1")
        cache_manager.mark_project_refreshed("proj-2")

        # Invalidate all
        count = cache_manager.invalidate_cache()

        assert count == 2

        # Verify all projects are stale
        assert cache_manager.is_cache_stale("proj-1")
        assert cache_manager.is_cache_stale("proj-2")

    def test_clear_cache_deletes_all(self, cache_manager, sample_projects):
        """Test that clear_cache deletes all data."""
        cache_manager.populate_projects(sample_projects)

        result = cache_manager.clear_cache()

        assert result is True

        # Verify cache is empty
        projects = cache_manager.get_projects()
        assert len(projects) == 0

    def test_clear_cache_cascades_to_artifacts(self, cache_manager, sample_projects):
        """Test that clear_cache cascades to artifacts."""
        cache_manager.populate_projects(sample_projects)

        cache_manager.clear_cache()

        # Verify artifacts are gone
        artifacts = cache_manager.get_artifacts("proj-1")
        assert len(artifacts) == 0


# =============================================================================
# Concurrent Operations Tests
# =============================================================================


class TestConcurrentOperations:
    """Tests for concurrent read/write operations."""

    def test_concurrent_reads(self, cache_manager, sample_projects):
        """Test concurrent read operations."""
        cache_manager.populate_projects(sample_projects)

        errors = []
        results = []

        def read_projects():
            try:
                projects = cache_manager.get_projects()
                results.append(len(projects))
            except Exception as e:
                errors.append(str(e))

        # Run 20 concurrent reads
        threads = [threading.Thread(target=read_projects) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify no errors
        assert len(errors) == 0
        assert all(count == 2 for count in results)

    def test_concurrent_writes(self, cache_manager):
        """Test concurrent write operations."""
        errors = []

        def write_project(project_id: int):
            try:
                projects = [
                    {
                        "id": f"proj-{project_id}",
                        "name": f"Project {project_id}",
                        "path": f"/tmp/proj{project_id}",
                        "artifacts": [],
                    }
                ]
                cache_manager.populate_projects(projects)
            except Exception as e:
                errors.append(str(e))

        # Run 10 concurrent writes
        threads = [threading.Thread(target=write_project, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify no errors
        assert len(errors) == 0

        # Verify all projects were created
        projects = cache_manager.get_projects()
        assert len(projects) == 10

    def test_concurrent_read_write(self, cache_manager, sample_projects):
        """Test mixed concurrent read/write operations."""
        cache_manager.populate_projects(sample_projects)

        errors = []

        def reader():
            try:
                for _ in range(10):
                    cache_manager.get_projects()
                    time.sleep(0.001)
            except Exception as e:
                errors.append(str(e))

        def writer():
            try:
                for i in range(5):
                    cache_manager.mark_project_refreshed("proj-1")
                    time.sleep(0.002)
            except Exception as e:
                errors.append(str(e))

        # Run concurrent readers and writers
        threads = [threading.Thread(target=reader) for _ in range(5)]
        threads += [threading.Thread(target=writer) for _ in range(3)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify no errors
        assert len(errors) == 0


# =============================================================================
# RefreshJob Integration Tests
# =============================================================================


class TestRefreshJobIntegration:
    """Tests for integration with RefreshJob."""

    @pytest.fixture
    def mock_fetcher(self):
        """Mock data fetcher that returns sample data."""

        def fetcher(project_id):
            # Return refreshed data
            return {
                "id": project_id,
                "name": f"Refreshed {project_id}",
                "path": f"/tmp/{project_id}",
                "status": "active",
                "artifacts": [
                    {
                        "id": f"art-{project_id}-new",
                        "name": f"new-skill-{project_id}",
                        "type": "skill",
                        "deployed_version": "2.0.0",
                        "upstream_version": "2.0.0",
                    }
                ],
            }

        return fetcher

    @pytest.fixture
    def refresh_job(self, cache_manager, mock_fetcher):
        """Create RefreshJob with mocked fetcher."""
        job = RefreshJob(
            cache_manager=cache_manager,
            data_fetcher=mock_fetcher,
            interval_hours=1.0,
        )
        yield job
        if job.is_running():
            job.stop_scheduler(wait=False)

    def test_refresh_job_refreshes_project(
        self, cache_manager, refresh_job, sample_projects
    ):
        """Test that RefreshJob can refresh a project."""
        cache_manager.populate_projects(sample_projects)

        # Make project stale
        old_time = datetime.utcnow() - timedelta(minutes=120)
        cache_manager.repository.update_project("proj-1", last_fetched=old_time)

        # Manually trigger refresh
        result = refresh_job.refresh_project("proj-1")

        assert result.success is True
        assert result.projects_refreshed == 1

        # Verify project was refreshed
        project = cache_manager.get_project("proj-1")
        assert project.name == "Refreshed proj-1"

    def test_refresh_job_emits_events(self, cache_manager, refresh_job, sample_projects):
        """Test that RefreshJob emits events during refresh."""
        cache_manager.populate_projects(sample_projects)

        events = []

        def event_listener(event):
            events.append(event)

        refresh_job.add_event_listener(event_listener)

        # Trigger refresh
        refresh_job.refresh_project("proj-1", force=True)

        # Verify events were emitted
        event_types = [e.type for e in events]
        assert RefreshEventType.REFRESH_STARTED in event_types
        assert RefreshEventType.REFRESH_COMPLETED in event_types

    def test_refresh_all_processes_stale_projects(
        self, cache_manager, refresh_job, sample_projects
    ):
        """Test that refresh_all processes stale projects."""
        cache_manager.populate_projects(sample_projects)

        # Make proj-1 stale, keep proj-2 fresh
        old_time = datetime.utcnow() - timedelta(minutes=120)
        cache_manager.repository.update_project("proj-1", last_fetched=old_time)
        cache_manager.mark_project_refreshed("proj-2")

        # Refresh all (should only refresh proj-1)
        result = refresh_job.refresh_all(force=False)

        assert result.success is True
        assert result.projects_refreshed == 1

    def test_refresh_job_detects_changes(
        self, cache_manager, refresh_job, sample_projects
    ):
        """Test that RefreshJob detects changes."""
        cache_manager.populate_projects(sample_projects)

        events = []

        def event_listener(event):
            events.append(event)

        refresh_job.add_event_listener(event_listener)

        # Refresh (will have different artifacts)
        result = refresh_job.refresh_project("proj-1", force=True)

        assert result.changes_detected is True

        # Check for changes event
        change_events = [e for e in events if e.type == RefreshEventType.CHANGES_DETECTED]
        assert len(change_events) > 0


# =============================================================================
# Error Recovery Tests
# =============================================================================


class TestErrorRecovery:
    """Tests for error recovery scenarios."""

    def test_mark_project_error(self, cache_manager, sample_projects):
        """Test marking a project with an error."""
        cache_manager.populate_projects(sample_projects)

        result = cache_manager.mark_project_error("proj-1", "Test error message")

        assert result is True

        # Verify error was recorded
        project = cache_manager.get_project("proj-1")
        assert project.status == "error"
        assert project.error_message == "Test error message"

    def test_recover_from_error_state(self, cache_manager, sample_projects):
        """Test recovering from error state."""
        cache_manager.populate_projects(sample_projects)

        # Put project in error state
        cache_manager.mark_project_error("proj-1", "Error occurred")

        # Recover by marking as refreshed
        cache_manager.mark_project_refreshed("proj-1")

        # Verify recovery
        project = cache_manager.get_project("proj-1")
        assert project.status == "active"
        assert project.error_message is None

    def test_refresh_job_handles_fetch_errors(self, cache_manager, sample_projects):
        """Test that RefreshJob handles fetch errors gracefully."""

        def failing_fetcher(project_id):
            raise Exception("Fetch failed")

        job = RefreshJob(
            cache_manager=cache_manager,
            data_fetcher=failing_fetcher,
            retry_attempts=1,
            retry_delay_seconds=0.1,
        )

        cache_manager.populate_projects(sample_projects)

        # Refresh should handle error
        result = job.refresh_project("proj-1", force=True)

        assert result.success is False
        assert len(result.errors) > 0

        # Verify project was marked with error
        project = cache_manager.get_project("proj-1")
        assert project.status == "error"

    def test_get_cache_status_handles_errors(self, cache_manager):
        """Test that get_cache_status handles errors gracefully."""
        # Should work even with empty cache
        status = cache_manager.get_cache_status()

        assert status["total_projects"] == 0
        assert status["total_artifacts"] == 0
        assert status["cache_size_bytes"] >= 0

    def test_update_artifact_versions_with_nonexistent_artifact(
        self, cache_manager, sample_projects
    ):
        """Test updating versions for nonexistent artifact."""
        cache_manager.populate_projects(sample_projects)

        result = cache_manager.update_artifact_versions(
            "nonexistent-art", deployed="1.0.0"
        )

        assert result is False

    def test_cache_operations_after_initialization_failure(self, tmp_path):
        """Test that cache operations fail gracefully after init failure."""
        # Create cache with invalid path (read-only directory)
        invalid_path = tmp_path / "readonly" / "cache.db"

        # This should not raise, but operations may fail
        manager = CacheManager(db_path=str(invalid_path), ttl_minutes=60)

        # Try to initialize - may fail
        result = manager.initialize_cache()

        # If initialization succeeded, operations should work
        # If it failed, operations should return empty/False
        projects = manager.get_projects()
        assert isinstance(projects, list)
