"""Add color and icon columns to deployment_sets.

Revision ID: 20260225_1200_add_color_icon_to_deployment_sets
Revises: 20260225_1100_add_custom_colors_table
Create Date: 2026-02-25 12:00:00.000000+00:00

Background
----------
Part of the color-icon-management feature.  Each deployment set can now carry
a visual identity via an optional hex color swatch and an optional icon
identifier.  Both columns are nullable so that existing rows are unaffected
and callers may choose to display a default/neutral style when they are NULL.

Columns added
-------------
``deployment_sets.color``
    String(7), nullable — CSS hex color string, e.g. ``#7c3aed``.
    Validated by CheckConstraint ``check_deployment_set_color_hex_format``
    (same pattern as ``custom_colors.hex``): value must be NULL or match
    ``#rrggbb`` / ``#rgb`` form.

``deployment_sets.icon``
    String(64), nullable — icon identifier string (e.g. a Lucide icon name
    or an internal slug).  No format constraint is applied at the DB level
    so that the icon set can evolve without schema changes.

Rollback
--------
Drop the two columns.  SQLite does not support ``DROP COLUMN`` natively on
older versions; the migration uses ``batch_alter_table`` for compatibility.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


# revision identifiers, used by Alembic.
revision: str = "20260225_1200_add_color_icon_to_deployment_sets"
down_revision: Union[str, None] = "20260225_1100_add_custom_colors_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "deployment_sets"
_COLOR_COL = "color"
_ICON_COL = "icon"
_COLOR_CHECK = "check_deployment_set_color_hex_format"


def _existing_columns(inspector: sa.engine.Inspector) -> set[str]:
    return {col["name"] for col in inspector.get_columns(_TABLE)}


def upgrade() -> None:
    """Add color and icon columns to deployment_sets."""
    bind = op.get_bind()
    inspector = sa_inspect(bind)

    # Guard: skip if deployment_sets table does not yet exist (fresh DB that
    # hasn't run the base migration yet — shouldn't happen in practice, but
    # defensive coding keeps the migration idempotent in test environments).
    if _TABLE not in inspector.get_table_names():
        return

    existing_cols = _existing_columns(inspector)

    with op.batch_alter_table(_TABLE) as batch_op:
        if _COLOR_COL not in existing_cols:
            batch_op.add_column(
                sa.Column(
                    _COLOR_COL,
                    sa.String(7),
                    nullable=True,
                    comment="Optional CSS hex color string, e.g. #7c3aed",
                )
            )
            batch_op.create_check_constraint(
                _COLOR_CHECK,
                "color IS NULL OR color LIKE '#______' OR color LIKE '#___'",
            )

        if _ICON_COL not in existing_cols:
            batch_op.add_column(
                sa.Column(
                    _ICON_COL,
                    sa.String(64),
                    nullable=True,
                    comment="Optional icon identifier string (e.g. a Lucide icon name)",
                )
            )


def downgrade() -> None:
    """Remove color and icon columns from deployment_sets.

    All stored color and icon values for deployment sets will be permanently
    lost on downgrade.
    """
    bind = op.get_bind()
    inspector = sa_inspect(bind)

    if _TABLE not in inspector.get_table_names():
        return

    existing_cols = _existing_columns(inspector)

    with op.batch_alter_table(_TABLE) as batch_op:
        # Drop columns in reverse order; drop constraint before the column it
        # references so that batch_alter_table can reconstruct the table cleanly.
        if _COLOR_COL in existing_cols:
            # SQLite batch mode reconstructs the table, so the constraint name
            # only needs to be dropped on dialects that support named constraints
            # (Postgres).  batch_alter_table handles this transparently.
            existing_constraints = {
                con["name"]
                for con in inspector.get_check_constraints(_TABLE)
            }
            if _COLOR_CHECK in existing_constraints:
                batch_op.drop_constraint(_COLOR_CHECK, type_="check")
            batch_op.drop_column(_COLOR_COL)

        if _ICON_COL in existing_cols:
            batch_op.drop_column(_ICON_COL)
