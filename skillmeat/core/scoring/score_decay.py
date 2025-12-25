"""Score decay system for time-based freshness adjustments.

This module implements a time-based decay system for community scores to ensure
freshness. Older scores receive a progressive decay penalty, encouraging regular
updates while preventing stale data from dominating rankings.

The decay system applies only to community-sourced scores (GitHub stars, registry data)
and does not affect user ratings or objective maintenance signals.

Example:
    >>> from skillmeat.core.scoring.score_decay import ScoreDecay
    >>> from datetime import datetime, timedelta, timezone
    >>>
    >>> decay = ScoreDecay()
    >>> last_updated = datetime.now(timezone.utc) - timedelta(days=90)  # 3 months old
    >>> result = decay.apply_decay(80.0, last_updated)
    >>> print(f"Original: {result.original_score}, Decayed: {result.decayed_score:.1f}")
    Original: 80.0, Decayed: 68.6
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Source types that receive decay treatment
DECAYING_SOURCES = {"github_stars", "registry", "community"}

# Source types that do NOT decay (user data and objective metrics)
NON_DECAYING_SOURCES = {"user_rating", "maintenance"}


@dataclass
class DecayedScore:
    """A score with time-based decay applied.

    Attributes:
        original_score: Original score before decay (0-100)
        decayed_score: Score after decay applied (0-100)
        decay_factor: Decay multiplier (0-1), where 1 = no decay
        months_old: Age of the score in months (fractional)
        last_updated: Timestamp when score was last updated
        computed_at: Timestamp when decay was computed
    """

    original_score: float  # 0-100
    decayed_score: float  # 0-100
    decay_factor: float  # 0-1
    months_old: float
    last_updated: datetime
    computed_at: datetime

    def __post_init__(self):
        """Validate score and factor ranges."""
        if not 0 <= self.original_score <= 100:
            raise ValueError(f"original_score must be 0-100, got {self.original_score}")
        if not 0 <= self.decayed_score <= 100:
            raise ValueError(f"decayed_score must be 0-100, got {self.decayed_score}")
        if not 0 <= self.decay_factor <= 1:
            raise ValueError(f"decay_factor must be 0-1, got {self.decay_factor}")
        if self.months_old < 0:
            raise ValueError(f"months_old must be >= 0, got {self.months_old}")


class ScoreDecay:
    """Apply time-based decay to scores for freshness.

    Implements a 5%/month decay rate with a maximum decay floor of 60%.
    This ensures that very old scores don't completely disappear, but are
    significantly downweighted compared to fresh data.

    The decay formula is:
        decay_factor = (1 - decay_rate) ^ months_old
        decay_factor = max(decay_factor, max_decay_factor)
        decayed_score = original_score * decay_factor

    Example decay progression (5%/month, 80.0 original score):
        - Fresh (0 months): 80.0 (100% of original)
        - 3 months: 68.6 (85.7% of original, 14.3% decay)
        - 6 months: 58.8 (73.5% of original, 26.5% decay)
        - 12 months: 43.2 (54.0% of original, 46.0% decay)
        - 18+ months: 32.0 (40.0% of original, 60% decay - floor reached)

    Attributes:
        decay_rate: Monthly decay rate (default: 0.05 = 5%)
        max_decay_factor: Minimum decay multiplier (default: 0.4 = 60% max decay)
    """

    # Default decay rate: 5% per month
    DEFAULT_DECAY_RATE = 0.05

    # Maximum decay (score won't go below this percentage of original)
    MAX_DECAY_FACTOR = 0.4  # 60% maximum decay

    def __init__(
        self,
        decay_rate: float = DEFAULT_DECAY_RATE,
        max_decay_factor: float = MAX_DECAY_FACTOR,
    ):
        """Initialize decay calculator.

        Args:
            decay_rate: Monthly decay rate (default: 0.05 = 5%)
            max_decay_factor: Minimum decay multiplier (default: 0.4 = 60% max decay)

        Raises:
            ValueError: If decay_rate not in [0, 1] or max_decay_factor not in [0, 1]

        Example:
            >>> # More aggressive decay (10%/month)
            >>> decay = ScoreDecay(decay_rate=0.10)
            >>>
            >>> # More lenient maximum decay (only 40% max)
            >>> decay = ScoreDecay(max_decay_factor=0.6)
        """
        if not 0 <= decay_rate <= 1:
            raise ValueError(f"decay_rate must be 0-1, got {decay_rate}")
        if not 0 <= max_decay_factor <= 1:
            raise ValueError(f"max_decay_factor must be 0-1, got {max_decay_factor}")

        self.decay_rate = decay_rate
        self.max_decay_factor = max_decay_factor

        logger.debug(
            f"Initialized ScoreDecay with rate={decay_rate:.2%}, "
            f"max_decay_factor={max_decay_factor:.2f}"
        )

    def calculate_decay_factor(
        self,
        last_updated: datetime,
        as_of: Optional[datetime] = None,
    ) -> float:
        """Calculate decay factor based on age.

        Formula: decay_factor = (1 - decay_rate) ^ months_old
        Clamped to max_decay_factor minimum to prevent total score collapse.

        Args:
            last_updated: When the score was last updated
            as_of: Calculate decay as of this time (default: now)

        Returns:
            Float between max_decay_factor and 1.0

        Example:
            >>> from datetime import datetime, timedelta, timezone
            >>> decay = ScoreDecay()
            >>> now = datetime.now(timezone.utc)
            >>> three_months_ago = now - timedelta(days=90)
            >>> factor = decay.calculate_decay_factor(three_months_ago)
            >>> assert 0.85 <= factor <= 0.87  # ~14% decay after 3 months
        """
        months_old = self.get_months_old(last_updated, as_of)

        # Apply exponential decay formula
        decay_factor = (1 - self.decay_rate) ** months_old

        # Apply floor to prevent excessive decay
        decay_factor = max(decay_factor, self.max_decay_factor)

        logger.debug(
            f"Calculated decay factor for {months_old:.1f} months: {decay_factor:.3f}"
        )

        return decay_factor

    def apply_decay(
        self,
        score: float,
        last_updated: datetime,
        as_of: Optional[datetime] = None,
    ) -> DecayedScore:
        """Apply decay to a score.

        Args:
            score: Original score (0-100)
            last_updated: When the score was last updated
            as_of: Calculate decay as of this time (default: now)

        Returns:
            DecayedScore with original and decayed values

        Raises:
            ValueError: If score not in [0, 100]

        Example:
            >>> from datetime import datetime, timedelta, timezone
            >>> decay = ScoreDecay()
            >>> now = datetime.now(timezone.utc)
            >>> six_months_ago = now - timedelta(days=180)
            >>> result = decay.apply_decay(80.0, six_months_ago)
            >>> print(f"Score decayed from {result.original_score} to {result.decayed_score:.1f}")
            Score decayed from 80.0 to 58.8
        """
        if not 0 <= score <= 100:
            raise ValueError(f"score must be 0-100, got {score}")

        computed_at = as_of if as_of else datetime.now(timezone.utc)
        months_old = self.get_months_old(last_updated, as_of)
        decay_factor = self.calculate_decay_factor(last_updated, as_of)

        decayed_score = score * decay_factor

        # Clamp to valid range (should not be needed, but safety check)
        decayed_score = min(100.0, max(0.0, decayed_score))

        logger.debug(
            f"Applied decay: {score:.1f} → {decayed_score:.1f} "
            f"(factor={decay_factor:.3f}, age={months_old:.1f} months)"
        )

        return DecayedScore(
            original_score=score,
            decayed_score=decayed_score,
            decay_factor=decay_factor,
            months_old=months_old,
            last_updated=last_updated,
            computed_at=computed_at,
        )

    def should_refresh(
        self,
        last_updated: datetime,
        threshold_days: int = 60,
    ) -> bool:
        """Determine if a score should be refreshed.

        Returns True if score is older than threshold_days, indicating
        that fetching fresh data would be beneficial.

        Args:
            last_updated: When the score was last updated
            threshold_days: Age threshold in days (default: 60)

        Returns:
            True if score age exceeds threshold

        Example:
            >>> from datetime import datetime, timedelta, timezone
            >>> decay = ScoreDecay()
            >>> now = datetime.now(timezone.utc)
            >>> old_score = now - timedelta(days=70)
            >>> assert decay.should_refresh(old_score, threshold_days=60) is True
            >>> recent_score = now - timedelta(days=30)
            >>> assert decay.should_refresh(recent_score, threshold_days=60) is False
        """
        if threshold_days < 0:
            raise ValueError(f"threshold_days must be >= 0, got {threshold_days}")

        now = datetime.now(timezone.utc)
        age_days = (now - last_updated).total_seconds() / 86400

        should_refresh = age_days > threshold_days

        logger.debug(
            f"Refresh check: age={age_days:.1f} days, threshold={threshold_days} days, "
            f"should_refresh={should_refresh}"
        )

        return should_refresh

    def get_months_old(
        self,
        last_updated: datetime,
        as_of: Optional[datetime] = None,
    ) -> float:
        """Calculate how many months old a timestamp is.

        Uses a simple conversion of 30 days = 1 month for consistency.

        Args:
            last_updated: Timestamp to measure age of
            as_of: Calculate age as of this time (default: now)

        Returns:
            Age in months (fractional, e.g., 2.5 months)

        Example:
            >>> from datetime import datetime, timedelta, timezone
            >>> decay = ScoreDecay()
            >>> now = datetime.now(timezone.utc)
            >>> three_months = now - timedelta(days=90)
            >>> age = decay.get_months_old(three_months)
            >>> assert 2.9 <= age <= 3.1  # ~3 months
        """
        if as_of is None:
            as_of = datetime.now(timezone.utc)

        # Handle timezone-naive datetimes by assuming UTC
        if last_updated.tzinfo is None:
            last_updated = last_updated.replace(tzinfo=timezone.utc)
        if as_of.tzinfo is None:
            as_of = as_of.replace(tzinfo=timezone.utc)

        age_seconds = (as_of - last_updated).total_seconds()
        age_days = age_seconds / 86400  # seconds per day
        months_old = age_days / 30.0  # 30 days = 1 month

        # Clamp to non-negative (future dates should not happen, but safety check)
        months_old = max(0.0, months_old)

        return months_old
