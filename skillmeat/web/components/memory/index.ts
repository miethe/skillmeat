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

export { ConfirmActionDialog } from './confirm-action-dialog';
export type { ConfirmActionDialogProps } from './confirm-action-dialog';

export { MemoryFormModal } from './memory-form-modal';
export type { MemoryFormModalProps } from './memory-form-modal';

export { MergeModal } from './merge-modal';
export type { MergeModalProps } from './merge-modal';

export {
  getConfidenceTier,
  getConfidenceColorClasses,
  getConfidenceBarColor,
  formatRelativeTime,
  getStatusDotClass,
  STATUS_DOT_CLASSES,
} from './memory-utils';
export type { ConfidenceTier } from './memory-utils';
