"""CLI command group for enterprise edition operations.

Exposes the ``skillmeat enterprise`` sub-command tree.  Currently provides:

    skillmeat enterprise migrate [--dry-run] [--force] [--collection-dir PATH]

The migrate sub-command uploads all locally collected artifacts to the
enterprise API.  Each artifact is read from the filesystem, checksummed,
and POSTed to ``POST /api/v1/artifacts/upload``.  Failures on individual
artifacts are non-fatal; they are reported in the results table and
contribute to the exit code (exit 1 when any artifact fails).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

import click
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table

from skillmeat.core.enterprise_config import is_enterprise_mode
from skillmeat.core.enterprise_migration import (
    ArtifactMigrationResult,
    ChecksumMismatch,
    ChecksumValidationResult,
    EnterpriseMigrationService,
    MigrationResult,
)
from skillmeat.core.hashing import _is_excluded

logger = logging.getLogger(__name__)

console = Console(force_terminal=True, legacy_windows=False)

# ---------------------------------------------------------------------------
# Default collection directory resolution
# ---------------------------------------------------------------------------


def _default_collection_dir() -> Path:
    """Return the default SkillMeat collection directory.

    Uses ``~/.skillmeat/collection/`` as the canonical default, which matches
    the path that :class:`~skillmeat.core.collection.CollectionManager` uses
    when no explicit path is given.

    Returns:
        Absolute ``Path`` to the default collection directory.
    """
    return Path.home() / ".skillmeat" / "collection"


# ---------------------------------------------------------------------------
# Rich output helpers
# ---------------------------------------------------------------------------


def _status_cell(result: ArtifactMigrationResult) -> str:
    """Return a coloured Rich markup string for a result's status.

    Args:
        result: Single-artifact migration result.

    Returns:
        Rich markup string — green check, red cross, or yellow "skipped".
    """
    if result.files_count == 0 and result.success and not result.error:
        return "[yellow]skipped[/yellow]"
    if result.success:
        prefix = "[dim](dry-run)[/dim] " if result.dry_run else ""
        return f"{prefix}[green]✓[/green]"
    return "[red]✗[/red]"


def _format_bytes(n: int) -> str:
    """Return a human-readable byte size string.

    Args:
        n: Number of bytes.

    Returns:
        Formatted string such as ``"1.2 KB"``, ``"3.4 MB"``, or ``"512 B"``.
    """
    if n >= 1_048_576:
        return f"{n / 1_048_576:.1f} MB"
    if n >= 1_024:
        return f"{n / 1_024:.1f} KB"
    return f"{n} B"


def _print_results_table(results: list[ArtifactMigrationResult], dry_run: bool) -> None:
    """Print a Rich table summarising per-artifact migration results.

    Args:
        results: List of per-artifact results from
            :meth:`~EnterpriseMigrationService.migrate_all`.
        dry_run: When True the table header includes a dry-run notice.
    """
    title = "Migration Preview (dry-run)" if dry_run else "Migration Results"
    table = Table(title=title, show_lines=False)
    table.add_column("Artifact", style="bold", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Files", justify="right")
    table.add_column("Size", justify="right")
    table.add_column("Error", style="red", no_wrap=False)

    for r in results:
        table.add_row(
            r.name,
            _status_cell(r),
            str(r.files_count) if r.files_count else "-",
            _format_bytes(r.total_bytes) if r.total_bytes else "-",
            r.error or "",
        )

    console.print(table)


# ---------------------------------------------------------------------------
# enterprise group
# ---------------------------------------------------------------------------


@click.group("enterprise")
def enterprise_cli() -> None:
    """Enterprise edition commands (requires SKILLMEAT_EDITION=enterprise)."""


# ---------------------------------------------------------------------------
# migrate sub-command
# ---------------------------------------------------------------------------


@enterprise_cli.command("migrate")
@click.option(
    "--dry-run / --no-dry-run",
    default=False,
    show_default=True,
    help="Preview what would be uploaded without making any API calls.",
)
@click.option(
    "--force / --no-force",
    default=False,
    show_default=True,
    help="Skip the confirmation prompt before migrating.",
)
@click.option(
    "--collection-dir",
    "collection_dir",
    default=None,
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    metavar="PATH",
    help=(
        "Root of the local SkillMeat collection to migrate "
        "(default: ~/.skillmeat/collection/)."
    ),
)
def migrate(
    dry_run: bool,
    force: bool,
    collection_dir: Optional[Path],
) -> None:
    """Upload local collection artifacts to the enterprise API.

    Reads every artifact directory found under COLLECTION_DIR/artifacts/ and
    uploads each one to the enterprise API endpoint.  A Rich summary table is
    printed after the run.  Individual failures are non-fatal: the command
    continues with remaining artifacts and exits with code 1 at the end if any
    artifact failed.

    Examples:

      skillmeat enterprise migrate --dry-run

      skillmeat enterprise migrate --force

      skillmeat enterprise migrate --collection-dir /path/to/collection
    """
    # ------------------------------------------------------------------
    # 1. Enterprise mode guard
    # ------------------------------------------------------------------
    if not is_enterprise_mode():
        console.print(
            "[bold red]Error:[/bold red] Enterprise commands require enterprise mode. "
            "Set the environment variable [bold]SKILLMEAT_EDITION=enterprise[/bold] "
            "and configure [bold]SKILLMEAT_API_URL[/bold] before running this command."
        )
        sys.exit(1)

    # ------------------------------------------------------------------
    # 2. Resolve collection directory
    # ------------------------------------------------------------------
    resolved_dir: Path = (collection_dir or _default_collection_dir()).expanduser().resolve()

    if not resolved_dir.exists():
        console.print(
            f"[bold red]Error:[/bold red] Collection directory not found: "
            f"[bold]{resolved_dir}[/bold]"
        )
        sys.exit(1)

    # Determine how many artifacts would be processed.
    artifacts_dir = resolved_dir / "artifacts"
    if artifacts_dir.is_dir():
        artifact_names = sorted(p.name for p in artifacts_dir.iterdir() if p.is_dir())
        artifact_count = len(artifact_names)
    else:
        artifact_count = 0

    # ------------------------------------------------------------------
    # 3. Dry-run banner
    # ------------------------------------------------------------------
    if dry_run:
        console.print(
            "[bold cyan][dry-run][/bold cyan] No API calls will be made. "
            "Previewing migration only."
        )

    # ------------------------------------------------------------------
    # 4. Confirmation prompt (skipped with --force or --dry-run)
    # ------------------------------------------------------------------
    if not force and not dry_run:
        if artifact_count == 0:
            console.print(
                f"[yellow]No artifact directories found under "
                f"[bold]{artifacts_dir}[/bold]. Nothing to migrate.[/yellow]"
            )
            sys.exit(0)

        confirmed = Confirm.ask(
            f"Migrate [bold]{artifact_count}[/bold] artifact(s) from "
            f"[bold]{resolved_dir}[/bold]?",
            default=False,
        )
        if not confirmed:
            console.print("[yellow]Migration cancelled.[/yellow]")
            sys.exit(0)

    # ------------------------------------------------------------------
    # 5. Run migration
    # ------------------------------------------------------------------
    svc = EnterpriseMigrationService()

    with console.status(
        "[bold green]Migrating artifacts…[/bold green]",
        spinner="dots",
    ):
        result: MigrationResult = svc.migrate_all(resolved_dir, dry_run=dry_run)

    # ------------------------------------------------------------------
    # 6. Print results table
    # ------------------------------------------------------------------
    if result.results:
        _print_results_table(result.results, dry_run=dry_run)
    else:
        console.print(
            f"[yellow]No artifact directories found under "
            f"[bold]{artifacts_dir}[/bold]. Nothing to migrate.[/yellow]"
        )
        sys.exit(0)

    # ------------------------------------------------------------------
    # 7. Print summary line
    # ------------------------------------------------------------------
    action_label = "previewed" if dry_run else "migrated"
    console.print(
        f"\n[bold]{result.succeeded}[/bold] {action_label}, "
        f"[bold]{result.failed}[/bold] failed, "
        f"[bold]{result.skipped}[/bold] skipped "
        f"(total: {result.total})"
    )

    # ------------------------------------------------------------------
    # 8. Exit code
    # ------------------------------------------------------------------
    if result.failed > 0:
        sys.exit(1)


# ---------------------------------------------------------------------------
# verify sub-command
# ---------------------------------------------------------------------------


def _build_local_checksums(artifact_path: Path) -> Dict[str, str]:
    """Walk *artifact_path* and return a ``{relative_path: sha256_hex}`` map.

    Uses the same exclusion rules as the migration upload so the two sides are
    always comparable.

    Args:
        artifact_path: Root directory of the artifact on the local filesystem.

    Returns:
        Dict mapping POSIX relative paths to their SHA-256 hex digests.
    """
    checksums: Dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(artifact_path, followlinks=True):
        dirnames[:] = sorted(d for d in dirnames if not _is_excluded(d))
        for filename in sorted(filenames):
            if _is_excluded(filename):
                continue
            full = Path(dirpath) / filename
            try:
                if not full.is_file():
                    continue
                h = hashlib.sha256()
                with open(full, "rb") as fh:
                    for chunk in iter(lambda: fh.read(65_536), b""):
                        h.update(chunk)
                rel = full.relative_to(artifact_path).as_posix()
                checksums[rel] = h.hexdigest()
            except (OSError, PermissionError) as exc:
                logger.warning("Cannot read %s for verification: %s", full, exc)
    return checksums


def _print_verify_table(
    local_checksums: Dict[str, str],
    validation: ChecksumValidationResult,
    server_files: set,
) -> None:
    """Print per-file verification results to the console.

    Args:
        local_checksums: Local checksum map used for ordering.
        validation: Result from :meth:`EnterpriseMigrationService.validate_checksums`.
        server_files: Set of relative paths reported by the server.
    """
    mismatch_paths = {m.path for m in validation.mismatches}

    for rel_path in sorted(local_checksums):
        if rel_path in mismatch_paths:
            console.print(f"  [red]X[/red] {rel_path}")
        else:
            console.print(f"  [green]checkmark[/green] {rel_path}")

    # Highlight files present on the server but missing locally.
    for rel_path in sorted(server_files - set(local_checksums)):
        console.print(f"  [yellow]?[/yellow] {rel_path}  [dim](server only)[/dim]")

    if validation.mismatches:
        table = Table(title="Checksum Mismatches", show_lines=True)
        table.add_column("File", style="bold")
        table.add_column("Local SHA256")
        table.add_column("Server SHA256")
        for m in validation.mismatches:
            local_display = (m.local[:16] + "...") if m.local else "[dim]<missing>[/dim]"
            server_display = (m.server[:16] + "...") if m.server else "[dim]<missing>[/dim]"
            table.add_row(m.path, local_display, server_display)
        console.print(table)


@enterprise_cli.command("verify")
@click.argument("artifact_name")
@click.option(
    "--collection-dir",
    "collection_dir",
    default=None,
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    metavar="PATH",
    help=(
        "Root of the local SkillMeat collection "
        "(default: ~/.skillmeat/collection/)."
    ),
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output results as JSON instead of human-readable text.",
)
def verify(
    artifact_name: str,
    collection_dir: Optional[Path],
    output_json: bool,
) -> None:
    """Re-download an uploaded artifact and compare checksums against local files.

    Downloads the artifact's file list from the enterprise API, computes
    SHA-256 on all local files, and reports any mismatches.  Each file is
    marked with a checkmark (match) or X (mismatch).  The command exits with
    code 1 when any file fails verification.

    Examples:

      skillmeat enterprise verify canvas

      skillmeat enterprise verify canvas --collection-dir /path/to/collection

      skillmeat enterprise verify canvas --json
    """
    from skillmeat.core.enterprise_http import enterprise_request

    # ------------------------------------------------------------------
    # 1. Enterprise mode guard
    # ------------------------------------------------------------------
    if not is_enterprise_mode():
        console.print(
            "[bold red]Error:[/bold red] Enterprise commands require enterprise mode. "
            "Set the environment variable [bold]SKILLMEAT_EDITION=enterprise[/bold] "
            "and configure [bold]SKILLMEAT_API_URL[/bold] before running this command."
        )
        sys.exit(1)

    # ------------------------------------------------------------------
    # 2. Resolve artifact directory
    # ------------------------------------------------------------------
    resolved_coll: Path = (
        collection_dir or _default_collection_dir()
    ).expanduser().resolve()
    artifact_path = resolved_coll / "artifacts" / artifact_name

    if not artifact_path.is_dir():
        msg = f"Artifact directory not found: {artifact_path}"
        if output_json:
            console.print_json(
                json.dumps({"artifact": artifact_name, "error": msg, "verified": False})
            )
        else:
            console.print(f"[bold red]Error:[/bold red] {msg}")
        sys.exit(1)

    # ------------------------------------------------------------------
    # 3. Build local checksum map
    # ------------------------------------------------------------------
    local_checksums = _build_local_checksums(artifact_path)

    # ------------------------------------------------------------------
    # 4. Fetch artifact metadata from enterprise API
    # ------------------------------------------------------------------
    try:
        resp = enterprise_request("GET", f"/api/v1/artifacts/{artifact_name}")
    except Exception as exc:
        msg = f"API request failed: {exc}"
        if output_json:
            console.print_json(
                json.dumps({"artifact": artifact_name, "error": msg, "verified": False})
            )
        else:
            console.print(f"[bold red]Enterprise API request failed:[/bold red] {exc}")
        sys.exit(1)

    if resp.status_code not in (200, 201):
        detail = resp.text[:200] if resp.text else "<empty>"
        msg = f"HTTP {resp.status_code}: {detail}"
        if output_json:
            console.print_json(
                json.dumps({"artifact": artifact_name, "error": msg, "verified": False})
            )
        else:
            console.print(
                f"[bold red]Enterprise API returned HTTP {resp.status_code}:[/bold red] "
                f"{detail}"
            )
        sys.exit(1)

    try:
        server_body: Dict = resp.json()
    except Exception:
        server_body = {}

    server_files: set = {
        entry["path"]
        for entry in server_body.get("files", [])
        if "path" in entry
    }

    # ------------------------------------------------------------------
    # 5. Validate checksums
    # ------------------------------------------------------------------
    svc = EnterpriseMigrationService()
    validation = svc.validate_checksums(local_checksums, server_body)

    # ------------------------------------------------------------------
    # 6. Output
    # ------------------------------------------------------------------
    if output_json:
        result_dict = {
            "artifact": artifact_name,
            "verified": validation.valid,
            "files_checked": len(local_checksums),
            "mismatches": [
                {"path": m.path, "local": m.local, "server": m.server}
                for m in validation.mismatches
            ],
        }
        console.print_json(json.dumps(result_dict))
        sys.exit(0 if validation.valid else 1)

    # Human-readable output.
    _print_verify_table(local_checksums, validation, server_files)

    if validation.valid:
        console.print(
            f"\n[green]All {len(local_checksums)} file(s) verified for "
            f"'{artifact_name}'[/green]"
        )
        sys.exit(0)
    else:
        console.print(
            f"\n[red]{len(validation.mismatches)} mismatch(es) found for "
            f"'{artifact_name}'[/red]"
        )
        sys.exit(1)
