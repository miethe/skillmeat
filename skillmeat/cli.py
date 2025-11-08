"""CLI entry point for SkillMeat.

This module will be populated with Click commands in Phase 7.
For now, it provides a basic entry point for smoke testing.
"""

import sys
import click
from rich.console import Console

from skillmeat import __version__

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="skillmeat")
def main():
    """SkillMeat: Personal collection manager for Claude Code artifacts.

    Manage Skills, Commands, Agents, and more across multiple projects.
    """
    pass


@main.command()
def init():
    """Initialize a new collection (placeholder)."""
    console.print("[yellow]SkillMeat is under development.[/yellow]")
    console.print(f"[blue]Version: {__version__}[/blue]")
    console.print("\n[green]Phase 1: Foundation complete![/green]")
    console.print("Phase 2+ coming soon: Collection management, deployment, and more.")


if __name__ == "__main__":
    sys.exit(main())
