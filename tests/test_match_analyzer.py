"""Unit tests for MatchAnalyzer._compute_metadata_score() and related scoring.

Tests cover:
- Relative ranking with rebalanced weights (tags 30%, type 15%, title bigram 25%,
  description BM25 25%, length sanity 5%).
- Same description + different name: metadata >= 0.6.
- Same name + different description: metadata >= 0.4.
- Completely different artifacts score low (< 0.3).
- Identical fingerprints score near 1.0.
- Individual component contributions are within expected ranges.
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

from pathlib import Path

import pytest

from skillmeat.core.scoring.match_analyzer import MatchAnalyzer
from skillmeat.models import ArtifactFingerprint


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def _make_fingerprint(
    name: str = "my-artifact",
    artifact_type: str = "skill",
    title: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    content_hash: str = "hash-a",
    structure_hash: str = "struct-a",
    metadata_hash: str = "meta-a",
    file_count: int = 3,
    total_size: int = 1024,
) -> ArtifactFingerprint:
    """Return an ArtifactFingerprint with sensible defaults."""
    return ArtifactFingerprint(
        artifact_path=Path(f"/collection/{name}"),
        artifact_name=name,
        artifact_type=artifact_type,
        content_hash=content_hash,
        metadata_hash=metadata_hash,
        structure_hash=structure_hash,
        title=title,
        description=description,
        tags=tags or [],
        file_count=file_count,
        total_size=total_size,
    )


# ---------------------------------------------------------------------------
# _compute_metadata_score — component isolation
# ---------------------------------------------------------------------------


class TestComputeMetadataScoreComponents:
    """Verify individual weight contributions produce expected sub-scores."""

    def setup_method(self) -> None:
        self.analyzer = MatchAnalyzer()

    def test_identical_fingerprints_score_near_one(self) -> None:
        fp = _make_fingerprint(
            name="canvas-design",
            artifact_type="skill",
            title="Canvas Design",
            description="Render interactive canvas diagrams for design prototyping workflows",
            tags=["canvas", "design", "diagram"],
        )
        score = self.analyzer._compute_metadata_score(fp, fp)
        # Identical → all components at maximum; tags jaccard=1, type=1, bigram=1,
        # bm25=1, length ratio=1 → theoretical max = 0.30+0.15+0.25+0.25+0.05 = 1.0
        assert score == pytest.approx(1.0, abs=1e-6)

    def test_type_mismatch_reduces_score(self) -> None:
        fp_a = _make_fingerprint(artifact_type="skill", name="linter", title="Linter")
        fp_b = _make_fingerprint(artifact_type="command", name="linter", title="Linter")
        score = self.analyzer._compute_metadata_score(fp_a, fp_b)
        # Type contributes 15%; mismatch loses that contribution.
        # Without type score the max from name match (bigram=1.0 → 0.25) only.
        # Score should be less than if types matched.
        score_same_type = self.analyzer._compute_metadata_score(fp_a, fp_a)
        assert score < score_same_type

    def test_tag_overlap_contributes_to_score(self) -> None:
        fp_a = _make_fingerprint(tags=["python", "linting", "static-analysis"])
        fp_b = _make_fingerprint(tags=["python", "linting", "formatting"])
        fp_no_overlap = _make_fingerprint(tags=["canvas", "design", "diagram"])

        score_overlap = self.analyzer._compute_metadata_score(fp_a, fp_b)
        score_no_overlap = self.analyzer._compute_metadata_score(fp_a, fp_no_overlap)
        assert score_overlap > score_no_overlap

    def test_empty_tags_contribute_zero(self) -> None:
        fp_a = _make_fingerprint(tags=[], name="tool-a", title="Tool A")
        fp_b = _make_fingerprint(tags=[], name="tool-b", title="Tool B")
        score = self.analyzer._compute_metadata_score(fp_a, fp_b)
        # Tags contribute 0; score must still be in valid range.
        assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# _compute_metadata_score — relative ranking scenarios
# ---------------------------------------------------------------------------


class TestComputeMetadataScoreRankings:
    """Verify rebalanced weights produce correct relative rankings."""

    def setup_method(self) -> None:
        self.analyzer = MatchAnalyzer()

    def test_same_description_different_name_scores_at_least_point_six(self) -> None:
        """Description BM25 (25%) + type (15%) + length sanity (5%) + partial name
        coverage should push metadata to >= 0.6 when descriptions are identical."""
        shared_desc = (
            "Analyse Python source files for linting errors, style violations, "
            "and type annotation issues using static analysis techniques"
        )
        fp_a = _make_fingerprint(
            name="py-linter",
            artifact_type="skill",
            title="Python Linter",
            description=shared_desc,
            tags=["python", "linting"],
        )
        fp_b = _make_fingerprint(
            name="code-checker",
            artifact_type="skill",
            title="Code Checker",
            description=shared_desc,
            tags=["python", "linting"],
        )
        score = self.analyzer._compute_metadata_score(fp_a, fp_b)
        assert score >= 0.6, f"Expected >= 0.6 for same description, got {score:.4f}"

    def test_same_name_different_description_scores_at_least_point_four(self) -> None:
        """Title bigram (25%) + type (15%) drives score >= 0.4 for identical names
        even when descriptions diverge completely."""
        fp_a = _make_fingerprint(
            name="canvas-design",
            artifact_type="skill",
            title="Canvas Design",
            description="Render interactive canvas diagrams for prototyping and mockups",
            tags=["canvas"],
        )
        fp_b = _make_fingerprint(
            name="canvas-design",
            artifact_type="skill",
            title="Canvas Design",
            description="Schedule automated database backup jobs and restore procedures",
            tags=["database"],
        )
        score = self.analyzer._compute_metadata_score(fp_a, fp_b)
        assert score >= 0.4, f"Expected >= 0.4 for same name, got {score:.4f}"

    def test_completely_different_artifacts_score_below_point_three(self) -> None:
        """Unrelated name, type mismatch, no shared tags, and unrelated descriptions
        should all contribute near-zero → total score < 0.3."""
        fp_a = _make_fingerprint(
            name="pdf-converter",
            artifact_type="skill",
            title="PDF Converter",
            description="Convert Word documents to PDF format preserving formatting and layout",
            tags=["pdf", "documents", "conversion"],
        )
        fp_b = _make_fingerprint(
            name="k8s-monitor",
            artifact_type="agent",
            title="Kubernetes Monitor",
            description="Watch pod health metrics and alert on cluster resource exhaustion",
            tags=["kubernetes", "monitoring", "devops"],
        )
        score = self.analyzer._compute_metadata_score(fp_a, fp_b)
        assert score < 0.3, f"Expected < 0.3 for completely different artifacts, got {score:.4f}"

    def test_same_name_same_description_ranks_above_same_name_only(self) -> None:
        """Pair with matching description should rank higher than pair with name only."""
        shared_name = "document-parser"
        shared_desc = "Parse structured documents and extract metadata fields for indexing"

        fp_base = _make_fingerprint(
            name=shared_name,
            artifact_type="skill",
            title="Document Parser",
            description=shared_desc,
            tags=["parsing"],
        )
        fp_same_desc = _make_fingerprint(
            name=shared_name,
            artifact_type="skill",
            title="Document Parser",
            description=shared_desc,
            tags=["parsing"],
        )
        fp_diff_desc = _make_fingerprint(
            name=shared_name,
            artifact_type="skill",
            title="Document Parser",
            description="Deploy containerised workloads onto Kubernetes clusters at scale",
            tags=["kubernetes"],
        )

        score_same_desc = self.analyzer._compute_metadata_score(fp_base, fp_same_desc)
        score_diff_desc = self.analyzer._compute_metadata_score(fp_base, fp_diff_desc)
        assert score_same_desc > score_diff_desc

    def test_tags_only_match_outranks_no_match(self) -> None:
        """When descriptions and names differ, shared tags should push score higher."""
        fp_a = _make_fingerprint(
            name="tool-alpha",
            artifact_type="skill",
            title="Tool Alpha",
            description="Render canvas diagrams interactively",
            tags=["canvas", "design", "diagram"],
        )
        fp_tag_match = _make_fingerprint(
            name="tool-beta",
            artifact_type="skill",
            title="Tool Beta",
            description="Schedule backup routines automatically",
            tags=["canvas", "design", "diagram"],
        )
        fp_no_match = _make_fingerprint(
            name="tool-gamma",
            artifact_type="skill",
            title="Tool Gamma",
            description="Schedule backup routines automatically",
            tags=["kubernetes", "devops", "cluster"],
        )
        score_tag_match = self.analyzer._compute_metadata_score(fp_a, fp_tag_match)
        score_no_match = self.analyzer._compute_metadata_score(fp_a, fp_no_match)
        assert score_tag_match > score_no_match

    def test_score_always_in_zero_to_one_range(self) -> None:
        """Metadata score must never exceed 1.0 or go below 0.0."""
        fp_a = _make_fingerprint(
            name="canvas-design",
            artifact_type="skill",
            title="Canvas Design",
            description="A canvas design skill for creating diagrams",
            tags=["canvas", "design"],
        )
        fp_b = _make_fingerprint(
            name="canvas-design",
            artifact_type="skill",
            title="Canvas Design",
            description="A canvas design skill for creating diagrams",
            tags=["canvas", "design"],
        )
        score = self.analyzer._compute_metadata_score(fp_a, fp_b)
        assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# compare() — integration smoke test
# ---------------------------------------------------------------------------


class TestMatchAnalyzerCompare:
    """Smoke tests for MatchAnalyzer.compare() ScoreBreakdown integration."""

    def setup_method(self) -> None:
        self.analyzer = MatchAnalyzer()

    def test_compare_returns_score_breakdown_with_all_components(self) -> None:
        fp_a = _make_fingerprint(
            name="canvas",
            artifact_type="skill",
            title="Canvas",
            description="Canvas design tool",
            tags=["canvas"],
            content_hash="hash-x",
            structure_hash="struct-x",
        )
        fp_b = _make_fingerprint(
            name="canvas-v2",
            artifact_type="skill",
            title="Canvas V2",
            description="Canvas design tool v2",
            tags=["canvas"],
            content_hash="hash-x",
            structure_hash="struct-x",
        )
        breakdown = self.analyzer.compare(fp_a, fp_b)

        assert 0.0 <= breakdown.keyword_score <= 1.0
        assert 0.0 <= breakdown.content_score <= 1.0
        assert 0.0 <= breakdown.structure_score <= 1.0
        assert 0.0 <= breakdown.metadata_score <= 1.0
        assert breakdown.semantic_score is None  # populated downstream

    def test_compare_identical_content_hash_gives_content_score_one(self) -> None:
        fp_a = _make_fingerprint(name="tool", content_hash="same-hash")
        fp_b = _make_fingerprint(name="tool-copy", content_hash="same-hash")
        breakdown = self.analyzer.compare(fp_a, fp_b)
        assert breakdown.content_score == 1.0

    def test_compare_identical_structure_hash_gives_structure_score_one(self) -> None:
        fp_a = _make_fingerprint(name="tool", structure_hash="same-struct")
        fp_b = _make_fingerprint(name="tool-copy", structure_hash="same-struct")
        breakdown = self.analyzer.compare(fp_a, fp_b)
        assert breakdown.structure_score == 1.0

    def test_compare_metadata_score_higher_for_similar_pair(self) -> None:
        shared_desc = (
            "Convert PDF documents to structured markdown preserving tables and headings"
        )
        fp_similar_a = _make_fingerprint(
            name="pdf-to-md",
            title="PDF to Markdown",
            description=shared_desc,
            tags=["pdf", "markdown"],
        )
        fp_similar_b = _make_fingerprint(
            name="pdf-markdown",
            title="PDF Markdown Converter",
            description=shared_desc,
            tags=["pdf", "markdown"],
        )
        fp_unrelated = _make_fingerprint(
            name="k8s-deploy",
            title="Kubernetes Deployer",
            description="Deploy containers to Kubernetes clusters",
            tags=["kubernetes", "devops"],
        )

        breakdown_similar = self.analyzer.compare(fp_similar_a, fp_similar_b)
        breakdown_unrelated = self.analyzer.compare(fp_similar_a, fp_unrelated)

        assert breakdown_similar.metadata_score > breakdown_unrelated.metadata_score
