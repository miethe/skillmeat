"""Unit tests for PathSegmentExtractor and related dataclasses."""
import pytest
from skillmeat.core.path_tags import (
    PathTagConfig,
    ExtractedSegment,
    PathSegmentExtractor,
)


class TestPathTagConfig:
    """Tests for PathTagConfig dataclass."""

    def test_defaults(self):
        """defaults() creates instance with recommended values."""
        config = PathTagConfig.defaults()
        assert config.enabled is True
        assert config.max_depth == 3
        assert config.normalize_numbers is True
        assert len(config.exclude_patterns) >= 2

    def test_from_json_valid(self):
        """from_json() deserializes valid JSON."""
        config = PathTagConfig.from_json('{"enabled": false, "max_depth": 2}')
        assert config.enabled is False
        assert config.max_depth == 2

    def test_from_json_with_all_fields(self):
        """from_json() deserializes all fields correctly."""
        json_str = '''{
            "enabled": true,
            "skip_segments": [0, 1],
            "max_depth": 5,
            "normalize_numbers": false,
            "exclude_patterns": ["^test$"]
        }'''
        config = PathTagConfig.from_json(json_str)
        assert config.enabled is True
        assert config.skip_segments == [0, 1]
        assert config.max_depth == 5
        assert config.normalize_numbers is False
        assert config.exclude_patterns == ["^test$"]

    def test_from_json_invalid_syntax(self):
        """from_json() raises ValueError for invalid JSON."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            PathTagConfig.from_json("not json")

    def test_from_json_non_dict(self):
        """from_json() raises ValueError for non-dict JSON."""
        with pytest.raises(ValueError, match="JSON must be an object/dict"):
            PathTagConfig.from_json("[1, 2, 3]")

    def test_from_json_invalid_enabled_type(self):
        """from_json() raises ValueError for non-bool enabled."""
        with pytest.raises(ValueError, match="'enabled' must be a boolean"):
            PathTagConfig.from_json('{"enabled": "true"}')

    def test_from_json_invalid_skip_segments_type(self):
        """from_json() raises ValueError for non-list skip_segments."""
        with pytest.raises(ValueError, match="'skip_segments' must be a list"):
            PathTagConfig.from_json('{"skip_segments": 1}')

    def test_from_json_invalid_skip_segments_content(self):
        """from_json() raises ValueError for non-int in skip_segments."""
        with pytest.raises(ValueError, match="'skip_segments' must contain only integers"):
            PathTagConfig.from_json('{"skip_segments": ["0", "1"]}')

    def test_from_json_invalid_max_depth_type(self):
        """from_json() raises ValueError for non-int max_depth."""
        with pytest.raises(ValueError, match="'max_depth' must be an integer"):
            PathTagConfig.from_json('{"max_depth": "3"}')

    def test_from_json_invalid_max_depth_value(self):
        """from_json() raises ValueError for max_depth < 1."""
        with pytest.raises(ValueError, match="'max_depth' must be at least 1"):
            PathTagConfig.from_json('{"max_depth": 0}')

    def test_from_json_invalid_normalize_numbers_type(self):
        """from_json() raises ValueError for non-bool normalize_numbers."""
        with pytest.raises(ValueError, match="'normalize_numbers' must be a boolean"):
            PathTagConfig.from_json('{"normalize_numbers": "false"}')

    def test_from_json_invalid_exclude_patterns_type(self):
        """from_json() raises ValueError for non-list exclude_patterns."""
        with pytest.raises(ValueError, match="'exclude_patterns' must be a list"):
            PathTagConfig.from_json('{"exclude_patterns": "pattern"}')

    def test_from_json_invalid_exclude_patterns_content(self):
        """from_json() raises ValueError for non-str in exclude_patterns."""
        with pytest.raises(ValueError, match="'exclude_patterns' must contain only strings"):
            PathTagConfig.from_json('{"exclude_patterns": [123]}')

    def test_to_json_roundtrip(self):
        """to_json() and from_json() are inverse operations."""
        original = PathTagConfig(enabled=True, max_depth=5, skip_segments=[0, 1])
        json_str = original.to_json()
        restored = PathTagConfig.from_json(json_str)
        assert restored.enabled == original.enabled
        assert restored.max_depth == original.max_depth
        assert restored.skip_segments == original.skip_segments

    def test_to_json_contains_fields(self):
        """to_json() includes all fields in output."""
        config = PathTagConfig(enabled=True, max_depth=5)
        json_str = config.to_json()
        assert '"enabled": true' in json_str
        assert '"max_depth": 5' in json_str


class TestExtractedSegment:
    """Tests for ExtractedSegment dataclass."""

    def test_creation_valid(self):
        """ExtractedSegment can be created with valid status."""
        seg = ExtractedSegment(segment="foo", normalized="foo", status="pending")
        assert seg.segment == "foo"
        assert seg.normalized == "foo"
        assert seg.status == "pending"
        assert seg.reason is None

    def test_creation_with_reason(self):
        """ExtractedSegment can be created with reason."""
        seg = ExtractedSegment(
            segment="node_modules",
            normalized="node_modules",
            status="excluded",
            reason="Common directory",
        )
        assert seg.reason == "Common directory"

    def test_creation_invalid_status(self):
        """ExtractedSegment raises ValueError for invalid status."""
        with pytest.raises(ValueError, match="Invalid status"):
            ExtractedSegment(segment="foo", normalized="foo", status="invalid")  # type: ignore[arg-type]

    def test_to_dict(self):
        """to_dict() returns correct dictionary representation."""
        seg = ExtractedSegment(segment="foo", normalized="bar", status="pending")
        data = seg.to_dict()
        assert data == {
            "segment": "foo",
            "normalized": "bar",
            "status": "pending",
            "reason": None,
        }

    def test_from_dict_valid(self):
        """from_dict() creates instance from valid dict."""
        data = {"segment": "foo", "normalized": "bar", "status": "pending"}
        seg = ExtractedSegment.from_dict(data)
        assert seg.segment == "foo"
        assert seg.normalized == "bar"
        assert seg.status == "pending"

    def test_from_dict_with_reason(self):
        """from_dict() handles optional reason field."""
        data = {
            "segment": "foo",
            "normalized": "bar",
            "status": "excluded",
            "reason": "Test reason",
        }
        seg = ExtractedSegment.from_dict(data)
        assert seg.reason == "Test reason"

    def test_from_dict_missing_segment(self):
        """from_dict() raises ValueError for missing segment."""
        data = {"normalized": "bar", "status": "pending"}
        with pytest.raises(ValueError, match="Missing required field: 'segment'"):
            ExtractedSegment.from_dict(data)

    def test_from_dict_missing_normalized(self):
        """from_dict() raises ValueError for missing normalized."""
        data = {"segment": "foo", "status": "pending"}
        with pytest.raises(ValueError, match="Missing required field: 'normalized'"):
            ExtractedSegment.from_dict(data)

    def test_from_dict_missing_status(self):
        """from_dict() raises ValueError for missing status."""
        data = {"segment": "foo", "normalized": "bar"}
        with pytest.raises(ValueError, match="Missing required field: 'status'"):
            ExtractedSegment.from_dict(data)

    def test_roundtrip(self):
        """to_dict() and from_dict() are inverse operations."""
        original = ExtractedSegment(
            segment="05-data", normalized="data", status="pending", reason="Test"
        )
        data = original.to_dict()
        restored = ExtractedSegment.from_dict(data)
        assert restored.segment == original.segment
        assert restored.normalized == original.normalized
        assert restored.status == original.status
        assert restored.reason == original.reason


class TestNormalization:
    """Tests for number prefix normalization."""

    @pytest.fixture
    def extractor(self):
        return PathSegmentExtractor(PathTagConfig.defaults())

    def test_normalize_dash_prefix(self, extractor):
        """05-data-ai normalizes to data-ai."""
        result = extractor.extract("root/05-data-ai/file.md")
        normalized = [s.normalized for s in result if s.status == "pending"]
        assert "data-ai" in normalized

    def test_normalize_underscore_prefix(self, extractor):
        """01_foundations normalizes to foundations."""
        result = extractor.extract("root/01_foundations/file.md")
        normalized = [s.normalized for s in result if s.status == "pending"]
        assert "foundations" in normalized

    def test_normalize_multi_digit(self, extractor):
        """100-basics normalizes to basics."""
        result = extractor.extract("root/100-basics/file.md")
        normalized = [s.normalized for s in result if s.status == "pending"]
        assert "basics" in normalized

    def test_no_change_without_prefix(self, extractor):
        """data-ai stays as data-ai (no leading digits)."""
        result = extractor.extract("root/data-ai/file.md")
        normalized = [s.normalized for s in result if s.status == "pending"]
        assert "data-ai" in normalized

    def test_preserve_version_strings(self, extractor):
        """v1.2 stays as v1.2 (not leading digit pattern)."""
        result = extractor.extract("root/v1.2/file.md")
        # v1.2 doesn't match the pattern (no dash/underscore after digits)
        normalized = [s.normalized for s in result]
        assert any("v1.2" in s.normalized for s in result)

    def test_normalization_disabled(self):
        """When normalize_numbers=False, segments stay unchanged."""
        config = PathTagConfig(normalize_numbers=False, exclude_patterns=[])
        extractor = PathSegmentExtractor(config)
        result = extractor.extract("root/05-data-ai/file.md")
        normalized = [s.normalized for s in result]
        assert "05-data-ai" in normalized

    def test_normalization_original_preserved(self, extractor):
        """Original segment value is preserved after normalization."""
        result = extractor.extract("root/05-data-ai/file.md")
        for seg in result:
            if seg.normalized == "data-ai":
                assert seg.segment == "05-data-ai"


class TestDepthLimiting:
    """Tests for max_depth configuration."""

    def test_max_depth_limits_segments(self):
        """max_depth=2 keeps only first 2 segments."""
        config = PathTagConfig(max_depth=2, skip_segments=[0], exclude_patterns=[])
        extractor = PathSegmentExtractor(config)
        result = extractor.extract("root/a/b/c/d/file.md")
        pending = [s for s in result if s.status == "pending"]
        assert len(pending) == 2
        assert pending[0].segment == "a"
        assert pending[1].segment == "b"

    def test_max_depth_zero(self):
        """max_depth=0 returns empty list (handled in from_json validation)."""
        # Note: from_json() validates max_depth >= 1, but we can test direct instantiation
        config = PathTagConfig(max_depth=0)
        extractor = PathSegmentExtractor(config)
        result = extractor.extract("root/a/b/file.md")
        assert result == []

    def test_max_depth_one(self):
        """max_depth=1 returns only first segment."""
        config = PathTagConfig(max_depth=1, exclude_patterns=[])
        extractor = PathSegmentExtractor(config)
        result = extractor.extract("a/b/c/file.md")
        pending = [s for s in result if s.status == "pending"]
        assert len(pending) == 1
        assert pending[0].segment == "a"

    def test_max_depth_exceeds_path_length(self):
        """max_depth larger than path returns all segments."""
        config = PathTagConfig(max_depth=10, exclude_patterns=[])
        extractor = PathSegmentExtractor(config)
        result = extractor.extract("a/b/file.md")
        pending = [s for s in result if s.status == "pending"]
        assert len(pending) == 2  # Only a and b (file.md is removed)


class TestSkipSegments:
    """Tests for skip_segments configuration."""

    def test_skip_first_segment(self):
        """skip_segments=[0] skips first segment."""
        config = PathTagConfig(skip_segments=[0], exclude_patterns=[])
        extractor = PathSegmentExtractor(config)
        result = extractor.extract("root/a/b/file.md")
        segments = [s.segment for s in result]
        assert "root" not in segments
        assert "a" in segments
        assert "b" in segments

    def test_skip_multiple_segments(self):
        """skip_segments=[0,1] skips first two segments."""
        config = PathTagConfig(skip_segments=[0, 1], exclude_patterns=[])
        extractor = PathSegmentExtractor(config)
        result = extractor.extract("root/skip/keep/file.md")
        segments = [s.segment for s in result]
        assert "root" not in segments
        assert "skip" not in segments
        assert "keep" in segments

    def test_skip_middle_segment(self):
        """skip_segments=[1] skips second segment."""
        config = PathTagConfig(skip_segments=[1], exclude_patterns=[])
        extractor = PathSegmentExtractor(config)
        result = extractor.extract("keep1/skip/keep2/file.md")
        segments = [s.segment for s in result]
        assert "keep1" in segments
        assert "skip" not in segments
        assert "keep2" in segments

    def test_skip_non_contiguous(self):
        """skip_segments=[0, 2] skips non-contiguous segments."""
        config = PathTagConfig(skip_segments=[0, 2], exclude_patterns=[])
        extractor = PathSegmentExtractor(config)
        result = extractor.extract("skip1/keep1/skip2/keep2/file.md")
        segments = [s.segment for s in result]
        assert "skip1" not in segments
        assert "keep1" in segments
        assert "skip2" not in segments
        assert "keep2" in segments


class TestPatternExclusion:
    """Tests for exclude_patterns configuration."""

    def test_exclude_pure_numbers(self):
        """Pure number segments are excluded."""
        config = PathTagConfig.defaults()
        extractor = PathSegmentExtractor(config)
        result = extractor.extract("root/05/file.md")
        excluded = [s for s in result if s.status == "excluded"]
        assert any(s.segment == "05" for s in excluded)

    def test_exclude_common_dirs(self):
        """Common directories (src, lib, test) are excluded."""
        config = PathTagConfig.defaults()
        extractor = PathSegmentExtractor(config)

        for dirname in ["src", "lib", "test", "docs", "examples"]:
            result = extractor.extract(f"root/{dirname}/file.md")
            excluded = [s for s in result if s.status == "excluded"]
            assert any(s.segment == dirname for s in excluded), f"{dirname} should be excluded"

    def test_exclude_node_modules(self):
        """node_modules is excluded."""
        config = PathTagConfig.defaults()
        extractor = PathSegmentExtractor(config)
        result = extractor.extract("root/node_modules/file.md")
        excluded = [s for s in result if s.status == "excluded"]
        assert any(s.segment == "node_modules" for s in excluded)

    def test_exclude_pycache(self):
        """__pycache__ is excluded."""
        config = PathTagConfig.defaults()
        extractor = PathSegmentExtractor(config)
        result = extractor.extract("root/__pycache__/file.md")
        excluded = [s for s in result if s.status == "excluded"]
        assert any(s.segment == "__pycache__" for s in excluded)

    def test_custom_exclude_pattern(self):
        """Custom exclude patterns work correctly."""
        config = PathTagConfig(exclude_patterns=[r"^temp.*"])
        extractor = PathSegmentExtractor(config)
        result = extractor.extract("root/temp-data/file.md")
        excluded = [s for s in result if s.status == "excluded"]
        assert any(s.segment == "temp-data" for s in excluded)

    def test_excluded_has_reason(self):
        """Excluded segments have reason field populated."""
        config = PathTagConfig.defaults()
        extractor = PathSegmentExtractor(config)
        result = extractor.extract("root/src/file.md")
        excluded = [s for s in result if s.status == "excluded"]
        assert all(s.reason is not None for s in excluded)
        assert all("Matched exclude pattern" in s.reason for s in excluded if s.reason)


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def extractor(self):
        return PathSegmentExtractor(PathTagConfig.defaults())

    def test_empty_path(self, extractor):
        """Empty path returns empty list."""
        assert extractor.extract("") == []

    def test_single_segment(self, extractor):
        """Single segment (just filename) returns empty list."""
        assert extractor.extract("file.md") == []

    def test_only_filename(self, extractor):
        """Path with only slashes and filename returns empty list."""
        result = extractor.extract("/file.md")
        assert len([s for s in result if s.status == "pending"]) == 0

    def test_trailing_slash(self, extractor):
        """Trailing slash is handled correctly."""
        config = PathTagConfig(exclude_patterns=[])
        extractor = PathSegmentExtractor(config)
        result = extractor.extract("a/b/file.md/")
        # The trailing slash creates an empty segment which is filtered
        segments = [s.segment for s in result]
        assert "a" in segments
        assert "b" in segments

    def test_leading_slash(self, extractor):
        """Leading slash is handled correctly."""
        config = PathTagConfig(exclude_patterns=[])
        extractor = PathSegmentExtractor(config)
        result = extractor.extract("/a/b/file.md")
        segments = [s.segment for s in result]
        assert "a" in segments
        assert "b" in segments

    def test_double_slashes(self, extractor):
        """Double slashes are filtered out."""
        config = PathTagConfig(exclude_patterns=[])
        extractor = PathSegmentExtractor(config)
        result = extractor.extract("a//b/file.md")
        segments = [s.segment for s in result]
        assert "a" in segments
        assert "b" in segments
        assert "" not in segments

    def test_skip_larger_than_path(self):
        """skip_segments larger than path returns empty list."""
        config = PathTagConfig(skip_segments=[0, 1, 2, 3, 4], exclude_patterns=[])
        extractor = PathSegmentExtractor(config)
        result = extractor.extract("a/b/file.md")
        pending = [s for s in result if s.status == "pending"]
        assert len(pending) == 0

    def test_all_excluded(self):
        """When all segments excluded, returns list with excluded status."""
        config = PathTagConfig(exclude_patterns=[r".*"])  # Exclude everything
        extractor = PathSegmentExtractor(config)
        result = extractor.extract("a/b/file.md")
        assert len(result) > 0
        assert all(s.status == "excluded" for s in result)

    def test_invalid_regex_in_config(self):
        """Invalid regex pattern raises ValueError on initialization."""
        config = PathTagConfig(exclude_patterns=[r"[invalid"])
        with pytest.raises(ValueError, match="Invalid regex pattern"):
            PathSegmentExtractor(config)


class TestExtractorConfiguration:
    """Tests for PathSegmentExtractor configuration."""

    def test_default_config(self):
        """Extractor uses defaults when no config provided."""
        extractor = PathSegmentExtractor()
        assert extractor.config.enabled is True
        assert extractor.config.max_depth == 3
        assert extractor.config.normalize_numbers is True

    def test_custom_config(self):
        """Extractor uses provided config."""
        config = PathTagConfig(max_depth=5, normalize_numbers=False)
        extractor = PathSegmentExtractor(config)
        assert extractor.config.max_depth == 5
        assert extractor.config.normalize_numbers is False

    def test_config_property(self):
        """config property returns the current configuration."""
        config = PathTagConfig(max_depth=10)
        extractor = PathSegmentExtractor(config)
        assert extractor.config is config
        assert extractor.config.max_depth == 10


class TestIntegration:
    """Integration tests for common workflows."""

    def test_typical_skill_path(self):
        """Extract segments from typical skill path."""
        config = PathTagConfig.defaults()
        extractor = PathSegmentExtractor(config)
        result = extractor.extract("anthropics/skills/05-data-processing/csv-parser/SKILL.md")

        pending = [s for s in result if s.status == "pending"]
        normalized = [s.normalized for s in pending]

        # Should get: anthropics, skills, data-processing (normalized from 05-data-processing)
        assert len(pending) == 3  # max_depth=3
        assert "anthropics" in normalized
        assert "skills" in normalized
        assert "data-processing" in normalized

    def test_with_skip_root(self):
        """Extract segments skipping repository root."""
        config = PathTagConfig(skip_segments=[0], max_depth=3)
        extractor = PathSegmentExtractor(config)
        result = extractor.extract("anthropics/skills/05-data-ai/skill.md")

        pending = [s for s in result if s.status == "pending"]
        segments = [s.segment for s in pending]

        # Should skip 'anthropics', get: skills, 05-data-ai
        assert "anthropics" not in segments
        assert "skills" in segments
        assert "05-data-ai" in segments

    def test_mixed_excluded_and_pending(self):
        """Extract with mix of excluded and pending segments."""
        config = PathTagConfig.defaults()
        extractor = PathSegmentExtractor(config)
        result = extractor.extract("root/src/my-feature/file.md")

        pending = [s for s in result if s.status == "pending"]
        excluded = [s for s in result if s.status == "excluded"]

        # 'src' should be excluded, others pending
        assert len(excluded) >= 1
        assert any(s.segment == "src" for s in excluded)
        assert any(s.segment == "my-feature" for s in pending)


@pytest.mark.slow
class TestPerformance:
    """Performance tests for extraction."""

    def test_bulk_extraction_performance(self):
        """1000 extractions complete in reasonable time."""
        import time

        config = PathTagConfig.defaults()
        extractor = PathSegmentExtractor(config)

        start = time.time()
        for i in range(1000):
            extractor.extract(f"org/repo/category-{i}/skill-{i}/file.md")
        elapsed = time.time() - start

        # Should complete in under 5 seconds (generous for CI)
        assert elapsed < 5.0, f"1000 extractions took {elapsed:.2f}s"

    def test_pattern_compilation_cached(self):
        """Exclude patterns are compiled once and reused."""
        config = PathTagConfig(exclude_patterns=[r"^test\d+$", r"^temp.*"])
        extractor = PathSegmentExtractor(config)

        # Compiled patterns should be cached in _compiled_patterns
        assert len(extractor._compiled_patterns) == 2

        # Multiple extractions should use same compiled patterns
        for i in range(100):
            extractor.extract(f"root/test{i}/file.md")

        # Still only 2 compiled patterns
        assert len(extractor._compiled_patterns) == 2
