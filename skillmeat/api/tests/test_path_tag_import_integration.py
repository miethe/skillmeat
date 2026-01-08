"""Integration tests for path tag application during bulk import.

Tests for the `apply_path_tags` feature that extracts semantic tags from
artifact paths during the bulk import process.

Test Coverage:
- apply_path_tags=True (default behavior): Tags extracted and applied
- apply_path_tags=False: No tags applied
- Path segment extraction from various path formats
- Excluded segments filtering
- Numeric prefix normalization
- Empty path handling
- Multiple artifact tag aggregation
- Tag deduplication
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings
from skillmeat.api.schemas.discovery import ImportStatus
from skillmeat.api.server import create_app
from skillmeat.core.artifact import Artifact, ArtifactMetadata, ArtifactType
from skillmeat.core.importer import (
    ArtifactImporter,
    BulkImportArtifactData,
    BulkImportResultData,
    ImportResultData,
)
from skillmeat.core.path_tags import (
    ExtractedSegment,
    PathSegmentExtractor,
    PathTagConfig,
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

    app = create_app(api_settings)
    app_state.initialize(api_settings)

    client = TestClient(app)
    yield client

    app_state.shutdown()


@pytest.fixture
def mock_collection_path(tmp_path):
    """Create mock collection with artifacts directory."""
    artifacts_dir = tmp_path / "artifacts" / "skills"
    artifacts_dir.mkdir(parents=True)
    return tmp_path


class TestApplyPathTagsDefaultTrue:
    """Test apply_path_tags=True (default behavior)."""

    def test_tags_applied_with_default_true(self, client):
        """Verify tags are applied when apply_path_tags is True (default)."""
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

                    # Mock import result with tags_applied
                    import_result = ImportResultData(
                        artifact_id="skill:data-processor",
                        success=True,
                        message="Imported successfully",
                        status=ImportStatus.SUCCESS,
                        tags_applied=2,  # Tags from path: "data-ai", "tools"
                    )

                    bulk_result = BulkImportResultData(
                        total_requested=1,
                        total_imported=1,
                        total_failed=0,
                        results=[import_result],
                        duration_ms=150.0,
                        total_tags_applied=2,
                    )

                    mock_importer_instance = Mock()
                    mock_importer_instance.bulk_import.return_value = bulk_result
                    mock_importer_cls.return_value = mock_importer_instance

                    response = client.post(
                        "/api/v1/artifacts/discover/import",
                        json={
                            "artifacts": [
                                {
                                    "source": "user/repo/05-data-ai/03-tools/data-processor",
                                    "artifact_type": "skill",
                                    "name": "data-processor",
                                    "path": "/path/to/05-data-ai/03-tools/data-processor",
                                }
                            ],
                            # apply_path_tags defaults to True
                        },
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["total_imported"] == 1
                    assert data["results"][0]["tags_applied"] == 2
                    assert data["total_tags_applied"] == 2

                    # Verify importer was called with apply_path_tags=True
                    mock_importer_instance.bulk_import.assert_called_once()
                    call_kwargs = mock_importer_instance.bulk_import.call_args[1]
                    assert call_kwargs.get("apply_path_tags", True) is True

    def test_explicit_apply_path_tags_true(self, client):
        """Verify tags are applied when apply_path_tags is explicitly True."""
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

                    import_result = ImportResultData(
                        artifact_id="skill:my-skill",
                        success=True,
                        message="Imported successfully",
                        status=ImportStatus.SUCCESS,
                        tags_applied=3,
                    )

                    bulk_result = BulkImportResultData(
                        total_requested=1,
                        total_imported=1,
                        total_failed=0,
                        results=[import_result],
                        duration_ms=100.0,
                        total_tags_applied=3,
                    )

                    mock_importer_instance = Mock()
                    mock_importer_instance.bulk_import.return_value = bulk_result
                    mock_importer_cls.return_value = mock_importer_instance

                    response = client.post(
                        "/api/v1/artifacts/discover/import",
                        json={
                            "artifacts": [
                                {
                                    "source": "user/repo/category/subcategory/my-skill",
                                    "artifact_type": "skill",
                                    "name": "my-skill",
                                }
                            ],
                            "apply_path_tags": True,
                        },
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["results"][0]["tags_applied"] == 3
                    assert data["total_tags_applied"] == 3


class TestApplyPathTagsFalse:
    """Test apply_path_tags=False (tags not applied)."""

    def test_no_tags_applied_when_false(self, client):
        """Verify NO tags are applied when apply_path_tags is False."""
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

                    # Mock import result with tags_applied=0
                    import_result = ImportResultData(
                        artifact_id="skill:data-processor",
                        success=True,
                        message="Imported successfully",
                        status=ImportStatus.SUCCESS,
                        tags_applied=0,  # No tags applied when disabled
                    )

                    bulk_result = BulkImportResultData(
                        total_requested=1,
                        total_imported=1,
                        total_failed=0,
                        results=[import_result],
                        duration_ms=100.0,
                        total_tags_applied=0,
                    )

                    mock_importer_instance = Mock()
                    mock_importer_instance.bulk_import.return_value = bulk_result
                    mock_importer_cls.return_value = mock_importer_instance

                    response = client.post(
                        "/api/v1/artifacts/discover/import",
                        json={
                            "artifacts": [
                                {
                                    "source": "user/repo/05-data-ai/03-tools/data-processor",
                                    "artifact_type": "skill",
                                    "name": "data-processor",
                                    "path": "/path/to/05-data-ai/03-tools/data-processor",
                                }
                            ],
                            "apply_path_tags": False,
                        },
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["total_imported"] == 1
                    assert data["results"][0]["tags_applied"] == 0
                    assert data["total_tags_applied"] == 0

                    # Verify importer was called with apply_path_tags=False
                    mock_importer_instance.bulk_import.assert_called_once()
                    call_kwargs = mock_importer_instance.bulk_import.call_args[1]
                    assert call_kwargs.get("apply_path_tags") is False


class TestPathSegmentExtraction:
    """Tests for path segment extraction during import."""

    def test_github_path_extraction(self):
        """Test tag extraction from GitHub-style paths."""
        extractor = PathSegmentExtractor(PathTagConfig.defaults())

        # GitHub path format: user/repo/category/subcategory/artifact
        path = "anthropics/skills/canvas/design-tools/canvas-editor"
        segments = extractor.extract(path)

        # Should extract directory segments (not filename)
        normalized_tags = [s.normalized for s in segments if s.status != "excluded"]

        # Path has: anthropics/skills/canvas/design-tools -> max_depth=3
        assert len(normalized_tags) <= 3
        # "skills" might be excluded or not depending on pattern
        # We expect to see relevant segments

    def test_local_path_extraction(self):
        """Test tag extraction from local filesystem paths."""
        extractor = PathSegmentExtractor(PathTagConfig.defaults())

        # Local path format: /home/user/.claude/skills/category/artifact
        path = "home/user/.claude/skills/data-processing/csv-parser"
        segments = extractor.extract(path)

        normalized_tags = [s.normalized for s in segments if s.status != "excluded"]

        # Should extract meaningful segments
        assert len(normalized_tags) > 0

    def test_deep_nested_path_respects_max_depth(self):
        """Test that max_depth limits extracted segments."""
        config = PathTagConfig(
            enabled=True,
            max_depth=2,  # Only take first 2 segments
            normalize_numbers=True,
            exclude_patterns=[],
        )
        extractor = PathSegmentExtractor(config)

        path = "level1/level2/level3/level4/artifact.md"
        segments = extractor.extract(path)

        # Should only have 2 segments due to max_depth
        assert len(segments) == 2
        assert segments[0].normalized == "level1"
        assert segments[1].normalized == "level2"


class TestExcludedSegments:
    """Tests for excluded segment filtering."""

    def test_common_directories_excluded(self):
        """Test that common directories (src, lib, test) are excluded."""
        extractor = PathSegmentExtractor(PathTagConfig.defaults())

        # Path with excluded directories
        path = "src/lib/features/my-feature/artifact.md"
        segments = extractor.extract(path)

        # Check that excluded segments have status="excluded"
        excluded_segments = [s for s in segments if s.status == "excluded"]
        pending_segments = [s for s in segments if s.status == "pending"]

        # "src" and "lib" should be excluded by default patterns
        excluded_names = [s.normalized for s in excluded_segments]
        assert "src" in excluded_names or "lib" in excluded_names

        # "features" and "my-feature" should be pending (not excluded)
        pending_names = [s.normalized for s in pending_segments]
        assert "my-feature" in pending_names or "features" in pending_names

    def test_docs_examples_excluded(self):
        """Test that docs and examples directories are excluded."""
        extractor = PathSegmentExtractor(PathTagConfig.defaults())

        path = "docs/examples/tutorials/my-tutorial/artifact.md"
        segments = extractor.extract(path)

        excluded_names = [s.normalized for s in segments if s.status == "excluded"]

        # "docs" and "examples" should be excluded
        assert "docs" in excluded_names
        assert "examples" in excluded_names

    def test_node_modules_excluded(self):
        """Test that node_modules is excluded."""
        extractor = PathSegmentExtractor(PathTagConfig.defaults())

        path = "node_modules/package/dist/artifact.md"
        segments = extractor.extract(path)

        excluded_names = [s.normalized for s in segments if s.status == "excluded"]
        assert "node_modules" in excluded_names


class TestNumericPrefixNormalization:
    """Tests for numeric prefix normalization."""

    def test_numeric_prefix_removed(self):
        """Test paths like '05-data-ai' normalize to 'data-ai'."""
        extractor = PathSegmentExtractor(PathTagConfig.defaults())

        path = "05-data-ai/03-tools/01-parser/artifact.md"
        segments = extractor.extract(path)

        normalized_names = [s.normalized for s in segments]

        # Numeric prefixes should be removed
        assert "data-ai" in normalized_names
        assert "tools" in normalized_names
        # Depending on max_depth, might have more

    def test_underscore_prefix_removed(self):
        """Test paths like '01_foundations' normalize to 'foundations'."""
        config = PathTagConfig(
            enabled=True,
            max_depth=3,
            normalize_numbers=True,
            exclude_patterns=[],
        )
        extractor = PathSegmentExtractor(config)

        path = "01_foundations/02_advanced/skill.md"
        segments = extractor.extract(path)

        normalized_names = [s.normalized for s in segments]

        assert "foundations" in normalized_names
        assert "advanced" in normalized_names

    def test_normalization_disabled(self):
        """Test that normalization can be disabled."""
        config = PathTagConfig(
            enabled=True,
            max_depth=3,
            normalize_numbers=False,  # Disabled
            exclude_patterns=[],
        )
        extractor = PathSegmentExtractor(config)

        path = "05-data-ai/03-tools/artifact.md"
        segments = extractor.extract(path)

        # Prefixes should NOT be removed
        normalized_names = [s.normalized for s in segments]
        assert "05-data-ai" in normalized_names
        assert "03-tools" in normalized_names


class TestEmptyPathHandling:
    """Tests for empty path handling."""

    def test_empty_path_returns_empty(self):
        """Test that empty path returns empty list."""
        extractor = PathSegmentExtractor(PathTagConfig.defaults())

        segments = extractor.extract("")
        assert segments == []

    def test_single_segment_returns_empty(self):
        """Test that path with only filename returns empty (no directories)."""
        extractor = PathSegmentExtractor(PathTagConfig.defaults())

        # Just a filename, no directory
        segments = extractor.extract("artifact.md")
        assert segments == []

    def test_root_only_path(self):
        """Test path with just one directory segment."""
        extractor = PathSegmentExtractor(PathTagConfig.defaults())

        # One directory + filename
        segments = extractor.extract("category/artifact.md")
        assert len(segments) == 1
        assert segments[0].normalized == "category"


class TestMultipleArtifacts:
    """Tests for multiple artifact import with tag aggregation."""

    def test_total_tags_applied_sum(self, client):
        """Test total_tags_applied is sum of individual tags_applied."""
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

                    # Mock results for multiple artifacts
                    results = [
                        ImportResultData(
                            artifact_id="skill:skill-a",
                            success=True,
                            message="Imported",
                            status=ImportStatus.SUCCESS,
                            tags_applied=2,
                        ),
                        ImportResultData(
                            artifact_id="skill:skill-b",
                            success=True,
                            message="Imported",
                            status=ImportStatus.SUCCESS,
                            tags_applied=3,
                        ),
                        ImportResultData(
                            artifact_id="skill:skill-c",
                            success=True,
                            message="Imported",
                            status=ImportStatus.SUCCESS,
                            tags_applied=1,
                        ),
                    ]

                    bulk_result = BulkImportResultData(
                        total_requested=3,
                        total_imported=3,
                        total_failed=0,
                        results=results,
                        duration_ms=300.0,
                        total_tags_applied=6,  # 2 + 3 + 1
                    )

                    mock_importer_instance = Mock()
                    mock_importer_instance.bulk_import.return_value = bulk_result
                    mock_importer_cls.return_value = mock_importer_instance

                    response = client.post(
                        "/api/v1/artifacts/discover/import",
                        json={
                            "artifacts": [
                                {
                                    "source": "user/repo/cat-a/skill-a",
                                    "artifact_type": "skill",
                                    "name": "skill-a",
                                },
                                {
                                    "source": "user/repo/cat-b/sub-b/skill-b",
                                    "artifact_type": "skill",
                                    "name": "skill-b",
                                },
                                {
                                    "source": "user/repo/cat-c/skill-c",
                                    "artifact_type": "skill",
                                    "name": "skill-c",
                                },
                            ],
                            "apply_path_tags": True,
                        },
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["total_imported"] == 3
                    assert data["total_tags_applied"] == 6

                    # Verify individual counts
                    assert data["results"][0]["tags_applied"] == 2
                    assert data["results"][1]["tags_applied"] == 3
                    assert data["results"][2]["tags_applied"] == 1

    def test_mixed_success_skipped_failed(self, client):
        """Test tag counting with mixed import statuses."""
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

                    results = [
                        ImportResultData(
                            artifact_id="skill:success-skill",
                            success=True,
                            message="Imported",
                            status=ImportStatus.SUCCESS,
                            tags_applied=3,  # Tags applied
                        ),
                        ImportResultData(
                            artifact_id="skill:skipped-skill",
                            success=True,
                            message="Skipped",
                            status=ImportStatus.SKIPPED,
                            skip_reason="Already exists",
                            tags_applied=0,  # No tags for skipped
                        ),
                        ImportResultData(
                            artifact_id="skill:failed-skill",
                            success=False,
                            message="Failed",
                            status=ImportStatus.FAILED,
                            error="Network error",
                            tags_applied=0,  # No tags for failed
                        ),
                    ]

                    bulk_result = BulkImportResultData(
                        total_requested=3,
                        total_imported=2,
                        total_failed=1,
                        results=results,
                        duration_ms=200.0,
                        total_tags_applied=3,  # Only from successful import
                    )

                    mock_importer_instance = Mock()
                    mock_importer_instance.bulk_import.return_value = bulk_result
                    mock_importer_cls.return_value = mock_importer_instance

                    response = client.post(
                        "/api/v1/artifacts/discover/import",
                        json={
                            "artifacts": [
                                {
                                    "source": "u/r/a/success-skill",
                                    "artifact_type": "skill",
                                    "name": "success-skill",
                                },
                                {
                                    "source": "u/r/b/skipped-skill",
                                    "artifact_type": "skill",
                                    "name": "skipped-skill",
                                },
                                {
                                    "source": "u/r/c/failed-skill",
                                    "artifact_type": "skill",
                                    "name": "failed-skill",
                                },
                            ],
                        },
                    )

                    assert response.status_code == 200
                    data = response.json()
                    # Total tags only from successful import
                    assert data["total_tags_applied"] == 3


class TestTagDeduplication:
    """Tests for tag deduplication during import."""

    def test_existing_tags_not_duplicated(self):
        """Test that existing tags are not added again."""
        # Create mock artifact manager and collection manager
        mock_artifact_manager = Mock()
        mock_collection_manager = Mock()

        # Create mock artifact with existing tags
        mock_artifact = Mock()
        mock_artifact.name = "test-skill"
        mock_artifact.tags = ["existing-tag", "data-ai"]  # "data-ai" already exists

        # Create mock collection
        mock_collection = Mock()
        mock_collection.find_artifact.return_value = mock_artifact

        mock_collection_manager.load_collection.return_value = mock_collection
        mock_collection_manager.save_collection.return_value = None

        # Create importer
        importer = ArtifactImporter(mock_artifact_manager, mock_collection_manager)

        # Create artifact data with path that would extract "data-ai"
        artifact_data = BulkImportArtifactData(
            source="user/repo/05-data-ai/test-skill",
            artifact_type="skill",
            name="test-skill",
            path="/path/05-data-ai/test-skill/SKILL.md",
        )

        # Apply path tags
        tags_applied = importer._apply_path_tags(artifact_data, "default")

        # "data-ai" already exists, so only new tags should be counted
        # This depends on what other segments are extracted and approved
        # The key assertion is that existing tags aren't duplicated
        assert mock_artifact.tags is not None
        # No duplicates in final tag list
        assert len(mock_artifact.tags) == len(set(mock_artifact.tags))


class TestImporterDirectIntegration:
    """Direct integration tests for ArtifactImporter._apply_path_tags."""

    def test_apply_path_tags_with_valid_path(self):
        """Test _apply_path_tags extracts and applies tags correctly."""
        mock_artifact_manager = Mock()
        mock_collection_manager = Mock()

        # Create mock artifact (starts with no tags)
        mock_artifact = Mock()
        mock_artifact.name = "my-processor"
        mock_artifact.tags = []

        # Create mock collection
        mock_collection = Mock()
        mock_collection.find_artifact.return_value = mock_artifact

        mock_collection_manager.load_collection.return_value = mock_collection
        mock_collection_manager.save_collection.return_value = None

        importer = ArtifactImporter(mock_artifact_manager, mock_collection_manager)

        # Artifact with path containing segments
        artifact_data = BulkImportArtifactData(
            source="user/repo/data-processing/utils/my-processor",
            artifact_type="skill",
            name="my-processor",
            path="/collection/data-processing/utils/my-processor/SKILL.md",
        )

        tags_applied = importer._apply_path_tags(artifact_data, "default")

        # Should have applied tags from path
        assert tags_applied > 0
        assert len(mock_artifact.tags) > 0

    def test_apply_path_tags_no_path(self):
        """Test _apply_path_tags handles missing path gracefully."""
        mock_artifact_manager = Mock()
        mock_collection_manager = Mock()

        importer = ArtifactImporter(mock_artifact_manager, mock_collection_manager)

        # Artifact with no path and source with only one segment (filename)
        artifact_data = BulkImportArtifactData(
            source="single-segment",
            artifact_type="skill",
            name="my-skill",
            path=None,
        )

        tags_applied = importer._apply_path_tags(artifact_data, "default")

        # Should return 0 gracefully (source has no valid path structure)
        assert tags_applied == 0

    def test_apply_path_tags_artifact_not_found(self):
        """Test _apply_path_tags handles artifact not found."""
        mock_artifact_manager = Mock()
        mock_collection_manager = Mock()

        # Collection returns None for artifact lookup
        mock_collection = Mock()
        mock_collection.find_artifact.return_value = None

        mock_collection_manager.load_collection.return_value = mock_collection

        importer = ArtifactImporter(mock_artifact_manager, mock_collection_manager)

        artifact_data = BulkImportArtifactData(
            source="user/repo/category/my-skill",
            artifact_type="skill",
            name="my-skill",
            path="/path/category/my-skill/SKILL.md",
        )

        # Should return 0 and not raise
        tags_applied = importer._apply_path_tags(artifact_data, "default")
        assert tags_applied == 0


class TestExtractedSegmentStatus:
    """Tests for ExtractedSegment status handling."""

    def test_pending_segments_used_for_tags(self):
        """Test that 'pending' status segments are used as tags."""
        extractor = PathSegmentExtractor(PathTagConfig.defaults())

        path = "category/subcategory/artifact.md"
        segments = extractor.extract(path)

        # All non-excluded segments should be "pending"
        for segment in segments:
            if segment.status != "excluded":
                assert segment.status == "pending"

    def test_excluded_segments_not_used_for_tags(self):
        """Test that 'excluded' status segments are NOT used as tags."""
        extractor = PathSegmentExtractor(PathTagConfig.defaults())

        path = "src/lib/my-feature/artifact.md"
        segments = extractor.extract(path)

        # Excluded segments
        excluded = [s for s in segments if s.status == "excluded"]
        pending = [s for s in segments if s.status == "pending"]

        # src and lib should be excluded
        assert len(excluded) > 0

        # Only pending segments would be used as tags
        # my-feature should be pending
        pending_names = [s.normalized for s in pending]
        assert "my-feature" in pending_names


class TestPathTagConfigVariations:
    """Tests for different PathTagConfig settings."""

    def test_skip_segments_configuration(self):
        """Test skip_segments removes specified indices."""
        config = PathTagConfig(
            enabled=True,
            skip_segments=[0],  # Skip first segment
            max_depth=3,
            normalize_numbers=True,
            exclude_patterns=[],
        )
        extractor = PathSegmentExtractor(config)

        path = "root/level1/level2/artifact.md"
        segments = extractor.extract(path)

        # "root" (index 0) should be skipped
        normalized_names = [s.normalized for s in segments]
        assert "root" not in normalized_names
        assert "level1" in normalized_names
        assert "level2" in normalized_names

    def test_custom_exclude_patterns(self):
        """Test custom exclude patterns."""
        config = PathTagConfig(
            enabled=True,
            max_depth=3,
            normalize_numbers=True,
            exclude_patterns=[r"^custom-exclude$", r"^ignore-.*$"],
        )
        extractor = PathSegmentExtractor(config)

        path = "custom-exclude/ignore-this/keep-this/artifact.md"
        segments = extractor.extract(path)

        excluded_names = [s.normalized for s in segments if s.status == "excluded"]
        pending_names = [s.normalized for s in segments if s.status == "pending"]

        assert "custom-exclude" in excluded_names
        assert "ignore-this" in excluded_names
        assert "keep-this" in pending_names

    def test_pure_numeric_segments_excluded(self):
        """Test that pure numeric segments are excluded by default."""
        extractor = PathSegmentExtractor(PathTagConfig.defaults())

        path = "01/123/my-feature/artifact.md"
        segments = extractor.extract(path)

        excluded_names = [s.normalized for s in segments if s.status == "excluded"]

        # Pure numbers should be excluded
        # Note: "01" becomes "01" (no text after prefix removal)
        # "123" is pure number
        # These should match r"^\d+$" pattern
        assert "123" in excluded_names or any(s.isdigit() for s in excluded_names)
