"""Tests for frontmatter extraction integration in artifact import workflow.

These tests verify that:
- Frontmatter is extracted during artifact import (both GitHub and local)
- Description is auto-populated from frontmatter
- Tools field is populated and normalized to Tool enum values
- Frontmatter is cached in metadata.extra['frontmatter']
- Unknown tools are tracked in metadata.extra['unknown_tools']
- Errors don't block imports (graceful handling)
"""

import pytest
from pathlib import Path

from skillmeat.core.artifact import ArtifactMetadata
from skillmeat.core.artifact_detection import ArtifactType
from skillmeat.core.enums import Tool
from skillmeat.sources.local import LocalSource
from skillmeat.utils.metadata import (
    extract_artifact_metadata,
    extract_frontmatter,
    populate_metadata_from_frontmatter,
)


class TestFrontmatterExtractionIntegration:
    """Test frontmatter extraction during artifact import."""

    def test_local_source_extracts_tools_from_frontmatter(self, tmp_path):
        """Test that local source extracts tools from frontmatter during import."""
        # Create agent with tools in frontmatter
        agent_file = tmp_path / "coder.md"
        agent_file.write_text("""---
name: coder
description: A coding assistant
tools:
  - Bash
  - Read
  - Write
  - Edit
---

# Coder Agent

This agent helps with coding tasks.
""")

        source = LocalSource()
        result = source.fetch(str(agent_file), ArtifactType.AGENT)

        # Tools should be extracted and validated
        assert result.metadata.tools is not None
        assert len(result.metadata.tools) == 4
        tool_values = [t.value for t in result.metadata.tools]
        assert "Bash" in tool_values
        assert "Read" in tool_values
        assert "Write" in tool_values
        assert "Edit" in tool_values

    def test_local_source_extracts_description_from_frontmatter(self, tmp_path):
        """Test that description is auto-populated from frontmatter."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
description: A powerful skill for testing
title: Test Skill
---

# Test Skill

Some content here.
""")

        source = LocalSource()
        result = source.fetch(str(skill_dir), ArtifactType.SKILL)

        assert result.metadata.description == "A powerful skill for testing"

    def test_local_source_caches_frontmatter_in_extra(self, tmp_path):
        """Test that full frontmatter is cached in metadata.extra['frontmatter']."""
        agent_file = tmp_path / "agent.md"
        agent_file.write_text("""---
name: test-agent
description: Test description
tools:
  - Bash
model: opus
custom_field: custom_value
---

# Agent
""")

        source = LocalSource()
        result = source.fetch(str(agent_file), ArtifactType.AGENT)

        # Full frontmatter should be cached
        assert "frontmatter" in result.metadata.extra
        cached = result.metadata.extra["frontmatter"]
        assert cached["name"] == "test-agent"
        assert cached["model"] == "opus"
        # Tools should be normalized in cached frontmatter
        assert "tools" in cached

    def test_local_source_tracks_unknown_tools(self, tmp_path):
        """Test that unknown tool names are tracked for debugging."""
        agent_file = tmp_path / "agent.md"
        agent_file.write_text("""---
name: agent
tools:
  - Bash
  - Read
  - InvalidTool
  - AnotherFakeTool
---

# Agent
""")

        source = LocalSource()
        result = source.fetch(str(agent_file), ArtifactType.AGENT)

        # Valid tools should be extracted
        tool_values = [t.value for t in result.metadata.tools]
        assert "Bash" in tool_values
        assert "Read" in tool_values
        assert len(result.metadata.tools) == 2

        # Unknown tools should be tracked
        assert "unknown_tools" in result.metadata.extra
        assert "InvalidTool" in result.metadata.extra["unknown_tools"]
        assert "AnotherFakeTool" in result.metadata.extra["unknown_tools"]

    def test_local_source_normalizes_tool_names(self, tmp_path):
        """Test that tool names are normalized to match Tool enum values."""
        agent_file = tmp_path / "agent.md"
        agent_file.write_text("""---
name: agent
tools:
  - bash
  - BASH
  - web-fetch
  - WebFetch
  - web_search
---

# Agent
""")

        source = LocalSource()
        result = source.fetch(str(agent_file), ArtifactType.AGENT)

        # All variations should normalize to canonical values
        tool_values = [t.value for t in result.metadata.tools]
        # Should contain Bash, WebFetch, WebSearch (deduplicated from variations)
        assert "Bash" in tool_values
        assert "WebFetch" in tool_values
        assert "WebSearch" in tool_values

    def test_local_source_handles_comma_separated_tools(self, tmp_path):
        """Test that comma-separated tool strings are handled."""
        agent_file = tmp_path / "agent.md"
        agent_file.write_text("""---
name: agent
tools: Bash,Read,Write
---

# Agent
""")

        source = LocalSource()
        result = source.fetch(str(agent_file), ArtifactType.AGENT)

        tool_values = [t.value for t in result.metadata.tools]
        assert "Bash" in tool_values
        assert "Read" in tool_values
        assert "Write" in tool_values

    def test_local_source_handles_single_tool_value(self, tmp_path):
        """Test that a single tool value is handled correctly."""
        agent_file = tmp_path / "agent.md"
        agent_file.write_text("""---
name: agent
tools: Bash
---

# Agent
""")

        source = LocalSource()
        result = source.fetch(str(agent_file), ArtifactType.AGENT)

        assert len(result.metadata.tools) == 1
        assert result.metadata.tools[0].value == "Bash"

    def test_local_source_handles_allowed_tools_field(self, tmp_path):
        """Test that allowed-tools field is also recognized."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
title: Test Skill
allowed-tools:
  - Read
  - Write
---

# Skill
""")

        source = LocalSource()
        result = source.fetch(str(skill_dir), ArtifactType.SKILL)

        tool_values = [t.value for t in result.metadata.tools]
        assert "Read" in tool_values
        assert "Write" in tool_values

    def test_local_source_gracefully_handles_malformed_yaml(self, tmp_path):
        """Test that malformed YAML doesn't block import."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        # Malformed YAML - invalid array syntax
        skill_md.write_text("""---
title: Test Skill
tools: [broken yaml
---

# Skill Content
""")

        source = LocalSource()
        # Should not raise, should return metadata with what it can extract
        result = source.fetch(str(skill_dir), ArtifactType.SKILL)

        # Import should succeed even with malformed frontmatter
        assert result is not None
        assert result.artifact_path == skill_dir

    def test_local_source_handles_no_frontmatter(self, tmp_path):
        """Test that artifacts without frontmatter still import successfully."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""# Skill Without Frontmatter

This skill has no YAML frontmatter at all.
""")

        source = LocalSource()
        result = source.fetch(str(skill_dir), ArtifactType.SKILL)

        # Should succeed with empty/default metadata
        assert result is not None
        assert result.metadata.tools == []

    def test_local_source_extracts_skills_field(self, tmp_path):
        """Test that skills field is extracted from frontmatter."""
        agent_file = tmp_path / "agent.md"
        agent_file.write_text("""---
name: agent
skills:
  - python-skill
  - web-search
---

# Agent
""")

        source = LocalSource()
        result = source.fetch(str(agent_file), ArtifactType.AGENT)

        # Skills should be in cached frontmatter
        assert "frontmatter" in result.metadata.extra
        assert result.metadata.extra["frontmatter"]["skills"] == ["python-skill", "web-search"]

    def test_local_source_extracts_hooks_field(self, tmp_path):
        """Test that hooks field is extracted from frontmatter."""
        agent_file = tmp_path / "agent.md"
        agent_file.write_text("""---
name: agent
hooks:
  pre-commit: true
  post-push: false
---

# Agent
""")

        source = LocalSource()
        result = source.fetch(str(agent_file), ArtifactType.AGENT)

        # Hooks should be in cached frontmatter
        assert "frontmatter" in result.metadata.extra
        hooks = result.metadata.extra["frontmatter"]["hooks"]
        assert hooks["pre-commit"] is True
        assert hooks["post-push"] is False


class TestExtractArtifactMetadataIntegration:
    """Test extract_artifact_metadata function with enhanced frontmatter extraction."""

    def test_extract_metadata_with_tools(self, tmp_path):
        """Test that extract_artifact_metadata extracts tools correctly."""
        agent_file = tmp_path / "agent.md"
        agent_file.write_text("""---
name: test-agent
description: Test agent
tools:
  - Bash
  - Read
  - Glob
---

# Agent
""")

        metadata = extract_artifact_metadata(agent_file, ArtifactType.AGENT)

        assert metadata.description == "Test agent"
        assert len(metadata.tools) == 3
        tool_values = [t.value for t in metadata.tools]
        assert "Bash" in tool_values
        assert "Read" in tool_values
        assert "Glob" in tool_values

    def test_extract_metadata_caches_frontmatter(self, tmp_path):
        """Test that extract_artifact_metadata caches full frontmatter."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
title: My Skill
description: Skill description
author: Test Author
version: 1.0.0
tools:
  - Bash
custom_key: custom_value
---

# Skill
""")

        metadata = extract_artifact_metadata(skill_dir, ArtifactType.SKILL)

        # Standard fields populated
        assert metadata.title == "My Skill"
        assert metadata.description == "Skill description"
        assert metadata.author == "Test Author"
        assert metadata.version == "1.0.0"

        # Frontmatter cached - custom fields are stored in extra dict within frontmatter
        assert "frontmatter" in metadata.extra
        # The frontmatter dict contains an 'extra' key for non-standard fields
        cached_fm = metadata.extra["frontmatter"]
        assert "extra" in cached_fm
        assert cached_fm["extra"]["custom_key"] == "custom_value"

    def test_extract_metadata_falls_back_to_content_description(self, tmp_path):
        """Test that description falls back to content extraction if not in frontmatter."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
title: Skill Title
---

This is the first paragraph that should become the description.

# More Content
""")

        metadata = extract_artifact_metadata(skill_dir, ArtifactType.SKILL)

        # Description should be extracted from content
        assert "first paragraph" in metadata.description

    def test_extract_metadata_tracks_frontmatter_tools(self, tmp_path):
        """Test that frontmatter_tools are tracked separately."""
        agent_file = tmp_path / "agent.md"
        agent_file.write_text("""---
tools:
  - Bash
  - Read
---

# Agent
""")

        metadata = extract_artifact_metadata(agent_file, ArtifactType.AGENT)

        # Extracted tools should be in frontmatter_tools
        assert "frontmatter_tools" in metadata.extra
        assert metadata.extra["frontmatter_tools"] == ["Bash", "Read"]


class TestPopulateMetadataFromFrontmatter:
    """Test populate_metadata_from_frontmatter function."""

    def test_populate_sets_description(self):
        """Test that populate_metadata_from_frontmatter sets description."""
        metadata = ArtifactMetadata()
        frontmatter = {"description": "Test description"}

        result = populate_metadata_from_frontmatter(metadata, frontmatter)

        assert result.description == "Test description"

    def test_populate_sets_tools(self):
        """Test that populate_metadata_from_frontmatter sets tools."""
        metadata = ArtifactMetadata()
        frontmatter = {"tools": ["Bash", "Read", "Write"]}

        result = populate_metadata_from_frontmatter(metadata, frontmatter)

        tool_values = [t.value for t in result.tools]
        assert "Bash" in tool_values
        assert "Read" in tool_values
        assert "Write" in tool_values

    def test_populate_caches_frontmatter(self):
        """Test that populate_metadata_from_frontmatter caches full frontmatter."""
        metadata = ArtifactMetadata()
        frontmatter = {
            "description": "Test",
            "tools": ["Bash"],
            "custom": "value"
        }

        result = populate_metadata_from_frontmatter(metadata, frontmatter)

        assert result.extra["frontmatter"] == frontmatter

    def test_populate_tracks_unknown_tools(self):
        """Test that populate_metadata_from_frontmatter tracks unknown tools."""
        metadata = ArtifactMetadata()
        frontmatter = {"tools": ["Bash", "NotARealTool", "AnotherFake"]}

        result = populate_metadata_from_frontmatter(metadata, frontmatter)

        # Valid tool extracted
        assert len(result.tools) == 1
        assert result.tools[0].value == "Bash"

        # Unknown tools tracked
        assert "unknown_tools" in result.extra
        assert "NotARealTool" in result.extra["unknown_tools"]
        assert "AnotherFake" in result.extra["unknown_tools"]

    def test_populate_handles_empty_frontmatter(self):
        """Test that populate_metadata_from_frontmatter handles empty frontmatter."""
        metadata = ArtifactMetadata()

        result = populate_metadata_from_frontmatter(metadata, {})

        # Should return unchanged metadata
        assert result == metadata

    def test_populate_handles_none_frontmatter(self):
        """Test that populate_metadata_from_frontmatter handles None frontmatter."""
        metadata = ArtifactMetadata()

        result = populate_metadata_from_frontmatter(metadata, None)

        # Should return unchanged metadata
        assert result == metadata

    def test_populate_sets_standard_metadata_fields(self):
        """Test that populate_metadata_from_frontmatter sets standard fields."""
        metadata = ArtifactMetadata()
        frontmatter = {
            "title": "Test Title",
            "author": "Test Author",
            "license": "MIT",
            "version": "2.0.0",
            "tags": ["tag1", "tag2"],
            "dependencies": ["dep1", "dep2"]
        }

        result = populate_metadata_from_frontmatter(metadata, frontmatter)

        assert result.title == "Test Title"
        assert result.author == "Test Author"
        assert result.license == "MIT"
        assert result.version == "2.0.0"
        assert result.tags == ["tag1", "tag2"]
        assert result.dependencies == ["dep1", "dep2"]


class TestExtractFrontmatter:
    """Test extract_frontmatter function with tools normalization."""

    def test_extract_normalizes_tools_to_list(self):
        """Test that tools are normalized to a list."""
        content = """---
tools: Bash,Read,Write
---
# Content
"""
        result = extract_frontmatter(content)

        assert result["tools"] == ["Bash", "Read", "Write"]

    def test_extract_handles_tools_array(self):
        """Test that YAML array of tools is preserved."""
        content = """---
tools:
  - Bash
  - Read
---
# Content
"""
        result = extract_frontmatter(content)

        assert result["tools"] == ["Bash", "Read"]

    def test_extract_preserves_original_tool_names(self):
        """Test that extract_frontmatter preserves original tool names for later validation."""
        content = """---
tools:
  - bash
  - GLOB
  - web-fetch
---
# Content
"""
        result = extract_frontmatter(content)

        # extract_frontmatter preserves original names; normalization happens in populate_metadata_from_frontmatter
        assert "bash" in result["tools"]
        assert "GLOB" in result["tools"]
        assert "web-fetch" in result["tools"]

    def test_extract_handles_allowed_tools_field(self):
        """Test that allowed-tools is extracted as tools."""
        content = """---
allowed-tools:
  - Read
  - Write
---
# Content
"""
        result = extract_frontmatter(content)

        assert result["tools"] == ["Read", "Write"]

    def test_extract_prefers_tools_over_allowed_tools(self):
        """Test that tools field is preferred over allowed-tools."""
        content = """---
tools:
  - Bash
allowed-tools:
  - Read
---
# Content
"""
        result = extract_frontmatter(content)

        # Should use tools, not allowed-tools
        assert result["tools"] == ["Bash"]

    def test_extract_returns_empty_for_no_frontmatter(self):
        """Test that empty dict returned when no frontmatter."""
        content = """# Just content
No frontmatter here.
"""
        result = extract_frontmatter(content)

        assert result == {}

    def test_extract_handles_bom_character(self):
        """Test that BOM character at start is handled."""
        content = """\ufeff---
name: test
---
# Content
"""
        result = extract_frontmatter(content)

        assert result["name"] == "test"

    def test_extract_handles_malformed_yaml_gracefully(self):
        """Test that malformed YAML is handled gracefully."""
        content = """---
name: test
tools: [broken
---
# Content
"""
        # Should not raise, should return partial data
        result = extract_frontmatter(content)

        # May have partial data or empty dict, but should not raise
        assert isinstance(result, dict)
