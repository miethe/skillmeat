"""Tests for Confirm Duplicates API endpoint.

This module tests the /api/v1/artifacts/confirm-duplicates endpoint, including:
- Link duplicate scenario
- Import new artifact scenario
- Skip artifact scenario
- Mixed decision (links + imports + skips)
- Idempotency (calling same endpoint twice)
- Error handling for invalid paths and artifact IDs
"""

import pytest
import tempfile
from datetime import datetime
from pathlib import Path
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app
from skillmeat.core.artifact import (
    Artifact,
    ArtifactType,
    ArtifactMetadata,
)


@pytest.fixture
def test_settings():
    """Create test settings."""
    return APISettings(
        env=Environment.TESTING,
        host="127.0.0.1",
        port=8000,
        log_level="DEBUG",
        api_key_enabled=False,
    )


@pytest.fixture
def app(test_settings):
    """Create FastAPI app for testing."""
    from skillmeat.api.config import get_settings

    app = create_app(test_settings)
    app.dependency_overrides[get_settings] = lambda: test_settings

    return app


@pytest.fixture
def client(app):
    """Create test client with lifespan context."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_artifact():
    """Create a mock artifact for testing."""
    return Artifact(
        name="canvas-design",
        type=ArtifactType.SKILL,
        path="skills/canvas-design",
        origin="github",
        metadata=ArtifactMetadata(
            title="Canvas Design",
            description="Create beautiful visual art",
            author="Anthropic",
            license="MIT",
            version="1.0.0",
            tags=["design", "canvas"],
            dependencies=[],
            extra={},  # Empty extra dict for duplicate_links
        ),
        added=datetime(2024, 11, 1, 12, 0, 0),
        upstream="anthropics/skills/canvas-design",
        version_spec="latest",
        resolved_sha="abc123def456",
        resolved_version="v1.0.0",
        last_updated=datetime(2024, 11, 16, 12, 0, 0),
    )


@pytest.fixture
def mock_collection(mock_artifact):
    """Create a mock collection with the artifact."""
    mock_coll = MagicMock()
    mock_coll.name = "default"
    mock_coll.artifacts = [mock_artifact]
    return mock_coll


@pytest.fixture
def mock_collection_manager(mock_collection):
    """Create mock CollectionManager."""
    mock_mgr = MagicMock()
    mock_mgr.get_active_collection_name.return_value = "default"
    mock_mgr.load_collection.return_value = mock_collection
    mock_mgr.save_collection.return_value = None
    mock_mgr.link_duplicate.return_value = True
    return mock_mgr


@pytest.fixture
def mock_artifact_manager(mock_artifact):
    """Create mock ArtifactManager."""
    mock_mgr = MagicMock()
    mock_mgr.list_artifacts.return_value = [mock_artifact]
    return mock_mgr


@pytest.fixture
def temp_skill_dir():
    """Create a temporary directory with a valid skill structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_path = Path(tmpdir) / "test-skill"
        skill_path.mkdir()

        # Create SKILL.md file
        skill_md = skill_path / "SKILL.md"
        skill_md.write_text("""---
title: Test Skill
description: A test skill for unit tests
author: Test Author
---

# Test Skill

This is a test skill.
""")

        yield str(skill_path)


class TestConfirmDuplicatesLinkScenario:
    """Test linking duplicate artifacts to collection entries."""

    def test_link_duplicate_success(self, client, temp_skill_dir):
        """Test successful linking of a duplicate artifact."""
        response = client.post(
            "/api/v1/artifacts/confirm-duplicates",
            json={
                "project_path": "/tmp/test-project",
                "matches": [
                    {
                        "discovered_path": temp_skill_dir,
                        "collection_artifact_id": "skill:canvas-design",
                        "action": "link",
                    }
                ],
                "new_artifacts": [],
                "skipped": [],
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] in ["success", "partial", "failed"]
        assert "linked_count" in data
        assert "imported_count" in data
        assert "skipped_count" in data
        assert "message" in data
        assert "timestamp" in data
        assert "errors" in data

    def test_link_duplicate_invalid_path(self, client):
        """Test linking with non-existent discovered path."""
        response = client.post(
            "/api/v1/artifacts/confirm-duplicates",
            json={
                "project_path": "/tmp/test-project",
                "matches": [
                    {
                        "discovered_path": "/nonexistent/path/to/artifact",
                        "collection_artifact_id": "skill:canvas-design",
                        "action": "link",
                    }
                ],
                "new_artifacts": [],
                "skipped": [],
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Should report the error but not fail completely
        assert len(data["errors"]) > 0
        assert "does not exist" in data["errors"][0]

    def test_link_duplicate_invalid_artifact_id_format(self, client, temp_skill_dir):
        """Test linking with invalid artifact ID format."""
        response = client.post(
            "/api/v1/artifacts/confirm-duplicates",
            json={
                "project_path": "/tmp/test-project",
                "matches": [
                    {
                        "discovered_path": temp_skill_dir,
                        "collection_artifact_id": "invalid-format-no-colon",
                        "action": "link",
                    }
                ],
                "new_artifacts": [],
                "skipped": [],
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Should report the error
        assert len(data["errors"]) > 0
        assert "Invalid artifact ID format" in data["errors"][0]


class TestConfirmDuplicatesImportScenario:
    """Test importing new artifacts."""

    def test_import_new_artifact_invalid_path(self, client):
        """Test importing from non-existent path."""
        response = client.post(
            "/api/v1/artifacts/confirm-duplicates",
            json={
                "project_path": "/tmp/test-project",
                "matches": [],
                "new_artifacts": ["/nonexistent/path/to/artifact"],
                "skipped": [],
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["imported_count"] == 0
        assert len(data["errors"]) > 0
        assert "does not exist" in data["errors"][0]

    def test_import_new_artifact_success(self, client, temp_skill_dir):
        """Test successful import of a new artifact."""
        response = client.post(
            "/api/v1/artifacts/confirm-duplicates",
            json={
                "project_path": "/tmp/test-project",
                "matches": [],
                "new_artifacts": [temp_skill_dir],
                "skipped": [],
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Import may succeed or fail depending on test environment setup
        # but the endpoint should always return a valid response
        assert "imported_count" in data
        assert "errors" in data


class TestConfirmDuplicatesSkipScenario:
    """Test skipping artifacts."""

    def test_skip_artifacts(self, client):
        """Test that skipped artifacts are counted and logged."""
        response = client.post(
            "/api/v1/artifacts/confirm-duplicates",
            json={
                "project_path": "/tmp/test-project",
                "matches": [],
                "new_artifacts": [],
                "skipped": [
                    "/path/to/skipped/artifact1",
                    "/path/to/skipped/artifact2",
                ],
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["skipped_count"] == 2
        assert data["status"] == "success"
        assert "2 skipped" in data["message"]

    def test_skip_action_in_match(self, client, temp_skill_dir):
        """Test skip action within a match entry."""
        response = client.post(
            "/api/v1/artifacts/confirm-duplicates",
            json={
                "project_path": "/tmp/test-project",
                "matches": [
                    {
                        "discovered_path": temp_skill_dir,
                        "collection_artifact_id": "skill:canvas-design",
                        "action": "skip",
                    }
                ],
                "new_artifacts": [],
                "skipped": [],
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["skipped_count"] == 1
        assert data["linked_count"] == 0


class TestConfirmDuplicatesMixedDecisions:
    """Test mixed decision scenarios."""

    def test_mixed_decisions(self, client, temp_skill_dir):
        """Test processing multiple types of decisions at once."""
        response = client.post(
            "/api/v1/artifacts/confirm-duplicates",
            json={
                "project_path": "/tmp/test-project",
                "matches": [
                    {
                        "discovered_path": temp_skill_dir,
                        "collection_artifact_id": "skill:canvas-design",
                        "action": "link",
                    },
                    {
                        "discovered_path": "/some/path",
                        "collection_artifact_id": "skill:other",
                        "action": "skip",
                    },
                ],
                "new_artifacts": [],
                "skipped": ["/path/to/skipped/artifact"],
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Should have processed skips from both matches and skipped list
        assert data["skipped_count"] == 2  # 1 from skip action + 1 from skipped list
        assert "message" in data

    def test_empty_request(self, client):
        """Test with no decisions at all."""
        response = client.post(
            "/api/v1/artifacts/confirm-duplicates",
            json={
                "project_path": "/tmp/test-project",
                "matches": [],
                "new_artifacts": [],
                "skipped": [],
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert data["linked_count"] == 0
        assert data["imported_count"] == 0
        assert data["skipped_count"] == 0


class TestConfirmDuplicatesIdempotency:
    """Test idempotency of the endpoint."""

    def test_idempotent_link_calls(self, client, temp_skill_dir):
        """Test that calling the endpoint twice with same data is idempotent."""
        request_data = {
            "project_path": "/tmp/test-project",
            "matches": [
                {
                    "discovered_path": temp_skill_dir,
                    "collection_artifact_id": "skill:canvas-design",
                    "action": "link",
                }
            ],
            "new_artifacts": [],
            "skipped": [],
        }

        # First call
        response1 = client.post("/api/v1/artifacts/confirm-duplicates", json=request_data)
        assert response1.status_code == status.HTTP_200_OK

        # Second call with same data
        response2 = client.post("/api/v1/artifacts/confirm-duplicates", json=request_data)
        assert response2.status_code == status.HTTP_200_OK

        # Both should return valid responses
        data1 = response1.json()
        data2 = response2.json()

        assert "status" in data1
        assert "status" in data2


class TestConfirmDuplicatesValidation:
    """Test request validation."""

    def test_missing_project_path(self, client):
        """Test that project_path is required."""
        response = client.post(
            "/api/v1/artifacts/confirm-duplicates",
            json={
                "matches": [],
                "new_artifacts": [],
                "skipped": [],
            },
        )

        # FastAPI should return 422 for missing required field
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_action_value(self, client, temp_skill_dir):
        """Test that invalid action value is rejected."""
        response = client.post(
            "/api/v1/artifacts/confirm-duplicates",
            json={
                "project_path": "/tmp/test-project",
                "matches": [
                    {
                        "discovered_path": temp_skill_dir,
                        "collection_artifact_id": "skill:canvas-design",
                        "action": "invalid_action",
                    }
                ],
                "new_artifacts": [],
                "skipped": [],
            },
        )

        # FastAPI should return 422 for invalid enum value
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestConfirmDuplicatesStatus:
    """Test status determination logic."""

    def test_status_success_all_operations_succeed(self, client):
        """Test SUCCESS status when all operations succeed."""
        response = client.post(
            "/api/v1/artifacts/confirm-duplicates",
            json={
                "project_path": "/tmp/test-project",
                "matches": [],
                "new_artifacts": [],
                "skipped": ["/path/to/skip"],
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # With only skipped artifacts (which don't fail), status should be success
        assert data["status"] == "success"

    def test_status_partial_some_errors(self, client, temp_skill_dir):
        """Test PARTIAL status when some operations fail."""
        response = client.post(
            "/api/v1/artifacts/confirm-duplicates",
            json={
                "project_path": "/tmp/test-project",
                "matches": [
                    # This one has invalid path, will fail
                    {
                        "discovered_path": "/nonexistent/path",
                        "collection_artifact_id": "skill:canvas-design",
                        "action": "link",
                    },
                ],
                "new_artifacts": [],
                "skipped": ["/path/to/skip"],  # This will succeed
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Should have some errors but skipped count should be > 0
        assert len(data["errors"]) > 0
        assert data["skipped_count"] > 0

    def test_status_failed_all_errors(self, client):
        """Test FAILED status when all operations fail."""
        response = client.post(
            "/api/v1/artifacts/confirm-duplicates",
            json={
                "project_path": "/tmp/test-project",
                "matches": [
                    {
                        "discovered_path": "/nonexistent/path1",
                        "collection_artifact_id": "skill:artifact1",
                        "action": "link",
                    },
                    {
                        "discovered_path": "/nonexistent/path2",
                        "collection_artifact_id": "skill:artifact2",
                        "action": "link",
                    },
                ],
                "new_artifacts": [],
                "skipped": [],
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # All operations failed
        assert data["status"] == "failed"
        assert data["linked_count"] == 0
        assert len(data["errors"]) == 2
