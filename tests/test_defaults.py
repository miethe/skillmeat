"""Tests for SmartDefaults module."""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from skillmeat.defaults import SmartDefaults, defaults


class TestDetectOutputFormat:
    """Tests for detect_output_format()."""

    def test_returns_table_when_tty(self):
        """Should return 'table' when stdout is a TTY."""
        with patch.object(sys.stdout, "isatty", return_value=True):
            with patch.dict(os.environ, {}, clear=True):
                result = SmartDefaults.detect_output_format()
                assert result == "table"

    def test_returns_json_when_piped(self):
        """Should return 'json' when stdout is not a TTY."""
        with patch.object(sys.stdout, "isatty", return_value=False):
            with patch.dict(os.environ, {}, clear=True):
                result = SmartDefaults.detect_output_format()
                assert result == "json"

    def test_env_override_json(self):
        """Should return 'json' when CLAUDECTL_JSON is set."""
        with patch.object(sys.stdout, "isatty", return_value=True):
            with patch.dict(os.environ, {"CLAUDECTL_JSON": "1"}):
                result = SmartDefaults.detect_output_format()
                assert result == "json"

    def test_env_override_takes_precedence(self):
        """CLAUDECTL_JSON should take precedence over TTY."""
        with patch.object(sys.stdout, "isatty", return_value=True):
            with patch.dict(os.environ, {"CLAUDECTL_JSON": "true"}):
                result = SmartDefaults.detect_output_format()
                assert result == "json"

    def test_env_override_with_piped_output(self):
        """CLAUDECTL_JSON should work even when piped."""
        with patch.object(sys.stdout, "isatty", return_value=False):
            with patch.dict(os.environ, {"CLAUDECTL_JSON": "1"}):
                result = SmartDefaults.detect_output_format()
                assert result == "json"


class TestDetectArtifactType:
    """Tests for detect_artifact_type()."""

    @pytest.mark.parametrize(
        "name,expected",
        [
            # Command patterns
            ("my-cli", "command"),
            ("tool-cmd", "command"),
            ("helper-command", "command"),
            ("MY-CLI", "command"),  # Case insensitive
            ("TOOL-CMD", "command"),
            ("Helper-Command", "command"),
            # Agent patterns
            ("my-agent", "agent"),
            ("helper-bot", "agent"),
            ("AI-AGENT", "agent"),  # Case insensitive
            ("Helper-Bot", "agent"),
            # Default to skill
            ("my-skill", "skill"),
            ("canvas", "skill"),
            ("pdf-tools", "skill"),
            ("", "skill"),  # Empty string
            ("random-name", "skill"),
            ("some-thing", "skill"),
            ("no-pattern-match", "skill"),
            # Edge cases
            ("cli", "skill"),  # Must be suffix, not standalone
            ("agent", "skill"),  # Must be suffix, not standalone
            ("prefix-cli-suffix", "skill"),  # Must be at end
            ("my-cli-tool", "skill"),  # Must be final suffix
        ],
    )
    def test_artifact_type_detection(self, name, expected):
        """Should detect artifact type from name patterns."""
        result = SmartDefaults.detect_artifact_type(name)
        assert result == expected

    def test_pattern_order_matters(self):
        """First matching pattern should win."""
        # Command pattern should match before any other
        result = SmartDefaults.detect_artifact_type("my-tool-cli")
        assert result == "command"


class TestGetDefaultProject:
    """Tests for get_default_project()."""

    def test_returns_cwd(self):
        """Should return current working directory."""
        expected = Path.cwd()
        result = SmartDefaults.get_default_project()
        assert result == expected

    def test_returns_path_object(self):
        """Should return a Path object."""
        result = SmartDefaults.get_default_project()
        assert isinstance(result, Path)


class TestGetDefaultCollection:
    """Tests for get_default_collection()."""

    def test_returns_active_collection(self):
        """Should return active_collection from config."""
        config = {"active_collection": "my-collection"}
        result = SmartDefaults.get_default_collection(config)
        assert result == "my-collection"

    def test_returns_default_when_missing(self):
        """Should return 'default' when not in config."""
        result = SmartDefaults.get_default_collection({})
        assert result == "default"

    def test_returns_none_when_value_is_none(self):
        """Should return None when value is explicitly None in config.

        Note: dict.get() returns the actual value if key exists, even if None.
        Only missing keys return the default value.
        """
        config = {"active_collection": None}
        result = SmartDefaults.get_default_collection(config)
        assert result is None

    def test_ignores_other_config_keys(self):
        """Should only look for active_collection key."""
        config = {
            "other_key": "some-value",
            "another_key": "another-value",
        }
        result = SmartDefaults.get_default_collection(config)
        assert result == "default"

    def test_preserves_collection_name(self):
        """Should preserve the exact collection name."""
        config = {"active_collection": "My-Special-Collection-123"}
        result = SmartDefaults.get_default_collection(config)
        assert result == "My-Special-Collection-123"


class TestApplyDefaults:
    """Tests for apply_defaults()."""

    def _make_context(self, smart_defaults=True, config=None):
        """Create a mock Click context."""
        ctx = MagicMock()
        ctx.obj = {
            "smart_defaults": smart_defaults,
            "config": config or {},
        }
        return ctx

    def test_applies_when_flag_set(self):
        """Should apply defaults when smart_defaults is True."""
        ctx = self._make_context(smart_defaults=True)
        params = {}

        result = SmartDefaults.apply_defaults(ctx, params)

        assert "project" in result
        assert "format" in result
        assert "collection" in result

    def test_skips_when_flag_not_set(self):
        """Should not apply defaults when smart_defaults is False."""
        ctx = self._make_context(smart_defaults=False)
        params = {}

        result = SmartDefaults.apply_defaults(ctx, params)

        assert result == {}

    def test_respects_explicit_overrides(self):
        """Should not override explicitly set values."""
        ctx = self._make_context(smart_defaults=True)
        params = {
            "project": Path("/explicit/path"),
            "format": "yaml",
            "collection": "explicit-collection",
        }

        result = SmartDefaults.apply_defaults(ctx, params)

        assert result["project"] == Path("/explicit/path")
        assert result["format"] == "yaml"
        assert result["collection"] == "explicit-collection"

    def test_applies_type_when_name_present(self):
        """Should infer type when name is present but type is not."""
        ctx = self._make_context(smart_defaults=True)
        params = {"name": "my-cli"}

        result = SmartDefaults.apply_defaults(ctx, params)

        assert result["type"] == "command"

    def test_skips_type_when_explicitly_set(self):
        """Should not override explicit type."""
        ctx = self._make_context(smart_defaults=True)
        params = {"name": "my-cli", "type": "skill"}

        result = SmartDefaults.apply_defaults(ctx, params)

        assert result["type"] == "skill"

    def test_skips_type_when_no_name(self):
        """Should not apply type default when name is missing."""
        ctx = self._make_context(smart_defaults=True)
        params = {}

        result = SmartDefaults.apply_defaults(ctx, params)

        assert "type" not in result

    def test_uses_config_for_collection_default(self):
        """Should use config to determine collection default."""
        ctx = self._make_context(
            smart_defaults=True, config={"active_collection": "from-config"}
        )
        params = {}

        result = SmartDefaults.apply_defaults(ctx, params)

        assert result["collection"] == "from-config"

    def test_handles_missing_config(self):
        """Should handle missing config gracefully."""
        ctx = MagicMock()
        ctx.obj = {"smart_defaults": True}  # No config key
        params = {}

        result = SmartDefaults.apply_defaults(ctx, params)

        # Should still apply defaults with empty config
        assert "project" in result
        assert "format" in result
        assert "collection" in result
        assert result["collection"] == "default"

    def test_preserves_existing_params(self):
        """Should preserve params that are not defaults."""
        ctx = self._make_context(smart_defaults=True)
        params = {
            "custom_param": "custom_value",
            "another_param": 123,
        }

        result = SmartDefaults.apply_defaults(ctx, params)

        assert result["custom_param"] == "custom_value"
        assert result["another_param"] == 123

    def test_type_detection_with_agent_name(self):
        """Should detect agent type from name."""
        ctx = self._make_context(smart_defaults=True)
        params = {"name": "helper-bot"}

        result = SmartDefaults.apply_defaults(ctx, params)

        assert result["type"] == "agent"

    def test_type_detection_defaults_to_skill(self):
        """Should default type to skill for non-matching names."""
        ctx = self._make_context(smart_defaults=True)
        params = {"name": "canvas"}

        result = SmartDefaults.apply_defaults(ctx, params)

        assert result["type"] == "skill"

    @patch.object(SmartDefaults, "get_default_project")
    @patch.object(SmartDefaults, "detect_output_format")
    def test_calls_detection_methods(self, mock_format, mock_project):
        """Should call detection methods when applying defaults."""
        mock_project.return_value = Path("/mocked/path")
        mock_format.return_value = "json"

        ctx = self._make_context(smart_defaults=True)
        params = {}

        result = SmartDefaults.apply_defaults(ctx, params)

        mock_project.assert_called_once()
        mock_format.assert_called_once()
        assert result["project"] == Path("/mocked/path")
        assert result["format"] == "json"


class TestDefaultsInstance:
    """Tests for the module-level defaults instance."""

    def test_instance_exists(self):
        """Should export a defaults instance."""
        assert defaults is not None
        assert isinstance(defaults, SmartDefaults)

    def test_instance_has_methods(self):
        """Instance should have all expected methods."""
        assert hasattr(defaults, "detect_output_format")
        assert hasattr(defaults, "detect_artifact_type")
        assert hasattr(defaults, "get_default_project")
        assert hasattr(defaults, "get_default_collection")
        assert hasattr(defaults, "apply_defaults")

    def test_instance_methods_callable(self):
        """Instance methods should be callable."""
        assert callable(defaults.detect_output_format)
        assert callable(defaults.detect_artifact_type)
        assert callable(defaults.get_default_project)
        assert callable(defaults.get_default_collection)
        assert callable(defaults.apply_defaults)


class TestSmartDefaultsClassAttributes:
    """Tests for SmartDefaults class attributes."""

    def test_default_type_is_skill(self):
        """Default type should be 'skill'."""
        assert SmartDefaults._DEFAULT_TYPE == "skill"

    def test_type_patterns_structure(self):
        """Type patterns should be a list of tuples."""
        assert isinstance(SmartDefaults._TYPE_PATTERNS, list)
        for pattern, artifact_type in SmartDefaults._TYPE_PATTERNS:
            assert hasattr(pattern, "match")  # Regex pattern
            assert isinstance(artifact_type, str)

    def test_type_patterns_order(self):
        """Type patterns should have command before agent."""
        pattern_types = [t for _, t in SmartDefaults._TYPE_PATTERNS]
        assert "command" in pattern_types
        assert "agent" in pattern_types
        # Command should come before agent (order matters)
        assert pattern_types.index("command") < pattern_types.index("agent")
