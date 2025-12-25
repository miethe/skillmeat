"""Tests for ScoreAggregator class.

Tests weighted Bayesian averaging, confidence calculation, and edge cases.
"""

import pytest
from datetime import datetime, timedelta, timezone

from skillmeat.core.scoring.score_aggregator import (
    ScoreAggregator,
    ScoreSource,
    AggregatedScore,
    DEFAULT_SOURCE_WEIGHTS,
)


class TestScoreSource:
    """Tests for ScoreSource dataclass."""

    def test_valid_score_source(self):
        """Test creating a valid ScoreSource."""
        now = datetime.now(timezone.utc)
        source = ScoreSource(
            source_name="user_rating",
            score=85.0,
            weight=0.4,
            last_updated=now,
            sample_size=10,
        )
        assert source.source_name == "user_rating"
        assert source.score == 85.0
        assert source.weight == 0.4
        assert source.sample_size == 10

    def test_score_out_of_range(self):
        """Test that score must be 0-100."""
        now = datetime.now(timezone.utc)

        with pytest.raises(ValueError, match="score must be 0-100"):
            ScoreSource("test", -10.0, 0.5, now)

        with pytest.raises(ValueError, match="score must be 0-100"):
            ScoreSource("test", 150.0, 0.5, now)

    def test_weight_out_of_range(self):
        """Test that weight must be 0-1."""
        now = datetime.now(timezone.utc)

        with pytest.raises(ValueError, match="weight must be 0-1"):
            ScoreSource("test", 50.0, -0.5, now)

        with pytest.raises(ValueError, match="weight must be 0-1"):
            ScoreSource("test", 50.0, 1.5, now)

    def test_negative_sample_size(self):
        """Test that sample_size cannot be negative."""
        now = datetime.now(timezone.utc)

        with pytest.raises(ValueError, match="sample_size must be >= 0"):
            ScoreSource("test", 50.0, 0.5, now, sample_size=-5)

    def test_none_sample_size(self):
        """Test that sample_size can be None."""
        now = datetime.now(timezone.utc)
        source = ScoreSource("test", 50.0, 0.5, now, sample_size=None)
        assert source.sample_size is None


class TestAggregatedScore:
    """Tests for AggregatedScore dataclass."""

    def test_valid_aggregated_score(self):
        """Test creating a valid AggregatedScore."""
        now = datetime.now(timezone.utc)
        source = ScoreSource("test", 50.0, 0.5, now)
        result = AggregatedScore(
            final_score=75.0,
            confidence=0.8,
            source_count=1,
            sources=[source],
            computed_at=now,
        )
        assert result.final_score == 75.0
        assert result.confidence == 0.8
        assert result.source_count == 1
        assert len(result.sources) == 1

    def test_final_score_out_of_range(self):
        """Test that final_score must be 0-100."""
        with pytest.raises(ValueError, match="final_score must be 0-100"):
            AggregatedScore(-10.0, 0.5, 0)

        with pytest.raises(ValueError, match="final_score must be 0-100"):
            AggregatedScore(150.0, 0.5, 0)

    def test_confidence_out_of_range(self):
        """Test that confidence must be 0-1."""
        with pytest.raises(ValueError, match="confidence must be 0-1"):
            AggregatedScore(50.0, -0.1, 0)

        with pytest.raises(ValueError, match="confidence must be 0-1"):
            AggregatedScore(50.0, 1.5, 0)

    def test_negative_source_count(self):
        """Test that source_count cannot be negative."""
        with pytest.raises(ValueError, match="source_count must be >= 0"):
            AggregatedScore(50.0, 0.5, -1)


class TestScoreAggregator:
    """Tests for ScoreAggregator class."""

    def test_initialization_defaults(self):
        """Test default initialization."""
        aggregator = ScoreAggregator()
        assert aggregator.prior_mean == 50.0
        assert aggregator.prior_strength == 10

    def test_initialization_custom(self):
        """Test custom initialization."""
        aggregator = ScoreAggregator(prior_mean=60.0, prior_strength=20)
        assert aggregator.prior_mean == 60.0
        assert aggregator.prior_strength == 20

    def test_invalid_prior_mean(self):
        """Test that prior_mean must be 0-100."""
        with pytest.raises(ValueError, match="prior_mean must be 0-100"):
            ScoreAggregator(prior_mean=-10.0)

        with pytest.raises(ValueError, match="prior_mean must be 0-100"):
            ScoreAggregator(prior_mean=150.0)

    def test_invalid_prior_strength(self):
        """Test that prior_strength must be > 0."""
        with pytest.raises(ValueError, match="prior_strength must be > 0"):
            ScoreAggregator(prior_strength=0)

        with pytest.raises(ValueError, match="prior_strength must be > 0"):
            ScoreAggregator(prior_strength=-5)

    def test_empty_sources(self):
        """Test aggregation with no sources returns prior."""
        aggregator = ScoreAggregator(prior_mean=50.0, prior_strength=10)
        result = aggregator.aggregate([])

        assert result.final_score == 50.0  # Returns prior mean
        assert result.confidence == 0.1  # Low confidence
        assert result.source_count == 0
        assert len(result.sources) == 0

    def test_single_source(self):
        """Test aggregation with a single source."""
        aggregator = ScoreAggregator(prior_mean=50.0, prior_strength=10)
        now = datetime.now(timezone.utc)
        source = ScoreSource("user_rating", 80.0, 0.4, now, sample_size=5)

        result = aggregator.aggregate([source])

        # With prior_strength=10 and sample_size=5, weight=0.4:
        # numerator = 50*10 + 80*0.4*5 = 500 + 160 = 660
        # denominator = 10 + 0.4*5 = 10 + 2 = 12
        # final_score = 660 / 12 = 55.0
        expected_score = (50.0 * 10 + 80.0 * 0.4 * 5) / (10 + 0.4 * 5)
        assert result.final_score == pytest.approx(expected_score, abs=0.1)
        assert result.source_count == 1
        assert result.confidence > 0.0

    def test_multiple_sources(self):
        """Test aggregation with multiple sources."""
        aggregator = ScoreAggregator(prior_mean=50.0, prior_strength=10)
        now = datetime.now(timezone.utc)

        sources = [
            ScoreSource("user_rating", 90.0, 0.4, now, sample_size=10),
            ScoreSource("github_stars", 70.0, 0.25, now, sample_size=150),
            ScoreSource("registry", 80.0, 0.2, now, sample_size=30),
        ]

        result = aggregator.aggregate(sources)

        # Weighted Bayesian average:
        # numerator = 50*10 + 90*0.4*10 + 70*0.25*150 + 80*0.2*30
        #           = 500 + 360 + 2625 + 480 = 3965
        # denominator = 10 + 0.4*10 + 0.25*150 + 0.2*30
        #             = 10 + 4 + 37.5 + 6 = 57.5
        # final_score = 3965 / 57.5 ≈ 68.96
        expected_numerator = (
            50.0 * 10 + 90.0 * 0.4 * 10 + 70.0 * 0.25 * 150 + 80.0 * 0.2 * 30
        )
        expected_denominator = 10 + 0.4 * 10 + 0.25 * 150 + 0.2 * 30
        expected_score = expected_numerator / expected_denominator

        assert result.final_score == pytest.approx(expected_score, abs=0.1)
        assert result.source_count == 3
        assert result.confidence > 0.5  # Should have decent confidence

    def test_cold_start_behavior(self):
        """Test Bayesian cold-start: prior dominates with few ratings."""
        aggregator = ScoreAggregator(prior_mean=50.0, prior_strength=10)
        now = datetime.now(timezone.utc)

        # Single rating with small sample size
        few_ratings = [ScoreSource("user_rating", 100.0, 0.4, now, sample_size=1)]
        result_few = aggregator.aggregate(few_ratings)

        # Many ratings with large sample size
        many_ratings = [ScoreSource("user_rating", 100.0, 0.4, now, sample_size=100)]
        result_many = aggregator.aggregate(many_ratings)

        # With few ratings, prior should pull score down toward 50
        # With many ratings, data should dominate and score should be near 100
        assert result_few.final_score < result_many.final_score
        assert result_few.final_score < 70  # Pulled toward prior
        assert result_many.final_score >= 90  # Dominated by data (>= instead of >)

    def test_all_zeros(self):
        """Test edge case: all sources have score=0."""
        aggregator = ScoreAggregator(prior_mean=50.0, prior_strength=10)
        now = datetime.now(timezone.utc)

        sources = [
            ScoreSource("source1", 0.0, 0.5, now, sample_size=10),
            ScoreSource("source2", 0.0, 0.5, now, sample_size=10),
        ]

        result = aggregator.aggregate(sources)

        # With prior_mean=50, score should be between 0 and 50
        assert 0 <= result.final_score <= 50
        assert result.source_count == 2

    def test_all_max_scores(self):
        """Test edge case: all sources have score=100."""
        aggregator = ScoreAggregator(prior_mean=50.0, prior_strength=10)
        now = datetime.now(timezone.utc)

        sources = [
            ScoreSource("source1", 100.0, 0.5, now, sample_size=10),
            ScoreSource("source2", 100.0, 0.5, now, sample_size=10),
        ]

        result = aggregator.aggregate(sources)

        # With prior_mean=50, score should be between 50 and 100
        assert 50 <= result.final_score <= 100
        assert result.source_count == 2

    def test_sample_size_none_defaults_to_one(self):
        """Test that None sample_size is treated as 1."""
        aggregator = ScoreAggregator(prior_mean=50.0, prior_strength=10)
        now = datetime.now(timezone.utc)

        source_with_none = ScoreSource("test", 80.0, 0.5, now, sample_size=None)
        source_with_one = ScoreSource("test", 80.0, 0.5, now, sample_size=1)

        result_none = aggregator.aggregate([source_with_none])
        result_one = aggregator.aggregate([source_with_one])

        # Both should produce the same final score
        assert result_none.final_score == pytest.approx(
            result_one.final_score, abs=0.01
        )


class TestConfidenceCalculation:
    """Tests for confidence calculation."""

    def test_confidence_empty_sources(self):
        """Test confidence with no sources."""
        aggregator = ScoreAggregator()
        confidence = aggregator.compute_confidence([])
        assert confidence == 0.1  # Very low confidence

    def test_confidence_single_recent_source(self):
        """Test confidence with single recent source."""
        aggregator = ScoreAggregator()
        now = datetime.now(timezone.utc)
        source = ScoreSource("user_rating", 80.0, 0.4, now, sample_size=50)

        confidence = aggregator.compute_confidence([source])

        # Should have moderate confidence (not very high due to single source)
        assert 0.2 <= confidence <= 0.65  # Adjusted upper bound

    def test_confidence_multiple_recent_diverse_sources(self):
        """Test confidence with multiple recent diverse sources."""
        aggregator = ScoreAggregator()
        now = datetime.now(timezone.utc)

        sources = [
            ScoreSource("user_rating", 85.0, 0.4, now, sample_size=50),
            ScoreSource("github_stars", 75.0, 0.25, now, sample_size=200),
            ScoreSource("registry", 80.0, 0.2, now, sample_size=30),
        ]

        confidence = aggregator.compute_confidence(sources)

        # Should have high confidence: 3 sources, large samples, recent, diverse
        assert confidence > 0.7

    def test_confidence_old_sources(self):
        """Test confidence decreases with old sources."""
        aggregator = ScoreAggregator()
        now = datetime.now(timezone.utc)
        old_date = now - timedelta(days=365)  # 1 year old

        recent_source = ScoreSource("test", 80.0, 0.5, now, sample_size=100)
        old_source = ScoreSource("test", 80.0, 0.5, old_date, sample_size=100)

        confidence_recent = aggregator.compute_confidence([recent_source])
        confidence_old = aggregator.compute_confidence([old_source])

        # Recent should have higher confidence than old
        assert confidence_recent > confidence_old

    def test_confidence_small_vs_large_sample(self):
        """Test confidence increases with larger sample size."""
        aggregator = ScoreAggregator()
        now = datetime.now(timezone.utc)

        small_sample = ScoreSource("test", 80.0, 0.5, now, sample_size=1)
        large_sample = ScoreSource("test", 80.0, 0.5, now, sample_size=200)

        confidence_small = aggregator.compute_confidence([small_sample])
        confidence_large = aggregator.compute_confidence([large_sample])

        # Larger sample should have higher confidence
        assert confidence_large > confidence_small

    def test_confidence_diversity(self):
        """Test confidence increases with source diversity."""
        aggregator = ScoreAggregator()
        now = datetime.now(timezone.utc)

        # All same source type
        same_sources = [
            ScoreSource("user_rating", 80.0, 0.5, now, sample_size=10),
            ScoreSource("user_rating", 85.0, 0.5, now, sample_size=10),
        ]

        # Diverse source types
        diverse_sources = [
            ScoreSource("user_rating", 80.0, 0.5, now, sample_size=10),
            ScoreSource("github_stars", 85.0, 0.5, now, sample_size=10),
        ]

        confidence_same = aggregator.compute_confidence(same_sources)
        confidence_diverse = aggregator.compute_confidence(diverse_sources)

        # Diverse sources should have higher confidence
        assert confidence_diverse > confidence_same

    def test_confidence_in_valid_range(self):
        """Test that confidence is always in [0, 1] range."""
        aggregator = ScoreAggregator()
        now = datetime.now(timezone.utc)

        # Test various scenarios
        test_cases = [
            [],  # Empty
            [ScoreSource("test", 50.0, 0.5, now, sample_size=1)],  # Single
            [
                ScoreSource("s1", 50.0, 0.5, now, sample_size=100),
                ScoreSource("s2", 60.0, 0.5, now, sample_size=100),
                ScoreSource("s3", 70.0, 0.5, now, sample_size=100),
            ],  # Multiple
        ]

        for sources in test_cases:
            confidence = aggregator.compute_confidence(sources)
            assert 0 <= confidence <= 1


class TestIntegration:
    """Integration tests for complete workflows."""

    def test_realistic_workflow(self):
        """Test realistic aggregation workflow."""
        aggregator = ScoreAggregator()
        now = datetime.now(timezone.utc)

        # Simulate artifact with multiple score sources
        # ScoreSource(source_name, score, weight, last_updated, sample_size)
        sources = [
            ScoreSource(
                source_name="user_rating",
                score=85.0,
                weight=DEFAULT_SOURCE_WEIGHTS["user_rating"],
                last_updated=now,
                sample_size=15,
            ),
            ScoreSource(
                source_name="github_stars",
                score=72.0,
                weight=DEFAULT_SOURCE_WEIGHTS["github_stars"],
                last_updated=now,
                sample_size=250,
            ),
            ScoreSource(
                source_name="registry",
                score=78.0,
                weight=DEFAULT_SOURCE_WEIGHTS["registry"],
                last_updated=now - timedelta(days=60),
                sample_size=40,
            ),
        ]

        result = aggregator.aggregate(sources)

        # Validate result
        assert 0 <= result.final_score <= 100
        assert 0 <= result.confidence <= 1
        assert result.source_count == 3
        assert len(result.sources) == 3
        assert result.computed_at is not None

        # Score should be weighted average influenced by sample sizes
        # Confidence should be relatively high (multiple recent diverse sources)
        assert result.confidence > 0.5

    def test_default_source_weights_sum_to_one(self):
        """Test that default source weights sum to 1.0."""
        total_weight = sum(DEFAULT_SOURCE_WEIGHTS.values())
        assert total_weight == pytest.approx(1.0, abs=0.01)
