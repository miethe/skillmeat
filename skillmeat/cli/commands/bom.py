"""Click command group for SkillBOM signing operations.

Provides the ``skillmeat bom`` subcommand tree:

    skillmeat bom sign [FILE] [--key PATH] [--output PATH]
    skillmeat bom verify [FILE] [--signature PATH] [--key PATH]
    skillmeat bom keygen [--dir PATH]
    skillmeat bom generate [--project PATH] [--output FILE] [--auto-sign] [--format FORMAT]
    skillmeat bom restore --commit SHA [--dry-run] [--force]
    skillmeat bom install-hook [--project PATH]

Ed25519 cryptography is provided by :mod:`skillmeat.core.bom.signing`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from skillmeat.core.bom.signing import (
    KeyGenerationError,
    KeyNotFoundError,
    SigningError,
    VerificationError,
    generate_signing_keypair,
    sign_bom,
    sign_file,
    verify_file,
)

console = Console(force_terminal=True, legacy_windows=False)

_DEFAULT_CONTEXT_LOCK = ".skillmeat/context.lock"
_DEFAULT_KEY_DIR = Path.home() / ".skillmeat" / "keys"


# ---------------------------------------------------------------------------
# bom group
# ---------------------------------------------------------------------------


@click.group("bom")
def bom_group() -> None:
    """SkillBOM management commands.

    Sign, verify, and manage Ed25519 signatures for SkillBOM context.lock
    snapshots.

    \b
    Examples:
      skillmeat bom keygen
      skillmeat bom sign
      skillmeat bom verify
    """


# ---------------------------------------------------------------------------
# sign sub-command
# ---------------------------------------------------------------------------


@bom_group.command("sign")
@click.argument(
    "file",
    default=_DEFAULT_CONTEXT_LOCK,
    metavar="FILE",
    type=click.Path(),
)
@click.option(
    "--key",
    "-k",
    "key_path",
    default=None,
    metavar="PATH",
    type=click.Path(),
    help="Path to Ed25519 private key PEM file.  Defaults to ~/.skillmeat/keys/skillbom_ed25519.",
)
@click.option(
    "--output",
    "-o",
    "output_path",
    default=None,
    metavar="PATH",
    type=click.Path(),
    help="Output path for the signature file.  Defaults to <FILE>.sig.",
)
def sign_cmd(file: str, key_path: Optional[str], output_path: Optional[str]) -> None:
    """Sign a BOM context.lock file with Ed25519.

    Reads the target FILE (default: .skillmeat/context.lock), signs it with
    the Ed25519 private key, and writes the binary signature to <FILE>.sig
    (or the path given via --output).

    If the private key does not exist you will be offered the option to
    generate a new keypair in the default key directory.

    \b
    Examples:
      skillmeat bom sign
      skillmeat bom sign .skillmeat/context.lock
      skillmeat bom sign --key ~/.skillmeat/keys/custom_key
      skillmeat bom sign --output /tmp/custom.sig
    """
    file_path = Path(file)
    resolved_key: Optional[Path] = Path(key_path) if key_path else None
    resolved_output: Optional[Path] = Path(output_path) if output_path else None

    # Check that the input file exists.
    if not file_path.exists():
        click.echo(f"Error: file not found: {file_path}", err=True)
        sys.exit(1)

    # If a custom key was specified but doesn't exist, error out immediately.
    if resolved_key is not None and not resolved_key.exists():
        click.echo(f"Error: key file not found: {resolved_key}", err=True)
        sys.exit(1)

    # If no key specified, check whether the default key exists; offer keygen.
    if resolved_key is None:
        default_private = _DEFAULT_KEY_DIR / "skillbom_ed25519"
        if not default_private.exists():
            console.print(
                "[yellow]No signing key found.[/yellow] "
                f"Default key path: [dim]{default_private}[/dim]"
            )
            if click.confirm("Generate a new Ed25519 keypair now?", default=True):
                _run_keygen(_DEFAULT_KEY_DIR)
                # Point resolved_key at the freshly generated key so sign_file
                # uses the correct (possibly patched) location.
                resolved_key = default_private
            else:
                click.echo("Aborted: no signing key available.", err=True)
                sys.exit(1)

    # Perform the signing.
    try:
        sig_path = sign_file(
            file_path=file_path,
            output_path=resolved_output,
            key_path=resolved_key,
        )
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except KeyNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except SigningError as exc:
        click.echo(f"Signing error: {exc}", err=True)
        sys.exit(1)

    # Re-read the result metadata for display by verifying immediately.
    # (sign_file only returns the sig path; key_id comes from sign_bom internally)
    _display_sign_success(file_path, sig_path, resolved_key)


def _display_sign_success(
    file_path: Path,
    sig_path: Path,
    key_path: Optional[Path],
) -> None:
    """Render a success panel after signing."""
    table = Table.grid(padding=(0, 2))
    table.add_column(style="dim", justify="right")
    table.add_column()

    table.add_row("File:", str(file_path))
    table.add_row("Signature:", str(sig_path))
    table.add_row("Algorithm:", "ed25519")
    if key_path:
        table.add_row("Key:", str(key_path))
    else:
        table.add_row("Key:", str(_DEFAULT_KEY_DIR / "skillbom_ed25519"))

    console.print(
        Panel(
            table,
            title="[green]BOM signed successfully[/green]",
            expand=False,
        )
    )


# ---------------------------------------------------------------------------
# verify sub-command
# ---------------------------------------------------------------------------


@bom_group.command("verify")
@click.argument(
    "file",
    default=_DEFAULT_CONTEXT_LOCK,
    metavar="FILE",
    type=click.Path(),
)
@click.option(
    "--signature",
    "-s",
    "signature_path",
    default=None,
    metavar="PATH",
    type=click.Path(),
    help="Path to signature file.  Defaults to <FILE>.sig.",
)
@click.option(
    "--key",
    "-k",
    "key_path",
    default=None,
    metavar="PATH",
    type=click.Path(),
    help="Path to Ed25519 public key PEM file.  Defaults to ~/.skillmeat/keys/skillbom_ed25519.pub.",
)
def verify_cmd(
    file: str,
    signature_path: Optional[str],
    key_path: Optional[str],
) -> None:
    """Verify a BOM signature.

    Checks the Ed25519 signature for FILE (default: .skillmeat/context.lock).
    Exits with code 0 when the signature is VALID, or code 1 when it is
    INVALID or an ERROR occurs.

    \b
    Examples:
      skillmeat bom verify
      skillmeat bom verify .skillmeat/context.lock
      skillmeat bom verify --signature custom.sig
      skillmeat bom verify --key ~/.skillmeat/keys/skillbom_ed25519.pub
    """
    file_path = Path(file)
    resolved_sig: Optional[Path] = Path(signature_path) if signature_path else None
    resolved_key: Optional[Path] = Path(key_path) if key_path else None

    # Validate input file.
    if not file_path.exists():
        click.echo(f"Error: file not found: {file_path}", err=True)
        sys.exit(1)

    # Verify.
    try:
        result = verify_file(
            file_path=file_path,
            signature_path=resolved_sig,
            key_path=resolved_key,
        )
    except FileNotFoundError as exc:
        _display_verify_error(str(exc))
        sys.exit(1)
    except VerificationError as exc:
        _display_verify_error(str(exc))
        sys.exit(1)

    if result.valid:
        _display_verify_valid(file_path, resolved_sig, result.key_id, result.algorithm)
        sys.exit(0)
    else:
        _display_verify_invalid(result.error)
        sys.exit(1)


def _display_verify_valid(
    file_path: Path,
    sig_path: Optional[Path],
    key_id: Optional[str],
    algorithm: str,
) -> None:
    effective_sig = sig_path or file_path.with_suffix(file_path.suffix + ".sig")

    table = Table.grid(padding=(0, 2))
    table.add_column(style="dim", justify="right")
    table.add_column()

    table.add_row("Status:", "[bold green]VALID[/bold green]")
    table.add_row("File:", str(file_path))
    table.add_row("Signature:", str(effective_sig))
    table.add_row("Algorithm:", algorithm)
    if key_id:
        table.add_row("Key ID:", key_id)

    console.print(
        Panel(
            table,
            title="[green]Signature verification[/green]",
            expand=False,
        )
    )


def _display_verify_invalid(error: Optional[str]) -> None:
    message = error or "Signature verification failed."
    table = Table.grid(padding=(0, 2))
    table.add_column(style="dim", justify="right")
    table.add_column()
    table.add_row("Status:", "[bold red]INVALID[/bold red]")
    table.add_row("Reason:", message)

    console.print(
        Panel(
            table,
            title="[red]Signature verification[/red]",
            expand=False,
        )
    )


def _display_verify_error(message: str) -> None:
    table = Table.grid(padding=(0, 2))
    table.add_column(style="dim", justify="right")
    table.add_column()
    table.add_row("Status:", "[bold yellow]ERROR[/bold yellow]")
    table.add_row("Detail:", message)

    console.print(
        Panel(
            table,
            title="[yellow]Signature verification[/yellow]",
            expand=False,
        )
    )


# ---------------------------------------------------------------------------
# keygen sub-command
# ---------------------------------------------------------------------------


@bom_group.command("keygen")
@click.option(
    "--dir",
    "-d",
    "key_dir",
    default=None,
    metavar="PATH",
    type=click.Path(),
    help=(
        "Directory in which to write the keypair.  "
        "Defaults to ~/.skillmeat/keys/."
    ),
)
def keygen_cmd(key_dir: Optional[str]) -> None:
    """Generate an Ed25519 signing keypair.

    Writes two files into the target directory (default: ~/.skillmeat/keys/):

    \b
      skillbom_ed25519      — private key (mode 0600)
      skillbom_ed25519.pub  — public key  (mode 0644)

    If the files already exist you will be prompted to confirm overwrite.

    \b
    Examples:
      skillmeat bom keygen
      skillmeat bom keygen --dir /path/to/keys
    """
    resolved_dir = Path(key_dir) if key_dir else _DEFAULT_KEY_DIR
    _run_keygen(resolved_dir)


def _run_keygen(key_dir: Path) -> None:
    """Generate and write an Ed25519 keypair, with overwrite prompt."""
    private_path = key_dir / "skillbom_ed25519"
    public_path = key_dir / "skillbom_ed25519.pub"

    if private_path.exists() or public_path.exists():
        if not click.confirm(
            f"Key files already exist in {key_dir}. Overwrite?",
            default=False,
        ):
            click.echo("Aborted: existing keys not overwritten.")
            return

    try:
        public_pem, _ = generate_signing_keypair(key_dir=key_dir)
    except KeyGenerationError as exc:
        click.echo(f"Key generation error: {exc}", err=True)
        sys.exit(1)

    table = Table.grid(padding=(0, 2))
    table.add_column(style="dim", justify="right")
    table.add_column()
    table.add_row("Private key:", str(private_path))
    table.add_row("Public key:", str(public_path))
    table.add_row("Algorithm:", "ed25519")
    table.add_row("Permissions:", "private 0600, public 0644")

    console.print(
        Panel(
            table,
            title="[green]Keypair generated[/green]",
            expand=False,
        )
    )


# ---------------------------------------------------------------------------
# generate sub-command
# ---------------------------------------------------------------------------


@bom_group.command("generate")
@click.option(
    "--project",
    "-p",
    "project_path",
    default=".",
    metavar="PATH",
    type=click.Path(),
    help="Project directory to generate the BOM for.  Defaults to the current directory.",
)
@click.option(
    "--output",
    "-o",
    "output_file",
    default=None,
    metavar="FILE",
    type=click.Path(),
    help=(
        "Output file path.  "
        "Defaults to <project>/.skillmeat/context.lock."
    ),
)
@click.option(
    "--auto-sign",
    "auto_sign",
    is_flag=True,
    default=False,
    help="Automatically sign the generated BOM with the default Ed25519 key.",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["json", "summary"], case_sensitive=False),
    default="summary",
    show_default=True,
    help="Output format.",
)
def generate_cmd(
    project_path: str,
    output_file: Optional[str],
    auto_sign: bool,
    output_format: str,
) -> None:
    """Generate a SkillBOM and write it to context.lock.

    Queries the local artifact cache for the project, assembles a BOM, and
    writes it atomically to the output file (default:
    .skillmeat/context.lock inside the project directory).

    When --auto-sign is given the BOM is immediately signed with the
    default Ed25519 key and a <FILE>.sig signature file is written
    alongside the output.

    \b
    Examples:
      skillmeat bom generate
      skillmeat bom generate --project /path/to/project
      skillmeat bom generate --output /tmp/snapshot.json
      skillmeat bom generate --auto-sign
      skillmeat bom generate --format json
    """
    resolved_project = Path(project_path).resolve()

    # Determine the output path.
    if output_file is not None:
        out_path = Path(output_file)
    else:
        out_path = resolved_project / ".skillmeat" / "context.lock"

    # Ensure the parent directory exists.
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        click.echo(f"Error: could not create output directory {out_path.parent}: {exc}", err=True)
        sys.exit(1)

    # Build BOM using the cache DB for the project.
    try:
        from skillmeat.cache.models import get_session  # noqa: PLC0415
        from skillmeat.core.bom.generator import BomGenerator, BomSerializer  # noqa: PLC0415
    except ImportError as exc:
        click.echo(f"Error: could not import BOM modules: {exc}", err=True)
        sys.exit(1)

    try:
        session = get_session()
    except Exception as exc:  # noqa: BLE001
        click.echo(f"Error: could not open cache database: {exc}", err=True)
        sys.exit(1)

    try:
        generator = BomGenerator(session=session, project_path=resolved_project)
        bom_dict = generator.generate()
    except Exception as exc:  # noqa: BLE001
        click.echo(f"Error: BOM generation failed: {exc}", err=True)
        sys.exit(1)

    serializer = BomSerializer()

    # Write BOM atomically.
    try:
        serializer.write_file(bom_dict, out_path)
    except OSError as exc:
        click.echo(f"Error: could not write BOM to {out_path}: {exc}", err=True)
        sys.exit(1)

    # Optional auto-sign.
    sig_path: Optional[Path] = None
    if auto_sign:
        bom_bytes = serializer.to_json(bom_dict).encode("utf-8")
        try:
            sig_result = sign_bom(bom_bytes)
            sig_path = out_path.with_suffix(out_path.suffix + ".sig")
            sig_path.write_bytes(sig_result.signature)
        except KeyNotFoundError:
            console.print(
                "[yellow]Warning:[/yellow] no signing key found; BOM was written without a signature.\n"
                f"Run [bold]skillmeat bom keygen[/bold] to create a key, then re-run with --auto-sign."
            )
        except SigningError as exc:
            console.print(f"[yellow]Warning:[/yellow] signing failed: {exc}. BOM was still written.")

    # Display results.
    artifact_count: int = bom_dict.get("artifact_count", len(bom_dict.get("artifacts", [])))
    generated_at: str = bom_dict.get("generated_at", "")
    bom_hash = ""
    try:
        bom_bytes_for_hash = serializer.to_json(bom_dict).encode("utf-8")
        import hashlib  # noqa: PLC0415
        bom_hash = hashlib.sha256(bom_bytes_for_hash).hexdigest()
    except Exception:  # noqa: BLE001
        pass

    if output_format == "json":
        output_data = {
            "status": "success",
            "output_file": str(out_path),
            "artifact_count": artifact_count,
            "generated_at": generated_at,
            "sha256": bom_hash,
            "signed": sig_path is not None,
            "signature_file": str(sig_path) if sig_path else None,
        }
        console.print(json.dumps(output_data, indent=2))
    else:
        table = Table.grid(padding=(0, 2))
        table.add_column(style="dim", justify="right")
        table.add_column()

        table.add_row("Output:", str(out_path))
        table.add_row("Artifacts:", str(artifact_count))
        if generated_at:
            table.add_row("Generated:", generated_at)
        if bom_hash:
            table.add_row("SHA-256:", bom_hash[:16] + "...")
        if sig_path is not None:
            table.add_row("Signature:", str(sig_path))

        console.print(
            Panel(
                table,
                title="[green]BOM generated successfully[/green]",
                expand=False,
            )
        )


# ---------------------------------------------------------------------------
# restore sub-command
# ---------------------------------------------------------------------------


@bom_group.command("restore")
@click.option(
    "--commit",
    "-c",
    "commit_sha",
    required=True,
    metavar="SHA",
    help="Git commit SHA to restore artifact state from.",
)
@click.option(
    "--dry-run",
    "dry_run",
    is_flag=True,
    default=False,
    help="Show what would change without making any filesystem modifications.",
)
@click.option(
    "--force",
    "force",
    is_flag=True,
    default=False,
    help="Skip the confirmation prompt before restoring.",
)
def restore_cmd(commit_sha: str, dry_run: bool, force: bool) -> None:
    """Restore artifact state from a git commit's linked BOM snapshot.

    Reads the SkillBOM-Hash footer from COMMIT's message, locates the
    corresponding BOM snapshot, and rehydrates the .claude/ directory.

    A summary of what will change is shown before restoration. Use
    --dry-run to inspect the diff without writing any files.

    \b
    Examples:
      skillmeat bom restore --commit abc1234
      skillmeat bom restore --commit abc1234 --dry-run
      skillmeat bom restore --commit abc1234 --force
    """
    try:
        from skillmeat.core.bom.git_integration import (  # noqa: PLC0415
            restore_from_commit,
        )
    except ImportError as exc:
        click.echo(f"Error: could not import git integration module: {exc}", err=True)
        sys.exit(1)

    target_dir = Path(".").resolve()

    # First do a dry-run to show what will change.
    console.print(f"[dim]Inspecting commit [bold]{commit_sha[:12]}[/bold]...[/dim]")
    try:
        preview = restore_from_commit(
            commit_hash=commit_sha,
            target_dir=target_dir,
            dry_run=True,
            repo_path=target_dir,
        )
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        click.echo(f"Error: restore preview failed: {exc}", err=True)
        sys.exit(1)

    # Display preview.
    preview_table = Table.grid(padding=(0, 2))
    preview_table.add_column(style="dim", justify="right")
    preview_table.add_column()

    preview_table.add_row("Commit:", commit_sha[:12])
    preview_table.add_row("BOM hash:", preview.bom_hash[:16] + "..." if preview.bom_hash else "unknown")
    preview_table.add_row("Total entries:", str(preview.total_entries))
    preview_table.add_row("Resolvable:", str(preview.resolved_entries))

    if preview.unresolved_entries:
        preview_table.add_row(
            "Unresolved:",
            "[yellow]" + ", ".join(preview.unresolved_entries) + "[/yellow]",
        )
    if preview.signature_valid is True:
        preview_table.add_row("Signature:", "[green]valid[/green]")
    elif preview.signature_valid is False:
        preview_table.add_row("Signature:", "[red]INVALID[/red]")

    console.print(
        Panel(
            preview_table,
            title="[cyan]Restore preview[/cyan]" if not dry_run else "[cyan]Dry-run — no changes will be made[/cyan]",
            expand=False,
        )
    )

    if dry_run:
        return

    if preview.total_entries == 0:
        click.echo("Nothing to restore (no entries found in BOM snapshot).", err=True)
        sys.exit(1)

    # Confirm before writing.
    if not force:
        if not click.confirm(
            f"Restore {preview.resolved_entries} artifact(s) into {target_dir}?",
            default=False,
        ):
            click.echo("Aborted.")
            return

    # Perform the actual restore.
    try:
        result = restore_from_commit(
            commit_hash=commit_sha,
            target_dir=target_dir,
            dry_run=False,
            repo_path=target_dir,
        )
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        click.echo(f"Error: restore failed: {exc}", err=True)
        sys.exit(1)

    # Show result.
    result_table = Table.grid(padding=(0, 2))
    result_table.add_column(style="dim", justify="right")
    result_table.add_column()
    result_table.add_row("Commit:", result.commit_sha[:12])
    result_table.add_row("Restored:", f"{result.resolved_entries}/{result.total_entries}")
    if result.unresolved_entries:
        result_table.add_row(
            "Unresolved:",
            "[yellow]" + ", ".join(result.unresolved_entries) + "[/yellow]",
        )

    title_color = "green" if not result.unresolved_entries else "yellow"
    console.print(
        Panel(
            result_table,
            title=f"[{title_color}]Restore complete[/{title_color}]",
            expand=False,
        )
    )

    if result.unresolved_entries:
        sys.exit(1)


# ---------------------------------------------------------------------------
# install-hook sub-command
# ---------------------------------------------------------------------------


@bom_group.command("install-hook")
@click.option(
    "--project",
    "-p",
    "project_path",
    default=".",
    metavar="PATH",
    type=click.Path(),
    help="Project (git repository) directory.  Defaults to the current directory.",
)
def install_hook_cmd(project_path: str) -> None:
    """Install Git hooks for automatic BOM tracking.

    Installs two hooks into <project>/.git/hooks/:

    \b
      prepare-commit-msg  — appends a SkillBOM-Hash footer to every commit message
      post-commit         — links the commit SHA back to the BOM snapshot in the DB

    Existing non-SkillBOM hooks are backed up with a .bak suffix before
    being replaced.

    \b
    Examples:
      skillmeat bom install-hook
      skillmeat bom install-hook --project /path/to/repo
    """
    try:
        from skillmeat.core.bom.git_integration import install_hooks  # noqa: PLC0415
    except ImportError as exc:
        click.echo(f"Error: could not import git integration module: {exc}", err=True)
        sys.exit(1)

    resolved_project = Path(project_path).resolve()

    try:
        install_hooks(resolved_project)
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        click.echo(f"Error: hook installation failed: {exc}", err=True)
        sys.exit(1)

    hooks_dir = resolved_project / ".git" / "hooks"
    installed_hooks = ["prepare-commit-msg", "post-commit"]

    table = Table.grid(padding=(0, 2))
    table.add_column(style="dim", justify="right")
    table.add_column()
    table.add_row("Repository:", str(resolved_project))
    table.add_row("Hooks dir:", str(hooks_dir))
    for hook_name in installed_hooks:
        table.add_row("Installed:", hook_name)

    console.print(
        Panel(
            table,
            title="[green]Git hooks installed[/green]",
            expand=False,
        )
    )
