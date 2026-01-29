/**
 * Type grouping utilities for marketplace folder view
 *
 * Groups artifacts by type for display in the folder detail pane,
 * maintaining consistent display order and providing type metadata.
 */

import type { CatalogEntry, ArtifactType } from '@/types/marketplace';

/**
 * Display order for artifact types (highest to lowest priority)
 */
const TYPE_DISPLAY_ORDER: ArtifactType[] = ['skill', 'command', 'agent', 'mcp', 'hook'];

/**
 * Type display metadata mapping
 */
const TYPE_DISPLAY_INFO: Record<
  ArtifactType,
  { label: string; plural: string; iconName: string }
> = {
  skill: { label: 'Skill', plural: 'Skills', iconName: 'Sparkles' },
  command: { label: 'Command', plural: 'Commands', iconName: 'Terminal' },
  agent: { label: 'Agent', plural: 'Agents', iconName: 'Bot' },
  mcp: { label: 'MCP Server', plural: 'MCP Servers', iconName: 'Server' },
  mcp_server: { label: 'MCP Server', plural: 'MCP Servers', iconName: 'Server' }, // Alias
  hook: { label: 'Hook', plural: 'Hooks', iconName: 'Anchor' },
};

/**
 * Group artifacts by their type for display.
 *
 * Groups are returned in a consistent display order (skill, command, agent, mcp, hook).
 * Empty groups are excluded from the result.
 *
 * @param entries - Array of CatalogEntry objects to group
 * @returns Map of artifact types to arrays of entries, in display order
 *
 * @example
 * const grouped = groupArtifactsByType(entries);
 * for (const [type, items] of grouped) {
 *   console.log(`${type}: ${items.length} items`);
 * }
 */
export function groupArtifactsByType(entries: CatalogEntry[]): Map<ArtifactType, CatalogEntry[]> {
  // First, collect entries by type (including unknown types)
  const typeMap = new Map<ArtifactType, CatalogEntry[]>();

  for (const entry of entries) {
    const type = normalizeArtifactType(entry.artifact_type);
    const existing = typeMap.get(type) || [];
    typeMap.set(type, [...existing, entry]);
  }

  // Build ordered result Map
  const result = new Map<ArtifactType, CatalogEntry[]>();

  // Add known types in display order
  for (const type of TYPE_DISPLAY_ORDER) {
    const entries = typeMap.get(type);
    if (entries && entries.length > 0) {
      result.set(type, sortEntriesWithinType(entries));
      typeMap.delete(type); // Remove from typeMap to track unknowns
    }
  }

  // Add any unknown types at the end (alphabetically)
  const unknownTypes = Array.from(typeMap.keys()).sort();
  for (const type of unknownTypes) {
    const entries = typeMap.get(type);
    if (entries && entries.length > 0) {
      result.set(type, sortEntriesWithinType(entries));
    }
  }

  return result;
}

/**
 * Get display information for an artifact type.
 *
 * Provides human-readable labels and icon names for UI rendering.
 *
 * @param type - The artifact type
 * @returns Display info including label, plural label, and icon name
 *
 * @example
 * const info = getTypeDisplayInfo('skill');
 * console.log(info.label);   // "Skill"
 * console.log(info.plural);  // "Skills"
 * console.log(info.iconName); // "Sparkles"
 */
export function getTypeDisplayInfo(type: ArtifactType): {
  label: string;
  plural: string;
  iconName: string;
} {
  const normalizedType = normalizeArtifactType(type);
  const info = TYPE_DISPLAY_INFO[normalizedType];

  if (info) {
    return info;
  }

  // Fallback for unknown types
  const fallbackLabel = type.charAt(0).toUpperCase() + type.slice(1);
  return {
    label: fallbackLabel,
    plural: `${fallbackLabel}s`,
    iconName: 'FileQuestion',
  };
}

/**
 * Sort entries within a type group.
 *
 * Default sort: alphabetically by name (case-insensitive), then by path.
 * Creates a new sorted array without mutating the input.
 *
 * @param entries - Entries to sort
 * @returns Sorted entries (new array)
 *
 * @example
 * const sorted = sortEntriesWithinType(entries);
 * // Result: ['agent-alpha', 'agent-beta', 'agent-gamma']
 */
export function sortEntriesWithinType(entries: CatalogEntry[]): CatalogEntry[] {
  return [...entries].sort((a, b) => {
    // Primary sort: name (case-insensitive)
    const nameA = a.name.toLowerCase();
    const nameB = b.name.toLowerCase();
    if (nameA < nameB) return -1;
    if (nameA > nameB) return 1;

    // Secondary sort: path (for same names)
    if (a.path < b.path) return -1;
    if (a.path > b.path) return 1;

    return 0;
  });
}

/**
 * Normalize artifact type to canonical form.
 *
 * Handles type aliases (e.g., 'mcp_server' -> 'mcp').
 *
 * @param type - The artifact type to normalize
 * @returns Normalized artifact type
 *
 * @internal
 */
function normalizeArtifactType(type: ArtifactType): ArtifactType {
  // Normalize mcp_server to mcp
  if (type === 'mcp_server') {
    return 'mcp';
  }
  return type;
}

/**
 * Get total count of entries across all types in a grouped result.
 *
 * @param grouped - Map returned by groupArtifactsByType
 * @returns Total number of entries
 *
 * @example
 * const grouped = groupArtifactsByType(entries);
 * const total = getTotalCount(grouped);
 */
export function getTotalCount(grouped: Map<ArtifactType, CatalogEntry[]>): number {
  let total = 0;
  for (const entries of grouped.values()) {
    total += entries.length;
  }
  return total;
}

/**
 * Get count of artifact types (groups) in a grouped result.
 *
 * @param grouped - Map returned by groupArtifactsByType
 * @returns Number of unique artifact types
 *
 * @example
 * const grouped = groupArtifactsByType(entries);
 * const typeCount = getTypeCount(grouped);
 */
export function getTypeCount(grouped: Map<ArtifactType, CatalogEntry[]>): number {
  return grouped.size;
}
