"""Tests for score decay system."""

import pytest
from datetime import datetime, timedelta, timezone

from skillmeat.core.scoring.score_decay import (
    ScoreDecay,
    DecayedScore,
    DECAYING_SOURCES,
    NON_DECAYING_SOURCES,
)


class TestScoreDecay:
    """Tests for ScoreDecay class."""

    def test_init_defaults(self):
        """Test initialization with default parameters."""
        decay = ScoreDecay()
        assert decay.decay_rate == 0.05
        assert decay.max_decay_factor == 0.4

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        decay = ScoreDecay(decay_rate=0.10, max_decay_factor=0.5)
        assert decay.decay_rate == 0.10
        assert decay.max_decay_factor == 0.5

    def test_init_validation(self):
        """Test initialization parameter validation."""
        # Invalid decay rate
        with pytest.raises(ValueError, match="decay_rate must be 0-1"):
            ScoreDecay(decay_rate=-0.1)
        with pytest.raises(ValueError, match="decay_rate must be 0-1"):
            ScoreDecay(decay_rate=1.5)

        # Invalid max_decay_factor
        with pytest.raises(ValueError, match="max_decay_factor must be 0-1"):
            ScoreDecay(max_decay_factor=-0.1)
        with pytest.raises(ValueError, match="max_decay_factor must be 0-1"):
            ScoreDecay(max_decay_factor=1.5)

    def test_get_months_old_fresh(self):
        """Test calculating age of fresh score (0 months)."""
        decay = ScoreDecay()
        now = datetime.now(timezone.utc)
        months = decay.get_months_old(now, as_of=now)
        assert months == 0.0

    def test_get_months_old_one_month(self):
        """Test calculating age of 1-month-old score."""
        decay = ScoreDecay()
        now = datetime.now(timezone.utc)
        one_month_ago = now - timedelta(days=30)
        months = decay.get_months_old(one_month_ago, as_of=now)
        assert 0.9 <= months <= 1.1  # ~1 month (allowing for rounding)

    def test_get_months_old_three_months(self):
        """Test calculating age of 3-month-old score."""
        decay = ScoreDecay()
        now = datetime.now(timezone.utc)
        three_months_ago = now - timedelta(days=90)
        months = decay.get_months_old(three_months_ago, as_of=now)
        assert 2.9 <= months <= 3.1  # ~3 months

    def test_get_months_old_six_months(self):
        """Test calculating age of 6-month-old score."""
        decay = ScoreDecay()
        now = datetime.now(timezone.utc)
        six_months_ago = now - timedelta(days=180)
        months = decay.get_months_old(six_months_ago, as_of=now)
        assert 5.9 <= months <= 6.1  # ~6 months

    def test_get_months_old_twelve_months(self):
        """Test calculating age of 12-month-old score."""
        decay = ScoreDecay()
        now = datetime.now(timezone.utc)
        twelve_months_ago = now - timedelta(days=365)
        months = decay.get_months_old(twelve_months_ago, as_of=now)
        assert 11.9 <= months <= 12.5  # ~12 months (365/30 = 12.17)

    def test_get_months_old_timezone_naive(self):
        """Test handling of timezone-naive datetimes."""
        decay = ScoreDecay()
        # Naive datetimes should be treated as UTC
        naive_now = datetime.now()
        naive_past = naive_now - timedelta(days=60)
        months = decay.get_months_old(naive_past, as_of=naive_now)
        assert 1.9 <= months <= 2.1  # ~2 months

    def test_get_months_old_future_date(self):
        """Test handling of future dates (edge case)."""
        decay = ScoreDecay()
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=30)
        months = decay.get_months_old(future, as_of=now)
        assert months == 0.0  # Clamped to non-negative

    def test_calculate_decay_factor_fresh(self):
        """Test decay factor for fresh score (0 months)."""
        decay = ScoreDecay()
        now = datetime.now(timezone.utc)
        factor = decay.calculate_decay_factor(now, as_of=now)
        assert factor == 1.0  # No decay

    def test_calculate_decay_factor_three_months(self):
        """Test decay factor for 3-month-old score (~14% decay)."""
        decay = ScoreDecay()
        now = datetime.now(timezone.utc)
        three_months_ago = now - timedelta(days=90)
        factor = decay.calculate_decay_factor(three_months_ago, as_of=now)
        # (1 - 0.05) ^ 3 = 0.95 ^ 3 ≈ 0.857 (~14% decay)
        assert 0.85 <= factor <= 0.87

    def test_calculate_decay_factor_six_months(self):
        """Test decay factor for 6-month-old score (~26% decay)."""
        decay = ScoreDecay()
        now = datetime.now(timezone.utc)
        six_months_ago = now - timedelta(days=180)
        factor = decay.calculate_decay_factor(six_months_ago, as_of=now)
        # (1 - 0.05) ^ 6 = 0.95 ^ 6 ≈ 0.735 (~26% decay)
        assert 0.73 <= factor <= 0.75

    def test_calculate_decay_factor_twelve_months(self):
        """Test decay factor for 12-month-old score (~46% decay)."""
        decay = ScoreDecay()
        now = datetime.now(timezone.utc)
        twelve_months_ago = now - timedelta(days=365)
        factor = decay.calculate_decay_factor(twelve_months_ago, as_of=now)
        # (1 - 0.05) ^ 12 = 0.95 ^ 12 ≈ 0.540 (~46% decay)
        assert 0.53 <= factor <= 0.55

    def test_calculate_decay_factor_max_floor(self):
        """Test that decay factor doesn't go below max_decay_factor."""
        decay = ScoreDecay(max_decay_factor=0.4)
        now = datetime.now(timezone.utc)
        # Very old score (5 years)
        very_old = now - timedelta(days=365 * 5)
        factor = decay.calculate_decay_factor(very_old, as_of=now)
        # Should be clamped to max_decay_factor
        assert factor == 0.4

    def test_apply_decay_fresh_score(self):
        """Test applying decay to fresh score (no decay)."""
        decay = ScoreDecay()
        now = datetime.now(timezone.utc)
        result = decay.apply_decay(80.0, now, as_of=now)

        assert isinstance(result, DecayedScore)
        assert result.original_score == 80.0
        assert result.decayed_score == 80.0  # No decay
        assert result.decay_factor == 1.0
        assert result.months_old == 0.0

    def test_apply_decay_three_months(self):
        """Test applying decay to 3-month-old score."""
        decay = ScoreDecay()
        now = datetime.now(timezone.utc)
        three_months_ago = now - timedelta(days=90)
        result = decay.apply_decay(80.0, three_months_ago, as_of=now)

        assert result.original_score == 80.0
        # 80 * 0.857 ≈ 68.6
        assert 68.0 <= result.decayed_score <= 69.0
        assert 0.85 <= result.decay_factor <= 0.87
        assert 2.9 <= result.months_old <= 3.1

    def test_apply_decay_six_months(self):
        """Test applying decay to 6-month-old score."""
        decay = ScoreDecay()
        now = datetime.now(timezone.utc)
        six_months_ago = now - timedelta(days=180)
        result = decay.apply_decay(80.0, six_months_ago, as_of=now)

        assert result.original_score == 80.0
        # 80 * 0.735 ≈ 58.8
        assert 58.0 <= result.decayed_score <= 60.0
        assert 0.73 <= result.decay_factor <= 0.75
        assert 5.9 <= result.months_old <= 6.1

    def test_apply_decay_twelve_months(self):
        """Test applying decay to 12-month-old score."""
        decay = ScoreDecay()
        now = datetime.now(timezone.utc)
        twelve_months_ago = now - timedelta(days=365)
        result = decay.apply_decay(80.0, twelve_months_ago, as_of=now)

        assert result.original_score == 80.0
        # 80 * 0.540 ≈ 43.2
        assert 42.0 <= result.decayed_score <= 44.0
        assert 0.53 <= result.decay_factor <= 0.55

    def test_apply_decay_max_floor(self):
        """Test that decayed score doesn't go below 40% of original (60% max decay)."""
        decay = ScoreDecay(max_decay_factor=0.4)
        now = datetime.now(timezone.utc)
        very_old = now - timedelta(days=365 * 5)
        result = decay.apply_decay(80.0, very_old, as_of=now)

        assert result.original_score == 80.0
        # 80 * 0.4 = 32.0 (floor)
        assert result.decayed_score == 32.0
        assert result.decay_factor == 0.4

    def test_apply_decay_edge_cases(self):
        """Test apply_decay with edge case scores."""
        decay = ScoreDecay()
        now = datetime.now(timezone.utc)
        three_months_ago = now - timedelta(days=90)

        # Score of 0
        result = decay.apply_decay(0.0, three_months_ago, as_of=now)
        assert result.decayed_score == 0.0

        # Score of 100
        result = decay.apply_decay(100.0, three_months_ago, as_of=now)
        assert 85.0 <= result.decayed_score <= 87.0

    def test_apply_decay_validation(self):
        """Test apply_decay score validation."""
        decay = ScoreDecay()
        now = datetime.now(timezone.utc)

        with pytest.raises(ValueError, match="score must be 0-100"):
            decay.apply_decay(-10.0, now)

        with pytest.raises(ValueError, match="score must be 0-100"):
            decay.apply_decay(150.0, now)

    def test_should_refresh_below_threshold(self):
        """Test should_refresh returns False for recent scores."""
        decay = ScoreDecay()
        now = datetime.now(timezone.utc)
        recent = now - timedelta(days=30)

        assert decay.should_refresh(recent, threshold_days=60) is False

    def test_should_refresh_above_threshold(self):
        """Test should_refresh returns True for old scores."""
        decay = ScoreDecay()
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=70)

        assert decay.should_refresh(old, threshold_days=60) is True

    def test_should_refresh_exact_threshold(self):
        """Test should_refresh at exact threshold boundary."""
        decay = ScoreDecay()
        now = datetime.now(timezone.utc)
        exactly_60_days = now - timedelta(days=60)

        # Exactly at threshold should refresh (threshold is inclusive via >)
        # This is correct behavior - a score that's exactly 60 days old should be refreshed
        assert decay.should_refresh(exactly_60_days, threshold_days=60) is True

    def test_should_refresh_validation(self):
        """Test should_refresh threshold validation."""
        decay = ScoreDecay()
        now = datetime.now(timezone.utc)

        with pytest.raises(ValueError, match="threshold_days must be >= 0"):
            decay.should_refresh(now, threshold_days=-1)

    def test_decayed_score_validation(self):
        """Test DecayedScore dataclass validation."""
        now = datetime.now(timezone.utc)

        # Valid score
        DecayedScore(
            original_score=80.0,
            decayed_score=68.0,
            decay_factor=0.85,
            months_old=3.0,
            last_updated=now,
            computed_at=now,
        )

        # Invalid original_score
        with pytest.raises(ValueError, match="original_score must be 0-100"):
            DecayedScore(
                original_score=-10.0,
                decayed_score=68.0,
                decay_factor=0.85,
                months_old=3.0,
                last_updated=now,
                computed_at=now,
            )

        # Invalid decayed_score
        with pytest.raises(ValueError, match="decayed_score must be 0-100"):
            DecayedScore(
                original_score=80.0,
                decayed_score=150.0,
                decay_factor=0.85,
                months_old=3.0,
                last_updated=now,
                computed_at=now,
            )

        # Invalid decay_factor
        with pytest.raises(ValueError, match="decay_factor must be 0-1"):
            DecayedScore(
                original_score=80.0,
                decayed_score=68.0,
                decay_factor=1.5,
                months_old=3.0,
                last_updated=now,
                computed_at=now,
            )

        # Invalid months_old
        with pytest.raises(ValueError, match="months_old must be >= 0"):
            DecayedScore(
                original_score=80.0,
                decayed_score=68.0,
                decay_factor=0.85,
                months_old=-1.0,
                last_updated=now,
                computed_at=now,
            )


class TestDecayingSources:
    """Tests for DECAYING_SOURCES and NON_DECAYING_SOURCES constants."""

    def test_decaying_sources_defined(self):
        """Test DECAYING_SOURCES contains expected source types."""
        assert "github_stars" in DECAYING_SOURCES
        assert "registry" in DECAYING_SOURCES
        assert "community" in DECAYING_SOURCES

    def test_non_decaying_sources_defined(self):
        """Test NON_DECAYING_SOURCES contains expected source types."""
        assert "user_rating" in NON_DECAYING_SOURCES
        assert "maintenance" in NON_DECAYING_SOURCES

    def test_sources_mutually_exclusive(self):
        """Test that DECAYING_SOURCES and NON_DECAYING_SOURCES don't overlap."""
        assert DECAYING_SOURCES.isdisjoint(NON_DECAYING_SOURCES)


class TestIntegration:
    """Integration tests for ScoreDecay with ScoreAggregator."""

    def test_decay_example_progression(self):
        """Test documented example decay progression matches formula."""
        decay = ScoreDecay()
        now = datetime.now(timezone.utc)
        original_score = 80.0

        # Fresh (0 months): 80.0 (100% of original)
        result = decay.apply_decay(original_score, now, as_of=now)
        assert result.decayed_score == 80.0

        # 3 months: 68.6 (85.7% of original, 14.3% decay)
        three_months = now - timedelta(days=90)
        result = decay.apply_decay(original_score, three_months, as_of=now)
        assert 68.0 <= result.decayed_score <= 69.0

        # 6 months: 58.8 (73.5% of original, 26.5% decay)
        six_months = now - timedelta(days=180)
        result = decay.apply_decay(original_score, six_months, as_of=now)
        assert 58.0 <= result.decayed_score <= 60.0

        # 12 months: 43.2 (54.0% of original, 46.0% decay)
        twelve_months = now - timedelta(days=365)
        result = decay.apply_decay(original_score, twelve_months, as_of=now)
        assert 42.0 <= result.decayed_score <= 44.0

        # 18+ months: 32.0 (40.0% of original, 60% decay - floor reached)
        eighteen_months = now - timedelta(days=365 * 1.5)
        result = decay.apply_decay(original_score, eighteen_months, as_of=now)
        # Should be at or near floor (0.4 * 80 = 32.0)
        assert 30.0 <= result.decayed_score <= 33.0
