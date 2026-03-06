"""add auth schema: users, teams, team_members tables and ownership columns

Revision ID: 20260306_003_add_auth_schema_local
Revises: 20260306_002_add_tenant_isolation
Create Date: 2026-03-06 00:03:00.000000+00:00

Background
----------
PRD-2 AAA/RBAC Foundation — DB-004.

This migration is the local-mode (SQLite) counterpart to the enterprise schema
migrations.  It introduces three new authentication/RBAC tables and adds
ownership + visibility columns to the four core entity tables.

New tables (dependency order)
------------------------------
1. users
       Local user accounts; one auto-created admin row at startup.
       Integer PK, optional Clerk external_id, system-wide role string.

2. teams
       Named groups for collaborative artifact management.
       Integer PK, unique name, soft-delete via is_active.

3. team_members
       Junction table: one row per (team, user) membership pair.
       FK → teams.id ON DELETE CASCADE.
       FK → users.id ON DELETE CASCADE.
       Unique constraint on (team_id, user_id).

New columns on existing tables
-------------------------------
Four tables receive identical ownership + visibility columns:
  - artifacts
  - collections
  - projects
  - groups

Columns added to each:
  - owner_id    (String, nullable) — FK-free string reference to users.id or
                a team identifier; kept as String for flexibility across
                local/enterprise modes.
  - owner_type  (String, nullable, default "user") — discriminator for owner_id;
                one of "user", "team".
  - visibility  (String, nullable, default "private") — one of "private",
                "internal", "public".

SQLite compatibility
--------------------
All ALTER TABLE operations use ``op.batch_alter_table()`` because SQLite does
not support ADD COLUMN with constraints in the standard ALTER TABLE path.
Alembic's batch mode rewrites the table, which is safe for the table sizes
expected in local mode.

Downgrade order
---------------
1. Drop owner_id / owner_type / visibility from groups, projects, collections,
   artifacts (batch_alter_table each).
2. Drop team_members (FK child).
3. Drop teams.
4. Drop users.

Schema reference
----------------
.claude/progress/aaa-rbac-foundation/phase-1-progress.md  (DB-004)
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------

revision: str = "20260306_003_add_auth_schema_local"
down_revision: Union[str, None] = "20260306_002_add_tenant_isolation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Tables that receive the ownership + visibility columns.
_OWNERSHIP_TABLES = ("artifacts", "collections", "projects", "groups")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _add_ownership_columns(batch_op: object) -> None:
    """Add owner_id, owner_type, visibility to a table via a batch op."""
    batch_op.add_column(
        sa.Column(
            "owner_id",
            sa.String(),
            nullable=True,
            comment=(
                "String reference to the owning user (int PK as str) or team name; "
                "NULL until the auth layer is active"
            ),
        )
    )
    batch_op.add_column(
        sa.Column(
            "owner_type",
            sa.String(50),
            nullable=True,
            server_default="user",
            comment="Discriminator for owner_id: 'user' or 'team'",
        )
    )
    batch_op.add_column(
        sa.Column(
            "visibility",
            sa.String(50),
            nullable=True,
            server_default="private",
            comment="Visibility scope: 'private', 'internal', or 'public'",
        )
    )


def _drop_ownership_columns(batch_op: object) -> None:
    """Drop owner_id, owner_type, visibility from a table via a batch op."""
    batch_op.drop_column("visibility")
    batch_op.drop_column("owner_type")
    batch_op.drop_column("owner_id")


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    """Create auth tables and add ownership columns to core entity tables."""

    # ------------------------------------------------------------------
    # 1. users
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
            comment="Auto-increment integer primary key",
        ),
        sa.Column(
            "external_id",
            sa.String(255),
            nullable=True,
            unique=True,
            comment="External identity provider ID (e.g. Clerk user_id); unique when set",
        ),
        sa.Column(
            "email",
            sa.String(320),
            nullable=True,
            comment="User email address; not enforced unique in local mode",
        ),
        sa.Column(
            "display_name",
            sa.String(255),
            nullable=True,
            comment="Human-readable display name shown in the UI",
        ),
        sa.Column(
            "role",
            sa.String(50),
            nullable=False,
            server_default="viewer",
            comment=(
                "System-wide role; one of viewer, team_member, team_admin, system_admin"
            ),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="1",
            comment="When False the account is disabled; row is retained for audit",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="UTC creation timestamp",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=True,
            comment="UTC last-modified timestamp; updated by app on every write",
        ),
    )

    op.create_index("idx_users_external_id", "users", ["external_id"])
    op.create_index("idx_users_email", "users", ["email"])
    op.create_index("idx_users_role", "users", ["role"])

    # ------------------------------------------------------------------
    # 2. teams
    # ------------------------------------------------------------------
    op.create_table(
        "teams",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
            comment="Auto-increment integer primary key",
        ),
        sa.Column(
            "name",
            sa.String(255),
            nullable=False,
            unique=True,
            comment="Unique human-readable team name",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Optional description of the team's purpose",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="1",
            comment="When False the team is dissolved but rows are retained for audit",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="UTC creation timestamp",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=True,
            comment="UTC last-modified timestamp",
        ),
    )

    op.create_index("idx_teams_name", "teams", ["name"])
    op.create_index("idx_teams_is_active", "teams", ["is_active"])

    # ------------------------------------------------------------------
    # 3. team_members
    # ------------------------------------------------------------------
    op.create_table(
        "team_members",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
            comment="Auto-increment integer primary key",
        ),
        sa.Column(
            "team_id",
            sa.Integer(),
            sa.ForeignKey("teams.id", ondelete="CASCADE", name="fk_team_members_team_id"),
            nullable=False,
            comment="Parent team; cascade-deletes this membership when team is removed",
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_team_members_user_id"),
            nullable=False,
            comment="Member user; cascade-deletes this membership when user is removed",
        ),
        sa.Column(
            "role",
            sa.String(50),
            nullable=False,
            server_default="team_member",
            comment="Role within the team; one of team_admin, team_member",
        ),
        sa.Column(
            "joined_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="UTC timestamp when the user joined the team",
        ),
        sa.UniqueConstraint(
            "team_id",
            "user_id",
            name="uq_team_members_team_user",
        ),
    )

    op.create_index("idx_team_members_team_id", "team_members", ["team_id"])
    op.create_index("idx_team_members_user_id", "team_members", ["user_id"])

    # ------------------------------------------------------------------
    # 4. Add ownership + visibility columns to existing tables.
    #
    # op.batch_alter_table() is required for SQLite because the standard
    # ALTER TABLE ... ADD COLUMN with constraints is not supported.  Alembic
    # rewrites the table behind the scenes, which is safe for local-mode
    # data volumes.
    # ------------------------------------------------------------------
    for table_name in _OWNERSHIP_TABLES:
        with op.batch_alter_table(table_name) as batch_op:
            _add_ownership_columns(batch_op)


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    """Drop ownership columns from core entity tables and remove auth tables."""

    # ------------------------------------------------------------------
    # 1. Remove ownership columns from existing tables (reverse table order
    #    for a clean rollback story, though the order here is not critical).
    # ------------------------------------------------------------------
    for table_name in reversed(_OWNERSHIP_TABLES):
        with op.batch_alter_table(table_name) as batch_op:
            _drop_ownership_columns(batch_op)

    # ------------------------------------------------------------------
    # 2. Drop team_members first (holds FKs to both teams and users).
    # ------------------------------------------------------------------
    op.drop_index("idx_team_members_user_id", table_name="team_members")
    op.drop_index("idx_team_members_team_id", table_name="team_members")
    op.drop_table("team_members")

    # ------------------------------------------------------------------
    # 3. Drop teams.
    # ------------------------------------------------------------------
    op.drop_index("idx_teams_is_active", table_name="teams")
    op.drop_index("idx_teams_name", table_name="teams")
    op.drop_table("teams")

    # ------------------------------------------------------------------
    # 4. Drop users.
    # ------------------------------------------------------------------
    op.drop_index("idx_users_role", table_name="users")
    op.drop_index("idx_users_email", table_name="users")
    op.drop_index("idx_users_external_id", table_name="users")
    op.drop_table("users")
