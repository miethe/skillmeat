/**
 * React Query hooks for MCP server management
 *
 * Provides data fetching and mutation hooks for MCP servers with
 * automatic caching, refetching, and error handling.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiRequest } from '@/lib/api';
import type {
  DeploymentRequest,
  DeploymentResponse,
  DeploymentStatus,
  MCPServer,
  MCPServerCreateRequest,
  MCPServerListResponse,
  MCPServerUpdateRequest,
} from '@/types/mcp';

// Query keys
export const mcpQueryKeys = {
  all: ['mcp'] as const,
  lists: () => [...mcpQueryKeys.all, 'list'] as const,
  list: (collection?: string) => [...mcpQueryKeys.lists(), collection] as const,
  details: () => [...mcpQueryKeys.all, 'detail'] as const,
  detail: (name: string, collection?: string) =>
    [...mcpQueryKeys.details(), name, collection] as const,
  status: (name: string) => [...mcpQueryKeys.all, 'status', name] as const,
};

// Query hooks

/**
 * Fetch all MCP servers in a collection
 */
export function useMcpServers(collection?: string) {
  return useQuery({
    queryKey: mcpQueryKeys.list(collection),
    queryFn: async (): Promise<MCPServerListResponse> => {
      const params = collection ? `?collection=${collection}` : '';
      return apiRequest<MCPServerListResponse>(`/mcp/servers${params}`);
    },
    staleTime: 30000, // Cache for 30 seconds
  });
}

/**
 * Fetch a specific MCP server by name
 */
export function useMcpServer(name: string, collection?: string) {
  return useQuery({
    queryKey: mcpQueryKeys.detail(name, collection),
    queryFn: async (): Promise<MCPServer> => {
      const params = collection ? `?collection=${collection}` : '';
      return apiRequest<MCPServer>(`/mcp/servers/${name}${params}`);
    },
    enabled: !!name,
    staleTime: 30000,
  });
}

/**
 * Fetch deployment status for an MCP server
 */
export function useMcpDeploymentStatus(name: string) {
  return useQuery({
    queryKey: mcpQueryKeys.status(name),
    queryFn: async (): Promise<DeploymentStatus> => {
      return apiRequest<DeploymentStatus>(`/mcp/servers/${name}/status`);
    },
    enabled: !!name,
    staleTime: 10000, // Refresh more frequently for status
    refetchInterval: 30000, // Auto-refetch every 30 seconds
  });
}

// Mutation hooks

/**
 * Create a new MCP server
 */
export function useCreateMcpServer(collection?: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: MCPServerCreateRequest): Promise<MCPServer> => {
      const params = collection ? `?collection=${collection}` : '';
      return apiRequest<MCPServer>(`/mcp/servers${params}`, {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },
    onSuccess: () => {
      // Invalidate servers list to refetch
      queryClient.invalidateQueries({ queryKey: mcpQueryKeys.lists() });
    },
  });
}

/**
 * Update an existing MCP server
 */
export function useUpdateMcpServer(name: string, collection?: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: MCPServerUpdateRequest): Promise<MCPServer> => {
      const params = collection ? `?collection=${collection}` : '';
      return apiRequest<MCPServer>(`/mcp/servers/${name}${params}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      });
    },
    onSuccess: () => {
      // Invalidate both list and detail queries
      queryClient.invalidateQueries({ queryKey: mcpQueryKeys.lists() });
      queryClient.invalidateQueries({
        queryKey: mcpQueryKeys.detail(name, collection),
      });
    },
  });
}

/**
 * Delete an MCP server
 */
export function useDeleteMcpServer(collection?: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (name: string): Promise<void> => {
      const params = collection ? `?collection=${collection}` : '';
      await apiRequest<void>(`/mcp/servers/${name}${params}`, {
        method: 'DELETE',
      });
    },
    onSuccess: () => {
      // Invalidate servers list to refetch
      queryClient.invalidateQueries({ queryKey: mcpQueryKeys.lists() });
    },
  });
}

/**
 * Deploy an MCP server to Claude Desktop
 */
export function useDeployMcpServer(name: string, collection?: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: DeploymentRequest = {}): Promise<DeploymentResponse> => {
      const params = collection ? `?collection=${collection}` : '';
      return apiRequest<DeploymentResponse>(`/mcp/servers/${name}/deploy${params}`, {
        method: 'POST',
        body: JSON.stringify(request),
      });
    },
    onSuccess: () => {
      // Invalidate server detail and deployment status
      queryClient.invalidateQueries({
        queryKey: mcpQueryKeys.detail(name, collection),
      });
      queryClient.invalidateQueries({ queryKey: mcpQueryKeys.status(name) });
      queryClient.invalidateQueries({ queryKey: mcpQueryKeys.lists() });
    },
  });
}

/**
 * Undeploy an MCP server from Claude Desktop
 */
export function useUndeployMcpServer(name: string, collection?: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (): Promise<DeploymentResponse> => {
      const params = collection ? `?collection=${collection}` : '';
      return apiRequest<DeploymentResponse>(`/mcp/servers/${name}/undeploy${params}`, {
        method: 'POST',
      });
    },
    onSuccess: () => {
      // Invalidate server detail and deployment status
      queryClient.invalidateQueries({
        queryKey: mcpQueryKeys.detail(name, collection),
      });
      queryClient.invalidateQueries({ queryKey: mcpQueryKeys.status(name) });
      queryClient.invalidateQueries({ queryKey: mcpQueryKeys.lists() });
    },
  });
}

/**
 * Hook for batch operations (select multiple servers)
 */
export function useMcpBatchOperations(collection?: string) {
  const deleteMutation = useDeleteMcpServer(collection);

  const deleteMultiple = async (names: string[]) => {
    const results = await Promise.allSettled(names.map((name) => deleteMutation.mutateAsync(name)));

    const succeeded = results.filter((r) => r.status === 'fulfilled').length;
    const failed = results.filter((r) => r.status === 'rejected').length;

    return { succeeded, failed, total: names.length };
  };

  return {
    deleteMultiple,
    isLoading: deleteMutation.isPending,
  };
}
