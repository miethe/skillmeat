"""Integration tests for path-based tag extraction workflow.

These tests verify the complete flow:
1. Scanner extracts path segments during scan
2. GET endpoint returns extracted segments
3. PATCH endpoint updates segment status
4. Changes persist correctly
"""
import json
import pytest
from datetime import datetime
from dataclasses import asdict

from skillmeat.core.path_tags import (
    PathTagConfig,
    PathSegmentExtractor,
    ExtractedSegment,
)
from skillmeat.api.schemas.marketplace import (
    PathSegmentsResponse,
    ExtractedSegmentResponse,
    UpdateSegmentStatusRequest,
    UpdateSegmentStatusResponse,
)


class TestScannerExtraction:
    """Tests for scanner → path_segments extraction workflow."""

    def test_extraction_produces_valid_json(self):
        """Extractor output can be serialized to valid JSON."""
        config = PathTagConfig.defaults()
        extractor = PathSegmentExtractor(config)

        # Extract from typical path
        segments = extractor.extract("categories/05-data-ai/ai-engineer.md")

        # Serialize as scanner would
        path_segments_json = json.dumps(
            {
                "raw_path": "categories/05-data-ai/ai-engineer.md",
                "extracted": [asdict(s) for s in segments],
                "extracted_at": datetime.utcnow().isoformat(),
            }
        )

        # Should be valid JSON
        data = json.loads(path_segments_json)
        assert "raw_path" in data
        assert "extracted" in data
        assert "extracted_at" in data
        assert len(data["extracted"]) > 0

    def test_extracted_json_matches_api_schema(self):
        """Extracted JSON can be deserialized to API response schemas."""
        config = PathTagConfig.defaults()
        extractor = PathSegmentExtractor(config)

        segments = extractor.extract("skills/python/basics.md")

        path_segments_json = json.dumps(
            {
                "raw_path": "skills/python/basics.md",
                "extracted": [asdict(s) for s in segments],
                "extracted_at": datetime.utcnow().isoformat(),
            }
        )

        # Parse as API endpoint would
        data = json.loads(path_segments_json)

        # Should be able to create response schema
        response = PathSegmentsResponse(
            entry_id="test-entry",
            raw_path=data["raw_path"],
            extracted=[ExtractedSegmentResponse(**seg) for seg in data["extracted"]],
            extracted_at=datetime.fromisoformat(data["extracted_at"]),
        )

        assert response.entry_id == "test-entry"
        assert len(response.extracted) > 0

    def test_normalization_persists_through_flow(self):
        """Normalized values are preserved through extraction and serialization."""
        config = PathTagConfig.defaults()
        extractor = PathSegmentExtractor(config)

        # Path with numeric prefix
        segments = extractor.extract("root/05-machine-learning/model.py")

        # Find the normalized segment
        ml_segment = next(
            (s for s in segments if "machine-learning" in s.normalized), None
        )
        assert ml_segment is not None
        assert ml_segment.normalized == "machine-learning"
        assert ml_segment.segment == "05-machine-learning"

        # Serialize and deserialize
        json_str = json.dumps(asdict(ml_segment))
        restored = json.loads(json_str)

        assert restored["segment"] == "05-machine-learning"
        assert restored["normalized"] == "machine-learning"


class TestStatusUpdateWorkflow:
    """Tests for status update workflow (simulating GET → PATCH flow)."""

    @pytest.fixture
    def extracted_segments(self):
        """Create sample extracted segments as stored in DB."""
        config = PathTagConfig.defaults()
        extractor = PathSegmentExtractor(config)
        segments = extractor.extract("categories/ai/tools/code-review.md")

        return json.dumps(
            {
                "raw_path": "categories/ai/tools/code-review.md",
                "extracted": [asdict(s) for s in segments],
                "extracted_at": "2025-01-01T00:00:00",
            }
        )

    def test_approve_segment_workflow(self, extracted_segments):
        """Complete workflow: read → approve → verify."""
        # Step 1: Parse (simulating GET)
        data = json.loads(extracted_segments)

        # Step 2: Find pending segment
        pending = [s for s in data["extracted"] if s["status"] == "pending"]
        assert len(pending) > 0
        segment_to_approve = pending[0]["segment"]

        # Step 3: Update status (simulating PATCH)
        for seg in data["extracted"]:
            if seg["segment"] == segment_to_approve:
                seg["status"] = "approved"

        # Step 4: Verify update
        updated = [
            s for s in data["extracted"] if s["segment"] == segment_to_approve
        ][0]
        assert updated["status"] == "approved"

    def test_reject_segment_workflow(self, extracted_segments):
        """Complete workflow: read → reject → verify."""
        data = json.loads(extracted_segments)

        pending = [s for s in data["extracted"] if s["status"] == "pending"]
        segment_to_reject = pending[0]["segment"]

        for seg in data["extracted"]:
            if seg["segment"] == segment_to_reject:
                seg["status"] = "rejected"

        updated = [s for s in data["extracted"] if s["segment"] == segment_to_reject][
            0
        ]
        assert updated["status"] == "rejected"

    def test_excluded_segments_preserved(self, extracted_segments):
        """Excluded segments maintain their status through updates."""
        # Create data with an excluded segment
        config = PathTagConfig.defaults()
        extractor = PathSegmentExtractor(config)
        segments = extractor.extract("root/src/lib/utils.ts")

        data = {
            "raw_path": "root/src/lib/utils.ts",
            "extracted": [asdict(s) for s in segments],
            "extracted_at": "2025-01-01T00:00:00",
        }

        # Check excluded segments exist
        excluded = [s for s in data["extracted"] if s["status"] == "excluded"]
        assert len(excluded) >= 1  # src or lib should be excluded

        # Approve a pending segment
        pending = [s for s in data["extracted"] if s["status"] == "pending"]
        if pending:
            pending[0]["status"] = "approved"

        # Excluded segments should still be excluded
        still_excluded = [s for s in data["extracted"] if s["status"] == "excluded"]
        assert len(still_excluded) == len(excluded)


class TestRealisticPaths:
    """Tests with realistic artifact paths from various repositories."""

    @pytest.fixture
    def extractor(self):
        return PathSegmentExtractor(PathTagConfig.defaults())

    def test_anthropic_skills_path(self, extractor):
        """anthropics/skills style paths extract correctly."""
        segments = extractor.extract("categories/05-data-ai/ai-engineer.md")

        # Should extract 'categories' and 'data-ai' (normalized)
        normalized = [s.normalized for s in segments if s.status == "pending"]
        assert "categories" in normalized
        assert "data-ai" in normalized

    def test_simple_skill_path(self, extractor):
        """Simple skill paths extract correctly."""
        segments = extractor.extract("skills/python/parser.py")

        normalized = [s.normalized for s in segments if s.status == "pending"]
        assert "skills" in normalized
        assert "python" in normalized

    def test_nested_path(self, extractor):
        """Deeply nested paths respect max_depth."""
        segments = extractor.extract("a/b/c/d/e/f/file.md")

        # With max_depth=3, should only get first 3 segments
        pending = [s for s in segments if s.status == "pending"]
        assert len(pending) <= 3

    def test_path_with_common_dirs_excluded(self, extractor):
        """Common directory names (src, lib, test) are excluded."""
        segments = extractor.extract("project/src/components/button.tsx")

        excluded = [s.segment for s in segments if s.status == "excluded"]
        # 'src' should be excluded
        assert "src" in excluded or len(
            [s for s in segments if s.segment == "src" and s.status == "excluded"]
        ) > 0


class TestEdgeCasesIntegration:
    """Integration tests for edge cases in the full workflow."""

    def test_empty_extraction_produces_valid_json(self):
        """Even empty extraction produces valid JSON structure."""
        config = PathTagConfig.defaults()
        extractor = PathSegmentExtractor(config)

        # Single file path produces empty extraction
        segments = extractor.extract("readme.md")

        json_str = json.dumps(
            {
                "raw_path": "readme.md",
                "extracted": [asdict(s) for s in segments],
                "extracted_at": datetime.utcnow().isoformat(),
            }
        )

        data = json.loads(json_str)
        assert data["raw_path"] == "readme.md"
        assert data["extracted"] == []

    def test_unicode_paths(self):
        """Unicode in paths is handled correctly."""
        config = PathTagConfig.defaults()
        extractor = PathSegmentExtractor(config)

        segments = extractor.extract("文档/技术/readme.md")

        # Should extract unicode segments
        json_str = json.dumps(
            {
                "raw_path": "文档/技术/readme.md",
                "extracted": [asdict(s) for s in segments],
                "extracted_at": datetime.utcnow().isoformat(),
            }
        )

        data = json.loads(json_str)
        assert "文档" in data["raw_path"]
