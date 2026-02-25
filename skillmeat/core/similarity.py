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

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    pass  # Will add artifact type imports later


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
