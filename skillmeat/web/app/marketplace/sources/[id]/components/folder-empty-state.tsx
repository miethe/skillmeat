'use client';

/**
 * FolderEmptyState Component
 *
 * Displays an empty state message when a folder has no importable artifacts.
 * Shows different states based on whether filters are active:
 * - No artifacts: Shows folder icon and message to select a different folder
 * - Filtered out: Shows search/filter icon with unfiltered count and clear filters button
 */

import { FolderOpen, SearchX } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

// ============================================================================
// Types
// ============================================================================

/**
 * Props for FolderEmptyState component.
 */
export interface FolderEmptyStateProps {
  /** Folder name for context */
  folderName: string;
  /** Whether filters are currently applied */
  hasActiveFilters: boolean;
  /** Total unfiltered count (to show "X filtered out" message) */
  unfilteredCount?: number;
  /** Callback to clear filters */
  onClearFilters?: () => void;
}

// ============================================================================
// Component
// ============================================================================

/**
 * FolderEmptyState - Displays empty state when folder has no matching artifacts
 *
 * Shows two distinct states:
 * 1. No artifacts (hasActiveFilters = false): Simple empty folder message
 * 2. Filtered out (hasActiveFilters = true): Shows unfiltered count and clear filters button
 *
 * @example
 * ```tsx
 * // No artifacts state
 * <FolderEmptyState
 *   folderName="src/skills"
 *   hasActiveFilters={false}
 * />
 *
 * // Filtered out state
 * <FolderEmptyState
 *   folderName="src/skills"
 *   hasActiveFilters={true}
 *   unfilteredCount={5}
 *   onClearFilters={handleClearFilters}
 * />
 * ```
 */
export function FolderEmptyState({
  folderName,
  hasActiveFilters,
  unfilteredCount,
  onClearFilters,
}: FolderEmptyStateProps) {
  // Filtered out state: show search icon and unfiltered count
  if (hasActiveFilters) {
    return (
      <div className={cn('flex flex-col items-center justify-center py-12')}>
        <SearchX className={cn('h-12 w-12 text-muted-foreground/50')} aria-hidden="true" />
        <h3 className={cn('mt-4 text-lg font-medium text-muted-foreground')}>
          No matching artifacts
        </h3>
        <p className={cn('mt-2 max-w-[300px] text-center text-sm text-muted-foreground')}>
          {unfilteredCount ? `${unfilteredCount} artifact${unfilteredCount !== 1 ? 's' : ''} ` : ''}
          in "{folderName}" don't match your current filters.
        </p>
        {onClearFilters && (
          <Button
            onClick={onClearFilters}
            variant="outline"
            size="sm"
            className="mt-4"
            aria-label="Clear all active filters"
          >
            Clear Filters
          </Button>
        )}
      </div>
    );
  }

  // No artifacts state: show folder icon and simple message
  return (
    <div className={cn('flex flex-col items-center justify-center py-12')}>
      <FolderOpen className={cn('h-12 w-12 text-muted-foreground/50')} aria-hidden="true" />
      <h3 className={cn('mt-4 text-lg font-medium text-muted-foreground')}>
        No artifacts in this folder
      </h3>
      <p className={cn('mt-2 max-w-[300px] text-center text-sm text-muted-foreground')}>
        This folder contains no importable artifacts. Try selecting a different folder from the
        tree.
      </p>
    </div>
  );
}
