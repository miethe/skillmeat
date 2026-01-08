"""MCP Server Deployment Manager for SkillMeat.

This module handles deployment of MCP servers to Claude Desktop's settings.json
configuration file, including backup, atomic updates, and environment scaffolding.
"""

import json
import platform
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console

from skillmeat.core.mcp.metadata import MCPServerMetadata, MCPServerStatus
from skillmeat.sources.github import ArtifactSpec, GitHubClient

console = Console()


@dataclass
class DeploymentResult:
    """Result of MCP server deployment operation."""

    server_name: str
    success: bool
    settings_path: Path
    backup_path: Optional[Path] = None
    env_file_path: Optional[Path] = None
    error_message: Optional[str] = None
    command: Optional[str] = None
    args: Optional[List[str]] = None


class MCPDeploymentManager:
    """Manages deployment of MCP servers to Claude Desktop configuration.

    This class handles:
    - Platform-specific settings.json location detection
    - Atomic updates with backup/restore
    - Repository cloning and package.json parsing
    - Environment variable scaffolding
    - Idempotent deployments (update, not duplicate)
    """

    def __init__(self, github_token: Optional[str] = None):
        """Initialize MCP deployment manager.

        Args:
            github_token: GitHub personal access token for private repos
        """
        self.github_client = GitHubClient(github_token)

    def get_settings_path(self) -> Path:
        """Get platform-specific Claude Desktop settings.json path.

        Returns:
            Path to Claude Desktop settings.json

        Raises:
            RuntimeError: If platform is not supported
        """
        system = platform.system()

        if system == "Darwin":  # macOS
            return (
                Path.home()
                / "Library"
                / "Application Support"
                / "Claude"
                / "claude_desktop_config.json"
            )
        elif system == "Windows":
            # Use APPDATA environment variable
            import os

            appdata = os.environ.get("APPDATA")
            if not appdata:
                raise RuntimeError("APPDATA environment variable not found")
            return Path(appdata) / "Claude" / "claude_desktop_config.json"
        elif system == "Linux":
            return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
        else:
            raise RuntimeError(f"Unsupported platform: {system}")

    def backup_settings(self, settings_path: Optional[Path] = None) -> Path:
        """Create backup of settings.json.

        Args:
            settings_path: Path to settings file (uses default if None)

        Returns:
            Path to backup file

        Raises:
            IOError: If backup creation fails
        """
        if settings_path is None:
            settings_path = self.get_settings_path()

        if not settings_path.exists():
            console.print(
                "[yellow]No existing settings.json found, will create new one[/yellow]"
            )
            return None

        # Create backup with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = (
            settings_path.parent / f"claude_desktop_config.backup.{timestamp}.json"
        )

        try:
            shutil.copy2(settings_path, backup_path)
            console.print(f"[green]Created backup: {backup_path}[/green]")
            return backup_path
        except Exception as e:
            raise IOError(f"Failed to create backup: {e}")

    def restore_settings(
        self, backup_path: Path, settings_path: Optional[Path] = None
    ) -> bool:
        """Restore settings.json from backup.

        Args:
            backup_path: Path to backup file
            settings_path: Path to settings file (uses default if None)

        Returns:
            True if restored successfully, False otherwise
        """
        if not backup_path or not backup_path.exists():
            console.print("[yellow]No backup to restore[/yellow]")
            return False

        try:
            if settings_path is None:
                settings_path = self.get_settings_path()
            shutil.copy2(backup_path, settings_path)
            console.print(f"[green]Restored settings from backup[/green]")
            return True
        except Exception as e:
            console.print(f"[red]Failed to restore backup: {e}[/red]")
            return False

    def read_settings(self, settings_path: Optional[Path] = None) -> Dict[str, Any]:
        """Read and parse settings.json.

        Args:
            settings_path: Path to settings file (uses default if None)

        Returns:
            Dictionary containing settings (empty dict if file doesn't exist)

        Raises:
            ValueError: If JSON is invalid
        """
        if settings_path is None:
            settings_path = self.get_settings_path()

        if not settings_path.exists():
            return {}

        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in settings file: {e}")
        except Exception as e:
            raise IOError(f"Failed to read settings: {e}")

    def write_settings(
        self, settings: Dict[str, Any], settings_path: Optional[Path] = None
    ) -> None:
        """Write settings to settings.json atomically.

        Uses temp file + atomic rename pattern for safety.

        Args:
            settings: Settings dictionary to write
            settings_path: Path to settings file (uses default if None)

        Raises:
            IOError: If write operation fails
        """
        if settings_path is None:
            settings_path = self.get_settings_path()

        # Ensure parent directory exists
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to temp file first
        temp_fd, temp_path = tempfile.mkstemp(
            dir=settings_path.parent,
            prefix=".claude_desktop_config.tmp.",
            suffix=".json",
            text=True,
        )

        try:
            with open(temp_fd, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
                f.write("\n")  # Add trailing newline

            # Atomic rename
            Path(temp_path).replace(settings_path)

        except Exception as e:
            # Clean up temp file on failure
            try:
                Path(temp_path).unlink(missing_ok=True)
            except:
                pass
            raise IOError(f"Failed to write settings: {e}")

    def is_server_deployed(
        self, name: str, settings_path: Optional[Path] = None
    ) -> bool:
        """Check if MCP server is already deployed.

        Args:
            name: Server name
            settings_path: Path to settings file (uses default if None)

        Returns:
            True if server exists in settings, False otherwise
        """
        try:
            settings = self.read_settings(settings_path)
            mcp_servers = settings.get("mcpServers", {})
            return name in mcp_servers
        except Exception:
            return False

    def get_deployed_servers(self, settings_path: Optional[Path] = None) -> List[str]:
        """Get list of deployed MCP server names.

        Args:
            settings_path: Path to settings file (uses default if None)

        Returns:
            List of server names
        """
        try:
            settings = self.read_settings(settings_path)
            mcp_servers = settings.get("mcpServers", {})
            return list(mcp_servers.keys())
        except Exception:
            return []

    def undeploy_server(self, name: str, settings_path: Optional[Path] = None) -> bool:
        """Remove MCP server from settings.json.

        Args:
            name: Server name
            settings_path: Path to settings file (uses default if None)

        Returns:
            True if removed, False if not found

        Raises:
            IOError: If operation fails
        """
        try:
            # Create backup first
            backup_path = self.backup_settings(settings_path)

            # Read settings
            settings = self.read_settings(settings_path)
            mcp_servers = settings.get("mcpServers", {})

            if name not in mcp_servers:
                console.print(f"[yellow]Server '{name}' not found in settings[/yellow]")
                return False

            # Remove server
            del mcp_servers[name]
            settings["mcpServers"] = mcp_servers

            # Write updated settings
            self.write_settings(settings, settings_path)

            console.print(f"[green]Removed server '{name}' from settings[/green]")
            return True

        except Exception as e:
            console.print(f"[red]Failed to undeploy server: {e}[/red]")
            if backup_path:
                self.restore_settings(backup_path)
            raise

    def _parse_package_json(self, repo_path: Path) -> Dict[str, Any]:
        """Parse package.json from MCP server repository.

        Args:
            repo_path: Path to cloned repository

        Returns:
            Dictionary containing package.json data

        Raises:
            ValueError: If package.json not found or invalid
        """
        package_json = repo_path / "package.json"

        if not package_json.exists():
            raise ValueError(
                f"package.json not found in repository. "
                "Manual configuration required for this MCP server."
            )

        try:
            with open(package_json, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid package.json: {e}")

    def _resolve_command_from_package(
        self, package_data: Dict[str, Any]
    ) -> tuple[str, List[str]]:
        """Resolve command and args from package.json.

        Common patterns:
        - NPM package: command="npx", args=["-y", "@scope/package-name"]
        - Local script: command="node", args=["path/to/script.js"]

        Args:
            package_data: Parsed package.json

        Returns:
            Tuple of (command, args)

        Raises:
            ValueError: If command cannot be determined
        """
        package_name = package_data.get("name")

        if not package_name:
            raise ValueError("package.json must contain a 'name' field")

        # For published npm packages, use npx
        if package_data.get("publishConfig") or package_name.startswith("@"):
            command = "npx"
            args = ["-y", package_name]
        else:
            # For local packages, use node with main entry point
            main_script = package_data.get("main", "index.js")
            command = "node"
            args = [main_script]

        return command, args

    def deploy_server(
        self,
        server: MCPServerMetadata,
        project_path: Optional[Path] = None,
        dry_run: bool = False,
        backup: bool = True,
    ) -> DeploymentResult:
        """Deploy MCP server to Claude Desktop settings.json.

        Flow:
        1. Resolve repository (clone if needed)
        2. Read package.json to get command/args
        3. Create settings.json backup (if requested)
        4. Update settings.json with server config
        5. Scaffold .env file if env_vars defined
        6. Mark server as INSTALLED in collection

        Args:
            server: MCPServerMetadata to deploy
            project_path: Optional project-specific deployment path
            dry_run: If True, show changes without applying
            backup: If True, create backup before modifying

        Returns:
            DeploymentResult with operation details

        Raises:
            RuntimeError: If deployment fails
        """
        console.print(f"[cyan]Deploying MCP server '{server.name}'...[/cyan]")

        # Get settings path
        try:
            settings_path = self.get_settings_path()
        except Exception as e:
            return DeploymentResult(
                server_name=server.name,
                success=False,
                settings_path=None,
                error_message=str(e),
            )

        # Create backup if requested
        backup_path = None
        if backup and not dry_run:
            try:
                backup_path = self.backup_settings(settings_path)
            except Exception as e:
                return DeploymentResult(
                    server_name=server.name,
                    success=False,
                    settings_path=settings_path,
                    error_message=f"Failed to create backup: {e}",
                )

        try:
            # Parse repository spec from server.repo
            # Support formats: "username/repo", "github.com/username/repo", "https://github.com/username/repo"
            repo_spec = server.repo
            if repo_spec.startswith("https://github.com/"):
                repo_spec = repo_spec.replace("https://github.com/", "")
            elif repo_spec.startswith("github.com/"):
                repo_spec = repo_spec.replace("github.com/", "")

            # Append version
            full_spec = f"{repo_spec}@{server.version}"

            # Parse spec
            spec = ArtifactSpec.parse(full_spec)

            # Resolve version
            console.print(f"[cyan]Resolving version '{server.version}'...[/cyan]")
            resolved_sha, resolved_version = self.github_client.resolve_version(spec)

            # Clone repository to temp directory
            console.print(f"[cyan]Cloning repository...[/cyan]")
            temp_dir = Path(tempfile.mkdtemp(prefix="skillmeat_mcp_"))

            try:
                self.github_client.clone_repo(spec, temp_dir, resolved_sha)

                # Parse package.json
                console.print(f"[cyan]Reading package.json...[/cyan]")
                package_data = self._parse_package_json(temp_dir)
                command, args = self._resolve_command_from_package(package_data)

                console.print(f"[green]Command: {command} {' '.join(args)}[/green]")

                # Build server config
                server_config = {
                    "command": command,
                    "args": args,
                }

                # Add env vars if present
                if server.env_vars:
                    server_config["env"] = server.env_vars

                if dry_run:
                    console.print("[yellow]DRY RUN: Would add server config:[/yellow]")
                    console.print(json.dumps({server.name: server_config}, indent=2))

                    return DeploymentResult(
                        server_name=server.name,
                        success=True,
                        settings_path=settings_path,
                        command=command,
                        args=args,
                    )

                # Read current settings
                settings = self.read_settings(settings_path)

                # Ensure mcpServers section exists
                if "mcpServers" not in settings:
                    settings["mcpServers"] = {}

                # Check if server already exists
                if server.name in settings["mcpServers"]:
                    console.print(
                        f"[yellow]Server '{server.name}' already exists, updating...[/yellow]"
                    )

                # Add/update server config
                settings["mcpServers"][server.name] = server_config

                # Write updated settings
                self.write_settings(settings, settings_path)

                console.print(
                    f"[green]Server '{server.name}' deployed to settings.json[/green]"
                )

                # Scaffold environment variables if needed
                env_file_path = None
                if server.env_vars:
                    env_file_path = self._scaffold_env_vars(server, project_path)

                # Update server metadata
                server.mark_installed()
                server.update_version(resolved_sha, resolved_version)

                return DeploymentResult(
                    server_name=server.name,
                    success=True,
                    settings_path=settings_path,
                    backup_path=backup_path,
                    env_file_path=env_file_path,
                    command=command,
                    args=args,
                )

            finally:
                # Clean up temp directory
                if temp_dir.exists():
                    shutil.rmtree(temp_dir, ignore_errors=True)

        except Exception as e:
            error_msg = f"Deployment failed: {e}"
            console.print(f"[red]{error_msg}[/red]")

            # Restore from backup if available
            if backup_path and not dry_run:
                console.print("[yellow]Restoring from backup...[/yellow]")
                self.restore_settings(backup_path)

            return DeploymentResult(
                server_name=server.name,
                success=False,
                settings_path=settings_path,
                backup_path=backup_path,
                error_message=error_msg,
            )

    def _scaffold_env_vars(
        self,
        server: MCPServerMetadata,
        project_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """Scaffold .env file with environment variables.

        Creates or updates .env file with MCP server environment variables.
        Format: MCP_{SERVER_NAME}_{VAR_NAME}=value

        Args:
            server: MCPServerMetadata with env_vars
            project_path: Optional project-specific path (uses collection dir if None)

        Returns:
            Path to .env file, or None if no env vars
        """
        if not server.env_vars:
            return None

        # Determine .env location
        if project_path:
            env_file = project_path / ".env"
        else:
            # Use collection directory
            from skillmeat.config import ConfigManager

            config = ConfigManager()
            collection_path = config.get_collections_dir()
            env_file = collection_path / ".env"

        # Read existing .env if present
        existing_vars = {}
        if env_file.exists():
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            existing_vars[key.strip()] = value.strip()
            except Exception as e:
                console.print(
                    f"[yellow]Warning: Failed to read existing .env: {e}[/yellow]"
                )

        # Add new variables with prefix
        server_prefix = f"MCP_{server.name.upper().replace('-', '_')}_"
        new_vars = {}

        for key, value in server.env_vars.items():
            env_key = f"{server_prefix}{key.upper()}"
            new_vars[env_key] = value
            existing_vars[env_key] = value

        # Write updated .env
        try:
            env_file.parent.mkdir(parents=True, exist_ok=True)

            with open(env_file, "w", encoding="utf-8") as f:
                f.write(f"# Environment variables for SkillMeat MCP servers\n")
                f.write(f"# Generated on {datetime.utcnow().isoformat()}\n\n")

                for key, value in sorted(existing_vars.items()):
                    f.write(f"{key}={value}\n")

            console.print(f"[green]Environment variables written to {env_file}[/green]")

            # Show instructions for sensitive values
            if new_vars:
                console.print(
                    "\n[yellow]NOTE: Update sensitive values in .env before use:[/yellow]"
                )
                for key in new_vars:
                    console.print(f"  {key}")
                console.print()

            return env_file

        except Exception as e:
            console.print(f"[yellow]Warning: Failed to write .env file: {e}[/yellow]")
            return None
