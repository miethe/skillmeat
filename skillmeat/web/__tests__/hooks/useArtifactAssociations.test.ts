/**
 * @jest-environment jsdom
 */
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React, { ReactNode } from 'react';
import { useArtifactAssociations } from '@/hooks/useArtifactAssociations';
import { apiRequest } from '@/lib/api';
import type { AssociationsDTO, AssociationItemDTO } from '@/types/associations';

// Mock apiRequest
jest.mock('@/lib/api', () => ({
  apiRequest: jest.fn(),
}));

const mockApiRequest = apiRequest as jest.MockedFunction<typeof apiRequest>;

// ---------------------------------------------------------------------------
// Factory helpers
// ---------------------------------------------------------------------------

const createMockAssociationItem = (
  overrides?: Partial<AssociationItemDTO>
): AssociationItemDTO => ({
  artifact_id: 'composite:parent-bundle',
  artifact_name: 'parent-bundle',
  artifact_type: 'composite',
  relationship_type: 'contains',
  pinned_version_hash: null,
  created_at: '2026-01-15T10:00:00Z',
  ...overrides,
});

const createMockAssociationsDTO = (overrides?: Partial<AssociationsDTO>): AssociationsDTO => ({
  artifact_id: 'skill:my-skill',
  parents: [],
  children: [],
  ...overrides,
});

// ---------------------------------------------------------------------------
// Test setup
// ---------------------------------------------------------------------------

describe('useArtifactAssociations', () => {
  let queryClient: QueryClient;

  const createWrapper = () => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    return ({ children }: { children: ReactNode }) =>
      React.createElement(QueryClientProvider, { client: queryClient }, children);
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  afterEach(() => {
    queryClient?.clear();
  });

  // -------------------------------------------------------------------------
  // Fetch on mount
  // -------------------------------------------------------------------------

  describe('fetching associations', () => {
    it('fetches associations on mount', async () => {
      const mockResponse = createMockAssociationsDTO({
        artifact_id: 'skill:canvas-design',
        parents: [
          createMockAssociationItem({
            artifact_id: 'composite:design-bundle',
            artifact_name: 'design-bundle',
          }),
        ],
        children: [],
      });

      mockApiRequest.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(() => useArtifactAssociations('skill:canvas-design'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(mockApiRequest).toHaveBeenCalledWith(
        '/artifacts/skill%3Acanvas-design/associations'
      );
      expect(result.current.data).toEqual(mockResponse);
    });

    it('URL-encodes artifactId containing colons and slashes', async () => {
      const mockResponse = createMockAssociationsDTO({ artifact_id: 'composite:a/b' });
      mockApiRequest.mockResolvedValueOnce(mockResponse);

      renderHook(() => useArtifactAssociations('composite:a/b'), { wrapper: createWrapper() });

      await waitFor(() => {
        expect(mockApiRequest).toHaveBeenCalled();
      });

      expect(mockApiRequest).toHaveBeenCalledWith(
        expect.stringContaining('composite%3Aa%2Fb')
      );
    });

    it('returns parents and children correctly', async () => {
      const parent = createMockAssociationItem({
        artifact_id: 'composite:suite',
        artifact_name: 'suite',
        artifact_type: 'composite',
        relationship_type: 'contains',
      });
      const child = createMockAssociationItem({
        artifact_id: 'skill:helper',
        artifact_name: 'helper',
        artifact_type: 'skill',
        pinned_version_hash: 'abc123def456',
      });
      const mockResponse = createMockAssociationsDTO({
        artifact_id: 'composite:my-composite',
        parents: [parent],
        children: [child],
      });

      mockApiRequest.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(() => useArtifactAssociations('composite:my-composite'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.parents).toHaveLength(1);
      expect(result.current.data?.parents[0]).toEqual(parent);
      expect(result.current.data?.children).toHaveLength(1);
      // Verify pinned hash on the child by checking the whole child object
      expect(result.current.data?.children).toContainEqual(
        expect.objectContaining({ pinned_version_hash: 'abc123def456' })
      );
    });

    it('handles empty parents and children arrays', async () => {
      const mockResponse = createMockAssociationsDTO({
        artifact_id: 'skill:standalone',
        parents: [],
        children: [],
      });

      mockApiRequest.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(() => useArtifactAssociations('skill:standalone'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.parents).toEqual([]);
      expect(result.current.data?.children).toEqual([]);
    });
  });

  // -------------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------------

  describe('loading state', () => {
    it('returns isLoading true while fetching', () => {
      mockApiRequest.mockImplementationOnce(
        () => new Promise((resolve) => setTimeout(resolve, 100))
      );

      const { result } = renderHook(() => useArtifactAssociations('skill:canvas-design'), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);
    });

    it('returns isLoading false after fetch completes', async () => {
      mockApiRequest.mockResolvedValueOnce(createMockAssociationsDTO());

      const { result } = renderHook(() => useArtifactAssociations('skill:canvas-design'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });
    });

    it('returns data undefined while loading', () => {
      mockApiRequest.mockImplementationOnce(
        () => new Promise((resolve) => setTimeout(resolve, 100))
      );

      const { result } = renderHook(() => useArtifactAssociations('skill:canvas-design'), {
        wrapper: createWrapper(),
      });

      expect(result.current.data).toBeUndefined();
    });
  });

  // -------------------------------------------------------------------------
  // Error handling
  // -------------------------------------------------------------------------

  describe('error handling', () => {
    it('returns error in state when API fails', async () => {
      const mockError = new Error('Network error');
      mockApiRequest.mockRejectedValueOnce(mockError);

      const { result } = renderHook(() => useArtifactAssociations('skill:canvas-design'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.error).toBeTruthy();
      });

      expect(result.current.error).toEqual(mockError);
    });

    it('keeps data undefined on error', async () => {
      mockApiRequest.mockRejectedValueOnce(new Error('Server error'));

      const { result } = renderHook(() => useArtifactAssociations('skill:canvas-design'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.error).toBeTruthy();
      });

      expect(result.current.data).toBeUndefined();
    });

    it('does not throw — error is returned in state, not propagated', async () => {
      mockApiRequest.mockRejectedValueOnce(new Error('404 Not Found'));

      // If the hook threw, renderHook would throw here
      const { result } = renderHook(() => useArtifactAssociations('skill:nonexistent'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Error surfaced via state, hook did not throw
      expect(result.current.error).toBeInstanceOf(Error);
    });
  });

  // -------------------------------------------------------------------------
  // Refetch when artifactId changes
  // -------------------------------------------------------------------------

  describe('refetch on artifactId change', () => {
    it('refetches when artifactId changes', async () => {
      const firstResponse = createMockAssociationsDTO({ artifact_id: 'skill:first' });
      const secondResponse = createMockAssociationsDTO({ artifact_id: 'skill:second' });

      mockApiRequest
        .mockResolvedValueOnce(firstResponse)
        .mockResolvedValueOnce(secondResponse);

      const { result, rerender } = renderHook(
        ({ artifactId }: { artifactId: string }) => useArtifactAssociations(artifactId),
        { wrapper: createWrapper(), initialProps: { artifactId: 'skill:first' } }
      );

      await waitFor(() => {
        expect(result.current.data?.artifact_id).toBe('skill:first');
      });

      rerender({ artifactId: 'skill:second' });

      await waitFor(() => {
        expect(result.current.data?.artifact_id).toBe('skill:second');
      });

      expect(mockApiRequest).toHaveBeenCalledTimes(2);
      expect(mockApiRequest).toHaveBeenNthCalledWith(
        1,
        '/artifacts/skill%3Afirst/associations'
      );
      expect(mockApiRequest).toHaveBeenNthCalledWith(
        2,
        '/artifacts/skill%3Asecond/associations'
      );
    });

    it('does not fetch when artifactId is empty string', async () => {
      const { result } = renderHook(() => useArtifactAssociations(''), {
        wrapper: createWrapper(),
      });

      // Wait a tick to ensure no fetch fires
      await new Promise((resolve) => setTimeout(resolve, 50));

      expect(mockApiRequest).not.toHaveBeenCalled();
      expect(result.current.isLoading).toBe(false);
      expect(result.current.data).toBeUndefined();
    });

    it('uses independent cache keys per artifactId', async () => {
      const responseA = createMockAssociationsDTO({ artifact_id: 'skill:alpha' });
      const responseB = createMockAssociationsDTO({ artifact_id: 'skill:beta' });

      mockApiRequest
        .mockResolvedValueOnce(responseA)
        .mockResolvedValueOnce(responseB);

      const { result: resultA } = renderHook(() => useArtifactAssociations('skill:alpha'), {
        wrapper: createWrapper(),
      });
      const { result: resultB } = renderHook(() => useArtifactAssociations('skill:beta'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(resultA.current.isSuccess).toBe(true);
        expect(resultB.current.isSuccess).toBe(true);
      });

      expect(resultA.current.data?.artifact_id).toBe('skill:alpha');
      expect(resultB.current.data?.artifact_id).toBe('skill:beta');
    });
  });

  // -------------------------------------------------------------------------
  // refetch function
  // -------------------------------------------------------------------------

  describe('refetch', () => {
    it('exposes a refetch function', async () => {
      mockApiRequest.mockResolvedValue(createMockAssociationsDTO());

      const { result } = renderHook(() => useArtifactAssociations('skill:canvas-design'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(typeof result.current.refetch).toBe('function');
    });

    it('re-calls the API when refetch is invoked', async () => {
      const firstResponse = createMockAssociationsDTO({
        parents: [],
        children: [],
      });
      const secondResponse = createMockAssociationsDTO({
        parents: [createMockAssociationItem()],
        children: [],
      });

      mockApiRequest
        .mockResolvedValueOnce(firstResponse)
        .mockResolvedValueOnce(secondResponse);

      const { result } = renderHook(() => useArtifactAssociations('skill:canvas-design'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.data?.parents).toHaveLength(0);
      });

      result.current.refetch();

      await waitFor(() => {
        expect(result.current.data?.parents).toHaveLength(1);
      });

      expect(mockApiRequest).toHaveBeenCalledTimes(2);
    });
  });

  // -------------------------------------------------------------------------
  // Query key
  // -------------------------------------------------------------------------

  describe('query key', () => {
    it('caches results under ["associations", artifactId]', async () => {
      mockApiRequest.mockResolvedValueOnce(createMockAssociationsDTO());

      const { result } = renderHook(() => useArtifactAssociations('skill:canvas-design'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      const cachedState = queryClient.getQueryState(['associations', 'skill:canvas-design']);
      expect(cachedState).toBeDefined();
      expect(cachedState?.status).toBe('success');
    });
  });
});
