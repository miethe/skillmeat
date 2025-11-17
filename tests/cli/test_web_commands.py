"""Tests for web CLI commands."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from skillmeat.cli import main


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


class TestWebDoctor:
    """Tests for 'skillmeat web doctor' command."""

    @patch("skillmeat.web.run_doctor")
    def test_doctor_success(self, mock_run_doctor, runner):
        """Test doctor command success."""
        mock_run_doctor.return_value = True

        result = runner.invoke(main, ["web", "doctor"])

        assert result.exit_code == 0
        mock_run_doctor.assert_called_once()

    @patch("skillmeat.web.run_doctor")
    def test_doctor_failure(self, mock_run_doctor, runner):
        """Test doctor command with failures."""
        mock_run_doctor.return_value = False

        result = runner.invoke(main, ["web", "doctor"])

        assert result.exit_code == 1
        mock_run_doctor.assert_called_once()

    @patch("skillmeat.web.run_doctor")
    def test_doctor_exception(self, mock_run_doctor, runner):
        """Test doctor command with exception."""
        mock_run_doctor.side_effect = Exception("Test error")

        result = runner.invoke(main, ["web", "doctor"])

        assert result.exit_code == 1
        assert "Test error" in result.output


class TestWebDev:
    """Tests for 'skillmeat web dev' command."""

    @patch("skillmeat.web.WebManager")
    @patch("skillmeat.web.check_prerequisites")
    def test_dev_default(self, mock_check_prereqs, mock_manager_class, runner):
        """Test dev command with defaults."""
        mock_check_prereqs.return_value = True
        mock_manager = Mock()
        mock_manager.start_dev.return_value = 0
        mock_manager_class.return_value = mock_manager

        result = runner.invoke(main, ["web", "dev"])

        assert result.exit_code == 0
        mock_check_prereqs.assert_called_once()
        mock_manager_class.assert_called_once_with(
            api_only=False,
            web_only=False,
            api_port=8000,
            web_port=3000,
            api_host="127.0.0.1",
        )
        mock_manager.start_dev.assert_called_once()

    @patch("skillmeat.web.WebManager")
    @patch("skillmeat.web.check_prerequisites")
    def test_dev_api_only(self, mock_check_prereqs, mock_manager_class, runner):
        """Test dev command with --api-only flag."""
        mock_check_prereqs.return_value = True
        mock_manager = Mock()
        mock_manager.start_dev.return_value = 0
        mock_manager_class.return_value = mock_manager

        result = runner.invoke(main, ["web", "dev", "--api-only"])

        assert result.exit_code == 0
        mock_manager_class.assert_called_once()
        call_kwargs = mock_manager_class.call_args[1]
        assert call_kwargs["api_only"] is True
        assert call_kwargs["web_only"] is False

    @patch("skillmeat.web.WebManager")
    @patch("skillmeat.web.check_prerequisites")
    def test_dev_web_only(self, mock_check_prereqs, mock_manager_class, runner):
        """Test dev command with --web-only flag."""
        mock_check_prereqs.return_value = True
        mock_manager = Mock()
        mock_manager.start_dev.return_value = 0
        mock_manager_class.return_value = mock_manager

        result = runner.invoke(main, ["web", "dev", "--web-only"])

        assert result.exit_code == 0
        mock_manager_class.assert_called_once()
        call_kwargs = mock_manager_class.call_args[1]
        assert call_kwargs["api_only"] is False
        assert call_kwargs["web_only"] is True

    @patch("skillmeat.web.WebManager")
    @patch("skillmeat.web.check_prerequisites")
    def test_dev_custom_ports(self, mock_check_prereqs, mock_manager_class, runner):
        """Test dev command with custom ports."""
        mock_check_prereqs.return_value = True
        mock_manager = Mock()
        mock_manager.start_dev.return_value = 0
        mock_manager_class.return_value = mock_manager

        result = runner.invoke(
            main, ["web", "dev", "--api-port", "8080", "--web-port", "3001"]
        )

        assert result.exit_code == 0
        mock_manager_class.assert_called_once()
        call_kwargs = mock_manager_class.call_args[1]
        assert call_kwargs["api_port"] == 8080
        assert call_kwargs["web_port"] == 3001

    @patch("skillmeat.web.check_prerequisites")
    def test_dev_prerequisites_not_met(self, mock_check_prereqs, runner):
        """Test dev command when prerequisites not met."""
        mock_check_prereqs.return_value = False

        result = runner.invoke(main, ["web", "dev"])

        assert result.exit_code == 1
        mock_check_prereqs.assert_called_once()

    @patch("skillmeat.web.WebManager")
    @patch("skillmeat.web.check_prerequisites")
    def test_dev_exception(self, mock_check_prereqs, mock_manager_class, runner):
        """Test dev command with exception."""
        mock_check_prereqs.return_value = True
        mock_manager_class.side_effect = Exception("Test error")

        result = runner.invoke(main, ["web", "dev"])

        assert result.exit_code == 1
        assert "Test error" in result.output


class TestWebBuild:
    """Tests for 'skillmeat web build' command."""

    @patch("skillmeat.web.WebManager")
    @patch("skillmeat.web.check_prerequisites")
    def test_build_success(self, mock_check_prereqs, mock_manager_class, runner):
        """Test build command success."""
        mock_check_prereqs.return_value = True
        mock_manager = Mock()
        mock_manager.build_web.return_value = 0
        mock_manager_class.return_value = mock_manager

        result = runner.invoke(main, ["web", "build"])

        assert result.exit_code == 0
        mock_check_prereqs.assert_called_once()
        mock_manager.build_web.assert_called_once()

    @patch("skillmeat.web.WebManager")
    @patch("skillmeat.web.check_prerequisites")
    def test_build_check_flag(self, mock_check_prereqs, mock_manager_class, runner):
        """Test build command with --check flag."""
        mock_check_prereqs.return_value = True
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager

        result = runner.invoke(main, ["web", "build", "--check"])

        assert result.exit_code == 0
        mock_check_prereqs.assert_called_once()
        # build_web should not be called with --check
        mock_manager.build_web.assert_not_called()

    @patch("skillmeat.web.check_prerequisites")
    def test_build_prerequisites_not_met(self, mock_check_prereqs, runner):
        """Test build when prerequisites not met."""
        mock_check_prereqs.return_value = False

        result = runner.invoke(main, ["web", "build"])

        assert result.exit_code == 1

    @patch("skillmeat.web.WebManager")
    @patch("skillmeat.web.check_prerequisites")
    def test_build_failure(self, mock_check_prereqs, mock_manager_class, runner):
        """Test build failure."""
        mock_check_prereqs.return_value = True
        mock_manager = Mock()
        mock_manager.build_web.return_value = 1
        mock_manager_class.return_value = mock_manager

        result = runner.invoke(main, ["web", "build"])

        assert result.exit_code == 1


class TestWebStart:
    """Tests for 'skillmeat web start' command."""

    @patch("skillmeat.web.WebManager")
    @patch("skillmeat.web.check_prerequisites")
    @patch("pathlib.Path.exists")
    def test_start_success(
        self, mock_exists, mock_check_prereqs, mock_manager_class, runner
    ):
        """Test start command success."""
        mock_check_prereqs.return_value = True
        mock_exists.return_value = True  # .next directory exists
        mock_manager = Mock()
        mock_manager.start_production.return_value = 0
        mock_manager_class.return_value = mock_manager

        result = runner.invoke(main, ["web", "start"])

        assert result.exit_code == 0
        mock_manager.start_production.assert_called_once()

    @patch("skillmeat.web.WebManager")
    @patch("skillmeat.web.check_prerequisites")
    def test_start_api_only(self, mock_check_prereqs, mock_manager_class, runner):
        """Test start with --api-only (no build check)."""
        mock_check_prereqs.return_value = True
        mock_manager = Mock()
        mock_manager.start_production.return_value = 0
        mock_manager_class.return_value = mock_manager

        result = runner.invoke(main, ["web", "start", "--api-only"])

        assert result.exit_code == 0
        mock_manager_class.assert_called_once()
        call_kwargs = mock_manager_class.call_args[1]
        assert call_kwargs["api_only"] is True

    @patch("skillmeat.web.check_prerequisites")
    @patch("pathlib.Path.exists")
    def test_start_no_build(self, mock_exists, mock_check_prereqs, runner):
        """Test start when Next.js not built."""
        mock_check_prereqs.return_value = True
        mock_exists.return_value = False  # .next directory doesn't exist

        result = runner.invoke(main, ["web", "start"])

        assert result.exit_code == 1
        assert "build not found" in result.output.lower()

    @patch("skillmeat.web.check_prerequisites")
    def test_start_prerequisites_not_met(self, mock_check_prereqs, runner):
        """Test start when prerequisites not met."""
        mock_check_prereqs.return_value = False

        result = runner.invoke(main, ["web", "start"])

        assert result.exit_code == 1

    @patch("skillmeat.web.WebManager")
    @patch("skillmeat.web.check_prerequisites")
    @patch("pathlib.Path.exists")
    def test_start_custom_ports(
        self, mock_exists, mock_check_prereqs, mock_manager_class, runner
    ):
        """Test start with custom ports."""
        mock_check_prereqs.return_value = True
        mock_exists.return_value = True
        mock_manager = Mock()
        mock_manager.start_production.return_value = 0
        mock_manager_class.return_value = mock_manager

        result = runner.invoke(
            main,
            [
                "web",
                "start",
                "--api-port",
                "8080",
                "--web-port",
                "3001",
                "--api-host",
                "0.0.0.0",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_manager_class.call_args[1]
        assert call_kwargs["api_port"] == 8080
        assert call_kwargs["web_port"] == 3001
        assert call_kwargs["api_host"] == "0.0.0.0"


class TestWebHelp:
    """Tests for web command help."""

    def test_web_help(self, runner):
        """Test web command help."""
        result = runner.invoke(main, ["web", "--help"])

        assert result.exit_code == 0
        assert "web" in result.output.lower()
        assert "dev" in result.output.lower()
        assert "build" in result.output.lower()
        assert "start" in result.output.lower()
        assert "doctor" in result.output.lower()

    def test_web_dev_help(self, runner):
        """Test web dev help."""
        result = runner.invoke(main, ["web", "dev", "--help"])

        assert result.exit_code == 0
        assert "development" in result.output.lower()
        assert "--api-only" in result.output.lower()
        assert "--web-only" in result.output.lower()

    def test_web_build_help(self, runner):
        """Test web build help."""
        result = runner.invoke(main, ["web", "build", "--help"])

        assert result.exit_code == 0
        assert "production" in result.output.lower()

    def test_web_start_help(self, runner):
        """Test web start help."""
        result = runner.invoke(main, ["web", "start", "--help"])

        assert result.exit_code == 0
        assert "production" in result.output.lower()

    def test_web_doctor_help(self, runner):
        """Test web doctor help."""
        result = runner.invoke(main, ["web", "doctor", "--help"])

        assert result.exit_code == 0
        assert "diagnose" in result.output.lower() or "diagnostic" in result.output.lower()
