"""Match history tracking for success metrics and algorithm improvement.

This module provides functionality to track user confirmations of artifact matches,
calculate success rates, and gather analytics to improve the scoring algorithm over time.

The match history system records:
- User queries and matched artifacts
- Confidence scores from the matching algorithm
- User feedback (confirmed, rejected, or ignored)
- Timestamps for analytics and time-based queries

Example:
    >>> tracker = MatchHistoryTracker()
    >>> # Record a match
    >>> match_id = tracker.record_match("pdf processor", "skill:pdf", 85.5)
    >>> # Later, confirm the match was helpful
    >>> tracker.confirm_match(match_id, MatchOutcome.CONFIRMED)
    >>> # Get statistics
    >>> stats = tracker.get_artifact_stats("skill:pdf")
    >>> print(f"Confirmation rate: {stats.confirmation_rate:.1%}")
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Optional
import sqlite3


class MatchOutcome(Enum):
    """Possible outcomes for a match confirmation."""

    CONFIRMED = "confirmed"  # User deployed/used the artifact
    REJECTED = "rejected"  # User explicitly said no
    IGNORED = "ignored"  # No feedback given (timeout or user chose different artifact)


@dataclass
class MatchRecord:
    """Record of a match and its outcome."""

    id: int
    query: str
    artifact_id: str
    confidence: float
    outcome: Optional[MatchOutcome]
    matched_at: datetime
    confirmed_at: Optional[datetime]


@dataclass
class MatchStats:
    """Aggregated match statistics."""

    total_matches: int
    confirmed: int
    rejected: int
    ignored: int
    confirmation_rate: float  # confirmed / (confirmed + rejected)
    average_confidence: float


class MatchHistoryTracker:
    """Track match outcomes to improve scoring over time.

    This class provides methods to:
    - Record matches between queries and artifacts
    - Confirm or reject matches based on user feedback
    - Calculate success rates and statistics
    - Support algorithm improvements through historical data

    The tracker uses SQLite for persistence via the cache database.
    """

    def __init__(self, db_path: Optional[str | Path] = None):
        """Initialize match history tracker.

        Args:
            db_path: Path to database file. If None, uses default location
                     at ~/.skillmeat/cache/cache.db
        """
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with proper settings.

        Returns:
            SQLite connection with Row factory configured

        Note:
            Connection must be closed by caller
        """
        from skillmeat.cache.schema import get_engine

        return get_engine(self.db_path)

    def record_match(
        self,
        query: str,
        artifact_id: str,
        confidence: float,
    ) -> int:
        """Record a new match.

        Args:
            query: User's search query
            artifact_id: Matched artifact identifier (e.g., "skill:pdf")
            confidence: Confidence score from matching algorithm (0-100)

        Returns:
            Match record ID for later confirmation

        Raises:
            sqlite3.Error: If database operation fails
            ValueError: If confidence is not between 0 and 100

        Example:
            >>> tracker = MatchHistoryTracker()
            >>> match_id = tracker.record_match("pdf processor", "skill:pdf", 85.5)
            >>> print(f"Recorded match {match_id}")
        """
        if not 0 <= confidence <= 100:
            raise ValueError(f"Confidence must be between 0 and 100, got {confidence}")

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO match_history (query, artifact_id, confidence, matched_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (query, artifact_id, confidence),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def confirm_match(
        self,
        match_id: int,
        outcome: MatchOutcome,
    ) -> None:
        """Record user's confirmation/rejection of a match.

        Args:
            match_id: ID of the match record to update
            outcome: User's feedback (CONFIRMED, REJECTED, or IGNORED)

        Raises:
            sqlite3.Error: If database operation fails
            ValueError: If match_id doesn't exist

        Example:
            >>> tracker = MatchHistoryTracker()
            >>> tracker.confirm_match(123, MatchOutcome.CONFIRMED)
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE match_history
                SET outcome = ?, confirmed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (outcome.value, match_id),
            )
            conn.commit()

            if cursor.rowcount == 0:
                raise ValueError(f"No match found with ID {match_id}")
        finally:
            conn.close()

    def get_artifact_stats(self, artifact_id: str) -> MatchStats:
        """Get match statistics for a specific artifact.

        Args:
            artifact_id: Artifact identifier (e.g., "skill:pdf")

        Returns:
            Aggregated statistics for the artifact

        Example:
            >>> tracker = MatchHistoryTracker()
            >>> stats = tracker.get_artifact_stats("skill:pdf")
            >>> print(f"Confirmation rate: {stats.confirmation_rate:.1%}")
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    COUNT(*) as total_matches,
                    SUM(CASE WHEN outcome = 'confirmed' THEN 1 ELSE 0 END) as confirmed,
                    SUM(CASE WHEN outcome = 'rejected' THEN 1 ELSE 0 END) as rejected,
                    SUM(CASE WHEN outcome = 'ignored' OR outcome IS NULL THEN 1 ELSE 0 END) as ignored,
                    AVG(confidence) as average_confidence
                FROM match_history
                WHERE artifact_id = ?
                """,
                (artifact_id,),
            )
            row = cursor.fetchone()

            total_matches = row["total_matches"] or 0
            confirmed = row["confirmed"] or 0
            rejected = row["rejected"] or 0
            ignored = row["ignored"] or 0
            average_confidence = row["average_confidence"] or 0.0

            # Calculate confirmation rate (ignore "ignored" outcomes)
            if confirmed + rejected > 0:
                confirmation_rate = confirmed / (confirmed + rejected)
            else:
                confirmation_rate = 0.0

            return MatchStats(
                total_matches=total_matches,
                confirmed=confirmed,
                rejected=rejected,
                ignored=ignored,
                confirmation_rate=confirmation_rate,
                average_confidence=average_confidence,
            )
        finally:
            conn.close()

    def get_query_stats(self, query: str) -> MatchStats:
        """Get match statistics for a specific query.

        Args:
            query: User's search query

        Returns:
            Aggregated statistics for the query

        Example:
            >>> tracker = MatchHistoryTracker()
            >>> stats = tracker.get_query_stats("pdf processor")
            >>> print(f"Total matches: {stats.total_matches}")
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    COUNT(*) as total_matches,
                    SUM(CASE WHEN outcome = 'confirmed' THEN 1 ELSE 0 END) as confirmed,
                    SUM(CASE WHEN outcome = 'rejected' THEN 1 ELSE 0 END) as rejected,
                    SUM(CASE WHEN outcome = 'ignored' OR outcome IS NULL THEN 1 ELSE 0 END) as ignored,
                    AVG(confidence) as average_confidence
                FROM match_history
                WHERE query = ?
                """,
                (query,),
            )
            row = cursor.fetchone()

            total_matches = row["total_matches"] or 0
            confirmed = row["confirmed"] or 0
            rejected = row["rejected"] or 0
            ignored = row["ignored"] or 0
            average_confidence = row["average_confidence"] or 0.0

            # Calculate confirmation rate (ignore "ignored" outcomes)
            if confirmed + rejected > 0:
                confirmation_rate = confirmed / (confirmed + rejected)
            else:
                confirmation_rate = 0.0

            return MatchStats(
                total_matches=total_matches,
                confirmed=confirmed,
                rejected=rejected,
                ignored=ignored,
                confirmation_rate=confirmation_rate,
                average_confidence=average_confidence,
            )
        finally:
            conn.close()

    def get_overall_stats(self) -> MatchStats:
        """Get overall match statistics across all artifacts and queries.

        Returns:
            Aggregated statistics for all matches

        Example:
            >>> tracker = MatchHistoryTracker()
            >>> stats = tracker.get_overall_stats()
            >>> print(f"Overall confirmation rate: {stats.confirmation_rate:.1%}")
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    COUNT(*) as total_matches,
                    SUM(CASE WHEN outcome = 'confirmed' THEN 1 ELSE 0 END) as confirmed,
                    SUM(CASE WHEN outcome = 'rejected' THEN 1 ELSE 0 END) as rejected,
                    SUM(CASE WHEN outcome = 'ignored' OR outcome IS NULL THEN 1 ELSE 0 END) as ignored,
                    AVG(confidence) as average_confidence
                FROM match_history
                """
            )
            row = cursor.fetchone()

            total_matches = row["total_matches"] or 0
            confirmed = row["confirmed"] or 0
            rejected = row["rejected"] or 0
            ignored = row["ignored"] or 0
            average_confidence = row["average_confidence"] or 0.0

            # Calculate confirmation rate (ignore "ignored" outcomes)
            if confirmed + rejected > 0:
                confirmation_rate = confirmed / (confirmed + rejected)
            else:
                confirmation_rate = 0.0

            return MatchStats(
                total_matches=total_matches,
                confirmed=confirmed,
                rejected=rejected,
                ignored=ignored,
                confirmation_rate=confirmation_rate,
                average_confidence=average_confidence,
            )
        finally:
            conn.close()

    def get_success_rate(self, artifact_id: str) -> float:
        """Get success rate for an artifact (0-1).

        Used to boost/penalize scores based on historical performance.

        Args:
            artifact_id: Artifact identifier (e.g., "skill:pdf")

        Returns:
            Success rate between 0.0 and 1.0 (same as confirmation rate)

        Example:
            >>> tracker = MatchHistoryTracker()
            >>> rate = tracker.get_success_rate("skill:pdf")
            >>> boosted_score = base_score * (1 + rate * 0.2)  # 20% boost at 100% success
        """
        stats = self.get_artifact_stats(artifact_id)
        return stats.confirmation_rate

    def get_recent_match(
        self,
        artifact_id: str,
        within_minutes: int = 30,
    ) -> Optional[MatchRecord]:
        """Get most recent match for an artifact within a time window.

        Used for auto-confirmation when a user deploys an artifact shortly
        after searching for it.

        Args:
            artifact_id: Artifact identifier (e.g., "skill:pdf")
            within_minutes: Time window in minutes (default: 30)

        Returns:
            Most recent match within the window, or None if no match found

        Example:
            >>> tracker = MatchHistoryTracker()
            >>> recent = tracker.get_recent_match("skill:pdf", within_minutes=30)
            >>> if recent and not recent.outcome:
            ...     tracker.confirm_match(recent.id, MatchOutcome.CONFIRMED)
        """
        # Calculate cutoff time (UTC)
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=within_minutes)

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, query, artifact_id, confidence, outcome, matched_at, confirmed_at
                FROM match_history
                WHERE artifact_id = ? AND matched_at >= ?
                ORDER BY matched_at DESC
                LIMIT 1
                """,
                (artifact_id, cutoff),
            )
            row = cursor.fetchone()

            if not row:
                return None

            # Parse outcome
            outcome = None
            if row["outcome"]:
                outcome = MatchOutcome(row["outcome"])

            # Parse timestamps (SQLite stores as strings)
            matched_at = datetime.fromisoformat(row["matched_at"])
            confirmed_at = None
            if row["confirmed_at"]:
                confirmed_at = datetime.fromisoformat(row["confirmed_at"])

            return MatchRecord(
                id=row["id"],
                query=row["query"],
                artifact_id=row["artifact_id"],
                confidence=row["confidence"],
                outcome=outcome,
                matched_at=matched_at,
                confirmed_at=confirmed_at,
            )
        finally:
            conn.close()
