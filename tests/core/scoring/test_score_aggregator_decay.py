"""Tests for ScoreAggregator integration with ScoreDecay."""

import pytest
from datetime import datetime, timedelta, timezone

from skillmeat.core.scoring.score_aggregator import (
    ScoreAggregator,
    ScoreSource,
    AggregatedScore,
)
from skillmeat.core.scoring.score_decay import ScoreDecay


class TestScoreAggregatorDecayIntegration:
    """Tests for aggregate_with_decay method."""

    def test_aggregate_with_decay_no_decay_applied(self):
        """Test that fresh scores receive no decay."""
        aggregator = ScoreAggregator()
        decay = ScoreDecay()
        now = datetime.now(timezone.utc)

        sources = [
            ScoreSource("github_stars", 80.0, 0.25, now, 150),
            ScoreSource("user_rating", 90.0, 0.4, now, 5),
        ]

        result = aggregator.aggregate_with_decay(sources, decay)

        assert isinstance(result, AggregatedScore)
        assert result.source_count == 2
        # With fresh scores, result should match non-decay aggregation
        result_no_decay = aggregator.aggregate(sources)
        assert abs(result.final_score - result_no_decay.final_score) < 0.1

    def test_aggregate_with_decay_applies_to_github_stars(self):
        """Test that decay is applied to github_stars source."""
        aggregator = ScoreAggregator()
        decay = ScoreDecay()
        now = datetime.now(timezone.utc)
        three_months_ago = now - timedelta(days=90)

        sources = [
            ScoreSource("github_stars", 80.0, 0.25, three_months_ago, 150),
            ScoreSource("user_rating", 90.0, 0.4, now, 5),
        ]

        result = aggregator.aggregate_with_decay(sources, decay)

        # GitHub stars should have decayed (~14% decay after 3 months)
        # Original: 80, Decayed: ~68.6
        # Without decay, aggregation would be higher
        result_no_decay = aggregator.aggregate(sources)
        assert result.final_score < result_no_decay.final_score

    def test_aggregate_with_decay_applies_to_registry(self):
        """Test that decay is applied to registry source."""
        aggregator = ScoreAggregator()
        decay = ScoreDecay()
        now = datetime.now(timezone.utc)
        six_months_ago = now - timedelta(days=180)

        sources = [
            ScoreSource("registry", 75.0, 0.2, six_months_ago, 100),
            ScoreSource("user_rating", 85.0, 0.4, now, 10),
        ]

        result = aggregator.aggregate_with_decay(sources, decay)

        # Registry should have decayed (~26% decay after 6 months)
        result_no_decay = aggregator.aggregate(sources)
        assert result.final_score < result_no_decay.final_score

    def test_aggregate_with_decay_skips_user_rating(self):
        """Test that user_rating source is not decayed."""
        aggregator = ScoreAggregator()
        decay = ScoreDecay()
        now = datetime.now(timezone.utc)
        one_year_ago = now - timedelta(days=365)

        sources = [
            ScoreSource("user_rating", 90.0, 0.4, one_year_ago, 5),
        ]

        result = aggregator.aggregate_with_decay(sources, decay)

        # User rating should not decay, even when very old
        result_no_decay = aggregator.aggregate(sources)
        assert abs(result.final_score - result_no_decay.final_score) < 0.1

    def test_aggregate_with_decay_skips_maintenance(self):
        """Test that maintenance source is not decayed."""
        aggregator = ScoreAggregator()
        decay = ScoreDecay()
        now = datetime.now(timezone.utc)
        one_year_ago = now - timedelta(days=365)

        sources = [
            ScoreSource("maintenance", 70.0, 0.15, one_year_ago, 1),
        ]

        result = aggregator.aggregate_with_decay(sources, decay)

        # Maintenance should not decay
        result_no_decay = aggregator.aggregate(sources)
        assert abs(result.final_score - result_no_decay.final_score) < 0.1

    def test_aggregate_with_decay_mixed_sources(self):
        """Test decay with mixed decaying and non-decaying sources."""
        aggregator = ScoreAggregator()
        decay = ScoreDecay()
        now = datetime.now(timezone.utc)
        six_months_ago = now - timedelta(days=180)

        sources = [
            ScoreSource("github_stars", 80.0, 0.25, six_months_ago, 150),
            ScoreSource("registry", 75.0, 0.2, six_months_ago, 100),
            ScoreSource("user_rating", 90.0, 0.4, now, 5),
            ScoreSource("maintenance", 70.0, 0.15, six_months_ago, 1),
        ]

        result = aggregator.aggregate_with_decay(sources, decay)

        # GitHub stars and registry should decay, user_rating and maintenance should not
        result_no_decay = aggregator.aggregate(sources)
        assert result.final_score < result_no_decay.final_score
        assert result.source_count == 4

    def test_aggregate_with_decay_uses_default_decay(self):
        """Test that default decay calculator is used when none provided."""
        aggregator = ScoreAggregator()
        now = datetime.now(timezone.utc)
        three_months_ago = now - timedelta(days=90)

        sources = [
            ScoreSource("github_stars", 80.0, 0.25, three_months_ago, 150),
        ]

        # Call without explicit decay calculator (should use default)
        result = aggregator.aggregate_with_decay(sources)

        assert isinstance(result, AggregatedScore)
        # Should have applied decay (final score lower than original)
        result_no_decay = aggregator.aggregate(sources)
        assert result.final_score < result_no_decay.final_score

    def test_aggregate_with_decay_custom_decay_rate(self):
        """Test aggregate_with_decay with custom decay rate."""
        aggregator = ScoreAggregator()
        # More aggressive decay (10%/month instead of 5%)
        aggressive_decay = ScoreDecay(decay_rate=0.10)
        now = datetime.now(timezone.utc)
        three_months_ago = now - timedelta(days=90)

        sources = [
            ScoreSource("github_stars", 80.0, 0.25, three_months_ago, 150),
        ]

        result_aggressive = aggregator.aggregate_with_decay(sources, aggressive_decay)
        result_default = aggregator.aggregate_with_decay(sources)

        # Aggressive decay should result in lower final score
        assert result_aggressive.final_score < result_default.final_score

    def test_aggregate_with_decay_empty_sources(self):
        """Test aggregate_with_decay with empty sources list."""
        aggregator = ScoreAggregator()
        decay = ScoreDecay()

        result = aggregator.aggregate_with_decay([], decay)

        # Should return prior mean (same as regular aggregate)
        assert result.final_score == aggregator.prior_mean
        assert result.source_count == 0

    def test_aggregate_with_decay_preserves_confidence_calculation(self):
        """Test that decay doesn't break confidence calculation."""
        aggregator = ScoreAggregator()
        decay = ScoreDecay()
        now = datetime.now(timezone.utc)
        three_months_ago = now - timedelta(days=90)

        sources = [
            ScoreSource("github_stars", 80.0, 0.25, three_months_ago, 150),
            ScoreSource("user_rating", 90.0, 0.4, now, 5),
        ]

        result = aggregator.aggregate_with_decay(sources, decay)

        # Confidence should still be valid (0-1 range)
        assert 0 <= result.confidence <= 1
        assert result.confidence > 0  # Should have some confidence with data

    def test_aggregate_with_decay_very_old_score(self):
        """Test decay with very old score (hits max decay floor)."""
        aggregator = ScoreAggregator()
        decay = ScoreDecay()
        now = datetime.now(timezone.utc)
        five_years_ago = now - timedelta(days=365 * 5)

        sources = [
            ScoreSource("github_stars", 80.0, 0.25, five_years_ago, 150),
            ScoreSource("user_rating", 90.0, 0.4, now, 5),
        ]

        result = aggregator.aggregate_with_decay(sources, decay)

        # Very old GitHub stars should hit max decay floor (40%)
        # 80 * 0.4 = 32.0
        # Should still produce valid aggregated score
        assert 0 <= result.final_score <= 100
        assert result.source_count == 2


class TestRealWorldScenarios:
    """Real-world scenario tests."""

    def test_stale_popular_artifact(self):
        """Test artifact with high stars but stale data."""
        aggregator = ScoreAggregator()
        decay = ScoreDecay()
        now = datetime.now(timezone.utc)
        one_year_ago = now - timedelta(days=365)

        sources = [
            # High stars but very old
            ScoreSource("github_stars", 95.0, 0.25, one_year_ago, 500),
            # Medium user rating, recent
            ScoreSource("user_rating", 70.0, 0.4, now, 8),
        ]

        result = aggregator.aggregate_with_decay(sources, decay)

        # Old stars should be significantly decayed (~46% decay)
        # 95 * 0.54 ≈ 51.3
        # Final score should favor fresher user rating
        result_no_decay = aggregator.aggregate(sources)
        assert result.final_score < result_no_decay.final_score

    def test_fresh_trending_artifact(self):
        """Test newly popular artifact with fresh data."""
        aggregator = ScoreAggregator()
        decay = ScoreDecay()
        now = datetime.now(timezone.utc)

        sources = [
            # Fresh high stars
            ScoreSource("github_stars", 85.0, 0.25, now, 200),
            # Fresh registry data
            ScoreSource("registry", 80.0, 0.2, now, 50),
            # Fresh user rating
            ScoreSource("user_rating", 88.0, 0.4, now, 12),
        ]

        result = aggregator.aggregate_with_decay(sources, decay)

        # All fresh, so decay should have minimal effect
        result_no_decay = aggregator.aggregate(sources)
        assert abs(result.final_score - result_no_decay.final_score) < 1.0

    def test_mixed_age_sources(self):
        """Test artifact with mixed-age sources."""
        aggregator = ScoreAggregator()
        decay = ScoreDecay()
        now = datetime.now(timezone.utc)

        sources = [
            # Old stars
            ScoreSource("github_stars", 90.0, 0.25, now - timedelta(days=365), 500),
            # Medium-age registry
            ScoreSource("registry", 75.0, 0.2, now - timedelta(days=90), 80),
            # Fresh user rating
            ScoreSource("user_rating", 85.0, 0.4, now, 6),
            # Old maintenance (doesn't decay)
            ScoreSource("maintenance", 65.0, 0.15, now - timedelta(days=180), 1),
        ]

        result = aggregator.aggregate_with_decay(sources, decay)

        # Should balance decayed old stars, slightly decayed registry,
        # fresh user rating, and non-decayed maintenance
        assert 0 <= result.final_score <= 100
        assert result.source_count == 4
        assert result.confidence > 0.5  # Good diversity and sample sizes
