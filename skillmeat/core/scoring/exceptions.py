"""Exception hierarchy for scoring operations.

This module defines the exception hierarchy for the SkillMeat scoring system,
providing granular error types for different failure scenarios.

Example:
    >>> from skillmeat.core.scoring.exceptions import ScoringError
    >>> try:
    ...     result = await score_artifacts(query, artifacts)
    ... except EmbeddingServiceUnavailable:
    ...     # Fall back to keyword-only scoring
    ...     result = keyword_score(query, artifacts)
    ... except ScoringTimeout:
    ...     # Return cached results or partial results
    ...     result = get_cached_results(query)
"""


class ScoringError(Exception):
    """Base exception for all scoring operations.

    All scoring-related exceptions inherit from this class, allowing
    callers to catch all scoring errors with a single except clause.

    Example:
        >>> try:
        ...     score = await scorer.score_artifact(query, artifact)
        ... except ScoringError as e:
        ...     logger.error(f"Scoring failed: {e}")
        ...     score = fallback_score
    """

    pass


class EmbeddingServiceUnavailable(ScoringError):
    """Embedding service is not available.

    Raised when the embedding service cannot be used due to:
    - Missing API key (ANTHROPIC_API_KEY not set)
    - Network connectivity issues
    - API rate limiting or quota exceeded
    - Service temporarily down

    This exception signals that the system should gracefully degrade
    to keyword-only scoring.

    Example:
        >>> try:
        ...     embedding = await embedder.get_embedding(text)
        ... except EmbeddingServiceUnavailable:
        ...     # Fall back to keyword matching
        ...     score = keyword_scorer.score(text)
    """

    pass


class ScoringTimeout(ScoringError):
    """Scoring operation exceeded timeout.

    Raised when a scoring operation takes longer than the configured
    timeout threshold. This typically indicates network issues, slow
    API responses, or resource constraints.

    The caller should handle this by:
    - Returning cached results if available
    - Falling back to faster keyword-only scoring
    - Returning partial results if some artifacts were scored

    Attributes:
        timeout_seconds: The timeout threshold that was exceeded

    Example:
        >>> try:
        ...     results = await scorer.score_all(query, artifacts, timeout=5.0)
        ... except ScoringTimeout as e:
        ...     logger.warning(f"Scoring timed out after {e.timeout_seconds}s")
        ...     results = get_cached_results(query)
    """

    def __init__(self, message: str, timeout_seconds: float):
        """Initialize timeout exception.

        Args:
            message: Human-readable error message
            timeout_seconds: The timeout threshold that was exceeded
        """
        super().__init__(message)
        self.timeout_seconds = timeout_seconds


class ArtifactNotFound(ScoringError):
    """Referenced artifact not found.

    Raised when attempting to score an artifact that doesn't exist
    in the collection or has been removed.

    Attributes:
        artifact_id: The identifier of the missing artifact

    Example:
        >>> try:
        ...     artifact = get_artifact("skill:missing")
        ...     score = scorer.score_artifact(query, artifact)
        ... except ArtifactNotFound as e:
        ...     logger.warning(f"Artifact not found: {e.artifact_id}")
        ...     # Skip this artifact
    """

    def __init__(self, message: str, artifact_id: str):
        """Initialize artifact not found exception.

        Args:
            message: Human-readable error message
            artifact_id: The identifier of the missing artifact
        """
        super().__init__(message)
        self.artifact_id = artifact_id
