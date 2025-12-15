"""Alembic environment configuration for SkillMeat cache database.

This module configures the Alembic migration environment for the standalone
SQLite cache database. It handles both online (direct database connection)
and offline (SQL script generation) migration modes.

Key Features:
    - SQLite-specific configuration (no connection pooling)
    - WAL mode and foreign key enforcement
    - Support for both online and offline migrations
    - Automatic schema comparison for autogenerate

Usage:
    This file is used by Alembic internally. You typically won't import it directly.
    Instead, use the helper functions in skillmeat.cache.migrations:

    >>> from skillmeat.cache.migrations import run_migrations
    >>> run_migrations()
"""

from __future__ import annotations

import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

# Add skillmeat to Python path for imports
from pathlib import Path

skillmeat_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(skillmeat_root))

# Alembic Config object (provides access to .ini values)
config = context.config

# Interpret the config file for Python logging (if present and has logging sections)
if config.config_file_name is not None:
    try:
        fileConfig(config.config_file_name)
    except KeyError:
        # Logging sections not present in alembic.ini, skip logging config
        pass

# SQLAlchemy MetaData object for autogenerate support
# Since we're using raw SQL schema, we don't have SQLAlchemy models
# This is None for now, but can be populated if we add SQLAlchemy models
target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is also acceptable here. By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the script output.

    This is useful for generating SQL migration scripts without database access.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # SQLite-specific settings
        render_as_batch=True,  # Required for SQLite ALTER TABLE support
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a connection
    with the context.

    This is the standard mode for applying migrations directly to a database.
    """
    # Get configuration and add SQLite-specific settings
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = config.get_main_option("sqlalchemy.url")

    # Create engine with SQLite-optimized settings
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        # SQLite doesn't use connection pooling
        poolclass=pool.NullPool,
        # SQLite-specific connection arguments
        connect_args={
            "check_same_thread": False,  # Allow multi-threaded access
            "timeout": 30.0,  # 30 second lock timeout
        },
    )

    with connectable.connect() as connection:
        # Execute PRAGMA statements before migrations
        connection.execute(text("PRAGMA journal_mode = WAL"))
        connection.execute(text("PRAGMA synchronous = NORMAL"))
        connection.execute(text("PRAGMA foreign_keys = ON"))
        connection.execute(text("PRAGMA temp_store = MEMORY"))
        connection.execute(text("PRAGMA cache_size = -64000"))
        connection.execute(text("PRAGMA mmap_size = 268435456"))
        connection.commit()

        # Configure migration context
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # SQLite-specific settings
            render_as_batch=True,  # Required for SQLite ALTER TABLE support
            compare_type=True,  # Detect column type changes
            compare_server_default=True,  # Detect default value changes
        )

        with context.begin_transaction():
            context.run_migrations()


# Determine which mode to run in
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
