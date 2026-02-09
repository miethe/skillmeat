"""API tests for context entity deployment endpoint."""

from __future__ import annotations

import tempfile
import shutil
from pathlib import Path

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app
from skillmeat.cache.models import Project, create_db_engine, create_tables
from skillmeat.cache.repositories import DeploymentProfileRepository
from skillmeat.core.enums import Platform


@pytest.fixture
def temp_db():
    """Create temporary sqlite DB path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    try:
        Path(db_path).unlink()
    except FileNotFoundError:
        pass


@pytest.fixture
def app(temp_db, monkeypatch):
    """Create API app with context-entities router bound to temp DB."""
    from skillmeat.api.config import get_settings
    from skillmeat.api.routers import context_entities
    from skillmeat.api.middleware.auth import verify_token

    settings = APISettings(
        env=Environment.TESTING,
        api_key_enabled=False,
    )
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[verify_token] = lambda: "test-token"

    create_tables(temp_db)
    engine = create_db_engine(temp_db)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def _get_session():
        return SessionLocal()

    monkeypatch.setattr(context_entities, "get_session", _get_session)
    monkeypatch.setattr(
        context_entities,
        "DeploymentProfileRepository",
        lambda: DeploymentProfileRepository(db_path=temp_db),
    )

    session = SessionLocal()
    try:
        project_path = Path(tempfile.gettempdir()) / "skillmeat-context-deploy-test-project"
        session.add(
            Project(
                id="proj-ctx-deploy",
                name=project_path.name,
                path=str(project_path.resolve()),
                status="active",
            )
        )
        session.commit()
    finally:
        session.close()
        engine.dispose()

    return app


@pytest.fixture
def client(app):
    """Create API test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def project_path():
    """Create temp project directory for deployment target."""
    project = Path(tempfile.gettempdir()) / "skillmeat-context-deploy-test-project"
    if project.exists():
        shutil.rmtree(project)
    project.mkdir(parents=True, exist_ok=True)
    return project


def _create_context_entity(client: TestClient, *, target_platforms=None) -> str:
    payload = {
        "name": "ctx-api-rules",
        "entity_type": "rule_file",
        "content": "# API Rules\n\nUse typed handlers.",
        "path_pattern": ".claude/rules/api.md",
        "auto_load": True,
    }
    if target_platforms is not None:
        payload["target_platforms"] = target_platforms

    response = client.post("/api/v1/context-entities", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["id"]


def test_deploy_context_entity_rewrites_to_selected_profile(client, project_path):
    """Deploy should rewrite .claude path_pattern to selected profile root."""
    entity_id = _create_context_entity(client)

    response = client.post(
        f"/api/v1/context-entities/{entity_id}/deploy",
        json={
            "project_path": str(project_path),
            "deployment_profile_id": "codex",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["success"] is True
    assert body["deployed_profiles"] == ["codex"]
    assert body["deployed_paths"] == [".codex/rules/api.md"]

    deployed_file = project_path / ".codex" / "rules" / "api.md"
    assert deployed_file.exists()
    assert "API Rules" in deployed_file.read_text(encoding="utf-8")


def test_deploy_context_entity_all_profiles(client, project_path, temp_db):
    """all_profiles should deploy once for each configured profile."""
    entity_id = _create_context_entity(client)

    repo = DeploymentProfileRepository(db_path=temp_db)
    repo.create(
        project_id="proj-ctx-deploy",
        profile_id="claude_code",
        platform=Platform.CLAUDE_CODE.value,
        root_dir=".claude",
        artifact_path_map={},
        config_filenames=["CLAUDE.md"],
        context_prefixes=[".claude/context/", ".claude/"],
        supported_types=["rule_file"],
    )
    repo.create(
        project_id="proj-ctx-deploy",
        profile_id="codex-default",
        platform=Platform.CODEX.value,
        root_dir=".codex",
        artifact_path_map={},
        config_filenames=["CODEX.md"],
        context_prefixes=[".codex/context/", ".codex/"],
        supported_types=["rule_file"],
    )

    response = client.post(
        f"/api/v1/context-entities/{entity_id}/deploy",
        json={
            "project_path": str(project_path),
            "all_profiles": True,
            "overwrite": True,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert sorted(body["deployed_profiles"]) == ["claude_code", "codex-default"]
    assert sorted(body["deployed_paths"]) == [".claude/rules/api.md", ".codex/rules/api.md"]
    assert (project_path / ".claude" / "rules" / "api.md").exists()
    assert (project_path / ".codex" / "rules" / "api.md").exists()


def test_deploy_context_entity_rejects_platform_mismatch_without_force(client, project_path):
    """Deploy should fail when target_platforms exclude selected profile platform."""
    entity_id = _create_context_entity(client, target_platforms=["claude_code"])

    response = client.post(
        f"/api/v1/context-entities/{entity_id}/deploy",
        json={
            "project_path": str(project_path),
            "deployment_profile_id": "codex",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "target_platforms" in response.json()["detail"]
