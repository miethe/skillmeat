"""Tests for marketplace cache functionality.

Tests the marketplace metadata caching implementation including
CacheManager methods, RefreshJob marketplace refresh, and API endpoints.
"""

import json
from datetime import datetime, timedelta

import pytest

from skillmeat.cache.manager import CacheManager
from skillmeat.cache.models import MarketplaceEntry


@pytest.fixture
def cache_manager(tmp_path):
    """Create a CacheManager with temporary database."""
    db_path = tmp_path / "cache.db"
    manager = CacheManager(db_path=str(db_path), ttl_minutes=60)
    manager.initialize_cache()
    return manager


@pytest.fixture
def sample_marketplace_entries():
    """Sample marketplace entries for testing."""
    return [
        {
            "id": "mkt-1",
            "name": "awesome-skill",
            "type": "skill",
            "url": "https://github.com/user/awesome-skill",
            "description": "An awesome skill",
            "data": {
                "publisher": "user",
                "license": "MIT",
                "tags": ["automation", "testing"],
                "version": "1.0.0",
            },
        },
        {
            "id": "mkt-2",
            "name": "cool-command",
            "type": "command",
            "url": "https://github.com/user/cool-command",
            "description": "A cool command",
            "data": {
                "publisher": "user",
                "license": "Apache-2.0",
                "tags": ["cli", "utility"],
                "version": "2.0.0",
            },
        },
        {
            "id": "mkt-3",
            "name": "smart-agent",
            "type": "agent",
            "url": "https://github.com/user/smart-agent",
            "description": "A smart agent",
            "data": {
                "publisher": "user",
                "license": "MIT",
                "tags": ["ai", "assistant"],
                "version": "1.5.0",
            },
        },
    ]


class TestMarketplaceCache:
    """Tests for marketplace cache operations."""

    def test_update_marketplace_cache(self, cache_manager, sample_marketplace_entries):
        """Test updating marketplace cache with entries."""
        # Update cache
        count = cache_manager.update_marketplace_cache(sample_marketplace_entries)

        # Verify count
        assert count == 3

        # Verify entries were cached
        entries = cache_manager.get_marketplace_entries()
        assert len(entries) == 3

    def test_get_marketplace_entries_with_type_filter(
        self, cache_manager, sample_marketplace_entries
    ):
        """Test retrieving marketplace entries with type filter."""
        # Populate cache
        cache_manager.update_marketplace_cache(sample_marketplace_entries)

        # Get only skills
        skills = cache_manager.get_marketplace_entries(entry_type="skill")
        assert len(skills) == 1
        assert skills[0].type == "skill"
        assert skills[0].name == "awesome-skill"

        # Get only commands
        commands = cache_manager.get_marketplace_entries(entry_type="command")
        assert len(commands) == 1
        assert commands[0].type == "command"
        assert commands[0].name == "cool-command"

    def test_get_marketplace_entries_all(
        self, cache_manager, sample_marketplace_entries
    ):
        """Test retrieving all marketplace entries."""
        # Populate cache
        cache_manager.update_marketplace_cache(sample_marketplace_entries)

        # Get all entries
        entries = cache_manager.get_marketplace_entries()
        assert len(entries) == 3

        # Verify types
        types = {e.type for e in entries}
        assert types == {"skill", "command", "agent"}

    def test_marketplace_cache_stores_data_as_json(
        self, cache_manager, sample_marketplace_entries
    ):
        """Test that additional data is stored as JSON."""
        # Populate cache
        cache_manager.update_marketplace_cache(sample_marketplace_entries)

        # Get entries
        entries = cache_manager.get_marketplace_entries()

        # Verify data is stored as JSON
        for entry in entries:
            assert entry.data is not None
            # Parse JSON to verify it's valid
            data_dict = json.loads(entry.data)
            assert "publisher" in data_dict
            assert "license" in data_dict
            assert "tags" in data_dict

    def test_is_marketplace_cache_stale_empty(self, cache_manager):
        """Test staleness check with empty cache."""
        # Empty cache should be stale
        assert cache_manager.is_marketplace_cache_stale()

    def test_is_marketplace_cache_stale_fresh(
        self, cache_manager, sample_marketplace_entries
    ):
        """Test staleness check with fresh cache."""
        # Populate cache
        cache_manager.update_marketplace_cache(sample_marketplace_entries)

        # Fresh cache should not be stale
        assert not cache_manager.is_marketplace_cache_stale()

    def test_is_marketplace_cache_stale_expired(
        self, cache_manager, sample_marketplace_entries
    ):
        """Test staleness check with expired cache."""
        # Populate cache
        cache_manager.update_marketplace_cache(sample_marketplace_entries)

        # Manually set cached_at to past TTL by directly updating SQL
        from sqlalchemy import update
        from skillmeat.cache.models import MarketplaceEntry as MarketplaceEntryModel

        stale_time = datetime.utcnow() - timedelta(hours=25)

        session = cache_manager.repository._get_session()
        try:
            session.execute(
                update(MarketplaceEntryModel).values(cached_at=stale_time)
            )
            session.commit()
        finally:
            session.close()

        # Expired cache should be stale
        assert cache_manager.is_marketplace_cache_stale(ttl_hours=24)

    def test_update_marketplace_cache_upsert(
        self, cache_manager, sample_marketplace_entries
    ):
        """Test that updating marketplace cache upserts entries."""
        # Initial populate
        cache_manager.update_marketplace_cache(sample_marketplace_entries)

        # Update with modified entries
        modified_entries = [
            {
                "id": "mkt-1",
                "name": "awesome-skill-v2",  # Changed name
                "type": "skill",
                "url": "https://github.com/user/awesome-skill",
                "description": "An awesome skill v2",  # Changed description
                "data": {"version": "2.0.0"},  # Changed version
            }
        ]

        count = cache_manager.update_marketplace_cache(modified_entries)
        assert count == 1

        # Verify entry was updated (not duplicated)
        entries = cache_manager.get_marketplace_entries()
        assert len(entries) == 3  # Still only 3 entries

        # Verify the specific entry was updated
        skill_entry = [e for e in entries if e.id == "mkt-1"][0]
        assert skill_entry.name == "awesome-skill-v2"
        assert skill_entry.description == "An awesome skill v2"

    def test_update_marketplace_cache_cleans_stale(
        self, cache_manager, sample_marketplace_entries
    ):
        """Test that updating marketplace cache removes stale entries."""
        # Populate cache
        cache_manager.update_marketplace_cache(sample_marketplace_entries)

        # Manually set ALL entries to be stale (> 24 hours old) using SQL update
        from sqlalchemy import update
        from skillmeat.cache.models import MarketplaceEntry as MarketplaceEntryModel

        stale_time = datetime.utcnow() - timedelta(hours=25)

        session = cache_manager.repository._get_session()
        try:
            session.execute(
                update(MarketplaceEntryModel).values(cached_at=stale_time)
            )
            session.commit()
        finally:
            session.close()

        # Verify all entries are now stale
        all_entries_before = cache_manager.repository.list_marketplace_entries()
        assert len(all_entries_before) == 3

        # Update cache (should clean stale entries)
        new_entries = [
            {
                "id": "mkt-4",
                "name": "new-skill",
                "type": "skill",
                "url": "https://github.com/user/new-skill",
                "description": "A new skill",
            }
        ]
        cache_manager.update_marketplace_cache(new_entries)

        # Verify stale entries were removed (deleted count should be logged)
        all_entries_after = cache_manager.repository.list_marketplace_entries()
        # Should have only the 1 new entry (old ones were stale and removed)
        assert len(all_entries_after) == 1
        assert all_entries_after[0].id == "mkt-4"

    def test_get_marketplace_entries_empty_cache(self, cache_manager):
        """Test retrieving marketplace entries from empty cache."""
        entries = cache_manager.get_marketplace_entries()
        assert len(entries) == 0

    def test_marketplace_cache_thread_safety(
        self, cache_manager, sample_marketplace_entries
    ):
        """Test thread-safe marketplace cache operations."""
        import threading

        def populate_cache():
            cache_manager.update_marketplace_cache(sample_marketplace_entries)

        def read_cache():
            entries = cache_manager.get_marketplace_entries()
            return len(entries)

        # Run concurrent operations
        threads = []
        for _ in range(5):
            t1 = threading.Thread(target=populate_cache)
            t2 = threading.Thread(target=read_cache)
            threads.extend([t1, t2])

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Verify cache is consistent
        entries = cache_manager.get_marketplace_entries()
        assert len(entries) == 3


class TestMarketplaceRefresh:
    """Tests for marketplace refresh functionality."""

    def test_refresh_marketplace_with_stale_cache(self, cache_manager, monkeypatch):
        """Test refreshing marketplace when cache is stale."""
        from skillmeat.cache.refresh import RefreshJob

        # Mock marketplace data fetcher
        mock_data = [
            {
                "id": "mkt-test",
                "name": "test-skill",
                "type": "skill",
                "url": "https://github.com/user/test",
                "description": "Test skill",
            }
        ]

        def mock_fetch_marketplace_data(self):
            return mock_data

        # Create refresh job
        refresh_job = RefreshJob(cache_manager=cache_manager)

        # Patch the fetch method
        monkeypatch.setattr(
            RefreshJob, "_fetch_marketplace_data", mock_fetch_marketplace_data
        )

        # Refresh marketplace
        result = refresh_job.refresh_marketplace()

        # Verify result
        assert result.success
        assert result.projects_refreshed == 1  # 1 entry updated

        # Verify cache was populated
        entries = cache_manager.get_marketplace_entries()
        assert len(entries) == 1
        assert entries[0].name == "test-skill"

    def test_refresh_marketplace_with_fresh_cache(
        self, cache_manager, sample_marketplace_entries
    ):
        """Test refreshing marketplace when cache is fresh."""
        from skillmeat.cache.refresh import RefreshJob

        # Populate fresh cache
        cache_manager.update_marketplace_cache(sample_marketplace_entries)

        # Create refresh job
        refresh_job = RefreshJob(cache_manager=cache_manager)

        # Refresh marketplace
        result = refresh_job.refresh_marketplace()

        # Verify result - should skip refresh since cache is fresh
        assert result.success
        assert result.projects_refreshed == 0

    def test_refresh_marketplace_failure(self, cache_manager, monkeypatch):
        """Test marketplace refresh when fetch fails."""
        from skillmeat.cache.refresh import RefreshJob

        # Mock fetch to return None (failure)
        def mock_fetch_marketplace_data(self):
            return None

        # Create refresh job
        refresh_job = RefreshJob(cache_manager=cache_manager)

        # Patch the fetch method
        monkeypatch.setattr(
            RefreshJob, "_fetch_marketplace_data", mock_fetch_marketplace_data
        )

        # Refresh marketplace
        result = refresh_job.refresh_marketplace()

        # Verify result indicates failure
        assert not result.success
        assert len(result.errors) > 0
