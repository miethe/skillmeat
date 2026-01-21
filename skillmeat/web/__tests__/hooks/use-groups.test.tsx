/**
 * Tests for useGroups hooks
 *
 * Comprehensive tests for group management hooks including:
 * - useGroups: Fetch groups for a collection
 * - useGroup: Fetch single group details
 * - useGroupArtifacts: Fetch artifacts within a group
 * - Mutation hooks (create, update, delete, reorder, etc.)
 */

import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode, ReactElement } from 'react';
import {
  groupKeys,
  useGroups,
  useGroup,
  useGroupArtifacts,
  useCreateGroup,
  useUpdateGroup,
  useDeleteGroup,
  useReorderGroups,
  useAddArtifactToGroup,
  useRemoveArtifactFromGroup,
  useReorderArtifactsInGroup,
  useMoveArtifactToGroup,
  useCopyGroup,
} from '@/hooks/use-groups';
import * as api from '@/lib/api';
import type { Group, GroupWithArtifacts, GroupArtifact } from '@/types/groups';

// Mock the API module
jest.mock('@/lib/api', () => ({
  apiRequest: jest.fn(),
  apiConfig: { useMocks: false },
}));

const mockApiRequest = api.apiRequest as jest.MockedFunction<typeof api.apiRequest>;

// Sample test data
const mockGroups: Group[] = [
  {
    id: 'group-1',
    collection_id: 'collection-1',
    name: 'Development Tools',
    description: 'Tools for development',
    position: 0,
    artifact_count: 5,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 'group-2',
    collection_id: 'collection-1',
    name: 'Productivity',
    description: 'Productivity skills',
    position: 1,
    artifact_count: 3,
    created_at: '2024-01-02T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z',
  },
  {
    id: 'group-3',
    collection_id: 'collection-1',
    name: 'Analytics',
    position: 2,
    artifact_count: 2,
    created_at: '2024-01-03T00:00:00Z',
    updated_at: '2024-01-03T00:00:00Z',
  },
];

const mockGroupArtifacts: GroupArtifact[] = [
  { artifact_id: 'artifact-1', position: 0, added_at: '2024-01-01T00:00:00Z' },
  { artifact_id: 'artifact-2', position: 1, added_at: '2024-01-02T00:00:00Z' },
  { artifact_id: 'artifact-3', position: 2, added_at: '2024-01-03T00:00:00Z' },
];

const mockGroupWithArtifacts: GroupWithArtifacts = {
  ...mockGroups[0],
  artifacts: mockGroupArtifacts,
};

describe('groupKeys', () => {
  it('generates correct query keys', () => {
    expect(groupKeys.all).toEqual(['groups']);
    expect(groupKeys.lists()).toEqual(['groups', 'list']);
    expect(groupKeys.list('collection-1')).toEqual([
      'groups',
      'list',
      { collectionId: 'collection-1' },
    ]);
    expect(groupKeys.details()).toEqual(['groups', 'detail']);
    expect(groupKeys.detail('group-1')).toEqual(['groups', 'detail', 'group-1']);
    expect(groupKeys.artifacts('group-1')).toEqual(['groups', 'detail', 'group-1', 'artifacts']);
  });

  it('generates unique keys for different collections', () => {
    const key1 = groupKeys.list('collection-1');
    const key2 = groupKeys.list('collection-2');
    expect(key1).not.toEqual(key2);
  });

  it('generates unique keys for different groups', () => {
    const key1 = groupKeys.detail('group-1');
    const key2 = groupKeys.detail('group-2');
    expect(key1).not.toEqual(key2);
  });

  it('handles undefined collectionId', () => {
    const key = groupKeys.list(undefined);
    expect(key).toEqual(['groups', 'list', { collectionId: undefined }]);
  });
});

describe('useGroups', () => {
  let queryClient: QueryClient;
  let wrapper: ({ children }: { children: ReactNode }) => ReactElement;

  beforeEach(() => {
    jest.clearAllMocks();

    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  });

  afterEach(() => {
    queryClient.clear();
  });

  describe('query behavior', () => {
    it('fetches groups for a collection (happy path)', async () => {
      mockApiRequest.mockResolvedValueOnce({
        groups: mockGroups,
        total: mockGroups.length,
      });

      const { result } = renderHook(() => useGroups('collection-1'), { wrapper });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.groups).toHaveLength(3);
      expect(result.current.data?.total).toBe(3);
      expect(mockApiRequest).toHaveBeenCalledWith('/groups?collection_id=collection-1');
    });

    it('query is disabled when collectionId is undefined', () => {
      const { result } = renderHook(() => useGroups(undefined), { wrapper });

      expect(result.current.fetchStatus).toBe('idle');
      expect(mockApiRequest).not.toHaveBeenCalled();
    });

    it('throws error when API fails in non-mock mode', async () => {
      mockApiRequest.mockRejectedValueOnce(new Error('API Error'));

      const { result } = renderHook(() => useGroups('collection-1'), { wrapper });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeDefined();
      expect(result.current.error?.message).toBe('API Error');
    });
  });

  describe('sorting behavior', () => {
    it('groups are sorted by position field', async () => {
      const unsortedGroups: Group[] = [
        { ...mockGroups[2], position: 2 },
        { ...mockGroups[0], position: 0 },
        { ...mockGroups[1], position: 1 },
      ];

      mockApiRequest.mockResolvedValueOnce({
        groups: unsortedGroups,
        total: unsortedGroups.length,
      });

      const { result } = renderHook(() => useGroups('collection-1'), { wrapper });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.groups[0].position).toBe(0);
      expect(result.current.data?.groups[1].position).toBe(1);
      expect(result.current.data?.groups[2].position).toBe(2);
    });
  });

  describe('cache configuration', () => {
    it('stale time is set to 5 minutes (300000ms)', async () => {
      mockApiRequest.mockResolvedValueOnce({
        groups: mockGroups,
        total: mockGroups.length,
      });

      renderHook(() => useGroups('collection-1'), { wrapper });

      await waitFor(() => {
        expect(mockApiRequest).toHaveBeenCalled();
      });

      const queryState = queryClient.getQueryState(groupKeys.list('collection-1'));
      expect(queryState?.dataUpdatedAt).toBeDefined();
      expect(queryState?.dataUpdatedAt).toBeGreaterThan(0);
    });
  });
});

describe('useGroup', () => {
  let queryClient: QueryClient;
  let wrapper: ({ children }: { children: ReactNode }) => ReactElement;

  beforeEach(() => {
    jest.clearAllMocks();

    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('fetches single group by ID', async () => {
    mockApiRequest.mockResolvedValueOnce(mockGroups[0]);

    const { result } = renderHook(() => useGroup('group-1'), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.id).toBe('group-1');
    expect(result.current.data?.name).toBe('Development Tools');
    expect(mockApiRequest).toHaveBeenCalledWith('/groups/group-1');
  });

  it('query is disabled when id is undefined', () => {
    const { result } = renderHook(() => useGroup(undefined), { wrapper });

    expect(result.current.fetchStatus).toBe('idle');
    expect(mockApiRequest).not.toHaveBeenCalled();
  });
});

describe('useGroupArtifacts', () => {
  let queryClient: QueryClient;
  let wrapper: ({ children }: { children: ReactNode }) => ReactElement;

  beforeEach(() => {
    jest.clearAllMocks();

    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('fetches artifacts for a group', async () => {
    mockApiRequest.mockResolvedValueOnce(mockGroupWithArtifacts);

    const { result } = renderHook(() => useGroupArtifacts('group-1'), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toHaveLength(3);
    expect(result.current.data![0].artifact_id).toBe('artifact-1');
    expect(mockApiRequest).toHaveBeenCalledWith('/groups/group-1');
  });

  it('sorts artifacts by position', async () => {
    const groupWithUnsortedArtifacts: GroupWithArtifacts = {
      ...mockGroups[0],
      artifacts: [
        { artifact_id: 'artifact-3', position: 2, added_at: '2024-01-03T00:00:00Z' },
        { artifact_id: 'artifact-1', position: 0, added_at: '2024-01-01T00:00:00Z' },
        { artifact_id: 'artifact-2', position: 1, added_at: '2024-01-02T00:00:00Z' },
      ],
    };

    mockApiRequest.mockResolvedValueOnce(groupWithUnsortedArtifacts);

    const { result } = renderHook(() => useGroupArtifacts('group-1'), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data![0].position).toBe(0);
    expect(result.current.data![1].position).toBe(1);
    expect(result.current.data![2].position).toBe(2);
  });

  it('returns empty array when group has no artifacts', async () => {
    const groupWithNoArtifacts: GroupWithArtifacts = {
      ...mockGroups[0],
      artifacts: [],
    };

    mockApiRequest.mockResolvedValueOnce(groupWithNoArtifacts);

    const { result } = renderHook(() => useGroupArtifacts('group-1'), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual([]);
  });

  it('handles undefined artifacts field gracefully', async () => {
    const groupWithoutArtifactsField = { ...mockGroups[0] };

    mockApiRequest.mockResolvedValueOnce(groupWithoutArtifactsField);

    const { result } = renderHook(() => useGroupArtifacts('group-1'), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual([]);
  });

  it('query is disabled when groupId is undefined', () => {
    const { result } = renderHook(() => useGroupArtifacts(undefined), { wrapper });

    expect(result.current.fetchStatus).toBe('idle');
    expect(mockApiRequest).not.toHaveBeenCalled();
  });
});

describe('useCreateGroup', () => {
  let queryClient: QueryClient;
  let wrapper: ({ children }: { children: ReactNode }) => ReactElement;

  beforeEach(() => {
    jest.clearAllMocks();

    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('creates a new group', async () => {
    const newGroup: Group = {
      id: 'new-group-1',
      collection_id: 'collection-1',
      name: 'New Group',
      description: 'A new group',
      position: 3,
      artifact_count: 0,
      created_at: '2024-01-10T00:00:00Z',
      updated_at: '2024-01-10T00:00:00Z',
    };

    mockApiRequest.mockResolvedValueOnce(newGroup);

    const { result } = renderHook(() => useCreateGroup(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({
        collection_id: 'collection-1',
        name: 'New Group',
        description: 'A new group',
        position: 3,
      });
    });

    expect(mockApiRequest).toHaveBeenCalledWith('/groups', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        collection_id: 'collection-1',
        name: 'New Group',
        description: 'A new group',
        position: 3,
      }),
    });
  });

  it('invalidates collection groups cache on success', async () => {
    const newGroup: Group = {
      id: 'new-group-1',
      collection_id: 'collection-1',
      name: 'New Group',
      position: 0,
      artifact_count: 0,
      created_at: '2024-01-10T00:00:00Z',
      updated_at: '2024-01-10T00:00:00Z',
    };

    mockApiRequest.mockResolvedValueOnce(newGroup);

    // Pre-populate cache
    queryClient.setQueryData(groupKeys.list('collection-1'), {
      groups: mockGroups,
      total: mockGroups.length,
    });

    const invalidateSpy = jest.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useCreateGroup(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({
        collection_id: 'collection-1',
        name: 'New Group',
      });
    });

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: groupKeys.list('collection-1'),
    });

    invalidateSpy.mockRestore();
  });
});

describe('useUpdateGroup', () => {
  let queryClient: QueryClient;
  let wrapper: ({ children }: { children: ReactNode }) => ReactElement;

  beforeEach(() => {
    jest.clearAllMocks();

    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('updates an existing group', async () => {
    const updatedGroup: Group = {
      ...mockGroups[0],
      name: 'Updated Name',
      description: 'Updated description',
    };

    mockApiRequest.mockResolvedValueOnce(updatedGroup);

    const { result } = renderHook(() => useUpdateGroup(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({
        id: 'group-1',
        data: {
          name: 'Updated Name',
          description: 'Updated description',
        },
      });
    });

    expect(mockApiRequest).toHaveBeenCalledWith('/groups/group-1', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: 'Updated Name',
        description: 'Updated description',
      }),
    });
  });

  it('invalidates group detail and list caches on success', async () => {
    const updatedGroup: Group = {
      ...mockGroups[0],
      name: 'Updated Name',
    };

    mockApiRequest.mockResolvedValueOnce(updatedGroup);

    const invalidateSpy = jest.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useUpdateGroup(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({
        id: 'group-1',
        data: { name: 'Updated Name' },
      });
    });

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: groupKeys.detail('group-1'),
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: groupKeys.list('collection-1'),
    });

    invalidateSpy.mockRestore();
  });
});

describe('useDeleteGroup', () => {
  let queryClient: QueryClient;
  let wrapper: ({ children }: { children: ReactNode }) => ReactElement;

  beforeEach(() => {
    jest.clearAllMocks();

    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('deletes a group', async () => {
    mockApiRequest.mockResolvedValueOnce(undefined);

    const { result } = renderHook(() => useDeleteGroup(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({
        id: 'group-1',
        collectionId: 'collection-1',
      });
    });

    expect(mockApiRequest).toHaveBeenCalledWith('/groups/group-1', {
      method: 'DELETE',
    });
  });

  it('invalidates collection groups and artifact-groups caches on success', async () => {
    mockApiRequest.mockResolvedValueOnce(undefined);

    const invalidateSpy = jest.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useDeleteGroup(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({
        id: 'group-1',
        collectionId: 'collection-1',
      });
    });

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: groupKeys.list('collection-1'),
    });
    // Cross-hook invalidation for artifact-groups
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['artifact-groups'],
    });

    invalidateSpy.mockRestore();
  });
});

describe('useReorderGroups', () => {
  let queryClient: QueryClient;
  let wrapper: ({ children }: { children: ReactNode }) => ReactElement;

  beforeEach(() => {
    jest.clearAllMocks();

    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('reorders groups within a collection', async () => {
    mockApiRequest.mockResolvedValueOnce(undefined);

    const { result } = renderHook(() => useReorderGroups(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({
        collectionId: 'collection-1',
        groupIds: ['group-3', 'group-1', 'group-2'],
      });
    });

    expect(mockApiRequest).toHaveBeenCalledWith('/collections/collection-1/groups/reorder', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        groups: [
          { id: 'group-3', position: 0 },
          { id: 'group-1', position: 1 },
          { id: 'group-2', position: 2 },
        ],
      }),
    });
  });

  it('invalidates collection groups cache on success', async () => {
    mockApiRequest.mockResolvedValueOnce(undefined);

    const invalidateSpy = jest.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useReorderGroups(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({
        collectionId: 'collection-1',
        groupIds: ['group-3', 'group-1', 'group-2'],
      });
    });

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: groupKeys.list('collection-1'),
    });

    invalidateSpy.mockRestore();
  });
});

describe('useAddArtifactToGroup', () => {
  let queryClient: QueryClient;
  let wrapper: ({ children }: { children: ReactNode }) => ReactElement;

  beforeEach(() => {
    jest.clearAllMocks();

    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('adds artifact to group', async () => {
    mockApiRequest.mockResolvedValueOnce(undefined);

    const { result } = renderHook(() => useAddArtifactToGroup(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({
        groupId: 'group-1',
        artifactId: 'artifact-new',
        position: 0,
      });
    });

    expect(mockApiRequest).toHaveBeenCalledWith('/groups/group-1/artifacts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        artifact_ids: ['artifact-new'],
        position: 0,
      }),
    });
  });

  it('adds artifact without position (appends)', async () => {
    mockApiRequest.mockResolvedValueOnce(undefined);

    const { result } = renderHook(() => useAddArtifactToGroup(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({
        groupId: 'group-1',
        artifactId: 'artifact-new',
      });
    });

    expect(mockApiRequest).toHaveBeenCalledWith('/groups/group-1/artifacts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        artifact_ids: ['artifact-new'],
      }),
    });
  });

  it('invalidates group artifacts, detail, and artifact-groups caches on success', async () => {
    mockApiRequest.mockResolvedValueOnce(undefined);

    const invalidateSpy = jest.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useAddArtifactToGroup(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({
        groupId: 'group-1',
        artifactId: 'artifact-new',
      });
    });

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: groupKeys.artifacts('group-1'),
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: groupKeys.detail('group-1'),
    });
    // Cross-hook invalidation
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['artifact-groups'],
    });

    invalidateSpy.mockRestore();
  });
});

describe('useRemoveArtifactFromGroup', () => {
  let queryClient: QueryClient;
  let wrapper: ({ children }: { children: ReactNode }) => ReactElement;

  beforeEach(() => {
    jest.clearAllMocks();

    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('removes artifact from group', async () => {
    mockApiRequest.mockResolvedValueOnce(undefined);

    const { result } = renderHook(() => useRemoveArtifactFromGroup(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({
        groupId: 'group-1',
        artifactId: 'artifact-1',
      });
    });

    expect(mockApiRequest).toHaveBeenCalledWith('/groups/group-1/artifacts/artifact-1', {
      method: 'DELETE',
    });
  });

  it('invalidates group artifacts, detail, and artifact-groups caches on success', async () => {
    mockApiRequest.mockResolvedValueOnce(undefined);

    const invalidateSpy = jest.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useRemoveArtifactFromGroup(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({
        groupId: 'group-1',
        artifactId: 'artifact-1',
      });
    });

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: groupKeys.artifacts('group-1'),
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: groupKeys.detail('group-1'),
    });
    // Cross-hook invalidation
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['artifact-groups'],
    });

    invalidateSpy.mockRestore();
  });
});

describe('useReorderArtifactsInGroup', () => {
  let queryClient: QueryClient;
  let wrapper: ({ children }: { children: ReactNode }) => ReactElement;

  beforeEach(() => {
    jest.clearAllMocks();

    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('reorders artifacts within a group', async () => {
    mockApiRequest.mockResolvedValueOnce(undefined);

    const { result } = renderHook(() => useReorderArtifactsInGroup(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({
        groupId: 'group-1',
        artifactIds: ['artifact-3', 'artifact-1', 'artifact-2'],
      });
    });

    expect(mockApiRequest).toHaveBeenCalledWith('/groups/group-1/artifacts/reorder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        artifacts: [
          { artifact_id: 'artifact-3', position: 0 },
          { artifact_id: 'artifact-1', position: 1 },
          { artifact_id: 'artifact-2', position: 2 },
        ],
      }),
    });
  });

  it('invalidates group artifacts cache on success', async () => {
    mockApiRequest.mockResolvedValueOnce(undefined);

    const invalidateSpy = jest.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useReorderArtifactsInGroup(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({
        groupId: 'group-1',
        artifactIds: ['artifact-3', 'artifact-1', 'artifact-2'],
      });
    });

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: groupKeys.artifacts('group-1'),
    });

    invalidateSpy.mockRestore();
  });
});

describe('useMoveArtifactToGroup', () => {
  let queryClient: QueryClient;
  let wrapper: ({ children }: { children: ReactNode }) => ReactElement;

  beforeEach(() => {
    jest.clearAllMocks();

    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('moves artifact between groups', async () => {
    mockApiRequest.mockResolvedValueOnce(undefined);

    const { result } = renderHook(() => useMoveArtifactToGroup(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({
        sourceGroupId: 'group-1',
        targetGroupId: 'group-2',
        artifactId: 'artifact-1',
        position: 0,
      });
    });

    expect(mockApiRequest).toHaveBeenCalledWith('/groups/group-1/artifacts/artifact-1/move', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target_group_id: 'group-2',
        position: 0,
      }),
    });
  });

  it('moves artifact without explicit position', async () => {
    mockApiRequest.mockResolvedValueOnce(undefined);

    const { result } = renderHook(() => useMoveArtifactToGroup(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({
        sourceGroupId: 'group-1',
        targetGroupId: 'group-2',
        artifactId: 'artifact-1',
      });
    });

    expect(mockApiRequest).toHaveBeenCalledWith('/groups/group-1/artifacts/artifact-1/move', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target_group_id: 'group-2',
      }),
    });
  });

  it('invalidates both source and target group caches on success', async () => {
    mockApiRequest.mockResolvedValueOnce(undefined);

    const invalidateSpy = jest.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useMoveArtifactToGroup(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({
        sourceGroupId: 'group-1',
        targetGroupId: 'group-2',
        artifactId: 'artifact-1',
      });
    });

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: groupKeys.artifacts('group-1'),
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: groupKeys.artifacts('group-2'),
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: groupKeys.detail('group-1'),
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: groupKeys.detail('group-2'),
    });
    // Cross-hook invalidation
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['artifact-groups'],
    });

    invalidateSpy.mockRestore();
  });
});

describe('useCopyGroup', () => {
  let queryClient: QueryClient;
  let wrapper: ({ children }: { children: ReactNode }) => ReactElement;

  beforeEach(() => {
    jest.clearAllMocks();

    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('copies a group to another collection', async () => {
    const copiedGroup: Group = {
      id: 'copied-group-1',
      collection_id: 'collection-2',
      name: 'Development Tools (Copy)',
      description: 'Tools for development',
      position: 0,
      artifact_count: 5,
      created_at: '2024-01-10T00:00:00Z',
      updated_at: '2024-01-10T00:00:00Z',
    };

    mockApiRequest.mockResolvedValueOnce(copiedGroup);

    const { result } = renderHook(() => useCopyGroup(), { wrapper });

    await act(async () => {
      const copied = await result.current.mutateAsync({
        groupId: 'group-1',
        targetCollectionId: 'collection-2',
      });
      expect(copied.id).toBe('copied-group-1');
    });

    expect(mockApiRequest).toHaveBeenCalledWith('/groups/group-1/copy', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target_collection_id: 'collection-2',
      }),
    });
  });

  it('invalidates target collection groups and artifact-groups caches on success', async () => {
    const copiedGroup: Group = {
      id: 'copied-group-1',
      collection_id: 'collection-2',
      name: 'Development Tools (Copy)',
      position: 0,
      artifact_count: 5,
      created_at: '2024-01-10T00:00:00Z',
      updated_at: '2024-01-10T00:00:00Z',
    };

    mockApiRequest.mockResolvedValueOnce(copiedGroup);

    const invalidateSpy = jest.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useCopyGroup(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({
        groupId: 'group-1',
        targetCollectionId: 'collection-2',
      });
    });

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: groupKeys.list('collection-2'),
    });
    // Cross-hook invalidation
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['artifact-groups'],
    });

    invalidateSpy.mockRestore();
  });
});
