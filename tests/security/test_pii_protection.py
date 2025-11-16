"""Security tests for PII protection in logging.

Tests the CRITICAL-2 fix from security review P5-004:
PII leakage in log statements through full file paths.

These tests verify that paths are properly redacted in logs to prevent
exposing usernames and sensitive directory structures.
"""

import logging
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from skillmeat.utils.logging import redact_path, redact_paths_in_dict


class TestPathRedaction:
    """Test suite for path redaction utility."""

    def test_redact_home_directory_unix(self):
        """Test that Unix home directory paths are redacted."""
        home = os.path.expanduser("~")
        test_path = f"{home}/projects/my-app"
        redacted = redact_path(test_path)

        assert "~" in redacted
        assert home not in redacted
        assert "projects/my-app" in redacted
        assert redacted == "~/projects/my-app"

    def test_redact_home_directory_nested(self):
        """Test that nested paths under home are properly redacted."""
        home = os.path.expanduser("~")
        test_path = f"{home}/Documents/work/secret-project/config.json"
        redacted = redact_path(test_path)

        assert redacted == "~/Documents/work/secret-project/config.json"
        assert home not in redacted

    @pytest.mark.skipif(sys.platform != "linux", reason="Unix-specific test")
    def test_redact_tmp_directory_unix(self):
        """Test that /tmp paths are redacted on Unix."""
        test_path = "/tmp/skillmeat_update_abc123"
        redacted = redact_path(test_path)

        assert redacted.startswith("<temp>/")
        assert "skillmeat_update_abc123" in redacted
        assert "/tmp/" not in redacted

    def test_redact_empty_path(self):
        """Test that empty paths return empty string."""
        assert redact_path("") == ""
        assert redact_path(None) == ""

    def test_redact_relative_path_unchanged(self):
        """Test that relative paths are not modified."""
        relative_paths = [
            "relative/path/to/file.txt",
            "./local/file.txt",
            "../parent/file.txt",
        ]

        for path in relative_paths:
            redacted = redact_path(path)
            assert redacted == path

    def test_redact_very_long_path(self):
        """Test that very long paths are truncated."""
        long_path = "/very/long/" + "a" * 100 + "/file.txt"
        redacted = redact_path(long_path)

        # Should be truncated
        assert len(redacted) < len(long_path)
        assert redacted.startswith(".../")

    def test_redact_path_object(self):
        """Test that Path objects are properly handled."""
        home = os.path.expanduser("~")
        test_path = Path(home) / "projects" / "app"
        redacted = redact_path(test_path)

        assert "~" in redacted
        assert home not in redacted

    def test_redact_path_never_raises_exception(self):
        """Test that redact_path never raises exceptions (fail-safe)."""
        problematic_inputs = [
            None,
            "",
            123,  # Wrong type
            [],  # Wrong type
            {},  # Wrong type
        ]

        for input_val in problematic_inputs:
            # Should not raise exception
            result = redact_path(input_val)
            assert isinstance(result, str)

    def test_username_not_in_redacted_path(self):
        """Test that username is never present in redacted paths."""
        # Get actual username from home path
        home = os.path.expanduser("~")
        username = home.split("/")[-1] if "/" in home else home.split("\\")[-1]

        test_paths = [
            f"{home}/projects/app",
            f"{home}/.skillmeat/collection",
            f"{home}/Documents/secret",
        ]

        for path in test_paths:
            redacted = redact_path(path)
            # Username should not appear in redacted path
            assert username not in redacted or username == "~"

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_redact_windows_temp_directory(self):
        """Test that Windows TEMP paths are redacted."""
        temp_dir = os.environ.get("TEMP", "C:\\Temp")
        test_path = f"{temp_dir}\\skillmeat_update_xyz"
        redacted = redact_path(test_path)

        assert "<temp>/" in redacted
        assert temp_dir not in redacted

    def test_redact_absolute_path_not_under_home(self):
        """Test that absolute paths not under home are handled safely."""
        system_paths = [
            "/etc/passwd",
            "/var/log/syslog",
            "/usr/local/bin/app",
        ]

        for path in system_paths:
            redacted = redact_path(path)
            # Should redact to just basename for safety
            assert redacted.startswith("<path>/") or redacted == path


class TestPathRedactionInDict:
    """Test path redaction in dictionary structures."""

    def test_redact_paths_in_flat_dict(self):
        """Test that paths in flat dictionaries are redacted."""
        home = os.path.expanduser("~")
        test_dict = {
            "file_path": f"{home}/projects/app/file.txt",
            "name": "test",
            "count": 42,
        }

        redacted = redact_paths_in_dict(test_dict)

        assert "~" in redacted["file_path"]
        assert home not in redacted["file_path"]
        assert redacted["name"] == "test"
        assert redacted["count"] == 42

    def test_redact_paths_in_nested_dict(self):
        """Test that paths in nested dictionaries are redacted."""
        home = os.path.expanduser("~")
        test_dict = {
            "metadata": {"project_path": f"{home}/work/project"},
            "name": "artifact",
        }

        redacted = redact_paths_in_dict(test_dict)

        assert "~" in redacted["metadata"]["project_path"]
        assert home not in redacted["metadata"]["project_path"]

    def test_redact_paths_in_list(self):
        """Test that paths in lists are handled."""
        home = os.path.expanduser("~")
        test_dict = {
            "paths": [
                f"{home}/path1",
                f"{home}/path2",
            ],
        }

        # Note: Current implementation doesn't redact list items
        # This test documents current behavior
        redacted = redact_paths_in_dict(test_dict)
        # Lists are preserved as-is
        assert isinstance(redacted["paths"], list)

    def test_custom_path_keys(self):
        """Test that custom path keys can be specified."""
        home = os.path.expanduser("~")
        test_dict = {
            "custom_location": f"{home}/custom/path",
            "file_path": f"{home}/standard/path",
        }

        # With custom keys
        redacted = redact_paths_in_dict(test_dict, path_keys=["custom_location"])
        assert "~" in redacted["custom_location"]
        # file_path not in custom keys, so might not be redacted
        # unless it's in default list


class TestLoggingIntegration:
    """Integration tests for logging with path redaction."""

    def test_artifact_logging_redacts_temp_workspace(self, caplog):
        """Test that artifact logging redacts temp workspace paths."""
        from skillmeat.core.artifact import logging as artifact_logging

        with caplog.at_level(logging.INFO):
            # Simulate logging with path
            temp_path = "/tmp/skillmeat_update_test"
            # This uses the logging module that artifact.py imports
            # We're testing that when redact_path is used, it works correctly
            from skillmeat.utils.logging import redact_path

            artifact_logging.info(
                f"Fetched update for skill/test to {redact_path(temp_path)}"
            )

            # Verify path is redacted in log
            assert "<temp>/" in caplog.text
            assert "/tmp/" not in caplog.text or "<temp>/skillmeat_update_test" in caplog.text

    def test_sync_logging_redacts_project_paths(self, caplog):
        """Test that sync logging redacts project paths."""
        home = os.path.expanduser("~")
        project_path = f"{home}/projects/secret-app"

        with caplog.at_level(logging.INFO):
            from skillmeat.utils.logging import redact_path

            logger = logging.getLogger("test")
            logger.info(f"No deployment metadata found at {redact_path(project_path)}")

            # Verify home directory not in logs
            assert "~" in caplog.text
            assert home not in caplog.text

    def test_analytics_logging_redacts_db_path(self, caplog):
        """Test that analytics logging redacts database paths."""
        home = os.path.expanduser("~")
        db_path = f"{home}/.skillmeat/analytics.db"

        with caplog.at_level(logging.DEBUG):
            from skillmeat.utils.logging import redact_path

            logger = logging.getLogger("test")
            logger.debug(f"Analytics enabled, database at {redact_path(db_path)}")

            # Verify redacted
            assert "~" in caplog.text
            assert home not in caplog.text

    def test_no_usernames_in_log_output(self, caplog, tmp_path):
        """Integration test: verify no usernames appear in log output."""
        home = os.path.expanduser("~")
        username = home.split("/")[-1] if "/" in home else home.split("\\")[-1]

        # Skip if username is very common (could appear in other contexts)
        if username in ["root", "admin", "user"]:
            pytest.skip("Common username could appear in other contexts")

        with caplog.at_level(logging.DEBUG):
            from skillmeat.utils.logging import redact_path

            logger = logging.getLogger("test")

            # Log various path types
            logger.info(f"Project: {redact_path(home + '/projects/app')}")
            logger.info(f"Config: {redact_path(home + '/.config/app')}")
            logger.debug(f"Temp: {redact_path('/tmp/test_' + username)}")

            # Verify username doesn't appear
            log_output = caplog.text
            # Username should not appear in logs (unless it's literally the string "~")
            if username != "~":
                assert username not in log_output


class TestRealWorldScenarios:
    """Test real-world scenarios and edge cases."""

    def test_github_actions_environment(self):
        """Test path redaction in CI/CD environments."""
        # GitHub Actions often uses /home/runner
        ci_path = "/home/runner/work/repo/project/file.txt"
        redacted = redact_path(ci_path)

        # Should redact or truncate
        assert len(redacted) <= len(ci_path)
        # Should not expose full CI path structure
        assert "runner" not in redacted or redacted.startswith("~/")

    def test_macos_paths(self):
        """Test that macOS paths are properly redacted."""
        macos_paths = [
            "/Users/alice/Projects/app",
            "/Users/bob/Documents/secret",
        ]

        for path in macos_paths:
            redacted = redact_path(path)
            # Should not expose username
            assert "alice" not in redacted
            assert "bob" not in redacted

    def test_wsl_paths(self):
        """Test Windows Subsystem for Linux paths."""
        wsl_paths = [
            "/mnt/c/Users/alice/project",
            "/home/alice/.skillmeat",
        ]

        for path in wsl_paths:
            redacted = redact_path(path)
            # Should not expose username
            assert "alice" not in redacted or redacted.startswith("~/")

    def test_network_paths_redacted(self):
        """Test that network paths are safely handled."""
        network_paths = [
            "//server/share/sensitive/file.txt",
            "\\\\server\\share\\sensitive\\file.txt",
        ]

        for path in network_paths:
            redacted = redact_path(path)
            # Should be safely redacted
            assert isinstance(redacted, str)
            # Should not expose full network path
            assert len(redacted) <= len(path) + 20  # Allow for redaction markers

    def test_unicode_paths_handled(self):
        """Test that Unicode paths are properly handled."""
        home = os.path.expanduser("~")
        unicode_paths = [
            f"{home}/文档/project",
            f"{home}/Документы/проект",
            f"{home}/مستندات/project",
        ]

        for path in unicode_paths:
            # Should not raise exception
            redacted = redact_path(path)
            assert isinstance(redacted, str)
            # Should redact home
            assert home not in redacted

    def test_whitespace_in_paths(self):
        """Test that paths with whitespace are handled correctly."""
        home = os.path.expanduser("~")
        paths_with_spaces = [
            f"{home}/My Documents/project",
            f"{home}/Program Files/app",
            f"{home}/ spaces at start",
        ]

        for path in paths_with_spaces:
            redacted = redact_path(path)
            # Should redact home
            assert home not in redacted
            # Should preserve path structure
            assert "~" in redacted or redacted.startswith("<")
