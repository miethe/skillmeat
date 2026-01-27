"""Tests for FTS5 feature detection.

Tests the FTS5 availability detection and caching logic.
"""

import pytest
from sqlalchemy.orm import Session

from skillmeat.api.utils.fts5 import (
    check_fts5_available,
    is_fts5_available,
    reset_fts5_check,
)
from skillmeat.cache.models import create_tables, get_session, init_session_factory


@pytest.fixture
def db_session(tmp_path):
    """Create temporary test database session."""
    db_path = tmp_path / "test.db"
    create_tables(db_path)
    init_session_factory(db_path)
    session = get_session(db_path)
    yield session
    session.close()


class TestFTS5Detection:
    """Tests for FTS5 detection functions."""

    def test_fts5_detection_caches_result(self, db_session: Session):
        """Test that FTS5 detection result is cached."""
        reset_fts5_check()

        result1 = check_fts5_available(db_session)
        result2 = check_fts5_available(db_session)

        # Should return same cached result
        assert result1 == result2

    def test_is_fts5_available_returns_false_before_check(self):
        """Test that is_fts5_available returns False before check is called."""
        reset_fts5_check()

        assert is_fts5_available() is False

    def test_reset_fts5_check_clears_cache(self, db_session: Session):
        """Test that reset_fts5_check clears the cached result."""
        reset_fts5_check()

        # First check
        check_fts5_available(db_session)

        # Reset should clear the cache
        reset_fts5_check()

        # After reset, is_fts5_available should return False again
        assert is_fts5_available() is False

    def test_check_fts5_returns_consistent_type(self, db_session: Session):
        """Test that check_fts5_available always returns a boolean."""
        reset_fts5_check()

        result = check_fts5_available(db_session)

        assert isinstance(result, bool)

    def test_is_fts5_available_returns_bool(self, db_session: Session):
        """Test that is_fts5_available always returns a boolean."""
        reset_fts5_check()

        # Before check
        result_before = is_fts5_available()
        assert isinstance(result_before, bool)

        # After check
        check_fts5_available(db_session)
        result_after = is_fts5_available()
        assert isinstance(result_after, bool)

    def test_fts5_detection_with_fresh_database(self, tmp_path):
        """Test FTS5 detection with a freshly created database.

        This tests the scenario where the catalog_fts table doesn't exist yet
        because the database was just created without running the FTS5 migration.
        """
        reset_fts5_check()

        db_path = tmp_path / "fresh.db"
        create_tables(db_path)
        init_session_factory(db_path)
        session = get_session(db_path)

        try:
            result = check_fts5_available(session)

            # Should return a boolean (may be True or False depending on
            # whether FTS5 table was created during init)
            assert isinstance(result, bool)

            # is_fts5_available should match the result
            assert is_fts5_available() == result
        finally:
            session.close()


class TestFTS5CachingBehavior:
    """Tests for FTS5 caching behavior across multiple sessions."""

    def test_cached_result_persists_across_sessions(
        self, db_session: Session, tmp_path
    ):
        """Test that the cached result persists even with different sessions."""
        reset_fts5_check()

        # First check with one session
        result1 = check_fts5_available(db_session)

        # Create a new session
        new_session = get_session(tmp_path / "test.db")
        try:
            # Should use cached result, not re-query
            result2 = check_fts5_available(new_session)

            assert result1 == result2
            assert is_fts5_available() == result1
        finally:
            new_session.close()

    def test_multiple_resets_work_correctly(self, db_session: Session):
        """Test that multiple reset cycles work correctly."""
        for _ in range(3):
            reset_fts5_check()
            assert is_fts5_available() is False

            check_fts5_available(db_session)
            # Result may be True or False depending on FTS5 availability
            result = is_fts5_available()
            assert isinstance(result, bool)
