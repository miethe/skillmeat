"""CLI command group for workflow management.

Exposes the ``skillmeat workflow`` sub-command tree.  Individual subcommands
are implemented in later batches (CLI-4.2 … CLI-4.11); this module provides
the group skeleton so the command is loadable and self-documenting today.
"""

from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console(force_terminal=True, legacy_windows=False)


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
    "--input",
    "input_json",
    default=None,
    help="JSON string of workflow inputs.",
)
@click.pass_context
def plan(ctx: click.Context, name: str, input_json: str) -> None:
    """Preview the execution plan for a workflow without running it.

    [Not yet implemented — CLI-4.6]
    """
    console.print("[yellow]workflow plan: not yet implemented (CLI-4.6)[/yellow]")


@workflow_cli.command(name="run")
@click.argument("name")
@click.option(
    "--input",
    "input_json",
    default=None,
    help="JSON string of workflow inputs.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Validate and plan without executing.",
)
@click.option(
    "--follow",
    is_flag=True,
    default=False,
    help="Stream execution events to stdout (SSE).",
)
@click.pass_context
def run(ctx: click.Context, name: str, input_json: str, dry_run: bool, follow: bool) -> None:
    """Execute a workflow by name.

    [Not yet implemented — CLI-4.7]
    """
    console.print("[yellow]workflow run: not yet implemented (CLI-4.7)[/yellow]")


@workflow_cli.command(name="runs")
@click.argument("name")
@click.option("--limit", default=10, show_default=True, help="Maximum rows to show.")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def runs(ctx: click.Context, name: str, limit: int, output_format: str) -> None:
    """List past executions of a workflow.

    [Not yet implemented — CLI-4.8]
    """
    console.print("[yellow]workflow runs: not yet implemented (CLI-4.8)[/yellow]")


@workflow_cli.command(name="approve")
@click.argument("run_id")
@click.argument("stage")
@click.option("--comment", default=None, help="Optional approval comment.")
@click.pass_context
def approve(ctx: click.Context, run_id: str, stage: str, comment: str) -> None:
    """Approve a paused stage in a running workflow execution.

    RUN_ID is the execution UUID; STAGE is the stage name that is awaiting
    human approval.

    [Not yet implemented — CLI-4.9]
    """
    console.print("[yellow]workflow approve: not yet implemented (CLI-4.9)[/yellow]")


@workflow_cli.command(name="cancel")
@click.argument("run_id")
@click.option("--reason", default=None, help="Optional cancellation reason.")
@click.pass_context
def cancel(ctx: click.Context, run_id: str, reason: str) -> None:
    """Cancel a running workflow execution.

    [Not yet implemented — CLI-4.10]
    """
    console.print("[yellow]workflow cancel: not yet implemented (CLI-4.10)[/yellow]")
