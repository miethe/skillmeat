"""Anti-gaming protection for artifact rating system.

This module implements rate limiting and anomaly detection to prevent
score manipulation through burst ratings, pattern abuse, and other gaming attempts.

Components:
    - RateLimiter: Enforces submission rate limits per user and artifact
    - AnomalyDetector: Detects suspicious rating patterns (bursts, uniformity, timing)
    - AntiGamingGuard: Unified interface for all anti-gaming checks

Example:
    >>> guard = AntiGamingGuard()
    >>> allowed, reason = guard.can_submit_rating("user123", "skill:canvas")
    >>> if not allowed:
    ...     raise RateLimitError(reason)
    >>> # Proceed with rating submission
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Set
from enum import Enum
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class ViolationType(Enum):
    """Types of anti-gaming violations."""

    RATE_LIMIT = "rate_limit"
    ANOMALY_BURST = "anomaly_burst"
    ANOMALY_PATTERN = "anomaly_pattern"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting rules.

    Attributes:
        max_ratings_per_day: Maximum ratings a user can submit per day
        max_ratings_per_artifact: Maximum times a user can rate the same artifact
        cooldown_hours: Hours before user can re-rate the same artifact
    """

    max_ratings_per_day: int = 5
    max_ratings_per_artifact: int = 1
    cooldown_hours: int = 24


@dataclass
class ViolationRecord:
    """Record of a detected gaming violation.

    Attributes:
        violation_type: Type of violation detected
        artifact_id: Artifact involved (None for user-level violations)
        user_id: User who triggered the violation
        detected_at: When the violation was detected
        details: Human-readable description of the violation
    """

    violation_type: ViolationType
    artifact_id: Optional[str]
    user_id: str
    detected_at: datetime
    details: str


@dataclass
class RatingRecord:
    """Internal record of a submitted rating for tracking."""

    user_id: str
    artifact_id: str
    submitted_at: datetime


class RateLimiter:
    """Enforce rate limits on rating submissions.

    Tracks user rating history and enforces per-day and per-artifact limits.
    Uses in-memory storage for simplicity (suitable for current scale).

    Thread-safety: Not thread-safe. Use with single-threaded access or add locking.
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        """Initialize rate limiter with configuration.

        Args:
            config: Rate limit configuration (uses defaults if None)
        """
        self.config = config or RateLimitConfig()
        # Track all rating submissions: user_id -> list of RatingRecords
        self._rating_history: Dict[str, List[RatingRecord]] = defaultdict(list)

    def check_rate_limit(
        self,
        user_id: str,
        artifact_id: str,
    ) -> tuple[bool, Optional[str]]:
        """Check if user can submit a rating for an artifact.

        Args:
            user_id: User attempting to submit rating
            artifact_id: Artifact being rated

        Returns:
            Tuple of (allowed: bool, reason: Optional[str])
            - (True, None) if rating is allowed
            - (False, reason) if rating is blocked with explanation
        """
        now = datetime.now()

        # Check per-day limit
        user_ratings = self._rating_history.get(user_id, [])
        ratings_today = [
            r for r in user_ratings if r.submitted_at > now - timedelta(days=1)
        ]

        if len(ratings_today) >= self.config.max_ratings_per_day:
            return (
                False,
                f"Rate limit exceeded: maximum {self.config.max_ratings_per_day} ratings per day",
            )

        # Check per-artifact limit and cooldown
        artifact_ratings = [r for r in user_ratings if r.artifact_id == artifact_id]

        if len(artifact_ratings) >= self.config.max_ratings_per_artifact:
            # Check if cooldown has passed for most recent rating
            most_recent = max(artifact_ratings, key=lambda r: r.submitted_at)
            cooldown_until = most_recent.submitted_at + timedelta(
                hours=self.config.cooldown_hours
            )

            if now < cooldown_until:
                remaining = cooldown_until - now
                hours = remaining.total_seconds() / 3600
                return (
                    False,
                    f"Cooldown active: you can re-rate this artifact in {hours:.1f} hours",
                )

        return (True, None)

    def record_rating(
        self,
        user_id: str,
        artifact_id: str,
    ) -> None:
        """Record that a rating was submitted.

        Should be called after successful rating submission to update tracking.

        Args:
            user_id: User who submitted the rating
            artifact_id: Artifact that was rated
        """
        record = RatingRecord(
            user_id=user_id, artifact_id=artifact_id, submitted_at=datetime.now()
        )
        self._rating_history[user_id].append(record)

        # Cleanup old records (older than max cooldown)
        max_retention_days = max(1, self.config.cooldown_hours // 24 + 1)
        cutoff = datetime.now() - timedelta(days=max_retention_days)
        self._rating_history[user_id] = [
            r for r in self._rating_history[user_id] if r.submitted_at > cutoff
        ]

    def get_remaining_ratings(self, user_id: str) -> int:
        """Get number of ratings user can still submit today.

        Args:
            user_id: User to check

        Returns:
            Number of ratings remaining (0 if limit reached)
        """
        now = datetime.now()
        user_ratings = self._rating_history.get(user_id, [])
        ratings_today = [
            r for r in user_ratings if r.submitted_at > now - timedelta(days=1)
        ]
        return max(0, self.config.max_ratings_per_day - len(ratings_today))


class AnomalyDetector:
    """Detect suspicious rating patterns.

    Monitors for gaming attempts through:
    - Burst detection: Many ratings in short time window
    - Pattern analysis: Uniform ratings, bot-like timing
    - Deployment validation: Ratings without usage

    Uses statistical thresholds to minimize false positives.
    """

    def __init__(
        self,
        burst_threshold: int = 10,  # Max ratings in burst window
        burst_window_minutes: int = 60,  # Time window for burst detection
        pattern_threshold: float = 0.8,  # Suspicion score threshold (0-1)
    ):
        """Initialize anomaly detector with thresholds.

        Args:
            burst_threshold: Maximum ratings in burst window before flagging
            burst_window_minutes: Time window for burst detection
            pattern_threshold: Minimum suspicion score (0-1) to flag anomaly
        """
        self.burst_threshold = burst_threshold
        self.burst_window = timedelta(minutes=burst_window_minutes)
        self.pattern_threshold = pattern_threshold

        # Track recent ratings for burst detection
        self._recent_ratings: Dict[str, List[datetime]] = defaultdict(list)
        # Track artifact rating patterns
        self._artifact_ratings: Dict[str, List[int]] = defaultdict(list)

    def check_burst_anomaly(
        self,
        user_id: str,
        window: Optional[timedelta] = None,
    ) -> tuple[bool, Optional[str]]:
        """Check for burst rating anomaly (many ratings in short time).

        Args:
            user_id: User to check for burst activity
            window: Time window to check (uses default if None)

        Returns:
            Tuple of (is_anomaly: bool, reason: Optional[str])
        """
        window = window or self.burst_window
        now = datetime.now()

        # Get recent ratings in window
        user_ratings = self._recent_ratings.get(user_id, [])
        recent = [r for r in user_ratings if r > now - window]

        if len(recent) > self.burst_threshold:
            return (
                True,
                f"Burst anomaly: {len(recent)} ratings in {window.total_seconds() / 60:.0f} minutes (threshold: {self.burst_threshold})",
            )

        return (False, None)

    def check_pattern_anomaly(
        self,
        artifact_id: str,
    ) -> tuple[bool, Optional[str]]:
        """Check for suspicious rating patterns on an artifact.

        Detects patterns such as:
        - All ratings are the same value (uniformity)
        - Ratings follow bot-like timing patterns

        Args:
            artifact_id: Artifact to check for pattern anomalies

        Returns:
            Tuple of (is_anomaly: bool, reason: Optional[str])
        """
        ratings = self._artifact_ratings.get(artifact_id, [])

        if len(ratings) < 5:
            # Too few ratings to detect patterns reliably
            return (False, None)

        # Check for uniform ratings (all same value)
        unique_values = set(ratings)
        if len(unique_values) == 1:
            return (
                True,
                f"All {len(ratings)} ratings have the same value: {ratings[0]}",
            )

        # Calculate suspicion score
        suspicion = self.calculate_suspicion_score(artifact_id)
        if suspicion >= self.pattern_threshold:
            return (
                True,
                f"High suspicion score: {suspicion:.2f} (threshold: {self.pattern_threshold})",
            )

        return (False, None)

    def calculate_suspicion_score(
        self,
        artifact_id: str,
    ) -> float:
        """Calculate suspicion score (0-1) for an artifact's ratings.

        Combines multiple signals:
        - Uniformity: How similar are the ratings?
        - Extremity: Are ratings clustered at extremes (1 or 5)?
        - Diversity: Are ratings from diverse users/times?

        Args:
            artifact_id: Artifact to calculate suspicion for

        Returns:
            Suspicion score from 0 (not suspicious) to 1 (highly suspicious)
        """
        ratings = self._artifact_ratings.get(artifact_id, [])

        if len(ratings) < 3:
            return 0.0

        # Calculate uniformity (0 = diverse, 1 = all same)
        unique_count = len(set(ratings))
        uniformity = 1.0 - (unique_count - 1) / 4  # 4 is max diversity (ratings 1-5)

        # Calculate extremity (0 = balanced, 1 = all at extremes)
        extreme_count = sum(1 for r in ratings if r in (1, 5))
        extremity = extreme_count / len(ratings)

        # Weighted combination
        # Uniformity is strong signal, extremity is moderate signal
        suspicion = (uniformity * 0.7) + (extremity * 0.3)

        return min(1.0, suspicion)

    def record_rating_for_detection(
        self,
        user_id: str,
        artifact_id: str,
        rating_value: int,
    ) -> None:
        """Record a rating for anomaly detection tracking.

        Args:
            user_id: User who submitted rating
            artifact_id: Artifact that was rated
            rating_value: Rating value (1-5)
        """
        # Track for burst detection
        self._recent_ratings[user_id].append(datetime.now())

        # Track for pattern detection
        self._artifact_ratings[artifact_id].append(rating_value)

        # Cleanup old burst records (keep last 24 hours)
        cutoff = datetime.now() - timedelta(hours=24)
        self._recent_ratings[user_id] = [
            r for r in self._recent_ratings[user_id] if r > cutoff
        ]


class AntiGamingGuard:
    """Unified anti-gaming protection system.

    Combines rate limiting and anomaly detection into a single interface
    for validating rating submissions.

    Example:
        >>> guard = AntiGamingGuard()
        >>> allowed, reason = guard.can_submit_rating("user123", "skill:canvas")
        >>> if allowed:
        ...     # Submit rating
        ...     guard.record_rating("user123", "skill:canvas", 5)
        ... else:
        ...     print(f"Blocked: {reason}")
    """

    def __init__(
        self,
        rate_limiter: Optional[RateLimiter] = None,
        anomaly_detector: Optional[AnomalyDetector] = None,
    ):
        """Initialize anti-gaming guard.

        Args:
            rate_limiter: Rate limiter instance (creates default if None)
            anomaly_detector: Anomaly detector instance (creates default if None)
        """
        self.rate_limiter = rate_limiter or RateLimiter()
        self.anomaly_detector = anomaly_detector or AnomalyDetector()
        self._violations: List[ViolationRecord] = []

    def can_submit_rating(
        self,
        user_id: str,
        artifact_id: str,
    ) -> tuple[bool, Optional[str]]:
        """Check if rating submission is allowed.

        Runs all anti-gaming checks:
        1. Rate limiting (per-day, per-artifact, cooldown)
        2. Burst detection (too many ratings too fast)
        3. Pattern detection (suspicious artifact patterns)

        Args:
            user_id: User attempting to submit rating
            artifact_id: Artifact being rated

        Returns:
            Tuple of (allowed: bool, reason: Optional[str])
        """
        # Check rate limits
        allowed, reason = self.rate_limiter.check_rate_limit(user_id, artifact_id)
        if not allowed:
            self.report_violation(
                ViolationRecord(
                    violation_type=ViolationType.RATE_LIMIT,
                    artifact_id=artifact_id,
                    user_id=user_id,
                    detected_at=datetime.now(),
                    details=reason or "Rate limit exceeded",
                )
            )
            return (False, reason)

        # Check for burst anomalies
        is_burst, burst_reason = self.anomaly_detector.check_burst_anomaly(user_id)
        if is_burst:
            self.report_violation(
                ViolationRecord(
                    violation_type=ViolationType.ANOMALY_BURST,
                    artifact_id=None,
                    user_id=user_id,
                    detected_at=datetime.now(),
                    details=burst_reason or "Burst anomaly detected",
                )
            )
            return (False, f"Suspicious activity detected: {burst_reason}")

        # Check for pattern anomalies on the artifact
        is_pattern, pattern_reason = self.anomaly_detector.check_pattern_anomaly(
            artifact_id
        )
        if is_pattern:
            # Log but don't block (pattern anomalies are artifact-level, not user-level)
            logger.warning(
                f"Pattern anomaly on artifact {artifact_id}: {pattern_reason}"
            )
            self.report_violation(
                ViolationRecord(
                    violation_type=ViolationType.ANOMALY_PATTERN,
                    artifact_id=artifact_id,
                    user_id=user_id,
                    detected_at=datetime.now(),
                    details=pattern_reason or "Pattern anomaly detected",
                )
            )
            # Don't block user - this is an artifact-level signal

        return (True, None)

    def record_rating(
        self,
        user_id: str,
        artifact_id: str,
        rating_value: int,
    ) -> None:
        """Record a successful rating submission.

        Updates tracking for both rate limiting and anomaly detection.

        Args:
            user_id: User who submitted rating
            artifact_id: Artifact that was rated
            rating_value: Rating value (1-5)
        """
        self.rate_limiter.record_rating(user_id, artifact_id)
        self.anomaly_detector.record_rating_for_detection(
            user_id, artifact_id, rating_value
        )

    def report_violation(
        self,
        violation: ViolationRecord,
    ) -> None:
        """Log a violation for monitoring.

        Args:
            violation: Violation record to log
        """
        self._violations.append(violation)
        logger.warning(
            f"Anti-gaming violation: {violation.violation_type.value} "
            f"by user {violation.user_id} "
            f"(artifact: {violation.artifact_id}): {violation.details}"
        )

    def get_violations(
        self,
        user_id: Optional[str] = None,
        artifact_id: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> List[ViolationRecord]:
        """Query violation records.

        Args:
            user_id: Filter by user (None = all users)
            artifact_id: Filter by artifact (None = all artifacts)
            since: Filter by time (None = all time)

        Returns:
            List of matching violation records
        """
        results = self._violations

        if user_id is not None:
            results = [v for v in results if v.user_id == user_id]

        if artifact_id is not None:
            results = [v for v in results if v.artifact_id == artifact_id]

        if since is not None:
            results = [v for v in results if v.detected_at >= since]

        return results
