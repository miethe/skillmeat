"""add supplementary auth indexes: owner_id on entity tables, enterprise_team_members composites

Revision ID: 20260306_006_add_auth_indexes_constraints
Revises: 20260306_005_populate_local_admin_defaults
Create Date: 2026-03-06 00:06:00.000000+00:00

Background
----------
PRD-2 AAA/RBAC Foundation (DB-007).  This migration adds supplementary indexes
that were intentionally deferred from the initial auth schema migrations
(003 and 004) to keep those migrations focused on table/column creation.

What already exists (do NOT re-create)
---------------------------------------
Migration 003 (local) already created:
  - idx_team_members_team_id  on team_members(team_id)
  - idx_team_members_user_id  on team_members(user_id)

Migration 004 (enterprise) already created:
  - ix_enterprise_artifacts_owner_id    on enterprise_artifacts(owner_id)
  - ix_enterprise_collections_owner_id  on enterprise_collections(owner_id)
  - idx_enterprise_team_members_tenant_id  on enterprise_team_members(tenant_id)
  - idx_enterprise_team_members_team_id    on enterprise_team_members(team_id)
  - idx_enterprise_team_members_user_id    on enterprise_team_members(user_id)

What this migration adds
-------------------------
Local (SQLite) — via batch_alter_table (required for SQLite ALTER TABLE):
  1. ix_artifacts_owner_id     on artifacts(owner_id)
  2. ix_collections_owner_id   on collections(owner_id)
  3. ix_projects_owner_id      on projects(owner_id)
  4. ix_groups_owner_id        on groups(owner_id)

Enterprise (PostgreSQL) — composite indexes for membership lookup patterns:
  5. ix_enterprise_team_members_tenant_team  on enterprise_team_members(tenant_id, team_id)
  6. ix_enterprise_team_members_tenant_user  on enterprise_team_members(tenant_id, user_id)

Downgrade order
---------------
1. Drop enterprise composite indexes (PostgreSQL only)
2. Drop local owner_id indexes from groups, projects, collections, artifacts
   (batch_alter_table each, reverse order)

Schema reference
----------------
docs/project_plans/architecture/enterprise-db-schema-v1.md  (PRD-2 §3)
.claude/progress/aaa-rbac-foundation/phase-1-progress.md    (DB-007)
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------

revision: str = "20260306_006_add_auth_indexes_constraints"
down_revision: Union[str, None] = "20260306_005_populate_local_admin_defaults"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Local (SQLite) entity tables that received owner_id in migration 003 but
# did not get a corresponding index at that time.
_LOCAL_OWNERSHIP_TABLES = ("artifacts", "collections", "projects", "groups")


# ---------------------------------------------------------------------------
# Dialect helpers
# ---------------------------------------------------------------------------


def _dialect_name() -> str:
    """Return the lowercase dialect name for the current connection."""
    return op.get_bind().dialect.name


def _is_postgresql() -> bool:
    return _dialect_name() == "postgresql"


def _is_sqlite() -> bool:
    return _dialect_name() == "sqlite"


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    """Add supplementary owner_id and team-member indexes."""

    # ------------------------------------------------------------------
    # Local (SQLite) — owner_id indexes on the four entity tables.
    #
    # batch_alter_table is required for SQLite because the standard
    # CREATE INDEX statement outside of a table rewrite is not supported
    # for columns that were added via batch operations in a prior migration.
    # We use it here for consistency and SQLite compatibility even though
    # CREATE INDEX alone would work on most SQLite builds; batch mode
    # guarantees correctness across all supported SQLite versions.
    # ------------------------------------------------------------------
    if _is_sqlite():
        for table_name in _LOCAL_OWNERSHIP_TABLES:
            with op.batch_alter_table(table_name) as batch_op:
                batch_op.create_index(
                    f"ix_{table_name}_owner_id",
                    ["owner_id"],
                )

    # ------------------------------------------------------------------
    # Enterprise (PostgreSQL) — composite indexes on enterprise_team_members.
    #
    # These two composite indexes support the two most common membership
    # lookup patterns:
    #   - "all members of a team within a tenant"   → (tenant_id, team_id)
    #   - "all teams a user belongs to in a tenant" → (tenant_id, user_id)
    #
    # The single-column indexes (team_id, user_id, tenant_id) already exist
    # from migration 004; these composites eliminate index merges for the
    # scoped lookup queries that include tenant_id in every WHERE clause.
    # ------------------------------------------------------------------
    if _is_postgresql():
        op.create_index(
            "ix_enterprise_team_members_tenant_team",
            "enterprise_team_members",
            ["tenant_id", "team_id"],
        )
        op.create_index(
            "ix_enterprise_team_members_tenant_user",
            "enterprise_team_members",
            ["tenant_id", "user_id"],
        )


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    """Drop all indexes added by this migration."""

    # ------------------------------------------------------------------
    # Enterprise composite indexes (drop before local to mirror upgrade order)
    # ------------------------------------------------------------------
    if _is_postgresql():
        op.drop_index(
            "ix_enterprise_team_members_tenant_user",
            table_name="enterprise_team_members",
        )
        op.drop_index(
            "ix_enterprise_team_members_tenant_team",
            table_name="enterprise_team_members",
        )

    # ------------------------------------------------------------------
    # Local owner_id indexes — reverse table order for symmetry.
    # ------------------------------------------------------------------
    if _is_sqlite():
        for table_name in reversed(_LOCAL_OWNERSHIP_TABLES):
            with op.batch_alter_table(table_name) as batch_op:
                batch_op.drop_index(f"ix_{table_name}_owner_id")
