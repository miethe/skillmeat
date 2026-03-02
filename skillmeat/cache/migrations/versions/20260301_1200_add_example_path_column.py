"""Add example_path column to entity_type_configs.

Revision ID: 20260301_1200_add_example_path_column
Revises: 20260301_1100_add_core_content_column
Create Date: 2026-03-01 12:00:00.000000+00:00

Background
----------
The API schema for EntityTypeConfig exposes ``example_path: Optional[str]``
but the ORM model and database table were missing this column.  This migration
adds the column so that the ORM and the API contract are consistent.

``example_path``
    A short filesystem path illustrating where entities of this type live
    (e.g. ``".claude/skills/my-skill/SKILL.md"``).  Shown in the creation
    form to help users understand the expected file layout.  ``NULL`` means
    no example is configured for this type.

Tables modified
---------------
``entity_type_configs``
  - ADD ``example_path``  TEXT  nullable

Rollback
--------
Drop the column.  No other tables are affected.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect as sa_inspect


# revision identifiers, used by Alembic.
revision: str = "20260301_1200_add_example_path_column"
down_revision: Union[str, None] = "20260301_1100_add_core_content_column"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add example_path column to entity_type_configs.

    Uses ``sa_inspect`` to check for column existence before adding so the
    migration is idempotent on databases that already have the column (e.g.
    when ``Base.metadata.create_all()`` was called before migration).
    """
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    existing_columns = {
        col["name"] for col in inspector.get_columns("entity_type_configs")
    }

    if "example_path" not in existing_columns:
        op.add_column(
            "entity_type_configs",
            sa.Column(
                "example_path",
                sa.String(),
                nullable=True,
                comment=(
                    "Short filesystem path illustrating where entities of this "
                    "type live. NULL means no example is configured."
                ),
            ),
        )


def downgrade() -> None:
    """Drop example_path column from entity_type_configs.

    All example path data stored in this column will be permanently lost.
    No other tables are affected.
    """
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    existing_columns = {
        col["name"] for col in inspector.get_columns("entity_type_configs")
    }

    if "example_path" in existing_columns:
        op.drop_column("entity_type_configs", "example_path")
