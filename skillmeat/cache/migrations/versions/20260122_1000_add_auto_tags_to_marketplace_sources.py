"""Add auto_tags column to marketplace_sources table

Revision ID: 20260122_1000_add_auto_tags_to_marketplace_sources
Revises: 20260120_1000_add_single_artifact_mode_to_marketplace_sources
Create Date: 2026-01-22 10:00:00.000000+00:00

This migration adds the auto_tags column to the marketplace_sources table to
support GitHub topic extraction as auto-tags.

GitHub repository topics are extracted during source creation/update when
import_repo_description is True. These topics become "auto-tags" that users
can approve or reject. Approved auto-tags are automatically added to the
source's regular tags list.

Auto-tags are source-level only and do NOT propagate to imported artifacts.
Use path_segments for artifact-level tagging.

JSON Structure:
{
    "extracted": [
        {
            "value": "original-topic",
            "normalized": "original-topic",
            "status": "pending|approved|rejected",
            "source": "github_topic"
        }
    ]
}

Schema Changes:
- Add auto_tags column: TEXT, nullable
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260122_1000_add_auto_tags_to_marketplace_sources"
down_revision: Union[str, None] = "20260120_1000_add_single_artifact_mode_to_marketplace_sources"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add auto_tags column to marketplace_sources table.

    This column stores GitHub repository topics as extractable auto-tags
    in JSON format. Topics are extracted when import_repo_description=True
    during source creation or update.

    Users can approve or reject auto-tags via the API. Approved tags are
    automatically added to the source's regular tags list.
    """
    op.add_column(
        "marketplace_sources",
        sa.Column(
            "auto_tags",
            sa.Text(),
            nullable=True,
            comment="JSON: {extracted: [{value, normalized, status, source}]} for GitHub topics",
        ),
    )


def downgrade() -> None:
    """Remove auto_tags column from marketplace_sources table.

    This reverts the migration by dropping the auto_tags column. Any
    auto-tag data stored in this column will be permanently lost.

    WARNING: This is a destructive operation. All auto-tag approval
    statuses will be lost.
    """
    op.drop_column("marketplace_sources", "auto_tags")
