"""Tests for scoring error handling and graceful degradation.

This test suite verifies that the scoring system handles errors gracefully,
including timeouts, missing API keys, and service failures.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from skillmeat.core.artifact import ArtifactMetadata
from skillmeat.core.scoring import (
    ArtifactNotFound,
    EmbeddingServiceUnavailable,
    ScoringError,
    ScoringTimeout,
)
from skillmeat.core.scoring.service import ScoringService
from skillmeat.core.scoring.utils import with_timeout


class TestExceptionHierarchy:
    """Test exception hierarchy and attributes."""

    def test_scoring_error_base(self):
        """ScoringError is base exception for all scoring errors."""
        error = ScoringError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"

    def test_embedding_service_unavailable(self):
        """EmbeddingServiceUnavailable inherits from ScoringError."""
        error = EmbeddingServiceUnavailable("API key missing")
        assert isinstance(error, ScoringError)
        assert isinstance(error, Exception)
        assert str(error) == "API key missing"

    def test_scoring_timeout_attributes(self):
        """ScoringTimeout includes timeout_seconds attribute."""
        error = ScoringTimeout("Operation timed out", timeout_seconds=5.0)
        assert isinstance(error, ScoringError)
        assert error.timeout_seconds == 5.0
        assert str(error) == "Operation timed out"

    def test_artifact_not_found_attributes(self):
        """ArtifactNotFound includes artifact_id attribute."""
        error = ArtifactNotFound("Artifact missing", artifact_id="skill:test")
        assert isinstance(error, ScoringError)
        assert error.artifact_id == "skill:test"
        assert str(error) == "Artifact missing"

    def test_catch_all_scoring_errors(self):
        """Can catch all scoring errors with base class."""
        errors = [
            ScoringError("generic"),
            EmbeddingServiceUnavailable("unavailable"),
            ScoringTimeout("timeout", timeout_seconds=5.0),
            ArtifactNotFound("not found", artifact_id="skill:test"),
        ]

        for error in errors:
            try:
                raise error
            except ScoringError:
                pass  # Should catch all
            else:
                pytest.fail(f"Failed to catch {type(error).__name__}")


class TestTimeoutWrapper:
    """Test timeout wrapper utility."""

    @pytest.mark.asyncio
    async def test_successful_completion(self):
        """Coroutine completes successfully within timeout."""

        async def quick_operation():
            await asyncio.sleep(0.01)
            return "result"

        result = await with_timeout(quick_operation(), timeout_seconds=1.0)
        assert result == "result"

    @pytest.mark.asyncio
    async def test_timeout_returns_fallback(self):
        """Timeout returns fallback value by default."""

        async def slow_operation():
            await asyncio.sleep(10.0)
            return "should not reach"

        result = await with_timeout(
            slow_operation(), timeout_seconds=0.1, fallback="fallback_value"
        )
        assert result == "fallback_value"

    @pytest.mark.asyncio
    async def test_timeout_returns_none_by_default(self):
        """Timeout returns None when no fallback specified."""

        async def slow_operation():
            await asyncio.sleep(10.0)
            return "should not reach"

        result = await with_timeout(slow_operation(), timeout_seconds=0.1)
        assert result is None

    @pytest.mark.asyncio
    async def test_timeout_raises_when_requested(self):
        """Timeout raises ScoringTimeout when raise_on_timeout=True."""

        async def slow_operation():
            await asyncio.sleep(10.0)
            return "should not reach"

        with pytest.raises(ScoringTimeout) as exc_info:
            await with_timeout(
                slow_operation(), timeout_seconds=0.1, raise_on_timeout=True
            )

        assert exc_info.value.timeout_seconds == 0.1


class TestScoringServiceDegradation:
    """Test ScoringService graceful degradation."""

    def test_semantic_available_with_valid_embedder(self):
        """semantic_available returns True when embedder is configured."""
        with patch(
            "skillmeat.core.scoring.embedder.SentenceTransformerEmbedder.is_available",
            return_value=True,
        ):
            service = ScoringService(enable_semantic=True)
            assert service.semantic_available is True

    def test_semantic_unavailable_without_api_key(self):
        """semantic_available returns False when embedder is unavailable."""
        with patch(
            "skillmeat.core.scoring.embedder.SentenceTransformerEmbedder.is_available",
            return_value=False,
        ):
            service = ScoringService(enable_semantic=True)
            assert service.semantic_available is False

    def test_semantic_unavailable_when_disabled(self):
        """semantic_available returns False when semantic disabled."""
        service = ScoringService(enable_semantic=False)
        assert service.semantic_available is False

    @pytest.mark.asyncio
    async def test_degradation_when_embedder_unavailable(self):
        """Degrades to keyword when embedder unavailable."""
        # Mock embedder as unavailable
        with patch(
            "skillmeat.core.scoring.embedder.SentenceTransformerEmbedder.is_available",
            return_value=False,
        ):
            service = ScoringService(enable_semantic=True, fallback_to_keyword=True)

            artifacts = [
                (
                    "pdf-tool",
                    ArtifactMetadata(
                        title="PDF Tool", description="Process PDFs", tags=["pdf"]
                    ),
                ),
            ]

            result = await service.score_artifacts("pdf", artifacts)

            # Should degrade to keyword
            assert result.degraded is True
            assert result.used_semantic is False
            assert "not available" in result.degradation_reason.lower()
            assert len(result.scores) > 0

    @pytest.mark.asyncio
    async def test_degradation_when_semantic_times_out(self):
        """Degrades to keyword when semantic scoring times out."""
        # Mock embedder as available but slow
        mock_embedder = Mock()
        mock_embedder.is_available.return_value = True

        # Mock semantic scorer to be slow
        async def slow_score(*args, **kwargs):
            await asyncio.sleep(10.0)
            return 90.0

        with patch(
            "skillmeat.core.scoring.semantic_scorer.SemanticScorer.score_artifact",
            side_effect=slow_score,
        ):
            service = ScoringService(
                embedder=mock_embedder,
                enable_semantic=True,
                semantic_timeout=0.1,
                fallback_to_keyword=True,
            )

            artifacts = [
                (
                    "pdf-tool",
                    ArtifactMetadata(
                        title="PDF Tool", description="Process PDFs", tags=["pdf"]
                    ),
                ),
            ]

            result = await service.score_artifacts("pdf", artifacts)

            # Should degrade to keyword
            assert result.degraded is True
            assert result.used_semantic is False
            assert "timed out" in result.degradation_reason.lower()
            assert len(result.scores) > 0

    @pytest.mark.asyncio
    async def test_successful_semantic_scoring(self):
        """Successfully uses semantic scoring when available."""
        # Mock embedder as available
        mock_embedder = Mock()
        mock_embedder.is_available.return_value = True

        # Mock semantic scorer to return scores
        async def mock_score(query, artifact):
            return 85.0

        with patch(
            "skillmeat.core.scoring.semantic_scorer.SemanticScorer.score_artifact",
            side_effect=mock_score,
        ):
            service = ScoringService(
                embedder=mock_embedder, enable_semantic=True, fallback_to_keyword=True
            )

            artifacts = [
                (
                    "pdf-tool",
                    ArtifactMetadata(
                        title="PDF Tool", description="Process PDFs", tags=["pdf"]
                    ),
                ),
            ]

            result = await service.score_artifacts("pdf", artifacts)

            # Should use semantic
            assert result.degraded is False
            assert result.used_semantic is True
            assert result.degradation_reason is None
            assert len(result.scores) > 0
            assert result.scores[0].match_score == 85.0

    @pytest.mark.asyncio
    async def test_raises_timeout_when_fallback_disabled(self):
        """Raises ScoringTimeout when fallback_to_keyword=False."""
        # Mock embedder as available but slow
        mock_embedder = Mock()
        mock_embedder.is_available.return_value = True

        async def slow_score(*args, **kwargs):
            await asyncio.sleep(10.0)
            return 90.0

        with patch(
            "skillmeat.core.scoring.semantic_scorer.SemanticScorer.score_artifact",
            side_effect=slow_score,
        ):
            service = ScoringService(
                embedder=mock_embedder,
                enable_semantic=True,
                semantic_timeout=0.1,
                fallback_to_keyword=False,  # Strict mode
            )

            artifacts = [
                (
                    "pdf-tool",
                    ArtifactMetadata(
                        title="PDF Tool", description="Process PDFs", tags=["pdf"]
                    ),
                ),
            ]

            with pytest.raises(ScoringTimeout):
                await service.score_artifacts("pdf", artifacts)

    @pytest.mark.asyncio
    async def test_keyword_only_mode(self):
        """Works correctly with semantic disabled."""
        service = ScoringService(enable_semantic=False)

        artifacts = [
            (
                "pdf-tool",
                ArtifactMetadata(
                    title="PDF Tool", description="Process PDFs", tags=["pdf"]
                ),
            ),
            (
                "image-tool",
                ArtifactMetadata(
                    title="Image Tool", description="Process images", tags=["image"]
                ),
            ),
        ]

        result = await service.score_artifacts("pdf", artifacts)

        # Should use keyword-only
        assert result.used_semantic is False
        assert result.degraded is False  # Not degraded, semantic was never enabled
        assert result.degradation_reason is None
        assert len(result.scores) > 0
        # PDF tool should rank higher
        assert "pdf" in result.scores[0].artifact_id.lower()


class TestScoringResultModel:
    """Test ScoringResult dataclass validation."""

    def test_valid_result(self):
        """Valid ScoringResult passes validation."""
        from skillmeat.core.scoring.models import ScoringResult

        result = ScoringResult(
            scores=[],
            used_semantic=True,
            degraded=False,
            degradation_reason=None,
            duration_ms=123.45,
            query="test query",
        )

        assert result.duration_ms == 123.45
        assert result.query == "test query"

    def test_degraded_requires_reason(self):
        """degraded=True requires degradation_reason."""
        from skillmeat.core.scoring.models import ScoringResult

        with pytest.raises(
            ValueError, match="degraded=True requires degradation_reason"
        ):
            ScoringResult(
                scores=[],
                used_semantic=False,
                degraded=True,
                degradation_reason=None,  # Invalid
                duration_ms=100.0,
            )

    def test_negative_duration_invalid(self):
        """Negative duration raises ValueError."""
        from skillmeat.core.scoring.models import ScoringResult

        with pytest.raises(ValueError, match="duration_ms must be >= 0"):
            ScoringResult(
                scores=[],
                used_semantic=False,
                degraded=False,
                degradation_reason=None,
                duration_ms=-10.0,  # Invalid
            )

    def test_duration_tracking(self):
        """Duration is tracked correctly."""

        @pytest.mark.asyncio
        async def test():
            service = ScoringService(enable_semantic=False)
            artifacts = [
                (
                    "test",
                    ArtifactMetadata(title="Test", description="Test", tags=[]),
                ),
            ]

            result = await service.score_artifacts("test", artifacts)
            assert result.duration_ms > 0
            assert result.duration_ms < 1000  # Should be very fast

        asyncio.run(test())


class TestDegradationFlags:
    """Test degradation flags in ScoringResult."""

    @pytest.mark.asyncio
    async def test_no_degradation_in_keyword_mode(self):
        """No degradation when semantic is disabled."""
        service = ScoringService(enable_semantic=False)
        artifacts = [
            ("test", ArtifactMetadata(title="Test", description="Test", tags=[])),
        ]

        result = await service.score_artifacts("test", artifacts)

        assert result.used_semantic is False
        assert result.degraded is False
        assert result.degradation_reason is None

    @pytest.mark.asyncio
    async def test_degradation_flag_set_correctly(self):
        """Degradation flag set when fallback occurs."""
        # Mock unavailable embedder
        with patch(
            "skillmeat.core.scoring.embedder.SentenceTransformerEmbedder.is_available",
            return_value=False,
        ):
            service = ScoringService(enable_semantic=True, fallback_to_keyword=True)
            artifacts = [
                ("test", ArtifactMetadata(title="Test", description="Test", tags=[])),
            ]

            result = await service.score_artifacts("test", artifacts)

            assert result.degraded is True
            assert result.used_semantic is False
            assert result.degradation_reason is not None
            assert len(result.degradation_reason) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
