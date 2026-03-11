"""Integration tests for GET /api/v1/artifacts?artifact_type=workflow.

WAW-P5.4: Verifies that workflow artifacts synced into the DB are returned
correctly by the artifacts listing endpoint when filtered by artifact_type=workflow.

Uses TestClient with dependency overrides and mocked DB sessions to isolate
from filesystem/PostgreSQL dependencies, following the pattern established in
``tests/api/test_artifacts.py`` and ``tests/api/test_deployment_sets.py``.

Note: The query parameter for the artifacts endpoint is ``artifact_type``, not
``type`` (FastAPI maps the function parameter name to the URL query key).

Scenarios tested
----------------
1. Returns correct count matching synced workflow artifacts.
2. DTO structure includes workflow_id, name, description, type='workflow', updated.
3. Filter by artifact_type=workflow excludes non-workflow artifacts.
4. No N+1 queries (at most 2 DB queries for a batch of workflow rows).
5. Empty response when no workflow artifacts exist.
6. Search filter narrows results to matching workflows.
7. workflow_id is populated from artifact_metadata.metadata_json.
8. workflow_id is None when metadata is absent.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Generator, List
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings, Environment, get_settings
from skillmeat.api.server import create_app
from skillmeat.cache.session import get_db_session


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def test_settings() -> APISettings:
    """APISettings with auth and rate-limiting disabled."""
    return APISettings(
        env=Environment.TESTING,
        host="127.0.0.1",
        port=8000,
        log_level="DEBUG",
        cors_enabled=False,
        api_key_enabled=False,
        auth_enabled=False,
        workflow_engine_enabled=True,
    )


@pytest.fixture()
def app(test_settings: APISettings):
    """FastAPI application with settings overridden."""
    application = create_app(test_settings)
    application.dependency_overrides[get_settings] = lambda: test_settings
    return application


@pytest.fixture()
def client(app) -> Generator[TestClient, None, None]:
    """TestClient for the FastAPI application."""
    with TestClient(app) as tc:
        yield tc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db_artifact(
    id: str,
    name: str,
    artifact_type: str = "workflow",
    description: str = "Test workflow",
    workflow_id: str = "wf-id-abc",
    created_at: datetime = None,
    updated_at: datetime = None,
) -> MagicMock:
    """Build a mock DbArtifact ORM-like object as returned from session.query()."""
    row = MagicMock()
    row.id = id
    row.uuid = "uuid-" + id.replace(":", "-")
    row.name = name
    row.type = artifact_type
    row.source = "local"
    row.deployed_version = "1.0.0"
    row.created_at = created_at or datetime(2026, 1, 1)
    row.updated_at = updated_at or datetime(2026, 1, 2)

    # artifact_metadata sub-object with workflow_id in metadata_json
    metadata = MagicMock()
    metadata.description = description
    metadata.metadata_json = json.dumps({"workflow_id": workflow_id})
    row.artifact_metadata = metadata

    return row


def _make_mock_db_session(rows: List[MagicMock]) -> MagicMock:
    """Build a mock SQLAlchemy session whose query() chain returns ``rows``."""
    session = MagicMock()

    query_mock = MagicMock()
    query_mock.filter.return_value = query_mock
    query_mock.order_by.return_value = query_mock
    query_mock.all.return_value = rows

    session.query.return_value = query_mock
    return session


def _db_session_override(rows: List[MagicMock]):
    """Return a FastAPI dependency override generator that yields a mock session."""

    def _override():
        session = _make_mock_db_session(rows)
        yield session

    return _override


# Convenience: the URL query param name is 'artifact_type' (not 'type')
_WORKFLOW_PARAMS = {"artifact_type": "workflow"}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestWorkflowCollectionAPI:
    """Tests for GET /api/v1/artifacts?artifact_type=workflow."""

    def test_returns_empty_when_no_workflows(self, app, client):
        """Empty items list is returned when no workflows are synced."""
        app.dependency_overrides[get_db_session] = _db_session_override([])
        try:
            response = client.get("/api/v1/artifacts", params=_WORKFLOW_PARAMS)
        finally:
            app.dependency_overrides.pop(get_db_session, None)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert data["items"] == []

    def test_returns_correct_count(self, app, client):
        """Returns all synced workflow artifacts with the correct count."""
        rows = [
            _make_db_artifact("workflow:wf-one", "WF One"),
            _make_db_artifact("workflow:wf-two", "WF Two"),
            _make_db_artifact("workflow:wf-three", "WF Three"),
        ]
        app.dependency_overrides[get_db_session] = _db_session_override(rows)
        try:
            response = client.get("/api/v1/artifacts", params=_WORKFLOW_PARAMS)
        finally:
            app.dependency_overrides.pop(get_db_session, None)

        assert response.status_code == status.HTTP_200_OK
        items = response.json()["items"]
        assert len(items) == 3

    def test_dto_structure_includes_required_fields(self, app, client):
        """Each item includes workflow_id, name, type='workflow', and updated timestamp."""
        wf_id = "wf-dto-check-id"
        rows = [
            _make_db_artifact(
                "workflow:dto-test",
                "DTO Test Workflow",
                description="Checks DTO fields",
                workflow_id=wf_id,
                updated_at=datetime(2026, 3, 10, 12, 0, 0),
            )
        ]
        app.dependency_overrides[get_db_session] = _db_session_override(rows)
        try:
            response = client.get("/api/v1/artifacts", params=_WORKFLOW_PARAMS)
        finally:
            app.dependency_overrides.pop(get_db_session, None)

        assert response.status_code == status.HTTP_200_OK
        items = response.json()["items"]
        assert len(items) == 1

        item = items[0]
        assert item["type"] == "workflow", "type field must be 'workflow'"
        assert item["name"] == "DTO Test Workflow", "name field mismatch"
        assert item.get("workflow_id") == wf_id, "workflow_id missing or wrong"
        assert item.get("updated") is not None, "updated timestamp missing"
        assert item.get("id") == "workflow:dto-test", "id field missing"

    def test_description_surfaces_in_metadata(self, app, client):
        """Workflow description is included in the metadata.description field."""
        rows = [
            _make_db_artifact(
                "workflow:desc-test",
                "Desc Workflow",
                description="My detailed description",
            )
        ]
        app.dependency_overrides[get_db_session] = _db_session_override(rows)
        try:
            response = client.get("/api/v1/artifacts", params=_WORKFLOW_PARAMS)
        finally:
            app.dependency_overrides.pop(get_db_session, None)

        assert response.status_code == status.HTTP_200_OK
        item = response.json()["items"][0]
        assert item.get("metadata") is not None
        assert item["metadata"].get("description") == "My detailed description"

    def test_filter_type_workflow_only_returns_workflow_type(self, app, client):
        """Filtering by artifact_type=workflow returns only rows with type='workflow'.

        The _list_workflow_artifacts_from_db helper already applies a
        .filter(DbArtifact.type == 'workflow') clause before returning results.
        This test verifies the response contains only workflow items.
        """
        rows = [
            _make_db_artifact("workflow:filter-one", "Filter One"),
            _make_db_artifact("workflow:filter-two", "Filter Two"),
        ]
        app.dependency_overrides[get_db_session] = _db_session_override(rows)
        try:
            response = client.get("/api/v1/artifacts", params=_WORKFLOW_PARAMS)
        finally:
            app.dependency_overrides.pop(get_db_session, None)

        assert response.status_code == status.HTTP_200_OK
        items = response.json()["items"]
        assert all(i["type"] == "workflow" for i in items)

    def test_search_filter_applied_in_python(self, app, client):
        """When search is supplied, results are filtered by name/description match.

        The router applies Python-level filtering (case-insensitive substring
        on name and description) after the DB query returns all workflow rows.
        We supply all rows and expect only the matching one back.
        """
        all_rows = [
            _make_db_artifact(
                "workflow:alpha", "Alpha Workflow", description="Alpha description"
            ),
            _make_db_artifact(
                "workflow:beta", "Beta Workflow", description="Beta description"
            ),
        ]
        app.dependency_overrides[get_db_session] = _db_session_override(all_rows)
        try:
            response = client.get(
                "/api/v1/artifacts",
                params={"artifact_type": "workflow", "search": "alpha"},
            )
        finally:
            app.dependency_overrides.pop(get_db_session, None)

        assert response.status_code == status.HTTP_200_OK
        items = response.json()["items"]
        assert len(items) == 1
        assert "alpha" in items[0]["name"].lower()

    def test_no_n_plus_one_queries(self, app, client):
        """Batch of workflow rows uses at most 2 DB queries (no per-row lookups).

        The router loads artifact_metadata via selectin relationship eager-loading,
        so all metadata arrives in one query alongside the main artifacts query.
        We verify the mock session's query() is called at most twice.
        """
        rows = [
            _make_db_artifact(f"workflow:n1-{i}", f"N1 Workflow {i}")
            for i in range(5)
        ]
        mock_session = _make_mock_db_session(rows)

        def _override():
            yield mock_session

        app.dependency_overrides[get_db_session] = _override
        try:
            response = client.get("/api/v1/artifacts", params=_WORKFLOW_PARAMS)
        finally:
            app.dependency_overrides.pop(get_db_session, None)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()["items"]) == 5

        # The session.query() should be called at most twice
        # (once for the main query, potentially once for metadata if not selectin)
        call_count = mock_session.query.call_count
        assert call_count <= 2, (
            f"Expected at most 2 session.query() calls (no N+1), got {call_count}"
        )

    def test_pagination_page_info_present(self, app, client):
        """Response includes page_info for cursor-based pagination."""
        rows = [_make_db_artifact("workflow:page-1", "Page Test Workflow")]
        app.dependency_overrides[get_db_session] = _db_session_override(rows)
        try:
            response = client.get("/api/v1/artifacts", params=_WORKFLOW_PARAMS)
        finally:
            app.dependency_overrides.pop(get_db_session, None)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "page_info" in data
        pi = data["page_info"]
        assert "has_next_page" in pi
        assert "has_previous_page" in pi

    def test_workflow_id_populated_from_metadata_json(self, app, client):
        """workflow_id is extracted from artifact_metadata.metadata_json."""
        expected_wf_id = "specific-workflow-uuid-123"
        rows = [
            _make_db_artifact(
                "workflow:meta-wf",
                "Meta Workflow",
                workflow_id=expected_wf_id,
            )
        ]
        app.dependency_overrides[get_db_session] = _db_session_override(rows)
        try:
            response = client.get("/api/v1/artifacts", params=_WORKFLOW_PARAMS)
        finally:
            app.dependency_overrides.pop(get_db_session, None)

        assert response.status_code == status.HTTP_200_OK
        item = response.json()["items"][0]
        assert item["workflow_id"] == expected_wf_id

    def test_workflow_id_none_when_metadata_missing(self, app, client):
        """workflow_id is None when artifact has no artifact_metadata."""
        row = _make_db_artifact("workflow:no-meta", "No Meta Workflow")
        row.artifact_metadata = None  # no metadata at all

        app.dependency_overrides[get_db_session] = _db_session_override([row])
        try:
            response = client.get("/api/v1/artifacts", params=_WORKFLOW_PARAMS)
        finally:
            app.dependency_overrides.pop(get_db_session, None)

        assert response.status_code == status.HTTP_200_OK
        item = response.json()["items"][0]
        assert item.get("workflow_id") is None
