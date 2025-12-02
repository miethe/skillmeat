"""Alembic migration infrastructure for SkillMeat cache database.

This module provides helper functions for managing database migrations
for the standalone SQLite cache database.

Usage:
    >>> from skillmeat.cache.migrations import run_migrations, get_current_revision
    >>> run_migrations()  # Apply all pending migrations
    >>> revision = get_current_revision()  # Check current state
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from alembic import command
from alembic.config import Config


def get_alembic_config(db_path: Optional[str | Path] = None) -> Config:
    """Create Alembic configuration for cache database.

    Args:
        db_path: Path to cache database. If None, uses default location
                at ~/.skillmeat/cache/cache.db

    Returns:
        Configured Alembic Config object

    Example:
        >>> config = get_alembic_config()
        >>> config = get_alembic_config("/custom/cache.db")
    """
    # Resolve database path
    if db_path is None:
        db_path = Path.home() / ".skillmeat" / "cache" / "cache.db"
    else:
        db_path = Path(db_path)

    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Get migrations directory (same directory as this file)
    migrations_dir = Path(__file__).parent

    # Create Alembic config
    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", str(migrations_dir))
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.absolute()}")

    # Set version locations to migrations/versions
    alembic_cfg.set_main_option("version_locations", str(migrations_dir / "versions"))

    return alembic_cfg


def run_migrations(db_path: Optional[str | Path] = None) -> None:
    """Run all pending migrations on the cache database.

    This function is idempotent - it can be called multiple times safely.
    It will only apply migrations that haven't been applied yet.

    Args:
        db_path: Path to cache database. If None, uses default location

    Raises:
        alembic.util.exc.CommandError: If migration fails

    Example:
        >>> from skillmeat.cache.migrations import run_migrations
        >>> run_migrations()  # Apply all pending migrations
        >>> run_migrations("/custom/cache.db")  # Custom database path
    """
    alembic_cfg = get_alembic_config(db_path)

    # Run upgrade to head (latest revision)
    command.upgrade(alembic_cfg, "head")


def get_current_revision(db_path: Optional[str | Path] = None) -> Optional[str]:
    """Get current migration revision of the cache database.

    Args:
        db_path: Path to cache database. If None, uses default location

    Returns:
        Current revision identifier (e.g., "001_initial_schema")
        or None if no migrations have been applied

    Raises:
        alembic.util.exc.CommandError: If database state check fails

    Example:
        >>> from skillmeat.cache.migrations import get_current_revision
        >>> revision = get_current_revision()
        >>> if revision:
        ...     print(f"Current revision: {revision}")
        ... else:
        ...     print("No migrations applied yet")
    """
    alembic_cfg = get_alembic_config(db_path)

    # Get current revision from database
    from alembic.script import ScriptDirectory
    from alembic.runtime.migration import MigrationContext
    from sqlalchemy import create_engine

    # Create engine
    db_url = alembic_cfg.get_main_option("sqlalchemy.url")
    engine = create_engine(db_url)

    # Get current revision
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current_rev = context.get_current_revision()
            return current_rev
    finally:
        engine.dispose()


def downgrade_migration(
    db_path: Optional[str | Path] = None, revision: str = "-1"
) -> None:
    """Downgrade database to a specific revision.

    Args:
        db_path: Path to cache database. If None, uses default location
        revision: Target revision identifier. Use "-1" for previous revision,
                 "base" for complete downgrade, or specific revision ID

    Raises:
        alembic.util.exc.CommandError: If downgrade fails

    Example:
        >>> from skillmeat.cache.migrations import downgrade_migration
        >>> downgrade_migration(revision="-1")  # Rollback one migration
        >>> downgrade_migration(revision="base")  # Complete rollback
    """
    alembic_cfg = get_alembic_config(db_path)
    command.downgrade(alembic_cfg, revision)


def show_current_revision(db_path: Optional[str | Path] = None) -> None:
    """Show current database revision (CLI-friendly output).

    Args:
        db_path: Path to cache database. If None, uses default location

    Example:
        >>> from skillmeat.cache.migrations import show_current_revision
        >>> show_current_revision()
        Current revision: 001_initial_schema
    """
    alembic_cfg = get_alembic_config(db_path)
    command.current(alembic_cfg, verbose=True)


def show_migration_history(db_path: Optional[str | Path] = None) -> None:
    """Show complete migration history (CLI-friendly output).

    Args:
        db_path: Path to cache database. If None, uses default location

    Example:
        >>> from skillmeat.cache.migrations import show_migration_history
        >>> show_migration_history()
        001_initial_schema -> Create initial cache schema
    """
    alembic_cfg = get_alembic_config(db_path)
    command.history(alembic_cfg, verbose=True)


__all__ = [
    "run_migrations",
    "get_current_revision",
    "downgrade_migration",
    "show_current_revision",
    "show_migration_history",
    "get_alembic_config",
]
