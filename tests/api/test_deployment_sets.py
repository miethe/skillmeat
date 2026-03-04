"""Tests for Deployment Sets API endpoints.

This module tests the /api/v1/deployment-sets endpoints, including:
- Create, list, get, update, delete deployment sets
- Clone a deployment set
- List, add, remove, update members
- Resolve a deployment set to its flat artifact list
- Batch deploy all artifacts in a deployment set
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_settings():
    """Create test API settings with auth disabled."""
    return APISettings(
        env=Environment.TESTING,
        host="127.0.0.1",
        port=8000,
        log_level="DEBUG",
        api_key_enabled=False,
        auth_enabled=False,
    )


@pytest.fixture
def app(test_settings):
    """Create FastAPI test application."""
    from skillmeat.api.config import get_settings

    app = create_app(test_settings)
    app.dependency_overrides[get_settings] = lambda: test_settings
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    with TestClient(app) as test_client:
        yield test_client


def _make_ds_orm(
    id="set-uuid-001",
    name="My Dev Setup",
    description="A dev setup",
    icon=None,
    color=None,
    tags=None,
    owner_id="local-user",
    members=None,
    created_at=None,
    updated_at=None,
):
    """Build a mock DeploymentSet ORM-like object."""
    ds = MagicMock()
    ds.id = id
    ds.name = name
    ds.description = description
    ds.icon = icon
    ds.color = color
    ds.owner_id = owner_id
    ds.members = members if members is not None else []
    ds.created_at = created_at or datetime(2026, 1, 1, 0, 0, 0)
    ds.updated_at = updated_at or datetime(2026, 1, 2, 0, 0, 0)
    ds.get_tags.return_value = tags if tags is not None else []
    return ds


def _make_member_orm(
    id="member-uuid-001",
    set_id="set-uuid-001",
    artifact_uuid="artifact-uuid-abc",
    group_id=None,
    member_set_id=None,
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
    m.position = position
    m.created_at = created_at or datetime(2026, 1, 1, 0, 0, 0)
    return m


# ---------------------------------------------------------------------------
# POST /api/v1/deployment-sets — create_deployment_set
# ---------------------------------------------------------------------------


class TestCreateDeploymentSet:
    """Tests for POST /api/v1/deployment-sets."""

    def test_create_deployment_set_success(self, client):
        """Creating a deployment set returns 201 with the new set data."""
        ds = _make_ds_orm(name="My Dev Setup")
        mock_repo = MagicMock()
        mock_repo.create.return_value = ds

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=mock_repo,
        ):
            response = client.post(
                "/api/v1/deployment-sets",
                json={"name": "My Dev Setup", "description": "A dev setup"},
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "My Dev Setup"
        assert data["id"] == "set-uuid-001"

    def test_create_deployment_set_repo_error_returns_422(self, client):
        """Repository errors during creation return 422."""
        from skillmeat.cache.repositories import RepositoryError

        mock_repo = MagicMock()
        mock_repo.create.side_effect = RepositoryError("duplicate name")

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=mock_repo,
        ):
            response = client.post(
                "/api/v1/deployment-sets",
                json={"name": "Duplicate Set"},
            )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_deployment_set_missing_name_returns_422(self, client):
        """Missing required 'name' field returns 422 validation error."""
        response = client.post("/api/v1/deployment-sets", json={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# GET /api/v1/deployment-sets — list_deployment_sets
# ---------------------------------------------------------------------------


class TestListDeploymentSets:
    """Tests for GET /api/v1/deployment-sets."""

    def test_list_deployment_sets_empty(self, client):
        """Listing deployment sets returns 200 with empty items list."""
        mock_repo = MagicMock()
        mock_repo.list.return_value = []
        mock_repo.count.return_value = 0

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=mock_repo,
        ):
            response = client.get("/api/v1/deployment-sets")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_deployment_sets_returns_items(self, client):
        """Listing returns all sets with correct structure."""
        ds1 = _make_ds_orm(id="set-001", name="Set One")
        ds2 = _make_ds_orm(id="set-002", name="Set Two")

        mock_repo = MagicMock()
        mock_repo.list.return_value = [ds1, ds2]
        mock_repo.count.return_value = 2

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=mock_repo,
        ):
            response = client.get("/api/v1/deployment-sets")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_list_deployment_sets_with_name_filter(self, client):
        """Name query parameter is forwarded to the repository."""
        mock_repo = MagicMock()
        mock_repo.list.return_value = []
        mock_repo.count.return_value = 0

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=mock_repo,
        ):
            response = client.get("/api/v1/deployment-sets?name=Dev")

        assert response.status_code == status.HTTP_200_OK
        mock_repo.list.assert_called_once()
        call_kwargs = mock_repo.list.call_args[1]
        assert call_kwargs.get("name") == "Dev"


# ---------------------------------------------------------------------------
# GET /api/v1/deployment-sets/{set_id} — get_deployment_set
# ---------------------------------------------------------------------------


class TestGetDeploymentSet:
    """Tests for GET /api/v1/deployment-sets/{set_id}."""

    def test_get_deployment_set_success(self, client):
        """Fetching an existing set returns 200."""
        ds = _make_ds_orm(id="set-uuid-001", name="My Set")
        mock_repo = MagicMock()
        mock_repo.get.return_value = ds

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=mock_repo,
        ):
            response = client.get("/api/v1/deployment-sets/set-uuid-001")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == "set-uuid-001"

    def test_get_deployment_set_not_found(self, client):
        """Fetching a non-existent set returns 404."""
        mock_repo = MagicMock()
        mock_repo.get.return_value = None

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=mock_repo,
        ):
            response = client.get("/api/v1/deployment-sets/nonexistent-id")

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# PUT /api/v1/deployment-sets/{set_id} — update_deployment_set
# ---------------------------------------------------------------------------


class TestUpdateDeploymentSet:
    """Tests for PUT /api/v1/deployment-sets/{set_id}."""

    def test_update_deployment_set_success(self, client):
        """Updating an existing set returns 200 with updated data."""
        ds = _make_ds_orm(id="set-uuid-001", name="Updated Set")
        mock_repo = MagicMock()
        mock_repo.update.return_value = ds

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=mock_repo,
        ):
            response = client.put(
                "/api/v1/deployment-sets/set-uuid-001",
                json={"name": "Updated Set"},
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == "Updated Set"

    def test_update_deployment_set_not_found(self, client):
        """Updating a non-existent set returns 404."""
        mock_repo = MagicMock()
        mock_repo.update.return_value = None

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=mock_repo,
        ):
            response = client.put(
                "/api/v1/deployment-sets/nonexistent-id",
                json={"name": "Ghost Set"},
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_deployment_set_repo_error_returns_422(self, client):
        """Repository errors during update return 422."""
        from skillmeat.cache.repositories import RepositoryError

        mock_repo = MagicMock()
        mock_repo.update.side_effect = RepositoryError("constraint violation")

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=mock_repo,
        ):
            response = client.put(
                "/api/v1/deployment-sets/set-uuid-001",
                json={"name": "Bad Update"},
            )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# DELETE /api/v1/deployment-sets/{set_id} — delete_deployment_set
# ---------------------------------------------------------------------------


class TestDeleteDeploymentSet:
    """Tests for DELETE /api/v1/deployment-sets/{set_id}."""

    def test_delete_deployment_set_success(self, client):
        """Deleting an existing set returns 204 with no content."""
        mock_repo = MagicMock()
        mock_repo.delete.return_value = True

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=mock_repo,
        ):
            response = client.delete("/api/v1/deployment-sets/set-uuid-001")

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_deployment_set_not_found(self, client):
        """Deleting a non-existent set returns 404."""
        mock_repo = MagicMock()
        mock_repo.delete.return_value = False

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=mock_repo,
        ):
            response = client.delete("/api/v1/deployment-sets/nonexistent-id")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_deployment_set_repo_error_returns_422(self, client):
        """Repository errors during deletion return 422."""
        from skillmeat.cache.repositories import RepositoryError

        mock_repo = MagicMock()
        mock_repo.delete.side_effect = RepositoryError("FK constraint")

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=mock_repo,
        ):
            response = client.delete("/api/v1/deployment-sets/set-uuid-001")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# POST /api/v1/deployment-sets/{set_id}/clone — clone_deployment_set
# ---------------------------------------------------------------------------


class TestCloneDeploymentSet:
    """Tests for POST /api/v1/deployment-sets/{set_id}/clone."""

    def test_clone_deployment_set_success(self, client):
        """Cloning an existing set returns 201 with the clone data."""
        source = _make_ds_orm(id="source-id", name="My Set", members=[])
        clone = _make_ds_orm(id="clone-id", name="My Set (copy)")

        mock_repo = MagicMock()
        # get() is called twice: once for source, once for the freshly created clone
        mock_repo.get.side_effect = [source, clone]
        mock_repo.create.return_value = clone

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=mock_repo,
        ):
            response = client.post("/api/v1/deployment-sets/source-id/clone")

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "copy" in data["name"]

    def test_clone_deployment_set_source_not_found(self, client):
        """Cloning a non-existent source set returns 404."""
        mock_repo = MagicMock()
        mock_repo.get.return_value = None

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=mock_repo,
        ):
            response = client.post("/api/v1/deployment-sets/ghost-id/clone")

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# GET /api/v1/deployment-sets/{set_id}/members — list_members
# ---------------------------------------------------------------------------


class TestListMembers:
    """Tests for GET /api/v1/deployment-sets/{set_id}/members."""

    def test_list_members_success(self, client):
        """Listing members of a valid set returns 200 with member list."""
        ds = _make_ds_orm()
        member = _make_member_orm()

        mock_repo = MagicMock()
        mock_repo.get.return_value = ds
        mock_repo.get_members.return_value = [member]

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=mock_repo,
        ):
            response = client.get("/api/v1/deployment-sets/set-uuid-001/members")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["artifact_uuid"] == "artifact-uuid-abc"

    def test_list_members_set_not_found(self, client):
        """Listing members of a non-existent set returns 404."""
        mock_repo = MagicMock()
        mock_repo.get.return_value = None

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=mock_repo,
        ):
            response = client.get("/api/v1/deployment-sets/ghost-id/members")

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# POST /api/v1/deployment-sets/{set_id}/members — add_member
# ---------------------------------------------------------------------------


class TestAddMember:
    """Tests for POST /api/v1/deployment-sets/{set_id}/members."""

    def test_add_artifact_member_success(self, client):
        """Adding an artifact member returns 201 with member data."""
        ds = _make_ds_orm()
        member = _make_member_orm(artifact_uuid="new-artifact-uuid")

        mock_repo = MagicMock()
        mock_repo.get.return_value = ds
        mock_repo.add_member.return_value = member

        mock_session = MagicMock()

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=mock_repo,
        ), patch(
            "skillmeat.api.routers.deployment_sets.get_session",
            return_value=mock_session,
        ):
            response = client.post(
                "/api/v1/deployment-sets/set-uuid-001/members",
                json={"artifact_uuid": "new-artifact-uuid", "position": 0},
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["member_type"] == "artifact"

    def test_add_member_set_not_found(self, client):
        """Adding a member to a non-existent set returns 404."""
        mock_repo = MagicMock()
        mock_repo.get.return_value = None

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=mock_repo,
        ):
            response = client.post(
                "/api/v1/deployment-sets/ghost-id/members",
                json={"artifact_uuid": "some-uuid"},
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_add_member_no_ref_returns_422(self, client):
        """Providing none of artifact_uuid/group_id/nested_set_id returns 422."""
        response = client.post(
            "/api/v1/deployment-sets/set-uuid-001/members",
            json={"position": 0},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_add_member_multiple_refs_returns_422(self, client):
        """Providing more than one reference field returns 422."""
        response = client.post(
            "/api/v1/deployment-sets/set-uuid-001/members",
            json={
                "artifact_uuid": "uuid-a",
                "group_id": "group-b",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_add_nested_set_member_cycle_returns_422(self, client):
        """Adding a nested set that would create a cycle returns 422."""
        from skillmeat.core.exceptions import DeploymentSetCycleError

        ds = _make_ds_orm()
        mock_repo = MagicMock()
        mock_repo.get.return_value = ds

        mock_session = MagicMock()
        mock_svc = MagicMock()
        mock_svc.add_member_with_cycle_check.side_effect = DeploymentSetCycleError(
            "set-uuid-001", path=["set-uuid-001", "set-uuid-001"]
        )

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=mock_repo,
        ), patch(
            "skillmeat.api.routers.deployment_sets.get_session",
            return_value=mock_session,
        ), patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetService",
            return_value=mock_svc,
        ):
            response = client.post(
                "/api/v1/deployment-sets/set-uuid-001/members",
                json={"nested_set_id": "set-uuid-001"},
            )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "circular" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# DELETE /api/v1/deployment-sets/{set_id}/members/{member_id} — remove_member
# ---------------------------------------------------------------------------


class TestRemoveMember:
    """Tests for DELETE /api/v1/deployment-sets/{set_id}/members/{member_id}."""

    def test_remove_member_success(self, client):
        """Removing an existing member returns 204."""
        ds = _make_ds_orm()
        mock_repo = MagicMock()
        mock_repo.get.return_value = ds
        mock_repo.remove_member.return_value = True

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=mock_repo,
        ):
            response = client.delete(
                "/api/v1/deployment-sets/set-uuid-001/members/member-uuid-001"
            )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_remove_member_set_not_found(self, client):
        """Removing a member from a non-existent set returns 404."""
        mock_repo = MagicMock()
        mock_repo.get.return_value = None

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=mock_repo,
        ):
            response = client.delete(
                "/api/v1/deployment-sets/ghost-id/members/member-uuid-001"
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_remove_member_not_found(self, client):
        """Removing a non-existent member returns 404."""
        ds = _make_ds_orm()
        mock_repo = MagicMock()
        mock_repo.get.return_value = ds
        mock_repo.remove_member.return_value = False

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=mock_repo,
        ):
            response = client.delete(
                "/api/v1/deployment-sets/set-uuid-001/members/ghost-member-id"
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# PUT /api/v1/deployment-sets/{set_id}/members/{member_id} — update_member_position
# ---------------------------------------------------------------------------


class TestUpdateMemberPosition:
    """Tests for PUT /api/v1/deployment-sets/{set_id}/members/{member_id}."""

    def test_update_member_position_success(self, client):
        """Updating a member position returns 200 with updated member."""
        ds = _make_ds_orm()
        member = _make_member_orm(position=3)

        mock_repo = MagicMock()
        mock_repo.get.return_value = ds
        mock_repo.update_member_position.return_value = member

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=mock_repo,
        ):
            response = client.put(
                "/api/v1/deployment-sets/set-uuid-001/members/member-uuid-001",
                json={"position": 3},
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["position"] == 3

    def test_update_member_position_set_not_found(self, client):
        """Updating a member when the set does not exist returns 404."""
        mock_repo = MagicMock()
        mock_repo.get.return_value = None

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=mock_repo,
        ):
            response = client.put(
                "/api/v1/deployment-sets/ghost-id/members/member-uuid-001",
                json={"position": 1},
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_member_position_member_not_found(self, client):
        """Updating a non-existent member returns 404."""
        ds = _make_ds_orm()
        mock_repo = MagicMock()
        mock_repo.get.return_value = ds
        mock_repo.update_member_position.return_value = None

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=mock_repo,
        ):
            response = client.put(
                "/api/v1/deployment-sets/set-uuid-001/members/ghost-member",
                json={"position": 1},
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_member_position_missing_position_returns_422(self, client):
        """Missing required 'position' field returns 422."""
        response = client.put(
            "/api/v1/deployment-sets/set-uuid-001/members/member-uuid-001",
            json={},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# GET /api/v1/deployment-sets/{set_id}/resolve — resolve_deployment_set
# ---------------------------------------------------------------------------


class TestResolveDeploymentSet:
    """Tests for GET /api/v1/deployment-sets/{set_id}/resolve."""

    def test_resolve_deployment_set_empty(self, client):
        """Resolving an empty set returns 200 with zero artifacts."""
        ds = _make_ds_orm()
        mock_repo = MagicMock()
        mock_repo.get.return_value = ds

        mock_session = MagicMock()
        mock_svc = MagicMock()
        mock_svc.resolve.return_value = []
        mock_session.query.return_value.filter.return_value.all.return_value = []

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=mock_repo,
        ), patch(
            "skillmeat.api.routers.deployment_sets.get_session",
            return_value=mock_session,
        ), patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetService",
            return_value=mock_svc,
        ):
            response = client.get("/api/v1/deployment-sets/set-uuid-001/resolve")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["set_id"] == "set-uuid-001"
        assert data["total_count"] == 0
        assert data["resolved_artifacts"] == []

    def test_resolve_deployment_set_not_found(self, client):
        """Resolving a non-existent set returns 404."""
        mock_repo = MagicMock()
        mock_repo.get.return_value = None

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=mock_repo,
        ):
            response = client.get("/api/v1/deployment-sets/ghost-id/resolve")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_resolve_deployment_set_depth_limit_returns_422(self, client):
        """Resolution depth-limit exceeded returns 422."""
        from skillmeat.core.exceptions import DeploymentSetResolutionError

        ds = _make_ds_orm()
        mock_repo = MagicMock()
        mock_repo.get.return_value = ds

        mock_session = MagicMock()
        mock_svc = MagicMock()
        mock_svc.resolve.side_effect = DeploymentSetResolutionError(
            "set-uuid-001", path=["set-uuid-001", "nested-set-id"], depth_limit=20
        )

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=mock_repo,
        ), patch(
            "skillmeat.api.routers.deployment_sets.get_session",
            return_value=mock_session,
        ), patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetService",
            return_value=mock_svc,
        ):
            response = client.get("/api/v1/deployment-sets/set-uuid-001/resolve")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# POST /api/v1/deployment-sets/{set_id}/deploy — batch_deploy
# ---------------------------------------------------------------------------


class TestBatchDeploy:
    """Tests for POST /api/v1/deployment-sets/{set_id}/deploy."""

    def test_batch_deploy_dry_run_success(self, client, tmp_path):
        """Dry-run batch deploy returns 200 with all results skipped."""
        ds = _make_ds_orm(id="set-uuid-001", name="My Set")
        mock_repo = MagicMock()
        mock_repo.get.return_value = ds

        mock_session = MagicMock()
        mock_svc = MagicMock()
        mock_svc.resolve.return_value = ["artifact-uuid-abc"]

        # Simulate artifact cache row
        art_row = MagicMock()
        art_row.uuid = "artifact-uuid-abc"
        art_row.name = "pdf-skill"
        art_row.type = "skill"
        mock_session.query.return_value.join.return_value.filter.return_value.all.return_value = [
            art_row
        ]

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=mock_repo,
        ), patch(
            "skillmeat.api.routers.deployment_sets.get_session",
            return_value=mock_session,
        ), patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetService",
            return_value=mock_svc,
        ):
            response = client.post(
                "/api/v1/deployment-sets/set-uuid-001/deploy",
                json={"project_path": str(tmp_path), "dry_run": True},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["dry_run"] is True
        assert data["total"] == 1
        assert data["skipped"] == 1
        assert data["succeeded"] == 0
        assert data["failed"] == 0

    def test_batch_deploy_set_not_found(self, client, tmp_path):
        """Batch deploy on a non-existent set returns 404."""
        mock_repo = MagicMock()
        mock_repo.get.return_value = None

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=mock_repo,
        ):
            response = client.post(
                "/api/v1/deployment-sets/ghost-id/deploy",
                json={"project_path": str(tmp_path), "dry_run": False},
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_batch_deploy_invalid_project_path_returns_422(self, client):
        """Batch deploy with a non-existent project path returns 422."""
        ds = _make_ds_orm()
        mock_repo = MagicMock()
        mock_repo.get.return_value = ds

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=mock_repo,
        ):
            response = client.post(
                "/api/v1/deployment-sets/set-uuid-001/deploy",
                json={
                    "project_path": "/this/path/does/not/exist/at/all",
                    "dry_run": False,
                },
            )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
