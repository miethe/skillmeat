"""CLI integration tests for alias commands (P1-T8)."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from skillmeat.cli import main


@pytest.fixture
def runner():
    """Create Click test runner."""
    return CliRunner()


class TestAliasCommand:
    """Test alias management commands."""

    def test_alias_help(self, runner):
        """Test alias command shows help."""
        result = runner.invoke(main, ["alias", "--help"])
        assert result.exit_code == 0
        assert "claudectl alias and shell integration" in result.output
        assert "install" in result.output
        assert "uninstall" in result.output

    def test_install_help(self, runner):
        """Test alias install command shows help."""
        result = runner.invoke(main, ["alias", "install", "--help"])
        assert result.exit_code == 0
        assert "claudectl wrapper" in result.output
        assert "--shells" in result.output
        assert "--force" in result.output

    def test_uninstall_help(self, runner):
        """Test alias uninstall command shows help."""
        result = runner.invoke(main, ["alias", "uninstall", "--help"])
        assert result.exit_code == 0
        assert "Remove claudectl wrapper" in result.output
        assert "--all" in result.output

    def test_install_creates_wrapper(self, runner):
        """Test install command creates wrapper script."""
        with runner.isolated_filesystem():
            with tempfile.TemporaryDirectory() as tmpdir:
                wrapper_path = Path(tmpdir) / "claudectl"

                with patch("skillmeat.wrapper.get_wrapper_path") as mock_get_path:
                    with patch("skillmeat.cli._install_shell_completion"):
                        mock_get_path.return_value = wrapper_path

                        result = runner.invoke(main, ["alias", "install"])

                        # Should succeed (exit code 0)
                        assert result.exit_code == 0

                        # Wrapper should be created
                        assert wrapper_path.exists()

                        # Wrapper should be executable
                        assert wrapper_path.stat().st_mode & 0o111

                        # Wrapper should contain expected content
                        content = wrapper_path.read_text()
                        assert "#!/bin/bash" in content
                        assert "CLAUDECTL_MODE=1" in content
                        assert "skillmeat --smart-defaults" in content

    def test_install_with_force_overwrites(self, runner):
        """Test install with --force overwrites existing wrapper."""
        with runner.isolated_filesystem():
            with tempfile.TemporaryDirectory() as tmpdir:
                wrapper_path = Path(tmpdir) / "claudectl"

                # Create existing wrapper
                wrapper_path.write_text("old content")

                with patch("skillmeat.wrapper.get_wrapper_path") as mock_get_path:
                    with patch("skillmeat.cli._install_shell_completion"):
                        mock_get_path.return_value = wrapper_path

                        result = runner.invoke(main, ["alias", "install", "--force"])

                        assert result.exit_code == 0

                        # Content should be new wrapper
                        content = wrapper_path.read_text()
                        assert "CLAUDECTL_MODE=1" in content
                        assert "old content" not in content

    def test_install_with_multiple_shells(self, runner):
        """Test install with multiple shells."""
        with runner.isolated_filesystem():
            with tempfile.TemporaryDirectory() as tmpdir:
                wrapper_path = Path(tmpdir) / "claudectl"

                with patch("skillmeat.wrapper.get_wrapper_path") as mock_get_path:
                    with patch("skillmeat.cli._install_shell_completion") as mock_install_comp:
                        mock_get_path.return_value = wrapper_path

                        result = runner.invoke(
                            main, ["alias", "install", "--shells", "bash", "--shells", "zsh"]
                        )

                        assert result.exit_code == 0

                        # Should try to install for both shells
                        assert mock_install_comp.call_count == 2

    def test_uninstall_removes_wrapper(self, runner):
        """Test uninstall removes wrapper."""
        with runner.isolated_filesystem():
            with tempfile.TemporaryDirectory() as tmpdir:
                wrapper_path = Path(tmpdir) / "claudectl"
                wrapper_path.write_text("wrapper content")

                with patch("skillmeat.wrapper.get_wrapper_path") as mock_get_path:
                    mock_get_path.return_value = wrapper_path

                    result = runner.invoke(main, ["alias", "uninstall"])

                    assert result.exit_code == 0
                    assert not wrapper_path.exists()

    def test_uninstall_with_all_flag(self, runner):
        """Test uninstall --all removes completions too."""
        with runner.isolated_filesystem():
            with tempfile.TemporaryDirectory() as tmpdir:
                wrapper_path = Path(tmpdir) / "claudectl"
                wrapper_path.write_text("wrapper content")

                with patch("skillmeat.wrapper.get_wrapper_path") as mock_get_path:
                    with patch("skillmeat.cli._uninstall_shell_completion") as mock_uninstall:
                        mock_get_path.return_value = wrapper_path
                        mock_uninstall.return_value = "/path/to/completion"

                        result = runner.invoke(main, ["alias", "uninstall", "--all"])

                        assert result.exit_code == 0

                        # Should try to uninstall completions for all shells
                        assert mock_uninstall.call_count == 3  # bash, zsh, fish

    def test_uninstall_when_nothing_exists(self, runner):
        """Test uninstall when nothing is installed."""
        with runner.isolated_filesystem():
            with tempfile.TemporaryDirectory() as tmpdir:
                wrapper_path = Path(tmpdir) / "claudectl"

                with patch("skillmeat.wrapper.get_wrapper_path") as mock_get_path:
                    mock_get_path.return_value = wrapper_path

                    result = runner.invoke(main, ["alias", "uninstall"])

                    # Should succeed but show nothing to uninstall
                    assert result.exit_code == 0
                    assert "Nothing to uninstall" in result.output or "not found" in result.output
