/**
 * useMultiSelect
 *
 * Generic multi-select hook for managing checkbox selection state over any
 * list of items. Generalises the pattern established by useExecutionSelection.
 */

'use client';

import { useState, useCallback, useMemo, useEffect } from 'react';

// ---------------------------------------------------------------------------
// Return type
// ---------------------------------------------------------------------------

export interface UseMultiSelectReturn<T> {
  /** Set of selected item IDs. */
  selectedIds: Set<string>;
  /** Returns true if the given item ID is selected. */
  isSelected: (id: string) => boolean;
  /** Toggles selection for the given item ID. */
  toggleSelection: (id: string) => void;
  /** Selects all items in the provided list. */
  selectAll: () => void;
  /** Clears all selections. */
  clearSelection: () => void;
  /** Toggles between selecting all items and clearing all selections. */
  toggleSelectAll: () => void;
  /** True when at least one item is selected. */
  hasSelection: boolean;
  /** Number of selected items. */
  selectedCount: number;
  /** Array of items whose IDs are currently selected. */
  selectedItems: T[];
  /** True when every item in the list is selected (and the list is non-empty). */
  isAllSelected: boolean;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Manages multi-select state for a list of items.
 *
 * @param items        - The current list of items to select from.
 * @param idExtractor  - Function that returns a stable string ID for an item.
 *                       Defaults to reading `(item as { id: string }).id`.
 *
 * Selection is automatically cleared whenever `items` reference changes
 * (e.g. new page of data loaded), preventing stale selections.
 *
 * @example
 * ```tsx
 * // Default id extractor (item.id)
 * const { selectedIds, toggleSelection, hasSelection, selectedItems } =
 *   useMultiSelect(artifacts);
 *
 * // Custom id extractor
 * const { selectedIds, toggleSelectAll, isAllSelected } =
 *   useMultiSelect(tags, (tag) => tag.slug);
 * ```
 */
export function useMultiSelect<T>(
  items: T[],
  idExtractor: (item: T) => string = (item) => (item as { id: string }).id
): UseMultiSelectReturn<T> {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // Auto-clear selection when the items list changes (new data loaded).
  useEffect(() => {
    setSelectedIds(new Set());
  }, [items]);

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
    setSelectedIds(new Set(items.map(idExtractor)));
  }, [items, idExtractor]);

  const clearSelection = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  const toggleSelectAll = useCallback(() => {
    setSelectedIds((prev) => {
      const allIds = items.map(idExtractor);
      const allSelected = allIds.length > 0 && allIds.every((id) => prev.has(id));
      return allSelected ? new Set() : new Set(allIds);
    });
  }, [items, idExtractor]);

  const hasSelection = selectedIds.size > 0;
  const selectedCount = selectedIds.size;

  const selectedItems = useMemo(
    () => items.filter((item) => selectedIds.has(idExtractor(item))),
    [items, selectedIds, idExtractor]
  );

  const isAllSelected =
    items.length > 0 && selectedIds.size === items.length;

  return {
    selectedIds,
    isSelected,
    toggleSelection,
    selectAll,
    clearSelection,
    toggleSelectAll,
    hasSelection,
    selectedCount,
    selectedItems,
    isAllSelected,
  };
}
