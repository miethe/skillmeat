"""Add 'composite' and 'mcp' to artifact_type CHECK constraint in artifacts table

Revision ID: 20260220_1200_add_composite_mcp_to_artifact_type_constraint
Revises: 20260220_0600_add_composite_to_catalog_type_constraint
Create Date: 2026-02-20 12:00:00.000000+00:00

This migration updates the CHECK constraint on the type column of the artifacts
table to include 'composite' and 'mcp' as valid artifact types.

The ORM model in skillmeat/cache/models.py already includes 'composite' and 'mcp'
in the constraint definition, but this migration was missing, causing
sqlite3.IntegrityError: CHECK constraint failed: check_artifact_type
when inserting composite artifacts.

Constraint Changes:
- Old: type IN ('skill', 'command', 'agent', 'mcp_server', 'hook',
       'project_config', 'spec_file', 'rule_file', 'context_file', 'progress_template')
- New: type IN ('skill', 'command', 'agent', 'mcp', 'mcp_server', 'hook',
       'composite', 'project_config', 'spec_file', 'rule_file', 'context_file', 'progress_template')

Note: SQLite requires table recreation to modify CHECK constraints.
This migration uses Alembic's batch_alter_table for SQLite compatibility.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260220_1200_add_composite_mcp_to_artifact_type_constraint"
down_revision: Union[str, None] = "20260220_0600_add_composite_to_catalog_type_constraint"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update check_artifact_type constraint to include 'composite' and 'mcp'.

    This enables artifacts to be stored with type='composite' or type='mcp'
    which are the type identifiers used for composite/plugin artifacts and
    MCP (Model Context Protocol) artifacts respectively. All previously
    supported types are retained for backward compatibility.

    Uses batch operations for SQLite compatibility since SQLite requires
    table recreation to modify CHECK constraints.
    """
    with op.batch_alter_table("artifacts") as batch_op:
        batch_op.drop_constraint("check_artifact_type", type_="check")
        batch_op.create_check_constraint(
            "check_artifact_type",
            "type IN ('skill', 'command', 'agent', 'mcp', 'mcp_server', 'hook', "
            "'composite', "
            "'project_config', 'spec_file', 'rule_file', 'context_file', 'progress_template')",
        )


def downgrade() -> None:
    """Revert check_artifact_type constraint to exclude 'composite' and 'mcp'.

    WARNING: This will fail if any entries have type='composite' or type='mcp'.
    Before running this downgrade, ensure all 'composite' and 'mcp' entries are
    either deleted or have their type changed to another valid type.
    """
    with op.batch_alter_table("artifacts") as batch_op:
        batch_op.drop_constraint("check_artifact_type", type_="check")
        batch_op.create_check_constraint(
            "check_artifact_type",
            "type IN ('skill', 'command', 'agent', 'mcp_server', 'hook', "
            "'project_config', 'spec_file', 'rule_file', 'context_file', 'progress_template')",
        )
