"""Unit tests for profile-aware context path validation."""

from pathlib import Path

import pytest

from skillmeat.core.path_resolver import DeploymentPathProfile
from skillmeat.core.validators.context_path_validator import (
    normalize_context_prefixes,
    rewrite_path_for_profile,
    validate_context_path,
)


def test_validate_context_path_allows_multiple_profile_prefixes():
    validated = validate_context_path(
        ".codex/specs/api.md",
        allowed_prefixes=[".claude/", ".codex/", ".gemini/"],
    )
    assert validated.normalized_path == ".codex/specs/api.md"
    assert validated.matched_prefix == ".codex/"


def test_validate_context_path_blocks_traversal():
    with pytest.raises(ValueError, match="cannot contain '..'"):
        validate_context_path(
            ".claude/specs/../../etc/passwd",
            allowed_prefixes=[".claude/"],
        )


def test_validate_context_path_blocks_escape_from_project(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()

    with pytest.raises(ValueError, match="path traversal"):
        validate_context_path(
            ".claude/specs/../../outside.md",
            project=project,
            allowed_prefixes=[".claude/"],
        )


def test_rewrite_path_for_profile_maps_root_directory():
    codex_profile = DeploymentPathProfile(profile_id="codex", root_dir=".codex")
    rewritten = rewrite_path_for_profile(".claude/rules/api.md", codex_profile)
    assert rewritten == ".codex/rules/api.md"


def test_normalize_context_prefixes_includes_profile_root_fallback():
    profile = DeploymentPathProfile(
        profile_id="codex",
        root_dir=".codex",
        context_prefixes=[".codex/context/"],
    )
    prefixes = normalize_context_prefixes(profile)
    assert ".codex/context/" in prefixes
    assert ".codex/" in prefixes
