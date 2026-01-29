/**
 * Folder detail pane filter utilities
 *
 * Applies catalog filters (type, confidence, search, status) to entries
 * displayed in the folder detail pane. Filters are AND conditions.
 */

import type { CatalogEntry, CatalogFilters, ArtifactType, CatalogStatus } from '@/types/marketplace';

/**
 * Apply filters to catalog entries.
 *
 * All filters are AND conditions. Empty/null filter values mean no filtering
 * for that dimension.
 *
 * @param entries - Entries to filter
 * @param filters - Current filter state
 * @returns Filtered entries
 *
 * @example
 * ```ts
 * const filtered = applyFiltersToEntries(entries, {
 *   artifact_type: 'skill',
 *   min_confidence: 0.8,
 *   search: 'python',
 *   status: 'new',
 * });
 * ```
 */
export function applyFiltersToEntries(
  entries: CatalogEntry[],
  filters: CatalogFilters
): CatalogEntry[] {
  return entries.filter((entry) => {
    // Type filter
    if (filters.artifact_type && entry.artifact_type !== filters.artifact_type) {
      return false;
    }

    // Confidence range filter
    if (filters.min_confidence !== undefined && entry.confidence_score < filters.min_confidence) {
      return false;
    }

    if (filters.max_confidence !== undefined && entry.confidence_score > filters.max_confidence) {
      return false;
    }

    // Status filter
    if (filters.status && entry.status !== filters.status) {
      return false;
    }

    // Search filter (case-insensitive, searches name and path)
    if (filters.search) {
      const searchTrimmed = filters.search.trim();
      if (searchTrimmed) {
        const searchLower = searchTrimmed.toLowerCase();
        const nameMatch = entry.name.toLowerCase().includes(searchLower);
        const pathMatch = entry.path.toLowerCase().includes(searchLower);

        if (!nameMatch && !pathMatch) {
          return false;
        }
      }
    }

    return true;
  });
}

/**
 * Check if any filters are active.
 *
 * @param filters - Current filter state
 * @returns true if any filters are set
 *
 * @example
 * ```ts
 * if (hasActiveFilters(filters)) {
 *   showFilterBadge();
 * }
 * ```
 */
export function hasActiveFilters(filters: CatalogFilters): boolean {
  return !!(
    filters.artifact_type ||
    filters.status ||
    filters.min_confidence !== undefined ||
    filters.max_confidence !== undefined ||
    (filters.search && filters.search.trim())
  );
}

/**
 * Get filter summary for display.
 *
 * @param filters - Current filter state
 * @returns Description like "2 filters active" or null if no filters
 *
 * @example
 * ```ts
 * const summary = getFilterSummary(filters);
 * // "3 filters active"
 * ```
 */
export function getFilterSummary(filters: CatalogFilters): string | null {
  if (!hasActiveFilters(filters)) {
    return null;
  }

  let count = 0;

  if (filters.artifact_type) count++;
  if (filters.status) count++;
  if (filters.min_confidence !== undefined || filters.max_confidence !== undefined) count++;
  if (filters.search && filters.search.trim()) count++;

  return `${count} filter${count !== 1 ? 's' : ''} active`;
}

/**
 * Group filtered entries by artifact type.
 *
 * Helper function to organize filtered entries for display in type sections.
 *
 * @param entries - Filtered entries to group
 * @returns Record mapping artifact type to entries
 *
 * @example
 * ```ts
 * const grouped = groupByType(filteredEntries);
 * // { skill: [...], command: [...], agent: [...] }
 * ```
 */
export function groupByType(entries: CatalogEntry[]): Record<ArtifactType, CatalogEntry[]> {
  return entries.reduce(
    (acc, entry) => {
      if (!acc[entry.artifact_type]) {
        acc[entry.artifact_type] = [];
      }
      acc[entry.artifact_type]!.push(entry);
      return acc;
    },
    {} as Record<ArtifactType, CatalogEntry[]>
  );
}

/**
 * Get count of entries by status.
 *
 * Helper to compute status-specific counts for filtered entries.
 *
 * @param entries - Entries to count
 * @returns Record mapping status to count
 *
 * @example
 * ```ts
 * const counts = getCountsByStatus(entries);
 * // { new: 5, imported: 3, excluded: 1 }
 * ```
 */
export function getCountsByStatus(entries: CatalogEntry[]): Record<CatalogStatus, number> {
  return entries.reduce(
    (acc, entry) => {
      if (!acc[entry.status]) {
        acc[entry.status] = 0;
      }
      acc[entry.status]!++;
      return acc;
    },
    {} as Record<CatalogStatus, number>
  );
}

/**
 * Get count of entries by type.
 *
 * Helper to compute type-specific counts for filtered entries.
 *
 * @param entries - Entries to count
 * @returns Record mapping artifact type to count
 *
 * @example
 * ```ts
 * const counts = getCountsByType(entries);
 * // { skill: 10, command: 5, agent: 2 }
 * ```
 */
export function getCountsByType(entries: CatalogEntry[]): Record<ArtifactType, number> {
  return entries.reduce(
    (acc, entry) => {
      if (!acc[entry.artifact_type]) {
        acc[entry.artifact_type] = 0;
      }
      acc[entry.artifact_type]!++;
      return acc;
    },
    {} as Record<ArtifactType, number>
  );
}
