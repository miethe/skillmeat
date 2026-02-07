"""Tests for MemoryExtractorService."""

import pytest
from sqlalchemy.orm import sessionmaker

from skillmeat.cache.models import Base, Project, create_db_engine
from skillmeat.core.services.memory_extractor_service import MemoryExtractorService


PROJECT_ID = "proj-extract-test"


@pytest.fixture
def seeded_db_path(tmp_path):
    db_path = tmp_path / "extract.db"
    engine = create_db_engine(db_path)
    Base.metadata.create_all(engine)

    session = sessionmaker(bind=engine)()
    session.add(
        Project(
            id=PROJECT_ID,
            name="Extraction Test Project",
            path="/tmp/extraction-project",
            status="active",
        )
    )
    session.commit()
    session.close()
    engine.dispose()

    return str(db_path)


def test_preview_extracts_candidates(seeded_db_path):
    service = MemoryExtractorService(db_path=seeded_db_path)
    corpus = """
    Decision: Use SQLAlchemy for persistence.
    Constraint: We must keep p95 latency under 200ms.
    Gotcha: Beware sqlite lock timeout during parallel tests.
    """

    candidates = service.preview(
        project_id=PROJECT_ID,
        text_corpus=corpus,
        profile="balanced",
        min_confidence=0.6,
    )

    assert len(candidates) >= 2
    assert all(c["status"] == "candidate" for c in candidates)
    assert all(c["confidence"] >= 0.6 for c in candidates)


def test_apply_persists_candidates_as_candidate_status(seeded_db_path):
    service = MemoryExtractorService(db_path=seeded_db_path)
    corpus = "Decision: Choose deterministic retries for flaky API calls."

    result = service.apply(
        project_id=PROJECT_ID,
        text_corpus=corpus,
        profile="balanced",
        min_confidence=0.6,
    )

    assert result["preview_total"] >= 1
    assert len(result["created"]) >= 1
    assert all(item["status"] == "candidate" for item in result["created"])


def test_profile_scoring_order_strict_vs_aggressive(seeded_db_path):
    service = MemoryExtractorService(db_path=seeded_db_path)
    corpus = "Decision: Use transactional retries for lock contention handling."

    strict = service.preview(
        project_id=PROJECT_ID,
        text_corpus=corpus,
        profile="strict",
        min_confidence=0.0,
    )
    aggressive = service.preview(
        project_id=PROJECT_ID,
        text_corpus=corpus,
        profile="aggressive",
        min_confidence=0.0,
    )

    assert len(strict) == 1
    assert len(aggressive) == 1
    assert aggressive[0]["confidence"] > strict[0]["confidence"]


def test_invalid_profile_raises_value_error(seeded_db_path):
    service = MemoryExtractorService(db_path=seeded_db_path)

    with pytest.raises(ValueError, match="Invalid extraction profile"):
        service.preview(
            project_id=PROJECT_ID,
            text_corpus="Decision: Use deterministic retries.",
            profile="experimental",
            min_confidence=0.0,
        )
