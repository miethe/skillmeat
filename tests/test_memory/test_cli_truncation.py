"""Tests for CLI run log truncation functionality."""

import pytest

from skillmeat.cli import _truncate_run_log


def test_truncation_small_file():
    """Content under 500KB should be returned unchanged."""
    content = "Decision: Use FastAPI.\n" * 1000  # ~25KB
    result = _truncate_run_log(content, max_bytes=500_000)
    assert result == content


def test_truncation_large_file():
    """Content over 500KB should be truncated to approximately 500KB."""
    # Create content > 500KB
    line = "Decision: This is a test line for truncation functionality.\n"
    content = line * 15000  # ~900KB

    result = _truncate_run_log(content, max_bytes=500_000)

    # Result should be smaller than original
    assert len(result.encode("utf-8")) < len(content.encode("utf-8"))

    # Result should be close to 500KB (allowing for line boundary adjustment)
    result_bytes = len(result.encode("utf-8"))
    assert result_bytes <= 500_000
    assert result_bytes >= 490_000  # Should be close to limit


def test_truncation_preserves_end():
    """Large file should preserve the LAST lines (most recent content)."""
    # Create content with distinctive start and end
    start_marker = "START_LINE_MARKER\n"
    end_marker = "END_LINE_MARKER\n"
    filler = "Filler line content for testing truncation.\n" * 15000

    content = start_marker + filler + end_marker

    result = _truncate_run_log(content, max_bytes=500_000)

    # End marker should be present (last content preserved)
    assert "END_LINE_MARKER" in result

    # Start marker should NOT be present (beginning was truncated)
    assert "START_LINE_MARKER" not in result


def test_truncation_line_boundary():
    """Truncated content should start at a complete line (no partial first line)."""
    # Create content with distinct lines
    lines = [f"Line {i:05d}: Some content here\n" for i in range(20000)]
    content = "".join(lines)

    result = _truncate_run_log(content, max_bytes=500_000)

    # First line should be complete (start with "Line " and contain ":")
    first_line = result.split("\n")[0]
    assert first_line.startswith("Line ")
    assert ":" in first_line

    # Verify first line is well-formed (matches expected pattern)
    assert first_line.count("Line") == 1
    assert first_line.count(":") == 1


def test_truncation_utf8_handling():
    """Truncation should handle UTF-8 encoding correctly (no broken characters)."""
    # Create content with multi-byte UTF-8 characters
    line = "Decision: Use 日本語 テスト 🚀 for internationalization.\n"
    content = line * 15000  # ~900KB with multi-byte chars

    result = _truncate_run_log(content, max_bytes=500_000)

    # Result should be valid UTF-8 (decode/encode should work)
    try:
        result.encode("utf-8")
        decoded = result.encode("utf-8").decode("utf-8")
        assert decoded == result
    except UnicodeDecodeError:
        pytest.fail("Truncated content contains invalid UTF-8")

    # Result should contain multi-byte characters (not corrupted)
    assert "🚀" in result or "日本語" in result


def test_truncation_custom_max_bytes():
    """Custom max_bytes parameter should be respected."""
    content = "A" * 10000  # 10KB

    result = _truncate_run_log(content, max_bytes=5000)

    # Result should be under custom limit
    assert len(result.encode("utf-8")) <= 5000

    # Original should be unchanged with higher limit
    result_large = _truncate_run_log(content, max_bytes=20000)
    assert result_large == content
