"""add tenant_id to collections table for tenant isolation

Revision ID: ent_002_tenant_isolation
Revises: ent_001_enterprise_schema
Create Date: 2026-03-06 00:02:00.000000+00:00

Background
----------
ENT-1.8: Only the `collections` table (the existing shared SQLite/PostgreSQL
cache table) requires a tenant_id column.  All other shared tables
(artifacts, projects, marketplace, groups, memory_items, workflow_*) are
either local-only or unaffected per the analysis in Section 7 of the
enterprise schema doc.

This migration is a no-op on any non-PostgreSQL dialect (SQLite).

Migration strategy
------------------
Adding NOT NULL to an existing table with rows requires a three-step approach:

1. Add column as nullable with a server_default so the DB fills it for any
   concurrent inserts during the migration window.
2. Backfill existing NULL rows to DEFAULT_TENANT_ID
   (00000000-0000-4000-a000-000000000001).
3. Alter column to NOT NULL — safe because step 2 guarantees no NULLs remain.

A plain B-tree index on tenant_id is added last to accelerate the per-tenant
WHERE clauses that all web queries must include.

Downgrade order
---------------
1. Drop index idx_collections_tenant_id
2. Drop column tenant_id from collections

Schema reference
----------------
docs/project_plans/architecture/enterprise-db-schema-v1.md  (Section 7)
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------

revision: str = "ent_002_tenant_isolation"
down_revision: Union[str, None] = "ent_001_enterprise_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Deterministic default tenant UUID (mirrors cache.constants.DEFAULT_TENANT_ID)
_DEFAULT_TENANT_ID = "00000000-0000-4000-a000-000000000001"


# ---------------------------------------------------------------------------
# Dialect guard
# ---------------------------------------------------------------------------


def _is_postgresql() -> bool:
    """Return True when the migration is running against a PostgreSQL database."""
    bind = op.get_bind()
    return bind.dialect.name == "postgresql"


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    """Add tenant_id to the collections table (PostgreSQL only)."""
    if not _is_postgresql():
        return  # No-op for SQLite and any other non-PostgreSQL dialect

    # ------------------------------------------------------------------
    # Step 1: Add tenant_id as nullable with a server_default.
    #
    # server_default fills the column for any rows inserted concurrently
    # during the migration window before step 3 makes it NOT NULL.
    # Using nullable=True here avoids a full table rewrite on Postgres for
    # tables that already contain rows (Postgres adds a nullable column
    # with a server_default as a metadata-only operation in PG 11+).
    # ------------------------------------------------------------------
    op.add_column(
        "collections",
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            server_default=_DEFAULT_TENANT_ID,
            comment=(
                "Tenant scope; backfilled to DEFAULT_TENANT_ID for all "
                "pre-existing rows. Every query MUST include WHERE tenant_id = ?."
            ),
        ),
    )

    # ------------------------------------------------------------------
    # Step 2: Backfill existing rows that predate this migration.
    #
    # The server_default handles new inserts; this UPDATE covers rows
    # that were written before the column existed.
    # ------------------------------------------------------------------
    op.execute(
        "UPDATE collections "
        f"SET tenant_id = '{_DEFAULT_TENANT_ID}' "
        "WHERE tenant_id IS NULL"
    )

    # ------------------------------------------------------------------
    # Step 3: Enforce NOT NULL now that all rows are populated.
    # ------------------------------------------------------------------
    op.alter_column("collections", "tenant_id", nullable=False)

    # ------------------------------------------------------------------
    # Step 4: B-tree index for per-tenant query performance.
    #
    # A plain op.create_index() is used here (not CONCURRENTLY) because
    # we are already inside a DDL transaction.  For zero-downtime
    # production deployments this index should be created separately with
    # CREATE INDEX CONCURRENTLY before applying the NOT NULL constraint;
    # the migration handles the common case (initial setup / dev / CI).
    # ------------------------------------------------------------------
    op.create_index(
        "idx_collections_tenant_id",
        "collections",
        ["tenant_id"],
    )


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    """Remove tenant_id from the collections table (PostgreSQL only)."""
    if not _is_postgresql():
        return  # No-op for SQLite and any other non-PostgreSQL dialect

    # Drop index before dropping column (required by Postgres).
    op.drop_index("idx_collections_tenant_id", table_name="collections")

    op.drop_column("collections", "tenant_id")
