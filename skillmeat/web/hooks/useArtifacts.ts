/**
 * React Query hooks for artifact data fetching
 *
 * These hooks provide data fetching, caching, and state management for artifacts.
 * Uses live API data with mock fallbacks to keep the UI responsive offline.
 */

import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from '@tanstack/react-query';
import type {
  Artifact,
  ArtifactFilters,
  ArtifactSort,
  ArtifactsResponse,
} from '@/types/artifact';
import { ApiError, apiConfig, apiRequest } from '@/lib/api';
import { fetchArtifactsPaginated, type ArtifactsPaginatedResponse } from '@/lib/api/artifacts';
import {
  mapApiResponseToArtifact,
  type ArtifactResponse,
} from '@/lib/api/mappers';

const USE_MOCKS = apiConfig.useMocks;

interface ApiPageInfo {
  has_next_page: boolean;
  has_previous_page: boolean;
  start_cursor: string | null;
  end_cursor: string | null;
  total_count: number;
}

interface ApiArtifactListResponse {
  items: ArtifactResponse[];
  page_info: ApiPageInfo;
}

// Mock data generator for development (uses unified Artifact schema)
const generateMockArtifacts = (): Artifact[] => {
  return [
    {
      id: 'skill:canvas-design',
      name: 'canvas-design',
      type: 'skill',
      scope: 'user',
      syncStatus: 'synced',
      version: 'v2.1.0',
      source: 'anthropics/skills/canvas-design',
      description: 'Create and edit visual designs with an interactive canvas',
      license: 'MIT',
      author: 'Anthropic',
      tags: ['design', 'visual', 'canvas'],
      upstream: {
        enabled: true,
        url: 'https://github.com/anthropics/skills/canvas-design',
        version: 'v2.1.0',
        currentSha: 'abc123',
        upstreamSha: 'abc123',
        updateAvailable: false,
        lastChecked: new Date().toISOString(),
      },
      usageStats: {
        totalDeployments: 5,
        activeProjects: 3,
        lastUsed: new Date(Date.now() - 86400000).toISOString(),
        usageCount: 42,
      },
      createdAt: new Date(Date.now() - 30 * 86400000).toISOString(),
      updatedAt: new Date(Date.now() - 2 * 86400000).toISOString(),
      aliases: ['design', 'canvas'],
      collection: 'Design Tools',
      collections: [
        { id: 'design-tools', name: 'Design Tools', artifact_count: 12 },
        { id: 'ai-tools', name: 'AI Tools', artifact_count: 25 },
        { id: 'productivity', name: 'Productivity', artifact_count: 8 },
      ],
    },
    {
      id: 'skill:docx-processor',
      name: 'docx-processor',
      type: 'skill',
      scope: 'user',
      syncStatus: 'outdated',
      version: 'v1.5.0',
      source: 'anthropics/skills/document-skills/docx',
      description: 'Read and process Microsoft Word documents',
      license: 'Apache-2.0',
      author: 'Anthropic',
      tags: ['document', 'docx', 'word'],
      upstream: {
        enabled: true,
        url: 'https://github.com/anthropics/skills/document-skills/docx',
        version: 'v1.8.0',
        currentSha: 'def456',
        upstreamSha: 'ghi789',
        updateAvailable: true,
        lastChecked: new Date().toISOString(),
      },
      usageStats: {
        totalDeployments: 2,
        activeProjects: 1,
        lastUsed: new Date(Date.now() - 7 * 86400000).toISOString(),
        usageCount: 15,
      },
      createdAt: new Date(Date.now() - 60 * 86400000).toISOString(),
      updatedAt: new Date(Date.now() - 45 * 86400000).toISOString(),
      collection: 'Document Processing',
      collections: [
        { id: 'document-processing', name: 'Document Processing', artifact_count: 6 },
      ],
    },
    {
      id: 'command:git-helper',
      name: 'git-helper',
      type: 'command',
      scope: 'user',
      syncStatus: 'synced',
      version: 'v1.0.0',
      source: 'local',
      origin: 'local',
      description: 'Custom git workflow commands',
      author: 'Local User',
      tags: ['git', 'vcs', 'workflow'],
      usageStats: {
        totalDeployments: 8,
        activeProjects: 8,
        lastUsed: new Date(Date.now() - 3600000).toISOString(),
        usageCount: 128,
      },
      createdAt: new Date(Date.now() - 90 * 86400000).toISOString(),
      updatedAt: new Date(Date.now() - 7 * 86400000).toISOString(),
      aliases: ['git'],
      collection: 'Developer Tools',
    },
    {
      id: 'agent:code-reviewer',
      name: 'code-reviewer',
      type: 'agent',
      scope: 'local',
      syncStatus: 'synced',
      version: 'v0.5.0',
      source: 'github.com/example/code-reviewer',
      origin: 'github',
      description: 'Automated code review assistant',
      license: 'MIT',
      author: 'Example User',
      tags: ['code-review', 'agent', 'quality'],
      upstream: {
        enabled: true,
        url: 'https://github.com/example/code-reviewer',
        version: 'v0.5.0',
        currentSha: 'jkl012',
        upstreamSha: 'jkl012',
        updateAvailable: false,
        lastChecked: new Date().toISOString(),
      },
      usageStats: {
        totalDeployments: 1,
        activeProjects: 1,
        lastUsed: new Date(Date.now() - 172800000).toISOString(),
        usageCount: 8,
      },
      createdAt: new Date(Date.now() - 14 * 86400000).toISOString(),
      updatedAt: new Date(Date.now() - 5 * 86400000).toISOString(),
      collection: 'Developer Tools',
    },
    {
      id: 'mcp:database-mcp',
      name: 'database-mcp',
      type: 'mcp',
      scope: 'user',
      syncStatus: 'synced',
      version: 'v2.0.1',
      source: 'anthropics/mcp-servers/database',
      origin: 'github',
      description: 'MCP server for database operations',
      license: 'MIT',
      author: 'Anthropic',
      tags: ['mcp', 'database', 'sql'],
      upstream: {
        enabled: true,
        url: 'https://github.com/anthropics/mcp-servers/database',
        version: 'v2.0.1',
        currentSha: 'mno345',
        upstreamSha: 'mno345',
        updateAvailable: false,
        lastChecked: new Date().toISOString(),
      },
      usageStats: {
        totalDeployments: 4,
        activeProjects: 3,
        lastUsed: new Date(Date.now() - 43200000).toISOString(),
        usageCount: 67,
      },
      createdAt: new Date(Date.now() - 20 * 86400000).toISOString(),
      updatedAt: new Date(Date.now() - 1 * 86400000).toISOString(),
      collection: 'Infrastructure',
    },
  ];
};

const DEFAULT_ARTIFACT_LIMIT = 100;

// Filter and sort artifacts
const filterAndSortArtifacts = (
  artifacts: Artifact[],
  filters: ArtifactFilters,
  sort: ArtifactSort
): Artifact[] => {
  let filtered = [...artifacts];

  // Apply type filter
  if (filters.type && filters.type !== 'all') {
    filtered = filtered.filter((a) => a.type === filters.type);
  }

  // Apply status filter (uses syncStatus in unified Artifact type)
  if (filters.status && filters.status !== 'all') {
    filtered = filtered.filter((a) => a.syncStatus === filters.status);
  }

  // Apply scope filter
  if (filters.scope && filters.scope !== 'all') {
    filtered = filtered.filter((a) => a.scope === filters.scope);
  }

  // Apply search filter (uses flattened metadata fields)
  if (filters.search) {
    const searchLower = filters.search.toLowerCase();
    filtered = filtered.filter(
      (a) =>
        a.name.toLowerCase().includes(searchLower) ||
        a.description?.toLowerCase().includes(searchLower) ||
        a.tags?.some((tag) => tag.toLowerCase().includes(searchLower))
    );
  }

  // Apply sorting
  filtered.sort((a, b) => {
    let aValue: string | number;
    let bValue: string | number;

    switch (sort.field) {
      case 'name':
        aValue = a.name;
        bValue = b.name;
        break;
      case 'updatedAt':
        aValue = new Date(a.updatedAt).getTime();
        bValue = new Date(b.updatedAt).getTime();
        break;
      case 'usageCount':
        aValue = a.usageStats?.usageCount ?? 0;
        bValue = b.usageStats?.usageCount ?? 0;
        break;
      default:
        return 0;
    }

    if (aValue < bValue) return sort.order === 'asc' ? -1 : 1;
    if (aValue > bValue) return sort.order === 'asc' ? 1 : -1;
    return 0;
  });

  return filtered;
};

// Query keys
const artifactKeys = {
  all: ['artifacts'] as const,
  lists: () => [...artifactKeys.all, 'list'] as const,
  list: (filters: ArtifactFilters, sort: ArtifactSort) =>
    [...artifactKeys.lists(), filters, sort] as const,
  details: () => [...artifactKeys.all, 'detail'] as const,
  detail: (id: string) => [...artifactKeys.details(), id] as const,
};

async function fetchArtifactsFromApi(
  filters: ArtifactFilters,
  sort: ArtifactSort
): Promise<ArtifactsResponse> {
  const params = new URLSearchParams({
    limit: DEFAULT_ARTIFACT_LIMIT.toString(),
  });

  if (filters.type && filters.type !== 'all') {
    params.set('artifact_type', filters.type);
  }

  try {
    const response = await apiRequest<ApiArtifactListResponse>(`/artifacts?${params.toString()}`);

    // Map API responses to unified Artifact type using centralized mapper
    const mappedArtifacts = response.items.map((item) =>
      mapApiResponseToArtifact(item, 'collection')
    );
    const filtered = filterAndSortArtifacts(mappedArtifacts, filters, sort);

    return {
      artifacts: filtered,
      total: response.page_info?.total_count ?? filtered.length,
      page: 1,
      pageSize: filtered.length,
    };
  } catch (error) {
    if (USE_MOCKS) {
      console.warn('[artifacts] API failed, falling back to mock data', error);
      const mockArtifacts = generateMockArtifacts();
      const filtered = filterAndSortArtifacts(mockArtifacts, filters, sort);
      return {
        artifacts: filtered,
        total: filtered.length,
        page: 1,
        pageSize: filtered.length,
      };
    }
    throw error;
  }
}

async function fetchArtifactFromApi(id: string): Promise<Artifact | null> {
  try {
    const artifact = await apiRequest<ArtifactResponse>(`/artifacts/${encodeURIComponent(id)}`);
    return mapApiResponseToArtifact(artifact, 'collection');
  } catch (error) {
    if (USE_MOCKS && error instanceof ApiError && error.status === 404) {
      return null;
    }
    console.error(`[artifacts] Failed to fetch artifact ${id} from API`, error);
    throw error;
  }
}

/**
 * Hook to fetch and filter artifacts
 */
export function useArtifacts(
  filters: ArtifactFilters = {},
  sort: ArtifactSort = { field: 'name', order: 'asc' }
) {
  return useQuery({
    queryKey: artifactKeys.list(filters, sort),
    queryFn: async (): Promise<ArtifactsResponse> => {
      return await fetchArtifactsFromApi(filters, sort);
    },
    staleTime: 5 * 60 * 1000, // 5 min - standard browsing stale time
  });
}

/**
 * Hook to fetch a single artifact by ID
 */
export function useArtifact(id: string) {
  return useQuery({
    queryKey: artifactKeys.detail(id),
    queryFn: async (): Promise<Artifact | null> => {
      return await fetchArtifactFromApi(id);
    },
    enabled: !!id,
    staleTime: 5 * 60 * 1000, // 5 min - matches useArtifacts()
  });
}

/**
 * Hook to update an artifact
 */
export function useUpdateArtifact() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (artifact: Partial<Artifact> & { id: string }) => {
      try {
        const response = await apiRequest<ArtifactResponse>(`/artifacts/${encodeURIComponent(artifact.id)}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(artifact),
        });
        return mapApiResponseToArtifact(response, 'collection');
      } catch (error) {
        if (USE_MOCKS) {
          console.warn('[artifacts] Update API failed, falling back to mock', error);
          return artifact as Artifact;
        }
        throw error;
      }
    },
    onSuccess: () => {
      // Invalidate and refetch artifacts
      queryClient.invalidateQueries({ queryKey: artifactKeys.all });
    },
  });
}

/**
 * Hook to delete an artifact
 */
export function useDeleteArtifact() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      try {
        await apiRequest<void>(`/artifacts/${encodeURIComponent(id)}`, {
          method: 'DELETE',
        });
        return id;
      } catch (error) {
        if (USE_MOCKS) {
          console.warn('[artifacts] Delete API failed, falling back to mock', error);
          return id;
        }
        throw error;
      }
    },
    onSuccess: () => {
      // Invalidate and refetch artifacts
      queryClient.invalidateQueries({ queryKey: artifactKeys.all });
      // Artifact may have been deployed
      queryClient.invalidateQueries({ queryKey: ['deployments'] });
      // Collection membership changes
      queryClient.invalidateQueries({ queryKey: ['collections'] });
    },
  });
}

/**
 * Hook to update artifact tags
 *
 * Updates all tags for an artifact in a single operation.
 * Tags are normalized on the server (lowercase, spaces to underscores)
 * and created if they don't already exist.
 *
 * @example
 * ```tsx
 * const updateTags = useUpdateArtifactTags();
 * await updateTags.mutateAsync({
 *   artifactId: 'skill:canvas-design',
 *   tags: ['design', 'visual', 'canvas'],
 *   collection: 'default',
 * });
 * ```
 */
export function useUpdateArtifactTags() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      artifactId,
      tags,
      collection,
    }: {
      artifactId: string;
      tags: string[];
      collection?: string;
    }) => {
      const params = new URLSearchParams();
      if (collection) {
        params.set('collection', collection);
      }

      const queryString = params.toString();
      const url = `/artifacts/${encodeURIComponent(artifactId)}/tags${queryString ? `?${queryString}` : ''}`;

      const response = await apiRequest<ArtifactResponse>(url, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tags }),
      });

      return mapApiResponseToArtifact(response, 'collection');
    },
    onSuccess: (_, { artifactId }) => {
      // Invalidate all artifact queries to refresh data
      queryClient.invalidateQueries({ queryKey: artifactKeys.all });
      // Also invalidate tag-specific queries for this artifact
      queryClient.invalidateQueries({ queryKey: ['tags', 'artifact', artifactId] });
    },
  });
}

/**
 * Options for infinite artifacts query (used for "All Collections" view)
 */
export interface InfiniteAllArtifactsOptions {
  /** Number of items to fetch per page */
  limit?: number;
  /** Filter by artifact type */
  artifact_type?: string;
  /** Filter by status */
  status?: string;
  /** Filter by scope */
  scope?: string;
  /** Search query */
  search?: string;
  /** Filter by tools (Claude Code tools used by artifact) */
  tools?: string[];
  /** Whether the query should be enabled */
  enabled?: boolean;
}

/**
 * Hook to fetch all artifacts with infinite scroll pagination
 *
 * Uses cursor-based pagination for efficient loading of large artifact lists.
 * This is the "All Collections" counterpart to useInfiniteCollectionArtifacts.
 *
 * @param options - Pagination and filtering options
 * @returns Infinite query result with pages array and pagination helpers
 *
 * @example
 * ```tsx
 * const {
 *   data,
 *   fetchNextPage,
 *   hasNextPage,
 *   isFetchingNextPage,
 * } = useInfiniteArtifacts({ limit: 20 });
 *
 * // Flatten pages to get all items
 * const allItems = data?.pages.flatMap(p => p.items) || [];
 *
 * // Get total count from first page
 * const totalCount = data?.pages[0]?.page_info.total_count || 0;
 * ```
 */
export function useInfiniteArtifacts(options?: InfiniteAllArtifactsOptions) {
  const { limit = 20, enabled = true, ...filters } = options || {};

  return useInfiniteQuery({
    queryKey: ['artifacts', 'infinite', filters],
    queryFn: async ({ pageParam }): Promise<ArtifactsPaginatedResponse> => {
      return fetchArtifactsPaginated({
        limit,
        after: pageParam,
        artifact_type: filters.artifact_type,
        status: filters.status,
        scope: filters.scope,
        search: filters.search,
        tools: filters.tools,
      });
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) =>
      lastPage.page_info.has_next_page ? (lastPage.page_info.end_cursor ?? undefined) : undefined,
    enabled,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
