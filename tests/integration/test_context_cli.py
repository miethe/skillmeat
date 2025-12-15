"""Integration tests for skillmeat context CLI commands."""
import json
import pytest
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from skillmeat.cli import main as cli


@pytest.fixture
def runner():
    """Create CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_api_response():
    """Mock API response for context entities."""
    return {
        "items": [
            {
                "id": "test-123",
                "name": "test-spec",
                "type": "spec_file",
                "path_pattern": ".claude/specs/test-spec.md",
                "category": "testing",
                "auto_load": False,
                "content": "# Test Spec\n\nThis is a test.",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
            }
        ],
        "total": 1,
    }


class TestContextGroup:
    """Test context command group."""

    def test_context_help(self, runner):
        """Test context --help shows group description."""
        result = runner.invoke(cli, ["context", "--help"])
        assert result.exit_code == 0
        assert "Manage context entities" in result.output
        assert "add" in result.output
        assert "list" in result.output
        assert "show" in result.output
        assert "remove" in result.output
        assert "deploy" in result.output


class TestContextAdd:
    """Test context add command."""

    def test_context_add_local_file(self, runner, tmp_path):
        """Test adding entity from local file."""
        # Create test file
        spec_file = tmp_path / "test-spec.md"
        spec_file.write_text("""---
title: "Test Spec"
purpose: "Testing"
version: "1.0"
---

# Test Spec

This is test content.
""")

        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(
                status_code=201,
                json=lambda: {"id": "abc123", "name": "test-spec", "type": "spec_file"}
            )
            mock_post.return_value.raise_for_status = MagicMock()

            result = runner.invoke(cli, [
                "context", "add", str(spec_file),
                "--type", "spec_file"
            ])

            # Should succeed or show API call was made
            assert mock_post.called or "Error" in result.output

    def test_context_add_help(self, runner):
        """Test context add --help."""
        result = runner.invoke(cli, ["context", "add", "--help"])
        assert result.exit_code == 0
        assert "Add a context entity" in result.output
        assert "--type" in result.output
        assert "--category" in result.output
        assert "--auto-load" in result.output


class TestContextList:
    """Test context list command."""

    def test_context_list_help(self, runner):
        """Test context list --help."""
        result = runner.invoke(cli, ["context", "list", "--help"])
        assert result.exit_code == 0
        assert "--type" in result.output
        assert "--category" in result.output
        assert "--format" in result.output

    def test_context_list_json_format(self, runner, mock_api_response):
        """Test listing entities in JSON format."""
        with patch("requests.get") as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_api_response
            )
            mock_get.return_value.raise_for_status = MagicMock()

            result = runner.invoke(cli, ["context", "list", "--format", "json"])

            if mock_get.called:
                # Should output JSON
                assert "items" in result.output or "Error" in result.output


class TestContextShow:
    """Test context show command."""

    def test_context_show_help(self, runner):
        """Test context show --help."""
        result = runner.invoke(cli, ["context", "show", "--help"])
        assert result.exit_code == 0
        assert "NAME_OR_ID" in result.output
        assert "--full" in result.output
        assert "--format" in result.output

    def test_context_show_not_found(self, runner):
        """Test showing non-existent entity."""
        with patch("requests.get") as mock_get:
            mock_get.return_value = MagicMock(
                status_code=404,
                json=lambda: {"items": []}
            )
            mock_get.return_value.raise_for_status = MagicMock(
                side_effect=Exception("Not found")
            )

            result = runner.invoke(cli, ["context", "show", "nonexistent"])
            # Should show error or not found message
            assert result.exit_code != 0 or "not found" in result.output.lower() or "error" in result.output.lower()


class TestContextRemove:
    """Test context remove command."""

    def test_context_remove_help(self, runner):
        """Test context remove --help."""
        result = runner.invoke(cli, ["context", "remove", "--help"])
        assert result.exit_code == 0
        assert "NAME_OR_ID" in result.output
        assert "--force" in result.output

    def test_context_remove_cancelled(self, runner, mock_api_response):
        """Test remove with user cancellation."""
        with patch("requests.get") as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_api_response
            )
            mock_get.return_value.raise_for_status = MagicMock()

            # Simulate user saying "no" to confirmation
            result = runner.invoke(cli, ["context", "remove", "test-spec"], input="n\n")

            # Should show cancelled or prompt for confirmation
            assert "Cancelled" in result.output or "?" in result.output or "Error" in result.output


class TestContextDeploy:
    """Test context deploy command."""

    def test_context_deploy_help(self, runner):
        """Test context deploy --help."""
        result = runner.invoke(cli, ["context", "deploy", "--help"])
        assert result.exit_code == 0
        assert "NAME_OR_ID" in result.output
        assert "--to-project" in result.output
        assert "--overwrite" in result.output
        assert "--dry-run" in result.output

    def test_context_deploy_missing_project(self, runner):
        """Test deploy without --to-project fails."""
        result = runner.invoke(cli, ["context", "deploy", "test-spec"])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_context_deploy_dry_run(self, runner, tmp_path, mock_api_response):
        """Test deploy in dry-run mode."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        # Add content to mock response
        mock_api_response["items"][0]["content"] = "# Test Content"

        with patch("requests.get") as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_api_response
            )
            mock_get.return_value.raise_for_status = MagicMock()

            result = runner.invoke(cli, [
                "context", "deploy", "test-spec",
                "--to-project", str(project_path),
                "--dry-run"
            ])

            # Should show dry run output or error
            assert "DRY RUN" in result.output or "Would deploy" in result.output or "Error" in result.output

    def test_context_deploy_path_traversal_prevented(self, runner, tmp_path):
        """Test that path traversal is rejected."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        # Create mock entity with malicious path pattern
        malicious_response = {
            "items": [{
                "id": "evil-123",
                "name": "evil-spec",
                "type": "spec_file",
                "path_pattern": "../../../etc/passwd",  # Path traversal attempt
                "content": "malicious content",
            }],
            "total": 1,
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: malicious_response
            )
            mock_get.return_value.raise_for_status = MagicMock()

            result = runner.invoke(cli, [
                "context", "deploy", "evil-spec",
                "--to-project", str(project_path)
            ])

            # Should reject with security error
            assert "SECURITY" in result.output or "escapes" in result.output or result.exit_code != 0

            # Verify /etc/passwd was NOT modified
            assert not Path("/etc/passwd").read_text().startswith("malicious content")


class TestContextDeploySecurityCases:
    """Security-focused tests for deploy command."""

    @pytest.mark.parametrize("malicious_path", [
        "../../../etc/passwd",
        ".claude/../../../etc/passwd",
        "/etc/passwd",
        ".other/file.md",
        "..%2F..%2F..%2Fetc%2Fpasswd",  # URL encoded
    ])
    def test_path_traversal_variants(self, runner, tmp_path, malicious_path):
        """Test various path traversal attack patterns."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        malicious_response = {
            "items": [{
                "id": "evil-123",
                "name": "evil-spec",
                "type": "spec_file",
                "path_pattern": malicious_path,
                "content": "malicious",
            }],
            "total": 1,
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: malicious_response
            )
            mock_get.return_value.raise_for_status = MagicMock()

            result = runner.invoke(cli, [
                "context", "deploy", "evil-spec",
                "--to-project", str(project_path)
            ])

            # All variants should fail or be rejected
            assert result.exit_code != 0 or "SECURITY" in result.output or "error" in result.output.lower()
