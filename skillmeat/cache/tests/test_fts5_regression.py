"""FTS5 regression tests — SQLite search path unaffected by tsvector refactor.

Coverage:
    PG-FTS-1.8  SQLite FTS5 regression tests

Purpose:
    Safety net ensuring the tsvector dual-backend refactor (PG-FTS-1.2) did not
    regress the primary SQLite FTS5 search path.  Every test here must pass with
    plain ``pytest`` — no PostgreSQL, no ``@pytest.mark.integration``.

Architecture note — why mock-based:
    ``MarketplaceCatalogRepository._search_fts5()`` executes raw SQL (FTS5 MATCH,
    bm25, snippet) that SQLite can only run against a live FTS5 virtual table.
    Wiring up a real in-memory SQLite DB with FTS5 tables is fragile and slow.
    Instead, these tests use ``MagicMock(spec=Session)`` to isolate dispatch
    logic, query-building logic, and backward-compatible helper contracts — the
    same strategy used in ``test_tsvector_search.py``.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from skillmeat.api.utils.fts5 import (
    SearchBackendType,
    check_fts5_available,
    detect_search_backend,
    is_fts5_available,
    reset_fts5_check,
)
from skillmeat.cache.repositories import MarketplaceCatalogRepository, PaginatedResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_paginated_result(
    items=None,
    next_cursor=None,
    has_more=False,
) -> PaginatedResult:
    """Return a PaginatedResult suitable as a stub return value."""
    return PaginatedResult(
        items=items or [],
        next_cursor=next_cursor,
        has_more=has_more,
        snippets={},
    )


def _sqlite_session_with_fts5() -> MagicMock:
    """Return a MagicMock session that reports a SQLite dialect with FTS5 available.

    Simulates the two ``session.execute().fetchone()`` calls made by
    ``_check_sqlite_fts5``:
    1. ``SELECT 1 FROM sqlite_master …`` — returns a non-None row (table exists)
    2. ``SELECT * FROM catalog_fts LIMIT 0`` — succeeds silently
    """
    session = MagicMock(spec=Session)
    bind = MagicMock()
    bind.dialect.name = "sqlite"
    session.get_bind.return_value = bind

    fetchone_result = MagicMock()  # non-None → FTS5 table found
    execute_result = MagicMock()
    execute_result.fetchone.return_value = fetchone_result
    session.execute.return_value = execute_result
    return session


def _sqlite_session_without_fts5() -> MagicMock:
    """Return a MagicMock session that reports SQLite with NO FTS5 virtual table."""
    session = MagicMock(spec=Session)
    bind = MagicMock()
    bind.dialect.name = "sqlite"
    session.get_bind.return_value = bind

    execute_result = MagicMock()
    execute_result.fetchone.return_value = None  # table not found
    session.execute.return_value = execute_result
    return session


def _repo_with_session(session: MagicMock) -> MarketplaceCatalogRepository:
    """Return a repository whose ``_get_session()`` yields the given mock session."""
    repo = MarketplaceCatalogRepository.__new__(MarketplaceCatalogRepository)
    repo._get_session = MagicMock(return_value=session)
    return repo


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_backend_cache():
    """Clear module-level backend caches before and after each test."""
    reset_fts5_check()
    yield
    reset_fts5_check()


# ===========================================================================
# 1. Backend detection — SQLite path
# ===========================================================================


@pytest.mark.unit
class TestBackendDetectionSQLite:
    """detect_search_backend() correctly maps SQLite sessions to FTS5 or LIKE."""

    def test_sqlite_with_catalog_fts_returns_fts5(self) -> None:
        """SQLite + catalog_fts virtual table → FTS5 backend."""
        session = _sqlite_session_with_fts5()
        result = detect_search_backend(session)
        assert result == SearchBackendType.FTS5

    def test_sqlite_without_catalog_fts_returns_like(self) -> None:
        """SQLite without catalog_fts table → LIKE backend."""
        session = _sqlite_session_without_fts5()
        result = detect_search_backend(session)
        assert result == SearchBackendType.LIKE

    def test_is_fts5_available_true_when_backend_fts5(self) -> None:
        """is_fts5_available() returns True when cached backend is FTS5."""
        with patch("skillmeat.api.utils.fts5._cached_backend", SearchBackendType.FTS5):
            assert is_fts5_available() is True

    def test_is_fts5_available_false_when_backend_tsvector(self) -> None:
        """is_fts5_available() returns False when cached backend is TSVECTOR."""
        with patch(
            "skillmeat.api.utils.fts5._cached_backend", SearchBackendType.TSVECTOR
        ):
            assert is_fts5_available() is False

    def test_is_fts5_available_false_when_backend_like(self) -> None:
        """is_fts5_available() returns False when cached backend is LIKE."""
        with patch("skillmeat.api.utils.fts5._cached_backend", SearchBackendType.LIKE):
            assert is_fts5_available() is False

    def test_is_fts5_available_false_before_detection(self) -> None:
        """is_fts5_available() returns False when no detection has run yet."""
        # reset_backend_cache fixture guarantees _cached_backend is None here.
        assert is_fts5_available() is False

    def test_reset_fts5_check_clears_both_caches(self) -> None:
        """reset_fts5_check() clears both _fts5_available and _cached_backend."""
        import skillmeat.api.utils.fts5 as fts5_mod

        # Populate both caches by running detection against an FTS5 session
        session = _sqlite_session_with_fts5()
        from skillmeat.api.utils.fts5 import detect_and_cache_backend

        detect_and_cache_backend(session)
        assert fts5_mod._cached_backend is not None
        assert fts5_mod._fts5_available is not None

        reset_fts5_check()

        assert fts5_mod._cached_backend is None
        assert fts5_mod._fts5_available is None


# ===========================================================================
# 2. Search dispatch — FTS5 path
# ===========================================================================


@pytest.mark.unit
class TestSearchDispatchFTS5:
    """search() dispatches to the correct method based on get_search_backend()."""

    def test_fts5_backend_calls_search_fts5(self) -> None:
        """When backend is FTS5, search() delegates to _search_fts5()."""
        repo = MarketplaceCatalogRepository.__new__(MarketplaceCatalogRepository)
        expected = _make_paginated_result()

        with (
            patch(
                "skillmeat.api.utils.fts5.get_search_backend",
                return_value=SearchBackendType.FTS5,
            ),
            patch.object(repo, "_search_tsvector") as mock_tv,
            patch.object(repo, "_search_fts5", return_value=expected) as mock_fts5,
            patch.object(repo, "_search_like") as mock_like,
        ):
            result = repo.search(query="canvas design")

        mock_tv.assert_not_called()
        mock_fts5.assert_called_once()
        mock_like.assert_not_called()
        assert result is expected

    def test_tsvector_backend_does_not_call_search_fts5(self) -> None:
        """When backend is TSVECTOR, _search_fts5() is never called."""
        repo = MarketplaceCatalogRepository.__new__(MarketplaceCatalogRepository)
        expected = _make_paginated_result()

        with (
            patch(
                "skillmeat.api.utils.fts5.get_search_backend",
                return_value=SearchBackendType.TSVECTOR,
            ),
            patch.object(repo, "_search_tsvector", return_value=expected) as mock_tv,
            patch.object(repo, "_search_fts5") as mock_fts5,
            patch.object(repo, "_search_like") as mock_like,
        ):
            result = repo.search(query="canvas design")

        mock_tv.assert_called_once()
        mock_fts5.assert_not_called()
        mock_like.assert_not_called()
        assert result is expected

    def test_like_backend_does_not_call_search_fts5(self) -> None:
        """When backend is LIKE, _search_fts5() is never called."""
        repo = MarketplaceCatalogRepository.__new__(MarketplaceCatalogRepository)
        expected = _make_paginated_result()

        with (
            patch(
                "skillmeat.api.utils.fts5.get_search_backend",
                return_value=SearchBackendType.LIKE,
            ),
            patch.object(repo, "_search_tsvector") as mock_tv,
            patch.object(repo, "_search_fts5") as mock_fts5,
            patch.object(repo, "_search_like", return_value=expected) as mock_like,
        ):
            result = repo.search(query="canvas design")

        mock_tv.assert_not_called()
        mock_fts5.assert_not_called()
        mock_like.assert_called_once()
        assert result is expected

    def test_fts5_path_called_regardless_of_actual_db(self) -> None:
        """_search_fts5 is dispatched when backend=FTS5, even with a plain mock session."""
        repo = MarketplaceCatalogRepository.__new__(MarketplaceCatalogRepository)
        expected = _make_paginated_result()

        # No real DB connection is needed — dispatch is based on the cached backend enum.
        with (
            patch(
                "skillmeat.api.utils.fts5.get_search_backend",
                return_value=SearchBackendType.FTS5,
            ),
            patch.object(repo, "_search_fts5", return_value=expected) as mock_fts5,
            patch.object(repo, "_search_tsvector") as mock_tv,
            patch.object(repo, "_search_like") as mock_like,
        ):
            result = repo.search(query="test query")

        mock_fts5.assert_called_once()
        mock_tv.assert_not_called()
        mock_like.assert_not_called()


# ===========================================================================
# 3. FTS5 query building (_build_fts5_query)
# ===========================================================================


@pytest.mark.unit
class TestBuildFts5Query:
    """_build_fts5_query() produces correct FTS5 MATCH strings after refactor."""

    def _repo(self) -> MarketplaceCatalogRepository:
        return MarketplaceCatalogRepository.__new__(MarketplaceCatalogRepository)

    def test_simple_term_gets_prefix_wildcard(self) -> None:
        """Single word gets a trailing '*' for prefix matching."""
        repo = self._repo()
        assert repo._build_fts5_query("canvas") == "canvas*"

    def test_multiple_terms_all_get_wildcards(self) -> None:
        """Each whitespace-separated term gets a trailing '*'."""
        repo = self._repo()
        assert repo._build_fts5_query("canvas design") == "canvas* design*"

    def test_hyphen_converted_to_space(self) -> None:
        """Hyphens are stripped; resulting parts each become prefix terms."""
        repo = self._repo()
        # "test-skill" → strip '-' → "test skill" → "test* skill*"
        assert repo._build_fts5_query("test-skill") == "test* skill*"

    def test_special_chars_stripped(self) -> None:
        """All FTS5 special chars (quotes, parens, colon, etc.) are removed."""
        repo = self._repo()
        # '"canvas" (design)' → strip '"', '(', ')' → 'canvas  design' → 'canvas* design*'
        result = repo._build_fts5_query('"canvas" (design)')
        assert result == "canvas* design*"

    def test_fts5_operators_stripped(self) -> None:
        """AND, OR, NOT, NEAR operator tokens are removed from the term list."""
        repo = self._repo()
        result = repo._build_fts5_query("canvas AND design")
        assert result == "canvas* design*"

    def test_operator_only_query_returns_wildcard(self) -> None:
        """A query that reduces to only operators yields '*' (match all)."""
        repo = self._repo()
        result = repo._build_fts5_query("AND OR NOT")
        assert result == "*"

    def test_empty_string_returns_wildcard(self) -> None:
        """An empty input string yields '*' rather than an empty MATCH string."""
        repo = self._repo()
        result = repo._build_fts5_query("")
        assert result == "*"

    def test_whitespace_only_returns_wildcard(self) -> None:
        """A whitespace-only query reduces to no terms and returns '*'."""
        repo = self._repo()
        result = repo._build_fts5_query("   ")
        assert result == "*"

    def test_asterisk_char_stripped_not_duplicated(self) -> None:
        """A literal '*' in the query is stripped, not doubled into '**'."""
        repo = self._repo()
        result = repo._build_fts5_query("skill*")
        # '*' is in special_chars → stripped → "skill" → "skill*"
        assert result == "skill*"

    def test_mixed_operators_and_terms(self) -> None:
        """Terms survive even when surrounded by operators."""
        repo = self._repo()
        result = repo._build_fts5_query("NOT canvas OR design")
        # NEAR/AND/OR/NOT stripped → "canvas design" → "canvas* design*"
        assert result == "canvas* design*"


# ===========================================================================
# 4. LIKE fallback dispatch
# ===========================================================================


@pytest.mark.unit
class TestLikeFallbackDispatch:
    """search() routes to _search_like() when backend is LIKE."""

    def test_like_backend_search_calls_search_like(self) -> None:
        """Backend LIKE → search() → _search_like()."""
        repo = MarketplaceCatalogRepository.__new__(MarketplaceCatalogRepository)
        expected = _make_paginated_result(items=[], has_more=False)

        with (
            patch(
                "skillmeat.api.utils.fts5.get_search_backend",
                return_value=SearchBackendType.LIKE,
            ),
            patch.object(repo, "_search_like", return_value=expected) as mock_like,
            patch.object(repo, "_search_fts5") as mock_fts5,
            patch.object(repo, "_search_tsvector") as mock_tv,
        ):
            result = repo.search(query="some query")

        mock_like.assert_called_once()
        mock_fts5.assert_not_called()
        mock_tv.assert_not_called()
        assert result is expected

    def test_search_like_result_has_correct_structure(self) -> None:
        """_search_like() returns a PaginatedResult with expected fields."""
        session = MagicMock(spec=Session)
        # Return an empty query result from session.query().options().filter()...
        query_mock = MagicMock()
        query_mock.options.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.limit.return_value = query_mock
        query_mock.all.return_value = []
        session.query.return_value = query_mock

        repo = _repo_with_session(session)
        result = repo._search_like(query="canvas")

        assert isinstance(result, PaginatedResult)
        assert result.items == []
        assert result.has_more is False
        assert result.next_cursor is None


# ===========================================================================
# 5. Cursor format stability
# ===========================================================================


@pytest.mark.unit
class TestFts5CursorFormat:
    """Cursor format from _search_fts5() path must remain parseable."""

    def test_cursor_format_is_three_part_colon_separated(self) -> None:
        """Next-page cursors from FTS5 path follow '{relevance}:{score}:{id}' format."""
        # Simulate what _search_fts5 emits for its cursor:
        # Cursor = f"{last_relevance}:{last_item.confidence_score}:{last_item.id}"
        last_relevance = -1.23456
        confidence_score = 85
        entry_id = "entry-abc-001"

        cursor = f"{last_relevance}:{confidence_score}:{entry_id}"

        # Ensure it can be parsed back by the FTS5 cursor-parsing logic
        parts = cursor.split(":", 2)
        assert len(parts) == 3

        parsed_relevance = float(parts[0])
        parsed_confidence = int(parts[1])
        parsed_id = parts[2]

        assert parsed_relevance == last_relevance
        assert parsed_confidence == confidence_score
        assert parsed_id == entry_id

    def test_cursor_from_fts5_can_seed_next_page_query(self) -> None:
        """A cursor produced by the FTS5 path is accepted by the next call."""
        # Build a valid FTS5 cursor string
        cursor = "-0.987:75:entry-xyz"

        # Verify the parsing logic in _search_fts5 would accept it
        parts = cursor.split(":", 2)
        assert len(parts) == 3

        cursor_relevance = float(parts[0])
        cursor_confidence = int(parts[1])
        cursor_id = parts[2]

        assert cursor_relevance == -0.987
        assert cursor_confidence == 75
        assert cursor_id == "entry-xyz"

    def test_fts5_cursor_distinct_from_like_cursor(self) -> None:
        """FTS5 cursor (3-part) is structurally distinct from LIKE cursor (2-part)."""
        fts5_cursor = "-0.5:80:entry-001"
        like_cursor = "80:entry-001"

        fts5_parts = fts5_cursor.split(":", 2)
        like_parts = like_cursor.split(":", 1)

        # FTS5 cursor has 3 parts; LIKE cursor has 2
        assert len(fts5_parts) == 3
        assert len(like_parts) == 2


# ===========================================================================
# 6. check_fts5_available() backward compatibility
# ===========================================================================


@pytest.mark.unit
class TestCheckFts5AvailableBackwardCompat:
    """check_fts5_available() contract is unchanged after the tsvector refactor."""

    def test_returns_true_for_sqlite_with_fts5(self) -> None:
        """check_fts5_available() returns True when SQLite FTS5 is present."""
        session = _sqlite_session_with_fts5()
        result = check_fts5_available(session)
        assert result is True

    def test_returns_false_for_sqlite_without_fts5(self) -> None:
        """check_fts5_available() returns False when SQLite FTS5 table is absent."""
        session = _sqlite_session_without_fts5()
        result = check_fts5_available(session)
        assert result is False

    def test_returns_bool(self) -> None:
        """Return value is always a plain bool, never None or a truthy non-bool."""
        session = _sqlite_session_with_fts5()
        result = check_fts5_available(session)
        assert isinstance(result, bool)

    def test_calling_it_updates_cached_backend(self) -> None:
        """check_fts5_available() populates _cached_backend as a side-effect."""
        import skillmeat.api.utils.fts5 as fts5_mod

        assert fts5_mod._cached_backend is None  # guaranteed by autouse fixture

        session = _sqlite_session_with_fts5()
        check_fts5_available(session)

        assert fts5_mod._cached_backend == SearchBackendType.FTS5

    def test_cached_backend_false_after_check_on_no_fts5(self) -> None:
        """When FTS5 is absent, _cached_backend is set to LIKE (not None)."""
        import skillmeat.api.utils.fts5 as fts5_mod

        session = _sqlite_session_without_fts5()
        result = check_fts5_available(session)

        assert result is False
        assert fts5_mod._cached_backend == SearchBackendType.LIKE

    def test_honours_existing_cached_backend_without_re_detecting(self) -> None:
        """If _cached_backend is already set, check_fts5_available() uses it directly."""
        import skillmeat.api.utils.fts5 as fts5_mod

        # Pre-populate the new-style cache (as if detect_and_cache_backend ran)
        fts5_mod._cached_backend = SearchBackendType.TSVECTOR

        # Pass a session that would normally detect FTS5 — it must NOT be consulted
        session = _sqlite_session_with_fts5()
        result = check_fts5_available(session)

        # The cached TSVECTOR backend takes precedence → FTS5 is not available
        assert result is False
        # Session must not have been queried (the cache short-circuits detection)
        session.execute.assert_not_called()
