"""Add clone target fields for clone-based artifact indexing

Revision ID: 20260124_1300_add_clone_target_fields
Revises: 20260124_1200_add_fts5_catalog_search
Create Date: 2026-01-24 13:00:00.000000+00:00

This migration adds fields to support clone-based artifact indexing, enabling
efficient repository cloning for deep indexing and webhook-based updates.

Phase 1 of clone-based artifact indexing implementation (DB-101).

Schema Changes to marketplace_sources:
- clone_target_json: Text field storing serialized CloneTarget for rapid re-indexing
- deep_indexing_enabled: Boolean flag to enable cloning entire artifact directories
- webhook_secret: Optional secret for GitHub webhook verification (future use)
- last_webhook_event_at: Timestamp of last webhook event received (future use)

Schema Changes to marketplace_catalog_entries:
- deep_search_text: Full-text content from deep indexing of artifact files
- deep_indexed_at: Timestamp of last deep indexing operation
- deep_index_files: JSON array of files included in deep index

Reference:
- SPIKE: docs/project_plans/SPIKEs/clone-based-artifact-indexing-spike.md
- Implementation Plan: docs/project_plans/implementation_plans/features/clone-based-artifact-indexing-v1.md
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260124_1300_add_clone_target_fields"
down_revision: Union[str, None] = "20260124_1200_add_fts5_catalog_search"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add clone target and deep indexing fields to marketplace tables.

    marketplace_sources changes:
    - clone_target_json: Stores serialized CloneTarget with owner, repo, ref,
      paths, and sparse config for efficient re-cloning without re-scanning
    - deep_indexing_enabled: When True, enables cloning entire artifact
      directories for enhanced full-text search
    - webhook_secret: Secret token for verifying GitHub webhook payloads
    - last_webhook_event_at: Tracks when last webhook event was received

    marketplace_catalog_entries changes:
    - deep_search_text: Stores full content from all files in artifact directory
    - deep_indexed_at: Timestamp when deep indexing was last performed
    - deep_index_files: JSON array of file paths included in deep index
    """
    # Add fields to marketplace_sources
    op.add_column(
        "marketplace_sources",
        sa.Column(
            "clone_target_json",
            sa.Text(),
            nullable=True,
            comment="JSON-serialized CloneTarget for rapid re-indexing",
        ),
    )

    op.add_column(
        "marketplace_sources",
        sa.Column(
            "deep_indexing_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="0",
            comment="Clone entire artifact directories for enhanced search",
        ),
    )

    op.add_column(
        "marketplace_sources",
        sa.Column(
            "webhook_secret",
            sa.String(64),
            nullable=True,
            comment="Secret for GitHub webhook verification (future use)",
        ),
    )

    op.add_column(
        "marketplace_sources",
        sa.Column(
            "last_webhook_event_at",
            sa.DateTime(),
            nullable=True,
            comment="Timestamp of last webhook event received",
        ),
    )

    # Add fields to marketplace_catalog_entries
    op.add_column(
        "marketplace_catalog_entries",
        sa.Column(
            "deep_search_text",
            sa.Text(),
            nullable=True,
            comment="Full-text content from deep indexing",
        ),
    )

    op.add_column(
        "marketplace_catalog_entries",
        sa.Column(
            "deep_indexed_at",
            sa.DateTime(),
            nullable=True,
            comment="Timestamp of last deep indexing",
        ),
    )

    op.add_column(
        "marketplace_catalog_entries",
        sa.Column(
            "deep_index_files",
            sa.Text(),
            nullable=True,
            comment="JSON array of files included in deep index",
        ),
    )


def downgrade() -> None:
    """Remove clone target and deep indexing fields from marketplace tables.

    This reverts the migration by dropping all clone-based indexing columns.
    Any stored CloneTarget configurations and deep-indexed content will be
    permanently lost.

    WARNING: This is a destructive operation. Re-scanning sources with deep
    indexing will be required to repopulate this data after upgrading again.
    """
    # Drop fields from marketplace_catalog_entries
    op.drop_column("marketplace_catalog_entries", "deep_index_files")
    op.drop_column("marketplace_catalog_entries", "deep_indexed_at")
    op.drop_column("marketplace_catalog_entries", "deep_search_text")

    # Drop fields from marketplace_sources
    op.drop_column("marketplace_sources", "last_webhook_event_at")
    op.drop_column("marketplace_sources", "webhook_secret")
    op.drop_column("marketplace_sources", "deep_indexing_enabled")
    op.drop_column("marketplace_sources", "clone_target_json")
