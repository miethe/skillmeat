"""Add share_scope column to memory_items

Revision ID: 20260207_1000_add_share_scope_to_memory_items
Revises: 20260205_1200_add_memory_and_context_tables
Create Date: 2026-02-07 10:00:00.000000+00:00

Adds a share scope field to memory items to support explicit cross-project
sharing semantics.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260207_1000_add_share_scope_to_memory_items"
down_revision: Union[str, None] = "20260205_1200_add_memory_and_context_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add share_scope column with constraint and index."""
    with op.batch_alter_table("memory_items", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "share_scope",
                sa.String(),
                nullable=False,
                server_default="project",
            )
        )
        batch_op.create_check_constraint(
            "ck_memory_items_share_scope",
            "share_scope IN ('private', 'project', 'global_candidate')",
        )
        batch_op.create_index(
            "idx_memory_items_share_scope",
            ["share_scope"],
            unique=False,
        )


def downgrade() -> None:
    """Remove share_scope column, check constraint, and index."""
    with op.batch_alter_table("memory_items", schema=None) as batch_op:
        batch_op.drop_index("idx_memory_items_share_scope")
        batch_op.drop_constraint("ck_memory_items_share_scope", type_="check")
        batch_op.drop_column("share_scope")
