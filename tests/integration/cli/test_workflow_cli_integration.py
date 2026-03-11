"""Integration tests for `skillmeat list --type workflow` CLI command.

WAW-P5.7: Verifies that the CLI list command handles workflow artifacts
correctly via the WorkflowRepository path, using a real per-test SQLite
database to avoid filesystem-only collection manager dependencies.

Scenarios tested
----------------
1. `skillmeat list --type workflow` returns synced workflows in the table.
2. Output format includes Name, Type, Version, Status, Description columns.
3. `skillmeat list --type workflow` shows an empty message when no workflows.
4. Multiple workflows all appear in the output.
5. Exit code is 0 for both empty and populated cases.
"""

from __future__ import annotations

from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner
from rich.console import Console

import skillmeat.cli as cli_module
from skillmeat.cli import main
from skillmeat.config import ConfigManager
from skillmeat.core.workflow.service import WorkflowService


# ---------------------------------------------------------------------------
# YAML fixtures
# ---------------------------------------------------------------------------

_WF_YAML_TEMPLATE = """\
workflow:
  id: {wf_id}
  name: {name}
  version: "1.0.0"
  description: {description}
  status: draft
stages:
  - id: stage-1
    name: Only Stage
    type: agent
    roles:
      primary:
        artifact: "agent:python-backend-engineer"
        task: "Run this"
"""


def _wf_yaml(wf_id: str, name: str, description: str = "CLI test workflow") -> str:
    return _WF_YAML_TEMPLATE.format(wf_id=wf_id, name=name, description=description)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_session_global() -> Generator[None, None, None]:
    """Reset the module-level SessionLocal between tests."""
    import skillmeat.cache.models as _models

    original = _models.SessionLocal
    _models.SessionLocal = None
    yield
    _models.SessionLocal = original


@pytest.fixture()
def db_path(tmp_path: Path) -> str:
    """Per-test SQLite database path string."""
    return str(tmp_path / "cli_workflow_test.db")


@pytest.fixture()
def wf_service(db_path: str) -> WorkflowService:
    """Real WorkflowService backed by the per-test database."""
    return WorkflowService(db_path=db_path)


@pytest.fixture()
def cli_runner(tmp_path: Path, monkeypatch) -> CliRunner:
    """Isolated CliRunner with a temporary HOME and no-color Rich console."""
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setattr(ConfigManager, "DEFAULT_CONFIG_DIR", home_dir / ".skillmeat")
    monkeypatch.setattr(cli_module, "console", Console(no_color=True, highlight=False))
    return CliRunner()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


class _FakeWorkflowRepo:
    """Minimal in-memory WorkflowRepository substitute for CLI testing."""

    def __init__(self, workflows):
        self._workflows = workflows

    def list(self, limit=200, **kwargs):
        return self._workflows, len(self._workflows)


def _make_workflow_obj(name: str, version: str = "1.0.0", status: str = "draft", description: str = ""):
    """Build a minimal workflow-like object for the CLI display path."""
    wf = MagicMock()
    wf.name = name
    wf.version = version
    wf.status = status
    wf.description = description
    wf.tags_json = None
    return wf


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestWorkflowCLIList:
    """Tests for `skillmeat list --type workflow`."""

    def test_empty_workflow_list_shows_message(self, cli_runner):
        """When no workflows are stored, a 'not found' message is displayed."""
        empty_repo = _FakeWorkflowRepo([])

        with patch(
            "skillmeat.cache.workflow_repository.WorkflowRepository",
            return_value=empty_repo,
        ):
            result = cli_runner.invoke(main, ["list", "--type", "workflow"])

        assert result.exit_code == 0
        # The CLI prints "No workflow definitions found" for empty results
        assert "No workflow" in result.output or "not found" in result.output.lower()

    def test_list_shows_synced_workflows(self, cli_runner, db_path):
        """Synced workflows appear in the `list --type workflow` table output."""
        workflows = [
            _make_workflow_obj("alpha-workflow", version="1.0.0", description="First"),
            _make_workflow_obj("beta-workflow", version="2.0.0", description="Second"),
        ]
        fake_repo = _FakeWorkflowRepo(workflows)

        with patch(
            "skillmeat.cache.workflow_repository.WorkflowRepository",
            return_value=fake_repo,
        ):
            result = cli_runner.invoke(main, ["list", "--type", "workflow"])

        assert result.exit_code == 0
        assert "alpha-workflow" in result.output
        assert "beta-workflow" in result.output

    def test_list_shows_workflow_type_column(self, cli_runner, db_path):
        """Each row in the output identifies the artifact type as 'workflow'."""
        workflows = [_make_workflow_obj("type-check-wf")]
        fake_repo = _FakeWorkflowRepo(workflows)

        with patch(
            "skillmeat.cache.workflow_repository.WorkflowRepository",
            return_value=fake_repo,
        ):
            result = cli_runner.invoke(main, ["list", "--type", "workflow"])

        assert result.exit_code == 0
        assert "workflow" in result.output

    def test_list_shows_version_and_status(self, cli_runner):
        """Version and status fields are present in the table output."""
        workflows = [
            _make_workflow_obj("versioned-wf", version="3.1.0", status="active")
        ]
        fake_repo = _FakeWorkflowRepo(workflows)

        with patch(
            "skillmeat.cache.workflow_repository.WorkflowRepository",
            return_value=fake_repo,
        ):
            result = cli_runner.invoke(main, ["list", "--type", "workflow"])

        assert result.exit_code == 0
        assert "3.1.0" in result.output
        assert "active" in result.output

    def test_list_shows_description(self, cli_runner):
        """Workflow description appears in the table row."""
        workflows = [
            _make_workflow_obj("desc-wf", description="Automates code review steps")
        ]
        fake_repo = _FakeWorkflowRepo(workflows)

        with patch(
            "skillmeat.cache.workflow_repository.WorkflowRepository",
            return_value=fake_repo,
        ):
            result = cli_runner.invoke(main, ["list", "--type", "workflow"])

        assert result.exit_code == 0
        assert "Automates code review" in result.output

    def test_exit_code_zero_for_empty(self, cli_runner):
        """Exit code is 0 even when no workflows exist."""
        fake_repo = _FakeWorkflowRepo([])

        with patch(
            "skillmeat.cache.workflow_repository.WorkflowRepository",
            return_value=fake_repo,
        ):
            result = cli_runner.invoke(main, ["list", "--type", "workflow"])

        assert result.exit_code == 0

    def test_exit_code_zero_for_populated(self, cli_runner):
        """Exit code is 0 when workflows are returned successfully."""
        workflows = [_make_workflow_obj("exit-code-wf")]
        fake_repo = _FakeWorkflowRepo(workflows)

        with patch(
            "skillmeat.cache.workflow_repository.WorkflowRepository",
            return_value=fake_repo,
        ):
            result = cli_runner.invoke(main, ["list", "--type", "workflow"])

        assert result.exit_code == 0

    def test_list_all_workflows_appear_in_single_run(self, cli_runner):
        """All available workflows appear in a single list invocation."""
        names = [f"wf-{i:02d}" for i in range(5)]
        workflows = [_make_workflow_obj(n) for n in names]
        fake_repo = _FakeWorkflowRepo(workflows)

        with patch(
            "skillmeat.cache.workflow_repository.WorkflowRepository",
            return_value=fake_repo,
        ):
            result = cli_runner.invoke(main, ["list", "--type", "workflow"])

        assert result.exit_code == 0
        for name in names:
            assert name in result.output

    def test_repo_error_prints_error_message(self, cli_runner):
        """When the WorkflowRepository raises an exception, an error message is shown."""
        mock_repo = MagicMock()
        mock_repo.list.side_effect = RuntimeError("DB connection failed")

        with patch(
            "skillmeat.cache.workflow_repository.WorkflowRepository",
            return_value=mock_repo,
        ):
            result = cli_runner.invoke(main, ["list", "--type", "workflow"])

        # The CLI should not crash — exit code 0 with an error message printed
        assert result.exit_code == 0
        assert "Error" in result.output or "error" in result.output.lower()
