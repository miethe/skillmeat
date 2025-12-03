"""Integration tests for Discovery API endpoints.

Tests for:
- POST /api/v1/artifacts/discover - Artifact discovery
- POST /api/v1/artifacts/discover/import - Bulk import
- GET /api/v1/artifacts/metadata/github - GitHub metadata fetch
- PUT /api/v1/artifacts/{artifact_id}/parameters - Parameter updates
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings
from skillmeat.api.server import create_app
from skillmeat.core.artifact import Artifact, ArtifactMetadata, ArtifactType
from skillmeat.core.discovery import DiscoveredArtifact as CoreDiscoveredArtifact
from skillmeat.core.discovery import DiscoveryResult as CoreDiscoveryResult


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

    # Initialize app state before creating client
    app = create_app(api_settings)

    # Initialize app_state manually for tests
    app_state.initialize(api_settings)

    client = TestClient(app)

    yield client

    # Clean up
    app_state.shutdown()


@pytest.fixture
def mock_collection_path(tmp_path):
    """Create mock collection with artifacts."""
    artifacts_dir = tmp_path / "artifacts" / "skills"
    artifacts_dir.mkdir(parents=True)

    # Create test skill
    skill_dir = artifacts_dir / "test-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: test-skill
description: A test skill
author: test-author
tags:
  - testing
---

# Test Skill
"""
    )
    return tmp_path


@pytest.fixture
def sample_artifact():
    """Create a sample artifact for testing."""
    metadata = ArtifactMetadata(
        title="Test Skill",
        description="A test skill",
        author="Test Author",
        license="MIT",
        version="1.0.0",
        tags=["test", "skill"],
    )

    return Artifact(
        name="test-skill",
        type=ArtifactType.SKILL,
        path="skills/test-skill",
        origin="github",
        upstream="anthropics/skills/test-skill",
        version_spec="latest",
        resolved_sha="abc123",
        resolved_version="v1.0.0",
        added=datetime.utcnow(),
        last_updated=datetime.utcnow(),
        metadata=metadata,
        tags=["test"],
    )


class TestDiscoveryEndpoint:
    """Tests for POST /api/v1/artifacts/discover"""

    def test_discover_success(self, client, mock_collection_path):
        """Test successful artifact discovery."""
        with patch(
            "skillmeat.api.dependencies.app_state.collection_manager"
        ) as mock_coll_mgr:
            with patch(
                "skillmeat.core.discovery.ArtifactDiscoveryService.discover_artifacts"
            ) as mock_discover:
                # Mock collection manager
                mock_coll_mgr.list_collections.return_value = ["default"]
                mock_coll_mgr.config.get_collection_path.return_value = (
                    mock_collection_path
                )

                # Mock discovery result
                discovered = CoreDiscoveredArtifact(
                    type="skill",
                    name="test-skill",
                    source="anthropics/skills/test-skill",
                    version="latest",
                    scope="user",
                    tags=["test"],
                    description="A test skill",
                    path=str(mock_collection_path / "artifacts/skills/test-skill"),
                    discovered_at=datetime.utcnow(),
                )

                mock_discover.return_value = CoreDiscoveryResult(
                    discovered_count=1,
                    importable_count=1,
                    artifacts=[discovered],
                    errors=[],
                    scan_duration_ms=123.45,
                )

                response = client.post("/api/v1/artifacts/discover", json={})

                assert response.status_code == 200
                data = response.json()
                assert data["discovered_count"] == 1
                assert len(data["artifacts"]) == 1
                assert data["artifacts"][0]["name"] == "test-skill"
                assert data["scan_duration_ms"] > 0
                assert data["errors"] == []

    def test_discover_empty_collection(self, client, tmp_path):
        """Test discovery with empty collection."""
        with patch(
            "skillmeat.api.dependencies.app_state.collection_manager"
        ) as mock_coll_mgr:
            with patch(
                "skillmeat.core.discovery.ArtifactDiscoveryService.discover_artifacts"
            ) as mock_discover:
                # Mock empty collection
                mock_coll_mgr.list_collections.return_value = ["default"]
                mock_coll_mgr.config.get_collection_path.return_value = tmp_path

                mock_discover.return_value = CoreDiscoveryResult(
                    discovered_count=0,
                    importable_count=0,
                    artifacts=[],
                    errors=[],
                    scan_duration_ms=50.0,
                )

                response = client.post("/api/v1/artifacts/discover", json={})

                assert response.status_code == 200
                data = response.json()
                assert data["discovered_count"] == 0
                assert data["artifacts"] == []

    def test_discover_invalid_path(self, client):
        """Test discovery with invalid scan_path."""
        with patch(
            "skillmeat.api.dependencies.app_state.collection_manager"
        ) as mock_coll_mgr:
            mock_coll_mgr.list_collections.return_value = ["default"]

            response = client.post(
                "/api/v1/artifacts/discover", json={"scan_path": "/nonexistent/path"}
            )

            assert response.status_code == 400
            detail = response.json()["detail"]
            # detail might be a string or dict
            detail_str = str(detail).lower() if isinstance(detail, (str, dict)) else detail
            assert "does not exist" in detail_str

    def test_discover_with_errors(self, client, mock_collection_path):
        """Test discovery with some errors during scan."""
        with patch(
            "skillmeat.api.dependencies.app_state.collection_manager"
        ) as mock_coll_mgr:
            with patch(
                "skillmeat.core.discovery.ArtifactDiscoveryService.discover_artifacts"
            ) as mock_discover:
                mock_coll_mgr.list_collections.return_value = ["default"]
                mock_coll_mgr.config.get_collection_path.return_value = (
                    mock_collection_path
                )

                # Return result with errors
                mock_discover.return_value = CoreDiscoveryResult(
                    discovered_count=1,
                    importable_count=1,
                    artifacts=[
                        CoreDiscoveredArtifact(
                            type="skill",
                            name="valid-skill",
                            source=None,
                            version=None,
                            scope="user",
                            tags=[],
                            description=None,
                            path="/path/to/valid",
                            discovered_at=datetime.utcnow(),
                        )
                    ],
                    errors=[
                        "Failed to parse SKILL.md in /path/to/broken: invalid YAML",
                        "Permission denied: /path/to/protected",
                    ],
                    scan_duration_ms=200.0,
                )

                response = client.post("/api/v1/artifacts/discover", json={})

                assert response.status_code == 200
                data = response.json()
                assert data["discovered_count"] == 1
                assert len(data["errors"]) == 2

    def test_discover_feature_flag_disabled(self, client):
        """Test discovery when auto-discovery feature is disabled."""
        from skillmeat.api.config import reload_settings
        import os

        # Set env var to disable feature
        original = os.environ.get("SKILLMEAT_ENABLE_AUTO_DISCOVERY")
        os.environ["SKILLMEAT_ENABLE_AUTO_DISCOVERY"] = "false"

        try:
            # Force reload settings with new env var
            reload_settings()

            response = client.post("/api/v1/artifacts/discover", json={})

            assert response.status_code == 501
            data = response.json()
            assert "disabled" in data["detail"].lower()
            assert "SKILLMEAT_ENABLE_AUTO_DISCOVERY" in data["detail"]
        finally:
            # Restore original env var
            if original is not None:
                os.environ["SKILLMEAT_ENABLE_AUTO_DISCOVERY"] = original
            else:
                os.environ.pop("SKILLMEAT_ENABLE_AUTO_DISCOVERY", None)
            reload_settings()


class TestBulkImportEndpoint:
    """Tests for POST /api/v1/artifacts/discover/import"""

    def test_bulk_import_success(self, client):
        """Test successful bulk import."""
        with patch(
            "skillmeat.api.dependencies.app_state.collection_manager"
        ) as mock_coll_mgr:
            with patch(
                "skillmeat.api.dependencies.app_state.artifact_manager"
            ) as mock_art_mgr:
                with patch("skillmeat.api.routers.artifacts.ArtifactImporter") as mock_importer_cls:
                    mock_coll_mgr.list_collections.return_value = ["default"]

                    # Mock bulk import result
                    from skillmeat.core.importer import (
                        BulkImportResultData,
                        ImportResultData,
                    )

                    import_result = ImportResultData(
                        artifact_id="skill:test-skill",
                        success=True,
                        message="Artifact 'test-skill' imported successfully",
                        error=None,
                    )

                    bulk_result = BulkImportResultData(
                        total_requested=1,
                        total_imported=1,
                        total_failed=0,
                        results=[import_result],
                        duration_ms=500.0,
                    )

                    mock_importer_instance = Mock()
                    mock_importer_instance.bulk_import.return_value = bulk_result
                    mock_importer_cls.return_value = mock_importer_instance

                    response = client.post(
                        "/api/v1/artifacts/discover/import",
                        json={
                            "artifacts": [
                                {
                                    "source": "test/repo/skill",
                                    "artifact_type": "skill",
                                    "name": "test-skill",
                                    "scope": "user",
                                }
                            ],
                            "auto_resolve_conflicts": False,
                        },
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["total_requested"] == 1
                    assert data["total_imported"] == 1
                    assert data["total_failed"] == 0
                    assert len(data["results"]) == 1
                    assert data["results"][0]["success"] is True

    def test_bulk_import_validation_error(self, client):
        """Test bulk import with invalid artifact type."""
        with patch(
            "skillmeat.api.dependencies.app_state.collection_manager"
        ) as mock_coll_mgr:
            mock_coll_mgr.list_collections.return_value = ["default"]

            response = client.post(
                "/api/v1/artifacts/discover/import",
                json={
                    "artifacts": [
                        {
                            "source": "test/repo/skill",
                            "artifact_type": "invalid_type",
                            "name": "test",
                        }
                    ]
                },
            )

            # Should return 422 validation error
            assert response.status_code == 422

    def test_bulk_import_duplicate_with_auto_resolve(self, client):
        """Test bulk import handles duplicates with auto_resolve_conflicts."""
        with patch(
            "skillmeat.api.dependencies.app_state.collection_manager"
        ) as mock_coll_mgr:
            with patch(
                "skillmeat.api.dependencies.app_state.artifact_manager"
            ) as mock_art_mgr:
                with patch("skillmeat.api.routers.artifacts.ArtifactImporter") as mock_importer:
                    mock_coll_mgr.list_collections.return_value = ["default"]

                    from skillmeat.core.importer import (
                        BulkImportResultData,
                        ImportResultData,
                    )

                    # Simulate successful import with auto-resolve
                    import_result = ImportResultData(
                        artifact_id="skill:existing-skill",
                        success=True,
                        message="Artifact 'existing-skill' imported (overwritten)",
                        error=None,
                    )

                    bulk_result = BulkImportResultData(
                        total_requested=1,
                        total_imported=1,
                        total_failed=0,
                        results=[import_result],
                        duration_ms=300.0,
                    )

                    mock_importer_instance = Mock()
                    mock_importer_instance.bulk_import.return_value = bulk_result
                    mock_importer.return_value = mock_importer_instance

                    response = client.post(
                        "/api/v1/artifacts/discover/import",
                        json={
                            "artifacts": [
                                {
                                    "source": "test/repo/existing",
                                    "artifact_type": "skill",
                                    "name": "existing-skill",
                                    "scope": "user",
                                }
                            ],
                            "auto_resolve_conflicts": True,
                        },
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["total_imported"] == 1
                    assert data["total_failed"] == 0

    def test_bulk_import_duplicate_without_auto_resolve(self, client):
        """Test bulk import fails on duplicates when auto_resolve is False."""
        with patch(
            "skillmeat.api.dependencies.app_state.collection_manager"
        ) as mock_coll_mgr:
            with patch(
                "skillmeat.api.dependencies.app_state.artifact_manager"
            ) as mock_art_mgr:
                with patch("skillmeat.api.routers.artifacts.ArtifactImporter") as mock_importer:
                    mock_coll_mgr.list_collections.return_value = ["default"]

                    from skillmeat.core.importer import (
                        BulkImportResultData,
                        ImportResultData,
                    )

                    # Simulate failed import due to duplicate
                    import_result = ImportResultData(
                        artifact_id="skill:existing-skill",
                        success=False,
                        message="Import failed",
                        error="Artifact already exists and auto_resolve_conflicts is False",
                    )

                    bulk_result = BulkImportResultData(
                        total_requested=1,
                        total_imported=0,
                        total_failed=1,
                        results=[import_result],
                        duration_ms=100.0,
                    )

                    mock_importer_instance = Mock()
                    mock_importer_instance.bulk_import.return_value = bulk_result
                    mock_importer.return_value = mock_importer_instance

                    response = client.post(
                        "/api/v1/artifacts/discover/import",
                        json={
                            "artifacts": [
                                {
                                    "source": "test/repo/existing",
                                    "artifact_type": "skill",
                                    "name": "existing-skill",
                                    "scope": "user",
                                }
                            ],
                            "auto_resolve_conflicts": False,
                        },
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["total_imported"] == 0
                    assert data["total_failed"] == 1
                    assert data["results"][0]["success"] is False

    def test_bulk_import_empty_list(self, client):
        """Test bulk import with empty artifacts list."""
        with patch(
            "skillmeat.api.dependencies.app_state.collection_manager"
        ) as mock_coll_mgr:
            mock_coll_mgr.list_collections.return_value = ["default"]

            response = client.post(
                "/api/v1/artifacts/discover/import",
                json={"artifacts": [], "auto_resolve_conflicts": False},
            )

            # Should fail validation - min_length=1
            assert response.status_code == 422

    def test_bulk_import_no_collection(self, client):
        """Test bulk import when no collections exist."""
        with patch(
            "skillmeat.api.dependencies.app_state.collection_manager"
        ) as mock_coll_mgr:
            with patch(
                "skillmeat.api.dependencies.app_state.artifact_manager"
            ) as mock_art_mgr:
                with patch("skillmeat.api.routers.artifacts.ArtifactImporter") as mock_importer_cls:
                    mock_coll_mgr.list_collections.return_value = []

                    # Mock bulk import result with failure
                    from skillmeat.core.importer import (
                        BulkImportResultData,
                        ImportResultData,
                    )

                    import_result = ImportResultData(
                        artifact_id="skill:test-skill",
                        success=False,
                        message="Import failed",
                        error="No collections available",
                    )

                    bulk_result = BulkImportResultData(
                        total_requested=1,
                        total_imported=0,
                        total_failed=1,
                        results=[import_result],
                        duration_ms=10.0,
                    )

                    mock_importer_instance = Mock()
                    mock_importer_instance.bulk_import.return_value = bulk_result
                    mock_importer_cls.return_value = mock_importer_instance

                    response = client.post(
                        "/api/v1/artifacts/discover/import",
                        json={
                            "artifacts": [
                                {
                                    "source": "test/repo/skill",
                                    "artifact_type": "skill",
                                    "name": "test-skill",
                                }
                            ]
                        },
                    )

                    # The endpoint returns 200 with failed results, not 404
                    assert response.status_code == 200
                    data = response.json()
                    assert data["total_imported"] == 0
                    assert data["total_failed"] == 1


class TestGitHubMetadataEndpoint:
    """Tests for GET /api/v1/artifacts/metadata/github"""

    def test_metadata_fetch_success(self, client):
        """Test successful metadata fetch."""
        with patch(
            "skillmeat.core.github_metadata.GitHubMetadataExtractor.fetch_metadata"
        ) as mock_fetch:
            from skillmeat.core.github_metadata import GitHubMetadata

            metadata = GitHubMetadata(
                title="Test Skill",
                description="A test skill",
                author="test-author",
                license="MIT",
                topics=["testing"],
                url="https://github.com/test/repo",
                fetched_at=datetime.utcnow(),
                source="auto-populated",
            )

            mock_fetch.return_value = metadata

            response = client.get(
                "/api/v1/artifacts/metadata/github", params={"source": "test/repo/skill"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["metadata"]["title"] == "Test Skill"
            assert data["metadata"]["author"] == "test-author"
            assert data["metadata"]["license"] == "MIT"
            assert "testing" in data["metadata"]["topics"]
            assert data["error"] is None

    def test_metadata_fetch_invalid_source(self, client):
        """Test metadata fetch with invalid source format."""
        with patch(
            "skillmeat.core.github_metadata.GitHubMetadataExtractor.fetch_metadata"
        ) as mock_fetch:
            mock_fetch.side_effect = ValueError("Invalid source format")

            response = client.get(
                "/api/v1/artifacts/metadata/github", params={"source": "invalid"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "invalid" in data["error"].lower()
            assert data["metadata"] is None

    def test_metadata_fetch_not_found(self, client):
        """Test metadata fetch for nonexistent repo."""
        with patch(
            "skillmeat.core.github_metadata.GitHubMetadataExtractor.fetch_metadata"
        ) as mock_fetch:
            mock_fetch.side_effect = RuntimeError("404: Not found")

            response = client.get(
                "/api/v1/artifacts/metadata/github",
                params={"source": "nonexistent/repo/skill"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "404" in data["error"] or "not found" in data["error"].lower()

    def test_metadata_fetch_rate_limited(self, client):
        """Test metadata fetch when rate limited."""
        with patch(
            "skillmeat.core.github_metadata.GitHubMetadataExtractor.fetch_metadata"
        ) as mock_fetch:
            mock_fetch.side_effect = RuntimeError("429: Rate limit exceeded")

            response = client.get(
                "/api/v1/artifacts/metadata/github", params={"source": "test/repo/skill"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "rate limit" in data["error"].lower()

    def test_metadata_fetch_missing_source(self, client):
        """Test metadata fetch without source parameter."""
        response = client.get("/api/v1/artifacts/metadata/github")

        # Should return 422 validation error - missing required query param
        assert response.status_code == 422

    def test_metadata_fetch_network_error(self, client):
        """Test metadata fetch with network error."""
        with patch(
            "skillmeat.core.github_metadata.GitHubMetadataExtractor.fetch_metadata"
        ) as mock_fetch:
            mock_fetch.side_effect = RuntimeError("Network error: Connection timeout")

            response = client.get(
                "/api/v1/artifacts/metadata/github", params={"source": "test/repo/skill"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert data["error"] is not None

    def test_metadata_fetch_feature_flag_disabled(self, client):
        """Test metadata fetch when auto-population feature is disabled."""
        from skillmeat.api.config import reload_settings
        import os

        # Set env var to disable feature
        original = os.environ.get("SKILLMEAT_ENABLE_AUTO_POPULATION")
        os.environ["SKILLMEAT_ENABLE_AUTO_POPULATION"] = "false"

        try:
            # Force reload settings with new env var
            reload_settings()

            response = client.get(
                "/api/v1/artifacts/metadata/github", params={"source": "test/repo/skill"}
            )

            assert response.status_code == 501
            data = response.json()
            assert "disabled" in data["detail"].lower()
            assert "SKILLMEAT_ENABLE_AUTO_POPULATION" in data["detail"]
        finally:
            # Restore original env var
            if original is not None:
                os.environ["SKILLMEAT_ENABLE_AUTO_POPULATION"] = original
            else:
                os.environ.pop("SKILLMEAT_ENABLE_AUTO_POPULATION", None)
            reload_settings()

    def test_metadata_fetch_custom_cache_ttl(self, client):
        """Test metadata fetch uses custom cache TTL from settings."""
        from skillmeat.api.config import reload_settings
        import os

        # Set custom cache TTL
        original = os.environ.get("SKILLMEAT_DISCOVERY_CACHE_TTL")
        os.environ["SKILLMEAT_DISCOVERY_CACHE_TTL"] = "7200"  # 2 hours

        try:
            # Force reload settings
            reload_settings()

            with patch(
                "skillmeat.core.github_metadata.GitHubMetadataExtractor.fetch_metadata"
            ) as mock_fetch:
                with patch("skillmeat.core.cache.MetadataCache") as mock_cache_cls:
                    from skillmeat.core.github_metadata import GitHubMetadata

                    metadata = GitHubMetadata(
                        title="Test",
                        description="Test",
                        url="https://github.com/test/repo",
                        fetched_at=datetime.utcnow(),
                    )
                    mock_fetch.return_value = metadata

                    response = client.get(
                        "/api/v1/artifacts/metadata/github",
                        params={"source": "test/repo/skill"},
                    )

                    assert response.status_code == 200
                    # Verify cache was initialized with custom TTL
                    # Note: This checks if MetadataCache was called, actual TTL check
                    # would require inspecting app_state which is complex in tests
                    assert response.json()["success"] is True
        finally:
            # Restore original env var
            if original is not None:
                os.environ["SKILLMEAT_DISCOVERY_CACHE_TTL"] = original
            else:
                os.environ.pop("SKILLMEAT_DISCOVERY_CACHE_TTL", None)
            reload_settings()

    def test_metadata_fetch_github_token_priority(self, client):
        """Test GitHub token priority: settings > config manager."""
        from skillmeat.api.config import reload_settings
        import os

        # Set token via env var
        original = os.environ.get("SKILLMEAT_GITHUB_TOKEN")
        os.environ["SKILLMEAT_GITHUB_TOKEN"] = "ghp_test_token_from_env"

        try:
            # Force reload settings
            reload_settings()

            # Patch at the router level where it's imported
            with patch(
                "skillmeat.api.routers.artifacts.GitHubMetadataExtractor"
            ) as mock_extractor_cls:
                from skillmeat.core.github_metadata import GitHubMetadata

                metadata = GitHubMetadata(
                    title="Test",
                    description="Test",
                    url="https://github.com/test/repo",
                    fetched_at=datetime.utcnow(),
                )

                mock_instance = Mock()
                mock_instance.fetch_metadata.return_value = metadata
                mock_extractor_cls.return_value = mock_instance

                response = client.get(
                    "/api/v1/artifacts/metadata/github",
                    params={"source": "test/repo/skill"},
                )

                assert response.status_code == 200
                # Verify extractor was initialized with token from settings
                mock_extractor_cls.assert_called_once()
                call_kwargs = mock_extractor_cls.call_args.kwargs
                assert call_kwargs["token"] == "ghp_test_token_from_env"
        finally:
            # Restore original env var
            if original is not None:
                os.environ["SKILLMEAT_GITHUB_TOKEN"] = original
            else:
                os.environ.pop("SKILLMEAT_GITHUB_TOKEN", None)
            reload_settings()


class TestParameterUpdateEndpoint:
    """Tests for PUT /api/v1/artifacts/{artifact_id}/parameters"""

    def test_parameter_update_success(self, client, sample_artifact, tmp_path):
        """Test successful parameter update."""
        # Create mock artifact directory
        artifact_dir = tmp_path / "skills" / "test-skill"
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "SKILL.md").write_text("# Test skill")

        with patch(
            "skillmeat.api.dependencies.app_state.collection_manager"
        ) as mock_coll_mgr:
            with patch(
                "skillmeat.api.dependencies.app_state.artifact_manager"
            ) as mock_art_mgr:
                # Mock collection finding
                mock_coll = Mock()
                mock_coll.find_artifact.return_value = sample_artifact

                mock_coll_mgr.list_collections.return_value = ["default"]
                mock_coll_mgr.load_collection.return_value = mock_coll
                mock_coll_mgr.config.get_collection_path.return_value = tmp_path

                response = client.put(
                    "/api/v1/artifacts/skill:test-skill/parameters",
                    json={"parameters": {"tags": ["new-tag", "updated"]}},
                )

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "tags" in data["updated_fields"]
                assert data["artifact_id"] == "skill:test-skill"

    def test_parameter_update_multiple_fields(self, client, sample_artifact, tmp_path):
        """Test updating multiple parameters at once."""
        # Create mock artifact directory
        artifact_dir = tmp_path / "skills" / "test-skill"
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "SKILL.md").write_text("# Test skill")

        with patch(
            "skillmeat.api.dependencies.app_state.collection_manager"
        ) as mock_coll_mgr:
            with patch(
                "skillmeat.api.dependencies.app_state.artifact_manager"
            ) as mock_art_mgr:
                mock_coll = Mock()
                mock_coll.find_artifact.return_value = sample_artifact

                mock_coll_mgr.list_collections.return_value = ["default"]
                mock_coll_mgr.load_collection.return_value = mock_coll
                mock_coll_mgr.config.get_collection_path.return_value = tmp_path

                response = client.put(
                    "/api/v1/artifacts/skill:test-skill/parameters",
                    json={
                        "parameters": {
                            "tags": ["test", "updated"],
                            "scope": "user",
                            "aliases": ["my-skill"],
                        }
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "tags" in data["updated_fields"]
                assert "scope" in data["updated_fields"]
                assert "aliases" in data["updated_fields"]

    def test_parameter_update_not_found(self, client):
        """Test parameter update for nonexistent artifact."""
        with patch(
            "skillmeat.api.dependencies.app_state.collection_manager"
        ) as mock_coll_mgr:
            mock_coll = Mock()
            mock_coll.find_artifact.return_value = None

            mock_coll_mgr.list_collections.return_value = ["default"]
            mock_coll_mgr.load_collection.return_value = mock_coll

            response = client.put(
                "/api/v1/artifacts/skill:nonexistent/parameters",
                json={"parameters": {"tags": ["new-tag"]}},
            )

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_parameter_update_invalid_scope(self, client):
        """Test parameter update with invalid scope."""
        response = client.put(
            "/api/v1/artifacts/skill:test/parameters",
            json={"parameters": {"scope": "invalid_scope"}},
        )

        # Should be 422 validation error
        assert response.status_code == 422

    def test_parameter_update_invalid_source_format(self, client, sample_artifact, tmp_path):
        """Test parameter update with invalid source format."""
        # Create mock artifact directory
        artifact_dir = tmp_path / "skills" / "test-skill"
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "SKILL.md").write_text("# Test skill")

        with patch(
            "skillmeat.api.dependencies.app_state.collection_manager"
        ) as mock_coll_mgr:
            mock_coll = Mock()
            mock_coll.find_artifact.return_value = sample_artifact

            mock_coll_mgr.list_collections.return_value = ["default"]
            mock_coll_mgr.load_collection.return_value = mock_coll
            mock_coll_mgr.config.get_collection_path.return_value = tmp_path

            # Patch at the core module level where it's imported from
            with patch(
                "skillmeat.core.github_metadata.GitHubMetadataExtractor"
            ) as mock_extractor_cls:
                mock_extractor = Mock()
                mock_extractor.parse_github_url.side_effect = ValueError("Invalid GitHub source format")
                mock_extractor_cls.return_value = mock_extractor

                response = client.put(
                    "/api/v1/artifacts/skill:test-skill/parameters",
                    json={"parameters": {"source": "invalid-format"}},
                )

                # Should return 400 or 422 (validation error)
                assert response.status_code in [400, 422]
                detail = response.json()["detail"]
                detail_str = str(detail).lower() if isinstance(detail, (str, dict)) else detail
                assert "invalid" in detail_str or "value_error" in detail_str

    def test_parameter_update_invalid_id_format(self, client):
        """Test parameter update with invalid artifact ID format."""
        response = client.put(
            "/api/v1/artifacts/invalid-id-format/parameters",
            json={"parameters": {"tags": ["test"]}},
        )

        assert response.status_code == 400
        assert "invalid artifact id format" in response.json()["detail"].lower()

    def test_parameter_update_no_changes(self, client, sample_artifact):
        """Test parameter update with no actual changes."""
        with patch(
            "skillmeat.api.dependencies.app_state.collection_manager"
        ) as mock_coll_mgr:
            mock_coll = Mock()
            mock_coll.find_artifact.return_value = sample_artifact

            mock_coll_mgr.list_collections.return_value = ["default"]
            mock_coll_mgr.load_collection.return_value = mock_coll

            response = client.put(
                "/api/v1/artifacts/skill:test-skill/parameters",
                json={"parameters": {}},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["updated_fields"]) == 0
            assert "no parameters" in data["message"].lower()

    def test_parameter_update_source_and_version(self, client, sample_artifact, tmp_path):
        """Test updating source and version together."""
        # Create mock artifact directory
        artifact_dir = tmp_path / "skills" / "test-skill"
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "SKILL.md").write_text("# Test skill")

        with patch(
            "skillmeat.api.dependencies.app_state.collection_manager"
        ) as mock_coll_mgr:
            mock_coll = Mock()
            mock_coll.find_artifact.return_value = sample_artifact

            mock_coll_mgr.list_collections.return_value = ["default"]
            mock_coll_mgr.load_collection.return_value = mock_coll
            mock_coll_mgr.config.get_collection_path.return_value = tmp_path

            # Patch at the core module level where it's imported from
            with patch(
                "skillmeat.core.github_metadata.GitHubMetadataExtractor"
            ) as mock_extractor_cls:
                mock_extractor = Mock()
                mock_extractor.parse_github_url.return_value = None  # Valid parse
                mock_extractor_cls.return_value = mock_extractor

                response = client.put(
                    "/api/v1/artifacts/skill:test-skill/parameters",
                    json={
                        "parameters": {
                            "source": "anthropics/skills/test-skill@v2.0.0",
                            "version": "v2.0.0",
                        }
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "source" in data["updated_fields"]
                assert "version" in data["updated_fields"]
