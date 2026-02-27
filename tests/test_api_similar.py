"""Integration tests for the GET /api/v1/artifacts/{artifact_id}/similar endpoint.

Tests mock SimilarityService.find_similar() at the service level so no real
scoring computation occurs.  A real in-memory SQLite database is used so that
the Artifact lookup (type:name → uuid resolution) executes exactly as it would
in production.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app
from skillmeat.cache.models import Artifact, Base, Project
from skillmeat.core.similarity import MatchType, ScoreBreakdown, SimilarityResult


# =============================================================================
# Helpers
# =============================================================================

_SKILL_TYPE = "skill"


def _make_breakdown(
    content: float = 0.5,
    structure: float = 0.5,
    metadata: float = 0.5,
    keyword: float = 0.5,
    semantic: float | None = None,
) -> ScoreBreakdown:
    return ScoreBreakdown(
        content_score=content,
        structure_score=structure,
        metadata_score=metadata,
        keyword_score=keyword,
        semantic_score=semantic,
    )


def _make_artifact_row(name: str, artifact_uuid: str | None = None) -> MagicMock:
    """Return a minimal mock that mimics an Artifact ORM row for SimilarityResult."""
    row = MagicMock()
    row.name = name
    row.type = _SKILL_TYPE
    row.artifact_type = _SKILL_TYPE
    row.source = f"github.com/test/{name}"
    # Pin description and tags to scalar values so Pydantic validation passes.
    row.description = None
    row.artifact_metadata = None
    row.tags = []
    return row


def _make_result(
    artifact_id: str,
    name: str,
    composite_score: float,
) -> SimilarityResult:
    """Build a SimilarityResult as SimilarityService would produce."""
    return SimilarityResult(
        artifact_id=artifact_id,
        artifact=_make_artifact_row(name),
        composite_score=composite_score,
        breakdown=_make_breakdown(),
    )


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def test_settings():
    """API settings configured for testing (no API key, no auth)."""
    return APISettings(
        env=Environment.TESTING,
        host="127.0.0.1",
        port=8000,
        log_level="DEBUG",
        api_key_enabled=False,
    )


@pytest.fixture(scope="module")
def test_engine(tmp_path_factory):
    """In-memory SQLite engine with the full schema."""
    db_path = tmp_path_factory.mktemp("db") / "test_similar.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def set_pragmas(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="module")
def test_session_factory(test_engine):
    return sessionmaker(bind=test_engine, autocommit=False, autoflush=False)


@pytest.fixture
def test_db(test_session_factory):
    """Provide a fresh session for each test; roll back after."""
    session = test_session_factory()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="module")
def shared_project(test_engine):
    """One Project row shared across all module-scope fixtures."""
    factory = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    session = factory()
    project = Project(
        id=uuid.uuid4().hex,
        name="Test Project",
        path="/tmp/similar-test-project",
        status="active",
    )
    session.add(project)
    session.commit()
    project_id = project.id
    session.close()
    return project_id


@pytest.fixture(scope="module")
def source_artifact(test_session_factory, shared_project):
    """Create the source artifact that the endpoint looks up (module-scoped, inserted once)."""
    session = test_session_factory()
    art_uuid = uuid.uuid4().hex
    artifact = Artifact(
        id="skill:source-artifact",
        uuid=art_uuid,
        project_id=shared_project,
        name="source-artifact",
        type=_SKILL_TYPE,
    )
    session.add(artifact)
    session.commit()
    artifact_id = artifact.id
    artifact_uuid = artifact.uuid
    artifact_name = artifact.name
    session.close()

    # Return a lightweight namespace so callers can access .id / .uuid / .name
    class _Row:
        id = artifact_id
        uuid = artifact_uuid
        name = artifact_name

    return _Row()


@pytest.fixture(scope="module")
def similar_artifact_row(test_session_factory, shared_project):
    """Create a second artifact in the DB that acts as a similar candidate (module-scoped)."""
    session = test_session_factory()
    art_uuid = uuid.uuid4().hex
    artifact = Artifact(
        id="skill:similar-one",
        uuid=art_uuid,
        project_id=shared_project,
        name="similar-one",
        type=_SKILL_TYPE,
    )
    session.add(artifact)
    session.commit()
    artifact_id = artifact.id
    artifact_uuid = artifact.uuid
    artifact_name = artifact.name
    session.close()

    class _Row:
        id = artifact_id
        uuid = artifact_uuid
        name = artifact_name

    return _Row()


@pytest.fixture
def app(test_settings):
    """FastAPI application configured for testing."""
    from skillmeat.api.config import get_settings

    application = create_app(test_settings)
    application.dependency_overrides[get_settings] = lambda: test_settings
    return application


@pytest.fixture
def client(app, test_session_factory):
    """Test client with DB session and auth mocked."""
    from skillmeat.api.middleware.auth import verify_token

    app.dependency_overrides[verify_token] = lambda: "mock-token"

    def get_test_session():
        return test_session_factory()

    def get_session_from_test_factory():
        return test_session_factory()

    with patch(
        "skillmeat.api.routers.artifacts.get_session", get_session_from_test_factory
    ):
        with TestClient(app) as test_client:
            yield test_client

    app.dependency_overrides.clear()


# =============================================================================
# Tests
# =============================================================================


class TestSimilarArtifactsHappyPath:
    """test_similar_happy_path — 200 with populated items list."""

    def test_returns_200_with_items(self, client, source_artifact, similar_artifact_row):
        """Endpoint returns 200 and SimilarArtifactsResponse with results."""
        mock_result = _make_result(
            artifact_id=similar_artifact_row.id,
            name=similar_artifact_row.name,
            composite_score=0.75,
        )

        with patch("skillmeat.core.similarity.SimilarityService.find_similar") as mock_find:
            mock_find.return_value = [mock_result]

            response = client.get("/api/v1/artifacts/skill:source-artifact/similar")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["artifact_id"] == "skill:source-artifact"
        assert data["total"] == 1
        assert len(data["items"]) == 1

        item = data["items"][0]
        assert item["artifact_id"] == similar_artifact_row.id
        assert item["name"] == "similar-one"
        assert item["artifact_type"] == _SKILL_TYPE
        assert item["composite_score"] == pytest.approx(0.75, abs=1e-6)
        assert item["match_type"] == MatchType.SIMILAR.value
        assert "breakdown" in item

    def test_response_breakdown_fields_present(self, client, source_artifact):
        """Breakdown contains all expected score fields."""
        breakdown = _make_breakdown(
            content=0.6,
            structure=0.7,
            metadata=0.8,
            keyword=0.9,
            semantic=0.5,
        )
        mock_result = SimilarityResult(
            artifact_id="skill:some-other",
            artifact=_make_artifact_row("some-other"),
            composite_score=0.55,
            breakdown=breakdown,
        )

        with patch("skillmeat.core.similarity.SimilarityService.find_similar") as mock_find:
            mock_find.return_value = [mock_result]

            response = client.get("/api/v1/artifacts/skill:source-artifact/similar")

        assert response.status_code == status.HTTP_200_OK
        bd = response.json()["items"][0]["breakdown"]
        assert bd["content_score"] == pytest.approx(0.6)
        assert bd["structure_score"] == pytest.approx(0.7)
        assert bd["metadata_score"] == pytest.approx(0.8)
        assert bd["keyword_score"] == pytest.approx(0.9)
        assert bd["semantic_score"] == pytest.approx(0.5)


class TestSimilarArtifactsEmptyResults:
    """test_similar_empty_results — 200 with empty items when no matches."""

    def test_returns_200_with_empty_items(self, client, source_artifact):
        """When find_similar returns no results, response has empty items list."""
        with patch("skillmeat.core.similarity.SimilarityService.find_similar") as mock_find:
            mock_find.return_value = []

            response = client.get("/api/v1/artifacts/skill:source-artifact/similar")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["artifact_id"] == "skill:source-artifact"
        assert data["total"] == 0
        assert data["items"] == []


class TestSimilarArtifactsNotFound:
    """test_similar_artifact_not_found — 404 for non-existent artifact_id."""

    def test_nonexistent_artifact_returns_404(self, client):
        """Artifact ID that is not in the DB returns 404."""
        with patch("skillmeat.core.similarity.SimilarityService.find_similar") as mock_find:
            response = client.get("/api/v1/artifacts/skill:does-not-exist/similar")
            mock_find.assert_not_called()

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()


class TestSimilarArtifactsLimitParam:
    """test_similar_limit_param — limit query parameter is forwarded correctly."""

    def test_limit_forwarded_to_service(self, client, source_artifact):
        """limit=2 is passed through to SimilarityService.find_similar."""
        results = [
            _make_result("skill:a", "a", 0.9),
            _make_result("skill:b", "b", 0.8),
        ]

        with patch("skillmeat.core.similarity.SimilarityService.find_similar") as mock_find:
            mock_find.return_value = results
            response = client.get(
                "/api/v1/artifacts/skill:source-artifact/similar?limit=2"
            )
            mock_find.assert_called_once()
            call_kwargs = mock_find.call_args.kwargs
            assert call_kwargs["limit"] == 2

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()["items"]) == 2

    def test_limit_zero_returns_422(self, client, source_artifact):
        """limit=0 violates ge=1 constraint → 422."""
        response = client.get("/api/v1/artifacts/skill:source-artifact/similar?limit=0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_limit_over_maximum_returns_422(self, client, source_artifact):
        """limit=51 violates le=50 constraint → 422."""
        response = client.get("/api/v1/artifacts/skill:source-artifact/similar?limit=51")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestSimilarArtifactsMinScoreParam:
    """test_similar_min_score_param — high min_score filters out low-scoring matches."""

    def test_min_score_forwarded_to_service(self, client, source_artifact):
        """min_score is passed through to find_similar; endpoint returns whatever the service gives."""
        with patch("skillmeat.core.similarity.SimilarityService.find_similar") as mock_find:
            mock_find.return_value = []  # service already filtered
            response = client.get(
                "/api/v1/artifacts/skill:source-artifact/similar?min_score=0.99"
            )
            call_kwargs = mock_find.call_args.kwargs
            assert call_kwargs["min_score"] == pytest.approx(0.99)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["total"] == 0

    def test_high_min_score_yields_empty_when_service_filters(
        self, client, source_artifact
    ):
        """Service returning no results for high threshold → empty items."""
        with patch("skillmeat.core.similarity.SimilarityService.find_similar") as mock_find:
            mock_find.return_value = []
            response = client.get(
                "/api/v1/artifacts/skill:source-artifact/similar?min_score=0.99"
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["items"] == []

    def test_min_score_negative_returns_422(self, client, source_artifact):
        """min_score=-1 violates ge=0.0 constraint → 422."""
        response = client.get(
            "/api/v1/artifacts/skill:source-artifact/similar?min_score=-1"
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_min_score_above_one_returns_422(self, client, source_artifact):
        """min_score=2 violates le=1.0 constraint → 422."""
        response = client.get(
            "/api/v1/artifacts/skill:source-artifact/similar?min_score=2"
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestSimilarArtifactsSourceFilter:
    """test_similar_source_filter — source query parameter is forwarded correctly."""

    @pytest.mark.parametrize("source_value", ["collection", "marketplace", "all"])
    def test_valid_source_forwarded(self, client, source_artifact, source_value):
        """Each valid source value is accepted and forwarded to find_similar."""
        with patch("skillmeat.core.similarity.SimilarityService.find_similar") as mock_find:
            mock_find.return_value = []
            response = client.get(
                f"/api/v1/artifacts/skill:source-artifact/similar?source={source_value}"
            )
            call_kwargs = mock_find.call_args.kwargs
            assert call_kwargs["source"] == source_value

        assert response.status_code == status.HTTP_200_OK

    def test_default_source_is_collection(self, client, source_artifact):
        """When source is omitted the default 'collection' is used."""
        with patch("skillmeat.core.similarity.SimilarityService.find_similar") as mock_find:
            mock_find.return_value = []
            client.get("/api/v1/artifacts/skill:source-artifact/similar")
            call_kwargs = mock_find.call_args.kwargs
            assert call_kwargs["source"] == "collection"

    def test_invalid_source_returns_422(self, client, source_artifact):
        """source=unknown violates the pattern constraint → 422."""
        response = client.get(
            "/api/v1/artifacts/skill:source-artifact/similar?source=unknown"
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestSimilarArtifactsInvalidParams:
    """test_similar_invalid_params — combined/edge-case validation failures."""

    def test_invalid_source_string(self, client, source_artifact):
        """source='bad' is rejected with 422."""
        response = client.get(
            "/api/v1/artifacts/skill:source-artifact/similar?source=bad"
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_non_numeric_limit(self, client, source_artifact):
        """limit='abc' cannot be coerced → 422."""
        response = client.get(
            "/api/v1/artifacts/skill:source-artifact/similar?limit=abc"
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_non_numeric_min_score(self, client, source_artifact):
        """min_score='high' cannot be coerced → 422."""
        response = client.get(
            "/api/v1/artifacts/skill:source-artifact/similar?min_score=high"
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_multiple_invalid_params_still_422(self, client, source_artifact):
        """Multiple invalid params at once → still 422."""
        response = client.get(
            "/api/v1/artifacts/skill:source-artifact/similar?limit=0&min_score=-1&source=nope"
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
