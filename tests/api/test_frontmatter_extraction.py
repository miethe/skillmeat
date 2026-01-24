"""Tests for frontmatter extraction during marketplace scan.

Tests the _extract_frontmatter_for_artifact function that extracts
search metadata (title, description, tags, search_text) from SKILL.md
files during artifact scanning.
"""

import json
import pytest
from unittest.mock import Mock

from skillmeat.api.routers.marketplace_sources import _extract_frontmatter_for_artifact
from skillmeat.api.schemas.marketplace import DetectedArtifact


class TestExtractFrontmatterForArtifact:
    """Tests for _extract_frontmatter_for_artifact function."""

    def test_extracts_all_fields_from_skill_md(self):
        """Test that all frontmatter fields are extracted correctly."""
        # Setup mock scanner
        mock_scanner = Mock()
        mock_scanner.get_file_content = Mock(return_value={
            "content": """---
title: Canvas Design Skill
description: A skill for designing visual elements
tags:
  - design
  - ui
  - canvas
---

# Canvas Design

This skill helps with designing visual elements.
""",
            "is_binary": False,
        })

        # Setup mock source
        mock_source = Mock()
        mock_source.owner = "test-owner"
        mock_source.repo_name = "test-repo"
        mock_source.ref = "main"

        # Create test artifact
        artifact = DetectedArtifact(
            artifact_type="skill",
            name="canvas-design",
            path="skills/canvas-design",
            upstream_url="https://github.com/test-owner/test-repo/tree/main/skills/canvas-design",
            confidence_score=90,
        )

        # Execute
        result = _extract_frontmatter_for_artifact(mock_scanner, mock_source, artifact)

        # Verify scanner was called with correct path
        mock_scanner.get_file_content.assert_called_once_with(
            owner="test-owner",
            repo="test-repo",
            path="skills/canvas-design/SKILL.md",
            ref="main",
        )

        # Verify extracted fields
        assert result["title"] == "Canvas Design Skill"
        assert result["description"] == "A skill for designing visual elements"
        assert result["search_tags"] == ["design", "ui", "canvas"]
        assert "canvas-design" in result["search_text"]
        assert "Canvas Design Skill" in result["search_text"]
        assert "design" in result["search_text"]

    def test_uses_name_field_when_title_missing(self):
        """Test that 'name' field is used if 'title' is missing."""
        mock_scanner = Mock()
        mock_scanner.get_file_content = Mock(return_value={
            "content": """---
name: My Skill Name
description: A description
---
""",
            "is_binary": False,
        })

        mock_source = Mock()
        mock_source.owner = "owner"
        mock_source.repo_name = "repo"
        mock_source.ref = "main"

        artifact = DetectedArtifact(
            artifact_type="skill",
            name="my-skill",
            path="skills/my-skill",
            upstream_url="https://github.com/owner/repo",
            confidence_score=80,
        )

        result = _extract_frontmatter_for_artifact(mock_scanner, mock_source, artifact)

        assert result["title"] == "My Skill Name"

    def test_skips_non_skill_artifacts(self):
        """Test that non-skill artifacts are skipped."""
        mock_scanner = Mock()
        mock_source = Mock()

        # Create command artifact
        artifact = DetectedArtifact(
            artifact_type="command",
            name="test-command",
            path="commands/test",
            upstream_url="https://github.com/test/test",
            confidence_score=80,
        )

        result = _extract_frontmatter_for_artifact(mock_scanner, mock_source, artifact)

        # Verify scanner was NOT called
        mock_scanner.get_file_content.assert_not_called()

        # Verify empty results
        assert result["title"] is None
        assert result["description"] is None
        assert result["search_tags"] is None
        assert result["search_text"] is None

    def test_handles_missing_skill_md_gracefully(self):
        """Test graceful handling when SKILL.md is not found."""
        mock_scanner = Mock()
        mock_scanner.get_file_content = Mock(return_value=None)

        mock_source = Mock()
        mock_source.owner = "owner"
        mock_source.repo_name = "repo"
        mock_source.ref = "main"

        artifact = DetectedArtifact(
            artifact_type="skill",
            name="missing-skill",
            path="skills/missing",
            upstream_url="https://github.com/owner/repo",
            confidence_score=80,
        )

        result = _extract_frontmatter_for_artifact(mock_scanner, mock_source, artifact)

        assert result["title"] is None
        assert result["description"] is None
        assert result["search_tags"] is None
        assert result["search_text"] is None

    def test_handles_binary_file_gracefully(self):
        """Test graceful handling when file is binary."""
        mock_scanner = Mock()
        mock_scanner.get_file_content = Mock(return_value={
            "content": "binary content",
            "is_binary": True,
        })

        mock_source = Mock()
        mock_source.owner = "owner"
        mock_source.repo_name = "repo"
        mock_source.ref = "main"

        artifact = DetectedArtifact(
            artifact_type="skill",
            name="binary-skill",
            path="skills/binary",
            upstream_url="https://github.com/owner/repo",
            confidence_score=80,
        )

        result = _extract_frontmatter_for_artifact(mock_scanner, mock_source, artifact)

        assert result["title"] is None

    def test_handles_no_frontmatter_gracefully(self):
        """Test handling of SKILL.md without frontmatter."""
        mock_scanner = Mock()
        mock_scanner.get_file_content = Mock(return_value={
            "content": """# My Skill

This skill has no frontmatter.
""",
            "is_binary": False,
        })

        mock_source = Mock()
        mock_source.owner = "owner"
        mock_source.repo_name = "repo"
        mock_source.ref = "main"

        artifact = DetectedArtifact(
            artifact_type="skill",
            name="no-frontmatter",
            path="skills/no-frontmatter",
            upstream_url="https://github.com/owner/repo",
            confidence_score=80,
        )

        result = _extract_frontmatter_for_artifact(mock_scanner, mock_source, artifact)

        assert result["title"] is None
        assert result["description"] is None
        assert result["search_tags"] is None
        assert result["search_text"] is None

    def test_handles_comma_separated_tags(self):
        """Test that comma-separated tags string is parsed correctly."""
        mock_scanner = Mock()
        mock_scanner.get_file_content = Mock(return_value={
            "content": """---
title: My Skill
tags: python, backend, api
---
""",
            "is_binary": False,
        })

        mock_source = Mock()
        mock_source.owner = "owner"
        mock_source.repo_name = "repo"
        mock_source.ref = "main"

        artifact = DetectedArtifact(
            artifact_type="skill",
            name="tagged-skill",
            path="skills/tagged",
            upstream_url="https://github.com/owner/repo",
            confidence_score=80,
        )

        result = _extract_frontmatter_for_artifact(mock_scanner, mock_source, artifact)

        assert result["search_tags"] == ["python", "backend", "api"]

    def test_truncates_long_title(self):
        """Test that title is truncated to 200 characters."""
        long_title = "A" * 300  # Title longer than 200 chars

        mock_scanner = Mock()
        mock_scanner.get_file_content = Mock(return_value={
            "content": f"""---
title: {long_title}
---
""",
            "is_binary": False,
        })

        mock_source = Mock()
        mock_source.owner = "owner"
        mock_source.repo_name = "repo"
        mock_source.ref = "main"

        artifact = DetectedArtifact(
            artifact_type="skill",
            name="long-title",
            path="skills/long",
            upstream_url="https://github.com/owner/repo",
            confidence_score=80,
        )

        result = _extract_frontmatter_for_artifact(mock_scanner, mock_source, artifact)

        assert len(result["title"]) == 200
        assert result["title"] == "A" * 200

    def test_handles_root_path_artifact(self):
        """Test artifact at root path (no subdirectory)."""
        mock_scanner = Mock()
        mock_scanner.get_file_content = Mock(return_value={
            "content": """---
title: Root Skill
---
""",
            "is_binary": False,
        })

        mock_source = Mock()
        mock_source.owner = "owner"
        mock_source.repo_name = "repo"
        mock_source.ref = "main"

        artifact = DetectedArtifact(
            artifact_type="skill",
            name="root-skill",
            path="",  # Root path
            upstream_url="https://github.com/owner/repo",
            confidence_score=80,
        )

        result = _extract_frontmatter_for_artifact(mock_scanner, mock_source, artifact)

        # Should look for SKILL.md at root
        mock_scanner.get_file_content.assert_called_once_with(
            owner="owner",
            repo="repo",
            path="SKILL.md",
            ref="main",
        )
        assert result["title"] == "Root Skill"

    def test_handles_exception_gracefully(self):
        """Test that exceptions during extraction are handled gracefully."""
        mock_scanner = Mock()
        mock_scanner.get_file_content = Mock(side_effect=Exception("Network error"))

        mock_source = Mock()
        mock_source.owner = "owner"
        mock_source.repo_name = "repo"
        mock_source.ref = "main"

        artifact = DetectedArtifact(
            artifact_type="skill",
            name="error-skill",
            path="skills/error",
            upstream_url="https://github.com/owner/repo",
            confidence_score=80,
        )

        # Should not raise, should return empty result
        result = _extract_frontmatter_for_artifact(mock_scanner, mock_source, artifact)

        assert result["title"] is None
        assert result["description"] is None
        assert result["search_tags"] is None
        assert result["search_text"] is None
