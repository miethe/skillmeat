"""Process manager for coordinating FastAPI and Next.js servers.

This module provides the WebManager class which orchestrates both the FastAPI
backend and Next.js frontend servers, handling process lifecycle, logging,
health checks, and graceful shutdown.
"""

import logging
import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Optional

import requests
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .requirements import RequirementsChecker

logger = logging.getLogger(__name__)


@dataclass
class ServerConfig:
    """Configuration for a server process."""

    name: str
    """Server name (e.g., 'API', 'Web')"""

    command: list[str]
    """Command to run (e.g., ['uvicorn', 'skillmeat.api.server:app'])"""

    cwd: Optional[Path] = None
    """Working directory for the process"""

    env: Optional[dict] = None
    """Environment variables"""

    health_url: Optional[str] = None
    """URL for health check"""

    startup_message: str = "Starting..."
    """Message to show during startup"""

    ready_message: str = "Ready"
    """Message to show when ready"""

    log_prefix: str = ""
    """Prefix for log lines"""

    log_color: str = "white"
    """Color for log output (for Rich)"""


class WebManager:
    """Manage FastAPI and Next.js server processes."""

    def __init__(
        self,
        api_only: bool = False,
        web_only: bool = False,
        api_port: int = 8000,
        web_port: int = 3000,
        api_host: str = "127.0.0.1",
    ):
        """Initialize web manager.

        Args:
            api_only: Run only the API server
            web_only: Run only the web server
            api_port: Port for FastAPI server
            web_port: Port for Next.js server
            api_host: Host for FastAPI server
        """
        self.api_only = api_only
        self.web_only = web_only
        self.api_port = api_port
        self.web_port = web_port
        self.api_host = api_host

        self.console = Console()
        self.processes: dict[str, subprocess.Popen] = {}
        self.log_threads: dict[str, threading.Thread] = {}
        self.shutdown_event = threading.Event()

        # Get web directory
        import skillmeat

        self.package_root = Path(skillmeat.__file__).parent
        self.web_dir = self.package_root / "web"

    def _get_api_config(self, reload: bool = True) -> ServerConfig:
        """Get configuration for FastAPI server.

        Args:
            reload: Enable auto-reload on code changes

        Returns:
            Server configuration
        """
        command = [
            sys.executable,
            "-m",
            "uvicorn",
            "skillmeat.api.server:app",
            "--host",
            self.api_host,
            "--port",
            str(self.api_port),
        ]

        if reload:
            command.append("--reload")

        return ServerConfig(
            name="API",
            command=command,
            cwd=self.package_root.parent,  # Project root
            health_url=f"http://{self.api_host}:{self.api_port}/health",
            startup_message=f"Starting FastAPI server on {self.api_host}:{self.api_port}...",
            ready_message=f"FastAPI ready at http://{self.api_host}:{self.api_port}",
            log_prefix="[API]",
            log_color="blue",
        )

    def _get_web_config(self, production: bool = False) -> ServerConfig:
        """Get configuration for Next.js server.

        Args:
            production: Use production mode (next start vs next dev)

        Returns:
            Server configuration
        """
        if production:
            command = ["pnpm", "start"]
            startup_msg = f"Starting Next.js server (production) on :{self.web_port}..."
            ready_msg = f"Next.js ready at http://localhost:{self.web_port} (production)"
        else:
            command = ["pnpm", "dev"]
            startup_msg = f"Starting Next.js server (dev) on :{self.web_port}..."
            ready_msg = f"Next.js ready at http://localhost:{self.web_port} (dev)"

        # Set environment variables for Next.js
        env = os.environ.copy()
        env["PORT"] = str(self.web_port)
        # Set API URL so frontend knows where to send requests
        env["NEXT_PUBLIC_API_URL"] = f"http://{self.api_host}:{self.api_port}"

        return ServerConfig(
            name="Web",
            command=command,
            cwd=self.web_dir,
            env=env,
            health_url=f"http://localhost:{self.web_port}",
            startup_message=startup_msg,
            ready_message=ready_msg,
            log_prefix="[Web]",
            log_color="green",
        )

    def _start_process(self, config: ServerConfig) -> subprocess.Popen:
        """Start a server process.

        Args:
            config: Server configuration

        Returns:
            Running process

        Raises:
            RuntimeError: If process fails to start
        """
        logger.info(f"Starting {config.name} server: {' '.join(config.command)}")

        try:
            process = subprocess.Popen(
                config.command,
                cwd=config.cwd,
                env=config.env or os.environ.copy(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,  # Line buffered
            )

            # Start log forwarding thread
            log_thread = threading.Thread(
                target=self._forward_logs,
                args=(config.name, process.stdout, config.log_prefix, config.log_color),
                daemon=True,
            )
            log_thread.start()

            self.processes[config.name] = process
            self.log_threads[config.name] = log_thread

            logger.info(f"{config.name} process started with PID {process.pid}")
            return process

        except Exception as e:
            logger.error(f"Failed to start {config.name} server: {e}")
            raise RuntimeError(f"Failed to start {config.name} server: {e}")

    def _forward_logs(
        self, name: str, stream: IO[str], prefix: str, color: str
    ) -> None:
        """Forward logs from a process to console.

        Args:
            name: Server name
            stream: Process stdout/stderr stream
            prefix: Log prefix
            color: Color for output
        """
        try:
            for line in stream:
                if self.shutdown_event.is_set():
                    break

                # Strip trailing newline
                line = line.rstrip()
                if not line:
                    continue

                # Print with color and prefix
                self.console.print(f"[{color}]{prefix}[/{color}] {line}")

        except Exception as e:
            if not self.shutdown_event.is_set():
                logger.error(f"Error forwarding {name} logs: {e}")

    def _wait_for_health(self, config: ServerConfig, timeout: int = 60) -> bool:
        """Wait for server to become healthy.

        Args:
            config: Server configuration
            timeout: Maximum time to wait in seconds

        Returns:
            True if server is healthy, False if timeout
        """
        if not config.health_url:
            # No health check URL, just wait a bit
            time.sleep(2)
            return True

        start_time = time.time()

        while time.time() - start_time < timeout:
            if self.shutdown_event.is_set():
                return False

            try:
                response = requests.get(config.health_url, timeout=1)
                if response.status_code == 200:
                    logger.info(f"{config.name} health check passed")
                    return True
            except (requests.RequestException, Exception):
                pass

            time.sleep(0.5)

        logger.warning(f"{config.name} health check timed out after {timeout}s")
        return False

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""

        def signal_handler(signum, frame):
            """Handle shutdown signals."""
            logger.info(f"Received signal {signum}, shutting down...")
            self.shutdown_event.set()

        # Register handlers for SIGINT (Ctrl+C) and SIGTERM
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def _stop_process(self, name: str, timeout: int = 10) -> None:
        """Stop a server process gracefully.

        Args:
            name: Server name
            timeout: Maximum time to wait for graceful shutdown
        """
        if name not in self.processes:
            return

        process = self.processes[name]

        logger.info(f"Stopping {name} server (PID {process.pid})...")

        try:
            # Try graceful shutdown first
            process.terminate()

            # Wait for process to exit
            try:
                process.wait(timeout=timeout)
                logger.info(f"{name} server stopped gracefully")
            except subprocess.TimeoutExpired:
                # Force kill if timeout
                logger.warning(f"{name} server didn't stop gracefully, force killing...")
                process.kill()
                process.wait(timeout=5)
                logger.info(f"{name} server killed")

        except Exception as e:
            logger.error(f"Error stopping {name} server: {e}")

        finally:
            # Clean up
            if name in self.processes:
                del self.processes[name]
            if name in self.log_threads:
                del self.log_threads[name]

    def start_dev(self) -> int:
        """Start development servers (FastAPI + Next.js).

        Returns:
            Exit code (0 for success)
        """
        # Set up signal handlers
        self._setup_signal_handlers()

        # Determine which servers to start
        configs = []
        if not self.web_only:
            configs.append(self._get_api_config(reload=True))
        if not self.api_only:
            configs.append(self._get_web_config(production=False))

        # Create progress display
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        )

        with Live(progress, console=self.console):
            for config in configs:
                # Add progress task
                task = progress.add_task(config.startup_message, total=None)

                # Start process
                try:
                    self._start_process(config)
                except RuntimeError as e:
                    progress.update(task, description=f"[red]Failed: {e}[/red]")
                    self.stop_all()
                    return 1

                # Wait for health check
                if self._wait_for_health(config):
                    progress.update(task, description=f"[green]{config.ready_message}[/green]")
                else:
                    progress.update(task, description=f"[red]Health check failed[/red]")
                    self.stop_all()
                    return 1

        # Print ready message
        self.console.print("\n[bold green]All servers ready![/bold green]\n")

        # Show URLs
        if not self.web_only:
            self.console.print(f"  API: http://{self.api_host}:{self.api_port}")
            self.console.print(f"  Docs: http://{self.api_host}:{self.api_port}/docs")
        if not self.api_only:
            self.console.print(f"  Web: http://localhost:{self.web_port}")

        self.console.print("\nPress Ctrl+C to stop\n")

        # Wait for shutdown signal
        try:
            while not self.shutdown_event.is_set():
                # Check if any process has died
                for name, process in list(self.processes.items()):
                    if process.poll() is not None:
                        logger.error(f"{name} server exited unexpectedly")
                        self.shutdown_event.set()
                        break

                time.sleep(0.5)

        except KeyboardInterrupt:
            pass

        # Stop all servers
        self.console.print("\n[yellow]Shutting down servers...[/yellow]")
        self.stop_all()

        return 0

    def start_production(self) -> int:
        """Start production servers (FastAPI + Next.js built).

        Returns:
            Exit code (0 for success)
        """
        # Set up signal handlers
        self._setup_signal_handlers()

        # Determine which servers to start
        configs = []
        if not self.web_only:
            configs.append(self._get_api_config(reload=False))
        if not self.api_only:
            configs.append(self._get_web_config(production=True))

        # Create progress display
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        )

        with Live(progress, console=self.console):
            for config in configs:
                # Add progress task
                task = progress.add_task(config.startup_message, total=None)

                # Start process
                try:
                    self._start_process(config)
                except RuntimeError as e:
                    progress.update(task, description=f"[red]Failed: {e}[/red]")
                    self.stop_all()
                    return 1

                # Wait for health check
                if self._wait_for_health(config):
                    progress.update(task, description=f"[green]{config.ready_message}[/green]")
                else:
                    progress.update(task, description=f"[red]Health check failed[/red]")
                    self.stop_all()
                    return 1

        # Print ready message
        self.console.print("\n[bold green]All servers ready![/bold green]\n")

        # Show URLs
        if not self.web_only:
            self.console.print(f"  API: http://{self.api_host}:{self.api_port}")
        if not self.api_only:
            self.console.print(f"  Web: http://localhost:{self.web_port}")

        self.console.print("\nPress Ctrl+C to stop\n")

        # Wait for shutdown signal
        try:
            while not self.shutdown_event.is_set():
                # Check if any process has died
                for name, process in list(self.processes.items()):
                    if process.poll() is not None:
                        logger.error(f"{name} server exited unexpectedly")
                        self.shutdown_event.set()
                        break

                time.sleep(0.5)

        except KeyboardInterrupt:
            pass

        # Stop all servers
        self.console.print("\n[yellow]Shutting down servers...[/yellow]")
        self.stop_all()

        return 0

    def build_web(self) -> int:
        """Build Next.js for production.

        Uses 'pnpm build:fresh' which cleans the .next cache before building
        to prevent MODULE_NOT_FOUND errors from corrupted webpack caches.

        Returns:
            Exit code (0 for success)
        """
        self.console.print("[cyan]Building Next.js application for production...[/cyan]")
        self.console.print("[dim]Cleaning cache and building fresh to prevent cache corruption[/dim]\n")

        try:
            # Run pnpm build:fresh (cleans cache then builds)
            result = subprocess.run(
                ["pnpm", "build:fresh"],
                cwd=self.web_dir,
                check=True,
            )

            self.console.print("\n[green]Build completed successfully![/green]")
            return result.returncode

        except subprocess.CalledProcessError as e:
            self.console.print(f"\n[red]Build failed with exit code {e.returncode}[/red]")
            return e.returncode
        except Exception as e:
            self.console.print(f"\n[red]Build failed: {e}[/red]")
            return 1

    def stop_all(self) -> None:
        """Stop all running servers."""
        for name in list(self.processes.keys()):
            self._stop_process(name)


def check_prerequisites(console: Console) -> bool:
    """Check if prerequisites are met for web commands.

    Args:
        console: Rich console for output

    Returns:
        True if all prerequisites are met, False otherwise
    """
    checker = RequirementsChecker()

    # Check all requirements
    all_ok, errors = checker.check_all()

    if not all_ok:
        console.print("[red]Prerequisites not met:[/red]\n")
        for error in errors:
            console.print(f"  [yellow]•[/yellow] {error}\n")

        console.print("[yellow]Run 'skillmeat web doctor' for detailed diagnostics.[/yellow]")
        return False

    return True
