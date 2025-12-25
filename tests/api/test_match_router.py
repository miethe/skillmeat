"""Tests for the match API router.

Tests artifact matching/search functionality using confidence scoring.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from skillmeat.api.server import app
from skillmeat.core.artifact import Artifact, ArtifactMetadata, ArtifactType
from skillmeat.core.scoring.models import ArtifactScore, ScoringResult


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_artifacts():
    """Mock artifact list for testing."""
    return [
        Artifact(
            name="pdf-processor",
            type=ArtifactType.SKILL,
            path="skills/pdf-processor",
            origin="github",
            metadata=ArtifactMetadata(
                title="PDF Processing Tool",
                description="Extract and manipulate PDF documents",
            ),
            added=datetime.now(timezone.utc),
        ),
        Artifact(
            name="image-tool",
            type=ArtifactType.SKILL,
            path="skills/image-tool",
            origin="github",
            metadata=ArtifactMetadata(
                title="Image Tool",
                description="Process and edit images",
            ),
            added=datetime.now(timezone.utc),
        ),
        Artifact(
            name="text-processor",
            type=ArtifactType.COMMAND,
            path="commands/text-processor",
            origin="github",
            metadata=ArtifactMetadata(
                title="Text Processor",
                description="Process text files",
            ),
            added=datetime.now(timezone.utc),
        ),
    ]


@pytest.fixture
def mock_scoring_result():
    """Mock scoring result with sample scores."""
    return ScoringResult(
        scores=[
            ArtifactScore(
                artifact_id="pdf-processor",
                trust_score=85.0,
                quality_score=92.5,
                match_score=95.0,
                confidence=90.0,
            ),
            ArtifactScore(
                artifact_id="text-processor",
                trust_score=80.0,
                quality_score=85.0,
                match_score=70.0,
                confidence=78.0,
            ),
            ArtifactScore(
                artifact_id="image-tool",
                trust_score=75.0,
                quality_score=80.0,
                match_score=60.0,
                confidence=72.0,
            ),
        ],
        used_semantic=True,
        degraded=False,
        degradation_reason=None,
        duration_ms=150.5,
        query="test query",
    )


@pytest.fixture
def mock_degraded_scoring_result():
    """Mock scoring result with degradation."""
    return ScoringResult(
        scores=[
            ArtifactScore(
                artifact_id="pdf-processor",
                trust_score=85.0,
                quality_score=92.5,
                match_score=70.0,  # Lower without semantic
                confidence=82.0,
            ),
        ],
        used_semantic=False,
        degraded=True,
        degradation_reason="Embedding service unavailable",
        duration_ms=75.0,
        query="test query",
    )


@pytest.fixture(autouse=True)
def setup_dependencies(mock_artifacts):
    """Setup dependency overrides for all tests."""
    from skillmeat.api import dependencies

    # Create mock managers
    mock_artifact_mgr = MagicMock()
    mock_artifact_mgr.list_artifacts.return_value = mock_artifacts

    mock_collection_mgr = MagicMock()

    # Override dependencies
    app.dependency_overrides[dependencies.get_artifact_manager] = lambda: mock_artifact_mgr
    app.dependency_overrides[dependencies.get_collection_manager] = lambda: mock_collection_mgr

    yield

    # Clear overrides
    app.dependency_overrides.clear()


class TestMatchEndpoint:
    """Tests for GET /api/v1/match endpoint."""

    def test_basic_match_query(self, client, mock_scoring_result):
        """Test basic artifact matching with query."""
        with patch("skillmeat.api.routers.match.ScoringService") as mock_scoring_service_cls:
            mock_scoring_service = MagicMock()
            mock_scoring_service.score_artifacts = AsyncMock(return_value=mock_scoring_result)
            mock_scoring_service_cls.return_value = mock_scoring_service

            response = client.get("/api/v1/match?q=pdf")

            assert response.status_code == 200
            data = response.json()

            # Check basic structure
            assert data["query"] == "pdf"
            assert len(data["matches"]) > 0
            assert data["total"] >= len(data["matches"])
            assert data["limit"] == 10  # Default
            assert data["min_confidence"] == 0.0  # Default
            assert data["schema_version"] == "1.0.0"
            assert "scored_at" in data
            assert data["degraded"] is False

            # Check matches are sorted by confidence
            confidences = [m["confidence"] for m in data["matches"]]
            assert confidences == sorted(confidences, reverse=True)

            # Check first match
            first_match = data["matches"][0]
            assert "artifact_id" in first_match
            assert "name" in first_match
            assert "artifact_type" in first_match
            assert "confidence" in first_match
            assert 0 <= first_match["confidence"] <= 100

    def test_match_with_limit(self, client, mock_scoring_result):
        """Test limit parameter restricts results."""
        with patch("skillmeat.api.routers.match.ScoringService") as mock_scoring_service_cls:
            mock_scoring_service = MagicMock()
            mock_scoring_service.score_artifacts = AsyncMock(return_value=mock_scoring_result)
            mock_scoring_service_cls.return_value = mock_scoring_service

            response = client.get("/api/v1/match?q=tool&limit=2")

            assert response.status_code == 200
            data = response.json()
            assert len(data["matches"]) <= 2
            assert data["limit"] == 2

    def test_match_with_min_confidence(self, client, mock_scoring_result):
        """Test min_confidence filters low-scoring results."""
        with patch("skillmeat.api.routers.match.ScoringService") as mock_scoring_service_cls:
            mock_scoring_service = MagicMock()
            mock_scoring_service.score_artifacts = AsyncMock(return_value=mock_scoring_result)
            mock_scoring_service_cls.return_value = mock_scoring_service

            response = client.get("/api/v1/match?q=pdf&min_confidence=80.0")

            assert response.status_code == 200
            data = response.json()

            # All matches should have confidence >= 80
            for match in data["matches"]:
                assert match["confidence"] >= 80.0

            assert data["min_confidence"] == 80.0

    def test_match_with_breakdown(self, client, mock_scoring_result):
        """Test include_breakdown flag adds score components."""
        with patch("skillmeat.api.routers.match.ScoringService") as mock_scoring_service_cls:
            mock_scoring_service = MagicMock()
            mock_scoring_service.score_artifacts = AsyncMock(return_value=mock_scoring_result)
            mock_scoring_service_cls.return_value = mock_scoring_service

            response = client.get("/api/v1/match?q=pdf&include_breakdown=true")

            assert response.status_code == 200
            data = response.json()

            # Check first match has breakdown
            if data["matches"]:
                first_match = data["matches"][0]
                assert "breakdown" in first_match
                breakdown = first_match["breakdown"]
                assert "trust_score" in breakdown
                assert "quality_score" in breakdown
                assert "match_score" in breakdown
                assert "semantic_used" in breakdown
                assert "context_boost_applied" in breakdown

                # Verify score ranges
                assert 0 <= breakdown["trust_score"] <= 100
                assert 0 <= breakdown["quality_score"] <= 100
                assert 0 <= breakdown["match_score"] <= 100

    def test_empty_query_returns_422(self, client):
        """Test empty query returns 422 Unprocessable Entity (validation error)."""
        response = client.get("/api/v1/match?q=")
        assert response.status_code == 422
        # FastAPI validation error format
        detail = response.json()["detail"]
        assert isinstance(detail, list)
        assert any("at least 1 character" in str(err) for err in detail)

    def test_response_includes_schema_version(self, client, mock_scoring_result):
        """Test response includes schema_version field."""
        with patch("skillmeat.api.routers.match.ScoringService") as mock_scoring_service_cls:
            mock_scoring_service = MagicMock()
            mock_scoring_service.score_artifacts = AsyncMock(return_value=mock_scoring_result)
            mock_scoring_service_cls.return_value = mock_scoring_service

            response = client.get("/api/v1/match?q=test")

            assert response.status_code == 200
            data = response.json()
            assert "schema_version" in data
            assert data["schema_version"] == "1.0.0"

    def test_degradation_flags_when_semantic_unavailable(self, client, mock_degraded_scoring_result):
        """Test degradation flags when semantic scoring unavailable."""
        with patch("skillmeat.api.routers.match.ScoringService") as mock_scoring_service_cls:
            mock_scoring_service = MagicMock()
            mock_scoring_service.score_artifacts = AsyncMock(return_value=mock_degraded_scoring_result)
            mock_scoring_service_cls.return_value = mock_scoring_service

            response = client.get("/api/v1/match?q=pdf")

            assert response.status_code == 200
            data = response.json()
            assert data["degraded"] is True
            assert data["degradation_reason"] is not None
            assert "unavailable" in data["degradation_reason"].lower()

    def test_invalid_limit_parameter(self, client):
        """Test invalid limit parameter returns validation error."""
        # Limit too high
        response = client.get("/api/v1/match?q=test&limit=200")
        assert response.status_code == 422  # Validation error

        # Limit too low
        response = client.get("/api/v1/match?q=test&limit=0")
        assert response.status_code == 422

    def test_invalid_min_confidence_parameter(self, client):
        """Test invalid min_confidence parameter returns validation error."""
        # Min confidence too high
        response = client.get("/api/v1/match?q=test&min_confidence=150")
        assert response.status_code == 422

        # Min confidence negative
        response = client.get("/api/v1/match?q=test&min_confidence=-10")
        assert response.status_code == 422

    def test_scoring_service_error_returns_500(self, client):
        """Test scoring service error returns 500."""
        with patch("skillmeat.api.routers.match.ScoringService") as mock_scoring_service_cls:
            mock_scoring_service = MagicMock()
            mock_scoring_service.score_artifacts = AsyncMock(side_effect=Exception("Scoring failed"))
            mock_scoring_service_cls.return_value = mock_scoring_service

            response = client.get("/api/v1/match?q=test")

            assert response.status_code == 500
            assert "failed" in response.json()["detail"].lower()

    def test_no_matches_returns_empty_list(self, client):
        """Test no matches returns empty list (not error)."""
        with patch("skillmeat.api.routers.match.ScoringService") as mock_scoring_service_cls:
            mock_scoring_service = MagicMock()
            mock_scoring_service.score_artifacts = AsyncMock(
                return_value=ScoringResult(
                    scores=[],
                    used_semantic=False,
                    degraded=False,
                    degradation_reason=None,
                    duration_ms=50.0,
                    query="nonexistent",
                )
            )
            mock_scoring_service_cls.return_value = mock_scoring_service

            response = client.get("/api/v1/match?q=nonexistent")

            assert response.status_code == 200
            data = response.json()
            assert data["matches"] == []
            assert data["total"] == 0
