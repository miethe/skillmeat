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
from typing import List, Optional, Tuple

from skillmeat.core.artifact import ArtifactMetadata
from skillmeat.core.similarity import ScoreBreakdown
from skillmeat.models import ArtifactFingerprint


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

    def compare(
        self,
        artifact_a: ArtifactFingerprint,
        artifact_b: ArtifactFingerprint,
    ) -> ScoreBreakdown:
        """Compare two artifacts and return a per-component score breakdown.

        Computes four independent similarity dimensions and returns them in a
        ``ScoreBreakdown``.  ``semantic_score`` is always ``None`` — that
        component is owned by ``SemanticScorer`` and filled in downstream.

        Score components
        ----------------
        keyword_score
            Symmetric TF-IDF keyword similarity: both artifacts' combined text
            (name + title + tags + description) is scored against the other's
            fields using the existing ``_score_field`` pipeline.  The two
            directional scores are averaged and normalised to [0, 1].

        content_score
            Hash-based content similarity.  Exact ``content_hash`` match → 1.0.
            Otherwise a size-ratio proxy captures partial overlap:
            ``min(size_a, size_b) / max(size_a, size_b)`` scaled by 0.5 as an
            upper bound when hashes differ.

        structure_score
            Hash-based structural similarity.  Exact ``structure_hash`` → 1.0.
            Otherwise the file-count ratio provides a structural approximation
            (``min / max``), scaled by 0.6 as the upper bound.

        metadata_score
            Weighted combination of:
            - Tag Jaccard similarity (50 %)
            - Artifact-type match (25 %)
            - Title token overlap / Jaccard (15 %)
            - Description length ratio (10 %)

        Args:
            artifact_a: First artifact fingerprint.
            artifact_b: Second artifact fingerprint.

        Returns:
            ``ScoreBreakdown`` with all fields populated except
            ``semantic_score`` (which is ``None``).

        Example:
            >>> from skillmeat.models import ArtifactFingerprint
            >>> from pathlib import Path
            >>> a = ArtifactFingerprint(
            ...     artifact_path=Path("/a"), artifact_name="canvas",
            ...     artifact_type="skill", content_hash="abc", metadata_hash="x",
            ...     structure_hash="s1", title="Canvas Design", tags=["design"],
            ...     file_count=3, total_size=1024,
            ... )
            >>> b = ArtifactFingerprint(
            ...     artifact_path=Path("/b"), artifact_name="canvas-v2",
            ...     artifact_type="skill", content_hash="abc", metadata_hash="x",
            ...     structure_hash="s1", title="Canvas Design V2", tags=["design"],
            ...     file_count=3, total_size=1024,
            ... )
            >>> analyzer = MatchAnalyzer()
            >>> breakdown = analyzer.compare(a, b)
            >>> assert 0.0 <= breakdown.keyword_score <= 1.0
            >>> assert breakdown.content_score == 1.0  # identical content hash
            >>> assert breakdown.semantic_score is None
        """
        return ScoreBreakdown(
            keyword_score=self._compute_keyword_score(artifact_a, artifact_b),
            content_score=self._compute_content_score(artifact_a, artifact_b),
            structure_score=self._compute_structure_score(artifact_a, artifact_b),
            metadata_score=self._compute_metadata_score(artifact_a, artifact_b),
            semantic_score=None,
        )

    # ------------------------------------------------------------------
    # Private helpers for compare()
    # ------------------------------------------------------------------

    def _artifact_combined_text(self, artifact: ArtifactFingerprint) -> str:
        """Return all text fields of a fingerprint joined as a single string.

        Args:
            artifact: Artifact fingerprint whose text fields are combined.

        Returns:
            Space-joined string of name, title, tags, and description.
        """
        parts = [artifact.artifact_name]
        if artifact.title:
            parts.append(artifact.title)
        if artifact.tags:
            parts.extend(artifact.tags)
        if artifact.description:
            parts.append(artifact.description)
        return " ".join(parts)

    def _compute_keyword_score(
        self,
        artifact_a: ArtifactFingerprint,
        artifact_b: ArtifactFingerprint,
    ) -> float:
        """Compute symmetric TF-IDF keyword similarity in [0, 1].

        Each artifact's combined text is used as the "query" against the
        other's individual fields.  The raw field-weighted score from
        ``score_artifact`` lives in [0, 100]; dividing by 100 and averaging
        the two directional scores yields a symmetric score in [0, 1].

        Args:
            artifact_a: First artifact fingerprint.
            artifact_b: Second artifact fingerprint.

        Returns:
            Keyword similarity score from 0.0 to 1.0.
        """
        # Build lightweight ArtifactMetadata proxies from fingerprints so we
        # can reuse the existing score_artifact() pipeline without duplication.
        meta_a = ArtifactMetadata(
            title=artifact_a.title or "",
            description=artifact_a.description or "",
            tags=list(artifact_a.tags),
        )
        meta_b = ArtifactMetadata(
            title=artifact_b.title or "",
            description=artifact_b.description or "",
            tags=list(artifact_b.tags),
        )

        query_from_a = self._artifact_combined_text(artifact_a)
        query_from_b = self._artifact_combined_text(artifact_b)

        # Score A's text against B's fields, and B's text against A's fields.
        score_a_vs_b = self.score_artifact(query_from_a, meta_b, artifact_b.artifact_name)
        score_b_vs_a = self.score_artifact(query_from_b, meta_a, artifact_a.artifact_name)

        # Average directional scores; score_artifact returns [0, 100].
        avg_raw = (score_a_vs_b + score_b_vs_a) / 2.0
        return min(1.0, max(0.0, avg_raw / 100.0))

    def _compute_content_score(
        self,
        artifact_a: ArtifactFingerprint,
        artifact_b: ArtifactFingerprint,
    ) -> float:
        """Compute content similarity in [0, 1] using hash + size proxy.

        Args:
            artifact_a: First artifact fingerprint.
            artifact_b: Second artifact fingerprint.

        Returns:
            Content similarity score from 0.0 to 1.0.
        """
        if artifact_a.content_hash == artifact_b.content_hash:
            return 1.0

        # Size-ratio proxy: max 0.5 when hashes differ (partial overlap).
        if artifact_a.total_size > 0 and artifact_b.total_size > 0:
            size_ratio = min(artifact_a.total_size, artifact_b.total_size) / max(
                artifact_a.total_size, artifact_b.total_size
            )
            return min(1.0, max(0.0, size_ratio * 0.5))

        return 0.0

    def _compute_structure_score(
        self,
        artifact_a: ArtifactFingerprint,
        artifact_b: ArtifactFingerprint,
    ) -> float:
        """Compute structural similarity in [0, 1] using hash + file-count proxy.

        Args:
            artifact_a: First artifact fingerprint.
            artifact_b: Second artifact fingerprint.

        Returns:
            Structure similarity score from 0.0 to 1.0.
        """
        if artifact_a.structure_hash == artifact_b.structure_hash:
            return 1.0

        # File-count ratio proxy: max 0.6 when hashes differ.
        if artifact_a.file_count > 0 and artifact_b.file_count > 0:
            count_ratio = min(artifact_a.file_count, artifact_b.file_count) / max(
                artifact_a.file_count, artifact_b.file_count
            )
            return min(1.0, max(0.0, count_ratio * 0.6))

        return 0.0

    def _compute_metadata_score(
        self,
        artifact_a: ArtifactFingerprint,
        artifact_b: ArtifactFingerprint,
    ) -> float:
        """Compute metadata similarity in [0, 1].

        Weighted combination:
        - Tag Jaccard similarity        50 %
        - Artifact-type match           25 %
        - Title token Jaccard           15 %
        - Description length ratio      10 %

        Args:
            artifact_a: First artifact fingerprint.
            artifact_b: Second artifact fingerprint.

        Returns:
            Metadata similarity score from 0.0 to 1.0.
        """
        score = 0.0

        # Tag Jaccard (50 %)
        tags_a = set(t.lower() for t in artifact_a.tags) if artifact_a.tags else set()
        tags_b = set(t.lower() for t in artifact_b.tags) if artifact_b.tags else set()
        if tags_a or tags_b:
            union = tags_a | tags_b
            jaccard = len(tags_a & tags_b) / len(union) if union else 0.0
            score += jaccard * 0.50
        # If both are empty, contribute 0 — no information either way.

        # Artifact-type match (25 %)
        if artifact_a.artifact_type and artifact_b.artifact_type:
            if artifact_a.artifact_type.lower() == artifact_b.artifact_type.lower():
                score += 0.25

        # Title token Jaccard (15 %)
        title_a = set(self._tokenize(artifact_a.title or ""))
        title_b = set(self._tokenize(artifact_b.title or ""))
        if title_a or title_b:
            union_t = title_a | title_b
            title_jaccard = len(title_a & title_b) / len(union_t) if union_t else 0.0
            score += title_jaccard * 0.15

        # Description length ratio (10 %)
        len_a = len(artifact_a.description or "")
        len_b = len(artifact_b.description or "")
        if len_a > 0 and len_b > 0:
            desc_ratio = min(len_a, len_b) / max(len_a, len_b)
            score += desc_ratio * 0.10

        return min(1.0, max(0.0, score))

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
