"""CLI integration tests for --members/--no-members deploy flags (SCA feature).

Tests verify that the Click layer correctly passes the include_members flag
through to DeploymentManager.deploy_artifacts(). The deployment layer itself
is exercised in tests/test_deployment_member_artifacts.py; these tests focus
exclusively on the CLI→service boundary.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from skillmeat.cli import main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_deployment_result(artifact_name: str = "test-skill") -> MagicMock:
    """Return a minimal mock DeploymentRecord for a successful deploy."""
    rec = MagicMock()
    rec.artifact_name = artifact_name
    rec.artifact_type = "skill"
    rec.artifact_path = Path(".claude/skills") / artifact_name
    rec.deployment_profile_id = "default"
    rec.platform = MagicMock()
    rec.platform.value = "macos"
    rec.profile_root_dir = str(Path.home() / ".claude")
    return rec


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def runner(tmp_path):
    """CliRunner for invoking CLI commands under test."""
    return CliRunner()


@pytest.fixture()
def project_dir(tmp_path):
    """Minimal project directory with a .claude/ skeleton."""
    claude = tmp_path / ".claude"
    claude.mkdir()
    (claude / "skills").mkdir()
    return tmp_path


# ---------------------------------------------------------------------------
# Core flag tests
# ---------------------------------------------------------------------------


class TestMembersFlagPassthrough:
    """Verify --members/--no-members reach deploy_artifacts() correctly."""

    def _invoke_deploy(
        self, runner: CliRunner, project_dir: Path, extra_args: list
    ) -> tuple:
        """Invoke deploy with a mocked DeploymentManager and return (result, mock)."""
        mock_deploy = MagicMock(return_value=[_make_deployment_result()])

        with patch(
            "skillmeat.cli.DeploymentManager"
        ) as MockMgr:
            MockMgr.return_value.deploy_artifacts = mock_deploy
            result = runner.invoke(
                main,
                ["deploy", "skill:foo", "--project", str(project_dir)] + extra_args,
                catch_exceptions=False,
            )

        return result, mock_deploy

    def test_members_flag_passes_include_members_true(
        self, runner: CliRunner, project_dir: Path
    ):
        """--members should call deploy_artifacts with include_members=True."""
        result, mock_deploy = self._invoke_deploy(
            runner, project_dir, ["--members"]
        )

        assert result.exit_code == 0, result.output
        mock_deploy.assert_called_once()
        _, kwargs = mock_deploy.call_args
        assert kwargs.get("include_members") is True

    def test_no_members_flag_passes_include_members_false(
        self, runner: CliRunner, project_dir: Path
    ):
        """--no-members should call deploy_artifacts with include_members=False."""
        result, mock_deploy = self._invoke_deploy(
            runner, project_dir, ["--no-members"]
        )

        assert result.exit_code == 0, result.output
        mock_deploy.assert_called_once()
        _, kwargs = mock_deploy.call_args
        assert kwargs.get("include_members") is False

    def test_default_behavior_includes_members(
        self, runner: CliRunner, project_dir: Path
    ):
        """When neither flag is given, include_members should default to True."""
        result, mock_deploy = self._invoke_deploy(runner, project_dir, [])

        assert result.exit_code == 0, result.output
        mock_deploy.assert_called_once()
        _, kwargs = mock_deploy.call_args
        assert kwargs.get("include_members") is True

    def test_members_flag_accepted_for_non_skill_artifact(
        self, runner: CliRunner, project_dir: Path
    ):
        """--members is a valid flag for any artifact type; it should not raise."""
        mock_deploy = MagicMock(
            return_value=[_make_deployment_result("my-command")]
        )

        with patch("skillmeat.cli.DeploymentManager") as MockMgr:
            MockMgr.return_value.deploy_artifacts = mock_deploy
            result = runner.invoke(
                main,
                [
                    "deploy",
                    "command:my-command",
                    "--project",
                    str(project_dir),
                    "--members",
                ],
                catch_exceptions=False,
            )

        assert result.exit_code == 0, result.output
        mock_deploy.assert_called_once()
        _, kwargs = mock_deploy.call_args
        assert kwargs.get("include_members") is True

    def test_no_members_flag_accepted_for_non_skill_artifact(
        self, runner: CliRunner, project_dir: Path
    ):
        """--no-members is a valid flag for any artifact type; no error raised."""
        mock_deploy = MagicMock(
            return_value=[_make_deployment_result("my-agent")]
        )

        with patch("skillmeat.cli.DeploymentManager") as MockMgr:
            MockMgr.return_value.deploy_artifacts = mock_deploy
            result = runner.invoke(
                main,
                [
                    "deploy",
                    "agent:my-agent",
                    "--project",
                    str(project_dir),
                    "--no-members",
                ],
                catch_exceptions=False,
            )

        assert result.exit_code == 0, result.output
        mock_deploy.assert_called_once()
        _, kwargs = mock_deploy.call_args
        assert kwargs.get("include_members") is False


# ---------------------------------------------------------------------------
# Output / help tests
# ---------------------------------------------------------------------------


class TestMembersFlagHelp:
    """Verify the --members flag is visible in the deploy help text."""

    def test_deploy_help_shows_members_flag(self):
        """deploy --help must document the --members/--no-members flag."""
        runner = CliRunner()
        result = runner.invoke(main, ["deploy", "--help"])

        assert result.exit_code == 0
        assert "--members" in result.output or "--no-members" in result.output
