"""Tests for scoring telemetry instrumentation.

This module tests that tracing spans are created correctly for scoring operations
with proper attributes, events, and hierarchical structure.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from skillmeat.core.artifact import ArtifactMetadata
from skillmeat.core.scoring.service import ScoringService
from skillmeat.core.scoring.score_calculator import ScoreCalculator
from skillmeat.core.scoring.match_analyzer import MatchAnalyzer
from skillmeat.core.scoring.models import ArtifactScore
from skillmeat.observability.tracing import Span


@pytest.fixture
def mock_span():
    """Create a mock span for testing."""
    span = Mock(spec=Span)
    span.span_id = "test-span-123"
    span.attributes = {}
    span.events = []

    def set_attribute(key, value):
        span.attributes[key] = value

    def add_event(name, attributes=None):
        span.events.append({"name": name, "attributes": attributes or {}})

    span.set_attribute = Mock(side_effect=set_attribute)
    span.add_event = Mock(side_effect=add_event)
    span.end = Mock(return_value=100.0)  # Mock duration

    return span


@pytest.fixture
def sample_artifacts():
    """Create sample artifacts for testing."""
    return [
        ("pdf-tool", ArtifactMetadata(
            title="PDF Tool",
            description="Convert PDF files",
            tags=["pdf", "converter"]
        )),
        ("image-tool", ArtifactMetadata(
            title="Image Tool",
            description="Process images",
            tags=["image", "processing"]
        )),
    ]


class TestScoringServiceTelemetry:
    """Test telemetry for ScoringService.score_artifacts."""

    @pytest.mark.asyncio
    async def test_span_created_with_correct_name(self, mock_span, sample_artifacts):
        """Test that span is created with operation name 'scoring.score_artifacts'."""
        service = ScoringService(enable_semantic=False)

        with patch('skillmeat.core.scoring.service.trace_operation') as mock_trace:
            # Configure mock to yield our mock span
            mock_trace.return_value.__enter__ = Mock(return_value=mock_span)
            mock_trace.return_value.__exit__ = Mock(return_value=False)

            await service.score_artifacts("pdf", sample_artifacts)

            # Verify trace_operation was called with correct name
            mock_trace.assert_called_once()
            call_args = mock_trace.call_args
            assert call_args[0][0] == "scoring.score_artifacts"

    @pytest.mark.asyncio
    async def test_span_attributes_set(self, mock_span, sample_artifacts):
        """Test that span attributes include query, artifact_count, used_semantic, degraded, duration_ms."""
        service = ScoringService(enable_semantic=False)

        with patch('skillmeat.core.scoring.service.trace_operation') as mock_trace:
            mock_trace.return_value.__enter__ = Mock(return_value=mock_span)
            mock_trace.return_value.__exit__ = Mock(return_value=False)

            await service.score_artifacts("pdf", sample_artifacts)

            # Check that trace_operation was called with query and artifact_count
            call_args = mock_trace.call_args
            assert call_args[1]["query"] == "pdf"
            assert call_args[1]["artifact_count"] == 2

            # Check that span attributes were set
            assert "scoring.used_semantic" in mock_span.attributes
            assert mock_span.attributes["scoring.used_semantic"] is False

            assert "scoring.degraded" in mock_span.attributes
            assert mock_span.attributes["scoring.degraded"] is False

            assert "scoring.duration_ms" in mock_span.attributes
            assert isinstance(mock_span.attributes["scoring.duration_ms"], (int, float))

    @pytest.mark.asyncio
    async def test_degradation_event_recorded(self, mock_span, sample_artifacts):
        """Test that degradation event is recorded when semantic scoring fails."""
        # Service with semantic enabled but no embedder (will degrade)
        service = ScoringService(
            embedder=None,
            enable_semantic=True,
            fallback_to_keyword=True
        )

        with patch('skillmeat.core.scoring.service.trace_operation') as mock_trace:
            mock_trace.return_value.__enter__ = Mock(return_value=mock_span)
            mock_trace.return_value.__exit__ = Mock(return_value=False)

            result = await service.score_artifacts("pdf", sample_artifacts)

            # Should be degraded
            assert result.degraded is True

            # Check span attributes
            assert mock_span.attributes["scoring.degraded"] is True

            # Check degradation event was recorded
            degradation_events = [
                e for e in mock_span.events if e["name"] == "scoring.degraded"
            ]
            assert len(degradation_events) == 1
            assert "reason" in degradation_events[0]["attributes"]


class TestScoreCalculatorTelemetry:
    """Test telemetry for ScoreCalculator.calculate_score."""

    @pytest.mark.asyncio
    async def test_span_created_with_correct_name(self, mock_span):
        """Test that span is created with operation name 'scoring.calculate_score'."""
        calculator = ScoreCalculator(match_analyzer=MatchAnalyzer())
        artifact = ArtifactMetadata(title="Test", description="Test artifact")

        with patch('skillmeat.core.scoring.score_calculator.trace_operation') as mock_trace:
            mock_trace.return_value.__enter__ = Mock(return_value=mock_span)
            mock_trace.return_value.__exit__ = Mock(return_value=False)

            await calculator.calculate_score(
                query="test",
                artifact=artifact,
                artifact_name="test-tool",
            )

            # Verify trace_operation was called
            mock_trace.assert_called_once()
            call_args = mock_trace.call_args
            assert call_args[0][0] == "scoring.calculate_score"

    @pytest.mark.asyncio
    async def test_span_attributes_include_scores(self, mock_span):
        """Test that span attributes include trust_score, quality_score, match_score, confidence."""
        calculator = ScoreCalculator(match_analyzer=MatchAnalyzer())
        artifact = ArtifactMetadata(title="PDF Tool", description="Convert PDFs")

        with patch('skillmeat.core.scoring.score_calculator.trace_operation') as mock_trace:
            mock_trace.return_value.__enter__ = Mock(return_value=mock_span)
            mock_trace.return_value.__exit__ = Mock(return_value=False)

            await calculator.calculate_score(
                query="pdf",
                artifact=artifact,
                artifact_name="pdf-tool",
                trust_score=75.0,
                quality_score=80.0,
            )

            # Check that trace_operation was called with artifact_id and query
            call_args = mock_trace.call_args
            assert "artifact_id" in call_args[1]
            assert call_args[1]["artifact_id"] == "skill:pdf-tool"
            assert "query" in call_args[1]
            assert call_args[1]["query"] == "pdf"

            # Check span attributes
            assert "scoring.trust_score" in mock_span.attributes
            assert mock_span.attributes["scoring.trust_score"] == 75.0

            assert "scoring.quality_score" in mock_span.attributes
            assert mock_span.attributes["scoring.quality_score"] == 80.0

            assert "scoring.match_score" in mock_span.attributes
            assert isinstance(mock_span.attributes["scoring.match_score"], (int, float))

            assert "scoring.confidence" in mock_span.attributes
            assert isinstance(mock_span.attributes["scoring.confidence"], (int, float))

    @pytest.mark.asyncio
    async def test_semantic_scoring_event(self, mock_span):
        """Test that semantic scoring event is recorded when semantic is used."""
        # Create a mock semantic scorer that returns a score
        mock_semantic_scorer = Mock()
        mock_semantic_scorer.is_available.return_value = True

        # Make score_artifact async
        async def mock_score_artifact(query, artifact):
            return 85.0

        mock_semantic_scorer.score_artifact = mock_score_artifact

        calculator = ScoreCalculator(
            match_analyzer=MatchAnalyzer(),
            semantic_scorer=mock_semantic_scorer,
        )
        artifact = ArtifactMetadata(title="PDF Tool", description="Convert PDFs")

        with patch('skillmeat.core.scoring.score_calculator.trace_operation') as mock_trace:
            mock_trace.return_value.__enter__ = Mock(return_value=mock_span)
            mock_trace.return_value.__exit__ = Mock(return_value=False)

            await calculator.calculate_score(
                query="pdf",
                artifact=artifact,
                artifact_name="pdf-tool",
            )

            # Check used_semantic attribute
            assert "scoring.used_semantic" in mock_span.attributes
            assert mock_span.attributes["scoring.used_semantic"] is True

            # Check semantic_match event was recorded
            semantic_events = [
                e for e in mock_span.events if e["name"] == "scoring.semantic_match"
            ]
            assert len(semantic_events) == 1
            event_attrs = semantic_events[0]["attributes"]
            assert "semantic_score" in event_attrs
            assert "keyword_score" in event_attrs
            assert "blend_weight_semantic" in event_attrs
            assert "blend_weight_keyword" in event_attrs

    @pytest.mark.asyncio
    async def test_keyword_only_event(self, mock_span):
        """Test that keyword_only event is recorded when semantic is not used."""
        calculator = ScoreCalculator(
            match_analyzer=MatchAnalyzer(),
            semantic_scorer=None,  # No semantic scorer
        )
        artifact = ArtifactMetadata(title="PDF Tool", description="Convert PDFs")

        with patch('skillmeat.core.scoring.score_calculator.trace_operation') as mock_trace:
            mock_trace.return_value.__enter__ = Mock(return_value=mock_span)
            mock_trace.return_value.__exit__ = Mock(return_value=False)

            await calculator.calculate_score(
                query="pdf",
                artifact=artifact,
                artifact_name="pdf-tool",
            )

            # Check used_semantic attribute
            assert "scoring.used_semantic" in mock_span.attributes
            assert mock_span.attributes["scoring.used_semantic"] is False

            # Check keyword_only event was recorded
            keyword_events = [
                e for e in mock_span.events if e["name"] == "scoring.keyword_only"
            ]
            assert len(keyword_events) == 1
            event_attrs = keyword_events[0]["attributes"]
            assert "keyword_score" in event_attrs


class TestMatchAPITelemetry:
    """Test telemetry for match API router."""

    @pytest.mark.asyncio
    async def test_match_router_span_attributes(self, mock_span):
        """Test that match router sets correct span attributes."""
        # This is more of an integration test - we'll mock the trace_operation
        from skillmeat.api.routers.match import match_artifacts
        from fastapi import Request

        # Create mock managers
        mock_artifact_mgr = Mock()
        mock_artifact_mgr.list_artifacts.return_value = []

        mock_collection_mgr = Mock()

        with patch('skillmeat.api.routers.match.trace_operation') as mock_trace:
            mock_trace.return_value.__enter__ = Mock(return_value=mock_span)
            mock_trace.return_value.__exit__ = Mock(return_value=False)

            try:
                await match_artifacts(
                    artifact_mgr=mock_artifact_mgr,
                    collection_mgr=mock_collection_mgr,
                    q="pdf",
                    limit=10,
                    min_confidence=0.0,
                    include_breakdown=False,
                )
            except Exception:
                pass  # May fail due to missing setup, but span should still be created

            # Verify trace_operation was called
            mock_trace.assert_called_once()
            call_args = mock_trace.call_args
            assert call_args[0][0] == "match.search"

            # Check initial attributes
            assert "query" in call_args[1]
            assert call_args[1]["query"] == "pdf"
            assert "limit" in call_args[1]
            assert call_args[1]["limit"] == 10
            assert "min_confidence" in call_args[1]
            assert call_args[1]["min_confidence"] == 0.0


class TestTelemetryPerformance:
    """Test that telemetry adds minimal overhead."""

    @pytest.mark.asyncio
    async def test_telemetry_overhead_is_minimal(self, sample_artifacts):
        """Test that span creation adds less than 1ms overhead."""
        import time

        service = ScoringService(enable_semantic=False)

        # Measure without telemetry (mock out trace_operation)
        with patch('skillmeat.core.scoring.service.trace_operation') as mock_trace:
            # Make trace_operation a no-op
            mock_trace.return_value.__enter__ = Mock(return_value=Mock())
            mock_trace.return_value.__exit__ = Mock(return_value=False)

            start = time.perf_counter()
            await service.score_artifacts("pdf", sample_artifacts)
            baseline_duration = (time.perf_counter() - start) * 1000

        # Measure with telemetry (real trace_operation)
        start = time.perf_counter()
        await service.score_artifacts("pdf", sample_artifacts)
        with_telemetry_duration = (time.perf_counter() - start) * 1000

        # Telemetry overhead should be less than 1ms
        overhead = with_telemetry_duration - baseline_duration
        assert overhead < 1.0, f"Telemetry overhead {overhead:.2f}ms exceeds 1ms threshold"
