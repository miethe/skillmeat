"""Dialect-aware SQL helpers for Alembic migrations.

This module centralizes database dialect detection and trigger creation so
that migration files can be made dialect-aware without duplicating
boilerplate.  All helpers use ``op.get_bind()`` to inspect the live
connection's dialect at migration time, meaning they are safe to call from
both ``upgrade()`` and ``downgrade()`` bodies.

Supported dialects
------------------
* **SQLite** – used for the default local/single-tenant configuration.
* **PostgreSQL** – used for the enterprise multi-tenant configuration.

Usage example
-------------
::

    from alembic import op
    from skillmeat.cache.migrations.dialect_helpers import (
        is_sqlite,
        is_postgresql,
        create_updated_at_trigger,
        drop_updated_at_trigger,
    )

    def upgrade() -> None:
        op.create_table("my_table", ...)
        create_updated_at_trigger("my_table")          # default column: updated_at
        create_updated_at_trigger("my_table", "synced_at")  # custom column

    def downgrade() -> None:
        drop_updated_at_trigger("my_table")
        op.drop_table("my_table")
"""

from __future__ import annotations

from alembic import op


# ---------------------------------------------------------------------------
# Dialect detection
# ---------------------------------------------------------------------------


def is_sqlite() -> bool:
    """Return True when the current migration connection targets SQLite.

    Uses ``op.get_bind()`` to inspect the active dialect, so this function
    must only be called from within a migration ``upgrade()`` or
    ``downgrade()`` body.

    Returns:
        True if the database dialect is SQLite, False otherwise.

    Example:
        >>> if is_sqlite():
        ...     op.execute("PRAGMA journal_mode=WAL")
    """
    return op.get_bind().dialect.name == "sqlite"


def is_postgresql() -> bool:
    """Return True when the current migration connection targets PostgreSQL.

    Uses ``op.get_bind()`` to inspect the active dialect, so this function
    must only be called from within a migration ``upgrade()`` or
    ``downgrade()`` body.

    Returns:
        True if the database dialect is PostgreSQL, False otherwise.

    Example:
        >>> if is_postgresql():
        ...     op.execute("SET search_path TO app_schema")
    """
    return op.get_bind().dialect.name == "postgresql"


# ---------------------------------------------------------------------------
# Trigger helpers
# ---------------------------------------------------------------------------


def create_updated_at_trigger(
    table_name: str,
    column: str = "updated_at",
) -> None:
    """Create a dialect-appropriate trigger to maintain an auto-updated timestamp.

    The trigger fires on every UPDATE to the target table and sets the
    specified column to the current wall-clock time.

    Trigger naming conventions
    ~~~~~~~~~~~~~~~~~~~~~~~~~~
    * **SQLite trigger name**: ``{table_name}_{column}``
    * **PostgreSQL function name**: ``update_{table_name}_{column}``
    * **PostgreSQL trigger name**: ``{table_name}_{column}_trigger``

    SQLite implementation
    ~~~~~~~~~~~~~~~~~~~~~
    Creates an ``AFTER UPDATE`` trigger that issues a follow-up
    ``UPDATE … SET {column} = CURRENT_TIMESTAMP WHERE id = NEW.id``.
    This matches the style established in ``001_initial_schema.py`` and all
    subsequent migration files in this project.

    PostgreSQL implementation
    ~~~~~~~~~~~~~~~~~~~~~~~~~
    1. Creates (or replaces) a trigger *function*
       ``update_{table_name}_{column}()`` that sets ``NEW.{column} = NOW()``
       and returns ``NEW``.
    2. Creates a ``BEFORE UPDATE`` trigger
       ``{table_name}_{column}_trigger`` on the table that calls the
       function for each row.

    Args:
        table_name: Name of the table to attach the trigger to.
        column: Name of the timestamp column to maintain.
                Defaults to ``"updated_at"``.

    Example:
        >>> create_updated_at_trigger("projects")
        >>> create_updated_at_trigger("collection_artifacts", "synced_at")
    """
    if is_postgresql():
        fn_name = f"update_{table_name}_{column}"
        trigger_name = f"{table_name}_{column}_trigger"

        # Create or replace the trigger function.
        op.execute(
            f"""
            CREATE OR REPLACE FUNCTION {fn_name}()
            RETURNS TRIGGER
            LANGUAGE plpgsql
            AS $$
            BEGIN
                NEW.{column} = NOW();
                RETURN NEW;
            END;
            $$;
            """
        )

        # Attach the trigger to the table.
        op.execute(
            f"""
            CREATE TRIGGER {trigger_name}
            BEFORE UPDATE ON {table_name}
            FOR EACH ROW
            EXECUTE FUNCTION {fn_name}();
            """
        )
    else:
        # SQLite — matches the naming and body style used throughout this
        # project's existing migration files.
        trigger_name = f"{table_name}_{column}"

        op.execute(
            f"""
            CREATE TRIGGER {trigger_name}
            AFTER UPDATE ON {table_name}
            FOR EACH ROW
            BEGIN
                UPDATE {table_name} SET {column} = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END;
            """
        )


def drop_updated_at_trigger(
    table_name: str,
    column: str = "updated_at",
) -> None:
    """Drop the trigger (and, on PostgreSQL, its backing function) created by
    :func:`create_updated_at_trigger`.

    Args:
        table_name: Name of the table whose trigger should be removed.
        column: Name of the timestamp column the trigger maintained.
                Defaults to ``"updated_at"``.

    Example:
        >>> drop_updated_at_trigger("projects")
        >>> drop_updated_at_trigger("collection_artifacts", "synced_at")
    """
    if is_postgresql():
        fn_name = f"update_{table_name}_{column}"
        trigger_name = f"{table_name}_{column}_trigger"

        op.execute(
            f"DROP TRIGGER IF EXISTS {trigger_name} ON {table_name};"
        )
        op.execute(
            f"DROP FUNCTION IF EXISTS {fn_name}();"
        )
    else:
        # SQLite
        trigger_name = f"{table_name}_{column}"
        op.execute(f"DROP TRIGGER IF EXISTS {trigger_name}")


__all__ = [
    "is_sqlite",
    "is_postgresql",
    "create_updated_at_trigger",
    "drop_updated_at_trigger",
]
