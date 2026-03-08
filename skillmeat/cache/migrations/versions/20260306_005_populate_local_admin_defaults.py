"""Populate local_admin user and backfill ownership on existing rows

Revision ID: 20260306_005_populate_local_admin_defaults
Revises: 20260306_004_add_auth_schema_enterprise
Create Date: 2026-03-06 00:05:00.000000+00:00

Background
----------
PRD-2 AAA/RBAC Foundation — DB-006.

This migration is a data migration that runs only in local (SQLite) mode.
It performs two operations:

1. Insert the implicit local_admin user row into the ``users`` table.
   The user carries a deterministic UUID as its ``external_id`` so it can be
   correlated across restarts.  The integer PK is 1 (first row).

2. Backfill ownership columns on existing rows in the four core entity tables:
   artifacts, collections, projects, groups.
   Rows whose ``owner_id`` is currently NULL are stamped with owner_id = '1'
   (the local_admin integer PK expressed as a string), owner_type = 'user',
   and visibility = 'private'.

Guard
-----
Both upgrade() and downgrade() are no-ops on non-SQLite dialects.  Enterprise
(PostgreSQL) deployments manage their own user-provisioning separately.

Schema reference
----------------
.claude/progress/aaa-rbac-foundation/phase-1-progress.md  (DB-006)
skillmeat/cache/constants.py  (LOCAL_ADMIN_USER_ID)
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------

revision: str = "20260306_005_populate_local_admin_defaults"
down_revision: Union[str, None] = "20260306_004_add_auth_schema_enterprise"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Matches skillmeat/cache/constants.py :: LOCAL_ADMIN_USER_ID
_LOCAL_ADMIN_EXTERNAL_ID = "00000000-0000-4000-a000-000000000002"

# Integer PK that will be assigned to the local_admin row.
# Expressed as a string because owner_id columns are String type.
_LOCAL_ADMIN_PK = "1"

# Tables that receive the ownership backfill.
_OWNERSHIP_TABLES = ("artifacts", "collections", "projects", "groups")


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    """Insert local_admin user and backfill ownership on existing rows."""

    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        return

    # ------------------------------------------------------------------
    # 1. Insert the local_admin user.
    #
    # We use INSERT OR IGNORE so the migration is idempotent — re-running it
    # after a partial failure will not raise a duplicate-key error.
    # The id column is an INTEGER PRIMARY KEY in SQLite; supplying id = 1
    # pins the row to a known, stable PK that the backfill step below relies on.
    # ------------------------------------------------------------------
    bind.execute(
        sa.text(
            """
            INSERT OR IGNORE INTO users
                (id, external_id, email, display_name, role, is_active)
            VALUES
                (1, :external_id, 'local@localhost', 'Local Admin', 'system_admin', 1)
            """
        ),
        {"external_id": _LOCAL_ADMIN_EXTERNAL_ID},
    )

    # ------------------------------------------------------------------
    # 2. Backfill ownership on existing entity rows.
    #
    # Only rows where owner_id IS NULL are touched so the migration is safe
    # to run even if partial backfills have already been applied.
    # ------------------------------------------------------------------
    for table in _OWNERSHIP_TABLES:
        bind.execute(
            sa.text(
                f"""
                UPDATE {table}
                SET
                    owner_id   = :owner_id,
                    owner_type = 'user',
                    visibility = 'private'
                WHERE owner_id IS NULL
                """  # noqa: S608 — table name is from a trusted internal constant
            ),
            {"owner_id": _LOCAL_ADMIN_PK},
        )


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    """Remove the local_admin user and clear ownership columns."""

    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        return

    # ------------------------------------------------------------------
    # 1. Clear ownership columns on all four entity tables.
    #    Set back to NULL to restore the pre-migration state.
    # ------------------------------------------------------------------
    for table in _OWNERSHIP_TABLES:
        bind.execute(
            sa.text(
                f"""
                UPDATE {table}
                SET
                    owner_id   = NULL,
                    owner_type = NULL,
                    visibility = NULL
                WHERE owner_id = :owner_id
                """  # noqa: S608
            ),
            {"owner_id": _LOCAL_ADMIN_PK},
        )

    # ------------------------------------------------------------------
    # 2. Delete the local_admin user row.
    # ------------------------------------------------------------------
    bind.execute(
        sa.text("DELETE FROM users WHERE external_id = :external_id"),
        {"external_id": _LOCAL_ADMIN_EXTERNAL_ID},
    )
