"""Add deployment_sets and deployment_set_members tables (deployment-sets-v1).

Revision ID: 20260224_1000_add_deployment_set_tables
Revises: 20260222_1100_add_description_to_deployment_profiles
Create Date: 2026-02-24 10:00:00.000000+00:00

Background
----------
Part of the deployment-sets feature (DS-001).  A DeploymentSet groups
collection artifacts, artifact groups, and/or nested deployment sets into
a single batch-deployable unit.  Membership is recorded in the sibling
``deployment_set_members`` table using a polymorphic reference: exactly one
of ``artifact_uuid``, ``group_id``, or ``member_set_id`` must be non-null
per row (enforced by a CHECK constraint).

Tables created
--------------
1. ``deployment_sets``
   - ``id`` (String, primary key, UUID hex)
   - ``name`` (String(255), non-null)
   - ``description`` (Text, nullable)
   - ``tags_json`` (Text, non-null, server_default ``"[]"``) — JSON list of strings
   - ``owner_id`` (String, non-null) — multi-user scoping
   - ``created_at`` / ``updated_at`` (DateTime, non-null)
   - CheckConstraint: ``length(name) > 0 AND length(name) <= 255``
   - Indexes: ``idx_deployment_sets_owner_id``,
              ``idx_deployment_sets_created_at``

2. ``deployment_set_members``
   - ``id`` (String, primary key, UUID hex)
   - ``set_id`` → ``deployment_sets.id`` ON DELETE CASCADE (non-null)
   - ``artifact_uuid`` (String, nullable) — collection artifact UUID
   - ``group_id`` (String, nullable) — artifact group id
   - ``member_set_id`` → ``deployment_sets.id`` ON DELETE SET NULL (nullable)
   - ``position`` (Integer, non-null, server_default ``0``)
   - ``created_at`` (DateTime, non-null)
   - CheckConstraint: exactly one of the three ref columns is non-null
     (SQLite-compatible integer coercion of boolean IS NOT NULL expressions)
   - CheckConstraint: ``position >= 0``
   - Indexes: ``idx_deployment_set_members_set_id``,
              ``idx_deployment_set_members_member_set_id``,
              ``idx_deployment_set_members_set_position`` (composite)

Rollback
--------
Drop ``deployment_set_members`` first (holds FKs back to
``deployment_sets``), then drop ``deployment_sets``.  No other tables or
columns are modified.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


# revision identifiers, used by Alembic.
revision: str = "20260224_1000_add_deployment_set_tables"
down_revision: Union[str, None] = "20260222_1100_add_description_to_deployment_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create deployment_sets then deployment_set_members tables.

    Order matters: ``deployment_sets`` must exist before
    ``deployment_set_members`` can declare its FKs back to that table.
    Both tables are net-new additions; no existing tables are modified.
    """
    # Check if tables already exist (e.g., via Base.metadata.create_all())
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    existing_tables = inspector.get_table_names()

    # -------------------------------------------------------------------------
    # 1. deployment_sets
    # -------------------------------------------------------------------------
    if "deployment_sets" not in existing_tables:
        op.create_table(
            "deployment_sets",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column(
                "tags_json",
                sa.Text(),
                nullable=False,
                server_default="[]",
                comment="JSON-serialized list of tag strings",
            ),
            sa.Column(
                "owner_id",
                sa.String(),
                nullable=False,
                comment="Owning user / identity scope for multi-user isolation",
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.CheckConstraint(
                "length(name) > 0 AND length(name) <= 255",
                name="check_deployment_set_name_length",
            ),
        )

        op.create_index(
            "idx_deployment_sets_owner_id",
            "deployment_sets",
            ["owner_id"],
        )
        op.create_index(
            "idx_deployment_sets_created_at",
            "deployment_sets",
            ["created_at"],
        )

    # -------------------------------------------------------------------------
    # 2. deployment_set_members
    # -------------------------------------------------------------------------
    # NOTE: member_set_id uses ON DELETE SET NULL because removing a nested
    # set should leave the member row in place (pointing at nothing) rather
    # than silently deleting it from the parent set — callers can then clean
    # up orphaned members explicitly.  set_id uses ON DELETE CASCADE so that
    # deleting the owning set removes all its member rows atomically.
    if "deployment_set_members" not in existing_tables:
        op.create_table(
            "deployment_set_members",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column(
                "set_id",
                sa.String(),
                sa.ForeignKey("deployment_sets.id", ondelete="CASCADE"),
                nullable=False,
                comment="FK to deployment_sets.id — CASCADE DELETE",
            ),
            sa.Column(
                "artifact_uuid",
                sa.String(),
                nullable=True,
                comment="Collection artifact UUID (ADR-007 stable identity); one-of-three",
            ),
            sa.Column(
                "group_id",
                sa.String(),
                nullable=True,
                comment="Artifact group id; one-of-three",
            ),
            sa.Column(
                "member_set_id",
                sa.String(),
                sa.ForeignKey("deployment_sets.id", ondelete="SET NULL"),
                nullable=True,
                comment="Nested deployment set id for hierarchical sets; one-of-three",
            ),
            sa.Column(
                "position",
                sa.Integer(),
                nullable=False,
                server_default="0",
                comment="Display/deployment order within the set (0-based)",
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            # Exactly one of the three polymorphic ref columns must be non-null.
            # SQLite coerces (col IS NOT NULL) to 0 or 1, so summing three such
            # expressions and asserting = 1 enforces the one-of-three invariant
            # without requiring a generated/computed column.
            sa.CheckConstraint(
                "(artifact_uuid IS NOT NULL) + (group_id IS NOT NULL)"
                " + (member_set_id IS NOT NULL) = 1",
                name="check_deployment_set_member_one_ref",
            ),
            sa.CheckConstraint(
                "position >= 0",
                name="check_deployment_set_member_position",
            ),
        )

        op.create_index(
            "idx_deployment_set_members_set_id",
            "deployment_set_members",
            ["set_id"],
        )
        op.create_index(
            "idx_deployment_set_members_member_set_id",
            "deployment_set_members",
            ["member_set_id"],
        )
        # Composite index for ordered retrieval within a parent set
        op.create_index(
            "idx_deployment_set_members_set_position",
            "deployment_set_members",
            ["set_id", "position"],
        )


def downgrade() -> None:
    """Drop deployment_set_members then deployment_sets.

    Tables are dropped in reverse dependency order: the child table
    (deployment_set_members) is dropped first so its FKs to deployment_sets
    are removed before the parent table is dropped.  All deployment set data
    and member associations will be permanently lost.
    """
    # Drop child table first (holds FKs back to deployment_sets)
    op.drop_index("idx_deployment_set_members_set_position", "deployment_set_members")
    op.drop_index("idx_deployment_set_members_member_set_id", "deployment_set_members")
    op.drop_index("idx_deployment_set_members_set_id", "deployment_set_members")
    op.drop_table("deployment_set_members")

    # Drop parent table last
    op.drop_index("idx_deployment_sets_created_at", "deployment_sets")
    op.drop_index("idx_deployment_sets_owner_id", "deployment_sets")
    op.drop_table("deployment_sets")
