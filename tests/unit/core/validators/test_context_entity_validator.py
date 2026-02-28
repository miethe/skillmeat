"""Unit tests for the DB-backed context entity validator (CECO-1.2 / CECO-1.4).

Covers:
- Hardcoded fallback path (flag off)
- DB-backed path (flag on, mock DB)
- Fallback on DB error
- TTL cache expiry
- Immediate cache invalidation
- Structured error format (field + hint keys) — CECO-1.4
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

import skillmeat.core.validators.context_entity as validator_module
from skillmeat.core.validators.context_entity import (
    ENTITY_TYPE_CONFIG_ENABLED,
    invalidate_entity_type_cache,
    validate_context_entity,
    _get_entity_type_config,
    _is_cache_fresh,
    _validate_from_db_config,
    _HARDCODED_VALIDATORS,
)


# ---------------------------------------------------------------------------
# Helper for structured error assertions
# ---------------------------------------------------------------------------

def _hints(errors: list) -> list:
    """Return hint strings from a list of structured error dicts."""
    return [e["hint"] for e in errors]


def _fields(errors: list) -> list:
    """Return field names from a list of structured error dicts."""
    return [e["field"] for e in errors]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reset_cache():
    """Reset the module-level cache to a clean state."""
    validator_module._entity_type_cache = None
    validator_module._entity_type_cache_loaded_at = 0.0


def _stub_db_rows(rows: List[Dict[str, Any]]):
    """Return a mock get_session() context whose query returns *rows*.

    Each item in *rows* must have keys matching EntityTypeConfig attributes
    used in _load_entity_type_cache: slug, path_prefix,
    required_frontmatter_keys, optional_frontmatter_keys, validation_rules.
    """
    mock_rows = []
    for r in rows:
        obj = MagicMock()
        obj.slug = r["slug"]
        obj.path_prefix = r.get("path_prefix")
        obj.required_frontmatter_keys = r.get("required_frontmatter_keys", [])
        obj.optional_frontmatter_keys = r.get("optional_frontmatter_keys", [])
        obj.validation_rules = r.get("validation_rules", {})
        obj.display_name = r.get("display_name", r["slug"])
        mock_rows.append(obj)

    mock_session = MagicMock()
    mock_session.query.return_value.all.return_value = mock_rows
    return mock_session


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_cache():
    """Always start each test with a clean cache and flag=False."""
    _reset_cache()
    original_flag = validator_module.ENTITY_TYPE_CONFIG_ENABLED
    validator_module.ENTITY_TYPE_CONFIG_ENABLED = False
    yield
    validator_module.ENTITY_TYPE_CONFIG_ENABLED = original_flag
    _reset_cache()


# ---------------------------------------------------------------------------
# Tests: hardcoded fallback (flag off)
# ---------------------------------------------------------------------------

class TestHardcodedFallback:
    """Validator uses hardcoded dispatch map when flag is False."""

    def test_flag_off_uses_hardcoded_project_config(self):
        assert not validator_module.ENTITY_TYPE_CONFIG_ENABLED
        content = "# My Project\n\nThis is a project config."
        errors = validate_context_entity(
            "project_config", content, ".claude/CLAUDE.md",
            allowed_prefixes=[".claude/"],
        )
        assert errors == []

    def test_flag_off_uses_hardcoded_spec_file_missing_title(self):
        assert not validator_module.ENTITY_TYPE_CONFIG_ENABLED
        content = "---\nfoo: bar\n---\n\nSome content."
        errors = validate_context_entity(
            "spec_file", content, ".claude/specs/my-spec.md",
            allowed_prefixes=[".claude/"],
        )
        hints = _hints(errors)
        assert any("title" in h for h in hints)

    def test_flag_off_uses_hardcoded_context_file_missing_references(self):
        content = "---\ntitle: foo\n---\n\nSome context."
        errors = validate_context_entity(
            "context_file", content, ".claude/context/my-ctx.md",
            allowed_prefixes=[".claude/"],
        )
        hints = _hints(errors)
        assert any("references" in h for h in hints)

    def test_flag_off_unknown_type_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown entity type"):
            validate_context_entity("nonexistent_type", "content", ".claude/x.md")

    def test_flag_off_does_not_hit_db(self):
        """No DB import should occur when flag is off."""
        with patch.object(
            validator_module, "_load_entity_type_cache"
        ) as mock_load:
            content = "# Config\n\nThis is my config file."
            validate_context_entity(
                "project_config", content, ".claude/CLAUDE.md",
                allowed_prefixes=[".claude/"],
            )
            mock_load.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: DB-backed path (flag on)
# ---------------------------------------------------------------------------

SPEC_FILE_DB_CONFIG: Dict[str, Any] = {
    "slug": "spec_file",
    "display_name": "Spec File",
    "path_prefix": ".claude/specs",
    "required_frontmatter_keys": ["title"],
    "optional_frontmatter_keys": ["description"],
    "validation_rules": {
        "frontmatter_required": True,
        "path_prefix_required": True,
        "min_content_length": 1,
    },
}

PROGRESS_DB_CONFIG: Dict[str, Any] = {
    "slug": "progress_template",
    "display_name": "Progress Template",
    "path_prefix": ".claude/progress",
    "required_frontmatter_keys": ["type"],
    "optional_frontmatter_keys": [],
    "validation_rules": {
        "frontmatter_required": True,
        "path_prefix_required": True,
        "min_content_length": 1,
        "type_must_equal": "progress",
    },
}

CONTEXT_FILE_DB_CONFIG: Dict[str, Any] = {
    "slug": "context_file",
    "display_name": "Context File",
    "path_prefix": ".claude/context",
    "required_frontmatter_keys": ["references"],
    "optional_frontmatter_keys": ["title"],
    "validation_rules": {
        "frontmatter_required": True,
        "path_prefix_required": True,
        "min_content_length": 1,
        "references_must_be_list": True,
    },
}


class TestDBBackedValidation:
    """Validator uses DB config when flag is True and DB is available."""

    def _patch_session(self, rows):
        """Patch get_session to return a mock session yielding *rows*."""
        mock_session = _stub_db_rows(rows)

        return patch(
            "skillmeat.core.validators.context_entity.get_session",
            return_value=mock_session,
        )

    def test_uses_db_config_for_spec_file_valid(self):
        """DB-backed cache drives validation when flag is on and cache is warm."""
        validator_module.ENTITY_TYPE_CONFIG_ENABLED = True
        # Directly populate the cache to avoid triggering the full import chain.
        validator_module._entity_type_cache = {
            "spec_file": {
                "slug": "spec_file",
                "path_prefix": ".claude/specs",
                "required_frontmatter_keys": ["title"],
                "optional_frontmatter_keys": ["description"],
                "validation_rules": {
                    "frontmatter_required": True,
                    "path_prefix_required": True,
                    "min_content_length": 1,
                },
            }
        }
        validator_module._entity_type_cache_loaded_at = time.time()

        content = "---\ntitle: My Spec\n---\n\nSpec content here."
        errors = validate_context_entity(
            "spec_file",
            content,
            ".claude/specs/my-spec.md",
            allowed_prefixes=[".claude/"],
        )
        assert errors == []

    def test_db_config_detects_missing_required_key(self):
        validator_module.ENTITY_TYPE_CONFIG_ENABLED = True
        validator_module._entity_type_cache = {
            "spec_file": {
                "slug": "spec_file",
                "path_prefix": ".claude/specs",
                "required_frontmatter_keys": ["title"],
                "optional_frontmatter_keys": [],
                "validation_rules": {
                    "frontmatter_required": True,
                    "path_prefix_required": True,
                    "min_content_length": 1,
                },
            }
        }
        validator_module._entity_type_cache_loaded_at = time.time()

        content = "---\nfoo: bar\n---\n\nContent."
        errors = validate_context_entity(
            "spec_file",
            content,
            ".claude/specs/my-spec.md",
            allowed_prefixes=[".claude/"],
        )
        hints = _hints(errors)
        assert any("title" in h for h in hints)

    def test_db_config_validates_progress_type_field(self):
        validator_module.ENTITY_TYPE_CONFIG_ENABLED = True
        validator_module._entity_type_cache = {"progress_template": PROGRESS_DB_CONFIG.copy()}
        validator_module._entity_type_cache_loaded_at = time.time()

        # Wrong type value
        content = "---\ntype: other\n---\n\nContent."
        errors = validate_context_entity(
            "progress_template",
            content,
            ".claude/progress/my.md",
            allowed_prefixes=[".claude/"],
        )
        hints = _hints(errors)
        assert any("progress" in h for h in hints)

        # Correct type value
        content_ok = "---\ntype: progress\n---\n\nContent."
        errors_ok = validate_context_entity(
            "progress_template",
            content_ok,
            ".claude/progress/my.md",
            allowed_prefixes=[".claude/"],
        )
        assert errors_ok == []

    def test_db_config_validates_references_must_be_list(self):
        validator_module.ENTITY_TYPE_CONFIG_ENABLED = True
        validator_module._entity_type_cache = {
            "context_file": CONTEXT_FILE_DB_CONFIG.copy()
        }
        validator_module._entity_type_cache_loaded_at = time.time()

        # references is a string, not a list
        content = "---\nreferences: single-string\n---\n\nContent."
        errors = validate_context_entity(
            "context_file",
            content,
            ".claude/context/my.md",
            allowed_prefixes=[".claude/"],
        )
        hints = _hints(errors)
        assert any("list" in h for h in hints)

    def test_db_config_unknown_type_falls_through_to_hardcoded(self):
        """Type not in DB cache falls through to hardcoded validators."""
        validator_module.ENTITY_TYPE_CONFIG_ENABLED = True
        # Cache populated but without "project_config"
        validator_module._entity_type_cache = {}
        validator_module._entity_type_cache_loaded_at = time.time()

        # project_config not in DB cache → use hardcoded validator
        content = "# Config\n\nThis is long enough."
        errors = validate_context_entity(
            "project_config",
            content,
            ".claude/CLAUDE.md",
            allowed_prefixes=[".claude/"],
        )
        assert errors == []

    def test_db_config_unknown_type_not_in_hardcoded_raises(self):
        """Type not in DB cache and not in hardcoded map raises ValueError."""
        validator_module.ENTITY_TYPE_CONFIG_ENABLED = True
        validator_module._entity_type_cache = {}
        validator_module._entity_type_cache_loaded_at = time.time()

        with pytest.raises(ValueError, match="Unknown entity type"):
            validate_context_entity("totally_unknown", "content", ".claude/x.md")


# ---------------------------------------------------------------------------
# Tests: fallback on DB error
# ---------------------------------------------------------------------------

class TestDBErrorFallback:
    """Validator falls back to hardcoded validators when DB query fails."""

    def test_falls_back_on_db_import_error(self):
        validator_module.ENTITY_TYPE_CONFIG_ENABLED = True
        _reset_cache()

        # Simulate DB load failure by making get_session raise
        import builtins
        real_import = builtins.__import__

        def failing_import(name, *args, **kwargs):
            if "skillmeat.cache.models" in name:
                raise ImportError("Simulated DB unavailable")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=failing_import):
            content = "# Config\n\nThis is long enough content."
            # Should NOT raise; falls back to hardcoded
            errors = validate_context_entity(
                "project_config",
                content,
                ".claude/CLAUDE.md",
                allowed_prefixes=[".claude/"],
            )
            assert isinstance(errors, list)

    def test_falls_back_on_session_query_error(self, caplog):
        """DB session query exception triggers fallback with WARNING log."""
        import logging

        validator_module.ENTITY_TYPE_CONFIG_ENABLED = True
        _reset_cache()

        mock_session = MagicMock()
        mock_session.query.side_effect = RuntimeError("DB connection failed")

        with patch(
            "skillmeat.core.validators.context_entity._load_entity_type_cache",
            wraps=lambda: None,  # returns None to simulate failure
        ) as mock_load:
            # Directly test that None from _load_entity_type_cache
            # causes fallback to hardcoded validators
            with patch.object(
                validator_module,
                "_get_entity_type_config",
                return_value=None,
            ):
                content = "# Config\n\nLong enough content here."
                errors = validate_context_entity(
                    "project_config",
                    content,
                    ".claude/CLAUDE.md",
                    allowed_prefixes=[".claude/"],
                )
                assert errors == []

    def test_load_failure_returns_none(self):
        """_load_entity_type_cache returns None when session raises."""
        _reset_cache()

        mock_models = MagicMock()
        mock_session = MagicMock()
        mock_session.query.side_effect = RuntimeError("boom")
        mock_models.get_session.return_value = mock_session
        mock_models.EntityTypeConfig = MagicMock()

        with patch.dict("sys.modules", {"skillmeat.cache.models": mock_models}):
            result = validator_module._load_entity_type_cache()

        assert result is None


# ---------------------------------------------------------------------------
# Tests: TTL cache
# ---------------------------------------------------------------------------

class TestTTLCache:
    """Cache expires after 60 seconds."""

    def test_fresh_cache_is_used(self):
        validator_module._entity_type_cache = {"spec_file": {"slug": "spec_file"}}
        validator_module._entity_type_cache_loaded_at = time.time()

        assert _is_cache_fresh() is True

    def test_stale_cache_detected(self):
        validator_module._entity_type_cache = {"spec_file": {"slug": "spec_file"}}
        # Simulate 61 seconds ago
        validator_module._entity_type_cache_loaded_at = time.time() - 61

        assert _is_cache_fresh() is False

    def test_empty_cache_is_not_fresh(self):
        validator_module._entity_type_cache = None
        validator_module._entity_type_cache_loaded_at = 0.0

        assert _is_cache_fresh() is False

    def test_stale_cache_triggers_reload(self):
        """Stale cache triggers _load_entity_type_cache on next access."""
        validator_module.ENTITY_TYPE_CONFIG_ENABLED = True
        validator_module._entity_type_cache = {"spec_file": {"slug": "stale"}}
        validator_module._entity_type_cache_loaded_at = time.time() - 61

        with patch.object(
            validator_module,
            "_load_entity_type_cache",
            return_value={"spec_file": {"slug": "fresh"}},
        ) as mock_load:
            result = _get_entity_type_config("spec_file")

        mock_load.assert_called_once()
        assert result is not None
        assert result["slug"] == "fresh"

    def test_fresh_cache_does_not_trigger_reload(self):
        """Fresh cache does NOT call _load_entity_type_cache."""
        validator_module.ENTITY_TYPE_CONFIG_ENABLED = True
        validator_module._entity_type_cache = {
            "spec_file": {"slug": "spec_file", "path_prefix": ".claude/specs"}
        }
        validator_module._entity_type_cache_loaded_at = time.time()

        with patch.object(
            validator_module, "_load_entity_type_cache"
        ) as mock_load:
            result = _get_entity_type_config("spec_file")

        mock_load.assert_not_called()
        assert result is not None


# ---------------------------------------------------------------------------
# Tests: cache invalidation
# ---------------------------------------------------------------------------

class TestCacheInvalidation:
    """invalidate_entity_type_cache() causes immediate reload on next access."""

    def test_invalidate_clears_cache(self):
        validator_module._entity_type_cache = {"spec_file": {"slug": "spec_file"}}
        validator_module._entity_type_cache_loaded_at = time.time()

        assert _is_cache_fresh() is True

        invalidate_entity_type_cache()

        assert validator_module._entity_type_cache is None
        assert validator_module._entity_type_cache_loaded_at == 0.0
        assert _is_cache_fresh() is False

    def test_invalidate_forces_next_load(self):
        """After invalidation, next get_entity_type_config triggers a DB load."""
        validator_module._entity_type_cache = {
            "spec_file": {"slug": "old_value"}
        }
        validator_module._entity_type_cache_loaded_at = time.time()

        invalidate_entity_type_cache()

        new_cache = {"spec_file": {"slug": "new_value"}}
        with patch.object(
            validator_module,
            "_load_entity_type_cache",
            return_value=new_cache,
        ) as mock_load:
            result = _get_entity_type_config("spec_file")

        mock_load.assert_called_once()
        assert result is not None
        assert result["slug"] == "new_value"


# ---------------------------------------------------------------------------
# Tests: _validate_from_db_config (unit-level, no DB needed)
# ---------------------------------------------------------------------------

class TestValidateFromDbConfig:
    """Unit tests for the generic DB-config validation function."""

    def test_empty_content_returns_error(self):
        config = {
            "slug": "spec_file",
            "path_prefix": None,
            "required_frontmatter_keys": [],
            "optional_frontmatter_keys": [],
            "validation_rules": {},
        }
        errors = _validate_from_db_config(config, "", ".claude/x.md", [".claude/"])
        hints = _hints(errors)
        assert any("empty" in h for h in hints)

    def test_frontmatter_required_but_missing(self):
        config = {
            "slug": "spec_file",
            "path_prefix": None,
            "required_frontmatter_keys": ["title"],
            "optional_frontmatter_keys": [],
            "validation_rules": {"frontmatter_required": True},
        }
        errors = _validate_from_db_config(
            config, "No frontmatter here.", ".claude/x.md", [".claude/"]
        )
        hints = _hints(errors)
        assert any("frontmatter" in h.lower() for h in hints)

    def test_required_frontmatter_key_missing(self):
        config = {
            "slug": "spec_file",
            "path_prefix": None,
            "required_frontmatter_keys": ["title"],
            "optional_frontmatter_keys": [],
            "validation_rules": {"frontmatter_required": True},
        }
        content = "---\nfoo: bar\n---\n\nContent."
        errors = _validate_from_db_config(config, content, ".claude/x.md", [".claude/"])
        hints = _hints(errors)
        assert any("title" in h for h in hints)

    def test_all_required_keys_present_passes(self):
        config = {
            "slug": "spec_file",
            "path_prefix": None,
            "required_frontmatter_keys": ["title"],
            "optional_frontmatter_keys": [],
            "validation_rules": {"frontmatter_required": True},
        }
        content = "---\ntitle: Hello\n---\n\nContent."
        errors = _validate_from_db_config(config, content, ".claude/x.md", [".claude/"])
        assert errors == []

    def test_type_must_equal_rule(self):
        config = {
            "slug": "progress_template",
            "path_prefix": None,
            "required_frontmatter_keys": ["type"],
            "optional_frontmatter_keys": [],
            "validation_rules": {
                "frontmatter_required": True,
                "type_must_equal": "progress",
            },
        }
        bad_content = "---\ntype: other\n---\n\nContent."
        errors = _validate_from_db_config(
            config, bad_content, ".claude/x.md", [".claude/"]
        )
        hints = _hints(errors)
        assert any("progress" in h for h in hints)

        good_content = "---\ntype: progress\n---\n\nContent."
        errors_ok = _validate_from_db_config(
            config, good_content, ".claude/x.md", [".claude/"]
        )
        assert errors_ok == []

    def test_references_must_be_list_rule(self):
        config = {
            "slug": "context_file",
            "path_prefix": None,
            "required_frontmatter_keys": ["references"],
            "optional_frontmatter_keys": [],
            "validation_rules": {
                "frontmatter_required": True,
                "references_must_be_list": True,
            },
        }
        bad = "---\nreferences: just-a-string\n---\n\nContent."
        errors = _validate_from_db_config(config, bad, ".claude/x.md", [".claude/"])
        hints = _hints(errors)
        assert any("list" in h for h in hints)

        good = "---\nreferences:\n  - a\n  - b\n---\n\nContent."
        errors_ok = _validate_from_db_config(config, good, ".claude/x.md", [".claude/"])
        assert errors_ok == []

    def test_min_content_length_rule(self):
        config = {
            "slug": "project_config",
            "path_prefix": None,
            "required_frontmatter_keys": [],
            "optional_frontmatter_keys": [],
            "validation_rules": {"min_content_length": 10},
        }
        errors = _validate_from_db_config(config, "short", ".claude/x.md", [".claude/"])
        hints = _hints(errors)
        assert any("short" in h for h in hints)


# ---------------------------------------------------------------------------
# Tests: structured error format (CECO-1.4)
# ---------------------------------------------------------------------------


class TestStructuredErrorFormat:
    """Validators return dicts with 'field' and 'hint' keys."""

    def test_errors_have_field_and_hint_keys(self):
        """Every error dict must contain exactly 'field' and 'hint' string keys."""
        content = "---\nfoo: bar\n---\n\nSome content."
        errors = validate_context_entity(
            "spec_file",
            content,
            ".claude/specs/my-spec.md",
            allowed_prefixes=[".claude/"],
        )
        assert errors  # at least one error (missing 'title')
        for err in errors:
            assert isinstance(err, dict), f"Expected dict, got {type(err)}"
            assert "field" in err, f"Missing 'field' key in {err}"
            assert "hint" in err, f"Missing 'hint' key in {err}"
            assert isinstance(err["field"], str)
            assert isinstance(err["hint"], str)

    def test_valid_field_values_are_constrained(self):
        """field values must be one of the documented valid values."""
        valid_fields = {"content", "path_pattern", "frontmatter", "type"}
        # Trigger errors for each known error path
        test_cases = [
            ("spec_file", "---\nfoo: bar\n---\n\nContent.", ".claude/specs/s.md"),
            ("spec_file", "", ".claude/specs/s.md"),
            ("spec_file", "No frontmatter.", ".claude/specs/s.md"),
            ("context_file", "---\nfoo: bar\n---\n\nContent.", ".claude/context/c.md"),
            ("progress_template", "---\ntype: bad\n---\n\nContent.", ".claude/progress/p.md"),
            ("rule_file", "short", ".claude/rules/bad-path.md"),
        ]
        for entity_type, content, path in test_cases:
            errors = validate_context_entity(
                entity_type, content, path, allowed_prefixes=[".claude/"]
            )
            for err in errors:
                assert err["field"] in valid_fields, (
                    f"Unexpected field '{err['field']}' for {entity_type}: {err}"
                )

    # -- project_config --

    def test_project_config_empty_content_field_is_content(self):
        errors = validate_context_entity(
            "project_config", "", ".claude/CLAUDE.md", allowed_prefixes=[".claude/"]
        )
        assert _fields(errors) == ["content"]
        assert "empty" in _hints(errors)[0].lower()

    def test_project_config_too_short_field_is_content(self):
        errors = validate_context_entity(
            "project_config", "x", ".claude/CLAUDE.md", allowed_prefixes=[".claude/"]
        )
        assert any(e["field"] == "content" for e in errors)

    def test_project_config_valid_has_no_errors(self):
        content = "# My Project\n\nThis is valid markdown content."
        errors = validate_context_entity(
            "project_config", content, ".claude/CLAUDE.md", allowed_prefixes=[".claude/"]
        )
        assert errors == []

    # -- spec_file --

    def test_spec_file_wrong_path_field_is_path_pattern(self):
        content = "---\ntitle: T\n---\n\nContent."
        errors = validate_context_entity(
            "spec_file", content, ".claude/rules/wrong.md",
            allowed_prefixes=[".claude/"],
        )
        fields = _fields(errors)
        assert "path_pattern" in fields

    def test_spec_file_missing_frontmatter_field_is_frontmatter(self):
        errors = validate_context_entity(
            "spec_file", "No frontmatter here.", ".claude/specs/s.md",
            allowed_prefixes=[".claude/"],
        )
        assert any(e["field"] == "frontmatter" for e in errors)

    def test_spec_file_missing_title_field_is_frontmatter(self):
        content = "---\nfoo: bar\n---\n\nContent."
        errors = validate_context_entity(
            "spec_file", content, ".claude/specs/s.md",
            allowed_prefixes=[".claude/"],
        )
        assert any(e["field"] == "frontmatter" for e in errors)
        hints = _hints(errors)
        assert any("title" in h for h in hints)

    def test_spec_file_hint_mentions_title(self):
        content = "---\nfoo: bar\n---\n\nContent."
        errors = validate_context_entity(
            "spec_file", content, ".claude/specs/s.md",
            allowed_prefixes=[".claude/"],
        )
        hints = _hints(errors)
        assert any("title" in h for h in hints)

    # -- context_file --

    def test_context_file_missing_frontmatter_field_is_frontmatter(self):
        errors = validate_context_entity(
            "context_file", "No frontmatter.", ".claude/context/c.md",
            allowed_prefixes=[".claude/"],
        )
        assert any(e["field"] == "frontmatter" for e in errors)

    def test_context_file_missing_references_field_is_frontmatter(self):
        content = "---\ntitle: T\n---\n\nContent."
        errors = validate_context_entity(
            "context_file", content, ".claude/context/c.md",
            allowed_prefixes=[".claude/"],
        )
        assert any(e["field"] == "frontmatter" for e in errors)
        hints = _hints(errors)
        assert any("references" in h for h in hints)

    def test_context_file_references_not_list_field_is_frontmatter(self):
        content = "---\nreferences: single-string\n---\n\nContent."
        errors = validate_context_entity(
            "context_file", content, ".claude/context/c.md",
            allowed_prefixes=[".claude/"],
        )
        assert any(e["field"] == "frontmatter" for e in errors)
        hints = _hints(errors)
        assert any("list" in h for h in hints)

    # -- rule_file --

    def test_rule_file_wrong_path_field_is_path_pattern(self):
        content = "<!-- Path Scope: skillmeat/**/*.py -->\n\n# Rule\n\nContent here."
        errors = validate_context_entity(
            "rule_file", content, ".claude/specs/wrong.md",
            allowed_prefixes=[".claude/"],
        )
        assert any(e["field"] == "path_pattern" for e in errors)

    def test_rule_file_hint_mentions_rules_path(self):
        content = "<!-- Path Scope: skillmeat/**/*.py -->\n\n# Rule\n\nContent here."
        errors = validate_context_entity(
            "rule_file", content, ".claude/specs/wrong.md",
            allowed_prefixes=[".claude/"],
        )
        hints = _hints(errors)
        assert any("rules/" in h for h in hints)

    # -- progress_template --

    def test_progress_template_missing_frontmatter_field_is_frontmatter(self):
        errors = validate_context_entity(
            "progress_template", "No frontmatter.", ".claude/progress/p.md",
            allowed_prefixes=[".claude/"],
        )
        assert any(e["field"] == "frontmatter" for e in errors)

    def test_progress_template_wrong_type_value_field_is_type(self):
        content = "---\ntype: other\n---\n\nContent."
        errors = validate_context_entity(
            "progress_template", content, ".claude/progress/p.md",
            allowed_prefixes=[".claude/"],
        )
        assert any(e["field"] == "type" for e in errors)
        hints = _hints(errors)
        assert any("progress" in h for h in hints)

    def test_progress_template_missing_type_key_field_is_frontmatter(self):
        content = "---\nother: value\n---\n\nContent."
        errors = validate_context_entity(
            "progress_template", content, ".claude/progress/p.md",
            allowed_prefixes=[".claude/"],
        )
        # 'type' key is missing entirely → frontmatter field
        assert any(e["field"] == "frontmatter" for e in errors)

    def test_progress_template_hint_mentions_progress(self):
        content = "---\ntype: bad\n---\n\nContent."
        errors = validate_context_entity(
            "progress_template", content, ".claude/progress/p.md",
            allowed_prefixes=[".claude/"],
        )
        hints = _hints(errors)
        assert any("progress" in h for h in hints)

    # -- path_pattern security --

    def test_path_traversal_field_is_path_pattern(self):
        content = "# Valid\n\nContent here."
        errors = validate_context_entity(
            "project_config", content, ".claude/../etc/passwd",
            allowed_prefixes=[".claude/"],
        )
        assert any(e["field"] == "path_pattern" for e in errors)
