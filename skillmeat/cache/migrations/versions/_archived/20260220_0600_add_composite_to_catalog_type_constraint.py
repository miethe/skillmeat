"""Add 'composite' to artifact_type CHECK constraint in marketplace_catalog_entries

Revision ID: 20260220_0600_add_composite_to_catalog_type_constraint
Revises: 20260219_1500_add_position_to_composite_memberships
Create Date: 2026-02-20 06:00:00.000000+00:00

This migration updates the CHECK constraint on the artifact_type column of
marketplace_catalog_entries to include 'composite' as a valid artifact type.

The ORM model in skillmeat/cache/models.py already includes 'composite' in the
constraint definition, but this migration was missing, causing
sqlite3.IntegrityError: CHECK constraint failed: check_catalog_artifact_type
when storing detected composite/plugin artifacts.

Constraint Changes:
- Old: artifact_type IN ('skill', 'command', 'agent', 'mcp', 'mcp_server', 'hook',
       'project_config', 'spec_file', 'rule_file', 'context_file', 'progress_template')
- New: artifact_type IN ('skill', 'command', 'agent', 'mcp', 'mcp_server', 'hook',
       'composite', 'project_config', 'spec_file', 'rule_file', 'context_file', 'progress_template')

Note: SQLite requires table recreation to modify CHECK constraints.
This migration uses Alembic's batch_alter_table for SQLite compatibility.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260220_0600_add_composite_to_catalog_type_constraint"
down_revision: Union[str, None] = "20260219_1500_add_position_to_composite_memberships"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update check_catalog_artifact_type constraint to include 'composite'.

    This enables marketplace catalog entries to be stored with artifact_type='composite'
    which is the type identifier used for composite/plugin artifacts. All previously
    supported types are retained for backward compatibility.

    Uses batch operations for SQLite compatibility since SQLite requires
    table recreation to modify CHECK constraints.
    """
    with op.batch_alter_table("marketplace_catalog_entries") as batch_op:
        batch_op.drop_constraint("check_catalog_artifact_type", type_="check")
        batch_op.create_check_constraint(
            "check_catalog_artifact_type",
            "artifact_type IN ('skill', 'command', 'agent', 'mcp', 'mcp_server', 'hook', "
            "'composite', "
            "'project_config', 'spec_file', 'rule_file', 'context_file', 'progress_template')",
        )


def downgrade() -> None:
    """Revert check_catalog_artifact_type constraint to exclude 'composite'.

    WARNING: This will fail if any entries have artifact_type='composite'.
    Before running this downgrade, ensure all 'composite' entries are either
    deleted or have their artifact_type changed to another valid type.
    """
    with op.batch_alter_table("marketplace_catalog_entries") as batch_op:
        batch_op.drop_constraint("check_catalog_artifact_type", type_="check")
        batch_op.create_check_constraint(
            "check_catalog_artifact_type",
            "artifact_type IN ('skill', 'command', 'agent', 'mcp', 'mcp_server', 'hook', "
            "'project_config', 'spec_file', 'rule_file', 'context_file', 'progress_template')",
        )
