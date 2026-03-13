"""Click command group for attestation management.

Provides the ``skillmeat attest`` subcommand tree:

    skillmeat attest create --artifact-id ID [options]
    skillmeat attest list [--artifact-id ID] [--owner-scope SCOPE] [--limit N]
    skillmeat attest show ATTESTATION_ID [--format table|json]

Attestation records are stored in the local SQLite cache DB via
:class:`~skillmeat.cache.models.AttestationRecord`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console(force_terminal=True, legacy_windows=False)

_DEFAULT_DB_PATH = str(Path.home() / ".skillmeat" / "cache" / "cache.db")

_VALID_OWNER_SCOPES = ("user", "team", "enterprise")
_VALID_VISIBILITIES = ("private", "team", "public")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_session():
    """Return a SQLAlchemy session backed by the local cache DB."""
    from skillmeat.cache.models import get_session

    return get_session(_DEFAULT_DB_PATH)


def _resolve_owner_id() -> str:
    """Resolve the effective owner ID from config or fallback to local user."""
    try:
        from skillmeat.core.config import ConfigManager

        cfg = ConfigManager()
        owner = cfg.get("owner-id")
        if owner:
            return str(owner)
    except Exception:
        pass
    import getpass

    return getpass.getuser()


def _format_timestamp(ts) -> str:
    """Return a short ISO-format string or an em-dash for None."""
    if ts is None:
        return "\u2014"
    try:
        return ts.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(ts)


def _print_list_table(records) -> None:
    """Render attestation records as a Rich summary table."""
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("ID", style="dim", justify="right", no_wrap=True)
    table.add_column("Artifact", style="bold")
    table.add_column("Owner Type", style="magenta")
    table.add_column("Owner ID", style="yellow")
    table.add_column("Visibility", style="cyan")
    table.add_column("Created At", style="green")

    vis_colours = {
        "private": "bright_red",
        "team": "bright_yellow",
        "public": "bright_green",
    }

    for rec in records:
        vis = rec.visibility or "private"
        vis_cell = f"[{vis_colours.get(vis, 'white')}]{vis}[/{vis_colours.get(vis, 'white')}]"
        table.add_row(
            str(rec.id),
            rec.artifact_id,
            rec.owner_type,
            rec.owner_id,
            vis_cell,
            _format_timestamp(rec.created_at),
        )

    console.print(table)


def _print_list_json(records) -> None:
    """Render attestation records as a JSON array to stdout."""
    click.echo(json.dumps([r.to_dict() for r in records], indent=2, default=str))


def _print_detail_table(rec) -> None:
    """Render a single AttestationRecord as a Rich detail panel."""
    roles_display = ", ".join(rec.roles) if rec.roles else "\u2014"
    scopes_display = ", ".join(rec.scopes) if rec.scopes else "\u2014"

    lines = [
        f"[bold]ID:[/bold]          {rec.id}",
        f"[bold]Artifact:[/bold]    {rec.artifact_id}",
        f"[bold]Owner Type:[/bold]  {rec.owner_type}",
        f"[bold]Owner ID:[/bold]    {rec.owner_id}",
        f"[bold]Visibility:[/bold]  {rec.visibility}",
        f"[bold]Roles:[/bold]       {roles_display}",
        f"[bold]Scopes:[/bold]      {scopes_display}",
        f"[bold]Created At:[/bold]  {_format_timestamp(rec.created_at)}",
        f"[bold]Updated At:[/bold]  {_format_timestamp(rec.updated_at)}",
    ]

    console.print(Panel("\n".join(lines), title="Attestation Detail", expand=False))


def _print_detail_json(rec) -> None:
    """Render a single AttestationRecord as JSON to stdout."""
    click.echo(json.dumps(rec.to_dict(), indent=2, default=str))


# ---------------------------------------------------------------------------
# attest group
# ---------------------------------------------------------------------------


@click.group("attest")
def attest_group() -> None:
    """Attestation management commands.

    Create, list, and inspect owner-scoped attestation records that associate
    artifacts with RBAC roles, permission scopes, and visibility settings.

    \b
    Examples:
      skillmeat attest create --artifact-id skill:my-skill --sign
      skillmeat attest list --artifact-id skill:my-skill
      skillmeat attest show 42
    """


# ---------------------------------------------------------------------------
# create sub-command
# ---------------------------------------------------------------------------


@attest_group.command("create")
@click.option(
    "--artifact-id",
    "artifact_id",
    required=True,
    metavar="ID",
    help="Artifact identifier in type:name format (e.g. skill:my-skill).",
)
@click.option(
    "--owner-scope",
    "owner_scope",
    default=None,
    show_default=True,
    type=click.Choice(list(_VALID_OWNER_SCOPES), case_sensitive=False),
    help="Owner scope: user | team | enterprise (default: auto from config).",
)
@click.option(
    "--roles",
    "roles",
    default=None,
    metavar="ROLES",
    help="Comma-separated roles to assert (e.g. viewer,team_member).",
)
@click.option(
    "--scopes",
    "scopes",
    default=None,
    metavar="SCOPES",
    help="Comma-separated permission scopes to grant.",
)
@click.option(
    "--visibility",
    "visibility",
    default="private",
    show_default=True,
    type=click.Choice(list(_VALID_VISIBILITIES), case_sensitive=False),
    help="Visibility level: private | team | public.",
)
@click.option(
    "--notes",
    "notes",
    default=None,
    metavar="TEXT",
    help="Free-text notes to attach to the attestation.",
)
@click.option(
    "--sign",
    "sign",
    is_flag=True,
    default=False,
    help="Sign the attestation record with the local Ed25519 key.",
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
def create_cmd(
    artifact_id: str,
    owner_scope: Optional[str],
    roles: Optional[str],
    scopes: Optional[str],
    visibility: str,
    notes: Optional[str],
    sign: bool,
    output_format: str,
) -> None:
    """Create a manual attestation record for an artifact.

    \b
    Examples:
      skillmeat attest create --artifact-id skill:my-skill
      skillmeat attest create --artifact-id skill:my-skill --roles viewer,team_member --visibility team
      skillmeat attest create --artifact-id skill:my-skill --sign --format json
    """
    from skillmeat.cache.models import AttestationRecord

    # Resolve owner scope
    effective_scope = owner_scope or "user"
    owner_id = _resolve_owner_id()

    # Parse comma-separated lists
    roles_list: Optional[List[str]] = (
        [r.strip() for r in roles.split(",") if r.strip()] if roles else None
    )
    scopes_list: Optional[List[str]] = (
        [s.strip() for s in scopes.split(",") if s.strip()] if scopes else None
    )

    # Optional signing
    signature_hex: Optional[str] = None
    if sign:
        try:
            from skillmeat.core.bom.signing import KeyNotFoundError, sign_bom

            payload = json.dumps(
                {
                    "artifact_id": artifact_id,
                    "owner_type": effective_scope,
                    "owner_id": owner_id,
                    "roles": roles_list,
                    "scopes": scopes_list,
                    "visibility": visibility,
                },
                sort_keys=True,
            ).encode()
            result = sign_bom(payload)
            signature_hex = result.signature.hex()
        except KeyNotFoundError:
            console.print(
                "[yellow]Warning:[/yellow] No Ed25519 signing key found — "
                "attestation created without signature. "
                "Run [bold]skillmeat bom keygen[/bold] to generate one."
            )
        except Exception as exc:
            console.print(f"[yellow]Warning:[/yellow] Signing failed: {exc} — continuing unsigned.")

    try:
        session = _get_session()
    except Exception as exc:
        console.print(f"[red]Error:[/red] Failed to open the cache database: {exc}")
        sys.exit(1)

    try:
        record = AttestationRecord(
            artifact_id=artifact_id,
            owner_type=effective_scope,
            owner_id=owner_id,
            roles=roles_list,
            scopes=scopes_list,
            visibility=visibility,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
    except Exception as exc:
        session.rollback()
        console.print(f"[red]Error:[/red] Failed to create attestation record: {exc}")
        sys.exit(1)
    finally:
        session.close()

    if output_format == "json":
        data = record.to_dict()
        if signature_hex:
            data["signature"] = signature_hex
        if notes:
            data["notes"] = notes
        click.echo(json.dumps(data, indent=2, default=str))
    else:
        console.print(
            f"[green]Attestation created[/green] (ID: [bold]{record.id}[/bold])"
        )
        _print_detail_table(record)
        if signature_hex:
            console.print(f"[dim]Signature:[/dim] {signature_hex[:32]}…")
        if notes:
            console.print(f"[dim]Notes:[/dim] {notes}")


# ---------------------------------------------------------------------------
# list sub-command
# ---------------------------------------------------------------------------


@attest_group.command("list")
@click.option(
    "--artifact-id",
    "artifact_id",
    default=None,
    metavar="ID",
    help="Filter by artifact identifier.",
)
@click.option(
    "--owner-scope",
    "owner_scope",
    default=None,
    type=click.Choice(list(_VALID_OWNER_SCOPES), case_sensitive=False),
    help="Filter by owner scope: user | team | enterprise.",
)
@click.option(
    "--limit",
    "-n",
    default=20,
    show_default=True,
    metavar="N",
    type=click.IntRange(1, 10000),
    help="Maximum number of records to display.",
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
def list_cmd(
    artifact_id: Optional[str],
    owner_scope: Optional[str],
    limit: int,
    output_format: str,
) -> None:
    """List attestation records with optional filters.

    \b
    Examples:
      skillmeat attest list
      skillmeat attest list --artifact-id skill:my-skill
      skillmeat attest list --owner-scope team --limit 50
      skillmeat attest list --format json
    """
    from skillmeat.cache.models import AttestationRecord

    try:
        session = _get_session()
    except Exception as exc:
        console.print(f"[red]Error:[/red] Failed to open the cache database: {exc}")
        sys.exit(1)

    try:
        query = session.query(AttestationRecord)
        if artifact_id:
            query = query.filter(AttestationRecord.artifact_id == artifact_id)
        if owner_scope:
            query = query.filter(AttestationRecord.owner_type == owner_scope)
        records = (
            query.order_by(AttestationRecord.created_at.desc()).limit(limit).all()
        )
    except Exception as exc:
        console.print(f"[red]Error:[/red] Failed to retrieve attestation records: {exc}")
        sys.exit(1)
    finally:
        session.close()

    if not records:
        filters: List[str] = []
        if artifact_id:
            filters.append(f"artifact '{artifact_id}'")
        if owner_scope:
            filters.append(f"owner scope '{owner_scope}'")
        scope_desc = " for " + ", ".join(filters) if filters else ""
        console.print(f"[yellow]No attestation records found{scope_desc}.[/yellow]")
        return

    if output_format == "json":
        _print_list_json(records)
    else:
        console.print(
            f"[bold]Attestation records[/bold] ([dim]{len(records)} record(s)[/dim])"
        )
        _print_list_table(records)


# ---------------------------------------------------------------------------
# show sub-command
# ---------------------------------------------------------------------------


@attest_group.command("show")
@click.argument("attestation_id", metavar="ATTESTATION_ID", type=int)
@click.option(
    "--format",
    "-f",
    "output_format",
    default="table",
    show_default=True,
    type=click.Choice(["table", "json"], case_sensitive=False),
    help="Output format.",
)
def show_cmd(attestation_id: int, output_format: str) -> None:
    """Show full detail for a single attestation record.

    ATTESTATION_ID is the integer primary key displayed in ``attest list``.

    \b
    Examples:
      skillmeat attest show 42
      skillmeat attest show 42 --format json
    """
    from skillmeat.cache.models import AttestationRecord

    try:
        session = _get_session()
    except Exception as exc:
        console.print(f"[red]Error:[/red] Failed to open the cache database: {exc}")
        sys.exit(1)

    try:
        record = (
            session.query(AttestationRecord)
            .filter(AttestationRecord.id == attestation_id)
            .first()
        )
    except Exception as exc:
        console.print(f"[red]Error:[/red] Failed to retrieve attestation record: {exc}")
        sys.exit(1)
    finally:
        session.close()

    if record is None:
        console.print(
            f"[red]Error:[/red] No attestation record found with ID {attestation_id}."
        )
        sys.exit(1)

    if output_format == "json":
        _print_detail_json(record)
    else:
        _print_detail_table(record)
