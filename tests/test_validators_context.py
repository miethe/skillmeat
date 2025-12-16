"""Tests for context entity validation module.

Tests validators for all 5 context entity types with focus on:
- Correct validation logic per entity type
- Path traversal prevention (security)
- Edge cases and error conditions
"""

import pytest

from skillmeat.core.validators.context_entity import (
    ValidationError,
    validate_context_entity,
    validate_context_file,
    validate_progress_template,
    validate_project_config,
    validate_rule_file,
    validate_spec_file,
)


class TestProjectConfig:
    """Test ProjectConfig entity validation (CLAUDE.md files)."""

    def test_valid_markdown_passes(self):
        """Test valid markdown without frontmatter passes."""
        content = """# SkillMeat Project

This is a valid markdown file for CLAUDE.md.

## Features
- Feature 1
- Feature 2
"""
        errors = validate_project_config(content, "CLAUDE.md")
        assert errors == []

    def test_valid_with_frontmatter_passes(self):
        """Test valid markdown with frontmatter passes."""
        content = """---
title: SkillMeat
version: 1.0.0
---

# Project Documentation

This is valid markdown with frontmatter.
"""
        errors = validate_project_config(content, "CLAUDE.md")
        assert errors == []

    def test_empty_content_fails(self):
        """Test empty content fails validation."""
        errors = validate_project_config("", "CLAUDE.md")
        assert len(errors) == 1
        assert "cannot be empty" in errors[0].lower()

    def test_whitespace_only_fails(self):
        """Test whitespace-only content fails validation."""
        errors = validate_project_config("   \n  \n  ", "CLAUDE.md")
        assert len(errors) == 1
        assert "cannot be empty" in errors[0].lower()

    def test_content_too_short_fails(self):
        """Test very short content fails validation."""
        errors = validate_project_config("# Hi", "CLAUDE.md")
        assert any("too short" in err.lower() for err in errors)

    def test_invalid_yaml_frontmatter_ignored(self):
        """Test invalid YAML frontmatter is gracefully ignored."""
        content = """---
this is not: valid: yaml: nope
---

# Valid Markdown Content

This should still pass because frontmatter is optional.
"""
        errors = validate_project_config(content, "CLAUDE.md")
        # Should pass - invalid frontmatter just means no frontmatter
        assert errors == []


class TestSpecFile:
    """Test SpecFile entity validation (.claude/specs/)."""

    def test_valid_spec_passes(self):
        """Test valid spec file with frontmatter passes."""
        content = """---
title: API Specification
version: 1.0.0
---

# API Spec

This is the spec content.
"""
        errors = validate_spec_file(content, ".claude/specs/api-spec.md")
        assert errors == []

    def test_missing_frontmatter_fails(self):
        """Test spec file without frontmatter fails."""
        content = """# Spec Content

This has no frontmatter.
"""
        errors = validate_spec_file(content, ".claude/specs/spec.md")
        assert any("frontmatter is required" in err.lower() for err in errors)

    def test_missing_title_field_fails(self):
        """Test spec file without title field fails."""
        content = """---
version: 1.0.0
---

# Content
"""
        errors = validate_spec_file(content, ".claude/specs/spec.md")
        assert any("title" in err.lower() for err in errors)

    def test_invalid_path_fails(self):
        """Test spec file not in .claude/specs/ fails."""
        content = """---
title: Spec
---

Content
"""
        errors = validate_spec_file(content, "specs/wrong-location.md")
        assert any(".claude/specs/" in err for err in errors)

    def test_empty_content_after_frontmatter_fails(self):
        """Test spec with frontmatter but no body content fails."""
        content = """---
title: Empty Spec
---

"""
        errors = validate_spec_file(content, ".claude/specs/spec.md")
        assert any("after frontmatter cannot be empty" in err.lower() for err in errors)

    def test_valid_with_multiple_frontmatter_fields(self):
        """Test spec with multiple frontmatter fields passes."""
        content = """---
title: Complete Spec
version: 2.0.0
author: Test User
references:
  - file1.py
  - file2.py
---

# Specification

Complete spec content.
"""
        errors = validate_spec_file(content, ".claude/specs/complete.md")
        assert errors == []


class TestRuleFile:
    """Test RuleFile entity validation (.claude/rules/)."""

    def test_valid_rule_file_passes(self):
        """Test valid rule file passes."""
        content = """<!-- Path Scope: skillmeat/api/**/*.py -->

# API Router Rules

Router patterns and conventions.
"""
        errors = validate_rule_file(content, ".claude/rules/api/routers.md")
        assert errors == []

    def test_rule_without_path_scope_passes(self):
        """Test rule file without path scope comment still passes."""
        content = """# General Rules

These are general rules without path scope.
"""
        errors = validate_rule_file(content, ".claude/rules/general.md")
        # Path scope is optional (warning only), should still pass
        assert errors == []

    def test_invalid_path_fails(self):
        """Test rule file not in .claude/rules/ fails."""
        content = """# Rules

Content
"""
        errors = validate_rule_file(content, "rules/wrong.md")
        assert any(".claude/rules/" in err for err in errors)

    def test_empty_content_fails(self):
        """Test empty rule file fails."""
        errors = validate_rule_file("", ".claude/rules/empty.md")
        assert any("cannot be empty" in err.lower() for err in errors)

    def test_nested_rule_path_valid(self):
        """Test nested rule file path is valid."""
        content = """<!-- Path Scope: skillmeat/web/**/*.ts -->

# Web Frontend Rules

Frontend patterns.
"""
        errors = validate_rule_file(content, ".claude/rules/web/components.md")
        assert errors == []


class TestContextFile:
    """Test ContextFile entity validation (.claude/context/)."""

    def test_valid_context_file_passes(self):
        """Test valid context file with references passes."""
        content = """---
title: Backend API Patterns
references:
  - skillmeat/api/routers/collections.py
  - skillmeat/api/schemas/collection.py
last_verified: 2025-12-13
---

# API Patterns

Backend patterns and conventions.
"""
        errors = validate_context_file(content, ".claude/context/backend-patterns.md")
        assert errors == []

    def test_missing_frontmatter_fails(self):
        """Test context file without frontmatter fails."""
        content = """# Context

No frontmatter here.
"""
        errors = validate_context_file(content, ".claude/context/test.md")
        assert any("frontmatter is required" in err.lower() for err in errors)

    def test_missing_references_field_fails(self):
        """Test context file without references field fails."""
        content = """---
title: Context
---

# Content
"""
        errors = validate_context_file(content, ".claude/context/test.md")
        assert any("references" in err.lower() for err in errors)

    def test_references_not_list_fails(self):
        """Test context file with non-list references fails."""
        content = """---
title: Context
references: "not a list"
---

# Content
"""
        errors = validate_context_file(content, ".claude/context/test.md")
        assert any("must be a list" in err.lower() for err in errors)

    def test_invalid_path_fails(self):
        """Test context file not in .claude/context/ fails."""
        content = """---
references:
  - file1.py
---

# Content
"""
        errors = validate_context_file(content, "context/wrong.md")
        assert any(".claude/context/" in err for err in errors)

    def test_empty_references_list_passes(self):
        """Test context file with empty references list passes."""
        content = """---
title: Context
references: []
---

# Content with empty references

This is valid.
"""
        errors = validate_context_file(content, ".claude/context/test.md")
        assert errors == []

    def test_valid_with_additional_fields(self):
        """Test context file with additional frontmatter fields passes."""
        content = """---
title: Comprehensive Context
references:
  - file1.py
  - file2.py
last_verified: 2025-12-13
author: Test
version: 1.0
---

# Context

Full context content.
"""
        errors = validate_context_file(content, ".claude/context/comprehensive.md")
        assert errors == []


class TestProgressTemplate:
    """Test ProgressTemplate entity validation (.claude/progress/)."""

    def test_valid_progress_template_passes(self):
        """Test valid progress template passes."""
        content = """---
type: progress
phase: 1
status: in_progress
tasks:
  - id: TASK-1.1
    status: pending
---

# Phase 1 Progress

## Tasks
- [ ] TASK-1.1: Create models
"""
        errors = validate_progress_template(
            content, ".claude/progress/agent-context-v1/phase-1-progress.md"
        )
        assert errors == []

    def test_missing_frontmatter_fails(self):
        """Test progress template without frontmatter fails."""
        content = """# Progress

No frontmatter.
"""
        errors = validate_progress_template(content, ".claude/progress/test.md")
        assert any("frontmatter is required" in err.lower() for err in errors)

    def test_missing_type_field_fails(self):
        """Test progress template without type field fails."""
        content = """---
phase: 1
---

# Progress
"""
        errors = validate_progress_template(content, ".claude/progress/test.md")
        assert any("type" in err.lower() for err in errors)

    def test_wrong_type_value_fails(self):
        """Test progress template with wrong type value fails."""
        content = """---
type: not-progress
---

# Progress
"""
        errors = validate_progress_template(content, ".claude/progress/test.md")
        assert any("must be 'progress'" in err.lower() for err in errors)

    def test_invalid_path_fails(self):
        """Test progress template not in .claude/progress/ fails."""
        content = """---
type: progress
---

# Progress
"""
        errors = validate_progress_template(content, "progress/wrong.md")
        assert any(".claude/progress/" in err for err in errors)

    def test_nested_progress_path_valid(self):
        """Test nested progress template path is valid."""
        content = """---
type: progress
phase: 2
---

# Phase 2 Progress

Content.
"""
        errors = validate_progress_template(
            content, ".claude/progress/feature-x/phase-2-progress.md"
        )
        assert errors == []

    def test_empty_content_after_frontmatter_fails(self):
        """Test progress template with no body content fails."""
        content = """---
type: progress
---

"""
        errors = validate_progress_template(content, ".claude/progress/test.md")
        assert any("after frontmatter cannot be empty" in err.lower() for err in errors)


class TestPathTraversalSecurity:
    """Test path traversal prevention across all entity types.

    CRITICAL: These tests ensure malicious paths cannot be used
    to access files outside the .claude directory.
    """

    @pytest.mark.parametrize(
        "entity_type,valid_path",
        [
            ("spec_file", ".claude/specs/test.md"),
            ("rule_file", ".claude/rules/test.md"),
            ("context_file", ".claude/context/test.md"),
            ("progress_template", ".claude/progress/test.md"),
        ],
    )
    def test_parent_directory_reference_fails(self, entity_type, valid_path):
        """Test paths with .. are rejected."""
        content = """---
title: Test
references: []
type: progress
---

# Content
"""
        malicious_path = valid_path.replace(".claude", ".claude/..")
        errors = validate_context_entity(entity_type, content, malicious_path)
        assert any(".." in err or "security" in err.lower() for err in errors)

    def test_project_config_parent_ref_fails(self):
        """Test project_config paths with .. are rejected."""
        content = """# Valid markdown

Content here.
"""
        errors = validate_project_config(content, "../CLAUDE.md")
        assert any(".." in err or "security" in err.lower() for err in errors)

    @pytest.mark.parametrize(
        "entity_type,malicious_path",
        [
            ("spec_file", ".claude/specs/../../etc/passwd"),
            ("rule_file", ".claude/rules/../../../secret"),
            ("context_file", ".claude/context/../../config"),
            ("progress_template", ".claude/progress/../../../data"),
        ],
    )
    def test_escape_attempts_fail(self, entity_type, malicious_path):
        """Test various escape attempts are blocked."""
        content = """---
title: Test
references: []
type: progress
---

# Content
"""
        errors = validate_context_entity(entity_type, content, malicious_path)
        assert any(
            ".." in err or "security" in err.lower() or "escape" in err.lower()
            for err in errors
        )

    @pytest.mark.parametrize(
        "entity_type,absolute_path",
        [
            ("spec_file", "/etc/passwd"),
            ("rule_file", "/tmp/evil.md"),
            ("context_file", "/var/log/test.md"),
            ("progress_template", "/root/.ssh/id_rsa"),
        ],
    )
    def test_unix_absolute_paths_fail(self, entity_type, absolute_path):
        """Test Unix-style absolute paths are rejected."""
        content = """---
title: Test
references: []
type: progress
---

# Content
"""
        errors = validate_context_entity(entity_type, content, absolute_path)
        assert any("absolute" in err.lower() for err in errors)

    @pytest.mark.parametrize(
        "entity_type,windows_path",
        [
            ("spec_file", "C:\\Windows\\system32\\config.md"),
            ("rule_file", "D:\\secrets\\data.md"),
            ("context_file", "E:\\temp\\evil.md"),
        ],
    )
    def test_windows_absolute_paths_fail(self, entity_type, windows_path):
        """Test Windows-style absolute paths are rejected."""
        content = """---
title: Test
references: []
type: progress
---

# Content
"""
        errors = validate_context_entity(entity_type, content, windows_path)
        assert any("absolute" in err.lower() for err in errors)

    def test_nested_parent_refs_fail(self):
        """Test deeply nested parent directory references fail."""
        content = """---
references: []
---

# Content
"""
        malicious_path = ".claude/context/../../../../../../etc/passwd"
        errors = validate_context_file(content, malicious_path)
        assert any(".." in err or "security" in err.lower() for err in errors)

    def test_hidden_parent_ref_fails(self):
        """Test hidden parent reference in middle of path fails."""
        content = """---
references: []
---

# Content
"""
        malicious_path = ".claude/context/../specs/test.md"
        errors = validate_context_file(content, malicious_path)
        assert any(".." in err or "security" in err.lower() for err in errors)

    def test_literal_dotdot_in_filename_fails(self):
        """Test literal .. in filename fails."""
        content = """---
references: []
---

# Content
"""
        # Literal ".." in path component
        malicious_path = ".claude/context/../secret.md"
        errors = validate_context_file(content, malicious_path)
        # Should fail due to parent directory reference
        assert any(".." in err or "security" in err.lower() for err in errors)


class TestValidateContextEntity:
    """Test unified validation function."""

    def test_project_config_delegation(self):
        """Test validate_context_entity delegates to project_config validator."""
        content = """# Valid Project

Content here.
"""
        errors = validate_context_entity("project_config", content, "CLAUDE.md")
        assert errors == []

    def test_spec_file_delegation(self):
        """Test validate_context_entity delegates to spec_file validator."""
        content = """---
title: Spec
---

# Content
"""
        errors = validate_context_entity("spec_file", content, ".claude/specs/test.md")
        assert errors == []

    def test_rule_file_delegation(self):
        """Test validate_context_entity delegates to rule_file validator."""
        content = """# Rules

Content.
"""
        errors = validate_context_entity("rule_file", content, ".claude/rules/test.md")
        assert errors == []

    def test_context_file_delegation(self):
        """Test validate_context_entity delegates to context_file validator."""
        content = """---
references: []
---

# Content
"""
        errors = validate_context_entity(
            "context_file", content, ".claude/context/test.md"
        )
        assert errors == []

    def test_progress_template_delegation(self):
        """Test validate_context_entity delegates to progress_template validator."""
        content = """---
type: progress
---

# Content
"""
        errors = validate_context_entity(
            "progress_template", content, ".claude/progress/test.md"
        )
        assert errors == []

    def test_unknown_entity_type_raises(self):
        """Test validate_context_entity raises on unknown entity type."""
        with pytest.raises(ValueError) as exc_info:
            validate_context_entity("unknown_type", "content", "path")
        assert "Unknown entity type" in str(exc_info.value)
        assert "unknown_type" in str(exc_info.value)

    def test_error_message_includes_valid_types(self):
        """Test error message includes list of valid entity types."""
        with pytest.raises(ValueError) as exc_info:
            validate_context_entity("invalid", "content", "path")
        error_msg = str(exc_info.value)
        assert "project_config" in error_msg
        assert "spec_file" in error_msg
        assert "rule_file" in error_msg
        assert "context_file" in error_msg
        assert "progress_template" in error_msg


class TestValidationError:
    """Test ValidationError dataclass."""

    def test_validation_error_creation(self):
        """Test creating ValidationError instance."""
        error = ValidationError(field="title", message="Missing title field")
        assert error.field == "title"
        assert error.message == "Missing title field"
        assert error.severity == "error"

    def test_validation_error_with_warning_severity(self):
        """Test creating ValidationError with warning severity."""
        error = ValidationError(
            field="references", message="No references found", severity="warning"
        )
        assert error.severity == "warning"

    def test_validation_error_str(self):
        """Test ValidationError string representation."""
        error = ValidationError(field="type", message="Invalid type value")
        assert str(error) == "[ERROR] type: Invalid type value"

    def test_validation_error_warning_str(self):
        """Test ValidationError warning string representation."""
        error = ValidationError(
            field="path_scope", message="No path scope comment", severity="warning"
        )
        assert str(error) == "[WARNING] path_scope: No path scope comment"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_frontmatter_with_empty_dict(self):
        """Test frontmatter with empty YAML dict."""
        content = """---
---

# Content

This has empty frontmatter.
"""
        # For spec files (requires title), empty frontmatter means missing title
        errors = validate_spec_file(content, ".claude/specs/test.md")
        # Empty frontmatter is parsed as None by the validator, so it should fail
        # with "frontmatter is required" rather than "title missing"
        assert len(errors) > 0

    def test_frontmatter_with_null_values(self):
        """Test frontmatter with null values."""
        content = """---
title: null
references: null
---

# Content
"""
        # For context files (references must be list)
        errors = validate_context_file(content, ".claude/context/test.md")
        # null is not a list, should fail
        assert any("references" in err.lower() for err in errors)

    def test_very_long_content_passes(self):
        """Test very long content passes validation."""
        long_content = """---
title: Long Content
---

# Introduction

""" + (
            "This is a very long paragraph. " * 1000
        )

        errors = validate_spec_file(long_content, ".claude/specs/long.md")
        assert errors == []

    def test_unicode_content_passes(self):
        """Test Unicode content is handled correctly."""
        content = """---
title: Unicode Test 中文 日本語
references:
  - файл.py
  - 文件.py
---

# Content with Unicode 🚀

测试 тест テスト
"""
        errors = validate_context_file(content, ".claude/context/unicode.md")
        assert errors == []

    def test_mixed_line_endings(self):
        """Test mixed line endings are handled."""
        content = "---\r\ntitle: Test\r\n---\r\n\n# Content\nWith mixed\r\nendings"
        errors = validate_spec_file(content, ".claude/specs/test.md")
        assert errors == []

    def test_multiline_yaml_values(self):
        """Test multiline YAML values in frontmatter."""
        content = """---
title: Test
description: |
  This is a multiline
  description that spans
  multiple lines.
references:
  - file1.py
  - file2.py
---

# Content
"""
        errors = validate_context_file(content, ".claude/context/test.md")
        assert errors == []

    def test_yaml_with_special_characters(self):
        """Test YAML with special characters."""
        content = """---
title: "Test: With Special & Characters"
references:
  - "file-with-dashes.py"
  - "file_with_underscores.py"
  - "file.with.dots.py"
---

# Content
"""
        errors = validate_context_file(content, ".claude/context/test.md")
        assert errors == []
