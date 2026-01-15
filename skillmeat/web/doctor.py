"""Environment diagnostics for web development setup.

This module provides comprehensive diagnostics for the SkillMeat web
development environment, checking Node.js, pnpm, Python, and related tools.
"""

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .requirements import RequirementsChecker, VersionInfo

logger = logging.getLogger(__name__)


@dataclass
class DiagnosticResult:
    """Result of a diagnostic check."""

    name: str
    """Name of the check (e.g., 'Node.js')"""

    status: str
    """Status: 'pass', 'warn', 'fail'"""

    message: str
    """Human-readable message"""

    details: Optional[str] = None
    """Additional details or suggestions"""

    version_info: Optional[VersionInfo] = None
    """Version information if applicable"""

    @property
    def passed(self) -> bool:
        """Check if diagnostic passed."""
        return self.status == "pass"

    @property
    def failed(self) -> bool:
        """Check if diagnostic failed."""
        return self.status == "fail"


class WebDoctor:
    """Diagnose web development environment."""

    def __init__(self):
        """Initialize web doctor."""
        self.checker = RequirementsChecker()
        self.results: list[DiagnosticResult] = []

    def check_python(self) -> DiagnosticResult:
        """Check Python installation and version.

        Returns:
            Diagnostic result for Python
        """
        python_info = self.checker.detect_python()

        if python_info is None:
            return DiagnosticResult(
                name="Python",
                status="fail",
                message="Python not detected",
                details="This should not happen as we are running in Python!",
            )

        # Check if Python 3.9+
        if python_info.major and python_info.major >= 3 and python_info.minor >= 9:
            return DiagnosticResult(
                name="Python",
                status="pass",
                message=f"Python {python_info.version}",
                details=f"Location: {python_info.path}",
                version_info=python_info,
            )
        else:
            return DiagnosticResult(
                name="Python",
                status="fail",
                message=f"Python {python_info.version} is too old",
                details="SkillMeat requires Python 3.9 or higher",
                version_info=python_info,
            )

    def check_node(self) -> DiagnosticResult:
        """Check Node.js installation and version.

        Returns:
            Diagnostic result for Node.js
        """
        node_ok, node_error = self.checker.check_node()
        node_info = self.checker.detect_node()

        if node_ok:
            return DiagnosticResult(
                name="Node.js",
                status="pass",
                message=f"Node.js {node_info.version}",
                details=f"Location: {node_info.path}",
                version_info=node_info,
            )
        else:
            return DiagnosticResult(
                name="Node.js",
                status="fail",
                message="Node.js not found or too old",
                details=node_error,
                version_info=node_info,
            )

    def check_pnpm(self) -> DiagnosticResult:
        """Check pnpm installation and version.

        Returns:
            Diagnostic result for pnpm
        """
        pnpm_ok, pnpm_error = self.checker.check_pnpm()
        pnpm_info = self.checker.detect_pnpm()

        if pnpm_ok:
            return DiagnosticResult(
                name="pnpm",
                status="pass",
                message=f"pnpm {pnpm_info.version}",
                details=f"Location: {pnpm_info.path}",
                version_info=pnpm_info,
            )
        else:
            return DiagnosticResult(
                name="pnpm",
                status="fail",
                message="pnpm not found or too old",
                details=pnpm_error,
                version_info=pnpm_info,
            )

    def check_web_directory(self) -> DiagnosticResult:
        """Check if web directory exists and is valid.

        Returns:
            Diagnostic result for web directory
        """
        web_ok, web_error = self.checker.check_web_directory()

        if web_ok:
            import skillmeat

            package_root = Path(skillmeat.__file__).parent
            web_dir = package_root / "web"

            return DiagnosticResult(
                name="Web Directory",
                status="pass",
                message="Next.js application found",
                details=f"Location: {web_dir}",
            )
        else:
            return DiagnosticResult(
                name="Web Directory",
                status="fail",
                message="Web directory missing or invalid",
                details=web_error,
            )

    def check_web_dependencies(self) -> DiagnosticResult:
        """Check if web dependencies are installed.

        Returns:
            Diagnostic result for web dependencies
        """
        deps_ok, deps_error = self.checker.check_web_dependencies()

        if deps_ok:
            import skillmeat

            package_root = Path(skillmeat.__file__).parent
            web_dir = package_root / "web"

            return DiagnosticResult(
                name="Web Dependencies",
                status="pass",
                message="node_modules installed",
                details=f"Location: {web_dir / 'node_modules'}",
            )
        else:
            return DiagnosticResult(
                name="Web Dependencies",
                status="fail",
                message="Web dependencies not installed",
                details=deps_error,
            )

    def check_api_availability(self) -> DiagnosticResult:
        """Check if FastAPI dependencies are available.

        Returns:
            Diagnostic result for API dependencies
        """
        try:
            import fastapi
            import uvicorn

            return DiagnosticResult(
                name="API Dependencies",
                status="pass",
                message=f"FastAPI {fastapi.__version__}, Uvicorn {uvicorn.__version__}",
                details="API server dependencies installed",
            )
        except ImportError as e:
            return DiagnosticResult(
                name="API Dependencies",
                status="fail",
                message="FastAPI or Uvicorn not installed",
                details=f"Import error: {e}",
            )

    def check_ports_available(self) -> DiagnosticResult:
        """Check if default ports are available.

        Returns:
            Diagnostic result for port availability
        """
        import socket

        ports_to_check = {
            8080: "FastAPI",
            3000: "Next.js",
        }

        unavailable = []

        for port, service in ports_to_check.items():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.bind(("127.0.0.1", port))
                sock.close()
            except OSError:
                unavailable.append(f"{service} (:{port})")

        if not unavailable:
            return DiagnosticResult(
                name="Port Availability",
                status="pass",
                message="Ports 8080 and 3000 available",
                details="No port conflicts detected",
            )
        else:
            return DiagnosticResult(
                name="Port Availability",
                status="warn",
                message=f"Ports in use: {', '.join(unavailable)}",
                details="Services may already be running or ports are in use by other applications",
            )

    def run_all_checks(self) -> list[DiagnosticResult]:
        """Run all diagnostic checks.

        Returns:
            List of diagnostic results
        """
        self.results = []

        # Core dependencies
        self.results.append(self.check_python())
        self.results.append(self.check_node())
        self.results.append(self.check_pnpm())

        # Web application
        self.results.append(self.check_web_directory())
        self.results.append(self.check_web_dependencies())

        # API dependencies
        self.results.append(self.check_api_availability())

        # Runtime checks
        self.results.append(self.check_ports_available())

        return self.results

    def print_summary(self) -> bool:
        """Print diagnostic summary.

        Returns:
            True if all checks passed, False otherwise
        """
        from rich.console import Console
        from rich.table import Table

        console = Console()

        # Print header
        console.print("\n[bold]SkillMeat Web Doctor[/bold]\n")
        console.print("Checking web development environment...\n")

        # Create results table
        table = Table(show_header=True, header_style="bold")
        table.add_column("Check", style="cyan")
        table.add_column("Status", style="white")
        table.add_column("Details", style="white")

        all_passed = True

        for result in self.results:
            # Determine status style
            if result.status == "pass":
                status_str = "[green]✓ PASS[/green]"
            elif result.status == "warn":
                status_str = "[yellow]⚠ WARN[/yellow]"
                all_passed = False
            else:
                status_str = "[red]✗ FAIL[/red]"
                all_passed = False

            # Add row to table
            table.add_row(
                result.name,
                status_str,
                result.message,
            )

        console.print(table)

        # Print detailed errors/warnings
        has_issues = False
        for result in self.results:
            if result.failed or (result.status == "warn" and result.details):
                if not has_issues:
                    console.print("\n[bold]Issues Found:[/bold]\n")
                    has_issues = True

                style = "red" if result.failed else "yellow"
                console.print(f"[{style}]{result.name}:[/{style}]")
                if result.details:
                    console.print(f"  {result.details}\n")

        # Print summary
        console.print()
        if all_passed:
            console.print(
                "[green]All checks passed! Ready for web development.[/green]"
            )
        else:
            console.print(
                "[yellow]Some checks failed. Please fix the issues above before running web commands.[/yellow]"
            )

        return all_passed


def run_doctor() -> bool:
    """Run web doctor diagnostics.

    Returns:
        True if all checks passed, False otherwise
    """
    doctor = WebDoctor()
    doctor.run_all_checks()
    return doctor.print_summary()
