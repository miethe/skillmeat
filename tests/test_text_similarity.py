"""Unit tests for skillmeat.core.scoring.text_similarity.

Tests cover:
- bigram_similarity: identical inputs, empty inputs, partial overlap, hyphen/underscore
  variants, completely different strings, single-character inputs (no bigrams).
- bm25_description_similarity: identical descriptions, empty inputs, related vs
  unrelated descriptions, all-stop-word descriptions, shared domain terms.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Circular-import guard
# ---------------------------------------------------------------------------
# skillmeat.core.scoring.__init__ pulls in quality_scorer → rating_store →
# cache.models → cache.marketplace → api.__init__ which completes the cycle.
# Pre-stubbing these modules before any skillmeat.core.scoring.* import avoids
# the circular ImportError without touching production code.
import sys
from unittest.mock import MagicMock as _MagicMock

for _mod in (
    "skillmeat.storage.rating_store",
    "skillmeat.cache.marketplace",
):
    if _mod not in sys.modules:
        sys.modules[_mod] = _MagicMock()

import pytest

from skillmeat.core.scoring.text_similarity import (
    bigram_similarity,
    bm25_description_similarity,
)


# ---------------------------------------------------------------------------
# bigram_similarity
# ---------------------------------------------------------------------------


class TestBigramSimilarity:
    """Tests for bigram_similarity(a, b)."""

    def test_identical_inputs_return_one(self) -> None:
        assert bigram_similarity("canvas-design", "canvas-design") == 1.0

    def test_identical_after_normalisation_return_one(self) -> None:
        # Lowercase normalisation
        assert bigram_similarity("CanvasDesign", "canvasdesign") == 1.0

    def test_empty_first_arg_returns_zero(self) -> None:
        assert bigram_similarity("", "canvas") == 0.0

    def test_empty_second_arg_returns_zero(self) -> None:
        assert bigram_similarity("canvas", "") == 0.0

    def test_both_empty_returns_zero(self) -> None:
        assert bigram_similarity("", "") == 0.0

    def test_single_char_first_arg_returns_zero(self) -> None:
        # Single character → no bigrams possible
        assert bigram_similarity("x", "canvas") == 0.0

    def test_single_char_second_arg_returns_zero(self) -> None:
        assert bigram_similarity("canvas", "y") == 0.0

    def test_both_single_char_returns_zero(self) -> None:
        assert bigram_similarity("a", "b") == 0.0

    def test_hyphen_underscore_variants_score_one(self) -> None:
        # Hyphens and underscores are stripped before comparison.
        assert bigram_similarity("canvas-design", "canvas_design") == 1.0

    def test_underscore_vs_no_separator(self) -> None:
        # "canvas_design" → "canvasdesign"; "canvasdesign" → same.
        assert bigram_similarity("canvas_design", "canvasdesign") == 1.0

    def test_partial_overlap_between_zero_and_one(self) -> None:
        score = bigram_similarity("canvas", "canvas-editor")
        assert 0.0 < score < 1.0

    def test_partial_overlap_expected_value(self) -> None:
        # "canvas" → "canvas"; "canvas-editor" → "canvaseditor" after normalisation.
        # Bigrams of "canvas": {ca, an, nv, va, as} (5 bigrams)
        # Bigrams of "canvaseditor": {ca, an, nv, va, as, se, ed, di, it, to, or} (11 bigrams)
        # Intersection: {ca, an, nv, va, as} = 5; union = 11; Jaccard ≈ 5/11 ≈ 0.4545
        score = bigram_similarity("canvas", "canvas-editor")
        assert abs(score - 5 / 11) < 1e-6

    def test_completely_different_strings_score_low(self) -> None:
        score = bigram_similarity("abcdefgh", "rstuvwxyz")
        assert score < 0.2

    def test_completely_different_short_strings_score_zero(self) -> None:
        # "ab" bigrams: {"ab"}; "cd" bigrams: {"cd"} → intersection 0, union 2 → 0.
        score = bigram_similarity("ab", "cd")
        assert score == 0.0

    def test_score_is_symmetric(self) -> None:
        a, b = "pdf-converter", "pdf-transform"
        assert bigram_similarity(a, b) == pytest.approx(bigram_similarity(b, a))

    def test_score_in_valid_range(self) -> None:
        score = bigram_similarity("document-reader", "document-writer")
        assert 0.0 <= score <= 1.0

    def test_prefix_match_scores_high(self) -> None:
        # Sharing a long common prefix produces many shared bigrams.
        score = bigram_similarity("code-review", "code-reviewer")
        assert score > 0.7


# ---------------------------------------------------------------------------
# bm25_description_similarity
# ---------------------------------------------------------------------------


class TestBm25DescriptionSimilarity:
    """Tests for bm25_description_similarity(desc_a, desc_b)."""

    def test_identical_descriptions_return_one(self) -> None:
        desc = "Converts PDF documents to structured markdown output for editing"
        assert bm25_description_similarity(desc, desc) == 1.0

    def test_empty_first_arg_returns_zero(self) -> None:
        assert bm25_description_similarity("", "some description") == 0.0

    def test_empty_second_arg_returns_zero(self) -> None:
        assert bm25_description_similarity("some description", "") == 0.0

    def test_both_empty_returns_zero(self) -> None:
        assert bm25_description_similarity("", "") == 0.0

    def test_all_stop_words_returns_zero(self) -> None:
        # After stop-word filtering both documents are empty → 0.
        assert bm25_description_similarity("the a is", "a the is") == 0.0

    def test_all_domain_stop_words_returns_zero(self) -> None:
        # Domain stop words: "skill", "tool", "agent", "command", "hook", "mcp", "server"
        assert bm25_description_similarity("skill tool command", "agent hook mcp server") == 0.0

    def test_related_descriptions_score_higher_than_unrelated(self) -> None:
        desc_a = "Analyse Python code and report linting errors and type violations"
        desc_related = "Inspect Python source files for lint and type checking issues"
        desc_unrelated = "Download satellite imagery and render geographic map tiles"

        score_related = bm25_description_similarity(desc_a, desc_related)
        score_unrelated = bm25_description_similarity(desc_a, desc_unrelated)
        assert score_related > score_unrelated

    def test_shared_domain_terms_score_above_zero(self) -> None:
        desc_a = "Generate interactive canvas diagrams for design prototyping"
        desc_b = "Render canvas-based visual diagrams with editing support"
        score = bm25_description_similarity(desc_a, desc_b)
        assert score > 0.0

    def test_no_shared_content_words_score_zero(self) -> None:
        desc_a = "Convert markdown documents to formatted PDF reports"
        desc_b = "Schedule automated backups for database clusters"
        score = bm25_description_similarity(desc_a, desc_b)
        # No overlapping non-stop words → BM25 raw score is 0.
        assert score == 0.0

    def test_score_in_valid_range(self) -> None:
        desc_a = "Analyse repository structure and generate dependency graphs"
        desc_b = "Parse codebase layout and produce dependency visualisations"
        score = bm25_description_similarity(desc_a, desc_b)
        assert 0.0 <= score <= 1.0

    def test_high_similarity_for_paraphrased_descriptions(self) -> None:
        desc_a = "Search code repositories for security vulnerabilities and report findings"
        desc_b = "Scan code repositories for security issues and produce vulnerability reports"
        score = bm25_description_similarity(desc_a, desc_b)
        # Shared non-stop tokens: "code", "repositories", "security" — partial overlap → > 0.25
        assert score > 0.25

    def test_partial_word_overlap_produces_intermediate_score(self) -> None:
        desc_a = "Convert PDF files to markdown format with table extraction"
        desc_b = "Convert image files to PNG format with colour correction"
        # "convert", "files", "format" overlap but "pdf", "markdown", "table" do not.
        score = bm25_description_similarity(desc_a, desc_b)
        assert 0.0 < score < 1.0

    def test_single_token_match_scores_above_zero(self) -> None:
        # Only one meaningful shared token after stop-word removal.
        desc_a = "Analyse Python imports"
        desc_b = "Inspect Python dependencies"
        score = bm25_description_similarity(desc_a, desc_b)
        assert score > 0.0
