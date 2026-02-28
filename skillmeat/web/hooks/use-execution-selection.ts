/**
 * useExecutionSelection
 *
 * Custom hook for managing multi-select state on the All Executions page.
 * Provides checkbox selection, select-all, clear, and derived helpers.
 */

'use client';

import { useState, useCallback, useMemo } from 'react';
import type { WorkflowExecution } from '@/types/workflow';

// ---------------------------------------------------------------------------
// Return type
// ---------------------------------------------------------------------------

export interface UseExecutionSelectionReturn {
  /** Set of selected execution IDs. */
  selectedIds: Set<string>;
  /** Returns true if the given execution ID is selected. */
  isSelected: (id: string) => boolean;
  /** Toggles selection for the given execution ID. */
  toggleSelection: (id: string) => void;
  /** Selects all executions in the provided list. */
  selectAll: () => void;
  /** Clears all selections. */
  clearSelection: () => void;
  /** True when at least one execution is selected. */
  hasSelection: boolean;
  /** Number of selected executions. */
  selectedCount: number;
  /** Array of WorkflowExecution objects for each selected ID. */
  selectedExecutions: WorkflowExecution[];
  /** True when every execution in the list is selected. */
  isAllSelected: boolean;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Manages multi-select state for a list of workflow executions.
 *
 * @param executions - The current list of executions to select from.
 *
 * @example
 * ```tsx
 * const { selectedIds, toggleSelection, hasSelection, selectedExecutions } =
 *   useExecutionSelection(executions);
 * ```
 */
export function useExecutionSelection(
  executions: WorkflowExecution[]
): UseExecutionSelectionReturn {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const isSelected = useCallback(
    (id: string) => selectedIds.has(id),
    [selectedIds]
  );

  const toggleSelection = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const selectAll = useCallback(() => {
    setSelectedIds(new Set(executions.map((e) => e.id)));
  }, [executions]);

  const clearSelection = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  const hasSelection = selectedIds.size > 0;
  const selectedCount = selectedIds.size;

  const selectedExecutions = useMemo(
    () => executions.filter((e) => selectedIds.has(e.id)),
    [executions, selectedIds]
  );

  const isAllSelected =
    executions.length > 0 && selectedIds.size === executions.length;

  return {
    selectedIds,
    isSelected,
    toggleSelection,
    selectAll,
    clearSelection,
    hasSelection,
    selectedCount,
    selectedExecutions,
    isAllSelected,
  };
}
