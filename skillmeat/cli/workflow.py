"""CLI command group for workflow management.

Exposes the ``skillmeat workflow`` sub-command tree.  Individual subcommands
are implemented in later batches (CLI-4.2 … CLI-4.11); this module provides
the group skeleton so the command is loadable and self-documenting today.
"""

from __future__ import annotations

import click
from rich.console import Console

console = Console(force_terminal=True, legacy_windows=False)


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
@click.pass_context
def create(ctx: click.Context, path: str) -> None:
    """Import a workflow YAML file into the collection.

    Reads PATH, validates the YAML schema, and stores the workflow definition
    in both the filesystem collection and the DB cache.

    [Not yet implemented — CLI-4.2]
    """
    console.print("[yellow]workflow create: not yet implemented (CLI-4.2)[/yellow]")


@workflow_cli.command(name="list")
@click.option("--status", default=None, help="Filter by workflow status.")
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

    [Not yet implemented — CLI-4.3]
    """
    console.print("[yellow]workflow list: not yet implemented (CLI-4.3)[/yellow]")


@workflow_cli.command(name="show")
@click.argument("name")
@click.pass_context
def show(ctx: click.Context, name: str) -> None:
    """Display a workflow definition, its stages, and last execution.

    [Not yet implemented — CLI-4.4]
    """
    console.print("[yellow]workflow show: not yet implemented (CLI-4.4)[/yellow]")


@workflow_cli.command(name="validate")
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
@click.pass_context
def validate(ctx: click.Context, path: str) -> None:
    """Validate a workflow YAML file without importing it.

    Parses and lints the YAML at PATH against the workflow schema, reporting
    any errors or warnings without modifying the collection.

    [Not yet implemented — CLI-4.5]
    """
    console.print("[yellow]workflow validate: not yet implemented (CLI-4.5)[/yellow]")


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
