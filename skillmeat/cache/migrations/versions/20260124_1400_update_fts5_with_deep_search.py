"""Update FTS5 virtual table to include deep_search_text column

Revision ID: 20260124_1400_update_fts5_with_deep_search
Revises: 20260124_1300_add_clone_target_fields
Create Date: 2026-01-24 14:00:00.000000+00:00

This migration updates the FTS5 virtual table to support deep indexing by adding
the deep_search_text column. FTS5 tables cannot be altered in place, so this
migration drops and recreates the virtual table and its associated triggers.

Changes:
- Drop existing catalog_fts table and triggers
- Recreate catalog_fts with deep_search_text column
- Recreate sync triggers to include deep_search_text
- Rebuild FTS index from existing data

Phase 1 of clone-based artifact indexing implementation (DB-105).

Reference:
- SPIKE: docs/project_plans/SPIKEs/clone-based-artifact-indexing-spike.md
- Previous FTS5 migration: 20260124_1200_add_fts5_catalog_search
"""

from __future__ import annotations

import logging
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260124_1400_update_fts5_with_deep_search"
down_revision: Union[str, None] = "20260124_1300_add_clone_target_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger(__name__)


def upgrade() -> None:
    """Update FTS5 virtual table to include deep_search_text column.

    FTS5 tables cannot be altered, so we must:
    1. Drop existing triggers (they reference the table)
    2. Drop the existing FTS5 virtual table
    3. Recreate with the new deep_search_text column
    4. Recreate triggers to sync all columns including deep_search_text
    5. Rebuild index from existing marketplace_catalog_entries data
    """
    try:
        # Step 1: Drop existing triggers
        op.execute("DROP TRIGGER IF EXISTS catalog_fts_au")
        op.execute("DROP TRIGGER IF EXISTS catalog_fts_ad")
        op.execute("DROP TRIGGER IF EXISTS catalog_fts_ai")

        # Step 2: Drop existing FTS5 virtual table
        op.execute("DROP TABLE IF EXISTS catalog_fts")

        # Step 3: Create new FTS5 virtual table with deep_search_text
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
                deep_search_text,
                content='marketplace_catalog_entries',
                content_rowid='rowid',
                tokenize='porter unicode61 remove_diacritics 2'
            )
            """
        )

        # Step 4: Recreate triggers with deep_search_text column

        # INSERT trigger - adds new entries to FTS index
        op.execute(
            """
            CREATE TRIGGER IF NOT EXISTS catalog_fts_ai AFTER INSERT ON marketplace_catalog_entries
            BEGIN
                INSERT INTO catalog_fts(
                    rowid, name, artifact_type, title, description,
                    search_text, search_tags, deep_search_text
                )
                VALUES (
                    NEW.rowid,
                    NEW.name,
                    NEW.artifact_type,
                    NEW.title,
                    NEW.description,
                    NEW.search_text,
                    NEW.search_tags,
                    NEW.deep_search_text
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
                    catalog_fts, rowid, name, artifact_type, title, description,
                    search_text, search_tags, deep_search_text
                )
                VALUES (
                    'delete',
                    OLD.rowid,
                    OLD.name,
                    OLD.artifact_type,
                    OLD.title,
                    OLD.description,
                    OLD.search_text,
                    OLD.search_tags,
                    OLD.deep_search_text
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
                    catalog_fts, rowid, name, artifact_type, title, description,
                    search_text, search_tags, deep_search_text
                )
                VALUES (
                    'delete',
                    OLD.rowid,
                    OLD.name,
                    OLD.artifact_type,
                    OLD.title,
                    OLD.description,
                    OLD.search_text,
                    OLD.search_tags,
                    OLD.deep_search_text
                );
                INSERT INTO catalog_fts(
                    rowid, name, artifact_type, title, description,
                    search_text, search_tags, deep_search_text
                )
                VALUES (
                    NEW.rowid,
                    NEW.name,
                    NEW.artifact_type,
                    NEW.title,
                    NEW.description,
                    NEW.search_text,
                    NEW.search_tags,
                    NEW.deep_search_text
                );
            END
            """
        )

        # Step 5: Rebuild FTS index from existing data
        # This populates the index with all existing entries that have search_text
        # deep_search_text may be NULL for entries not yet deep-indexed
        op.execute(
            """
            INSERT INTO catalog_fts(
                rowid, name, artifact_type, title, description,
                search_text, search_tags, deep_search_text
            )
            SELECT
                rowid, name, artifact_type, title, description,
                search_text, search_tags, deep_search_text
            FROM marketplace_catalog_entries
            WHERE search_text IS NOT NULL
            """
        )

        # Optimize the FTS index after bulk insert
        op.execute("INSERT INTO catalog_fts(catalog_fts) VALUES('optimize')")

        logger.info(
            "FTS5 catalog_fts updated with deep_search_text column and index rebuilt"
        )

    except Exception as e:
        error_msg = str(e).lower()
        if "no such module: fts5" in error_msg or "fts5" in error_msg:
            logger.warning(
                "FTS5 is not available in this SQLite installation. "
                "Full-text search will fall back to LIKE-based queries. "
                f"Error: {e}"
            )
        else:
            raise


def downgrade() -> None:
    """Revert FTS5 table to version without deep_search_text.

    Recreates the original FTS5 schema from migration 20260124_1200 with only
    the original 6 columns (name, artifact_type, title, description, search_text, search_tags).
    """
    # Step 1: Drop triggers
    op.execute("DROP TRIGGER IF EXISTS catalog_fts_au")
    op.execute("DROP TRIGGER IF EXISTS catalog_fts_ad")
    op.execute("DROP TRIGGER IF EXISTS catalog_fts_ai")

    # Step 2: Drop the FTS5 virtual table
    op.execute("DROP TABLE IF EXISTS catalog_fts")

    # Step 3: Recreate original FTS5 table WITHOUT deep_search_text
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

    # Step 4: Recreate original triggers without deep_search_text

    # INSERT trigger
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

    # DELETE trigger
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

    # UPDATE trigger
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

    # Step 5: Rebuild index
    op.execute(
        """
        INSERT INTO catalog_fts(rowid, name, artifact_type, title, description, search_text, search_tags)
        SELECT rowid, name, artifact_type, title, description, search_text, search_tags
        FROM marketplace_catalog_entries
        WHERE search_text IS NOT NULL
        """
    )

    # Optimize after rebuild
    op.execute("INSERT INTO catalog_fts(catalog_fts) VALUES('optimize')")

    logger.info("FTS5 catalog_fts reverted to original schema without deep_search_text")
