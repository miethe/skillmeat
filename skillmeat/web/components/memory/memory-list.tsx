'use client';

/**
 * MemoryList Component
 *
 * Wrapper component that manages the memory list display including loading,
 * empty, and error states. Renders MemoryCard components in a scrollable
 * divide-y list with keyboard navigation support.
 *
 * Design spec reference: sections 3.6 and 3.7
 */

import {
  Brain,
  Plus,
  AlertTriangle,
  RefreshCw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { MemoryItemResponse } from '@/sdk/models/MemoryItemResponse';
import { MemoryCard } from './memory-card';
import { MemoryCardSkeleton } from './memory-card-skeleton';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface MemoryListProps {
  /** Array of memory items to display. */
  memories: MemoryItemResponse[];
  /** Whether the query is currently loading. */
  isLoading: boolean;
  /** Whether the query encountered an error. */
  isError: boolean;
  /** The error object if the query failed. */
  error?: Error | null;
  /** Callback to retry a failed query. */
  refetch: () => void;
  /** Set of currently selected memory IDs. */
  selectedIds: Set<string>;
  /** Index of the currently keyboard-focused item (-1 = none). */
  focusedIndex: number;
  /** Toggle selection for a given memory ID. */
  onToggleSelect: (id: string) => void;
  /** Approve (promote) a memory item. */
  onApprove: (id: string) => void;
  /** Reject (deprecate) a memory item. */
  onReject: (id: string) => void;
  /** Open edit for a memory item. */
  onEdit: (id: string) => void;
  /** Open merge dialog for a memory item. */
  onMerge: (id: string) => void;
  /** Click handler to select/focus a card (opens detail panel). */
  onCardClick: (id: string) => void;
  /** Callback to create a new memory (used in empty state CTA). */
  onCreateMemory: () => void;
}

// ---------------------------------------------------------------------------
// Skeleton count for loading state
// ---------------------------------------------------------------------------

const SKELETON_COUNT = 6;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * MemoryList -- renders the list of memory cards with loading/empty/error states.
 *
 * @example
 * ```tsx
 * <MemoryList
 *   memories={data?.items ?? []}
 *   isLoading={isLoading}
 *   isError={isError}
 *   error={error}
 *   refetch={refetch}
 *   selectedIds={selectedIds}
 *   focusedIndex={focusedIndex}
 *   onToggleSelect={toggleSelect}
 *   onApprove={handleApprove}
 *   onReject={handleReject}
 *   onEdit={handleEdit}
 *   onMerge={handleMerge}
 *   onCardClick={handleCardClick}
 *   onCreateMemory={handleCreateMemory}
 * />
 * ```
 */
export function MemoryList({
  memories,
  isLoading,
  isError,
  error,
  refetch,
  selectedIds,
  focusedIndex,
  onToggleSelect,
  onApprove,
  onReject,
  onEdit,
  onMerge,
  onCardClick,
  onCreateMemory,
}: MemoryListProps) {
  // ---------------------------------------------------------------------------
  // Loading State
  // ---------------------------------------------------------------------------
  if (isLoading) {
    return (
      <div className="divide-y" role="status" aria-label="Loading memories">
        {Array.from({ length: SKELETON_COUNT }).map((_, i) => (
          <MemoryCardSkeleton key={i} />
        ))}
        <span className="sr-only">Loading memory items...</span>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Error State
  // ---------------------------------------------------------------------------
  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center" role="alert">
        <div className="rounded-full bg-destructive/10 p-4 mb-4">
          <AlertTriangle className="h-8 w-8 text-destructive" aria-hidden="true" />
        </div>
        <h3 className="text-lg font-semibold">Failed to load memories</h3>
        <p className="mt-2 max-w-sm text-sm text-muted-foreground">
          {error?.message ?? 'An unexpected error occurred.'}
        </p>
        <Button variant="outline" className="mt-4" size="sm" onClick={refetch}>
          <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
          Retry
        </Button>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Empty State
  // ---------------------------------------------------------------------------
  if (!memories || memories.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="rounded-full bg-muted p-4 mb-4">
          <Brain className="h-8 w-8 text-muted-foreground" aria-hidden="true" />
        </div>
        <h3 className="text-lg font-semibold">No memories yet</h3>
        <p className="mt-2 max-w-sm text-sm text-muted-foreground">
          Memories are automatically extracted from agent sessions, or you can
          create them manually.
        </p>
        <Button className="mt-4" size="sm" onClick={onCreateMemory}>
          <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
          Create First Memory
        </Button>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Default: Scrollable List
  // ---------------------------------------------------------------------------
  return (
    <>
      <div className="sr-only" aria-live="polite" aria-atomic="true">
        {memories.length} {memories.length === 1 ? 'memory item' : 'memory items'} displayed
      </div>
      <div
        role="grid"
        aria-label="Memory items"
        aria-rowcount={memories.length}
        className="flex-1 overflow-y-auto divide-y"
      >
        {memories.map((memory, index) => (
          <MemoryCard
            key={memory.id}
            memory={memory}
            selected={selectedIds.has(memory.id)}
            focused={focusedIndex === index}
            onToggleSelect={onToggleSelect}
            onApprove={onApprove}
            onReject={onReject}
            onEdit={onEdit}
            onMerge={onMerge}
            onClick={onCardClick}
          />
        ))}
      </div>
    </>
  );
}
