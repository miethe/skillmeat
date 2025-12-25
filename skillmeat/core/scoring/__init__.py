"""Scoring infrastructure for artifact confidence and quality metrics."""

from .anti_gaming import (
    AntiGamingGuard,
    AnomalyDetector,
    RateLimiter,
    RateLimitConfig,
    ViolationRecord,
    ViolationType,
)
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
from .score_aggregator import AggregatedScore, ScoreAggregator, ScoreSource
from .score_decay import DecayedScore, ScoreDecay
from .semantic_scorer import SemanticScorer
from .service import ScoringService

__all__ = [
    # Models
    "ArtifactScore",
    "UserRating",
    "CommunityScore",
    "ScoringResult",
    "AggregatedScore",
    "ScoreSource",
    "DecayedScore",
    # Scorers
    "QualityScorer",
    "MatchAnalyzer",
    "SemanticScorer",
    "ScoreAggregator",
    "ScoreDecay",
    # Context
    "ContextBooster",
    "ProjectContext",
    # Embedding
    "EmbeddingProvider",
    "HaikuEmbedder",
    # Service
    "ScoringService",
    # Anti-Gaming
    "AntiGamingGuard",
    "RateLimiter",
    "RateLimitConfig",
    "AnomalyDetector",
    "ViolationRecord",
    "ViolationType",
    # Exceptions
    "ScoringError",
    "EmbeddingServiceUnavailable",
    "ScoringTimeout",
    "ArtifactNotFound",
]
