"""Unit tests for tsvector full-text search implementation.

Coverage:
    PG-FTS-1.6  Unit tests for tsvector search

Architecture note — why mock-based:
    ``MarketplaceCatalogRepository._search_tsvector()`` calls
    ``session.execute()`` with PostgreSQL-specific SQL expressions
    (``websearch_to_tsquery``, ``ts_rank_cd``, ``ts_headline``,
    ``search_vector.op("@@")``) that SQLite cannot compile.  All tests
    therefore use ``MagicMock`` sessions so that repository logic
    (query cleaning, fallbacks, deep_match detection, cursor formatting,
    dispatch) is exercised without a live database.

    Backend detection tests use ``MagicMock(spec=Session)`` with a patched
    dialect so that ``detect_search_backend()`` can be exercised in isolation.
"""

from __future__ import annotations

import logging
from typing import List, Optional
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from skillmeat.api.utils.fts5 import (
    SearchBackendType,
    detect_search_backend,
    is_fts5_available,
    is_tsvector_available,
    reset_fts5_check,
)
from skillmeat.cache.repositories import MarketplaceCatalogRepository, PaginatedResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entry(
    entry_id: str = "entry-001",
    confidence_score: int = 80,
    status: str = "new",
) -> MagicMock:
    """Return a lightweight MarketplaceCatalogEntry-shaped mock."""
    entry = MagicMock()
    entry.id = entry_id
    entry.confidence_score = confidence_score
    entry.status = status
    return entry


def _make_like_result(
    items: Optional[List[MagicMock]] = None,
    next_cursor: Optional[str] = None,
    has_more: bool = False,
) -> PaginatedResult:
    """Build a PaginatedResult that simulates a LIKE-path response."""
    return PaginatedResult(
        items=items or [],
        next_cursor=next_cursor,
        has_more=has_more,
        snippets={},
    )


def _make_session_with_rows(rows: list) -> MagicMock:
    """Return a MagicMock(spec=Session) whose execute().all() returns *rows*."""
    session = MagicMock(spec=Session)
    execute_result = MagicMock()
    execute_result.all.return_value = rows
    session.execute.return_value = execute_result
    return session


def _repo_with_session(session: MagicMock) -> MarketplaceCatalogRepository:
    """Return a MarketplaceCatalogRepository whose _get_session() yields *session*."""
    repo = MarketplaceCatalogRepository.__new__(MarketplaceCatalogRepository)
    repo._get_session = MagicMock(return_value=session)
    return repo


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_backend_cache():
    """Reset fts5/tsvector module-level cache before and after each test."""
    reset_fts5_check()
    yield
    reset_fts5_check()


# ===========================================================================
# 1. Backend detection tests (detect_search_backend)
# ===========================================================================


@pytest.mark.unit
class TestDetectSearchBackend:
    """detect_search_backend() probes the dialect and column existence."""

    def _pg_session(self, has_search_vector: bool = True) -> MagicMock:
        """Return a mock session that looks like PostgreSQL."""
        session = MagicMock(spec=Session)
        # Simulate session.get_bind() → engine with dialect.name == "postgresql"
        bind = MagicMock()
        bind.dialect.name = "postgresql"
        session.get_bind.return_value = bind

        # _check_pg_tsvector() does session.execute(...).fetchone()
        fetchone_result = MagicMock() if has_search_vector else None
        execute_result = MagicMock()
        execute_result.fetchone.return_value = fetchone_result
        session.execute.return_value = execute_result

        return session

    def _sqlite_session(self, has_fts5: bool = True) -> MagicMock:
        """Return a mock session that looks like SQLite."""
        session = MagicMock(spec=Session)
        bind = MagicMock()
        bind.dialect.name = "sqlite"
        session.get_bind.return_value = bind

        # _check_sqlite_fts5() first checks sqlite_master, then probes the table.
        # Both calls go through session.execute().fetchone().
        fetchone_result = MagicMock() if has_fts5 else None
        execute_result = MagicMock()
        execute_result.fetchone.return_value = fetchone_result
        session.execute.return_value = execute_result

        return session

    def test_pg_with_search_vector_returns_tsvector(self) -> None:
        """PostgreSQL + search_vector column → TSVECTOR backend."""
        session = self._pg_session(has_search_vector=True)
        result = detect_search_backend(session)
        assert result == SearchBackendType.TSVECTOR

    def test_pg_without_search_vector_returns_like(self) -> None:
        """PostgreSQL without search_vector column → LIKE backend."""
        session = self._pg_session(has_search_vector=False)
        result = detect_search_backend(session)
        assert result == SearchBackendType.LIKE

    def test_sqlite_with_fts5_returns_fts5(self) -> None:
        """SQLite with catalog_fts virtual table → FTS5 backend."""
        session = self._sqlite_session(has_fts5=True)
        result = detect_search_backend(session)
        assert result == SearchBackendType.FTS5

    def test_sqlite_without_fts5_returns_like(self) -> None:
        """SQLite without catalog_fts table → LIKE backend."""
        session = self._sqlite_session(has_fts5=False)
        result = detect_search_backend(session)
        assert result == SearchBackendType.LIKE

    def test_unknown_dialect_returns_like(self) -> None:
        """An unrecognised dialect name always falls back to LIKE."""
        session = MagicMock(spec=Session)
        bind = MagicMock()
        bind.dialect.name = "oracle"
        session.get_bind.return_value = bind
        result = detect_search_backend(session)
        assert result == SearchBackendType.LIKE

    def test_get_bind_exception_falls_back_to_bind(self) -> None:
        """When get_bind() raises, falls back to session.bind attribute."""
        session = MagicMock(spec=Session)
        session.get_bind.side_effect = Exception("not supported")

        # Provide dialect via session.bind
        bind = MagicMock()
        bind.dialect.name = "sqlite"
        session.bind = bind

        # Mock the _check_sqlite_fts5 to return True (fts5 available)
        fetchone_result = MagicMock()
        execute_result = MagicMock()
        execute_result.fetchone.return_value = fetchone_result
        session.execute.return_value = execute_result

        result = detect_search_backend(session)
        assert result == SearchBackendType.FTS5

    def test_detection_exception_returns_like(self) -> None:
        """Any unhandled exception during detection yields LIKE (safe fallback)."""
        session = MagicMock(spec=Session)
        session.get_bind.side_effect = RuntimeError("catastrophic failure")
        # Make session.bind also fail so there's no fallback
        del session.bind  # Ensure AttributeError on .bind access

        result = detect_search_backend(session)
        assert result == SearchBackendType.LIKE


# ===========================================================================
# 2. Cached accessor tests (is_tsvector_available / is_fts5_available)
# ===========================================================================


@pytest.mark.unit
class TestCachedAccessors:
    """is_tsvector_available() / is_fts5_available() reflect cached backend."""

    def test_is_tsvector_available_true_when_tsvector(self) -> None:
        """is_tsvector_available() returns True iff cached backend is TSVECTOR."""
        with patch("skillmeat.api.utils.fts5._cached_backend", SearchBackendType.TSVECTOR):
            assert is_tsvector_available() is True

    def test_is_tsvector_available_false_when_fts5(self) -> None:
        with patch("skillmeat.api.utils.fts5._cached_backend", SearchBackendType.FTS5):
            assert is_tsvector_available() is False

    def test_is_tsvector_available_false_when_like(self) -> None:
        with patch("skillmeat.api.utils.fts5._cached_backend", SearchBackendType.LIKE):
            assert is_tsvector_available() is False

    def test_is_fts5_available_true_when_fts5(self) -> None:
        """is_fts5_available() still returns True when backend is FTS5."""
        with patch("skillmeat.api.utils.fts5._cached_backend", SearchBackendType.FTS5):
            assert is_fts5_available() is True

    def test_is_fts5_available_false_when_tsvector(self) -> None:
        with patch("skillmeat.api.utils.fts5._cached_backend", SearchBackendType.TSVECTOR):
            assert is_fts5_available() is False

    def test_is_tsvector_available_false_when_uncached(self) -> None:
        """Before any detection run, is_tsvector_available() returns False."""
        # reset_backend_cache fixture ensures _cached_backend is None
        assert is_tsvector_available() is False

    def test_is_fts5_available_false_when_uncached(self) -> None:
        """Before any detection run, is_fts5_available() returns False."""
        assert is_fts5_available() is False


# ===========================================================================
# 3. Search dispatch tests (search() method)
# ===========================================================================


@pytest.mark.unit
class TestSearchDispatch:
    """search() routes to the correct backend based on get_search_backend()."""

    def test_search_calls_tsvector_when_backend_tsvector(self) -> None:
        """When backend is TSVECTOR, search() delegates to _search_tsvector()."""
        repo = MarketplaceCatalogRepository.__new__(MarketplaceCatalogRepository)
        expected = _make_like_result()

        # get_search_backend is imported lazily inside search() from
        # skillmeat.api.utils.fts5, so patch it at the source module.
        with (
            patch(
                "skillmeat.api.utils.fts5.get_search_backend",
                return_value=SearchBackendType.TSVECTOR,
            ),
            patch.object(repo, "_search_tsvector", return_value=expected) as mock_tv,
            patch.object(repo, "_search_fts5") as mock_fts5,
            patch.object(repo, "_search_like") as mock_like,
        ):
            result = repo.search(query="canvas")

        mock_tv.assert_called_once()
        mock_fts5.assert_not_called()
        mock_like.assert_not_called()
        assert result is expected

    def test_search_calls_fts5_when_backend_fts5(self) -> None:
        """When backend is FTS5, search() delegates to _search_fts5()."""
        repo = MarketplaceCatalogRepository.__new__(MarketplaceCatalogRepository)
        expected = _make_like_result()

        with (
            patch(
                "skillmeat.api.utils.fts5.get_search_backend",
                return_value=SearchBackendType.FTS5,
            ),
            patch.object(repo, "_search_tsvector") as mock_tv,
            patch.object(repo, "_search_fts5", return_value=expected) as mock_fts5,
            patch.object(repo, "_search_like") as mock_like,
        ):
            result = repo.search(query="canvas")

        mock_tv.assert_not_called()
        mock_fts5.assert_called_once()
        mock_like.assert_not_called()
        assert result is expected

    def test_search_calls_like_when_backend_like(self) -> None:
        """When backend is LIKE, search() delegates to _search_like()."""
        repo = MarketplaceCatalogRepository.__new__(MarketplaceCatalogRepository)
        expected = _make_like_result()

        with (
            patch(
                "skillmeat.api.utils.fts5.get_search_backend",
                return_value=SearchBackendType.LIKE,
            ),
            patch.object(repo, "_search_tsvector") as mock_tv,
            patch.object(repo, "_search_fts5") as mock_fts5,
            patch.object(repo, "_search_like", return_value=expected) as mock_like,
        ):
            result = repo.search(query="canvas")

        mock_tv.assert_not_called()
        mock_fts5.assert_not_called()
        mock_like.assert_called_once()
        assert result is expected

    def test_search_no_query_calls_like(self) -> None:
        """When query is None (browse mode), search() always uses _search_like()."""
        repo = MarketplaceCatalogRepository.__new__(MarketplaceCatalogRepository)
        expected = _make_like_result()

        with (
            patch(
                "skillmeat.api.utils.fts5.get_search_backend",
                return_value=SearchBackendType.TSVECTOR,
            ),
            patch.object(repo, "_search_tsvector") as mock_tv,
            patch.object(repo, "_search_fts5") as mock_fts5,
            patch.object(repo, "_search_like", return_value=expected) as mock_like,
        ):
            result = repo.search(query=None)

        mock_tv.assert_not_called()
        mock_fts5.assert_not_called()
        mock_like.assert_called_once()
        assert result is expected


# ===========================================================================
# 4. Query cleaning tests (_search_tsvector internal behaviour)
# ===========================================================================


@pytest.mark.unit
class TestTsvectorQueryCleaning:
    """_search_tsvector() cleans special characters before building tsquery."""

    def _call_tsvector_with_query(
        self,
        query: str,
        like_result: Optional[PaginatedResult] = None,
    ) -> tuple[MarketplaceCatalogRepository, MagicMock, MagicMock]:
        """Set up repo with mocked _search_like and _get_session.

        Returns (repo, mock_like, session_mock).
        """
        session = _make_session_with_rows([])  # No rows → has_more=False

        repo = MarketplaceCatalogRepository.__new__(MarketplaceCatalogRepository)
        repo._get_session = MagicMock(return_value=session)

        fallback = like_result or _make_like_result()
        mock_like = MagicMock(return_value=fallback)
        repo._search_like = mock_like

        return repo, mock_like, session

    def test_special_chars_stripped_from_query(self) -> None:
        """Special characters are removed before passing query to websearch_to_tsquery."""
        repo, _, session = self._call_tsvector_with_query("test-skill (v2)")
        # Execute _search_tsvector and ensure it doesn't raise (session.execute is mocked)
        result = repo._search_tsvector(query="test-skill (v2)")
        # The query must have been executed (not fallen through to LIKE)
        session.execute.assert_called()

    def test_empty_query_after_cleaning_falls_back_to_like(self) -> None:
        """A query consisting entirely of special chars falls back to _search_like()."""
        repo, mock_like, _ = self._call_tsvector_with_query("---")
        result = repo._search_tsvector(query="---")
        mock_like.assert_called_once()

    def test_operator_only_query_falls_back_to_like(self) -> None:
        """Queries that reduce to bare FTS operators fall back to _search_like()."""
        repo, mock_like, _ = self._call_tsvector_with_query("AND OR NOT")
        result = repo._search_tsvector(query="AND OR NOT")
        mock_like.assert_called_once()

    def test_mixed_special_chars_and_words_execute_tsvector(self) -> None:
        """Mixed query with valid words after stripping should use tsvector SQL."""
        repo, mock_like, session = self._call_tsvector_with_query("canvas-design (v2)")
        repo._search_tsvector(query="canvas-design (v2)")
        # Special chars stripped → "canvas design v2" → valid terms → SQL executed
        session.execute.assert_called()
        mock_like.assert_not_called()

    def test_near_operator_stripped_from_terms(self) -> None:
        """The NEAR operator keyword is stripped like AND/OR/NOT."""
        repo, mock_like, session = self._call_tsvector_with_query("NEAR word")
        repo._search_tsvector(query="NEAR word")
        # "word" survives → SQL executed, no LIKE fallback
        session.execute.assert_called()
        mock_like.assert_not_called()


# ===========================================================================
# 5. Deep match detection tests
# ===========================================================================


@pytest.mark.unit
class TestDeepMatchDetection:
    """deep_match flag reflects whether title/description snippet contains <mark>."""

    def _make_row(
        self,
        entry_id: str = "e1",
        rank: float = -0.5,
        title_snippet: Optional[str] = None,
        desc_snippet: Optional[str] = None,
    ) -> tuple:
        """Return a row tuple (entry, rank, title_snippet, desc_snippet)."""
        entry = _make_entry(entry_id=entry_id)
        return (entry, rank, title_snippet, desc_snippet)

    def _run_tsvector(self, rows: list) -> PaginatedResult:
        """Run _search_tsvector with a mocked session returning *rows*."""
        session = _make_session_with_rows(rows)
        repo = _repo_with_session(session)
        # Prevent real LIKE fallback from firing
        repo._search_like = MagicMock(return_value=_make_like_result())
        return repo._search_tsvector(query="canvas")

    def test_deep_match_false_when_title_snippet_has_mark(self) -> None:
        """deep_match=False when title snippet contains <mark>."""
        rows = [self._make_row(title_snippet="Some <mark>canvas</mark> art")]
        result = self._run_tsvector(rows)
        assert result.snippets["e1"]["deep_match"] is False

    def test_deep_match_false_when_description_snippet_has_mark(self) -> None:
        """deep_match=False when description snippet contains <mark>."""
        rows = [self._make_row(desc_snippet="A <mark>canvas</mark> drawing tool")]
        result = self._run_tsvector(rows)
        assert result.snippets["e1"]["deep_match"] is False

    def test_deep_match_true_when_no_snippet_has_mark(self) -> None:
        """deep_match=True when neither title nor description contains <mark>."""
        rows = [self._make_row(title_snippet="plain title", desc_snippet="plain desc")]
        result = self._run_tsvector(rows)
        assert result.snippets["e1"]["deep_match"] is True

    def test_deep_match_true_when_both_snippets_are_none(self) -> None:
        """deep_match=True when both snippets are None (match in search_vector only)."""
        rows = [self._make_row(title_snippet=None, desc_snippet=None)]
        result = self._run_tsvector(rows)
        assert result.snippets["e1"]["deep_match"] is True

    def test_matched_file_is_none_for_tsvector(self) -> None:
        """matched_file is always None for tsvector path (no per-file index)."""
        rows = [self._make_row(title_snippet="<mark>canvas</mark>")]
        result = self._run_tsvector(rows)
        assert result.snippets["e1"]["matched_file"] is None

    def test_snippets_stored_for_each_entry(self) -> None:
        """Snippet dict is populated for every returned entry."""
        rows = [
            self._make_row("e1", title_snippet="<mark>canvas</mark>"),
            self._make_row("e2", desc_snippet="<mark>design</mark>"),
            self._make_row("e3"),
        ]
        result = self._run_tsvector(rows)
        assert set(result.snippets.keys()) == {"e1", "e2", "e3"}


# ===========================================================================
# 6. Cursor format tests
# ===========================================================================


@pytest.mark.unit
class TestCursorFormat:
    """Cursor produced by _search_tsvector mirrors the FTS5 '{rank}:{score}:{id}' format."""

    def _run_tsvector_rows(self, rows: list, limit: int = 50) -> PaginatedResult:
        session = _make_session_with_rows(rows)
        repo = _repo_with_session(session)
        repo._search_like = MagicMock(return_value=_make_like_result())
        return repo._search_tsvector(query="canvas", limit=limit)

    def _make_overflow_rows(
        self, count: int, base_rank: float = -0.8
    ) -> list:
        """Return *count* rows, each with a distinct ID and confidence."""
        return [
            (_make_entry(f"entry-{i:03d}", confidence_score=90 - i), base_rank - i * 0.01, None, None)
            for i in range(count)
        ]

    def test_cursor_none_when_no_more_results(self) -> None:
        """next_cursor is None when has_more is False."""
        rows = [(_make_entry("e1", 85), -0.5, None, None)]
        result = self._run_tsvector_rows(rows, limit=50)
        assert result.next_cursor is None
        assert result.has_more is False

    def test_cursor_format_matches_fts5_pattern(self) -> None:
        """next_cursor follows '{rank}:{confidence_score}:{id}' format."""
        # Produce limit+1 rows to trigger has_more=True
        rows = self._make_overflow_rows(count=51)
        result = self._run_tsvector_rows(rows, limit=50)

        assert result.has_more is True
        assert result.next_cursor is not None

        parts = result.next_cursor.split(":", 2)
        assert len(parts) == 3, f"Expected 3 cursor parts, got: {result.next_cursor!r}"

        rank_part, score_part, id_part = parts
        # rank is a float (negated ts_rank_cd)
        float(rank_part)  # Should not raise
        # score is an integer
        int(score_part)
        # id is the entry id of the last item in the page
        assert id_part == "entry-049"

    def test_cursor_parsed_correctly_on_second_page(self) -> None:
        """A cursor from the first page is accepted without error on the second call."""
        cursor = "-0.95:70:entry-049"
        session = _make_session_with_rows([])
        repo = _repo_with_session(session)
        repo._search_like = MagicMock(return_value=_make_like_result())
        # Should not raise — cursor parsing is fault-tolerant
        result = repo._search_tsvector(query="canvas", cursor=cursor)
        session.execute.assert_called()

    def test_legacy_cursor_format_accepted(self) -> None:
        """Legacy 2-part cursor 'confidence:id' (from LIKE path) is accepted."""
        cursor = "70:entry-049"
        session = _make_session_with_rows([])
        repo = _repo_with_session(session)
        repo._search_like = MagicMock(return_value=_make_like_result())
        result = repo._search_tsvector(query="canvas", cursor=cursor)
        session.execute.assert_called()

    def test_malformed_cursor_does_not_raise(self) -> None:
        """A completely invalid cursor string is silently ignored."""
        cursor = "not-a-cursor"
        session = _make_session_with_rows([])
        repo = _repo_with_session(session)
        repo._search_like = MagicMock(return_value=_make_like_result())
        result = repo._search_tsvector(query="canvas", cursor=cursor)
        # Should succeed without raising
        session.execute.assert_called()


# ===========================================================================
# 7. Fallback behaviour tests
# ===========================================================================


@pytest.mark.unit
class TestTsvectorFallback:
    """_search_tsvector() falls back to _search_like() on exception."""

    def test_session_execute_exception_triggers_like_fallback(self) -> None:
        """If session.execute() raises, _search_like() is called."""
        session = MagicMock(spec=Session)
        session.execute.side_effect = RuntimeError("PG connection error")

        fallback_result = _make_like_result(items=[_make_entry()])
        repo = _repo_with_session(session)
        mock_like = MagicMock(return_value=fallback_result)
        repo._search_like = mock_like

        result = repo._search_tsvector(query="canvas")

        mock_like.assert_called_once()
        assert result is fallback_result

    def test_fallback_passes_original_query_to_like(self) -> None:
        """On exception, _search_like receives the original (pre-clean) query."""
        session = MagicMock(spec=Session)
        session.execute.side_effect = RuntimeError("error")

        repo = _repo_with_session(session)
        fallback_result = _make_like_result()
        mock_like = MagicMock(return_value=fallback_result)
        repo._search_like = mock_like

        original_query = "canvas design"
        repo._search_tsvector(
            query=original_query,
            artifact_type="skill",
            source_ids=["src-1"],
            min_confidence=50,
            limit=10,
        )

        call_kwargs = mock_like.call_args
        assert call_kwargs.kwargs.get("query") == original_query or (
            len(call_kwargs.args) > 0 and call_kwargs.args[0] == original_query
        )

    def test_fallback_passes_all_filter_params(self) -> None:
        """On exception, _search_like receives all original filter arguments."""
        session = MagicMock(spec=Session)
        session.execute.side_effect = RuntimeError("error")

        repo = _repo_with_session(session)
        mock_like = MagicMock(return_value=_make_like_result())
        repo._search_like = mock_like

        repo._search_tsvector(
            query="skill",
            artifact_type="command",
            source_ids=["src-a", "src-b"],
            min_confidence=75,
            tags=["automation"],
            limit=25,
            cursor="100:some-id",
        )

        mock_like.assert_called_once()
        kwargs = mock_like.call_args.kwargs
        assert kwargs.get("artifact_type") == "command"
        assert kwargs.get("source_ids") == ["src-a", "src-b"]
        assert kwargs.get("min_confidence") == 75
        assert kwargs.get("tags") == ["automation"]
        assert kwargs.get("limit") == 25

    def test_empty_query_fallback_passes_original_query(self) -> None:
        """When query cleans to empty, _search_like receives the raw original query."""
        session = MagicMock(spec=Session)
        repo = _repo_with_session(session)
        mock_like = MagicMock(return_value=_make_like_result())
        repo._search_like = mock_like

        # "---" strips to empty → LIKE fallback before SQL execution
        repo._search_tsvector(query="---")
        mock_like.assert_called_once()
        # Original query passed, not the cleaned empty string
        kwargs = mock_like.call_args.kwargs
        assert kwargs.get("query") == "---"


# ===========================================================================
# 8. Pagination / has_more tests
# ===========================================================================


@pytest.mark.unit
class TestTsvectorPagination:
    """_search_tsvector() returns correct has_more and trims rows to limit."""

    def _make_rows(self, n: int) -> list:
        return [
            (_make_entry(f"e{i}", 90), -0.5, None, None)
            for i in range(n)
        ]

    def test_has_more_false_when_rows_lte_limit(self) -> None:
        rows = self._make_rows(5)
        session = _make_session_with_rows(rows)
        repo = _repo_with_session(session)
        repo._search_like = MagicMock(return_value=_make_like_result())
        result = repo._search_tsvector(query="canvas", limit=10)
        assert result.has_more is False
        assert len(result.items) == 5

    def test_has_more_true_when_rows_gt_limit(self) -> None:
        rows = self._make_rows(11)
        session = _make_session_with_rows(rows)
        repo = _repo_with_session(session)
        repo._search_like = MagicMock(return_value=_make_like_result())
        result = repo._search_tsvector(query="canvas", limit=10)
        assert result.has_more is True
        assert len(result.items) == 10

    def test_empty_result_has_no_cursor(self) -> None:
        session = _make_session_with_rows([])
        repo = _repo_with_session(session)
        repo._search_like = MagicMock(return_value=_make_like_result())
        result = repo._search_tsvector(query="canvas")
        assert result.next_cursor is None
        assert result.has_more is False
        assert result.items == []
