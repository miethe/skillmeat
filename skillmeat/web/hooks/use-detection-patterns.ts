/**
 * React Query hook for fetching artifact detection patterns from the backend
 *
 * Detection patterns define which directory names are recognized as artifact
 * containers (e.g., 'skills', 'commands', 'agents'). This enables consistent
 * artifact type detection between frontend and backend.
 *
 * The hook uses aggressive caching since detection patterns rarely change:
 * - 30-minute stale time (patterns are essentially static)
 * - 1-hour garbage collection time
 * - Single retry on failure
 *
 * Falls back to DEFAULT_LEAF_CONTAINERS on error for graceful degradation.
 */

import { useQuery } from '@tanstack/react-query';
import {
  getDetectionPatterns,
  type DetectionPatternsResponse,
} from '@/lib/api/config';

/**
 * Default leaf container names used when API is unavailable
 *
 * This fallback ensures the UI remains functional even if the config
 * endpoint is unreachable. Values mirror the backend's CONTAINER_ALIASES.
 */
export const DEFAULT_LEAF_CONTAINERS = [
  // Skill containers
  'skills',
  'skill',
  // Command containers
  'commands',
  'command',
  'cmd',
  // Agent containers
  'agents',
  'agent',
  // MCP server containers
  'mcp_servers',
  'mcp-servers',
  'mcp',
  'mcpServers',
  'servers',
  // Hook containers
  'hooks',
  'hook',
];

/**
 * Default container aliases mapping artifact types to valid directory names
 */
export const DEFAULT_CONTAINER_ALIASES: Record<string, string[]> = {
  skill: ['skills', 'skill'],
  command: ['commands', 'command', 'cmd'],
  agent: ['agents', 'agent'],
  mcp: ['mcp_servers', 'mcp-servers', 'mcp', 'mcpServers', 'servers'],
  hook: ['hooks', 'hook'],
};

/**
 * Default canonical container names (preferred directory name per type)
 */
export const DEFAULT_CANONICAL_CONTAINERS: Record<string, string> = {
  skill: 'skills',
  command: 'commands',
  agent: 'agents',
  mcp: 'mcp_servers',
  hook: 'hooks',
};

/**
 * Default root-level folders to exclude from semantic navigation
 *
 * These are too high-level to be useful for navigation purposes.
 * Note: 'plugins' intentionally excluded - they're meaningful folders
 * that should be shown as they often contain the main artifact structure.
 */
export const DEFAULT_ROOT_EXCLUSIONS = [
  'src',
  'lib',
  'packages',
  'apps',
  'examples',
];

/**
 * Query key factory for detection pattern queries
 */
export const detectionPatternKeys = {
  all: ['detection-patterns'] as const,
  patterns: () => [...detectionPatternKeys.all, 'patterns'] as const,
};

/**
 * Hook to fetch artifact detection patterns from the backend
 *
 * Detection patterns define valid container directory names for each artifact
 * type. Uses aggressive caching since these patterns rarely change.
 *
 * @returns Query result with detection patterns and convenience accessors
 *
 * @example
 * ```tsx
 * const { leafContainers, isLeafContainer, isLoading } = useDetectionPatterns();
 *
 * // Check if a directory is a leaf container
 * if (isLeafContainer('skills')) {
 *   // This is an artifact container, not a navigation folder
 * }
 *
 * // Access all leaf containers
 * const excluded = folders.filter(f => leafContainers.includes(f.name));
 * ```
 */
export function useDetectionPatterns() {
  const query = useQuery({
    queryKey: detectionPatternKeys.patterns(),
    queryFn: getDetectionPatterns,
    staleTime: 30 * 60 * 1000, // 30 minutes - patterns rarely change
    gcTime: 60 * 60 * 1000, // Keep in cache for 1 hour
    retry: 1, // Only retry once on failure
  });

  // Extract values with fallbacks for graceful degradation
  const leafContainers = query.data?.leaf_containers ?? DEFAULT_LEAF_CONTAINERS;
  const containerAliases = query.data?.container_aliases ?? DEFAULT_CONTAINER_ALIASES;
  const canonicalContainers = query.data?.canonical_containers ?? DEFAULT_CANONICAL_CONTAINERS;

  // Create a Set for O(1) lookups
  const leafContainerSet = new Set(leafContainers);

  return {
    /** Flattened list of all valid container directory names */
    leafContainers,
    /** Maps artifact type to valid container names */
    containerAliases,
    /** Maps artifact type to preferred container name */
    canonicalContainers,
    /** Raw response data from the API */
    data: query.data,
    /** Whether the initial query is loading */
    isLoading: query.isLoading,
    /** Whether data is being fetched (includes background refetch) */
    isFetching: query.isFetching,
    /** Query error if any */
    error: query.error,
    /** Whether data was loaded from API (vs fallback) */
    isFromApi: !!query.data,
    /**
     * Check if a directory name is a leaf container
     * @param name - Directory name to check
     * @returns true if the name is a recognized artifact container
     */
    isLeafContainer: (name: string): boolean => leafContainerSet.has(name),
    /**
     * Get the artifact type for a container name
     * @param containerName - Directory name to look up
     * @returns Artifact type string or undefined if not found
     */
    getArtifactType: (containerName: string): string | undefined => {
      for (const [type, aliases] of Object.entries(containerAliases)) {
        if (aliases.includes(containerName)) {
          return type;
        }
      }
      return undefined;
    },
    /** Manually refetch detection patterns */
    refetch: query.refetch,
  };
}

export type { DetectionPatternsResponse };
