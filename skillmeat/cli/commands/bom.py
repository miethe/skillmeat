"""Click command group for SkillBOM signing operations.

Provides the ``skillmeat bom`` subcommand tree:

    skillmeat bom sign [FILE] [--key PATH] [--output PATH]
    skillmeat bom verify [FILE] [--signature PATH] [--key PATH]
    skillmeat bom keygen [--dir PATH]

Ed25519 cryptography is provided by :mod:`skillmeat.core.bom.signing`.
"""

from __future__ import annotations

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
