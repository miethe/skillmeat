"""Fix artifact_fts triggers: replace a.title with NULL

Revision ID: 20260226_1900_fix_artifact_fts_triggers
Revises: 20260226_1200_add_artifact_embeddings
Create Date: 2026-02-26 19:00:00.000000+00:00

Background
----------
The artifact_fts_ai and artifact_fts_au triggers created by migration
20260226_1000_add_similarity_cache_schema may have been deployed with a
buggy variant that references ``a.title`` from the ``artifacts`` table.
That column does not exist on ``artifacts`` at this schema version, which
causes every INSERT or UPDATE on ``collection_artifacts`` to raise an
OperationalError and silently prevents FTS indexing.

The correct value for the ``title`` column is ``NULL`` — the FTS5 schema
already documents that ``title`` is reserved for forward-compatibility and
will be populated by the scoring engine once a richer title source is
available.

Changes
-------
FTS-1  Drop the three artifact_fts sync triggers unconditionally.
FTS-2  Recreate artifact_fts_ai with NULL in place of a.title.
FTS-3  Recreate artifact_fts_ad (unchanged, for completeness).
FTS-4  Recreate artifact_fts_au with NULL in place of a.title.

Rollback
--------
Recreates the same correct triggers (NULL for title).  We intentionally
do not restore the buggy a.title variant on downgrade — rolling back to a
known-broken state would be harmful.
"""

from __future__ import annotations

import logging
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260226_1900_fix_artifact_fts_triggers"
down_revision: Union[str, None] = "20260226_1200_add_artifact_embeddings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger(__name__)

_COLLECTION_ARTIFACTS_TABLE = "collection_artifacts"
_FTS_TABLE = "artifact_fts"


def _drop_triggers() -> None:
    """Drop all three artifact_fts sync triggers unconditionally."""
    for trigger in ("artifact_fts_ai", "artifact_fts_ad", "artifact_fts_au"):
        logger.info("Dropping trigger %s (if exists)", trigger)
        op.execute(f"DROP TRIGGER IF EXISTS {trigger}")


def _create_triggers() -> None:
    """Recreate the three artifact_fts sync triggers with NULL for title."""

    # INSERT trigger — index new artifacts.
    # title is NULL; the FTS5 column exists for forward-compatibility and will
    # be populated by the scoring engine once a richer title source is available.
    logger.info("Creating trigger artifact_fts_ai")
    op.execute(
        f"""
        CREATE TRIGGER artifact_fts_ai
        AFTER INSERT ON {_COLLECTION_ARTIFACTS_TABLE}
        BEGIN
            INSERT INTO {_FTS_TABLE}(artifact_uuid, name, title, description, tags)
            SELECT
                NEW.artifact_uuid,
                a.name,
                NULL,
                a.description,
                NEW.tags_json
            FROM artifacts a
            WHERE a.uuid = NEW.artifact_uuid;
        END
        """
    )

    # DELETE trigger — remove de-indexed artifacts.
    logger.info("Creating trigger artifact_fts_ad")
    op.execute(
        f"""
        CREATE TRIGGER artifact_fts_ad
        AFTER DELETE ON {_COLLECTION_ARTIFACTS_TABLE}
        BEGIN
            DELETE FROM {_FTS_TABLE}
            WHERE artifact_uuid = OLD.artifact_uuid;
        END
        """
    )

    # UPDATE trigger — re-index on metadata changes.
    logger.info("Creating trigger artifact_fts_au")
    op.execute(
        f"""
        CREATE TRIGGER artifact_fts_au
        AFTER UPDATE ON {_COLLECTION_ARTIFACTS_TABLE}
        BEGIN
            DELETE FROM {_FTS_TABLE}
            WHERE artifact_uuid = OLD.artifact_uuid;
            INSERT INTO {_FTS_TABLE}(artifact_uuid, name, title, description, tags)
            SELECT
                NEW.artifact_uuid,
                a.name,
                NULL,
                a.description,
                NEW.tags_json
            FROM artifacts a
            WHERE a.uuid = NEW.artifact_uuid;
        END
        """
    )


def upgrade() -> None:
    logger.info(
        "SSO fix: dropping and recreating artifact_fts triggers "
        "(replace a.title with NULL)"
    )
    _drop_triggers()
    _create_triggers()
    logger.info("artifact_fts trigger fix complete")


def downgrade() -> None:
    # Intentionally recreate the correct (NULL) triggers on downgrade.
    # Restoring the buggy a.title variant would cause immediate runtime errors.
    logger.info(
        "SSO fix downgrade: recreating artifact_fts triggers with NULL title"
    )
    _drop_triggers()
    _create_triggers()
    logger.info("artifact_fts trigger downgrade complete")
