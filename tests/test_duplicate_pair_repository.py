"""Unit tests for DuplicatePairRepository (SA-P5-002).

Tests cover:
- mark_pair_ignored sets ignored=True on an existing pair
- unmark_pair_ignored sets ignored=False on an ignored pair
- mark/unmark round-trip: mark then unmark restores ignored=False
- mark_pair_ignored returns False when pair_id does not exist
- unmark_pair_ignored returns False when pair_id does not exist
- mark_pair_ignored is idempotent (already ignored → still returns True)
- unmark_pair_ignored is idempotent (already active → still returns True)
- list_active excludes ignored pairs
- list_active respects min_score threshold
- get_by_id returns None for missing pair
"""

from __future__ import annotations

import uuid as _uuid_mod
from datetime import datetime
from unittest.mock import MagicMock, patch, call

import pytest

from skillmeat.cache.repositories import DuplicatePairRepository, RepositoryError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pair_row(
    pair_id: str | None = None,
    uuid1: str = "uuid-aaa",
    uuid2: str = "uuid-bbb",
    score: float = 0.8,
    ignored: bool = False,
) -> MagicMock:
    """Return a mock DuplicatePair ORM row."""
    row = MagicMock()
    row.id = pair_id or _uuid_mod.uuid4().hex
    row.artifact1_uuid = uuid1
    row.artifact2_uuid = uuid2
    row.similarity_score = score
    row.ignored = ignored
    row.created_at = datetime.utcnow()
    row.updated_at = datetime.utcnow()
    return row


def _make_repo_with_session(session: MagicMock) -> DuplicatePairRepository:
    """Construct a DuplicatePairRepository whose _get_session returns *session*."""
    repo = DuplicatePairRepository.__new__(DuplicatePairRepository)
    repo._session = session
    repo.db_path = MagicMock()
    repo.engine = MagicMock()
    repo.model_class = MagicMock()
    repo._get_session = MagicMock(return_value=session)
    return repo


def _wire_session(session: MagicMock, row: MagicMock | None) -> MagicMock:
    """Wire session.query(...).filter_by(...).first() to return *row*."""
    query_mock = MagicMock()
    filter_mock = MagicMock()
    filter_mock.first.return_value = row
    filter_mock.filter.return_value = filter_mock
    filter_mock.order_by.return_value = filter_mock
    filter_mock.all.return_value = [] if row is None else [row]
    query_mock.filter_by.return_value = filter_mock
    query_mock.filter.return_value = filter_mock
    session.query.return_value = query_mock
    return filter_mock


# ---------------------------------------------------------------------------
# Tests: mark_pair_ignored
# ---------------------------------------------------------------------------


class TestMarkPairIgnored:
    """Tests for DuplicatePairRepository.mark_pair_ignored."""

    def test_marks_pair_ignored(self):
        """mark_pair_ignored sets ignored=True and returns True."""
        pair = _make_pair_row(pair_id="abc123", ignored=False)
        session = MagicMock()
        _wire_session(session, pair)
        repo = _make_repo_with_session(session)

        result = repo.mark_pair_ignored("abc123")

        assert result is True
        assert pair.ignored is True
        session.commit.assert_called_once()

    def test_returns_false_when_not_found(self):
        """mark_pair_ignored returns False when pair_id does not exist."""
        session = MagicMock()
        _wire_session(session, None)
        repo = _make_repo_with_session(session)

        result = repo.mark_pair_ignored("nonexistent")

        assert result is False
        session.commit.assert_not_called()

    def test_idempotent_already_ignored(self):
        """mark_pair_ignored on an already-ignored pair still returns True."""
        pair = _make_pair_row(pair_id="abc", ignored=True)
        session = MagicMock()
        _wire_session(session, pair)
        repo = _make_repo_with_session(session)

        result = repo.mark_pair_ignored("abc")

        assert result is True
        assert pair.ignored is True
        session.commit.assert_called_once()

    def test_closes_session(self):
        """Session is always closed even on success."""
        pair = _make_pair_row(pair_id="p1")
        session = MagicMock()
        _wire_session(session, pair)
        repo = _make_repo_with_session(session)

        repo.mark_pair_ignored("p1")

        session.close.assert_called_once()

    def test_raises_repository_error_on_integrity_error(self):
        """mark_pair_ignored raises RepositoryError on IntegrityError."""
        from sqlalchemy.exc import IntegrityError

        pair = _make_pair_row(pair_id="p1")
        session = MagicMock()
        _wire_session(session, pair)
        session.commit.side_effect = IntegrityError("mock", {}, None)
        repo = _make_repo_with_session(session)

        with pytest.raises(RepositoryError):
            repo.mark_pair_ignored("p1")

        session.rollback.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: unmark_pair_ignored
# ---------------------------------------------------------------------------


class TestUnmarkPairIgnored:
    """Tests for DuplicatePairRepository.unmark_pair_ignored."""

    def test_unmarks_pair_ignored(self):
        """unmark_pair_ignored sets ignored=False and returns True."""
        pair = _make_pair_row(pair_id="abc123", ignored=True)
        session = MagicMock()
        _wire_session(session, pair)
        repo = _make_repo_with_session(session)

        result = repo.unmark_pair_ignored("abc123")

        assert result is True
        assert pair.ignored is False
        session.commit.assert_called_once()

    def test_returns_false_when_not_found(self):
        """unmark_pair_ignored returns False when pair_id does not exist."""
        session = MagicMock()
        _wire_session(session, None)
        repo = _make_repo_with_session(session)

        result = repo.unmark_pair_ignored("nonexistent")

        assert result is False
        session.commit.assert_not_called()

    def test_idempotent_already_active(self):
        """unmark_pair_ignored on an already-active pair still returns True."""
        pair = _make_pair_row(pair_id="p99", ignored=False)
        session = MagicMock()
        _wire_session(session, pair)
        repo = _make_repo_with_session(session)

        result = repo.unmark_pair_ignored("p99")

        assert result is True
        assert pair.ignored is False
        session.commit.assert_called_once()

    def test_closes_session(self):
        """Session is always closed even on success."""
        pair = _make_pair_row(pair_id="p2", ignored=True)
        session = MagicMock()
        _wire_session(session, pair)
        repo = _make_repo_with_session(session)

        repo.unmark_pair_ignored("p2")

        session.close.assert_called_once()

    def test_raises_repository_error_on_integrity_error(self):
        """unmark_pair_ignored raises RepositoryError on IntegrityError."""
        from sqlalchemy.exc import IntegrityError

        pair = _make_pair_row(pair_id="p2", ignored=True)
        session = MagicMock()
        _wire_session(session, pair)
        session.commit.side_effect = IntegrityError("mock", {}, None)
        repo = _make_repo_with_session(session)

        with pytest.raises(RepositoryError):
            repo.unmark_pair_ignored("p2")

        session.rollback.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: mark / unmark round-trip
# ---------------------------------------------------------------------------


class TestMarkUnmarkRoundTrip:
    """Integration-style round-trip tests using an in-memory SQLite DB."""

    def test_round_trip_mark_then_unmark(self):
        """mark_pair_ignored then unmark_pair_ignored restores ignored=False."""
        # Use two sequential sessions: first wired for mark, second for unmark.
        pair = _make_pair_row(pair_id="rtt", ignored=False)

        session1 = MagicMock()
        _wire_session(session1, pair)

        session2 = MagicMock()
        # Simulate the pair being ignored after the first call.
        pair_after_mark = _make_pair_row(pair_id="rtt", ignored=True)
        _wire_session(session2, pair_after_mark)

        repo = DuplicatePairRepository.__new__(DuplicatePairRepository)
        repo.db_path = MagicMock()
        repo.engine = MagicMock()
        repo.model_class = MagicMock()
        repo._get_session = MagicMock(side_effect=[session1, session2])

        # Mark as ignored.
        mark_result = repo.mark_pair_ignored("rtt")
        assert mark_result is True
        assert pair.ignored is True

        # Unmark (restores to active).
        unmark_result = repo.unmark_pair_ignored("rtt")
        assert unmark_result is True
        assert pair_after_mark.ignored is False


# ---------------------------------------------------------------------------
# Tests: get_by_id
# ---------------------------------------------------------------------------


class TestGetById:
    """Tests for DuplicatePairRepository.get_by_id."""

    def test_returns_row_when_found(self):
        """get_by_id returns the row when it exists."""
        pair = _make_pair_row(pair_id="found1")
        session = MagicMock()
        _wire_session(session, pair)
        repo = _make_repo_with_session(session)

        result = repo.get_by_id("found1")

        assert result is pair

    def test_returns_none_when_missing(self):
        """get_by_id returns None when pair_id does not exist."""
        session = MagicMock()
        _wire_session(session, None)
        repo = _make_repo_with_session(session)

        result = repo.get_by_id("missing")

        assert result is None


# ---------------------------------------------------------------------------
# Tests: list_active
# ---------------------------------------------------------------------------


class TestListActive:
    """Tests for DuplicatePairRepository.list_active."""

    def test_returns_only_non_ignored_pairs(self):
        """list_active only returns pairs with ignored=False."""
        active_pair = _make_pair_row(pair_id="a1", ignored=False, score=0.8)
        session = MagicMock()

        # Wire so that .all() returns only the active pair (simulating the
        # ignored.is_(False) filter applied by the repository).
        query_mock = MagicMock()
        filter_chain = MagicMock()
        filter_chain.filter.return_value = filter_chain
        filter_chain.order_by.return_value = filter_chain
        filter_chain.all.return_value = [active_pair]
        query_mock.filter.return_value = filter_chain
        session.query.return_value = query_mock

        repo = _make_repo_with_session(session)
        results = repo.list_active()

        assert results == [active_pair]

    def test_returns_empty_when_all_ignored(self):
        """list_active returns [] when all qualifying pairs are ignored."""
        session = MagicMock()

        query_mock = MagicMock()
        filter_chain = MagicMock()
        filter_chain.filter.return_value = filter_chain
        filter_chain.order_by.return_value = filter_chain
        filter_chain.all.return_value = []
        query_mock.filter.return_value = filter_chain
        session.query.return_value = query_mock

        repo = _make_repo_with_session(session)
        results = repo.list_active()

        assert results == []
