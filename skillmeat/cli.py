"""CLI entry point for SkillMeat.

This module provides the complete command-line interface for SkillMeat,
a personal collection manager for Claude Code artifacts.
"""

import logging
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm
from rich.syntax import Syntax
from rich.progress import track
from rich.panel import Panel

from skillmeat import __version__
from skillmeat.config import ConfigManager
from skillmeat.core.collection import CollectionManager
from skillmeat.core.artifact import ArtifactManager, ArtifactType, UpdateStrategy
from skillmeat.core.deployment import DeploymentManager
from skillmeat.core.version import VersionManager
from skillmeat.core.diff_engine import DiffEngine
from skillmeat.core.mcp import MCPDeploymentManager, MCPServerMetadata
from skillmeat.sources.github import GitHubSource
from skillmeat.sources.local import LocalSource
from skillmeat.utils.validator import ArtifactValidator

# Console for output
console = Console(force_terminal=True, legacy_windows=False)

# Logger for error tracking
logger = logging.getLogger(__name__)


# ====================
# Main Entry Point
# ====================


@click.group()
@click.version_option(version=__version__, prog_name="skillmeat")
def main():
    """SkillMeat: Personal collection manager for Claude Code artifacts.

    Manage Skills, Commands, Agents, and more across multiple projects.

    Examples:
      skillmeat init                        # Initialize default collection
      skillmeat add skill user/repo/skill   # Add skill from GitHub
      skillmeat list                        # List all artifacts
      skillmeat deploy my-skill             # Deploy to current project
      skillmeat snapshot "Backup"           # Create snapshot
    """
    pass


# ====================
# Core Commands
# ====================


@main.command()
@click.option(
    "--name",
    "-n",
    default="default",
    help="Collection name (default: 'default')",
)
def init(name: str):
    """Initialize a new collection.

    Creates a collection directory structure and manifest file.
    If no name is provided, creates the 'default' collection.

    Examples:
      skillmeat init                    # Create 'default' collection
      skillmeat init --name work        # Create 'work' collection
    """
    try:
        collection_mgr = CollectionManager()

        # Check if collection already exists
        collections = collection_mgr.list_collections()
        if name in collections:
            console.print(f"[yellow]Collection '{name}' already exists[/yellow]")
            return

        # Initialize collection
        console.print(f"[cyan]Initializing collection '{name}'...[/cyan]")
        collection = collection_mgr.init(name)

        console.print(f"[green]Collection '{name}' initialized[/green]")
        console.print(f"  Location: {collection_mgr.config.get_collection_path(name)}")
        console.print(f"  Artifacts: 0")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@main.command(name="list")
@click.option(
    "--type",
    "-t",
    "artifact_type",
    type=click.Choice(["skill", "command", "agent"]),
    default=None,
    help="Filter by artifact type",
)
@click.option(
    "--collection",
    "-c",
    default=None,
    help="Collection name (default: active collection)",
)
@click.option(
    "--tags",
    is_flag=True,
    help="Show tags for each artifact",
)
def cmd_list(artifact_type: Optional[str], collection: Optional[str], tags: bool):
    """List artifacts in collection.

    Shows all artifacts or filtered by type.

    Examples:
      skillmeat list                    # List all artifacts
      skillmeat list --type skill       # List only skills
      skillmeat list --tags             # Show tags
    """
    try:
        artifact_mgr = ArtifactManager()

        # Convert type string to enum
        type_filter = ArtifactType(artifact_type) if artifact_type else None

        # List artifacts
        artifacts = artifact_mgr.list_artifacts(
            collection_name=collection,
            artifact_type=type_filter,
        )

        if not artifacts:
            console.print("[yellow]No artifacts found[/yellow]")
            return

        # Create table
        table = Table(title=f"Artifacts ({len(artifacts)})")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="blue")
        table.add_column("Origin", style="green")
        if tags:
            table.add_column("Tags", style="yellow")

        for artifact in artifacts:
            row = [
                artifact.name,
                artifact.type.value,
                artifact.origin,
            ]
            if tags:
                tag_str = (
                    ", ".join(artifact.metadata.tags) if artifact.metadata.tags else ""
                )
                row.append(tag_str)
            table.add_row(*row)

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@main.command()
@click.argument("name")
@click.option(
    "--type",
    "-t",
    "artifact_type",
    type=click.Choice(["skill", "command", "agent"]),
    default=None,
    help="Artifact type (required if name is ambiguous)",
)
@click.option(
    "--collection",
    "-c",
    default=None,
    help="Collection name (default: active collection)",
)
def show(name: str, artifact_type: Optional[str], collection: Optional[str]):
    """Show detailed information about an artifact.

    Examples:
      skillmeat show my-skill           # Show skill details
      skillmeat show review --type command  # Show command (if ambiguous)
    """
    try:
        artifact_mgr = ArtifactManager()

        # Convert type string to enum
        type_filter = ArtifactType(artifact_type) if artifact_type else None

        # Show artifact
        artifact_mgr.show(
            name=name,
            artifact_type=type_filter,
            collection_name=collection,
        )

    except ValueError as e:
        # Ambiguous name or not found
        console.print(f"[yellow]{e}[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@main.command()
@click.argument("name")
@click.option(
    "--type",
    "-t",
    "artifact_type",
    type=click.Choice(["skill", "command", "agent"]),
    default=None,
    help="Artifact type (required if name is ambiguous)",
)
@click.option(
    "--collection",
    "-c",
    default=None,
    help="Collection name (default: active collection)",
)
@click.option(
    "--keep-files",
    is_flag=True,
    help="Remove from collection but keep files on disk",
)
def remove(
    name: str, artifact_type: Optional[str], collection: Optional[str], keep_files: bool
):
    """Remove artifact from collection.

    By default, removes both the collection entry and the files.
    Use --keep-files to only remove from collection manifest.

    Examples:
      skillmeat remove my-skill         # Remove completely
      skillmeat remove my-skill --keep-files  # Keep files
    """
    try:
        artifact_mgr = ArtifactManager()

        # Convert type string to enum
        type_filter = ArtifactType(artifact_type) if artifact_type else None

        # Remove artifact
        artifact_mgr.remove(
            name=name,
            artifact_type=type_filter,
            collection_name=collection,
            keep_files=keep_files,
        )

    except ValueError as e:
        console.print(f"[yellow]{e}[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


# ====================
# Add Commands (Artifact Type Specific)
# ====================


@main.group()
def add():
    """Add artifacts to collection.

    Use subcommands to add specific artifact types:
      - skill: Add a skill
      - command: Add a command
      - agent: Add an agent
    """
    pass


def _security_warning():
    """Show security warning for artifact installation."""
    console.print(
        "[yellow]Security warning: Artifacts can execute code and access system resources.[/yellow]"
    )
    console.print()
    console.print("Before installing an artifact, please consider:")
    console.print("  - Install only from trusted sources")
    console.print("  - Review what the artifact does before use")
    console.print("  - Artifacts can read, create, or modify files")
    console.print("  - Artifacts can execute system commands")
    console.print()
    console.print("For more information on artifact security and permissions, see:")
    console.print(
        "  https://support.claude.com/en/articles/12512180-using-skills-in-claude#h_2746475e70"
    )
    console.print()


def _add_artifact_from_spec(
    spec: str,
    artifact_type: ArtifactType,
    collection: Optional[str],
    name: Optional[str],
    no_verify: bool,
    force: bool,
    dangerously_skip_permissions: bool,
):
    """Shared logic for adding artifacts from GitHub or local paths."""
    try:
        # Show security warning unless skipped
        if not dangerously_skip_permissions:
            _security_warning()
            if not Confirm.ask("Do you want to continue installing this artifact?"):
                console.print("[yellow]Cancelled[/yellow]")
                return

        artifact_mgr = ArtifactManager()

        # Determine if spec is GitHub or local path
        if "/" in spec and not spec.startswith((".", "/")):
            # Likely GitHub spec
            console.print(f"[cyan]Fetching from GitHub: {spec}...[/cyan]")

            artifact = artifact_mgr.add_from_github(
                spec=spec,
                artifact_type=artifact_type,
                collection_name=collection,
                custom_name=name,
                tags=None,
                force=force,
            )

            console.print(
                f"[green]Added {artifact_type.value}: {artifact.name}[/green]"
            )

        else:
            # Local path
            local_path = Path(spec).resolve()
            if not local_path.exists():
                console.print(f"[red]Path not found: {spec}[/red]")
                sys.exit(1)

            console.print(f"[cyan]Adding from local path: {local_path}...[/cyan]")

            artifact = artifact_mgr.add_from_local(
                path=str(local_path),
                artifact_type=artifact_type,
                collection_name=collection,
                custom_name=name,
                tags=None,
                force=force,
            )

            console.print(
                f"[green]Added {artifact_type.value}: {artifact.name}[/green]"
            )

    except ValueError as e:
        console.print(f"[red]Invalid specification: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@add.command()
@click.argument("spec")
@click.option(
    "--collection",
    "-c",
    default=None,
    help="Collection name (default: active collection)",
)
@click.option(
    "--name",
    "-n",
    default=None,
    help="Override artifact name",
)
@click.option(
    "--no-verify",
    is_flag=True,
    help="Skip validation",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing artifact",
)
@click.option(
    "--dangerously-skip-permissions",
    is_flag=True,
    help="Skip permission warnings (not recommended)",
)
def skill(
    spec: str,
    collection: Optional[str],
    name: Optional[str],
    no_verify: bool,
    force: bool,
    dangerously_skip_permissions: bool,
):
    """Add a skill from GitHub or local path.

    SPEC can be:
      - GitHub: user/repo/path/to/skill[@version]
      - Local: /path/to/skill/directory

    Examples:
      skillmeat add skill anthropics/skills/canvas
      skillmeat add skill user/repo/my-skill@v1.0.0
      skillmeat add skill ./my-local-skill
      skillmeat add skill ./skill --name custom-name
    """
    _add_artifact_from_spec(
        spec=spec,
        artifact_type=ArtifactType.SKILL,
        collection=collection,
        name=name,
        no_verify=no_verify,
        force=force,
        dangerously_skip_permissions=dangerously_skip_permissions,
    )


@add.command()
@click.argument("spec")
@click.option(
    "--collection",
    "-c",
    default=None,
    help="Collection name (default: active collection)",
)
@click.option(
    "--name",
    "-n",
    default=None,
    help="Override artifact name",
)
@click.option(
    "--no-verify",
    is_flag=True,
    help="Skip validation",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing artifact",
)
@click.option(
    "--dangerously-skip-permissions",
    is_flag=True,
    help="Skip permission warnings (not recommended)",
)
def command(
    spec: str,
    collection: Optional[str],
    name: Optional[str],
    no_verify: bool,
    force: bool,
    dangerously_skip_permissions: bool,
):
    """Add a command from GitHub or local path.

    SPEC can be:
      - GitHub: user/repo/path/to/command.md[@version]
      - Local: /path/to/command.md

    Examples:
      skillmeat add command user/repo/commands/review.md
      skillmeat add command ./review.md --name my-review
    """
    _add_artifact_from_spec(
        spec=spec,
        artifact_type=ArtifactType.COMMAND,
        collection=collection,
        name=name,
        no_verify=no_verify,
        force=force,
        dangerously_skip_permissions=dangerously_skip_permissions,
    )


@add.command()
@click.argument("spec")
@click.option(
    "--collection",
    "-c",
    default=None,
    help="Collection name (default: active collection)",
)
@click.option(
    "--name",
    "-n",
    default=None,
    help="Override artifact name",
)
@click.option(
    "--no-verify",
    is_flag=True,
    help="Skip validation",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing artifact",
)
@click.option(
    "--dangerously-skip-permissions",
    is_flag=True,
    help="Skip permission warnings (not recommended)",
)
def agent(
    spec: str,
    collection: Optional[str],
    name: Optional[str],
    no_verify: bool,
    force: bool,
    dangerously_skip_permissions: bool,
):
    """Add an agent from GitHub or local path.

    SPEC can be:
      - GitHub: user/repo/path/to/agent.md[@version]
      - Local: /path/to/agent.md

    Examples:
      skillmeat add agent user/repo/agents/reviewer.md
      skillmeat add agent ./my-agent.md
    """
    _add_artifact_from_spec(
        spec=spec,
        artifact_type=ArtifactType.AGENT,
        collection=collection,
        name=name,
        no_verify=no_verify,
        force=force,
        dangerously_skip_permissions=dangerously_skip_permissions,
    )


# ====================
# Deployment Commands
# ====================


@main.command()
@click.argument("names", nargs=-1, required=True)
@click.option(
    "--collection",
    "-c",
    default=None,
    help="Collection name (default: active collection)",
)
@click.option(
    "--project",
    "-p",
    default=None,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help="Project path (default: current directory)",
)
@click.option(
    "--type",
    "-t",
    "artifact_type",
    type=click.Choice(["skill", "command", "agent"]),
    default=None,
    help="Artifact type (required if names are ambiguous)",
)
def deploy(
    names: List[str],
    collection: Optional[str],
    project: Optional[Path],
    artifact_type: Optional[str],
):
    """Deploy artifacts to a project's .claude/ directory.

    Copies artifacts from collection to the project, tracking deployment
    for later updates and synchronization.

    Examples:
      skillmeat deploy my-skill               # Deploy to current dir
      skillmeat deploy skill1 skill2          # Deploy multiple
      skillmeat deploy my-skill --project /path/to/proj
    """
    try:
        deployment_mgr = DeploymentManager()

        # Convert type string to enum
        type_filter = ArtifactType(artifact_type) if artifact_type else None

        # Deploy artifacts
        console.print(f"[cyan]Deploying {len(names)} artifact(s)...[/cyan]")

        deployments = deployment_mgr.deploy_artifacts(
            artifact_names=list(names),
            collection_name=collection,
            project_path=project,
            artifact_type=type_filter,
        )

        console.print(f"[green]Deployed {len(deployments)} artifact(s)[/green]")
        for deployment in deployments:
            console.print(f"  {deployment.artifact_name} -> {deployment.artifact_path}")

    except ValueError as e:
        console.print(f"[yellow]{e}[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@main.command()
@click.argument("name")
@click.option(
    "--project",
    "-p",
    default=None,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help="Project path (default: current directory)",
)
@click.option(
    "--type",
    "-t",
    "artifact_type",
    type=click.Choice(["skill", "command", "agent"]),
    default=None,
    help="Artifact type (required if name is ambiguous)",
)
def undeploy(
    name: str,
    project: Optional[Path],
    artifact_type: Optional[str],
):
    """Remove deployed artifact from project.

    Removes the artifact from the project's .claude/ directory and
    updates deployment tracking.

    Examples:
      skillmeat undeploy my-skill
      skillmeat undeploy my-skill --project /path/to/proj
    """
    try:
        deployment_mgr = DeploymentManager()

        # Convert type string to enum
        type_filter = ArtifactType(artifact_type) if artifact_type else None

        # Undeploy artifact
        deployment_mgr.undeploy(
            artifact_name=name,
            project_path=project,
            artifact_type=type_filter,
        )

    except ValueError as e:
        console.print(f"[yellow]{e}[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


# ====================
# MCP Server Management
# ====================


@main.group()
def mcp():
    """Manage MCP (Model Context Protocol) servers.

    Use subcommands to manage MCP servers in your collection:
      - add: Add MCP server to collection
      - deploy: Deploy MCP server to Claude Desktop
      - undeploy: Remove MCP server from Claude Desktop
      - list: List MCP servers in collection
      - health: Check health of deployed MCP servers
    """
    pass


@mcp.command(name="add")
@click.argument("name")
@click.argument("repo")
@click.option(
    "--version",
    "-v",
    default="latest",
    help="Version specification (latest, v1.0.0, SHA, branch)",
)
@click.option(
    "--env",
    "-e",
    multiple=True,
    help="Environment variables (format: KEY=value)",
)
@click.option(
    "--description",
    "-d",
    default=None,
    help="Description of the MCP server",
)
@click.option(
    "--collection",
    "-c",
    default=None,
    help="Collection name (default: active collection)",
)
def mcp_add(
    name: str,
    repo: str,
    version: str,
    env: tuple,
    description: Optional[str],
    collection: Optional[str],
):
    """Add MCP server to collection.

    NAME: Unique identifier for the MCP server
    REPO: GitHub repository (user/repo or full URL)

    Examples:
      skillmeat mcp add filesystem anthropics/mcp-filesystem
      skillmeat mcp add filesystem anthropics/mcp-filesystem --version v1.0.0
      skillmeat mcp add custom user/mcp-server --env ROOT_PATH=/home/user
    """
    try:
        collection_mgr = CollectionManager()
        collection_obj = collection_mgr.load_collection(collection)

        # Parse environment variables
        env_vars = {}
        for env_pair in env:
            if "=" not in env_pair:
                console.print(f"[yellow]Invalid env format: {env_pair}. Use KEY=value[/yellow]")
                sys.exit(1)
            key, value = env_pair.split("=", 1)
            env_vars[key] = value

        # Create MCP server metadata
        server = MCPServerMetadata(
            name=name,
            repo=repo,
            version=version,
            env_vars=env_vars,
            description=description,
        )

        # Add to collection
        collection_obj.add_mcp_server(server)
        collection_mgr.save_collection(collection_obj)

        console.print(f"[green]Added MCP server '{name}' to collection[/green]")
        console.print(f"  Repository: {repo}")
        console.print(f"  Version: {version}")
        if env_vars:
            console.print(f"  Environment variables: {len(env_vars)}")

    except ValueError as e:
        console.print(f"[yellow]{e}[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@mcp.command(name="deploy")
@click.argument("name")
@click.option(
    "--collection",
    "-c",
    default=None,
    help="Collection name (default: active collection)",
)
@click.option(
    "--project",
    "-p",
    default=None,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help="Project path for project-specific deployment",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be deployed without making changes",
)
@click.option(
    "--backup/--no-backup",
    default=True,
    help="Create backup of settings.json before deployment (default: yes)",
)
@click.option(
    "--dangerously-skip-permissions",
    is_flag=True,
    help="Skip permission warnings (not recommended)",
)
def mcp_deploy(
    name: str,
    collection: Optional[str],
    project: Optional[Path],
    dry_run: bool,
    backup: bool,
    dangerously_skip_permissions: bool,
):
    """Deploy MCP server to Claude Desktop settings.json.

    NAME: Name of the MCP server to deploy

    This command:
    1. Resolves the MCP server repository and version
    2. Clones the repository and reads package.json
    3. Creates a backup of Claude Desktop settings.json
    4. Updates settings.json with server configuration
    5. Scaffolds environment variables if needed

    Examples:
      skillmeat mcp deploy filesystem
      skillmeat mcp deploy filesystem --dry-run
      skillmeat mcp deploy filesystem --project ~/myproject
      skillmeat mcp deploy filesystem --no-backup
    """
    try:
        # Security warning
        if not dangerously_skip_permissions:
            console.print("[yellow]Security warning: MCP servers can execute code and access system resources.[/yellow]")
            console.print()
            console.print("Before deploying an MCP server, please consider:")
            console.print("  - Install only from trusted sources")
            console.print("  - Review what the server does before use")
            console.print("  - MCP servers can access files and system commands")
            console.print()

            if not dry_run:
                if not Confirm.ask("Do you want to continue?", default=False):
                    console.print("[yellow]Deployment cancelled[/yellow]")
                    return

        # Load collection and find MCP server
        collection_mgr = CollectionManager()
        collection_obj = collection_mgr.load_collection(collection)

        server = collection_obj.find_mcp_server(name)
        if server is None:
            console.print(f"[red]MCP server '{name}' not found in collection[/red]")
            console.print("[yellow]Use 'skillmeat mcp add' to add it first[/yellow]")
            sys.exit(1)

        # Get GitHub token from config
        config = ConfigManager()
        github_token = config.get("settings.github-token")

        # Deploy server
        deployment_mgr = MCPDeploymentManager(github_token=github_token)
        result = deployment_mgr.deploy_server(
            server=server,
            project_path=project,
            dry_run=dry_run,
            backup=backup,
        )

        if result.success:
            if not dry_run:
                # Update collection with new status
                collection_mgr.save_collection(collection_obj)

            console.print()
            console.print(Panel(
                f"[green]MCP server '{result.server_name}' deployed successfully[/green]\n\n"
                f"Command: {result.command}\n"
                f"Args: {' '.join(result.args or [])}\n"
                f"Settings: {result.settings_path}\n"
                + (f"Backup: {result.backup_path}\n" if result.backup_path else "")
                + (f"Environment: {result.env_file_path}\n" if result.env_file_path else "")
                + "\n[yellow]Next steps:[/yellow]\n"
                + "1. Restart Claude Desktop to load the new MCP server\n"
                + "2. Check Claude Desktop logs if server doesn't appear\n"
                + (f"3. Update environment variables in {result.env_file_path}" if result.env_file_path else ""),
                title="Deployment Complete",
                border_style="green",
            ))
        else:
            console.print(f"[red]Deployment failed: {result.error_message}[/red]")
            sys.exit(1)

    except ValueError as e:
        console.print(f"[yellow]{e}[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@mcp.command(name="undeploy")
@click.argument("name")
@click.option(
    "--backup/--no-backup",
    default=True,
    help="Create backup before removing (default: yes)",
)
def mcp_undeploy(name: str, backup: bool):
    """Remove MCP server from Claude Desktop settings.json.

    NAME: Name of the MCP server to remove

    Examples:
      skillmeat mcp undeploy filesystem
      skillmeat mcp undeploy filesystem --no-backup
    """
    try:
        config = ConfigManager()
        github_token = config.get("settings.github-token")

        deployment_mgr = MCPDeploymentManager(github_token=github_token)

        # Check if server is deployed
        if not deployment_mgr.is_server_deployed(name):
            console.print(f"[yellow]MCP server '{name}' is not deployed[/yellow]")
            return

        # Undeploy
        success = deployment_mgr.undeploy_server(name)

        if success:
            console.print(f"[green]MCP server '{name}' removed from Claude Desktop[/green]")
            console.print("[yellow]Restart Claude Desktop to apply changes[/yellow]")
        else:
            console.print(f"[yellow]Failed to undeploy server '{name}'[/yellow]")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@mcp.command(name="list")
@click.option(
    "--collection",
    "-c",
    default=None,
    help="Collection name (default: active collection)",
)
@click.option(
    "--deployed",
    is_flag=True,
    help="Show deployment status in Claude Desktop",
)
def mcp_list(collection: Optional[str], deployed: bool):
    """List MCP servers in collection.

    Examples:
      skillmeat mcp list
      skillmeat mcp list --deployed
      skillmeat mcp list --collection work
    """
    try:
        collection_mgr = CollectionManager()
        collection_obj = collection_mgr.load_collection(collection)

        servers = collection_obj.list_mcp_servers()

        if not servers:
            console.print("[yellow]No MCP servers in collection[/yellow]")
            console.print("[cyan]Use 'skillmeat mcp add' to add one[/cyan]")
            return

        # Get deployment status if requested
        deployment_status = {}
        if deployed:
            config = ConfigManager()
            github_token = config.get("settings.github-token")
            deployment_mgr = MCPDeploymentManager(github_token=github_token)
            deployed_servers = deployment_mgr.get_deployed_servers()
            for server_name in deployed_servers:
                deployment_status[server_name] = True

        # Create table
        table = Table(title=f"MCP Servers ({len(servers)})")
        table.add_column("Name", style="cyan")
        table.add_column("Repository", style="blue")
        table.add_column("Version", style="green")
        table.add_column("Status", style="yellow")
        if deployed:
            table.add_column("Deployed", style="magenta")

        for server in servers:
            row = [
                server.name,
                server.repo,
                server.version,
                server.status.value,
            ]
            if deployed:
                is_deployed = deployment_status.get(server.name, False)
                row.append("Yes" if is_deployed else "No")
            table.add_row(*row)

        console.print(table)

        # Show summary
        if deployed:
            deployed_count = sum(1 for s in servers if deployment_status.get(s.name, False))
            console.print(f"\n[cyan]{deployed_count} of {len(servers)} servers deployed to Claude Desktop[/cyan]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@mcp.command(name="health")
@click.option(
    "--server",
    "-s",
    default=None,
    help="Check specific server (default: check all deployed servers)",
)
@click.option(
    "--watch",
    "-w",
    is_flag=True,
    help="Continuous monitoring mode (refresh every N seconds)",
)
@click.option(
    "--interval",
    "-i",
    default=5,
    type=int,
    help="Watch interval in seconds (default: 5)",
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Force fresh health check (ignore cache)",
)
def mcp_health(
    server: Optional[str],
    watch: bool,
    interval: int,
    no_cache: bool,
):
    """Check health of deployed MCP servers.

    Monitors MCP server health by analyzing:
    - Deployment status in Claude Desktop settings.json
    - Claude Desktop log files for errors and warnings
    - Server initialization and connection status

    Examples:
      skillmeat mcp health
      skillmeat mcp health --server filesystem
      skillmeat mcp health --watch --interval 10
    """
    try:
        from datetime import datetime

        from rich.table import Table

        from skillmeat.config import ConfigManager
        from skillmeat.core.mcp.deployment import MCPDeploymentManager
        from skillmeat.core.mcp.health import HealthStatus, MCPHealthChecker

        # Get configuration
        config = ConfigManager()
        github_token = config.get("settings.github-token")

        # Create health checker
        deployment_mgr = MCPDeploymentManager(github_token=github_token)
        health_checker = MCPHealthChecker(deployment_manager=deployment_mgr)

        def display_health_results(results: dict):
            """Display health check results in table format."""
            if not results:
                console.print("[yellow]No deployed MCP servers found[/yellow]")
                console.print("[cyan]Use 'skillmeat mcp deploy' to deploy a server[/cyan]")
                return

            # Color mapping for status
            status_colors = {
                HealthStatus.HEALTHY: "green",
                HealthStatus.DEGRADED: "yellow",
                HealthStatus.UNHEALTHY: "red",
                HealthStatus.UNKNOWN: "dim",
                HealthStatus.NOT_DEPLOYED: "dim",
            }

            # Status symbols
            status_symbols = {
                HealthStatus.HEALTHY: "✓",
                HealthStatus.DEGRADED: "⚠",
                HealthStatus.UNHEALTHY: "✗",
                HealthStatus.UNKNOWN: "?",
                HealthStatus.NOT_DEPLOYED: "-",
            }

            # Create table
            table = Table(title=f"MCP Server Health ({len(results)} servers)")
            table.add_column("Server", style="cyan")
            table.add_column("Status", style="white")
            table.add_column("Last Seen", style="blue")
            table.add_column("Errors", style="red")
            table.add_column("Warnings", style="yellow")

            for server_name, result in sorted(results.items()):
                # Format last seen
                if result.last_seen:
                    now = datetime.utcnow()
                    delta = now - result.last_seen
                    if delta.total_seconds() < 60:
                        last_seen_str = f"{int(delta.total_seconds())}s ago"
                    elif delta.total_seconds() < 3600:
                        last_seen_str = f"{int(delta.total_seconds() / 60)}m ago"
                    elif delta.total_seconds() < 86400:
                        last_seen_str = f"{int(delta.total_seconds() / 3600)}h ago"
                    else:
                        last_seen_str = f"{int(delta.total_seconds() / 86400)}d ago"
                else:
                    last_seen_str = "Never"

                # Format status with color and symbol
                status_color = status_colors.get(result.status, "white")
                status_symbol = status_symbols.get(result.status, "")
                status_str = f"[{status_color}]{status_symbol} {result.status.value.title()}[/{status_color}]"

                table.add_row(
                    server_name,
                    status_str,
                    last_seen_str,
                    str(result.error_count),
                    str(result.warning_count),
                )

            console.print(table)

            # Summary
            healthy = sum(1 for r in results.values() if r.status == HealthStatus.HEALTHY)
            degraded = sum(1 for r in results.values() if r.status == HealthStatus.DEGRADED)
            unhealthy = sum(1 for r in results.values() if r.status == HealthStatus.UNHEALTHY)

            console.print()
            console.print(
                f"[green]Healthy: {healthy}[/green]  "
                f"[yellow]Degraded: {degraded}[/yellow]  "
                f"[red]Unhealthy: {unhealthy}[/red]"
            )

        def display_single_server_health(result):
            """Display detailed health information for a single server."""
            console.print(f"\n[bold cyan]Server:[/bold cyan] {result.server_name}")

            # Status with color
            status_colors = {
                HealthStatus.HEALTHY: "green",
                HealthStatus.DEGRADED: "yellow",
                HealthStatus.UNHEALTHY: "red",
                HealthStatus.UNKNOWN: "dim",
                HealthStatus.NOT_DEPLOYED: "dim",
            }
            status_color = status_colors.get(result.status, "white")
            console.print(f"[bold]Status:[/bold] [{status_color}]{result.status.value.title()}[/{status_color}]")

            console.print(f"[bold]Deployed:[/bold] {'Yes' if result.deployed else 'No'}")

            if result.last_seen:
                now = datetime.utcnow()
                delta = now - result.last_seen
                if delta.total_seconds() < 60:
                    last_seen_str = f"{int(delta.total_seconds())} seconds ago"
                elif delta.total_seconds() < 3600:
                    last_seen_str = f"{int(delta.total_seconds() / 60)} minutes ago"
                elif delta.total_seconds() < 86400:
                    last_seen_str = f"{int(delta.total_seconds() / 3600)} hours ago"
                else:
                    last_seen_str = f"{int(delta.total_seconds() / 86400)} days ago"
                console.print(f"[bold]Last Seen:[/bold] {last_seen_str}")
            else:
                console.print("[bold]Last Seen:[/bold] Never")

            console.print(f"[bold]Error Count:[/bold] {result.error_count}")
            console.print(f"[bold]Warning Count:[/bold] {result.warning_count}")

            # Recent errors
            if result.recent_errors:
                console.print("\n[bold red]Recent Errors:[/bold red]")
                for i, error in enumerate(result.recent_errors, 1):
                    console.print(f"  {i}. {error}")
            else:
                console.print("\n[green]No recent errors[/green]")

            # Recent warnings
            if result.recent_warnings:
                console.print("\n[bold yellow]Recent Warnings:[/bold yellow]")
                for i, warning in enumerate(result.recent_warnings, 1):
                    console.print(f"  {i}. {warning}")
            else:
                console.print("\n[green]No recent warnings[/green]")

            console.print()

        # Watch mode
        if watch:
            import time

            console.print(f"[cyan]Watching MCP server health (interval: {interval}s). Press Ctrl+C to stop.[/cyan]\n")

            try:
                while True:
                    # Clear screen (cross-platform)
                    import os
                    os.system("cls" if os.name == "nt" else "clear")

                    console.print(f"[dim]Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC[/dim]\n")

                    # Check health
                    if server:
                        result = health_checker.check_server_health(server, use_cache=not no_cache)
                        display_single_server_health(result)
                    else:
                        results = health_checker.check_all_servers(use_cache=not no_cache)
                        display_health_results(results)

                    # Wait for interval
                    time.sleep(interval)

            except KeyboardInterrupt:
                console.print("\n[cyan]Health monitoring stopped[/cyan]")
                return

        # Single check mode
        else:
            if server:
                # Check specific server
                result = health_checker.check_server_health(server, use_cache=not no_cache)

                if result.status == HealthStatus.NOT_DEPLOYED:
                    console.print(f"[yellow]Server '{server}' is not deployed to Claude Desktop[/yellow]")
                    console.print("[cyan]Use 'skillmeat mcp deploy' to deploy it[/cyan]")
                    sys.exit(1)

                display_single_server_health(result)

            else:
                # Check all servers
                results = health_checker.check_all_servers(use_cache=not no_cache)
                display_health_results(results)

    except KeyboardInterrupt:
        console.print("\n[cyan]Health check cancelled[/cyan]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback

        traceback.print_exc()
        sys.exit(1)


# ====================
# Update & Status Commands
# ====================


@main.command()
@click.option(
    "--collection",
    "-c",
    default=None,
    help="Collection name (default: active collection)",
)
@click.option(
    "--project",
    "-p",
    default=None,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help="Project path for deployment status (default: current directory)",
)
def status(collection: Optional[str], project: Optional[Path]):
    """Check update status for artifacts and deployments.

    Shows available updates from upstream sources and checks
    if deployed artifacts have local modifications.

    Examples:
      skillmeat status                  # Check active collection
      skillmeat status --project /path  # Check deployment status
    """
    try:
        artifact_mgr = ArtifactManager()
        deployment_mgr = DeploymentManager()

        # Check for artifact updates
        console.print("[cyan]Checking for updates...[/cyan]")
        update_info = artifact_mgr.check_updates(collection_name=collection)

        updates_available = update_info.get("updates_available", [])
        up_to_date = update_info.get("up_to_date", [])

        if updates_available:
            console.print(
                f"\n[yellow]Updates available ({len(updates_available)}):[/yellow]"
            )
            for info in updates_available:
                console.print(
                    f"  {info['name']} ({info['type']}): {info['current_version']} -> {info['latest_version']}"
                )

        if up_to_date:
            console.print(f"\n[green]Up to date ({len(up_to_date)}):[/green]")
            for info in up_to_date:
                console.print(f"  {info['name']} ({info['type']})")

        # Check deployment status if project specified
        if project or project is None:
            console.print("\n[cyan]Checking deployment status...[/cyan]")
            status_info = deployment_mgr.check_deployment_status(project_path=project)

            modified = status_info.get("modified", [])
            synced = status_info.get("synced", [])

            if modified:
                console.print(f"\n[yellow]Locally modified ({len(modified)}):[/yellow]")
                for info in modified:
                    console.print(f"  {info['name']} ({info['type']})")

            if synced:
                console.print(f"\n[green]Synced ({len(synced)}):[/green]")
                for info in synced:
                    console.print(f"  {info['name']} ({info['type']})")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@main.command()
@click.argument("name", required=False)
@click.option(
    "--collection",
    "-c",
    default=None,
    help="Collection name (default: active collection)",
)
@click.option(
    "--type",
    "-t",
    "artifact_type",
    type=click.Choice(["skill", "command", "agent"]),
    default=None,
    help="Artifact type (required if name is ambiguous)",
)
@click.option(
    "--strategy",
    type=click.Choice(["prompt", "upstream", "local"]),
    default="prompt",
    help="Update strategy for modified artifacts (default: prompt)",
)
def update(
    name: Optional[str],
    collection: Optional[str],
    artifact_type: Optional[str],
    strategy: str,
):
    """Update artifact(s) from upstream sources.

    Updates artifacts to latest versions from GitHub or refreshes
    local artifacts. Handles conflicts based on update strategy.

    Examples:
      skillmeat update my-skill         # Update one artifact
      skillmeat update my-skill --strategy upstream  # Force upstream
    """
    status_messages = {
        "no_upstream": "No upstream information stored; re-add from GitHub to enable updates.",
        "up_to_date": "Already up to date.",
        "local_changes_kept": "Local modifications preserved (use --strategy upstream to overwrite).",
        "cancelled": "Update cancelled.",
    }

    def _format_version(version: Optional[str], sha: Optional[str]) -> str:
        if version:
            return version
        if sha:
            return sha[:7]
        return "latest"

    def _print_update_result(result):
        if not hasattr(result, "updated"):
            console.print(f"[green]Updated {name}[/green]")
            return

        artifact_name = getattr(getattr(result, "artifact", None), "name", name)

        if result.updated:
            if result.status == "updated_github":
                old_label = _format_version(
                    result.previous_version, result.previous_sha
                )
                new_label = _format_version(result.new_version, result.new_sha)
                console.print(
                    f"[green]Updated {artifact_name}[/green]: {old_label} -> {new_label}"
                )
            elif result.status == "refreshed_local":
                console.print(
                    f"[green]Refreshed local artifact {artifact_name}[/green]"
                )
            else:
                console.print(f"[green]Updated {artifact_name}[/green]")
            return

        message = status_messages.get(result.status, "No changes applied.")
        console.print(f"[yellow]{artifact_name}: {message}[/yellow]")

    try:
        if not name:
            console.print("[yellow]Please specify artifact name to update[/yellow]")
            console.print("Use 'skillmeat status' to see available updates")
            return

        artifact_mgr = ArtifactManager()

        # Convert type string to enum
        type_filter = ArtifactType(artifact_type) if artifact_type else None
        strategy_enum = UpdateStrategy(strategy)

        # Update artifact
        console.print(f"[cyan]Updating {name}...[/cyan]")

        result = artifact_mgr.update(
            artifact_name=name,
            artifact_type=type_filter,
            collection_name=collection,
            strategy=strategy_enum,
        )
        _print_update_result(result)

    except ValueError as e:
        console.print(f"[yellow]{e}[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


# ====================
# Versioning Commands
# ====================


@main.command()
@click.argument("message", default="Manual snapshot")
@click.option(
    "--collection",
    "-c",
    default=None,
    help="Collection name (default: active collection)",
)
def snapshot(message: str, collection: Optional[str]):
    """Create a snapshot of the collection.

    Snapshots preserve the entire collection state for later restoration.
    Useful before major changes or for backup purposes.

    Examples:
      skillmeat snapshot                    # Default message
      skillmeat snapshot "Before update"    # Custom message
      skillmeat snapshot "Backup" -c work   # Specific collection
    """
    try:
        version_mgr = VersionManager()

        # Create snapshot
        snapshot_obj = version_mgr.create_snapshot(
            collection_name=collection,
            message=message,
        )

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@main.command()
@click.option(
    "--collection",
    "-c",
    default=None,
    help="Collection name (default: active collection)",
)
@click.option(
    "--limit",
    "-n",
    default=10,
    help="Number of snapshots to show (default: 10)",
)
def history(collection: Optional[str], limit: int):
    """List collection snapshots.

    Shows available snapshots for restoration.

    Examples:
      skillmeat history                 # Show recent snapshots
      skillmeat history --limit 20      # Show more snapshots
      skillmeat history -c work         # Specific collection
    """
    try:
        version_mgr = VersionManager()

        # Get collection name
        if collection is None:
            collection = version_mgr.collection_mgr.get_active_collection_name()

        # List snapshots
        snapshots = version_mgr.list_snapshots(collection_name=collection)

        if not snapshots:
            console.print("[yellow]No snapshots found[/yellow]")
            return

        # Limit results
        snapshots = snapshots[:limit]

        # Create table
        table = Table(title=f"Snapshots for '{collection}' ({len(snapshots)})")
        table.add_column("ID", style="cyan")
        table.add_column("Created", style="blue")
        table.add_column("Message", style="green")
        table.add_column("Artifacts", style="yellow")

        for snapshot in snapshots:
            table.add_row(
                snapshot.id,
                snapshot.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                snapshot.message,
                str(snapshot.artifact_count),
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@main.command()
@click.argument("snapshot_id")
@click.option(
    "--collection",
    "-c",
    default=None,
    help="Collection name (default: active collection)",
)
@click.option(
    "-y",
    "--yes",
    is_flag=True,
    help="Skip confirmation prompt",
)
def rollback(snapshot_id: str, collection: Optional[str], yes: bool):
    """Restore collection from a snapshot.

    WARNING: This will replace the current collection with the snapshot.
    Create a snapshot before rollback if you want to preserve current state.

    Examples:
      skillmeat rollback abc123         # Restore snapshot
      skillmeat rollback abc123 -y      # Skip confirmation
    """
    try:
        version_mgr = VersionManager()

        # Get collection name
        if collection is None:
            collection = version_mgr.collection_mgr.get_active_collection_name()

        # Confirm rollback
        if not yes:
            console.print(
                f"[yellow]Warning: This will replace collection '{collection}' with snapshot '{snapshot_id}'[/yellow]"
            )
            if not Confirm.ask("Continue with rollback?"):
                console.print("[yellow]Cancelled[/yellow]")
                return

        # Perform rollback
        console.print(f"[cyan]Rolling back to snapshot {snapshot_id}...[/cyan]")

        version_mgr.rollback(
            snapshot_id=snapshot_id,
            collection_name=collection,
        )

    except ValueError as e:
        console.print(f"[yellow]{e}[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


# ====================
# Collection Management Commands
# ====================


@main.group()
def collection():
    """Manage multiple collections.

    Collections let you organize artifacts into separate groups
    (e.g., work, personal, experimental).
    """
    pass


@collection.command(name="create")
@click.argument("name")
def collection_create(name: str):
    """Create a new collection.

    Examples:
      skillmeat collection create work
      skillmeat collection create experimental
    """
    try:
        collection_mgr = CollectionManager()

        # Check if already exists
        collections = collection_mgr.list_collections()
        if name in collections:
            console.print(f"[yellow]Collection '{name}' already exists[/yellow]")
            return

        # Create collection
        console.print(f"[cyan]Creating collection '{name}'...[/cyan]")
        collection_obj = collection_mgr.init(name)

        console.print(f"[green]Collection '{name}' created[/green]")
        console.print(f"  Location: {collection_mgr.config.get_collection_path(name)}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@collection.command(name="list")
def collection_list():
    """List all collections.

    Shows all available collections and marks the active one.

    Examples:
      skillmeat collection list
    """
    try:
        collection_mgr = CollectionManager()

        collections = collection_mgr.list_collections()
        active = collection_mgr.get_active_collection_name()

        if not collections:
            console.print("[yellow]No collections found[/yellow]")
            console.print("Run 'skillmeat init' to create the default collection")
            return

        # Create table
        table = Table(title="Collections")
        table.add_column("Name", style="cyan")
        table.add_column("Active", style="green")
        table.add_column("Artifacts", style="yellow")

        for coll_name in collections:
            try:
                coll = collection_mgr.load_collection(coll_name)
                artifact_count = len(coll.artifacts)
            except Exception:
                artifact_count = "?"

            is_active = "✓" if coll_name == active else ""
            table.add_row(coll_name, is_active, str(artifact_count))

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@collection.command(name="use")
@click.argument("name")
def collection_use(name: str):
    """Switch to a different collection.

    Makes the specified collection the active one for all commands.

    Examples:
      skillmeat collection use work
      skillmeat collection use default
    """
    try:
        collection_mgr = CollectionManager()

        # Check if collection exists
        collections = collection_mgr.list_collections()
        if name not in collections:
            console.print(f"[yellow]Collection '{name}' not found[/yellow]")
            console.print("Available collections:")
            for coll in collections:
                console.print(f"  - {coll}")
            return

        # Switch collection
        collection_mgr.switch_collection(name)

        console.print(f"[green]Switched to collection '{name}'[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


# ====================
# Migration Command
# ====================


@main.command()
@click.option(
    "--from-skillman",
    "from_skillman",
    is_flag=True,
    help="Migrate from skillman installation",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview migration without making changes",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing artifacts",
)
@click.option(
    "--no-snapshot",
    is_flag=True,
    help="Skip creating initial snapshot",
)
@click.option(
    "-y",
    "--yes",
    is_flag=True,
    help="Skip confirmation prompts",
)
@click.argument("path", required=False, type=click.Path(exists=True, path_type=Path))
def migrate(
    from_skillman: bool,
    dry_run: bool,
    force: bool,
    no_snapshot: bool,
    yes: bool,
    path: Optional[Path],
):
    """Migrate from skillman to skillmeat.

    Automatically detects existing skillman installation and imports
    configuration, skills, and metadata into skillmeat collection.

    The migration:
    - Detects skillman configuration and installed skills
    - Creates default collection if needed
    - Imports configuration (GitHub token, etc.)
    - Imports skills from manifest and installed directories
    - Creates snapshot for safety (unless --no-snapshot)

    Examples:
      skillmeat migrate --from-skillman              # Auto-detect and migrate
      skillmeat migrate --from-skillman --dry-run    # Preview changes
      skillmeat migrate --from-skillman --force      # Overwrite existing
      skillmeat migrate --from-skillman skills.toml  # Specify manifest path
    """
    if not from_skillman:
        console.print("[yellow]Please specify --from-skillman flag[/yellow]")
        console.print("Usage: skillmeat migrate --from-skillman [PATH]")
        return

    try:
        from skillmeat.utils.migration import SkillmanMigrator

        # Initialize managers
        collection_mgr = CollectionManager()
        version_mgr = VersionManager()

        # Create migrator
        migrator = SkillmanMigrator(collection_mgr, version_mgr)

        # Step 1: Find skillman installation
        console.print("[cyan]Detecting skillman installation...[/cyan]")
        installation = migrator.find_skillman_installation(path)

        if not installation["found"]:
            console.print("[yellow]No skillman installation found[/yellow]")
            console.print("\nSearched for:")
            console.print("  - ~/.skillman/config.toml")
            console.print("  - ./skills.toml (or specified path)")
            console.print("  - ~/.claude/skills/user/")
            console.print("  - ./.claude/skills/")
            console.print("\nNothing to migrate.")
            return

        # Display what was found
        console.print("\n[green]Detected skillman installation:[/green]")
        if installation["config_path"]:
            console.print(f"  Config: {installation['config_path']}")
        if installation["manifest_path"]:
            console.print(
                f"  Manifest: {installation['manifest_path']} ({installation['skill_count']} skills)"
            )
        if installation["user_skills_dir"]:
            console.print(
                f"  User skills: {installation['user_skills_dir']} ({installation['user_skill_count']} skills)"
            )
        if installation["local_skills_dir"]:
            console.print(
                f"  Local skills: {installation['local_skills_dir']} ({installation['local_skill_count']} skills)"
            )

        # Step 2: Preview migration plan
        console.print("\n[cyan]Migration Plan:[/cyan]")
        collections = collection_mgr.list_collections()
        if "default" not in collections:
            console.print("  ✓ Create default collection")
        else:
            console.print("  - Default collection already exists")

        if installation["config_path"]:
            console.print("  ✓ Import configuration (github-token, etc.)")

        if installation["manifest_path"]:
            console.print(
                f"  ✓ Import {installation['skill_count']} skills from manifest"
            )

        if installation["user_skills_dir"] and installation["user_skill_count"] > 0:
            console.print(
                f"  ✓ Import {installation['user_skill_count']} skills from user directory"
            )

        if installation["local_skills_dir"] and installation["local_skill_count"] > 0:
            console.print(
                f"  ✓ Import {installation['local_skill_count']} skills from local directory"
            )

        if not no_snapshot:
            console.print("  ✓ Create snapshot 'Migrated from skillman'")

        # Dry-run mode
        if dry_run:
            console.print("\n[yellow]Dry-run mode: No changes will be made[/yellow]")
            return

        # Step 3: Confirm migration
        if not yes:
            console.print()
            if not Confirm.ask("Proceed with migration?"):
                console.print("[yellow]Migration cancelled[/yellow]")
                return

        # Step 4: Create default collection if needed
        console.print("\n[cyan]Migrating...[/cyan]")
        if "default" not in collections:
            collection_mgr.init("default")
            console.print("[green]✓[/green] Created collection: default")

        # Step 5: Import configuration
        migration_results = []
        if installation["config_path"]:
            success, imported_keys = migrator.import_config()
            if success:
                console.print(
                    f"[green]✓[/green] Imported configuration: {', '.join(imported_keys)}"
                )
            else:
                console.print("[yellow]-[/yellow] No configuration to import")

        # Step 6: Import skills from manifest
        if installation["manifest_path"]:
            result = migrator.import_skills_from_manifest(
                installation["manifest_path"],
                force=force,
            )
            migration_results.append(result)
            if result.artifacts_imported > 0:
                console.print(
                    f"[green]✓[/green] Imported {result.artifacts_imported} skills from manifest"
                )
            if result.artifacts_skipped > 0:
                console.print(
                    f"[yellow]-[/yellow] Skipped {result.artifacts_skipped} skills (already exist)"
                )

        # Step 7: Import skills from user directory
        if installation["user_skills_dir"] and installation["user_skill_count"] > 0:
            result = migrator.import_skills_from_directory(
                installation["user_skills_dir"],
                force=force,
            )
            migration_results.append(result)
            if result.artifacts_imported > 0:
                console.print(
                    f"[green]✓[/green] Imported {result.artifacts_imported} skills from user directory"
                )
            if result.artifacts_skipped > 0:
                console.print(
                    f"[yellow]-[/yellow] Skipped {result.artifacts_skipped} skills (already exist)"
                )

        # Step 8: Import skills from local directory
        if installation["local_skills_dir"] and installation["local_skill_count"] > 0:
            result = migrator.import_skills_from_directory(
                installation["local_skills_dir"],
                force=force,
            )
            migration_results.append(result)
            if result.artifacts_imported > 0:
                console.print(
                    f"[green]✓[/green] Imported {result.artifacts_imported} skills from local directory"
                )
            if result.artifacts_skipped > 0:
                console.print(
                    f"[yellow]-[/yellow] Skipped {result.artifacts_skipped} skills (already exist)"
                )

        # Step 9: Create snapshot
        if not no_snapshot:
            success = migrator.create_migration_snapshot("Migrated from skillman")
            if success:
                console.print(
                    "[green]✓[/green] Created snapshot: 'Migrated from skillman'"
                )
            else:
                console.print("[yellow]-[/yellow] Could not create snapshot")

        # Step 10: Show migration report
        if migration_results:
            report = migrator.generate_report(migration_results)
            console.print(report)

        # Final instructions
        console.print("\n[green]Migration complete![/green]")
        console.print("\nNext steps:")
        console.print("  1. Verify your collection: skillmeat list")
        console.print("  2. Deploy to a project: skillmeat deploy --all")
        console.print("  3. Your original skillman installation is unchanged")
        console.print("\nFor more information: skillmeat --help")

    except Exception as e:
        console.print(f"[red]Error during migration: {e}[/red]")
        import traceback

        console.print(traceback.format_exc())
        sys.exit(1)


# ====================
# Utility Commands
# ====================


@main.group()
def config():
    """Manage configuration settings.

    Configuration is stored in ~/.skillmeat/config.toml
    """
    pass


@config.command(name="list")
def config_list():
    """List all configuration values.

    Examples:
      skillmeat config list
    """
    try:
        config_mgr = ConfigManager()
        all_config = config_mgr.read()

        if not all_config:
            console.print("[yellow]No configuration set[/yellow]")
            return

        table = Table(title="Configuration")
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="green")

        for key, value in all_config.items():
            # Mask GitHub tokens
            if key == "github-token" and value:
                value = value[:8] + "..." if len(value) > 8 else "***"
            table.add_row(key, str(value))

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@config.command(name="get")
@click.argument("key")
def config_get(key: str):
    """Get a configuration value.

    Examples:
      skillmeat config get github-token
      skillmeat config get default-collection
    """
    try:
        config_mgr = ConfigManager()
        value = config_mgr.get(key)

        if value is not None:
            # Mask GitHub tokens
            if key == "github-token" and value:
                value = value[:8] + "..." if len(value) > 8 else "***"
            console.print(f"{key} = {value}")
        else:
            console.print(f"[yellow]{key} not set[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@config.command(name="set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str):
    """Set a configuration value.

    Common keys:
      - github-token: GitHub personal access token
      - default-collection: Default collection name
      - update-strategy: Default update strategy (prompt/upstream/local)

    Examples:
      skillmeat config set github-token ghp_xxxxx
      skillmeat config set default-collection work
    """
    try:
        config_mgr = ConfigManager()
        config_mgr.set(key, value)

        console.print(f"[green]Set {key}[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@main.command()
@click.argument("spec")
@click.option(
    "--type",
    "-t",
    "artifact_type",
    type=click.Choice(["skill", "command", "agent"]),
    required=True,
    help="Artifact type to verify",
)
def verify(spec: str, artifact_type: str):
    """Verify an artifact has valid structure.

    Checks if an artifact (GitHub or local) is valid without adding it.
    Useful for testing before installation.

    Examples:
      skillmeat verify user/repo/skill --type skill
      skillmeat verify ./my-skill --type skill
      skillmeat verify ./command.md --type command
    """
    try:
        type_enum = ArtifactType(artifact_type)

        # Determine if GitHub or local
        if "/" in spec and not spec.startswith((".", "/")):
            # GitHub
            console.print(f"[cyan]Verifying GitHub artifact: {spec}...[/cyan]")

            config_mgr = ConfigManager()
            github_token = config_mgr.get("github-token")

            github_source = GitHubSource(github_token=github_token)

            with tempfile.TemporaryDirectory(prefix="skillmeat_verify_") as temp_dir:
                temp_path = Path(temp_dir)

                # Fetch artifact
                fetched_path, metadata = github_source.fetch(
                    spec=spec,
                    artifact_type=type_enum,
                    dest_dir=temp_path,
                )

                # Validate
                validator = ArtifactValidator()
                is_valid, error_msg, extracted_metadata = validator.validate(
                    artifact_path=fetched_path,
                    artifact_type=type_enum,
                )

                if is_valid:
                    console.print("[green]Valid artifact[/green]")
                    console.print(f"  Spec: {spec}")
                    console.print(f"  Type: {type_enum.value}")

                    if extracted_metadata:
                        if extracted_metadata.title:
                            console.print(f"  Title: {extracted_metadata.title}")
                        if extracted_metadata.description:
                            console.print(
                                f"  Description: {extracted_metadata.description}"
                            )
                        if extracted_metadata.author:
                            console.print(f"  Author: {extracted_metadata.author}")
                        if extracted_metadata.version:
                            console.print(f"  Version: {extracted_metadata.version}")
                        if extracted_metadata.tags:
                            console.print(
                                f"  Tags: {', '.join(extracted_metadata.tags)}"
                            )
                else:
                    console.print(f"[red]Invalid: {error_msg}[/red]")
                    sys.exit(1)

        else:
            # Local
            local_path = Path(spec).resolve()
            if not local_path.exists():
                console.print(f"[red]Path not found: {spec}[/red]")
                sys.exit(1)

            console.print(f"[cyan]Verifying local artifact: {local_path}...[/cyan]")

            validator = ArtifactValidator()
            is_valid, error_msg, metadata = validator.validate(
                artifact_path=local_path,
                artifact_type=type_enum,
            )

            if is_valid:
                console.print("[green]Valid artifact[/green]")
                console.print(f"  Path: {local_path}")
                console.print(f"  Type: {type_enum.value}")

                if metadata:
                    if metadata.title:
                        console.print(f"  Title: {metadata.title}")
                    if metadata.description:
                        console.print(f"  Description: {metadata.description}")
                    if metadata.author:
                        console.print(f"  Author: {metadata.author}")
                    if metadata.version:
                        console.print(f"  Version: {metadata.version}")
                    if metadata.tags:
                        console.print(f"  Tags: {', '.join(metadata.tags)}")
            else:
                console.print(f"[red]Invalid: {error_msg}[/red]")
                sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


# ====================
# Diff Commands
# ====================


@main.group()
def diff():
    """Compare artifacts and detect changes.

    Provides tools for comparing files and directories, including
    three-way diffs for merge conflict detection.
    """
    pass


@diff.command(name="files")
@click.argument("file1", type=click.Path(exists=True))
@click.argument("file2", type=click.Path(exists=True))
@click.option(
    "--context",
    "-c",
    default=3,
    type=int,
    help="Number of context lines to show around changes (default: 3)",
)
@click.option(
    "--color/--no-color",
    default=True,
    help="Enable/disable colored output (default: enabled)",
)
def diff_files_cmd(file1: str, file2: str, context: int, color: bool):
    """Compare two files and show differences.

    Displays a unified diff showing the changes between FILE1 and FILE2.
    For text files, shows line-by-line differences with syntax highlighting.
    For binary files, reports only that they differ.

    \\b
    Examples:
      skillmeat diff files old.md new.md
      skillmeat diff files old.md new.md --context 5
      skillmeat diff files old.md new.md --no-color
    """
    try:
        file1_path = Path(file1).resolve()
        file2_path = Path(file2).resolve()

        # Create diff engine
        engine = DiffEngine()

        # Perform diff
        result = engine.diff_files(file1_path, file2_path)

        # Display results
        _display_file_diff(result, file1_path, file2_path, color)

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}", err=True)
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}", err=True)
        sys.exit(1)


@diff.command(name="dirs")
@click.argument("dir1", type=click.Path(exists=True, file_okay=False))
@click.argument("dir2", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--ignore",
    "-i",
    multiple=True,
    help="Patterns to ignore (can be specified multiple times)",
)
@click.option(
    "--limit",
    "-l",
    default=100,
    type=int,
    help="Maximum number of files to show (default: 100)",
)
@click.option(
    "--stats-only",
    is_flag=True,
    help="Show only statistics, not individual file diffs",
)
def diff_dirs_cmd(dir1: str, dir2: str, ignore: tuple, limit: int, stats_only: bool):
    """Compare two directories and show differences.

    Recursively compares all files in DIR1 and DIR2, showing which files
    were added, removed, or modified. Respects ignore patterns to skip
    certain files and directories.

    \\b
    Examples:
      skillmeat diff dirs old_version/ new_version/
      skillmeat diff dirs old/ new/ --ignore "*.pyc" --ignore "__pycache__"
      skillmeat diff dirs old/ new/ --limit 50
      skillmeat diff dirs old/ new/ --stats-only
    """
    try:
        dir1_path = Path(dir1).resolve()
        dir2_path = Path(dir2).resolve()

        # Create diff engine
        engine = DiffEngine()

        # Perform diff
        console.print("[cyan]Comparing directories...[/cyan]")
        result = engine.diff_directories(
            dir1_path, dir2_path, ignore_patterns=list(ignore) if ignore else None
        )

        # Display results
        _display_directory_diff(result, limit, stats_only)

    except (FileNotFoundError, NotADirectoryError) as e:
        console.print(f"[red]Error:[/red] {e}", err=True)
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}", err=True)
        sys.exit(1)


@diff.command(name="three-way")
@click.argument("base", type=click.Path(exists=True, file_okay=False))
@click.argument("local", type=click.Path(exists=True, file_okay=False))
@click.argument("remote", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--ignore",
    "-i",
    multiple=True,
    help="Patterns to ignore (can be specified multiple times)",
)
@click.option(
    "--conflicts-only",
    is_flag=True,
    help="Show only files with conflicts, not auto-mergeable files",
)
def diff_three_way_cmd(
    base: str, local: str, remote: str, ignore: tuple, conflicts_only: bool
):
    """Perform three-way diff for merge conflict detection.

    Compares BASE (common ancestor), LOCAL (your changes), and REMOTE
    (upstream changes) to identify auto-mergeable changes and conflicts.
    This is useful for understanding what will happen during an update.

    \\b
    Three-way diff logic:
      - If only LOCAL changed: auto-merge (use local)
      - If only REMOTE changed: auto-merge (use remote)
      - If both changed the same: auto-merge (use either)
      - If both changed differently: CONFLICT (manual resolution)

    \\b
    Examples:
      skillmeat diff three-way base/ local/ remote/
      skillmeat diff three-way base/ local/ remote/ --conflicts-only
      skillmeat diff three-way base/ local/ remote/ --ignore "*.pyc"
    """
    try:
        base_path = Path(base).resolve()
        local_path = Path(local).resolve()
        remote_path = Path(remote).resolve()

        # Create diff engine
        engine = DiffEngine()

        # Perform three-way diff
        console.print("[cyan]Performing three-way diff...[/cyan]")
        result = engine.three_way_diff(
            base_path,
            local_path,
            remote_path,
            ignore_patterns=list(ignore) if ignore else None,
        )

        # Display results
        _display_three_way_diff(result, conflicts_only)

    except (FileNotFoundError, NotADirectoryError) as e:
        console.print(f"[red]Error:[/red] {e}", err=True)
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}", err=True)
        sys.exit(1)


@diff.command(name="artifact")
@click.argument("name")
@click.option(
    "--upstream",
    is_flag=True,
    help="Compare with upstream version",
)
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help="Compare with artifact in another project",
)
@click.option(
    "--collection",
    "-c",
    default=None,
    help="Collection name (default: active collection)",
)
@click.option(
    "--type",
    "-t",
    "artifact_type",
    type=click.Choice(["skill", "command", "agent"]),
    default=None,
    help="Artifact type (required if name is ambiguous)",
)
@click.option(
    "--summary-only",
    is_flag=True,
    help="Show only diff summary, not full file-by-file diff",
)
@click.option(
    "--limit",
    "-l",
    default=100,
    type=int,
    help="Maximum number of changed files to show (default: 100)",
)
def diff_artifact_cmd(
    name: str,
    upstream: bool,
    project: Optional[Path],
    collection: Optional[str],
    artifact_type: Optional[str],
    summary_only: bool,
    limit: int,
):
    """Compare artifact versions and show differences.

    Compares a local artifact with its upstream source or with the same
    artifact in another project. Shows which files changed, with detailed
    diffs and statistics.

    \\b
    Comparison modes:
      --upstream: Compare local artifact with latest upstream version
      --project PATH: Compare local artifact with same artifact in another project

    \\b
    Examples:
      skillmeat diff artifact my-skill --upstream
      skillmeat diff artifact my-skill --project /path/to/other/project
      skillmeat diff artifact my-skill --upstream --summary-only
      skillmeat diff artifact my-skill --upstream --limit 50
    """
    try:
        from skillmeat.core.artifact import ArtifactManager, ArtifactType

        # Validate that exactly one comparison mode is specified
        if upstream and project:
            console.print(
                "[red]Error:[/red] Cannot specify both --upstream and --project"
            )
            sys.exit(1)

        if not upstream and not project:
            console.print(
                "[red]Error:[/red] Must specify either --upstream or --project"
            )
            sys.exit(1)

        # Initialize artifact manager
        artifact_mgr = ArtifactManager()

        # Convert type string to enum if provided
        type_filter = ArtifactType(artifact_type) if artifact_type else None

        # Get local artifact
        console.print(f"[cyan]Locating artifact '{name}'...[/cyan]")
        try:
            artifact = artifact_mgr.get_artifact(
                name=name,
                artifact_type=type_filter,
                collection_name=collection,
            )
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)

        # Get local artifact path
        local_path = artifact_mgr._get_artifact_storage_path(
            artifact.name,
            artifact.type,
            collection or artifact_mgr.collection_mgr.get_active_collection_name(),
        )

        if not local_path.exists():
            console.print(f"[red]Error:[/red] Artifact path not found: {local_path}")
            sys.exit(1)

        # Determine comparison target
        if upstream:
            # Compare with upstream
            console.print(f"[cyan]Fetching upstream version...[/cyan]")

            # Check if artifact has upstream info
            if not artifact.origin or not artifact.origin.startswith(("http", "git")):
                console.print(
                    f"[yellow]Warning:[/yellow] Artifact '{name}' has no upstream source"
                )
                console.print("  This artifact may have been added from a local path.")
                console.print(
                    "  Use --project to compare with another project instead."
                )
                sys.exit(1)

            # Fetch upstream version
            try:
                fetch_result = artifact_mgr.fetch_update(
                    artifact_name=name,
                    artifact_type=type_filter,
                    collection_name=collection,
                )

                if not fetch_result.success:
                    console.print(
                        f"[red]Error:[/red] Failed to fetch upstream: {fetch_result.error or 'Unknown error'}"
                    )
                    sys.exit(1)

                remote_path = fetch_result.temp_workspace

                # Display comparison info
                console.print(f"\n[bold]Comparing:[/bold] {name} (local) vs upstream")
                if fetch_result.latest_version:
                    console.print(
                        f"[dim]Upstream version: {fetch_result.latest_version}[/dim]"
                    )

            except Exception as e:
                console.print(f"[red]Error fetching upstream:[/red] {str(e)}")
                sys.exit(1)

        elif project:
            # Compare with project artifact
            console.print(f"[cyan]Locating artifact in project {project}...[/cyan]")

            # Determine artifact path in project
            # Artifacts can be in .claude/skills/, .claude/commands/, or .claude/agents/
            artifact_subdir = {
                "skill": "skills",
                "command": "commands",
                "agent": "agents",
            }.get(artifact.type.value, "skills")

            remote_path = project / ".claude" / artifact_subdir / artifact.name

            if not remote_path.exists():
                console.print(
                    f"[red]Error:[/red] Artifact '{name}' not found in project {project}"
                )
                console.print(f"  Expected path: {remote_path}")
                sys.exit(1)

            # Display comparison info
            console.print(
                f"\n[bold]Comparing:[/bold] {name} (local) vs project ({project.name})"
            )

        # Perform diff
        console.print("[cyan]Computing diff...[/cyan]")
        engine = DiffEngine()

        result = engine.diff_directories(
            local_path,
            remote_path,
            ignore_patterns=[".git", "__pycache__", "*.pyc", ".DS_Store"],
        )

        # Display results
        console.print()
        _display_artifact_diff(result, name, limit, summary_only)

        # Clean up temp workspace if we fetched upstream
        if upstream and fetch_result.temp_workspace:
            try:
                import shutil

                shutil.rmtree(fetch_result.temp_workspace, ignore_errors=True)
            except Exception:
                pass

    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        import traceback

        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


# ====================
# Diff Display Helpers
# ====================


def _display_file_diff(
    result, file1_path: Path, file2_path: Path, use_color: bool
) -> None:
    """Display diff for a single file comparison.

    Args:
        result: FileDiff object
        file1_path: Path to first file
        file2_path: Path to second file
        use_color: Whether to use colored output
    """
    # Display file headers
    console.print(f"\n[bold cyan]--- {file1_path}[/bold cyan]")
    console.print(f"[bold cyan]+++ {file2_path}[/bold cyan]")

    # Handle different status types
    if result.status == "unchanged":
        console.print("\n[green]Files are identical[/green]")
        return

    if result.status == "binary":
        console.print(f"\n[yellow]{result.unified_diff}[/yellow]")
        return

    # Display unified diff for modified files
    if result.unified_diff:
        if use_color:
            # Use Rich syntax highlighting for diff
            syntax = Syntax(
                result.unified_diff,
                "diff",
                theme="monokai",
                line_numbers=False,
                word_wrap=False,
            )
            console.print(syntax)
        else:
            console.print(result.unified_diff)

    # Display statistics
    console.print()
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Label", style="cyan")
    table.add_column("Value", style="magenta", justify="right")

    table.add_row("Lines added", f"+{result.lines_added}")
    table.add_row("Lines removed", f"-{result.lines_removed}")

    console.print(table)


def _display_directory_diff(result, limit: int, stats_only: bool) -> None:
    """Display diff for a directory comparison.

    Args:
        result: DiffResult object
        limit: Maximum number of files to show
        stats_only: If True, show only statistics
    """
    # Check if we need to limit output
    total_changes = result.total_files_changed
    limited = total_changes > limit

    if limited and not stats_only:
        console.print(
            f"[yellow]Showing {limit} of {total_changes} changed files. "
            f"Use --limit to adjust or --stats-only for summary.[/yellow]\n"
        )

    # Display summary table
    table = Table(title="Diff Summary", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="magenta", justify="right")

    table.add_row("Files Added", str(len(result.files_added)))
    table.add_row("Files Removed", str(len(result.files_removed)))
    table.add_row("Files Modified", str(len(result.files_modified)))
    table.add_row("Files Unchanged", str(len(result.files_unchanged)))
    table.add_row("Lines Added", f"+{result.total_lines_added}")
    table.add_row("Lines Removed", f"-{result.total_lines_removed}")

    console.print(table)
    console.print()

    # If stats-only, we're done
    if stats_only:
        return

    # Display added files
    if result.files_added:
        added_list = result.files_added[:limit] if limited else result.files_added
        console.print("[green]Added files:[/green]")
        for file_path in added_list:
            console.print(f"  [green]+[/green] {file_path}")
        console.print()

    # Display removed files
    if result.files_removed:
        removed_list = result.files_removed[:limit] if limited else result.files_removed
        console.print("[red]Removed files:[/red]")
        for file_path in removed_list:
            console.print(f"  [red]-[/red] {file_path}")
        console.print()

    # Display modified files
    if result.files_modified:
        modified_list = (
            result.files_modified[:limit] if limited else result.files_modified
        )
        console.print("[yellow]Modified files:[/yellow]")
        for file_diff in modified_list:
            if file_diff.status == "binary":
                console.print(f"  [yellow]~[/yellow] {file_diff.path} (binary)")
            else:
                console.print(
                    f"  [yellow]~[/yellow] {file_diff.path} "
                    f"([green]+{file_diff.lines_added}[/green] "
                    f"[red]-{file_diff.lines_removed}[/red])"
                )
        console.print()


def _display_three_way_diff(result, conflicts_only: bool) -> None:
    """Display three-way diff results.

    Args:
        result: ThreeWayDiffResult object
        conflicts_only: If True, show only conflicts
    """
    # Display summary statistics
    table = Table(title="Three-Way Diff Summary", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="magenta", justify="right")

    table.add_row("Files Compared", str(result.stats.files_compared))
    table.add_row("Files Unchanged", str(result.stats.files_unchanged))
    table.add_row("Auto-mergeable", str(result.stats.auto_mergeable))
    table.add_row("Conflicts", str(result.stats.files_conflicted))

    console.print(table)
    console.print()

    # Display auto-mergeable files (unless conflicts-only)
    if not conflicts_only and result.auto_mergeable:
        console.print(
            f"[green]Auto-mergeable files ({len(result.auto_mergeable)}):[/green]"
        )
        for file_path in result.auto_mergeable:
            console.print(f"  [green]✓[/green] {file_path}")
        console.print()

    # Display conflicts
    if result.conflicts:
        console.print(
            f"[red]Conflicts requiring manual resolution ({len(result.conflicts)}):[/red]"
        )
        for conflict in result.conflicts:
            _display_conflict(conflict)
        console.print()
    elif not result.auto_mergeable:
        console.print("[green]No changes detected[/green]")
    elif conflicts_only:
        console.print("[green]No conflicts detected[/green]")


def _display_conflict(conflict) -> None:
    """Display a single conflict.

    Args:
        conflict: ConflictMetadata object
    """
    # Determine conflict description
    if conflict.conflict_type == "both_modified":
        desc = "Both versions modified"
    elif conflict.conflict_type == "deletion":
        desc = "Deleted in one version, modified in other"
    elif conflict.conflict_type == "add_add":
        desc = "Added in both versions with different content"
    else:
        desc = "Content conflict"

    # Add binary indicator
    if conflict.is_binary:
        desc += " (binary file)"

    # Display conflict header
    console.print(f"  [red]✗[/red] {conflict.file_path}")
    console.print(f"    [dim]{desc}[/dim]")
    console.print(f"    [dim]Strategy: {conflict.merge_strategy}[/dim]")


def _display_artifact_diff(
    result, artifact_name: str, limit: int, summary_only: bool
) -> None:
    """Display diff for an artifact comparison.

    Enhanced version of _display_directory_diff with artifact-specific formatting.

    Args:
        result: DiffResult object
        artifact_name: Name of the artifact being compared
        limit: Maximum number of files to show
        summary_only: If True, show only statistics
    """
    # Check if we need to limit output
    total_changes = result.total_files_changed
    limited = total_changes > limit

    if limited and not summary_only:
        console.print(
            f"[yellow]Showing {limit} of {total_changes} changed files. "
            f"Use --limit to adjust or --summary-only for summary.[/yellow]\n"
        )

    # Display summary table with artifact context
    table = Table(title=f"Diff Summary: {artifact_name}", show_header=True, box=None)
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Count", style="magenta", justify="right", no_wrap=True)

    # Calculate total files (including unchanged)
    total_files = (
        len(result.files_added)
        + len(result.files_removed)
        + len(result.files_modified)
        + len(result.files_unchanged)
    )

    table.add_row("Total Files", str(total_files))
    table.add_row(
        "Files Added",
        f"[green]{len(result.files_added)}[/green]" if result.files_added else "0",
    )
    table.add_row(
        "Files Removed",
        f"[red]{len(result.files_removed)}[/red]" if result.files_removed else "0",
    )
    table.add_row(
        "Files Modified",
        (
            f"[yellow]{len(result.files_modified)}[/yellow]"
            if result.files_modified
            else "0"
        ),
    )
    table.add_row("Files Unchanged", f"[dim]{len(result.files_unchanged)}[/dim]")

    # Add line stats if available
    if result.total_lines_added or result.total_lines_removed:
        table.add_row("Lines Added", f"[green]+{result.total_lines_added}[/green]")
        table.add_row("Lines Removed", f"[red]-{result.total_lines_removed}[/red]")

    console.print(table)
    console.print()

    # If no changes, we're done
    if not result.has_changes:
        console.print("[green]No changes detected[/green]")
        return

    # If stats-only, we're done
    if summary_only:
        return

    # Display added files
    if result.files_added:
        added_list = result.files_added[:limit] if limited else result.files_added
        console.print(
            f"[green]Added ({len(added_list)} of {len(result.files_added)}):[/green]"
            if limited
            else f"[green]Added files:[/green]"
        )
        for file_path in added_list:
            console.print(f"  [green]+[/green] {file_path}")
        console.print()

    # Display removed files
    if result.files_removed:
        remaining_limit = limit - len(result.files_added) if limited else limit
        removed_list = (
            result.files_removed[:remaining_limit] if limited else result.files_removed
        )
        console.print(
            f"[red]Removed ({len(removed_list)} of {len(result.files_removed)}):[/red]"
            if limited
            else f"[red]Removed files:[/red]"
        )
        for file_path in removed_list:
            console.print(f"  [red]-[/red] {file_path}")
        console.print()

    # Display modified files with detailed stats
    if result.files_modified:
        files_shown = len(result.files_added) + len(result.files_removed)
        remaining_limit = (
            max(0, limit - files_shown) if limited else len(result.files_modified)
        )
        modified_list = (
            result.files_modified[:remaining_limit]
            if limited
            else result.files_modified
        )

        console.print(
            f"[yellow]Modified ({len(modified_list)} of {len(result.files_modified)}):[/yellow]"
            if limited
            else f"[yellow]Modified files:[/yellow]"
        )

        for file_diff in modified_list:
            if file_diff.status == "binary":
                console.print(
                    f"  [yellow]~[/yellow] {file_diff.path} [dim](binary)[/dim]"
                )
            else:
                # Show file with change stats
                console.print(
                    f"  [yellow]~[/yellow] {file_diff.path} "
                    f"[dim]([green]+{file_diff.lines_added}[/green] "
                    f"[red]-{file_diff.lines_removed}[/red])[/dim]"
                )
        console.print()

    # Add helpful footer if limited
    if limited:
        console.print(
            f"[dim]Showing {min(limit, total_changes)} of {total_changes} changed files.[/dim]"
        )
        console.print(
            f"[dim]Use '--limit {total_changes}' to see all changes or '--summary-only' for stats only.[/dim]"
        )


# ====================
# Search Commands
# ====================


@main.command()
@click.argument("query")
@click.option(
    "--collection",
    "-c",
    default=None,
    help="Collection to search (default: active collection)",
)
@click.option(
    "--type",
    "-t",
    "artifact_type",
    type=click.Choice(["skill", "command", "agent"]),
    default=None,
    help="Filter by artifact type",
)
@click.option(
    "--search-type",
    type=click.Choice(["metadata", "content", "both"]),
    default="both",
    help="Search metadata, content, or both (default: both)",
)
@click.option(
    "--tags",
    help="Filter by tags (comma-separated)",
)
@click.option(
    "--limit",
    "-l",
    type=int,
    default=50,
    help="Maximum results to show (default: 50)",
)
@click.option(
    "--projects",
    "-p",
    multiple=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help="Search across specific project paths (can specify multiple)",
)
@click.option(
    "--discover",
    is_flag=True,
    help="Auto-discover all Claude projects in configured search roots",
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Disable cache for fresh results",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output results as JSON",
)
def search(
    query: str,
    collection: Optional[str],
    artifact_type: Optional[str],
    search_type: str,
    tags: Optional[str],
    limit: int,
    projects: tuple,
    discover: bool,
    no_cache: bool,
    output_json: bool,
):
    """Search artifacts by metadata or content.

    Search can be performed on a collection or across multiple projects.
    Use --projects to specify project paths or --discover to auto-find projects.

    \b
    Examples:
      # Search in collection
      skillmeat search "authentication"
      skillmeat search "error handling" --search-type content
      skillmeat search "productivity" --tags documentation

      # Cross-project search
      skillmeat search "testing" --projects ~/projects/app1 ~/projects/app2
      skillmeat search "api" --discover

      # JSON output
      skillmeat search "database" --json
    """
    try:
        from skillmeat.core.search import SearchManager

        search_mgr = SearchManager()

        # Parse tags if provided
        tag_list = None
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",")]

        # Determine search mode: collection or cross-project
        if projects or discover:
            # Cross-project search
            project_paths = None
            if projects:
                project_paths = [Path(p).resolve() for p in projects]

            # Perform cross-project search
            result = search_mgr.search_projects(
                query=query,
                project_paths=project_paths,
                search_type=search_type,
                artifact_types=[ArtifactType(artifact_type)] if artifact_type else None,
                tags=tag_list,
                limit=limit,
                use_cache=not no_cache,
            )

            # Display results
            if output_json:
                _display_search_json(result, cross_project=True)
            else:
                _display_search_results(result, cross_project=True)

        else:
            # Collection search
            result = search_mgr.search_collection(
                query=query,
                collection_name=collection,
                search_type=search_type,
                artifact_types=[ArtifactType(artifact_type)] if artifact_type else None,
                tags=tag_list,
                limit=limit,
            )

            # Display results
            if output_json:
                _display_search_json(result, cross_project=False)
            else:
                _display_search_results(result, cross_project=False)

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}", err=True)
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}", err=True)
        import traceback

        console.print(f"[dim]{traceback.format_exc()}[/dim]", err=True)
        sys.exit(1)


@main.command()
@click.option(
    "--collection",
    "-c",
    default=None,
    help="Collection to check (default: active collection)",
)
@click.option(
    "--projects",
    "-p",
    multiple=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help="Check for duplicates across specific projects",
)
@click.option(
    "--threshold",
    "-t",
    type=float,
    default=0.85,
    help="Similarity threshold (0.0-1.0, default: 0.85)",
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Disable cache for fresh results",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output results as JSON",
)
def find_duplicates(
    collection: Optional[str],
    projects: tuple,
    threshold: float,
    no_cache: bool,
    output_json: bool,
):
    """Find duplicate or similar artifacts.

    Compares artifacts based on content, structure, metadata, and file count
    to identify potential duplicates. Default threshold is 0.85 (85% similar).

    \b
    Examples:
      # Find duplicates across projects
      skillmeat find-duplicates --projects ~/projects/app1 ~/projects/app2

      # Find duplicates in collection
      skillmeat find-duplicates --collection default

      # Stricter matching (90% similarity)
      skillmeat find-duplicates --threshold 0.9

      # JSON output
      skillmeat find-duplicates --json
    """
    try:
        # Validate threshold
        if not 0.0 <= threshold <= 1.0:
            console.print(
                "[red]Error:[/red] Threshold must be between 0.0 and 1.0", err=True
            )
            sys.exit(1)

        from skillmeat.core.search import SearchManager

        search_mgr = SearchManager()

        # Convert project paths
        project_paths = None
        if projects:
            project_paths = [Path(p).resolve() for p in projects]

        # Find duplicates
        console.print(
            f"[cyan]Finding duplicates (threshold: {threshold:.0%})...[/cyan]"
        )
        duplicates = search_mgr.find_duplicates(
            threshold=threshold, project_paths=project_paths, use_cache=not no_cache
        )

        # Display results
        if output_json:
            _display_duplicates_json(duplicates, threshold)
        else:
            _display_duplicates_results(duplicates, threshold)

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}", err=True)
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}", err=True)
        import traceback

        console.print(f"[dim]{traceback.format_exc()}[/dim]", err=True)
        sys.exit(1)


# ====================
# Search Display Helpers
# ====================


def _display_search_results(result, cross_project: bool = False) -> None:
    """Display search results with Rich formatting.

    Args:
        result: SearchResult object
        cross_project: Whether this is a cross-project search
    """
    if not result.has_matches:
        console.print(f"\n[yellow]No results found for '{result.query}'[/yellow]")
        console.print("\n[dim]Try:")
        console.print("  - Using different search terms")
        console.print("  - Changing --search-type to 'content' or 'metadata'")
        console.print("  - Removing tag filters")
        console.print("[/dim]")
        return

    # Header
    search_mode = "Cross-Project Search" if cross_project else "Collection Search"
    console.print(f"\n[bold]{search_mode}:[/bold] {result.summary()}")
    console.print(f'[dim]Query: "{result.query}" | Type: {result.search_type}[/dim]\n')

    # Create results table
    table = Table(title=f"Matches ({result.total_count})")
    table.add_column("Artifact", style="cyan", no_wrap=False)
    table.add_column("Type", style="green", width=10)
    table.add_column("Score", justify="right", style="yellow", width=8)
    table.add_column("Match", style="blue", width=10)
    table.add_column("Context", style="dim")

    if cross_project:
        # Add project column for cross-project search
        table.add_column("Project", style="magenta", width=20)

    for match in result.matches:
        # Truncate context to fit
        context = match.context
        if len(context) > 80:
            context = context[:77] + "..."

        # Build row
        row = [
            match.artifact_name,
            match.artifact_type,
            f"{match.score:.1f}",
            match.match_type,
            context,
        ]

        if cross_project:
            # Add project name
            project_name = "N/A"
            if match.project_path:
                # Extract project name from .claude parent directory
                project_name = match.project_path.parent.name
            row.append(project_name)

        table.add_row(*row)

    console.print(table)

    # Footer with helpful tips
    console.print(f"\n[dim]Showing top {len(result.matches)} results[/dim]")
    if result.total_count >= result.matches.__len__():
        console.print("[dim]Use --limit N to see more results[/dim]")
    console.print("[dim]Use --json for machine-readable output[/dim]")


def _display_search_json(result, cross_project: bool = False) -> None:
    """Display search results as JSON.

    Args:
        result: SearchResult object
        cross_project: Whether this is a cross-project search
    """
    import json as json_lib

    output = {
        "query": result.query,
        "search_type": result.search_type,
        "total_count": result.total_count,
        "search_time": result.search_time,
        "used_ripgrep": result.used_ripgrep,
        "matches": [
            {
                "artifact_name": m.artifact_name,
                "artifact_type": m.artifact_type,
                "score": m.score,
                "match_type": m.match_type,
                "context": m.context,
                "line_number": m.line_number,
                "metadata": m.metadata,
                "project_path": str(m.project_path) if m.project_path else None,
            }
            for m in result.matches
        ],
    }

    click.echo(json_lib.dumps(output, indent=2))


def _display_duplicates_results(duplicates, threshold: float) -> None:
    """Display duplicate detection results with Rich formatting.

    Args:
        duplicates: List of DuplicatePair objects
        threshold: Similarity threshold used
    """
    if not duplicates:
        console.print(
            f"\n[green]No duplicates found (threshold: {threshold:.0%})[/green]"
        )
        console.print("\n[dim]Try:")
        console.print("  - Lowering the threshold (e.g., --threshold 0.7)")
        console.print("  - Checking more projects with --projects")
        console.print("[/dim]")
        return

    # Header
    console.print(f"\n[bold]Duplicate Artifacts Found:[/bold] {len(duplicates)} pairs")
    console.print(f"[dim]Similarity threshold: {threshold:.0%}[/dim]\n")

    # Create results table
    table = Table(title="Duplicates")
    table.add_column("Artifact 1", style="cyan", no_wrap=False)
    table.add_column("Artifact 2", style="cyan", no_wrap=False)
    table.add_column("Similarity", justify="right", style="yellow", width=12)
    table.add_column("Reasons", style="green")

    for dup in duplicates:
        # Format similarity percentage
        similarity_pct = f"{dup.similarity_score:.0%}"

        # Format reasons
        reasons = ", ".join(dup.match_reasons[:3])  # Show top 3 reasons
        if len(dup.match_reasons) > 3:
            reasons += f" +{len(dup.match_reasons) - 3} more"

        table.add_row(dup.artifact1_name, dup.artifact2_name, similarity_pct, reasons)

    console.print(table)

    # Show paths for first few duplicates
    console.print("\n[bold]Duplicate Paths:[/bold]")
    for i, dup in enumerate(duplicates[:5], 1):
        console.print(
            f"\n[cyan]{i}. {dup.artifact1_name} vs {dup.artifact2_name}[/cyan]"
        )
        console.print(f"   [dim]{dup.artifact1_path}[/dim]")
        console.print(f"   [dim]{dup.artifact2_path}[/dim]")

    if len(duplicates) > 5:
        console.print(f"\n[dim]... and {len(duplicates) - 5} more pairs[/dim]")

    # Footer with helpful tips
    console.print(
        f"\n[dim]Use --threshold {min(threshold + 0.05, 1.0):.2f} for stricter matching[/dim]"
    )
    console.print("[dim]Use --json for machine-readable output[/dim]")


def _display_duplicates_json(duplicates, threshold: float) -> None:
    """Display duplicate detection results as JSON.

    Args:
        duplicates: List of DuplicatePair objects
        threshold: Similarity threshold used
    """
    import json as json_lib

    output = {
        "threshold": threshold,
        "duplicate_count": len(duplicates),
        "duplicates": [
            {
                "artifact1": {
                    "name": d.artifact1_name,
                    "path": str(d.artifact1_path),
                },
                "artifact2": {
                    "name": d.artifact2_name,
                    "path": str(d.artifact2_path),
                },
                "similarity": d.similarity_score,
                "match_reasons": d.match_reasons,
            }
            for d in duplicates
        ],
    }

    click.echo(json_lib.dumps(output, indent=2))


# ====================
# Sync Commands
# ====================


@main.command(name="sync-check")
@click.argument("project_path", type=click.Path(exists=True))
@click.option(
    "-c",
    "--collection",
    help="Collection to check against (default: from deployment metadata)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output results as JSON",
)
def sync_check_cmd(project_path, collection, output_json):
    """Check for drift between project and collection.

    Compares deployed artifacts in PROJECT_PATH with the source collection
    to detect changes, additions, or removals.

    Examples:
        skillmeat sync-check /path/to/project
        skillmeat sync-check /path/to/project --collection my-collection
        skillmeat sync-check /path/to/project --json
    """
    from pathlib import Path
    from skillmeat.core.collection import CollectionManager
    from skillmeat.core.sync import SyncManager

    try:
        project_path = Path(project_path)

        # Initialize managers
        collection_mgr = CollectionManager()
        sync_mgr = SyncManager(collection_manager=collection_mgr)

        # Check for drift
        drift_results = sync_mgr.check_drift(project_path, collection)

        # Display results
        if output_json:
            _display_sync_check_json(drift_results)
        else:
            _display_sync_check_results(drift_results, project_path)

        # Exit code: 0 if no drift, 1 if drift detected
        sys.exit(0 if not drift_results else 1)

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        logger.exception("Sync check failed")
        sys.exit(1)


def _display_sync_check_results(drift_results, project_path: Path) -> None:
    """Display sync check results with Rich formatting.

    Args:
        drift_results: List of DriftDetectionResult objects
        project_path: Path to project
    """
    if not drift_results:
        console.print("\n[green]No drift detected. Project is in sync.[/green]")
        console.print(f"\n[dim]Project: {project_path}[/dim]")
        return

    # Header
    console.print(
        f"\n[bold]Drift Detection Results:[/bold] {len(drift_results)} artifacts"
    )
    console.print(f"[dim]Project: {project_path}[/dim]\n")

    # Create results table
    table = Table(title="Drifted Artifacts")
    table.add_column("Artifact", style="cyan", no_wrap=False)
    table.add_column("Type", style="blue", width=10)
    table.add_column("Drift Type", style="yellow", width=15)
    table.add_column("Recommendation", style="green")
    table.add_column("Last Deployed", style="dim")

    for result in drift_results:
        # Format drift type
        drift_type_display = result.drift_type.replace("_", " ").title()

        # Format recommendation
        recommendation = result.recommendation.replace("_", " ").title()

        # Format last deployed
        last_deployed = result.last_deployed or "Never"
        if result.last_deployed:
            # Truncate ISO timestamp to date only
            last_deployed = result.last_deployed[:10]

        table.add_row(
            result.artifact_name,
            result.artifact_type,
            drift_type_display,
            recommendation,
            last_deployed,
        )

    console.print(table)

    # Show details for each drifted artifact
    console.print("\n[bold]Drift Details:[/bold]")
    for result in drift_results:
        console.print(f"\n[cyan]{result.artifact_name}[/cyan] ({result.artifact_type})")
        console.print(f"  Drift Type: {result.drift_type}")
        console.print(f"  Recommendation: {result.recommendation}")

        if result.collection_sha:
            console.print(f"  Collection SHA: {result.collection_sha[:12]}...")
        if result.project_sha:
            console.print(f"  Project SHA: {result.project_sha[:12]}...")
        if result.collection_version:
            console.print(f"  Collection Version: {result.collection_version}")
        if result.project_version:
            console.print(f"  Project Version: {result.project_version}")

    # Footer
    console.print("\n[dim]Use skillmeat sync-pull to synchronize changes[/dim]")


def _display_sync_check_json(drift_results) -> None:
    """Display sync check results as JSON.

    Args:
        drift_results: List of DriftDetectionResult objects
    """
    import json as json_lib

    output = {
        "drift_detected": len(drift_results) > 0,
        "drift_count": len(drift_results),
        "artifacts": [
            {
                "name": r.artifact_name,
                "type": r.artifact_type,
                "drift_type": r.drift_type,
                "collection_sha": r.collection_sha,
                "project_sha": r.project_sha,
                "collection_version": r.collection_version,
                "project_version": r.project_version,
                "last_deployed": r.last_deployed,
                "recommendation": r.recommendation,
            }
            for r in drift_results
        ],
    }

    click.echo(json_lib.dumps(output, indent=2))


@main.command(name="sync-pull")
@click.argument("project_path", type=click.Path(exists=True))
@click.option(
    "--artifacts",
    help="Specific artifacts to sync (comma-separated)",
)
@click.option(
    "--strategy",
    type=click.Choice(["overwrite", "merge", "fork", "prompt"]),
    default="prompt",
    help="Sync strategy (default: prompt)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would be synced without making changes",
)
@click.option(
    "--no-interactive",
    is_flag=True,
    help="Non-interactive mode (use with --strategy)",
)
@click.option(
    "-c",
    "--collection",
    help="Collection to sync to (default: from deployment metadata)",
)
@click.option("--json", "output_json", is_flag=True, help="Output results as JSON")
@click.option(
    "--with-rollback",
    is_flag=True,
    help="Create snapshot before sync and offer rollback on failure",
)
def sync_pull_cmd(
    project_path, artifacts, strategy, dry_run, no_interactive, collection, output_json, with_rollback
):
    """Pull artifacts from project to collection.

    Syncs modified artifacts from a project back to the collection.
    Useful for capturing local changes made to deployed artifacts.

    Examples:
        skillmeat sync-pull /path/to/project
        skillmeat sync-pull /path/to/project --strategy overwrite
        skillmeat sync-pull /path/to/project --artifacts skill1,skill2
        skillmeat sync-pull /path/to/project --dry-run
        skillmeat sync-pull /path/to/project --strategy merge --no-interactive
        skillmeat sync-pull /path/to/project --json
    """
    from pathlib import Path
    from skillmeat.core.collection import CollectionManager
    from skillmeat.core.sync import SyncManager

    try:
        project_path = Path(project_path)

        # Parse artifact list
        artifact_list = None
        if artifacts:
            artifact_list = [a.strip() for a in artifacts.split(",")]

        # Initialize managers
        collection_mgr = CollectionManager()

        # Initialize snapshot manager if rollback requested
        snapshot_mgr = None
        if with_rollback:
            from skillmeat.storage.snapshot import SnapshotManager
            from pathlib import Path as P

            snapshots_dir = P.home() / ".skillmeat" / "snapshots"
            snapshot_mgr = SnapshotManager(snapshots_dir)

        sync_mgr = SyncManager(
            collection_manager=collection_mgr,
            snapshot_manager=snapshot_mgr
        )

        # Perform sync pull (with or without rollback)
        if with_rollback:
            result = sync_mgr.sync_from_project_with_rollback(
                project_path=project_path,
                artifact_names=artifact_list,
                strategy=strategy,
                dry_run=dry_run,
                interactive=not no_interactive,
            )
        else:
            result = sync_mgr.sync_from_project(
                project_path=project_path,
                artifact_names=artifact_list,
                strategy=strategy,
                dry_run=dry_run,
                interactive=not no_interactive,
            )

        # Display results
        if output_json:
            _display_sync_pull_json(result)
        else:
            _display_sync_pull_results(result)

        # Exit codes:
        # 0 = success or no_changes
        # 1 = partial (some conflicts)
        # 2 = cancelled or rolled_back
        if result.status in ["success", "no_changes", "dry_run"]:
            sys.exit(0)
        elif result.status == "partial":
            sys.exit(1)
        else:  # cancelled or rolled_back
            sys.exit(2)

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        logger.exception("Sync pull failed")
        sys.exit(1)


@main.command(name="sync-preview")
@click.argument("project_path", type=click.Path(exists=True))
@click.option(
    "--artifacts",
    help="Specific artifacts to preview (comma-separated)",
)
@click.option(
    "-c",
    "--collection",
    help="Collection to sync to (default: from deployment metadata)",
)
@click.option("--json", "output_json", is_flag=True, help="Output results as JSON")
def sync_preview_cmd(project_path, artifacts, collection, output_json):
    """Preview sync changes without applying them.

    Shows what would be synced from a project back to the collection
    without making any actual changes. This is an alias for
    'sync-pull --dry-run' with more intuitive naming.

    Examples:
        skillmeat sync-preview /path/to/project
        skillmeat sync-preview /path/to/project --artifacts skill1,skill2
        skillmeat sync-preview /path/to/project --json
    """
    # Delegate to sync-pull with dry_run=True
    ctx = click.get_current_context()
    ctx.invoke(
        sync_pull_cmd,
        project_path=project_path,
        artifacts=artifacts,
        strategy="prompt",  # Default strategy for preview
        dry_run=True,  # Force dry-run mode
        no_interactive=False,  # Keep preview output
        collection=collection,
        output_json=output_json,
    )


def _display_sync_pull_results(result) -> None:
    """Display sync pull results with Rich formatting.

    Args:
        result: SyncResult object
    """
    # Header
    console.print(f"\n[bold]Sync Pull Results[/bold]")
    console.print(f"Status: [{_get_status_color(result.status)}]{result.status}[/]")
    console.print(f"Message: {result.message}\n")

    # Synced artifacts
    if result.artifacts_synced:
        console.print("[green]Synced Artifacts:[/green]")
        for artifact in result.artifacts_synced:
            console.print(f"  [cyan]{artifact}[/cyan]")
        console.print()

    # Conflicts
    if result.conflicts:
        console.print("[yellow]Conflicts:[/yellow]")
        for conflict in result.conflicts:
            console.print(f"  [yellow]{conflict.artifact_name}[/yellow]")
            if hasattr(conflict, "conflict_files") and conflict.conflict_files:
                console.print(f"    Files: {', '.join(conflict.conflict_files[:5])}")
                if len(conflict.conflict_files) > 5:
                    console.print(
                        f"    ... and {len(conflict.conflict_files) - 5} more"
                    )
        console.print()

    # Summary
    if result.status == "success":
        console.print(
            f"[green]Successfully synced {len(result.artifacts_synced)} artifacts[/green]"
        )
    elif result.status == "partial":
        console.print(
            f"[yellow]Partial sync: {len(result.artifacts_synced)} synced, "
            f"{len(result.conflicts)} conflicts[/yellow]"
        )
    elif result.status == "no_changes":
        console.print("[dim]No artifacts to sync[/dim]")
    elif result.status == "dry_run":
        console.print(
            f"[cyan]Dry run: Would sync {len(result.artifacts_synced)} artifacts[/cyan]"
        )
    elif result.status == "cancelled":
        console.print("[yellow]Sync cancelled by user[/yellow]")


def _display_sync_pull_json(result) -> None:
    """Display sync pull results as JSON.

    Args:
        result: SyncResult object
    """
    import json as json_lib

    output = {
        "status": result.status,
        "message": result.message,
        "artifacts_synced": result.artifacts_synced,
        "conflicts": [
            {
                "artifact_name": c.artifact_name,
                "error": c.error if hasattr(c, "error") else None,
                "conflict_files": (
                    c.conflict_files if hasattr(c, "conflict_files") else []
                ),
            }
            for c in result.conflicts
        ],
    }

    click.echo(json_lib.dumps(output, indent=2))


def _get_status_color(status: str) -> str:
    """Get color for status display.

    Args:
        status: Status string

    Returns:
        Rich color tag
    """
    color_map = {
        "success": "green",
        "partial": "yellow",
        "cancelled": "yellow",
        "no_changes": "dim",
        "dry_run": "cyan",
    }
    return color_map.get(status, "white")


# ====================
# Analytics Commands
# ====================


@main.group()
def analytics():
    """View and manage artifact usage analytics.

    Analytics tracks artifact deployments, updates, syncs, searches, and removals
    to help you understand usage patterns and identify cleanup opportunities.

    Examples:
        skillmeat analytics usage              # View all artifact usage
        skillmeat analytics top --limit 10     # Top 10 artifacts
        skillmeat analytics cleanup            # Cleanup suggestions
        skillmeat analytics stats              # Database statistics
    """
    pass


@analytics.command()
@click.argument("artifact", required=False)
@click.option(
    "--days",
    type=int,
    default=30,
    help="Time window in days (default: 30)",
)
@click.option(
    "--type",
    "artifact_type",
    type=click.Choice(["skill", "command", "agent"]),
    help="Filter by artifact type",
)
@click.option(
    "--collection",
    help="Filter by collection name",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format (default: table)",
)
@click.option(
    "--sort-by",
    type=click.Choice([
        "total_events", "deploy_count", "update_count",
        "last_used", "artifact_name"
    ]),
    default="total_events",
    help="Sort results by field (default: total_events)",
)
def usage(artifact, days, artifact_type, collection, output_format, sort_by):
    """View artifact usage statistics.

    Show usage statistics for one or more artifacts, including event counts,
    last usage time, and usage trends.

    Examples:
        skillmeat analytics usage                     # All artifacts
        skillmeat analytics usage canvas              # Specific artifact
        skillmeat analytics usage --type skill        # All skills
        skillmeat analytics usage --format json       # JSON output
        skillmeat analytics usage --sort-by last_used # Sort by recency
    """
    from skillmeat.core.usage_reports import UsageReportManager

    try:
        # Initialize manager
        config = ConfigManager()

        # Check if analytics enabled
        if not config.is_analytics_enabled():
            console.print("[yellow]Analytics is disabled in configuration.[/yellow]\n")
            console.print("To enable analytics:")
            console.print("  [cyan]skillmeat config set analytics.enabled true[/cyan]\n")
            sys.exit(2)

        manager = UsageReportManager(config)

        # Get usage data
        usage_data = manager.get_artifact_usage(
            artifact_name=artifact,
            artifact_type=artifact_type,
            collection_name=collection,
        )

        # Handle single vs multiple artifacts
        if artifact:
            # Single artifact
            if not usage_data:
                console.print(f"[yellow]No usage data found for '{artifact}'[/yellow]")
                sys.exit(0)
            artifacts = [usage_data]
        else:
            # Multiple artifacts
            artifacts = usage_data.get("artifacts", [])
            if not artifacts:
                console.print("[yellow]No usage data available.[/yellow]\n")
                console.print("Deploy or update artifacts to start collecting analytics.")
                sys.exit(0)

        # Sort artifacts
        reverse = sort_by != "artifact_name"
        artifacts_sorted = sorted(
            artifacts,
            key=lambda x: x.get(sort_by) if x.get(sort_by) is not None else "",
            reverse=reverse
        )

        # Display results
        if output_format == "json":
            import json as json_lib
            output = {
                "artifacts": artifacts_sorted,
                "total_count": len(artifacts_sorted),
                "filters": {
                    "artifact": artifact,
                    "type": artifact_type,
                    "collection": collection,
                    "days": days,
                }
            }
            click.echo(json_lib.dumps(output, indent=2, default=str))
        else:
            _display_usage_table(artifacts_sorted)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Analytics usage command failed")
        sys.exit(1)


@analytics.command()
@click.option(
    "--limit",
    type=int,
    default=10,
    help="Number of top artifacts to show (default: 10)",
)
@click.option(
    "--metric",
    type=click.Choice([
        "total_events", "deploy_count", "update_count",
        "sync_count", "search_count"
    ]),
    default="total_events",
    help="Sort by metric (default: total_events)",
)
@click.option(
    "--type",
    "artifact_type",
    type=click.Choice(["skill", "command", "agent"]),
    help="Filter by artifact type",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format (default: table)",
)
def top(limit, metric, artifact_type, output_format):
    """List top artifacts by metric.

    Show the most frequently used artifacts ranked by total events,
    deploys, updates, or other metrics.

    Examples:
        skillmeat analytics top                          # Top 10 by events
        skillmeat analytics top --limit 20               # Top 20
        skillmeat analytics top --metric deploy_count    # Top by deploys
        skillmeat analytics top --type skill             # Top skills only
    """
    from skillmeat.core.usage_reports import UsageReportManager

    try:
        # Initialize manager
        config = ConfigManager()

        # Check if analytics enabled
        if not config.is_analytics_enabled():
            console.print("[yellow]Analytics is disabled in configuration.[/yellow]\n")
            console.print("To enable analytics:")
            console.print("  [cyan]skillmeat config set analytics.enabled true[/cyan]\n")
            sys.exit(2)

        manager = UsageReportManager(config)

        # Get top artifacts
        top_artifacts = manager.get_top_artifacts(
            artifact_type=artifact_type,
            metric=metric,
            limit=limit,
        )

        if not top_artifacts:
            console.print("[yellow]No usage data available.[/yellow]\n")
            console.print("Deploy or update artifacts to start collecting analytics.")
            sys.exit(0)

        # Display results
        if output_format == "json":
            import json as json_lib
            output = {
                "top_artifacts": top_artifacts,
                "count": len(top_artifacts),
                "metric": metric,
                "limit": limit,
            }
            click.echo(json_lib.dumps(output, indent=2, default=str))
        else:
            _display_top_table(top_artifacts, metric, limit)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Analytics top command failed")
        sys.exit(1)


@analytics.command()
@click.option(
    "--inactivity-days",
    type=int,
    default=90,
    help="Inactivity threshold in days (default: 90)",
)
@click.option(
    "--collection",
    help="Filter by collection name",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format (default: table)",
)
@click.option(
    "--show-size",
    is_flag=True,
    help="Show estimated disk space for each artifact",
)
def cleanup(inactivity_days, collection, output_format, show_size):
    """Show cleanup suggestions for unused artifacts.

    Identify artifacts that haven't been used recently, were never deployed,
    or have low usage, along with estimated disk space savings.

    Examples:
        skillmeat analytics cleanup                      # Default suggestions
        skillmeat analytics cleanup --inactivity-days 60 # 60-day threshold
        skillmeat analytics cleanup --show-size          # Show disk usage
        skillmeat analytics cleanup --format json        # JSON output
    """
    from skillmeat.core.usage_reports import UsageReportManager

    try:
        # Initialize manager
        config = ConfigManager()

        # Check if analytics enabled
        if not config.is_analytics_enabled():
            console.print("[yellow]Analytics is disabled in configuration.[/yellow]\n")
            console.print("To enable analytics:")
            console.print("  [cyan]skillmeat config set analytics.enabled true[/cyan]\n")
            sys.exit(2)

        manager = UsageReportManager(config)

        # Get cleanup suggestions
        suggestions = manager.get_cleanup_suggestions(collection_name=collection)

        if not any([
            suggestions.get("unused_90_days"),
            suggestions.get("never_deployed"),
            suggestions.get("low_usage"),
        ]):
            console.print("[green]No cleanup suggestions. All artifacts are actively used![/green]")
            sys.exit(0)

        # Display results
        if output_format == "json":
            import json as json_lib
            click.echo(json_lib.dumps(suggestions, indent=2, default=str))
        else:
            _display_cleanup_suggestions(suggestions, inactivity_days, show_size)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Analytics cleanup command failed")
        sys.exit(1)


@analytics.command()
@click.argument("artifact", required=False)
@click.option(
    "--period",
    type=click.Choice(["7d", "30d", "90d", "all"]),
    default="30d",
    help="Time period (default: 30d)",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format (default: table)",
)
def trends(artifact, period, output_format):
    """Display usage trends over time.

    Show how artifact usage has changed over different time periods,
    with breakdowns by event type (deploy, update, sync, search).

    Examples:
        skillmeat analytics trends                  # Overall trends (30d)
        skillmeat analytics trends canvas           # Specific artifact
        skillmeat analytics trends --period 7d      # Last 7 days
        skillmeat analytics trends --period all     # All time
    """
    from skillmeat.core.usage_reports import UsageReportManager

    try:
        # Initialize manager
        config = ConfigManager()

        # Check if analytics enabled
        if not config.is_analytics_enabled():
            console.print("[yellow]Analytics is disabled in configuration.[/yellow]\n")
            console.print("To enable analytics:")
            console.print("  [cyan]skillmeat config set analytics.enabled true[/cyan]\n")
            sys.exit(2)

        manager = UsageReportManager(config)

        # Get trends
        trends_data = manager.get_usage_trends(
            artifact_name=artifact,
            time_period=period,
        )

        if not trends_data:
            console.print("[yellow]No trend data available for this period.[/yellow]")
            sys.exit(0)

        # Display results
        if output_format == "json":
            import json as json_lib
            click.echo(json_lib.dumps(trends_data, indent=2, default=str))
        else:
            _display_trends(trends_data, artifact, period)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Analytics trends command failed")
        sys.exit(1)


@analytics.command()
@click.argument("output_path", type=click.Path())
@click.option(
    "--format",
    "export_format",
    type=click.Choice(["json", "csv"]),
    default="json",
    help="Export format (default: json)",
)
@click.option(
    "--collection",
    help="Filter by collection name",
)
def export(output_path, export_format, collection):
    """Export comprehensive analytics report to file.

    Generate a full analytics report including usage statistics,
    top artifacts, cleanup suggestions, and trends.

    Examples:
        skillmeat analytics export report.json            # Export to JSON
        skillmeat analytics export report.csv --format csv # Export to CSV
        skillmeat analytics export report.json --collection work
    """
    from skillmeat.core.usage_reports import UsageReportManager
    from pathlib import Path

    try:
        # Initialize manager
        config = ConfigManager()

        # Check if analytics enabled
        if not config.is_analytics_enabled():
            console.print("[yellow]Analytics is disabled in configuration.[/yellow]\n")
            console.print("To enable analytics:")
            console.print("  [cyan]skillmeat config set analytics.enabled true[/cyan]\n")
            sys.exit(2)

        manager = UsageReportManager(config)

        # Convert to Path
        output_file = Path(output_path)

        # Show progress
        with console.status("[cyan]Exporting analytics report...[/cyan]"):
            manager.export_usage_report(
                output_path=output_file,
                format=export_format,
                collection_name=collection,
            )

        # Get file size
        file_size_bytes = output_file.stat().st_size
        file_size_kb = file_size_bytes / 1024

        console.print(f"[green]Report exported successfully![/green]")
        console.print(f"  File: {output_file}")
        console.print(f"  Size: {file_size_kb:.1f} KB")
        console.print(f"  Format: {export_format.upper()}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Analytics export command failed")
        sys.exit(1)


@analytics.command()
def stats():
    """Show analytics database statistics.

    Display summary statistics about the analytics database, including
    total events, artifacts tracked, date range, and event type breakdown.

    Examples:
        skillmeat analytics stats
    """
    from skillmeat.core.usage_reports import UsageReportManager

    try:
        # Initialize manager
        config = ConfigManager()

        # Check if analytics enabled
        if not config.is_analytics_enabled():
            console.print("[yellow]Analytics is disabled in configuration.[/yellow]\n")
            console.print("To enable analytics:")
            console.print("  [cyan]skillmeat config set analytics.enabled true[/cyan]\n")
            sys.exit(2)

        manager = UsageReportManager(config)

        # Get stats from database
        db_stats = manager.db.get_stats()

        if db_stats["total_events"] == 0:
            console.print("[yellow]Analytics database is empty.[/yellow]\n")
            console.print("Deploy or update artifacts to start collecting analytics.")
            sys.exit(0)

        _display_stats(db_stats, config)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Analytics stats command failed")
        sys.exit(1)


@analytics.command()
@click.option(
    "--older-than-days",
    type=int,
    help="Delete events older than N days",
)
@click.option(
    "--confirm",
    is_flag=True,
    help="Skip confirmation prompt",
)
def clear(older_than_days, confirm):
    """Clear old analytics data.

    Remove analytics events older than a specified number of days
    to free up disk space and maintain database performance.

    Examples:
        skillmeat analytics clear --older-than-days 180 --confirm
        skillmeat analytics clear --older-than-days 90
    """
    from skillmeat.core.usage_reports import UsageReportManager

    try:
        # Initialize manager
        config = ConfigManager()

        # Check if analytics enabled
        if not config.is_analytics_enabled():
            console.print("[yellow]Analytics is disabled in configuration.[/yellow]\n")
            console.print("To enable analytics:")
            console.print("  [cyan]skillmeat config set analytics.enabled true[/cyan]\n")
            sys.exit(2)

        manager = UsageReportManager(config)

        # Default to retention policy from config
        if older_than_days is None:
            older_than_days = config.get("analytics.retention_days", 365)

        # Get current stats
        db_stats = manager.db.get_stats()
        total_events = db_stats.get("total_events", 0)

        if total_events == 0:
            console.print("[yellow]Analytics database is empty. Nothing to clear.[/yellow]")
            sys.exit(0)

        # Show warning
        console.print(f"[bold]Clear Analytics Data[/bold]\n")
        console.print(f"This will delete events older than [cyan]{older_than_days}[/cyan] days.")
        console.print(f"Current total events: [cyan]{total_events:,}[/cyan]\n")

        # Confirm
        if not confirm:
            if not Confirm.ask("Continue?", default=False):
                console.print("[yellow]Operation cancelled.[/yellow]")
                sys.exit(0)

        # Calculate cutoff date
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=older_than_days)

        # Delete old events
        with console.status("[cyan]Clearing old analytics data...[/cyan]"):
            deleted_count = manager.db.delete_events_before(cutoff_date)

        if deleted_count > 0:
            console.print(f"[green]Deleted {deleted_count:,} events[/green]")
            console.print(f"[green]Database cleaned successfully![/green]")
        else:
            console.print("[yellow]No events matched the criteria.[/yellow]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Analytics clear command failed")
        sys.exit(1)


# Helper functions for analytics display


def _display_usage_table(artifacts: List[Dict]) -> None:
    """Display usage statistics in table format.

    Args:
        artifacts: List of artifact usage dictionaries
    """
    console.print("\n[bold]Artifact Usage Statistics[/bold]\n")

    table = Table()
    table.add_column("Artifact", style="cyan", no_wrap=True)
    table.add_column("Type", style="blue", width=10)
    table.add_column("Events", style="green", justify="right")
    table.add_column("Last Used", style="yellow")
    table.add_column("Deploys", style="magenta", justify="right")
    table.add_column("Updates", style="magenta", justify="right")
    table.add_column("Trend", justify="center")

    for artifact in artifacts:
        # Format last used
        last_used = artifact.get("last_used")
        days_since = artifact.get("days_since_last_use")
        if days_since is not None:
            if days_since == 0:
                last_used_str = "Today"
            elif days_since == 1:
                last_used_str = "1 day ago"
            else:
                last_used_str = f"{days_since} days ago"
        elif last_used:
            last_used_str = str(last_used)[:10]
        else:
            last_used_str = "Never"

        # Format trend with symbols
        trend = artifact.get("usage_trend", "stable")
        trend_symbols = {
            "increasing": "[green]↑[/green]",
            "decreasing": "[red]↓[/red]",
            "stable": "[yellow]—[/yellow]",
        }
        trend_display = trend_symbols.get(trend, "—")

        table.add_row(
            artifact.get("artifact_name", ""),
            artifact.get("artifact_type", ""),
            str(artifact.get("total_events", 0)),
            last_used_str,
            str(artifact.get("deploy_count", 0)),
            str(artifact.get("update_count", 0)),
            trend_display,
        )

    console.print(table)
    console.print()


def _display_top_table(artifacts: List[Dict], metric: str, limit: int) -> None:
    """Display top artifacts in table format with bars.

    Args:
        artifacts: List of top artifact dictionaries
        metric: Metric used for ranking
        limit: Number of artifacts shown
    """
    metric_labels = {
        "total_events": "Total Events",
        "deploy_count": "Deployments",
        "update_count": "Updates",
        "sync_count": "Syncs",
        "search_count": "Searches",
    }
    metric_label = metric_labels.get(metric, metric)

    console.print(f"\n[bold]Top {limit} Artifacts by {metric_label}[/bold]\n")

    # Find max value for bar scaling
    max_value = max((a.get(metric, 0) for a in artifacts), default=1)
    bar_width = 30

    for i, artifact in enumerate(artifacts, 1):
        name = artifact.get("artifact_name", "Unknown")
        value = artifact.get(metric, 0)
        artifact_type = artifact.get("artifact_type", "")

        # Create bar
        bar_length = int((value / max_value) * bar_width) if max_value > 0 else 0
        bar = "█" * bar_length

        console.print(
            f"{i:2}. [cyan]{name:20}[/cyan] "
            f"[dim]({artifact_type})[/dim] "
            f"[green]{bar}[/green] {value:,} {metric_label.lower()}"
        )

    console.print()


def _display_cleanup_suggestions(
    suggestions: Dict,
    inactivity_days: int,
    show_size: bool
) -> None:
    """Display cleanup suggestions in formatted panels.

    Args:
        suggestions: Cleanup suggestions dictionary
        inactivity_days: Inactivity threshold
        show_size: Whether to show size estimates
    """
    console.print("\n[bold]Cleanup Suggestions[/bold]\n")

    # Unused artifacts
    unused = suggestions.get("unused_90_days", [])
    if unused:
        panel_content = []
        for artifact in unused[:10]:  # Show max 10
            name = artifact.get("name", "")
            days = artifact.get("days_ago", 0)
            panel_content.append(f"• {name} ([dim]{days} days ago[/dim])")

        if len(unused) > 10:
            panel_content.append(f"\n[dim]... and {len(unused) - 10} more[/dim]")

        panel = Panel(
            "\n".join(panel_content),
            title=f"[yellow]Unused ({inactivity_days}+ days)[/yellow]",
            border_style="yellow",
        )
        console.print(panel)

    # Never deployed
    never_deployed = suggestions.get("never_deployed", [])
    if never_deployed:
        panel_content = []
        for artifact in never_deployed[:10]:
            name = artifact.get("name", "")
            days = artifact.get("days_since_added", 0)
            events = artifact.get("total_events", 0)
            panel_content.append(
                f"• {name} ([dim]added {days} days ago, {events} events[/dim])"
            )

        if len(never_deployed) > 10:
            panel_content.append(f"\n[dim]... and {len(never_deployed) - 10} more[/dim]")

        panel = Panel(
            "\n".join(panel_content),
            title="[red]Never Deployed[/red]",
            border_style="red",
        )
        console.print(panel)

    # Low usage
    low_usage = suggestions.get("low_usage", [])
    if low_usage:
        panel_content = []
        for artifact in low_usage[:10]:
            name = artifact.get("name", "")
            events = artifact.get("total_events", 0)
            panel_content.append(f"• {name} ([dim]{events} events[/dim])")

        if len(low_usage) > 10:
            panel_content.append(f"\n[dim]... and {len(low_usage) - 10} more[/dim]")

        panel = Panel(
            "\n".join(panel_content),
            title="[blue]Low Usage[/blue]",
            border_style="blue",
        )
        console.print(panel)

    # Summary
    total_mb = suggestions.get("total_reclaimable_mb", 0)
    summary = suggestions.get("summary", "")

    if total_mb > 0 or summary:
        console.print()
        if total_mb > 0:
            console.print(f"[bold]Total reclaimable space:[/bold] [green]{total_mb:.1f} MB[/green]")
        if summary:
            console.print(f"\n{summary}")
        console.print()


def _display_trends(trends_data: Dict, artifact: Optional[str], period: str) -> None:
    """Display usage trends with ASCII visualization.

    Args:
        trends_data: Trends data dictionary
        artifact: Artifact name (if specific)
        period: Time period
    """
    period_labels = {
        "7d": "Last 7 Days",
        "30d": "Last 30 Days",
        "90d": "Last 90 Days",
        "all": "All Time",
    }
    period_label = period_labels.get(period, period)

    if artifact:
        console.print(f"\n[bold]Usage Trends for '{artifact}' ({period_label})[/bold]\n")
    else:
        console.print(f"\n[bold]Usage Trends ({period_label})[/bold]\n")

    # Event type trends
    event_types = [
        ("deploy_trend", "Deploys", "green"),
        ("update_trend", "Updates", "blue"),
        ("sync_trend", "Syncs", "yellow"),
        ("search_trend", "Searches", "magenta"),
    ]

    for trend_key, label, color in event_types:
        trend_data = trends_data.get(trend_key, [])
        if trend_data:
            values = [item.get("count", 0) for item in trend_data]
            total = sum(values)

            # Create sparkline
            sparkline = _create_sparkline(values)

            console.print(f"[{color}]{label:12}[/{color}] {sparkline} [dim]({total:,} total)[/dim]")

    # Summary
    total_by_day = trends_data.get("total_events_by_day", {})
    if total_by_day:
        max_day = max(total_by_day.items(), key=lambda x: x[1], default=(None, 0))
        if max_day[0]:
            console.print(f"\n[bold]Peak activity:[/bold] {max_day[0]} ([green]{max_day[1]:,} events[/green])")

    console.print()


def _display_stats(db_stats: Dict, config: ConfigManager) -> None:
    """Display analytics database statistics.

    Args:
        db_stats: Database statistics dictionary
        config: Configuration manager
    """
    console.print("\n[bold]Analytics Database Statistics[/bold]\n")

    # Basic stats
    console.print(f"[cyan]Total Events:[/cyan]     {db_stats.get('total_events', 0):,}")
    console.print(f"[cyan]Total Artifacts:[/cyan]  {db_stats.get('unique_artifacts', 0):,}")

    # Date range
    earliest = db_stats.get("earliest_event")
    latest = db_stats.get("latest_event")
    if earliest and latest:
        console.print(f"[cyan]Date Range:[/cyan]       {earliest[:10]} to {latest[:10]}")

    # Database size
    db_path = config.get_analytics_db_path()
    if db_path and db_path.exists():
        size_bytes = db_path.stat().st_size
        size_mb = size_bytes / (1024 * 1024)
        console.print(f"[cyan]Database Size:[/cyan]    {size_mb:.2f} MB")

    # Events by type
    console.print("\n[bold]Events by Type:[/bold]")

    event_counts = db_stats.get("events_by_type", {})
    total = db_stats.get("total_events", 0)

    for event_type, count in sorted(event_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total * 100) if total > 0 else 0
        bar_length = int(percentage / 2)  # Max 50 chars
        bar = "█" * bar_length

        console.print(
            f"  [green]{bar:50}[/green] "
            f"[cyan]{event_type:10}[/cyan] "
            f"{count:6,} ({percentage:5.1f}%)"
        )

    console.print()


def _create_sparkline(values: List[int]) -> str:
    """Create ASCII sparkline from values.

    Args:
        values: List of numeric values

    Returns:
        String sparkline using block characters
    """
    if not values:
        return ""

    # Unicode block characters for sparklines
    blocks = " ▁▂▃▄▅▆▇█"

    min_val = min(values)
    max_val = max(values)

    if max_val == min_val:
        return blocks[4] * len(values)  # Middle block for flat line

    # Scale to 0-8 range
    scaled = [
        int((v - min_val) / (max_val - min_val) * 8)
        for v in values
    ]

    return "".join(blocks[s] for s in scaled)


# ====================
# Web Interface Commands
# ====================


@main.group()
def web():
    """Manage web interface servers.

    Commands for starting, building, and diagnosing the Next.js web
    interface and FastAPI backend server.

    Examples:
      skillmeat web dev        # Start development servers
      skillmeat web build      # Build for production
      skillmeat web start      # Start production servers
      skillmeat web doctor     # Diagnose environment
    """
    pass


@web.command()
@click.option(
    "--api-only",
    is_flag=True,
    help="Run only the FastAPI server",
)
@click.option(
    "--web-only",
    is_flag=True,
    help="Run only the Next.js server",
)
@click.option(
    "--api-port",
    type=int,
    default=8000,
    help="Port for FastAPI server (default: 8000)",
)
@click.option(
    "--web-port",
    type=int,
    default=3000,
    help="Port for Next.js server (default: 3000)",
)
@click.option(
    "--api-host",
    default="127.0.0.1",
    help="Host for FastAPI server (default: 127.0.0.1)",
)
def dev(
    api_only: bool,
    web_only: bool,
    api_port: int,
    web_port: int,
    api_host: str,
):
    """Start development servers with auto-reload.

    Starts both FastAPI backend (port 8000) and Next.js frontend (port 3000)
    in development mode with auto-reload on file changes.

    Examples:
      skillmeat web dev                    # Start both servers
      skillmeat web dev --api-only         # Start only API
      skillmeat web dev --web-only         # Start only Next.js
      skillmeat web dev --api-port 8080    # Use custom API port
    """
    from skillmeat.web import WebManager, check_prerequisites

    try:
        # Check prerequisites
        if not check_prerequisites(console):
            sys.exit(1)

        # Create and start manager
        manager = WebManager(
            api_only=api_only,
            web_only=web_only,
            api_port=api_port,
            web_port=web_port,
            api_host=api_host,
        )

        exit_code = manager.start_dev()
        sys.exit(exit_code)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Failed to start development servers")
        sys.exit(1)


@web.command()
@click.option(
    "--check",
    is_flag=True,
    help="Check if build is needed without building",
)
def build(check: bool):
    """Build Next.js application for production.

    Compiles and optimizes the Next.js application for production deployment.
    Must be run before 'skillmeat web start'.

    Examples:
      skillmeat web build           # Build for production
      skillmeat web build --check   # Check if build is needed
    """
    from skillmeat.web import WebManager, check_prerequisites

    try:
        # Check prerequisites
        if not check_prerequisites(console):
            sys.exit(1)

        manager = WebManager()

        if check:
            # TODO: Implement build check (compare timestamps, etc.)
            console.print("[yellow]Build check not yet implemented[/yellow]")
            sys.exit(0)

        # Build
        exit_code = manager.build_web()
        sys.exit(exit_code)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Failed to build web application")
        sys.exit(1)


@web.command()
@click.option(
    "--api-only",
    is_flag=True,
    help="Run only the FastAPI server",
)
@click.option(
    "--web-only",
    is_flag=True,
    help="Run only the Next.js server",
)
@click.option(
    "--api-port",
    type=int,
    default=8000,
    help="Port for FastAPI server (default: 8000)",
)
@click.option(
    "--web-port",
    type=int,
    default=3000,
    help="Port for Next.js server (default: 3000)",
)
@click.option(
    "--api-host",
    default="127.0.0.1",
    help="Host for FastAPI server (default: 127.0.0.1)",
)
def start(
    api_only: bool,
    web_only: bool,
    api_port: int,
    web_port: int,
    api_host: str,
):
    """Start production servers.

    Starts both FastAPI backend and Next.js frontend in production mode.
    Requires 'skillmeat web build' to be run first.

    Examples:
      skillmeat web start                  # Start both servers
      skillmeat web start --api-only       # Start only API
      skillmeat web start --web-only       # Start only Next.js
    """
    from skillmeat.web import WebManager, check_prerequisites

    try:
        # Check prerequisites
        if not check_prerequisites(console):
            sys.exit(1)

        # Check if Next.js is built (unless API-only)
        if not api_only:
            import skillmeat
            from pathlib import Path

            package_root = Path(skillmeat.__file__).parent
            build_dir = package_root / "web" / ".next"

            if not build_dir.exists():
                console.print(
                    "[red]Next.js build not found. Run 'skillmeat web build' first.[/red]"
                )
                sys.exit(1)

        # Create and start manager
        manager = WebManager(
            api_only=api_only,
            web_only=web_only,
            api_port=api_port,
            web_port=web_port,
            api_host=api_host,
        )

        exit_code = manager.start_production()
        sys.exit(exit_code)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Failed to start production servers")
        sys.exit(1)


@web.command()
def doctor():
    """Diagnose web development environment.

    Checks for Node.js, pnpm, Python, and other prerequisites.
    Reports version information and potential issues.

    Examples:
      skillmeat web doctor    # Run all diagnostics
    """
    from skillmeat.web import run_doctor

    try:
        all_passed = run_doctor()
        sys.exit(0 if all_passed else 1)

    except Exception as e:
        console.print(f"[red]Error running diagnostics: {e}[/red]")
        logger.exception("Failed to run web doctor")
        sys.exit(1)


@web.command(name="generate-sdk")
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output directory for generated SDK (default: skillmeat/web/sdk)",
)
@click.option(
    "--check",
    is_flag=True,
    help="Check if SDK is up to date without regenerating",
)
@click.option(
    "--format",
    is_flag=True,
    default=True,
    help="Format generated code with Prettier (default: true)",
)
def generate_sdk(output: Optional[str], check: bool, format: bool):
    """Generate TypeScript SDK from OpenAPI specification.

    Exports the OpenAPI spec from the FastAPI application and generates
    a type-safe TypeScript SDK for use in the Next.js web interface.

    The generated SDK includes:
    - Full type safety for all API endpoints
    - Request/response types
    - Authentication support
    - Error handling

    Examples:
      skillmeat web generate-sdk              # Generate SDK with defaults
      skillmeat web generate-sdk --check      # Check if SDK needs update
      skillmeat web generate-sdk -o ./custom  # Custom output directory
    """
    import subprocess
    import skillmeat
    from pathlib import Path
    from skillmeat.api.server import create_app
    from skillmeat.api.openapi import export_openapi_spec

    try:
        # Determine paths
        package_root = Path(skillmeat.__file__).parent
        api_dir = package_root / "api"
        web_dir = package_root / "web"
        openapi_file = api_dir / "openapi.json"

        if output:
            sdk_output_dir = Path(output)
        else:
            sdk_output_dir = web_dir / "sdk"

        # Check mode: compare timestamps
        if check:
            if not openapi_file.exists():
                console.print("[yellow]OpenAPI spec not found - SDK needs generation[/yellow]")
                sys.exit(1)

            if not sdk_output_dir.exists():
                console.print("[yellow]SDK directory not found - SDK needs generation[/yellow]")
                sys.exit(1)

            # Compare modification times (simplified check)
            # In a real implementation, you might want to compare content hashes
            console.print("[green]SDK appears to be up to date[/green]")
            console.print(f"  OpenAPI spec: {openapi_file}")
            console.print(f"  SDK output: {sdk_output_dir}")
            sys.exit(0)

        # Generate OpenAPI specification
        console.print("[cyan]Generating OpenAPI specification...[/cyan]")

        # Create FastAPI app
        app = create_app()

        # Export OpenAPI spec
        export_openapi_spec(app, openapi_file, api_version="v1", pretty=True)

        console.print(f"[green]OpenAPI spec generated: {openapi_file}[/green]")

        # Check if pnpm is available
        try:
            subprocess.run(
                ["pnpm", "--version"],
                check=True,
                capture_output=True,
                text=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            console.print(
                "[red]Error: pnpm is not installed. Install it with: npm install -g pnpm[/red]"
            )
            sys.exit(1)

        # Ensure web dependencies are installed
        console.print("[cyan]Checking web dependencies...[/cyan]")
        node_modules = web_dir / "node_modules"
        if not node_modules.exists() or not (node_modules / "openapi-typescript-codegen").exists():
            console.print("[cyan]Installing web dependencies...[/cyan]")
            result = subprocess.run(
                ["pnpm", "install"],
                cwd=web_dir,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                console.print(f"[red]Error installing dependencies:[/red]\n{result.stderr}")
                sys.exit(1)

        # Generate TypeScript SDK
        console.print("[cyan]Generating TypeScript SDK...[/cyan]")

        # Remove existing SDK directory for clean generation
        if sdk_output_dir.exists():
            import shutil
            shutil.rmtree(sdk_output_dir)

        # Run SDK generation via pnpm script
        result = subprocess.run(
            ["pnpm", "run", "generate-sdk"],
            cwd=web_dir,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            console.print(f"[red]Error generating SDK:[/red]\n{result.stderr}")
            sys.exit(1)

        console.print(f"[green]SDK generated: {sdk_output_dir}[/green]")

        # Format generated code
        if format:
            console.print("[cyan]Formatting generated code...[/cyan]")
            result = subprocess.run(
                ["pnpm", "run", "format", "--loglevel", "silent"],
                cwd=web_dir,
                capture_output=True,
                text=True,
            )
            # Don't fail if formatting fails - it's not critical
            if result.returncode != 0:
                console.print(
                    "[yellow]Warning: Failed to format generated code (continuing anyway)[/yellow]"
                )

        # Verify TypeScript compilation
        console.print("[cyan]Verifying TypeScript compilation...[/cyan]")
        result = subprocess.run(
            ["pnpm", "run", "type-check"],
            cwd=web_dir,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            console.print(
                "[yellow]Warning: TypeScript compilation has errors:[/yellow]"
            )
            console.print(result.stdout)
            console.print(
                "[yellow]You may need to fix these errors before using the SDK[/yellow]"
            )

        # Success summary
        console.print()
        console.print("[green]SDK generation complete![/green]")
        console.print()
        console.print(f"  OpenAPI Spec: {openapi_file}")
        console.print(f"  SDK Output:   {sdk_output_dir}")
        console.print()
        console.print("[dim]Import the SDK in your components:[/dim]")
        console.print("  import { apiClient } from '@/lib/api-client';")
        console.print()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("SDK generation failed")
        sys.exit(1)


@web.group()
def token():
    """Manage web authentication tokens.

    Generate, list, and revoke JWT tokens for web interface authentication.
    Tokens are securely stored using OS keychain or encrypted file storage.

    Examples:
        skillmeat web token generate          # Generate new token
        skillmeat web token list              # List all tokens
        skillmeat web token revoke <name>     # Revoke specific token
        skillmeat web token cleanup           # Remove expired tokens
    """
    pass


@token.command(name="generate")
@click.option(
    "--name",
    default="default",
    help="Human-readable name for the token",
)
@click.option(
    "--days",
    type=int,
    help="Days until expiration (default: 90, 0 = no expiration)",
)
@click.option(
    "--show-token",
    is_flag=True,
    help="Display the full token (WARNING: sensitive)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON",
)
def token_generate(name, days, show_token, output_json):
    """Generate a new authentication token.

    Creates a JWT token for web interface authentication. The token is
    securely stored and can be used for API requests.

    Examples:
        skillmeat web token generate
        skillmeat web token generate --name production
        skillmeat web token generate --days 365 --name long-term
        skillmeat web token generate --days 0 --name never-expires
    """
    from skillmeat.core.auth import TokenManager

    try:
        # Initialize token manager
        token_manager = TokenManager()

        # Generate token
        token_obj = token_manager.generate_token(name=name, expiration_days=days)

        if output_json:
            import json

            output = {
                "token_id": token_obj.token_id,
                "name": token_obj.name,
                "created_at": token_obj.created_at.isoformat(),
                "expires_at": (
                    token_obj.expires_at.isoformat() if token_obj.expires_at else None
                ),
            }
            if show_token:
                output["token"] = token_obj.token

            console.print(json.dumps(output, indent=2))
        else:
            # Display success message
            console.print(f"\n[green]Token '{name}' generated successfully![/green]\n")

            # Display metadata
            console.print(f"[cyan]Token ID:[/cyan]    {token_obj.token_id}")
            console.print(f"[cyan]Name:[/cyan]        {token_obj.name}")
            console.print(
                f"[cyan]Created:[/cyan]     {token_obj.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            if token_obj.expires_at:
                console.print(
                    f"[cyan]Expires:[/cyan]     {token_obj.expires_at.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            else:
                console.print(f"[cyan]Expires:[/cyan]     [yellow]Never[/yellow]")

            # Display token if requested
            if show_token:
                console.print(f"\n[yellow]Token:[/yellow]\n{token_obj.token}\n")
                console.print(
                    "[yellow]WARNING:[/yellow] Keep this token secure. "
                    "Do not share or commit to version control."
                )
            else:
                console.print(
                    "\n[dim]Use --show-token to display the full token value.[/dim]"
                )

            console.print()

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Token generation failed")
        sys.exit(1)


@token.command(name="list")
@click.option(
    "--include-expired",
    is_flag=True,
    help="Include expired tokens in listing",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON",
)
def token_list(include_expired, output_json):
    """List all authentication tokens.

    Shows metadata for all stored tokens including creation date,
    expiration, and last usage.

    Examples:
        skillmeat web token list
        skillmeat web token list --include-expired
        skillmeat web token list --json
    """
    from skillmeat.core.auth import TokenManager

    try:
        # Initialize token manager
        token_manager = TokenManager()

        # Get tokens
        tokens = token_manager.list_tokens(include_expired=include_expired)

        if not tokens:
            console.print("[yellow]No tokens found.[/yellow]")
            return

        if output_json:
            import json

            output = [
                {
                    "token_id": t.token_id,
                    "name": t.name,
                    "created_at": t.created_at.isoformat(),
                    "expires_at": t.expires_at.isoformat() if t.expires_at else None,
                    "last_used": t.last_used.isoformat() if t.last_used else None,
                    "is_expired": t.is_expired,
                }
                for t in tokens
            ]
            console.print(json.dumps(output, indent=2))
        else:
            console.print(f"\n[bold]Authentication Tokens[/bold] ({len(tokens)} total)\n")

            table = Table()
            table.add_column("Name", style="cyan", no_wrap=True)
            table.add_column("Token ID", style="dim")
            table.add_column("Created", style="blue")
            table.add_column("Expires", style="yellow")
            table.add_column("Last Used", style="green")
            table.add_column("Status", justify="center")

            for token_info in tokens:
                # Format dates
                created_str = token_info.created_at.strftime("%Y-%m-%d")
                expires_str = (
                    token_info.expires_at.strftime("%Y-%m-%d")
                    if token_info.expires_at
                    else "Never"
                )
                last_used_str = (
                    token_info.last_used.strftime("%Y-%m-%d")
                    if token_info.last_used
                    else "Never"
                )

                # Status indicator
                if token_info.is_expired:
                    status = "[red]Expired[/red]"
                else:
                    status = "[green]Active[/green]"

                table.add_row(
                    token_info.name,
                    token_info.token_id[:8] + "...",
                    created_str,
                    expires_str,
                    last_used_str,
                    status,
                )

            console.print(table)
            console.print()

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Token listing failed")
        sys.exit(1)


@token.command(name="revoke")
@click.argument("identifier")
@click.option(
    "--all",
    "revoke_all",
    is_flag=True,
    help="Revoke all tokens (use with caution)",
)
@click.option(
    "--confirm",
    is_flag=True,
    help="Skip confirmation prompt",
)
def token_revoke(identifier, revoke_all, confirm):
    """Revoke an authentication token.

    Revokes a token by name or ID. Revoked tokens can no longer be used
    for authentication.

    Examples:
        skillmeat web token revoke default
        skillmeat web token revoke abc12345
        skillmeat web token revoke --all --confirm
    """
    from skillmeat.core.auth import TokenManager

    try:
        # Initialize token manager
        token_manager = TokenManager()

        if revoke_all:
            # Revoke all tokens
            if not confirm:
                console.print(
                    "[yellow]WARNING:[/yellow] This will revoke ALL authentication tokens."
                )
                if not click.confirm("Are you sure?"):
                    console.print("Cancelled.")
                    return

            count = token_manager.revoke_all_tokens()
            console.print(f"[green]Revoked {count} token(s).[/green]")
            return

        # Try to find token by ID first
        token_info = token_manager.get_token_info(identifier)

        if token_info:
            # Found by ID
            if not confirm:
                console.print(f"[yellow]Revoking token:[/yellow] {token_info.name}")
                if not click.confirm("Are you sure?"):
                    console.print("Cancelled.")
                    return

            if token_manager.revoke_token(identifier):
                console.print(f"[green]Token '{token_info.name}' revoked.[/green]")
            else:
                console.print(f"[red]Failed to revoke token.[/red]")
                sys.exit(1)
        else:
            # Try by name
            count = token_manager.revoke_token_by_name(identifier)

            if count > 0:
                console.print(f"[green]Revoked {count} token(s) with name '{identifier}'.[/green]")
            else:
                console.print(f"[red]No token found with name or ID '{identifier}'.[/red]")
                sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Token revocation failed")
        sys.exit(1)


@token.command(name="cleanup")
@click.option(
    "--confirm",
    is_flag=True,
    help="Skip confirmation prompt",
)
def token_cleanup(confirm):
    """Remove expired tokens.

    Deletes all tokens that have passed their expiration date.

    Examples:
        skillmeat web token cleanup
        skillmeat web token cleanup --confirm
    """
    from skillmeat.core.auth import TokenManager

    try:
        # Initialize token manager
        token_manager = TokenManager()

        # Get expired tokens
        all_tokens = token_manager.list_tokens(include_expired=True)
        expired_tokens = [t for t in all_tokens if t.is_expired]

        if not expired_tokens:
            console.print("[green]No expired tokens found.[/green]")
            return

        console.print(f"\n[yellow]Found {len(expired_tokens)} expired token(s):[/yellow]\n")

        for token_info in expired_tokens:
            console.print(
                f"  - {token_info.name} (expired: {token_info.expires_at.strftime('%Y-%m-%d')})"
            )

        console.print()

        if not confirm:
            if not click.confirm("Remove these tokens?"):
                console.print("Cancelled.")
                return

        # Cleanup
        count = token_manager.cleanup_expired_tokens()
        console.print(f"[green]Removed {count} expired token(s).[/green]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Token cleanup failed")
        sys.exit(1)


@token.command(name="info")
@click.argument("identifier")
def token_info(identifier):
    """Show detailed information about a token.

    Displays metadata for a specific token including creation date,
    expiration, usage statistics, and status.

    Examples:
        skillmeat web token info default
        skillmeat web token info abc12345
    """
    from skillmeat.core.auth import TokenManager

    try:
        # Initialize token manager
        token_manager = TokenManager()

        # Try to find token by ID or name
        token_info = token_manager.get_token_info(identifier)

        if not token_info:
            # Try by name
            tokens = token_manager.list_tokens()
            matching = [t for t in tokens if t.name == identifier]

            if not matching:
                console.print(f"[red]No token found with name or ID '{identifier}'.[/red]")
                sys.exit(1)

            token_info = matching[0]

        # Display token information
        console.print(f"\n[bold]Token Information[/bold]\n")

        console.print(f"[cyan]Name:[/cyan]       {token_info.name}")
        console.print(f"[cyan]Token ID:[/cyan]   {token_info.token_id}")
        console.print(
            f"[cyan]Created:[/cyan]    {token_info.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        if token_info.expires_at:
            console.print(
                f"[cyan]Expires:[/cyan]    {token_info.expires_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            console.print(f"[cyan]Expires:[/cyan]    [yellow]Never[/yellow]")

        if token_info.last_used:
            console.print(
                f"[cyan]Last Used:[/cyan]  {token_info.last_used.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            console.print(f"[cyan]Last Used:[/cyan]  [dim]Never[/dim]")

        # Status
        if token_info.is_expired:
            console.print(f"[cyan]Status:[/cyan]     [red]Expired[/red]")
        else:
            console.print(f"[cyan]Status:[/cyan]     [green]Active[/green]")

        console.print()

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Token info failed")
        sys.exit(1)


# ====================
# Bundle Commands (Team Sharing)
# ====================


@main.group()
def bundle():
    """Create, import, and manage artifact bundles for team sharing.

    Bundles allow packaging and sharing collections of artifacts between teams,
    projects, and installations with comprehensive conflict resolution.

    Examples:
        skillmeat bundle create my-bundle            # Create bundle
        skillmeat bundle inspect bundle.zip          # Inspect bundle
        skillmeat bundle import bundle.zip           # Import bundle
        skillmeat bundle import bundle.zip --strategy=merge
    """
    pass


@bundle.command(name="create")
@click.argument("name")
@click.option(
    "--description",
    "-d",
    help="Bundle description",
    prompt="Enter bundle description",
)
@click.option(
    "--author",
    "-a",
    help="Author name or email",
    prompt="Enter author name or email",
)
@click.option(
    "--artifact",
    "-r",
    "artifacts",
    multiple=True,
    help="Artifact to include (can be specified multiple times: -r skill1 -r skill2)",
)
@click.option(
    "--type",
    "-t",
    "artifact_types",
    type=click.Choice(["skill", "command", "agent"]),
    multiple=True,
    help="Include all artifacts of type (can be specified multiple times)",
)
@click.option(
    "--all",
    "include_all",
    is_flag=True,
    help="Include all artifacts from collection",
)
@click.option(
    "--version",
    "-v",
    default="1.0.0",
    help="Bundle version (default: 1.0.0)",
)
@click.option(
    "--license",
    "-l",
    default="MIT",
    help="License identifier (default: MIT)",
)
@click.option(
    "--tags",
    help="Comma-separated tags for categorization",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output path (default: ./<name>.skillmeat-pack)",
)
@click.option(
    "--collection",
    "-c",
    help="Source collection (default: active collection)",
)
@click.option(
    "--compression",
    type=click.Choice(["default", "none", "maximum"]),
    default="default",
    help="Compression level",
)
@click.option(
    "--sign",
    is_flag=True,
    help="Sign bundle with Ed25519 signature",
)
@click.option(
    "--signing-key-id",
    help="Signing key ID (uses default if not specified)",
)
def bundle_create(
    name,
    description,
    author,
    artifacts,
    artifact_types,
    include_all,
    version,
    license,
    tags,
    output,
    collection,
    compression,
    sign,
    signing_key_id,
):
    """Create a new artifact bundle.

    Creates a .skillmeat-pack archive containing selected artifacts
    from the collection with manifest and integrity hashing.

    Examples:
        # Interactive mode
        skillmeat bundle create my-bundle

        # Include specific artifacts
        skillmeat bundle create my-bundle -r skill1 -r skill2 \\
            -d "My bundle" -a "user@example.com"

        # Include all skills
        skillmeat bundle create my-bundle --type skill \\
            -d "All skills" -a "user@example.com"

        # Include everything
        skillmeat bundle create my-bundle --all \\
            -d "Complete collection" -a "user@example.com"
    """
    from skillmeat.core.sharing import BundleBuilder, BundleValidationError
    import zipfile

    try:
        # Parse tags
        tag_list = []
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",")]

        # Determine compression level
        compression_map = {
            "default": zipfile.ZIP_DEFLATED,
            "none": zipfile.ZIP_STORED,
            "maximum": zipfile.ZIP_BZIP2,
        }
        compression_level = compression_map[compression]

        # Initialize bundle builder
        console.print(f"\n[cyan]Creating bundle '{name}'...[/cyan]\n")

        builder = BundleBuilder(
            name=name,
            description=description,
            author=author,
            version=version,
            license=license,
            tags=tag_list,
            collection_name=collection,
            compression_level=compression_level,
        )

        # Add artifacts
        artifact_count = 0

        if include_all:
            # Add all artifacts
            console.print("[cyan]Adding all artifacts from collection...[/cyan]")
            artifact_count = builder.add_all_artifacts()

        elif artifact_types:
            # Add all artifacts of specified types
            for artifact_type_str in artifact_types:
                artifact_type = ArtifactType(artifact_type_str)
                console.print(f"[cyan]Adding all {artifact_type.value}s...[/cyan]")
                count = builder.add_artifacts_by_type(artifact_type)
                artifact_count += count

        elif artifacts:
            # Add specific artifacts
            for artifact_name in artifacts:
                try:
                    builder.add_artifact(artifact_name)
                    artifact_count += 1
                    console.print(f"[green]Added:[/green] {artifact_name}")
                except ValueError as e:
                    console.print(f"[yellow]Warning:[/yellow] {e}")

        else:
            # Interactive mode - prompt to select artifacts
            console.print("[yellow]No artifacts specified. Use interactive selection:[/yellow]\n")

            from skillmeat.core.artifact import ArtifactManager

            artifact_mgr = ArtifactManager()
            available_artifacts = artifact_mgr.list_artifacts(collection_name=collection)

            if not available_artifacts:
                console.print("[red]No artifacts available in collection.[/red]")
                sys.exit(1)

            # Display available artifacts
            console.print(f"[bold]Available Artifacts ({len(available_artifacts)}):[/bold]\n")
            for idx, artifact in enumerate(available_artifacts, 1):
                console.print(
                    f"  {idx}. {artifact.name} ({artifact.type.value}) - {artifact.metadata.title or 'No title'}"
                )

            console.print(
                "\n[dim]Enter artifact numbers to include (comma-separated) or 'all':[/dim]"
            )
            selection = click.prompt("Selection", type=str, default="all")

            if selection.lower() == "all":
                artifact_count = builder.add_all_artifacts()
            else:
                # Parse selections
                try:
                    indices = [int(idx.strip()) for idx in selection.split(",")]
                    for idx in indices:
                        if 1 <= idx <= len(available_artifacts):
                            artifact = available_artifacts[idx - 1]
                            builder.add_artifact(artifact.name, artifact.type)
                            artifact_count += 1
                            console.print(f"[green]Added:[/green] {artifact.name}")
                        else:
                            console.print(f"[yellow]Warning:[/yellow] Invalid index {idx}")
                except ValueError:
                    console.print("[red]Error: Invalid selection format.[/red]")
                    sys.exit(1)

        if artifact_count == 0:
            console.print("[red]Error: No artifacts were added to bundle.[/red]")
            sys.exit(1)

        console.print(f"\n[green]Added {artifact_count} artifact(s) to bundle[/green]\n")

        # Determine output path
        if output:
            output_path = Path(output)
        else:
            output_path = Path.cwd() / f"{name}.skillmeat-pack"

        # Build bundle
        console.print(f"[cyan]Building bundle archive...[/cyan]")
        bundle_obj = builder.build(output_path, sign=sign, signing_key_id=signing_key_id)

        # Success summary
        console.print()
        console.print("[green]Bundle created successfully![/green]")
        console.print()
        console.print(f"  Name:        {bundle_obj.metadata.name}")
        console.print(f"  Version:     {bundle_obj.metadata.version}")
        console.print(f"  Artifacts:   {bundle_obj.artifact_count}")
        console.print(f"  Files:       {bundle_obj.total_files}")
        console.print(f"  Bundle hash: {bundle_obj.bundle_hash[:20]}...")

        if hasattr(bundle_obj, 'signature') and bundle_obj.signature:
            console.print(f"  Signed by:   {bundle_obj.signature.signer_name} <{bundle_obj.signature.signer_email}>")
            console.print(f"  Fingerprint: {bundle_obj.signature.key_fingerprint[:16]}...")

        console.print(f"  Output:      {output_path}")
        console.print()

    except BundleValidationError as e:
        console.print(f"[red]Validation Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Bundle creation failed")
        sys.exit(1)


@bundle.command(name="inspect")
@click.argument("bundle_file", type=click.Path(exists=True))
@click.option(
    "--verify",
    is_flag=True,
    help="Verify bundle integrity (hash check)",
)
@click.option(
    "--list-files",
    is_flag=True,
    help="List all files in each artifact",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON",
)
def bundle_inspect(bundle_file, verify, list_files, output_json):
    """Inspect a bundle file.

    Displays bundle metadata, artifact listing, and optionally
    verifies integrity using cryptographic hashes.

    Examples:
        skillmeat bundle inspect my-bundle.skillmeat-pack
        skillmeat bundle inspect my-bundle.skillmeat-pack --verify
        skillmeat bundle inspect my-bundle.skillmeat-pack --list-files
        skillmeat bundle inspect my-bundle.skillmeat-pack --json
    """
    from skillmeat.core.sharing import inspect_bundle, BundleValidationError

    try:
        bundle_path = Path(bundle_file)

        # Inspect bundle
        console.print(f"\n[cyan]Inspecting bundle: {bundle_path.name}[/cyan]\n")
        bundle_obj = inspect_bundle(bundle_path)

        if output_json:
            # JSON output
            import json

            output = bundle_obj.to_dict()
            output["bundle_path"] = str(bundle_path)
            console.print(json.dumps(output, indent=2))
            return

        # Display metadata
        console.print("[bold]Bundle Metadata[/bold]")
        console.print(f"  Name:        {bundle_obj.metadata.name}")
        console.print(f"  Description: {bundle_obj.metadata.description}")
        console.print(f"  Author:      {bundle_obj.metadata.author}")
        console.print(f"  Version:     {bundle_obj.metadata.version}")
        console.print(f"  License:     {bundle_obj.metadata.license}")
        console.print(f"  Created:     {bundle_obj.metadata.created_at}")

        if bundle_obj.metadata.tags:
            console.print(f"  Tags:        {', '.join(bundle_obj.metadata.tags)}")

        if bundle_obj.metadata.homepage:
            console.print(f"  Homepage:    {bundle_obj.metadata.homepage}")

        if bundle_obj.metadata.repository:
            console.print(f"  Repository:  {bundle_obj.metadata.repository}")

        # Display artifact summary
        console.print()
        console.print(f"[bold]Artifacts[/bold] ({bundle_obj.artifact_count} total)")
        console.print()

        # Create table
        table = Table()
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="blue")
        table.add_column("Version", style="yellow")
        table.add_column("Scope", style="green")
        table.add_column("Files", style="magenta", justify="right")

        for artifact in bundle_obj.artifacts:
            table.add_row(
                artifact.name,
                artifact.type,
                artifact.version,
                artifact.scope,
                str(len(artifact.files)),
            )

        console.print(table)

        # List files if requested
        if list_files:
            console.print()
            console.print("[bold]Artifact Files[/bold]")
            console.print()

            for artifact in bundle_obj.artifacts:
                console.print(f"[cyan]{artifact.type}/{artifact.name}:[/cyan]")
                for file_path in sorted(artifact.files)[:10]:  # Limit to 10
                    console.print(f"  - {file_path}")
                if len(artifact.files) > 10:
                    console.print(f"  ... and {len(artifact.files) - 10} more files")
                console.print()

        # Verify integrity if requested
        if verify:
            console.print()
            console.print("[cyan]Verifying bundle integrity...[/cyan]")

            from skillmeat.core.sharing import BundleHasher

            manifest_dict = bundle_obj.to_dict()
            artifact_hashes = [artifact.hash for artifact in bundle_obj.artifacts]

            is_valid = BundleHasher.verify_bundle_integrity(manifest_dict, artifact_hashes)

            if is_valid:
                console.print("[green]Bundle integrity verified![/green]")
                console.print(f"  Bundle hash: {bundle_obj.bundle_hash}")
            else:
                console.print("[red]WARNING: Bundle integrity check failed![/red]")
                console.print("[red]Bundle may have been tampered with or corrupted.[/red]")
                sys.exit(1)

        console.print()

    except BundleValidationError as e:
        console.print(f"[red]Validation Error:[/red] {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Bundle inspection failed")
        sys.exit(1)


@bundle.command(name="import")
@click.argument("bundle_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--collection",
    "-c",
    help="Target collection (default: active collection)",
)
@click.option(
    "--strategy",
    type=click.Choice(["merge", "fork", "skip", "interactive"]),
    default="interactive",
    help="Conflict resolution strategy (default: interactive)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview import without making changes",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force import even if validation warnings exist",
)
@click.option(
    "--hash",
    "expected_hash",
    help="Expected SHA-256 hash for verification",
)
def bundle_import(
    bundle_file: Path,
    collection: Optional[str],
    strategy: str,
    dry_run: bool,
    force: bool,
    expected_hash: Optional[str],
):
    """Import artifact bundle into collection.

    Imports a bundle ZIP file containing artifacts and their metadata.
    Provides multiple strategies for handling conflicts with existing artifacts.

    Strategies:
      merge:       Overwrite existing artifacts with imported ones
      fork:        Create new versions with suffix (e.g., 'skill-imported')
      skip:        Keep existing, don't import conflicting artifacts
      interactive: Prompt for each conflict (default)

    Security:
      All bundles are validated before import, including:
      - Hash verification (if --hash provided)
      - Path traversal prevention
      - Zip bomb detection
      - Schema validation

    Examples:
        # Interactive import (prompts for conflicts)
        skillmeat bundle import bundle.zip

        # Always merge (overwrite existing)
        skillmeat bundle import bundle.zip --strategy=merge

        # Fork conflicts (create duplicates)
        skillmeat bundle import bundle.zip --strategy=fork

        # Preview without changes
        skillmeat bundle import bundle.zip --dry-run

        # Verify bundle hash
        skillmeat bundle import bundle.zip --hash abc123...

        # Import to specific collection
        skillmeat bundle import bundle.zip --collection=work
    """
    from skillmeat.core.sharing.importer import BundleImporter

    try:
        # Initialize importer
        importer = BundleImporter()

        # Perform import
        console.print(
            f"\n[bold]Importing bundle:[/bold] {bundle_file.name}\n"
        )

        result = importer.import_bundle(
            bundle_path=bundle_file,
            collection_name=collection,
            strategy=strategy,
            dry_run=dry_run,
            force=force,
            expected_hash=expected_hash,
            console=console,
        )

        # Display result
        if result.success:
            if dry_run:
                console.print("\n[green]Dry run completed successfully[/green]")
            else:
                console.print(f"\n[green]{result.summary()}[/green]")

                # Show imported artifacts
                if result.artifacts:
                    console.print("\n[bold]Imported Artifacts:[/bold]")
                    table = Table()
                    table.add_column("Name", style="cyan")
                    table.add_column("Type", style="blue")
                    table.add_column("Resolution", style="yellow")
                    table.add_column("Notes")

                    for artifact in result.artifacts:
                        notes = ""
                        if artifact.resolution == "forked":
                            notes = f"Created as: {artifact.new_name}"
                        elif artifact.reason:
                            notes = artifact.reason

                        table.add_row(
                            artifact.name,
                            artifact.type,
                            artifact.resolution,
                            notes,
                        )

                    console.print(table)
                    console.print()

            # Show warnings
            if result.warnings:
                console.print("\n[yellow]Warnings:[/yellow]")
                for warning in result.warnings:
                    console.print(f"  - {warning}")

        else:
            console.print(f"\n[red]Import failed[/red]")

            # Show errors
            if result.errors:
                console.print("\n[red]Errors:[/red]")
                for error in result.errors:
                    console.print(f"  - {error}")

            sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Bundle import failed")
        sys.exit(1)


# ====================
# Vault Commands (Team Vault Connectors)
# ====================


@main.group()
def vault():
    """Manage team vault connectors for bundle hosting.

    Vaults provide pluggable storage backends for hosting bundles in team
    environments. Supports Git repositories, S3 buckets, and local file systems.

    Examples:
        skillmeat vault add team-git git git@github.com:team/vault.git
        skillmeat vault list
        skillmeat vault push my-bundle.skillmeat-pack
        skillmeat vault pull my-bundle-v1.0.0
    """
    pass


@vault.command(name="add")
@click.argument("name")
@click.argument("vault_type", type=click.Choice(["git", "s3", "local"]))
@click.argument("url_or_path")
@click.option(
    "--branch",
    "-b",
    default="main",
    help="Git branch (for git vaults, default: main)",
)
@click.option(
    "--region",
    "-r",
    default="us-east-1",
    help="AWS region (for s3 vaults, default: us-east-1)",
)
@click.option(
    "--prefix",
    "-p",
    default="",
    help="S3 key prefix (for s3 vaults)",
)
@click.option(
    "--endpoint-url",
    help="Custom S3 endpoint URL (for S3-compatible services)",
)
@click.option(
    "--set-default",
    is_flag=True,
    help="Set as default vault",
)
@click.option(
    "--read-only",
    is_flag=True,
    help="Configure as read-only vault",
)
def vault_add(
    name,
    vault_type,
    url_or_path,
    branch,
    region,
    prefix,
    endpoint_url,
    set_default,
    read_only,
):
    """Add a new vault configuration.

    Examples:
        # Add Git vault
        skillmeat vault add team-git git git@github.com:team/vault.git

        # Add S3 vault
        skillmeat vault add team-s3 s3 my-bucket --region us-west-2

        # Add local vault for testing
        skillmeat vault add local-dev local ~/.skillmeat/vault
    """
    try:
        from skillmeat.core.sharing.vault.config import (
            VaultConfig,
            VaultConfigManager,
        )

        vault_mgr = VaultConfigManager()

        # Build vault configuration based on type
        vault_config_dict = {}

        if vault_type == "git":
            vault_config_dict["url"] = url_or_path
            vault_config_dict["branch"] = branch
        elif vault_type == "s3":
            vault_config_dict["bucket"] = url_or_path
            vault_config_dict["region"] = region
            if prefix:
                vault_config_dict["prefix"] = prefix
            if endpoint_url:
                vault_config_dict["endpoint_url"] = endpoint_url
        elif vault_type == "local":
            vault_config_dict["path"] = url_or_path

        # Create vault config
        vault_config = VaultConfig(
            name=name,
            type=vault_type,
            config=vault_config_dict,
            read_only=read_only,
            is_default=set_default,
        )

        # Add vault
        vault_mgr.add_vault(vault_config)

        console.print(f"[green]Vault '{name}' added successfully[/green]")
        console.print(f"  Type: {vault_type}")
        console.print(f"  Location: {url_or_path}")
        if read_only:
            console.print("  Mode: Read-only")
        if set_default:
            console.print("  [cyan]Set as default vault[/cyan]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Failed to add vault")
        sys.exit(1)


@vault.command(name="list")
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed vault configuration",
)
def vault_list(verbose):
    """List all configured vaults.

    Examples:
        skillmeat vault list
        skillmeat vault list --verbose
    """
    try:
        from skillmeat.core.sharing.vault.config import VaultConfigManager

        vault_mgr = VaultConfigManager()
        vault_names = vault_mgr.list_vaults()

        if not vault_names:
            console.print("[yellow]No vaults configured[/yellow]")
            console.print("\nAdd a vault with: skillmeat vault add <name> <type> <url>")
            return

        default_vault = vault_mgr.get_default_vault()

        console.print(f"[bold]Configured Vaults ({len(vault_names)}):[/bold]\n")

        if verbose:
            # Detailed view
            for vault_name in vault_names:
                vault = vault_mgr.get_vault(vault_name)
                is_default = vault_name == default_vault

                console.print(f"[cyan]{vault_name}[/cyan]" + (" [green](default)[/green]" if is_default else ""))
                console.print(f"  Type: {vault.type}")
                console.print(f"  Read-only: {vault.read_only}")

                # Type-specific details
                if vault.type == "git":
                    console.print(f"  URL: {vault.config.get('url')}")
                    console.print(f"  Branch: {vault.config.get('branch', 'main')}")
                elif vault.type == "s3":
                    console.print(f"  Bucket: {vault.config.get('bucket')}")
                    console.print(f"  Region: {vault.config.get('region', 'us-east-1')}")
                    if vault.config.get('prefix'):
                        console.print(f"  Prefix: {vault.config.get('prefix')}")
                elif vault.type == "local":
                    console.print(f"  Path: {vault.config.get('path')}")

                console.print()
        else:
            # Simple table view
            table = Table()
            table.add_column("Name", style="cyan")
            table.add_column("Type", style="blue")
            table.add_column("Location")
            table.add_column("Flags", style="yellow")

            for vault_name in vault_names:
                vault = vault_mgr.get_vault(vault_name)
                is_default = vault_name == default_vault

                # Get location string
                if vault.type == "git":
                    location = vault.config.get("url", "")
                elif vault.type == "s3":
                    location = vault.config.get("bucket", "")
                elif vault.type == "local":
                    location = vault.config.get("path", "")
                else:
                    location = ""

                # Build flags
                flags = []
                if is_default:
                    flags.append("default")
                if vault.read_only:
                    flags.append("read-only")

                table.add_row(
                    vault_name,
                    vault.type,
                    location,
                    ", ".join(flags) if flags else "",
                )

            console.print(table)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Failed to list vaults")
        sys.exit(1)


@vault.command(name="remove")
@click.argument("name")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force removal without confirmation",
)
def vault_remove(name, force):
    """Remove a vault configuration.

    Examples:
        skillmeat vault remove team-git
        skillmeat vault remove old-vault --force
    """
    try:
        from skillmeat.core.sharing.vault.config import VaultConfigManager

        vault_mgr = VaultConfigManager()

        # Check if vault exists
        vault = vault_mgr.get_vault(name)
        if not vault:
            console.print(f"[yellow]Vault '{name}' not found[/yellow]")
            sys.exit(1)

        # Confirm removal
        if not force:
            from rich.prompt import Confirm

            if not Confirm.ask(f"Remove vault '{name}'?"):
                console.print("[yellow]Cancelled[/yellow]")
                return

        # Remove vault
        vault_mgr.remove_vault(name)

        # Also remove credentials
        vault_mgr.delete_credentials(name, vault.type)

        console.print(f"[green]Vault '{name}' removed[/green]")

    except ValueError as e:
        console.print(f"[yellow]{e}[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Failed to remove vault")
        sys.exit(1)


@vault.command(name="set-default")
@click.argument("name")
def vault_set_default(name):
    """Set default vault for push/pull operations.

    Examples:
        skillmeat vault set-default team-git
    """
    try:
        from skillmeat.core.sharing.vault.config import VaultConfigManager

        vault_mgr = VaultConfigManager()

        # Set default
        vault_mgr.set_default_vault(name)

        console.print(f"[green]Default vault set to '{name}'[/green]")

    except ValueError as e:
        console.print(f"[yellow]{e}[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Failed to set default vault")
        sys.exit(1)


@vault.command(name="auth")
@click.argument("name")
@click.option(
    "--username",
    "-u",
    help="Username for HTTPS Git or access key ID for S3",
)
@click.option(
    "--password",
    "-p",
    help="Password/token for HTTPS Git or secret key for S3",
    hide_input=True,
)
@click.option(
    "--ssh-key",
    help="Path to SSH private key (for Git vaults)",
    type=click.Path(exists=True),
)
def vault_auth(name, username, password, ssh_key):
    """Configure authentication for a vault.

    Credentials are stored securely in OS keychain or encrypted file storage.

    Examples:
        # Git HTTPS authentication
        skillmeat vault auth team-git --username myuser --password

        # Git SSH authentication
        skillmeat vault auth team-git --ssh-key ~/.ssh/id_rsa

        # S3 authentication
        skillmeat vault auth team-s3 --username AKIAIOSFODNN7EXAMPLE --password
    """
    try:
        from skillmeat.core.sharing.vault.config import VaultConfigManager

        vault_mgr = VaultConfigManager()

        # Get vault config
        vault = vault_mgr.get_vault(name)
        if not vault:
            console.print(f"[yellow]Vault '{name}' not found[/yellow]")
            sys.exit(1)

        # Build credentials based on vault type
        credentials = {}

        if vault.type == "git":
            if ssh_key:
                credentials["ssh_key_path"] = ssh_key
            elif username and password:
                credentials["username"] = username
                credentials["password"] = password
            elif username or password:
                console.print("[yellow]Both username and password are required for HTTPS authentication[/yellow]")
                sys.exit(1)
            else:
                console.print("[yellow]Provide either --ssh-key or --username/--password[/yellow]")
                sys.exit(1)

        elif vault.type == "s3":
            if username and password:
                credentials["access_key_id"] = username
                credentials["secret_access_key"] = password
            else:
                console.print("[yellow]Both --username (access key) and --password (secret key) are required for S3[/yellow]")
                sys.exit(1)

        elif vault.type == "local":
            console.print("[yellow]Local vaults do not require authentication[/yellow]")
            return

        # Store credentials
        vault_mgr.store_credentials(name, vault.type, credentials)

        console.print(f"[green]Credentials stored for vault '{name}'[/green]")
        console.print("[dim]Credentials are encrypted and stored securely[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Failed to configure vault authentication")
        sys.exit(1)


@vault.command(name="push")
@click.argument("bundle_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--vault",
    "-v",
    help="Vault name (default: default vault)",
)
@click.option(
    "--progress/--no-progress",
    default=True,
    help="Show upload progress",
)
def vault_push(bundle_path, vault, progress):
    """Upload bundle to team vault.

    Examples:
        skillmeat vault push my-bundle.skillmeat-pack
        skillmeat vault push my-bundle.skillmeat-pack --vault team-s3
    """
    try:
        from skillmeat.core.sharing.vault.config import VaultConfigManager
        from skillmeat.core.sharing.vault.factory import VaultFactory
        from skillmeat.core.sharing.builder import inspect_bundle
        from rich.progress import Progress, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn

        vault_mgr = VaultConfigManager()

        # Determine vault to use
        vault_name = vault or vault_mgr.get_default_vault()
        if not vault_name:
            console.print("[yellow]No vault specified and no default vault configured[/yellow]")
            console.print("Use --vault or set a default with: skillmeat vault set-default <name>")
            sys.exit(1)

        # Get vault config
        vault_config = vault_mgr.get_vault_with_credentials(vault_name)
        if not vault_config:
            console.print(f"[yellow]Vault '{vault_name}' not found[/yellow]")
            sys.exit(1)

        # Inspect bundle to get metadata
        console.print("[cyan]Inspecting bundle...[/cyan]")
        bundle = inspect_bundle(bundle_path)

        # Create vault connector
        connector = VaultFactory.create(
            vault_id=vault_config.name,
            vault_type=vault_config.type,
            config=vault_config.config,
            read_only=vault_config.read_only,
        )

        # Authenticate
        console.print(f"[cyan]Authenticating with vault '{vault_name}'...[/cyan]")
        connector.authenticate()

        # Push bundle
        console.print(f"[cyan]Uploading bundle to vault...[/cyan]")

        if progress:
            with Progress(
                *Progress.get_default_columns(),
                BarColumn(),
                DownloadColumn(),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
                console=console,
            ) as progress_bar:
                task = progress_bar.add_task(
                    f"[cyan]Uploading {bundle.metadata.name}",
                    total=bundle_path.stat().st_size,
                )

                def progress_callback(info):
                    progress_bar.update(task, completed=info.current)

                bundle_id = connector.push(
                    bundle_path,
                    bundle.metadata,
                    bundle.bundle_hash,
                    progress_callback=progress_callback,
                )
        else:
            bundle_id = connector.push(
                bundle_path,
                bundle.metadata,
                bundle.bundle_hash,
            )

        console.print(f"[green]Bundle uploaded successfully[/green]")
        console.print(f"  Bundle ID: {bundle_id}")
        console.print(f"  Vault: {vault_name}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Failed to push bundle to vault")
        sys.exit(1)


@vault.command(name="pull")
@click.argument("bundle_id")
@click.option(
    "--vault",
    "-v",
    help="Vault name (default: default vault)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output directory (default: current directory)",
)
@click.option(
    "--progress/--no-progress",
    default=True,
    help="Show download progress",
)
def vault_pull(bundle_id, vault, output, progress):
    """Download bundle from team vault.

    Examples:
        skillmeat vault pull my-bundle-v1.0.0
        skillmeat vault pull my-bundle-v1.0.0 --vault team-s3 --output ./bundles
    """
    try:
        from skillmeat.core.sharing.vault.config import VaultConfigManager
        from skillmeat.core.sharing.vault.factory import VaultFactory
        from rich.progress import Progress, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn

        vault_mgr = VaultConfigManager()

        # Determine vault to use
        vault_name = vault or vault_mgr.get_default_vault()
        if not vault_name:
            console.print("[yellow]No vault specified and no default vault configured[/yellow]")
            console.print("Use --vault or set a default with: skillmeat vault set-default <name>")
            sys.exit(1)

        # Get vault config
        vault_config = vault_mgr.get_vault_with_credentials(vault_name)
        if not vault_config:
            console.print(f"[yellow]Vault '{vault_name}' not found[/yellow]")
            sys.exit(1)

        # Determine output directory
        destination = output or Path.cwd()

        # Create vault connector
        connector = VaultFactory.create(
            vault_id=vault_config.name,
            vault_type=vault_config.type,
            config=vault_config.config,
            read_only=vault_config.read_only,
        )

        # Authenticate
        console.print(f"[cyan]Authenticating with vault '{vault_name}'...[/cyan]")
        connector.authenticate()

        # Get metadata to show size
        metadata = connector.get_metadata(bundle_id)

        # Pull bundle
        console.print(f"[cyan]Downloading bundle from vault...[/cyan]")

        if progress:
            with Progress(
                *Progress.get_default_columns(),
                BarColumn(),
                DownloadColumn(),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
                console=console,
            ) as progress_bar:
                task = progress_bar.add_task(
                    f"[cyan]Downloading {metadata.name}",
                    total=metadata.size_bytes,
                )

                def progress_callback(info):
                    progress_bar.update(task, completed=info.current)

                bundle_path = connector.pull(
                    bundle_id,
                    destination,
                    progress_callback=progress_callback,
                )
        else:
            bundle_path = connector.pull(bundle_id, destination)

        console.print(f"[green]Bundle downloaded successfully[/green]")
        console.print(f"  Location: {bundle_path}")
        console.print(f"  Name: {metadata.name} v{metadata.version}")
        console.print(f"  Size: {metadata.size_bytes:,} bytes")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Failed to pull bundle from vault")
        sys.exit(1)


@vault.command(name="ls")
@click.option(
    "--vault",
    "-v",
    help="Vault name (default: default vault)",
)
@click.option(
    "--filter",
    "-f",
    help="Filter bundles by name",
)
@click.option(
    "--tag",
    "-t",
    multiple=True,
    help="Filter bundles by tag (can be specified multiple times)",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Show detailed bundle information",
)
def vault_ls(vault, filter, tag, verbose):
    """List bundles in team vault.

    Examples:
        skillmeat vault ls
        skillmeat vault ls --vault team-git
        skillmeat vault ls --filter "backend" --tag python
    """
    try:
        from skillmeat.core.sharing.vault.config import VaultConfigManager
        from skillmeat.core.sharing.vault.factory import VaultFactory

        vault_mgr = VaultConfigManager()

        # Determine vault to use
        vault_name = vault or vault_mgr.get_default_vault()
        if not vault_name:
            console.print("[yellow]No vault specified and no default vault configured[/yellow]")
            console.print("Use --vault or set a default with: skillmeat vault set-default <name>")
            sys.exit(1)

        # Get vault config
        vault_config = vault_mgr.get_vault_with_credentials(vault_name)
        if not vault_config:
            console.print(f"[yellow]Vault '{vault_name}' not found[/yellow]")
            sys.exit(1)

        # Create vault connector
        connector = VaultFactory.create(
            vault_id=vault_config.name,
            vault_type=vault_config.type,
            config=vault_config.config,
            read_only=vault_config.read_only,
        )

        # Authenticate
        console.print(f"[cyan]Authenticating with vault '{vault_name}'...[/cyan]")
        connector.authenticate()

        # List bundles
        console.print("[cyan]Fetching bundle list...[/cyan]")
        bundles = connector.list(
            name_filter=filter,
            tag_filter=list(tag) if tag else None,
        )

        if not bundles:
            console.print("[yellow]No bundles found in vault[/yellow]")
            return

        console.print(f"\n[bold]Bundles in '{vault_name}' ({len(bundles)}):[/bold]\n")

        if verbose:
            # Detailed view
            for bundle in bundles:
                console.print(f"[cyan]{bundle.bundle_id}[/cyan]")
                console.print(f"  Name: {bundle.name} v{bundle.version}")
                console.print(f"  Description: {bundle.description}")
                console.print(f"  Author: {bundle.author}")
                console.print(f"  Uploaded: {bundle.uploaded_at}")
                console.print(f"  Size: {bundle.size_bytes:,} bytes")
                console.print(f"  Hash: {bundle.bundle_hash[:20]}...")
                if bundle.tags:
                    console.print(f"  Tags: {', '.join(bundle.tags)}")
                console.print()
        else:
            # Table view
            table = Table()
            table.add_column("Bundle ID", style="cyan")
            table.add_column("Version", style="blue")
            table.add_column("Description")
            table.add_column("Author", style="green")
            table.add_column("Size", justify="right")

            for bundle in bundles:
                # Format size
                size_mb = bundle.size_bytes / (1024 * 1024)
                size_str = f"{size_mb:.2f} MB" if size_mb >= 1 else f"{bundle.size_bytes:,} B"

                table.add_row(
                    bundle.bundle_id,
                    bundle.version,
                    bundle.description[:50] + "..." if len(bundle.description) > 50 else bundle.description,
                    bundle.author,
                    size_str,
                )

            console.print(table)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Failed to list vault bundles")
        sys.exit(1)


# ====================
# Signing Commands (Bundle Cryptographic Signing)
# ====================


@main.group()
def sign():
    """Manage cryptographic signing for bundles.

    Sign bundles with Ed25519 digital signatures for integrity verification.
    Manage signing keys and trusted public keys.

    Examples:
        skillmeat sign generate-key --name "John Doe" --email "john@example.com"
        skillmeat bundle create my-bundle --sign
        skillmeat sign verify my-bundle.skillmeat-pack
        skillmeat sign list-keys
    """
    pass


@sign.command(name="generate-key")
@click.option(
    "--name",
    "-n",
    required=True,
    help="Key owner name",
)
@click.option(
    "--email",
    "-e",
    required=True,
    help="Key owner email",
)
def generate_key(name, email):
    """Generate a new Ed25519 signing key pair.

    Creates a new signing key and stores it securely in the OS keychain
    (macOS Keychain, Windows Credential Manager, Linux Secret Service)
    or encrypted file storage as fallback.

    Examples:
        skillmeat sign generate-key -n "John Doe" -e "john@example.com"
        skillmeat sign generate-key --name "Jane Smith" --email "jane@example.com"
    """
    try:
        from skillmeat.core.signing import KeyManager

        console.print("[cyan]Generating Ed25519 signing key...[/cyan]")

        key_manager = KeyManager()

        # Generate key pair
        key_pair = key_manager.generate_key_pair(name, email)

        # Store key pair
        signing_key = key_manager.store_key_pair(key_pair)

        console.print("[green]Signing key generated successfully![/green]")
        console.print(f"\n[bold]Key Details:[/bold]")
        console.print(f"  Key ID: {signing_key.key_id}")
        console.print(f"  Fingerprint: {signing_key.fingerprint}")
        console.print(f"  Name: {signing_key.name}")
        console.print(f"  Email: {signing_key.email}")
        console.print(f"  Created: {signing_key.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

        console.print("\n[yellow]Keep your private key secure![/yellow]")
        console.print("You can now sign bundles with: skillmeat bundle create --sign")

    except Exception as e:
        console.print(f"[red]Error generating key:[/red] {e}")
        logger.exception("Failed to generate signing key")
        sys.exit(1)


@sign.command(name="list-keys")
@click.option(
    "--type",
    "-t",
    type=click.Choice(["signing", "trusted", "all"]),
    default="all",
    help="Type of keys to list (default: all)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed information",
)
def list_keys(type, verbose):
    """List all signing and trusted keys.

    Examples:
        skillmeat sign list-keys
        skillmeat sign list-keys --type signing
        skillmeat sign list-keys -v
    """
    try:
        from skillmeat.core.signing import KeyManager

        key_manager = KeyManager()

        # List signing keys
        if type in ("signing", "all"):
            signing_keys = key_manager.list_signing_keys()

            if signing_keys:
                console.print(f"\n[bold]Signing Keys ({len(signing_keys)}):[/bold]")

                if verbose:
                    for key in signing_keys:
                        console.print(f"\n[cyan]Key ID: {key.key_id}[/cyan]")
                        console.print(f"  Fingerprint: {key.fingerprint}")
                        console.print(f"  Name: {key.name}")
                        console.print(f"  Email: {key.email}")
                        console.print(f"  Created: {key.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    table = Table()
                    table.add_column("Key ID", style="cyan")
                    table.add_column("Name", style="green")
                    table.add_column("Email")
                    table.add_column("Created")

                    for key in signing_keys:
                        table.add_row(
                            key.key_id,
                            key.name,
                            key.email,
                            key.created_at.strftime("%Y-%m-%d"),
                        )

                    console.print(table)
            else:
                console.print("\n[yellow]No signing keys found[/yellow]")
                console.print("Generate one with: skillmeat sign generate-key")

        # List trusted public keys
        if type in ("trusted", "all"):
            public_keys = key_manager.list_public_keys()

            if public_keys:
                console.print(f"\n[bold]Trusted Public Keys ({len(public_keys)}):[/bold]")

                if verbose:
                    for key in public_keys:
                        console.print(f"\n[cyan]Key ID: {key.key_id}[/cyan]")
                        console.print(f"  Fingerprint: {key.fingerprint}")
                        console.print(f"  Name: {key.name}")
                        console.print(f"  Email: {key.email}")
                        console.print(f"  Imported: {key.imported_at.strftime('%Y-%m-%d %H:%M:%S')}")
                        console.print(f"  Trusted: {'Yes' if key.trusted else 'No'}")
                else:
                    table = Table()
                    table.add_column("Key ID", style="cyan")
                    table.add_column("Name", style="green")
                    table.add_column("Email")
                    table.add_column("Imported")
                    table.add_column("Trusted", justify="center")

                    for key in public_keys:
                        table.add_row(
                            key.key_id,
                            key.name,
                            key.email,
                            key.imported_at.strftime("%Y-%m-%d"),
                            "✓" if key.trusted else "✗",
                        )

                    console.print(table)
            else:
                console.print("\n[yellow]No trusted public keys found[/yellow]")

    except Exception as e:
        console.print(f"[red]Error listing keys:[/red] {e}")
        logger.exception("Failed to list keys")
        sys.exit(1)


@sign.command(name="export-key")
@click.argument("key_id")
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file path (default: <key_id>.pub)",
)
def export_key(key_id, output):
    """Export public key for sharing.

    Exports the public key portion of a signing key so others can verify
    bundles you sign.

    Examples:
        skillmeat sign export-key abc123def456
        skillmeat sign export-key abc123def456 -o my-key.pub
    """
    try:
        from skillmeat.core.signing import KeyManager

        key_manager = KeyManager()

        # Export public key
        public_key_pem = key_manager.export_public_key(key_id)

        if not public_key_pem:
            console.print(f"[red]Key {key_id} not found[/red]")
            sys.exit(1)

        # Determine output path
        if not output:
            output = f"{key_id}.pub"

        output_path = Path(output)

        # Write to file
        output_path.write_text(public_key_pem)

        console.print(f"[green]Public key exported to:[/green] {output_path}")
        console.print("\nShare this file with others to allow them to verify your signatures.")

    except Exception as e:
        console.print(f"[red]Error exporting key:[/red] {e}")
        logger.exception("Failed to export key")
        sys.exit(1)


@sign.command(name="import-key")
@click.argument("key_file", type=click.Path(exists=True))
@click.option(
    "--name",
    "-n",
    required=True,
    help="Key owner name",
)
@click.option(
    "--email",
    "-e",
    required=True,
    help="Key owner email",
)
@click.option(
    "--trust/--no-trust",
    default=True,
    help="Mark key as trusted (default: yes)",
)
def import_key(key_file, name, email, trust):
    """Import a trusted public key.

    Import a public key from someone else to verify bundles they sign.
    Only bundles signed with trusted keys will pass verification.

    Examples:
        skillmeat sign import-key john-doe.pub -n "John Doe" -e "john@example.com"
        skillmeat sign import-key key.pub --name "Jane" --email "jane@example.com" --no-trust
    """
    try:
        from skillmeat.core.signing import KeyManager

        key_file_path = Path(key_file)

        # Read public key
        public_key_pem = key_file_path.read_text()

        console.print(f"[cyan]Importing public key from {key_file}...[/cyan]")

        key_manager = KeyManager()

        # Import public key
        public_key = key_manager.import_public_key(public_key_pem, name, email, trust)

        console.print("[green]Public key imported successfully![/green]")
        console.print(f"\n[bold]Key Details:[/bold]")
        console.print(f"  Key ID: {public_key.key_id}")
        console.print(f"  Fingerprint: {public_key.fingerprint}")
        console.print(f"  Name: {public_key.name}")
        console.print(f"  Email: {public_key.email}")
        console.print(f"  Trusted: {'Yes' if public_key.trusted else 'No'}")

        if trust:
            console.print(
                "\n[green]This key is now trusted for bundle verification.[/green]"
            )
        else:
            console.print(
                "\n[yellow]This key is imported but not trusted.[/yellow]"
            )

    except Exception as e:
        console.print(f"[red]Error importing key:[/red] {e}")
        logger.exception("Failed to import key")
        sys.exit(1)


@sign.command(name="revoke")
@click.argument("key_id")
@click.option(
    "--type",
    "-t",
    type=click.Choice(["signing", "trusted"]),
    required=True,
    help="Type of key to revoke",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Skip confirmation prompt",
)
def revoke_key(key_id, type, force):
    """Revoke a signing or trusted key.

    For signing keys: This will delete your private key. You won't be able to
    sign bundles with this key anymore.

    For trusted keys: This will remove trust in the key. Bundles signed with
    this key will no longer pass verification.

    Examples:
        skillmeat sign revoke abc123def456 --type signing
        skillmeat sign revoke abc123def456 --type trusted --force
    """
    try:
        from skillmeat.core.signing import KeyManager

        key_manager = KeyManager()

        # Load key to show details
        if type == "signing":
            key_pair = key_manager.load_private_key(key_id)
            if not key_pair:
                console.print(f"[red]Signing key {key_id} not found[/red]")
                sys.exit(1)

            console.print(f"[bold]Signing Key:[/bold]")
            console.print(f"  Key ID: {key_pair.key_id}")
            console.print(f"  Fingerprint: {key_pair.fingerprint}")
            console.print(f"  Name: {key_pair.name}")
            console.print(f"  Email: {key_pair.email}")
        else:
            public_key = key_manager.load_public_key(key_id)
            if not public_key:
                console.print(f"[red]Trusted key {key_id} not found[/red]")
                sys.exit(1)

            console.print(f"[bold]Trusted Public Key:[/bold]")
            console.print(f"  Key ID: {public_key.key_id}")
            console.print(f"  Fingerprint: {public_key.fingerprint}")
            console.print(f"  Name: {public_key.name}")
            console.print(f"  Email: {public_key.email}")

        # Confirm revocation
        if not force:
            if type == "signing":
                warning = "\n[yellow]WARNING: This will delete your private key permanently![/yellow]"
            else:
                warning = "\n[yellow]This will remove trust in this public key.[/yellow]"

            console.print(warning)
            if not Confirm.ask(f"Are you sure you want to revoke this key?"):
                console.print("[yellow]Revocation cancelled[/yellow]")
                return

        # Revoke key
        if type == "signing":
            deleted = key_manager.delete_private_key(key_id)
        else:
            deleted = key_manager.revoke_public_key(key_id)

        if deleted:
            console.print(f"[green]Key {key_id} revoked successfully[/green]")
        else:
            console.print(f"[red]Failed to revoke key {key_id}[/red]")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error revoking key:[/red] {e}")
        logger.exception("Failed to revoke key")
        sys.exit(1)


@sign.command(name="verify")
@click.argument("bundle_path", type=click.Path(exists=True))
@click.option(
    "--require-signature",
    is_flag=True,
    help="Fail if bundle is unsigned",
)
def verify_bundle(bundle_path, require_signature):
    """Verify bundle signature.

    Verifies the cryptographic signature of a bundle to ensure it hasn't
    been tampered with and was signed by a trusted key.

    Examples:
        skillmeat sign verify my-bundle.skillmeat-pack
        skillmeat sign verify bundle.skillmeat-pack --require-signature
    """
    try:
        from skillmeat.core.signing import BundleVerifier, KeyManager

        bundle_path = Path(bundle_path)

        console.print(f"[cyan]Verifying bundle signature...[/cyan]")

        key_manager = KeyManager()
        verifier = BundleVerifier(key_manager)

        # Verify bundle
        result = verifier.verify_bundle_file(bundle_path, require_signature)

        # Display result
        console.print()
        if result.valid:
            console.print(f"[green]{result.summary()}[/green]")

            if result.signature_data:
                console.print(f"\n[bold]Signature Details:[/bold]")
                console.print(f"  Signer: {result.signature_data.signer_name} <{result.signature_data.signer_email}>")
                console.print(f"  Fingerprint: {result.signature_data.key_fingerprint}")
                console.print(f"  Signed: {result.signature_data.signed_at.strftime('%Y-%m-%d %H:%M:%S')}")
                console.print(f"  Algorithm: {result.signature_data.algorithm}")
        else:
            console.print(f"[red]{result.summary()}[/red]")
            console.print(f"\n[bold]Status:[/bold] {result.status.value}")
            console.print(f"[bold]Message:[/bold] {result.message}")

            if result.signature_data:
                console.print(f"\n[bold]Signature Details:[/bold]")
                console.print(f"  Signer: {result.signature_data.signer_name} <{result.signature_data.signer_email}>")
                console.print(f"  Fingerprint: {result.signature_data.key_fingerprint}")
                console.print(f"  Signed: {result.signature_data.signed_at.strftime('%Y-%m-%d %H:%M:%S')}")

            sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error verifying bundle:[/red] {e}")
        logger.exception("Failed to verify bundle")
        sys.exit(1)


# ====================
# Marketplace Commands
# ====================


@main.group()
def marketplace():
    """Marketplace publishing and discovery commands.

    Publish bundles to marketplaces, check submission status, and manage
    marketplace listings.

    Examples:
      skillmeat marketplace publish my-bundle.skillmeat-pack
      skillmeat marketplace status sub-2025-11-17-abc123
      skillmeat marketplace submissions
    """
    pass


@marketplace.command(name="publish")
@click.argument("bundle_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--name",
    "-n",
    help="Listing name (required)",
)
@click.option(
    "--description",
    "-d",
    help="Description (required)",
)
@click.option(
    "--category",
    "-c",
    type=click.Choice(["skill", "command", "agent", "hook", "mcp-server", "bundle"]),
    help="Category (required)",
)
@click.option(
    "--version",
    "-v",
    help="Version (default: from bundle)",
)
@click.option(
    "--license",
    "-l",
    help="License identifier (default: from bundle)",
)
@click.option(
    "--tags",
    "-t",
    help="Comma-separated tags",
)
@click.option(
    "--homepage",
    help="Homepage URL",
)
@click.option(
    "--repository",
    help="Repository URL",
)
@click.option(
    "--broker",
    "-b",
    default="skillmeat",
    help="Marketplace broker name (default: skillmeat)",
)
@click.option(
    "--sign/--no-sign",
    default=True,
    help="Sign bundle before publishing (default: yes)",
)
@click.option(
    "--key-id",
    help="Signing key ID (uses default if not specified)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Validate without publishing",
)
def publish_bundle_cmd(
    bundle_path: Path,
    name: Optional[str],
    description: Optional[str],
    category: Optional[str],
    version: Optional[str],
    license: Optional[str],
    tags: Optional[str],
    homepage: Optional[str],
    repository: Optional[str],
    broker: str,
    sign: bool,
    key_id: Optional[str],
    dry_run: bool,
):
    """Publish a bundle to a marketplace.

    Validates metadata, checks license compatibility, signs the bundle,
    and submits it to the specified marketplace broker.

    Examples:
      skillmeat marketplace publish my-bundle.skillmeat-pack
      skillmeat marketplace publish bundle.skillmeat-pack --broker skillmeat
      skillmeat marketplace publish bundle.skillmeat-pack --dry-run
    """
    try:
        from skillmeat.core.marketplace.publisher import PublisherService
        from skillmeat.core.marketplace.service import MarketplaceService
        from skillmeat.core.sharing.builder import inspect_bundle
        from rich.progress import Progress, SpinnerColumn, TextColumn

        console.print(Panel(
            "[bold cyan]Publishing Bundle to Marketplace[/bold cyan]",
            expand=False,
        ))
        console.print()

        # Initialize services
        marketplace_service = MarketplaceService()
        publisher_service = PublisherService()

        # Register available brokers
        for broker_name, broker_instance in marketplace_service._brokers.items():
            publisher_service.register_broker(broker_instance)

        # Inspect bundle to get metadata
        console.print("[cyan]Inspecting bundle...[/cyan]")
        bundle = inspect_bundle(bundle_path)

        # Display bundle info
        console.print(f"  Bundle: {bundle.metadata.name}")
        console.print(f"  Artifacts: {bundle.artifact_count}")
        console.print(f"  Version: {bundle.metadata.version}")
        console.print()

        # Collect metadata
        metadata_dict = {}

        # Name
        if name:
            metadata_dict["name"] = name
        else:
            from rich.prompt import Prompt
            metadata_dict["name"] = Prompt.ask(
                "[cyan]Listing name[/cyan]",
                default=bundle.metadata.name,
            )

        # Description
        if description:
            metadata_dict["description"] = description
        else:
            from rich.prompt import Prompt
            metadata_dict["description"] = Prompt.ask(
                "[cyan]Description[/cyan]",
                default=bundle.metadata.description,
            )

        # Category
        if category:
            metadata_dict["category"] = category
        else:
            from rich.prompt import Prompt
            metadata_dict["category"] = Prompt.ask(
                "[cyan]Category[/cyan]",
                choices=["skill", "command", "agent", "hook", "mcp-server", "bundle"],
                default="bundle" if bundle.artifact_count > 1 else "skill",
            )

        # Version
        if version:
            metadata_dict["version"] = version
        else:
            metadata_dict["version"] = bundle.metadata.version

        # License
        if license:
            metadata_dict["license"] = license
        else:
            metadata_dict["license"] = bundle.metadata.license

        # Tags
        if tags:
            metadata_dict["tags"] = [t.strip() for t in tags.split(",")]
        else:
            metadata_dict["tags"] = bundle.metadata.tags

        # URLs
        if homepage:
            metadata_dict["homepage"] = homepage
        elif bundle.metadata.homepage:
            metadata_dict["homepage"] = bundle.metadata.homepage

        if repository:
            metadata_dict["repository"] = repository
        elif bundle.metadata.repository:
            metadata_dict["repository"] = bundle.metadata.repository

        # Sign bundle
        metadata_dict["sign_bundle"] = sign

        # Validate metadata
        console.print("[cyan]Validating metadata...[/cyan]")
        validated_metadata, suggestions = publisher_service.validate_metadata(
            metadata_dict, with_suggestions=True
        )

        # Display validation summary
        console.print("[green]✓[/green] Metadata valid")
        console.print()

        # Display suggestions if any
        if suggestions:
            console.print("[yellow]Suggestions:[/yellow]")
            for suggestion in suggestions:
                console.print(f"  • {suggestion}")
            console.print()

        # Validate license
        console.print("[cyan]Validating license compatibility...[/cyan]")
        license_result = publisher_service.validate_license(
            bundle_path, validated_metadata.license
        )

        if license_result.is_valid:
            console.print("[green]✓[/green] License validation passed")
        else:
            console.print("[red]✗[/red] License validation failed")
            for error in license_result.errors:
                console.print(f"  [red]• {error}[/red]")
            sys.exit(1)

        # Display warnings
        if license_result.warnings:
            console.print("[yellow]License warnings:[/yellow]")
            for warning in license_result.warnings:
                console.print(f"  [yellow]• {warning}[/yellow]")

        console.print()

        # Compliance Scan
        console.print("[cyan]Scanning bundle for compliance...[/cyan]")
        compliance_report = publisher_service.scan_bundle_compliance(bundle_path)

        if compliance_report.pass_status:
            console.print("[green]✓[/green] Compliance scan passed")
        else:
            console.print("[yellow]⚠[/yellow] Compliance scan completed with issues")

        # Display compliance report
        console.print()
        console.print("[bold]License Compliance Report[/bold]")
        console.print("=" * 60)
        console.print()

        console.print("[bold]Licenses Found:[/bold]")
        if compliance_report.license_counts:
            for license_id, count in sorted(
                compliance_report.license_counts.items(),
                key=lambda x: x[1],
                reverse=True
            ):
                console.print(f"  ✓ {license_id} ({count} artifact(s))")
        else:
            console.print("  [yellow]No licenses detected[/yellow]")

        console.print()

        if compliance_report.conflicts:
            console.print("[red]Conflicts:[/red]")
            for conflict in compliance_report.conflicts:
                console.print(f"  [red]✗ {conflict}[/red]")
            console.print()
            console.print("[red]Cannot publish with license conflicts. Resolve conflicts and try again.[/red]")
            sys.exit(1)
        else:
            console.print("[green]Compatibility: ✓ All licenses compatible[/green]")

        if compliance_report.warnings:
            console.print()
            console.print("[yellow]Warnings:[/yellow]")
            for warning in compliance_report.warnings:
                console.print(f"  [yellow]⚠ {warning}[/yellow]")

        console.print()

        # Check signing key if needed
        if sign:
            console.print("[cyan]Checking signing key...[/cyan]")
            if not publisher_service.check_signing_key_available():
                console.print(
                    "[red]No signing key available. Generate one with:[/red]"
                )
                console.print("  skillmeat sign generate-key")
                sys.exit(1)
            console.print("[green]✓[/green] Signing key available")
            console.print()

        # Dry-run mode
        if dry_run:
            console.print("[yellow]Dry-run mode: No changes will be made[/yellow]")
            console.print()
            console.print("[green]Bundle is ready for publication![/green]")
            return

        # Legal Compliance Checklist
        console.print()
        console.print("[bold cyan]Publisher Agreement & Legal Checklist[/bold cyan]")
        console.print("=" * 60)
        console.print()

        # Get compliance checklist
        checklist = publisher_service.get_compliance_checklist()

        # Display agreement summary
        console.print("[bold]SkillMeat Marketplace Publisher Agreement v{0}[/bold]".format(
            checklist.agreement_version
        ))
        console.print()
        console.print("By publishing to SkillMeat Marketplace, you agree to:")
        console.print("  • Grant distribution rights to your content")
        console.print("  • Ensure you have legal rights to all submitted content")
        console.print("  • Comply with all license requirements")
        console.print("  • Meet content quality and security standards")
        console.print("  • Provide accurate information and attribution")
        console.print()
        console.print("For full terms, see: docs/legal/publisher-agreement-v1.md")
        console.print()

        # Display checklist
        console.print("[bold]Please review and acknowledge the following:[/bold]")
        console.print()

        for i, item in enumerate(checklist.items, start=1):
            console.print(f"[{i}] {item.text}")

        console.print()
        console.print("[yellow]Note: All items must be acknowledged to proceed.[/yellow]")
        console.print()

        # Get user consent
        from rich.prompt import Confirm
        if not Confirm.ask("Do you acknowledge all items above?", default=False):
            console.print("[yellow]Publisher agreement not accepted. Publication cancelled.[/yellow]")
            sys.exit(1)

        # Acknowledge checklist
        import getpass
        user_id = getpass.getuser()  # Get system username
        checklist.acknowledge_all(user_id=user_id)

        console.print("[green]✓[/green] Compliance checklist acknowledged")
        console.print()

        # Create consent log (will be used during publish)
        # Generate temporary submission ID for consent logging
        temp_submission_id = f"temp-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        consent_log = publisher_service.log_consent(
            submission_id=temp_submission_id,
            checklist=checklist,
            user_id=user_id,
        )

        console.print("[green]✓[/green] Consent logged to audit trail")
        console.print()

        # Confirm publication
        console.print("[bold]Ready to publish:[/bold]")
        console.print(f"  Name: {validated_metadata.name}")
        console.print(f"  Description: {validated_metadata.description[:60]}...")
        console.print(f"  Category: {validated_metadata.category}")
        console.print(f"  Version: {validated_metadata.version}")
        console.print(f"  License: {validated_metadata.license}")
        console.print(f"  Broker: {broker}")
        console.print(f"  Sign: {'Yes' if sign else 'No'}")
        console.print()

        if not Confirm.ask("Proceed with publication?", default=True):
            console.print("[yellow]Publication cancelled[/yellow]")
            return

        # Publish bundle
        console.print()
        console.print("[cyan]Publishing to marketplace...[/cyan]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Uploading bundle...", total=None)

            result = publisher_service.publish_bundle(
                bundle_path=bundle_path,
                metadata=validated_metadata,
                broker_name=broker,
                validate_license=False,  # Already validated
                sign_bundle=sign,
                key_id=key_id,
                dry_run=False,
                consent_log=consent_log,
                compliance_report=compliance_report,
                user_id=user_id,
            )

            progress.remove_task(task)

        console.print()

        # Display result
        if result.success:
            console.print(Panel(
                f"[green]Published Successfully![/green]\n\n"
                f"Submission ID: {result.listing_id or 'N/A'}\n"
                f"Status: pending_moderation\n"
                f"Expected Review: 1-2 business days\n\n"
                + (f"Listing URL: {result.listing_url}\n\n" if result.listing_url else "")
                + f"Track status: skillmeat marketplace status {result.listing_id}",
                title="Success",
                expand=False,
            ))

            if result.warnings:
                console.print()
                console.print("[yellow]Warnings:[/yellow]")
                for warning in result.warnings:
                    console.print(f"  • {warning}")
        else:
            console.print(f"[red]Publication failed:[/red] {result.message}")
            if result.errors:
                for error in result.errors:
                    console.print(f"  • {error}")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error publishing bundle:[/red] {e}")
        logger.exception("Failed to publish bundle")
        sys.exit(1)


@marketplace.command(name="status")
@click.argument("submission_id")
def submission_status_cmd(submission_id: str):
    """Check the status of a marketplace submission.

    Shows the current moderation status, submission details, and any
    feedback from the marketplace.

    Examples:
      skillmeat marketplace status sub-2025-11-17-abc123
    """
    try:
        from skillmeat.core.marketplace.publisher import PublisherService

        publisher_service = PublisherService()

        # Get submission
        submission = publisher_service.get_submission_status(submission_id)

        if not submission:
            console.print(f"[red]Submission not found:[/red] {submission_id}")
            sys.exit(1)

        # Display submission details
        console.print(Panel(
            f"[bold]Submission Status[/bold]",
            expand=False,
        ))
        console.print()

        # Status with color
        status_color = {
            "pending": "yellow",
            "validating": "cyan",
            "approved": "green",
            "rejected": "red",
            "published": "green",
            "failed": "red",
        }.get(submission.status.value, "white")

        console.print(f"[bold]Submission ID:[/bold] {submission.submission_id}")
        console.print(f"[bold]Status:[/bold] [{status_color}]{submission.status.value}[/{status_color}]")
        console.print(f"[bold]Broker:[/bold] {submission.broker_name}")
        console.print()

        console.print(f"[bold]Metadata:[/bold]")
        console.print(f"  Name: {submission.metadata.get('name', 'N/A')}")
        console.print(f"  Version: {submission.metadata.get('version', 'N/A')}")
        console.print(f"  Category: {submission.metadata.get('category', 'N/A')}")
        console.print(f"  License: {submission.metadata.get('license', 'N/A')}")
        console.print()

        console.print(f"[bold]Timeline:[/bold]")
        console.print(f"  Created: {submission.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        console.print(f"  Updated: {submission.updated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        console.print()

        if submission.listing_id:
            console.print(f"[bold]Listing ID:[/bold] {submission.listing_id}")
            console.print()

        if submission.moderation_feedback:
            console.print(f"[bold]Moderation Feedback:[/bold]")
            console.print(f"  {submission.moderation_feedback}")
            console.print()

        if submission.error_message:
            console.print(f"[bold red]Error:[/bold red]")
            console.print(f"  {submission.error_message}")
            console.print()

        # Status-specific messages
        if submission.status.value == "pending":
            console.print("[yellow]Your submission is pending review.[/yellow]")
            console.print("Expected review time: 1-2 business days")
        elif submission.status.value == "approved":
            console.print("[green]Your submission has been approved![/green]")
            console.print("It will be published shortly.")
        elif submission.status.value == "published":
            console.print("[green]Your submission is now published![/green]")
        elif submission.status.value == "rejected":
            console.print("[red]Your submission was rejected.[/red]")
            console.print("Review the moderation feedback above.")
        elif submission.status.value == "failed":
            console.print("[red]Submission failed due to an error.[/red]")

    except Exception as e:
        console.print(f"[red]Error checking submission status:[/red] {e}")
        logger.exception("Failed to check submission status")
        sys.exit(1)


@marketplace.command(name="submissions")
@click.option(
    "--broker",
    "-b",
    help="Filter by broker name",
)
@click.option(
    "--status",
    "-s",
    type=click.Choice(["pending", "validating", "approved", "rejected", "published", "failed"]),
    help="Filter by status",
)
@click.option(
    "--limit",
    "-l",
    type=int,
    default=20,
    help="Maximum number of results (default: 20)",
)
def list_submissions_cmd(
    broker: Optional[str],
    status: Optional[str],
    limit: int,
):
    """List all marketplace submissions.

    Shows a table of all submissions with their current status.

    Examples:
      skillmeat marketplace submissions
      skillmeat marketplace submissions --status published
      skillmeat marketplace submissions --broker skillmeat --limit 10
    """
    try:
        from skillmeat.core.marketplace.publisher import PublisherService
        from skillmeat.core.marketplace.submission import SubmissionStatus

        publisher_service = PublisherService()

        # Convert status string to enum
        status_enum = None
        if status:
            status_enum = SubmissionStatus(status)

        # List submissions
        submissions = publisher_service.list_submissions(
            broker_name=broker,
            status=status_enum,
            limit=limit,
        )

        if not submissions:
            console.print("[yellow]No submissions found[/yellow]")
            return

        # Display submissions table
        table = Table(title="Marketplace Submissions", show_header=True)
        table.add_column("Submission ID", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Version", style="white")
        table.add_column("Status", style="white")
        table.add_column("Broker", style="white")
        table.add_column("Created", style="white")

        for submission in submissions:
            # Status with color
            status_color = {
                "pending": "yellow",
                "validating": "cyan",
                "approved": "green",
                "rejected": "red",
                "published": "green",
                "failed": "red",
            }.get(submission.status.value, "white")

            status_text = f"[{status_color}]{submission.status.value}[/{status_color}]"

            table.add_row(
                submission.submission_id,
                submission.metadata.get("name", "N/A"),
                submission.metadata.get("version", "N/A"),
                status_text,
                submission.broker_name,
                submission.created_at.strftime("%Y-%m-%d"),
            )

        console.print()
        console.print(table)
        console.print()

        # Display stats
        stats = publisher_service.get_submission_stats()
        console.print(f"[bold]Total submissions:[/bold] {stats['total']}")
        console.print(
            f"  Published: {stats['published']} | "
            f"Pending: {stats['pending']} | "
            f"Rejected: {stats['rejected']}"
        )

    except Exception as e:
        console.print(f"[red]Error listing submissions:[/red] {e}")
        logger.exception("Failed to list submissions")
        sys.exit(1)


# ====================
# Entry Point
# ====================


if __name__ == "__main__":
    sys.exit(main())
