/**
 * React hooks for template operations using TanStack Query
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type {
  ProjectTemplate,
  TemplateListResponse,
  CreateTemplateRequest,
  UpdateTemplateRequest,
  DeployTemplateRequest,
  DeployTemplateResponse,
  TemplateFilters,
} from '@/types/template';
import {
  fetchTemplates,
  fetchTemplateById,
  createTemplate,
  updateTemplate,
  deleteTemplate,
  deployTemplate,
} from '@/lib/api/templates';

// =============================================================================
// Query Key Factory
// =============================================================================

export const templateKeys = {
  all: ['templates'] as const,
  lists: () => [...templateKeys.all, 'list'] as const,
  list: (filters?: TemplateFilters) => [...templateKeys.lists(), filters] as const,
  details: () => [...templateKeys.all, 'detail'] as const,
  detail: (id: string) => [...templateKeys.details(), id] as const,
};

// =============================================================================
// Query Hooks
// =============================================================================

/**
 * Fetch all templates with optional filtering and pagination
 */
export function useTemplates(filters?: TemplateFilters) {
  return useQuery<TemplateListResponse, Error>({
    queryKey: templateKeys.list(filters),
    queryFn: () => fetchTemplates(filters),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Fetch template by ID with full entity details
 */
export function useTemplate(id: string) {
  return useQuery<ProjectTemplate, Error>({
    queryKey: templateKeys.detail(id),
    queryFn: () => fetchTemplateById(id),
    staleTime: 5 * 60 * 1000, // 5 minutes
    enabled: !!id, // Only fetch if ID is provided
  });
}

// =============================================================================
// Mutation Hooks
// =============================================================================

/**
 * Create new template
 */
export function useCreateTemplate() {
  const queryClient = useQueryClient();

  return useMutation<ProjectTemplate, Error, CreateTemplateRequest>({
    mutationFn: async (data: CreateTemplateRequest) => {
      return createTemplate(data);
    },
    onSuccess: () => {
      // Invalidate all template lists
      queryClient.invalidateQueries({ queryKey: templateKeys.lists() });
    },
  });
}

/**
 * Update existing template
 */
export function useUpdateTemplate() {
  const queryClient = useQueryClient();

  return useMutation<ProjectTemplate, Error, { id: string; data: UpdateTemplateRequest }>({
    mutationFn: async ({ id, data }) => {
      return updateTemplate(id, data);
    },
    onSuccess: (_, { id }) => {
      // Invalidate specific template detail
      queryClient.invalidateQueries({ queryKey: templateKeys.detail(id) });
      // Invalidate all template lists
      queryClient.invalidateQueries({ queryKey: templateKeys.lists() });
    },
  });
}

/**
 * Delete template
 */
export function useDeleteTemplate() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: async (id: string) => {
      return deleteTemplate(id);
    },
    onSuccess: (_, id) => {
      // Invalidate specific template detail
      queryClient.invalidateQueries({ queryKey: templateKeys.detail(id) });
      // Invalidate all template lists
      queryClient.invalidateQueries({ queryKey: templateKeys.lists() });
    },
  });
}

/**
 * Deploy template to a project
 */
export function useDeployTemplate() {
  const queryClient = useQueryClient();

  return useMutation<DeployTemplateResponse, Error, { id: string; data: DeployTemplateRequest }>({
    mutationFn: async ({ id, data }) => {
      return deployTemplate(id, data);
    },
    onSuccess: () => {
      // Invalidate deployment queries if they exist
      queryClient.invalidateQueries({ queryKey: ['deployments'] });
    },
  });
}
