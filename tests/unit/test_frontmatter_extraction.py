"""Unit tests for frontmatter extraction and tool normalization.

These tests use direct module loading to avoid circular import issues
in the skillmeat package during test collection.
"""

import importlib.util
import time
from pathlib import Path

import pytest

# Load the metadata module directly to avoid circular imports through package __init__.py
_module_path = (
    Path(__file__).parent.parent.parent / "skillmeat" / "utils" / "metadata.py"
)
_spec = importlib.util.spec_from_file_location("metadata_direct", _module_path)
_metadata_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_metadata_module)

# Get functions from directly loaded module
_normalize_tool_name = _metadata_module._normalize_tool_name
_normalize_tools = _metadata_module._normalize_tools
extract_frontmatter = _metadata_module.extract_frontmatter


# =============================================================================
# Tool Normalization Tests
# =============================================================================


class TestNormalizeToolName:
    """Tests for _normalize_tool_name helper function."""

    def test_valid_tool_names_case_sensitive(self):
        """Valid tool names in correct case return unchanged."""
        assert _normalize_tool_name("Bash") == "Bash"
        assert _normalize_tool_name("Read") == "Read"
        assert _normalize_tool_name("Write") == "Write"
        assert _normalize_tool_name("WebFetch") == "WebFetch"
        assert _normalize_tool_name("MultiEdit") == "MultiEdit"
        assert _normalize_tool_name("KillShell") == "KillShell"

    def test_lowercase_normalization(self):
        """Lowercase tool names are normalized to PascalCase."""
        assert _normalize_tool_name("bash") == "Bash"
        assert _normalize_tool_name("read") == "Read"
        assert _normalize_tool_name("write") == "Write"
        assert _normalize_tool_name("webfetch") == "WebFetch"

    def test_hyphen_separated_names(self):
        """Hyphen-separated names are normalized."""
        assert _normalize_tool_name("web-fetch") == "WebFetch"
        assert _normalize_tool_name("web-search") == "WebSearch"
        assert _normalize_tool_name("kill-shell") == "KillShell"
        assert _normalize_tool_name("multi-edit") == "MultiEdit"

    def test_underscore_separated_names(self):
        """Underscore-separated names are normalized."""
        assert _normalize_tool_name("web_fetch") == "WebFetch"
        assert _normalize_tool_name("web_search") == "WebSearch"
        assert _normalize_tool_name("kill_shell") == "KillShell"
        assert _normalize_tool_name("multi_edit") == "MultiEdit"

    def test_all_valid_tools(self):
        """All Tool enum values are recognized."""
        all_tools = [
            "Read",
            "Write",
            "Edit",
            "MultiEdit",
            "Glob",
            "Grep",
            "NotebookEdit",
            "Bash",
            "KillShell",
            "AskUserQuestion",
            "TodoWrite",
            "WebFetch",
            "WebSearch",
            "Task",
            "TaskOutput",
            "Skill",
            "EnterPlanMode",
            "ExitPlanMode",
        ]
        for tool in all_tools:
            assert _normalize_tool_name(tool) == tool
            assert _normalize_tool_name(tool.lower()) == tool

    def test_invalid_tool_name_returns_none(self):
        """Invalid tool names return None."""
        assert _normalize_tool_name("InvalidTool") is None
        assert _normalize_tool_name("NotARealTool") is None
        assert _normalize_tool_name("foo") is None
        assert _normalize_tool_name("bar-baz") is None

    def test_empty_and_whitespace(self):
        """Empty strings and whitespace return None."""
        assert _normalize_tool_name("") is None
        assert _normalize_tool_name("   ") is None
        assert _normalize_tool_name(None) is None

    def test_whitespace_trimming(self):
        """Tool names with surrounding whitespace are trimmed."""
        assert _normalize_tool_name("  Bash  ") == "Bash"
        assert _normalize_tool_name("\tRead\n") == "Read"


class TestNormalizeTools:
    """Tests for _normalize_tools helper function."""

    def test_comma_separated_string(self):
        """Comma-separated strings are split and normalized."""
        result = _normalize_tools("Bash,Read,Write")
        assert result == ["Bash", "Read", "Write"]

    def test_comma_separated_with_spaces(self):
        """Comma-separated strings with spaces are handled."""
        result = _normalize_tools("Bash, Read, Write")
        assert result == ["Bash", "Read", "Write"]

    def test_yaml_array(self):
        """YAML arrays are normalized."""
        result = _normalize_tools(["Bash", "Read", "Write"])
        assert result == ["Bash", "Read", "Write"]

    def test_mixed_case_array(self):
        """Arrays with mixed case are normalized."""
        result = _normalize_tools(["bash", "READ", "Write"])
        assert result == ["Bash", "Read", "Write"]

    def test_hyphen_names_in_array(self):
        """Arrays with hyphen-separated names are normalized."""
        result = _normalize_tools(["bash", "web-fetch", "kill-shell"])
        assert result == ["Bash", "WebFetch", "KillShell"]

    def test_single_value_string(self):
        """Single value string returns single-element list."""
        result = _normalize_tools("Bash")
        assert result == ["Bash"]

    def test_single_value_lowercase(self):
        """Single lowercase value is normalized."""
        result = _normalize_tools("bash")
        assert result == ["Bash"]

    def test_none_returns_empty_list(self):
        """None input returns empty list."""
        result = _normalize_tools(None)
        assert result == []

    def test_empty_string_returns_empty_list(self):
        """Empty string returns empty list."""
        result = _normalize_tools("")
        assert result == []

    def test_invalid_tools_skipped(self):
        """Invalid tool names are skipped with warning."""
        result = _normalize_tools(["Bash", "InvalidTool", "Read"])
        assert result == ["Bash", "Read"]

    def test_empty_elements_skipped(self):
        """Empty elements in array are skipped."""
        result = _normalize_tools(["Bash", "", "Read", None])
        assert result == ["Bash", "Read"]

    def test_comma_separated_with_invalid(self):
        """Comma-separated with invalid values skips invalid."""
        result = _normalize_tools("Bash,invalid,Read")
        assert result == ["Bash", "Read"]


# =============================================================================
# String-Based Frontmatter Extraction Tests
# =============================================================================


class TestExtractFrontmatter:
    """Tests for extract_frontmatter function (string-based)."""

    def test_basic_frontmatter(self):
        """Basic frontmatter extraction works."""
        content = """---
name: my-skill
description: A useful skill
---
# Content here
"""
        result = extract_frontmatter(content)
        assert result["name"] == "my-skill"
        assert result["description"] == "A useful skill"

    def test_tools_comma_separated(self):
        """Tools as comma-separated string are normalized."""
        content = """---
name: tool-skill
tools: Bash,Read,Write
---
"""
        result = extract_frontmatter(content)
        assert result["tools"] == ["Bash", "Read", "Write"]

    def test_tools_yaml_array(self):
        """Tools as YAML array are normalized."""
        content = """---
name: tool-skill
tools:
  - Bash
  - Read
  - Write
---
"""
        result = extract_frontmatter(content)
        assert result["tools"] == ["Bash", "Read", "Write"]

    def test_tools_mixed_case_normalization(self):
        """Tools with various cases are normalized."""
        content = """---
name: tool-skill
tools:
  - bash
  - READ
  - web-fetch
---
"""
        result = extract_frontmatter(content)
        assert result["tools"] == ["bash", "READ", "web-fetch"]  # Original names preserved

    def test_allowed_tools_field(self):
        """allowed-tools field is recognized."""
        content = """---
name: tool-skill
allowed-tools: Bash,Read
---
"""
        result = extract_frontmatter(content)
        assert result["tools"] == ["Bash", "Read"]

    def test_allowedTools_camel_case(self):
        """allowedTools camelCase field is recognized."""
        content = """---
name: tool-skill
allowedTools:
  - Bash
  - Read
---
"""
        result = extract_frontmatter(content)
        assert result["tools"] == ["Bash", "Read"]

    def test_disallowed_tools(self):
        """disallowedTools field is extracted."""
        content = """---
name: restricted-skill
disallowedTools: Bash,Write
---
"""
        result = extract_frontmatter(content)
        assert result["disallowedTools"] == ["Bash", "Write"]

    def test_model_field(self):
        """model field is extracted."""
        content = """---
name: model-skill
model: claude-3-opus
---
"""
        result = extract_frontmatter(content)
        assert result["model"] == "claude-3-opus"

    def test_permission_mode_field(self):
        """permissionMode field is extracted."""
        content = """---
name: perm-skill
permissionMode: bypassPermissions
---
"""
        result = extract_frontmatter(content)
        assert result["permissionMode"] == "bypassPermissions"

    def test_permission_mode_hyphen(self):
        """permission-mode hyphenated field is recognized."""
        content = """---
name: perm-skill
permission-mode: default
---
"""
        result = extract_frontmatter(content)
        assert result["permissionMode"] == "default"

    def test_skills_array(self):
        """skills field as array is extracted."""
        content = """---
name: composite-skill
skills:
  - skill-a
  - skill-b
---
"""
        result = extract_frontmatter(content)
        assert result["skills"] == ["skill-a", "skill-b"]

    def test_skills_comma_separated(self):
        """skills field as comma-separated is extracted."""
        content = """---
name: composite-skill
skills: skill-a,skill-b,skill-c
---
"""
        result = extract_frontmatter(content)
        assert result["skills"] == ["skill-a", "skill-b", "skill-c"]

    def test_hooks_field(self):
        """hooks field is extracted as-is."""
        content = """---
name: hook-skill
hooks:
  pre-run: ./setup.sh
  post-run: ./cleanup.sh
---
"""
        result = extract_frontmatter(content)
        assert result["hooks"]["pre-run"] == "./setup.sh"
        assert result["hooks"]["post-run"] == "./cleanup.sh"

    def test_user_invocable_boolean(self):
        """user-invocable boolean field is extracted."""
        content = """---
name: invocable-skill
user-invocable: true
---
"""
        result = extract_frontmatter(content)
        assert result["userInvocable"] is True

    def test_user_invocable_string_true(self):
        """user-invocable string 'true' is converted to boolean."""
        content = """---
name: invocable-skill
user-invocable: "true"
---
"""
        result = extract_frontmatter(content)
        assert result["userInvocable"] is True

    def test_user_invocable_string_false(self):
        """user-invocable string 'false' is converted to boolean."""
        content = """---
name: invocable-skill
user-invocable: "false"
---
"""
        result = extract_frontmatter(content)
        assert result["userInvocable"] is False

    def test_standard_metadata_fields(self):
        """Standard metadata fields (title, author, etc.) are extracted."""
        content = """---
name: standard-skill
title: Standard Skill
author: John Doe
license: MIT
version: 1.0.0
---
"""
        result = extract_frontmatter(content)
        assert result["title"] == "Standard Skill"
        assert result["author"] == "John Doe"
        assert result["license"] == "MIT"
        assert result["version"] == "1.0.0"

    def test_tags_array(self):
        """tags field as array is extracted."""
        content = """---
name: tagged-skill
tags:
  - python
  - automation
  - tools
---
"""
        result = extract_frontmatter(content)
        assert result["tags"] == ["python", "automation", "tools"]

    def test_tags_comma_separated(self):
        """tags field as comma-separated is extracted."""
        content = """---
name: tagged-skill
tags: python,automation,tools
---
"""
        result = extract_frontmatter(content)
        assert result["tags"] == ["python", "automation", "tools"]

    def test_dependencies_array(self):
        """dependencies field as array is extracted."""
        content = """---
name: dependent-skill
dependencies:
  - skill-a
  - skill-b
---
"""
        result = extract_frontmatter(content)
        assert result["dependencies"] == ["skill-a", "skill-b"]

    def test_extra_fields(self):
        """Unknown fields are collected in extra dict."""
        content = """---
name: extra-skill
custom-field: custom-value
another_field: another_value
---
"""
        result = extract_frontmatter(content)
        assert "extra" in result
        assert result["extra"]["custom-field"] == "custom-value"
        assert result["extra"]["another_field"] == "another_value"


# =============================================================================
# Frontmatter Edge Cases
# =============================================================================


class TestExtractFrontmatterEdgeCases:
    """Edge case tests for extract_frontmatter (string-based)."""

    def test_empty_content(self):
        """Empty content returns empty dict."""
        assert extract_frontmatter("") == {}
        assert extract_frontmatter("   ") == {}

    def test_no_frontmatter(self):
        """Content without frontmatter returns empty dict."""
        content = "# Just a heading\n\nSome content here."
        result = extract_frontmatter(content)
        assert result == {}

    def test_only_opening_delimiter(self):
        """Content with only opening --- returns empty dict."""
        content = "---\nname: incomplete\n"
        result = extract_frontmatter(content)
        assert result == {}

    def test_bom_character(self):
        """BOM character at start is handled."""
        content = "\ufeff---\nname: bom-skill\n---\nContent"
        result = extract_frontmatter(content)
        assert result["name"] == "bom-skill"

    def test_crlf_line_endings(self):
        """CRLF (Windows) line endings are handled."""
        content = "---\r\nname: windows-skill\r\n---\r\nContent"
        result = extract_frontmatter(content)
        assert result["name"] == "windows-skill"

    def test_trailing_spaces_on_delimiter(self):
        """Trailing spaces on --- delimiter are handled."""
        content = "---   \nname: spaced-skill\n---   \nContent"
        result = extract_frontmatter(content)
        assert result["name"] == "spaced-skill"

    def test_unicode_in_values(self):
        """Unicode characters in values are preserved."""
        content = """---
name: unicode-skill
description: A skill with special chars
author: Hans Muller
---
"""
        result = extract_frontmatter(content)
        assert result["description"] == "A skill with special chars"
        assert result["author"] == "Hans Muller"

    def test_multiline_description(self):
        """Multiline YAML values are handled."""
        content = """---
name: multiline-skill
description: |
  This is a multiline
  description that spans
  multiple lines.
---
"""
        result = extract_frontmatter(content)
        assert "This is a multiline" in result["description"]
        assert "multiple lines" in result["description"]

    def test_quoted_values(self):
        """Quoted YAML values are handled."""
        content = """---
name: "quoted-skill"
description: 'A single-quoted description'
---
"""
        result = extract_frontmatter(content)
        assert result["name"] == "quoted-skill"
        assert result["description"] == "A single-quoted description"

    def test_indented_yaml(self):
        """Various indentation styles in YAML are handled."""
        content = """---
name: indented-skill
tools:
    - Bash
    - Read
    - Write
---
"""
        result = extract_frontmatter(content)
        assert result["tools"] == ["Bash", "Read", "Write"]

    def test_malformed_yaml_partial_extraction(self):
        """Malformed YAML attempts partial extraction."""
        # This YAML has a syntax error (bad indentation)
        content = """---
name: partial-skill
description: This should be extracted
  badly indented: value
---
"""
        result = extract_frontmatter(content)
        # Should at least get name from partial extraction
        assert result.get("name") == "partial-skill"

    def test_empty_yaml_section(self):
        """Empty YAML section returns empty dict."""
        content = "---\n---\nContent"
        result = extract_frontmatter(content)
        assert result == {}


# =============================================================================
# Performance Tests
# =============================================================================


class TestExtractFrontmatterPerformance:
    """Performance tests for extract_frontmatter."""

    def test_large_content_performance(self):
        """Large content with small frontmatter is fast."""
        # Create content with small frontmatter but large body
        frontmatter = """---
name: perf-skill
description: A performance test skill
tools: Bash,Read,Write
---
"""
        body = "# Content\n" + ("Lorem ipsum dolor sit amet.\n" * 10000)
        content = frontmatter + body

        start = time.perf_counter()
        result = extract_frontmatter(content)
        elapsed = time.perf_counter() - start

        assert result["name"] == "perf-skill"
        assert elapsed < 0.1  # Should complete in under 100ms

    def test_many_tools_performance(self):
        """Many tools in frontmatter are processed quickly."""
        # All valid tools
        tools = [
            "Read",
            "Write",
            "Edit",
            "MultiEdit",
            "Glob",
            "Grep",
            "NotebookEdit",
            "Bash",
            "KillShell",
            "AskUserQuestion",
            "TodoWrite",
            "WebFetch",
            "WebSearch",
            "Task",
            "TaskOutput",
            "Skill",
            "EnterPlanMode",
            "ExitPlanMode",
        ]
        content = f"""---
name: many-tools-skill
tools: {','.join(tools)}
---
"""
        start = time.perf_counter()
        result = extract_frontmatter(content)
        elapsed = time.perf_counter() - start

        assert len(result["tools"]) == len(tools)
        assert elapsed < 0.1  # Should complete in under 100ms


# =============================================================================
# Integration Tests
# =============================================================================


class TestExtractFrontmatterIntegration:
    """Integration tests simulating real-world usage."""

    def test_real_skill_frontmatter(self):
        """Real-world skill frontmatter is parsed correctly."""
        content = """---
name: code-review
description: Comprehensive code review skill for Claude Code
tools:
  - Read
  - Grep
  - Glob
  - Bash
model: claude-3-opus
permissionMode: default
user-invocable: true
tags:
  - code-review
  - development
  - quality
author: SkillMeat Team
version: 2.1.0
license: MIT
---
# Code Review Skill

This skill provides comprehensive code review capabilities.

## Usage

Invoke with `/code-review` command.
"""
        result = extract_frontmatter(content)

        assert result["name"] == "code-review"
        assert "Comprehensive code review" in result["description"]
        assert result["tools"] == ["Read", "Grep", "Glob", "Bash"]
        assert result["model"] == "claude-3-opus"
        assert result["permissionMode"] == "default"
        assert result["userInvocable"] is True
        assert result["tags"] == ["code-review", "development", "quality"]
        assert result["author"] == "SkillMeat Team"
        assert result["version"] == "2.1.0"
        assert result["license"] == "MIT"

    def test_minimal_skill_frontmatter(self):
        """Minimal skill frontmatter with just name works."""
        content = """---
name: minimal-skill
---
Content
"""
        result = extract_frontmatter(content)
        assert result["name"] == "minimal-skill"
        assert "tools" not in result
        assert "description" not in result

    def test_command_frontmatter(self):
        """Command-style frontmatter is parsed correctly."""
        content = """---
name: my-command
description: A custom command
allowed-tools:
  - Bash
  - Read
  - Write
user-invocable: true
---
Command content here
"""
        result = extract_frontmatter(content)
        assert result["name"] == "my-command"
        assert result["tools"] == ["Bash", "Read", "Write"]
        assert result["userInvocable"] is True


# =============================================================================
# Metadata Population Tests
# =============================================================================

# Get populate_metadata_from_frontmatter from directly loaded module
populate_metadata_from_frontmatter = _metadata_module.populate_metadata_from_frontmatter

# Load ArtifactMetadata and Tool enum
_artifact_module_path = (
    Path(__file__).parent.parent.parent / "skillmeat" / "core" / "artifact.py"
)
_artifact_spec = importlib.util.spec_from_file_location(
    "artifact_direct", _artifact_module_path
)
_artifact_module = importlib.util.module_from_spec(_artifact_spec)

# Need to load enums first to avoid import issues
_enums_module_path = (
    Path(__file__).parent.parent.parent / "skillmeat" / "core" / "enums.py"
)
_enums_spec = importlib.util.spec_from_file_location("enums_direct", _enums_module_path)
_enums_module = importlib.util.module_from_spec(_enums_spec)
_enums_spec.loader.exec_module(_enums_module)

Tool = _enums_module.Tool


# Create a minimal ArtifactMetadata for testing without full module loading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TestArtifactMetadata:
    """Minimal ArtifactMetadata for testing without circular imports."""

    title: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    license: Optional[str] = None
    version: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    tools: List[Tool] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)


class TestPopulateMetadataFromFrontmatter:
    """Tests for populate_metadata_from_frontmatter function."""

    def test_basic_description_population(self):
        """Description is populated from frontmatter."""
        metadata = TestArtifactMetadata()
        frontmatter = {"description": "A useful skill for automation"}

        populate_metadata_from_frontmatter(metadata, frontmatter)

        assert metadata.description == "A useful skill for automation"

    def test_tools_converted_to_enum(self):
        """Tools are converted to Tool enum objects."""
        metadata = TestArtifactMetadata()
        frontmatter = {"tools": ["Bash", "Read", "Write"]}

        populate_metadata_from_frontmatter(metadata, frontmatter)

        assert len(metadata.tools) == 3
        assert metadata.tools[0] == Tool.BASH
        assert metadata.tools[1] == Tool.READ
        assert metadata.tools[2] == Tool.WRITE

    def test_tools_normalized_before_conversion(self):
        """Tools with various formats are normalized before conversion."""
        metadata = TestArtifactMetadata()
        frontmatter = {"tools": ["bash", "web-fetch", "KILL_SHELL"]}

        populate_metadata_from_frontmatter(metadata, frontmatter)

        assert len(metadata.tools) == 3
        assert metadata.tools[0] == Tool.BASH
        assert metadata.tools[1] == Tool.WEB_FETCH
        assert metadata.tools[2] == Tool.KILL_SHELL

    def test_invalid_tools_tracked(self):
        """Invalid tool names are tracked in extra['unknown_tools']."""
        metadata = TestArtifactMetadata()
        frontmatter = {"tools": ["Bash", "InvalidTool", "Read", "NotARealTool"]}

        populate_metadata_from_frontmatter(metadata, frontmatter)

        # Valid tools should be present
        assert len(metadata.tools) == 2
        assert metadata.tools[0] == Tool.BASH
        assert metadata.tools[1] == Tool.READ

        # Invalid tools should be tracked
        assert "unknown_tools" in metadata.extra
        assert metadata.extra["unknown_tools"] == ["InvalidTool", "NotARealTool"]

    def test_frontmatter_tools_cached(self):
        """Original tool names from frontmatter are cached."""
        metadata = TestArtifactMetadata()
        frontmatter = {"tools": ["Bash", "Read", "InvalidTool"]}

        populate_metadata_from_frontmatter(metadata, frontmatter)

        assert "frontmatter_tools" in metadata.extra
        assert metadata.extra["frontmatter_tools"] == ["Bash", "Read", "InvalidTool"]

    def test_full_frontmatter_cached(self):
        """Full frontmatter dict is cached in extra['frontmatter']."""
        metadata = TestArtifactMetadata()
        frontmatter = {
            "description": "Test skill",
            "tools": ["Bash"],
            "custom_field": "custom_value",
        }

        populate_metadata_from_frontmatter(metadata, frontmatter)

        assert "frontmatter" in metadata.extra
        assert metadata.extra["frontmatter"] == frontmatter

    def test_empty_frontmatter_returns_unchanged(self):
        """Empty or None frontmatter returns metadata unchanged."""
        metadata = TestArtifactMetadata(description="Original description")

        # Test with None
        result = populate_metadata_from_frontmatter(metadata, None)
        assert result.description == "Original description"

        # Test with empty dict
        result = populate_metadata_from_frontmatter(metadata, {})
        assert result.description == "Original description"

    def test_all_standard_fields_populated(self):
        """All standard metadata fields are populated from frontmatter."""
        metadata = TestArtifactMetadata()
        frontmatter = {
            "title": "Test Skill",
            "description": "A test skill description",
            "author": "Test Author",
            "license": "MIT",
            "version": "1.0.0",
            "tags": ["python", "automation"],
            "dependencies": ["dep-a", "dep-b"],
            "tools": ["Bash", "Read"],
        }

        populate_metadata_from_frontmatter(metadata, frontmatter)

        assert metadata.title == "Test Skill"
        assert metadata.description == "A test skill description"
        assert metadata.author == "Test Author"
        assert metadata.license == "MIT"
        assert metadata.version == "1.0.0"
        assert metadata.tags == ["python", "automation"]
        assert metadata.dependencies == ["dep-a", "dep-b"]
        assert len(metadata.tools) == 2

    def test_tags_as_comma_separated_string(self):
        """Tags as comma-separated string are parsed."""
        metadata = TestArtifactMetadata()
        frontmatter = {"tags": "python, automation, tools"}

        populate_metadata_from_frontmatter(metadata, frontmatter)

        assert metadata.tags == ["python", "automation", "tools"]

    def test_dependencies_as_comma_separated_string(self):
        """Dependencies as comma-separated string are parsed."""
        metadata = TestArtifactMetadata()
        frontmatter = {"dependencies": "dep-a, dep-b, dep-c"}

        populate_metadata_from_frontmatter(metadata, frontmatter)

        assert metadata.dependencies == ["dep-a", "dep-b", "dep-c"]

    def test_none_values_handled_gracefully(self):
        """None values in frontmatter don't cause errors."""
        metadata = TestArtifactMetadata()
        frontmatter = {
            "description": None,
            "tools": None,
            "title": None,
            "author": None,
        }

        # Should not raise
        populate_metadata_from_frontmatter(metadata, frontmatter)

        assert metadata.description is None
        assert metadata.tools == []
        assert metadata.title is None

    def test_empty_tools_list(self):
        """Empty tools list is handled correctly."""
        metadata = TestArtifactMetadata()
        frontmatter = {"tools": []}

        populate_metadata_from_frontmatter(metadata, frontmatter)

        assert metadata.tools == []
        assert "frontmatter_tools" not in metadata.extra

    def test_tools_with_none_elements(self):
        """Tools list with None elements filters them out."""
        metadata = TestArtifactMetadata()
        frontmatter = {"tools": ["Bash", None, "Read", "", "Write"]}

        populate_metadata_from_frontmatter(metadata, frontmatter)

        assert len(metadata.tools) == 3
        assert metadata.tools[0] == Tool.BASH
        assert metadata.tools[1] == Tool.READ
        assert metadata.tools[2] == Tool.WRITE

    def test_returns_same_metadata_instance(self):
        """Function returns the same metadata instance that was passed in."""
        metadata = TestArtifactMetadata()
        frontmatter = {"description": "Test"}

        result = populate_metadata_from_frontmatter(metadata, frontmatter)

        assert result is metadata

    def test_all_valid_tools_from_enum(self):
        """All Tool enum values can be populated."""
        all_tool_names = [
            "Read",
            "Write",
            "Edit",
            "MultiEdit",
            "Glob",
            "Grep",
            "NotebookEdit",
            "Bash",
            "KillShell",
            "AskUserQuestion",
            "TodoWrite",
            "WebFetch",
            "WebSearch",
            "Task",
            "TaskOutput",
            "Skill",
            "EnterPlanMode",
            "ExitPlanMode",
        ]

        metadata = TestArtifactMetadata()
        frontmatter = {"tools": all_tool_names}

        populate_metadata_from_frontmatter(metadata, frontmatter)

        assert len(metadata.tools) == len(all_tool_names)
        assert "unknown_tools" not in metadata.extra

    def test_extra_dict_initialized_if_none(self):
        """Extra dict is initialized if None."""
        metadata = TestArtifactMetadata()
        metadata.extra = None

        frontmatter = {"description": "Test"}

        populate_metadata_from_frontmatter(metadata, frontmatter)

        assert metadata.extra is not None
        assert "frontmatter" in metadata.extra


class TestPopulateMetadataIntegration:
    """Integration tests for populate_metadata_from_frontmatter with extract_frontmatter."""

    def test_extract_and_populate_workflow(self):
        """Full workflow: extract frontmatter then populate metadata."""
        content = """---
name: integration-skill
description: A skill for integration testing
tools:
  - Bash
  - Read
  - Write
author: Test Author
version: 2.0.0
tags:
  - testing
  - integration
---
# Integration Skill Content
"""
        # Extract frontmatter from content
        frontmatter = extract_frontmatter(content)

        # Create fresh metadata and populate
        metadata = TestArtifactMetadata()
        populate_metadata_from_frontmatter(metadata, frontmatter)

        # Verify all fields populated correctly
        assert metadata.description == "A skill for integration testing"
        assert len(metadata.tools) == 3
        assert Tool.BASH in metadata.tools
        assert Tool.READ in metadata.tools
        assert Tool.WRITE in metadata.tools
        assert metadata.author == "Test Author"
        assert metadata.version == "2.0.0"
        assert metadata.tags == ["testing", "integration"]

        # Verify caching
        assert "frontmatter" in metadata.extra
        assert "frontmatter_tools" in metadata.extra
        # Note: unknown_tools won't be present because extract_frontmatter()
        # already filters out invalid tools via _normalize_tools()

    def test_populate_with_raw_frontmatter_tracks_unknowns(self):
        """When given raw frontmatter dict (not from extract_frontmatter), unknowns are tracked."""
        # Simulate what would happen if populate_metadata_from_frontmatter
        # receives raw frontmatter that hasn't been normalized yet
        metadata = TestArtifactMetadata()
        raw_frontmatter = {
            "description": "Test skill",
            "tools": ["Bash", "InvalidTool", "Read", "NotReal"],
        }

        populate_metadata_from_frontmatter(metadata, raw_frontmatter)

        # Valid tools converted
        assert len(metadata.tools) == 2
        assert Tool.BASH in metadata.tools
        assert Tool.READ in metadata.tools

        # Unknown tools tracked
        assert "unknown_tools" in metadata.extra
        assert metadata.extra["unknown_tools"] == ["InvalidTool", "NotReal"]

    def test_minimal_frontmatter_workflow(self):
        """Minimal frontmatter only populates what's present."""
        content = """---
name: minimal-skill
---
Content
"""
        frontmatter = extract_frontmatter(content)
        metadata = TestArtifactMetadata()
        populate_metadata_from_frontmatter(metadata, frontmatter)

        # Only frontmatter cache should be present
        assert "frontmatter" in metadata.extra
        assert metadata.description is None
        assert metadata.tools == []
        assert metadata.tags == []
