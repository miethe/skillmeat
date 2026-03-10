"""Update check_catalog_status constraint to include 'excluded' status

Revision ID: 20260102_1000_update_catalog_status_constraint
Revises: 20251231_2103_add_exclusion_to_catalog
Create Date: 2026-01-02 10:00:00.000000+00:00

This migration updates the CHECK constraint on the status column of
marketplace_catalog_entries to include 'excluded' as a valid status value.

The previous migration (20251231_2103) added excluded_at and excluded_reason
columns to support marking entries as "not an artifact", but the CHECK
constraint was not updated to allow the 'excluded' status value.

Constraint Changes:
- Old: status IN ('new', 'updated', 'removed', 'imported')
- New: status IN ('new', 'updated', 'removed', 'imported', 'excluded')

Note: SQLite requires table recreation to modify CHECK constraints.
This migration uses Alembic's batch_alter_table for SQLite compatibility.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260102_1000_update_catalog_status_constraint"
down_revision: Union[str, None] = "20251231_2103_add_exclusion_to_catalog"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update check_catalog_status constraint to include 'excluded' status.

    This enables catalog entries to be set to 'excluded' status when they
    are marked as false positives (not actual artifacts). The excluded_at
    and excluded_reason columns were added in the previous migration.

    Uses batch operations for SQLite compatibility since SQLite requires
    table recreation to modify CHECK constraints.
    """
    with op.batch_alter_table("marketplace_catalog_entries") as batch_op:
        batch_op.drop_constraint("check_catalog_status", type_="check")
        batch_op.create_check_constraint(
            "check_catalog_status",
            "status IN ('new', 'updated', 'removed', 'imported', 'excluded')",
        )


def downgrade() -> None:
    """Revert check_catalog_status constraint to exclude 'excluded' status.

    WARNING: This will fail if any entries have status='excluded'.
    Before running this downgrade, ensure all excluded entries are
    either deleted or have their status changed to a valid value.
    """
    with op.batch_alter_table("marketplace_catalog_entries") as batch_op:
        batch_op.drop_constraint("check_catalog_status", type_="check")
        batch_op.create_check_constraint(
            "check_catalog_status",
            "status IN ('new', 'updated', 'removed', 'imported')",
        )
