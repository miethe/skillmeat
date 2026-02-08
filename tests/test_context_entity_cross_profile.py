"""Cross-profile context entity deployment integration tests."""

from click.testing import CliRunner
from unittest.mock import MagicMock, patch

from skillmeat.cli import main as cli


def test_context_entity_dry_run_rewrites_profile_root(tmp_path):
    runner = CliRunner()
    project_path = tmp_path / "project"
    project_path.mkdir()
    (project_path / ".claude").mkdir()
    (project_path / ".codex").mkdir()

    api_payload = {
        "items": [
            {
                "id": "ctx-1",
                "name": "api-spec",
                "type": "spec_file",
                "path_pattern": ".claude/specs/api.md",
                "content": "# API Spec",
            }
        ]
    }

    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: api_payload,
        )
        mock_get.return_value.raise_for_status = MagicMock()

        claude = runner.invoke(
            cli,
            [
                "context",
                "deploy",
                "api-spec",
                "--to-project",
                str(project_path),
                "--profile",
                "claude_code",
                "--dry-run",
            ],
        )
        codex = runner.invoke(
            cli,
            [
                "context",
                "deploy",
                "api-spec",
                "--to-project",
                str(project_path),
                "--profile",
                "codex",
                "--dry-run",
            ],
        )

    assert claude.exit_code == 0
    assert codex.exit_code == 0
    assert ".claude/specs/api.md" in claude.output
    assert ".codex/specs/api.md" in codex.output


def test_context_entity_project_config_discovery_for_profile(tmp_path):
    runner = CliRunner()
    project_path = tmp_path / "project"
    project_path.mkdir()
    (project_path / ".gemini").mkdir()
    (project_path / ".gemini" / "GEMINI.md").write_text("# Gemini Config")

    api_payload = {
        "items": [
            {
                "id": "ctx-2",
                "name": "gemini-config",
                "type": "project_config",
                "path_pattern": "GEMINI.md",
                "content": "# Gemini Config",
            }
        ]
    }

    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: api_payload,
        )
        mock_get.return_value.raise_for_status = MagicMock()

        result = runner.invoke(
            cli,
            [
                "context",
                "deploy",
                "gemini-config",
                "--to-project",
                str(project_path),
                "--profile",
                "gemini",
                "--dry-run",
            ],
        )

    assert result.exit_code == 0
    assert "GEMINI.md" in result.output
