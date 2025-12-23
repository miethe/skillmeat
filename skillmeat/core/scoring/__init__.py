"""Scoring infrastructure for artifact confidence and quality metrics."""

from .context_booster import ContextBooster, ProjectContext
from .embedding_provider import EmbeddingProvider
from .exceptions import (
    ArtifactNotFound,
    EmbeddingServiceUnavailable,
    ScoringError,
    ScoringTimeout,
)
from .haiku_embedder import HaikuEmbedder
from .match_analyzer import MatchAnalyzer
from .models import ArtifactScore, CommunityScore, ScoringResult, UserRating
from .quality_scorer import QualityScorer
from .semantic_scorer import SemanticScorer
from .service import ScoringService

__all__ = [
    # Models
    "ArtifactScore",
    "UserRating",
    "CommunityScore",
    "ScoringResult",
    # Scorers
    "QualityScorer",
    "MatchAnalyzer",
    "SemanticScorer",
    # Context
    "ContextBooster",
    "ProjectContext",
    # Embedding
    "EmbeddingProvider",
    "HaikuEmbedder",
    # Service
    "ScoringService",
    # Exceptions
    "ScoringError",
    "EmbeddingServiceUnavailable",
    "ScoringTimeout",
    "ArtifactNotFound",
]
