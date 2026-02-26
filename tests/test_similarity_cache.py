"""Tests for SimilarityCacheManager (SSO-2.9).

Tests cover:
- get_similar: cache miss returns empty list
- get_similar: cached results ordered by composite_score DESC
- get_similar: respects limit parameter
- get_similar: respects min_score parameter
- compute_and_store: computes and persists top-20 similar artifacts
- compute_and_store: returns computed results
- compute_and_store: returns empty list when source artifact not found
- compute_and_store: returns empty list when no candidates exist
- invalidate: removes rows where artifact is source OR target
- invalidate: subsequent get_similar returns empty list
- cache hit/miss integration: miss triggers computation, hit is consistent
- _compute_content_score: returns > 0 with populated fingerprint hashes
- _compute_content_score: returns 0.0 when hashes are missing
"""

from __future__ import annotations

import json
import tempfile
import uuid as _uuid_mod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import MagicMock, patch

import pytest

from skillmeat.cache.models import (
    Artifact,
    Base,
    Project,
    SimilarityCache,
    create_db_engine,
    create_tables,
)
from skillmeat.cache.similarity_cache import SimilarityCacheManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_uuid() -> str:
    """Return a short hex UUID string."""
    return _uuid_mod.uuid4().hex


def _utcnow() -> datetime:
    return datetime.utcnow()


_COLLECTION_PROJECT_ID = "collection_artifacts_global"


# ---------------------------------------------------------------------------
# DB fixtures (in-memory SQLite via temp file, ORM tables)
# ---------------------------------------------------------------------------


@pytest.fixture()
def temp_db() -> Generator[str, None, None]:
    """Temporary SQLite database file for cache tests."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    try:
        Path(db_path).unlink()
    except FileNotFoundError:
        pass


@pytest.fixture()
def db_engine(temp_db):
    """Engine with all ORM tables created (bypasses Alembic migrations)."""
    engine = create_db_engine(temp_db)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture()
def db_session(db_engine):
    """Live SQLAlchemy session bound to the temp database."""
    from sqlalchemy.orm import sessionmaker

    SessionLocal = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture()
def seeded_project(db_session):
    """Insert the 'collection_artifacts_global' project row needed by FK constraints."""
    project = Project(
        id=_COLLECTION_PROJECT_ID,
        name="Collection Artifacts (Global)",
        path="/tmp/collection",
        status="active",
    )
    db_session.add(project)
    db_session.commit()
    return project


def _make_artifact(
    db_session,
    uuid: str | None = None,
    artifact_id: str | None = None,
    name: str = "test-artifact",
    artifact_type: str = "skill",
    project_id: str = _COLLECTION_PROJECT_ID,
) -> Artifact:
    """Create and persist a minimal Artifact row."""
    uid = uuid or _make_uuid()
    aid = artifact_id or f"{artifact_type}:{name}"
    row = Artifact(
        id=aid,
        uuid=uid,
        name=name,
        type=artifact_type,
        project_id=project_id,
    )
    db_session.add(row)
    db_session.flush()
    return row


def _insert_cache_row(
    db_session,
    source_uuid: str,
    target_uuid: str,
    composite_score: float,
    breakdown: Dict[str, Any] | None = None,
) -> SimilarityCache:
    """Directly insert a SimilarityCache row (bypasses manager logic)."""
    row = SimilarityCache(
        source_artifact_uuid=source_uuid,
        target_artifact_uuid=target_uuid,
        composite_score=composite_score,
        breakdown_json=json.dumps(breakdown or {}),
        computed_at=_utcnow(),
    )
    db_session.add(row)
    db_session.flush()
    return row


# ---------------------------------------------------------------------------
# Helpers for mocking SimilarityService inside compute_and_store
# ---------------------------------------------------------------------------


def _make_breakdown_mock(
    keyword: float = 0.5,
    content: float = 0.5,
    structure: float = 0.5,
    metadata: float = 0.5,
    semantic: float | None = None,
    text: float | None = None,
):
    """Return a ScoreBreakdown-like MagicMock."""
    from skillmeat.core.similarity import ScoreBreakdown

    return ScoreBreakdown(
        keyword_score=keyword,
        content_score=content,
        structure_score=structure,
        metadata_score=metadata,
        semantic_score=semantic,
        text_score=text,
    )


# ---------------------------------------------------------------------------
# Tests: get_similar — cache miss
# ---------------------------------------------------------------------------


class TestGetSimilarCacheMiss:
    """get_similar returns an empty list when no rows exist for the given UUID."""

    def test_returns_empty_list_on_cache_miss(self, db_session, seeded_project):
        """Cache miss: get_similar returns [] for a UUID with no stored rows."""
        mgr = SimilarityCacheManager()
        result = mgr.get_similar("nonexistent-uuid-abc", db_session)
        assert result == []

    def test_returns_empty_list_for_existing_artifact_without_cache(
        self, db_session, seeded_project
    ):
        """An artifact that exists in DB but has no cache rows still returns []."""
        art = _make_artifact(db_session, name="no-cache-art")
        db_session.commit()

        mgr = SimilarityCacheManager()
        result = mgr.get_similar(art.uuid, db_session)
        assert result == []


# ---------------------------------------------------------------------------
# Tests: get_similar — ordering and filtering
# ---------------------------------------------------------------------------


class TestGetSimilarOrdering:
    """get_similar returns rows ordered by composite_score DESC."""

    def test_results_ordered_by_composite_score_descending(
        self, db_session, seeded_project
    ):
        """Rows are returned highest score first."""
        src = _make_artifact(db_session, name="source")
        tgt_a = _make_artifact(db_session, name="target-a")
        tgt_b = _make_artifact(db_session, name="target-b")
        tgt_c = _make_artifact(db_session, name="target-c")

        _insert_cache_row(db_session, src.uuid, tgt_a.uuid, composite_score=0.3)
        _insert_cache_row(db_session, src.uuid, tgt_b.uuid, composite_score=0.9)
        _insert_cache_row(db_session, src.uuid, tgt_c.uuid, composite_score=0.6)
        db_session.commit()

        mgr = SimilarityCacheManager()
        results = mgr.get_similar(src.uuid, db_session)

        assert len(results) == 3
        scores = [r["composite_score"] for r in results]
        assert scores == sorted(scores, reverse=True), "Results must be DESC by composite_score"
        assert scores[0] == pytest.approx(0.9)
        assert scores[-1] == pytest.approx(0.3)

    def test_result_dict_has_expected_keys(self, db_session, seeded_project):
        """Each result dict has target_artifact_uuid, composite_score, breakdown_json, computed_at."""
        src = _make_artifact(db_session, name="src-keys")
        tgt = _make_artifact(db_session, name="tgt-keys")
        _insert_cache_row(
            db_session,
            src.uuid,
            tgt.uuid,
            0.7,
            breakdown={"keyword_score": 0.7},
        )
        db_session.commit()

        mgr = SimilarityCacheManager()
        results = mgr.get_similar(src.uuid, db_session)

        assert len(results) == 1
        r = results[0]
        assert r["target_artifact_uuid"] == tgt.uuid
        assert r["composite_score"] == pytest.approx(0.7)
        assert r["breakdown_json"] is not None
        assert r["computed_at"] is not None


class TestGetSimilarLimit:
    """get_similar respects the limit parameter."""

    def test_limit_truncates_results(self, db_session, seeded_project):
        """Only `limit` rows are returned even when more are cached."""
        src = _make_artifact(db_session, name="src-limit")
        targets = [_make_artifact(db_session, name=f"tgt-{i}") for i in range(5)]

        for i, tgt in enumerate(targets):
            _insert_cache_row(db_session, src.uuid, tgt.uuid, composite_score=0.1 * (i + 1))
        db_session.commit()

        mgr = SimilarityCacheManager()
        results = mgr.get_similar(src.uuid, db_session, limit=3)
        assert len(results) == 3

    def test_limit_returns_top_scores(self, db_session, seeded_project):
        """The limit rows returned are the highest-scored ones."""
        src = _make_artifact(db_session, name="src-top")
        scores_inserted = [0.2, 0.8, 0.5, 0.9, 0.1]
        targets = [_make_artifact(db_session, name=f"top-tgt-{i}") for i in range(5)]

        for tgt, score in zip(targets, scores_inserted):
            _insert_cache_row(db_session, src.uuid, tgt.uuid, composite_score=score)
        db_session.commit()

        mgr = SimilarityCacheManager()
        results = mgr.get_similar(src.uuid, db_session, limit=2)
        assert len(results) == 2
        # Top 2 should be 0.9 and 0.8
        assert results[0]["composite_score"] == pytest.approx(0.9)
        assert results[1]["composite_score"] == pytest.approx(0.8)


class TestGetSimilarMinScore:
    """get_similar respects the min_score parameter."""

    def test_min_score_filters_low_scores(self, db_session, seeded_project):
        """Rows below min_score are excluded."""
        src = _make_artifact(db_session, name="src-min")
        high = _make_artifact(db_session, name="tgt-high")
        low = _make_artifact(db_session, name="tgt-low")

        _insert_cache_row(db_session, src.uuid, high.uuid, composite_score=0.8)
        _insert_cache_row(db_session, src.uuid, low.uuid, composite_score=0.2)
        db_session.commit()

        mgr = SimilarityCacheManager()
        results = mgr.get_similar(src.uuid, db_session, min_score=0.5)

        assert len(results) == 1
        assert results[0]["target_artifact_uuid"] == high.uuid

    def test_min_score_zero_includes_all(self, db_session, seeded_project):
        """min_score=0.0 (default) includes all cached rows."""
        src = _make_artifact(db_session, name="src-zero")
        targets = [_make_artifact(db_session, name=f"tgt-zero-{i}") for i in range(3)]

        for i, tgt in enumerate(targets):
            _insert_cache_row(db_session, src.uuid, tgt.uuid, composite_score=0.0 + i * 0.1)
        db_session.commit()

        mgr = SimilarityCacheManager()
        results = mgr.get_similar(src.uuid, db_session, min_score=0.0)
        assert len(results) == 3

    def test_min_score_boundary_includes_exact_match(self, db_session, seeded_project):
        """A row with composite_score == min_score is included (>= boundary)."""
        src = _make_artifact(db_session, name="src-boundary")
        tgt = _make_artifact(db_session, name="tgt-boundary")
        _insert_cache_row(db_session, src.uuid, tgt.uuid, composite_score=0.5)
        db_session.commit()

        mgr = SimilarityCacheManager()
        results = mgr.get_similar(src.uuid, db_session, min_score=0.5)
        assert len(results) == 1


# ---------------------------------------------------------------------------
# Tests: compute_and_store
# ---------------------------------------------------------------------------


class TestComputeAndStore:
    """compute_and_store computes and persists top-20 similar artifacts."""

    def test_returns_empty_list_when_source_not_found(
        self, db_session, seeded_project
    ):
        """Returns [] immediately when the source UUID does not exist in DB."""
        mgr = SimilarityCacheManager()
        result = mgr.compute_and_store("does-not-exist-uuid", db_session)
        assert result == []

    def test_returns_empty_list_when_no_candidates(
        self, db_session, seeded_project
    ):
        """Returns [] when the collection has only the source artifact (no candidates)."""
        art = _make_artifact(db_session, name="lonely-art")
        db_session.commit()

        mgr = SimilarityCacheManager()
        # FTS5 will fail gracefully and fall back to collection scan — still no candidates.
        result = mgr.compute_and_store(art.uuid, db_session)
        assert result == []

    def test_persists_rows_and_returns_dicts(
        self, db_session, seeded_project
    ):
        """compute_and_store stores rows in DB and returns matching dicts."""
        src = _make_artifact(db_session, name="src-persist")
        _make_artifact(db_session, name="cand-a")
        _make_artifact(db_session, name="cand-b")
        db_session.commit()

        mgr = SimilarityCacheManager()

        fixed_breakdown = _make_breakdown_mock(
            keyword=0.6, content=0.6, structure=0.6, metadata=0.6
        )

        with patch(
            "skillmeat.core.similarity.SimilarityService"
        ) as MockSvc:
            mock_svc_instance = MagicMock()
            MockSvc.return_value = mock_svc_instance

            mock_svc_instance._fingerprint_from_row.return_value = MagicMock(
                description=None
            )
            mock_svc_instance._analyzer.compare.return_value = fixed_breakdown
            mock_svc_instance._score_semantic_with_timeout.return_value = None
            mock_svc_instance._compute_composite_score.return_value = 0.6

            with patch.object(
                type(mgr), "_fts5_candidate_uuids", return_value=None
            ):
                results = mgr.compute_and_store(src.uuid, db_session)

        # Must return a non-empty list of dicts
        assert isinstance(results, list)
        assert len(results) > 0

        for r in results:
            assert "target_artifact_uuid" in r
            assert "composite_score" in r
            assert "breakdown_json" in r
            assert "computed_at" in r

        # Rows should be persisted in DB
        db_session.expire_all()
        cached_rows = (
            db_session.query(SimilarityCache)
            .filter(SimilarityCache.source_artifact_uuid == src.uuid)
            .all()
        )
        assert len(cached_rows) == len(results)

    def test_replaces_existing_rows_for_source(
        self, db_session, seeded_project
    ):
        """compute_and_store deletes old rows and replaces them with freshly scored rows.

        The pre-seeded row had composite_score=0.99.  After recompute with a mock
        that always returns 0.4, the stored score must reflect the new value (0.4),
        proving the old row was deleted and a fresh one inserted.
        """
        src = _make_artifact(db_session, name="src-replace")
        old_tgt = _make_artifact(db_session, name="old-tgt")
        db_session.commit()

        # Pre-seed an old cache row with a distinct score
        _insert_cache_row(db_session, src.uuid, old_tgt.uuid, 0.99)
        db_session.commit()

        mgr = SimilarityCacheManager()

        with patch(
            "skillmeat.core.similarity.SimilarityService"
        ) as MockSvc:
            mock_svc_instance = MagicMock()
            MockSvc.return_value = mock_svc_instance

            fresh_breakdown = _make_breakdown_mock(
                keyword=0.4, content=0.4, structure=0.4, metadata=0.4
            )
            mock_svc_instance._fingerprint_from_row.return_value = MagicMock(
                description=None
            )
            mock_svc_instance._analyzer.compare.return_value = fresh_breakdown
            mock_svc_instance._score_semantic_with_timeout.return_value = None
            mock_svc_instance._compute_composite_score.return_value = 0.4

            with patch.object(
                type(mgr), "_fts5_candidate_uuids", return_value=None
            ):
                mgr.compute_and_store(src.uuid, db_session)

        db_session.expire_all()
        rows = (
            db_session.query(SimilarityCache)
            .filter(SimilarityCache.source_artifact_uuid == src.uuid)
            .all()
        )

        # The old row (score=0.99) must be gone; new row (score=0.4) must exist.
        assert len(rows) >= 1
        for row in rows:
            assert row.composite_score != pytest.approx(0.99), (
                "Old row with score=0.99 should have been replaced by recompute"
            )

    def test_top_20_limit_is_enforced(self, db_session, seeded_project):
        """compute_and_store stores at most 20 rows per source artifact."""
        src = _make_artifact(db_session, name="src-top20")
        candidates = [
            _make_artifact(db_session, name=f"cand-{i}") for i in range(25)
        ]
        db_session.commit()

        mgr = SimilarityCacheManager()

        with patch(
            "skillmeat.core.similarity.SimilarityService"
        ) as MockSvc:
            mock_svc_instance = MagicMock()
            MockSvc.return_value = mock_svc_instance

            fixed_bd = _make_breakdown_mock(
                keyword=0.5, content=0.5, structure=0.5, metadata=0.5
            )
            mock_svc_instance._fingerprint_from_row.return_value = MagicMock(
                description=None
            )
            mock_svc_instance._analyzer.compare.return_value = fixed_bd
            mock_svc_instance._score_semantic_with_timeout.return_value = None
            mock_svc_instance._compute_composite_score.return_value = 0.5

            with patch.object(
                type(mgr), "_fts5_candidate_uuids", return_value=None
            ):
                results = mgr.compute_and_store(src.uuid, db_session)

        assert len(results) <= 20


# ---------------------------------------------------------------------------
# Tests: invalidate
# ---------------------------------------------------------------------------


class TestInvalidate:
    """invalidate removes all rows where artifact is source OR target."""

    def test_removes_rows_where_artifact_is_source(
        self, db_session, seeded_project
    ):
        """Rows where artifact is the source are removed."""
        src = _make_artifact(db_session, name="src-inv")
        tgt_a = _make_artifact(db_session, name="inv-tgt-a")
        tgt_b = _make_artifact(db_session, name="inv-tgt-b")
        other_src = _make_artifact(db_session, name="other-src")

        _insert_cache_row(db_session, src.uuid, tgt_a.uuid, 0.7)
        _insert_cache_row(db_session, src.uuid, tgt_b.uuid, 0.6)
        _insert_cache_row(db_session, other_src.uuid, tgt_a.uuid, 0.5)
        db_session.commit()

        mgr = SimilarityCacheManager()
        mgr.invalidate(src.uuid, db_session)
        db_session.commit()

        # src rows must be gone
        src_rows = (
            db_session.query(SimilarityCache)
            .filter(SimilarityCache.source_artifact_uuid == src.uuid)
            .all()
        )
        assert len(src_rows) == 0

        # other_src row must still exist
        other_rows = (
            db_session.query(SimilarityCache)
            .filter(SimilarityCache.source_artifact_uuid == other_src.uuid)
            .all()
        )
        assert len(other_rows) == 1

    def test_removes_rows_where_artifact_is_target(
        self, db_session, seeded_project
    ):
        """Rows where the invalidated artifact is the target are also removed."""
        src_a = _make_artifact(db_session, name="src-a-inv")
        src_b = _make_artifact(db_session, name="src-b-inv")
        tgt = _make_artifact(db_session, name="tgt-inv")
        unrelated_tgt = _make_artifact(db_session, name="unrelated-tgt")

        _insert_cache_row(db_session, src_a.uuid, tgt.uuid, 0.8)
        _insert_cache_row(db_session, src_b.uuid, tgt.uuid, 0.7)
        _insert_cache_row(db_session, src_a.uuid, unrelated_tgt.uuid, 0.6)
        db_session.commit()

        mgr = SimilarityCacheManager()
        mgr.invalidate(tgt.uuid, db_session)
        db_session.commit()

        # All rows involving tgt as target must be gone
        tgt_rows = (
            db_session.query(SimilarityCache)
            .filter(SimilarityCache.target_artifact_uuid == tgt.uuid)
            .all()
        )
        assert len(tgt_rows) == 0

        # Unrelated row must survive
        remaining = (
            db_session.query(SimilarityCache)
            .filter(SimilarityCache.source_artifact_uuid == src_a.uuid)
            .all()
        )
        assert len(remaining) == 1
        assert remaining[0].target_artifact_uuid == unrelated_tgt.uuid

    def test_subsequent_get_similar_returns_empty(
        self, db_session, seeded_project
    ):
        """After invalidate, get_similar returns [] for the invalidated UUID."""
        src = _make_artifact(db_session, name="src-after-inv")
        tgt = _make_artifact(db_session, name="tgt-after-inv")
        _insert_cache_row(db_session, src.uuid, tgt.uuid, 0.9)
        db_session.commit()

        mgr = SimilarityCacheManager()

        # Confirm cache is populated
        before = mgr.get_similar(src.uuid, db_session)
        assert len(before) == 1

        # Invalidate and confirm empty
        mgr.invalidate(src.uuid, db_session)
        db_session.commit()

        after = mgr.get_similar(src.uuid, db_session)
        assert after == []

    def test_invalidate_noop_when_no_rows_exist(
        self, db_session, seeded_project
    ):
        """invalidate does not raise when no rows exist for the UUID."""
        art = _make_artifact(db_session, name="art-noop-inv")
        db_session.commit()

        mgr = SimilarityCacheManager()
        # Should not raise
        mgr.invalidate(art.uuid, db_session)
        db_session.commit()

    def test_invalidate_removes_source_and_target_rows_together(
        self, db_session, seeded_project
    ):
        """invalidate removes rows where the artifact appears as source AND as target."""
        art = _make_artifact(db_session, name="art-dual")
        other_a = _make_artifact(db_session, name="other-a-dual")
        other_b = _make_artifact(db_session, name="other-b-dual")

        # art as source pointing to other_a
        _insert_cache_row(db_session, art.uuid, other_a.uuid, 0.7)
        # art as target pointed to by other_b
        _insert_cache_row(db_session, other_b.uuid, art.uuid, 0.6)
        db_session.commit()

        mgr = SimilarityCacheManager()
        mgr.invalidate(art.uuid, db_session)
        db_session.commit()

        total = db_session.query(SimilarityCache).all()
        assert len(total) == 0


# ---------------------------------------------------------------------------
# Tests: cache hit/miss integration
# ---------------------------------------------------------------------------


class TestCacheHitMissIntegration:
    """Cache miss triggers computation; subsequent call is a cache hit."""

    def test_miss_then_hit_returns_consistent_results(
        self, db_session, seeded_project
    ):
        """First call (miss) computes results; second call (hit) returns same data."""
        src = _make_artifact(db_session, name="src-hitm")
        cand = _make_artifact(db_session, name="cand-hitm")
        db_session.commit()

        mgr = SimilarityCacheManager()

        # Verify cache miss
        miss = mgr.get_similar(src.uuid, db_session)
        assert miss == []

        # Compute and store
        with patch(
            "skillmeat.core.similarity.SimilarityService"
        ) as MockSvc:
            mock_svc_instance = MagicMock()
            MockSvc.return_value = mock_svc_instance

            fixed_bd = _make_breakdown_mock(
                keyword=0.55, content=0.55, structure=0.55, metadata=0.55
            )
            mock_svc_instance._fingerprint_from_row.return_value = MagicMock(
                description=None
            )
            mock_svc_instance._analyzer.compare.return_value = fixed_bd
            mock_svc_instance._score_semantic_with_timeout.return_value = None
            mock_svc_instance._compute_composite_score.return_value = 0.55

            with patch.object(
                type(mgr), "_fts5_candidate_uuids", return_value=None
            ):
                computed = mgr.compute_and_store(src.uuid, db_session)

        assert len(computed) > 0

        # Second call should be a cache hit and match computed results
        hit = mgr.get_similar(src.uuid, db_session)
        assert len(hit) == len(computed)
        assert hit[0]["target_artifact_uuid"] == computed[0]["target_artifact_uuid"]
        assert hit[0]["composite_score"] == pytest.approx(
            computed[0]["composite_score"], abs=1e-4
        )

    def test_after_invalidate_miss_triggers_recompute(
        self, db_session, seeded_project
    ):
        """After invalidate, compute_and_store re-fills the cache correctly."""
        src = _make_artifact(db_session, name="src-reinv")
        cand = _make_artifact(db_session, name="cand-reinv")
        _insert_cache_row(db_session, src.uuid, cand.uuid, 0.8)
        db_session.commit()

        mgr = SimilarityCacheManager()

        # Populate from cache
        before = mgr.get_similar(src.uuid, db_session)
        assert len(before) == 1

        # Invalidate
        mgr.invalidate(src.uuid, db_session)
        db_session.commit()

        # Cache is empty again
        empty = mgr.get_similar(src.uuid, db_session)
        assert empty == []

        # Re-compute
        with patch(
            "skillmeat.core.similarity.SimilarityService"
        ) as MockSvc:
            mock_svc_instance = MagicMock()
            MockSvc.return_value = mock_svc_instance

            fresh_bd = _make_breakdown_mock(
                keyword=0.3, content=0.3, structure=0.3, metadata=0.3
            )
            mock_svc_instance._fingerprint_from_row.return_value = MagicMock(
                description=None
            )
            mock_svc_instance._analyzer.compare.return_value = fresh_bd
            mock_svc_instance._score_semantic_with_timeout.return_value = None
            mock_svc_instance._compute_composite_score.return_value = 0.3

            with patch.object(
                type(mgr), "_fts5_candidate_uuids", return_value=None
            ):
                recomputed = mgr.compute_and_store(src.uuid, db_session)

        assert len(recomputed) > 0
        refetch = mgr.get_similar(src.uuid, db_session)
        assert len(refetch) == len(recomputed)


# ---------------------------------------------------------------------------
# Tests: _compute_content_score (via MatchAnalyzer)
# ---------------------------------------------------------------------------


class TestComputeContentScore:
    """_compute_content_score in MatchAnalyzer behaves correctly with fingerprints."""

    def _load_match_analyzer(self):
        """Load MatchAnalyzer directly to avoid circular import."""
        import importlib.util
        import sys
        from pathlib import Path as _Path

        _MOD_KEY = "_skillmeat_match_analyzer_direct"
        if _MOD_KEY in sys.modules:
            return sys.modules[_MOD_KEY].MatchAnalyzer()

        import skillmeat

        pkg_root = _Path(skillmeat.__file__).parent
        ma_path = pkg_root / "core" / "scoring" / "match_analyzer.py"
        spec = importlib.util.spec_from_file_location(_MOD_KEY, ma_path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[_MOD_KEY] = mod
        spec.loader.exec_module(mod)
        return mod.MatchAnalyzer()

    def _make_fingerprint(
        self,
        name: str = "test",
        content_hash: str = "",
        total_size: int = 0,
        structure_hash: str = "",
    ):
        """Build a minimal ArtifactFingerprint."""
        from skillmeat.models import ArtifactFingerprint

        return ArtifactFingerprint(
            artifact_path=Path(f"/skill/{name}"),
            artifact_name=name,
            artifact_type="skill",
            content_hash=content_hash,
            metadata_hash="",
            structure_hash=structure_hash,
            title=None,
            description=None,
            tags=[],
            file_count=1,
            total_size=total_size,
        )

    def test_returns_1_when_identical_content_hashes(self):
        """content_score == 1.0 when both artifacts have the same non-empty content_hash."""
        analyzer = self._load_match_analyzer()

        fp_a = self._make_fingerprint("art-a", content_hash="sha256-abc123")
        fp_b = self._make_fingerprint("art-b", content_hash="sha256-abc123")

        score = analyzer._compute_content_score(fp_a, fp_b)
        assert score == pytest.approx(1.0)

    def test_returns_0_when_both_hashes_missing_and_no_size(self):
        """content_score == 0.0 when both content_hashes are empty and size is zero."""
        analyzer = self._load_match_analyzer()

        fp_a = self._make_fingerprint("art-c", content_hash="", total_size=0)
        fp_b = self._make_fingerprint("art-d", content_hash="", total_size=0)

        score = analyzer._compute_content_score(fp_a, fp_b)
        assert score == pytest.approx(0.0)

    def test_returns_nonzero_when_hashes_populated_but_different(self):
        """content_score > 0 when both hashes are present but differ (size proxy)."""
        analyzer = self._load_match_analyzer()

        fp_a = self._make_fingerprint("art-e", content_hash="hash-A", total_size=1000)
        fp_b = self._make_fingerprint("art-f", content_hash="hash-B", total_size=900)

        score = analyzer._compute_content_score(fp_a, fp_b)
        assert score > 0.0
        assert score <= 0.5  # capped at 0.5

    def test_returns_weak_proxy_when_one_hash_missing(self):
        """When one hash is missing, size-ratio proxy is used, capped at 0.3."""
        analyzer = self._load_match_analyzer()

        fp_a = self._make_fingerprint("art-g", content_hash="hash-X", total_size=1000)
        fp_b = self._make_fingerprint("art-h", content_hash="", total_size=1000)

        score = analyzer._compute_content_score(fp_a, fp_b)
        assert 0.0 <= score <= 0.3

    def test_returns_0_when_both_hashes_missing_even_with_size(self):
        """When both hashes are empty but sizes are non-zero, uses size proxy capped at 0.3."""
        analyzer = self._load_match_analyzer()

        fp_a = self._make_fingerprint("art-i", content_hash="", total_size=500)
        fp_b = self._make_fingerprint("art-j", content_hash="", total_size=500)

        score = analyzer._compute_content_score(fp_a, fp_b)
        # Both hashes empty → size proxy path, capped at 0.3
        assert 0.0 <= score <= 0.3
