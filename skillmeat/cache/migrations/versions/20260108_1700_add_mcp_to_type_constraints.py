"""Add 'mcp' to artifact_type CHECK constraint in marketplace_catalog_entries

Revision ID: 20260108_1700_add_mcp_to_type_constraints
Revises: 20260104_1000_add_path_based_tag_extraction
Create Date: 2026-01-08 17:00:00.000000+00:00

This migration updates the CHECK constraint on the artifact_type column of
marketplace_catalog_entries to include 'mcp' as a valid artifact type.

The Claude marketplace uses 'mcp' as the artifact type identifier, while
SkillMeat internally uses 'mcp_server'. Both values should be accepted
to support seamless marketplace integration.

Constraint Changes:
- Old: artifact_type IN ('skill', 'command', 'agent', 'mcp_server', 'hook',
       'project_config', 'spec_file', 'rule_file', 'context_file', 'progress_template')
- New: artifact_type IN ('skill', 'command', 'agent', 'mcp', 'mcp_server', 'hook',
       'project_config', 'spec_file', 'rule_file', 'context_file', 'progress_template')

Note: SQLite requires table recreation to modify CHECK constraints.
This migration uses Alembic's batch_alter_table for SQLite compatibility.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260108_1700_add_mcp_to_type_constraints"
down_revision: Union[str, None] = "20260104_1000_add_path_based_tag_extraction"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update check_catalog_artifact_type constraint to include 'mcp'.

    This enables marketplace catalog entries to be stored with artifact_type='mcp'
    which is the type identifier used by the Claude marketplace. The 'mcp_server'
    type is also kept for backward compatibility with existing entries.

    Uses batch operations for SQLite compatibility since SQLite requires
    table recreation to modify CHECK constraints.
    """
    with op.batch_alter_table("marketplace_catalog_entries") as batch_op:
        batch_op.drop_constraint("check_catalog_artifact_type", type_="check")
        batch_op.create_check_constraint(
            "check_catalog_artifact_type",
            "artifact_type IN ('skill', 'command', 'agent', 'mcp', 'mcp_server', 'hook', "
            "'project_config', 'spec_file', 'rule_file', 'context_file', 'progress_template')",
        )


def downgrade() -> None:
    """Revert check_catalog_artifact_type constraint to exclude 'mcp'.

    WARNING: This will fail if any entries have artifact_type='mcp'.
    Before running this downgrade, ensure all 'mcp' entries are either
    deleted or have their artifact_type changed to 'mcp_server'.
    """
    with op.batch_alter_table("marketplace_catalog_entries") as batch_op:
        batch_op.drop_constraint("check_catalog_artifact_type", type_="check")
        batch_op.create_check_constraint(
            "check_catalog_artifact_type",
            "artifact_type IN ('skill', 'command', 'agent', 'mcp_server', 'hook', "
            "'project_config', 'spec_file', 'rule_file', 'context_file', 'progress_template')",
        )
