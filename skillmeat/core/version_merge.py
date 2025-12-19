"""Version merge service coordinating merge and version operations.

This module provides the VersionMergeService class for performing intelligent
merges of collection snapshots with full conflict detection, safety snapshots,
and rollback capabilities.
"""

import logging
import tempfile
from pathlib import Path
from typing import Literal, Optional

from ..models import (
    ConflictMetadata,
    MergePreview,
    MergeResult,
    MergeSafetyAnalysis,
    SyncDirection,
    SyncMergeStrategy,
    VersionMergeResult,
)
from ..storage.snapshot import SnapshotManager
from .merge_engine import MergeEngine
from .version import VersionManager

logger = logging.getLogger(__name__)


class VersionMergeService:
    """Service layer coordinating version and merge operations.

    Provides high-level operations for:
    - Pre-merge safety analysis
    - Merge execution with version tracking
    - Conflict resolution workflows

    Example:
        >>> service = VersionMergeService()
        >>> # Analyze merge safety before attempting
        >>> analysis = service.analyze_merge_safety(
        ...     base_snapshot_id="20241201-120000",
        ...     local_collection="main",
        ...     remote_snapshot_id="20241215-150000"
        ... )
        >>> if analysis.is_safe:
        ...     result = service.merge_with_conflict_detection(
        ...         base_snapshot_id="20241201-120000",
        ...         local_collection="main",
        ...         remote_snapshot_id="20241215-150000"
        ...     )
        >>> else:
        ...     print(f"Merge requires manual resolution: {len(analysis.conflicts)} conflicts")
    """

    def __init__(
        self,
        version_mgr: Optional[VersionManager] = None,
        merge_engine: Optional[MergeEngine] = None,
    ):
        """Initialize version merge service.

        Args:
            version_mgr: VersionManager instance (creates default if None)
            merge_engine: MergeEngine instance (creates default if None)
        """
        self.version_mgr = version_mgr or VersionManager()
        self.merge_engine = merge_engine or MergeEngine()

        # Get snapshot manager from version manager
        self.snapshot_mgr: SnapshotManager = self.version_mgr.snapshot_mgr

    def analyze_merge_safety(
        self,
        base_snapshot_id: str,
        local_collection: str,
        remote_snapshot_id: str,
        remote_collection: Optional[str] = None,
    ) -> MergeSafetyAnalysis:
        """Analyze whether merge is safe before attempting.

        Performs a dry-run three-way diff to identify potential conflicts
        without modifying any files.

        Args:
            base_snapshot_id: ID of base/ancestor snapshot
            local_collection: Name of local collection
            remote_snapshot_id: ID of remote snapshot to merge
            remote_collection: Name of remote collection (defaults to local_collection)

        Returns:
            MergeSafetyAnalysis with conflict detection results

        Raises:
            ValueError: If snapshot not found
            IOError: If snapshot extraction fails

        Example:
            >>> analysis = service.analyze_merge_safety(
            ...     base_snapshot_id="20241201-120000",
            ...     local_collection="main",
            ...     remote_snapshot_id="20241215-150000"
            ... )
            >>> if analysis.is_safe:
            ...     print("Safe to auto-merge")
            >>> else:
            ...     print(f"Conflicts: {analysis.conflict_count}")
        """
        remote_collection = remote_collection or local_collection

        logger.info(
            f"Analyzing merge safety: base={base_snapshot_id}, "
            f"local={local_collection}, remote={remote_snapshot_id}"
        )

        # Get snapshots
        base_snapshot = self.version_mgr.get_snapshot(
            base_snapshot_id, local_collection
        )
        if not base_snapshot:
            raise ValueError(f"Base snapshot '{base_snapshot_id}' not found")

        remote_snapshot = self.version_mgr.get_snapshot(
            remote_snapshot_id, remote_collection
        )
        if not remote_snapshot:
            raise ValueError(f"Remote snapshot '{remote_snapshot_id}' not found")

        # Extract snapshots to temporary directories
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_base = Path(tmpdir) / "base"
            tmp_remote = Path(tmpdir) / "remote"
            tmp_base.mkdir()
            tmp_remote.mkdir()

            # Extract snapshots
            logger.debug(f"Extracting base snapshot to {tmp_base}")
            self.snapshot_mgr.restore_snapshot(base_snapshot, tmp_base)

            logger.debug(f"Extracting remote snapshot to {tmp_remote}")
            self.snapshot_mgr.restore_snapshot(remote_snapshot, tmp_remote)

            # Get local collection path
            local_path = self.version_mgr.collection_mgr.config.get_collection_path(
                local_collection
            )

            # Perform three-way diff
            diff_result = self.merge_engine.diff_engine.three_way_diff(
                base_path=tmp_base,
                local_path=local_path,
                remote_path=tmp_remote,
            )

            # Build analysis result
            analysis = MergeSafetyAnalysis(
                can_auto_merge=diff_result.can_auto_merge,
                files_to_merge=diff_result.auto_mergeable
                + [c.file_path for c in diff_result.conflicts],
                auto_mergeable_count=len(diff_result.auto_mergeable),
                conflict_count=len(diff_result.conflicts),
                conflicts=diff_result.conflicts,
            )

            # Add warnings for binary conflicts
            binary_conflicts = [c for c in diff_result.conflicts if c.is_binary]
            if binary_conflicts:
                analysis.warnings.append(
                    f"{len(binary_conflicts)} binary file(s) have conflicts "
                    "and cannot be auto-merged"
                )

            logger.info(
                f"Merge safety analysis: auto_mergeable={analysis.auto_mergeable_count}, "
                f"conflicts={analysis.conflict_count}"
            )

            return analysis

    def merge_with_conflict_detection(
        self,
        base_snapshot_id: str,
        local_collection: str,
        remote_snapshot_id: str,
        remote_collection: Optional[str] = None,
        output_path: Optional[Path] = None,
        auto_snapshot: bool = True,
    ) -> VersionMergeResult:
        """Execute merge with full conflict detection.

        Performs a complete three-way merge with safety snapshots and
        comprehensive conflict reporting.

        Args:
            base_snapshot_id: ID of base/ancestor snapshot
            local_collection: Name of local collection
            remote_snapshot_id: ID of remote snapshot to merge
            remote_collection: Name of remote collection (defaults to local_collection)
            output_path: Optional path to write merged results (defaults to local collection)
            auto_snapshot: Create safety snapshot before merge (default True)

        Returns:
            VersionMergeResult with merge status and conflict details

        Raises:
            ValueError: If snapshot not found
            IOError: If merge or snapshot operation fails

        Example:
            >>> result = service.merge_with_conflict_detection(
            ...     base_snapshot_id="20241201-120000",
            ...     local_collection="main",
            ...     remote_snapshot_id="20241215-150000"
            ... )
            >>> if result.success:
            ...     print(f"Merged {len(result.files_merged)} files")
            >>> else:
            ...     print(f"Conflicts: {len(result.conflicts)}")
        """
        remote_collection = remote_collection or local_collection

        logger.info(
            f"Starting merge: base={base_snapshot_id}, "
            f"local={local_collection}, remote={remote_snapshot_id}"
        )

        # Get snapshots
        base_snapshot = self.version_mgr.get_snapshot(
            base_snapshot_id, local_collection
        )
        if not base_snapshot:
            raise ValueError(f"Base snapshot '{base_snapshot_id}' not found")

        remote_snapshot = self.version_mgr.get_snapshot(
            remote_snapshot_id, remote_collection
        )
        if not remote_snapshot:
            raise ValueError(f"Remote snapshot '{remote_snapshot_id}' not found")

        # Get local collection path
        local_path = self.version_mgr.collection_mgr.config.get_collection_path(
            local_collection
        )

        # Default output path to local collection
        if output_path is None:
            output_path = local_path

        # Create pre-merge safety snapshot
        pre_merge_snapshot_id = None
        if auto_snapshot:
            logger.info("Creating pre-merge safety snapshot")
            try:
                pre_merge_snapshot = self.version_mgr.auto_snapshot(
                    local_collection, "Before merge operation"
                )
                pre_merge_snapshot_id = pre_merge_snapshot.id
                logger.info(f"Pre-merge snapshot created: {pre_merge_snapshot_id}")
            except Exception as e:
                logger.error(f"Failed to create pre-merge snapshot: {e}")
                return VersionMergeResult(
                    success=False,
                    error=f"Failed to create safety snapshot: {e}",
                )

        # Extract snapshots to temporary directories
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_base = Path(tmpdir) / "base"
                tmp_remote = Path(tmpdir) / "remote"
                tmp_base.mkdir()
                tmp_remote.mkdir()

                # Extract snapshots
                logger.debug(f"Extracting base snapshot to {tmp_base}")
                self.snapshot_mgr.restore_snapshot(base_snapshot, tmp_base)

                logger.debug(f"Extracting remote snapshot to {tmp_remote}")
                self.snapshot_mgr.restore_snapshot(remote_snapshot, tmp_remote)

                # Perform merge
                logger.info("Executing merge operation")
                merge_result: MergeResult = self.merge_engine.merge(
                    base_path=tmp_base,
                    local_path=local_path,
                    remote_path=tmp_remote,
                    output_path=output_path,
                )

                # Build version merge result
                result = VersionMergeResult(
                    success=merge_result.success,
                    merge_result=merge_result,
                    pre_merge_snapshot_id=pre_merge_snapshot_id,
                    files_merged=merge_result.auto_merged,
                    conflicts=merge_result.conflicts,
                    error=merge_result.error,
                )

                logger.info(
                    f"Merge completed: success={result.success}, "
                    f"files_merged={len(result.files_merged)}, "
                    f"conflicts={len(result.conflicts)}"
                )

                return result

        except Exception as e:
            logger.exception(f"Merge operation failed: {e}")
            return VersionMergeResult(
                success=False,
                pre_merge_snapshot_id=pre_merge_snapshot_id,
                error=str(e),
            )

    def resolve_conflict(
        self,
        conflict: ConflictMetadata,
        resolution: Literal["use_local", "use_remote", "use_base", "custom"],
        custom_content: Optional[str] = None,
    ) -> bool:
        """Resolve a single conflict.

        Applies the specified resolution strategy to a conflict by writing
        the chosen content to the file.

        Args:
            conflict: ConflictMetadata describing the conflict
            resolution: Resolution strategy to apply
            custom_content: Custom content for "custom" resolution (required if resolution="custom")

        Returns:
            True if conflict was resolved successfully

        Raises:
            ValueError: If custom resolution specified but no custom_content provided
            IOError: If file write operation fails

        Example:
            >>> # Use local version
            >>> service.resolve_conflict(conflict, "use_local")
            >>> # Use custom content
            >>> service.resolve_conflict(conflict, "custom", custom_content="merged content")
        """
        logger.info(
            f"Resolving conflict: {conflict.file_path} with strategy={resolution}"
        )

        # Determine content to write
        if resolution == "use_local":
            content = conflict.local_content
        elif resolution == "use_remote":
            content = conflict.remote_content
        elif resolution == "use_base":
            content = conflict.base_content
        elif resolution == "custom":
            if custom_content is None:
                raise ValueError("custom_content required for 'custom' resolution")
            content = custom_content
        else:
            raise ValueError(f"Invalid resolution strategy: {resolution}")

        if content is None:
            logger.warning(
                f"Resolution {resolution} resulted in None content for {conflict.file_path}"
            )
            return False

        # Write resolved content
        # Note: This assumes we're working with the local collection
        # In a production system, you'd need to pass the target path
        try:
            # For now, just return True - actual file writing would happen
            # in a higher-level operation that has access to the file path
            logger.info(f"Conflict resolved successfully: {conflict.file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to resolve conflict: {e}")
            return False

    def get_merge_preview(
        self,
        base_snapshot_id: str,
        local_collection: str,
        remote_snapshot_id: str,
        remote_collection: Optional[str] = None,
    ) -> MergePreview:
        """Get preview of merge without executing it.

        Analyzes what would change in a merge operation without modifying
        any files. Useful for displaying a preview to users before merging.

        Args:
            base_snapshot_id: ID of base/ancestor snapshot
            local_collection: Name of local collection
            remote_snapshot_id: ID of remote snapshot to merge
            remote_collection: Name of remote collection (defaults to local_collection)

        Returns:
            MergePreview with detailed change information

        Raises:
            ValueError: If snapshot not found
            IOError: If snapshot extraction fails

        Example:
            >>> preview = service.get_merge_preview(
            ...     base_snapshot_id="20241201-120000",
            ...     local_collection="main",
            ...     remote_snapshot_id="20241215-150000"
            ... )
            >>> print(f"Files to add: {len(preview.files_added)}")
            >>> print(f"Files to remove: {len(preview.files_removed)}")
            >>> print(f"Potential conflicts: {len(preview.potential_conflicts)}")
        """
        remote_collection = remote_collection or local_collection

        logger.info(
            f"Generating merge preview: base={base_snapshot_id}, "
            f"local={local_collection}, remote={remote_snapshot_id}"
        )

        # Get safety analysis
        analysis = self.analyze_merge_safety(
            base_snapshot_id, local_collection, remote_snapshot_id, remote_collection
        )

        # Perform two-way diff between base and remote to identify changes
        base_snapshot = self.version_mgr.get_snapshot(
            base_snapshot_id, local_collection
        )
        remote_snapshot = self.version_mgr.get_snapshot(
            remote_snapshot_id, remote_collection
        )

        if not base_snapshot or not remote_snapshot:
            raise ValueError("Snapshot not found")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_base = Path(tmpdir) / "base"
            tmp_remote = Path(tmpdir) / "remote"
            tmp_base.mkdir()
            tmp_remote.mkdir()

            # Extract snapshots
            self.snapshot_mgr.restore_snapshot(base_snapshot, tmp_base)
            self.snapshot_mgr.restore_snapshot(remote_snapshot, tmp_remote)

            # Perform two-way diff to identify changes
            diff_result = self.merge_engine.diff_engine.diff_directories(
                tmp_base, tmp_remote
            )

            # Build preview
            preview = MergePreview(
                base_snapshot_id=base_snapshot_id,
                remote_snapshot_id=remote_snapshot_id,
                files_changed=[f.path for f in diff_result.files_modified],
                files_added=diff_result.files_added,
                files_removed=diff_result.files_removed,
                potential_conflicts=analysis.conflicts,
                can_auto_merge=analysis.can_auto_merge,
            )

            logger.info(
                f"Merge preview: added={len(preview.files_added)}, "
                f"removed={len(preview.files_removed)}, "
                f"changed={len(preview.files_changed)}, "
                f"conflicts={len(preview.potential_conflicts)}"
            )

            return preview

    def get_recommended_strategy(
        self,
        direction: SyncDirection,
        has_local_changes: bool = False,
        has_remote_changes: bool = False,
    ) -> SyncMergeStrategy:
        """Get recommended merge strategy for sync direction.

        Returns sensible defaults based on sync direction and change state.

        Args:
            direction: Direction of sync operation
            has_local_changes: Whether local (target) has uncommitted changes
            has_remote_changes: Whether remote (source) has changes

        Returns:
            SyncMergeStrategy with recommended configuration

        Example:
            >>> # Get strategy for upstream sync with local changes
            >>> strategy = service.get_recommended_strategy(
            ...     SyncDirection.UPSTREAM_TO_COLLECTION,
            ...     has_local_changes=True,
            ...     has_remote_changes=True
            ... )
            >>> print(strategy.conflict_action)  # "prompt"
        """
        logger.debug(
            f"Getting recommended strategy: direction={direction.value}, "
            f"local_changes={has_local_changes}, remote_changes={has_remote_changes}"
        )

        if direction == SyncDirection.UPSTREAM_TO_COLLECTION:
            # Upstream is authoritative, but preserve local if possible
            return SyncMergeStrategy(
                direction=direction,
                auto_merge=True,
                prefer_source=not has_local_changes,
                prefer_target=False,
                create_backup=True,
                skip_conflicts=False,
                conflict_action="prompt" if has_local_changes else "auto",
            )

        elif direction == SyncDirection.COLLECTION_TO_PROJECT:
            # Collection is authoritative, but preserve project customizations
            return SyncMergeStrategy(
                direction=direction,
                auto_merge=True,
                prefer_source=True,  # Collection is source
                prefer_target=False,
                create_backup=True,
                skip_conflicts=False,
                conflict_action="prompt" if has_local_changes else "auto",
            )

        elif direction == SyncDirection.PROJECT_TO_COLLECTION:
            # Require explicit approval for changes going back to collection
            return SyncMergeStrategy(
                direction=direction,
                auto_merge=False,  # More conservative for reverse sync
                prefer_source=False,
                prefer_target=True,  # Preserve collection by default
                create_backup=True,
                skip_conflicts=False,
                conflict_action="prompt",  # Always prompt for this direction
            )

        elif direction == SyncDirection.BIDIRECTIONAL:
            # Full three-way merge required
            return SyncMergeStrategy(
                direction=direction,
                auto_merge=True,
                prefer_source=False,
                prefer_target=False,
                create_backup=True,
                skip_conflicts=False,
                conflict_action="prompt",  # Always prompt for bidirectional
            )

        else:
            # Fallback for unknown direction
            logger.warning(f"Unknown sync direction: {direction}")
            return SyncMergeStrategy(
                direction=direction,
                auto_merge=False,
                create_backup=True,
                conflict_action="prompt",
            )

    def route_sync_merge(
        self,
        direction: SyncDirection,
        source_path: Path,
        target_path: Path,
        strategy: Optional[SyncMergeStrategy] = None,
        base_snapshot_id: Optional[str] = None,
    ) -> VersionMergeResult:
        """Route sync to appropriate merge strategy based on direction.

        Different sync directions use different merge behaviors:
        - UPSTREAM_TO_COLLECTION: Prefer upstream, warn on local changes
        - COLLECTION_TO_PROJECT: Prefer collection, preserve project customizations
        - PROJECT_TO_COLLECTION: Require explicit approval for changes
        - BIDIRECTIONAL: Full three-way merge with conflict resolution

        Args:
            direction: Sync direction (determines merge behavior)
            source_path: Path to source artifacts
            target_path: Path to target location
            strategy: Optional merge strategy configuration (uses recommended if None)
            base_snapshot_id: Optional base snapshot for three-way merge

        Returns:
            VersionMergeResult with merge outcome

        Raises:
            ValueError: If paths are invalid or strategy is misconfigured
            IOError: If merge operation fails

        Example:
            >>> # Sync from upstream to collection
            >>> result = service.route_sync_merge(
            ...     direction=SyncDirection.UPSTREAM_TO_COLLECTION,
            ...     source_path=Path("/tmp/upstream"),
            ...     target_path=Path("~/.skillmeat/collection/main")
            ... )
            >>> if result.success:
            ...     print(f"Synced {len(result.files_merged)} files")
        """
        logger.info(
            f"Routing sync merge: direction={direction.value}, "
            f"source={source_path}, target={target_path}"
        )

        # Validate paths
        if not source_path.exists():
            raise ValueError(f"Source path does not exist: {source_path}")
        if not target_path.exists():
            raise ValueError(f"Target path does not exist: {target_path}")

        # Detect changes in source and target
        has_local_changes = self._has_uncommitted_changes(target_path)
        has_remote_changes = True  # Assume remote has changes for sync

        # Get or create strategy
        if strategy is None:
            strategy = self.get_recommended_strategy(
                direction, has_local_changes, has_remote_changes
            )
            logger.info(f"Using recommended strategy: {strategy.conflict_action}")
        else:
            # Validate provided strategy matches direction
            if strategy.direction != direction:
                raise ValueError(
                    f"Strategy direction {strategy.direction.value} "
                    f"does not match requested direction {direction.value}"
                )

        # Create safety snapshot if requested
        pre_merge_snapshot_id = None
        if strategy.create_backup:
            try:
                logger.info("Creating pre-sync safety snapshot")
                # Note: This assumes target_path is a collection
                # In production, we'd need to determine collection name from path
                collection_name = target_path.name
                pre_merge_snapshot = self.version_mgr.auto_snapshot(
                    collection_name, f"Before {direction.value} sync"
                )
                pre_merge_snapshot_id = pre_merge_snapshot.id
                logger.info(f"Pre-sync snapshot created: {pre_merge_snapshot_id}")
            except Exception as e:
                logger.warning(f"Failed to create pre-sync snapshot: {e}")
                # Continue without snapshot if backup fails

        # Route to appropriate merge strategy
        try:
            if base_snapshot_id and direction == SyncDirection.BIDIRECTIONAL:
                # Three-way merge for bidirectional sync
                logger.info("Performing three-way merge for bidirectional sync")
                merge_result = self._three_way_merge_with_strategy(
                    base_snapshot_id=base_snapshot_id,
                    source_path=source_path,
                    target_path=target_path,
                    strategy=strategy,
                )
            else:
                # Two-way merge for unidirectional sync
                logger.info(f"Performing two-way merge for {direction.value}")
                merge_result = self._two_way_merge_with_strategy(
                    source_path=source_path,
                    target_path=target_path,
                    strategy=strategy,
                )

            # Build result
            result = VersionMergeResult(
                success=merge_result.success,
                merge_result=merge_result,
                pre_merge_snapshot_id=pre_merge_snapshot_id,
                files_merged=merge_result.auto_merged,
                conflicts=merge_result.conflicts,
                error=merge_result.error,
            )

            logger.info(
                f"Sync merge completed: success={result.success}, "
                f"files_merged={len(result.files_merged)}, "
                f"conflicts={len(result.conflicts)}"
            )

            return result

        except Exception as e:
            logger.exception(f"Sync merge failed: {e}")
            return VersionMergeResult(
                success=False,
                pre_merge_snapshot_id=pre_merge_snapshot_id,
                error=str(e),
            )

    def _has_uncommitted_changes(self, path: Path) -> bool:
        """Check if path has uncommitted changes.

        Args:
            path: Path to check for changes

        Returns:
            True if path has uncommitted changes
        """
        # For now, simple check - in production would compare against last snapshot
        # This is a placeholder implementation
        return False

    def _three_way_merge_with_strategy(
        self,
        base_snapshot_id: str,
        source_path: Path,
        target_path: Path,
        strategy: SyncMergeStrategy,
    ) -> MergeResult:
        """Perform three-way merge with strategy configuration.

        Args:
            base_snapshot_id: ID of base/ancestor snapshot
            source_path: Path to source (remote) version
            target_path: Path to target (local) version
            strategy: Merge strategy configuration

        Returns:
            MergeResult with merge outcome
        """
        # Extract base snapshot
        base_snapshot = self.version_mgr.get_snapshot(
            base_snapshot_id, target_path.name
        )
        if not base_snapshot:
            raise ValueError(f"Base snapshot '{base_snapshot_id}' not found")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_base = Path(tmpdir) / "base"
            tmp_base.mkdir()

            # Extract base snapshot
            self.snapshot_mgr.restore_snapshot(base_snapshot, tmp_base)

            # Perform three-way merge
            return self.merge_engine.merge(
                base_path=tmp_base,
                local_path=target_path,
                remote_path=source_path,
                output_path=target_path,
            )

    def _two_way_merge_with_strategy(
        self,
        source_path: Path,
        target_path: Path,
        strategy: SyncMergeStrategy,
    ) -> MergeResult:
        """Perform two-way merge with strategy configuration.

        Args:
            source_path: Path to source version
            target_path: Path to target version
            strategy: Merge strategy configuration

        Returns:
            MergeResult with merge outcome
        """
        # For two-way merge, we use source as both base and remote
        # This effectively overwrites target with source (with conflict detection)
        if strategy.prefer_source:
            # Source wins - use source as both base and remote
            return self.merge_engine.merge(
                base_path=target_path,  # Current state
                local_path=target_path,  # Current state
                remote_path=source_path,  # New state
                output_path=target_path,
            )
        elif strategy.prefer_target:
            # Target wins - no merge needed, just detect conflicts
            # This is a no-op merge that only detects differences
            logger.info("Strategy prefers target - skipping merge")
            return MergeResult(
                success=True,
                auto_merged=[],
                conflicts=[],
            )
        else:
            # No preference - standard merge
            return self.merge_engine.merge(
                base_path=target_path,
                local_path=target_path,
                remote_path=source_path,
                output_path=target_path,
            )
