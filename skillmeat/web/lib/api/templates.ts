/**
 * Template API service functions
 */
import type {
  ProjectTemplate,
  TemplateListResponse,
  CreateTemplateRequest,
  UpdateTemplateRequest,
  DeployTemplateRequest,
  DeployTemplateResponse,
  TemplateFilters,
} from '@/types/template';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';

/**
 * Build API URL with versioned path
 */
function buildUrl(path: string): string {
  return `${API_BASE}/api/${API_VERSION}${path}`;
}

/**
 * Fetch all templates with optional filtering and pagination
 */
export async function fetchTemplates(
  filters?: TemplateFilters
): Promise<TemplateListResponse> {
  const params = new URLSearchParams();

  if (filters?.search) params.set('search', filters.search);
  if (filters?.collection_id) params.set('collection_id', filters.collection_id);
  if (filters?.limit) params.set('limit', filters.limit.toString());
  if (filters?.after) params.set('after', filters.after);

  const url = buildUrl(`/project-templates${params.toString() ? `?${params.toString()}` : ''}`);
  const response = await fetch(url);

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to fetch templates: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Fetch template by ID with full entity details
 */
export async function fetchTemplateById(id: string): Promise<ProjectTemplate> {
  const response = await fetch(buildUrl(`/project-templates/${id}`));

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to fetch template: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Create new template
 */
export async function createTemplate(
  data: CreateTemplateRequest
): Promise<ProjectTemplate> {
  const response = await fetch(buildUrl('/project-templates'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to create template: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Update existing template
 */
export async function updateTemplate(
  id: string,
  data: UpdateTemplateRequest
): Promise<ProjectTemplate> {
  const response = await fetch(buildUrl(`/project-templates/${id}`), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to update template: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Delete template
 */
export async function deleteTemplate(id: string): Promise<void> {
  const response = await fetch(buildUrl(`/project-templates/${id}`), {
    method: 'DELETE',
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to delete template: ${response.statusText}`);
  }
}

/**
 * Deploy template to a project
 */
export async function deployTemplate(
  id: string,
  data: DeployTemplateRequest
): Promise<DeployTemplateResponse> {
  const response = await fetch(buildUrl(`/project-templates/${id}/deploy`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to deploy template: ${response.statusText}`);
  }

  return response.json();
}
