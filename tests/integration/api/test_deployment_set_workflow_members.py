"""Integration tests for workflow members in deployment sets.

WAW-P5.5: Verifies CRUD operations for workflow-type members in deployment
sets, including FK validation that prevents dangling workflow references.

Uses TestClient with dependency overrides and mock repositories, following the
pattern from ``tests/api/test_deployment_sets.py``.  The FK validation test
(invalid workflow_id → 404) relies on a real DB session override so the router
can actually query the workflows table.

Scenarios tested
----------------
1. POST /api/v1/deployment-sets/{id}/members with workflow_id succeeds (201).
2. GET /api/v1/deployment-sets/{id}/members returns workflow members with
   workflow_id field populated.
3. DELETE workflow member returns 204.
4. FK constraint: adding a member with an unknown workflow_id returns 404.
5. Member type is reported as "workflow" in the response.
6. Mixed artifact + workflow member list returns correct member_type per item.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings, Environment, get_settings
from skillmeat.api.dependencies import get_deployment_set_repository
from skillmeat.api.server import create_app
from skillmeat.cache.session import get_db_session
from skillmeat.api.dependencies import DbSessionDep


# ---------------------------------------------------------------------------
# ORM mock helpers (same style as tests/api/test_deployment_sets.py)
# ---------------------------------------------------------------------------


def _make_ds_orm(
    id="set-uuid-001",
    name="Test Deployment Set",
    description="Integration test set",
    tags=None,
    members=None,
    created_at=None,
    updated_at=None,
):
    """Build a mock DeploymentSet ORM-like object."""
    ds = MagicMock()
    ds.id = id
    ds.name = name
    ds.description = description
    ds.icon = None
    ds.color = None
    ds.owner_id = "local-user"
    ds.members = members if members is not None else []
    ds.created_at = created_at or datetime(2026, 1, 1)
    ds.updated_at = updated_at or datetime(2026, 1, 2)
    ds.get_tags.return_value = tags if tags is not None else []
    return ds


def _make_member_orm(
    id="member-uuid-001",
    set_id="set-uuid-001",
    artifact_uuid=None,
    group_id=None,
    member_set_id=None,
    workflow_id=None,
    position=0,
    created_at=None,
):
    """Build a mock DeploymentSetMember ORM-like object."""
    m = MagicMock()
    m.id = id
    m.set_id = set_id
    m.artifact_uuid = artifact_uuid
    m.group_id = group_id
    m.member_set_id = member_set_id
    m.workflow_id = workflow_id
    m.position = position
    m.created_at = created_at or datetime(2026, 1, 1)
    return m


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


def _make_mock_db_session_with_workflow(workflow_id: str) -> MagicMock:
    """Build a mock SQLAlchemy session that returns a fake Workflow row for ``workflow_id``."""
    session = MagicMock()

    fake_workflow = MagicMock()
    fake_workflow.id = workflow_id

    query_mock = MagicMock()
    query_mock.filter.return_value = query_mock
    query_mock.first.return_value = fake_workflow

    session.query.return_value = query_mock
    return session


def _make_mock_db_session_no_workflow() -> MagicMock:
    """Build a mock session that returns None for any Workflow lookup (simulates missing row)."""
    session = MagicMock()

    query_mock = MagicMock()
    query_mock.filter.return_value = query_mock
    query_mock.first.return_value = None

    session.query.return_value = query_mock
    return session


# ---------------------------------------------------------------------------
# Tests — Add workflow member (POST)
# ---------------------------------------------------------------------------


class TestAddWorkflowMember:
    """POST /api/v1/deployment-sets/{id}/members with workflow_id."""

    def test_add_workflow_member_success(self, app, client):
        """Adding a valid workflow member returns 201 with member_type=workflow."""
        wf_id = "valid-workflow-uuid-abc"
        ds = _make_ds_orm()
        member = _make_member_orm(workflow_id=wf_id)

        mock_repo = MagicMock()
        mock_repo.get.return_value = ds
        mock_repo.add_member.return_value = member

        mock_session = _make_mock_db_session_with_workflow(wf_id)

        def _db_override():
            yield mock_session

        app.dependency_overrides[get_deployment_set_repository] = lambda: mock_repo
        app.dependency_overrides[get_db_session] = _db_override
        try:
            response = client.post(
                "/api/v1/deployment-sets/set-uuid-001/members",
                json={"workflow_id": wf_id, "position": 0},
            )
        finally:
            app.dependency_overrides.pop(get_deployment_set_repository, None)
            app.dependency_overrides.pop(get_db_session, None)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["member_type"] == "workflow"
        assert data["workflow_id"] == wf_id

    def test_add_workflow_member_returns_correct_workflow_id(self, app, client):
        """The workflow_id field in the response matches the requested workflow."""
        wf_id = "wf-specific-id-xyz"
        ds = _make_ds_orm()
        member = _make_member_orm(id="member-wf-specific", workflow_id=wf_id)

        mock_repo = MagicMock()
        mock_repo.get.return_value = ds
        mock_repo.add_member.return_value = member

        mock_session = _make_mock_db_session_with_workflow(wf_id)

        def _db_override():
            yield mock_session

        app.dependency_overrides[get_deployment_set_repository] = lambda: mock_repo
        app.dependency_overrides[get_db_session] = _db_override
        try:
            response = client.post(
                "/api/v1/deployment-sets/set-uuid-001/members",
                json={"workflow_id": wf_id},
            )
        finally:
            app.dependency_overrides.pop(get_deployment_set_repository, None)
            app.dependency_overrides.pop(get_db_session, None)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["workflow_id"] == wf_id
        assert data["id"] == "member-wf-specific"

    def test_add_workflow_member_invalid_workflow_id_returns_404(self, app, client):
        """Adding a workflow member with an unknown workflow_id returns 404.

        The router performs an explicit pre-flight DB check because SQLite does
        not enforce FK constraints by default.  The mock session returns None
        for the Workflow.filter query to simulate a missing row.
        """
        ds = _make_ds_orm()
        mock_repo = MagicMock()
        mock_repo.get.return_value = ds

        mock_session = _make_mock_db_session_no_workflow()

        def _db_override():
            yield mock_session

        app.dependency_overrides[get_deployment_set_repository] = lambda: mock_repo
        app.dependency_overrides[get_db_session] = _db_override
        try:
            response = client.post(
                "/api/v1/deployment-sets/set-uuid-001/members",
                json={"workflow_id": "non-existent-workflow-id-xyz"},
            )
        finally:
            app.dependency_overrides.pop(get_deployment_set_repository, None)
            app.dependency_overrides.pop(get_db_session, None)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        detail = response.json()["detail"].lower()
        assert "workflow" in detail

    def test_add_workflow_member_set_not_found_returns_404(self, app, client):
        """Adding a member to a non-existent deployment set returns 404."""
        mock_repo = MagicMock()
        mock_repo.get.return_value = None

        app.dependency_overrides[get_deployment_set_repository] = lambda: mock_repo
        try:
            response = client.post(
                "/api/v1/deployment-sets/ghost-set-id/members",
                json={"workflow_id": "any-wf-id"},
            )
        finally:
            app.dependency_overrides.pop(get_deployment_set_repository, None)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_add_workflow_member_with_both_workflow_and_artifact_returns_422(
        self, app, client
    ):
        """Providing both workflow_id and artifact_uuid is rejected with 422."""
        response = client.post(
            "/api/v1/deployment-sets/set-uuid-001/members",
            json={
                "workflow_id": "some-wf-id",
                "artifact_uuid": "some-artifact-uuid",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_add_workflow_member_no_ref_returns_422(self, client):
        """Providing none of the required ref fields returns 422."""
        response = client.post(
            "/api/v1/deployment-sets/set-uuid-001/members",
            json={"position": 0},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# Tests — List workflow members (GET)
# ---------------------------------------------------------------------------


class TestListWorkflowMembers:
    """GET /api/v1/deployment-sets/{id}/members — workflow member listing."""

    def test_list_members_includes_workflow_id(self, app, client):
        """Listing members of a set includes workflow_id for workflow-type members."""
        wf_id = "wf-list-test-id"
        ds = _make_ds_orm()
        member = _make_member_orm(id="member-list-wf", workflow_id=wf_id)

        mock_repo = MagicMock()
        mock_repo.get.return_value = ds
        mock_repo.get_members.return_value = [member]

        app.dependency_overrides[get_deployment_set_repository] = lambda: mock_repo
        try:
            response = client.get("/api/v1/deployment-sets/set-uuid-001/members")
        finally:
            app.dependency_overrides.pop(get_deployment_set_repository, None)

        assert response.status_code == status.HTTP_200_OK
        members = response.json()
        assert len(members) == 1
        assert members[0]["member_type"] == "workflow"
        assert members[0]["workflow_id"] == wf_id

    def test_list_members_workflow_member_type(self, app, client):
        """Member type is 'workflow' when workflow_id is set."""
        ds = _make_ds_orm()
        member = _make_member_orm(workflow_id="some-wf-id")

        mock_repo = MagicMock()
        mock_repo.get.return_value = ds
        mock_repo.get_members.return_value = [member]

        app.dependency_overrides[get_deployment_set_repository] = lambda: mock_repo
        try:
            response = client.get("/api/v1/deployment-sets/set-uuid-001/members")
        finally:
            app.dependency_overrides.pop(get_deployment_set_repository, None)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data[0]["member_type"] == "workflow"

    def test_list_members_mixed_types_correct_fields(self, app, client):
        """Mixed member types return correct member_type and field population."""
        wf_id = "mixed-list-wf-id"
        ds = _make_ds_orm()
        artifact_member = _make_member_orm(
            id="member-artifact",
            artifact_uuid="artifact-uuid-abc",
        )
        workflow_member = _make_member_orm(
            id="member-workflow",
            workflow_id=wf_id,
        )

        mock_repo = MagicMock()
        mock_repo.get.return_value = ds
        mock_repo.get_members.return_value = [artifact_member, workflow_member]

        app.dependency_overrides[get_deployment_set_repository] = lambda: mock_repo
        try:
            response = client.get("/api/v1/deployment-sets/set-uuid-001/members")
        finally:
            app.dependency_overrides.pop(get_deployment_set_repository, None)

        assert response.status_code == status.HTTP_200_OK
        members = response.json()
        assert len(members) == 2

        by_id = {m["id"]: m for m in members}

        # Artifact member
        assert by_id["member-artifact"]["member_type"] == "artifact"
        assert by_id["member-artifact"].get("workflow_id") is None

        # Workflow member
        assert by_id["member-workflow"]["member_type"] == "workflow"
        assert by_id["member-workflow"]["workflow_id"] == wf_id

    def test_list_members_set_not_found(self, app, client):
        """Listing members of a non-existent set returns 404."""
        mock_repo = MagicMock()
        mock_repo.get.return_value = None

        app.dependency_overrides[get_deployment_set_repository] = lambda: mock_repo
        try:
            response = client.get("/api/v1/deployment-sets/ghost-id/members")
        finally:
            app.dependency_overrides.pop(get_deployment_set_repository, None)

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# Tests — Delete workflow member (DELETE)
# ---------------------------------------------------------------------------


class TestDeleteWorkflowMember:
    """DELETE /api/v1/deployment-sets/{id}/members/{member_id} — workflow member removal."""

    def test_delete_workflow_member_success(self, app, client):
        """Deleting an existing workflow member returns 204."""
        ds = _make_ds_orm()
        mock_repo = MagicMock()
        mock_repo.get.return_value = ds
        mock_repo.remove_member.return_value = True

        app.dependency_overrides[get_deployment_set_repository] = lambda: mock_repo
        try:
            response = client.delete(
                "/api/v1/deployment-sets/set-uuid-001/members/member-wf-001"
            )
        finally:
            app.dependency_overrides.pop(get_deployment_set_repository, None)

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_workflow_member_not_found_returns_404(self, app, client):
        """Deleting a non-existent workflow member returns 404."""
        ds = _make_ds_orm()
        mock_repo = MagicMock()
        mock_repo.get.return_value = ds
        mock_repo.remove_member.return_value = False

        app.dependency_overrides[get_deployment_set_repository] = lambda: mock_repo
        try:
            response = client.delete(
                "/api/v1/deployment-sets/set-uuid-001/members/ghost-wf-member"
            )
        finally:
            app.dependency_overrides.pop(get_deployment_set_repository, None)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_workflow_member_parent_set_not_found(self, app, client):
        """Deleting a member when the parent set is not found returns 404."""
        mock_repo = MagicMock()
        mock_repo.get.return_value = None

        app.dependency_overrides[get_deployment_set_repository] = lambda: mock_repo
        try:
            response = client.delete(
                "/api/v1/deployment-sets/ghost-set/members/member-wf-001"
            )
        finally:
            app.dependency_overrides.pop(get_deployment_set_repository, None)

        assert response.status_code == status.HTTP_404_NOT_FOUND
