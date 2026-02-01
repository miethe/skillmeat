/**
 * Entity Lifecycle Management Hook
 *
 * Provides centralized entity management with context for filtering,
 * selection, and CRUD operations across collection and project modes.
 */

import { createContext, useContext, useState, useCallback, useMemo, ReactNode } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiRequest, apiConfig } from '@/lib/api';
import {
  mapArtifactsToEntities,
  type ApiArtifactResponse,
} from '@/lib/api/entity-mapper';
import type { SyncStatus } from '@/types/artifact';
import type { Entity, EntityType, EntityStatus } from '@/types/entity';
import type {
  ArtifactCreateRequest,
  ArtifactCreateResponse,
  ArtifactListResponse,
  ArtifactResponse,
  ArtifactUpdateRequest,
  ArtifactDeployRequest,
  ArtifactSyncRequest,
  ProjectDetail,
} from '@/sdk';

const USE_MOCKS = apiConfig.useMocks;

// ============================================================================
// Mock Fallback Utility
// ============================================================================

/**
 * Wraps an async API call with mock fallback behavior.
 * If the API call fails and mocks are enabled in non-production, logs a warning and returns the mock result.
 * Otherwise, re-throws the error.
 *
 * @param apiCall - The async function that performs the API request
 * @param mockFallback - The value to return (or function to call) when using mock fallback
 * @param context - A string describing the operation for logging purposes
 * @returns The result of the API call or mock fallback
 */
async function withMockFallback<T>(
  apiCall: () => Promise<T>,
  mockFallback: T | (() => T),
  context: string
): Promise<T> {
  try {
    return await apiCall();
  } catch (error) {
    if (USE_MOCKS && process.env.NODE_ENV !== 'production') {
      console.warn(`[entities] ${context} API failed, using mock fallback`, error);
      return typeof mockFallback === 'function' ? (mockFallback as () => T)() : mockFallback;
    }
    throw error;
  }
}

// ============================================================================
// Types
// ============================================================================

/**
 * Entity Lifecycle Context Value
 *
 * Provides centralized state and operations for entity management across collection and project modes.
 */
export interface EntityLifecycleContextValue {
  // ============================================================================
  // State
  // ============================================================================

  /** Current array of entities (filtered by typeFilter and statusFilter) */
  entities: Entity[];
  /** IDs of currently selected entities */
  selectedEntities: string[];
  /** Whether entity data is being loaded */
  isLoading: boolean;
  /** Whether entity data is being refetched */
  isRefetching: boolean;
  /** Any error that occurred during loading or operations */
  error: Error | null;

  // ============================================================================
  // Filters
  // ============================================================================

  /** Filter by entity type (skill, command, agent, mcp, hook) */
  typeFilter: EntityType | null;
  /** Filter by entity status (synced, modified, outdated, conflict) */
  statusFilter: EntityStatus | null;
  /** Full-text search query applied to entity names and descriptions */
  searchQuery: string;

  // ============================================================================
  // Context Mode
  // ============================================================================

  /** Operating mode: 'collection' for global collection view or 'project' for specific project */
  mode: 'collection' | 'project';
  /** Path to project when mode is 'project', undefined for collection mode */
  projectPath?: string;

  // ============================================================================
  // Filter Actions
  // ============================================================================

  /** Update type filter */
  setTypeFilter: (type: EntityType | null) => void;
  /** Update status filter */
  setStatusFilter: (status: EntityStatus | null) => void;
  /** Update search query */
  setSearchQuery: (query: string) => void;

  // ============================================================================
  // Selection Actions
  // ============================================================================

  /** Select a single entity by ID */
  selectEntity: (id: string) => void;
  /** Deselect a single entity by ID */
  deselectEntity: (id: string) => void;
  /** Clear all selected entities */
  clearSelection: () => void;
  /** Select all currently filtered entities */
  selectAll: () => void;

  // ============================================================================
  // CRUD Operations
  // ============================================================================

  /** Create new entity */
  createEntity: (data: CreateEntityInput) => Promise<void>;
  /** Update existing entity (tags, description, aliases) */
  updateEntity: (id: string, data: UpdateEntityInput) => Promise<void>;
  /** Delete entity */
  deleteEntity: (id: string) => Promise<void>;

  // ============================================================================
  // Lifecycle Operations
  // ============================================================================

  /** Deploy entity to specified project */
  deployEntity: (id: string, projectPath: string) => Promise<void>;
  /** Sync entity changes between collection and project */
  syncEntity: (id: string, projectPath: string) => Promise<void>;

  // ============================================================================
  // Utilities
  // ============================================================================

  /** Manually refetch entity list */
  refetch: () => void;
}

/**
 * Input data for creating a new entity
 */
export interface CreateEntityInput {
  /** Entity name (alphanumeric, hyphens, underscores) */
  name: string;
  /** Entity type (skill, command, agent, mcp, hook) */
  type: EntityType;
  /** Source location: GitHub (owner/repo/path[@version]) or local file path */
  source: string;
  /** Source type: GitHub repository or local file system */
  sourceType: 'github' | 'local';
  /** Optional tags for categorization and discovery */
  tags?: string[];
  /** Optional description of the entity */
  description?: string;
}

/**
 * Input data for updating an existing entity
 *
 * Only editable fields are included. Most metadata like name and source are immutable.
 */
export interface UpdateEntityInput {
  /** Updated tags for the entity */
  tags?: string[];
  /** Updated description */
  description?: string;
  /** Updated aliases for quick access */
  aliases?: string[];
}

// ============================================================================
// Context
// ============================================================================

const EntityLifecycleContext = createContext<EntityLifecycleContextValue | null>(null);

// ============================================================================
// Provider Component
// ============================================================================

/**
 * Props for EntityLifecycleProvider component
 */
export interface EntityLifecycleProviderProps {
  /** Child components that will have access to the entity lifecycle context */
  children: ReactNode;
  /** Operating mode: 'collection' (default) or 'project' */
  mode?: 'collection' | 'project';
  /** Required when mode is 'project' - path to the target project directory */
  projectPath?: string;
  /** Optional collection ID for collection mode (defaults to 'default') */
  collectionId?: string;
}

/**
 * EntityLifecycleProvider - Context provider for entity management
 *
 * Provides centralized state and operations for managing entities in both collection
 * and project modes. Handles:
 * - Entity data fetching and caching (via React Query)
 * - Multi-selection with batch operations
 * - Filtering (type, status, search) with client-side refinement
 * - CRUD operations (create, read, update, delete)
 * - Lifecycle operations (deploy, sync)
 * - Error handling and loading states
 *
 * @example
 * ```tsx
 * // Collection view
 * <EntityLifecycleProvider mode="collection">
 *   <EntityManagementPage />
 * </EntityLifecycleProvider>
 *
 * // Project view
 * <EntityLifecycleProvider mode="project" projectPath="/home/user/my-project">
 *   <ProjectManagementPage />
 * </EntityLifecycleProvider>
 * ```
 *
 * @param props - EntityLifecycleProviderProps configuration
 * @returns Context provider wrapping children
 */
export function EntityLifecycleProvider({
  children,
  mode = 'collection',
  projectPath,
  collectionId,
}: EntityLifecycleProviderProps) {
  const queryClient = useQueryClient();

  // ============================================================================
  // State
  // ============================================================================

  const [typeFilter, setTypeFilter] = useState<EntityType | null>(null);
  const [statusFilter, setStatusFilter] = useState<EntityStatus | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedEntities, setSelectedEntities] = useState<string[]>([]);

  // ============================================================================
  // Data Fetching
  // ============================================================================

  const queryKey = useMemo(
    () => ['entities', mode, projectPath, typeFilter, statusFilter, searchQuery],
    [mode, projectPath, typeFilter, statusFilter, searchQuery]
  );

  const {
    data: entities = [],
    isLoading,
    error,
    refetch,
    isRefetching,
  } = useQuery({
    queryKey,
    queryFn: async (): Promise<Entity[]> => {
      if (mode === 'collection') {
        return fetchCollectionEntities(typeFilter, searchQuery, collectionId);
      } else {
        if (!projectPath) {
          throw new Error('Project path is required for project mode');
        }
        return fetchProjectEntities(projectPath, typeFilter, searchQuery);
      }
    },
    staleTime: 5 * 60 * 1000, // 5 minutes - don't refetch if data is fresh
    gcTime: 30 * 60 * 1000, // 30 minutes - keep in cache
  });

  // Apply status filter client-side (Entity.syncStatus maps to EntityStatus)
  const filteredEntities = useMemo(() => {
    if (!statusFilter) return entities;
    return entities.filter((e: Entity) => e.syncStatus === statusFilter);
  }, [entities, statusFilter]);

  // ============================================================================
  // Selection Actions
  // ============================================================================

  const selectEntity = useCallback((id: string) => {
    setSelectedEntities((prev: string[]) => [...new Set([...prev, id])]);
  }, []);

  const deselectEntity = useCallback((id: string) => {
    setSelectedEntities((prev: string[]) => prev.filter((e: string) => e !== id));
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedEntities([]);
  }, []);

  const selectAll = useCallback(() => {
    setSelectedEntities(filteredEntities.map((e: Entity) => e.id));
  }, [filteredEntities]);

  // ============================================================================
  // CRUD Mutations
  // ============================================================================

  const createMutation = useMutation({
    mutationFn: async (data: CreateEntityInput) => {
      const request: ArtifactCreateRequest = {
        name: data.name,
        source: data.source,
        artifact_type: data.type,
        source_type: data.sourceType,
        tags: data.tags,
      };

      await withMockFallback(
        () =>
          apiRequest<ArtifactCreateResponse>('/artifacts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request),
          }),
        undefined,
        'Create'
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['entities'] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: UpdateEntityInput }) => {
      const request: ArtifactUpdateRequest = {
        tags: data.tags,
        aliases: data.aliases,
      };

      await withMockFallback(
        () =>
          apiRequest<ArtifactResponse>(`/artifacts/${encodeURIComponent(id)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request),
          }),
        undefined,
        'Update'
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['entities'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await withMockFallback(
        () =>
          apiRequest<void>(`/artifacts/${encodeURIComponent(id)}`, {
            method: 'DELETE',
          }),
        undefined,
        'Delete'
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['entities'] });
    },
  });

  const deployMutation = useMutation({
    mutationFn: async ({ id, projectPath }: { id: string; projectPath: string }) => {
      const request: ArtifactDeployRequest = {
        project_path: projectPath,
      };

      await withMockFallback(
        () =>
          apiRequest(`/artifacts/${encodeURIComponent(id)}/deploy`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request),
          }),
        undefined,
        'Deploy'
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['entities'] });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });

  const syncMutation = useMutation({
    mutationFn: async ({ id, projectPath }: { id: string; projectPath: string }) => {
      const request: ArtifactSyncRequest = {
        project_path: projectPath,
        strategy: 'ours',
      };

      await withMockFallback(
        () =>
          apiRequest(`/artifacts/${encodeURIComponent(id)}/sync`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request),
          }),
        undefined,
        'Sync'
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['entities'] });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });

  // ============================================================================
  // Public API
  // ============================================================================

  const createEntity = useCallback(
    async (data: CreateEntityInput) => {
      await createMutation.mutateAsync(data);
    },
    [createMutation]
  );

  const updateEntity = useCallback(
    async (id: string, data: UpdateEntityInput) => {
      await updateMutation.mutateAsync({ id, data });
    },
    [updateMutation]
  );

  const deleteEntity = useCallback(
    async (id: string) => {
      await deleteMutation.mutateAsync(id);
    },
    [deleteMutation]
  );

  const deployEntity = useCallback(
    async (id: string, targetProjectPath: string) => {
      await deployMutation.mutateAsync({ id, projectPath: targetProjectPath });
    },
    [deployMutation]
  );

  const syncEntity = useCallback(
    async (id: string, targetProjectPath: string) => {
      await syncMutation.mutateAsync({ id, projectPath: targetProjectPath });
    },
    [syncMutation]
  );

  // ============================================================================
  // Context Value
  // ============================================================================

  const value: EntityLifecycleContextValue = {
    // State
    entities: filteredEntities,
    selectedEntities,
    isLoading,
    isRefetching,
    error: error as Error | null,

    // Filters
    typeFilter,
    statusFilter,
    searchQuery,

    // Context mode
    mode,
    projectPath,

    // Actions
    setTypeFilter,
    setStatusFilter,
    setSearchQuery,
    selectEntity,
    deselectEntity,
    clearSelection,
    selectAll,

    // CRUD operations
    createEntity,
    updateEntity,
    deleteEntity,

    // Lifecycle operations
    deployEntity,
    syncEntity,

    // Refetch
    refetch,
  };

  return (
    <EntityLifecycleContext.Provider value={value}>{children}</EntityLifecycleContext.Provider>
  );
}

// ============================================================================
// Hook
// ============================================================================

/**
 * useEntityLifecycle - Hook to access entity management context
 *
 * Provides full access to entity state, filters, selections, and operations.
 * Must be used within EntityLifecycleProvider.
 *
 * @throws {Error} If used outside of EntityLifecycleProvider
 *
 * @example
 * ```tsx
 * function EntityManager() {
 *   const {
 *     entities,
 *     selectedEntities,
 *     createEntity,
 *     deleteEntity,
 *     deployEntity,
 *   } = useEntityLifecycle();
 *
 *   return (
 *     <div>
 *       <EntityList entities={entities} />
 *       <Button onClick={() => createEntity({...})}>
 *         Create Entity
 *       </Button>
 *     </div>
 *   );
 * }
 * ```
 *
 * @returns EntityLifecycleContextValue with all state and operations
 */
export function useEntityLifecycle(): EntityLifecycleContextValue {
  const context = useContext(EntityLifecycleContext);
  if (!context) {
    throw new Error('useEntityLifecycle must be used within EntityLifecycleProvider');
  }
  return context;
}

// ============================================================================
// Helper Functions
// ============================================================================

async function fetchCollectionEntities(
  typeFilter: EntityType | null,
  searchQuery: string,
  collectionId?: string
): Promise<Entity[]> {
  const params = new URLSearchParams({
    limit: '100',
  });

  if (typeFilter) {
    params.set('artifact_type', typeFilter);
  }

  const processResponse = (response: ArtifactListResponse): Entity[] => {
    // Use centralized mapper with 'collection' context
    const entities: Entity[] = mapArtifactsToEntities(
      response.items as ApiArtifactResponse[],
      'collection'
    );

    // Attach collection info if provided (mapper doesn't have access to external collectionId)
    const entitiesWithCollection: Entity[] = entities.map((entity) => ({
      ...entity,
      collection: collectionId || entity.collection || 'default',
    }));

    // Apply search filter client-side
    if (searchQuery) {
      const searchLower = searchQuery.toLowerCase();
      return entitiesWithCollection.filter(
        (e: Entity) =>
          e.name.toLowerCase().includes(searchLower) ||
          e.description?.toLowerCase().includes(searchLower) ||
          e.tags?.some((tag: string) => tag.toLowerCase().includes(searchLower))
      );
    }

    return entitiesWithCollection;
  };

  return withMockFallback(
    async () => {
      const response = await apiRequest<ArtifactListResponse>(`/artifacts?${params.toString()}`);
      return processResponse(response);
    },
    () => generateMockCollectionEntities(typeFilter, searchQuery, collectionId),
    'Collection'
  );
}

async function fetchProjectEntities(
  projectPath: string,
  typeFilter: EntityType | null,
  searchQuery: string
): Promise<Entity[]> {
  const processResponse = (response: ProjectDetail): Entity[] => {
    // Map deployments to entities
    const deployments = response.deployments || [];
    const now = new Date().toISOString();
    const entities: Entity[] = deployments.map((deployment) => ({
      id: `${deployment.artifact_type}:${deployment.artifact_name}`,
      name: deployment.artifact_name,
      type: deployment.artifact_type as EntityType,
      scope: 'local' as const,
      collection: deployment.from_collection,
      projectPath,
      syncStatus: (deployment.local_modifications ? 'modified' : 'synced') as SyncStatus,
      version: deployment.version || undefined,
      source: deployment.artifact_path,
      deployedAt: deployment.deployed_at,
      modifiedAt: deployment.deployed_at,
      createdAt: deployment.deployed_at || now,
      updatedAt: deployment.deployed_at || now,
    }));

    // Apply type filter
    let filtered = typeFilter ? entities.filter((e: Entity) => e.type === typeFilter) : entities;

    // Apply search filter
    if (searchQuery) {
      const searchLower = searchQuery.toLowerCase();
      filtered = filtered.filter((e: Entity) => e.name.toLowerCase().includes(searchLower));
    }

    return filtered;
  };

  // Encode project path as base64 for use as ID
  const projectId = btoa(projectPath);

  return withMockFallback(
    async () => {
      const response = await apiRequest<ProjectDetail>(`/projects/${projectId}`);
      return processResponse(response);
    },
    () => generateMockProjectEntities(projectPath, typeFilter, searchQuery),
    'Project'
  );
}

// ============================================================================
// Mock Data Generators
// ============================================================================

function generateMockCollectionEntities(
  typeFilter: EntityType | null,
  searchQuery: string,
  collectionId?: string
): Entity[] {
  const effectiveCollection = collectionId || 'default';

  const mockEntities: Entity[] = [
    {
      id: 'skill:canvas-design',
      name: 'canvas-design',
      type: 'skill',
      scope: 'user',
      collection: effectiveCollection,
      syncStatus: 'synced',
      tags: ['design', 'visual'],
      description: 'Create and edit visual designs with an interactive canvas',
      version: 'v2.1.0',
      source: 'anthropics/skills/canvas-design',
      createdAt: new Date(Date.now() - 30 * 86400000).toISOString(),
      updatedAt: new Date(Date.now() - 2 * 86400000).toISOString(),
      deployedAt: new Date(Date.now() - 30 * 86400000).toISOString(),
      modifiedAt: new Date(Date.now() - 2 * 86400000).toISOString(),
    },
    {
      id: 'skill:docx-processor',
      name: 'docx-processor',
      type: 'skill',
      scope: 'user',
      collection: effectiveCollection,
      syncStatus: 'outdated',
      tags: ['document', 'docx'],
      description: 'Read and process Microsoft Word documents',
      version: 'v1.5.0',
      source: 'anthropics/skills/document-skills/docx',
      createdAt: new Date(Date.now() - 60 * 86400000).toISOString(),
      updatedAt: new Date(Date.now() - 45 * 86400000).toISOString(),
      deployedAt: new Date(Date.now() - 60 * 86400000).toISOString(),
      modifiedAt: new Date(Date.now() - 45 * 86400000).toISOString(),
    },
    {
      id: 'command:git-helper',
      name: 'git-helper',
      type: 'command',
      scope: 'user',
      collection: effectiveCollection,
      syncStatus: 'synced',
      tags: ['git', 'vcs'],
      description: 'Custom git workflow commands',
      version: 'v1.0.0',
      source: 'local',
      createdAt: new Date(Date.now() - 90 * 86400000).toISOString(),
      updatedAt: new Date(Date.now() - 7 * 86400000).toISOString(),
      deployedAt: new Date(Date.now() - 90 * 86400000).toISOString(),
      modifiedAt: new Date(Date.now() - 7 * 86400000).toISOString(),
    },
  ];

  let filtered = typeFilter
    ? mockEntities.filter((e: Entity) => e.type === typeFilter)
    : mockEntities;

  if (searchQuery) {
    const searchLower = searchQuery.toLowerCase();
    filtered = filtered.filter(
      (e: Entity) =>
        e.name.toLowerCase().includes(searchLower) ||
        e.description?.toLowerCase().includes(searchLower)
    );
  }

  return filtered;
}

function generateMockProjectEntities(
  projectPath: string,
  typeFilter: EntityType | null,
  searchQuery: string
): Entity[] {
  const mockEntities: Entity[] = [
    {
      id: 'skill:canvas-design',
      name: 'canvas-design',
      type: 'skill',
      scope: 'local',
      projectPath,
      syncStatus: 'synced',
      version: 'v2.1.0',
      source: 'skills/canvas-design',
      createdAt: new Date(Date.now() - 2 * 86400000).toISOString(),
      updatedAt: new Date(Date.now() - 2 * 86400000).toISOString(),
      deployedAt: new Date(Date.now() - 2 * 86400000).toISOString(),
      modifiedAt: new Date(Date.now() - 2 * 86400000).toISOString(),
    },
    {
      id: 'skill:docx-processor',
      name: 'docx-processor',
      type: 'skill',
      scope: 'local',
      projectPath,
      syncStatus: 'modified',
      version: 'v1.5.0',
      source: 'skills/docx-processor',
      createdAt: new Date(Date.now() - 5 * 86400000).toISOString(),
      updatedAt: new Date(Date.now() - 1 * 86400000).toISOString(),
      deployedAt: new Date(Date.now() - 5 * 86400000).toISOString(),
      modifiedAt: new Date(Date.now() - 1 * 86400000).toISOString(),
    },
  ];

  let filtered = typeFilter
    ? mockEntities.filter((e: Entity) => e.type === typeFilter)
    : mockEntities;

  if (searchQuery) {
    const searchLower = searchQuery.toLowerCase();
    filtered = filtered.filter((e: Entity) => e.name.toLowerCase().includes(searchLower));
  }

  return filtered;
}
