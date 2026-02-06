/**
 * Context modules API service functions
 */
import { apiRequest } from '@/lib/api';
import type { ContextModuleResponse } from '@/sdk/models/ContextModuleResponse';
import type { ContextModuleListResponse } from '@/sdk/models/ContextModuleListResponse';
import type { ContextModuleCreateRequest } from '@/sdk/models/ContextModuleCreateRequest';
import type { ContextModuleUpdateRequest } from '@/sdk/models/ContextModuleUpdateRequest';
import type { AddMemoryToModuleRequest } from '@/sdk/models/AddMemoryToModuleRequest';
import type { MemoryItemResponse } from '@/sdk/models/MemoryItemResponse';

export async function fetchContextModules(
  projectId: string,
  params?: { limit?: number; cursor?: string }
): Promise<ContextModuleListResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_id', projectId);
  if (params?.limit != null) searchParams.set('limit', String(params.limit));
  if (params?.cursor) searchParams.set('cursor', params.cursor);
  return apiRequest<ContextModuleListResponse>(`/context-modules?${searchParams.toString()}`);
}

export async function fetchContextModule(
  moduleId: string,
  includeItems?: boolean
): Promise<ContextModuleResponse> {
  const params = new URLSearchParams();
  if (includeItems) params.set('include_items', 'true');
  const qs = params.toString();
  return apiRequest<ContextModuleResponse>(`/context-modules/${moduleId}${qs ? `?${qs}` : ''}`);
}

export async function createContextModule(
  projectId: string,
  data: ContextModuleCreateRequest
): Promise<ContextModuleResponse> {
  return apiRequest<ContextModuleResponse>(
    `/context-modules?project_id=${encodeURIComponent(projectId)}`,
    {
      method: 'POST',
      body: JSON.stringify(data),
    }
  );
}

export async function updateContextModule(
  moduleId: string,
  data: ContextModuleUpdateRequest
): Promise<ContextModuleResponse> {
  return apiRequest<ContextModuleResponse>(`/context-modules/${moduleId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteContextModule(moduleId: string): Promise<void> {
  return apiRequest<void>(`/context-modules/${moduleId}`, { method: 'DELETE' });
}

export async function addMemoryToModule(
  moduleId: string,
  data: AddMemoryToModuleRequest
): Promise<ContextModuleResponse> {
  return apiRequest<ContextModuleResponse>(`/context-modules/${moduleId}/memories`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function removeMemoryFromModule(
  moduleId: string,
  memoryId: string
): Promise<void> {
  return apiRequest<void>(`/context-modules/${moduleId}/memories/${memoryId}`, {
    method: 'DELETE',
  });
}

export async function fetchModuleMemories(
  moduleId: string,
  limit?: number
): Promise<MemoryItemResponse[]> {
  const params = new URLSearchParams();
  if (limit != null) params.set('limit', String(limit));
  const qs = params.toString();
  return apiRequest<MemoryItemResponse[]>(
    `/context-modules/${moduleId}/memories${qs ? `?${qs}` : ''}`
  );
}
