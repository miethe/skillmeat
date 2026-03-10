"""Add color column to entity_type_configs.

Revision ID: 20260301_1300_add_color_to_entity_type_configs
Revises: 20260301_1200_add_example_path_column
Create Date: 2026-03-01 13:00:00.000000+00:00

Background
----------
The EntityTypeConfig model needs a ``color`` field so each entity type can
carry a custom hex color used by the frontend card indicators.  Without it the
UI falls back to theme defaults for every type.

``color``
    Optional hex color code (e.g. ``'#3B82F6'``) stored as a 7-character
    string (``#`` + 6 hex digits).  ``NULL`` means no custom color is
    configured for this type and the frontend applies its default palette.

Tables modified
---------------
``entity_type_configs``
  - ADD ``color``  VARCHAR(7)  nullable

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
revision: str = "20260301_1300_add_color_to_entity_type_configs"
down_revision: Union[str, None] = "20260301_1200_add_example_path_column"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add color column to entity_type_configs.

    Uses ``sa_inspect`` to check for column existence before adding so the
    migration is idempotent on databases that already have the column (e.g.
    when ``Base.metadata.create_all()`` was called before migration).
    """
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    existing_columns = {
        col["name"] for col in inspector.get_columns("entity_type_configs")
    }

    if "color" not in existing_columns:
        op.add_column(
            "entity_type_configs",
            sa.Column(
                "color",
                sa.String(7),
                nullable=True,
                comment=(
                    "Optional hex color code for UI card indicators "
                    "(e.g. '#3B82F6'). NULL uses default theme colors."
                ),
            ),
        )


def downgrade() -> None:
    """Drop color column from entity_type_configs.

    All color data stored in this column will be permanently lost.
    No other tables are affected.
    """
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    existing_columns = {
        col["name"] for col in inspector.get_columns("entity_type_configs")
    }

    if "color" in existing_columns:
        op.drop_column("entity_type_configs", "color")
