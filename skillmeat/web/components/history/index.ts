/**
 * History components for version management
 *
 * Components for browsing snapshot history, comparing versions,
 * and performing rollback operations.
 */

// Timeline and metadata components
export { VersionTimeline, type VersionTimelineProps } from './version-timeline';
export { SnapshotMetadata } from './snapshot-metadata';
export type { SnapshotMetadataProps } from './snapshot-metadata';

// Comparison view
export { VersionComparisonView, type VersionComparisonViewProps } from './version-comparison-view';

// Rollback dialog
export { RollbackDialog, type RollbackDialogProps } from './rollback-dialog';

// Container component
export { SnapshotHistoryTab, type SnapshotHistoryTabProps } from './snapshot-history-tab';
