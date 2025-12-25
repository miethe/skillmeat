"""Tests for match history tracking functionality.

This test module ensures that:
- Match records are stored correctly
- Confirmations update outcomes properly
- Statistics calculations are accurate
- Edge cases are handled gracefully
- Database transactions work correctly
"""

from __future__ import annotations

import pytest
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile

from skillmeat.core.scoring.match_history import (
    MatchHistoryTracker,
    MatchOutcome,
    MatchRecord,
    MatchStats,
)


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    # Initialize database schema
    from skillmeat.cache.schema import init_database

    init_database(db_path)

    yield db_path

    # Cleanup
    db_path.unlink(missing_ok=True)


@pytest.fixture
def tracker(temp_db):
    """Create MatchHistoryTracker instance with temp database."""
    return MatchHistoryTracker(db_path=temp_db)


class TestMatchRecording:
    """Tests for recording matches."""

    def test_record_match_basic(self, tracker):
        """Test basic match recording."""
        match_id = tracker.record_match(
            query="pdf processor",
            artifact_id="skill:pdf",
            confidence=85.5,
        )

        assert match_id > 0

    def test_record_match_returns_unique_ids(self, tracker):
        """Test that each match gets a unique ID."""
        id1 = tracker.record_match("query1", "artifact1", 70.0)
        id2 = tracker.record_match("query2", "artifact2", 80.0)

        assert id1 != id2
        assert id2 > id1

    def test_record_match_invalid_confidence_low(self, tracker):
        """Test that confidence below 0 raises ValueError."""
        with pytest.raises(ValueError, match="Confidence must be between 0 and 100"):
            tracker.record_match("query", "artifact", -1.0)

    def test_record_match_invalid_confidence_high(self, tracker):
        """Test that confidence above 100 raises ValueError."""
        with pytest.raises(ValueError, match="Confidence must be between 0 and 100"):
            tracker.record_match("query", "artifact", 101.0)

    def test_record_match_boundary_confidence(self, tracker):
        """Test boundary values for confidence (0 and 100)."""
        id1 = tracker.record_match("query", "artifact", 0.0)
        id2 = tracker.record_match("query", "artifact", 100.0)

        assert id1 > 0
        assert id2 > 0


class TestMatchConfirmation:
    """Tests for confirming/rejecting matches."""

    def test_confirm_match_confirmed(self, tracker):
        """Test marking a match as confirmed."""
        match_id = tracker.record_match("query", "artifact", 80.0)
        tracker.confirm_match(match_id, MatchOutcome.CONFIRMED)

        # Verify via stats
        stats = tracker.get_artifact_stats("artifact")
        assert stats.confirmed == 1
        assert stats.rejected == 0
        assert stats.ignored == 0

    def test_confirm_match_rejected(self, tracker):
        """Test marking a match as rejected."""
        match_id = tracker.record_match("query", "artifact", 80.0)
        tracker.confirm_match(match_id, MatchOutcome.REJECTED)

        stats = tracker.get_artifact_stats("artifact")
        assert stats.confirmed == 0
        assert stats.rejected == 1
        assert stats.ignored == 0

    def test_confirm_match_ignored(self, tracker):
        """Test marking a match as ignored."""
        match_id = tracker.record_match("query", "artifact", 80.0)
        tracker.confirm_match(match_id, MatchOutcome.IGNORED)

        stats = tracker.get_artifact_stats("artifact")
        assert stats.confirmed == 0
        assert stats.rejected == 0
        assert stats.ignored == 1

    def test_confirm_match_nonexistent_id(self, tracker):
        """Test that confirming nonexistent match raises ValueError."""
        with pytest.raises(ValueError, match="No match found with ID"):
            tracker.confirm_match(99999, MatchOutcome.CONFIRMED)

    def test_confirm_match_updates_existing(self, tracker):
        """Test that confirming a match multiple times updates the outcome."""
        match_id = tracker.record_match("query", "artifact", 80.0)

        # First confirmation
        tracker.confirm_match(match_id, MatchOutcome.REJECTED)
        stats = tracker.get_artifact_stats("artifact")
        assert stats.rejected == 1
        assert stats.confirmed == 0

        # Change to confirmed
        tracker.confirm_match(match_id, MatchOutcome.CONFIRMED)
        stats = tracker.get_artifact_stats("artifact")
        assert stats.rejected == 0
        assert stats.confirmed == 1


class TestArtifactStats:
    """Tests for artifact-level statistics."""

    def test_get_artifact_stats_no_data(self, tracker):
        """Test stats for artifact with no matches."""
        stats = tracker.get_artifact_stats("nonexistent")

        assert stats.total_matches == 0
        assert stats.confirmed == 0
        assert stats.rejected == 0
        assert stats.ignored == 0
        assert stats.confirmation_rate == 0.0
        assert stats.average_confidence == 0.0

    def test_get_artifact_stats_single_match(self, tracker):
        """Test stats with single confirmed match."""
        match_id = tracker.record_match("query", "artifact", 85.5)
        tracker.confirm_match(match_id, MatchOutcome.CONFIRMED)

        stats = tracker.get_artifact_stats("artifact")

        assert stats.total_matches == 1
        assert stats.confirmed == 1
        assert stats.rejected == 0
        assert stats.confirmation_rate == 1.0
        assert stats.average_confidence == 85.5

    def test_get_artifact_stats_multiple_matches(self, tracker):
        """Test stats with multiple matches."""
        # 3 confirmed, 1 rejected, 1 ignored
        id1 = tracker.record_match("query1", "artifact", 90.0)
        id2 = tracker.record_match("query2", "artifact", 80.0)
        id3 = tracker.record_match("query3", "artifact", 70.0)
        id4 = tracker.record_match("query4", "artifact", 60.0)
        id5 = tracker.record_match("query5", "artifact", 50.0)

        tracker.confirm_match(id1, MatchOutcome.CONFIRMED)
        tracker.confirm_match(id2, MatchOutcome.CONFIRMED)
        tracker.confirm_match(id3, MatchOutcome.CONFIRMED)
        tracker.confirm_match(id4, MatchOutcome.REJECTED)
        tracker.confirm_match(id5, MatchOutcome.IGNORED)

        stats = tracker.get_artifact_stats("artifact")

        assert stats.total_matches == 5
        assert stats.confirmed == 3
        assert stats.rejected == 1
        assert stats.ignored == 1
        # Confirmation rate: 3 / (3 + 1) = 0.75 (ignores "ignored")
        assert stats.confirmation_rate == 0.75
        # Average: (90 + 80 + 70 + 60 + 50) / 5 = 70.0
        assert stats.average_confidence == 70.0

    def test_get_artifact_stats_confirmation_rate_ignores_ignored(self, tracker):
        """Test that confirmation rate calculation ignores 'ignored' outcomes."""
        # 1 confirmed, 0 rejected, 10 ignored
        id1 = tracker.record_match("q1", "artifact", 80.0)
        tracker.confirm_match(id1, MatchOutcome.CONFIRMED)

        for i in range(10):
            mid = tracker.record_match(f"q{i+2}", "artifact", 50.0)
            tracker.confirm_match(mid, MatchOutcome.IGNORED)

        stats = tracker.get_artifact_stats("artifact")

        assert stats.total_matches == 11
        assert stats.confirmed == 1
        assert stats.ignored == 10
        # Confirmation rate: 1 / (1 + 0) = 1.0 (ignores 10 ignored)
        assert stats.confirmation_rate == 1.0

    def test_get_artifact_stats_only_ignored(self, tracker):
        """Test confirmation rate when all matches are ignored."""
        id1 = tracker.record_match("q1", "artifact", 80.0)
        tracker.confirm_match(id1, MatchOutcome.IGNORED)

        stats = tracker.get_artifact_stats("artifact")

        assert stats.total_matches == 1
        assert stats.ignored == 1
        # Confirmation rate: 0 / (0 + 0) = 0.0 (no confirmed or rejected)
        assert stats.confirmation_rate == 0.0


class TestQueryStats:
    """Tests for query-level statistics."""

    def test_get_query_stats_no_data(self, tracker):
        """Test stats for query with no matches."""
        stats = tracker.get_query_stats("nonexistent query")

        assert stats.total_matches == 0
        assert stats.confirmation_rate == 0.0

    def test_get_query_stats_multiple_artifacts(self, tracker):
        """Test stats for a query that matched multiple artifacts."""
        # Same query, different artifacts
        id1 = tracker.record_match("pdf", "artifact1", 90.0)
        id2 = tracker.record_match("pdf", "artifact2", 80.0)
        id3 = tracker.record_match("pdf", "artifact3", 70.0)

        tracker.confirm_match(id1, MatchOutcome.CONFIRMED)
        tracker.confirm_match(id2, MatchOutcome.CONFIRMED)
        tracker.confirm_match(id3, MatchOutcome.REJECTED)

        stats = tracker.get_query_stats("pdf")

        assert stats.total_matches == 3
        assert stats.confirmed == 2
        assert stats.rejected == 1
        assert stats.confirmation_rate == 2.0 / 3.0


class TestOverallStats:
    """Tests for overall statistics across all matches."""

    def test_get_overall_stats_no_data(self, tracker):
        """Test overall stats with no matches."""
        stats = tracker.get_overall_stats()

        assert stats.total_matches == 0
        assert stats.confirmation_rate == 0.0

    def test_get_overall_stats_mixed_data(self, tracker):
        """Test overall stats with matches from multiple queries and artifacts."""
        # Different queries and artifacts
        id1 = tracker.record_match("query1", "artifact1", 90.0)
        id2 = tracker.record_match("query2", "artifact2", 80.0)
        id3 = tracker.record_match("query3", "artifact3", 70.0)
        id4 = tracker.record_match("query4", "artifact4", 60.0)

        tracker.confirm_match(id1, MatchOutcome.CONFIRMED)
        tracker.confirm_match(id2, MatchOutcome.CONFIRMED)
        tracker.confirm_match(id3, MatchOutcome.REJECTED)
        tracker.confirm_match(id4, MatchOutcome.IGNORED)

        stats = tracker.get_overall_stats()

        assert stats.total_matches == 4
        assert stats.confirmed == 2
        assert stats.rejected == 1
        assert stats.ignored == 1
        # Confirmation rate: 2 / (2 + 1) ≈ 0.6667
        assert abs(stats.confirmation_rate - 2.0 / 3.0) < 0.001
        # Average: (90 + 80 + 70 + 60) / 4 = 75.0
        assert stats.average_confidence == 75.0


class TestSuccessRate:
    """Tests for success rate calculation."""

    def test_get_success_rate_same_as_confirmation_rate(self, tracker):
        """Test that success rate equals confirmation rate."""
        id1 = tracker.record_match("query", "artifact", 90.0)
        id2 = tracker.record_match("query", "artifact", 80.0)

        tracker.confirm_match(id1, MatchOutcome.CONFIRMED)
        tracker.confirm_match(id2, MatchOutcome.REJECTED)

        success_rate = tracker.get_success_rate("artifact")
        stats = tracker.get_artifact_stats("artifact")

        assert success_rate == stats.confirmation_rate
        assert success_rate == 0.5

    def test_get_success_rate_no_data(self, tracker):
        """Test success rate for artifact with no data."""
        success_rate = tracker.get_success_rate("nonexistent")
        assert success_rate == 0.0


class TestRecentMatch:
    """Tests for recent match retrieval."""

    def test_get_recent_match_within_window(self, tracker, temp_db):
        """Test retrieving match within time window."""
        match_id = tracker.record_match("query", "artifact", 85.0)

        # Should find the match (just created, within 30 min window)
        recent = tracker.get_recent_match("artifact", within_minutes=30)

        assert recent is not None
        assert recent.id == match_id
        assert recent.query == "query"
        assert recent.artifact_id == "artifact"
        assert recent.confidence == 85.0
        assert recent.outcome is None

    def test_get_recent_match_outside_window(self, tracker, temp_db):
        """Test that old matches outside window are not returned."""
        # Record a match
        match_id = tracker.record_match("query", "artifact", 85.0)

        # Manually update matched_at to be 2 hours ago
        conn = sqlite3.connect(str(temp_db))
        try:
            two_hours_ago = datetime.now(timezone.utc) - timedelta(hours=2)
            conn.execute(
                "UPDATE match_history SET matched_at = ? WHERE id = ?",
                (two_hours_ago, match_id),
            )
            conn.commit()
        finally:
            conn.close()

        # Should NOT find the match (outside 30 min window)
        recent = tracker.get_recent_match("artifact", within_minutes=30)
        assert recent is None

    def test_get_recent_match_no_matches(self, tracker):
        """Test when there are no matches for the artifact."""
        recent = tracker.get_recent_match("nonexistent", within_minutes=30)
        assert recent is None

    def test_get_recent_match_returns_most_recent(self, tracker):
        """Test that only the most recent match is returned."""
        id1 = tracker.record_match("query1", "artifact", 70.0)
        id2 = tracker.record_match("query2", "artifact", 80.0)
        id3 = tracker.record_match("query3", "artifact", 90.0)

        recent = tracker.get_recent_match("artifact", within_minutes=30)

        assert recent is not None
        assert recent.id == id3  # Most recent
        assert recent.confidence == 90.0

    def test_get_recent_match_with_outcome(self, tracker):
        """Test retrieving match that has been confirmed."""
        match_id = tracker.record_match("query", "artifact", 85.0)
        tracker.confirm_match(match_id, MatchOutcome.CONFIRMED)

        recent = tracker.get_recent_match("artifact", within_minutes=30)

        assert recent is not None
        assert recent.outcome == MatchOutcome.CONFIRMED
        assert recent.confirmed_at is not None


class TestDatabaseIntegration:
    """Tests for database connection and transaction handling."""

    def test_tracker_uses_provided_db_path(self, temp_db):
        """Test that tracker uses the provided database path."""
        tracker = MatchHistoryTracker(db_path=temp_db)
        match_id = tracker.record_match("query", "artifact", 80.0)

        # Verify data was written to the correct database
        conn = sqlite3.connect(str(temp_db))
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM match_history")
            count = cursor.fetchone()[0]
            assert count == 1
        finally:
            conn.close()

    def test_tracker_closes_connections(self, tracker):
        """Test that tracker properly closes database connections."""
        # Record multiple matches to ensure connections are opened/closed
        for i in range(10):
            tracker.record_match(f"query{i}", f"artifact{i}", 80.0)

        # If connections aren't closed, this would eventually fail or leak
        stats = tracker.get_overall_stats()
        assert stats.total_matches == 10


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_query_string(self, tracker):
        """Test recording match with empty query."""
        match_id = tracker.record_match("", "artifact", 80.0)
        assert match_id > 0

        stats = tracker.get_query_stats("")
        assert stats.total_matches == 1

    def test_special_characters_in_query(self, tracker):
        """Test handling special characters in query."""
        special_query = "pdf's & special-chars: <test>"
        match_id = tracker.record_match(special_query, "artifact", 80.0)
        assert match_id > 0

        stats = tracker.get_query_stats(special_query)
        assert stats.total_matches == 1

    def test_long_artifact_id(self, tracker):
        """Test handling very long artifact IDs."""
        long_id = "a" * 1000
        match_id = tracker.record_match("query", long_id, 80.0)
        assert match_id > 0

        stats = tracker.get_artifact_stats(long_id)
        assert stats.total_matches == 1

    def test_concurrent_stats_calculations(self, tracker):
        """Test that stats calculations don't interfere with each other."""
        # Setup: 2 artifacts, 2 queries
        tracker.record_match("query1", "artifact1", 90.0)
        tracker.record_match("query1", "artifact2", 80.0)
        tracker.record_match("query2", "artifact1", 70.0)

        # Calculate stats concurrently (well, sequentially but simulating concurrent access)
        stats1 = tracker.get_artifact_stats("artifact1")
        stats2 = tracker.get_artifact_stats("artifact2")
        stats_q1 = tracker.get_query_stats("query1")
        stats_overall = tracker.get_overall_stats()

        # Verify each has correct counts
        assert stats1.total_matches == 2
        assert stats2.total_matches == 1
        assert stats_q1.total_matches == 2
        assert stats_overall.total_matches == 3
