"""Tests for web doctor diagnostics."""

from unittest.mock import Mock, patch

import pytest

from skillmeat.web.doctor import DiagnosticResult, WebDoctor
from skillmeat.web.requirements import VersionInfo


class TestDiagnosticResult:
    """Tests for DiagnosticResult class."""

    def test_basic_result(self):
        """Test basic diagnostic result."""
        result = DiagnosticResult(
            name="Test",
            status="pass",
            message="Test passed",
        )

        assert result.name == "Test"
        assert result.status == "pass"
        assert result.message == "Test passed"
        assert result.details is None
        assert result.version_info is None

    def test_passed_property(self):
        """Test passed property."""
        pass_result = DiagnosticResult(name="Test", status="pass", message="OK")
        fail_result = DiagnosticResult(name="Test", status="fail", message="Failed")
        warn_result = DiagnosticResult(name="Test", status="warn", message="Warning")

        assert pass_result.passed is True
        assert fail_result.passed is False
        assert warn_result.passed is False

    def test_failed_property(self):
        """Test failed property."""
        pass_result = DiagnosticResult(name="Test", status="pass", message="OK")
        fail_result = DiagnosticResult(name="Test", status="fail", message="Failed")
        warn_result = DiagnosticResult(name="Test", status="warn", message="Warning")

        assert pass_result.failed is False
        assert fail_result.failed is True
        assert warn_result.failed is False

    def test_with_details(self):
        """Test result with details."""
        result = DiagnosticResult(
            name="Test",
            status="fail",
            message="Test failed",
            details="Error details here",
        )

        assert result.details == "Error details here"

    def test_with_version_info(self):
        """Test result with version info."""
        version_info = VersionInfo(
            version="18.20.0",
            path="/usr/bin/node",
            raw_output="v18.20.0",
        )

        result = DiagnosticResult(
            name="Node.js",
            status="pass",
            message="Node.js 18.20.0",
            version_info=version_info,
        )

        assert result.version_info == version_info


class TestWebDoctor:
    """Tests for WebDoctor class."""

    def test_init(self):
        """Test doctor initialization."""
        doctor = WebDoctor()

        assert doctor.checker is not None
        assert doctor.results == []

    def test_check_python_success(self):
        """Test Python check success."""
        python_info = VersionInfo(
            version="3.10.0",
            path="/usr/bin/python3",
            raw_output="3.10.0",
        )

        doctor = WebDoctor()
        doctor.checker.detect_python = Mock(return_value=python_info)
        result = doctor.check_python()

        assert result.status == "pass"
        assert result.name == "Python"
        assert "3.10.0" in result.message

    def test_check_python_too_old(self):
        """Test Python check with old version."""
        python_info = VersionInfo(
            version="3.7.0",
            path="/usr/bin/python3",
            raw_output="3.7.0",
        )

        doctor = WebDoctor()
        doctor.checker.detect_python = Mock(return_value=python_info)
        result = doctor.check_python()

        assert result.status == "fail"
        assert "too old" in result.message

    def test_check_node_success(self):
        """Test Node.js check success."""
        node_info = VersionInfo(
            version="18.20.0",
            path="/usr/bin/node",
            raw_output="v18.20.0",
        )

        doctor = WebDoctor()
        doctor.checker.check_node = Mock(return_value=(True, None))
        doctor.checker.detect_node = Mock(return_value=node_info)
        result = doctor.check_node()

        assert result.status == "pass"
        assert result.name == "Node.js"
        assert "18.20.0" in result.message

    def test_check_node_failure(self):
        """Test Node.js check failure."""
        doctor = WebDoctor()
        doctor.checker.check_node = Mock(return_value=(False, "Node.js not found"))
        doctor.checker.detect_node = Mock(return_value=None)
        result = doctor.check_node()

        assert result.status == "fail"
        assert "not found" in result.message.lower()

    def test_check_pnpm_success(self):
        """Test pnpm check success."""
        pnpm_info = VersionInfo(
            version="8.15.0",
            path="/usr/bin/pnpm",
            raw_output="8.15.0",
        )

        doctor = WebDoctor()
        doctor.checker.check_pnpm = Mock(return_value=(True, None))
        doctor.checker.detect_pnpm = Mock(return_value=pnpm_info)
        result = doctor.check_pnpm()

        assert result.status == "pass"
        assert result.name == "pnpm"
        assert "8.15.0" in result.message

    def test_check_pnpm_failure(self):
        """Test pnpm check failure."""
        doctor = WebDoctor()
        doctor.checker.check_pnpm = Mock(return_value=(False, "pnpm not found"))
        doctor.checker.detect_pnpm = Mock(return_value=None)
        result = doctor.check_pnpm()

        assert result.status == "fail"

    def test_check_web_directory_success(self):
        """Test web directory check success."""
        doctor = WebDoctor()
        doctor.checker.check_web_directory = Mock(return_value=(True, None))
        result = doctor.check_web_directory()

        assert result.status == "pass"
        assert result.name == "Web Directory"

    def test_check_web_directory_failure(self):
        """Test web directory check failure."""
        doctor = WebDoctor()
        doctor.checker.check_web_directory = Mock(
            return_value=(False, "Directory not found")
        )
        result = doctor.check_web_directory()

        assert result.status == "fail"

    def test_check_web_dependencies_success(self):
        """Test web dependencies check success."""
        doctor = WebDoctor()
        doctor.checker.check_web_dependencies = Mock(return_value=(True, None))
        result = doctor.check_web_dependencies()

        assert result.status == "pass"
        assert result.name == "Web Dependencies"

    def test_check_web_dependencies_failure(self):
        """Test web dependencies check failure."""
        doctor = WebDoctor()
        doctor.checker.check_web_dependencies = Mock(
            return_value=(False, "Dependencies not installed")
        )
        result = doctor.check_web_dependencies()

        assert result.status == "fail"

    def test_check_api_availability_success(self):
        """Test API dependencies check success."""
        doctor = WebDoctor()
        result = doctor.check_api_availability()

        # FastAPI and Uvicorn should be installed in test environment
        assert result.status == "pass"
        assert result.name == "API Dependencies"

    @patch("builtins.__import__")
    def test_check_api_availability_failure(self, mock_import):
        """Test API dependencies check failure."""
        mock_import.side_effect = ImportError("Module not found")

        doctor = WebDoctor()
        result = doctor.check_api_availability()

        assert result.status == "fail"

    @patch("socket.socket")
    def test_check_ports_available_success(self, mock_socket_class):
        """Test port availability check success."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        doctor = WebDoctor()
        result = doctor.check_ports_available()

        assert result.status == "pass"
        assert result.name == "Port Availability"

    @patch("socket.socket")
    def test_check_ports_available_in_use(self, mock_socket_class):
        """Test port availability check with ports in use."""
        mock_socket = Mock()
        mock_socket.bind.side_effect = OSError("Address already in use")
        mock_socket_class.return_value = mock_socket

        doctor = WebDoctor()
        result = doctor.check_ports_available()

        assert result.status == "warn"
        assert "in use" in result.message.lower()

    def test_run_all_checks(self):
        """Test running all checks."""
        doctor = WebDoctor()

        with patch.object(doctor, "check_python") as mock_python:
            with patch.object(doctor, "check_node") as mock_node:
                with patch.object(doctor, "check_pnpm") as mock_pnpm:
                    with patch.object(doctor, "check_web_directory") as mock_web_dir:
                        with patch.object(
                            doctor, "check_web_dependencies"
                        ) as mock_web_deps:
                            with patch.object(
                                doctor, "check_api_availability"
                            ) as mock_api:
                                with patch.object(
                                    doctor, "check_ports_available"
                                ) as mock_ports:
                                    # Mock all checks to return pass
                                    for mock_check in [
                                        mock_python,
                                        mock_node,
                                        mock_pnpm,
                                        mock_web_dir,
                                        mock_web_deps,
                                        mock_api,
                                        mock_ports,
                                    ]:
                                        mock_check.return_value = DiagnosticResult(
                                            name="Test",
                                            status="pass",
                                            message="OK",
                                        )

                                    results = doctor.run_all_checks()

        assert len(results) == 7
        assert all(r.status == "pass" for r in results)

    @patch("rich.console.Console")
    def test_print_summary_all_passed(self, mock_console_class):
        """Test print summary with all checks passed."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        doctor = WebDoctor()
        doctor.results = [
            DiagnosticResult(name="Test1", status="pass", message="OK"),
            DiagnosticResult(name="Test2", status="pass", message="OK"),
        ]

        result = doctor.print_summary()

        assert result is True
        assert mock_console.print.called

    @patch("rich.console.Console")
    def test_print_summary_with_failures(self, mock_console_class):
        """Test print summary with failures."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        doctor = WebDoctor()
        doctor.results = [
            DiagnosticResult(name="Test1", status="pass", message="OK"),
            DiagnosticResult(
                name="Test2",
                status="fail",
                message="Failed",
                details="Error details",
            ),
        ]

        result = doctor.print_summary()

        assert result is False
        assert mock_console.print.called


class TestRunDoctor:
    """Tests for run_doctor function."""

    @patch("skillmeat.web.doctor.WebDoctor")
    def test_run_doctor(self, mock_doctor_class):
        """Test run_doctor function."""
        from skillmeat.web.doctor import run_doctor

        mock_doctor = Mock()
        mock_doctor.run_all_checks.return_value = []
        mock_doctor.print_summary.return_value = True
        mock_doctor_class.return_value = mock_doctor

        result = run_doctor()

        assert result is True
        mock_doctor.run_all_checks.assert_called_once()
        mock_doctor.print_summary.assert_called_once()
