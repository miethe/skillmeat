/**
 * Context entities API service functions
 */
import type {
  ContextEntity,
  CreateContextEntityRequest,
  UpdateContextEntityRequest,
  ContextEntityFilters,
  ContextEntityListResponse,
  ContextEntityDeployRequest,
  ContextEntityDeployResponse,
  EntityTypeConfig,
  EntityTypeConfigCreate,
  EntityTypeConfigUpdate,
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
 * Normalise a single context entity from the API response.
 * The backend may return `type` (Pydantic alias) instead of `entity_type`,
 * so we ensure the frontend always sees `entity_type`.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function normalizeEntity(raw: any): ContextEntity {
  if (raw.entity_type === undefined && raw.type !== undefined) {
    raw.entity_type = raw.type;
  }
  return raw as ContextEntity;
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

  const data = await response.json();
  // Normalise items in case the API returns `type` instead of `entity_type`
  if (data.items) {
    data.items = data.items.map(normalizeEntity);
  }
  return data;
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

  return normalizeEntity(await response.json());
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

  return normalizeEntity(await response.json());
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

  return normalizeEntity(await response.json());
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
  data: ContextEntityDeployRequest
): Promise<ContextEntityDeployResponse> {
  const response = await fetch(buildUrl(`/context-entities/${id}/deploy`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to deploy context entity: ${response.statusText}`);
  }

  return response.json();
}

// ============================================================================
// Entity Type Config API Methods
// ============================================================================

/**
 * Fetch all entity type configurations
 */
export async function fetchEntityTypeConfigs(): Promise<EntityTypeConfig[]> {
  const response = await fetch(buildUrl('/settings/entity-type-configs'));

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(
      errorBody.detail || `Failed to fetch entity type configs: ${response.statusText}`
    );
  }

  return response.json();
}

/**
 * Create a new entity type configuration
 */
export async function createEntityTypeConfig(
  data: EntityTypeConfigCreate
): Promise<EntityTypeConfig> {
  const response = await fetch(buildUrl('/settings/entity-type-configs'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(
      errorBody.detail || `Failed to create entity type config: ${response.statusText}`
    );
  }

  return response.json();
}

/**
 * Update an existing entity type configuration by slug
 */
export async function updateEntityTypeConfig(
  slug: string,
  data: EntityTypeConfigUpdate
): Promise<EntityTypeConfig> {
  const response = await fetch(buildUrl(`/settings/entity-type-configs/${slug}`), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(
      errorBody.detail || `Failed to update entity type config: ${response.statusText}`
    );
  }

  return response.json();
}

/**
 * Delete an entity type configuration by slug
 */
export async function deleteEntityTypeConfig(slug: string): Promise<void> {
  const response = await fetch(buildUrl(`/settings/entity-type-configs/${slug}`), {
    method: 'DELETE',
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(
      errorBody.detail || `Failed to delete entity type config: ${response.statusText}`
    );
  }

  // DELETE returns 204 No Content
}

// ============================================================================
// Entity Category API Methods
// ============================================================================

export interface EntityCategory {
  id: number;
  name: string;
  slug: string;
  description?: string;
  color?: string;
  entity_type_slug?: string;
  platform?: string;
  sort_order: number;
  is_builtin: boolean;
  created_at: string;
  updated_at: string;
}

export interface EntityCategoryCreateRequest {
  name: string;
  slug?: string;
  description?: string;
  color?: string;
  entity_type_slug?: string;
  platform?: string;
  sort_order?: number;
}

export interface EntityCategoryFilters {
  entity_type_slug?: string;
  platform?: string;
}

/**
 * Fetch all entity categories with optional filters
 */
export async function fetchEntityCategories(
  filters?: EntityCategoryFilters
): Promise<EntityCategory[]> {
  const params = new URLSearchParams();
  if (filters?.entity_type_slug) params.set('entity_type_slug', filters.entity_type_slug);
  if (filters?.platform) params.set('platform', filters.platform);

  const qs = params.toString();
  const url = buildUrl(`/settings/entity-categories${qs ? `?${qs}` : ''}`);
  const response = await fetch(url);

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(
      errorBody.detail || `Failed to fetch entity categories: ${response.statusText}`
    );
  }

  return response.json();
}

/**
 * Create a new entity category
 */
export async function createEntityCategory(
  data: EntityCategoryCreateRequest
): Promise<EntityCategory> {
  const response = await fetch(buildUrl('/settings/entity-categories'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(
      errorBody.detail || `Failed to create entity category: ${response.statusText}`
    );
  }

  return response.json();
}

export interface EntityCategoryUpdateRequest {
  name?: string;
  slug?: string;
  description?: string;
  color?: string;
  entity_type_slug?: string;
  platform?: string;
  sort_order?: number;
}

/**
 * Update an existing entity category by slug
 */
export async function updateEntityCategory(
  slug: string,
  data: EntityCategoryUpdateRequest
): Promise<EntityCategory> {
  const response = await fetch(buildUrl(`/settings/entity-categories/${slug}`), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(
      errorBody.detail || `Failed to update entity category: ${response.statusText}`
    );
  }

  return response.json();
}

/**
 * Delete an entity category by slug
 */
export async function deleteEntityCategory(slug: string): Promise<void> {
  const response = await fetch(buildUrl(`/settings/entity-categories/${slug}`), {
    method: 'DELETE',
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(
      errorBody.detail || `Failed to delete entity category: ${response.statusText}`
    );
  }

  // DELETE returns 204 No Content
}
