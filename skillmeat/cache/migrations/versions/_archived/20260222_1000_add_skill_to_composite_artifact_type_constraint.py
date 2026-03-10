"""Add 'skill' to composite_type CHECK constraint in composite_artifacts table

Revision ID: 20260222_1000_add_skill_to_composite_artifact_type_constraint
Revises: 20260220_1200_add_composite_mcp_to_artifact_type_constraint
Create Date: 2026-02-22 10:00:00.000000+00:00

This migration updates the CHECK constraint on the composite_type column of
composite_artifacts to include 'skill' as a valid composite variant type.

Background
----------
The CompositeArtifact model supports multi-artifact bundles whose variant is
determined by ``composite_type``.  The original constraint (migration
20260218_1100_add_composite_artifact_tables) only recognised three variants:
'plugin', 'stack', 'suite'.  A fourth variant — 'skill' — is now required so
that skill-based composite bundles can be stored and validated correctly.

Constraint Changes:
- Old: composite_type IN ('plugin', 'stack', 'suite')
- New: composite_type IN ('plugin', 'stack', 'suite', 'skill')

Existing Data
-------------
All existing rows retain their current composite_type values ('plugin',
'stack', 'suite').  The expansion is purely additive; no data is modified.

Note: SQLite requires table recreation to modify CHECK constraints.
This migration uses Alembic's batch_alter_table for SQLite compatibility.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260222_1000_add_skill_to_composite_artifact_type_constraint"
down_revision: Union[str, None] = (
    "20260220_1200_add_composite_mcp_to_artifact_type_constraint"
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update check_composite_artifact_type constraint to include 'skill'.

    Expands the set of valid composite_type values from ('plugin', 'stack',
    'suite') to ('plugin', 'stack', 'suite', 'skill').  This allows
    CompositeArtifact rows to carry composite_type='skill' without triggering
    a CHECK constraint violation.

    All previously supported composite types are retained; no existing rows
    are modified by this migration.

    Uses batch operations for SQLite compatibility since SQLite requires
    table recreation to modify CHECK constraints.
    """
    with op.batch_alter_table("composite_artifacts") as batch_op:
        batch_op.drop_constraint("check_composite_artifact_type", type_="check")
        batch_op.create_check_constraint(
            "check_composite_artifact_type",
            "composite_type IN ('plugin', 'stack', 'suite', 'skill')",
        )


def downgrade() -> None:
    """Revert check_composite_artifact_type constraint to exclude 'skill'.

    Restores the original three-value constraint: ('plugin', 'stack', 'suite').

    WARNING: This will fail if any rows have composite_type='skill'.  Before
    running this downgrade, ensure all 'skill' composite_artifacts are either
    deleted or have their composite_type changed to another valid type.
    """
    with op.batch_alter_table("composite_artifacts") as batch_op:
        batch_op.drop_constraint("check_composite_artifact_type", type_="check")
        batch_op.create_check_constraint(
            "check_composite_artifact_type",
            "composite_type IN ('plugin', 'stack', 'suite')",
        )
