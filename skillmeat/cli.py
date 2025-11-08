"""CLI entry point for SkillMeat.

This module provides the complete command-line interface for SkillMeat,
a personal collection manager for Claude Code artifacts.
"""

import sys
import tempfile
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm

from skillmeat import __version__
from skillmeat.config import ConfigManager
from skillmeat.core.collection import CollectionManager
from skillmeat.core.artifact import ArtifactManager, ArtifactType, UpdateStrategy
from skillmeat.core.deployment import DeploymentManager
from skillmeat.core.version import VersionManager
from skillmeat.sources.github import GitHubSource
from skillmeat.sources.local import LocalSource
from skillmeat.utils.validator import ArtifactValidator

# Console for output
console = Console(force_terminal=True, legacy_windows=False)


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
            console.print(
                f"[yellow]Collection '{name}' already exists[/yellow]"
            )
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
                tag_str = ", ".join(artifact.metadata.tags) if artifact.metadata.tags else ""
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
def remove(name: str, artifact_type: Optional[str], collection: Optional[str], keep_files: bool):
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
                override_name=name,
                verify=not no_verify,
                force=force,
            )

            console.print(f"[green]Added {artifact_type.value}: {artifact.name}[/green]")

        else:
            # Local path
            local_path = Path(spec).resolve()
            if not local_path.exists():
                console.print(f"[red]Path not found: {spec}[/red]")
                sys.exit(1)

            console.print(f"[cyan]Adding from local path: {local_path}...[/cyan]")

            artifact = artifact_mgr.add_from_local(
                local_path=local_path,
                artifact_type=artifact_type,
                collection_name=collection,
                override_name=name,
                verify=not no_verify,
                force=force,
            )

            console.print(f"[green]Added {artifact_type.value}: {artifact.name}[/green]")

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
            console.print(f"\n[yellow]Updates available ({len(updates_available)}):[/yellow]")
            for info in updates_available:
                console.print(f"  {info['name']} ({info['type']}): {info['current_version']} -> {info['latest_version']}")

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

        artifact_mgr.update(
            name=name,
            artifact_type=type_filter,
            collection_name=collection,
            strategy=strategy_enum,
        )

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
                            console.print(f"  Description: {extracted_metadata.description}")
                        if extracted_metadata.author:
                            console.print(f"  Author: {extracted_metadata.author}")
                        if extracted_metadata.version:
                            console.print(f"  Version: {extracted_metadata.version}")
                        if extracted_metadata.tags:
                            console.print(f"  Tags: {', '.join(extracted_metadata.tags)}")
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
# Entry Point
# ====================


if __name__ == "__main__":
    sys.exit(main())
