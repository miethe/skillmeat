"""Click command group for SkillMeat authentication.

Provides the ``skillmeat auth`` subcommand tree.  Currently exposes:

    skillmeat auth login [--no-browser] [--timeout SECONDS]

The ``login`` command runs the OAuth 2.0 Device Authorization Grant (RFC 8628)
against a configured Clerk issuer.  In local (zero-auth) mode it prints an
informative message instead of initiating the flow.

Credential storage is intentionally out of scope for this module — CLI-002
will add a ``TokenStore`` that persists the tokens returned here.
"""

from __future__ import annotations

import os
import sys
import webbrowser

import click
from rich.console import Console
from rich.panel import Panel

from skillmeat.cli.auth_flow import (
    AuthConfig,
    DeviceCodeFlow,
    DeviceCodeAccessDeniedError,
    DeviceCodeConfigError,
    DeviceCodeExpiredError,
    DeviceCodeTimeoutError,
    DeviceCodeFlowError,
)

console = Console(force_terminal=True, legacy_windows=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_local_mode() -> bool:
    """Return True when SkillMeat is running in zero-auth (local) mode.

    Checks the ``SKILLMEAT_AUTH_MODE`` environment variable first (explicit
    override), then falls back to reading ``APISettings`` if available.

    Returns:
        True when no authentication provider is configured.
    """
    auth_mode = os.environ.get("SKILLMEAT_AUTH_MODE", "").strip().lower()
    if auth_mode == "local":
        return True
    if auth_mode and auth_mode != "clerk":
        # Unknown explicit mode — treat as local to be safe.
        return True

    # No explicit override — consult API settings if reachable.
    try:
        from skillmeat.api.config import get_settings

        settings = get_settings()
        return not settings.auth_enabled or settings.auth_provider == "local"
    except Exception:
        # API settings unavailable (e.g. running without API installed).
        # Fall back to env-var based detection.
        issuer = os.environ.get("SKILLMEAT_AUTH_ISSUER_URL", "").strip()
        client_id = os.environ.get("SKILLMEAT_AUTH_CLIENT_ID", "").strip()
        return not (issuer and client_id)


# ---------------------------------------------------------------------------
# auth group
# ---------------------------------------------------------------------------


@click.group("auth")
def auth_cli() -> None:
    """Authentication commands for SkillMeat."""


# ---------------------------------------------------------------------------
# login sub-command
# ---------------------------------------------------------------------------


@auth_cli.command("login")
@click.option(
    "--no-browser",
    is_flag=True,
    default=False,
    help="Do not attempt to open the verification URL in a browser automatically.",
)
@click.option(
    "--timeout",
    "timeout",
    default=300,
    show_default=True,
    metavar="SECONDS",
    help="Maximum time (in seconds) to wait for the user to authorize the device.",
)
def login(no_browser: bool, timeout: int) -> None:
    """Log in to SkillMeat using the OAuth device code flow.

    Opens a browser window and prompts you to authorize this device.  The
    command polls for authorization until the device code expires or the
    optional timeout is reached.

    In local (zero-auth) mode this command prints an informational message
    and exits without making any network requests.

    \b
    Examples:
      skillmeat auth login
      skillmeat auth login --no-browser
      skillmeat auth login --timeout 600
    """
    # ------------------------------------------------------------------
    # Local-mode guard
    # ------------------------------------------------------------------
    if _is_local_mode():
        console.print(
            Panel(
                "[bold cyan]SkillMeat is running in local (zero-auth) mode.[/bold cyan]\n\n"
                "No authentication is required.  All API endpoints are accessible "
                "without credentials.\n\n"
                "To enable authentication, set [bold]SKILLMEAT_AUTH_MODE=clerk[/bold] "
                "and configure [bold]SKILLMEAT_AUTH_ISSUER_URL[/bold] and "
                "[bold]SKILLMEAT_AUTH_CLIENT_ID[/bold].",
                title="[green]Auth not required[/green]",
                expand=False,
            )
        )
        return

    # ------------------------------------------------------------------
    # Build config from environment
    # ------------------------------------------------------------------
    config = AuthConfig()

    try:
        _run_device_code_flow(config, no_browser=no_browser, timeout=timeout)
    except DeviceCodeConfigError as exc:
        raise click.ClickException(str(exc)) from exc
    except DeviceCodeAccessDeniedError:
        console.print("[bold red]Authorization denied.[/bold red] The request was cancelled.")
        sys.exit(1)
    except DeviceCodeExpiredError:
        console.print(
            "[bold red]Device code expired.[/bold red] "
            "Please run [bold]skillmeat auth login[/bold] again."
        )
        sys.exit(1)
    except DeviceCodeTimeoutError:
        console.print(
            f"[bold red]Timed out[/bold red] after {timeout} seconds waiting for authorization."
        )
        sys.exit(1)
    except DeviceCodeFlowError as exc:
        raise click.ClickException(f"Authentication error: {exc}") from exc
    except Exception as exc:  # pragma: no cover — unexpected errors
        raise click.ClickException(f"Unexpected error during login: {exc}") from exc


# ---------------------------------------------------------------------------
# Internal flow orchestration (separated for testability)
# ---------------------------------------------------------------------------


def _run_device_code_flow(
    config: AuthConfig,
    *,
    no_browser: bool = False,
    timeout: int = 300,
) -> None:
    """Run the device-code flow and print the result.

    This function is separated from the Click command so that tests can call
    it directly with a mock ``AuthConfig`` (and a mock HTTP client injected
    into ``DeviceCodeFlow``).

    Args:
        config:     Populated :class:`~skillmeat.cli.auth_flow.AuthConfig`.
        no_browser: When True, skip the automatic ``webbrowser.open()`` call.
        timeout:    Maximum seconds to wait for authorization.

    Raises:
        Any exception raised by :class:`~skillmeat.cli.auth_flow.DeviceCodeFlow`.
    """
    flow = DeviceCodeFlow(config)

    # Step 1 — Initiate the device-code request.
    console.print("[dim]Requesting device code...[/dim]")
    device_auth = flow.start()

    # Step 2 — Display instructions to the user.
    verification_url = (
        device_auth.verification_uri_complete or device_auth.verification_uri
    )
    console.print(
        Panel(
            f"[bold]To log in, visit:[/bold]\n\n"
            f"  [bold cyan]{device_auth.verification_uri}[/bold cyan]\n\n"
            f"[bold]Enter code:[/bold]\n\n"
            f"  [bold yellow]{device_auth.user_code}[/bold yellow]\n\n"
            f"[dim]The code expires in {device_auth.expires_in} seconds.[/dim]",
            title="[green]Authorize SkillMeat[/green]",
            expand=False,
        )
    )

    # Step 3 — Optionally open the browser.
    if not no_browser:
        opened = False
        try:
            opened = webbrowser.open(verification_url)
        except Exception:  # pragma: no cover
            pass
        if opened:
            console.print("[dim]Browser opened automatically.[/dim]")
        else:
            console.print(
                "[dim]Could not open browser automatically. "
                "Please visit the URL above manually.[/dim]"
            )

    # Step 4 — Poll until authorized.
    console.print("[dim]Waiting for authorization...[/dim]")
    result = flow.poll(device_auth, timeout=float(timeout))

    # Step 5 — Report success.
    # NOTE: CLI-002 will persist result.access_token / result.refresh_token here.
    console.print(
        Panel(
            "[bold green]Successfully logged in![/bold green]\n\n"
            "[dim]Tokens have been received but are not yet persisted "
            "(credential storage is implemented in CLI-002).[/dim]",
            title="[green]Login successful[/green]",
            expand=False,
        )
    )

    if result.expires_in is not None:
        console.print(
            f"[dim]Access token expires in {result.expires_in} seconds.[/dim]"
        )
