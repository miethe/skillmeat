"""Tests for VersionMergeService."""

import tempfile
from pathlib import Path

import pytest

from skillmeat.core.version_merge import VersionMergeService
from skillmeat.core.version import VersionManager
from skillmeat.core.collection import CollectionManager
from skillmeat.storage.snapshot import SnapshotManager


class TestVersionMergeService:
    """Test VersionMergeService functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def collection_setup(self, temp_dir):
        """Set up collection manager and version manager for testing."""
        # Create collection structure
        collection_path = temp_dir / "collections" / "test"
        collection_path.mkdir(parents=True, exist_ok=True)

        # Create some test files
        (collection_path / "skills").mkdir(exist_ok=True)
        (collection_path / "skills" / "test.md").write_text("# Test Skill")

        # Create snapshots directory
        snapshots_dir = temp_dir / "snapshots"
        snapshots_dir.mkdir(parents=True, exist_ok=True)

        # Create managers
        snapshot_mgr = SnapshotManager(snapshots_dir)

        # Create a minimal collection manager (we'll mock config)
        collection_mgr = CollectionManager()
        # Override collection path for testing
        original_get_path = collection_mgr.config.get_collection_path
        collection_mgr.config.get_collection_path = lambda name: collection_path

        version_mgr = VersionManager(
            collection_mgr=collection_mgr, snapshot_mgr=snapshot_mgr
        )

        return {
            "collection_path": collection_path,
            "snapshots_dir": snapshots_dir,
            "snapshot_mgr": snapshot_mgr,
            "version_mgr": version_mgr,
            "collection_mgr": collection_mgr,
        }

    def test_service_initialization(self, collection_setup):
        """Test VersionMergeService initialization."""
        version_mgr = collection_setup["version_mgr"]

        # Test with provided version manager
        service = VersionMergeService(version_mgr=version_mgr)
        assert service.version_mgr is version_mgr
        assert service.merge_engine is not None
        assert service.snapshot_mgr is not None

    def test_service_initialization_defaults(self):
        """Test VersionMergeService initialization with defaults."""
        # Test with default managers
        service = VersionMergeService()
        assert service.version_mgr is not None
        assert service.merge_engine is not None
        assert service.snapshot_mgr is not None

    def test_analyze_merge_safety_snapshot_not_found(self, collection_setup):
        """Test analyze_merge_safety raises error for missing snapshot."""
        version_mgr = collection_setup["version_mgr"]
        service = VersionMergeService(version_mgr=version_mgr)

        with pytest.raises(ValueError, match="not found"):
            service.analyze_merge_safety(
                base_snapshot_id="nonexistent",
                local_collection="test",
                remote_snapshot_id="also-nonexistent",
            )

    def test_merge_with_conflict_detection_snapshot_not_found(self, collection_setup):
        """Test merge_with_conflict_detection raises error for missing snapshot."""
        version_mgr = collection_setup["version_mgr"]
        service = VersionMergeService(version_mgr=version_mgr)

        with pytest.raises(ValueError, match="not found"):
            service.merge_with_conflict_detection(
                base_snapshot_id="nonexistent",
                local_collection="test",
                remote_snapshot_id="also-nonexistent",
            )

    def test_get_merge_preview_snapshot_not_found(self, collection_setup):
        """Test get_merge_preview raises error for missing snapshot."""
        version_mgr = collection_setup["version_mgr"]
        service = VersionMergeService(version_mgr=version_mgr)

        with pytest.raises(ValueError, match="not found|Snapshot not found"):
            service.get_merge_preview(
                base_snapshot_id="nonexistent",
                local_collection="test",
                remote_snapshot_id="also-nonexistent",
            )

    def test_resolve_conflict_use_local(self, collection_setup):
        """Test resolve_conflict with use_local strategy."""
        from skillmeat.models import ConflictMetadata

        service = VersionMergeService()
        conflict = ConflictMetadata(
            file_path="test.txt",
            conflict_type="content",
            base_content="base",
            local_content="local version",
            remote_content="remote version",
        )

        # This should succeed (returns True)
        result = service.resolve_conflict(conflict, "use_local")
        assert result is True

    def test_resolve_conflict_use_remote(self, collection_setup):
        """Test resolve_conflict with use_remote strategy."""
        from skillmeat.models import ConflictMetadata

        service = VersionMergeService()
        conflict = ConflictMetadata(
            file_path="test.txt",
            conflict_type="content",
            base_content="base",
            local_content="local version",
            remote_content="remote version",
        )

        result = service.resolve_conflict(conflict, "use_remote")
        assert result is True

    def test_resolve_conflict_use_base(self, collection_setup):
        """Test resolve_conflict with use_base strategy."""
        from skillmeat.models import ConflictMetadata

        service = VersionMergeService()
        conflict = ConflictMetadata(
            file_path="test.txt",
            conflict_type="content",
            base_content="base version",
            local_content="local",
            remote_content="remote",
        )

        result = service.resolve_conflict(conflict, "use_base")
        assert result is True

    def test_resolve_conflict_custom(self, collection_setup):
        """Test resolve_conflict with custom content."""
        from skillmeat.models import ConflictMetadata

        service = VersionMergeService()
        conflict = ConflictMetadata(
            file_path="test.txt",
            conflict_type="content",
            base_content="base",
            local_content="local",
            remote_content="remote",
        )

        result = service.resolve_conflict(
            conflict, "custom", custom_content="manually merged content"
        )
        assert result is True

    def test_resolve_conflict_custom_no_content(self, collection_setup):
        """Test resolve_conflict with custom strategy but no content."""
        from skillmeat.models import ConflictMetadata

        service = VersionMergeService()
        conflict = ConflictMetadata(
            file_path="test.txt",
            conflict_type="content",
            base_content="base",
            local_content="local",
            remote_content="remote",
        )

        with pytest.raises(ValueError, match="custom_content required"):
            service.resolve_conflict(conflict, "custom")

    def test_resolve_conflict_invalid_strategy(self, collection_setup):
        """Test resolve_conflict with invalid strategy."""
        from skillmeat.models import ConflictMetadata

        service = VersionMergeService()
        conflict = ConflictMetadata(
            file_path="test.txt",
            conflict_type="content",
            base_content="base",
            local_content="local",
            remote_content="remote",
        )

        with pytest.raises(ValueError, match="Invalid resolution strategy"):
            service.resolve_conflict(conflict, "invalid_strategy")

    def test_resolve_conflict_none_content(self, collection_setup):
        """Test resolve_conflict when selected content is None."""
        from skillmeat.models import ConflictMetadata

        service = VersionMergeService()
        conflict = ConflictMetadata(
            file_path="test.txt",
            conflict_type="deletion",
            base_content="base",
            local_content=None,  # File deleted locally
            remote_content="remote",
        )

        # Should return False when content is None
        result = service.resolve_conflict(conflict, "use_local")
        assert result is False


class TestMergeSafetyAnalysis:
    """Test MergeSafetyAnalysis dataclass."""

    def test_is_safe_property(self):
        """Test is_safe property calculation."""
        from skillmeat.models import MergeSafetyAnalysis

        # Safe merge: auto-mergeable with no conflicts
        safe_analysis = MergeSafetyAnalysis(
            can_auto_merge=True,
            auto_mergeable_count=5,
            conflict_count=0,
        )
        assert safe_analysis.is_safe is True

        # Unsafe merge: has conflicts
        unsafe_analysis = MergeSafetyAnalysis(
            can_auto_merge=False,
            auto_mergeable_count=3,
            conflict_count=2,
        )
        assert unsafe_analysis.is_safe is False

        # Edge case: can auto merge but has conflicts (shouldn't happen)
        edge_case = MergeSafetyAnalysis(
            can_auto_merge=True,
            auto_mergeable_count=3,
            conflict_count=1,
        )
        assert edge_case.is_safe is False


class TestVersionMergeResult:
    """Test VersionMergeResult dataclass."""

    def test_basic_fields(self):
        """Test VersionMergeResult basic fields."""
        from skillmeat.models import VersionMergeResult

        result = VersionMergeResult(
            success=True,
            pre_merge_snapshot_id="snap-123",
            files_merged=["file1.txt", "file2.txt"],
        )

        assert result.success is True
        assert result.pre_merge_snapshot_id == "snap-123"
        assert len(result.files_merged) == 2
        assert result.merge_result is None
        assert result.error is None


class TestMergePreview:
    """Test MergePreview dataclass."""

    def test_basic_fields(self):
        """Test MergePreview basic fields."""
        from skillmeat.models import MergePreview

        preview = MergePreview(
            base_snapshot_id="snap-base",
            remote_snapshot_id="snap-remote",
            files_added=["new1.txt", "new2.txt"],
            files_removed=["old.txt"],
            files_changed=["changed.txt"],
            can_auto_merge=True,
        )

        assert preview.base_snapshot_id == "snap-base"
        assert preview.remote_snapshot_id == "snap-remote"
        assert len(preview.files_added) == 2
        assert len(preview.files_removed) == 1
        assert len(preview.files_changed) == 1
        assert preview.can_auto_merge is True
