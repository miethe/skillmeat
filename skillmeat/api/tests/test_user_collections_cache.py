"""Tests for user collections cache refresh endpoints.

Tests for:
- POST /api/v1/user-collections/{collection_id}/refresh-cache (scoped)
- POST /api/v1/user-collections/refresh-cache (batch)
"""

import json
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings
from skillmeat.api.server import create_app
from skillmeat.cache.models import Collection, CollectionArtifact
from skillmeat.core.artifact import Artifact, ArtifactMetadata, ArtifactType


@pytest.fixture
def api_settings():
    """Create test API settings with auth disabled."""
    return APISettings(
        env="testing",
        api_key_enabled=False,
        cors_enabled=True,
    )


@pytest.fixture
def client(api_settings):
    """Create test client with initialized app state."""
    from skillmeat.api.dependencies import app_state

    app = create_app(api_settings)
    app_state.initialize(api_settings)

    client = TestClient(app)

    yield client

    app_state.shutdown()


@pytest.fixture
def mock_collection():
    """Create a mock Collection ORM instance."""
    collection = MagicMock(spec=Collection)
    collection.id = uuid.uuid4().hex
    collection.name = "Test Collection"
    collection.description = "A test collection"
    collection.created_at = datetime.utcnow()
    collection.updated_at = datetime.utcnow()
    return collection


@pytest.fixture
def mock_collection_artifacts(mock_collection):
    """Create mock CollectionArtifact instances."""
    artifacts = []
    for i in range(3):
        ca = MagicMock(spec=CollectionArtifact)
        ca.collection_id = mock_collection.id
        ca.artifact_id = f"skill:test-skill-{i}"
        ca.added_at = datetime.utcnow()
        ca.description = None
        ca.author = None
        ca.license = None
        ca.tags_json = None
        ca.version = None
        ca.source = None
        ca.origin = None
        ca.origin_source = None
        ca.resolved_sha = None
        ca.resolved_version = None
        ca.synced_at = None
        artifacts.append(ca)
    return artifacts


@pytest.fixture
def mock_file_artifact():
    """Create a mock file-based Artifact."""
    metadata = ArtifactMetadata(
        title="Test Skill",
        description="A test skill description",
        author="Test Author",
        license="MIT",
        version="1.0.0",
        tags=["test", "skill"],
    )
    artifact = Artifact(
        name="test-skill-0",
        type=ArtifactType.SKILL,
        path="skills/test-skill-0",
        origin="github",
        upstream="anthropics/skills/test-skill-0",
        version_spec="latest",
        resolved_sha="abc123def456",
        resolved_version="v1.0.0",
        added=datetime.utcnow(),
        last_updated=datetime.utcnow(),
        metadata=metadata,
        tags=["test"],
    )
    return artifact


class TestRefreshCollectionCache:
    """Tests for POST /user-collections/{collection_id}/refresh-cache endpoint."""

    def test_refresh_cache_success(
        self, client, mock_collection, mock_collection_artifacts, mock_file_artifact
    ):
        """Test successful cache refresh for a collection."""
        collection_id = mock_collection.id

        with patch(
            "skillmeat.api.routers.user_collections.get_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            # Configure session.query to return collection and artifacts
            mock_collection_query = MagicMock()
            mock_collection_query.filter_by.return_value.first.return_value = (
                mock_collection
            )

            mock_artifacts_query = MagicMock()
            mock_artifacts_query.filter_by.return_value.all.return_value = (
                mock_collection_artifacts
            )

            def query_side_effect(model):
                if model == Collection:
                    return mock_collection_query
                elif model == CollectionArtifact:
                    return mock_artifacts_query
                return MagicMock()

            mock_session.query.side_effect = query_side_effect

            with patch(
                "skillmeat.api.dependencies.app_state.artifact_manager"
            ) as mock_art_mgr:
                # Return file artifact for the lookup
                mock_art_mgr.show.return_value = mock_file_artifact

                response = client.post(
                    f"/api/v1/user-collections/{collection_id}/refresh-cache"
                )

                assert response.status_code == 200
                data = response.json()
                assert data["collection_id"] == collection_id
                assert data["updated_count"] == 3
                assert data["skipped_count"] == 0
                assert data["errors"] == []

    def test_refresh_cache_collection_not_found(self, client):
        """Test 404 when collection doesn't exist."""
        non_existent_id = uuid.uuid4().hex

        with patch(
            "skillmeat.api.routers.user_collections.get_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            # Collection not found
            mock_query = MagicMock()
            mock_query.filter_by.return_value.first.return_value = None
            mock_session.query.return_value = mock_query

            response = client.post(
                f"/api/v1/user-collections/{non_existent_id}/refresh-cache"
            )

            assert response.status_code == 404
            data = response.json()
            assert data["detail"]["error"] == "collection_not_found"
            assert non_existent_id in data["detail"]["message"]

    def test_refresh_cache_partial_failure(
        self, client, mock_collection, mock_collection_artifacts, mock_file_artifact
    ):
        """Test that partial failures don't crash the endpoint."""
        collection_id = mock_collection.id

        with patch(
            "skillmeat.api.routers.user_collections.get_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            mock_collection_query = MagicMock()
            mock_collection_query.filter_by.return_value.first.return_value = (
                mock_collection
            )

            mock_artifacts_query = MagicMock()
            mock_artifacts_query.filter_by.return_value.all.return_value = (
                mock_collection_artifacts
            )

            def query_side_effect(model):
                if model == Collection:
                    return mock_collection_query
                elif model == CollectionArtifact:
                    return mock_artifacts_query
                return MagicMock()

            mock_session.query.side_effect = query_side_effect

            with patch(
                "skillmeat.api.dependencies.app_state.artifact_manager"
            ) as mock_art_mgr:
                # First call succeeds, second raises exception, third succeeds
                call_count = [0]

                def show_side_effect(*args, **kwargs):
                    call_count[0] += 1
                    if call_count[0] == 2:
                        raise Exception("File system error")
                    return mock_file_artifact

                mock_art_mgr.show.side_effect = show_side_effect

                response = client.post(
                    f"/api/v1/user-collections/{collection_id}/refresh-cache"
                )

                assert response.status_code == 200
                data = response.json()
                assert data["collection_id"] == collection_id
                # 2 succeeded, 1 failed
                assert data["updated_count"] == 2
                assert data["skipped_count"] == 1
                assert len(data["errors"]) == 1
                assert "test-skill-1" in data["errors"][0]

    def test_refresh_cache_empty_collection(self, client, mock_collection):
        """Test refresh with no artifacts in collection."""
        collection_id = mock_collection.id

        with patch(
            "skillmeat.api.routers.user_collections.get_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            mock_collection_query = MagicMock()
            mock_collection_query.filter_by.return_value.first.return_value = (
                mock_collection
            )

            mock_artifacts_query = MagicMock()
            # Empty collection - no artifacts
            mock_artifacts_query.filter_by.return_value.all.return_value = []

            def query_side_effect(model):
                if model == Collection:
                    return mock_collection_query
                elif model == CollectionArtifact:
                    return mock_artifacts_query
                return MagicMock()

            mock_session.query.side_effect = query_side_effect

            response = client.post(
                f"/api/v1/user-collections/{collection_id}/refresh-cache"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["collection_id"] == collection_id
            assert data["updated_count"] == 0
            assert data["skipped_count"] == 0
            assert data["errors"] == []

    def test_refresh_cache_artifact_not_in_filesystem(
        self, client, mock_collection, mock_collection_artifacts
    ):
        """Test refresh when artifact exists in DB but not filesystem."""
        collection_id = mock_collection.id

        with patch(
            "skillmeat.api.routers.user_collections.get_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            mock_collection_query = MagicMock()
            mock_collection_query.filter_by.return_value.first.return_value = (
                mock_collection
            )

            mock_artifacts_query = MagicMock()
            mock_artifacts_query.filter_by.return_value.all.return_value = (
                mock_collection_artifacts
            )

            def query_side_effect(model):
                if model == Collection:
                    return mock_collection_query
                elif model == CollectionArtifact:
                    return mock_artifacts_query
                return MagicMock()

            mock_session.query.side_effect = query_side_effect

            with patch(
                "skillmeat.api.dependencies.app_state.artifact_manager"
            ) as mock_art_mgr:
                # Artifact not found in filesystem
                mock_art_mgr.show.return_value = None

                response = client.post(
                    f"/api/v1/user-collections/{collection_id}/refresh-cache"
                )

                assert response.status_code == 200
                data = response.json()
                assert data["updated_count"] == 0
                # All skipped because not found in filesystem
                assert data["skipped_count"] == 3


class TestRefreshAllCollectionsCache:
    """Tests for POST /user-collections/refresh-cache endpoint."""

    def test_refresh_all_success(
        self, client, mock_collection, mock_collection_artifacts, mock_file_artifact
    ):
        """Test successful batch refresh."""
        # Create second collection
        mock_collection_2 = MagicMock(spec=Collection)
        mock_collection_2.id = uuid.uuid4().hex
        mock_collection_2.name = "Second Collection"

        with patch(
            "skillmeat.api.routers.user_collections.get_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            # Return list of collections
            mock_query = MagicMock()
            mock_query.all.return_value = [mock_collection, mock_collection_2]
            mock_session.query.return_value = mock_query

            with patch(
                "skillmeat.api.routers.user_collections._refresh_single_collection_cache"
            ) as mock_refresh:
                # Return success for both collections
                mock_refresh.side_effect = [
                    {
                        "collection_id": mock_collection.id,
                        "updated": 2,
                        "skipped": 1,
                        "errors": [],
                    },
                    {
                        "collection_id": mock_collection_2.id,
                        "updated": 3,
                        "skipped": 0,
                        "errors": [],
                    },
                ]

                response = client.post("/api/v1/user-collections/refresh-cache")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["collections_refreshed"] == 2
                assert data["total_updated"] == 5
                assert data["total_skipped"] == 1
                assert data["errors"] == []
                assert "duration_seconds" in data

    def test_refresh_all_empty_database(self, client):
        """Test batch refresh with no collections."""
        with patch(
            "skillmeat.api.routers.user_collections.get_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            # No collections in database
            mock_query = MagicMock()
            mock_query.all.return_value = []
            mock_session.query.return_value = mock_query

            response = client.post("/api/v1/user-collections/refresh-cache")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["collections_refreshed"] == 0
            assert data["total_updated"] == 0
            assert data["total_skipped"] == 0
            assert data["errors"] == []
            assert data["duration_seconds"] == 0.0

    def test_refresh_all_partial_failure(self, client, mock_collection):
        """Test batch refresh continues on individual collection failures."""
        mock_collection_2 = MagicMock(spec=Collection)
        mock_collection_2.id = uuid.uuid4().hex
        mock_collection_2.name = "Failing Collection"

        mock_collection_3 = MagicMock(spec=Collection)
        mock_collection_3.id = uuid.uuid4().hex
        mock_collection_3.name = "Third Collection"

        with patch(
            "skillmeat.api.routers.user_collections.get_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            mock_query = MagicMock()
            mock_query.all.return_value = [
                mock_collection,
                mock_collection_2,
                mock_collection_3,
            ]
            mock_session.query.return_value = mock_query

            with patch(
                "skillmeat.api.routers.user_collections._refresh_single_collection_cache"
            ) as mock_refresh:
                # First succeeds, second fails, third succeeds
                def refresh_side_effect(session, collection, artifact_mgr):
                    if collection.id == mock_collection_2.id:
                        raise Exception("Database connection error")
                    return {
                        "collection_id": collection.id,
                        "updated": 2,
                        "skipped": 0,
                        "errors": [],
                    }

                mock_refresh.side_effect = refresh_side_effect

                response = client.post("/api/v1/user-collections/refresh-cache")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                # Only 2 collections refreshed (1 failed)
                assert data["collections_refreshed"] == 2
                assert data["total_updated"] == 4
                # Errors include the failed collection
                assert len(data["errors"]) == 1
                assert data["errors"][0]["collection_id"] == mock_collection_2.id
                assert "Database connection error" in data["errors"][0]["errors"][0]

    def test_refresh_all_with_artifact_errors(self, client, mock_collection):
        """Test batch refresh reports per-collection artifact errors."""
        with patch(
            "skillmeat.api.routers.user_collections.get_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            mock_query = MagicMock()
            mock_query.all.return_value = [mock_collection]
            mock_session.query.return_value = mock_query

            with patch(
                "skillmeat.api.routers.user_collections._refresh_single_collection_cache"
            ) as mock_refresh:
                # Return result with artifact-level errors
                mock_refresh.return_value = {
                    "collection_id": mock_collection.id,
                    "updated": 2,
                    "skipped": 1,
                    "errors": ["Failed to refresh skill:broken-skill: File not found"],
                }

                response = client.post("/api/v1/user-collections/refresh-cache")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["collections_refreshed"] == 1
                assert data["total_updated"] == 2
                assert data["total_skipped"] == 1
                # Artifact-level errors are aggregated
                assert len(data["errors"]) == 1
                assert data["errors"][0]["collection_id"] == mock_collection.id
                assert "broken-skill" in data["errors"][0]["errors"][0]


class TestRefreshCacheIntegration:
    """Integration tests for cache refresh functionality."""

    def test_refresh_updates_cache_fields(
        self, client, mock_collection, mock_file_artifact
    ):
        """Test that refresh properly updates all cache fields on CollectionArtifact."""
        collection_id = mock_collection.id

        # Create a single CollectionArtifact that will be updated
        ca = MagicMock(spec=CollectionArtifact)
        ca.collection_id = collection_id
        ca.artifact_id = "skill:test-skill-0"
        ca.description = None
        ca.author = None
        ca.license = None
        ca.tags_json = None
        ca.version = None
        ca.source = None
        ca.origin = None
        ca.origin_source = None
        ca.resolved_sha = None
        ca.resolved_version = None
        ca.synced_at = None

        with patch(
            "skillmeat.api.routers.user_collections.get_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            mock_collection_query = MagicMock()
            mock_collection_query.filter_by.return_value.first.return_value = (
                mock_collection
            )

            mock_artifacts_query = MagicMock()
            mock_artifacts_query.filter_by.return_value.all.return_value = [ca]

            def query_side_effect(model):
                if model == Collection:
                    return mock_collection_query
                elif model == CollectionArtifact:
                    return mock_artifacts_query
                return MagicMock()

            mock_session.query.side_effect = query_side_effect

            with patch(
                "skillmeat.api.dependencies.app_state.artifact_manager"
            ) as mock_art_mgr:
                mock_art_mgr.show.return_value = mock_file_artifact

                response = client.post(
                    f"/api/v1/user-collections/{collection_id}/refresh-cache"
                )

                assert response.status_code == 200

                # Verify all cache fields were set on the CollectionArtifact
                assert ca.description == "A test skill description"
                assert ca.author == "Test Author"
                assert ca.license == "MIT"
                assert ca.tags_json == json.dumps(["test", "skill"])
                assert ca.version == "1.0.0"
                assert ca.source == "anthropics/skills/test-skill-0"
                assert ca.origin == "github"
                assert ca.resolved_sha == "abc123def456"
                assert ca.resolved_version == "v1.0.0"
                assert ca.synced_at is not None
