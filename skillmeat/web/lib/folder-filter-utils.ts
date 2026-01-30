/**
 * Folder detail pane filter utilities
 *
 * Applies catalog filters (type, confidence, search, status) to entries
 * displayed in the folder detail pane. Filters are AND conditions.
 */

import type { CatalogEntry, CatalogFilters, ArtifactType, CatalogStatus } from '@/types/marketplace';
import { DEFAULT_LEAF_CONTAINERS } from '@/hooks/use-detection-patterns';

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

/**
 * Get artifacts that should be displayed for a folder in the filtered tree context.
 *
 * This includes:
 * 1. Artifacts directly in the folder
 * 2. Artifacts from filtered-out leaf containers that are immediate children of this folder
 *
 * When leaf containers (skills/, commands/, etc.) are filtered from the navigation tree,
 * their artifacts need to be "promoted" to the parent folder for display.
 *
 * @param catalog - All catalog entries for the source
 * @param folderPath - The folder path to get artifacts for
 * @param leafContainers - List of leaf container folder names (defaults to DEFAULT_LEAF_CONTAINERS)
 * @returns Artifacts that should be displayed for this folder
 *
 * @example
 * ```ts
 * // Folder: "anthropics"
 * // Catalog has: anthropics/my-skill, anthropics/skills/other-skill
 * // With skills being a leaf container, both artifacts are returned
 * const artifacts = getDisplayArtifactsForFolder(catalog, 'anthropics');
 * // Returns both my-skill and other-skill
 * ```
 *
 * @example
 * ```ts
 * // With custom leaf containers
 * const artifacts = getDisplayArtifactsForFolder(
 *   catalog,
 *   'vendor/tools',
 *   ['custom-container', 'artifacts']
 * );
 * ```
 */
export function getDisplayArtifactsForFolder(
  catalog: CatalogEntry[],
  folderPath: string,
  leafContainers: string[] = DEFAULT_LEAF_CONTAINERS
): CatalogEntry[] {
  const leafContainerSet = new Set(leafContainers);

  return catalog.filter((entry) => {
    // Get the directory containing this artifact
    const lastSlash = entry.path.lastIndexOf('/');

    // Special case: root path (empty string) - return artifacts with no parent folder
    if (folderPath === '') {
      // Root artifacts have no slash in their path
      if (lastSlash === -1) {
        return true;
      }
      // Also include artifacts directly in leaf containers at root level
      // e.g., "skills/my-skill" when viewing root
      const segments = entry.path.split('/');
      const firstSegment = segments[0];
      if (segments.length === 2 && firstSegment && leafContainerSet.has(firstSegment)) {
        return true;
      }
      return false;
    }

    if (lastSlash === -1) return false; // Root-level artifact, no folder (and we're not at root)

    const entryDir = entry.path.substring(0, lastSlash);

    // Case 1: Direct match - artifact is directly in the folder
    if (entryDir === folderPath) {
      return true;
    }

    // Case 2: Artifact is in an immediate leaf container child
    // Pattern: folderPath/leafContainer/artifactName
    // We need to check if entryDir matches folderPath/leafContainer
    if (entryDir.startsWith(folderPath + '/')) {
      const relativePath = entryDir.substring(folderPath.length + 1);

      // Check if the relative path is just a single leaf container segment
      // e.g., "skills" or "commands" (no further nesting)
      if (!relativePath.includes('/')) {
        // Single segment - check if it's a leaf container
        if (leafContainerSet.has(relativePath)) {
          return true;
        }
      }

      // Case 3: Artifact is in nested leaf containers
      // Pattern: folderPath/leafContainer1/leafContainer2/.../artifactName
      // All intermediate segments must be leaf containers
      const segments = relativePath.split('/');
      const pathSegments = segments.slice(0, -1); // Exclude the artifact name segment

      // If there are no path segments after folder path, not a match
      // (already handled in Case 1)
      if (pathSegments.length === 0) {
        // Just the leaf container, which we check below
        const firstSegment = segments[0];
        if (firstSegment && leafContainerSet.has(firstSegment)) {
          return true;
        }
        return false;
      }

      // Actually, let me reconsider. The entry.path includes the artifact name.
      // entryDir = entry.path without the artifact name
      // relativePath = entryDir minus folderPath and the leading slash
      // So relativePath is the path between folderPath and the artifact (not including artifact)

      // For "folderPath/skills/commands/my-cmd":
      // entry.path = "folderPath/skills/commands/my-cmd"
      // entryDir = "folderPath/skills/commands"
      // relativePath = "skills/commands"
      // segments = ["skills", "commands"]
      // All must be leaf containers for the artifact to be promoted

      const allAreLeafContainers = segments.every((segment) =>
        leafContainerSet.has(segment)
      );

      if (allAreLeafContainers) {
        return true;
      }
    }

    return false;
  });
}
