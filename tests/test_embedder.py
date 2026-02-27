"""Tests for Phase 3 embedding providers and cache embedding integration (SSO-3.6).

Covers:
- SentenceTransformerEmbedder: availability, lazy loading, embedding output
- AnthropicEmbedder: always-unavailable stub behaviour
- SimilarityCacheManager: _get_or_compute_embedding (cache hit/miss),
  _cosine_similarity helpers, and composite score computation with/without
  embeddings available

All tests pass WITHOUT sentence_transformers installed — imports are mocked
throughout using unittest.mock.patch.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Circular-import guard (same pattern as test_text_similarity.py)
# ---------------------------------------------------------------------------
# skillmeat.core.scoring.__init__ pulls in quality_scorer → rating_store →
# cache.models → cache.marketplace → api.__init__ which completes the cycle.
# Pre-stubbing these modules before any skillmeat import avoids the circular
# ImportError without touching production code.
import sys
from unittest.mock import MagicMock as _MagicMock

for _mod in (
    "skillmeat.storage.rating_store",
    "skillmeat.cache.marketplace",
):
    if _mod not in sys.modules:
        sys.modules[_mod] = _MagicMock()

import asyncio
import json
import tempfile
import uuid as _uuid_mod
from datetime import datetime
from pathlib import Path
from typing import Generator, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_uuid() -> str:
    """Return a short hex UUID string."""
    return _uuid_mod.uuid4().hex


_COLLECTION_PROJECT_ID = "collection_artifacts_global"


# ---------------------------------------------------------------------------
# SentenceTransformerEmbedder tests
# ---------------------------------------------------------------------------


class TestSentenceTransformerEmbedderAvailability:
    """is_available() reflects whether sentence_transformers is importable."""

    def setup_method(self):
        """Reset the module-level cache before each test."""
        import skillmeat.core.scoring.embedder as _emb_mod

        _emb_mod._sentence_transformers_available = None

    def test_is_available_when_installed(self):
        """is_available() returns True when sentence_transformers can be imported."""
        import skillmeat.core.scoring.embedder as _emb_mod

        fake_st = _MagicMock()
        with patch.dict(sys.modules, {"sentence_transformers": fake_st}):
            # Force re-evaluation by resetting the cache flag.
            _emb_mod._sentence_transformers_available = None
            from skillmeat.core.scoring.embedder import SentenceTransformerEmbedder

            embedder = SentenceTransformerEmbedder()
            assert embedder.is_available() is True

    def test_is_available_when_not_installed(self):
        """is_available() returns False when sentence_transformers raises ImportError."""
        import skillmeat.core.scoring.embedder as _emb_mod

        _emb_mod._sentence_transformers_available = None

        # Remove the package from sys.modules so the import inside the check fails.
        with patch.dict(sys.modules, {"sentence_transformers": None}):
            _emb_mod._sentence_transformers_available = None
            from skillmeat.core.scoring.embedder import SentenceTransformerEmbedder

            embedder = SentenceTransformerEmbedder()
            assert embedder.is_available() is False


class TestSentenceTransformerEmbedderGetEmbedding:
    """get_embedding() behaviour under various conditions."""

    def setup_method(self):
        """Reset the module-level availability cache before each test."""
        import skillmeat.core.scoring.embedder as _emb_mod

        _emb_mod._sentence_transformers_available = None

    def test_get_embedding_returns_none_when_unavailable(self):
        """When sentence_transformers is not installed, get_embedding() returns None."""
        import skillmeat.core.scoring.embedder as _emb_mod

        _emb_mod._sentence_transformers_available = False

        from skillmeat.core.scoring.embedder import SentenceTransformerEmbedder

        embedder = SentenceTransformerEmbedder()
        result = asyncio.run(embedder.get_embedding("some text"))
        assert result is None

    def test_get_embedding_empty_text_returns_none(self):
        """Empty string returns None regardless of availability."""
        import skillmeat.core.scoring.embedder as _emb_mod

        # Even with availability True, empty text short-circuits to None.
        _emb_mod._sentence_transformers_available = True

        fake_st = _MagicMock()
        with patch.dict(sys.modules, {"sentence_transformers": fake_st}):
            from skillmeat.core.scoring.embedder import SentenceTransformerEmbedder

            embedder = SentenceTransformerEmbedder()
            result = asyncio.run(embedder.get_embedding(""))
        assert result is None

    def test_get_embedding_whitespace_only_returns_none(self):
        """Whitespace-only string returns None (treated as empty)."""
        import skillmeat.core.scoring.embedder as _emb_mod

        _emb_mod._sentence_transformers_available = True

        fake_st = _MagicMock()
        with patch.dict(sys.modules, {"sentence_transformers": fake_st}):
            from skillmeat.core.scoring.embedder import SentenceTransformerEmbedder

            embedder = SentenceTransformerEmbedder()
            result = asyncio.run(embedder.get_embedding("   \t\n"))
        assert result is None

    def test_get_embedding_returns_vector_of_floats(self):
        """With a mocked model, get_embedding() returns a list of floats."""
        import numpy as np

        import skillmeat.core.scoring.embedder as _emb_mod

        _emb_mod._sentence_transformers_available = True

        # Build a fake 384-element numpy array the model would return.
        fake_vector = np.ones(384, dtype=np.float32)

        fake_model = MagicMock()
        fake_model.encode.return_value = fake_vector

        fake_st_module = MagicMock()
        fake_st_module.SentenceTransformer.return_value = fake_model

        with patch.dict(sys.modules, {"sentence_transformers": fake_st_module}):
            _emb_mod._sentence_transformers_available = True
            from skillmeat.core.scoring.embedder import SentenceTransformerEmbedder

            embedder = SentenceTransformerEmbedder()
            # Inject the mock model directly to bypass lazy load.
            embedder._model = fake_model

            result = asyncio.run(embedder.get_embedding("process PDF files"))

        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 384
        assert all(isinstance(v, float) for v in result)

    def test_get_embedding_dimension(self):
        """get_embedding_dimension() returns 384."""
        from skillmeat.core.scoring.embedder import SentenceTransformerEmbedder

        embedder = SentenceTransformerEmbedder()
        assert embedder.get_embedding_dimension() == 384

    def test_lazy_model_loading_not_at_init(self):
        """The model is NOT loaded during __init__; _model remains None until first call."""
        from skillmeat.core.scoring.embedder import SentenceTransformerEmbedder

        embedder = SentenceTransformerEmbedder()
        # Model must be None immediately after construction.
        assert embedder._model is None

    def test_lazy_model_loading_on_first_get_embedding(self):
        """_load_model() is called only on the first get_embedding() invocation."""
        import numpy as np

        import skillmeat.core.scoring.embedder as _emb_mod

        _emb_mod._sentence_transformers_available = True

        fake_vector = np.zeros(384, dtype=np.float32)
        fake_model = MagicMock()
        fake_model.encode.return_value = fake_vector

        fake_st_module = MagicMock()
        fake_st_module.SentenceTransformer.return_value = fake_model

        with patch.dict(sys.modules, {"sentence_transformers": fake_st_module}):
            _emb_mod._sentence_transformers_available = True
            from skillmeat.core.scoring.embedder import SentenceTransformerEmbedder

            embedder = SentenceTransformerEmbedder()
            assert embedder._model is None  # Not loaded yet

            asyncio.run(embedder.get_embedding("hello"))

            # After first call the model should now be set.
            assert embedder._model is not None
            fake_st_module.SentenceTransformer.assert_called_once_with(
                SentenceTransformerEmbedder.MODEL_NAME
            )


# ---------------------------------------------------------------------------
# AnthropicEmbedder tests
# ---------------------------------------------------------------------------


class TestAnthropicEmbedder:
    """AnthropicEmbedder is always unavailable (stub behaviour)."""

    @pytest.fixture()
    def tmp_cache_db(self, tmp_path: Path) -> Path:
        """Provide an isolated SQLite path so tests don't pollute ~/.skillmeat."""
        return tmp_path / "test_embeddings.db"

    def test_anthropic_embedder_is_never_available(self, tmp_cache_db):
        """is_available() always returns False — Anthropic has no embedding API."""
        from skillmeat.core.scoring.haiku_embedder import AnthropicEmbedder

        embedder = AnthropicEmbedder(cache_db=tmp_cache_db)
        assert embedder.is_available() is False

    def test_anthropic_embedder_get_embedding_returns_none(self, tmp_cache_db):
        """get_embedding() returns None for any non-empty text."""
        from skillmeat.core.scoring.haiku_embedder import AnthropicEmbedder

        embedder = AnthropicEmbedder(cache_db=tmp_cache_db)
        result = asyncio.run(embedder.get_embedding("classify images and text"))
        assert result is None

    def test_anthropic_embedder_get_embedding_returns_none_for_empty(
        self, tmp_cache_db
    ):
        """get_embedding() returns None for empty text (as with all providers)."""
        from skillmeat.core.scoring.haiku_embedder import AnthropicEmbedder

        embedder = AnthropicEmbedder(cache_db=tmp_cache_db)
        result = asyncio.run(embedder.get_embedding(""))
        assert result is None

    def test_anthropic_embedder_dimension_placeholder(self, tmp_cache_db):
        """get_embedding_dimension() returns the documented placeholder (768)."""
        from skillmeat.core.scoring.haiku_embedder import AnthropicEmbedder

        embedder = AnthropicEmbedder(cache_db=tmp_cache_db)
        assert embedder.get_embedding_dimension() == 768

    def test_haiku_embedder_alias_still_works(self, tmp_cache_db):
        """HaikuEmbedder backward-compat alias resolves to AnthropicEmbedder."""
        from skillmeat.core.scoring.haiku_embedder import AnthropicEmbedder, HaikuEmbedder

        embedder = HaikuEmbedder(cache_db=tmp_cache_db)
        assert isinstance(embedder, AnthropicEmbedder)
        assert embedder.is_available() is False


# ---------------------------------------------------------------------------
# _cosine_similarity unit tests (pure math, no DB)
# ---------------------------------------------------------------------------


class TestCosineSimilarity:
    """SimilarityCacheManager._cosine_similarity edge cases."""

    def _csim(self, a: List[float], b: List[float]) -> float:
        from skillmeat.cache.similarity_cache import SimilarityCacheManager

        return SimilarityCacheManager._cosine_similarity(a, b)

    def test_identical_vectors_return_one(self):
        """Cosine similarity of a vector with itself is 1.0."""
        v = [1.0, 0.5, 0.2, 0.8]
        assert self._csim(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors_return_zero(self):
        """Orthogonal vectors have cosine similarity 0.0."""
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert self._csim(a, b) == pytest.approx(0.0)

    def test_zero_vector_a_returns_zero(self):
        """Zero vector (all zeros) in position a yields 0.0."""
        assert self._csim([0.0, 0.0, 0.0], [1.0, 0.5, 0.2]) == pytest.approx(0.0)

    def test_zero_vector_b_returns_zero(self):
        """Zero vector in position b yields 0.0."""
        assert self._csim([1.0, 0.5, 0.2], [0.0, 0.0, 0.0]) == pytest.approx(0.0)

    def test_both_zero_vectors_return_zero(self):
        """Two zero vectors yield 0.0 (not NaN)."""
        assert self._csim([0.0, 0.0], [0.0, 0.0]) == pytest.approx(0.0)

    def test_mismatched_length_returns_zero(self):
        """Vectors of different length return 0.0."""
        assert self._csim([1.0, 0.0], [1.0, 0.0, 0.0]) == pytest.approx(0.0)

    def test_empty_vectors_return_zero(self):
        """Empty vectors return 0.0."""
        assert self._csim([], []) == pytest.approx(0.0)

    def test_antiparallel_vectors_clamped_to_zero(self):
        """Antiparallel vectors (cosine = -1) are clamped to 0.0."""
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        result = self._csim(a, b)
        assert result == pytest.approx(0.0)

    def test_result_is_in_unit_range(self):
        """Result is always in [0.0, 1.0]."""
        import random

        rng = random.Random(42)
        for _ in range(20):
            a = [rng.uniform(-1, 1) for _ in range(8)]
            b = [rng.uniform(-1, 1) for _ in range(8)]
            result = self._csim(a, b)
            assert 0.0 <= result <= 1.0


# ---------------------------------------------------------------------------
# _get_or_compute_embedding tests (DB integration)
# ---------------------------------------------------------------------------


@pytest.fixture()
def temp_db() -> Generator[str, None, None]:
    """Temporary SQLite database file path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    try:
        Path(db_path).unlink()
    except FileNotFoundError:
        pass


@pytest.fixture()
def db_engine(temp_db):
    """Engine with all ORM tables created (bypasses Alembic)."""
    from skillmeat.cache.models import Base, create_db_engine

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
    """Insert the collection project row required by FK constraints."""
    from skillmeat.cache.models import Project

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
    name: str = "test-artifact",
    artifact_type: str = "skill",
    project_id: str = _COLLECTION_PROJECT_ID,
):
    """Create and persist a minimal Artifact row."""
    from skillmeat.cache.models import Artifact

    uid = uuid or _make_uuid()
    aid = f"{artifact_type}:{name}"
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


class TestGetOrComputeEmbedding:
    """SimilarityCacheManager._get_or_compute_embedding cache hit and miss paths."""

    def _make_mock_embedder(self, vector: List[float] | None = None):
        """Return a mock embedder that resolves get_embedding to *vector*."""
        embedder = MagicMock()
        embedder.MODEL_NAME = "all-MiniLM-L6-v2"
        # get_embedding is async; use AsyncMock so asyncio.run works correctly.
        embedder.get_embedding = AsyncMock(return_value=vector)
        return embedder

    def _make_embedding_blob(self, vector: List[float]) -> bytes:
        """Serialise *vector* to float32 bytes the way the manager stores it."""
        import numpy as np

        return np.array(vector, dtype=np.float32).tobytes()

    def test_cache_miss_calls_embedder_and_stores_result(
        self, db_session, seeded_project
    ):
        """On cache miss, embedder is called and result is persisted."""
        from skillmeat.cache.models import ArtifactEmbedding
        from skillmeat.cache.similarity_cache import SimilarityCacheManager

        # artifact_embeddings has an FK to artifacts.uuid — create the row first.
        art = _make_artifact(db_session, name="emb-miss-art")
        db_session.commit()

        mgr = SimilarityCacheManager()
        vector = [0.1 * i for i in range(384)]
        mock_embedder = self._make_mock_embedder(vector=vector)

        result = mgr._get_or_compute_embedding(
            art.uuid, "some artifact text", db_session, mock_embedder
        )

        assert result is not None
        assert len(result) == 384
        assert result[0] == pytest.approx(0.0, abs=1e-5)

        # Verify persisted row exists.
        db_session.expire_all()
        stored = (
            db_session.query(ArtifactEmbedding)
            .filter(ArtifactEmbedding.artifact_uuid == art.uuid)
            .first()
        )
        assert stored is not None
        assert stored.model_name == "all-MiniLM-L6-v2"
        assert stored.embedding_dim == 384

    def test_cache_hit_returns_stored_vector_without_calling_embedder(
        self, db_session, seeded_project
    ):
        """On cache hit, the stored embedding is returned and embedder is NOT called."""
        from skillmeat.cache.models import ArtifactEmbedding
        from skillmeat.cache.similarity_cache import SimilarityCacheManager

        # artifact_embeddings FK requires a real artifacts row.
        art = _make_artifact(db_session, name="emb-hit-art")
        db_session.commit()

        stored_vector = [float(i) for i in range(384)]
        blob = self._make_embedding_blob(stored_vector)

        # Pre-seed the DB with an existing embedding row.
        row = ArtifactEmbedding(
            artifact_uuid=art.uuid,
            embedding=blob,
            model_name="all-MiniLM-L6-v2",
            embedding_dim=384,
            computed_at=datetime.utcnow(),
        )
        db_session.add(row)
        db_session.commit()

        mock_embedder = self._make_mock_embedder(vector=None)
        mgr = SimilarityCacheManager()

        result = mgr._get_or_compute_embedding(
            art.uuid, "some artifact text", db_session, mock_embedder
        )

        assert result is not None
        assert len(result) == 384
        # embedder.get_embedding must NOT have been called.
        mock_embedder.get_embedding.assert_not_called()

    def test_cache_miss_returns_none_when_embedder_returns_none(
        self, db_session, seeded_project
    ):
        """When the embedder returns None, _get_or_compute_embedding returns None."""
        from skillmeat.cache.similarity_cache import SimilarityCacheManager

        # No artifact row needed — embedder returns None before any DB write.
        mock_embedder = self._make_mock_embedder(vector=None)
        mgr = SimilarityCacheManager()

        result = mgr._get_or_compute_embedding(
            _make_uuid(), "some text", db_session, mock_embedder
        )
        assert result is None

    def test_model_name_mismatch_triggers_recompute(
        self, db_session, seeded_project
    ):
        """A stored embedding with a different model name triggers recomputation."""
        import numpy as np

        from skillmeat.cache.models import ArtifactEmbedding
        from skillmeat.cache.similarity_cache import SimilarityCacheManager

        # FK requires a real artifact row.
        art = _make_artifact(db_session, name="emb-mismatch-art")
        db_session.commit()

        old_vector = [1.0] * 768
        blob = np.array(old_vector, dtype=np.float32).tobytes()

        # Store embedding with a different model name.
        row = ArtifactEmbedding(
            artifact_uuid=art.uuid,
            embedding=blob,
            model_name="old-model-v1",
            embedding_dim=768,
            computed_at=datetime.utcnow(),
        )
        db_session.add(row)
        db_session.commit()

        new_vector = [0.5] * 384
        mock_embedder = self._make_mock_embedder(vector=new_vector)
        mock_embedder.MODEL_NAME = "all-MiniLM-L6-v2"

        mgr = SimilarityCacheManager()
        result = mgr._get_or_compute_embedding(
            art.uuid, "updated text", db_session, mock_embedder
        )

        # Recomputed with the new model.
        assert result is not None
        mock_embedder.get_embedding.assert_called_once()


# ---------------------------------------------------------------------------
# compute_and_store with/without embeddings (composite score integration)
# ---------------------------------------------------------------------------


class TestComputeAndStoreEmbeddingIntegration:
    """composite score includes semantic_score when embedder is available."""

    def _make_breakdown_mock(
        self,
        keyword: float = 0.5,
        content: float = 0.5,
        structure: float = 0.5,
        metadata: float = 0.5,
        semantic: float | None = None,
        text: float | None = None,
    ):
        """Return a ScoreBreakdown with the given values."""
        from skillmeat.core.similarity import ScoreBreakdown

        return ScoreBreakdown(
            keyword_score=keyword,
            content_score=content,
            structure_score=structure,
            metadata_score=metadata,
            semantic_score=semantic,
            text_score=text,
        )

    def test_compute_and_store_without_embeddings_uses_fallback_weights(
        self, db_session, seeded_project
    ):
        """When embedder is unavailable, breakdown_json has no semantic_score key.

        SentenceTransformerEmbedder is imported inside the function body of
        compute_and_store, so we patch it at its definition module and also
        pin the availability flag so the instantiated instance returns False.
        """
        from skillmeat.cache.similarity_cache import SimilarityCacheManager
        import skillmeat.core.scoring.embedder as _emb_mod

        src = _make_artifact(db_session, name="src-noemb")
        _make_artifact(db_session, name="cand-noemb")
        db_session.commit()

        mgr = SimilarityCacheManager()
        fixed_bd = self._make_breakdown_mock(semantic=None)

        # Pin availability to False so the instance.is_available() returns False.
        original_flag = _emb_mod._sentence_transformers_available
        _emb_mod._sentence_transformers_available = False
        try:
            with patch(
                "skillmeat.core.similarity.SimilarityService"
            ) as MockSvc:
                mock_svc_instance = MagicMock()
                MockSvc.return_value = mock_svc_instance
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
        finally:
            _emb_mod._sentence_transformers_available = original_flag

        assert len(results) > 0
        for r in results:
            bd = json.loads(r["breakdown_json"])
            # When embedder unavailable, semantic path falls through to
            # _score_semantic_with_timeout which we mocked to return None.
            # The persisted breakdown must not contain "semantic_score".
            assert "semantic_score" not in bd

    def test_compute_and_store_with_embeddings_includes_semantic_score(
        self, db_session, seeded_project
    ):
        """When embedder is available, breakdown_json includes semantic_score.

        Because SentenceTransformerEmbedder is instantiated inside compute_and_store
        via a local import, we:
          1. Pin _sentence_transformers_available = True so is_available() returns True.
          2. Patch _get_or_compute_embedding on the manager instance to return a
             fixed vector for both source and candidate, bypassing real encoding.
        """
        from skillmeat.cache.similarity_cache import SimilarityCacheManager
        import skillmeat.core.scoring.embedder as _emb_mod

        src = _make_artifact(db_session, name="src-emb")
        _make_artifact(db_session, name="cand-emb")
        db_session.commit()

        mgr = SimilarityCacheManager()
        fixed_bd = self._make_breakdown_mock(semantic=None)
        fake_vector = [0.1] * 384

        original_flag = _emb_mod._sentence_transformers_available
        _emb_mod._sentence_transformers_available = True

        # Also stub SentenceTransformer so the lazy load inside _load_model
        # doesn't try to download a model.
        fake_st_module = MagicMock()
        fake_model_instance = MagicMock()
        fake_model_instance.encode.return_value = fake_vector
        fake_st_module.SentenceTransformer.return_value = fake_model_instance

        try:
            with patch.dict(sys.modules, {"sentence_transformers": fake_st_module}):
                with patch(
                    "skillmeat.core.similarity.SimilarityService"
                ) as MockSvc:
                    mock_svc_instance = MagicMock()
                    MockSvc.return_value = mock_svc_instance
                    mock_svc_instance._fingerprint_from_row.return_value = MagicMock(
                        description="artifact description"
                    )
                    mock_svc_instance._analyzer.compare.return_value = fixed_bd
                    mock_svc_instance._compute_composite_score.return_value = 0.6

                    # _get_or_compute_embedding must return a vector for both source
                    # and candidate so cosine similarity is actually computed.
                    with patch.object(
                        mgr,
                        "_get_or_compute_embedding",
                        return_value=fake_vector,
                    ):
                        with patch.object(
                            type(mgr), "_fts5_candidate_uuids", return_value=None
                        ):
                            results = mgr.compute_and_store(src.uuid, db_session)
        finally:
            _emb_mod._sentence_transformers_available = original_flag

        assert len(results) > 0
        for r in results:
            bd = json.loads(r["breakdown_json"])
            # Embedding path → semantic_score must be present.
            assert "semantic_score" in bd
            sem = bd["semantic_score"]
            assert 0.0 <= sem <= 1.0
