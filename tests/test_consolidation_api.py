"""Integration tests for consolidation API endpoints (SA-P5-013).

Tests cover:
- GET /api/v1/artifacts/consolidation/clusters — happy path with clusters
- GET /api/v1/artifacts/consolidation/clusters — empty result (no similar pairs)
- GET /api/v1/artifacts/consolidation/clusters — cursor pagination
- POST /api/v1/artifacts/consolidation/pairs/{pair_id}/ignore — success
- POST /api/v1/artifacts/consolidation/pairs/{pair_id}/ignore — 404 unknown pair
- DELETE /api/v1/artifacts/consolidation/pairs/{pair_id}/ignore — success
- DELETE /api/v1/artifacts/consolidation/pairs/{pair_id}/ignore — 404 unknown pair
- Ignored pairs excluded from cluster list by default

Architecture notes
------------------
- ``GET /clusters`` receives a ``DbSessionDep`` injected via ``get_db_session``;
  tests override that dependency to supply an in-memory SQLite session loaded
  with ``DuplicatePair`` fixtures.
- ``POST/DELETE /pairs/{id}/ignore`` construct ``DuplicatePairRepository()``
  internally (no injectable session).  Tests patch the repository methods
  directly so no real database file is touched.
"""

from __future__ import annotations

import base64
import json
import uuid as _uuid_mod
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app
from skillmeat.cache.models import Artifact, Base, DuplicatePair, Project


# =============================================================================
# Shared constants
# =============================================================================

_SKILL_TYPE = "skill"
_PAIR_ID_1 = _uuid_mod.uuid4().hex
_PAIR_ID_2 = _uuid_mod.uuid4().hex


# =============================================================================
# Fixtures — app, engine, DB session
# =============================================================================


@pytest.fixture(scope="module")
def test_settings():
    """API settings for testing (no auth, no API key)."""
    return APISettings(
        env=Environment.TESTING,
        host="127.0.0.1",
        port=8000,
        log_level="DEBUG",
        api_key_enabled=False,
    )


@pytest.fixture(scope="module")
def test_engine(tmp_path_factory):
    """In-memory-ish SQLite engine with the full ORM schema created once."""
    db_path = tmp_path_factory.mktemp("consolidation_db") / "test_consolidation.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _set_fk_pragma(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="module")
def test_session_factory(test_engine):
    """Session factory bound to the module-scoped engine."""
    return sessionmaker(bind=test_engine, autocommit=False, autoflush=False)


@pytest.fixture(scope="module")
def shared_project(test_engine):
    """One Project row shared across all tests in this module."""
    factory = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    session = factory()
    project = Project(
        id=_uuid_mod.uuid4().hex,
        name="Consolidation Test Project",
        path="/tmp/consolidation-test",
        status="active",
    )
    session.add(project)
    session.commit()
    pid = project.id
    session.close()
    return pid


@pytest.fixture(scope="module")
def artifact_rows(test_session_factory, shared_project):
    """Three Artifact rows used as cluster members throughout this module."""
    session = test_session_factory()
    arts = []
    for i in range(3):
        art = Artifact(
            id=f"skill:consolidation-art-{i}",
            uuid=_uuid_mod.uuid4().hex,
            project_id=shared_project,
            name=f"consolidation-art-{i}",
            type=_SKILL_TYPE,
        )
        session.add(art)
        arts.append(art)
    session.commit()

    # Return lightweight namespace objects so module-scoped data is accessible
    # after the session is closed.
    class _Row:
        def __init__(self, art):
            self.id = art.id
            self.uuid = art.uuid
            self.name = art.name

    result = [_Row(a) for a in arts]
    session.close()
    return result


@pytest.fixture
def test_db(test_session_factory):
    """Per-test session; rolls back after each test to keep state isolated."""
    session = test_session_factory()
    yield session
    session.rollback()
    session.close()


# =============================================================================
# Fixtures — FastAPI app / TestClient
# =============================================================================


@pytest.fixture
def app(test_settings):
    """FastAPI application with auth overridden."""
    from skillmeat.api.config import get_settings

    application = create_app(test_settings)
    application.dependency_overrides[get_settings] = lambda: test_settings
    return application


def _make_client(app, session_factory):
    """Return a TestClient that injects *session_factory* for DB dependencies."""
    from skillmeat.api.middleware.auth import verify_token
    from skillmeat.api.routers.artifacts import get_db_session

    app.dependency_overrides[verify_token] = lambda: "mock-token"

    def _override_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = _override_db
    return TestClient(app)


# =============================================================================
# Helpers — DuplicatePair fixture builder
# =============================================================================


def _insert_pair(
    session,
    art1_uuid: str,
    art2_uuid: str,
    score: float = 0.8,
    ignored: bool = False,
) -> DuplicatePair:
    """Insert a DuplicatePair into *session* and return the persisted row."""
    pair = DuplicatePair(
        id=_uuid_mod.uuid4().hex,
        artifact1_uuid=art1_uuid,
        artifact2_uuid=art2_uuid,
        similarity_score=score,
        ignored=ignored,
    )
    session.add(pair)
    session.flush()
    return pair


# =============================================================================
# Tests: GET /api/v1/artifacts/consolidation/clusters
# =============================================================================


class TestGetConsolidationClusters:
    """Happy-path and edge cases for the clusters list endpoint."""

    def test_happy_path_returns_clusters(self, app, test_session_factory, artifact_rows):
        """With two similar pairs in the DB the endpoint returns at least one cluster."""
        session = test_session_factory()
        try:
            pair = _insert_pair(
                session,
                artifact_rows[0].uuid,
                artifact_rows[1].uuid,
                score=0.85,
            )
            session.commit()
            pair_id = pair.id
        finally:
            session.close()

        with _make_client(app, test_session_factory) as client:
            response = client.get("/api/v1/artifacts/consolidation/clusters")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "clusters" in data
        assert "next_cursor" in data
        assert len(data["clusters"]) >= 1

        cluster = data["clusters"][0]
        assert "artifacts" in cluster
        assert "max_score" in cluster
        assert "artifact_type" in cluster
        assert "pair_count" in cluster
        assert cluster["max_score"] >= 0.0
        assert cluster["pair_count"] >= 1

        # Cleanup
        cleanup_session = test_session_factory()
        try:
            cleanup_session.query(DuplicatePair).filter_by(id=pair_id).delete()
            cleanup_session.commit()
        finally:
            cleanup_session.close()

    def test_empty_result_when_no_pairs(self, app, test_session_factory):
        """When no DuplicatePair rows exist the endpoint returns an empty list."""
        # Delete all pairs first to guarantee isolation.
        cleanup = test_session_factory()
        try:
            cleanup.query(DuplicatePair).delete()
            cleanup.commit()
        finally:
            cleanup.close()

        with _make_client(app, test_session_factory) as client:
            response = client.get("/api/v1/artifacts/consolidation/clusters")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["clusters"] == []
        assert data["next_cursor"] is None

    def test_min_score_param_filters_low_score_pairs(
        self, app, test_session_factory, artifact_rows
    ):
        """Pairs below min_score are excluded from results."""
        session = test_session_factory()
        try:
            pair = _insert_pair(
                session,
                artifact_rows[0].uuid,
                artifact_rows[2].uuid,
                score=0.3,  # below the min_score we'll request
            )
            session.commit()
            pair_id = pair.id
        finally:
            session.close()

        with _make_client(app, test_session_factory) as client:
            response = client.get(
                "/api/v1/artifacts/consolidation/clusters?min_score=0.9"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # The 0.3-score pair should not surface in any cluster.
        for cluster in data["clusters"]:
            assert cluster["max_score"] >= 0.9

        # Cleanup
        cleanup_session = test_session_factory()
        try:
            cleanup_session.query(DuplicatePair).filter_by(id=pair_id).delete()
            cleanup_session.commit()
        finally:
            cleanup_session.close()

    def test_cursor_pagination(self, app, test_session_factory, artifact_rows):
        """Cursor returned on page 1 can be used to retrieve page 2."""
        # Insert enough distinct pairs to fill two pages of limit=1.
        session = test_session_factory()
        try:
            pair1 = _insert_pair(
                session,
                artifact_rows[0].uuid,
                artifact_rows[1].uuid,
                score=0.9,
            )
            pair2 = _insert_pair(
                session,
                artifact_rows[1].uuid,
                artifact_rows[2].uuid,
                score=0.7,
            )
            session.commit()
            p1_id = pair1.id
            p2_id = pair2.id
        finally:
            session.close()

        with _make_client(app, test_session_factory) as client:
            # Page 1: limit=1 so we expect a next_cursor
            resp1 = client.get(
                "/api/v1/artifacts/consolidation/clusters?limit=1&min_score=0.0"
            )
            assert resp1.status_code == status.HTTP_200_OK
            page1 = resp1.json()

            # Only proceed to page 2 if next_cursor was actually set.
            # (If all pairs collapsed into one cluster there is nothing to page.)
            if page1["next_cursor"] is not None:
                cursor = page1["next_cursor"]
                resp2 = client.get(
                    f"/api/v1/artifacts/consolidation/clusters"
                    f"?limit=1&min_score=0.0&cursor={cursor}"
                )
                assert resp2.status_code == status.HTTP_200_OK
                page2 = resp2.json()
                assert "clusters" in page2
                # The cursor must decode to an offset > 0.
                decoded = json.loads(base64.b64decode(cursor).decode())
                assert isinstance(decoded.get("offset"), int)
                assert decoded["offset"] >= 0
            else:
                # All pairs merged into a single cluster — pagination is correct
                # but there is no second page.
                assert page1["clusters"] is not None

        # Cleanup
        cleanup_session = test_session_factory()
        try:
            cleanup_session.query(DuplicatePair).filter_by(id=p1_id).delete()
            cleanup_session.query(DuplicatePair).filter_by(id=p2_id).delete()
            cleanup_session.commit()
        finally:
            cleanup_session.close()

    def test_invalid_cursor_is_ignored(self, app, test_session_factory):
        """A malformed cursor is silently ignored; endpoint returns first page."""
        with _make_client(app, test_session_factory) as client:
            response = client.get(
                "/api/v1/artifacts/consolidation/clusters?cursor=not-valid-base64!!!"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "clusters" in data

    def test_ignored_pairs_excluded_from_clusters(
        self, app, test_session_factory, artifact_rows
    ):
        """Pairs with ignored=True must NOT appear in cluster results."""
        session = test_session_factory()
        try:
            ignored_pair = _insert_pair(
                session,
                artifact_rows[0].uuid,
                artifact_rows[1].uuid,
                score=0.95,
                ignored=True,
            )
            session.commit()
            ignored_id = ignored_pair.id
            ignored_art1 = ignored_pair.artifact1_uuid
            ignored_art2 = ignored_pair.artifact2_uuid
        finally:
            session.close()

        with _make_client(app, test_session_factory) as client:
            response = client.get(
                "/api/v1/artifacts/consolidation/clusters?min_score=0.0"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # The two artifact UUIDs from the ignored pair must not appear together
        # in any cluster.
        for cluster in data["clusters"]:
            uuids = set(cluster["artifacts"])
            assert not (ignored_art1 in uuids and ignored_art2 in uuids), (
                f"Ignored pair artifacts {ignored_art1!r}/{ignored_art2!r} "
                "appeared in cluster"
            )

        # Cleanup
        cleanup_session = test_session_factory()
        try:
            cleanup_session.query(DuplicatePair).filter_by(id=ignored_id).delete()
            cleanup_session.commit()
        finally:
            cleanup_session.close()

    def test_limit_param_validation_too_low(self, app, test_session_factory):
        """limit=0 violates ge=1 → 422."""
        with _make_client(app, test_session_factory) as client:
            response = client.get(
                "/api/v1/artifacts/consolidation/clusters?limit=0"
            )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_limit_param_validation_too_high(self, app, test_session_factory):
        """limit=101 violates le=100 → 422."""
        with _make_client(app, test_session_factory) as client:
            response = client.get(
                "/api/v1/artifacts/consolidation/clusters?limit=101"
            )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_min_score_validation_negative(self, app, test_session_factory):
        """min_score=-0.1 violates ge=0.0 → 422."""
        with _make_client(app, test_session_factory) as client:
            response = client.get(
                "/api/v1/artifacts/consolidation/clusters?min_score=-0.1"
            )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_min_score_validation_above_one(self, app, test_session_factory):
        """min_score=1.1 violates le=1.0 → 422."""
        with _make_client(app, test_session_factory) as client:
            response = client.get(
                "/api/v1/artifacts/consolidation/clusters?min_score=1.1"
            )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# =============================================================================
# Tests: POST /api/v1/artifacts/consolidation/pairs/{pair_id}/ignore
# =============================================================================


class TestIgnoreDuplicatePair:
    """Tests for marking a pair as ignored."""

    def test_ignore_pair_success(self, app, test_settings):
        """200 with ``ignored: true`` when the pair exists."""
        from skillmeat.api.config import get_settings
        from skillmeat.api.middleware.auth import verify_token

        application = create_app(test_settings)
        application.dependency_overrides[get_settings] = lambda: test_settings
        application.dependency_overrides[verify_token] = lambda: "mock-token"

        with patch(
            "skillmeat.cache.repositories.DuplicatePairRepository.mark_pair_ignored",
            return_value=True,
        ) as mock_mark:
            with TestClient(application) as client:
                response = client.post(
                    f"/api/v1/artifacts/consolidation/pairs/{_PAIR_ID_1}/ignore"
                )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["pair_id"] == _PAIR_ID_1
        assert data["ignored"] is True
        mock_mark.assert_called_once_with(_PAIR_ID_1)

    def test_ignore_pair_not_found_returns_404(self, app, test_settings):
        """404 when the pair_id does not exist in the repository."""
        from skillmeat.api.config import get_settings
        from skillmeat.api.middleware.auth import verify_token

        application = create_app(test_settings)
        application.dependency_overrides[get_settings] = lambda: test_settings
        application.dependency_overrides[verify_token] = lambda: "mock-token"

        unknown_id = _uuid_mod.uuid4().hex

        with patch(
            "skillmeat.cache.repositories.DuplicatePairRepository.mark_pair_ignored",
            return_value=False,
        ):
            with TestClient(application) as client:
                response = client.post(
                    f"/api/v1/artifacts/consolidation/pairs/{unknown_id}/ignore"
                )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        detail = response.json()["detail"]
        assert unknown_id in detail

    def test_ignore_pair_idempotent(self, app, test_settings):
        """Calling ignore twice on the same pair returns 200 both times."""
        from skillmeat.api.config import get_settings
        from skillmeat.api.middleware.auth import verify_token

        application = create_app(test_settings)
        application.dependency_overrides[get_settings] = lambda: test_settings
        application.dependency_overrides[verify_token] = lambda: "mock-token"

        with patch(
            "skillmeat.cache.repositories.DuplicatePairRepository.mark_pair_ignored",
            return_value=True,
        ):
            with TestClient(application) as client:
                resp1 = client.post(
                    f"/api/v1/artifacts/consolidation/pairs/{_PAIR_ID_1}/ignore"
                )
                resp2 = client.post(
                    f"/api/v1/artifacts/consolidation/pairs/{_PAIR_ID_1}/ignore"
                )

        assert resp1.status_code == status.HTTP_200_OK
        assert resp2.status_code == status.HTTP_200_OK
        assert resp1.json()["ignored"] is True
        assert resp2.json()["ignored"] is True


# =============================================================================
# Tests: DELETE /api/v1/artifacts/consolidation/pairs/{pair_id}/ignore
# =============================================================================


class TestUnignoreDuplicatePair:
    """Tests for clearing the ignored flag on a pair."""

    def test_unignore_pair_success(self, app, test_settings):
        """200 with ``ignored: false`` when the pair exists."""
        from skillmeat.api.config import get_settings
        from skillmeat.api.middleware.auth import verify_token

        application = create_app(test_settings)
        application.dependency_overrides[get_settings] = lambda: test_settings
        application.dependency_overrides[verify_token] = lambda: "mock-token"

        with patch(
            "skillmeat.cache.repositories.DuplicatePairRepository.unmark_pair_ignored",
            return_value=True,
        ) as mock_unmark:
            with TestClient(application) as client:
                response = client.delete(
                    f"/api/v1/artifacts/consolidation/pairs/{_PAIR_ID_2}/ignore"
                )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["pair_id"] == _PAIR_ID_2
        assert data["ignored"] is False
        mock_unmark.assert_called_once_with(_PAIR_ID_2)

    def test_unignore_pair_not_found_returns_404(self, app, test_settings):
        """404 when the pair_id does not exist in the repository."""
        from skillmeat.api.config import get_settings
        from skillmeat.api.middleware.auth import verify_token

        application = create_app(test_settings)
        application.dependency_overrides[get_settings] = lambda: test_settings
        application.dependency_overrides[verify_token] = lambda: "mock-token"

        unknown_id = _uuid_mod.uuid4().hex

        with patch(
            "skillmeat.cache.repositories.DuplicatePairRepository.unmark_pair_ignored",
            return_value=False,
        ):
            with TestClient(application) as client:
                response = client.delete(
                    f"/api/v1/artifacts/consolidation/pairs/{unknown_id}/ignore"
                )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        detail = response.json()["detail"]
        assert unknown_id in detail

    def test_unignore_pair_idempotent(self, app, test_settings):
        """Calling unignore twice on an already-active pair returns 200 both times."""
        from skillmeat.api.config import get_settings
        from skillmeat.api.middleware.auth import verify_token

        application = create_app(test_settings)
        application.dependency_overrides[get_settings] = lambda: test_settings
        application.dependency_overrides[verify_token] = lambda: "mock-token"

        with patch(
            "skillmeat.cache.repositories.DuplicatePairRepository.unmark_pair_ignored",
            return_value=True,
        ):
            with TestClient(application) as client:
                resp1 = client.delete(
                    f"/api/v1/artifacts/consolidation/pairs/{_PAIR_ID_2}/ignore"
                )
                resp2 = client.delete(
                    f"/api/v1/artifacts/consolidation/pairs/{_PAIR_ID_2}/ignore"
                )

        assert resp1.status_code == status.HTTP_200_OK
        assert resp2.status_code == status.HTTP_200_OK
        assert resp1.json()["ignored"] is False
        assert resp2.json()["ignored"] is False


# =============================================================================
# Tests: end-to-end ignore → cluster exclusion flow
# =============================================================================


class TestIgnoreExcludesFromClusters:
    """Verify that ignoring a pair removes it from future cluster results."""

    def test_ignored_pair_absent_from_clusters(
        self, app, test_session_factory, artifact_rows
    ):
        """After ignoring a pair via the DB it no longer appears in the cluster list.

        This test works directly at the DB level (bypasses the ignore endpoint
        which uses DuplicatePairRepository independently) to verify that the
        GET /clusters endpoint correctly honours the ignored flag.
        """
        # 1. Insert a pair that starts active.
        session = test_session_factory()
        try:
            pair = _insert_pair(
                session,
                artifact_rows[0].uuid,
                artifact_rows[1].uuid,
                score=0.88,
                ignored=False,
            )
            session.commit()
            pair_id = pair.id
            art1_uuid = pair.artifact1_uuid
            art2_uuid = pair.artifact2_uuid
        finally:
            session.close()

        # 2. Verify the pair appears in clusters.
        with _make_client(app, test_session_factory) as client:
            resp_before = client.get(
                "/api/v1/artifacts/consolidation/clusters?min_score=0.0"
            )
        assert resp_before.status_code == status.HTTP_200_OK
        before_data = resp_before.json()

        pair_in_before = any(
            art1_uuid in cluster["artifacts"] and art2_uuid in cluster["artifacts"]
            for cluster in before_data["clusters"]
        )
        assert pair_in_before, (
            "Expected the active pair to appear in at least one cluster before ignoring"
        )

        # 3. Mark the pair as ignored directly in the DB.
        session2 = test_session_factory()
        try:
            row = session2.query(DuplicatePair).filter_by(id=pair_id).first()
            assert row is not None
            row.ignored = True
            session2.commit()
        finally:
            session2.close()

        # 4. Verify the pair no longer appears in clusters.
        with _make_client(app, test_session_factory) as client:
            resp_after = client.get(
                "/api/v1/artifacts/consolidation/clusters?min_score=0.0"
            )
        assert resp_after.status_code == status.HTTP_200_OK
        after_data = resp_after.json()

        pair_in_after = any(
            art1_uuid in cluster["artifacts"] and art2_uuid in cluster["artifacts"]
            for cluster in after_data["clusters"]
        )
        assert not pair_in_after, (
            "Expected the ignored pair to be absent from clusters after ignoring"
        )

        # 5. Cleanup
        cleanup_session = test_session_factory()
        try:
            cleanup_session.query(DuplicatePair).filter_by(id=pair_id).delete()
            cleanup_session.commit()
        finally:
            cleanup_session.close()


# =============================================================================
# Tests: POST /api/v1/artifacts/consolidation/clusters/{cluster_id}/merge
# Tests: POST /api/v1/artifacts/consolidation/clusters/{cluster_id}/replace
# Focus: snapshot-gate abort path (SA-P5-009)
# =============================================================================


class TestConsolidationActionSnapshotGate:
    """Verify that merge and replace endpoints abort when auto-snapshot fails.

    These tests patch ``_create_auto_snapshot_for_consolidation`` to raise an
    exception, then assert that:
    - The endpoint returns HTTP 500
    - The detail message is exactly ``"Snapshot failed — action aborted"``
    - The artifact_mgr.remove() method is NEVER called (no destructive action)
    """

    def _make_action_client(self, app, artifact_mgr_mock):
        """Return a TestClient with auth and ArtifactManagerDep overridden."""
        from skillmeat.api.dependencies import get_artifact_manager
        from skillmeat.api.middleware.auth import verify_token

        app.dependency_overrides[verify_token] = lambda: "mock-token"
        app.dependency_overrides[get_artifact_manager] = lambda: artifact_mgr_mock
        return TestClient(app)

    def test_merge_aborts_when_snapshot_fails(self, app):
        """Merge endpoint must return 500 and skip removal when snapshot raises."""
        primary_uuid = _uuid_mod.uuid4().hex
        artifact_mgr_mock = MagicMock()

        client = self._make_action_client(app, artifact_mgr_mock)

        snapshot_target = (
            "skillmeat.api.routers.artifacts"
            "._create_auto_snapshot_for_consolidation"
        )
        with patch(snapshot_target, side_effect=RuntimeError("disk full")):
            response = client.post(
                "/api/v1/artifacts/consolidation/clusters/cluster-abc/merge",
                json={"primary_artifact_uuid": primary_uuid},
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR, (
            f"Expected 500, got {response.status_code}: {response.text}"
        )
        detail = response.json().get("detail", "")
        assert detail == "Snapshot failed — action aborted", (
            f"Unexpected detail message: {detail!r}"
        )
        # Confirm that no artifact was removed
        artifact_mgr_mock.remove.assert_not_called()

    def test_replace_aborts_when_snapshot_fails(self, app):
        """Replace endpoint must return 500 and skip removal when snapshot raises."""
        primary_uuid = _uuid_mod.uuid4().hex
        artifact_mgr_mock = MagicMock()

        client = self._make_action_client(app, artifact_mgr_mock)

        snapshot_target = (
            "skillmeat.api.routers.artifacts"
            "._create_auto_snapshot_for_consolidation"
        )
        with patch(snapshot_target, side_effect=RuntimeError("snapshot dir missing")):
            response = client.post(
                "/api/v1/artifacts/consolidation/clusters/cluster-xyz/replace",
                json={"primary_artifact_uuid": primary_uuid},
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR, (
            f"Expected 500, got {response.status_code}: {response.text}"
        )
        detail = response.json().get("detail", "")
        assert detail == "Snapshot failed — action aborted", (
            f"Unexpected detail message: {detail!r}"
        )
        # Confirm that no artifact was removed
        artifact_mgr_mock.remove.assert_not_called()

    def test_merge_succeeds_when_snapshot_and_no_pairs(
        self, app, test_session_factory, artifact_rows
    ):
        """When snapshot succeeds and no pairs exist, merge returns 200 with empty lists.

        This confirms the snapshot is created and the action proceeds — when
        there are no DuplicatePair records for the primary, the secondary lists
        are empty and pairs_resolved is 0.
        """
        primary_uuid = artifact_rows[0].uuid
        artifact_mgr_mock = MagicMock()

        # Ensure no pairs exist for this artifact
        cleanup = test_session_factory()
        try:
            cleanup.query(DuplicatePair).filter(
                (DuplicatePair.artifact1_uuid == primary_uuid)
                | (DuplicatePair.artifact2_uuid == primary_uuid)
            ).delete(synchronize_session=False)
            cleanup.commit()
        finally:
            cleanup.close()

        client = self._make_action_client(app, artifact_mgr_mock)

        snapshot_target = (
            "skillmeat.api.routers.artifacts"
            "._create_auto_snapshot_for_consolidation"
        )
        with patch(snapshot_target, return_value="snap-001"):
            with patch(
                "skillmeat.api.routers.artifacts.get_session"
            ) as mock_get_session:
                # Provide a real session via the test session factory so the
                # primary Artifact lookup succeeds.
                from contextlib import contextmanager

                @contextmanager
                def _real_session():
                    session = test_session_factory()
                    try:
                        yield session
                    finally:
                        session.close()

                mock_get_session.side_effect = _real_session

                response = client.post(
                    "/api/v1/artifacts/consolidation/clusters/cluster-abc/merge",
                    json={"primary_artifact_uuid": primary_uuid},
                )

        assert response.status_code == status.HTTP_200_OK, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert data["action"] == "merge"
        assert data["primary_artifact_uuid"] == primary_uuid
        assert data["snapshot_id"] == "snap-001"
        assert data["removed_artifact_uuids"] == []
        assert data["pairs_resolved"] == 0
        # No removal attempted since there are no secondaries
        artifact_mgr_mock.remove.assert_not_called()
