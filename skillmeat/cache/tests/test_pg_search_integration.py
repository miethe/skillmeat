"""Integration tests for PostgreSQL tsvector full-text search.

These tests exercise the ``search_vector`` column, GIN index, and trigger that
are added by migration ``20260310_0001_add_pg_fulltext_search``.  They also
validate the ``MarketplaceCatalogRepository.search()`` and
``_search_tsvector()`` methods end-to-end against a real PostgreSQL database.

All tests are marked ``@pytest.mark.integration`` and will be skipped
automatically when a PostgreSQL database is not reachable.

Requirements
------------
* A running PostgreSQL instance accessible via ``TEST_DATABASE_URL`` (default:
  ``postgresql://localhost:5432/skillmeat_test``).
* The test database must exist and the connecting user must have CREATE / DROP
  privileges within it.

Running
-------
.. code-block:: bash

    # With the default URL:
    pytest skillmeat/cache/tests/test_pg_search_integration.py -v -m integration

    # With a custom URL:
    TEST_DATABASE_URL=postgresql://user:pass@host:5432/mydb \\
        pytest skillmeat/cache/tests/test_pg_search_integration.py -v -m integration

Skipping
--------
If the database is not reachable the entire module is skipped via a
module-level ``pytest.skip`` call rather than raising connection errors.
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Generator
from pathlib import Path
from typing import Optional

import pytest
import sqlalchemy as sa
from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from sqlalchemy.orm import Session, sessionmaker

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_DB_URL = "postgresql://localhost:5432/skillmeat_test"
_ALEMBIC_INI = Path(__file__).parent.parent / "migrations" / "alembic.ini"
_MIGRATIONS_DIR = Path(__file__).parent.parent / "migrations"

_CATALOG_TABLE = "marketplace_catalog_entries"
_SOURCES_TABLE = "marketplace_sources"
_SEARCH_VECTOR_COL = "search_vector"
_GIN_INDEX = "ix_marketplace_catalog_entries_search_vector"
_TRIGGER = "marketplace_catalog_search_vector_trigger"
_TRIGGER_FN = "marketplace_catalog_search_vector_update"


# ---------------------------------------------------------------------------
# PostgreSQL availability check (module-level skip)
# ---------------------------------------------------------------------------


def _get_test_db_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", _DEFAULT_DB_URL)


def _pg_available(db_url: str) -> bool:
    """Return True if a connection to the PostgreSQL URL can be established."""
    if "postgresql" not in db_url:
        return False
    try:
        engine = sa.create_engine(db_url, pool_pre_ping=True)
        with engine.connect():
            pass
        engine.dispose()
        return True
    except Exception:
        return False


_DB_URL = _get_test_db_url()
if not _pg_available(_DB_URL):
    pytest.skip(
        f"PostgreSQL not available at {_DB_URL!r} — set TEST_DATABASE_URL to a "
        "reachable PostgreSQL instance to run these integration tests.",
        allow_module_level=True,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_alembic_cfg(db_url: str) -> AlembicConfig:
    """Build an AlembicConfig pointed at the test database."""
    cfg = AlembicConfig(str(_ALEMBIC_INI))
    cfg.set_main_option("script_location", str(_MIGRATIONS_DIR))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def _drop_all_tables(engine: sa.engine.Engine) -> None:
    """Drop all user tables and Alembic version tracking."""
    with engine.begin() as conn:
        result = conn.execute(
            sa.text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            )
        )
        tables = [row[0] for row in result]
        for table in tables:
            conn.execute(sa.text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))

        # Drop trigger functions created by migrations.
        result = conn.execute(
            sa.text(
                """
                SELECT p.proname
                FROM pg_proc p
                JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname = 'public'
                  AND p.proname LIKE 'update_%'
                """
            )
        )
        for row in result:
            conn.execute(sa.text(f"DROP FUNCTION IF EXISTS {row[0]}() CASCADE"))

        # Drop the FTS trigger function specifically.
        conn.execute(
            sa.text(f"DROP FUNCTION IF EXISTS {_TRIGGER_FN}() CASCADE")
        )


def _unique_id(prefix: str = "test") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _insert_source(conn: sa.engine.Connection, source_id: str) -> None:
    """Insert a minimal marketplace_sources row required by FK constraints."""
    conn.execute(
        sa.text(
            f"""
            INSERT INTO {_SOURCES_TABLE}
                (id, repo_url, owner, repo_name, ref)
            VALUES
                (:id, :repo_url, :owner, :repo_name, 'main')
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {
            "id": source_id,
            "repo_url": f"https://github.com/test/{source_id}",
            "owner": "test",
            "repo_name": source_id,
        },
    )


def _insert_catalog_entry(
    conn: sa.engine.Connection,
    *,
    entry_id: str,
    source_id: str,
    name: str,
    title: str = "",
    description: str = "",
    search_tags: Optional[str] = None,
    search_text: str = "",
    deep_search_text: str = "",
    artifact_type: str = "skill",
    confidence_score: int = 80,
    status: str = "new",
) -> None:
    """Insert a ``marketplace_catalog_entries`` row for testing."""
    conn.execute(
        sa.text(
            f"""
            INSERT INTO {_CATALOG_TABLE}
                (id, source_id, artifact_type, name, path, upstream_url,
                 confidence_score, status, title, description,
                 search_tags, search_text, deep_search_text)
            VALUES
                (:id, :source_id, :artifact_type, :name, :path, :upstream_url,
                 :confidence_score, :status, :title, :description,
                 :search_tags, :search_text, :deep_search_text)
            """
        ),
        {
            "id": entry_id,
            "source_id": source_id,
            "artifact_type": artifact_type,
            "name": name,
            "path": f"skills/{name}",
            "upstream_url": f"https://github.com/test/repo/tree/main/skills/{name}",
            "confidence_score": confidence_score,
            "status": status,
            "title": title,
            "description": description,
            "search_tags": search_tags,
            "search_text": search_text,
            "deep_search_text": deep_search_text,
        },
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def pg_engine() -> Generator[sa.engine.Engine, None, None]:
    """Return a SQLAlchemy engine for the test PostgreSQL database."""
    engine = sa.create_engine(_DB_URL, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_db(pg_engine: sa.engine.Engine) -> Generator[None, None, None]:
    """Drop all tables before each test and run migrations to head.

    Using ``autouse=True`` guarantees each test starts with a freshly migrated
    schema, eliminating inter-test order dependencies.
    """
    _drop_all_tables(pg_engine)
    alembic_command.upgrade(_make_alembic_cfg(_DB_URL), "head")
    yield
    # Post-test cleanup intentionally omitted so failures can be inspected.
    # The pre-test teardown above ensures the next test starts clean.


@pytest.fixture()
def pg_session(pg_engine: sa.engine.Engine) -> Generator[Session, None, None]:
    """Return an ORM Session backed by the test PostgreSQL engine.

    Uses a transaction that is rolled back on teardown so tests that rely on
    ORM layer isolation can use this instead of raw connections.
    """
    SessionLocal = sessionmaker(bind=pg_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def source_id(pg_engine: sa.engine.Engine) -> str:
    """Insert a shared marketplace_sources row and return its ID."""
    sid = _unique_id("src")
    with pg_engine.begin() as conn:
        _insert_source(conn, sid)
    return sid


# ---------------------------------------------------------------------------
# Helper: force tsvector backend for MarketplaceCatalogRepository
# ---------------------------------------------------------------------------


def _make_catalog_repo(db_path: str):
    """Create a MarketplaceCatalogRepository wired to the PostgreSQL URL and
    force the tsvector search backend so that ``search()`` always delegates to
    ``_search_tsvector()`` during these tests."""
    import skillmeat.api.utils.fts5 as fts5_module
    from skillmeat.api.utils.fts5 import SearchBackendType
    from skillmeat.cache.repositories import MarketplaceCatalogRepository

    # Override the module-level cached backend so ``get_search_backend()``
    # returns TSVECTOR without needing an application startup probe.
    fts5_module._cached_backend = SearchBackendType.TSVECTOR

    repo = MarketplaceCatalogRepository(db_path=db_path)
    return repo


# ---------------------------------------------------------------------------
# Tests — Migration artefacts
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_migration_creates_search_vector_column(
    pg_engine: sa.engine.Engine,
) -> None:
    """Migration adds ``search_vector`` column to marketplace_catalog_entries."""
    inspector = sa.inspect(pg_engine)
    columns = {col["name"] for col in inspector.get_columns(_CATALOG_TABLE)}
    assert _SEARCH_VECTOR_COL in columns, (
        f"Column '{_SEARCH_VECTOR_COL}' not found in {_CATALOG_TABLE} after "
        "running migrations to head.  Check that "
        "20260310_0001_add_pg_fulltext_search ran successfully."
    )


@pytest.mark.integration
def test_migration_creates_gin_index(
    pg_engine: sa.engine.Engine,
) -> None:
    """Migration creates the GIN index on the ``search_vector`` column."""
    with pg_engine.connect() as conn:
        result = conn.execute(
            sa.text(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = :table
                  AND indexname = :index
                """
            ),
            {"table": _CATALOG_TABLE, "index": _GIN_INDEX},
        )
        row = result.fetchone()

    assert row is not None, (
        f"GIN index '{_GIN_INDEX}' not found on {_CATALOG_TABLE}.  "
        "The migration may not have created it."
    )


# ---------------------------------------------------------------------------
# Tests — Trigger behaviour
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_trigger_populates_search_vector_on_insert(
    pg_engine: sa.engine.Engine,
    source_id: str,
) -> None:
    """INSERT trigger populates ``search_vector`` automatically (not NULL)."""
    entry_id = _unique_id("entry")
    with pg_engine.begin() as conn:
        _insert_catalog_entry(
            conn,
            entry_id=entry_id,
            source_id=source_id,
            name="canvas-skill",
            title="Canvas Design Skill",
            description="A skill for creating canvas layouts",
        )

    with pg_engine.connect() as conn:
        row = conn.execute(
            sa.text(
                f"SELECT {_SEARCH_VECTOR_COL} IS NOT NULL AS populated "
                f"FROM {_CATALOG_TABLE} WHERE id = :id"
            ),
            {"id": entry_id},
        ).fetchone()

    assert row is not None, f"Catalog entry {entry_id!r} not found after INSERT."
    assert row[0] is True, (
        f"search_vector is NULL after INSERT — the trigger "
        f"'{_TRIGGER}' may not have fired."
    )


@pytest.mark.integration
def test_trigger_updates_search_vector_on_title_change(
    pg_engine: sa.engine.Engine,
    source_id: str,
) -> None:
    """UPDATE trigger refreshes ``search_vector`` when ``title`` changes."""
    entry_id = _unique_id("entry")
    with pg_engine.begin() as conn:
        _insert_catalog_entry(
            conn,
            entry_id=entry_id,
            source_id=source_id,
            name="updatable-skill",
            title="Original Title",
            description="Some description",
        )

    with pg_engine.connect() as conn:
        before = conn.execute(
            sa.text(
                f"SELECT {_SEARCH_VECTOR_COL}::text FROM {_CATALOG_TABLE} WHERE id = :id"
            ),
            {"id": entry_id},
        ).scalar()

    with pg_engine.begin() as conn:
        conn.execute(
            sa.text(
                f"UPDATE {_CATALOG_TABLE} SET title = :title WHERE id = :id"
            ),
            {"title": "Completely Different Zephyr Title", "id": entry_id},
        )

    with pg_engine.connect() as conn:
        after = conn.execute(
            sa.text(
                f"SELECT {_SEARCH_VECTOR_COL}::text FROM {_CATALOG_TABLE} WHERE id = :id"
            ),
            {"id": entry_id},
        ).scalar()

    assert before is not None, "search_vector was NULL before UPDATE"
    assert after is not None, "search_vector became NULL after UPDATE"
    assert after != before, (
        "search_vector did not change after title UPDATE — the UPDATE trigger "
        f"'{_TRIGGER}' may not have fired."
    )
    # The new token "zephyr" (from the new title) must appear in the updated vector.
    assert "zephyr" in after.lower(), (
        f"Expected 'zephyr' (from new title) to appear in search_vector after "
        f"UPDATE.  Got: {after!r}"
    )


# ---------------------------------------------------------------------------
# Tests — Search relevance
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_title_match_ranks_higher_than_description_only(
    pg_engine: sa.engine.Engine,
    source_id: str,
) -> None:
    """Title matches (weight A) rank above description-only matches (weight C).

    Inserts two entries that both contain the term "quantum":
    - entry_title: "quantum" appears in the title.
    - entry_desc:  "quantum" appears only in the description.

    The tsvector relevance ranking should place entry_title first.
    """
    entry_title = _unique_id("entry")
    entry_desc = _unique_id("entry")

    with pg_engine.begin() as conn:
        _insert_catalog_entry(
            conn,
            entry_id=entry_title,
            source_id=source_id,
            name="quantum-title",
            title="Quantum Computing Skill",
            description="A skill about general computation",
            confidence_score=75,
        )
        _insert_catalog_entry(
            conn,
            entry_id=entry_desc,
            source_id=source_id,
            name="quantum-desc",
            title="Generic Computation Tool",
            description="Explores quantum mechanics concepts",
            confidence_score=75,
        )

    with pg_engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                f"""
                SELECT id,
                       ts_rank_cd({_SEARCH_VECTOR_COL},
                                   websearch_to_tsquery('english', 'quantum')) AS rank
                FROM {_CATALOG_TABLE}
                WHERE {_SEARCH_VECTOR_COL} @@ websearch_to_tsquery('english', 'quantum')
                ORDER BY rank DESC
                """
            )
        ).fetchall()

    ids_in_order = [row[0] for row in rows]
    assert entry_title in ids_in_order, (
        "Title-matching entry not found in tsvector search results for 'quantum'."
    )
    assert entry_desc in ids_in_order, (
        "Description-matching entry not found in tsvector search results for 'quantum'."
    )
    assert ids_in_order.index(entry_title) < ids_in_order.index(entry_desc), (
        "Expected title match to rank higher than description-only match, but got "
        f"order: {ids_in_order}"
    )


@pytest.mark.integration
def test_tag_search_finds_entry_by_search_tags(
    pg_engine: sa.engine.Engine,
    source_id: str,
) -> None:
    """Entry is found when searching for a term that appears in search_tags."""
    entry_id = _unique_id("entry")
    # Tags are stored as a JSON array serialized to a string and then indexed by
    # the trigger using to_tsvector on the raw string.  Use simple word tokens.
    tags_raw = json.dumps(["automation", "ci-cd", "pipeline"])

    with pg_engine.begin() as conn:
        _insert_catalog_entry(
            conn,
            entry_id=entry_id,
            source_id=source_id,
            name="pipeline-skill",
            title="Pipeline Orchestrator",
            description="Manages build pipelines",
            search_tags=tags_raw,
            confidence_score=80,
        )

    with pg_engine.connect() as conn:
        result = conn.execute(
            sa.text(
                f"""
                SELECT id
                FROM {_CATALOG_TABLE}
                WHERE {_SEARCH_VECTOR_COL} @@ websearch_to_tsquery('english', 'automation')
                """
            )
        ).fetchall()

    ids = [row[0] for row in result]
    assert entry_id in ids, (
        f"Entry {entry_id!r} not found when searching for 'automation' "
        f"(present in search_tags).  Got: {ids}"
    )


@pytest.mark.integration
def test_deep_content_search_returns_deep_match_flag(
    pg_engine: sa.engine.Engine,
    source_id: str,
) -> None:
    """An entry where the query term only appears in ``deep_search_text`` should
    surface with ``deep_match=True`` via the repository search method."""
    import skillmeat.api.utils.fts5 as fts5_module
    from skillmeat.api.utils.fts5 import SearchBackendType
    from skillmeat.cache.repositories import MarketplaceCatalogRepository

    # Override module-level cached backend.
    fts5_module._cached_backend = SearchBackendType.TSVECTOR

    entry_id = _unique_id("entry")
    unique_deep_term = "xylophonematic"  # Very unlikely to appear anywhere else.

    with pg_engine.begin() as conn:
        _insert_catalog_entry(
            conn,
            entry_id=entry_id,
            source_id=source_id,
            name="deep-indexed-skill",
            title="Some Ordinary Skill",
            description="Does not mention the secret term",
            deep_search_text=f"The secret term is {unique_deep_term} found deep",
            confidence_score=70,
        )

    repo = MarketplaceCatalogRepository(db_path=_DB_URL)
    result = repo.search(query=unique_deep_term, limit=10)

    matching = [e for e in result.items if e.id == entry_id]
    assert matching, (
        f"Entry {entry_id!r} not found in search results for {unique_deep_term!r}.  "
        f"Got {len(result.items)} items total."
    )

    snippets = result.snippets or {}
    snippet_data = snippets.get(entry_id, {})
    assert snippet_data.get("deep_match") is True, (
        f"Expected deep_match=True for entry where query term is only in "
        f"deep_search_text.  Got snippet_data={snippet_data!r}"
    )


# ---------------------------------------------------------------------------
# Tests — Cursor pagination
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_cursor_pagination_returns_next_page(
    pg_engine: sa.engine.Engine,
    source_id: str,
) -> None:
    """Searching with ``limit=2`` produces a cursor; using it returns page 2."""
    import skillmeat.api.utils.fts5 as fts5_module
    from skillmeat.api.utils.fts5 import SearchBackendType
    from skillmeat.cache.repositories import MarketplaceCatalogRepository

    fts5_module._cached_backend = SearchBackendType.TSVECTOR

    # Insert 5 entries that all share the query term.
    prefix = _unique_id("pag")
    with pg_engine.begin() as conn:
        for i in range(5):
            _insert_catalog_entry(
                conn,
                entry_id=f"{prefix}-{i}",
                source_id=source_id,
                name=f"pagination-skill-{i}",
                title=f"Pagination Skill Number {i}",
                description="Shared description term: pagiterm",
                confidence_score=80,
            )

    repo = MarketplaceCatalogRepository(db_path=_DB_URL)

    # First page.
    page1 = repo.search(query="pagiterm", limit=2)
    assert len(page1.items) == 2, (
        f"Expected 2 items on first page, got {len(page1.items)}."
    )
    assert page1.has_more is True, (
        "Expected has_more=True after first page of 2 from 5 results."
    )
    assert page1.next_cursor is not None, (
        "Expected next_cursor to be set when has_more=True."
    )

    # Second page using the cursor.
    page2 = repo.search(query="pagiterm", limit=2, cursor=page1.next_cursor)
    assert len(page2.items) >= 1, (
        f"Expected at least 1 item on second page, got {len(page2.items)}."
    )

    # No item should appear on both pages.
    page1_ids = {e.id for e in page1.items}
    page2_ids = {e.id for e in page2.items}
    overlap = page1_ids & page2_ids
    assert not overlap, (
        f"Items appeared on both pages: {overlap}.  Cursor pagination is broken."
    )


# ---------------------------------------------------------------------------
# Tests — Snippet markup
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_search_snippets_contain_mark_tags(
    pg_engine: sa.engine.Engine,
    source_id: str,
) -> None:
    """Snippets for matching entries contain ``<mark>`` highlight tags."""
    import skillmeat.api.utils.fts5 as fts5_module
    from skillmeat.api.utils.fts5 import SearchBackendType
    from skillmeat.cache.repositories import MarketplaceCatalogRepository

    fts5_module._cached_backend = SearchBackendType.TSVECTOR

    entry_id = _unique_id("entry")
    with pg_engine.begin() as conn:
        _insert_catalog_entry(
            conn,
            entry_id=entry_id,
            source_id=source_id,
            name="markdown-skill",
            title="Markdown Rendering Tool",
            description="A tool that renders markdown documents beautifully",
            confidence_score=85,
        )

    repo = MarketplaceCatalogRepository(db_path=_DB_URL)
    result = repo.search(query="markdown", limit=10)

    matching = [e for e in result.items if e.id == entry_id]
    assert matching, (
        f"Entry {entry_id!r} not found in search results for 'markdown'."
    )

    snippets = result.snippets or {}
    snippet_data = snippets.get(entry_id, {})

    # At least one of title_snippet or description_snippet should contain <mark>.
    title_snip = snippet_data.get("title_snippet") or ""
    desc_snip = snippet_data.get("description_snippet") or ""
    has_mark = "<mark>" in title_snip or "<mark>" in desc_snip
    assert has_mark, (
        f"Expected <mark> highlight tags in snippet for entry {entry_id!r}.  "
        f"title_snippet={title_snip!r}, description_snippet={desc_snip!r}"
    )


# ---------------------------------------------------------------------------
# Tests — Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_empty_query_returns_results_without_exception(
    pg_engine: sa.engine.Engine,
    source_id: str,
) -> None:
    """Empty query falls back gracefully and returns results without raising."""
    import skillmeat.api.utils.fts5 as fts5_module
    from skillmeat.api.utils.fts5 import SearchBackendType
    from skillmeat.cache.repositories import MarketplaceCatalogRepository

    fts5_module._cached_backend = SearchBackendType.TSVECTOR

    entry_id = _unique_id("entry")
    with pg_engine.begin() as conn:
        _insert_catalog_entry(
            conn,
            entry_id=entry_id,
            source_id=source_id,
            name="empty-query-skill",
            title="General Skill",
            description="Should appear in no-query listing",
        )

    repo = MarketplaceCatalogRepository(db_path=_DB_URL)

    # Empty query should not raise — it falls back to LIKE/all-results path.
    result = repo.search(query="", limit=50)
    assert isinstance(result.items, list), (
        "Expected a list of items for empty query, got something else."
    )
    # The entry we inserted should appear (no-query returns all active entries).
    ids = {e.id for e in result.items}
    assert entry_id in ids, (
        f"Entry {entry_id!r} not found in empty-query results.  Got {ids}"
    )


@pytest.mark.integration
def test_special_characters_only_query_does_not_raise(
    pg_engine: sa.engine.Engine,
    source_id: str,
) -> None:
    """A query composed entirely of special characters is handled gracefully.

    ``websearch_to_tsquery`` may strip all tokens, leaving a no-op query.
    The repository must fall back without raising an exception.
    """
    import skillmeat.api.utils.fts5 as fts5_module
    from skillmeat.api.utils.fts5 import SearchBackendType
    from skillmeat.cache.repositories import MarketplaceCatalogRepository

    fts5_module._cached_backend = SearchBackendType.TSVECTOR

    with pg_engine.begin() as conn:
        _insert_catalog_entry(
            conn,
            entry_id=_unique_id("entry"),
            source_id=source_id,
            name="noise-skill",
            title="Noise Reducer",
            description="Removes signal noise",
        )

    repo = MarketplaceCatalogRepository(db_path=_DB_URL)

    # These queries should not raise regardless of whether they return results.
    for noisy_query in ("!!!@@@###", "--- ---", "'''", '"""'):
        try:
            result = repo.search(query=noisy_query, limit=10)
            assert isinstance(result.items, list), (
                f"Expected list for query {noisy_query!r}, got {type(result.items)}"
            )
        except Exception as exc:
            pytest.fail(
                f"repo.search(query={noisy_query!r}) raised {type(exc).__name__}: {exc}"
            )


# ---------------------------------------------------------------------------
# Tests — LIKE vs tsvector comparison
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_tsvector_is_superset_of_like_for_same_query(
    pg_engine: sa.engine.Engine,
    source_id: str,
) -> None:
    """tsvector results are a superset of (or equal to) LIKE results.

    Any entry found by a case-insensitive LIKE search for a query term must
    also appear in the tsvector results for the same term.  This guards against
    tsvector silently dropping results that LIKE would find.
    """
    import skillmeat.api.utils.fts5 as fts5_module
    from skillmeat.api.utils.fts5 import SearchBackendType
    from skillmeat.cache.repositories import MarketplaceCatalogRepository

    term = "retrieval"

    # Insert entries that mention the term in various fields.
    entries = [
        ("title-only", "Retrieval Augmented Tool", "Does other things", ""),
        ("desc-only", "Another Tool", "Uses information retrieval techniques", ""),
        ("both-fields", "Retrieval Pipeline", "Efficient retrieval architecture", ""),
    ]

    inserted_ids = set()
    with pg_engine.begin() as conn:
        for name, title, desc, deep in entries:
            eid = _unique_id(name)
            inserted_ids.add(eid)
            _insert_catalog_entry(
                conn,
                entry_id=eid,
                source_id=source_id,
                name=name,
                title=title,
                description=desc,
                deep_search_text=deep,
                confidence_score=75,
            )

    # LIKE results via raw SQL (case-insensitive).
    with pg_engine.connect() as conn:
        like_rows = conn.execute(
            sa.text(
                f"""
                SELECT id FROM {_CATALOG_TABLE}
                WHERE (LOWER(title) LIKE :pat
                    OR LOWER(description) LIKE :pat)
                  AND status NOT IN ('excluded', 'removed')
                  AND id = ANY(:ids)
                """
            ),
            {"pat": f"%{term.lower()}%", "ids": list(inserted_ids)},
        ).fetchall()
    like_ids = {row[0] for row in like_rows}

    # tsvector results via repository.
    fts5_module._cached_backend = SearchBackendType.TSVECTOR
    repo = MarketplaceCatalogRepository(db_path=_DB_URL)
    ts_result = repo.search(query=term, limit=100)
    ts_ids = {e.id for e in ts_result.items} & inserted_ids

    missing = like_ids - ts_ids
    assert not missing, (
        f"tsvector search missed {len(missing)} entry/entries that LIKE found: "
        f"{missing}.  tsvector should be a superset of LIKE results."
    )
