/**
 * React Query hooks for project data fetching and mutations
 *
 * These hooks provide data fetching, caching, and state management for projects.
 * Uses live API data with mock fallbacks to keep the UI responsive offline.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type {
  ProjectSummary,
  ProjectDetail,
  ProjectsResponse,
  ProjectDetailResponse,
} from "@/types/project";
import { ApiError, apiConfig, apiRequest } from "@/lib/api";
import type { ProjectCreateRequest, ProjectUpdateRequest } from "@/sdk";

const USE_MOCKS = apiConfig.useMocks;

// Mock data generator for development
const generateMockProjects = (): ProjectSummary[] => {
  return [
    {
      id: "L1VzZXJzL2pvaG4vcHJvamVjdHMvd2ViLWFwcA==",
      path: "/Users/john/projects/web-app",
      name: "web-app",
      deployment_count: 8,
      last_deployment: new Date(Date.now() - 86400000).toISOString(),
    },
    {
      id: "L1VzZXJzL2pvaG4vcHJvamVjdHMvYXBpLXNlcnZpY2U=",
      path: "/Users/john/projects/api-service",
      name: "api-service",
      deployment_count: 5,
      last_deployment: new Date(Date.now() - 2 * 86400000).toISOString(),
    },
    {
      id: "L1VzZXJzL2pvaG4vcHJvamVjdHMvZGF0YS1waXBlbGluZQ==",
      path: "/Users/john/projects/data-pipeline",
      name: "data-pipeline",
      deployment_count: 3,
      last_deployment: new Date(Date.now() - 7 * 86400000).toISOString(),
    },
    {
      id: "L1VzZXJzL2pvaG4vcHJvamVjdHMvbW9iaWxlLWFwcA==",
      path: "/Users/john/projects/mobile-app",
      name: "mobile-app",
      deployment_count: 2,
      last_deployment: new Date(Date.now() - 14 * 86400000).toISOString(),
    },
  ];
};

const generateMockProjectDetail = (projectId: string): ProjectDetail | null => {
  const projects = generateMockProjects();
  const project = projects.find((p) => p.id === projectId);

  if (!project) {
    return null;
  }

  return {
    ...project,
    deployments: [
      {
        artifact_name: "canvas-design",
        artifact_type: "skill",
        from_collection: "default",
        deployed_at: new Date(Date.now() - 2 * 86400000).toISOString(),
        artifact_path: "skills/canvas-design",
        version: "v2.1.0",
        collection_sha: "abc123def456",
        local_modifications: false,
      },
      {
        artifact_name: "docx-processor",
        artifact_type: "skill",
        from_collection: "default",
        deployed_at: new Date(Date.now() - 5 * 86400000).toISOString(),
        artifact_path: "skills/docx-processor",
        version: "v1.5.0",
        collection_sha: "def789ghi012",
        local_modifications: true,
      },
      {
        artifact_name: "review",
        artifact_type: "command",
        from_collection: "custom",
        deployed_at: new Date(Date.now() - 10 * 86400000).toISOString(),
        artifact_path: "commands/review.md",
        version: "v1.0.0",
        collection_sha: "ghi345jkl678",
        local_modifications: false,
      },
    ],
    stats: {
      by_type: {
        skill: 5,
        command: 2,
        agent: 1,
      },
      by_collection: {
        default: 6,
        custom: 2,
      },
      modified_count: 1,
    },
  };
};

// Query keys
const projectKeys = {
  all: ["projects"] as const,
  lists: () => [...projectKeys.all, "list"] as const,
  list: () => [...projectKeys.lists()] as const,
  details: () => [...projectKeys.all, "detail"] as const,
  detail: (id: string) => [...projectKeys.details(), id] as const,
};

async function fetchProjectsFromApi(
  forceRefresh: boolean = false
): Promise<ProjectSummary[]> {
  const params = new URLSearchParams({
    limit: "100", // Get all projects (they're typically not numerous)
  });

  // Add refresh parameter to bypass backend cache
  if (forceRefresh) {
    params.set("refresh", "true");
  }

  try {
    const response = await apiRequest<ProjectsResponse>(
      `/projects?${params.toString()}`
    );

    return response.items;
  } catch (error) {
    if (USE_MOCKS) {
      console.warn("[projects] API failed, falling back to mock data", error);
      return generateMockProjects();
    }
    throw error;
  }
}

async function fetchProjectFromApi(id: string): Promise<ProjectDetail | null> {
  try {
    const response = await apiRequest<ProjectDetailResponse>(`/projects/${id}`);

    return {
      id: response.id,
      path: response.path,
      name: response.name,
      deployment_count: response.deployment_count,
      last_deployment: response.last_deployment,
      deployments: response.deployments,
      stats: response.stats,
    };
  } catch (error) {
    if (USE_MOCKS && error instanceof ApiError && error.status === 404) {
      return generateMockProjectDetail(id);
    }
    console.error(`[projects] Failed to fetch project ${id} from API`, error);
    throw error;
  }
}

async function createProjectApi(
  data: ProjectCreateRequest
): Promise<ProjectDetail> {
  const response = await apiRequest<ProjectDetail>("/projects", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  return response;
}

async function updateProjectApi(
  id: string,
  data: ProjectUpdateRequest
): Promise<ProjectDetail> {
  const response = await apiRequest<ProjectDetail>(`/projects/${id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  return response;
}

async function deleteProjectApi(
  id: string,
  deleteFiles: boolean = false
): Promise<void> {
  await apiRequest(`/projects/${id}?delete_files=${deleteFiles}`, {
    method: "DELETE",
  });
}

// Cache configuration
const PROJECTS_STALE_TIME = 5 * 60 * 1000; // 5 minutes - backend caches for this long
const PROJECTS_GC_TIME = 10 * 60 * 1000; // 10 minutes - keep in memory longer

/**
 * Hook to fetch all projects with deployments
 *
 * The backend now caches project discovery results for 5 minutes,
 * so we match that with our frontend stale time.
 *
 * @returns Query result with projects list and refresh function
 */
export function useProjects() {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: projectKeys.list(),
    queryFn: async (): Promise<ProjectSummary[]> => {
      return await fetchProjectsFromApi();
    },
    staleTime: PROJECTS_STALE_TIME,
    gcTime: PROJECTS_GC_TIME,
  });

  /**
   * Force refresh the projects list, bypassing both frontend and backend cache.
   * Use this after making changes outside the app or when data seems stale.
   */
  const forceRefresh = async () => {
    // Fetch with forceRefresh to bypass backend cache
    const freshData = await fetchProjectsFromApi(true);
    // Update the cache with fresh data
    queryClient.setQueryData(projectKeys.list(), freshData);
    return freshData;
  };

  return {
    ...query,
    forceRefresh,
  };
}

/**
 * Hook to fetch a single project by ID
 */
export function useProject(id: string) {
  return useQuery({
    queryKey: projectKeys.detail(id),
    queryFn: async (): Promise<ProjectDetail | null> => {
      return await fetchProjectFromApi(id);
    },
    enabled: !!id,
  });
}

/**
 * Hook to create a new project
 */
export function useCreateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createProjectApi,
    onSuccess: () => {
      // Invalidate projects list to refetch
      queryClient.invalidateQueries({ queryKey: projectKeys.list() });
    },
  });
}

/**
 * Hook to update an existing project
 */
export function useUpdateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ProjectUpdateRequest }) =>
      updateProjectApi(id, data),
    onSuccess: (data) => {
      // Invalidate both list and detail queries
      queryClient.invalidateQueries({ queryKey: projectKeys.list() });
      queryClient.invalidateQueries({ queryKey: projectKeys.detail(data.id) });
    },
  });
}

/**
 * Hook to delete a project
 */
export function useDeleteProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      deleteFiles = false,
    }: {
      id: string;
      deleteFiles?: boolean;
    }) => deleteProjectApi(id, deleteFiles),
    onSuccess: () => {
      // Invalidate projects list to refetch
      queryClient.invalidateQueries({ queryKey: projectKeys.list() });
    },
  });
}
