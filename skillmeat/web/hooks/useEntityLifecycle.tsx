/**
 * Entity Lifecycle Management Hook
 *
 * Provides centralized entity management with context for filtering,
 * selection, and CRUD operations across collection and project modes.
 */

import { createContext, useContext, useState, useCallback, useMemo, ReactNode } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiRequest, apiConfig } from '@/lib/api';
import type {
  Entity,
  EntityType,
  EntityStatus,
} from '@/types/entity';
import type {
  ArtifactCreateRequest,
  ArtifactCreateResponse,
  ArtifactResponse,
  ArtifactListResponse,
  ArtifactUpdateRequest,
  ArtifactDeployRequest,
  ArtifactSyncRequest,
  ProjectDetail,
} from '@/sdk';

const USE_MOCKS = apiConfig.useMocks;

// ============================================================================
// Types
// ============================================================================

export interface EntityLifecycleContextValue {
  // State
  entities: Entity[];
  selectedEntities: string[];
  isLoading: boolean;
  error: Error | null;

  // Filters
  typeFilter: EntityType | null;
  statusFilter: EntityStatus | null;
  searchQuery: string;

  // Context mode
  mode: 'collection' | 'project';
  projectPath?: string;

  // Actions
  setTypeFilter: (type: EntityType | null) => void;
  setStatusFilter: (status: EntityStatus | null) => void;
  setSearchQuery: (query: string) => void;
  selectEntity: (id: string) => void;
  deselectEntity: (id: string) => void;
  clearSelection: () => void;
  selectAll: () => void;

  // CRUD operations
  createEntity: (data: CreateEntityInput) => Promise<void>;
  updateEntity: (id: string, data: UpdateEntityInput) => Promise<void>;
  deleteEntity: (id: string) => Promise<void>;

  // Lifecycle operations
  deployEntity: (id: string, projectPath: string) => Promise<void>;
  syncEntity: (id: string, projectPath: string) => Promise<void>;

  // Refetch
  refetch: () => void;
}

export interface CreateEntityInput {
  name: string;
  type: EntityType;
  source: string;
  sourceType: 'github' | 'local';
  tags?: string[];
  description?: string;
}

export interface UpdateEntityInput {
  tags?: string[];
  description?: string;
  aliases?: string[];
}

// ============================================================================
// Context
// ============================================================================

const EntityLifecycleContext = createContext<EntityLifecycleContextValue | null>(null);

// ============================================================================
// API Mapping Functions
// ============================================================================

function mapApiArtifactToEntity(artifact: ArtifactResponse, mode: 'collection' | 'project', projectPath?: string): Entity {
  const metadata = artifact.metadata || {};
  const upstream = artifact.upstream;
  const isOutdated = upstream?.update_available ?? false;
  const hasLocalMods = upstream?.has_local_modifications ?? false;

  let status: EntityStatus = 'synced';
  if (hasLocalMods) status = 'modified';
  else if (isOutdated) status = 'outdated';

  return {
    id: artifact.id,
    name: artifact.name,
    type: artifact.type as EntityType,
    collection: mode === 'collection' ? 'default' : undefined,
    projectPath: mode === 'project' ? projectPath : undefined,
    status,
    tags: metadata.tags || [],
    description: metadata.description || undefined,
    version: artifact.version || metadata.version || undefined,
    source: artifact.source,
    deployedAt: artifact.added,
    modifiedAt: artifact.updated,
    aliases: artifact.aliases || [],
  };
}

// ============================================================================
// Provider Component
// ============================================================================

export interface EntityLifecycleProviderProps {
  children: ReactNode;
  mode?: 'collection' | 'project';
  projectPath?: string;
}

export function EntityLifecycleProvider({
  children,
  mode = 'collection',
  projectPath,
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
  } = useQuery({
    queryKey,
    queryFn: async (): Promise<Entity[]> => {
      if (mode === 'collection') {
        return fetchCollectionEntities(typeFilter, searchQuery);
      } else {
        if (!projectPath) {
          throw new Error('Project path is required for project mode');
        }
        return fetchProjectEntities(projectPath, typeFilter, searchQuery);
      }
    },
    staleTime: 30000,
  });

  // Apply status filter client-side
  const filteredEntities = useMemo(() => {
    if (!statusFilter) return entities;
    return entities.filter((e: Entity) => e.status === statusFilter);
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

      try {
        await apiRequest<ArtifactCreateResponse>('/artifacts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(request),
        });
      } catch (error) {
        if (USE_MOCKS) {
          console.warn('[entities] Create API failed, using mock', error);
          return;
        }
        throw error;
      }
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

      try {
        await apiRequest<ArtifactResponse>(`/artifacts/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(request),
        });
      } catch (error) {
        if (USE_MOCKS) {
          console.warn('[entities] Update API failed, using mock', error);
          return;
        }
        throw error;
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['entities'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      try {
        await apiRequest<void>(`/artifacts/${id}`, {
          method: 'DELETE',
        });
      } catch (error) {
        if (USE_MOCKS) {
          console.warn('[entities] Delete API failed, using mock', error);
          return;
        }
        throw error;
      }
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

      try {
        await apiRequest(`/artifacts/${id}/deploy`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(request),
        });
      } catch (error) {
        if (USE_MOCKS) {
          console.warn('[entities] Deploy API failed, using mock', error);
          return;
        }
        throw error;
      }
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

      try {
        await apiRequest(`/artifacts/${id}/sync`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(request),
        });
      } catch (error) {
        if (USE_MOCKS) {
          console.warn('[entities] Sync API failed, using mock', error);
          return;
        }
        throw error;
      }
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
    <EntityLifecycleContext.Provider value={value}>
      {children}
    </EntityLifecycleContext.Provider>
  );
}

// ============================================================================
// Hook
// ============================================================================

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
  searchQuery: string
): Promise<Entity[]> {
  const params = new URLSearchParams({
    limit: '100',
  });

  if (typeFilter) {
    params.set('artifact_type', typeFilter);
  }

  try {
    const response = await apiRequest<ArtifactListResponse>(`/artifacts?${params.toString()}`);
    const entities = response.items.map(item => mapApiArtifactToEntity(item, 'collection'));

    // Apply search filter client-side
    if (searchQuery) {
      const searchLower = searchQuery.toLowerCase();
      return entities.filter(
        (e: Entity) =>
          e.name.toLowerCase().includes(searchLower) ||
          e.description?.toLowerCase().includes(searchLower) ||
          e.tags?.some((tag: string) => tag.toLowerCase().includes(searchLower))
      );
    }

    return entities;
  } catch (error) {
    if (USE_MOCKS) {
      console.warn('[entities] Collection API failed, using mock data', error);
      return generateMockCollectionEntities(typeFilter, searchQuery);
    }
    throw error;
  }
}

async function fetchProjectEntities(
  projectPath: string,
  typeFilter: EntityType | null,
  searchQuery: string
): Promise<Entity[]> {
  try {
    // Encode project path as base64 for use as ID
    const projectId = btoa(projectPath);
    const response = await apiRequest<ProjectDetail>(`/projects/${projectId}`);

    // Map deployments to entities
    const deployments = response.deployments || [];
    const entities: Entity[] = deployments.map(deployment => ({
      id: `${deployment.artifact_type}:${deployment.artifact_name}`,
      name: deployment.artifact_name,
      type: deployment.artifact_type as EntityType,
      projectPath,
      status: (deployment.local_modifications ? 'modified' : 'synced') as EntityStatus,
      version: deployment.version || undefined,
      source: deployment.artifact_path,
      deployedAt: deployment.deployed_at,
      modifiedAt: deployment.deployed_at,
    }));

    // Apply type filter
    let filtered = typeFilter ? entities.filter((e: Entity) => e.type === typeFilter) : entities;

    // Apply search filter
    if (searchQuery) {
      const searchLower = searchQuery.toLowerCase();
      filtered = filtered.filter((e: Entity) => e.name.toLowerCase().includes(searchLower));
    }

    return filtered;
  } catch (error) {
    if (USE_MOCKS) {
      console.warn('[entities] Project API failed, using mock data', error);
      return generateMockProjectEntities(projectPath, typeFilter, searchQuery);
    }
    throw error;
  }
}

// ============================================================================
// Mock Data Generators
// ============================================================================

function generateMockCollectionEntities(
  typeFilter: EntityType | null,
  searchQuery: string
): Entity[] {
  const mockEntities: Entity[] = [
    {
      id: 'skill:canvas-design',
      name: 'canvas-design',
      type: 'skill',
      collection: 'default',
      status: 'synced',
      tags: ['design', 'visual'],
      description: 'Create and edit visual designs with an interactive canvas',
      version: 'v2.1.0',
      source: 'anthropics/skills/canvas-design',
      deployedAt: new Date(Date.now() - 30 * 86400000).toISOString(),
      modifiedAt: new Date(Date.now() - 2 * 86400000).toISOString(),
    },
    {
      id: 'skill:docx-processor',
      name: 'docx-processor',
      type: 'skill',
      collection: 'default',
      status: 'outdated',
      tags: ['document', 'docx'],
      description: 'Read and process Microsoft Word documents',
      version: 'v1.5.0',
      source: 'anthropics/skills/document-skills/docx',
      deployedAt: new Date(Date.now() - 60 * 86400000).toISOString(),
      modifiedAt: new Date(Date.now() - 45 * 86400000).toISOString(),
    },
    {
      id: 'command:git-helper',
      name: 'git-helper',
      type: 'command',
      collection: 'default',
      status: 'synced',
      tags: ['git', 'vcs'],
      description: 'Custom git workflow commands',
      version: 'v1.0.0',
      source: 'local',
      deployedAt: new Date(Date.now() - 90 * 86400000).toISOString(),
      modifiedAt: new Date(Date.now() - 7 * 86400000).toISOString(),
    },
  ];

  let filtered = typeFilter ? mockEntities.filter((e: Entity) => e.type === typeFilter) : mockEntities;

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
      projectPath,
      status: 'synced',
      version: 'v2.1.0',
      source: 'skills/canvas-design',
      deployedAt: new Date(Date.now() - 2 * 86400000).toISOString(),
      modifiedAt: new Date(Date.now() - 2 * 86400000).toISOString(),
    },
    {
      id: 'skill:docx-processor',
      name: 'docx-processor',
      type: 'skill',
      projectPath,
      status: 'modified',
      version: 'v1.5.0',
      source: 'skills/docx-processor',
      deployedAt: new Date(Date.now() - 5 * 86400000).toISOString(),
      modifiedAt: new Date(Date.now() - 1 * 86400000).toISOString(),
    },
  ];

  let filtered = typeFilter ? mockEntities.filter((e: Entity) => e.type === typeFilter) : mockEntities;

  if (searchQuery) {
    const searchLower = searchQuery.toLowerCase();
    filtered = filtered.filter((e: Entity) => e.name.toLowerCase().includes(searchLower));
  }

  return filtered;
}
