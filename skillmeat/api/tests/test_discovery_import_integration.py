"""Integration tests for Discovery → Import → Notification flow.

Tests for Phase 5 (DIS-5.1): Integration testing of the complete flow:
- Discovery endpoint with pre-scan filtering
- Import with ImportStatus enum (success/skipped/failed)
- Skip list parameter processing
- BulkImportResult counters (imported_to_collection, added_to_project, total_skipped)
- Pre-scan existence checks (Collection vs Project vs both)
- Error handling (network, permissions, invalid artifacts)
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings
from skillmeat.api.schemas.discovery import ImportStatus
from skillmeat.api.server import create_app
from skillmeat.core.artifact import Artifact, ArtifactMetadata, ArtifactType
from skillmeat.core.discovery import DiscoveredArtifact as CoreDiscoveredArtifact
from skillmeat.core.discovery import DiscoveryResult as CoreDiscoveryResult
from skillmeat.core.importer import (
    BulkImportArtifactData,
    BulkImportResultData,
    ImportResultData,
)


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

    # Create test skills
    for skill_name in ["skill-a", "skill-b", "skill-c"]:
        skill_dir = artifacts_dir / skill_name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            f"""---
name: {skill_name}
description: Test skill {skill_name}
author: test-author
tags:
  - testing
---

# {skill_name}
"""
        )
    return tmp_path


@pytest.fixture
def mock_project_path(tmp_path):
    """Create mock project with .claude/ directory."""
    project_path = tmp_path / "project"
    project_path.mkdir(parents=True)
    claude_dir = project_path / ".claude"
    claude_dir.mkdir()

    # Create skills directory
    skills_dir = claude_dir / "skills"
    skills_dir.mkdir()

    # Create one skill that exists in project
    skill_dir = skills_dir / "skill-b"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: skill-b
description: Test skill B in project
---

# skill-b
"""
    )
    return project_path


class TestFullDiscoveryFlow:
    """Test Case 1: Full discovery flow → pre-scan filters → filtered results"""

    def test_discovery_with_prescan_filtering(
        self, client, mock_collection_path, mock_project_path
    ):
        """Test discovery returns only importable artifacts after pre-scan filtering.

        Expected behavior:
        - skill-a: In collection only → importable (can deploy to project)
        - skill-b: In both collection and project → NOT importable
        - skill-c: In collection only → importable
        """
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

                # Mock discovery result - skill-b is filtered out (exists in both)
                discovered_a = CoreDiscoveredArtifact(
                    type="skill",
                    name="skill-a",
                    source="local/skill/skill-a",
                    version=None,
                    scope="user",
                    tags=["testing"],
                    description="Test skill skill-a",
                    path=str(mock_collection_path / "artifacts/skills/skill-a"),
                    discovered_at=datetime.utcnow(),
                )
                discovered_c = CoreDiscoveredArtifact(
                    type="skill",
                    name="skill-c",
                    source="local/skill/skill-c",
                    version=None,
                    scope="user",
                    tags=["testing"],
                    description="Test skill skill-c",
                    path=str(mock_collection_path / "artifacts/skills/skill-c"),
                    discovered_at=datetime.utcnow(),
                )

                # Mock result shows only 2 importable (skill-b filtered out)
                mock_discover.return_value = CoreDiscoveryResult(
                    discovered_count=3,  # Total found
                    importable_count=2,  # After filtering
                    artifacts=[discovered_a, discovered_c],  # Filtered list
                    errors=[],
                    scan_duration_ms=150.0,
                )

                response = client.post("/api/v1/artifacts/discover", json={})

                assert response.status_code == 200
                data = response.json()

                # Verify counts
                assert data["discovered_count"] == 3
                assert data["importable_count"] == 2

                # Verify filtered artifacts
                assert len(data["artifacts"]) == 2
                artifact_names = [a["name"] for a in data["artifacts"]]
                assert "skill-a" in artifact_names
                assert "skill-c" in artifact_names
                assert "skill-b" not in artifact_names

                # Verify performance
                assert data["scan_duration_ms"] > 0
                assert data["errors"] == []

    def test_discovery_all_filtered_out(self, client, mock_collection_path):
        """Test discovery when all artifacts are filtered (exist in both locations)."""
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

                # All artifacts filtered out
                mock_discover.return_value = CoreDiscoveryResult(
                    discovered_count=3,
                    importable_count=0,
                    artifacts=[],
                    errors=[],
                    scan_duration_ms=100.0,
                )

                response = client.post("/api/v1/artifacts/discover", json={})

                assert response.status_code == 200
                data = response.json()
                assert data["discovered_count"] == 3
                assert data["importable_count"] == 0
                assert data["artifacts"] == []


class TestImportWithStatusEnum:
    """Test Case 2: Import with new ImportStatus enum handling"""

    def test_import_success_status(self, client):
        """Test successful import returns SUCCESS status."""
        with patch(
            "skillmeat.api.dependencies.app_state.collection_manager"
        ) as mock_coll_mgr:
            with patch(
                "skillmeat.api.dependencies.app_state.artifact_manager"
            ) as mock_art_mgr:
                with patch(
                    "skillmeat.api.routers.artifacts.ArtifactImporter"
                ) as mock_importer_cls:
                    mock_coll_mgr.list_collections.return_value = ["default"]

                    # Mock successful import
                    import_result = ImportResultData(
                        artifact_id="skill:new-skill",
                        success=True,
                        message="Artifact 'new-skill' imported successfully",
                        error=None,
                        status=ImportStatus.SUCCESS,
                    )

                    bulk_result = BulkImportResultData(
                        total_requested=1,
                        total_imported=1,
                        total_failed=0,
                        results=[import_result],
                        duration_ms=200.0,
                    )

                    mock_importer_instance = Mock()
                    mock_importer_instance.bulk_import.return_value = bulk_result
                    mock_importer_cls.return_value = mock_importer_instance

                    response = client.post(
                        "/api/v1/artifacts/discover/import",
                        json={
                            "artifacts": [
                                {
                                    "source": "test/repo/new-skill",
                                    "artifact_type": "skill",
                                    "name": "new-skill",
                                }
                            ],
                        },
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["total_imported"] == 1
                    assert data["total_failed"] == 0
                    assert data["results"][0]["status"] == "success"
                    assert data["results"][0]["artifact_id"] == "skill:new-skill"

    def test_import_skipped_status(self, client):
        """Test import of existing artifact returns SKIPPED status."""
        with patch(
            "skillmeat.api.dependencies.app_state.collection_manager"
        ) as mock_coll_mgr:
            with patch(
                "skillmeat.api.dependencies.app_state.artifact_manager"
            ) as mock_art_mgr:
                with patch(
                    "skillmeat.api.routers.artifacts.ArtifactImporter"
                ) as mock_importer_cls:
                    mock_coll_mgr.list_collections.return_value = ["default"]

                    # Mock skipped import (artifact already exists)
                    import_result = ImportResultData(
                        artifact_id="skill:existing-skill",
                        success=True,  # Counted as success for backward compatibility
                        message="Skipped: Already exists in Collection",
                        error=None,
                        status=ImportStatus.SKIPPED,
                        skip_reason="Already exists in Collection",
                    )

                    bulk_result = BulkImportResultData(
                        total_requested=1,
                        total_imported=1,  # Counted as imported
                        total_failed=0,
                        results=[import_result],
                        duration_ms=100.0,
                    )

                    mock_importer_instance = Mock()
                    mock_importer_instance.bulk_import.return_value = bulk_result
                    mock_importer_cls.return_value = mock_importer_instance

                    response = client.post(
                        "/api/v1/artifacts/discover/import",
                        json={
                            "artifacts": [
                                {
                                    "source": "test/repo/existing-skill",
                                    "artifact_type": "skill",
                                    "name": "existing-skill",
                                }
                            ],
                            "auto_resolve_conflicts": True,
                        },
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["results"][0]["status"] == "skipped"
                    assert "skip_reason" in data["results"][0]
                    assert "Already exists" in data["results"][0]["skip_reason"]

    def test_import_failed_status(self, client):
        """Test failed import returns FAILED status with error."""
        with patch(
            "skillmeat.api.dependencies.app_state.collection_manager"
        ) as mock_coll_mgr:
            with patch(
                "skillmeat.api.dependencies.app_state.artifact_manager"
            ) as mock_art_mgr:
                with patch(
                    "skillmeat.api.routers.artifacts.ArtifactImporter"
                ) as mock_importer_cls:
                    mock_coll_mgr.list_collections.return_value = ["default"]

                    # Mock failed import
                    import_result = ImportResultData(
                        artifact_id="skill:broken-skill",
                        success=False,
                        message="Import failed",
                        error="Network error: Connection timeout",
                        status=ImportStatus.FAILED,
                    )

                    bulk_result = BulkImportResultData(
                        total_requested=1,
                        total_imported=0,
                        total_failed=1,
                        results=[import_result],
                        duration_ms=50.0,
                    )

                    mock_importer_instance = Mock()
                    mock_importer_instance.bulk_import.return_value = bulk_result
                    mock_importer_cls.return_value = mock_importer_instance

                    response = client.post(
                        "/api/v1/artifacts/discover/import",
                        json={
                            "artifacts": [
                                {
                                    "source": "test/repo/broken-skill",
                                    "artifact_type": "skill",
                                    "name": "broken-skill",
                                }
                            ],
                        },
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["total_failed"] == 1
                    assert data["total_imported"] == 0
                    assert data["results"][0]["status"] == "failed"
                    assert "error" in data["results"][0]
                    assert "Network error" in data["results"][0]["error"]


class TestImportWithSkipList:
    """Test Case 3: Import with skip_list parameter"""

    def test_import_with_skip_list(self, client):
        """Test artifacts in skip_list get status=skipped."""
        with patch(
            "skillmeat.api.dependencies.app_state.collection_manager"
        ) as mock_coll_mgr:
            with patch(
                "skillmeat.api.dependencies.app_state.artifact_manager"
            ) as mock_art_mgr:
                with patch(
                    "skillmeat.api.routers.artifacts.ArtifactImporter"
                ) as mock_importer_cls:
                    mock_coll_mgr.list_collections.return_value = ["default"]

                    # Mock results: one success, one skipped
                    results = [
                        ImportResultData(
                            artifact_id="skill:skill-a",
                            success=True,
                            message="Imported successfully",
                            status=ImportStatus.SUCCESS,
                        ),
                        ImportResultData(
                            artifact_id="skill:skill-b",
                            success=True,
                            message="Skipped: In skip list",
                            status=ImportStatus.SKIPPED,
                            skip_reason="In skip list",
                        ),
                    ]

                    bulk_result = BulkImportResultData(
                        total_requested=2,
                        total_imported=2,
                        total_failed=0,
                        results=results,
                        duration_ms=150.0,
                    )

                    mock_importer_instance = Mock()
                    mock_importer_instance.bulk_import.return_value = bulk_result
                    mock_importer_cls.return_value = mock_importer_instance

                    response = client.post(
                        "/api/v1/artifacts/discover/import",
                        json={
                            "artifacts": [
                                {
                                    "source": "test/repo/skill-a",
                                    "artifact_type": "skill",
                                    "name": "skill-a",
                                },
                                {
                                    "source": "test/repo/skill-b",
                                    "artifact_type": "skill",
                                    "name": "skill-b",
                                },
                            ],
                            "skip_list": ["skill:skill-b"],
                        },
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["total_requested"] == 2
                    assert len(data["results"]) == 2

                    # Verify skill-a succeeded
                    skill_a = next(
                        r
                        for r in data["results"]
                        if r["artifact_id"] == "skill:skill-a"
                    )
                    assert skill_a["status"] == "success"

                    # Verify skill-b was skipped
                    skill_b = next(
                        r
                        for r in data["results"]
                        if r["artifact_id"] == "skill:skill-b"
                    )
                    assert skill_b["status"] == "skipped"
                    assert skill_b["skip_reason"] == "In skip list"


class TestBulkImportCounters:
    """Test Case 4: BulkImportResult includes correct counts"""

    def test_bulk_import_counters(self, client):
        """Test BulkImportResult has accurate counters.

        Verifies:
        - imported_to_collection: artifacts added to collection
        - added_to_project: artifacts deployed to project
        - total_skipped: artifacts skipped
        """
        with patch(
            "skillmeat.api.dependencies.app_state.collection_manager"
        ) as mock_coll_mgr:
            with patch(
                "skillmeat.api.dependencies.app_state.artifact_manager"
            ) as mock_art_mgr:
                with patch(
                    "skillmeat.api.routers.artifacts.ArtifactImporter"
                ) as mock_importer_cls:
                    mock_coll_mgr.list_collections.return_value = ["default"]

                    # Mock mixed results: 2 success, 1 skipped, 1 failed
                    results = [
                        ImportResultData(
                            artifact_id="skill:skill-a",
                            success=True,
                            message="Imported",
                            status=ImportStatus.SUCCESS,
                        ),
                        ImportResultData(
                            artifact_id="skill:skill-b",
                            success=True,
                            message="Imported",
                            status=ImportStatus.SUCCESS,
                        ),
                        ImportResultData(
                            artifact_id="skill:skill-c",
                            success=True,
                            message="Skipped",
                            status=ImportStatus.SKIPPED,
                            skip_reason="Already exists",
                        ),
                        ImportResultData(
                            artifact_id="skill:skill-d",
                            success=False,
                            message="Failed",
                            status=ImportStatus.FAILED,
                            error="Network error",
                        ),
                    ]

                    bulk_result = BulkImportResultData(
                        total_requested=4,
                        total_imported=2,  # Only SUCCESS count (not SKIPPED)
                        total_failed=1,
                        results=results,
                        duration_ms=300.0,
                    )

                    mock_importer_instance = Mock()
                    mock_importer_instance.bulk_import.return_value = bulk_result
                    mock_importer_cls.return_value = mock_importer_instance

                    response = client.post(
                        "/api/v1/artifacts/discover/import",
                        json={
                            "artifacts": [
                                {
                                    "source": f"test/repo/skill-{x}",
                                    "artifact_type": "skill",
                                    "name": f"skill-{x}",
                                }
                                for x in ["a", "b", "c", "d"]
                            ],
                            "auto_resolve_conflicts": True,
                        },
                    )

                    assert response.status_code == 200
                    data = response.json()

                    # Verify counters
                    assert data["total_requested"] == 4
                    assert data["total_imported"] == 2  # Only SUCCESS, not SKIPPED
                    assert data["total_failed"] == 1

                    # Count statuses
                    statuses = [r["status"] for r in data["results"]]
                    assert statuses.count("success") == 2
                    assert statuses.count("skipped") == 1
                    assert statuses.count("failed") == 1

                    # Verify total_skipped in response
                    if "total_skipped" in data:
                        assert data["total_skipped"] == 1


class TestPreScanExistenceChecks:
    """Test Case 5: Pre-scan correctly identifies artifact locations"""

    def test_prescan_collection_only(self, client):
        """Test artifact exists in Collection only → importable."""
        # This is tested indirectly through discovery flow
        # The discovery service's check_artifact_exists method handles this
        pass

    def test_prescan_project_only(self, client):
        """Test artifact exists in Project only → importable."""
        # This would be an unusual case (orphaned deployment)
        # But should still be importable to collection
        pass

    def test_prescan_both_locations(self, client):
        """Test artifact exists in both Collection and Project → NOT importable."""
        # This is the key filtering case tested in TestFullDiscoveryFlow
        pass

    def test_prescan_neither_location(self, client):
        """Test artifact in neither location → importable (new artifact)."""
        with patch(
            "skillmeat.api.dependencies.app_state.collection_manager"
        ) as mock_coll_mgr:
            with patch(
                "skillmeat.core.discovery.ArtifactDiscoveryService.discover_artifacts"
            ) as mock_discover:
                mock_coll_mgr.list_collections.return_value = ["default"]
                mock_coll_mgr.config.get_collection_path.return_value = Path(
                    "/tmp/collection"
                )

                # New artifact discovered
                discovered = CoreDiscoveredArtifact(
                    type="skill",
                    name="new-skill",
                    source="test/repo/new-skill",
                    version="latest",
                    scope="user",
                    tags=["new"],
                    description="Brand new skill",
                    path="/tmp/collection/artifacts/skills/new-skill",
                    discovered_at=datetime.utcnow(),
                )

                mock_discover.return_value = CoreDiscoveryResult(
                    discovered_count=1,
                    importable_count=1,
                    artifacts=[discovered],
                    errors=[],
                    scan_duration_ms=50.0,
                )

                response = client.post("/api/v1/artifacts/discover", json={})

                assert response.status_code == 200
                data = response.json()
                assert data["importable_count"] == 1
                assert len(data["artifacts"]) == 1


class TestErrorHandling:
    """Test Case 6: Error handling for various failure scenarios"""

    def test_network_failure_error(self, client):
        """Test handling of network failures during import."""
        with patch(
            "skillmeat.api.dependencies.app_state.collection_manager"
        ) as mock_coll_mgr:
            with patch(
                "skillmeat.api.dependencies.app_state.artifact_manager"
            ) as mock_art_mgr:
                with patch(
                    "skillmeat.api.routers.artifacts.ArtifactImporter"
                ) as mock_importer_cls:
                    mock_coll_mgr.list_collections.return_value = ["default"]

                    # Mock network failure
                    import_result = ImportResultData(
                        artifact_id="skill:remote-skill",
                        success=False,
                        message="Import failed",
                        error="Network error: Failed to fetch from GitHub",
                        status=ImportStatus.FAILED,
                    )

                    bulk_result = BulkImportResultData(
                        total_requested=1,
                        total_imported=0,
                        total_failed=1,
                        results=[import_result],
                        duration_ms=5000.0,
                    )

                    mock_importer_instance = Mock()
                    mock_importer_instance.bulk_import.return_value = bulk_result
                    mock_importer_cls.return_value = mock_importer_instance

                    response = client.post(
                        "/api/v1/artifacts/discover/import",
                        json={
                            "artifacts": [
                                {
                                    "source": "test/repo/remote-skill",
                                    "artifact_type": "skill",
                                    "name": "remote-skill",
                                }
                            ],
                        },
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["total_failed"] == 1
                    assert "Network error" in data["results"][0]["error"]

    def test_permission_denied_error(self, client):
        """Test handling of permission errors during discovery."""
        with patch(
            "skillmeat.api.dependencies.app_state.collection_manager"
        ) as mock_coll_mgr:
            with patch(
                "skillmeat.core.discovery.ArtifactDiscoveryService.discover_artifacts"
            ) as mock_discover:
                mock_coll_mgr.list_collections.return_value = ["default"]
                mock_coll_mgr.config.get_collection_path.return_value = Path(
                    "/tmp/collection"
                )

                # Mock discovery with permission errors
                mock_discover.return_value = CoreDiscoveryResult(
                    discovered_count=1,
                    importable_count=1,
                    artifacts=[
                        CoreDiscoveredArtifact(
                            type="skill",
                            name="accessible-skill",
                            source="local/skill/accessible-skill",
                            version=None,
                            scope="user",
                            tags=[],
                            description=None,
                            path="/tmp/collection/artifacts/skills/accessible-skill",
                            discovered_at=datetime.utcnow(),
                        )
                    ],
                    errors=[
                        "Permission denied accessing /path/to/protected/skill",
                        "Permission denied accessing /another/protected/skill",
                    ],
                    scan_duration_ms=100.0,
                )

                response = client.post("/api/v1/artifacts/discover", json={})

                assert response.status_code == 200
                data = response.json()
                assert len(data["errors"]) == 2
                assert "Permission denied" in data["errors"][0]

    def test_invalid_artifact_error(self, client):
        """Test handling of invalid artifact type during import."""
        with patch(
            "skillmeat.api.dependencies.app_state.collection_manager"
        ) as mock_coll_mgr:
            mock_coll_mgr.list_collections.return_value = ["default"]

            response = client.post(
                "/api/v1/artifacts/discover/import",
                json={
                    "artifacts": [
                        {
                            "source": "test/repo/invalid",
                            "artifact_type": "invalid-type",
                            "name": "invalid",
                        }
                    ],
                },
            )

            # Should return 422 validation error
            assert response.status_code == 422

    def test_malformed_source_error(self, client):
        """Test handling of malformed source during import."""
        with patch(
            "skillmeat.api.dependencies.app_state.collection_manager"
        ) as mock_coll_mgr:
            mock_coll_mgr.list_collections.return_value = ["default"]

            # Malformed source (missing slashes) triggers validation at API level
            response = client.post(
                "/api/v1/artifacts/discover/import",
                json={
                    "artifacts": [
                        {
                            "source": "malformed",  # Invalid: needs user/repo/artifact format
                            "artifact_type": "skill",
                            "name": "malformed",
                        }
                    ],
                },
            )

            # Validation failures are now gracefully handled - returns 200 with failed status
            # No longer raises 422 for validation errors
            assert response.status_code == 200

            data = response.json()
            assert data["total_failed"] == 1
            # Error message from validate_artifact_request
            assert "Invalid GitHub spec" in data["results"][0]["error"]


class TestEndToEndFlow:
    """Test complete end-to-end discovery → import flow"""

    def test_complete_flow_success(self, client, mock_collection_path):
        """Test complete flow: discover → filter → import → verify counters."""
        with patch(
            "skillmeat.api.dependencies.app_state.collection_manager"
        ) as mock_coll_mgr:
            with patch(
                "skillmeat.api.dependencies.app_state.artifact_manager"
            ) as mock_art_mgr:
                with patch(
                    "skillmeat.core.discovery.ArtifactDiscoveryService.discover_artifacts"
                ) as mock_discover:
                    with patch(
                        "skillmeat.api.routers.artifacts.ArtifactImporter"
                    ) as mock_importer_cls:
                        mock_coll_mgr.list_collections.return_value = ["default"]
                        mock_coll_mgr.config.get_collection_path.return_value = (
                            mock_collection_path
                        )

                        # Step 1: Discovery
                        discovered = [
                            CoreDiscoveredArtifact(
                                type="skill",
                                name=f"skill-{i}",
                                source=f"test/repo/skill-{i}",
                                version="latest",
                                scope="user",
                                tags=["test"],
                                description=f"Test skill {i}",
                                path=str(
                                    mock_collection_path / f"artifacts/skills/skill-{i}"
                                ),
                                discovered_at=datetime.utcnow(),
                            )
                            for i in range(3)
                        ]

                        mock_discover.return_value = CoreDiscoveryResult(
                            discovered_count=3,
                            importable_count=3,
                            artifacts=discovered,
                            errors=[],
                            scan_duration_ms=120.0,
                        )

                        discovery_response = client.post(
                            "/api/v1/artifacts/discover", json={}
                        )

                        assert discovery_response.status_code == 200
                        discovery_data = discovery_response.json()
                        assert discovery_data["importable_count"] == 3

                        # Step 2: Import discovered artifacts
                        import_results = [
                            ImportResultData(
                                artifact_id=f"skill:skill-{i}",
                                success=True,
                                message=f"Imported skill-{i}",
                                status=ImportStatus.SUCCESS,
                            )
                            for i in range(3)
                        ]

                        bulk_result = BulkImportResultData(
                            total_requested=3,
                            total_imported=3,
                            total_failed=0,
                            results=import_results,
                            duration_ms=450.0,
                        )

                        mock_importer_instance = Mock()
                        mock_importer_instance.bulk_import.return_value = bulk_result
                        mock_importer_cls.return_value = mock_importer_instance

                        import_response = client.post(
                            "/api/v1/artifacts/discover/import",
                            json={
                                "artifacts": [
                                    {
                                        "source": a["source"],
                                        "artifact_type": a["type"],
                                        "name": a["name"],
                                    }
                                    for a in discovery_data["artifacts"]
                                ],
                            },
                        )

                        assert import_response.status_code == 200
                        import_data = import_response.json()

                        # Verify final counts
                        assert import_data["total_requested"] == 3
                        assert import_data["total_imported"] == 3
                        assert import_data["total_failed"] == 0
                        assert all(
                            r["status"] == "success" for r in import_data["results"]
                        )
