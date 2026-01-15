/**
 * Context entities API service functions
 */
import type {
  ContextEntity,
  CreateContextEntityRequest,
  UpdateContextEntityRequest,
  ContextEntityFilters,
  ContextEntityListResponse,
} from '@/types/context-entity';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';

/**
 * Build API URL with versioned path
 */
function buildUrl(path: string): string {
  return `${API_BASE}/api/${API_VERSION}${path}`;
}

/**
 * Fetch context entities with optional filtering
 */
export async function fetchContextEntities(
  filters?: ContextEntityFilters
): Promise<ContextEntityListResponse> {
  const params = new URLSearchParams();

  // Add filter parameters if provided
  if (filters?.entity_type) {
    params.set('entity_type', filters.entity_type);
  }
  if (filters?.category) {
    params.set('category', filters.category);
  }
  if (filters?.auto_load !== undefined) {
    params.set('auto_load', filters.auto_load.toString());
  }
  if (filters?.search) {
    params.set('search', filters.search);
  }
  if (filters?.limit) {
    params.set('limit', filters.limit.toString());
  }
  if (filters?.after) {
    params.set('after', filters.after);
  }

  const url = buildUrl(`/context-entities${params.toString() ? `?${params.toString()}` : ''}`);
  const response = await fetch(url);

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to fetch context entities: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Fetch single context entity by ID
 */
export async function fetchContextEntity(id: string): Promise<ContextEntity> {
  const response = await fetch(buildUrl(`/context-entities/${id}`));

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to fetch context entity: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Create new context entity
 */
export async function createContextEntity(
  data: CreateContextEntityRequest
): Promise<ContextEntity> {
  const response = await fetch(buildUrl('/context-entities'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to create context entity: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Update existing context entity
 */
export async function updateContextEntity(
  id: string,
  data: UpdateContextEntityRequest
): Promise<ContextEntity> {
  const response = await fetch(buildUrl(`/context-entities/${id}`), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to update context entity: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Delete context entity
 */
export async function deleteContextEntity(id: string): Promise<void> {
  const response = await fetch(buildUrl(`/context-entities/${id}`), {
    method: 'DELETE',
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to delete context entity: ${response.statusText}`);
  }

  // DELETE returns 204 No Content (no body to parse)
}

/**
 * Fetch raw markdown content for a context entity
 */
export async function fetchContextEntityContent(id: string): Promise<string> {
  const response = await fetch(buildUrl(`/context-entities/${id}/content`));

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(
      errorBody.detail || `Failed to fetch context entity content: ${response.statusText}`
    );
  }

  // Content endpoint returns plain text (markdown), not JSON
  return response.text();
}

/**
 * Deploy context entity to a project
 */
export async function deployContextEntity(
  id: string,
  projectPath: string
): Promise<void> {
  const response = await fetch(buildUrl(`/context-entities/${id}/deploy`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_path: projectPath }),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to deploy context entity: ${response.statusText}`);
  }
}
