"""SimilarityCacheManager — read/write layer for the SimilarityCache table.

This module provides a standalone manager class that wraps the
``SimilarityCache`` ORM model.  It is intentionally thin — it delegates all
scoring to :class:`~skillmeat.core.similarity.SimilarityService` and handles
only persistence, invalidation, and FTS5-based candidate pre-filtering.

Typical usage::

    from skillmeat.cache.models import get_session
    from skillmeat.cache.similarity_cache import SimilarityCacheManager

    manager = SimilarityCacheManager()
    session = get_session()
    try:
        results = manager.get_similar(artifact_uuid, session)
        if not results:
            results = manager.compute_and_store(artifact_uuid, session)
    finally:
        session.close()
"""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Maximum number of similar artifacts stored per source artifact.
_TOP_N = 20

# FTS5 candidate pool size — score only the top-N FTS5 hits before full scoring.
_FTS5_CANDIDATE_LIMIT = 50


class SimilarityCacheManager:
    """Manages the ``similarity_cache`` table for pre-computed similarity scores.

    Provides four operations:

    * :meth:`get_similar`       — cache lookup (returns empty list on miss)
    * :meth:`compute_and_store` — score + persist top-20 similar artifacts
    * :meth:`invalidate`        — delete rows where artifact is source OR target
    * :meth:`rebuild_all`       — truncate + recompute for all artifacts

    All methods accept a caller-provided ``session`` so they compose cleanly
    with the caller's transaction boundary.  This class never opens or closes
    sessions itself.

    FTS5 pre-filtering
    ------------------
    Before full scoring, :meth:`compute_and_store` issues a raw
    ``SELECT artifact_uuid FROM artifact_fts WHERE artifact_fts MATCH ? LIMIT 50``
    query to narrow the candidate pool.  If the ``artifact_fts`` virtual table
    does not exist (SQLite compiled without FTS5, or the table was never
    created) the query will raise an ``OperationalError``, which is caught and
    logged; the method falls back to scoring *all* collection artifacts.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_similar(
        self,
        artifact_uuid: str,
        session: "Session",
        limit: int = 20,
        min_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Return cached similar artifacts for *artifact_uuid*.

        Performs a single ``SELECT`` against ``similarity_cache`` ordered by
        ``composite_score DESC``.  Returns an **empty list** when no cached
        rows exist (cache miss) — the caller is responsible for calling
        :meth:`compute_and_store` in that case.

        Args:
            artifact_uuid: UUID of the source artifact to look up.
            session:       Open SQLAlchemy session (not closed by this method).
            limit:         Maximum number of rows to return (default 20).
            min_score:     Minimum composite score to include (default 0.0).

        Returns:
            List of dicts with keys ``target_artifact_uuid``,
            ``composite_score``, ``breakdown_json``, ``computed_at``.
            Ordered by ``composite_score`` descending.
        """
        from skillmeat.cache.models import SimilarityCache

        rows = (
            session.query(SimilarityCache)
            .filter(
                SimilarityCache.source_artifact_uuid == artifact_uuid,
                SimilarityCache.composite_score >= min_score,
            )
            .order_by(SimilarityCache.composite_score.desc())
            .limit(limit)
            .all()
        )

        return [self._row_to_dict(row) for row in rows]

    def compute_and_store(
        self,
        artifact_uuid: str,
        session: "Session",
    ) -> List[Dict[str, Any]]:
        """Score top-20 similar artifacts and persist them to the cache.

        Algorithm:

        1. Fetch the source ``Artifact`` row; return ``[]`` if not found.
        2. Build a MATCH query from name + description + tags and run FTS5
           pre-filter (fallback to all collection artifacts on error).
        3. Score each candidate using
           :class:`~skillmeat.core.similarity.SimilarityService`.
        4. Persist the top-20 results (replacing any existing rows for this
           source).
        5. Return the persisted results as a list of dicts.

        Args:
            artifact_uuid: UUID of the source artifact to score from.
            session:       Open SQLAlchemy session.

        Returns:
            List of dicts with keys ``target_artifact_uuid``,
            ``composite_score``, ``breakdown_json``, ``computed_at``.
            Ordered by ``composite_score`` descending.  Empty list when the
            source artifact is not found or has no viable candidates.
        """
        from skillmeat.cache.models import Artifact, SimilarityCache
        from skillmeat.core.similarity import SimilarityService, ScoreBreakdown

        # 1. Resolve source artifact.
        source_row: Optional[Artifact] = (
            session.query(Artifact).filter(Artifact.uuid == artifact_uuid).first()
        )
        if source_row is None:
            logger.debug(
                "SimilarityCacheManager.compute_and_store: artifact uuid=%s not found.",
                artifact_uuid,
            )
            return []

        # 2. Obtain candidate UUIDs (FTS5 pre-filter with graceful fallback).
        candidate_uuids = self._fts5_candidate_uuids(source_row, session)

        # 3. Fetch candidate Artifact rows; always exclude the source itself.
        if candidate_uuids is not None:
            # FTS5 gave us a specific pool.
            candidates = (
                session.query(Artifact)
                .filter(
                    Artifact.uuid.in_(candidate_uuids),
                    Artifact.uuid != artifact_uuid,
                )
                .all()
            )
        else:
            # Fallback: score everything in the collection.
            _COLLECTION_PROJECT_ID = "collection_artifacts_global"
            candidates = (
                session.query(Artifact)
                .filter(
                    Artifact.project_id == _COLLECTION_PROJECT_ID,
                    Artifact.uuid != artifact_uuid,
                )
                .all()
            )

        if not candidates:
            logger.debug(
                "SimilarityCacheManager.compute_and_store: no candidates for uuid=%s.",
                artifact_uuid,
            )
            return []

        # 4. Score candidates via SimilarityService helpers (reuse without DB I/O).
        svc = SimilarityService(session=session)
        source_fp = svc._fingerprint_from_row(source_row)

        # Enrich source description from CollectionArtifact if needed.
        if not source_fp.description:
            from skillmeat.cache.models import CollectionArtifact

            ca = (
                session.query(CollectionArtifact)
                .filter(CollectionArtifact.artifact_uuid == artifact_uuid)
                .first()
            )
            if ca and ca.description:
                source_fp.description = ca.description

        # Determine whether the SentenceTransformerEmbedder is available for
        # DB-cached embedding lookups.  When available we compute cosine
        # similarity directly from stored vectors, which is much faster than
        # the per-pair SemanticScorer path (no async event loop per pair).
        try:
            from skillmeat.core.scoring.embedder import SentenceTransformerEmbedder

            _embedder = SentenceTransformerEmbedder()
            _use_embedding_cache = _embedder.is_available()
        except Exception:  # noqa: BLE001
            _embedder = None  # type: ignore[assignment]
            _use_embedding_cache = False

        # Pre-compute source embedding once (if embedder is available).
        source_emb: Optional[List[float]] = None
        if _use_embedding_cache:
            source_name = getattr(source_row, "name", "") or ""
            source_desc = getattr(source_fp, "description", "") or ""
            source_text = f"{source_name} {source_desc}".strip()
            if source_text:
                source_emb = self._get_or_compute_embedding(
                    artifact_uuid, source_text, session, _embedder
                )

        scored: List[tuple[float, str, ScoreBreakdown]] = []
        for candidate in candidates:
            candidate_fp = svc._fingerprint_from_row(candidate)

            # Enrich candidate description if needed.
            if not candidate_fp.description:
                from skillmeat.cache.models import CollectionArtifact

                cand_uuid = getattr(candidate, "uuid", None)
                if cand_uuid:
                    ca = (
                        session.query(CollectionArtifact)
                        .filter(CollectionArtifact.artifact_uuid == str(cand_uuid))
                        .first()
                    )
                    if ca and ca.description:
                        candidate_fp.description = ca.description

            breakdown = svc._analyzer.compare(source_fp, candidate_fp)

            # Compute semantic score: prefer DB-cached embedding cosine
            # similarity when available; fall back to the timeout-guarded
            # SemanticScorer path otherwise.
            semantic_score: Optional[float] = None
            if _use_embedding_cache and source_emb is not None:
                cand_uuid_str = str(getattr(candidate, "uuid", ""))
                cand_name = getattr(candidate, "name", "") or ""
                cand_desc = getattr(candidate_fp, "description", "") or ""
                cand_text = f"{cand_name} {cand_desc}".strip()
                if cand_text and cand_uuid_str:
                    cand_emb = self._get_or_compute_embedding(
                        cand_uuid_str, cand_text, session, _embedder
                    )
                    if cand_emb is not None:
                        semantic_score = self._cosine_similarity(source_emb, cand_emb)
            else:
                semantic_score = svc._score_semantic_with_timeout(source_fp, candidate_fp)

            breakdown = ScoreBreakdown(
                keyword_score=breakdown.keyword_score,
                content_score=breakdown.content_score,
                structure_score=breakdown.structure_score,
                metadata_score=breakdown.metadata_score,
                semantic_score=semantic_score,
                text_score=breakdown.text_score,
            )
            composite = svc._compute_composite_score(breakdown)
            scored.append((composite, str(candidate.uuid), breakdown))

        # Sort descending by composite score and take top-N.
        scored.sort(key=lambda t: t[0], reverse=True)
        top_results = scored[:_TOP_N]

        # 5. Persist — delete existing rows for this source first.
        session.query(SimilarityCache).filter(
            SimilarityCache.source_artifact_uuid == artifact_uuid
        ).delete(synchronize_session=False)

        now = datetime.utcnow()
        new_rows: List[SimilarityCache] = []
        for composite, target_uuid, breakdown in top_results:
            breakdown_data: Dict[str, Any] = {
                "keyword_score": breakdown.keyword_score,
                "content_score": breakdown.content_score,
                "structure_score": breakdown.structure_score,
                "metadata_score": breakdown.metadata_score,
            }
            if breakdown.semantic_score is not None:
                breakdown_data["semantic_score"] = breakdown.semantic_score
            if breakdown.text_score is not None:
                breakdown_data["text_score"] = breakdown.text_score

            row = SimilarityCache(
                source_artifact_uuid=artifact_uuid,
                target_artifact_uuid=target_uuid,
                composite_score=composite,
                breakdown_json=json.dumps(breakdown_data),
                computed_at=now,
            )
            new_rows.append(row)

        session.add_all(new_rows)
        session.flush()

        logger.info(
            "SimilarityCacheManager: stored %d similarity rows for uuid=%s.",
            len(new_rows),
            artifact_uuid,
        )

        return [self._row_to_dict(row) for row in new_rows]

    def invalidate(self, artifact_uuid: str, session: "Session") -> None:
        """Delete all ``SimilarityCache`` rows involving *artifact_uuid*.

        Removes rows where the artifact appears as **source** OR **target** so
        that stale scores do not linger after the artifact's content changes.

        Args:
            artifact_uuid: UUID of the artifact whose cache entries should be
                           deleted.
            session:       Open SQLAlchemy session.
        """
        from skillmeat.cache.models import SimilarityCache
        import sqlalchemy as sa

        deleted = session.execute(
            sa.delete(SimilarityCache).where(
                sa.or_(
                    SimilarityCache.source_artifact_uuid == artifact_uuid,
                    SimilarityCache.target_artifact_uuid == artifact_uuid,
                )
            )
        ).rowcount

        logger.info(
            "SimilarityCacheManager.invalidate: removed %d rows for uuid=%s.",
            deleted,
            artifact_uuid,
        )

    def rebuild_all(self, session: "Session") -> None:
        """Truncate the entire ``similarity_cache`` table and recompute all scores.

        This is a batch admin operation.  It iterates over every collection
        artifact and calls :meth:`compute_and_store` for each one.  The full
        recompute can be expensive for large collections; it is intended for
        admin/maintenance use (e.g., after a scoring algorithm change).

        Args:
            session: Open SQLAlchemy session.
        """
        from skillmeat.cache.models import Artifact, SimilarityCache
        import sqlalchemy as sa

        # Clear the entire table.
        deleted = session.execute(sa.delete(SimilarityCache)).rowcount
        logger.info(
            "SimilarityCacheManager.rebuild_all: cleared %d existing rows.", deleted
        )

        # Fetch all collection artifacts.
        _COLLECTION_PROJECT_ID = "collection_artifacts_global"
        all_artifacts = (
            session.query(Artifact)
            .filter(Artifact.project_id == _COLLECTION_PROJECT_ID)
            .all()
        )

        logger.info(
            "SimilarityCacheManager.rebuild_all: recomputing similarity for %d artifacts.",
            len(all_artifacts),
        )

        for artifact in all_artifacts:
            uuid_str = str(artifact.uuid)
            try:
                self.compute_and_store(uuid_str, session)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "SimilarityCacheManager.rebuild_all: error scoring uuid=%s: %s",
                    uuid_str,
                    exc,
                )

        logger.info("SimilarityCacheManager.rebuild_all: complete.")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fts5_candidate_uuids(
        self, source_row: object, session: "Session"
    ) -> Optional[List[str]]:
        """Return top-50 candidate UUIDs from the FTS5 index, or ``None`` on failure.

        Builds a MATCH query from the source artifact's name, description, and
        tags, then queries the ``artifact_fts`` virtual table.

        Args:
            source_row: The source ``Artifact`` ORM row.
            session:    Open SQLAlchemy session.

        Returns:
            List of UUID strings (may be empty), or ``None`` when FTS5 is
            unavailable or the query fails for any reason.
        """
        import sqlalchemy as sa

        # Build the query text from name, description, and tags.
        parts: List[str] = []

        name = getattr(source_row, "name", None)
        if name:
            parts.append(name)

        # Try artifact_metadata relationship for description + tags.
        meta = getattr(source_row, "artifact_metadata", None)
        if meta is not None:
            desc = getattr(meta, "description", None)
            if desc:
                parts.append(desc)
            try:
                tags = meta.get_tags_list()
                if tags:
                    parts.extend(tags)
            except Exception:  # noqa: BLE001
                pass
        else:
            desc = getattr(source_row, "description", None)
            if desc:
                parts.append(desc)

        if not parts:
            logger.debug(
                "SimilarityCacheManager._fts5_candidate_uuids: "
                "no text for FTS5 query on uuid=%s; using fallback.",
                getattr(source_row, "uuid", "?"),
            )
            return None

        # Sanitise for FTS5: strip double-quotes, wrap each token, join with OR.
        tokens = " ".join(parts).split()
        sanitised_tokens = [t.replace('"', "").replace("'", "") for t in tokens if t]
        if not sanitised_tokens:
            return None
        match_query = " OR ".join(f'"{tok}"' for tok in sanitised_tokens[:20])

        try:
            result = session.execute(
                sa.text(
                    "SELECT artifact_uuid FROM artifact_fts "
                    "WHERE artifact_fts MATCH :q LIMIT :lim"
                ),
                {"q": match_query, "lim": _FTS5_CANDIDATE_LIMIT},
            )
            uuids = [row[0] for row in result]
            logger.debug(
                "SimilarityCacheManager._fts5_candidate_uuids: "
                "FTS5 returned %d candidates for uuid=%s.",
                len(uuids),
                getattr(source_row, "uuid", "?"),
            )
            return uuids
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "SimilarityCacheManager._fts5_candidate_uuids: "
                "FTS5 query failed (%s); falling back to full scan.",
                exc,
            )
            return None

    def _get_or_compute_embedding(
        self,
        artifact_uuid: str,
        text: str,
        session: "Session",
        embedder: object,
    ) -> Optional[List[float]]:
        """Return the stored embedding for *artifact_uuid*, computing it if absent.

        Checks the ``artifact_embeddings`` table first.  If a matching row
        exists and the ``model_name`` matches the current embedder model, the
        stored bytes are deserialised and returned without re-encoding.

        If no matching row is found (or the model name has changed), the
        embedder is called synchronously via ``asyncio`` and the result is
        persisted for future reuse.

        Args:
            artifact_uuid: UUID of the artifact whose embedding is requested.
            text:          Text to embed (name + description, pre-joined).
            session:       Open SQLAlchemy session.
            embedder:      A ``SentenceTransformerEmbedder`` instance.

        Returns:
            List of ``float`` values (the embedding vector), or ``None`` when
            encoding fails or the embedder is unavailable.
        """
        from skillmeat.cache.models import ArtifactEmbedding

        model_name: str = getattr(embedder, "MODEL_NAME", "unknown")

        # Try cache hit first.
        existing: Optional[ArtifactEmbedding] = (
            session.query(ArtifactEmbedding)
            .filter(ArtifactEmbedding.artifact_uuid == artifact_uuid)
            .first()
        )
        if existing is not None and existing.model_name == model_name:
            try:
                import numpy as np

                vec = np.frombuffer(existing.embedding, dtype=np.float32)
                return [float(v) for v in vec]
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "SimilarityCacheManager._get_or_compute_embedding: "
                    "failed to deserialise stored embedding for uuid=%s: %s",
                    artifact_uuid,
                    exc,
                )
                # Fall through to recompute below.

        # Cache miss (or model changed): compute embedding synchronously.
        import asyncio

        def _run_async() -> Optional[List[float]]:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(embedder.get_embedding(text))  # type: ignore[union-attr]
            finally:
                loop.close()

        try:
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_run_async)
                vector: Optional[List[float]] = future.result(timeout=5.0)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "SimilarityCacheManager._get_or_compute_embedding: "
                "embedding computation failed for uuid=%s: %s",
                artifact_uuid,
                exc,
            )
            return None

        if vector is None:
            return None

        # Serialise and persist.
        try:
            import numpy as np

            arr = np.array(vector, dtype=np.float32)
            blob = arr.tobytes()
            dim = len(vector)

            if existing is not None:
                # Update in place (model name changed or prior deserialisation failed).
                existing.embedding = blob
                existing.model_name = model_name
                existing.embedding_dim = dim
                existing.computed_at = datetime.utcnow()
            else:
                new_row = ArtifactEmbedding(
                    artifact_uuid=artifact_uuid,
                    embedding=blob,
                    model_name=model_name,
                    embedding_dim=dim,
                    computed_at=datetime.utcnow(),
                )
                session.add(new_row)

            session.flush()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "SimilarityCacheManager._get_or_compute_embedding: "
                "failed to persist embedding for uuid=%s: %s",
                artifact_uuid,
                exc,
            )
            # Non-fatal: return the computed vector even if storage failed.

        return vector

    @staticmethod
    def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        """Compute cosine similarity between two vectors.

        Returns 0.0 for zero vectors (magnitude == 0) or mismatched lengths
        rather than raising an exception, so a single bad embedding never
        aborts the entire scoring loop.

        Args:
            vec_a: First embedding vector.
            vec_b: Second embedding vector.

        Returns:
            Cosine similarity in [0.0, 1.0].  Returns 0.0 for degenerate
            inputs (zero vectors or length mismatch).
        """
        if len(vec_a) != len(vec_b) or not vec_a:
            return 0.0

        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        mag_a = math.sqrt(sum(a * a for a in vec_a))
        mag_b = math.sqrt(sum(b * b for b in vec_b))

        if mag_a == 0.0 or mag_b == 0.0:
            return 0.0

        # Clamp to [0.0, 1.0] — floating-point imprecision can push slightly
        # past 1.0 for identical vectors.
        return min(1.0, max(0.0, dot / (mag_a * mag_b)))

    @staticmethod
    def _row_to_dict(row: object) -> Dict[str, Any]:
        """Convert a ``SimilarityCache`` ORM row to a plain dict.

        Args:
            row: A ``SimilarityCache`` ORM instance.

        Returns:
            Dict with keys ``target_artifact_uuid``, ``composite_score``,
            ``breakdown_json``, ``computed_at``.
        """
        return {
            "target_artifact_uuid": getattr(row, "target_artifact_uuid", None),
            "composite_score": getattr(row, "composite_score", 0.0),
            "breakdown_json": getattr(row, "breakdown_json", None),
            "computed_at": getattr(row, "computed_at", None),
        }
