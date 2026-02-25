"""Similar Artifacts — Detection, Comparison & Consolidation.

Provides SimilarityService for finding, scoring, and ranking similar artifacts
using ArtifactFingerprint + MatchAnalyzer + optional SemanticScorer.

Design notes
------------
- ``ScoreBreakdown`` is a frozen dataclass so it can be used as a dict key or
  in sets without risk of post-construction mutation.
- ``SimilarityResult.match_type`` is derived automatically in ``__post_init__``
  from the composite score — callers never set it directly.
- ``semantic_score`` on ``ScoreBreakdown`` is ``Optional[float]`` because the
  SemanticScorer may be unavailable (not configured) or may time-out; the rest
  of the pipeline continues without it.
- ``SimilarityService`` will be added in a later task once the repository and
  API layers are in place.

Usage
-----
>>> from skillmeat.core.similarity import SimilarityResult, ScoreBreakdown, MatchType
>>> breakdown = ScoreBreakdown(
...     content_score=0.9,
...     structure_score=0.8,
...     metadata_score=0.7,
...     keyword_score=0.6,
... )
>>> result = SimilarityResult(
...     artifact_id="skill:canvas-design",
...     artifact=None,
...     composite_score=0.82,
...     breakdown=breakdown,
... )
>>> result.match_type
<MatchType.NEAR_DUPLICATE: 'near_duplicate'>
"""

from __future__ import annotations

import concurrent.futures
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class MatchType(str, Enum):
    """Classification of similarity match strength.

    Thresholds
    ----------
    EXACT           Score >= 0.95
    NEAR_DUPLICATE  Score >= 0.80
    SIMILAR         Score >= 0.50
    RELATED         Score >= min_score threshold (anything below 0.50)
    """

    EXACT = "exact"
    NEAR_DUPLICATE = "near_duplicate"
    SIMILAR = "similar"
    RELATED = "related"


@dataclass(frozen=True)
class ScoreBreakdown:
    """Individual score components from similarity analysis.

    All scores are in the range 0.0–1.0.  ``semantic_score`` is ``None``
    when the SemanticScorer is unavailable or timed out; the composite
    score is computed from the remaining components in that case.

    Attributes:
        content_score:   Similarity based on raw file-content hashes.
        structure_score: Similarity based on directory/file-tree structure.
        metadata_score:  Similarity based on title, description, and tags.
        keyword_score:   Similarity based on keyword/TF-IDF match analysis.
        semantic_score:  Embedding-based semantic similarity (optional).
    """

    content_score: float = 0.0
    structure_score: float = 0.0
    metadata_score: float = 0.0
    keyword_score: float = 0.0
    semantic_score: Optional[float] = None  # None when SemanticScorer unavailable/timed out


@dataclass
class SimilarityResult:
    """A single similar artifact with its composite score and breakdown.

    ``match_type`` is derived automatically from ``composite_score`` in
    ``__post_init__`` and must not be provided by callers.

    Attributes:
        artifact_id:     Canonical ``type:name`` identifier for the artifact.
        artifact:        The artifact object (typed as ``object`` until the
                         CachedArtifact import is wired up in a later task).
        composite_score: Weighted aggregate of all score components (0.0–1.0).
        breakdown:       Per-component score breakdown.
        match_type:      Derived strength classification (set in __post_init__).
    """

    artifact_id: str
    artifact: object  # Will be typed as CachedArtifact once available
    composite_score: float
    breakdown: ScoreBreakdown
    match_type: MatchType = field(init=False)

    def __post_init__(self) -> None:
        """Derive match_type from composite_score."""
        if self.composite_score >= 0.95:
            self.match_type = MatchType.EXACT
        elif self.composite_score >= 0.80:
            self.match_type = MatchType.NEAR_DUPLICATE
        elif self.composite_score >= 0.50:
            self.match_type = MatchType.SIMILAR
        else:
            self.match_type = MatchType.RELATED


class SimilarityService:
    """Orchestrates artifact similarity detection using multiple scorers.

    Wraps ArtifactFingerprint + MatchAnalyzer + optional SemanticScorer.
    SemanticScorer has an 800 ms timeout; falls back to keyword-only
    transparently on timeout or any scoring error.

    Composite score weights
    ----------------------
    keyword   0.30
    content   0.25
    structure 0.20
    metadata  0.15
    semantic  0.10  (redistributed proportionally when unavailable)

    Attributes:
        SEMANTIC_TIMEOUT_MS: Hard timeout (in ms) for each SemanticScorer call.
        _analyzer:           MatchAnalyzer instance shared across all comparisons.
        _semantic:           SemanticScorer instance, or None when unavailable.
        _session:            Optional SQLAlchemy session for DB queries.
    """

    SEMANTIC_TIMEOUT_MS: int = 800

    # Composite score weights (must sum to 1.0 when semantic is available)
    _WEIGHTS: dict[str, float] = {
        "keyword": 0.30,
        "content": 0.25,
        "structure": 0.20,
        "metadata": 0.15,
        "semantic": 0.10,
    }

    def __init__(self, session: Optional["Session"] = None) -> None:
        """Initialize with optional DB session for repository access.

        Args:
            session: SQLAlchemy Session to use for DB queries.  When ``None``
                     the service will attempt to open its own session via
                     ``skillmeat.cache.models.get_session`` at call time.
        """
        from skillmeat.core.scoring.match_analyzer import MatchAnalyzer

        self._analyzer = MatchAnalyzer()
        self._session = session
        self._semantic: Optional[object] = None  # SemanticScorer | None

        # Attempt to build the SemanticScorer; failures are non-fatal.
        try:
            from skillmeat.core.scoring.haiku_embedder import HaikuEmbedder
            from skillmeat.core.scoring.semantic_scorer import SemanticScorer

            embedder = HaikuEmbedder()
            scorer = SemanticScorer(embedder)
            if scorer.is_available():
                self._semantic = scorer
                logger.debug("SimilarityService: SemanticScorer initialised.")
            else:
                logger.debug(
                    "SimilarityService: SemanticScorer unavailable (no API key?)."
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "SimilarityService: could not initialise SemanticScorer: %s", exc
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def find_similar(
        self,
        artifact_id: str,
        limit: int = 10,
        min_score: float = 0.3,
        source: str = "collection",
    ) -> List[SimilarityResult]:
        """Find artifacts similar to the given artifact.

        Args:
            artifact_id: UUID (hex) of the target artifact in the DB.
            limit:       Maximum number of results to return (default 10).
            min_score:   Minimum composite score threshold — results below
                         this value are excluded (default 0.3).
            source:      Where to search.  One of:

                         * ``'collection'`` — artifacts in the user's
                           collection (project_id == 'collection_artifacts_global')
                         * ``'marketplace'`` — MarketplaceCatalogEntry rows
                         * ``'all'`` — both of the above

        Returns:
            List of :class:`SimilarityResult` sorted by ``composite_score``
            descending.  Returns an empty list when the target artifact is not
            found or no candidates meet ``min_score``.
        """
        session = self._get_session()
        try:
            return self._find_similar_impl(
                session=session,
                artifact_id=artifact_id,
                limit=limit,
                min_score=min_score,
                source=source,
            )
        finally:
            if self._session is None:
                # We opened the session ourselves — close it.
                session.close()

    # ------------------------------------------------------------------
    # Private implementation helpers
    # ------------------------------------------------------------------

    def _get_session(self) -> "Session":
        """Return the injected session or open a fresh one."""
        if self._session is not None:
            return self._session
        from skillmeat.cache.models import get_session

        return get_session()

    def _find_similar_impl(
        self,
        session: "Session",
        artifact_id: str,
        limit: int,
        min_score: float,
        source: str,
    ) -> List[SimilarityResult]:
        """Core implementation running inside an open session."""
        from skillmeat.cache.models import Artifact

        # 1. Fetch target artifact by UUID.
        target_row: Optional[Artifact] = (
            session.query(Artifact).filter(Artifact.uuid == artifact_id).first()
        )
        if target_row is None:
            logger.debug(
                "SimilarityService.find_similar: artifact uuid=%s not found.",
                artifact_id,
            )
            return []

        # 2. Build ArtifactFingerprint for the target.
        target_fp = self._fingerprint_from_row(target_row)

        # 3. Fetch candidate rows (exclude the target itself).
        candidates = self._fetch_candidates(session, artifact_id, source)
        if not candidates:
            return []

        # 4. Score each candidate and collect results.
        results: List[SimilarityResult] = []
        for row in candidates:
            candidate_fp = self._fingerprint_from_row(row)

            # 4a. Keyword/content/structure/metadata scores via MatchAnalyzer.compare().
            breakdown = self._analyzer.compare(target_fp, candidate_fp)

            # 4b. Optional semantic score with 800 ms timeout.
            semantic_score = self._score_semantic_with_timeout(target_fp, candidate_fp)

            # 4c. Rebuild breakdown with semantic score (ScoreBreakdown is frozen).
            breakdown = ScoreBreakdown(
                keyword_score=breakdown.keyword_score,
                content_score=breakdown.content_score,
                structure_score=breakdown.structure_score,
                metadata_score=breakdown.metadata_score,
                semantic_score=semantic_score,
            )

            # 4d. Compute weighted composite score.
            composite = self._compute_composite_score(breakdown)

            # 4e. Apply min_score filter.
            if composite < min_score:
                continue

            results.append(
                SimilarityResult(
                    artifact_id=row.id,
                    artifact=row,
                    composite_score=composite,
                    breakdown=breakdown,
                )
            )

        # 5. Sort descending by composite_score and return top N.
        results.sort(key=lambda r: r.composite_score, reverse=True)
        return results[:limit]

    def _fingerprint_from_row(self, row: object) -> object:
        """Build an :class:`~skillmeat.models.ArtifactFingerprint` from a DB row.

        Handles both ``Artifact`` (collection) and ``MarketplaceCatalogEntry``
        (marketplace) rows by inspecting available attributes.

        Args:
            row: SQLAlchemy ORM row — either an ``Artifact`` or a
                 ``MarketplaceCatalogEntry`` instance.

        Returns:
            An :class:`~skillmeat.models.ArtifactFingerprint` suitable for
            passing to :meth:`MatchAnalyzer.compare`.
        """
        from skillmeat.models import ArtifactFingerprint

        # --- Determine name, type, title, description, tags ---
        artifact_name: str = getattr(row, "name", "") or ""
        artifact_type: str = getattr(row, "type", "") or getattr(
            row, "artifact_type", ""
        ) or ""
        title: Optional[str] = None
        description: Optional[str] = getattr(row, "description", None)
        tags: List[str] = []
        content_hash: str = getattr(row, "content_hash", "") or ""
        total_size: int = 0
        file_count: int = 0
        structure_hash: str = ""
        metadata_hash: str = ""

        # Enrich from artifact_metadata relationship if available (Artifact rows).
        meta = getattr(row, "artifact_metadata", None)
        if meta is not None:
            if not description:
                description = getattr(meta, "description", None)
            tags = meta.get_tags_list()
            # Pull title from the metadata JSON if stored there.
            meta_dict = meta.get_metadata_dict()
            if meta_dict:
                title = meta_dict.get("title") or None
                if not description:
                    description = meta_dict.get("description") or None

        # Fallback: MarketplaceCatalogEntry may expose title directly.
        if title is None:
            title = getattr(row, "title", None)

        # MarketplaceCatalogEntry tags are stored as JSON list.
        if not tags:
            raw_tags = getattr(row, "tags", None)
            if isinstance(raw_tags, list):
                tags = [str(t) for t in raw_tags]
            elif isinstance(raw_tags, str) and raw_tags:
                tags = [t.strip() for t in raw_tags.split(",") if t.strip()]

        # Use artifact path as a stable but dummy Path (fingerprinting only needs it
        # as an identifier; the actual path is not accessed during compare()).
        artifact_path = Path(f"/{artifact_type}/{artifact_name}")

        return ArtifactFingerprint(
            artifact_path=artifact_path,
            artifact_name=artifact_name,
            artifact_type=artifact_type,
            content_hash=content_hash,
            metadata_hash=metadata_hash,
            structure_hash=structure_hash,
            title=title,
            description=description,
            tags=tags,
            file_count=file_count,
            total_size=total_size,
        )

    def _fetch_candidates(
        self, session: "Session", exclude_uuid: str, source: str
    ) -> List[object]:
        """Fetch candidate artifact rows from the DB based on source param.

        Args:
            session:      Open SQLAlchemy session.
            exclude_uuid: UUID of the target artifact (excluded from results).
            source:       ``'collection'``, ``'marketplace'``, or ``'all'``.

        Returns:
            List of ORM rows (``Artifact`` and/or ``MarketplaceCatalogEntry``).
        """
        rows: List[object] = []

        if source in ("collection", "all"):
            rows.extend(self._fetch_collection_candidates(session, exclude_uuid))

        if source in ("marketplace", "all"):
            rows.extend(self._fetch_marketplace_candidates(session))

        return rows

    def _fetch_collection_candidates(
        self, session: "Session", exclude_uuid: str
    ) -> List[object]:
        """Fetch Artifact rows from the user's collection (excluding target)."""
        from skillmeat.cache.models import Artifact

        _COLLECTION_PROJECT_ID = "collection_artifacts_global"
        return (
            session.query(Artifact)
            .filter(
                Artifact.project_id == _COLLECTION_PROJECT_ID,
                Artifact.uuid != exclude_uuid,
            )
            .all()
        )

    def _fetch_marketplace_candidates(self, session: "Session") -> List[object]:
        """Fetch MarketplaceCatalogEntry rows for similarity comparison."""
        from skillmeat.cache.models import MarketplaceCatalogEntry

        return (
            session.query(MarketplaceCatalogEntry)
            .filter(MarketplaceCatalogEntry.status == "active")
            .all()
        )

    def _score_semantic_with_timeout(
        self,
        target_fp: object,
        candidate_fp: object,
    ) -> Optional[float]:
        """Run SemanticScorer with an 800 ms wall-clock timeout.

        Returns ``None`` on timeout, error, or when SemanticScorer is
        unavailable, so the caller can redistribute the weight.

        Args:
            target_fp:    Fingerprint for the target artifact.
            candidate_fp: Fingerprint for the candidate artifact.

        Returns:
            Semantic similarity score in [0, 1], or ``None``.
        """
        if self._semantic is None:
            return None

        import asyncio
        from skillmeat.core.artifact import ArtifactMetadata
        from skillmeat.core.scoring.semantic_scorer import SemanticScorer

        semantic_scorer: SemanticScorer = self._semantic  # type: ignore[assignment]

        # Build a combined query string from the target fingerprint's text.
        target_parts: List[str] = []
        if hasattr(target_fp, "artifact_name") and target_fp.artifact_name:  # type: ignore[union-attr]
            target_parts.append(target_fp.artifact_name)  # type: ignore[union-attr]
        if hasattr(target_fp, "title") and target_fp.title:  # type: ignore[union-attr]
            target_parts.append(target_fp.title)  # type: ignore[union-attr]
        if hasattr(target_fp, "description") and target_fp.description:  # type: ignore[union-attr]
            target_parts.append(target_fp.description)  # type: ignore[union-attr]
        query_text = " ".join(target_parts).strip()
        if not query_text:
            return None

        # Build a lightweight ArtifactMetadata for the candidate.
        candidate_meta = ArtifactMetadata(
            title=getattr(candidate_fp, "title", "") or "",
            description=getattr(candidate_fp, "description", "") or "",
            tags=list(getattr(candidate_fp, "tags", [])),
        )

        def _run_async() -> Optional[float]:
            """Execute the async score_artifact in a fresh event loop."""
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(
                    semantic_scorer.score_artifact(query_text, candidate_meta)
                )
            finally:
                loop.close()

        timeout_s = self.SEMANTIC_TIMEOUT_MS / 1000.0
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_run_async)
                raw_score = future.result(timeout=timeout_s)
        except concurrent.futures.TimeoutError:
            logger.warning(
                "SimilarityService: SemanticScorer timed out after %d ms; "
                "falling back to keyword-only scoring.",
                self.SEMANTIC_TIMEOUT_MS,
            )
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "SimilarityService: SemanticScorer raised %s; "
                "falling back to keyword-only scoring.",
                exc,
            )
            return None

        # SemanticScorer returns scores in [0, 100]; normalise to [0, 1].
        if raw_score is None:
            return None
        return min(1.0, max(0.0, raw_score / 100.0))

    def _compute_composite_score(self, breakdown: ScoreBreakdown) -> float:
        """Compute weighted average of score components.

        Weights: keyword=0.30, content=0.25, structure=0.20, metadata=0.15,
        semantic=0.10.  When ``breakdown.semantic_score`` is ``None`` the
        0.10 semantic weight is redistributed proportionally across the
        remaining four components.

        Args:
            breakdown: Per-component score breakdown from MatchAnalyzer.

        Returns:
            Composite similarity score in [0.0, 1.0].
        """
        weights = dict(self._WEIGHTS)

        if breakdown.semantic_score is None:
            # Remove the semantic key and redistribute its weight.
            semantic_w = weights.pop("semantic")
            total_remaining = sum(weights.values())
            if total_remaining > 0:
                for key in weights:
                    weights[key] += semantic_w * (weights[key] / total_remaining)

        component_values = {
            "keyword": breakdown.keyword_score,
            "content": breakdown.content_score,
            "structure": breakdown.structure_score,
            "metadata": breakdown.metadata_score,
        }
        if breakdown.semantic_score is not None:
            component_values["semantic"] = breakdown.semantic_score

        composite = sum(
            component_values[key] * weights[key] for key in component_values
        )
        return min(1.0, max(0.0, composite))
