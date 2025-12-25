"""Shell compatibility tests for claudectl completions.

Tests the bash, zsh, and fish completion scripts for syntax validity
and basic functionality requirements.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent


class TestBashCompletion:
    """Tests for bash completion script."""

    completion_file = PROJECT_ROOT / "bash" / "claudectl-completion.bash"

    def test_file_exists(self):
        """Completion file should exist."""
        assert self.completion_file.exists(), f"Missing: {self.completion_file}"

    def test_bash_syntax(self):
        """Bash syntax should be valid."""
        if not self.completion_file.exists():
            pytest.skip("Completion file not found")

        result = subprocess.run(
            ["bash", "-n", str(self.completion_file)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Bash syntax error: {result.stderr}"

    def test_contains_completion_function(self):
        """Should define _claudectl_complete function."""
        if not self.completion_file.exists():
            pytest.skip("Completion file not found")

        content = self.completion_file.read_text()
        assert "_claudectl_complete" in content or "_claudectl" in content

    def test_registers_completion(self):
        """Should register completion with 'complete' command."""
        if not self.completion_file.exists():
            pytest.skip("Completion file not found")

        content = self.completion_file.read_text()
        assert "complete " in content
        assert "claudectl" in content

    def test_contains_main_commands(self):
        """Should contain main command names."""
        if not self.completion_file.exists():
            pytest.skip("Completion file not found")

        content = self.completion_file.read_text()
        expected_commands = ["quick-add", "deploy", "remove", "undeploy", "search", "list"]
        for cmd in expected_commands:
            assert cmd in content, f"Missing command: {cmd}"


class TestZshCompletion:
    """Tests for zsh completion script."""

    completion_file = PROJECT_ROOT / "zsh" / "_claudectl"

    def test_file_exists(self):
        """Completion file should exist."""
        assert self.completion_file.exists(), f"Missing: {self.completion_file}"

    def test_starts_with_compdef(self):
        """Zsh completion should start with #compdef."""
        if not self.completion_file.exists():
            pytest.skip("Completion file not found")

        content = self.completion_file.read_text()
        assert content.strip().startswith("#compdef")

    def test_defines_completion_function(self):
        """Should define _claudectl function."""
        if not self.completion_file.exists():
            pytest.skip("Completion file not found")

        content = self.completion_file.read_text()
        assert "_claudectl()" in content or "_claudectl ()" in content

    def test_contains_main_commands(self):
        """Should contain main command names."""
        if not self.completion_file.exists():
            pytest.skip("Completion file not found")

        content = self.completion_file.read_text()
        expected_commands = ["quick-add", "deploy", "remove", "undeploy", "search", "list"]
        for cmd in expected_commands:
            assert cmd in content, f"Missing command: {cmd}"

    def test_uses_arguments_or_describe(self):
        """Should use _arguments or _describe for completion."""
        if not self.completion_file.exists():
            pytest.skip("Completion file not found")

        content = self.completion_file.read_text()
        assert "_arguments" in content or "_describe" in content


class TestFishCompletion:
    """Tests for fish completion script."""

    completion_file = PROJECT_ROOT / "fish" / "claudectl.fish"

    def test_file_exists(self):
        """Completion file should exist."""
        assert self.completion_file.exists(), f"Missing: {self.completion_file}"

    def test_fish_syntax(self):
        """Fish syntax should be valid (if fish is available)."""
        if not self.completion_file.exists():
            pytest.skip("Completion file not found")

        # Check if fish is available
        try:
            subprocess.run(["fish", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pytest.skip("fish shell not available")

        result = subprocess.run(
            ["fish", "-n", str(self.completion_file)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Fish syntax error: {result.stderr}"

    def test_uses_complete_command(self):
        """Should use 'complete' command for registration."""
        if not self.completion_file.exists():
            pytest.skip("Completion file not found")

        content = self.completion_file.read_text()
        assert "complete -c claudectl" in content

    def test_contains_main_commands(self):
        """Should contain main command names."""
        if not self.completion_file.exists():
            pytest.skip("Completion file not found")

        content = self.completion_file.read_text()
        expected_commands = ["quick-add", "deploy", "remove", "undeploy", "search", "list"]
        for cmd in expected_commands:
            assert cmd in content, f"Missing command: {cmd}"


class TestShellVersionRequirements:
    """Document shell version requirements."""

    def test_document_bash_requirements(self):
        """Bash 4+ is required for completion."""
        # This is a documentation test - just verify we can check versions
        try:
            result = subprocess.run(
                ["bash", "--version"],
                capture_output=True,
                text=True,
            )
            version_line = result.stdout.split('\n')[0]
            # Bash should be 4.0 or higher
            assert "version" in version_line.lower()
        except FileNotFoundError:
            pytest.skip("bash not available")

    def test_document_zsh_requirements(self):
        """Zsh 5+ is required for completion."""
        try:
            result = subprocess.run(
                ["zsh", "--version"],
                capture_output=True,
                text=True,
            )
            assert "zsh" in result.stdout.lower()
        except FileNotFoundError:
            pytest.skip("zsh not available")

    def test_document_fish_requirements(self):
        """Fish 3+ is required for completion."""
        try:
            result = subprocess.run(
                ["fish", "--version"],
                capture_output=True,
                text=True,
            )
            assert "fish" in result.stdout.lower()
        except FileNotFoundError:
            pytest.skip("fish not available")


class TestCompletionFilesPresent:
    """Verify all completion files are present."""

    def test_all_completion_files_exist(self):
        """All three shell completion files should exist."""
        files = [
            PROJECT_ROOT / "bash" / "claudectl-completion.bash",
            PROJECT_ROOT / "zsh" / "_claudectl",
            PROJECT_ROOT / "fish" / "claudectl.fish",
        ]

        missing = [f for f in files if not f.exists()]
        assert not missing, f"Missing completion files: {missing}"
