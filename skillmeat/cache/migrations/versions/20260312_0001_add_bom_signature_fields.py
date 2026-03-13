"""Add signing_key_id column to bom_snapshots (skillbom-attestation TASK-6.4)

Revision ID: 20260312_0001_add_bom_signature_fields
Revises: 20260311_0003_add_skillbom_attestation_tables
Create Date: 2026-03-12 00:01:00.000000+00:00

Background
----------
TASK-6.4 — Signature chain validation, BomSnapshot storage, auto-sign, and
restore verification.

The ``bom_snapshots`` table was created in
``20260311_0003_add_skillbom_attestation_tables`` with ``signature`` (Text)
and ``signature_algorithm`` (String) columns.  This migration adds the missing
``signing_key_id`` column (SHA-256 fingerprint of the signing public key) so
that verifiers can identify which key produced a given signature without
needing the full public key embedded in the BOM.

Changes
-------
1. Add column ``signing_key_id`` (String(128), nullable) to ``bom_snapshots``.

Dialect Strategy
----------------
* ``op.add_column`` works uniformly on SQLite and PostgreSQL.
* ``batch_alter_table`` is NOT needed here because we are only adding a
  nullable column (no constraint changes).  SQLite allows adding nullable
  columns via plain ``ALTER TABLE … ADD COLUMN``.

Idempotency
-----------
The upgrade function checks whether the column already exists before adding
it, so the migration is safe to run against databases that were already
partially migrated or created via ``Base.metadata.create_all``.

Downgrade
---------
Drops ``signing_key_id`` using ``batch_alter_table`` (required for SQLite
column drops, which otherwise raise ``OperationalError``).

Schema reference
----------------
skillmeat/cache/models.py  (BomSnapshot)
skillmeat/core/bom/signing.py  (sign_bom returns key_id)
"""

from __future__ import annotations

import logging
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

from skillmeat.cache.migrations.dialect_helpers import is_sqlite

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------

revision: str = "20260312_0001_add_bom_signature_fields"
down_revision: Union[str, None] = "20260311_0003_add_skillbom_attestation_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

log = logging.getLogger(__name__)

_TABLE = "bom_snapshots"
_COLUMN = "signing_key_id"


# ---------------------------------------------------------------------------
# Idempotency helper
# ---------------------------------------------------------------------------


def _column_exists(bind: sa.engine.Connection) -> bool:
    """Return True if ``signing_key_id`` already exists on ``bom_snapshots``."""
    if is_sqlite():
        result = bind.execute(text(f"PRAGMA table_info({_TABLE})"))
        return any(row[1] == _COLUMN for row in result.fetchall())
    else:
        result = bind.execute(
            text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = :tbl
                  AND column_name = :col
                """
            ),
            {"tbl": _TABLE, "col": _COLUMN},
        )
        return result.fetchone() is not None


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    """Add signing_key_id column to bom_snapshots."""
    bind = op.get_bind()

    if _column_exists(bind):
        log.info(
            "add_bom_signature_fields: column %r already exists on %r; skipping.",
            _COLUMN,
            _TABLE,
        )
        return

    log.info("add_bom_signature_fields: adding column %r to %r.", _COLUMN, _TABLE)
    op.add_column(
        _TABLE,
        sa.Column(
            _COLUMN,
            sa.String(128),
            nullable=True,
            comment="SHA-256 fingerprint (hex) of the signing public key",
        ),
    )
    log.info("add_bom_signature_fields: upgrade complete.")


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    """Drop signing_key_id from bom_snapshots.

    Uses batch_alter_table so that SQLite (which cannot drop columns natively
    before 3.35.0) gets a full table-rebuild.
    """
    log.info("add_bom_signature_fields: dropping column %r from %r.", _COLUMN, _TABLE)
    with op.batch_alter_table(_TABLE) as batch_op:
        batch_op.drop_column(_COLUMN)
    log.info("add_bom_signature_fields: downgrade complete.")
