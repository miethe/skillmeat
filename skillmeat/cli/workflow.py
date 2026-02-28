"""CLI command group for workflow management.

Exposes the ``skillmeat workflow`` sub-command tree.  Individual subcommands
are implemented in later batches (CLI-4.2 … CLI-4.11); this module provides
the group skeleton so the command is loadable and self-documenting today.
"""

from __future__ import annotations

import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console(force_terminal=True, legacy_windows=False)


# ---------------------------------------------------------------------------
# Feature-flag guard
# ---------------------------------------------------------------------------


def _workflow_engine_enabled() -> bool:
    """Return True when the workflow engine feature flag is enabled.

    Reads the ``SKILLMEAT_WORKFLOW_ENGINE_ENABLED`` environment variable first
    (mirrors ``APISettings``), then falls back to the ``APISettings`` singleton
    so the check works without starting the API server.

    Returns:
        True when the workflow engine is enabled (the default).
    """
    env_val = os.environ.get("SKILLMEAT_WORKFLOW_ENGINE_ENABLED", "").strip().lower()
    if env_val in ("0", "false", "no", "off"):
        return False
    if env_val in ("1", "true", "yes", "on"):
        return True

    # Fall back to the API settings singleton (reads .env, config, etc.)
    try:
        from skillmeat.api.config import get_settings

        return get_settings().workflow_engine_enabled
    except Exception:
        # If the API settings layer is unavailable, default to enabled.
        return True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _print_issue(level: str, issue: object) -> None:
    """Print a single ValidationIssue with Rich styling.

    Handles both structured ``ValidationIssue`` dataclass instances (which have
    ``category``, ``message``, ``stage_id``, and ``field`` attributes) and plain
    string fallbacks so callers never need to type-guard.
    """
    if isinstance(issue, str):
        prefix = "[yellow]Warning:[/yellow]" if level == "warning" else "[red]Error:[/red]"
        console.print(f"  {prefix} {issue}")
        return

    # Structured ValidationIssue
    category = getattr(issue, "category", "unknown")
    message = getattr(issue, "message", str(issue))
    stage_id = getattr(issue, "stage_id", None)
    field = getattr(issue, "field", None)

    if level == "warning":
        label = "[yellow]Warning[/yellow]"
        bracket_style = "yellow"
    else:
        label = "[red]Error[/red]"
        bracket_style = "red"

    parts: list[str] = [f"  {label} [{bracket_style}]{category}[/{bracket_style}]"]
    if stage_id:
        parts.append(f"[dim]stage={stage_id!r}[/dim]")
    if field:
        parts.append(f"[dim]field={field!r}[/dim]")
    parts.append(message)

    console.print(" ".join(parts))


# ---------------------------------------------------------------------------
# Group definition
# ---------------------------------------------------------------------------


@click.group(name="workflow")
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    hidden=True,
    help="Enable debug output for workflow commands.",
)
@click.pass_context
def workflow_cli(ctx: click.Context, debug: bool) -> None:
    """Manage and execute SkillMeat workflows.

    Workflows are multi-stage, agent-driven pipelines defined in YAML.
    Use subcommands to create, validate, plan, and run workflows, then
    inspect execution history and handle approval gates.

    Examples:

      skillmeat workflow create ./my-workflow.yaml   # Import + store workflow
      skillmeat workflow list                        # List stored workflows
      skillmeat workflow show my-workflow            # Inspect definition
      skillmeat workflow validate ./my-workflow.yaml # Lint without importing
      skillmeat workflow plan my-workflow            # Preview execution plan
      skillmeat workflow run my-workflow             # Execute a workflow
      skillmeat workflow runs my-workflow            # List past executions
      skillmeat workflow approve <run-id> <stage>   # Approve a paused stage
      skillmeat workflow cancel <run-id>             # Cancel a running workflow
    """
    ctx.ensure_object(dict)
    ctx.obj["workflow_debug"] = debug

    # Feature-flag guard — applied at the group level so every subcommand
    # is gated automatically without repeating the check in each handler.
    # Allow ``--help`` to pass through so users can still see the command tree.
    if ctx.invoked_subcommand is not None and not _workflow_engine_enabled():
        console.print(
            "[yellow]Workflow engine is coming soon.[/yellow] "
            "Enable it by setting SKILLMEAT_WORKFLOW_ENGINE_ENABLED=true."
        )
        sys.exit(0)


# ---------------------------------------------------------------------------
# Subcommand stubs (CLI-4.2 … CLI-4.11 will replace these bodies)
# ---------------------------------------------------------------------------


@workflow_cli.command(name="create")
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
@click.option("--name", default=None, help="Override the workflow name from the YAML.")
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite an existing workflow with the same name.",
)
@click.pass_context
def create(ctx: click.Context, path: str, name: str, force: bool) -> None:
    """Import a workflow YAML file into the collection.

    Reads PATH, validates the YAML schema, and stores the workflow definition
    in both the filesystem collection (~/.skillmeat/collection/workflows/) and
    the DB cache.

    Examples:

      skillmeat workflow create ./my-workflow.yaml

      skillmeat workflow create ./my-workflow.yaml --name custom-name

      skillmeat workflow create ./my-workflow.yaml --force
    """
    from skillmeat.core.artifact import Artifact, ArtifactMetadata
    from skillmeat.core.artifact_detection import ArtifactType
    from skillmeat.core.collection import CollectionManager
    from skillmeat.core.workflow.exceptions import (
        WorkflowError,
        WorkflowParseError,
        WorkflowValidationError,
    )
    from skillmeat.core.workflow.service import WorkflowService

    yaml_path = Path(path).resolve()
    debug = ctx.obj.get("workflow_debug", False) if ctx.obj else False

    # -----------------------------------------------------------------------
    # Step 1: Read and validate the YAML via WorkflowService
    # -----------------------------------------------------------------------
    console.print(f"[cyan]Reading workflow definition from:[/cyan] {yaml_path}")

    try:
        yaml_content = yaml_path.read_text(encoding="utf-8")
    except OSError as exc:
        console.print(f"[red]Error:[/red] Cannot read file: {exc}")
        sys.exit(1)

    # Validate via the service (parse + schema + DAG + expression checks)
    svc = WorkflowService()

    try:
        validation_result = svc.validate(yaml_content, is_yaml=True)
    except WorkflowError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)

    # Show warnings even on success
    if validation_result.warnings:
        for warn in validation_result.warnings:
            console.print(f"  [yellow]Warning:[/yellow] {warn}")

    if not validation_result.valid:
        console.print("[red]Workflow validation failed:[/red]")
        for err in validation_result.errors:
            console.print(f"  [red]-[/red] {err}")
        sys.exit(1)

    # -----------------------------------------------------------------------
    # Step 2: Parse the workflow to extract metadata for storage
    # -----------------------------------------------------------------------
    try:
        import yaml as _yaml

        raw = _yaml.safe_load(yaml_content)
        workflow_meta = raw.get("workflow", {})
        workflow_id_from_yaml = workflow_meta.get("id", yaml_path.stem)
        workflow_name = name or workflow_meta.get("name", workflow_id_from_yaml)
        workflow_version = workflow_meta.get("version", "1.0.0")
        workflow_description = workflow_meta.get("description")
        num_stages = len(raw.get("stages", []))
        tags = workflow_meta.get("tags", [])
    except Exception as exc:
        console.print(f"[red]Error:[/red] Failed to extract workflow metadata: {exc}")
        sys.exit(1)

    # -----------------------------------------------------------------------
    # Step 3: Filesystem — copy YAML to collection/workflows/<name>/
    # -----------------------------------------------------------------------
    collection_mgr = CollectionManager()
    try:
        collection = collection_mgr.load_collection()
        collection_name = collection.name
        collection_path = collection_mgr.config.get_collection_path(collection_name)
    except Exception as exc:
        console.print(f"[red]Error:[/red] Could not load collection: {exc}")
        sys.exit(1)

    workflows_dir = collection_path / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)

    # Use the CLI name override or YAML workflow name as the filesystem slug
    fs_name = workflow_name.replace(" ", "-").lower()
    artifact_dir = workflows_dir / fs_name

    # Handle existing artifact on filesystem
    if artifact_dir.exists():
        if force:
            shutil.rmtree(artifact_dir)
            console.print(f"[dim]Removed existing workflow at {artifact_dir}[/dim]")
        else:
            # Check if this name already exists in the manifest
            existing = collection.find_artifact(fs_name, ArtifactType.WORKFLOW)
            if existing:
                console.print(
                    f"[red]Error:[/red] Workflow '{fs_name}' already exists in the collection. "
                    "Use --force to overwrite."
                )
                sys.exit(1)

    # Create artifact directory and copy the YAML file
    artifact_dir.mkdir(parents=True, exist_ok=True)
    dest_yaml = artifact_dir / yaml_path.name
    shutil.copy2(yaml_path, dest_yaml)

    if debug:
        console.print(f"[dim]Stored workflow YAML at: {dest_yaml}[/dim]")

    # -----------------------------------------------------------------------
    # Step 4: Update the collection manifest
    # -----------------------------------------------------------------------
    # Remove any existing entry for this workflow name (--force path)
    if force:
        existing_in_manifest = collection.find_artifact(fs_name, ArtifactType.WORKFLOW)
        if existing_in_manifest:
            collection.remove_artifact(fs_name, ArtifactType.WORKFLOW)

    artifact = Artifact(
        name=fs_name,
        type=ArtifactType.WORKFLOW,
        path=str(artifact_dir.relative_to(collection_path)),
        origin="local",
        metadata=ArtifactMetadata(description=workflow_description),
        added=datetime.utcnow(),
        tags=tags,
    )
    try:
        collection.add_artifact(artifact)
    except ValueError as exc:
        # Duplicate guard (shouldn't reach here after --force handling above)
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)

    collection_mgr.save_collection(collection)

    # -----------------------------------------------------------------------
    # Step 5: Persist to DB via WorkflowService
    # -----------------------------------------------------------------------
    try:
        # Check for existing record and handle --force
        existing_records = svc.list()
        existing_dto = next((w for w in existing_records if w.name == workflow_name), None)

        if existing_dto:
            if force:
                dto = svc.update(existing_dto.id, yaml_content)
            else:
                console.print(
                    f"[red]Error:[/red] A workflow named '{workflow_name}' already exists in "
                    "the database. Use --force to overwrite."
                )
                sys.exit(1)
        else:
            dto = svc.create(yaml_content=yaml_content, project_id=collection_name)
    except WorkflowParseError as exc:
        console.print(f"[red]Parse error:[/red] {exc}")
        sys.exit(1)
    except WorkflowValidationError as exc:
        console.print(f"[red]Validation error:[/red] {exc}")
        sys.exit(1)
    except WorkflowError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)

    # -----------------------------------------------------------------------
    # Step 6: Rich success output
    # -----------------------------------------------------------------------
    console.print()
    console.print(f"[green]Workflow imported successfully.[/green]")
    console.print()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="bold")
    table.add_column("Value")

    table.add_row("Name", workflow_name)
    table.add_row("Version", workflow_version)
    table.add_row("Stages", str(num_stages))
    table.add_row("DB ID", dto.id)
    table.add_row("Collection", collection_name)
    table.add_row("Path", str(artifact_dir))
    if tags:
        table.add_row("Tags", ", ".join(tags))
    if workflow_description:
        table.add_row("Description", workflow_description)

    console.print(table)
    console.print()


@workflow_cli.command(name="list")
@click.option(
    "--status",
    default=None,
    help="Filter by workflow status (e.g. draft, active, archived).",
)
@click.option("--tag", default=None, help="Filter by tag.")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def list_workflows(ctx: click.Context, status: str, tag: str, output_format: str) -> None:
    """List workflows stored in the collection.

    Queries all workflow definitions from the DB cache and displays them as a
    Rich table (default) or JSON.  Use --status and --tag to narrow results.

    Examples:

      skillmeat workflow list

      skillmeat workflow list --status active

      skillmeat workflow list --tag ci --format json
    """
    import json as _json

    from skillmeat.core.workflow.exceptions import WorkflowError
    from skillmeat.core.workflow.service import WorkflowService

    try:
        svc = WorkflowService()
        # Fetch up to 500 records; pagination footer shown when > 50 returned.
        workflows = svc.list(limit=500)
    except WorkflowError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Error:[/red] Failed to query workflows: {exc}")
        sys.exit(1)

    # -----------------------------------------------------------------------
    # Client-side filtering
    # -----------------------------------------------------------------------
    if status is not None:
        workflows = [w for w in workflows if w.status == status]

    if tag is not None:
        workflows = [w for w in workflows if tag in w.tags]

    # -----------------------------------------------------------------------
    # Empty state
    # -----------------------------------------------------------------------
    if not workflows:
        if status or tag:
            parts: list[str] = []
            if status:
                parts.append(f"status={status!r}")
            if tag:
                parts.append(f"tag={tag!r}")
            console.print(
                f"[dim]No workflows found matching {', '.join(parts)}.[/dim]"
            )
        else:
            console.print(
                "[dim]No workflows found. Use [bold]skillmeat workflow create[/bold]"
                " to import a workflow.[/dim]"
            )
        return

    # -----------------------------------------------------------------------
    # JSON output
    # -----------------------------------------------------------------------
    if output_format == "json":
        payload = [
            {
                "id": w.id,
                "name": w.name,
                "version": w.version,
                "stages": len(w.stages),
                "status": w.status,
                "tags": w.tags,
                "description": w.description,
                "project_id": w.project_id,
                "updated_at": w.updated_at.isoformat() if w.updated_at else None,
                "created_at": w.created_at.isoformat() if w.created_at else None,
            }
            for w in workflows
        ]
        console.print_json(_json.dumps(payload))
        return

    # -----------------------------------------------------------------------
    # Rich table output
    # -----------------------------------------------------------------------
    table = Table(
        show_header=True,
        header_style="bold cyan",
        show_lines=False,
        box=None,
        padding=(0, 1),
    )
    table.add_column("Name", style="bold", no_wrap=True)
    table.add_column("Version", style="dim", no_wrap=True)
    table.add_column("Stages", justify="right", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Tags")
    table.add_column("Updated", style="dim", no_wrap=True)

    _STATUS_STYLES: dict[str, str] = {
        "active": "green",
        "draft": "yellow",
        "archived": "dim",
    }

    for w in workflows:
        status_style = _STATUS_STYLES.get(w.status, "white")
        status_cell = f"[{status_style}]{w.status}[/{status_style}]"

        tags_cell = ", ".join(w.tags) if w.tags else "[dim]-[/dim]"

        if w.updated_at:
            updated_cell = w.updated_at.strftime("%Y-%m-%d %H:%M")
        else:
            updated_cell = "-"

        table.add_row(
            w.name,
            w.version,
            str(len(w.stages)),
            status_cell,
            tags_cell,
            updated_cell,
        )

    console.print(table)

    # Pagination footer when many results were returned
    total = len(workflows)
    if total > 50:
        console.print(
            f"\n[dim]Showing {total} workflow(s).[/dim]"
        )


@workflow_cli.command(name="show")
@click.argument("name")
@click.pass_context
def show(ctx: click.Context, name: str) -> None:
    """Display a workflow definition, its stages, and last execution.

    Looks up the workflow named NAME from the DB, prints its metadata and
    stage table, then shows a summary of the most recent execution if one
    exists.

    Examples:

      skillmeat workflow show my-workflow

      skillmeat workflow show code-review-pipeline
    """
    from rich.panel import Panel
    from rich.text import Text

    from skillmeat.core.workflow.exceptions import WorkflowError
    from skillmeat.core.workflow.execution_service import WorkflowExecutionService
    from skillmeat.core.workflow.service import WorkflowService

    debug = ctx.obj.get("workflow_debug", False) if ctx.obj else False

    # ------------------------------------------------------------------
    # Step 1: Look up the workflow by name.
    # ------------------------------------------------------------------
    try:
        svc = WorkflowService()
        workflows = svc.list(limit=500)
    except WorkflowError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Error:[/red] Failed to query workflows: {exc}")
        sys.exit(1)

    dto = next((w for w in workflows if w.name == name), None)
    if dto is None:
        console.print(f"[red]Error:[/red] Workflow '{name}' not found.")
        console.print(
            "[dim]Use [bold]skillmeat workflow list[/bold] to see available workflows.[/dim]"
        )
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 2: Metadata panel.
    # ------------------------------------------------------------------
    _STATUS_STYLES: dict[str, str] = {
        "active": "green",
        "draft": "yellow",
        "archived": "dim",
    }
    status_style = _STATUS_STYLES.get(dto.status, "white")

    meta_table = Table(show_header=False, box=None, padding=(0, 2))
    meta_table.add_column("Field", style="bold cyan", no_wrap=True)
    meta_table.add_column("Value")

    meta_table.add_row("Name", dto.name)
    meta_table.add_row("Version", dto.version)
    meta_table.add_row(
        "Status",
        Text(dto.status, style=status_style),
    )
    meta_table.add_row("Stages", str(len(dto.stages)))
    if dto.description:
        meta_table.add_row("Description", dto.description)
    if dto.tags:
        meta_table.add_row("Tags", ", ".join(dto.tags))
    if dto.project_id:
        meta_table.add_row("Project", dto.project_id)
    meta_table.add_row(
        "Created",
        dto.created_at.strftime("%Y-%m-%d %H:%M UTC") if dto.created_at else "-",
    )
    meta_table.add_row(
        "Updated",
        dto.updated_at.strftime("%Y-%m-%d %H:%M UTC") if dto.updated_at else "-",
    )
    if debug:
        meta_table.add_row("DB ID", dto.id)

    console.print()
    console.print(Panel(meta_table, title="[bold]Workflow Definition[/bold]", expand=False))

    # ------------------------------------------------------------------
    # Step 3: Stages table.
    # ------------------------------------------------------------------
    if dto.stages:
        stages_table = Table(
            show_header=True,
            header_style="bold cyan",
            show_lines=False,
            box=None,
            padding=(0, 1),
        )
        stages_table.add_column("#", justify="right", style="dim", no_wrap=True)
        stages_table.add_column("Stage Name", style="bold", no_wrap=True)
        stages_table.add_column("Type", no_wrap=True)
        stages_table.add_column("Depends On")
        stages_table.add_column("Timeout", justify="right", no_wrap=True)

        _TYPE_STYLES: dict[str, str] = {
            "agent": "blue",
            "gate": "magenta",
            "fan_out": "cyan",
        }

        for stage in dto.stages:
            type_style = _TYPE_STYLES.get(stage.stage_type, "white")
            type_cell = Text(stage.stage_type, style=type_style)

            depends_cell = (
                ", ".join(stage.depends_on) if stage.depends_on else "[dim]-[/dim]"
            )

            # Extract timeout from roles dict if present.
            timeout_cell = "-"
            if stage.roles and isinstance(stage.roles, dict):
                raw_timeout = stage.roles.get("timeout_seconds")
                if raw_timeout is not None:
                    timeout_cell = f"{raw_timeout}s"

            stages_table.add_row(
                str(stage.order_index + 1),
                stage.name,
                type_cell,
                depends_cell,
                timeout_cell,
            )

        console.print()
        console.print(Panel(stages_table, title="[bold]Stages[/bold]", expand=False))
    else:
        console.print()
        console.print("[dim]No stages defined.[/dim]")

    # ------------------------------------------------------------------
    # Step 4: Last execution summary.
    # ------------------------------------------------------------------
    try:
        exec_svc = WorkflowExecutionService()
        executions = exec_svc.list_executions(workflow_id=dto.id, limit=1)
        last_exec = executions[0] if executions else None
    except Exception as exc:  # noqa: BLE001
        # Non-fatal: execution history is informational.
        if debug:
            console.print(f"[dim]Could not fetch execution history: {exc}[/dim]")
        last_exec = None

    if last_exec is not None:
        _EXEC_STATUS_STYLES: dict[str, str] = {
            "completed": "green",
            "failed": "red",
            "running": "cyan",
            "paused": "yellow",
            "pending": "dim",
            "cancelled": "dim",
        }
        exec_status_style = _EXEC_STATUS_STYLES.get(last_exec.status, "white")

        exec_table = Table(show_header=False, box=None, padding=(0, 2))
        exec_table.add_column("Field", style="bold cyan", no_wrap=True)
        exec_table.add_column("Value")

        exec_table.add_row("Run ID", last_exec.id)
        exec_table.add_row(
            "Status",
            Text(last_exec.status, style=exec_status_style),
        )
        exec_table.add_row(
            "Started",
            last_exec.started_at.strftime("%Y-%m-%d %H:%M UTC")
            if last_exec.started_at
            else "-",
        )

        # Compute duration from started_at → completed_at.
        if last_exec.started_at and last_exec.completed_at:
            delta = last_exec.completed_at - last_exec.started_at
            total_seconds = int(delta.total_seconds())
            if total_seconds < 60:
                duration_str = f"{total_seconds}s"
            else:
                minutes, seconds = divmod(total_seconds, 60)
                duration_str = f"{minutes}m {seconds}s"
            exec_table.add_row("Duration", duration_str)
        elif last_exec.started_at and last_exec.status in ("running", "paused"):
            exec_table.add_row("Duration", "[dim]in progress[/dim]")
        else:
            exec_table.add_row("Duration", "-")

        console.print()
        console.print(
            Panel(exec_table, title="[bold]Last Execution[/bold]", expand=False)
        )
    else:
        console.print()
        console.print("[dim]No executions recorded for this workflow.[/dim]")

    console.print()


@workflow_cli.command(name="validate")
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Treat warnings as errors (exit code 1 when any warnings are present).",
)
@click.pass_context
def validate(ctx: click.Context, path: str, strict: bool) -> None:
    """Validate a workflow YAML file without importing it.

    Parses and lints the YAML at PATH against the workflow schema, running
    all static analysis passes (schema, expressions, DAG, artifact format).
    The collection is never modified.

    Exit code 0 on success; 1 when errors (or warnings with --strict) are found.

    Examples:

      skillmeat workflow validate ./my-workflow.yaml

      skillmeat workflow validate ./my-workflow.yaml --strict
    """
    from skillmeat.core.workflow.exceptions import WorkflowError
    from skillmeat.core.workflow.service import WorkflowService

    yaml_path = Path(path).resolve()
    debug = ctx.obj.get("workflow_debug", False) if ctx.obj else False

    # -----------------------------------------------------------------------
    # Step 1: Read the YAML file.
    # -----------------------------------------------------------------------
    try:
        yaml_content = yaml_path.read_text(encoding="utf-8")
    except OSError as exc:
        console.print(f"[red]Error:[/red] Cannot read file: {exc}")
        sys.exit(1)

    if debug:
        console.print(f"[dim]Validating: {yaml_path}[/dim]")

    # -----------------------------------------------------------------------
    # Step 2: Run full validation via WorkflowService (no DB writes).
    # -----------------------------------------------------------------------
    try:
        svc = WorkflowService()
        result = svc.validate(yaml_content, is_yaml=True)
    except WorkflowError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)

    # -----------------------------------------------------------------------
    # Step 3: Extract workflow name and stage count for the success summary.
    # -----------------------------------------------------------------------
    workflow_name: str = yaml_path.stem
    num_stages: int = 0
    try:
        import yaml as _yaml

        raw = _yaml.safe_load(yaml_content)
        if isinstance(raw, dict):
            wf_meta = raw.get("workflow", {})
            workflow_name = wf_meta.get("name") or wf_meta.get("id") or yaml_path.stem
            num_stages = len(raw.get("stages", []))
    except Exception:  # noqa: BLE001
        pass  # non-fatal — name/count are cosmetic

    # -----------------------------------------------------------------------
    # Step 4: Determine effective validity (--strict promotes warnings).
    # -----------------------------------------------------------------------
    effective_errors = list(result.errors)
    if strict and result.warnings:
        effective_errors.extend(result.warnings)

    is_valid = len(effective_errors) == 0

    # -----------------------------------------------------------------------
    # Step 5: Print output.
    # -----------------------------------------------------------------------
    if is_valid:
        console.print(
            f"[green]✓[/green] Valid workflow: [bold]{workflow_name}[/bold] ({num_stages} stage{'s' if num_stages != 1 else ''})"
        )
        # Print any non-promoted warnings even on success.
        if result.warnings and not strict:
            console.print()
            for warn in result.warnings:
                _print_issue("warning", warn)
    else:
        console.print(
            f"[red]✗[/red] Workflow validation failed: [bold]{yaml_path.name}[/bold]"
        )
        console.print()
        for issue in effective_errors:
            _print_issue("error", issue)

        # If --strict is what promoted warnings to errors, show a note.
        if strict and result.warnings and not result.errors:
            console.print()
            console.print(
                f"[dim]({len(result.warnings)} warning(s) treated as errors due to --strict)[/dim]"
            )
        sys.exit(1)


@workflow_cli.command(name="plan")
@click.argument("name")
@click.option(
    "--param",
    "params",
    multiple=True,
    metavar="KEY=VALUE",
    help=(
        "Workflow parameter override in KEY=VALUE format. "
        "Repeat to pass multiple parameters."
    ),
)
@click.pass_context
def plan(ctx: click.Context, name: str, params: tuple) -> None:
    """Preview the execution plan for a workflow without running it.

    Resolves parameters, computes the parallel execution batches via topological
    sort, and displays the plan as a Rich tree.  No execution happens.

    Exit code 0 on success; 1 on error or validation failure.

    Examples:

      skillmeat workflow plan my-workflow

      skillmeat workflow plan my-workflow --param feature=auth-v2

      skillmeat workflow plan my-workflow --param feature=auth-v2 --param env=prod
    """
    from rich.panel import Panel
    from rich.text import Text
    from rich.tree import Tree

    from skillmeat.core.workflow.exceptions import (
        WorkflowError,
        WorkflowNotFoundError,
        WorkflowValidationError,
    )
    from skillmeat.core.workflow.service import WorkflowService

    debug = ctx.obj.get("workflow_debug", False) if ctx.obj else False

    # -----------------------------------------------------------------------
    # Step 1: Parse --param key=val pairs.
    # -----------------------------------------------------------------------
    parameters: dict = {}
    for raw in params:
        if "=" not in raw:
            console.print(
                f"[red]Error:[/red] Invalid --param format: {raw!r}. "
                "Expected KEY=VALUE."
            )
            sys.exit(1)
        key, _, value = raw.partition("=")
        key = key.strip()
        if not key:
            console.print(
                f"[red]Error:[/red] Empty key in --param: {raw!r}."
            )
            sys.exit(1)
        parameters[key] = value

    # -----------------------------------------------------------------------
    # Step 2: Look up workflow by name from DB.
    # -----------------------------------------------------------------------
    try:
        svc = WorkflowService()
        workflows = svc.list(limit=500)
    except WorkflowError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Error:[/red] Failed to query workflows: {exc}")
        sys.exit(1)

    dto = next((w for w in workflows if w.name == name), None)
    if dto is None:
        console.print(f"[red]Error:[/red] Workflow '{name}' not found.")
        console.print(
            "[dim]Use [bold]skillmeat workflow list[/bold] to see available workflows.[/dim]"
        )
        sys.exit(1)

    # -----------------------------------------------------------------------
    # Step 3: Generate the execution plan via SVC-3.3.
    # -----------------------------------------------------------------------
    try:
        execution_plan = svc.plan(dto.id, parameters=parameters)
    except WorkflowNotFoundError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)
    except WorkflowValidationError as exc:
        console.print(f"[red]Validation error:[/red] {exc}")
        sys.exit(1)
    except WorkflowError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Error:[/red] Failed to generate plan: {exc}")
        if debug:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)

    # -----------------------------------------------------------------------
    # Step 4: Display validation warnings (plan was generated, so it's valid).
    # -----------------------------------------------------------------------
    if execution_plan.validation.warnings:
        for warn in execution_plan.validation.warnings:
            _print_issue("warning", warn)
        console.print()

    # -----------------------------------------------------------------------
    # Step 5: Display plan header.
    # -----------------------------------------------------------------------
    total_stages = sum(len(b.stages) for b in execution_plan.batches)
    header_table = Table(show_header=False, box=None, padding=(0, 2))
    header_table.add_column("Field", style="bold cyan", no_wrap=True)
    header_table.add_column("Value")

    header_table.add_row("Workflow", execution_plan.workflow_name)
    header_table.add_row("Version", execution_plan.workflow_version)
    header_table.add_row("Batches", str(len(execution_plan.batches)))
    header_table.add_row("Stages", str(total_stages))

    if execution_plan.parameters:
        param_str = ", ".join(
            f"{k}={v!r}" for k, v in sorted(execution_plan.parameters.items())
        )
        header_table.add_row("Parameters", param_str)
    else:
        header_table.add_row("Parameters", "[dim](none)[/dim]")

    console.print()
    console.print(Panel(header_table, title="[bold]Execution Plan[/bold]", expand=False))
    console.print()

    # -----------------------------------------------------------------------
    # Step 6: Build Rich tree for each batch.
    # -----------------------------------------------------------------------
    _TYPE_STYLES: dict[str, str] = {
        "agent": "blue",
        "gate": "magenta",
        "fan_out": "cyan",
    }

    for batch in execution_plan.batches:
        batch_num = batch.index + 1  # 1-based

        if batch.index == 0:
            batch_label = f"[bold]Batch {batch_num}[/bold] [dim](parallel)[/dim]"
        else:
            parallel_label = "parallel" if len(batch.stages) > 1 else "sequential"
            batch_label = (
                f"[bold]Batch {batch_num}[/bold] "
                f"[dim]({parallel_label}, after Batch {batch_num - 1})[/dim]"
            )

        tree = Tree(batch_label)

        for ps in batch.stages:
            type_style = _TYPE_STYLES.get(ps.stage_type, "white")
            stage_label = (
                f"[bold]{ps.name}[/bold]"
                f"  [{type_style}]{ps.stage_type}[/{type_style}]"
                f"  [dim]pending[/dim]"
            )
            stage_node = tree.add(stage_label)

            # Stage ID (always shown)
            stage_node.add(f"[dim]id:[/dim] {ps.stage_id}")

            # Depends on
            if ps.depends_on:
                stage_node.add(f"[dim]depends_on:[/dim] {', '.join(ps.depends_on)}")

            if ps.stage_type == "gate":
                if ps.gate_approvers:
                    stage_node.add(
                        f"[dim]approvers:[/dim] {', '.join(ps.gate_approvers)}"
                    )
                if ps.gate_timeout:
                    stage_node.add(f"[dim]timeout:[/dim] {ps.gate_timeout}")
            else:
                # Agent stage details
                if ps.primary_artifact:
                    artifact_str = ps.primary_artifact
                    if ps.model:
                        artifact_str += f"  [dim]({ps.model})[/dim]"
                    stage_node.add(f"[dim]agent:[/dim] {artifact_str}")

                if ps.tools:
                    stage_node.add(f"[dim]tools:[/dim] {', '.join(ps.tools)}")

                if ps.inputs:
                    inputs_node = stage_node.add("[dim]inputs:[/dim]")
                    for inp_name, source in ps.inputs.items():
                        inputs_node.add(
                            f"[cyan]{inp_name}[/cyan] [dim]<-[/dim] {source}"
                        )

                if ps.outputs:
                    stage_node.add(f"[dim]outputs:[/dim] {', '.join(ps.outputs)}")

                if ps.context_modules:
                    stage_node.add(
                        f"[dim]context:[/dim] {', '.join(ps.context_modules)}"
                    )

                if ps.condition:
                    stage_node.add(f"[dim]condition:[/dim] {ps.condition}")

                if ps.timeout:
                    stage_node.add(f"[dim]timeout:[/dim] {ps.timeout}")

        console.print(tree)
        console.print()

    # -----------------------------------------------------------------------
    # Step 7: Footer — estimated time.
    # -----------------------------------------------------------------------
    from skillmeat.core.workflow.planner import _format_seconds

    estimated = _format_seconds(execution_plan.estimated_timeout_seconds)
    console.print(f"[dim]Estimated total time:[/dim] [bold]{estimated}[/bold]")
    console.print()


@workflow_cli.command(name="run")
@click.argument("name")
@click.option(
    "--param",
    "params",
    multiple=True,
    metavar="KEY=VALUE",
    help=(
        "Workflow parameter override in KEY=VALUE format. "
        "Repeat to pass multiple parameters."
    ),
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show the execution plan without running it.",
)
@click.pass_context
def run(ctx: click.Context, name: str, params: tuple, dry_run: bool) -> None:
    """Execute a workflow by name with Rich live progress display.

    Looks up the workflow by NAME, validates it, and runs all stages in
    topological order.  Progress is shown live: each stage is tracked with
    its current status (pending / running / done / failed).  On completion
    a summary table is printed.

    Use --dry-run to preview the execution plan without running anything
    (equivalent to ``skillmeat workflow plan``).

    Examples:

      skillmeat workflow run my-workflow

      skillmeat workflow run my-workflow --param env=prod --param feature=auth

      skillmeat workflow run my-workflow --dry-run
    """
    import threading
    import time

    from rich.live import Live
    from rich.panel import Panel
    from rich.spinner import Spinner
    from rich.table import Table
    from rich.text import Text
    from rich.tree import Tree

    from skillmeat.core.workflow.exceptions import (
        WorkflowError,
        WorkflowNotFoundError,
        WorkflowValidationError,
    )
    from skillmeat.core.workflow.execution_service import WorkflowExecutionService
    from skillmeat.core.workflow.service import WorkflowService

    debug = ctx.obj.get("workflow_debug", False) if ctx.obj else False

    # -----------------------------------------------------------------------
    # Step 1: Parse --param key=val pairs.
    # -----------------------------------------------------------------------
    parameters: dict = {}
    for raw in params:
        if "=" not in raw:
            console.print(
                f"[red]Error:[/red] Invalid --param format: {raw!r}. "
                "Expected KEY=VALUE."
            )
            sys.exit(1)
        key, _, value = raw.partition("=")
        key = key.strip()
        if not key:
            console.print(f"[red]Error:[/red] Empty key in --param: {raw!r}.")
            sys.exit(1)
        parameters[key] = value

    # -----------------------------------------------------------------------
    # Step 2: Look up workflow by name from DB.
    # -----------------------------------------------------------------------
    try:
        svc = WorkflowService()
        workflows = svc.list(limit=500)
    except WorkflowError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Error:[/red] Failed to query workflows: {exc}")
        sys.exit(1)

    dto = next((w for w in workflows if w.name == name), None)
    if dto is None:
        console.print(f"[red]Error:[/red] Workflow '{name}' not found.")
        console.print(
            "[dim]Use [bold]skillmeat workflow list[/bold] to see available workflows.[/dim]"
        )
        sys.exit(1)

    # -----------------------------------------------------------------------
    # Step 3: --dry-run → show plan (same as `workflow plan`) and exit.
    # -----------------------------------------------------------------------
    if dry_run:
        try:
            execution_plan = svc.plan(dto.id, parameters=parameters)
        except WorkflowNotFoundError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            sys.exit(1)
        except WorkflowValidationError as exc:
            console.print(f"[red]Validation error:[/red] {exc}")
            sys.exit(1)
        except WorkflowError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            sys.exit(1)

        if execution_plan.validation.warnings:
            for warn in execution_plan.validation.warnings:
                _print_issue("warning", warn)
            console.print()

        total_stages = sum(len(b.stages) for b in execution_plan.batches)
        header_table = Table(show_header=False, box=None, padding=(0, 2))
        header_table.add_column("Field", style="bold cyan", no_wrap=True)
        header_table.add_column("Value")
        header_table.add_row("Workflow", execution_plan.workflow_name)
        header_table.add_row("Version", execution_plan.workflow_version)
        header_table.add_row("Batches", str(len(execution_plan.batches)))
        header_table.add_row("Stages", str(total_stages))
        if execution_plan.parameters:
            param_str = ", ".join(
                f"{k}={v!r}" for k, v in sorted(execution_plan.parameters.items())
            )
            header_table.add_row("Parameters", param_str)
        else:
            header_table.add_row("Parameters", "[dim](none)[/dim]")

        console.print()
        console.print(
            Panel(
                header_table,
                title="[bold]Execution Plan (dry-run)[/bold]",
                expand=False,
            )
        )
        console.print()

        _TYPE_STYLES: dict[str, str] = {
            "agent": "blue",
            "gate": "magenta",
            "fan_out": "cyan",
        }
        for batch in execution_plan.batches:
            batch_num = batch.index + 1
            if batch.index == 0:
                batch_label = f"[bold]Batch {batch_num}[/bold] [dim](parallel)[/dim]"
            else:
                parallel_label = "parallel" if len(batch.stages) > 1 else "sequential"
                batch_label = (
                    f"[bold]Batch {batch_num}[/bold] "
                    f"[dim]({parallel_label}, after Batch {batch_num - 1})[/dim]"
                )
            tree = Tree(batch_label)
            for ps in batch.stages:
                type_style = _TYPE_STYLES.get(ps.stage_type, "white")
                stage_label = (
                    f"[bold]{ps.name}[/bold]"
                    f"  [{type_style}]{ps.stage_type}[/{type_style}]"
                    f"  [dim]pending[/dim]"
                )
                tree.add(stage_label)
            console.print(tree)
            console.print()

        from skillmeat.core.workflow.planner import _format_seconds

        estimated = _format_seconds(execution_plan.estimated_timeout_seconds)
        console.print(f"[dim]Estimated total time:[/dim] [bold]{estimated}[/bold]")
        console.print(
            "[dim]Dry-run complete. No execution was started.[/dim]"
        )
        return

    # -----------------------------------------------------------------------
    # Step 4: Start execution.
    # -----------------------------------------------------------------------
    exec_svc = WorkflowExecutionService()

    try:
        execution = exec_svc.start_execution(
            workflow_id=dto.id,
            parameters=parameters,
        )
    except WorkflowNotFoundError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)
    except WorkflowValidationError as exc:
        console.print(f"[red]Validation error:[/red] {exc}")
        sys.exit(1)
    except WorkflowError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Error:[/red] Failed to start execution: {exc}")
        if debug:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)

    execution_id = execution.id
    console.print(
        f"\n[cyan]Starting workflow:[/cyan] [bold]{name}[/bold]  "
        f"[dim](run {execution_id[:8]})[/dim]"
    )
    if parameters:
        param_str = ", ".join(f"{k}={v!r}" for k, v in sorted(parameters.items()))
        console.print(f"[dim]Parameters:[/dim] {param_str}")
    console.print()

    # -----------------------------------------------------------------------
    # Step 5: Build the initial stage status map from the execution record.
    # -----------------------------------------------------------------------
    # stage_id -> {"name": str, "status": str, "type": str, "error": str|None}
    stage_info: dict[str, dict] = {}
    ordered_stage_ids: list[str] = []
    for step in sorted(execution.steps, key=lambda s: s.batch_index):
        if step.stage_id not in stage_info:
            ordered_stage_ids.append(step.stage_id)
        stage_info[step.stage_id] = {
            "name": step.stage_name,
            "status": step.status,
            "type": step.stage_type,
            "error": step.error_message,
        }

    total_stages = len(ordered_stage_ids)

    # -----------------------------------------------------------------------
    # Step 6: Define the Rich renderable for live progress.
    # -----------------------------------------------------------------------
    _STATUS_ICON: dict[str, str] = {
        "pending": "[dim]...[/dim]",
        "running": "[cyan]-->[/cyan]",
        "completed": "[green]OK [/green]",
        "failed": "[red]ERR[/red]",
        "skipped": "[yellow]SKP[/yellow]",
    }
    _TYPE_STYLES_RUN: dict[str, str] = {
        "agent": "blue",
        "gate": "magenta",
        "fan_out": "cyan",
    }

    def _build_progress_table() -> Table:
        done = sum(
            1 for s in stage_info.values() if s["status"] in ("completed", "skipped")
        )
        failed = sum(1 for s in stage_info.values() if s["status"] == "failed")

        t = Table(
            show_header=True,
            header_style="bold cyan",
            box=None,
            padding=(0, 1),
            expand=False,
        )
        t.add_column("", width=3, no_wrap=True)
        t.add_column("Stage", style="bold", no_wrap=True)
        t.add_column("Type", no_wrap=True)
        t.add_column("Status", no_wrap=True)

        for sid in ordered_stage_ids:
            info = stage_info[sid]
            icon = _STATUS_ICON.get(info["status"], "   ")
            type_style = _TYPE_STYLES_RUN.get(info["type"], "white")
            type_cell = Text(info["type"], style=type_style)

            status = info["status"]
            if status == "running":
                status_cell = Text(status, style="cyan")
            elif status == "completed":
                status_cell = Text(status, style="green")
            elif status == "failed":
                status_cell = Text(status, style="red")
            elif status == "skipped":
                status_cell = Text(status, style="yellow")
            else:
                status_cell = Text(status, style="dim")

            t.add_row(icon, info["name"], type_cell, status_cell)

        # Footer row: progress counter.
        t.add_section()
        progress_label = f"[dim]Progress: {done}/{total_stages} stages"
        if failed:
            progress_label += f" ({failed} failed)"
        progress_label += "[/dim]"
        t.add_row("", progress_label, "", "")

        return t

    # -----------------------------------------------------------------------
    # Step 7: Run execution in a background thread; poll events in main thread.
    # -----------------------------------------------------------------------
    result_holder: dict = {"dto": None, "error": None}

    def _run_thread() -> None:
        try:
            result_holder["dto"] = exec_svc.run_execution(execution_id)
        except Exception as exc:  # noqa: BLE001
            result_holder["error"] = exc

    thread = threading.Thread(target=_run_thread, daemon=True)
    thread.start()

    last_seq = 0
    terminal_types = {"execution_completed", "execution_failed"}

    with Live(
        _build_progress_table(),
        console=console,
        refresh_per_second=4,
        transient=False,
    ) as live:
        finished = False
        while not finished:
            # Poll events emitted by the execution service.
            events = exec_svc.get_events(execution_id, after_seq=last_seq)
            for event in events:
                last_seq = event["seq"] + 1
                etype = event["type"]
                data = event.get("data", {})

                if etype == "stage_started":
                    sid = data.get("stage_id", "")
                    if sid in stage_info:
                        stage_info[sid]["status"] = "running"

                elif etype in ("stage_completed", "stage_skipped"):
                    sid = data.get("stage_id", "")
                    if sid in stage_info:
                        stage_info[sid]["status"] = (
                            "completed" if etype == "stage_completed" else "skipped"
                        )

                elif etype == "stage_failed":
                    sid = data.get("stage_id", "")
                    if sid in stage_info:
                        stage_info[sid]["status"] = "failed"
                        stage_info[sid]["error"] = data.get("error")

                if etype in terminal_types:
                    finished = True

            live.update(_build_progress_table())

            # Also stop when the thread finishes (handles edge cases where
            # terminal events may have been missed).
            if not thread.is_alive():
                # One final event drain.
                for event in exec_svc.get_events(execution_id, after_seq=last_seq):
                    etype = event["type"]
                    data = event.get("data", {})
                    if etype == "stage_started":
                        sid = data.get("stage_id", "")
                        if sid in stage_info:
                            stage_info[sid]["status"] = "running"
                    elif etype in ("stage_completed", "stage_skipped"):
                        sid = data.get("stage_id", "")
                        if sid in stage_info:
                            stage_info[sid]["status"] = (
                                "completed" if etype == "stage_completed" else "skipped"
                            )
                    elif etype == "stage_failed":
                        sid = data.get("stage_id", "")
                        if sid in stage_info:
                            stage_info[sid]["status"] = "failed"
                            stage_info[sid]["error"] = data.get("error")
                live.update(_build_progress_table())
                finished = True

            if not finished:
                time.sleep(0.25)

    thread.join(timeout=5)

    # -----------------------------------------------------------------------
    # Step 8: Retrieve final execution DTO.
    # -----------------------------------------------------------------------
    final_exc_error = result_holder.get("error")
    if final_exc_error is not None:
        console.print(f"\n[red]Execution error:[/red] {final_exc_error}")
        if debug:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)

    final_dto = result_holder.get("dto")
    if final_dto is None:
        # Fallback: fetch from DB.
        try:
            final_dto = exec_svc.get_execution(execution_id)
        except Exception as exc:  # noqa: BLE001
            console.print(f"\n[red]Error:[/red] Could not retrieve execution result: {exc}")
            sys.exit(1)

    # -----------------------------------------------------------------------
    # Step 9: Summary table.
    # -----------------------------------------------------------------------
    console.print()

    # Compute duration.
    duration_str = "-"
    if final_dto.started_at and final_dto.completed_at:
        delta = final_dto.completed_at - final_dto.started_at
        total_secs = int(delta.total_seconds())
        if total_secs < 60:
            duration_str = f"{total_secs}s"
        else:
            minutes, seconds = divmod(total_secs, 60)
            duration_str = f"{minutes}m {seconds}s"

    overall_status = final_dto.status
    status_style = {
        "completed": "green",
        "failed": "red",
        "cancelled": "yellow",
    }.get(overall_status, "white")

    summary = Table(show_header=False, box=None, padding=(0, 2))
    summary.add_column("Field", style="bold cyan", no_wrap=True)
    summary.add_column("Value")
    summary.add_row("Run ID", execution_id)
    summary.add_row("Workflow", name)
    summary.add_row(
        "Status",
        Text(overall_status, style=status_style),
    )
    summary.add_row("Duration", duration_str)
    summary.add_row(
        "Stages",
        f"{sum(1 for s in final_dto.steps if s.status in ('completed', 'skipped'))}"
        f"/{total_stages} completed",
    )
    if final_dto.error_message:
        summary.add_row("[red]Error[/red]", final_dto.error_message)

    console.print(
        Panel(
            summary,
            title=(
                f"[bold green]Execution Complete[/bold green]"
                if overall_status == "completed"
                else f"[bold red]Execution {overall_status.title()}[/bold red]"
            ),
            expand=False,
        )
    )

    # Per-stage result table (only when there are interesting details).
    failed_steps = [s for s in final_dto.steps if s.status == "failed"]
    if failed_steps or debug:
        console.print()
        detail = Table(
            show_header=True,
            header_style="bold cyan",
            box=None,
            padding=(0, 1),
        )
        detail.add_column("Stage", style="bold", no_wrap=True)
        detail.add_column("Status", no_wrap=True)
        detail.add_column("Error / Detail")

        for step in sorted(final_dto.steps, key=lambda s: s.batch_index):
            st = step.status
            if st == "completed":
                sc = Text(st, style="green")
            elif st == "failed":
                sc = Text(st, style="red")
            elif st == "skipped":
                sc = Text(st, style="yellow")
            else:
                sc = Text(st, style="dim")

            err_cell = step.error_message or "[dim]-[/dim]"
            detail.add_row(step.stage_name, sc, err_cell)

        console.print(detail)

    console.print()

    # Exit code 1 on failure.
    if overall_status in ("failed", "cancelled"):
        if failed_steps:
            console.print(
                f"[red]Failed stage{'s' if len(failed_steps) > 1 else ''}:[/red] "
                + ", ".join(s.stage_name for s in failed_steps)
            )
        sys.exit(1)


@workflow_cli.command(name="runs")
@click.argument("run_id", required=False, default=None)
@click.option("--workflow", "workflow_name", default=None, help="Filter by workflow name.")
@click.option(
    "--status",
    "filter_status",
    type=click.Choice(["pending", "running", "completed", "failed", "cancelled"]),
    default=None,
    help="Filter by execution status.",
)
@click.option("--logs", is_flag=True, default=False, help="Show log output for stages.")
@click.option("--limit", default=20, show_default=True, help="Maximum rows to show (list mode).")
@click.pass_context
def runs(
    ctx: click.Context,
    run_id: str | None,
    workflow_name: str | None,
    filter_status: str | None,
    logs: bool,
    limit: int,
) -> None:
    """List or inspect workflow executions.

    Without RUN_ID, lists recent executions in a table.  With RUN_ID, shows
    detailed metadata and a per-stage status table for that run.

    Examples:

      skillmeat workflow runs

      skillmeat workflow runs --workflow my-workflow --status failed

      skillmeat workflow runs abc123def456 --logs
    """
    import json as _json  # noqa: PLC0415

    from rich.panel import Panel  # noqa: PLC0415
    from rich.text import Text  # noqa: PLC0415

    from skillmeat.core.workflow.exceptions import (  # noqa: PLC0415
        WorkflowExecutionNotFoundError,
    )
    from skillmeat.core.workflow.execution_service import (  # noqa: PLC0415
        WorkflowExecutionService,
    )

    exec_svc = WorkflowExecutionService()

    # ------------------------------------------------------------------
    # Helper: format a duration from two optional datetimes.
    # ------------------------------------------------------------------
    def _fmt_duration(started_at: object, completed_at: object) -> str:
        if started_at is None:
            return "-"
        end = completed_at or datetime.utcnow()
        total_secs = int((end - started_at).total_seconds())
        if total_secs < 0:
            return "-"
        if total_secs < 60:
            return f"{total_secs}s"
        minutes, seconds = divmod(total_secs, 60)
        return f"{minutes}m {seconds}s"

    # ------------------------------------------------------------------
    # Helper: map status → Rich colour string.
    # ------------------------------------------------------------------
    def _status_style(status: str) -> str:
        return {
            "completed": "green",
            "failed": "red",
            "running": "yellow",
            "pending": "yellow",
            "waiting_for_approval": "cyan",
            "cancelled": "dim",
            "skipped": "yellow",
        }.get(status, "white")

    # =================== Detail view (RUN_ID supplied) ===================
    if run_id is not None:
        try:
            dto = exec_svc.get_execution(run_id)
        except WorkflowExecutionNotFoundError:
            console.print(f"[red]Error:[/red] No execution found with ID {run_id!r}")
            sys.exit(1)
        except Exception as exc:  # noqa: BLE001
            console.print(f"[red]Error:[/red] {exc}")
            sys.exit(1)

        duration_str = _fmt_duration(dto.started_at, dto.completed_at)
        st_style = _status_style(dto.status)

        # --- Metadata panel ---
        meta = Table(show_header=False, box=None, padding=(0, 2))
        meta.add_column("Field", style="bold cyan", no_wrap=True)
        meta.add_column("Value")
        meta.add_row("Run ID", dto.id)
        meta.add_row("Workflow ID", dto.workflow_id)
        meta.add_row("Status", Text(dto.status, style=st_style))
        meta.add_row(
            "Started",
            dto.started_at.strftime("%Y-%m-%d %H:%M:%S UTC") if dto.started_at else "-",
        )
        meta.add_row(
            "Completed",
            dto.completed_at.strftime("%Y-%m-%d %H:%M:%S UTC") if dto.completed_at else "-",
        )
        meta.add_row("Duration", duration_str)
        if dto.error_message:
            meta.add_row("[red]Error[/red]", dto.error_message)
        if dto.parameters:
            meta.add_row("Parameters", _json.dumps(dto.parameters))

        console.print(
            Panel(
                meta,
                title=f"[bold]Execution Detail[/bold] — {dto.id[:12]}",
                expand=False,
            )
        )

        # --- Per-stage table ---
        if dto.steps:
            console.print()
            stage_table = Table(
                show_header=True,
                header_style="bold cyan",
                box=None,
                padding=(0, 1),
            )
            stage_table.add_column("Stage", style="bold", no_wrap=True)
            stage_table.add_column("Type", no_wrap=True)
            stage_table.add_column("Status", no_wrap=True)
            stage_table.add_column("Duration", no_wrap=True)
            if logs:
                stage_table.add_column("Error / Output")

            for step in sorted(dto.steps, key=lambda s: (s.batch_index, s.stage_id)):
                step_dur = _fmt_duration(step.started_at, step.completed_at)
                sc = Text(step.status, style=_status_style(step.status))
                row_args: list[object] = [step.stage_name, step.stage_type, sc, step_dur]
                if logs:
                    detail_cell = step.error_message or (
                        _json.dumps(step.output) if step.output else "[dim]-[/dim]"
                    )
                    row_args.append(detail_cell)
                stage_table.add_row(*[str(a) if not isinstance(a, Text) else a for a in row_args])

            console.print(stage_table)
        else:
            console.print("[dim]No stages recorded for this execution.[/dim]")

        # Non-zero exit for terminal failures.
        if dto.status in ("failed", "cancelled"):
            sys.exit(1)
        return

    # =================== List view (no RUN_ID) ===================
    # Optionally resolve workflow_name → workflow_id for filtering.
    workflow_id_filter: str | None = None
    if workflow_name:
        try:
            from skillmeat.core.workflow.service import WorkflowService  # noqa: PLC0415

            wf_svc = WorkflowService()
            wf_list, _ = wf_svc.list(limit=200)
            matches = [w for w in wf_list if w.name == workflow_name]
            if not matches:
                console.print(
                    f"[red]Error:[/red] No workflow named {workflow_name!r} found."
                )
                sys.exit(1)
            workflow_id_filter = matches[0].id
        except Exception as exc:  # noqa: BLE001
            console.print(f"[red]Error:[/red] Could not look up workflow: {exc}")
            sys.exit(1)

    try:
        executions = exec_svc.list_executions(
            workflow_id=workflow_id_filter,
            status=filter_status,
            limit=limit,
        )
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)

    if not executions:
        console.print("[dim]No executions found.[/dim]")
        return

    list_table = Table(
        show_header=True,
        header_style="bold cyan",
        box=None,
        padding=(0, 1),
    )
    list_table.add_column("Run ID", no_wrap=True)
    list_table.add_column("Workflow ID", no_wrap=True)
    list_table.add_column("Status", no_wrap=True)
    list_table.add_column("Started", no_wrap=True)
    list_table.add_column("Duration", no_wrap=True)

    from rich.text import Text  # noqa: PLC0415, F811

    for exc_dto in executions:
        run_id_short = exc_dto.id[:12]
        wf_short = exc_dto.workflow_id[:12]
        sc = Text(exc_dto.status, style=_status_style(exc_dto.status))
        started_str = (
            exc_dto.started_at.strftime("%Y-%m-%d %H:%M") if exc_dto.started_at else "-"
        )
        dur_str = _fmt_duration(exc_dto.started_at, exc_dto.completed_at)
        list_table.add_row(run_id_short, wf_short, sc, started_str, dur_str)

    console.print(list_table)
    console.print(f"\n[dim]Showing {len(executions)} execution(s). Use a run ID to see details.[/dim]")


@workflow_cli.command(name="approve")
@click.argument("run_id")
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Skip confirmation prompt.",
)
@click.pass_context
def approve(ctx: click.Context, run_id: str, yes: bool) -> None:
    """Approve the gate stage that is waiting for approval in a run.

    RUN_ID is the execution UUID.  The command locates the gate step that is
    in ``waiting_for_approval`` state, confirms with the user (unless --yes),
    and marks it as approved so the execution can continue.

    Examples:

      skillmeat workflow approve abc123def456

      skillmeat workflow approve abc123def456 --yes
    """
    from rich.panel import Panel  # noqa: PLC0415
    from rich.text import Text  # noqa: PLC0415

    from skillmeat.core.workflow.exceptions import (  # noqa: PLC0415
        WorkflowExecutionInvalidStateError,
        WorkflowExecutionNotFoundError,
    )
    from skillmeat.core.workflow.execution_service import (  # noqa: PLC0415
        WorkflowExecutionService,
    )

    exec_svc = WorkflowExecutionService()

    # Fetch execution to find which gate stage is waiting.
    try:
        dto = exec_svc.get_execution(run_id)
    except WorkflowExecutionNotFoundError:
        console.print(f"[red]Error:[/red] No execution found with ID {run_id!r}")
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)

    # Find the gate step currently waiting for approval.
    waiting_steps = [
        s for s in dto.steps
        if s.status == "waiting_for_approval" and s.stage_type == "gate"
    ]
    if not waiting_steps:
        # Broaden search: any step waiting for approval regardless of type.
        waiting_steps = [s for s in dto.steps if s.status == "waiting_for_approval"]

    if not waiting_steps:
        console.print(
            f"[yellow]No gate stage is currently waiting for approval in run {run_id[:12]}.[/yellow]"
        )
        console.print(f"  Execution status: [bold]{dto.status}[/bold]")
        sys.exit(1)

    gate_step = waiting_steps[0]

    console.print(
        Panel(
            f"Run ID:    {run_id}\n"
            f"Gate:      {gate_step.stage_name} (stage_id={gate_step.stage_id!r})\n"
            f"Status:    [cyan]waiting_for_approval[/cyan]",
            title="[bold]Pending Gate Approval[/bold]",
            expand=False,
        )
    )

    if not yes:
        try:
            click.confirm("Approve this gate stage?", abort=True)
        except click.Abort:
            console.print("[dim]Approval cancelled.[/dim]")
            sys.exit(0)

    try:
        step_dto = exec_svc.approve_gate(run_id, gate_step.stage_id)
    except WorkflowExecutionNotFoundError:
        console.print(f"[red]Error:[/red] Execution {run_id!r} not found.")
        sys.exit(1)
    except WorkflowExecutionInvalidStateError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)

    console.print(
        f"[green]Gate approved:[/green] {step_dto.stage_name!r} is now "
        f"{Text(step_dto.status, style='green')}"
    )
    console.print("[dim]The execution will continue to the next stage.[/dim]")


@workflow_cli.command(name="cancel")
@click.argument("run_id")
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Skip confirmation prompt.",
)
@click.pass_context
def cancel(ctx: click.Context, run_id: str, yes: bool) -> None:
    """Cancel a running or pending workflow execution.

    RUN_ID is the execution UUID.  The command confirms with the user (unless
    --yes) then marks all active steps as ``cancelled`` and sets the execution
    status to ``cancelled``.

    Examples:

      skillmeat workflow cancel abc123def456

      skillmeat workflow cancel abc123def456 --yes
    """
    from rich.panel import Panel  # noqa: PLC0415

    from skillmeat.core.workflow.exceptions import (  # noqa: PLC0415
        WorkflowExecutionNotFoundError,
    )
    from skillmeat.core.workflow.execution_service import (  # noqa: PLC0415
        WorkflowExecutionService,
    )

    exec_svc = WorkflowExecutionService()

    # Fetch the execution first to show current state to the user.
    try:
        dto = exec_svc.get_execution(run_id)
    except WorkflowExecutionNotFoundError:
        console.print(f"[red]Error:[/red] No execution found with ID {run_id!r}")
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)

    _already_terminal = {"completed", "failed", "cancelled"}
    if dto.status in _already_terminal:
        console.print(
            f"[yellow]Execution {run_id[:12]} is already in terminal state:[/yellow] "
            f"[bold]{dto.status}[/bold]"
        )
        sys.exit(0)

    console.print(
        Panel(
            f"Run ID:    {run_id}\n"
            f"Status:    [yellow]{dto.status}[/yellow]\n"
            f"Stages:    {len(dto.steps)} step(s)",
            title="[bold]Cancel Execution[/bold]",
            expand=False,
        )
    )

    if not yes:
        try:
            click.confirm(
                f"Cancel execution {run_id[:12]}? This cannot be undone.",
                abort=True,
            )
        except click.Abort:
            console.print("[dim]Cancellation aborted.[/dim]")
            sys.exit(0)

    try:
        cancelled_dto = exec_svc.cancel_execution(run_id)
    except WorkflowExecutionNotFoundError:
        console.print(f"[red]Error:[/red] Execution {run_id!r} not found.")
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)

    active_cancelled = sum(1 for s in cancelled_dto.steps if s.status == "cancelled")
    console.print(
        f"[green]Cancelled:[/green] Execution {run_id[:12]} — "
        f"{active_cancelled} stage(s) marked cancelled."
    )
