"""add enterprise auth schema: enterprise_users, enterprise_teams, enterprise_team_members, ownership columns

Revision ID: 20260306_004_add_auth_schema_enterprise
Revises: 20260306_003_add_auth_schema_local
Create Date: 2026-03-06 00:04:00.000000+00:00

Background
----------
PRD-2 AAA/RBAC Foundation (DB-005).  This migration extends the enterprise
PostgreSQL schema with three new tables and adds ownership/visibility columns
to the two existing enterprise entity tables.

New tables (dependency order)
------------------------------
1. enterprise_users
       Stores the identity and system-level role for each user within a tenant.
       Maps to the Clerk-managed external identity via ``clerk_user_id``.

2. enterprise_teams
       Named group of enterprise users scoped to a single tenant.

3. enterprise_team_members
       Junction table linking users to teams.  Both FKs carry ON DELETE CASCADE
       so orphaned rows are cleaned up automatically.

New columns on existing tables
-------------------------------
enterprise_artifacts:
    owner_id   UUID nullable — UUID of the owning user/team.
    owner_type VARCHAR(20) nullable, default 'user'.
    visibility VARCHAR(20) nullable, default 'private'.

enterprise_collections:
    owner_id, owner_type, visibility — same semantics as above.

Indexes
-------
All new table indexes use op.create_index().  The owner_id indexes on the
existing tables likewise use op.create_index().

Downgrade order
---------------
1. Drop owner_id index + columns from enterprise_collections
2. Drop owner_id index + columns from enterprise_artifacts
3. Drop enterprise_team_members (junction table)
4. Drop enterprise_teams
5. Drop enterprise_users

Schema reference
----------------
docs/project_plans/architecture/enterprise-db-schema-v1.md  (PRD-2 §3)
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------

revision: str = "20260306_004_add_auth_schema_enterprise"
down_revision: Union[str, None] = "20260306_003_add_auth_schema_local"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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
    """Create enterprise auth tables and add ownership columns (PostgreSQL only)."""
    if not _is_postgresql():
        return  # No-op for SQLite and any other non-PostgreSQL dialect

    # ------------------------------------------------------------------
    # 1. enterprise_users
    # ------------------------------------------------------------------
    op.create_table(
        "enterprise_users",
        # Identity
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Globally unique user identifier",
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Tenant scope; every query MUST include WHERE tenant_id = ?",
        ),
        # External identity
        sa.Column(
            "clerk_user_id",
            sa.String(255),
            nullable=True,
            comment=(
                "Clerk user_id for the external authentication provider. "
                "NULL for service accounts or before Clerk integration is active. "
                "Unique within a tenant (uq_enterprise_users_tenant_clerk)."
            ),
        ),
        # Contact
        sa.Column(
            "email",
            sa.String(320),
            nullable=True,
            comment=(
                "User email address. "
                "Unique within a tenant (uq_enterprise_users_tenant_email) when set."
            ),
        ),
        sa.Column(
            "display_name",
            sa.String(255),
            nullable=True,
            comment="Human-readable display name shown in the UI",
        ),
        # Role
        sa.Column(
            "role",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'viewer'"),
            comment=(
                "System-wide role; one of UserRole enum values "
                "(viewer, team_member, team_admin, system_admin)"
            ),
        ),
        # Soft-delete
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
            comment="Soft-delete: False = account disabled, row retained for audit",
        ),
        # Audit
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="Timezone-aware creation timestamp; server-generated",
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="Timezone-aware last-modified timestamp; updated by app on every write",
        ),
        sa.Column(
            "created_by",
            sa.String(255),
            nullable=True,
            comment="User ID or 'system'; NULL until PRD-2 AuthContext is fully wired",
        ),
        # Named constraints
        sa.UniqueConstraint(
            "tenant_id",
            "clerk_user_id",
            name="uq_enterprise_users_tenant_clerk",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "email",
            name="uq_enterprise_users_tenant_email",
        ),
    )

    # B-tree indexes on enterprise_users
    op.create_index(
        "idx_enterprise_users_tenant_id",
        "enterprise_users",
        ["tenant_id"],
    )
    op.create_index(
        "idx_enterprise_users_tenant_clerk",
        "enterprise_users",
        ["tenant_id", "clerk_user_id"],
    )
    op.create_index(
        "idx_enterprise_users_tenant_email",
        "enterprise_users",
        ["tenant_id", "email"],
    )
    op.create_index(
        "idx_enterprise_users_tenant_role",
        "enterprise_users",
        ["tenant_id", "role"],
    )

    # ------------------------------------------------------------------
    # 2. enterprise_teams
    # ------------------------------------------------------------------
    op.create_table(
        "enterprise_teams",
        # Identity
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Globally unique team identifier",
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Tenant scope; every query MUST include WHERE tenant_id = ?",
        ),
        # Core metadata
        sa.Column(
            "name",
            sa.String(255),
            nullable=False,
            comment="Human-readable team name; unique within a tenant",
        ),
        sa.Column(
            "description",
            sa.Text,
            nullable=True,
            comment="Optional free-text description of the team's purpose",
        ),
        # Soft-delete
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
            comment="Soft-delete: False = team dissolved, row retained for audit",
        ),
        # Audit
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="Timezone-aware creation timestamp",
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="Timezone-aware last-modified timestamp; updated on every write",
        ),
        sa.Column(
            "created_by",
            sa.String(255),
            nullable=True,
            comment="User ID or 'system'; NULL until PRD-2 AuthContext is fully wired",
        ),
        # Named constraints
        sa.UniqueConstraint(
            "tenant_id",
            "name",
            name="uq_enterprise_teams_tenant_name",
        ),
    )

    # B-tree indexes on enterprise_teams
    op.create_index(
        "idx_enterprise_teams_tenant_id",
        "enterprise_teams",
        ["tenant_id"],
    )
    op.create_index(
        "idx_enterprise_teams_tenant_name",
        "enterprise_teams",
        ["tenant_id", "name"],
    )

    # ------------------------------------------------------------------
    # 3. enterprise_team_members
    # ------------------------------------------------------------------
    op.create_table(
        "enterprise_team_members",
        # Identity
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Globally unique membership row identifier",
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment=(
                "Denormalized tenant scope for query performance; "
                "must equal the parent team's tenant_id — validated at write time"
            ),
        ),
        # Foreign keys
        sa.Column(
            "team_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "enterprise_teams.id",
                ondelete="CASCADE",
                name="fk_enterprise_team_members_team_id",
            ),
            nullable=False,
            comment="Parent team; cascade-deletes this membership when team is removed",
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "enterprise_users.id",
                ondelete="CASCADE",
                name="fk_enterprise_team_members_user_id",
            ),
            nullable=False,
            comment="Member user; cascade-deletes this membership when user is removed",
        ),
        # Team-level role
        sa.Column(
            "role",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'team_member'"),
            comment="Role within the team; one of team_admin, team_member",
        ),
        # Audit — joined_at is immutable (no onupdate)
        sa.Column(
            "joined_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="Timezone-aware timestamp when the user joined the team; immutable",
        ),
        sa.Column(
            "created_by",
            sa.String(255),
            nullable=True,
            comment="User ID or 'system'; NULL until PRD-2 AuthContext is fully wired",
        ),
        # Named constraints
        sa.UniqueConstraint(
            "tenant_id",
            "team_id",
            "user_id",
            name="uq_enterprise_team_members_tenant_team_user",
        ),
    )

    # B-tree indexes on enterprise_team_members
    op.create_index(
        "idx_enterprise_team_members_tenant_id",
        "enterprise_team_members",
        ["tenant_id"],
    )
    op.create_index(
        "idx_enterprise_team_members_team_id",
        "enterprise_team_members",
        ["team_id"],
    )
    op.create_index(
        "idx_enterprise_team_members_user_id",
        "enterprise_team_members",
        ["user_id"],
    )

    # ------------------------------------------------------------------
    # 4. Add owner_id / owner_type / visibility to enterprise_artifacts
    # ------------------------------------------------------------------
    op.add_column(
        "enterprise_artifacts",
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="UUID of the user who owns this artifact; NULL = system/unowned",
        ),
    )
    op.add_column(
        "enterprise_artifacts",
        sa.Column(
            "owner_type",
            sa.String(20),
            nullable=True,
            server_default=sa.text("'user'"),
            comment="Owner type; stores OwnerType enum value, e.g. 'user' or 'team'",
        ),
    )
    op.add_column(
        "enterprise_artifacts",
        sa.Column(
            "visibility",
            sa.String(20),
            nullable=True,
            server_default=sa.text("'private'"),
            comment=(
                "Visibility level; stores Visibility enum value, "
                "e.g. 'private', 'internal', 'public'"
            ),
        ),
    )
    op.create_index(
        "ix_enterprise_artifacts_owner_id",
        "enterprise_artifacts",
        ["owner_id"],
    )

    # ------------------------------------------------------------------
    # 5. Add owner_id / owner_type / visibility to enterprise_collections
    # ------------------------------------------------------------------
    op.add_column(
        "enterprise_collections",
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="UUID of the user who owns this collection; NULL = system/unowned",
        ),
    )
    op.add_column(
        "enterprise_collections",
        sa.Column(
            "owner_type",
            sa.String(20),
            nullable=True,
            server_default=sa.text("'user'"),
            comment="Owner type; stores OwnerType enum value, e.g. 'user' or 'team'",
        ),
    )
    op.add_column(
        "enterprise_collections",
        sa.Column(
            "visibility",
            sa.String(20),
            nullable=True,
            server_default=sa.text("'private'"),
            comment=(
                "Visibility level; stores Visibility enum value, "
                "e.g. 'private', 'internal', 'public'"
            ),
        ),
    )
    op.create_index(
        "ix_enterprise_collections_owner_id",
        "enterprise_collections",
        ["owner_id"],
    )


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    """Drop enterprise auth tables and remove ownership columns (PostgreSQL only)."""
    if not _is_postgresql():
        return  # No-op for SQLite and any other non-PostgreSQL dialect

    # ------------------------------------------------------------------
    # 5 (reversed). Drop ownership columns from enterprise_collections
    # ------------------------------------------------------------------
    op.drop_index("ix_enterprise_collections_owner_id", table_name="enterprise_collections")
    op.drop_column("enterprise_collections", "visibility")
    op.drop_column("enterprise_collections", "owner_type")
    op.drop_column("enterprise_collections", "owner_id")

    # ------------------------------------------------------------------
    # 4 (reversed). Drop ownership columns from enterprise_artifacts
    # ------------------------------------------------------------------
    op.drop_index("ix_enterprise_artifacts_owner_id", table_name="enterprise_artifacts")
    op.drop_column("enterprise_artifacts", "visibility")
    op.drop_column("enterprise_artifacts", "owner_type")
    op.drop_column("enterprise_artifacts", "owner_id")

    # ------------------------------------------------------------------
    # 3 (reversed). Drop enterprise_team_members
    # ------------------------------------------------------------------
    op.drop_index(
        "idx_enterprise_team_members_user_id",
        table_name="enterprise_team_members",
    )
    op.drop_index(
        "idx_enterprise_team_members_team_id",
        table_name="enterprise_team_members",
    )
    op.drop_index(
        "idx_enterprise_team_members_tenant_id",
        table_name="enterprise_team_members",
    )
    op.drop_table("enterprise_team_members")

    # ------------------------------------------------------------------
    # 2 (reversed). Drop enterprise_teams
    # ------------------------------------------------------------------
    op.drop_index(
        "idx_enterprise_teams_tenant_name",
        table_name="enterprise_teams",
    )
    op.drop_index(
        "idx_enterprise_teams_tenant_id",
        table_name="enterprise_teams",
    )
    op.drop_table("enterprise_teams")

    # ------------------------------------------------------------------
    # 1 (reversed). Drop enterprise_users
    # ------------------------------------------------------------------
    op.drop_index(
        "idx_enterprise_users_tenant_role",
        table_name="enterprise_users",
    )
    op.drop_index(
        "idx_enterprise_users_tenant_email",
        table_name="enterprise_users",
    )
    op.drop_index(
        "idx_enterprise_users_tenant_clerk",
        table_name="enterprise_users",
    )
    op.drop_index(
        "idx_enterprise_users_tenant_id",
        table_name="enterprise_users",
    )
    op.drop_table("enterprise_users")
