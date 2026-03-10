"""Add artifacts.target_platforms and deployment_profiles table.

Revision ID: 20260207_1400_add_deployment_profiles_and_target_platforms
Revises: 20260207_1000_add_share_scope_to_memory_items
Create Date: 2026-02-07 14:00:00.000000+00:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260207_1400_add_deployment_profiles_and_target_platforms"
down_revision: Union[str, None] = "20260207_1000_add_share_scope_to_memory_items"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add target platforms column and deployment profiles table."""
    with op.batch_alter_table("artifacts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("target_platforms", sa.JSON(), nullable=True))

    op.create_table(
        "deployment_profiles",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("profile_id", sa.String(), nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("root_dir", sa.Text(), nullable=False),
        sa.Column("artifact_path_map", sa.JSON(), nullable=True),
        sa.Column("config_filenames", sa.JSON(), nullable=True),
        sa.Column("context_prefixes", sa.JSON(), nullable=True),
        sa.Column("supported_types", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "project_id",
            "profile_id",
            name="uq_deployment_profiles_project_profile_id",
        ),
        sa.CheckConstraint(
            "platform IN ('claude_code', 'codex', 'gemini', 'cursor', 'other')",
            name="ck_deployment_profiles_platform",
        ),
    )
    op.create_index(
        "idx_deployment_profiles_project_profile",
        "deployment_profiles",
        ["project_id", "profile_id"],
        unique=True,
    )


def downgrade() -> None:
    """Remove deployment profiles table and target platforms column."""
    op.drop_index("idx_deployment_profiles_project_profile", table_name="deployment_profiles")
    op.drop_table("deployment_profiles")

    with op.batch_alter_table("artifacts", schema=None) as batch_op:
        batch_op.drop_column("target_platforms")
