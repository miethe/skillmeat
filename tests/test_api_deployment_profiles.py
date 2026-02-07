"""Integration tests for deployment profile API endpoints."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app
from skillmeat.cache.models import Project, create_db_engine, create_tables
from skillmeat.cache.repositories import DeploymentProfileRepository


@pytest.fixture
def temp_db():
    """Temporary database path for deployment profile API tests."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    try:
        Path(db_path).unlink()
    except FileNotFoundError:
        pass


@pytest.fixture
def app(temp_db, monkeypatch):
    """Create app with deployment profile repository bound to a temp DB."""
    from skillmeat.api.config import get_settings
    from skillmeat.api.middleware.auth import verify_token
    from skillmeat.api.routers import deployment_profiles

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
    session = SessionLocal()
    try:
        session.add(
            Project(
                id="proj-api-1",
                name="API Project",
                path="/tmp/proj-api-1",
                status="active",
            )
        )
        session.commit()
    finally:
        session.close()
        engine.dispose()

    repo = DeploymentProfileRepository(db_path=temp_db)
    monkeypatch.setattr(deployment_profiles, "DeploymentProfileRepository", lambda: repo)

    return app


@pytest.fixture
def client(app):
    """Create API test client."""
    with TestClient(app) as test_client:
        yield test_client


def test_deployment_profile_crud_endpoints(client):
    """CRUD endpoints should support deployment profile lifecycle."""
    payload = {
        "profile_id": "codex-default",
        "platform": "codex",
        "root_dir": ".codex",
        "artifact_path_map": {"skill": "skills"},
        "project_config_filenames": ["CODEX.md"],
        "context_path_prefixes": [".codex/context/"],
        "supported_artifact_types": ["skill", "command"],
    }

    create_resp = client.post("/api/v1/projects/proj-api-1/profiles", json=payload)
    assert create_resp.status_code == status.HTTP_201_CREATED
    created = create_resp.json()
    assert created["profile_id"] == "codex-default"
    assert created["platform"] == "codex"

    list_resp = client.get("/api/v1/projects/proj-api-1/profiles")
    assert list_resp.status_code == status.HTTP_200_OK
    listed = list_resp.json()
    assert len(listed) == 1
    assert listed[0]["profile_id"] == "codex-default"

    get_resp = client.get("/api/v1/projects/proj-api-1/profiles/codex-default")
    assert get_resp.status_code == status.HTTP_200_OK
    assert get_resp.json()["root_dir"] == ".codex"

    update_resp = client.put(
        "/api/v1/projects/proj-api-1/profiles/codex-default",
        json={"root_dir": ".codex-custom", "supported_artifact_types": ["skill"]},
    )
    assert update_resp.status_code == status.HTTP_200_OK
    updated = update_resp.json()
    assert updated["root_dir"] == ".codex-custom"
    assert updated["supported_artifact_types"] == ["skill"]

    delete_resp = client.delete("/api/v1/projects/proj-api-1/profiles/codex-default")
    assert delete_resp.status_code == status.HTTP_204_NO_CONTENT

    missing_resp = client.get("/api/v1/projects/proj-api-1/profiles/codex-default")
    assert missing_resp.status_code == status.HTTP_404_NOT_FOUND
