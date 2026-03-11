"""Add workflow_id to deployment_set_members and update one-ref CHECK constraint

Revision ID: waw_001_add_workflow_id
Revises: pg_001_fulltext_search
Create Date: 2026-03-10 00:02:00.000000+00:00

Background
----------
WAW-P1.1 — Workflow Artifact Wiring, Phase 1.

The ``deployment_set_members`` table uses a polymorphic "exactly one non-null"
pattern: each row references exactly one target type (artifact, group, or
nested set) via a mutually exclusive nullable FK column.  This migration adds
``workflow_id`` as a fourth option so that Workflow definitions can be
composed into DeploymentSets.

Changes
-------
1. Add column ``workflow_id`` (String, nullable) with FK to ``workflows.id``
   (CASCADE delete).
2. Create index ``idx_deployment_set_members_workflow_id`` on ``workflow_id``.
3. Replace the three-column CHECK constraint
   ``check_deployment_set_member_one_ref`` with a four-column version that
   includes ``workflow_id``.

Dialect strategy
----------------
* **Both dialects**: ``op.add_column`` and ``op.create_index`` work uniformly.
* **CHECK constraint update**:
  - *SQLite*: ``ALTER TABLE … ADD/DROP CONSTRAINT`` is not supported.  The
    constraint is replaced via ``op.batch_alter_table`` with
    ``recreate="always"``, which rebuilds the table.  FK enforcement is
    temporarily disabled around the batch operation to avoid FK violations
    from child tables.
  - *PostgreSQL*: Native ``ALTER TABLE … DROP CONSTRAINT`` /
    ``ALTER TABLE … ADD CONSTRAINT`` is used directly.

The CASE WHEN expression ``(CASE WHEN col IS NOT NULL THEN 1 ELSE 0 END)``
is used instead of ``CAST(bool AS int)`` because the latter is not supported
in SQLite.

Downgrade
---------
1. Revert the CHECK constraint to the three-column form.
2. Drop the index.
3. Drop the column.

WARNING: Any rows with ``workflow_id IS NOT NULL`` will violate the restored
three-column constraint.  Remove or update those rows before running the
downgrade.

Schema reference
----------------
docs/project_plans/architecture/ADRs/
.claude/progress/workflow-artifact-wiring/
"""

from __future__ import annotations

import logging
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

from skillmeat.cache.migrations.dialect_helpers import is_sqlite, is_postgresql

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------

revision: str = "waw_001_add_workflow_id"
down_revision: Union[str, None] = "pg_001_fulltext_search"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TABLE = "deployment_set_members"
_COLUMN = "workflow_id"
_INDEX = "idx_deployment_set_members_workflow_id"
_CONSTRAINT = "check_deployment_set_member_one_ref"

# CHECK constraint expressions — single source of truth.
_CHECK_FOUR_COLS = (
    "(CASE WHEN artifact_uuid IS NOT NULL THEN 1 ELSE 0 END)"
    " + (CASE WHEN group_id IS NOT NULL THEN 1 ELSE 0 END)"
    " + (CASE WHEN member_set_id IS NOT NULL THEN 1 ELSE 0 END)"
    " + (CASE WHEN workflow_id IS NOT NULL THEN 1 ELSE 0 END) = 1"
)
_CHECK_THREE_COLS = (
    "(CASE WHEN artifact_uuid IS NOT NULL THEN 1 ELSE 0 END)"
    " + (CASE WHEN group_id IS NOT NULL THEN 1 ELSE 0 END)"
    " + (CASE WHEN member_set_id IS NOT NULL THEN 1 ELSE 0 END) = 1"
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Idempotency helpers
# ---------------------------------------------------------------------------


def _column_exists(bind: sa.engine.Connection) -> bool:
    """Return True if the workflow_id column already exists on the table."""
    if is_sqlite():
        result = bind.execute(
            text(f"PRAGMA table_info({_TABLE})")
        )
        return any(row[1] == _COLUMN for row in result.fetchall())
    else:
        result = bind.execute(
            text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = :tbl
                  AND column_name = :col
                """
            ),
            {"tbl": _TABLE, "col": _COLUMN},
        )
        return result.fetchone() is not None


def _constraint_has_workflow(bind: sa.engine.Connection) -> bool:
    """Return True if the one-ref CHECK constraint already includes workflow_id."""
    if is_sqlite():
        result = bind.execute(
            text(
                "SELECT sql FROM sqlite_master "
                "WHERE type='table' AND name=:tbl"
            ),
            {"tbl": _TABLE},
        )
        row = result.fetchone()
        create_sql: str = (row[0] or "") if row else ""
        return "workflow_id" in create_sql
    else:
        result = bind.execute(
            text(
                """
                SELECT pg_get_constraintdef(c.oid)
                FROM pg_constraint c
                JOIN pg_class t ON t.oid = c.conrelid
                WHERE c.conname = :cname
                  AND t.relname = :tbl
                  AND c.contype = 'c'
                """
            ),
            {"cname": _CONSTRAINT, "tbl": _TABLE},
        )
        row = result.fetchone()
        constraint_def: str = (row[0] or "") if row else ""
        return "workflow_id" in constraint_def


# ---------------------------------------------------------------------------
# Upgrade helpers
# ---------------------------------------------------------------------------


def _upgrade_add_column_and_index() -> None:
    """Add workflow_id column and its index (both dialects)."""
    op.add_column(
        _TABLE,
        sa.Column(
            _COLUMN,
            sa.String(),
            sa.ForeignKey("workflows.id", ondelete="CASCADE"),
            nullable=True,
            comment="Workflow id (WAW-P1.1)",
        ),
    )
    op.create_index(_INDEX, _TABLE, [_COLUMN])


def _upgrade_constraint_sqlite() -> None:
    """Replace the CHECK constraint on SQLite via batch table rebuild."""
    log.info(
        "add_workflow_id_to_deployment_set_members (SQLite): rebuilding table "
        "to replace CHECK constraint."
    )
    # Disable FK enforcement so that the table-copy does not trigger
    # violations from child tables that reference deployment_set_members.
    op.execute(text("PRAGMA foreign_keys = OFF"))
    try:
        with op.batch_alter_table(_TABLE, recreate="always") as batch_op:
            batch_op.drop_constraint(_CONSTRAINT, type_="check")
            batch_op.create_check_constraint(_CONSTRAINT, _CHECK_FOUR_COLS)
    finally:
        op.execute(text("PRAGMA foreign_keys = ON"))


def _upgrade_constraint_postgresql() -> None:
    """Replace the CHECK constraint on PostgreSQL via ALTER TABLE."""
    log.info(
        "add_workflow_id_to_deployment_set_members (PostgreSQL): replacing "
        "CHECK constraint via ALTER TABLE."
    )
    op.execute(
        text(
            f"ALTER TABLE {_TABLE} DROP CONSTRAINT IF EXISTS {_CONSTRAINT}"
        )
    )
    op.execute(
        text(
            f"ALTER TABLE {_TABLE} ADD CONSTRAINT {_CONSTRAINT} "
            f"CHECK ({_CHECK_FOUR_COLS})"
        )
    )


# ---------------------------------------------------------------------------
# Downgrade helpers
# ---------------------------------------------------------------------------


def _downgrade_constraint_sqlite() -> None:
    """Restore the three-column CHECK constraint on SQLite."""
    log.info(
        "add_workflow_id_to_deployment_set_members (SQLite): restoring "
        "three-column CHECK constraint."
    )
    op.execute(text("PRAGMA foreign_keys = OFF"))
    try:
        with op.batch_alter_table(_TABLE, recreate="always") as batch_op:
            batch_op.drop_constraint(_CONSTRAINT, type_="check")
            batch_op.create_check_constraint(_CONSTRAINT, _CHECK_THREE_COLS)
    finally:
        op.execute(text("PRAGMA foreign_keys = ON"))


def _downgrade_constraint_postgresql() -> None:
    """Restore the three-column CHECK constraint on PostgreSQL."""
    log.info(
        "add_workflow_id_to_deployment_set_members (PostgreSQL): restoring "
        "three-column CHECK constraint."
    )
    op.execute(
        text(
            f"ALTER TABLE {_TABLE} DROP CONSTRAINT IF EXISTS {_CONSTRAINT}"
        )
    )
    op.execute(
        text(
            f"ALTER TABLE {_TABLE} ADD CONSTRAINT {_CONSTRAINT} "
            f"CHECK ({_CHECK_THREE_COLS})"
        )
    )


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    """Add workflow_id column, index, and update the one-ref CHECK constraint."""
    bind = op.get_bind()

    # --- Column + index (both dialects) ---
    if _column_exists(bind):
        log.info(
            "add_workflow_id_to_deployment_set_members: column %r already exists; "
            "skipping add_column.",
            _COLUMN,
        )
    else:
        log.info(
            "add_workflow_id_to_deployment_set_members: adding column %r.", _COLUMN
        )
        _upgrade_add_column_and_index()

    # --- CHECK constraint ---
    if _constraint_has_workflow(bind):
        log.info(
            "add_workflow_id_to_deployment_set_members: CHECK constraint already "
            "includes workflow_id; skipping constraint update."
        )
        return

    if is_sqlite():
        _upgrade_constraint_sqlite()
    elif is_postgresql():
        _upgrade_constraint_postgresql()
    else:
        log.warning(
            "add_workflow_id_to_deployment_set_members: unknown dialect %r; "
            "skipping CHECK constraint update.",
            bind.dialect.name,
        )


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    """Revert CHECK constraint to three-column form and drop workflow_id column.

    WARNING: Any rows with workflow_id IS NOT NULL will violate the restored
    constraint.  Remove or update those rows before running this downgrade.
    """
    bind = op.get_bind()

    # --- Restore CHECK constraint first (column must still exist) ---
    if is_sqlite():
        _downgrade_constraint_sqlite()
    elif is_postgresql():
        _downgrade_constraint_postgresql()
    else:
        log.warning(
            "add_workflow_id_to_deployment_set_members downgrade: unknown dialect %r; "
            "skipping CHECK constraint restore.",
            bind.dialect.name,
        )

    # --- Drop index and column ---
    op.drop_index(_INDEX, table_name=_TABLE)
    op.drop_column(_TABLE, _COLUMN)
