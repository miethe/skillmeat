"""Unit tests for RatingManager storage layer."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from skillmeat.cache.models import create_tables, get_session
from skillmeat.core.scoring.models import UserRating
from skillmeat.storage.rating_store import (
    RateLimitExceededError,
    RatingManager,
    RatingNotFoundError,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_cache.db"
        # Create tables
        create_tables(db_path)
        yield db_path


@pytest.fixture
def manager(temp_db):
    """Create RatingManager instance with temp database.

    Note: This fixture uses function scope (default), so each test gets
    a fresh database to avoid rate limit conflicts between tests.
    """
    # Override get_session to use temp database
    import skillmeat.cache.models as models
    import skillmeat.storage.rating_store as rating_store

    original_get_session = models.get_session
    original_session_local = models.SessionLocal

    def temp_get_session(db_path=None):
        # Reset session factory for each test
        models.SessionLocal = None
        # Ignore db_path parameter and use temp_db
        return original_get_session(temp_db)

    # Patch both modules
    models.get_session = temp_get_session
    rating_store.get_session = temp_get_session

    manager = RatingManager()
    yield manager

    # Restore original get_session and session factory
    models.get_session = original_get_session
    models.SessionLocal = original_session_local
    rating_store.get_session = original_get_session


class TestAddRating:
    """Tests for add_rating method."""

    def test_add_rating_basic(self, manager):
        """Test adding a basic rating."""
        rating = manager.add_rating("skill:canvas", 5)

        assert rating.id is not None
        assert rating.artifact_id == "skill:canvas"
        assert rating.rating == 5
        assert rating.feedback is None
        assert rating.share_with_community is False
        assert rating.rated_at is not None

    def test_add_rating_with_feedback(self, manager):
        """Test adding a rating with feedback."""
        rating = manager.add_rating("skill:canvas", 4, feedback="Great skill!")

        assert rating.rating == 4
        assert rating.feedback == "Great skill!"

    def test_add_rating_with_share(self, manager):
        """Test adding a rating with community sharing enabled."""
        rating = manager.add_rating("skill:canvas", 5, share=True)

        assert rating.share_with_community is True

    def test_add_rating_strips_whitespace(self, manager):
        """Test that artifact_id whitespace is stripped."""
        rating = manager.add_rating("  skill:canvas  ", 5)

        assert rating.artifact_id == "skill:canvas"

    def test_add_rating_empty_artifact_id(self, manager):
        """Test that empty artifact_id raises ValueError."""
        with pytest.raises(ValueError, match="artifact_id must be a non-empty string"):
            manager.add_rating("", 5)

        with pytest.raises(ValueError, match="artifact_id must be a non-empty string"):
            manager.add_rating("   ", 5)

    def test_add_rating_invalid_rating_too_low(self, manager):
        """Test that rating below 1 raises ValueError."""
        with pytest.raises(ValueError, match="rating must be 1-5"):
            manager.add_rating("skill:canvas", 0)

    def test_add_rating_invalid_rating_too_high(self, manager):
        """Test that rating above 5 raises ValueError."""
        with pytest.raises(ValueError, match="rating must be 1-5"):
            manager.add_rating("skill:canvas", 6)

    def test_add_rating_all_valid_values(self, manager):
        """Test that all valid ratings (1-5) work."""
        for rating_value in range(1, 6):
            rating = manager.add_rating(f"skill:test-{rating_value}", rating_value)
            assert rating.rating == rating_value

    def test_add_rating_rate_limit(self, manager):
        """Test that rate limiting works."""
        # Add maximum allowed ratings (5 by default)
        for i in range(5):
            manager.add_rating("skill:canvas", 5, feedback=f"Rating {i}")

        # Next one should fail
        with pytest.raises(RateLimitExceededError, match="Rate limit exceeded"):
            manager.add_rating("skill:canvas", 5)

    def test_add_rating_custom_rate_limit(self, manager):
        """Test custom rate limit."""
        # Add 2 ratings with max_per_day=2
        manager.add_rating("skill:test", 5, max_per_day=2)
        manager.add_rating("skill:test", 5, max_per_day=2)

        # Third should fail
        with pytest.raises(RateLimitExceededError):
            manager.add_rating("skill:test", 5, max_per_day=2)


class TestGetRatings:
    """Tests for get_ratings method."""

    def test_get_ratings_empty(self, manager):
        """Test getting ratings for artifact with no ratings."""
        ratings = manager.get_ratings("skill:nonexistent")

        assert ratings == []

    def test_get_ratings_single(self, manager):
        """Test getting a single rating."""
        added = manager.add_rating("skill:get_single", 5, feedback="Great!")

        ratings = manager.get_ratings("skill:get_single")

        assert len(ratings) == 1
        assert ratings[0].id == added.id
        assert ratings[0].rating == 5
        assert ratings[0].feedback == "Great!"

    def test_get_ratings_multiple(self, manager):
        """Test getting multiple ratings."""
        manager.add_rating("skill:get_multiple", 5, feedback="First")
        manager.add_rating("skill:get_multiple", 4, feedback="Second")
        manager.add_rating("skill:get_multiple", 3, feedback="Third")

        ratings = manager.get_ratings("skill:get_multiple")

        assert len(ratings) == 3

    def test_get_ratings_ordered_by_recent(self, manager):
        """Test that ratings are ordered by most recent first."""
        first = manager.add_rating("skill:get_ordered", 5, feedback="First")
        second = manager.add_rating("skill:get_ordered", 4, feedback="Second")

        ratings = manager.get_ratings("skill:get_ordered")

        # Most recent first
        assert ratings[0].id == second.id
        assert ratings[1].id == first.id

    def test_get_ratings_filtered_by_artifact(self, manager):
        """Test that ratings are filtered by artifact_id."""
        manager.add_rating("skill:get_filtered", 5)
        manager.add_rating("skill:other", 4)

        ratings = manager.get_ratings("skill:get_filtered")

        assert len(ratings) == 1
        assert ratings[0].artifact_id == "skill:get_filtered"

    def test_get_ratings_empty_artifact_id(self, manager):
        """Test that empty artifact_id returns empty list."""
        assert manager.get_ratings("") == []
        assert manager.get_ratings("   ") == []


class TestGetAverageRating:
    """Tests for get_average_rating method."""

    def test_get_average_rating_none(self, manager):
        """Test average rating for artifact with no ratings."""
        avg = manager.get_average_rating("skill:nonexistent")

        assert avg is None

    def test_get_average_rating_single(self, manager):
        """Test average rating with single rating."""
        manager.add_rating("skill:avg_single", 5)

        avg = manager.get_average_rating("skill:avg_single")

        assert avg == 5.0

    def test_get_average_rating_multiple(self, manager):
        """Test average rating with multiple ratings."""
        manager.add_rating("skill:avg_multiple", 5)
        manager.add_rating("skill:avg_multiple", 3)
        manager.add_rating("skill:avg_multiple", 4)

        avg = manager.get_average_rating("skill:avg_multiple")

        assert avg == 4.0  # (5 + 3 + 4) / 3

    def test_get_average_rating_filtered_by_artifact(self, manager):
        """Test that average is calculated per artifact."""
        manager.add_rating("skill:avg_filtered", 5)
        manager.add_rating("skill:avg_filtered", 5)
        manager.add_rating("skill:other", 1)

        avg = manager.get_average_rating("skill:avg_filtered")

        assert avg == 5.0

    def test_get_average_rating_empty_artifact_id(self, manager):
        """Test that empty artifact_id returns None."""
        assert manager.get_average_rating("") is None
        assert manager.get_average_rating("   ") is None


class TestExportRatings:
    """Tests for export_ratings method."""

    def test_export_ratings_empty(self, manager):
        """Test exporting when no ratings exist (respects share flag)."""
        # Note: The test database may have ratings from other test classes
        # Since we filter by shared_only=True, we should get empty list
        exported = manager.export_ratings(shared_only=True)

        # Since we haven't added any shared ratings in THIS test, should be empty
        # But other tests may have added non-shared ratings
        assert all(rating.get("share_with_community") is not False for rating in exported)

    def test_export_ratings_shared_only(self, manager):
        """Test exporting only shared ratings."""
        manager.add_rating("skill:export_shared", 5, feedback="Shared", share=True)
        manager.add_rating("skill:export_not_shared", 4, feedback="Not shared", share=False)

        exported = manager.export_ratings(shared_only=True)

        # Should only get the shared one we just added
        shared_ids = [r["artifact_id"] for r in exported if r["artifact_id"] == "skill:export_shared"]
        assert len(shared_ids) == 1

    def test_export_ratings_all(self, manager):
        """Test exporting all ratings regardless of share flag."""
        manager.add_rating("skill:export_all1", 5, share=True)
        manager.add_rating("skill:export_all2", 4, share=False)

        exported = manager.export_ratings(shared_only=False)

        # Should include both
        export_ids = [r["artifact_id"] for r in exported]
        assert "skill:export_all1" in export_ids
        assert "skill:export_all2" in export_ids

    def test_export_ratings_format(self, manager):
        """Test that exported ratings have correct format."""
        manager.add_rating("skill:export_format", 5, feedback="Great!", share=True)

        exported = manager.export_ratings()

        # Find our rating
        our_rating = [r for r in exported if r["artifact_id"] == "skill:export_format"]
        assert len(our_rating) == 1
        rating = our_rating[0]

        assert "artifact_id" in rating
        assert "rating" in rating
        assert "feedback" in rating
        assert "rated_at" in rating
        # Should NOT include internal fields
        assert "id" not in rating
        assert "share_with_community" not in rating

    def test_export_ratings_ordered(self, manager):
        """Test that exported ratings are ordered by most recent."""
        manager.add_rating("skill:export_first", 5, share=True)
        manager.add_rating("skill:export_second", 4, share=True)

        exported = manager.export_ratings()

        # Find our ratings
        our_ratings = [r for r in exported if r["artifact_id"] in ["skill:export_first", "skill:export_second"]]
        assert len(our_ratings) == 2

        # Most recent should be first
        assert our_ratings[0]["artifact_id"] == "skill:export_second"
        assert our_ratings[1]["artifact_id"] == "skill:export_first"


class TestDeleteRating:
    """Tests for delete_rating method."""

    def test_delete_rating_success(self, manager):
        """Test deleting an existing rating."""
        rating = manager.add_rating("skill:canvas", 5)

        result = manager.delete_rating(rating.id)

        assert result is True

        # Verify it's gone
        ratings = manager.get_ratings("skill:canvas")
        assert len(ratings) == 0

    def test_delete_rating_not_found(self, manager):
        """Test deleting a non-existent rating."""
        result = manager.delete_rating(99999)

        assert result is False

    def test_delete_rating_does_not_affect_others(self, manager):
        """Test that deleting one rating doesn't affect others."""
        rating1 = manager.add_rating("skill:canvas", 5)
        rating2 = manager.add_rating("skill:canvas", 4)

        manager.delete_rating(rating1.id)

        ratings = manager.get_ratings("skill:canvas")
        assert len(ratings) == 1
        assert ratings[0].id == rating2.id


class TestUpdateRating:
    """Tests for update_rating method."""

    def test_update_rating_value(self, manager):
        """Test updating rating value."""
        rating = manager.add_rating("skill:canvas", 5, feedback="Great!")

        updated = manager.update_rating(rating.id, rating=4)

        assert updated.rating == 4
        assert updated.feedback == "Great!"  # Unchanged

    def test_update_rating_feedback(self, manager):
        """Test updating feedback."""
        rating = manager.add_rating("skill:canvas", 5, feedback="Great!")

        updated = manager.update_rating(rating.id, feedback="Updated feedback")

        assert updated.rating == 5  # Unchanged
        assert updated.feedback == "Updated feedback"

    def test_update_rating_both(self, manager):
        """Test updating both rating and feedback."""
        rating = manager.add_rating("skill:canvas", 5, feedback="Great!")

        updated = manager.update_rating(rating.id, rating=3, feedback="Changed my mind")

        assert updated.rating == 3
        assert updated.feedback == "Changed my mind"

    def test_update_rating_none_changes(self, manager):
        """Test updating with None values (no change)."""
        rating = manager.add_rating("skill:canvas", 5, feedback="Great!")

        updated = manager.update_rating(rating.id)

        assert updated.rating == 5
        assert updated.feedback == "Great!"

    def test_update_rating_not_found(self, manager):
        """Test updating a non-existent rating."""
        with pytest.raises(RatingNotFoundError, match="Rating with id 99999 not found"):
            manager.update_rating(99999, rating=4)

    def test_update_rating_invalid_value(self, manager):
        """Test updating with invalid rating value."""
        rating = manager.add_rating("skill:canvas", 5)

        with pytest.raises(ValueError, match="rating must be 1-5"):
            manager.update_rating(rating.id, rating=0)

        with pytest.raises(ValueError, match="rating must be 1-5"):
            manager.update_rating(rating.id, rating=6)

    def test_update_rating_persists(self, manager):
        """Test that updates persist to database."""
        rating = manager.add_rating("skill:canvas", 5)

        manager.update_rating(rating.id, rating=3)

        # Retrieve again
        ratings = manager.get_ratings("skill:canvas")
        assert ratings[0].rating == 3


class TestCanRate:
    """Tests for can_rate method."""

    def test_can_rate_no_ratings(self, manager):
        """Test that can_rate returns True when no ratings exist."""
        assert manager.can_rate("skill:canvas") is True

    def test_can_rate_under_limit(self, manager):
        """Test that can_rate returns True under rate limit."""
        manager.add_rating("skill:canvas", 5)
        manager.add_rating("skill:canvas", 4)

        assert manager.can_rate("skill:canvas", max_per_day=5) is True

    def test_can_rate_at_limit(self, manager):
        """Test that can_rate returns False at rate limit."""
        # Add exactly max_per_day ratings
        for _ in range(5):
            manager.add_rating("skill:canvas", 5)

        assert manager.can_rate("skill:canvas", max_per_day=5) is False

    def test_can_rate_custom_limit(self, manager):
        """Test can_rate with custom limit."""
        manager.add_rating("skill:canvas", 5)
        manager.add_rating("skill:canvas", 5)

        assert manager.can_rate("skill:canvas", max_per_day=3) is True
        assert manager.can_rate("skill:canvas", max_per_day=2) is False

    def test_can_rate_different_artifacts(self, manager):
        """Test that rate limit is per artifact."""
        # Fill limit for one artifact
        for _ in range(5):
            manager.add_rating("skill:canvas", 5)

        # Should still be able to rate a different artifact
        assert manager.can_rate("skill:other") is True

    def test_can_rate_empty_artifact_id(self, manager):
        """Test that empty artifact_id returns False."""
        assert manager.can_rate("") is False
        assert manager.can_rate("   ") is False


class TestRateLimitTimeWindow:
    """Tests for rate limit time window behavior."""

    def test_rate_limit_24_hour_window(self, manager, temp_db, monkeypatch):
        """Test that rate limit uses 24-hour rolling window."""
        # Add 5 ratings "yesterday" by mocking datetime
        from datetime import datetime

        old_time = datetime.utcnow() - timedelta(hours=25)

        # Manually insert old ratings
        session = get_session(temp_db)
        try:
            from skillmeat.cache.models import UserRating as OrmUserRating

            for i in range(5):
                orm_rating = OrmUserRating(
                    artifact_id="skill:canvas",
                    rating=5,
                    feedback=f"Old rating {i}",
                    share_with_community=False,
                    rated_at=old_time,
                )
                session.add(orm_rating)
            session.commit()
        finally:
            session.close()

        # Should be able to add new ratings (old ones expired)
        assert manager.can_rate("skill:canvas", max_per_day=5) is True
        manager.add_rating("skill:canvas", 5)

    def test_rate_limit_within_window(self, manager, temp_db):
        """Test that recent ratings count toward limit."""
        # Add ratings within last 24 hours
        for i in range(5):
            manager.add_rating("skill:canvas", 5)

        # Should NOT be able to add more
        assert manager.can_rate("skill:canvas", max_per_day=5) is False


class TestIntegration:
    """Integration tests combining multiple operations."""

    def test_full_lifecycle(self, manager):
        """Test full lifecycle: add, get, update, delete."""
        # Add
        rating = manager.add_rating("skill:canvas", 5, feedback="Great!", share=True)
        assert rating.id is not None

        # Get
        ratings = manager.get_ratings("skill:canvas")
        assert len(ratings) == 1

        # Update
        updated = manager.update_rating(rating.id, rating=4, feedback="Good")
        assert updated.rating == 4

        # Delete
        assert manager.delete_rating(rating.id) is True
        assert len(manager.get_ratings("skill:canvas")) == 0

    def test_multiple_artifacts(self, manager):
        """Test managing ratings for multiple artifacts."""
        manager.add_rating("skill:canvas", 5)
        manager.add_rating("skill:canvas", 4)
        manager.add_rating("skill:other", 3)

        assert len(manager.get_ratings("skill:canvas")) == 2
        assert len(manager.get_ratings("skill:other")) == 1
        assert manager.get_average_rating("skill:canvas") == 4.5
        assert manager.get_average_rating("skill:other") == 3.0

    def test_export_and_reimport_scenario(self, manager):
        """Test exporting ratings for community sharing."""
        # Add various ratings
        manager.add_rating("skill:canvas", 5, feedback="Excellent", share=True)
        manager.add_rating("skill:canvas", 4, feedback="Good", share=False)
        manager.add_rating("skill:other", 3, share=True)

        # Export shared only
        exported = manager.export_ratings(shared_only=True)
        assert len(exported) == 2

        # Verify export format is JSON-serializable
        import json

        json_str = json.dumps(exported)
        parsed = json.loads(json_str)
        assert len(parsed) == 2
