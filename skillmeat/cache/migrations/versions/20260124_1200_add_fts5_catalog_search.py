"""Add FTS5 virtual table for catalog full-text search

Revision ID: 20260124_1200_add_fts5_catalog_search
Revises: 20260124_1100_add_search_indexes_to_catalog_entries
Create Date: 2026-01-24 12:00:00.000000+00:00

This migration adds FTS5 full-text search capability to the marketplace catalog.
FTS5 provides efficient tokenized search with Porter stemming for natural language
queries across artifact names, titles, descriptions, and tags.

Components created:
1. catalog_fts - FTS5 virtual table for full-text search
2. catalog_fts_ai - INSERT trigger to sync new entries
3. catalog_fts_ad - DELETE trigger to remove deleted entries
4. catalog_fts_au - UPDATE trigger to sync modified entries

The FTS5 table uses:
- content='marketplace_catalog_entries' - External content table mode
- content_rowid='rowid' - Link via SQLite rowid
- tokenize='porter unicode61 remove_diacritics 2' - Porter stemming with Unicode support

Phase 1 of cross-source search implementation (FTS-001).
"""

from __future__ import annotations

import logging
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260124_1200_add_fts5_catalog_search"
down_revision: Union[str, None] = "20260124_1100_add_search_indexes_to_catalog_entries"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger(__name__)


def upgrade() -> None:
    """Add FTS5 virtual table and sync triggers for catalog search.

    Creates an FTS5 virtual table linked to marketplace_catalog_entries for
    efficient full-text search. The external content table mode avoids data
    duplication while maintaining search performance.

    Triggers maintain index synchronization on INSERT/UPDATE/DELETE.

    Note: FTS5 requires SQLite to be compiled with ENABLE_FTS5. If FTS5 is
    not available, the migration logs a warning and continues. The search
    functionality will fall back to LIKE-based queries.
    """
    try:
        # Create FTS5 virtual table with external content mode
        # Using external content table to avoid data duplication
        # name and artifact_type are UNINDEXED for filtering without tokenization
        op.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS catalog_fts USING fts5(
                name UNINDEXED,
                artifact_type UNINDEXED,
                title,
                description,
                search_text,
                search_tags,
                content='marketplace_catalog_entries',
                content_rowid='rowid',
                tokenize='porter unicode61 remove_diacritics 2'
            )
            """
        )

        # INSERT trigger - adds new entries to FTS index
        op.execute(
            """
            CREATE TRIGGER IF NOT EXISTS catalog_fts_ai AFTER INSERT ON marketplace_catalog_entries
            BEGIN
                INSERT INTO catalog_fts(
                    rowid, name, artifact_type, title, description, search_text, search_tags
                )
                VALUES (
                    NEW.rowid,
                    NEW.name,
                    NEW.artifact_type,
                    NEW.title,
                    NEW.description,
                    NEW.search_text,
                    NEW.search_tags
                );
            END
            """
        )

        # DELETE trigger - removes entries from FTS index
        # Uses special 'catalog_fts' delete command for external content tables
        op.execute(
            """
            CREATE TRIGGER IF NOT EXISTS catalog_fts_ad AFTER DELETE ON marketplace_catalog_entries
            BEGIN
                INSERT INTO catalog_fts(
                    catalog_fts, rowid, name, artifact_type, title, description, search_text, search_tags
                )
                VALUES (
                    'delete',
                    OLD.rowid,
                    OLD.name,
                    OLD.artifact_type,
                    OLD.title,
                    OLD.description,
                    OLD.search_text,
                    OLD.search_tags
                );
            END
            """
        )

        # UPDATE trigger - removes old entry and inserts new one
        # This handles the case where indexed columns change
        op.execute(
            """
            CREATE TRIGGER IF NOT EXISTS catalog_fts_au AFTER UPDATE ON marketplace_catalog_entries
            BEGIN
                INSERT INTO catalog_fts(
                    catalog_fts, rowid, name, artifact_type, title, description, search_text, search_tags
                )
                VALUES (
                    'delete',
                    OLD.rowid,
                    OLD.name,
                    OLD.artifact_type,
                    OLD.title,
                    OLD.description,
                    OLD.search_text,
                    OLD.search_tags
                );
                INSERT INTO catalog_fts(
                    rowid, name, artifact_type, title, description, search_text, search_tags
                )
                VALUES (
                    NEW.rowid,
                    NEW.name,
                    NEW.artifact_type,
                    NEW.title,
                    NEW.description,
                    NEW.search_text,
                    NEW.search_tags
                );
            END
            """
        )

        # Populate FTS index with existing data
        # Only populates entries that have search_text (those that have been indexed)
        op.execute(
            """
            INSERT INTO catalog_fts(rowid, name, artifact_type, title, description, search_text, search_tags)
            SELECT rowid, name, artifact_type, title, description, search_text, search_tags
            FROM marketplace_catalog_entries
            WHERE search_text IS NOT NULL
            """
        )

        logger.info("FTS5 catalog_fts virtual table created successfully")

    except Exception as e:
        # FTS5 may not be available if SQLite wasn't compiled with ENABLE_FTS5
        # This is a compile-time option and cannot be enabled at runtime
        error_msg = str(e).lower()
        if "no such module: fts5" in error_msg or "fts5" in error_msg:
            logger.warning(
                "FTS5 is not available in this SQLite installation. "
                "Full-text search will fall back to LIKE-based queries. "
                "To enable FTS5, SQLite must be compiled with SQLITE_ENABLE_FTS5. "
                f"Error: {e}"
            )
        else:
            # Re-raise unexpected errors
            raise


def downgrade() -> None:
    """Remove FTS5 virtual table and sync triggers.

    Drops triggers first to avoid any issues with the virtual table removal.
    The FTS index data is automatically removed when the virtual table is dropped.
    """
    # Drop triggers first (order matters - triggers reference the table)
    op.execute("DROP TRIGGER IF EXISTS catalog_fts_au")
    op.execute("DROP TRIGGER IF EXISTS catalog_fts_ad")
    op.execute("DROP TRIGGER IF EXISTS catalog_fts_ai")

    # Drop the FTS5 virtual table
    op.execute("DROP TABLE IF EXISTS catalog_fts")

    logger.info("FTS5 catalog_fts virtual table and triggers removed")
