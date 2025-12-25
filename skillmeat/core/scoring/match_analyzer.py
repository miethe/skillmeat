"""Keyword-based match scoring for artifacts.

Scores artifacts based on query keyword matches against artifact metadata fields
(name, title, description, tags, aliases). Uses TF-IDF-inspired scoring to handle
multi-word queries and provides normalized scores in 0-100 range.

Example:
    >>> analyzer = MatchAnalyzer()
    >>> artifacts = [...]  # List of ArtifactMetadata instances
    >>> results = analyzer.score_all("pdf converter", artifacts)
    >>> for artifact, score in results[:5]:
    ...     print(f"{artifact.title}: {score:.1f}")
"""

import re
from collections import Counter
from typing import List, Tuple

from skillmeat.core.artifact import ArtifactMetadata


# Field weights for scoring (must sum to 1.0)
FIELD_WEIGHTS = {
    "name": 0.30,  # Primary identifier
    "title": 0.25,  # Display name
    "tags": 0.20,  # Explicit categorization
    "description": 0.15,  # Detailed description
    "extra_aliases": 0.10,  # Alternative names from metadata.extra
}

# Minimum score threshold for relevance (0-100)
MIN_RELEVANCE_THRESHOLD = 10.0


class MatchAnalyzer:
    """Keyword-based match scoring for artifacts.

    Uses weighted field matching with TF-IDF-inspired term frequency scoring
    to rank artifacts by relevance to a query string.

    Attributes:
        field_weights: Dict mapping field names to score weights
        min_threshold: Minimum score for relevance filtering
    """

    def __init__(
        self,
        field_weights: dict[str, float] | None = None,
        min_threshold: float = MIN_RELEVANCE_THRESHOLD,
    ):
        """Initialize match analyzer with optional custom weights.

        Args:
            field_weights: Custom field weights (must sum to 1.0)
            min_threshold: Minimum score threshold (0-100)

        Raises:
            ValueError: If field_weights don't sum to approximately 1.0
        """
        self.field_weights = field_weights or FIELD_WEIGHTS
        self.min_threshold = min_threshold

        # Validate weights sum to ~1.0
        weight_sum = sum(self.field_weights.values())
        if not 0.99 <= weight_sum <= 1.01:
            raise ValueError(
                f"Field weights must sum to 1.0, got {weight_sum:.3f}. "
                f"Weights: {self.field_weights}"
            )

    def score_artifact(
        self, query: str, artifact: ArtifactMetadata, artifact_name: str = ""
    ) -> float:
        """Score single artifact against query.

        Args:
            query: Search query string
            artifact: ArtifactMetadata instance to score
            artifact_name: Artifact name (since ArtifactMetadata doesn't store it)

        Returns:
            Match score from 0-100

        Example:
            >>> analyzer = MatchAnalyzer()
            >>> artifact = ArtifactMetadata(
            ...     title="PDF Converter",
            ...     description="Convert documents to PDF",
            ...     tags=["pdf", "conversion"],
            ... )
            >>> score = analyzer.score_artifact("pdf", artifact, "pdf-converter")
            >>> assert score > 80  # High match for direct keyword
        """
        # Normalize and tokenize query
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return 0.0

        # Extract and score each field
        field_scores = {}

        # Name field
        name_text = artifact_name or ""
        field_scores["name"] = self._score_field(query_tokens, name_text)

        # Title field
        title_text = artifact.title or ""
        field_scores["title"] = self._score_field(query_tokens, title_text)

        # Tags field (exact match bonus)
        tags_text = " ".join(artifact.tags) if artifact.tags else ""
        field_scores["tags"] = self._score_field(
            query_tokens, tags_text, exact_match_bonus=True
        )

        # Description field
        desc_text = artifact.description or ""
        field_scores["description"] = self._score_field(query_tokens, desc_text)

        # Extra aliases from metadata.extra
        aliases = artifact.extra.get("aliases", []) if artifact.extra else []
        aliases_text = " ".join(aliases) if aliases else ""
        field_scores["extra_aliases"] = self._score_field(
            query_tokens, aliases_text, exact_match_bonus=True
        )

        # Calculate weighted total
        total_score = sum(
            field_scores.get(field, 0.0) * weight
            for field, weight in self.field_weights.items()
        )

        # Normalize to 0-100 range
        return min(100.0, max(0.0, total_score))

    def score_all(
        self,
        query: str,
        artifacts: List[Tuple[str, ArtifactMetadata]],
        filter_threshold: bool = True,
    ) -> List[Tuple[str, ArtifactMetadata, float]]:
        """Score and rank all artifacts by relevance.

        Args:
            query: Search query string
            artifacts: List of (name, ArtifactMetadata) tuples
            filter_threshold: If True, filter out scores below min_threshold

        Returns:
            List of (name, artifact, score) tuples sorted by descending score

        Example:
            >>> analyzer = MatchAnalyzer()
            >>> artifacts = [
            ...     ("pdf-tool", ArtifactMetadata(title="PDF Tool", tags=["pdf"])),
            ...     ("image-tool", ArtifactMetadata(title="Image Tool", tags=["image"])),
            ... ]
            >>> results = analyzer.score_all("pdf", artifacts)
            >>> assert results[0][2] > results[1][2]  # pdf-tool ranks higher
        """
        scored = []
        for name, artifact in artifacts:
            score = self.score_artifact(query, artifact, artifact_name=name)

            # Apply threshold filter if enabled
            if filter_threshold and score < self.min_threshold:
                continue

            scored.append((name, artifact, score))

        # Sort by score descending
        scored.sort(key=lambda x: x[2], reverse=True)
        return scored

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into normalized terms.

        Args:
            text: Input text to tokenize

        Returns:
            List of lowercase alphanumeric tokens

        Example:
            >>> analyzer = MatchAnalyzer()
            >>> analyzer._tokenize("PDF-Converter Tool!")
            ['pdf', 'converter', 'tool']
        """
        if not text:
            return []

        # Convert to lowercase
        text = text.lower()

        # Split on non-alphanumeric characters (keeps hyphens in words)
        # Pattern: split on whitespace and special chars, but preserve hyphenated words
        tokens = re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text)

        # Remove empty strings and duplicates while preserving order
        seen = set()
        result = []
        for token in tokens:
            if token and token not in seen:
                seen.add(token)
                result.append(token)

        return result

    def _score_field(
        self, query_tokens: List[str], field_text: str, exact_match_bonus: bool = False
    ) -> float:
        """Score a single field against query tokens.

        Returns raw score that will be weighted by field importance.
        Scoring is generous to account for field weights (0.15-0.30):
        - Exact token match: +100 points per occurrence (capped at 3)
        - Partial token match (substring): +50 points per occurrence
        - Exact phrase match (all tokens in order): +60 points
        - Exact tag/alias match: +80 points bonus

        Args:
            query_tokens: Normalized query tokens
            field_text: Field text to score
            exact_match_bonus: If True, give bonus for exact tag/alias matches

        Returns:
            Field score (will be weighted by field weight and capped at 100)

        Example:
            >>> analyzer = MatchAnalyzer()
            >>> tokens = ["pdf", "converter"]
            >>> score = analyzer._score_field(tokens, "PDF Converter Tool")
            >>> assert score > 100.0  # Raw score before weighting
        """
        if not field_text:
            return 0.0

        # Tokenize field text
        field_tokens = self._tokenize(field_text)
        if not field_tokens:
            return 0.0

        # Count term frequencies
        field_token_counts = Counter(field_tokens)

        score = 0.0

        # Exact token matches (with TF weighting)
        for query_token in query_tokens:
            if query_token in field_token_counts:
                # Add 130 points per exact match, capped at 3 occurrences
                exact_matches = field_token_counts[query_token]
                score += 130.0 * min(exact_matches, 3)

        # Partial token matches (substring matching)
        for query_token in query_tokens:
            for field_token in field_tokens:
                if query_token in field_token and query_token != field_token:
                    # Partial match: 50 points (e.g., "pdf" in "pdf-converter")
                    score += 50.0

        # Exact match bonus for tags/aliases
        if exact_match_bonus:
            # Check if any field token exactly matches any query token
            if any(token in query_tokens for token in field_tokens):
                score += 80.0  # Bonus for exact tag match

        # Phrase match bonus (all query tokens appear in order)
        if len(query_tokens) > 1 and self._contains_phrase(field_tokens, query_tokens):
            score += 60.0  # Bonus for phrase match

        return score

    def _contains_phrase(
        self, field_tokens: List[str], query_tokens: List[str]
    ) -> bool:
        """Check if field contains all query tokens in order (allowing gaps).

        Args:
            field_tokens: Tokenized field text
            query_tokens: Tokenized query

        Returns:
            True if all query tokens appear in field_tokens in order

        Example:
            >>> analyzer = MatchAnalyzer()
            >>> field = ["pdf", "converter", "tool"]
            >>> query = ["pdf", "tool"]
            >>> analyzer._contains_phrase(field, query)
            True
            >>> query2 = ["tool", "pdf"]
            >>> analyzer._contains_phrase(field, query2)
            False
        """
        if not query_tokens or not field_tokens:
            return False

        # Find positions of query tokens in field
        positions = []
        for q_token in query_tokens:
            try:
                # Find first occurrence after last found position
                start_idx = positions[-1] + 1 if positions else 0
                idx = field_tokens.index(q_token, start_idx)
                positions.append(idx)
            except (ValueError, IndexError):
                # Token not found in order
                return False

        return True
