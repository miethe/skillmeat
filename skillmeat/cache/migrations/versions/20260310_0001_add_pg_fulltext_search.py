"""add PostgreSQL full-text search (tsvector) to marketplace_catalog_entries

Revision ID: 20260310_0001_add_pg_fulltext_search
Revises: 20260306_006_add_auth_indexes_constraints
Create Date: 2026-03-10 00:01:00.000000+00:00

Background
----------
PG-FTS-1.1 — PostgreSQL Full-Text Search v1.

Adds a `search_vector` tsvector column to `marketplace_catalog_entries` that
is populated by a BEFORE INSERT OR UPDATE trigger.  The column is indexed with
a GIN index for fast full-text queries.

Weights used by `to_tsvector()`:
  A — title          (highest relevance)
  B — search_tags
  C — description
  D — search_text, deep_search_text  (lowest relevance)

This migration is PostgreSQL-only.  It is a no-op on SQLite (local edition).

What this migration adds (PostgreSQL only)
------------------------------------------
1. Column  `search_vector` TSVECTOR NULL  on marketplace_catalog_entries
2. GIN index  ix_marketplace_catalog_entries_search_vector
3. PL/pgSQL trigger function  marketplace_catalog_search_vector_update()
4. BEFORE INSERT OR UPDATE trigger  marketplace_catalog_search_vector_trigger
5. Backfill of existing rows via UPDATE

Downgrade order (PostgreSQL only)
-----------------------------------
1. Drop trigger
2. Drop trigger function
3. Drop GIN index
4. Drop column

Schema reference
----------------
docs/project_plans/implementation_plans/features/pg-fulltext-search-v1.md
.claude/progress/pg-fulltext-search/
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------

revision: str = "20260310_0001_add_pg_fulltext_search"
down_revision: Union[str, None] = "20260306_006_add_auth_indexes_constraints"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TABLE = "marketplace_catalog_entries"
_COLUMN = "search_vector"
_INDEX = "ix_marketplace_catalog_entries_search_vector"
_TRIGGER_FN = "marketplace_catalog_search_vector_update"
_TRIGGER = "marketplace_catalog_search_vector_trigger"

# ---------------------------------------------------------------------------
# Dialect helpers
# ---------------------------------------------------------------------------


def _is_postgresql() -> bool:
    """Return True when running against a PostgreSQL database."""
    return op.get_bind().dialect.name == "postgresql"


# ---------------------------------------------------------------------------
# SQL fragments
# ---------------------------------------------------------------------------

_TRIGGER_FUNCTION_SQL = f"""
CREATE OR REPLACE FUNCTION {_TRIGGER_FN}()
RETURNS trigger AS $$
BEGIN
  NEW.search_vector :=
    setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(NEW.search_tags, '')), 'B') ||
    setweight(to_tsvector('english', coalesce(NEW.description, '')), 'C') ||
    setweight(to_tsvector('english', coalesce(NEW.search_text, '')), 'D') ||
    setweight(to_tsvector('english', coalesce(NEW.deep_search_text, '')), 'D');
  RETURN NEW;
END
$$ LANGUAGE plpgsql;
"""

_CREATE_TRIGGER_SQL = f"""
CREATE TRIGGER {_TRIGGER}
BEFORE INSERT OR UPDATE ON {_TABLE}
FOR EACH ROW EXECUTE FUNCTION {_TRIGGER_FN}();
"""

_BACKFILL_SQL = f"""
UPDATE {_TABLE} SET search_vector =
    setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(search_tags, '')), 'B') ||
    setweight(to_tsvector('english', coalesce(description, '')), 'C') ||
    setweight(to_tsvector('english', coalesce(search_text, '')), 'D') ||
    setweight(to_tsvector('english', coalesce(deep_search_text, '')), 'D');
"""

# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    """Add tsvector column, GIN index, trigger, and backfill existing rows."""
    if not _is_postgresql():
        return

    # 1. Add the search_vector column (nullable — existing rows have no value yet).
    op.add_column(
        _TABLE,
        sa.Column(_COLUMN, sa.Text(), nullable=True),  # placeholder type, overridden below
    )

    # Replace the placeholder column with the native TSVECTOR type.  Alembic
    # does not ship a built-in TSVECTOR type, so we use DDL directly.
    op.execute(
        text(
            f"ALTER TABLE {_TABLE} ALTER COLUMN {_COLUMN} TYPE tsvector "
            f"USING NULL::tsvector"
        )
    )

    # 2. Create GIN index for fast full-text lookups.
    op.create_index(
        _INDEX,
        _TABLE,
        [_COLUMN],
        postgresql_using="gin",
    )

    # 3. Create the trigger function.
    op.execute(text(_TRIGGER_FUNCTION_SQL))

    # 4. Attach the trigger to the table.
    op.execute(text(_CREATE_TRIGGER_SQL))

    # 5. Backfill existing rows so the column is not NULL for historical data.
    op.execute(text(_BACKFILL_SQL))


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    """Remove trigger, function, index, and column added by this migration."""
    if not _is_postgresql():
        return

    # 1. Drop trigger first (depends on the function).
    op.execute(
        text(f"DROP TRIGGER IF EXISTS {_TRIGGER} ON {_TABLE}")
    )

    # 2. Drop trigger function.
    op.execute(
        text(f"DROP FUNCTION IF EXISTS {_TRIGGER_FN}()")
    )

    # 3. Drop GIN index.
    op.drop_index(_INDEX, table_name=_TABLE)

    # 4. Drop the column.
    op.drop_column(_TABLE, _COLUMN)
