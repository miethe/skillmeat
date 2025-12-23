"""Integration test for error handling and graceful degradation.

This test demonstrates the complete error handling workflow in a real-world scenario.
"""

import asyncio

import pytest

from skillmeat.core.artifact import ArtifactMetadata
from skillmeat.core.scoring import ScoringService


@pytest.mark.asyncio
async def test_complete_degradation_workflow():
    """Integration test showing complete degradation workflow.

    This test demonstrates:
    1. Service initialization without API key
    2. Automatic degradation to keyword scoring
    3. Proper metadata tracking
    4. Duration tracking
    5. Working results despite degradation
    """
    # Initialize service without embedder (semantic unavailable)
    service = ScoringService(
        embedder=None,  # No embedder = semantic unavailable
        enable_semantic=True,  # Try to use semantic
        fallback_to_keyword=True,  # But fall back on failure
    )

    # Create test artifacts
    artifacts = [
        (
            "pdf-converter",
            ArtifactMetadata(
                title="PDF Converter",
                description="Convert documents to and from PDF format",
                tags=["pdf", "converter", "document"],
            ),
        ),
        (
            "image-processor",
            ArtifactMetadata(
                title="Image Processor",
                description="Process and manipulate images",
                tags=["image", "graphics", "processing"],
            ),
        ),
        (
            "pdf-reader",
            ArtifactMetadata(
                title="PDF Reader",
                description="Read and extract text from PDF files",
                tags=["pdf", "reader", "text-extraction"],
            ),
        ),
    ]

    # Score artifacts with query
    result = await service.score_artifacts("convert pdf files", artifacts)

    # Verify degradation metadata
    assert result.degraded is True, "Should be degraded (no embedder)"
    assert result.used_semantic is False, "Should not use semantic"
    assert result.degradation_reason is not None, "Should have degradation reason"
    assert "not available" in result.degradation_reason.lower()

    # Verify results still work
    assert len(result.scores) == 3, "Should return all artifacts"
    assert result.query == "convert pdf files"
    assert result.duration_ms > 0, "Should track duration"

    # Verify scoring quality (keyword-based)
    # PDF converter should rank highest (has both "pdf" and "converter")
    assert "pdf-converter" in result.scores[0].artifact_id
    assert result.scores[0].match_score > 50.0, "Should have good match score"

    # PDF reader should rank second (has "pdf")
    assert "pdf-reader" in result.scores[1].artifact_id

    # Image processor should rank lowest (no "pdf" or "convert")
    assert "image-processor" in result.scores[2].artifact_id

    print(f"\n✓ Degradation workflow successful")
    print(f"  - Degraded: {result.degraded}")
    print(f"  - Reason: {result.degradation_reason}")
    print(f"  - Duration: {result.duration_ms:.1f}ms")
    print(
        f"  - Top result: {result.scores[0].artifact_id} ({result.scores[0].match_score:.1f}%)"
    )


@pytest.mark.asyncio
async def test_keyword_only_mode_no_degradation():
    """Test that keyword-only mode doesn't set degradation flag.

    When semantic is explicitly disabled (not degraded), the degradation
    flag should be False.
    """
    # Initialize with semantic explicitly disabled
    service = ScoringService(enable_semantic=False)

    artifacts = [
        (
            "test-artifact",
            ArtifactMetadata(
                title="Test Artifact",
                description="A test artifact",
                tags=["test"],
            ),
        ),
    ]

    result = await service.score_artifacts("test", artifacts)

    # Should not be marked as degraded
    assert result.degraded is False, "Keyword-only mode is not degradation"
    assert result.used_semantic is False, "Should not use semantic"
    assert result.degradation_reason is None, "No degradation occurred"

    print(f"\n✓ Keyword-only mode works correctly")
    print(f"  - Degraded: {result.degraded} (expected: False)")
    print(f"  - Used semantic: {result.used_semantic} (expected: False)")


if __name__ == "__main__":
    # Run integration tests
    asyncio.run(test_complete_degradation_workflow())
    asyncio.run(test_keyword_only_mode_no_degradation())
    print("\n✓ All integration tests passed")
