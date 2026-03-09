"""Add 'workflow' to check_artifact_type CHECK constraint on artifacts table.

Revision ID: 20260303_1100_add_workflow_to_artifact_type_check
Revises: 20260303_1000_add_remote_git_platform_and_deployment_set_remote_fields
Create Date: 2026-03-03 11:00:00.000000+00:00

Background
----------
The ``ArtifactType`` enum already includes the ``workflow`` value but the
corresponding SQLite CHECK constraint on the ``artifacts`` table did not.
This caused ``CHECK constraint failed`` errors whenever a workflow artifact
was inserted or updated via the cache layer.

Changes
-------
1. ``artifacts`` — extend the ``check_artifact_type`` CHECK constraint to
   include ``'workflow'``.  Because SQLite does not support
   ``ALTER TABLE ... ADD/DROP CONSTRAINT``, the table is rebuilt via
   ``batch_alter_table`` with ``recreate="always"``.

   Updated type list:
   ``('skill', 'command', 'agent', 'mcp', 'mcp_server', 'hook', 'workflow',
   'composite', 'project_config', 'spec_file', 'rule_file', 'context_file',
   'progress_template')``

SQLite FK Safety
----------------
env.py enables ``PRAGMA foreign_keys = ON`` globally.  When
``batch_alter_table`` with ``recreate="always"`` copies the ``artifacts``
table to a temp table, SQLite FK enforcement on the new table can conflict
with FK references *from* child tables (e.g. ``collection_artifacts``,
``group_artifacts``, ``artifact_tags``).  To avoid this the migration
temporarily disables FK enforcement around the batch alter and re-enables it
immediately afterwards.

PostgreSQL Notes
----------------
PostgreSQL supports native ``ALTER TABLE ... DROP CONSTRAINT`` and
``ALTER TABLE ... ADD CONSTRAINT`` for CHECK constraints, so no table
recreation is required.  The idempotency guard uses ``pg_constraint`` to
inspect the current constraint definition.

Backward Compatibility
----------------------
Existing rows are unaffected; all other valid type values remain in the
constraint.  Code that does not use workflow artifacts continues to work
unchanged.

Rollback
--------
Rebuild ``artifacts`` with the original CHECK constraint (without
``'workflow'``).
"""

from __future__ import annotations

import logging
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

from skillmeat.cache.migrations.dialect_helpers import is_sqlite, is_postgresql


log = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "20260303_1100_add_workflow_to_artifact_type_check"
down_revision: Union[str, None] = (
    "20260303_1000_add_remote_git_platform_and_deployment_set_remote_fields"
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Canonical type lists — single source of truth for this migration.
_TYPES_WITH_WORKFLOW = (
    "('skill', 'command', 'agent', 'mcp', 'mcp_server', 'hook', 'workflow', "
    "'composite', 'project_config', 'spec_file', 'rule_file', 'context_file', "
    "'progress_template')"
)
_TYPES_WITHOUT_WORKFLOW = (
    "('skill', 'command', 'agent', 'mcp', 'mcp_server', 'hook', "
    "'composite', 'project_config', 'spec_file', 'rule_file', 'context_file', "
    "'progress_template')"
)

# PostgreSQL constraint name — matches the name used in the ORM model.
_PG_CONSTRAINT_NAME = "check_artifact_type"


def _workflow_already_in_constraint_sqlite(bind: sa.engine.Connection) -> bool:
    """Return True if the check_artifact_type constraint already lists 'workflow' (SQLite).

    SQLite stores the original SQL text of CHECK constraints in
    ``sqlite_master``.  We inspect that text to decide whether the migration
    has already been applied (idempotency guard).
    """
    result = bind.execute(
        text(
            "SELECT sql FROM sqlite_master "
            "WHERE type='table' AND name='artifacts'"
        )
    )
    row = result.fetchone()
    if row is None:
        return False
    create_sql: str = row[0] or ""
    return "'workflow'" in create_sql


def _workflow_already_in_constraint_pg(bind: sa.engine.Connection) -> bool:
    """Return True if the check_artifact_type constraint already lists 'workflow' (PostgreSQL).

    Queries ``pg_constraint`` joined with ``pg_class`` to retrieve the
    constraint definition text and checks whether it already contains the
    ``'workflow'`` literal.
    """
    result = bind.execute(
        text(
            """
            SELECT pg_get_constraintdef(c.oid)
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            WHERE c.conname = :cname
              AND t.relname = 'artifacts'
              AND c.contype = 'c'
            """
        ),
        {"cname": _PG_CONSTRAINT_NAME},
    )
    row = result.fetchone()
    if row is None:
        return False
    constraint_def: str = row[0] or ""
    return "'workflow'" in constraint_def or "workflow" in constraint_def


def _get_pg_constraint_name(bind: sa.engine.Connection) -> str | None:
    """Return the name of the check_artifact_type constraint on artifacts (PostgreSQL).

    Returns None if no matching CHECK constraint is found.
    """
    result = bind.execute(
        text(
            """
            SELECT c.conname
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            WHERE c.conname = :cname
              AND t.relname = 'artifacts'
              AND c.contype = 'c'
            """
        ),
        {"cname": _PG_CONSTRAINT_NAME},
    )
    row = result.fetchone()
    return row[0] if row else None


def upgrade() -> None:
    """Add 'workflow' to the check_artifact_type CHECK constraint.

    The operation is idempotent: if the constraint already contains
    ``'workflow'`` (e.g. because ``Base.metadata.create_all()`` was called
    after the model was updated but before this migration ran), the alter
    is skipped.
    """
    bind = op.get_bind()

    if is_sqlite():
        log.info(
            "add_workflow_to_artifact_type_check upgrade: running SQLite dialect path."
        )
        _upgrade_sqlite(bind)
    elif is_postgresql():
        log.info(
            "add_workflow_to_artifact_type_check upgrade: running PostgreSQL dialect path."
        )
        _upgrade_postgresql(bind)
    else:
        log.warning(
            "add_workflow_to_artifact_type_check upgrade: unknown dialect %r; skipping.",
            bind.dialect.name,
        )


def _upgrade_sqlite(bind: sa.engine.Connection) -> None:
    """SQLite upgrade: rebuild artifacts table via batch_alter_table."""
    if _workflow_already_in_constraint_sqlite(bind):
        log.info(
            "add_workflow_to_artifact_type_check (SQLite): constraint already "
            "contains 'workflow'; skipping."
        )
        return

    # Temporarily disable FK enforcement so that the table-copy performed by
    # batch_alter_table does not trigger FK violations from child tables that
    # reference artifacts.uuid.
    op.execute(text("PRAGMA foreign_keys = OFF"))
    try:
        with op.batch_alter_table("artifacts", recreate="always") as batch_op:
            batch_op.drop_constraint("check_artifact_type", type_="check")
            batch_op.create_check_constraint(
                "check_artifact_type",
                f"type IN {_TYPES_WITH_WORKFLOW}",
            )
    finally:
        op.execute(text("PRAGMA foreign_keys = ON"))


def _upgrade_postgresql(bind: sa.engine.Connection) -> None:
    """PostgreSQL upgrade: use ALTER TABLE to replace the CHECK constraint."""
    if _workflow_already_in_constraint_pg(bind):
        log.info(
            "add_workflow_to_artifact_type_check (PostgreSQL): constraint already "
            "contains 'workflow'; skipping."
        )
        return

    # Drop the existing constraint if it exists.
    existing_name = _get_pg_constraint_name(bind)
    if existing_name:
        log.info(
            "add_workflow_to_artifact_type_check (PostgreSQL): dropping constraint %r.",
            existing_name,
        )
        op.execute(
            text(f"ALTER TABLE artifacts DROP CONSTRAINT {existing_name}")
        )

    # Add the updated constraint with 'workflow' included.
    log.info(
        "add_workflow_to_artifact_type_check (PostgreSQL): adding updated constraint."
    )
    op.execute(
        text(
            f"ALTER TABLE artifacts ADD CONSTRAINT {_PG_CONSTRAINT_NAME} "
            f"CHECK (type IN ('skill', 'command', 'agent', 'mcp', 'mcp_server', "
            f"'hook', 'workflow', 'composite', 'project_config', 'spec_file', "
            f"'rule_file', 'context_file', 'progress_template'))"
        )
    )


def downgrade() -> None:
    """Remove 'workflow' from the check_artifact_type CHECK constraint.

    Rebuilds the ``artifacts`` table with the original constraint that does
    not include ``'workflow'``.  Rows with ``type = 'workflow'`` will violate
    the restored constraint; callers are responsible for removing such rows
    before running the downgrade.
    """
    bind = op.get_bind()

    if is_sqlite():
        log.info(
            "add_workflow_to_artifact_type_check downgrade: running SQLite dialect path."
        )
        _downgrade_sqlite()
    elif is_postgresql():
        log.info(
            "add_workflow_to_artifact_type_check downgrade: running PostgreSQL dialect path."
        )
        _downgrade_postgresql(bind)
    else:
        log.warning(
            "add_workflow_to_artifact_type_check downgrade: unknown dialect %r; skipping.",
            bind.dialect.name,
        )


def _downgrade_sqlite() -> None:
    """SQLite downgrade: rebuild artifacts table via batch_alter_table."""
    op.execute(text("PRAGMA foreign_keys = OFF"))
    try:
        with op.batch_alter_table("artifacts", recreate="always") as batch_op:
            batch_op.drop_constraint("check_artifact_type", type_="check")
            batch_op.create_check_constraint(
                "check_artifact_type",
                f"type IN {_TYPES_WITHOUT_WORKFLOW}",
            )
    finally:
        op.execute(text("PRAGMA foreign_keys = ON"))


def _downgrade_postgresql(bind: sa.engine.Connection) -> None:
    """PostgreSQL downgrade: use ALTER TABLE to restore the constraint without 'workflow'."""
    # Drop the constraint with 'workflow'.
    existing_name = _get_pg_constraint_name(bind)
    if existing_name:
        log.info(
            "add_workflow_to_artifact_type_check downgrade (PostgreSQL): "
            "dropping constraint %r.",
            existing_name,
        )
        op.execute(
            text(f"ALTER TABLE artifacts DROP CONSTRAINT {existing_name}")
        )

    # Add the original constraint without 'workflow'.
    log.info(
        "add_workflow_to_artifact_type_check downgrade (PostgreSQL): "
        "adding constraint without 'workflow'."
    )
    op.execute(
        text(
            f"ALTER TABLE artifacts ADD CONSTRAINT {_PG_CONSTRAINT_NAME} "
            f"CHECK (type IN ('skill', 'command', 'agent', 'mcp', 'mcp_server', "
            f"'hook', 'composite', 'project_config', 'spec_file', 'rule_file', "
            f"'context_file', 'progress_template'))"
        )
    )
