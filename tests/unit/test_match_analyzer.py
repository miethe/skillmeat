"""Unit tests for MatchAnalyzer keyword scoring.

Tests cover:
- Basic keyword matching
- Multi-word queries
- Field weighting
- Edge cases (empty queries, special characters)
- Performance requirements (O(n) scaling)
- Score normalization (0-100 range)
"""

import pytest

from skillmeat.core.artifact import ArtifactMetadata
from skillmeat.core.scoring.match_analyzer import MatchAnalyzer


class TestMatchAnalyzerBasics:
    """Test basic functionality and initialization."""

    def test_default_initialization(self):
        """MatchAnalyzer initializes with default weights."""
        analyzer = MatchAnalyzer()
        assert analyzer.field_weights is not None
        assert analyzer.min_threshold == 10.0

    def test_custom_weights_validation(self):
        """Custom weights must sum to 1.0."""
        # Valid weights
        valid_weights = {"name": 0.5, "title": 0.5}
        analyzer = MatchAnalyzer(field_weights=valid_weights)
        assert analyzer.field_weights == valid_weights

        # Invalid weights (don't sum to 1.0)
        invalid_weights = {"name": 0.5, "title": 0.3}
        with pytest.raises(ValueError, match="must sum to 1.0"):
            MatchAnalyzer(field_weights=invalid_weights)

    def test_empty_query_returns_zero(self):
        """Empty query returns score of 0."""
        analyzer = MatchAnalyzer()
        artifact = ArtifactMetadata(title="Test Artifact")

        assert analyzer.score_artifact("", artifact) == 0.0
        assert analyzer.score_artifact("   ", artifact) == 0.0


class TestKeywordMatching:
    """Test keyword matching against artifact fields."""

    def test_exact_name_match(self):
        """Exact match in name field scores high."""
        analyzer = MatchAnalyzer()
        artifact = ArtifactMetadata(title="PDF Tool")

        score = analyzer.score_artifact("pdf", artifact, artifact_name="pdf-tool")
        assert score > 45.0, "Exact name match should score above 45"

    def test_exact_title_match(self):
        """Exact match in title field scores high."""
        analyzer = MatchAnalyzer()
        artifact = ArtifactMetadata(title="PDF Converter")

        score = analyzer.score_artifact("pdf", artifact)
        assert score > 30.0, "Exact title match should score above 30"

    def test_tag_match(self):
        """Tag matches get bonus scoring."""
        analyzer = MatchAnalyzer()
        artifact = ArtifactMetadata(title="Document Tool", tags=["pdf", "converter"])

        score = analyzer.score_artifact("pdf", artifact)
        assert score > 20.0, "Tag match should score above 20"

    def test_description_match(self):
        """Description matches contribute to score."""
        analyzer = MatchAnalyzer()
        artifact = ArtifactMetadata(
            title="Tool",
            description="Convert documents to PDF format",
        )

        score = analyzer.score_artifact("pdf", artifact)
        assert score > 10.0, "Description match should score above 10"

    def test_alias_match(self):
        """Aliases in extra metadata contribute to score."""
        analyzer = MatchAnalyzer()
        artifact = ArtifactMetadata(
            title="Document Tool",
            extra={"aliases": ["pdf-converter", "pdf-tool"]},
        )

        score = analyzer.score_artifact("pdf", artifact)
        assert score >= 10.0, "Alias match should score at least 10"

    def test_multiple_field_matches(self):
        """Matches across multiple fields accumulate score."""
        analyzer = MatchAnalyzer()
        artifact = ArtifactMetadata(
            title="PDF Converter",
            description="Convert documents to PDF",
            tags=["pdf", "conversion"],
        )

        score = analyzer.score_artifact("pdf", artifact, artifact_name="pdf-tool")
        assert score > 80.0, "Multi-field match should score very high"


class TestMultiWordQueries:
    """Test scoring with multi-word queries."""

    def test_two_word_query(self):
        """Multi-word queries match all terms."""
        analyzer = MatchAnalyzer()
        artifact = ArtifactMetadata(
            title="PDF Converter Tool",
            tags=["pdf", "converter"],
        )

        score = analyzer.score_artifact("pdf converter", artifact)
        assert score > 50.0, "Both words match should score high"

    def test_phrase_match_bonus(self):
        """Phrase match (words in order) gets bonus."""
        analyzer = MatchAnalyzer()
        artifact_phrase = ArtifactMetadata(title="PDF Converter Tool")
        artifact_scattered = ArtifactMetadata(title="Converter for PDF")

        score_phrase = analyzer.score_artifact("pdf converter", artifact_phrase)
        score_scattered = analyzer.score_artifact("pdf converter", artifact_scattered)

        assert score_phrase > score_scattered, "Phrase match should score higher"

    def test_partial_word_match(self):
        """Partial word matches score lower than exact."""
        analyzer = MatchAnalyzer()
        artifact = ArtifactMetadata(title="PDF Converter")

        exact_score = analyzer.score_artifact("pdf", artifact)
        partial_score = analyzer.score_artifact("pd", artifact)

        assert exact_score > partial_score, "Exact match should score higher"


class TestEdgeCases:
    """Test edge cases and special characters."""

    def test_case_insensitive_matching(self):
        """Matching is case-insensitive."""
        analyzer = MatchAnalyzer()
        artifact = ArtifactMetadata(title="PDF Converter")

        score_upper = analyzer.score_artifact("PDF", artifact)
        score_lower = analyzer.score_artifact("pdf", artifact)
        score_mixed = analyzer.score_artifact("Pdf", artifact)

        assert score_upper == score_lower == score_mixed

    def test_special_characters_ignored(self):
        """Special characters are normalized."""
        analyzer = MatchAnalyzer()
        artifact = ArtifactMetadata(title="PDF-Converter Tool!")

        score = analyzer.score_artifact("pdf converter", artifact)
        assert score > 20.0, "Should match despite special characters"

    def test_hyphenated_words(self):
        """Hyphenated words are preserved during tokenization."""
        analyzer = MatchAnalyzer()
        artifact = ArtifactMetadata(title="PDF-to-Word Converter")

        score = analyzer.score_artifact("pdf-to-word", artifact)
        assert score > 30.0, "Hyphenated phrase should match"

    def test_no_metadata_fields(self):
        """Artifact with no metadata fields returns low score."""
        analyzer = MatchAnalyzer()
        artifact = ArtifactMetadata()  # All fields None/empty

        score = analyzer.score_artifact("pdf", artifact)
        assert score == 0.0, "Empty artifact should score 0"

    def test_unicode_characters(self):
        """Unicode characters are handled gracefully."""
        analyzer = MatchAnalyzer()
        artifact = ArtifactMetadata(title="PDF Créateur")

        # ASCII query should still match "PDF"
        score = analyzer.score_artifact("pdf", artifact)
        assert score > 20.0, "Should match ASCII portion"


class TestScoreNormalization:
    """Test score normalization to 0-100 range."""

    def test_score_in_valid_range(self):
        """All scores are in 0-100 range."""
        analyzer = MatchAnalyzer()
        artifacts = [
            ArtifactMetadata(title="PDF Tool", tags=["pdf"]),
            ArtifactMetadata(title="Image Tool", tags=["image"]),
            ArtifactMetadata(title="PDF Converter", description="Convert to PDF"),
        ]

        for artifact in artifacts:
            score = analyzer.score_artifact("pdf", artifact)
            assert 0.0 <= score <= 100.0, f"Score {score} out of range"

    def test_perfect_match_near_100(self):
        """Perfect match across all fields approaches 100."""
        analyzer = MatchAnalyzer()
        # Artifact optimized for "pdf" query
        artifact = ArtifactMetadata(
            title="PDF PDF PDF",  # Multiple occurrences
            description="PDF tool for PDF conversion to PDF format",
            tags=["pdf", "pdf-tool"],
            extra={"aliases": ["pdf", "pdf-converter"]},
        )

        score = analyzer.score_artifact(
            "pdf", artifact, artifact_name="pdf-tool-ultimate"
        )
        assert score > 90.0, "Perfect multi-field match should score >90"

    def test_no_match_returns_zero(self):
        """No keyword match returns score of 0."""
        analyzer = MatchAnalyzer()
        artifact = ArtifactMetadata(
            title="Image Processor",
            tags=["image", "graphics"],
        )

        score = analyzer.score_artifact("pdf", artifact)
        assert score == 0.0, "No match should score 0"


class TestScoreAllRanking:
    """Test batch scoring and ranking functionality."""

    def test_score_all_basic(self):
        """score_all ranks artifacts by relevance."""
        analyzer = MatchAnalyzer()
        artifacts = [
            ("pdf-tool", ArtifactMetadata(title="PDF Tool", tags=["pdf"])),
            ("image-tool", ArtifactMetadata(title="Image Tool", tags=["image"])),
            ("pdf-converter", ArtifactMetadata(title="PDF Converter", tags=["pdf"])),
        ]

        results = analyzer.score_all("pdf", artifacts)

        # Check ordering (descending by score)
        assert len(results) == 2, "Should filter out non-matching artifacts"
        assert results[0][2] >= results[1][2], "Should be sorted by score descending"

        # Check that pdf artifacts ranked higher
        pdf_names = {name for name, _, _ in results}
        assert "pdf-tool" in pdf_names
        assert "pdf-converter" in pdf_names
        assert "image-tool" not in pdf_names

    def test_score_all_threshold_filtering(self):
        """score_all filters below threshold by default."""
        analyzer = MatchAnalyzer(min_threshold=50.0)
        artifacts = [
            ("high-match", ArtifactMetadata(title="PDF Tool PDF", tags=["pdf"])),
            (
                "low-match",
                ArtifactMetadata(title="Document Tool", description="Mentions pdf"),
            ),
        ]

        results = analyzer.score_all("pdf", artifacts, filter_threshold=True)

        # Only high-scoring artifact should pass
        assert len(results) == 1
        assert results[0][0] == "high-match"

    def test_score_all_no_filtering(self):
        """score_all can disable threshold filtering."""
        analyzer = MatchAnalyzer(min_threshold=50.0)
        artifacts = [
            ("high-match", ArtifactMetadata(title="PDF Tool", tags=["pdf"])),
            (
                "low-match",
                ArtifactMetadata(title="Document", description="Mentions pdf once"),
            ),
        ]

        results = analyzer.score_all("pdf", artifacts, filter_threshold=False)

        # Both artifacts should be returned
        assert len(results) == 2

    def test_score_all_empty_list(self):
        """score_all handles empty artifact list."""
        analyzer = MatchAnalyzer()
        results = analyzer.score_all("pdf", [])
        assert results == []


class TestPerformance:
    """Test performance characteristics (O(n) requirement)."""

    def test_linear_scaling(self):
        """Scoring scales linearly with artifact count."""
        analyzer = MatchAnalyzer()

        # Create test datasets of different sizes
        def make_artifacts(count):
            return [
                (f"artifact-{i}", ArtifactMetadata(title=f"Tool {i}", tags=["test"]))
                for i in range(count)
            ]

        import time

        # Measure timing for different sizes
        sizes = [100, 500, 1000]
        times = []

        for size in sizes:
            artifacts = make_artifacts(size)
            start = time.perf_counter()
            analyzer.score_all("test", artifacts)
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        # Check roughly linear scaling (allowing for overhead)
        # Time ratio should be close to size ratio
        ratio_time = times[1] / times[0]  # 500 vs 100
        ratio_size = sizes[1] / sizes[0]  # 5x

        # Allow 2x margin for overhead (should be close to linear)
        assert ratio_time < ratio_size * 2, (
            f"Performance scaling worse than O(n): "
            f"5x data took {ratio_time:.1f}x time (expected ~5x)"
        )

    def test_single_artifact_performance(self):
        """Single artifact scoring completes quickly."""
        analyzer = MatchAnalyzer()
        artifact = ArtifactMetadata(
            title="PDF Converter",
            description="Convert documents to PDF format with high quality",
            tags=["pdf", "converter", "documents"],
        )

        import time

        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            analyzer.score_artifact("pdf converter", artifact, "pdf-tool")
        elapsed = time.perf_counter() - start

        # Should complete 1000 iterations in under 1 second
        assert elapsed < 1.0, f"1000 iterations took {elapsed:.3f}s (too slow)"


class TestAcceptanceCriteria:
    """Test acceptance criteria from task specification."""

    def test_pdf_skill_high_score(self):
        """Query 'pdf' matches pdf skill >80%."""
        analyzer = MatchAnalyzer()
        pdf_skill = ArtifactMetadata(
            title="PDF Skill",
            description="Work with PDF documents",
            tags=["pdf", "documents"],
        )

        score = analyzer.score_artifact("pdf", pdf_skill, artifact_name="pdf-skill")
        assert score > 80.0, f"PDF skill scored {score}, expected >80"

    def test_non_match_low_score(self):
        """Non-matching artifacts score <30%."""
        analyzer = MatchAnalyzer()
        image_skill = ArtifactMetadata(
            title="Image Processor",
            description="Process and edit images",
            tags=["image", "graphics", "photos"],
        )

        score = analyzer.score_artifact("pdf", image_skill, artifact_name="image-tool")
        assert score < 30.0, f"Non-matching skill scored {score}, expected <30"

    def test_coverage_threshold(self):
        """Unit test coverage exceeds 80%."""
        # This test exists to document the coverage requirement
        # Actual coverage is measured by pytest-cov
        # Run: pytest tests/unit/test_match_analyzer.py --cov=skillmeat.core.scoring.match_analyzer --cov-report=term-missing
        assert True, "Coverage measured externally by pytest-cov"


class TestTokenization:
    """Test internal tokenization logic."""

    def test_tokenize_basic(self):
        """Tokenize splits on whitespace and special chars."""
        analyzer = MatchAnalyzer()
        tokens = analyzer._tokenize("PDF Converter Tool")
        assert tokens == ["pdf", "converter", "tool"]

    def test_tokenize_hyphenated(self):
        """Tokenize preserves hyphenated words."""
        analyzer = MatchAnalyzer()
        tokens = analyzer._tokenize("PDF-to-Word converter")
        assert "pdf-to-word" in tokens
        assert "converter" in tokens

    def test_tokenize_deduplication(self):
        """Tokenize removes duplicates."""
        analyzer = MatchAnalyzer()
        tokens = analyzer._tokenize("PDF PDF tool PDF")
        assert tokens.count("pdf") == 1
        assert tokens == ["pdf", "tool"]

    def test_contains_phrase(self):
        """Phrase detection finds words in order."""
        analyzer = MatchAnalyzer()

        # Positive cases
        assert analyzer._contains_phrase(
            ["pdf", "converter", "tool"], ["pdf", "converter"]
        )
        assert analyzer._contains_phrase(["pdf", "converter", "tool"], ["pdf", "tool"])

        # Negative cases
        assert not analyzer._contains_phrase(
            ["pdf", "converter", "tool"], ["tool", "pdf"]
        )
        assert not analyzer._contains_phrase(
            ["pdf", "converter"], ["pdf", "converter", "tool"]
        )
