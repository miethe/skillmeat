"""Add description column to deployment_profiles table

Revision ID: 20260222_1100_add_description_to_deployment_profiles
Revises: 20260222_1000_add_skill_to_composite_artifact_type_constraint
Create Date: 2026-02-22 11:00:00.000000+00:00

This migration adds an optional free-text description column to the
deployment_profiles table to support the Enhanced Platform Profiles feature.

Column Added
------------
- description (TEXT, nullable): Human-readable description of the deployment
  profile, e.g. "Claude Code profile for monorepo root".

Existing Data
-------------
All existing rows receive NULL for the new column.  No existing data is
modified.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


# revision identifiers, used by Alembic.
revision: str = "20260222_1100_add_description_to_deployment_profiles"
down_revision: Union[str, None] = (
    "20260222_1000_add_skill_to_composite_artifact_type_constraint"
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nullable description TEXT column to deployment_profiles.

    The column is nullable so that existing rows are unaffected and the
    migration can be applied without a data backfill step.

    Idempotent: skips the ALTER TABLE if the column already exists (e.g.,
    when Base.metadata.create_all() was called before Alembic migrations ran).
    """
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    existing_columns = [col["name"] for col in inspector.get_columns("deployment_profiles")]
    if "description" not in existing_columns:
        with op.batch_alter_table("deployment_profiles") as batch_op:
            batch_op.add_column(sa.Column("description", sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove description column from deployment_profiles."""
    with op.batch_alter_table("deployment_profiles") as batch_op:
        batch_op.drop_column("description")
