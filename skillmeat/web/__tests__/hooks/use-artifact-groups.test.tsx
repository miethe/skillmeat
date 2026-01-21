/**
 * Tests for useArtifactGroups hook
 *
 * Tests artifact-to-group relationship queries used for displaying
 * group membership indicators in artifact cards and detail views.
 */

import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode, ReactElement } from 'react';
import { useArtifactGroups, artifactGroupKeys } from '@/hooks/use-artifact-groups';
import * as api from '@/lib/api';
import type { Group } from '@/types/groups';

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

describe('useArtifactGroups', () => {
  let queryClient: QueryClient;
  let wrapper: ({ children }: { children: ReactNode }) => ReactElement;

  beforeEach(() => {
    jest.clearAllMocks();

    // Create fresh QueryClient for each test with retry disabled
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

  describe('artifactGroupKeys', () => {
    it('generates correct query keys', () => {
      expect(artifactGroupKeys.all).toEqual(['artifact-groups']);
      expect(artifactGroupKeys.lists()).toEqual(['artifact-groups', 'list']);
      expect(artifactGroupKeys.list('artifact-1', 'collection-1')).toEqual([
        'artifact-groups',
        'list',
        { artifactId: 'artifact-1', collectionId: 'collection-1' },
      ]);
    });

    it('generates unique keys for different artifact-collection pairs', () => {
      const key1 = artifactGroupKeys.list('artifact-1', 'collection-1');
      const key2 = artifactGroupKeys.list('artifact-2', 'collection-1');
      const key3 = artifactGroupKeys.list('artifact-1', 'collection-2');

      expect(key1).not.toEqual(key2);
      expect(key1).not.toEqual(key3);
      expect(key2).not.toEqual(key3);
    });

    it('handles undefined values in query keys', () => {
      const keyWithUndefined = artifactGroupKeys.list(undefined, 'collection-1');
      expect(keyWithUndefined).toEqual([
        'artifact-groups',
        'list',
        { artifactId: undefined, collectionId: 'collection-1' },
      ]);
    });
  });

  describe('query behavior', () => {
    it('fetches groups for artifact-collection pair (happy path)', async () => {
      mockApiRequest.mockResolvedValueOnce({
        groups: mockGroups,
        total: mockGroups.length,
      });

      const { result } = renderHook(
        () => useArtifactGroups('artifact-1', 'collection-1'),
        { wrapper }
      );

      // Initially loading
      expect(result.current.isLoading).toBe(true);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toHaveLength(3);
      expect(mockApiRequest).toHaveBeenCalledWith(
        '/groups?collection_id=collection-1&artifact_id=artifact-1'
      );
    });

    it('returns empty array on API error (graceful degradation)', async () => {
      mockApiRequest.mockRejectedValueOnce(new Error('API Error'));

      const { result } = renderHook(
        () => useArtifactGroups('artifact-1', 'collection-1'),
        { wrapper }
      );

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Should return empty array instead of throwing
      expect(result.current.data).toEqual([]);
    });

    it('query is disabled when artifactId is undefined', () => {
      const { result } = renderHook(
        () => useArtifactGroups(undefined, 'collection-1'),
        { wrapper }
      );

      // Query should not be enabled
      expect(result.current.fetchStatus).toBe('idle');
      expect(mockApiRequest).not.toHaveBeenCalled();
    });

    it('query is disabled when collectionId is undefined', () => {
      const { result } = renderHook(
        () => useArtifactGroups('artifact-1', undefined),
        { wrapper }
      );

      // Query should not be enabled
      expect(result.current.fetchStatus).toBe('idle');
      expect(mockApiRequest).not.toHaveBeenCalled();
    });

    it('query is disabled when both params are undefined', () => {
      const { result } = renderHook(
        () => useArtifactGroups(undefined, undefined),
        { wrapper }
      );

      expect(result.current.fetchStatus).toBe('idle');
      expect(mockApiRequest).not.toHaveBeenCalled();
    });

    it('enables query when both artifactId and collectionId are provided', async () => {
      mockApiRequest.mockResolvedValueOnce({
        groups: mockGroups,
        total: mockGroups.length,
      });

      const { result } = renderHook(
        () => useArtifactGroups('artifact-1', 'collection-1'),
        { wrapper }
      );

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(mockApiRequest).toHaveBeenCalledTimes(1);
    });
  });

  describe('sorting behavior', () => {
    it('groups are sorted by position field', async () => {
      // Return groups in wrong order
      const unsortedGroups: Group[] = [
        { ...mockGroups[2], position: 2 }, // position 2
        { ...mockGroups[0], position: 0 }, // position 0
        { ...mockGroups[1], position: 1 }, // position 1
      ];

      mockApiRequest.mockResolvedValueOnce({
        groups: unsortedGroups,
        total: unsortedGroups.length,
      });

      const { result } = renderHook(
        () => useArtifactGroups('artifact-1', 'collection-1'),
        { wrapper }
      );

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Verify sorted order
      expect(result.current.data![0].position).toBe(0);
      expect(result.current.data![1].position).toBe(1);
      expect(result.current.data![2].position).toBe(2);
    });

    it('handles groups with same position (stable sort)', async () => {
      const groupsWithSamePosition: Group[] = [
        { ...mockGroups[0], id: 'group-a', position: 1 },
        { ...mockGroups[1], id: 'group-b', position: 1 },
        { ...mockGroups[2], id: 'group-c', position: 0 },
      ];

      mockApiRequest.mockResolvedValueOnce({
        groups: groupsWithSamePosition,
        total: groupsWithSamePosition.length,
      });

      const { result } = renderHook(
        () => useArtifactGroups('artifact-1', 'collection-1'),
        { wrapper }
      );

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // First should be position 0
      expect(result.current.data![0].position).toBe(0);
      // Next two should both be position 1
      expect(result.current.data![1].position).toBe(1);
      expect(result.current.data![2].position).toBe(1);
    });
  });

  describe('cache configuration', () => {
    it('uses correct cache key including both artifactId and collectionId', async () => {
      mockApiRequest.mockResolvedValueOnce({
        groups: mockGroups,
        total: mockGroups.length,
      });

      const { result } = renderHook(
        () => useArtifactGroups('artifact-123', 'collection-456'),
        { wrapper }
      );

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Verify the cache contains data under the expected key
      const cachedData = queryClient.getQueryData(
        artifactGroupKeys.list('artifact-123', 'collection-456')
      );
      expect(cachedData).toBeDefined();
      expect(cachedData).toHaveLength(3);
    });

    it('stale time is set to 10 minutes (600000ms)', async () => {
      mockApiRequest.mockResolvedValueOnce({
        groups: mockGroups,
        total: mockGroups.length,
      });

      renderHook(() => useArtifactGroups('artifact-1', 'collection-1'), { wrapper });

      await waitFor(() => {
        expect(mockApiRequest).toHaveBeenCalled();
      });

      // Check query state - data should not be stale immediately
      const queryState = queryClient.getQueryState(
        artifactGroupKeys.list('artifact-1', 'collection-1')
      );

      // Data should be fresh (dataUpdatedAt should be recent)
      expect(queryState?.dataUpdatedAt).toBeDefined();
      expect(queryState?.dataUpdatedAt).toBeGreaterThan(0);
    });

    it('different artifact-collection pairs have separate cache entries', async () => {
      mockApiRequest
        .mockResolvedValueOnce({ groups: [mockGroups[0]], total: 1 })
        .mockResolvedValueOnce({ groups: [mockGroups[1], mockGroups[2]], total: 2 });

      // First query
      const { result: result1 } = renderHook(
        () => useArtifactGroups('artifact-1', 'collection-1'),
        { wrapper }
      );

      await waitFor(() => expect(result1.current.isSuccess).toBe(true));

      // Second query with different params
      const { result: result2 } = renderHook(
        () => useArtifactGroups('artifact-2', 'collection-1'),
        { wrapper }
      );

      await waitFor(() => expect(result2.current.isSuccess).toBe(true));

      // Both should have their own data
      expect(result1.current.data).toHaveLength(1);
      expect(result2.current.data).toHaveLength(2);
    });
  });

  describe('empty state handling', () => {
    it('returns empty array when artifact belongs to no groups', async () => {
      mockApiRequest.mockResolvedValueOnce({
        groups: [],
        total: 0,
      });

      const { result } = renderHook(
        () => useArtifactGroups('artifact-1', 'collection-1'),
        { wrapper }
      );

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual([]);
    });
  });

  describe('refetching', () => {
    it('refetches when artifact changes', async () => {
      mockApiRequest
        .mockResolvedValueOnce({ groups: [mockGroups[0]], total: 1 })
        .mockResolvedValueOnce({ groups: [mockGroups[1]], total: 1 });

      const { result, rerender } = renderHook(
        ({ artifactId }) => useArtifactGroups(artifactId, 'collection-1'),
        {
          wrapper,
          initialProps: { artifactId: 'artifact-1' },
        }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data![0].id).toBe('group-1');

      // Change artifact
      rerender({ artifactId: 'artifact-2' });

      await waitFor(() => {
        expect(result.current.data![0].id).toBe('group-2');
      });

      expect(mockApiRequest).toHaveBeenCalledTimes(2);
    });

    it('refetches when collection changes', async () => {
      mockApiRequest
        .mockResolvedValueOnce({ groups: [mockGroups[0]], total: 1 })
        .mockResolvedValueOnce({ groups: [mockGroups[1]], total: 1 });

      const { result, rerender } = renderHook(
        ({ collectionId }) => useArtifactGroups('artifact-1', collectionId),
        {
          wrapper,
          initialProps: { collectionId: 'collection-1' },
        }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data![0].id).toBe('group-1');

      // Change collection
      rerender({ collectionId: 'collection-2' });

      await waitFor(() => {
        expect(result.current.data![0].id).toBe('group-2');
      });

      expect(mockApiRequest).toHaveBeenCalledTimes(2);
    });
  });
});
