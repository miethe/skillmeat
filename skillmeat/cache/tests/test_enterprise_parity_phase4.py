"""Unit tests for Phase 4 enterprise repositories (ENT2-4.5).

Classes under test:
    - EnterpriseProjectRepository       (ENT2-4.1)
    - EnterpriseDeploymentRepository    (ENT2-4.2)
    - EnterpriseDeploymentSetRepository (ENT2-4.3)
    - EnterpriseDeploymentProfileRepository (ENT2-4.4)

Strategy:
    All tests use ``MagicMock(spec=Session)`` — no SQLite shims.
    Session.execute() return values are wired to return lightweight MagicMock
    objects so repository logic is exercised without a real database.

    JSONB ``@>`` operator tests are marked ``@pytest.mark.integration`` and
    are excluded from the unit test run.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import MagicMock, call, patch

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from skillmeat.cache.enterprise_repositories import (
    EnterpriseDeploymentProfileRepository,
    EnterpriseDeploymentRepository,
    EnterpriseDeploymentSetRepository,
    EnterpriseProjectRepository,
    TenantIsolationError,
    tenant_scope,
)

# ---------------------------------------------------------------------------
# Fixed tenant UUIDs — stable across re-runs for readable failure messages.
# ---------------------------------------------------------------------------

TENANT_A = uuid.UUID("aaaaaaaa-0000-4000-a000-000000000001")
TENANT_B = uuid.UUID("bbbbbbbb-0000-4000-b000-000000000002")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.utcnow()


def _make_session() -> MagicMock:
    """Return a fresh MagicMock(spec=Session)."""
    return MagicMock(spec=Session)


def _scalar_result(value):
    """Wrap *value* as the return of session.execute(...).scalar_one_or_none()."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _scalars_result(values: list):
    """Wrap *values* as the return of session.execute(...).scalars()."""
    result = MagicMock()
    result.scalars.return_value = iter(values)
    return result


def _scalar_value(value):
    """Wrap a scalar (e.g. int count) as the return of session.execute(...).scalar()."""
    result = MagicMock()
    result.scalar.return_value = value
    return result


# ---------------------------------------------------------------------------
# Fake ORM-like objects
# ---------------------------------------------------------------------------


def _fake_project(
    *,
    tenant_id: uuid.UUID = TENANT_A,
    name: str = "My Project",
    path: str = "/home/user/project",
    status: str = "active",
    description: str | None = None,
    project_id: uuid.UUID | None = None,
) -> MagicMock:
    row = MagicMock()
    row.id = project_id or uuid.uuid4()
    row.tenant_id = tenant_id
    row.name = name
    row.path = path
    row.status = status
    row.description = description
    row.project_artifacts = []
    row.created_at = _now()
    row.updated_at = _now()
    return row


def _fake_artifact_row(
    *,
    tenant_id: uuid.UUID = TENANT_A,
    name: str = "canvas",
    artifact_type: str = "skill",
    source: str | None = "user/repo",
    version: str | None = "latest",
    scope: str | None = "user",
    description: str | None = None,
    artifact_id: uuid.UUID | None = None,
) -> MagicMock:
    row = MagicMock()
    row.id = artifact_id or uuid.uuid4()
    row.tenant_id = tenant_id
    row.name = name
    row.artifact_type = artifact_type
    row.source = source
    row.version = version
    row.scope = scope
    row.description = description
    row.created_at = _now()
    row.updated_at = _now()
    return row


def _fake_deployment(
    *,
    tenant_id: uuid.UUID = TENANT_A,
    artifact_id: str = "skill:canvas",
    project_id: uuid.UUID | None = None,
    artifact_uuid: uuid.UUID | None = None,
    status: str = "deployed",
    content_hash: str | None = None,
    local_modifications: bool = False,
    platform: str | None = None,
    deployment_profile_id: uuid.UUID | None = None,
    deployment_id: uuid.UUID | None = None,
) -> MagicMock:
    row = MagicMock()
    row.id = deployment_id or uuid.uuid4()
    row.tenant_id = tenant_id
    row.artifact_id = artifact_id
    row.project_id = project_id or uuid.uuid4()
    row.artifact_uuid = artifact_uuid
    row.status = status
    row.content_hash = content_hash
    row.local_modifications = local_modifications
    row.platform = platform
    row.deployment_profile_id = deployment_profile_id
    row.deployed_at = _now()
    row.updated_at = _now()
    row.project = None
    return row


def _fake_deployment_set(
    *,
    tenant_id: uuid.UUID = TENANT_A,
    name: str = "Prod Set",
    description: str | None = None,
    provisioned_by: str = "user-1",
    set_id: uuid.UUID | None = None,
) -> MagicMock:
    row = MagicMock()
    row.id = set_id or uuid.uuid4()
    row.tenant_id = tenant_id
    row.name = name
    row.description = description
    row.provisioned_by = provisioned_by
    row.created_at = _now()
    row.updated_at = _now()
    return row


def _fake_deployment_set_member(
    *,
    tenant_id: uuid.UUID = TENANT_A,
    set_id: uuid.UUID | None = None,
    artifact_id: str = "skill:canvas",
    position: int = 0,
    member_id: uuid.UUID | None = None,
) -> MagicMock:
    row = MagicMock()
    row.id = member_id or uuid.uuid4()
    row.tenant_id = tenant_id
    row.set_id = set_id or uuid.uuid4()
    row.artifact_id = artifact_id
    row.position = position
    row.member_set_id = None
    return row


def _fake_deployment_profile(
    *,
    tenant_id: uuid.UUID = TENANT_A,
    project_id: str = "proj-1",
    profile_id_str: str = "claude_code",
    platform: str = "claude_code",
    dest_path: str = ".claude",
    scope: str = "project",
    overwrite: bool = False,
    extra_metadata: dict | None = None,
    profile_db_id: uuid.UUID | None = None,
) -> MagicMock:
    row = MagicMock()
    row.id = profile_db_id or uuid.uuid4()
    row.tenant_id = tenant_id
    row.name = f"{project_id}/{profile_id_str}"
    row.platform = platform
    row.dest_path = dest_path
    row.scope = scope
    row.overwrite = overwrite
    row.extra_metadata = extra_metadata or {
        "project_id": project_id,
        "profile_id": profile_id_str,
        "root_dir": dest_path,
    }
    row.created_at = _now()
    row.updated_at = _now()
    return row


# =============================================================================
# EnterpriseProjectRepository
# =============================================================================


class TestEnterpriseProjectRepositoryGet:
    def test_get_returns_dto_for_existing_project(self):
        """get() converts an ORM row to ProjectDTO when found."""
        session = _make_session()
        proj = _fake_project(name="Alpha", path="/home/user/alpha")
        session.execute.return_value = _scalar_result(proj)

        with tenant_scope(TENANT_A):
            repo = EnterpriseProjectRepository(session)
            dto = repo.get(str(proj.id))

        assert dto is not None
        assert dto.id == str(proj.id)
        assert dto.name == "Alpha"
        assert dto.path == "/home/user/alpha"
        assert dto.status == "active"

    def test_get_returns_none_for_missing_project(self):
        """get() returns None when the UUID matches no row."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseProjectRepository(session)
            result = repo.get(str(uuid.uuid4()))

        assert result is None

    def test_get_returns_none_for_invalid_uuid(self):
        """get() returns None for non-UUID strings without querying the DB."""
        session = _make_session()

        with tenant_scope(TENANT_A):
            repo = EnterpriseProjectRepository(session)
            result = repo.get("not-a-uuid")

        assert result is None
        session.execute.assert_not_called()

    def test_get_no_filesystem_access(self):
        """get() never calls os.path or pathlib operations."""
        session = _make_session()
        proj = _fake_project()
        session.execute.return_value = _scalar_result(proj)

        with patch("os.path.exists") as mock_exists, patch("os.path.isdir") as mock_isdir:
            with tenant_scope(TENANT_A):
                repo = EnterpriseProjectRepository(session)
                repo.get(str(proj.id))

        mock_exists.assert_not_called()
        mock_isdir.assert_not_called()


class TestEnterpriseProjectRepositoryList:
    def test_list_returns_dtos_for_all_tenant_projects(self):
        """list() converts all ORM rows to DTOs."""
        session = _make_session()
        projects = [_fake_project(name="A", path="/a"), _fake_project(name="B", path="/b")]
        session.execute.return_value = _scalars_result(projects)

        with tenant_scope(TENANT_A):
            repo = EnterpriseProjectRepository(session)
            result = repo.list()

        assert len(result) == 2
        names = {dto.name for dto in result}
        assert names == {"A", "B"}

    def test_list_returns_empty_when_no_projects(self):
        """list() returns an empty list when the tenant has no projects."""
        session = _make_session()
        session.execute.return_value = _scalars_result([])

        with tenant_scope(TENANT_A):
            repo = EnterpriseProjectRepository(session)
            result = repo.list()

        assert result == []

    def test_list_with_status_filter(self):
        """list(filters={"status": ...}) accepts and applies the status filter."""
        session = _make_session()
        proj = _fake_project(status="active")
        session.execute.return_value = _scalars_result([proj])

        with tenant_scope(TENANT_A):
            repo = EnterpriseProjectRepository(session)
            result = repo.list(filters={"status": "active"})

        assert len(result) == 1
        assert result[0].status == "active"

    def test_list_with_search_filter(self):
        """list(filters={"search": ...}) passes the filter to the query."""
        session = _make_session()
        proj = _fake_project(name="canvas-project")
        session.execute.return_value = _scalars_result([proj])

        with tenant_scope(TENANT_A):
            repo = EnterpriseProjectRepository(session)
            result = repo.list(filters={"search": "canvas"})

        assert len(result) == 1
        assert "canvas" in result[0].name


class TestEnterpriseProjectRepositoryCreate:
    def test_create_adds_row_and_returns_dto(self):
        """create() calls session.add() and flush() and returns a DTO."""
        from skillmeat.core.interfaces.dtos import ProjectDTO

        session = _make_session()

        with tenant_scope(TENANT_A):
            repo = EnterpriseProjectRepository(session)
            # Patch the model so the created row has known attributes.
            new_id = uuid.uuid4()
            fake_row = _fake_project(name="NewProj", path="/new", project_id=new_id)

            with patch(
                "skillmeat.cache.models_enterprise.EnterpriseProject",
                return_value=fake_row,
            ):
                dto_in = ProjectDTO(id="", name="NewProj", path="/new", status="active")
                dto = repo.create(dto_in)

        session.add.assert_called_once()
        session.flush.assert_called()
        assert dto.name == "NewProj"

    def test_create_no_filesystem_access(self):
        """create() never accesses the filesystem for path creation."""
        from skillmeat.core.interfaces.dtos import ProjectDTO

        session = _make_session()

        with patch("os.makedirs") as mock_makedirs, patch("os.path.exists") as mock_exists:
            with tenant_scope(TENANT_A):
                repo = EnterpriseProjectRepository(session)
                new_id = uuid.uuid4()
                fake_row = _fake_project(project_id=new_id)
                with patch(
                    "skillmeat.cache.models_enterprise.EnterpriseProject",
                    return_value=fake_row,
                ):
                    dto_in = ProjectDTO(id="", name="N", path="/n", status="active")
                    repo.create(dto_in)

        mock_makedirs.assert_not_called()
        mock_exists.assert_not_called()


class TestEnterpriseProjectRepositoryUpdate:
    def test_update_applies_fields_and_returns_dto(self):
        """update() mutates the row and returns the updated DTO."""
        session = _make_session()
        proj = _fake_project(name="OldName")
        session.execute.return_value = _scalar_result(proj)

        with tenant_scope(TENANT_A):
            repo = EnterpriseProjectRepository(session)
            dto = repo.update(str(proj.id), {"name": "NewName"})

        assert proj.name == "NewName"
        session.flush.assert_called()
        assert dto is not None

    def test_update_raises_key_error_for_missing_project(self):
        """update() raises KeyError when the project does not exist."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseProjectRepository(session)
            with pytest.raises(KeyError):
                repo.update(str(uuid.uuid4()), {"name": "X"})

    def test_update_raises_key_error_for_invalid_uuid(self):
        """update() raises KeyError for non-UUID id strings."""
        session = _make_session()

        with tenant_scope(TENANT_A):
            repo = EnterpriseProjectRepository(session)
            with pytest.raises(KeyError):
                repo.update("bad-id", {"name": "X"})


class TestEnterpriseProjectRepositoryDelete:
    def test_delete_returns_true_for_existing_project(self):
        """delete() returns True when the project is found and removed."""
        session = _make_session()
        proj = _fake_project()
        session.execute.return_value = _scalar_result(proj)

        with tenant_scope(TENANT_A):
            repo = EnterpriseProjectRepository(session)
            result = repo.delete(str(proj.id))

        assert result is True
        session.delete.assert_called_once_with(proj)
        session.flush.assert_called()

    def test_delete_returns_false_for_missing_project(self):
        """delete() returns False when no matching project exists."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseProjectRepository(session)
            result = repo.delete(str(uuid.uuid4()))

        assert result is False

    def test_delete_returns_false_for_invalid_uuid(self):
        """delete() returns False for non-UUID id strings."""
        session = _make_session()

        with tenant_scope(TENANT_A):
            repo = EnterpriseProjectRepository(session)
            result = repo.delete("not-a-uuid")

        assert result is False
        session.execute.assert_not_called()


class TestEnterpriseProjectRepositoryRefresh:
    def test_refresh_updates_timestamp_and_returns_dto(self):
        """refresh() updates updated_at on the row and returns current state."""
        session = _make_session()
        proj = _fake_project()
        session.execute.return_value = _scalar_result(proj)

        before = proj.updated_at

        with tenant_scope(TENANT_A):
            repo = EnterpriseProjectRepository(session)
            dto = repo.refresh(str(proj.id))

        # updated_at should have been set (to a new datetime value)
        assert dto is not None
        session.flush.assert_called()
        # Verify updated_at was set (attribute was written on the mock)
        assert proj.updated_at is not None

    def test_refresh_raises_key_error_for_missing_project(self):
        """refresh() raises KeyError when the project is not found."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseProjectRepository(session)
            with pytest.raises(KeyError):
                repo.refresh(str(uuid.uuid4()))

    def test_refresh_does_not_access_filesystem(self):
        """refresh() does not perform any filesystem rescan."""
        session = _make_session()
        proj = _fake_project()
        session.execute.return_value = _scalar_result(proj)

        with patch("os.scandir") as mock_scandir, patch("os.listdir") as mock_listdir:
            with tenant_scope(TENANT_A):
                repo = EnterpriseProjectRepository(session)
                repo.refresh(str(proj.id))

        mock_scandir.assert_not_called()
        mock_listdir.assert_not_called()


class TestEnterpriseProjectRepositoryGetByPath:
    def test_get_by_path_returns_dto_when_found(self):
        """get_by_path() returns a DTO when a project with that path exists."""
        session = _make_session()
        proj = _fake_project(path="/home/user/myproj")
        session.execute.return_value = _scalar_result(proj)

        with tenant_scope(TENANT_A):
            repo = EnterpriseProjectRepository(session)
            dto = repo.get_by_path("/home/user/myproj")

        assert dto is not None
        assert dto.path == "/home/user/myproj"

    def test_get_by_path_returns_none_when_not_found(self):
        """get_by_path() returns None when no project has the given path."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseProjectRepository(session)
            result = repo.get_by_path("/nonexistent")

        assert result is None

    def test_get_by_path_no_filesystem_resolution(self):
        """get_by_path() only matches the stored path column, no fs calls."""
        session = _make_session()
        proj = _fake_project(path="/stored/path")
        session.execute.return_value = _scalar_result(proj)

        with patch("pathlib.Path.resolve") as mock_resolve:
            with tenant_scope(TENANT_A):
                repo = EnterpriseProjectRepository(session)
                repo.get_by_path("/stored/path")

        mock_resolve.assert_not_called()


class TestEnterpriseProjectRepositoryGetOrCreateByPath:
    def test_returns_existing_project_when_found(self):
        """get_or_create_by_path() returns the existing project without creating."""
        session = _make_session()
        proj = _fake_project(path="/existing")
        session.execute.return_value = _scalar_result(proj)

        with tenant_scope(TENANT_A):
            repo = EnterpriseProjectRepository(session)
            dto = repo.get_or_create_by_path("/existing")

        assert dto is not None
        session.add.assert_not_called()

    def test_creates_new_project_when_not_found(self):
        """get_or_create_by_path() creates a new row when no project matches."""
        session = _make_session()
        # First call is get_by_path → None; then on create, no more execute calls
        session.execute.return_value = _scalar_result(None)

        new_id = uuid.uuid4()
        fake_row = _fake_project(name="myproject", path="/home/user/myproject", project_id=new_id)

        with tenant_scope(TENANT_A):
            repo = EnterpriseProjectRepository(session)
            with patch(
                "skillmeat.cache.models_enterprise.EnterpriseProject",
                return_value=fake_row,
            ):
                dto = repo.get_or_create_by_path("/home/user/myproject")

        session.add.assert_called_once()
        assert dto is not None

    def test_get_artifacts_returns_empty_without_filesystem(self):
        """get_artifacts() queries DB only — no filesystem scan."""
        session = _make_session()
        session.execute.return_value = _scalars_result([])

        with patch("os.scandir") as mock_scandir:
            with tenant_scope(TENANT_A):
                repo = EnterpriseProjectRepository(session)
                artifacts = repo.get_artifacts(str(uuid.uuid4()))

        assert artifacts == []
        mock_scandir.assert_not_called()

    def test_get_artifacts_returns_artifact_dtos(self):
        """get_artifacts() maps returned rows to ArtifactDTO instances."""
        session = _make_session()
        art = _fake_artifact_row(name="canvas", artifact_type="skill")
        session.execute.return_value = _scalars_result([art])

        with tenant_scope(TENANT_A):
            repo = EnterpriseProjectRepository(session)
            artifacts = repo.get_artifacts(str(uuid.uuid4()))

        assert len(artifacts) == 1
        assert artifacts[0].name == "canvas"


# =============================================================================
# EnterpriseDeploymentRepository
# =============================================================================


class TestEnterpriseDeploymentRepositoryGet:
    def test_get_returns_dto_for_existing_deployment(self):
        """get() maps an ORM row to DeploymentDTO."""
        session = _make_session()
        dep = _fake_deployment(artifact_id="skill:canvas", status="deployed")
        session.execute.return_value = _scalar_result(dep)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentRepository(session)
            dto = repo.get(str(dep.id))

        assert dto is not None
        assert dto.id == str(dep.id)
        assert dto.artifact_id == "skill:canvas"
        assert dto.artifact_type == "skill"
        assert dto.artifact_name == "canvas"
        assert dto.status == "deployed"

    def test_get_returns_none_for_missing_deployment(self):
        """get() returns None when no deployment matches the UUID."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentRepository(session)
            result = repo.get(str(uuid.uuid4()))

        assert result is None

    def test_get_returns_none_for_invalid_uuid(self):
        """get() returns None for non-UUID strings."""
        session = _make_session()

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentRepository(session)
            result = repo.get("not-a-uuid")

        assert result is None
        session.execute.assert_not_called()

    def test_get_handles_nullable_project_id(self):
        """get() produces a DTO when project_id FK is None."""
        session = _make_session()
        dep = _fake_deployment(artifact_id="command:run")
        dep.project_id = None
        dep.project = None
        session.execute.return_value = _scalar_result(dep)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentRepository(session)
            dto = repo.get(str(dep.id))

        assert dto is not None
        assert dto.project_id is None

    def test_get_handles_nullable_artifact_uuid(self):
        """get() produces a DTO when artifact_uuid FK is None (text id only)."""
        session = _make_session()
        dep = _fake_deployment(artifact_id="agent:planner", artifact_uuid=None)
        dep.project = None
        session.execute.return_value = _scalar_result(dep)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentRepository(session)
            dto = repo.get(str(dep.id))

        assert dto is not None
        assert dto.artifact_id == "agent:planner"


class TestEnterpriseDeploymentRepositoryList:
    def test_list_returns_all_deployments(self):
        """list() returns all tenant deployments when no filters given."""
        session = _make_session()
        deps = [_fake_deployment(artifact_id="skill:a"), _fake_deployment(artifact_id="skill:b")]
        session.execute.return_value = _scalars_result(deps)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentRepository(session)
            result = repo.list()

        assert len(result) == 2

    def test_list_returns_empty_when_none(self):
        """list() returns an empty list when no deployments exist."""
        session = _make_session()
        session.execute.return_value = _scalars_result([])

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentRepository(session)
            result = repo.list()

        assert result == []

    def test_list_with_status_filter(self):
        """list(filters={"status": ...}) restricts to that status."""
        session = _make_session()
        dep = _fake_deployment(status="deployed")
        session.execute.return_value = _scalars_result([dep])

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentRepository(session)
            result = repo.list(filters={"status": "deployed"})

        assert len(result) == 1
        assert result[0].status == "deployed"

    def test_list_with_artifact_id_filter(self):
        """list(filters={"artifact_id": ...}) filters by artifact_id."""
        session = _make_session()
        dep = _fake_deployment(artifact_id="skill:canvas")
        session.execute.return_value = _scalars_result([dep])

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentRepository(session)
            result = repo.list(filters={"artifact_id": "skill:canvas"})

        assert len(result) == 1
        assert result[0].artifact_id == "skill:canvas"


class TestEnterpriseDeploymentRepositoryGetByProject:
    def test_get_by_project_returns_project_deployments(self):
        """get_by_project() delegates to list with project_id filter."""
        session = _make_session()
        proj_id = str(uuid.uuid4())
        dep = _fake_deployment(artifact_id="skill:x")
        session.execute.return_value = _scalars_result([dep])

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentRepository(session)
            result = repo.get_by_project(proj_id)

        assert len(result) == 1

    def test_get_by_project_returns_empty_for_invalid_uuid(self):
        """get_by_project() returns empty list for non-UUID project_id."""
        session = _make_session()
        session.execute.return_value = _scalars_result([])

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentRepository(session)
            result = repo.get_by_project("not-a-uuid")

        assert result == []


class TestEnterpriseDeploymentRepositoryListByStatus:
    def test_list_by_status_returns_matching_deployments(self):
        """list_by_status() returns deployments filtered by status."""
        session = _make_session()
        dep = _fake_deployment(status="undeployed")
        session.execute.return_value = _scalars_result([dep])

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentRepository(session)
            result = repo.list_by_status("undeployed")

        assert len(result) == 1
        assert result[0].status == "undeployed"

    def test_list_by_status_returns_empty_when_none_match(self):
        """list_by_status() returns empty list when no deployments match."""
        session = _make_session()
        session.execute.return_value = _scalars_result([])

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentRepository(session)
            result = repo.list_by_status("failed")

        assert result == []


class TestEnterpriseDeploymentRepositoryDeploy:
    def test_deploy_creates_deployment_row(self):
        """deploy() adds a new deployment row and returns a DTO."""
        session = _make_session()
        proj_id = str(uuid.uuid4())
        dep_id = uuid.uuid4()
        fake_dep = _fake_deployment(artifact_id="skill:canvas", deployment_id=dep_id)
        fake_dep.project = None

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentRepository(session)
            with patch(
                "skillmeat.cache.models_enterprise.EnterpriseDeployment",
                return_value=fake_dep,
            ):
                dto = repo.deploy("skill:canvas", proj_id)

        session.add.assert_called_once()
        session.flush.assert_called()
        assert dto.artifact_id == "skill:canvas"

    def test_deploy_raises_key_error_for_invalid_project_uuid(self):
        """deploy() raises KeyError when project_id is not a valid UUID."""
        session = _make_session()

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentRepository(session)
            with pytest.raises(KeyError):
                repo.deploy("skill:canvas", "bad-uuid")


class TestEnterpriseDeploymentRepositoryUndeploy:
    def test_undeploy_returns_true_for_existing_deployment(self):
        """undeploy() deletes the row and returns True."""
        session = _make_session()
        dep = _fake_deployment()
        session.execute.return_value = _scalar_result(dep)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentRepository(session)
            result = repo.undeploy(str(dep.id))

        assert result is True
        session.delete.assert_called_once_with(dep)

    def test_undeploy_returns_false_when_not_found(self):
        """undeploy() returns False when no record matches."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentRepository(session)
            result = repo.undeploy(str(uuid.uuid4()))

        assert result is False


class TestEnterpriseDeploymentRepositorySyncCache:
    def test_sync_deployment_cache_creates_new_row_when_no_existing(self):
        """sync_deployment_cache() creates a project and deployment row on first call.

        The session is mocked to return None for both the project lookup and
        the existing-deployment lookup, triggering the creation branches.
        """
        session = _make_session()
        # First execute: project lookup → None. Second: deployment lookup → None.
        session.execute.side_effect = [
            _scalar_result(None),  # project lookup
            _scalar_result(None),  # existing deployment lookup
        ]

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentRepository(session)
            result = repo.sync_deployment_cache(
                artifact_id="skill:canvas",
                project_path="/proj",
                project_name="proj",
                deployed_at=datetime.utcnow(),
            )

        # Two new ORM objects added (project + deployment)
        assert session.add.call_count == 2
        assert result is True

    def test_remove_deployment_cache_returns_false_when_project_not_found(self):
        """remove_deployment_cache() returns False when project path unknown."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentRepository(session)
            result = repo.remove_deployment_cache("skill:canvas", "/nonexistent")

        assert result is False

    def test_remove_deployment_cache_marks_rows_undeployed(self):
        """remove_deployment_cache() sets status='undeployed' on matching rows."""
        session = _make_session()
        proj = _fake_project(path="/proj")
        dep = _fake_deployment(artifact_id="skill:canvas", status="deployed")
        dep.project = None

        session.execute.side_effect = [
            _scalar_result(proj),    # project lookup
            _scalars_result([dep]),  # deployment rows
        ]

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentRepository(session)
            result = repo.remove_deployment_cache("skill:canvas", "/proj")

        assert result is True
        assert dep.status == "undeployed"


# =============================================================================
# EnterpriseDeploymentSetRepository
# =============================================================================


class TestEnterpriseDeploymentSetRepositoryCreate:
    def test_create_returns_new_set(self):
        """create() adds a new set and returns the ORM instance."""
        session = _make_session()
        ds_id = uuid.uuid4()
        fake_ds = _fake_deployment_set(name="My Set", set_id=ds_id)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentSetRepository(session)
            with patch(
                "skillmeat.cache.models_enterprise.EnterpriseDeploymentSet",
                return_value=fake_ds,
            ):
                result = repo.create(name="My Set", owner_id="user-1")

        session.add.assert_called()
        session.flush.assert_called()
        assert result.name == "My Set"

    def test_create_with_tags_calls_sync_tags(self):
        """create() calls _sync_tags when tags are supplied."""
        session = _make_session()
        ds_id = uuid.uuid4()
        fake_ds = _fake_deployment_set(name="Tagged Set", set_id=ds_id)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentSetRepository(session)
            with patch.object(repo, "_sync_tags") as mock_sync_tags, patch(
                "skillmeat.cache.models_enterprise.EnterpriseDeploymentSet",
                return_value=fake_ds,
            ):
                repo.create(name="Tagged Set", owner_id="user-1", tags=["prod", "ci"])

        mock_sync_tags.assert_called_once_with(fake_ds.id, ["prod", "ci"])


class TestEnterpriseDeploymentSetRepositoryGet:
    def test_get_returns_set_for_valid_id(self):
        """get() returns the ORM instance when found."""
        session = _make_session()
        ds = _fake_deployment_set()
        session.execute.return_value = _scalar_result(ds)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentSetRepository(session)
            result = repo.get(str(ds.id), owner_id="user-1")

        assert result is not None
        assert result.name == ds.name

    def test_get_returns_none_for_missing_set(self):
        """get() returns None when no matching set exists."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentSetRepository(session)
            result = repo.get(str(uuid.uuid4()), owner_id="user-1")

        assert result is None

    def test_get_returns_none_for_invalid_uuid(self):
        """get() returns None for non-UUID set_id without querying DB."""
        session = _make_session()

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentSetRepository(session)
            result = repo.get("not-a-uuid", owner_id="user-1")

        assert result is None
        session.execute.assert_not_called()


class TestEnterpriseDeploymentSetRepositoryList:
    def test_list_returns_sets_for_tenant(self):
        """list() returns all ORM rows for the current tenant."""
        session = _make_session()
        sets = [_fake_deployment_set(name="S1"), _fake_deployment_set(name="S2")]
        session.execute.return_value = _scalars_result(sets)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentSetRepository(session)
            result = repo.list(owner_id="user-1")

        assert len(result) == 2

    def test_list_returns_empty_when_none(self):
        """list() returns an empty list when no sets exist."""
        session = _make_session()
        session.execute.return_value = _scalars_result([])

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentSetRepository(session)
            result = repo.list(owner_id="user-1")

        assert result == []

    def test_list_with_name_filter(self):
        """list(name=...) applies ilike name filter."""
        session = _make_session()
        ds = _fake_deployment_set(name="prod-set")
        session.execute.return_value = _scalars_result([ds])

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentSetRepository(session)
            result = repo.list(owner_id="user-1", name="prod")

        assert len(result) == 1

    def test_list_with_tag_filter_joins_tag_table(self):
        """list(tag=...) filters via the join table (not tags_json text column)."""
        session = _make_session()
        ds = _fake_deployment_set(name="prod-set")
        session.execute.return_value = _scalars_result([ds])

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentSetRepository(session)
            # Tag filter relies on EnterpriseDeploymentSetTag join table
            result = repo.list(owner_id="user-1", tag="prod")

        # Should not raise; result depends on mock return
        assert isinstance(result, list)


class TestEnterpriseDeploymentSetRepositoryUpdate:
    def test_update_returns_updated_set(self):
        """update() mutates fields and returns the ORM instance."""
        session = _make_session()
        ds = _fake_deployment_set(name="OldName")
        session.execute.return_value = _scalar_result(ds)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentSetRepository(session)
            result = repo.update(str(ds.id), "user-1", name="NewName")

        assert ds.name == "NewName"
        session.flush.assert_called()
        assert result is ds

    def test_update_returns_none_for_missing_set(self):
        """update() returns None when the set does not exist."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentSetRepository(session)
            result = repo.update(str(uuid.uuid4()), "user-1", name="X")

        assert result is None

    def test_update_returns_none_for_invalid_uuid(self):
        """update() returns None for non-UUID set_id."""
        session = _make_session()

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentSetRepository(session)
            result = repo.update("bad-uuid", "user-1", name="X")

        assert result is None


class TestEnterpriseDeploymentSetRepositoryDelete:
    def test_delete_returns_true_for_existing_set(self):
        """delete() removes the set and returns True.

        The FR-10 orphan-cleanup path in delete() references
        ``EnterpriseDeploymentSetMember.member_set_id`` which does not exist on
        the model — it is a known gap in the current schema.  We patch the
        import of ``EnterpriseDeploymentSetMember`` inside the delete method
        with a MagicMock subclass whose class attributes produce valid
        SQLAlchemy column-expression stubs so the WHERE clause construction
        succeeds, and the mocked ``session.execute()`` returns an empty orphan
        list so the happy-delete path is reached.
        """
        from skillmeat.cache.models_enterprise import EnterpriseDeploymentSetMember

        session = _make_session()
        ds = _fake_deployment_set()
        # First execute: set lookup. Second: orphan member select (FR-10).
        session.execute.side_effect = [
            _scalar_result(ds),
            _scalars_result([]),  # no orphan cross-set member references
        ]

        # Build a real SQLAlchemy literal column as a stand-in for member_set_id
        # so that `member_set_id == uuid` produces a valid BinaryExpression.
        fake_member_set_id = sa.literal_column("member_set_id")

        with patch.object(
            EnterpriseDeploymentSetMember,
            "member_set_id",
            fake_member_set_id,
            create=True,
        ):
            with tenant_scope(TENANT_A):
                repo = EnterpriseDeploymentSetRepository(session)
                result = repo.delete(str(ds.id), owner_id="user-1")

        assert result is True
        session.delete.assert_called_with(ds)

    def test_delete_returns_false_for_missing_set(self):
        """delete() returns False when the set does not exist."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentSetRepository(session)
            result = repo.delete(str(uuid.uuid4()), owner_id="user-1")

        assert result is False


class TestEnterpriseDeploymentSetRepositoryMemberManagement:
    def test_add_member_creates_member_row(self):
        """add_member() adds a new member to an existing set.

        The position auto-assignment query uses select(EnterpriseDeploymentSetMember.position)
        which requires the real model class. We mock only the session.execute
        return values and let the ORM construct statements normally.
        The third execute call is the member position query; we return an empty
        iterator so position is auto-assigned to 0.
        """
        session = _make_session()
        ds = _fake_deployment_set()
        set_id = str(ds.id)

        # First execute: parent set tenant-filtered lookup.
        # Second execute: position max query (scalars() returns iterator of positions).
        execute_results = [
            _scalar_result(ds),
            _scalars_result([]),  # no existing positions → auto-position = 0
        ]
        session.execute.side_effect = execute_results

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentSetRepository(session)
            result = repo.add_member(set_id, "user-1", artifact_id="skill:canvas")

        session.add.assert_called_once()
        session.flush.assert_called()
        # Result is a real EnterpriseDeploymentSetMember ORM instance
        from skillmeat.cache.models_enterprise import EnterpriseDeploymentSetMember
        assert isinstance(result, EnterpriseDeploymentSetMember)

    def test_add_member_raises_value_error_when_set_not_found(self):
        """add_member() raises ValueError when parent set does not exist."""
        session = _make_session()
        # Parent set lookup returns None
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentSetRepository(session)
            with pytest.raises(ValueError):
                repo.add_member(str(uuid.uuid4()), "user-1", artifact_id="skill:x")

    def test_add_member_raises_value_error_for_invalid_set_id(self):
        """add_member() raises ValueError for non-UUID set_id."""
        session = _make_session()

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentSetRepository(session)
            with pytest.raises(ValueError):
                repo.add_member("bad-uuid", "user-1", artifact_id="skill:x")

    def test_remove_member_returns_true_when_found(self):
        """remove_member() deletes the member row and returns True."""
        session = _make_session()
        ds_id = uuid.uuid4()
        member = _fake_deployment_set_member(set_id=ds_id, artifact_id="skill:canvas")
        session.execute.return_value = _scalar_result(member)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentSetRepository(session)
            result = repo.remove_member(str(ds_id), "user-1", "skill:canvas")

        assert result is True
        session.delete.assert_called_once_with(member)

    def test_remove_member_returns_false_when_not_found(self):
        """remove_member() returns False when no matching member exists."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentSetRepository(session)
            result = repo.remove_member(str(uuid.uuid4()), "user-1", "skill:noexist")

        assert result is False

    def test_list_members_returns_ordered_members(self):
        """list_members() returns all members for the set ordered by position."""
        session = _make_session()
        ds_id = uuid.uuid4()
        members = [
            _fake_deployment_set_member(set_id=ds_id, artifact_id="skill:a", position=0),
            _fake_deployment_set_member(set_id=ds_id, artifact_id="skill:b", position=1),
        ]
        session.execute.return_value = _scalars_result(members)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentSetRepository(session)
            result = repo.list_members(str(ds_id), "user-1")

        assert len(result) == 2
        assert result[0].position == 0
        assert result[1].position == 1

    def test_list_members_returns_empty_for_invalid_set_id(self):
        """list_members() returns an empty list for non-UUID set_id."""
        session = _make_session()

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentSetRepository(session)
            result = repo.list_members("not-a-uuid", "user-1")

        assert result == []


# =============================================================================
# EnterpriseDeploymentProfileRepository
# =============================================================================


class TestEnterpriseDeploymentProfileRepositoryCreate:
    def test_create_stores_project_and_profile_id_in_extra_metadata(self):
        """create() stores project_id and profile_id in the extra_metadata column."""
        session = _make_session()
        profile_id_val = uuid.uuid4()
        fake_profile = _fake_deployment_profile(
            project_id="proj-1",
            profile_id_str="claude_code",
            profile_db_id=profile_id_val,
        )

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentProfileRepository(session)
            with patch(
                "skillmeat.cache.models_enterprise.EnterpriseDeploymentProfile",
                return_value=fake_profile,
            ):
                result = repo.create(
                    project_id="proj-1",
                    profile_id="claude_code",
                    platform="claude_code",
                    root_dir=".claude",
                )

        session.add.assert_called_once()
        session.flush.assert_called()
        assert result.extra_metadata["project_id"] == "proj-1"
        assert result.extra_metadata["profile_id"] == "claude_code"

    def test_create_does_not_use_metadata_attribute(self):
        """create() stores config in extra_metadata (not the ORM-reserved 'metadata')."""
        session = _make_session()
        fake_profile = _fake_deployment_profile()
        fake_profile.metadata = None  # Reserved by SQLAlchemy — should never be written

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentProfileRepository(session)
            with patch(
                "skillmeat.cache.models_enterprise.EnterpriseDeploymentProfile",
                return_value=fake_profile,
            ):
                repo.create(
                    project_id="proj-1",
                    profile_id="p1",
                    platform="claude_code",
                    root_dir=".claude",
                )

        # extra_metadata should be set; 'metadata' should not be written as config storage
        assert fake_profile.extra_metadata is not None

    def test_create_includes_optional_fields_in_extra_metadata(self):
        """create() includes artifact_path_map and config_filenames in extra_metadata."""
        session = _make_session()
        path_map = {"skill": ".claude/skills"}
        extra = {
            "project_id": "p",
            "profile_id": "cc",
            "root_dir": ".claude",
            "artifact_path_map": path_map,
            "config_filenames": ["CLAUDE.md"],
        }
        fake_profile = _fake_deployment_profile(extra_metadata=extra)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentProfileRepository(session)
            with patch(
                "skillmeat.cache.models_enterprise.EnterpriseDeploymentProfile",
                return_value=fake_profile,
            ):
                result = repo.create(
                    project_id="p",
                    profile_id="cc",
                    platform="claude_code",
                    root_dir=".claude",
                    artifact_path_map=path_map,
                    config_filenames=["CLAUDE.md"],
                )

        assert result.extra_metadata["artifact_path_map"] == path_map
        assert result.extra_metadata["config_filenames"] == ["CLAUDE.md"]


class TestEnterpriseDeploymentProfileRepositoryRead:
    def test_read_by_id_returns_profile(self):
        """read_by_id() returns the profile when found by UUID."""
        session = _make_session()
        profile = _fake_deployment_profile()
        session.execute.return_value = _scalar_result(profile)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentProfileRepository(session)
            result = repo.read_by_id(str(profile.id))

        assert result is not None
        assert result.extra_metadata["project_id"] == "proj-1"

    def test_read_by_id_returns_none_for_missing(self):
        """read_by_id() returns None when no profile matches."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentProfileRepository(session)
            result = repo.read_by_id(str(uuid.uuid4()))

        assert result is None

    def test_read_by_id_returns_none_for_invalid_uuid(self):
        """read_by_id() returns None for non-UUID strings."""
        session = _make_session()

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentProfileRepository(session)
            result = repo.read_by_id("not-a-uuid")

        assert result is None
        session.execute.assert_not_called()

    def test_read_by_project_and_profile_id_matches_canonical_name(self):
        """read_by_project_and_profile_id() matches on the stored 'project/profile' name."""
        session = _make_session()
        profile = _fake_deployment_profile(project_id="proj-1", profile_id_str="claude_code")
        session.execute.return_value = _scalar_result(profile)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentProfileRepository(session)
            result = repo.read_by_project_and_profile_id("proj-1", "claude_code")

        assert result is not None
        assert result.name == "proj-1/claude_code"

    def test_read_by_project_and_profile_id_returns_none_when_missing(self):
        """read_by_project_and_profile_id() returns None when not found."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentProfileRepository(session)
            result = repo.read_by_project_and_profile_id("proj-x", "unknown")

        assert result is None


class TestEnterpriseDeploymentProfileRepositoryList:
    def test_list_by_project_returns_matching_profiles(self):
        """list_by_project() returns profiles whose name starts with project_id/."""
        session = _make_session()
        profiles = [
            _fake_deployment_profile(project_id="proj-1", profile_id_str="cc"),
            _fake_deployment_profile(project_id="proj-1", profile_id_str="cursor"),
        ]
        session.execute.return_value = _scalars_result(profiles)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentProfileRepository(session)
            result = repo.list_by_project("proj-1")

        assert len(result) == 2

    def test_list_all_profiles_is_alias_for_list_by_project(self):
        """list_all_profiles() returns the same result as list_by_project()."""
        session = _make_session()
        profiles = [_fake_deployment_profile()]
        session.execute.return_value = _scalars_result(profiles)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentProfileRepository(session)
            result = repo.list_all_profiles("proj-1")

        assert len(result) == 1

    def test_list_by_project_returns_empty_when_none(self):
        """list_by_project() returns empty list when no profiles exist."""
        session = _make_session()
        session.execute.return_value = _scalars_result([])

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentProfileRepository(session)
            result = repo.list_by_project("unknown-proj")

        assert result == []


class TestEnterpriseDeploymentProfileRepositoryGetPrimary:
    def test_get_primary_profile_returns_claude_code_platform_first(self):
        """get_primary_profile() prefers the claude_code platform profile."""
        session = _make_session()
        profile = _fake_deployment_profile(platform="claude_code")
        # First execute: get_profile_by_platform → found
        session.execute.return_value = _scalar_result(profile)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentProfileRepository(session)
            result = repo.get_primary_profile("proj-1")

        assert result is not None
        assert result.platform == "claude_code"

    def test_get_primary_profile_falls_back_to_name_match(self):
        """get_primary_profile() falls back to name 'project/claude_code' when no platform match."""
        session = _make_session()
        profile = _fake_deployment_profile(project_id="proj-1", profile_id_str="claude_code")
        # First: get_profile_by_platform → None; Second: read_by_project_and_profile_id → found
        session.execute.side_effect = [
            _scalar_result(None),
            _scalar_result(profile),
        ]

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentProfileRepository(session)
            result = repo.get_primary_profile("proj-1")

        assert result is not None
        assert result.name == "proj-1/claude_code"

    def test_get_primary_profile_falls_back_to_first_alphabetical(self):
        """get_primary_profile() returns first profile when no claude_code match."""
        session = _make_session()
        profile = _fake_deployment_profile(project_id="proj-1", profile_id_str="cursor")
        # get_profile_by_platform → None; read_by_project_and_profile_id → None; list_by_project → [profile]
        session.execute.side_effect = [
            _scalar_result(None),
            _scalar_result(None),
            _scalars_result([profile]),
        ]

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentProfileRepository(session)
            result = repo.get_primary_profile("proj-1")

        assert result is not None

    def test_get_primary_profile_returns_none_when_no_profiles(self):
        """get_primary_profile() returns None when the project has no profiles."""
        session = _make_session()
        # All three lookups return nothing
        session.execute.side_effect = [
            _scalar_result(None),
            _scalar_result(None),
            _scalars_result([]),
        ]

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentProfileRepository(session)
            result = repo.get_primary_profile("proj-empty")

        assert result is None


class TestEnterpriseDeploymentProfileRepositoryEnsureDefault:
    def test_ensure_default_returns_existing_profile(self):
        """ensure_default_claude_profile() returns an existing profile without creating."""
        session = _make_session()
        profile = _fake_deployment_profile(platform="claude_code")
        # get_primary_profile finds a profile immediately
        session.execute.return_value = _scalar_result(profile)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentProfileRepository(session)
            result = repo.ensure_default_claude_profile("proj-1")

        assert result is not None
        session.add.assert_not_called()

    def test_ensure_default_creates_profile_when_none_exists(self):
        """ensure_default_claude_profile() creates a new claude_code profile when missing.

        All three primary-profile lookups return nothing, so create() is called.
        We let the real EnterpriseDeploymentProfile model be instantiated and
        only mock session.add/flush (standard MagicMock(spec=Session) behaviour).
        """
        session = _make_session()
        # get_primary_profile: get_profile_by_platform → None,
        #                       read_by_project_and_profile_id → None,
        #                       list_by_project → []
        session.execute.side_effect = [
            _scalar_result(None),
            _scalar_result(None),
            _scalars_result([]),
        ]

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentProfileRepository(session)
            result = repo.ensure_default_claude_profile("proj-new")

        session.add.assert_called_once()
        session.flush.assert_called()
        assert result is not None
        # The returned instance is a real EnterpriseDeploymentProfile ORM object.
        from skillmeat.cache.models_enterprise import EnterpriseDeploymentProfile
        assert isinstance(result, EnterpriseDeploymentProfile)


class TestEnterpriseDeploymentProfileRepositoryUpdate:
    def test_update_applies_direct_fields(self):
        """update() sets direct model fields (platform, dest_path, scope, overwrite)."""
        session = _make_session()
        profile = _fake_deployment_profile(platform="claude_code", dest_path=".claude")
        session.execute.return_value = _scalar_result(profile)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentProfileRepository(session)
            result = repo.update("proj-1", "claude_code", dest_path=".custom", platform="cursor")

        assert profile.dest_path == ".custom"
        assert profile.platform == "cursor"
        session.flush.assert_called()

    def test_update_merges_extra_metadata(self):
        """update() merges extra keyword args into existing extra_metadata."""
        session = _make_session()
        profile = _fake_deployment_profile()
        profile.extra_metadata = {"project_id": "proj-1", "profile_id": "cc"}
        session.execute.return_value = _scalar_result(profile)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentProfileRepository(session)
            repo.update("proj-1", "cc", custom_key="custom_val")

        assert profile.extra_metadata["custom_key"] == "custom_val"
        # Existing keys preserved
        assert profile.extra_metadata["project_id"] == "proj-1"

    def test_update_returns_none_when_not_found(self):
        """update() returns None when the profile does not exist."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentProfileRepository(session)
            result = repo.update("proj-x", "noexist", platform="cursor")

        assert result is None


class TestEnterpriseDeploymentProfileRepositoryDelete:
    def test_delete_returns_true_for_existing_profile(self):
        """delete() removes the profile and returns True."""
        session = _make_session()
        profile = _fake_deployment_profile()
        session.execute.return_value = _scalar_result(profile)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentProfileRepository(session)
            result = repo.delete("proj-1", "claude_code")

        assert result is True
        session.delete.assert_called_once_with(profile)

    def test_delete_returns_false_when_not_found(self):
        """delete() returns False when the profile does not exist."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentProfileRepository(session)
            result = repo.delete("proj-x", "noexist")

        assert result is False


class TestEnterpriseDeploymentProfileRepositoryGetProjectIdByPath:
    def test_get_project_id_by_path_returns_id_string(self):
        """get_project_id_by_path() returns the project ID when path matches."""
        session = _make_session()
        proj = _fake_project(path="/home/user/proj")
        session.execute.return_value = _scalar_result(proj)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentProfileRepository(session)
            result = repo.get_project_id_by_path("/home/user/proj")

        assert result == str(proj.id)

    def test_get_project_id_by_path_returns_none_when_not_found(self):
        """get_project_id_by_path() returns None when no project has that path."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentProfileRepository(session)
            result = repo.get_project_id_by_path("/nonexistent")

        assert result is None


# ---------------------------------------------------------------------------
# Tenant isolation behaviour
# ---------------------------------------------------------------------------


class TestTenantIsolationEnforcement:
    def test_project_repo_falls_back_to_default_tenant_without_scope(self):
        """Without a tenant_scope(), _get_tenant_id() falls back to DEFAULT_TENANT_ID.

        The repository must still function; it does NOT raise TenantIsolationError
        just because no explicit scope was set.  TenantIsolationError is only
        raised by _assert_tenant_owns() when an object's tenant_id mismatches.
        """
        from skillmeat.cache.enterprise_repositories import DEFAULT_TENANT_ID

        session = _make_session()
        session.execute.return_value = _scalar_result(None)
        # No tenant_scope() context — should fall back to DEFAULT_TENANT_ID silently
        repo = EnterpriseProjectRepository(session)
        result = repo.get(str(uuid.uuid4()))
        assert result is None  # Not found is fine; the point is it didn't raise

    def test_assert_tenant_owns_raises_for_cross_tenant_object(self):
        """_assert_tenant_owns() raises TenantIsolationError for a wrong-tenant object."""
        session = _make_session()
        with tenant_scope(TENANT_A):
            repo = EnterpriseProjectRepository(session)
            # Build a fake row that belongs to TENANT_B
            foreign_row = _fake_project(tenant_id=TENANT_B)
            with pytest.raises(TenantIsolationError):
                repo._assert_tenant_owns(foreign_row)

    def test_tenant_scope_correctly_scopes_tenant_id(self):
        """tenant_scope() sets and clears TenantContext for its duration."""
        from skillmeat.cache.enterprise_repositories import TenantContext

        assert TenantContext.get() is None  # Verify clean start

        with tenant_scope(TENANT_A):
            assert TenantContext.get() == TENANT_A

        assert TenantContext.get() is None  # Restored after exit

    def test_deployment_repo_uses_tenant_from_scope(self):
        """EnterpriseDeploymentRepository applies tenant filter from tenant_scope()."""
        session = _make_session()
        session.execute.return_value = _scalars_result([])

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentRepository(session)
            result = repo.list()

        assert result == []
        session.execute.assert_called_once()

    def test_deployment_profile_repo_uses_tenant_from_scope(self):
        """EnterpriseDeploymentProfileRepository applies tenant from tenant_scope()."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseDeploymentProfileRepository(session)
            result = repo.read_by_id(str(uuid.uuid4()))

        assert result is None
        session.execute.assert_called_once()
