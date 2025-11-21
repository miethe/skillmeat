import pytest
from fastapi import status
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app
from skillmeat.api.routers import sync as sync_router
from skillmeat.models import SyncJobRecord, SyncJobState


class FakeJobService:
    def __init__(self):
        self.jobs = {}

    def create_job(self, **kwargs):
        job = SyncJobRecord(
            id="job123",
            direction=kwargs.get("direction", ""),
            artifacts=kwargs.get("artifacts") or [],
            artifact_type=kwargs.get("artifact_type"),
            project_path=kwargs.get("project_path"),
            collection=kwargs.get("collection"),
            strategy=kwargs.get("strategy"),
            resolution=kwargs.get("resolution"),
            dry_run=kwargs.get("dry_run", False),
            state=SyncJobState.QUEUED,
        )
        self.jobs[job.id] = job
        return job

    def get_job(self, job_id: str):
        return self.jobs.get(job_id)


@pytest.fixture
def test_settings():
    return APISettings(
        env=Environment.TESTING,
        host="127.0.0.1",
        port=8000,
        log_level="DEBUG",
        cors_enabled=True,
        cors_origins=["http://localhost:3000"],
        api_key_enabled=False,
    )


@pytest.fixture
def app(test_settings):
    from skillmeat.api.config import get_settings

    app = create_app(test_settings)
    app.dependency_overrides[get_settings] = lambda: test_settings
    fake_service = FakeJobService()
    app.dependency_overrides[sync_router.get_job_service] = lambda: fake_service
    return app


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


def test_job_requires_project_path_for_collection_to_project(client):
    resp = client.post(
        "/api/v1/sync/jobs",
        json={"direction": "collection_to_project"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "project_path" in resp.json()["detail"]


def test_job_requires_valid_resolution_for_resolve(client):
    resp = client.post(
        "/api/v1/sync/jobs",
        json={
            "direction": "resolve",
            "project_path": "/tmp/project",
            "artifacts": ["demo"],
            "resolution": "invalid",
        },
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "resolution" in resp.json()["detail"]


def test_get_job_status_not_found(client):
    resp = client.get("/api/v1/sync/jobs/does-not-exist")
    assert resp.status_code == status.HTTP_404_NOT_FOUND
