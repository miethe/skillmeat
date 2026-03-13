"""Click command group for artifact activity history.

Provides the ``skillmeat history`` subcommand tree:

    skillmeat history [ARTIFACT_NAME] [--limit N] [--event-type TYPE] [--format table|json]
    skillmeat history --all [--limit N] [--event-type TYPE] [--format table|json]

Activity events are read from the local SQLite cache DB via
:class:`~skillmeat.cache.repository_factory.RepositoryFactory` and the
:class:`~skillmeat.core.bom.history.ArtifactActivityService`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.table import Table

console = Console(force_terminal=True, legacy_windows=False)

_VALID_EVENT_TYPES = ("create", "update", "delete", "deploy", "undeploy", "sync")


def _get_activity_service():
    """Build an ArtifactActivityService backed by the local cache DB."""
    from skillmeat.cache.models import get_session
    from skillmeat.core.bom.history import ArtifactActivityService
    from skillmeat.core.repositories.local_artifact_activity import (
        LocalArtifactActivityRepository,
    )

    default_db_path = str(Path.home() / ".skillmeat" / "cache" / "cache.db")
    session = get_session(default_db_path)
    repo = LocalArtifactActivityRepository(session=session)
    return ArtifactActivityService(repository=repo)


def _format_timestamp(ts) -> str:
    """Return a short ISO-format string or '—' for None."""
    if ts is None:
        return "\u2014"
    try:
        return ts.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(ts)


def _print_table(events, show_artifact_column: bool = False) -> None:
    """Render *events* as a Rich table to the console."""
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("ID", style="dim", justify="right", no_wrap=True)
    if show_artifact_column:
        table.add_column("Artifact", style="bold")
    table.add_column("Event Type", style="magenta")
    table.add_column("Timestamp", style="green")
    table.add_column("Actor", style="yellow")
    table.add_column("Owner Type", style="cyan")
    table.add_column("Content Hash", style="dim", no_wrap=True)

    event_type_colours = {
        "create": "bright_green",
        "update": "bright_yellow",
        "delete": "bright_red",
        "deploy": "bright_blue",
        "undeploy": "orange3",
        "sync": "bright_cyan",
    }

    for event in events:
        colour = event_type_colours.get(event.event_type, "white")
        event_type_cell = f"[{colour}]{event.event_type}[/{colour}]"
        hash_display = (event.content_hash[:12] + "…") if event.content_hash else "\u2014"
        row = [
            str(event.id),
        ]
        if show_artifact_column:
            row.append(event.artifact_id)
        row += [
            event_type_cell,
            _format_timestamp(event.timestamp),
            event.actor_id or "\u2014",
            event.owner_type,
            hash_display,
        ]
        table.add_row(*row)

    console.print(table)


def _print_json(events) -> None:
    """Render *events* as a JSON array to stdout."""
    data: List[dict] = []
    for event in events:
        data.append(event.to_dict())
    click.echo(json.dumps(data, indent=2, default=str))


# ---------------------------------------------------------------------------
# history group
# ---------------------------------------------------------------------------


@click.group("history", invoke_without_command=True)
@click.argument("artifact_name", required=False, default=None, metavar="ARTIFACT_NAME")
@click.option(
    "--all",
    "show_all",
    is_flag=True,
    default=False,
    help="Show activity history for ALL artifacts.",
)
@click.option(
    "--limit",
    "-n",
    default=20,
    show_default=True,
    metavar="N",
    type=click.IntRange(1, 10000),
    help="Maximum number of events to display.",
)
@click.option(
    "--event-type",
    "-e",
    "event_type",
    default=None,
    metavar="TYPE",
    type=click.Choice(list(_VALID_EVENT_TYPES), case_sensitive=False),
    help="Filter events by type (create/update/delete/deploy/undeploy/sync).",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    default="table",
    show_default=True,
    type=click.Choice(["table", "json"], case_sensitive=False),
    help="Output format.",
)
@click.pass_context
def history_group(
    ctx: click.Context,
    artifact_name: Optional[str],
    show_all: bool,
    limit: int,
    event_type: Optional[str],
    output_format: str,
) -> None:
    """Show artifact activity history.

    When ARTIFACT_NAME is provided, display the event log for that specific
    artifact only.  Pass --all to aggregate events across every artifact.

    \b
    Examples:
      skillmeat history my-skill
      skillmeat history my-skill --limit 50 --event-type deploy
      skillmeat history --all --format json
      skillmeat history --all --event-type sync --limit 100
    """
    # If a sub-command was invoked (future extension), let it run.
    if ctx.invoked_subcommand is not None:
        return

    # Validate argument combination.
    if not show_all and not artifact_name:
        console.print(
            "[red]Error:[/red] Provide ARTIFACT_NAME or pass [bold]--all[/bold] "
            "to show history for all artifacts."
        )
        console.print("Run [bold]skillmeat history --help[/bold] for usage.")
        sys.exit(1)

    if show_all and artifact_name:
        console.print(
            "[red]Error:[/red] Cannot specify both ARTIFACT_NAME and [bold]--all[/bold]."
        )
        sys.exit(1)

    # Resolve event_type to lower-case (Choice already validates).
    normalized_event_type = event_type.lower() if event_type else None

    try:
        service = _get_activity_service()
    except Exception as exc:
        console.print(f"[red]Error:[/red] Failed to open the cache database: {exc}")
        sys.exit(1)

    try:
        events = service.list_events(
            artifact_id=artifact_name if not show_all else None,
            event_type=normalized_event_type,
            limit=limit,
            offset=0,
        )
    except Exception as exc:
        console.print(f"[red]Error:[/red] Failed to retrieve history events: {exc}")
        sys.exit(1)

    if not events:
        scope = "all artifacts" if show_all else f"artifact '{artifact_name}'"
        if normalized_event_type:
            scope += f" (event type: {normalized_event_type})"
        console.print(f"[yellow]No history events found for {scope}.[/yellow]")
        return

    if output_format == "json":
        _print_json(events)
    else:
        if show_all:
            console.print(
                f"[bold]Activity history — all artifacts[/bold] "
                f"([dim]{len(events)} event(s)[/dim])"
            )
        else:
            console.print(
                f"[bold]Activity history for '{artifact_name}'[/bold] "
                f"([dim]{len(events)} event(s)[/dim])"
            )
        _print_table(events, show_artifact_column=show_all)
