/**
 * Sync Status Components
 *
 * Components for the 3-panel artifact synchronization UI.
 * Used in the Sync Status tab of the unified entity modal.
 */

// Main composite component
export { SyncStatusTab } from './sync-status-tab';
export type { SyncStatusTabProps } from './sync-status-tab';

// Sub-components
export { ArtifactFlowBanner } from './artifact-flow-banner';
export type { ArtifactFlowBannerProps } from './artifact-flow-banner';

export { ComparisonSelector } from './comparison-selector';
export type { ComparisonSelectorProps, ComparisonScope } from './comparison-selector';

export { DriftAlertBanner } from './drift-alert-banner';
export type { DriftAlertBannerProps, DriftStatus } from './drift-alert-banner';

export { FilePreviewPane } from './file-preview-pane';
export type { FilePreviewPaneProps } from './file-preview-pane';

export { SyncActionsFooter } from './sync-actions-footer';
export type { SyncActionsFooterProps } from './sync-actions-footer';

export { SyncConfirmationDialog } from './sync-confirmation-dialog';
export type { SyncConfirmationDialogProps } from './sync-confirmation-dialog';
