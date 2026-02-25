"""Unit tests for SimilarityService, SimilarityResult, ScoreBreakdown, and MatchType.

Tests cover:
- Happy path: find_similar returns sorted SimilarityResult list
- Empty results when all candidates score below min_score
- Artifact-not-found returns empty list (no exception)
- Limit enforcement on top-N results
- min_score threshold filtering
- SemanticScorer timeout fallback (scores still returned, semantic_score=None)
- SemanticScorer unavailable (None) — keyword-only scoring path
- Composite score weight calculation with all components present
- Composite score weight redistribution when semantic_score is None
- MatchType classification thresholds
- ScoreBreakdown is a frozen dataclass (immutable)
"""

from __future__ import annotations

import concurrent.futures
import dataclasses
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from skillmeat.core.similarity import (
    MatchType,
    ScoreBreakdown,
    SimilarityResult,
    SimilarityService,
)


# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------

def _make_breakdown(
    keyword: float = 0.0,
    content: float = 0.0,
    structure: float = 0.0,
    metadata: float = 0.0,
    semantic: float | None = None,
) -> ScoreBreakdown:
    """Return a ScoreBreakdown with the given component values."""
    return ScoreBreakdown(
        keyword_score=keyword,
        content_score=content,
        structure_score=structure,
        metadata_score=metadata,
        semantic_score=semantic,
    )


def _make_artifact_row(
    uuid: str,
    artifact_id: str = "skill:canvas",
    name: str = "canvas",
    artifact_type: str = "skill",
    description: str = "A canvas skill",
    content_hash: str = "abc123",
    project_id: str = "collection_artifacts_global",
) -> MagicMock:
    """Return a mock Artifact ORM row with the minimum attributes needed."""
    row = MagicMock()
    row.uuid = uuid
    row.id = artifact_id
    row.name = name
    row.type = artifact_type
    row.description = description
    row.content_hash = content_hash
    row.project_id = project_id
    # artifact_metadata is used in _fingerprint_from_row; return None for simplicity
    row.artifact_metadata = None
    # MarketplaceCatalogEntry-style attributes fall back to None
    row.title = None
    row.tags = None
    row.artifact_type = artifact_type  # alias used in fingerprint builder
    row.total_size = 0
    row.file_count = 0
    row.structure_hash = ""
    row.metadata_hash = ""
    return row


def _make_session_with_target_and_candidates(
    target_row: MagicMock,
    candidate_rows: list[MagicMock],
) -> MagicMock:
    """Return a mock SQLAlchemy session wired for _find_similar_impl."""
    session = MagicMock()

    # session.query(Artifact).filter(...).first() → target_row
    # session.query(Artifact).filter(...).all() → candidate_rows
    # We intercept via side_effect on the query chain.
    query_mock = MagicMock()
    filter_mock = MagicMock()

    # .first() returns target
    filter_mock.first.return_value = target_row
    # .all() returns candidates
    filter_mock.all.return_value = candidate_rows
    filter_mock.filter.return_value = filter_mock  # support chained .filter().filter()

    query_mock.filter.return_value = filter_mock
    session.query.return_value = query_mock

    return session


# ---------------------------------------------------------------------------
# SimilarityService construction helper (bypasses real SemanticScorer init)
# ---------------------------------------------------------------------------

def _make_service(session: MagicMock, semantic: object = None) -> SimilarityService:
    """Build a SimilarityService with mocked internal dependencies.

    Bypasses __init__ so no real SemanticScorer is constructed.
    Sets ``_semantic`` to the provided value (None by default).

    MatchAnalyzer is loaded via ``spec_from_file_location`` (not by dotted
    package name) to avoid the pre-existing circular import in the codebase:
    ``skillmeat.core.scoring.__init__`` → quality_scorer → rating_store →
    cache.models → cache.marketplace → api.schemas → api.server →
    api.routers.ratings → ``from skillmeat.core.scoring import QualityScorer``
    (which fails because the package __init__ is still mid-execution).
    """
    import importlib.util
    import sys

    _MOD_KEY = "_skillmeat_match_analyzer_direct"
    if _MOD_KEY in sys.modules:
        mod = sys.modules[_MOD_KEY]
    else:
        import skillmeat  # ensure package root is in sys.modules

        pkg_root = Path(skillmeat.__file__).parent
        ma_path = pkg_root / "core" / "scoring" / "match_analyzer.py"
        spec = importlib.util.spec_from_file_location(_MOD_KEY, ma_path)
        mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        sys.modules[_MOD_KEY] = mod
        spec.loader.exec_module(mod)  # type: ignore[union-attr]

    analyzer = mod.MatchAnalyzer()

    svc = SimilarityService.__new__(SimilarityService)
    svc._analyzer = analyzer
    svc._session = session
    svc._semantic = semantic
    return svc


# ---------------------------------------------------------------------------
# Test: ScoreBreakdown immutability
# ---------------------------------------------------------------------------

def test_score_breakdown_frozen():
    """ScoreBreakdown is a frozen dataclass — mutation raises FrozenInstanceError."""
    bd = _make_breakdown(keyword=0.5, content=0.5)
    with pytest.raises((dataclasses.FrozenInstanceError, TypeError, AttributeError)):
        bd.keyword_score = 0.9  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Test: MatchType classification
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "score, expected_type",
    [
        (0.95, MatchType.EXACT),
        (1.00, MatchType.EXACT),
        (0.80, MatchType.NEAR_DUPLICATE),
        (0.82, MatchType.NEAR_DUPLICATE),
        (0.94, MatchType.NEAR_DUPLICATE),
        (0.50, MatchType.SIMILAR),
        (0.75, MatchType.SIMILAR),
        (0.79, MatchType.SIMILAR),
        (0.30, MatchType.RELATED),
        (0.00, MatchType.RELATED),
        (0.49, MatchType.RELATED),
    ],
)
def test_match_type_classification(score: float, expected_type: MatchType):
    """SimilarityResult derives correct MatchType from composite_score."""
    result = SimilarityResult(
        artifact_id="skill:test",
        artifact=None,
        composite_score=score,
        breakdown=_make_breakdown(),
    )
    assert result.match_type is expected_type


# ---------------------------------------------------------------------------
# Test: composite score weight calculation
# ---------------------------------------------------------------------------

def test_composite_score_weights():
    """Composite score uses documented weights when semantic is available.

    Weights: keyword=0.30, content=0.25, structure=0.20, metadata=0.15, semantic=0.10
    """
    svc = _make_service(session=MagicMock())
    bd = _make_breakdown(
        keyword=1.0,
        content=0.0,
        structure=0.0,
        metadata=0.0,
        semantic=0.0,
    )
    score = svc._compute_composite_score(bd)
    assert pytest.approx(score, abs=1e-6) == 0.30

    bd2 = _make_breakdown(
        keyword=0.0,
        content=1.0,
        structure=0.0,
        metadata=0.0,
        semantic=0.0,
    )
    assert pytest.approx(svc._compute_composite_score(bd2), abs=1e-6) == 0.25

    bd_all = _make_breakdown(
        keyword=1.0,
        content=1.0,
        structure=1.0,
        metadata=1.0,
        semantic=1.0,
    )
    assert pytest.approx(svc._compute_composite_score(bd_all), abs=1e-6) == 1.0


def test_composite_score_no_semantic():
    """Composite score redistributes the 0.10 semantic weight when semantic=None.

    Original weights without semantic: keyword=0.30, content=0.25, structure=0.20, metadata=0.15.
    Sum = 0.90.  Each is scaled up by 1/0.90 so they sum to 1.0.
    Redistributed: keyword≈0.3333, content≈0.2778, structure≈0.2222, metadata≈0.1667.
    """
    svc = _make_service(session=MagicMock())
    bd = _make_breakdown(
        keyword=1.0,
        content=0.0,
        structure=0.0,
        metadata=0.0,
        semantic=None,  # semantic unavailable
    )
    score = svc._compute_composite_score(bd)
    # keyword alone should be 0.30 / 0.90 ≈ 0.3333
    assert pytest.approx(score, abs=1e-4) == 0.30 / 0.90

    bd_all_no_sem = _make_breakdown(
        keyword=1.0,
        content=1.0,
        structure=1.0,
        metadata=1.0,
        semantic=None,
    )
    # All non-semantic components at 1.0 → composite must equal 1.0
    assert pytest.approx(svc._compute_composite_score(bd_all_no_sem), abs=1e-6) == 1.0


# ---------------------------------------------------------------------------
# Test: find_similar — happy path
# ---------------------------------------------------------------------------

def test_find_similar_happy_path():
    """find_similar returns SimilarityResults sorted by composite_score descending."""
    target = _make_artifact_row(uuid="uuid-target", artifact_id="skill:target", name="target")
    cand_a = _make_artifact_row(uuid="uuid-a", artifact_id="skill:a", name="a")
    cand_b = _make_artifact_row(uuid="uuid-b", artifact_id="skill:b", name="b")
    cand_c = _make_artifact_row(uuid="uuid-c", artifact_id="skill:c", name="c")

    session = _make_session_with_target_and_candidates(target, [cand_a, cand_b, cand_c])
    svc = _make_service(session)

    # Control breakdown scores via MatchAnalyzer.compare mock
    breakdowns = {
        "uuid-a": _make_breakdown(keyword=0.9, content=0.9, structure=0.9, metadata=0.9),
        "uuid-b": _make_breakdown(keyword=0.5, content=0.5, structure=0.5, metadata=0.5),
        "uuid-c": _make_breakdown(keyword=0.7, content=0.7, structure=0.7, metadata=0.7),
    }

    def _fake_compare(fp_a, fp_b):
        # fp_b.artifact_name is derived from the candidate row's name attribute
        for row in [cand_a, cand_b, cand_c]:
            if row.name == fp_b.artifact_name:
                return breakdowns[row.uuid]
        return _make_breakdown()

    svc._analyzer.compare = _fake_compare  # type: ignore[method-assign]

    results = svc.find_similar("uuid-target", limit=10, min_score=0.1)

    assert len(results) == 3
    # Must be sorted descending
    scores = [r.composite_score for r in results]
    assert scores == sorted(scores, reverse=True)
    # The highest scorer is cand_a (keyword+content+structure+metadata all at 0.9)
    assert results[0].artifact_id == "skill:a"


# ---------------------------------------------------------------------------
# Test: find_similar — empty results (all below min_score)
# ---------------------------------------------------------------------------

def test_find_similar_empty_results():
    """Returns empty list when all candidates score below min_score."""
    target = _make_artifact_row(uuid="uuid-t")
    cand = _make_artifact_row(uuid="uuid-c", name="other")

    session = _make_session_with_target_and_candidates(target, [cand])
    svc = _make_service(session)

    # All components zero → composite = 0.0, below any min_score
    svc._analyzer.compare = MagicMock(return_value=_make_breakdown())  # type: ignore[method-assign]

    results = svc.find_similar("uuid-t", min_score=0.3)
    assert results == []


# ---------------------------------------------------------------------------
# Test: find_similar — artifact not found
# ---------------------------------------------------------------------------

def test_find_similar_artifact_not_found():
    """Returns empty list when target artifact uuid does not exist in DB."""
    session = MagicMock()
    # Simulate no row found: .filter().first() returns None
    query_mock = MagicMock()
    filter_mock = MagicMock()
    filter_mock.first.return_value = None
    query_mock.filter.return_value = filter_mock
    session.query.return_value = query_mock

    svc = _make_service(session)
    results = svc.find_similar("nonexistent-uuid")
    assert results == []


# ---------------------------------------------------------------------------
# Test: find_similar — limit enforcement
# ---------------------------------------------------------------------------

def test_find_similar_limit_enforcement():
    """Only top `limit` results are returned even when more candidates score above min_score."""
    target = _make_artifact_row(uuid="uuid-t")
    candidates = [
        _make_artifact_row(uuid=f"uuid-{i}", artifact_id=f"skill:{i}", name=f"cand{i}")
        for i in range(10)
    ]

    session = _make_session_with_target_and_candidates(target, candidates)
    svc = _make_service(session)

    # All candidates score high
    svc._analyzer.compare = MagicMock(  # type: ignore[method-assign]
        return_value=_make_breakdown(keyword=0.9, content=0.9, structure=0.9, metadata=0.9)
    )

    results = svc.find_similar("uuid-t", limit=3, min_score=0.1)
    assert len(results) == 3


# ---------------------------------------------------------------------------
# Test: find_similar — min_score filtering
# ---------------------------------------------------------------------------

def test_find_similar_min_score_filter():
    """Only candidates whose composite score >= min_score are returned."""
    target = _make_artifact_row(uuid="uuid-t")
    high = _make_artifact_row(uuid="uuid-h", artifact_id="skill:high", name="high")
    low = _make_artifact_row(uuid="uuid-l", artifact_id="skill:low", name="low")

    session = _make_session_with_target_and_candidates(target, [high, low])
    svc = _make_service(session)

    def _fake_compare(fp_a, fp_b):
        if fp_b.artifact_name == "high":
            return _make_breakdown(keyword=0.8, content=0.8, structure=0.8, metadata=0.8)
        # low scorer: all zeros
        return _make_breakdown()

    svc._analyzer.compare = _fake_compare  # type: ignore[method-assign]

    results = svc.find_similar("uuid-t", min_score=0.5)
    assert len(results) == 1
    assert results[0].artifact_id == "skill:high"


# ---------------------------------------------------------------------------
# Test: SemanticScorer timeout fallback
# ---------------------------------------------------------------------------

def test_semantic_scorer_timeout_fallback():
    """When SemanticScorer times out, results are still returned with semantic_score=None.

    The composite score must still be computed (using redistributed weights).
    """
    target = _make_artifact_row(uuid="uuid-t", name="target-artifact")
    cand = _make_artifact_row(uuid="uuid-c", artifact_id="skill:c", name="cand-artifact")

    session = _make_session_with_target_and_candidates(target, [cand])

    # Build a fake semantic scorer whose score_artifact coroutine times out
    fake_semantic = MagicMock()
    fake_semantic  # will be set on service._semantic

    svc = _make_service(session, semantic=fake_semantic)

    # Override the timeout helper to simulate a real TimeoutError from futures
    original_score = svc._score_semantic_with_timeout

    def _timeout_score(target_fp, candidate_fp):
        return None  # simulates what happens after TimeoutError catches

    svc._score_semantic_with_timeout = _timeout_score  # type: ignore[method-assign]

    high_breakdown = _make_breakdown(keyword=0.8, content=0.8, structure=0.8, metadata=0.8)
    svc._analyzer.compare = MagicMock(return_value=high_breakdown)  # type: ignore[method-assign]

    results = svc.find_similar("uuid-t", min_score=0.1)

    assert len(results) == 1
    result = results[0]
    # semantic_score must be None (timeout fallback)
    assert result.breakdown.semantic_score is None
    # composite_score must be > 0 (computed from the four remaining components)
    assert result.composite_score > 0.0


def test_semantic_scorer_timeout_via_futures():
    """_score_semantic_with_timeout returns None when futures.TimeoutError is raised."""
    target = _make_artifact_row(uuid="uuid-t", name="target-artifact")
    cand = _make_artifact_row(uuid="uuid-c", artifact_id="skill:c", name="cand-artifact")

    session = _make_session_with_target_and_candidates(target, [cand])

    fake_semantic = MagicMock()
    svc = _make_service(session, semantic=fake_semantic)

    from skillmeat.models import ArtifactFingerprint

    target_fp = ArtifactFingerprint(
        artifact_path=Path("/skill/target"),
        artifact_name="target-artifact",
        artifact_type="skill",
        content_hash="",
        metadata_hash="",
        structure_hash="",
        title="Target Artifact",
        description="A skill for testing",
        tags=["test"],
        file_count=1,
        total_size=100,
    )
    cand_fp = ArtifactFingerprint(
        artifact_path=Path("/skill/cand"),
        artifact_name="cand-artifact",
        artifact_type="skill",
        content_hash="",
        metadata_hash="",
        structure_hash="",
        title=None,
        description=None,
        tags=[],
        file_count=1,
        total_size=100,
    )

    # Patch ThreadPoolExecutor.submit().result() to raise TimeoutError
    with patch("concurrent.futures.ThreadPoolExecutor") as mock_executor_cls:
        mock_executor = MagicMock()
        mock_executor_cls.return_value.__enter__ = MagicMock(return_value=mock_executor)
        mock_executor_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_future = MagicMock()
        mock_future.result.side_effect = concurrent.futures.TimeoutError()
        mock_executor.submit.return_value = mock_future

        score = svc._score_semantic_with_timeout(target_fp, cand_fp)

    assert score is None


# ---------------------------------------------------------------------------
# Test: SemanticScorer unavailable (None)
# ---------------------------------------------------------------------------

def test_semantic_scorer_unavailable():
    """When _semantic is None, keyword-only scoring path is used.

    Composite score must be > 0 when keyword/content/structure/metadata components
    are non-zero, and semantic_score on the breakdown must be None.
    """
    target = _make_artifact_row(uuid="uuid-t")
    cand = _make_artifact_row(uuid="uuid-c", artifact_id="skill:c", name="cand")

    session = _make_session_with_target_and_candidates(target, [cand])
    svc = _make_service(session, semantic=None)  # explicitly no semantic scorer

    non_zero_bd = _make_breakdown(keyword=0.6, content=0.6, structure=0.6, metadata=0.6)
    svc._analyzer.compare = MagicMock(return_value=non_zero_bd)  # type: ignore[method-assign]

    results = svc.find_similar("uuid-t", min_score=0.1)

    assert len(results) == 1
    result = results[0]
    assert result.breakdown.semantic_score is None
    assert result.composite_score > 0.0

    # Verify _score_semantic_with_timeout returns None immediately when _semantic is None
    from skillmeat.models import ArtifactFingerprint

    dummy_fp = ArtifactFingerprint(
        artifact_path=Path("/skill/test"),
        artifact_name="test",
        artifact_type="skill",
        content_hash="",
        metadata_hash="",
        structure_hash="",
        title=None,
        description=None,
        tags=[],
        file_count=0,
        total_size=0,
    )
    assert svc._score_semantic_with_timeout(dummy_fp, dummy_fp) is None


# ---------------------------------------------------------------------------
# Test: SimilarityResult dataclass fields
# ---------------------------------------------------------------------------

def test_similarity_result_fields():
    """SimilarityResult stores artifact_id, artifact, composite_score, and breakdown."""
    bd = _make_breakdown(keyword=0.5, content=0.5)
    fake_artifact = object()
    result = SimilarityResult(
        artifact_id="skill:canvas",
        artifact=fake_artifact,
        composite_score=0.72,
        breakdown=bd,
    )
    assert result.artifact_id == "skill:canvas"
    assert result.artifact is fake_artifact
    assert result.composite_score == 0.72
    assert result.breakdown is bd
    assert result.match_type is MatchType.SIMILAR


# ---------------------------------------------------------------------------
# Test: no candidates scenario
# ---------------------------------------------------------------------------

def test_find_similar_no_candidates():
    """Returns empty list when no candidate rows exist in the collection."""
    target = _make_artifact_row(uuid="uuid-t")
    session = _make_session_with_target_and_candidates(target, [])
    svc = _make_service(session)

    results = svc.find_similar("uuid-t")
    assert results == []


# ---------------------------------------------------------------------------
# Test: _fingerprint_from_row — artifact_metadata enrichment branch
# ---------------------------------------------------------------------------

def test_fingerprint_from_row_with_artifact_metadata():
    """_fingerprint_from_row uses artifact_metadata.get_tags_list() and get_metadata_dict()."""
    row = _make_artifact_row(uuid="uuid-x", name="enriched", description=None)

    meta = MagicMock()
    meta.description = "Meta description"
    meta.get_tags_list.return_value = ["tag-a", "tag-b"]
    meta.get_metadata_dict.return_value = {"title": "Meta Title", "description": "Dict desc"}
    row.artifact_metadata = meta

    svc = _make_service(MagicMock())
    fp = svc._fingerprint_from_row(row)

    assert fp.title == "Meta Title"
    assert "tag-a" in fp.tags
    assert "tag-b" in fp.tags
    # description comes from meta.description (non-empty) so dict description unused
    assert fp.description == "Meta description"


def test_fingerprint_from_row_metadata_dict_description_fallback():
    """_fingerprint_from_row falls back to meta_dict description when meta.description is empty."""
    row = _make_artifact_row(uuid="uuid-y", name="partial", description=None)

    meta = MagicMock()
    meta.description = None  # no direct description
    meta.get_tags_list.return_value = []
    meta.get_metadata_dict.return_value = {"title": None, "description": "Dict-only desc"}
    row.artifact_metadata = meta

    svc = _make_service(MagicMock())
    fp = svc._fingerprint_from_row(row)

    assert fp.description == "Dict-only desc"
    # title stays None when meta_dict title is falsy
    assert fp.title is None


def test_fingerprint_from_row_list_tags():
    """_fingerprint_from_row reads list-type tags from marketplace-style rows."""
    row = _make_artifact_row(uuid="uuid-mkt", name="mkt-item")
    row.artifact_metadata = None
    row.tags = ["python", "ai", "skill"]  # list form
    row.title = "Marketplace Item"

    svc = _make_service(MagicMock())
    fp = svc._fingerprint_from_row(row)

    assert fp.tags == ["python", "ai", "skill"]
    assert fp.title == "Marketplace Item"


def test_fingerprint_from_row_string_tags():
    """_fingerprint_from_row splits comma-separated string tags."""
    row = _make_artifact_row(uuid="uuid-str", name="str-item")
    row.artifact_metadata = None
    row.tags = "python, ai, skill"
    row.title = "String Tag Item"

    svc = _make_service(MagicMock())
    fp = svc._fingerprint_from_row(row)

    assert fp.tags == ["python", "ai", "skill"]


# ---------------------------------------------------------------------------
# Test: _fetch_candidates source routing
# ---------------------------------------------------------------------------

def test_fetch_candidates_marketplace_source():
    """source='marketplace' only calls _fetch_marketplace_candidates."""
    svc = _make_service(MagicMock())
    svc._fetch_collection_candidates = MagicMock(return_value=[])
    svc._fetch_marketplace_candidates = MagicMock(return_value=["mkt-row"])

    rows = svc._fetch_candidates(MagicMock(), "uuid-x", source="marketplace")

    svc._fetch_collection_candidates.assert_not_called()
    svc._fetch_marketplace_candidates.assert_called_once()
    assert rows == ["mkt-row"]


def test_fetch_candidates_all_source():
    """source='all' calls both collection and marketplace candidate fetchers."""
    svc = _make_service(MagicMock())
    svc._fetch_collection_candidates = MagicMock(return_value=["col-row"])
    svc._fetch_marketplace_candidates = MagicMock(return_value=["mkt-row"])

    rows = svc._fetch_candidates(MagicMock(), "uuid-x", source="all")

    svc._fetch_collection_candidates.assert_called_once()
    svc._fetch_marketplace_candidates.assert_called_once()
    assert "col-row" in rows
    assert "mkt-row" in rows


def test_fetch_candidates_collection_source():
    """source='collection' only calls _fetch_collection_candidates."""
    svc = _make_service(MagicMock())
    svc._fetch_collection_candidates = MagicMock(return_value=["col-row"])
    svc._fetch_marketplace_candidates = MagicMock(return_value=[])

    rows = svc._fetch_candidates(MagicMock(), "uuid-x", source="collection")

    svc._fetch_collection_candidates.assert_called_once()
    svc._fetch_marketplace_candidates.assert_not_called()
    assert rows == ["col-row"]


# ---------------------------------------------------------------------------
# Test: _score_semantic_with_timeout — successful async path
# ---------------------------------------------------------------------------

def test_score_semantic_with_timeout_success():
    """_score_semantic_with_timeout normalises scores from [0,100] to [0,1]."""
    from skillmeat.models import ArtifactFingerprint

    fake_semantic = MagicMock()
    svc = _make_service(MagicMock(), semantic=fake_semantic)

    target_fp = ArtifactFingerprint(
        artifact_path=Path("/skill/target"),
        artifact_name="my-skill",
        artifact_type="skill",
        content_hash="",
        metadata_hash="",
        structure_hash="",
        title="My Skill",
        description="Does stuff",
        tags=["skill"],
        file_count=1,
        total_size=100,
    )
    cand_fp = ArtifactFingerprint(
        artifact_path=Path("/skill/cand"),
        artifact_name="other-skill",
        artifact_type="skill",
        content_hash="",
        metadata_hash="",
        structure_hash="",
        title="Other",
        description="Other desc",
        tags=[],
        file_count=1,
        total_size=100,
    )

    # Patch ThreadPoolExecutor so future.result() returns the raw score (0-100 scale)
    with patch("concurrent.futures.ThreadPoolExecutor") as mock_exec_cls:
        mock_exec = MagicMock()
        mock_exec_cls.return_value.__enter__ = MagicMock(return_value=mock_exec)
        mock_exec_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_future = MagicMock()
        mock_future.result.return_value = 75.0  # raw score from SemanticScorer
        mock_exec.submit.return_value = mock_future

        score = svc._score_semantic_with_timeout(target_fp, cand_fp)

    assert score is not None
    assert pytest.approx(score, abs=1e-6) == 0.75  # normalised to [0, 1]


def test_score_semantic_with_timeout_error_fallback():
    """_score_semantic_with_timeout returns None when SemanticScorer raises an error."""
    from skillmeat.models import ArtifactFingerprint

    fake_semantic = MagicMock()
    svc = _make_service(MagicMock(), semantic=fake_semantic)

    target_fp = ArtifactFingerprint(
        artifact_path=Path("/skill/t"),
        artifact_name="my-skill",
        artifact_type="skill",
        content_hash="",
        metadata_hash="",
        structure_hash="",
        title="My Skill",
        description="Does stuff",
        tags=["test"],
        file_count=1,
        total_size=50,
    )
    cand_fp = ArtifactFingerprint(
        artifact_path=Path("/skill/c"),
        artifact_name="other",
        artifact_type="skill",
        content_hash="",
        metadata_hash="",
        structure_hash="",
        title=None,
        description=None,
        tags=[],
        file_count=1,
        total_size=50,
    )

    with patch("concurrent.futures.ThreadPoolExecutor") as mock_exec_cls:
        mock_exec = MagicMock()
        mock_exec_cls.return_value.__enter__ = MagicMock(return_value=mock_exec)
        mock_exec_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_future = MagicMock()
        mock_future.result.side_effect = RuntimeError("embedder exploded")
        mock_exec.submit.return_value = mock_future

        score = svc._score_semantic_with_timeout(target_fp, cand_fp)

    assert score is None


def test_score_semantic_empty_query_text():
    """_score_semantic_with_timeout returns None when target has no text for query building."""
    from skillmeat.models import ArtifactFingerprint

    fake_semantic = MagicMock()
    svc = _make_service(MagicMock(), semantic=fake_semantic)

    # Fingerprint with no name, title, or description — query_text will be empty
    empty_fp = ArtifactFingerprint(
        artifact_path=Path("/skill/empty"),
        artifact_name="",
        artifact_type="skill",
        content_hash="",
        metadata_hash="",
        structure_hash="",
        title=None,
        description=None,
        tags=[],
        file_count=0,
        total_size=0,
    )

    score = svc._score_semantic_with_timeout(empty_fp, empty_fp)
    assert score is None


# ---------------------------------------------------------------------------
# Test: find_similar — marketplace source integration
# ---------------------------------------------------------------------------

def test_find_similar_marketplace_source():
    """find_similar with source='marketplace' searches MarketplaceCatalogEntry rows."""
    target = _make_artifact_row(uuid="uuid-t", name="target")
    mkt_row = MagicMock()
    mkt_row.uuid = "uuid-mkt"
    mkt_row.id = "skill:mkt-skill"
    mkt_row.name = "mkt-skill"
    mkt_row.type = ""
    mkt_row.artifact_type = "skill"
    mkt_row.description = "A marketplace skill"
    mkt_row.content_hash = ""
    mkt_row.artifact_metadata = None
    mkt_row.title = "Marketplace Skill"
    mkt_row.tags = ["ai"]
    mkt_row.total_size = 0
    mkt_row.file_count = 0
    mkt_row.structure_hash = ""
    mkt_row.metadata_hash = ""

    session = MagicMock()

    # Patch _fetch_candidates on the service to inject our mock row
    svc = _make_service(session)
    svc._fetch_candidates = MagicMock(return_value=[mkt_row])

    # Patch _fingerprint_from_row to avoid real imports during row building
    from skillmeat.models import ArtifactFingerprint

    def _fp(row):
        return ArtifactFingerprint(
            artifact_path=Path(f"/skill/{row.name}"),
            artifact_name=row.name,
            artifact_type="skill",
            content_hash="",
            metadata_hash="",
            structure_hash="",
            title=getattr(row, "title", None),
            description=getattr(row, "description", None),
            tags=[],
            file_count=0,
            total_size=0,
        )

    svc._fingerprint_from_row = _fp

    # target query
    query_mock = MagicMock()
    filter_mock = MagicMock()
    filter_mock.first.return_value = target
    query_mock.filter.return_value = filter_mock
    session.query.return_value = query_mock

    high_bd = _make_breakdown(keyword=0.8, content=0.8, structure=0.8, metadata=0.8)
    svc._analyzer.compare = MagicMock(return_value=high_bd)

    results = svc.find_similar("uuid-t", source="marketplace", min_score=0.1)

    assert len(results) == 1
    assert results[0].artifact_id == "skill:mkt-skill"


# ---------------------------------------------------------------------------
# SA-P5-001: SimilarityService.get_consolidation_clusters tests
# ---------------------------------------------------------------------------

def _make_duplicate_pair(
    pair_id: str,
    uuid1: str,
    uuid2: str,
    score: float,
    ignored: bool = False,
) -> MagicMock:
    """Return a mock DuplicatePair ORM row."""
    pair = MagicMock()
    pair.id = pair_id
    pair.artifact1_uuid = uuid1
    pair.artifact2_uuid = uuid2
    pair.similarity_score = score
    pair.ignored = ignored
    return pair


def _make_cluster_service(pairs: list, artifact_rows: list | None = None) -> tuple:
    """Build a SimilarityService with a session mocked for cluster tests.

    Returns (svc, session) so callers can assert against session if needed.

    The session mock is wired so:
    - session.query(DuplicatePair).filter(...).all() → pairs
    - session.query(Artifact).filter(...).all() → artifact_rows (default [])
    """
    session = MagicMock()

    if artifact_rows is None:
        artifact_rows = []

    # We need to route query calls to the correct mock depending on the model
    # class passed to session.query().
    from skillmeat.cache.models import DuplicatePair as _DP, Artifact as _Artifact

    class _QueryRouter:
        """Routes .query(Model) calls to appropriate mock data."""

        def __init__(self, pairs_data, artifacts_data):
            self._pairs = pairs_data
            self._artifacts = artifacts_data

        def __call__(self, model):
            if model is _DP:
                q = MagicMock()
                q.filter.return_value = q
                q.all.return_value = self._pairs
                return q
            if model is _Artifact:
                q = MagicMock()
                q.filter.return_value = q
                q.all.return_value = self._artifacts
                return q
            q = MagicMock()
            q.filter.return_value = q
            q.all.return_value = []
            q.first.return_value = None
            return q

    session.query = _QueryRouter(pairs, artifact_rows)

    svc = _make_service(session)
    return svc, session


class TestGetConsolidationClusters:
    """Tests for SimilarityService.get_consolidation_clusters."""

    def test_empty_when_no_pairs(self):
        """Returns empty clusters list when no DuplicatePair rows exist."""
        svc, _ = _make_cluster_service(pairs=[])
        result = svc.get_consolidation_clusters(min_score=0.5)
        assert result["clusters"] == []
        assert result["next_cursor"] is None

    def test_single_pair_forms_single_cluster(self):
        """A single qualifying pair becomes one cluster with two artifacts."""
        pairs = [
            _make_duplicate_pair("p1", "uuid-a", "uuid-b", score=0.8, ignored=False),
        ]
        svc, _ = _make_cluster_service(pairs=pairs)
        result = svc.get_consolidation_clusters(min_score=0.5)

        assert len(result["clusters"]) == 1
        cluster = result["clusters"][0]
        assert set(cluster["artifacts"]) == {"uuid-a", "uuid-b"}
        assert cluster["max_score"] == pytest.approx(0.8)
        assert cluster["pair_count"] == 1
        assert result["next_cursor"] is None

    def test_transitive_pairs_merge_into_single_cluster(self):
        """Pairs (A,B) and (B,C) must be merged into a single cluster {A,B,C}."""
        pairs = [
            _make_duplicate_pair("p1", "uuid-a", "uuid-b", score=0.8),
            _make_duplicate_pair("p2", "uuid-b", "uuid-c", score=0.7),
        ]
        svc, _ = _make_cluster_service(pairs=pairs)
        result = svc.get_consolidation_clusters(min_score=0.5)

        assert len(result["clusters"]) == 1
        cluster = result["clusters"][0]
        assert set(cluster["artifacts"]) == {"uuid-a", "uuid-b", "uuid-c"}
        assert cluster["max_score"] == pytest.approx(0.8)
        assert cluster["pair_count"] == 2

    def test_disjoint_pairs_form_separate_clusters(self):
        """Pairs (A,B) and (C,D) have no shared member → two separate clusters."""
        pairs = [
            _make_duplicate_pair("p1", "uuid-a", "uuid-b", score=0.9),
            _make_duplicate_pair("p2", "uuid-c", "uuid-d", score=0.6),
        ]
        svc, _ = _make_cluster_service(pairs=pairs)
        result = svc.get_consolidation_clusters(min_score=0.5)

        assert len(result["clusters"]) == 2
        # Sorted by max_score descending: first cluster is the 0.9 one.
        assert result["clusters"][0]["max_score"] == pytest.approx(0.9)
        assert result["clusters"][1]["max_score"] == pytest.approx(0.6)

    def test_ignored_pairs_excluded(self):
        """Pairs with ignored=True must not appear in any cluster."""
        pairs = [
            _make_duplicate_pair("p1", "uuid-a", "uuid-b", score=0.8, ignored=True),
            _make_duplicate_pair("p2", "uuid-c", "uuid-d", score=0.7, ignored=False),
        ]
        # The mock for DuplicatePair query returns only non-ignored pairs
        # (the service passes `ignored.is_(False)` filter; our mock just
        # returns whatever we give it, so we simulate by only passing active).
        active_pairs = [p for p in pairs if not p.ignored]
        svc, _ = _make_cluster_service(pairs=active_pairs)
        result = svc.get_consolidation_clusters(min_score=0.5)

        all_uuids = {
            u for c in result["clusters"] for u in c["artifacts"]
        }
        # The ignored pair's uuids must not appear.
        assert "uuid-a" not in all_uuids
        assert "uuid-b" not in all_uuids

    def test_clusters_sorted_by_max_score_descending(self):
        """Clusters must be ordered highest max_score first."""
        pairs = [
            _make_duplicate_pair("p1", "uuid-a", "uuid-b", score=0.6),
            _make_duplicate_pair("p2", "uuid-c", "uuid-d", score=0.95),
            _make_duplicate_pair("p3", "uuid-e", "uuid-f", score=0.75),
        ]
        svc, _ = _make_cluster_service(pairs=pairs)
        result = svc.get_consolidation_clusters(min_score=0.5)

        scores = [c["max_score"] for c in result["clusters"]]
        assert scores == sorted(scores, reverse=True)

    def test_cursor_pagination_first_page(self):
        """First-page response has next_cursor when more clusters exist."""
        pairs = [
            _make_duplicate_pair(f"p{i}", f"uuid-{i}a", f"uuid-{i}b", score=0.9 - i * 0.01)
            for i in range(10)
        ]
        svc, _ = _make_cluster_service(pairs=pairs)
        result = svc.get_consolidation_clusters(min_score=0.5, limit=3)

        assert len(result["clusters"]) == 3
        assert result["next_cursor"] is not None

    def test_cursor_pagination_last_page(self):
        """Last page has next_cursor=None."""
        pairs = [
            _make_duplicate_pair(f"p{i}", f"uuid-{i}a", f"uuid-{i}b", score=0.9 - i * 0.01)
            for i in range(5)
        ]
        svc, _ = _make_cluster_service(pairs=pairs)

        # First page: limit=3
        page1 = svc.get_consolidation_clusters(min_score=0.5, limit=3)
        assert page1["next_cursor"] is not None

        # Second page uses cursor from first page
        page2 = svc.get_consolidation_clusters(
            min_score=0.5, limit=3, cursor=page1["next_cursor"]
        )
        assert len(page2["clusters"]) == 2  # 5 total - 3 on page1
        assert page2["next_cursor"] is None

    def test_cursor_pagination_non_overlapping(self):
        """Pages must not return duplicate clusters."""
        pairs = [
            _make_duplicate_pair(f"p{i}", f"uuid-{i}a", f"uuid-{i}b", score=0.9 - i * 0.01)
            for i in range(6)
        ]
        svc, _ = _make_cluster_service(pairs=pairs)

        page1 = svc.get_consolidation_clusters(min_score=0.5, limit=3)
        page2 = svc.get_consolidation_clusters(
            min_score=0.5, limit=3, cursor=page1["next_cursor"]
        )

        ids1 = {frozenset(c["artifacts"]) for c in page1["clusters"]}
        ids2 = {frozenset(c["artifacts"]) for c in page2["clusters"]}
        assert ids1.isdisjoint(ids2), "Pages must not overlap"

    def test_invalid_cursor_treated_as_first_page(self):
        """An invalid cursor string falls back to offset=0 (first page)."""
        pairs = [
            _make_duplicate_pair("p1", "uuid-a", "uuid-b", score=0.8),
        ]
        svc, _ = _make_cluster_service(pairs=pairs)
        result = svc.get_consolidation_clusters(
            min_score=0.5, limit=10, cursor="not-valid-base64!!!"
        )
        assert len(result["clusters"]) == 1

    def test_artifact_type_resolved_from_db(self):
        """artifact_type on each cluster is resolved via bulk Artifact look-up."""
        pairs = [
            _make_duplicate_pair("p1", "uuid-a", "uuid-b", score=0.8),
        ]

        art_a = MagicMock()
        art_a.uuid = "uuid-a"
        art_a.type = "skill"
        art_b = MagicMock()
        art_b.uuid = "uuid-b"
        art_b.type = "skill"

        svc, _ = _make_cluster_service(pairs=pairs, artifact_rows=[art_a, art_b])
        result = svc.get_consolidation_clusters(min_score=0.5)

        assert result["clusters"][0]["artifact_type"] == "skill"

    def test_artifact_type_empty_when_no_db_rows(self):
        """artifact_type falls back to empty string when artifact rows are missing."""
        pairs = [
            _make_duplicate_pair("p1", "uuid-x", "uuid-y", score=0.7),
        ]
        svc, _ = _make_cluster_service(pairs=pairs, artifact_rows=[])
        result = svc.get_consolidation_clusters(min_score=0.5)

        assert result["clusters"][0]["artifact_type"] == ""

    def test_limit_enforced(self):
        """No more than ``limit`` clusters are returned."""
        pairs = [
            _make_duplicate_pair(f"p{i}", f"uuid-{i}a", f"uuid-{i}b", score=0.8)
            for i in range(15)
        ]
        svc, _ = _make_cluster_service(pairs=pairs)
        result = svc.get_consolidation_clusters(min_score=0.5, limit=7)

        assert len(result["clusters"]) <= 7
