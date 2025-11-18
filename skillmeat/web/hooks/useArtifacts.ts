/**
 * React Query hooks for artifact data fetching
 *
 * These hooks provide data fetching, caching, and state management for artifacts.
 * Uses live API data with mock fallbacks to keep the UI responsive offline.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type {
  Artifact,
  ArtifactFilters,
  ArtifactSort,
  ArtifactsResponse,
  ArtifactScope,
  ArtifactType,
} from "@/types/artifact";
import { ApiError, apiConfig, apiRequest } from "@/lib/api";

const USE_MOCKS = apiConfig.useMocks;

interface ApiPageInfo {
  has_next_page: boolean;
  has_previous_page: boolean;
  start_cursor: string | null;
  end_cursor: string | null;
  total_count: number;
}

interface ApiArtifactMetadata {
  title?: string;
  description?: string;
  license?: string;
  author?: string;
  version?: string;
  tags?: string[];
}

interface ApiArtifactUpstream {
  tracking_enabled: boolean;
  current_sha?: string;
  upstream_sha?: string;
  update_available: boolean;
  has_local_modifications: boolean;
}

interface ApiArtifact {
  id: string;
  name: string;
  type: ArtifactType;
  source: string;
  version?: string;
  aliases?: string[];
  metadata?: ApiArtifactMetadata;
  upstream?: ApiArtifactUpstream;
  added: string;
  updated: string;
}

interface ApiArtifactListResponse {
  items: ApiArtifact[];
  page_info: ApiPageInfo;
}

// Mock data generator for development
const generateMockArtifacts = (): Artifact[] => {

  return [
    {
      id: "1",
      name: "canvas-design",
      type: "skill",
      scope: "user",
      status: "active",
      version: "v2.1.0",
      source: "anthropics/skills/canvas-design",
      metadata: {
        title: "Canvas Design",
        description: "Create and edit visual designs with an interactive canvas",
        license: "MIT",
        author: "Anthropic",
        version: "2.1.0",
        tags: ["design", "visual", "canvas"],
      },
      upstreamStatus: {
        hasUpstream: true,
        upstreamUrl: "https://github.com/anthropics/skills/canvas-design",
        upstreamVersion: "v2.1.0",
        currentVersion: "v2.1.0",
        isOutdated: false,
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
      aliases: ["design", "canvas"],
    },
    {
      id: "2",
      name: "docx-processor",
      type: "skill",
      scope: "user",
      status: "outdated",
      version: "v1.5.0",
      source: "anthropics/skills/document-skills/docx",
      metadata: {
        title: "DOCX Processor",
        description: "Read and process Microsoft Word documents",
        license: "Apache-2.0",
        author: "Anthropic",
        version: "1.5.0",
        tags: ["document", "docx", "word"],
      },
      upstreamStatus: {
        hasUpstream: true,
        upstreamUrl: "https://github.com/anthropics/skills/document-skills/docx",
        upstreamVersion: "v1.8.0",
        currentVersion: "v1.5.0",
        isOutdated: true,
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
    },
    {
      id: "3",
      name: "git-helper",
      type: "command",
      scope: "user",
      status: "active",
      version: "v1.0.0",
      source: "local",
      metadata: {
        title: "Git Helper",
        description: "Custom git workflow commands",
        author: "Local User",
        version: "1.0.0",
        tags: ["git", "vcs", "workflow"],
      },
      upstreamStatus: {
        hasUpstream: false,
        isOutdated: false,
      },
      usageStats: {
        totalDeployments: 8,
        activeProjects: 8,
        lastUsed: new Date(Date.now() - 3600000).toISOString(),
        usageCount: 128,
      },
      createdAt: new Date(Date.now() - 90 * 86400000).toISOString(),
      updatedAt: new Date(Date.now() - 7 * 86400000).toISOString(),
      aliases: ["git"],
    },
    {
      id: "4",
      name: "code-reviewer",
      type: "agent",
      scope: "local",
      status: "active",
      version: "v0.5.0",
      source: "github.com/example/code-reviewer",
      metadata: {
        title: "Code Reviewer Agent",
        description: "Automated code review assistant",
        license: "MIT",
        author: "Example User",
        version: "0.5.0",
        tags: ["code-review", "agent", "quality"],
      },
      upstreamStatus: {
        hasUpstream: true,
        upstreamUrl: "https://github.com/example/code-reviewer",
        upstreamVersion: "v0.5.0",
        currentVersion: "v0.5.0",
        isOutdated: false,
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
    },
    {
      id: "5",
      name: "database-mcp",
      type: "mcp",
      scope: "user",
      status: "active",
      version: "v2.0.1",
      source: "anthropics/mcp-servers/database",
      metadata: {
        title: "Database MCP Server",
        description: "MCP server for database operations",
        license: "MIT",
        author: "Anthropic",
        version: "2.0.1",
        tags: ["mcp", "database", "sql"],
      },
      upstreamStatus: {
        hasUpstream: true,
        upstreamUrl: "https://github.com/anthropics/mcp-servers/database",
        upstreamVersion: "v2.0.1",
        currentVersion: "v2.0.1",
        isOutdated: false,
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
    },
  ];
};

const DEFAULT_ARTIFACT_LIMIT = 200;

const mapApiArtifact = (artifact: ApiArtifact): Artifact => {
  const metadata = artifact.metadata || {};
  const upstream = artifact.upstream;
  const updatedAt = artifact.updated || artifact.added;
  const isOutdated = upstream?.update_available ?? false;
  const scope: ArtifactScope = artifact.source === "local" ? "local" : "user";

  return {
    id: artifact.id,
    name: artifact.name,
    type: artifact.type,
    scope,
    status: isOutdated ? "outdated" : "active",
    version: artifact.version || metadata.version,
    source: artifact.source,
    metadata: {
      title: metadata.title || artifact.name,
      description: metadata.description || "",
      license: metadata.license,
      author: metadata.author,
      version: metadata.version || artifact.version,
      tags: metadata.tags || [],
    },
    upstreamStatus: {
      hasUpstream: Boolean(upstream?.tracking_enabled),
      upstreamUrl:
        artifact.source?.startsWith("http") || artifact.source?.includes("github.com")
          ? artifact.source
          : undefined,
      upstreamVersion: upstream?.upstream_sha,
      currentVersion: upstream?.current_sha || artifact.version,
      isOutdated,
      lastChecked: updatedAt,
    },
    usageStats: {
      totalDeployments: 0,
      activeProjects: 0,
      lastUsed: updatedAt,
      usageCount: 0,
    },
    createdAt: artifact.added,
    updatedAt,
    aliases: artifact.aliases || [],
  };
};

// Filter and sort artifacts
const filterAndSortArtifacts = (
  artifacts: Artifact[],
  filters: ArtifactFilters,
  sort: ArtifactSort
): Artifact[] => {
  let filtered = [...artifacts];

  // Apply type filter
  if (filters.type && filters.type !== "all") {
    filtered = filtered.filter((a) => a.type === filters.type);
  }

  // Apply status filter
  if (filters.status && filters.status !== "all") {
    filtered = filtered.filter((a) => a.status === filters.status);
  }

  // Apply scope filter
  if (filters.scope && filters.scope !== "all") {
    filtered = filtered.filter((a) => a.scope === filters.scope);
  }

  // Apply search filter
  if (filters.search) {
    const searchLower = filters.search.toLowerCase();
    filtered = filtered.filter(
      (a) =>
        a.name.toLowerCase().includes(searchLower) ||
        a.metadata.title?.toLowerCase().includes(searchLower) ||
        a.metadata.description?.toLowerCase().includes(searchLower) ||
        a.metadata.tags?.some((tag) => tag.toLowerCase().includes(searchLower))
    );
  }

  // Apply sorting
  filtered.sort((a, b) => {
    let aValue: any;
    let bValue: any;

    switch (sort.field) {
      case "name":
        aValue = a.name;
        bValue = b.name;
        break;
      case "updatedAt":
        aValue = new Date(a.updatedAt).getTime();
        bValue = new Date(b.updatedAt).getTime();
        break;
      case "usageCount":
        aValue = a.usageStats.usageCount;
        bValue = b.usageStats.usageCount;
        break;
      default:
        return 0;
    }

    if (aValue < bValue) return sort.order === "asc" ? -1 : 1;
    if (aValue > bValue) return sort.order === "asc" ? 1 : -1;
    return 0;
  });

  return filtered;
};

// Query keys
const artifactKeys = {
  all: ["artifacts"] as const,
  lists: () => [...artifactKeys.all, "list"] as const,
  list: (filters: ArtifactFilters, sort: ArtifactSort) =>
    [...artifactKeys.lists(), filters, sort] as const,
  details: () => [...artifactKeys.all, "detail"] as const,
  detail: (id: string) => [...artifactKeys.details(), id] as const,
};

async function fetchArtifactsFromApi(
  filters: ArtifactFilters,
  sort: ArtifactSort
): Promise<ArtifactsResponse> {
  const params = new URLSearchParams({
    limit: DEFAULT_ARTIFACT_LIMIT.toString(),
  });

  if (filters.type && filters.type !== "all") {
    params.set("artifact_type", filters.type);
  }

  try {
    const response = await apiRequest<ApiArtifactListResponse>(
      `/artifacts?${params.toString()}`
    );

    const mappedArtifacts = response.items.map(mapApiArtifact);
    const filtered = filterAndSortArtifacts(mappedArtifacts, filters, sort);

    return {
      artifacts: filtered,
      total: response.page_info?.total_count ?? filtered.length,
      page: 1,
      pageSize: filtered.length,
    };
  } catch (error) {
    if (USE_MOCKS) {
      console.warn("[artifacts] API failed, falling back to mock data", error);
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
    const artifact = await apiRequest<ApiArtifact>(`/artifacts/${id}`);
    return mapApiArtifact(artifact);
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
  sort: ArtifactSort = { field: "name", order: "asc" }
) {
  return useQuery({
    queryKey: artifactKeys.list(filters, sort),
    queryFn: async (): Promise<ArtifactsResponse> => {
      return await fetchArtifactsFromApi(filters, sort);
    },
    staleTime: 30000, // Consider data fresh for 30 seconds
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
  });
}

/**
 * Hook to update an artifact
 */
export function useUpdateArtifact() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (artifact: Partial<Artifact> & { id: string }) => {
      // TODO: Replace with actual API call when artifact update endpoint is available
      return artifact;
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
      // TODO: Replace with actual API call when artifact delete endpoint is available
      return id;
    },
    onSuccess: () => {
      // Invalidate and refetch artifacts
      queryClient.invalidateQueries({ queryKey: artifactKeys.all });
    },
  });
}
