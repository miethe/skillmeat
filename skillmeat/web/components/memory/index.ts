/**
 * Memory Components Barrel Export
 *
 * Central export point for all memory-related UI components.
 * Import from '@/components/memory' for clean imports.
 */

export { MemoryCard } from './memory-card';
export type { MemoryCardProps } from './memory-card';

export { MemoryTypeBadge } from './memory-type-badge';
export type { MemoryTypeBadgeProps } from './memory-type-badge';

export { MemoryCardSkeleton } from './memory-card-skeleton';

export { MemoryFilterBar } from './memory-filter-bar';
export type { MemoryFilterBarProps } from './memory-filter-bar';

export { MemoryList } from './memory-list';
export type { MemoryListProps } from './memory-list';

export { BatchActionBar } from './batch-action-bar';
export type { BatchActionBarProps } from './batch-action-bar';

export { MemoryDetailPanel } from './memory-detail-panel';
export type { MemoryDetailPanelProps } from './memory-detail-panel';

export { BaseMemoryModal } from './base-memory-modal';
export type { BaseMemoryModalProps } from './base-memory-modal';

export { MemoryDetailsModal } from './memory-details-modal';
export type { MemoryDetailsModalProps, MemoryDetailsTab } from './memory-details-modal';

export { ConfirmActionDialog } from './confirm-action-dialog';
export type { ConfirmActionDialogProps } from './confirm-action-dialog';

export { MemoryFormModal } from './memory-form-modal';
export type { MemoryFormModalProps } from './memory-form-modal';

export { MergeModal } from './merge-modal';
export type { MergeModalProps } from './merge-modal';

export { KeyboardHelpModal } from './keyboard-help-modal';
export type { KeyboardHelpModalProps } from './keyboard-help-modal';

export { ContextModulesTab } from './context-modules-tab';
export type { ContextModulesTabProps } from './context-modules-tab';

export { ModuleEditor } from './module-editor';
export type { ModuleEditorProps } from './module-editor';

export { EffectiveContextPreview } from './effective-context-preview';
export type { EffectiveContextPreviewProps } from './effective-context-preview';

export { ContextPackGenerator } from './context-pack-generator';
export type { ContextPackGeneratorProps } from './context-pack-generator';

export {
  getConfidenceTier,
  getConfidenceColorClasses,
  getConfidenceBarColor,
  formatRelativeTime,
  getStatusDotClass,
  STATUS_DOT_CLASSES,
} from './memory-utils';
export type { ConfidenceTier } from './memory-utils';
