"""Tests for composite score calculator."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from skillmeat.core.artifact import ArtifactMetadata
from skillmeat.core.scoring.context_booster import ContextBooster
from skillmeat.core.scoring.match_analyzer import MatchAnalyzer
from skillmeat.core.scoring.models import ArtifactScore
from skillmeat.core.scoring.score_calculator import (
    DEFAULT_WEIGHTS,
    KEYWORD_WEIGHT,
    SEMANTIC_WEIGHT,
    ScoreCalculator,
)
from skillmeat.core.scoring.semantic_scorer import SemanticScorer


@pytest.fixture
def match_analyzer():
    """Create match analyzer for testing."""
    return MatchAnalyzer()


@pytest.fixture
def mock_semantic_scorer():
    """Create mock semantic scorer."""
    scorer = MagicMock(spec=SemanticScorer)
    scorer.is_available.return_value = True
    scorer.score_artifact = AsyncMock(return_value=85.0)
    return scorer


@pytest.fixture
def mock_context_booster():
    """Create mock context booster."""
    booster = MagicMock(spec=ContextBooster)
    booster.apply_boost = MagicMock(side_effect=lambda artifact, score: score * 1.1)
    return booster


@pytest.fixture
def sample_artifact():
    """Create sample artifact for testing."""
    return ArtifactMetadata(
        title="PDF Converter Tool",
        description="Convert documents to PDF format with ease",
        tags=["pdf", "conversion", "documents"],
    )


class TestScoreCalculatorInit:
    """Test ScoreCalculator initialization."""

    def test_init_with_defaults(self, match_analyzer):
        """Test initialization with default weights."""
        calculator = ScoreCalculator(match_analyzer=match_analyzer)

        assert calculator.match_analyzer is match_analyzer
        assert calculator.semantic_scorer is None
        assert calculator.context_booster is None
        assert calculator.weights == DEFAULT_WEIGHTS

    def test_init_with_custom_weights(self, match_analyzer):
        """Test initialization with custom weights."""
        custom_weights = {"trust": 0.3, "quality": 0.3, "match": 0.4}
        calculator = ScoreCalculator(
            match_analyzer=match_analyzer, weights=custom_weights
        )

        assert calculator.weights == custom_weights

    def test_init_with_all_components(
        self, match_analyzer, mock_semantic_scorer, mock_context_booster
    ):
        """Test initialization with all optional components."""
        calculator = ScoreCalculator(
            match_analyzer=match_analyzer,
            semantic_scorer=mock_semantic_scorer,
            context_booster=mock_context_booster,
        )

        assert calculator.semantic_scorer is mock_semantic_scorer
        assert calculator.context_booster is mock_context_booster

    def test_init_validates_weight_sum(self, match_analyzer):
        """Test that initialization validates weights sum to 1.0."""
        invalid_weights = {"trust": 0.5, "quality": 0.3, "match": 0.1}  # Sum = 0.9

        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            ScoreCalculator(match_analyzer=match_analyzer, weights=invalid_weights)

    def test_init_accepts_weights_within_tolerance(self, match_analyzer):
        """Test that weights within ±0.01 of 1.0 are accepted."""
        # 0.995 should be accepted (within tolerance)
        weights = {"trust": 0.33, "quality": 0.33, "match": 0.335}

        calculator = ScoreCalculator(match_analyzer=match_analyzer, weights=weights)
        assert calculator.weights == weights


class TestCalculateScore:
    """Test calculate_score method."""

    @pytest.mark.asyncio
    async def test_basic_score_calculation(self, match_analyzer, sample_artifact):
        """Test basic composite score calculation with keyword-only."""
        calculator = ScoreCalculator(match_analyzer=match_analyzer)

        score = await calculator.calculate_score(
            query="pdf converter",
            artifact=sample_artifact,
            artifact_name="pdf-tool",
            trust_score=75.0,
            quality_score=80.0,
        )

        # Verify result structure
        assert isinstance(score, ArtifactScore)
        assert score.artifact_id == "skill:pdf-tool"
        assert score.trust_score == 75.0
        assert score.quality_score == 80.0
        assert score.match_score is not None
        assert 0 <= score.confidence <= 100
        assert score.schema_version == "1.0.0"
        assert isinstance(score.last_updated, datetime)

    @pytest.mark.asyncio
    async def test_score_with_defaults(self, match_analyzer, sample_artifact):
        """Test scoring with default trust and quality scores."""
        calculator = ScoreCalculator(match_analyzer=match_analyzer)

        score = await calculator.calculate_score(
            query="pdf", artifact=sample_artifact, artifact_name="pdf-tool"
        )

        # Should use defaults (50.0)
        assert score.trust_score == 50.0
        assert score.quality_score == 50.0

    @pytest.mark.asyncio
    async def test_score_validates_trust_range(self, match_analyzer, sample_artifact):
        """Test that trust_score is validated to 0-100 range."""
        calculator = ScoreCalculator(match_analyzer=match_analyzer)

        with pytest.raises(ValueError, match="trust_score must be 0-100"):
            await calculator.calculate_score(
                query="pdf",
                artifact=sample_artifact,
                artifact_name="pdf-tool",
                trust_score=150.0,  # Invalid
            )

    @pytest.mark.asyncio
    async def test_score_validates_quality_range(self, match_analyzer, sample_artifact):
        """Test that quality_score is validated to 0-100 range."""
        calculator = ScoreCalculator(match_analyzer=match_analyzer)

        with pytest.raises(ValueError, match="quality_score must be 0-100"):
            await calculator.calculate_score(
                query="pdf",
                artifact=sample_artifact,
                artifact_name="pdf-tool",
                quality_score=-10.0,  # Invalid
            )

    @pytest.mark.asyncio
    async def test_semantic_blending_when_available(
        self, match_analyzer, mock_semantic_scorer, sample_artifact
    ):
        """Test that semantic and keyword scores are blended when available."""
        # Mock returns semantic score of 90.0
        mock_semantic_scorer.score_artifact.return_value = 90.0

        calculator = ScoreCalculator(
            match_analyzer=match_analyzer, semantic_scorer=mock_semantic_scorer
        )

        score = await calculator.calculate_score(
            query="pdf converter",
            artifact=sample_artifact,
            artifact_name="pdf-tool",
            trust_score=50.0,
            quality_score=50.0,
        )

        # Verify semantic scorer was called
        mock_semantic_scorer.is_available.assert_called_once()
        mock_semantic_scorer.score_artifact.assert_called_once_with(
            query="pdf converter", artifact=sample_artifact
        )

        # Match score should be blend of semantic (90) and keyword
        # We can't predict exact keyword score, but we know it's blended
        assert score.match_score is not None

    @pytest.mark.asyncio
    async def test_semantic_fallback_to_keyword(
        self, match_analyzer, mock_semantic_scorer, sample_artifact
    ):
        """Test fallback to keyword-only when semantic returns None."""
        # Mock semantic scorer returns None (unavailable)
        mock_semantic_scorer.score_artifact.return_value = None

        calculator = ScoreCalculator(
            match_analyzer=match_analyzer, semantic_scorer=mock_semantic_scorer
        )

        score = await calculator.calculate_score(
            query="pdf",
            artifact=sample_artifact,
            artifact_name="pdf-tool",
            trust_score=50.0,
            quality_score=50.0,
        )

        # Should fall back to keyword-only
        assert score.match_score is not None

    @pytest.mark.asyncio
    async def test_semantic_fallback_on_exception(
        self, match_analyzer, mock_semantic_scorer, sample_artifact
    ):
        """Test fallback to keyword-only when semantic scoring raises exception."""
        # Mock semantic scorer raises exception
        mock_semantic_scorer.score_artifact.side_effect = RuntimeError(
            "Embedding failed"
        )

        calculator = ScoreCalculator(
            match_analyzer=match_analyzer, semantic_scorer=mock_semantic_scorer
        )

        score = await calculator.calculate_score(
            query="pdf",
            artifact=sample_artifact,
            artifact_name="pdf-tool",
            trust_score=50.0,
            quality_score=50.0,
        )

        # Should gracefully fall back to keyword-only
        assert score.match_score is not None
        assert 0 <= score.confidence <= 100

    @pytest.mark.asyncio
    async def test_context_boost_applied(
        self, match_analyzer, mock_context_booster, sample_artifact
    ):
        """Test that context boost is applied when configured."""
        calculator = ScoreCalculator(
            match_analyzer=match_analyzer, context_booster=mock_context_booster
        )

        score = await calculator.calculate_score(
            query="pdf",
            artifact=sample_artifact,
            artifact_name="pdf-tool",
            trust_score=50.0,
            quality_score=50.0,
        )

        # Verify context booster was called
        mock_context_booster.apply_boost.assert_called_once()
        assert score.match_score is not None

    @pytest.mark.asyncio
    async def test_composite_formula(self, match_analyzer, sample_artifact):
        """Test that composite confidence formula is correct."""
        calculator = ScoreCalculator(match_analyzer=match_analyzer)

        # Use simple inputs to verify formula
        score = await calculator.calculate_score(
            query="pdf",
            artifact=sample_artifact,
            artifact_name="pdf-tool",
            trust_score=80.0,
            quality_score=60.0,
        )

        # Expected formula: (trust * 0.25) + (quality * 0.25) + (match * 0.50)
        expected_partial = (80.0 * 0.25) + (60.0 * 0.25)  # = 35.0
        # match_score unknown, but confidence should include it
        assert 0 <= score.confidence <= 100

        # With all scores at 100, confidence should be 100
        score_perfect = await calculator.calculate_score(
            query="pdf converter tool documents",  # High match
            artifact=sample_artifact,
            artifact_name="pdf-converter",
            trust_score=100.0,
            quality_score=100.0,
        )
        # Should be close to 100 (match score might not be exactly 100)
        assert score_perfect.confidence >= 90.0

    @pytest.mark.asyncio
    async def test_custom_weights(self, match_analyzer, sample_artifact):
        """Test that custom weights are applied correctly."""
        custom_weights = {"trust": 0.5, "quality": 0.3, "match": 0.2}
        calculator = ScoreCalculator(
            match_analyzer=match_analyzer, weights=custom_weights
        )

        score = await calculator.calculate_score(
            query="pdf",
            artifact=sample_artifact,
            artifact_name="pdf-tool",
            trust_score=100.0,
            quality_score=50.0,
        )

        # With custom weights, trust has more influence
        # Expected: (100 * 0.5) + (50 * 0.3) + (match * 0.2) = 65 + match*0.2
        assert score.confidence >= 65.0

    @pytest.mark.asyncio
    async def test_empty_query(self, match_analyzer, sample_artifact):
        """Test behavior with empty query."""
        calculator = ScoreCalculator(match_analyzer=match_analyzer)

        score = await calculator.calculate_score(
            query="",
            artifact=sample_artifact,
            artifact_name="pdf-tool",
            trust_score=50.0,
            quality_score=50.0,
        )

        # Should still return valid score (match_score will be 0)
        assert score.match_score == 0.0
        # Confidence will be based on trust and quality only
        expected = (50.0 * 0.25) + (50.0 * 0.25) + (0.0 * 0.50)  # = 25.0
        assert score.confidence == pytest.approx(expected)


class TestCalculateScoresBatch:
    """Test calculate_scores batch method."""

    @pytest.mark.asyncio
    async def test_batch_scoring(self, match_analyzer):
        """Test batch scoring of multiple artifacts."""
        artifact1 = ArtifactMetadata(
            title="PDF Tool",
            description="Convert PDFs",
            tags=["pdf"],
        )
        artifact2 = ArtifactMetadata(
            title="Image Tool",
            description="Process images",
            tags=["image"],
        )

        artifacts = [
            ("pdf-tool", artifact1, "skill"),
            ("image-tool", artifact2, "skill"),
        ]

        calculator = ScoreCalculator(match_analyzer=match_analyzer)

        scores = await calculator.calculate_scores(
            query="pdf", artifacts=artifacts, trust_scores={}, quality_scores={}
        )

        # Should return scores for both artifacts
        assert len(scores) == 2
        assert all(isinstance(s, ArtifactScore) for s in scores)

    @pytest.mark.asyncio
    async def test_batch_with_custom_trust_quality(self, match_analyzer):
        """Test batch scoring with custom trust and quality scores."""
        artifact1 = ArtifactMetadata(title="PDF Tool", tags=["pdf"])

        artifacts = [("pdf-tool", artifact1, "skill")]

        trust_scores = {"pdf-tool": 90.0}
        quality_scores = {"pdf-tool": 85.0}

        calculator = ScoreCalculator(match_analyzer=match_analyzer)

        scores = await calculator.calculate_scores(
            query="pdf",
            artifacts=artifacts,
            trust_scores=trust_scores,
            quality_scores=quality_scores,
        )

        assert len(scores) == 1
        assert scores[0].trust_score == 90.0
        assert scores[0].quality_score == 85.0

    @pytest.mark.asyncio
    async def test_batch_sorted_by_confidence(self, match_analyzer):
        """Test that batch results are sorted by descending confidence."""
        # Create artifacts with different expected scores
        high_match = ArtifactMetadata(
            title="PDF Converter Tool",
            description="Convert documents to PDF",
            tags=["pdf", "converter"],
        )
        low_match = ArtifactMetadata(
            title="Image Editor",
            description="Edit images",
            tags=["image"],
        )

        artifacts = [
            ("low-match", low_match, "skill"),
            ("high-match", high_match, "skill"),
        ]

        trust_scores = {"high-match": 100.0, "low-match": 50.0}
        quality_scores = {"high-match": 100.0, "low-match": 50.0}

        calculator = ScoreCalculator(match_analyzer=match_analyzer)

        scores = await calculator.calculate_scores(
            query="pdf converter",
            artifacts=artifacts,
            trust_scores=trust_scores,
            quality_scores=quality_scores,
        )

        # high-match should rank higher
        assert scores[0].artifact_id == "skill:high-match"
        assert scores[1].artifact_id == "skill:low-match"
        assert scores[0].confidence >= scores[1].confidence

    @pytest.mark.asyncio
    async def test_batch_with_defaults(self, match_analyzer):
        """Test batch scoring uses defaults when trust/quality not provided."""
        artifact = ArtifactMetadata(title="Test Tool", tags=["test"])

        artifacts = [("test-tool", artifact, "skill")]

        calculator = ScoreCalculator(match_analyzer=match_analyzer)

        scores = await calculator.calculate_scores(query="test", artifacts=artifacts)

        # Should use default scores (50.0)
        assert scores[0].trust_score == 50.0
        assert scores[0].quality_score == 50.0

    @pytest.mark.asyncio
    async def test_batch_empty_list(self, match_analyzer):
        """Test batch scoring with empty artifact list."""
        calculator = ScoreCalculator(match_analyzer=match_analyzer)

        scores = await calculator.calculate_scores(query="test", artifacts=[])

        assert scores == []


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_semantic_scorer_unavailable(
        self, match_analyzer, mock_semantic_scorer, sample_artifact
    ):
        """Test behavior when semantic scorer is unavailable."""
        # Mock semantic scorer as unavailable
        mock_semantic_scorer.is_available.return_value = False

        calculator = ScoreCalculator(
            match_analyzer=match_analyzer, semantic_scorer=mock_semantic_scorer
        )

        score = await calculator.calculate_score(
            query="pdf",
            artifact=sample_artifact,
            artifact_name="pdf-tool",
            trust_score=50.0,
            quality_score=50.0,
        )

        # Should fall back to keyword-only
        mock_semantic_scorer.score_artifact.assert_not_called()
        assert score.match_score is not None

    @pytest.mark.asyncio
    async def test_all_zeros(self, match_analyzer):
        """Test scoring with all zero inputs."""
        artifact = ArtifactMetadata(title="", description="", tags=[])

        calculator = ScoreCalculator(match_analyzer=match_analyzer)

        score = await calculator.calculate_score(
            query="",
            artifact=artifact,
            artifact_name="empty",
            trust_score=0.0,
            quality_score=0.0,
        )

        assert score.confidence == 0.0
        assert score.trust_score == 0.0
        assert score.quality_score == 0.0
        assert score.match_score == 0.0

    @pytest.mark.asyncio
    async def test_all_max_scores(self, match_analyzer, sample_artifact):
        """Test scoring with all maximum scores."""
        calculator = ScoreCalculator(match_analyzer=match_analyzer)

        score = await calculator.calculate_score(
            query="pdf converter tool",  # High relevance
            artifact=sample_artifact,
            artifact_name="pdf-converter",
            trust_score=100.0,
            quality_score=100.0,
        )

        # Confidence should be high (likely 100 or close)
        assert score.confidence >= 90.0

    @pytest.mark.asyncio
    async def test_confidence_clamped_to_100(self, match_analyzer, sample_artifact):
        """Test that confidence is clamped to 100 even with boost."""
        # Create a context booster with high multiplier
        mock_booster = MagicMock(spec=ContextBooster)
        mock_booster.apply_boost = MagicMock(
            side_effect=lambda artifact, score: score * 1.5
        )  # 50% boost

        calculator = ScoreCalculator(
            match_analyzer=match_analyzer, context_booster=mock_booster
        )

        score = await calculator.calculate_score(
            query="pdf converter",
            artifact=sample_artifact,
            artifact_name="pdf-converter",
            trust_score=100.0,
            quality_score=100.0,
        )

        # Should be clamped to 100
        assert score.confidence <= 100.0

    @pytest.mark.asyncio
    async def test_unicode_query(self, match_analyzer, sample_artifact):
        """Test scoring with Unicode characters in query."""
        calculator = ScoreCalculator(match_analyzer=match_analyzer)

        score = await calculator.calculate_score(
            query="pдf convertér 文档",  # Mixed Unicode
            artifact=sample_artifact,
            artifact_name="pdf-tool",
            trust_score=50.0,
            quality_score=50.0,
        )

        # Should handle gracefully
        assert 0 <= score.confidence <= 100
