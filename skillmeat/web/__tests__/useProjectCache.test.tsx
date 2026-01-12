/**
 * @jest-environment jsdom
 */
import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useProjectCache } from '@/hooks';
import { apiRequest } from '@/lib/api';
import type { ProjectsResponse } from '@/types/project';

// Mock the API module
jest.mock('@/lib/api', () => ({
  apiRequest: jest.fn(),
}));

const mockedApiRequest = apiRequest as jest.MockedFunction<typeof apiRequest>;

// Test wrapper with QueryClientProvider
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('useProjectCache', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Loading State', () => {
    it('starts in loading state during initial fetch', async () => {
      const mockResponse: ProjectsResponse = {
        items: [],
        page_info: {
          has_next_page: false,
          has_previous_page: false,
          start_cursor: null,
          end_cursor: null,
          total_count: 0,
        },
      };

      mockedApiRequest.mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve(mockResponse), 100))
      );

      const { result } = renderHook(() => useProjectCache(), {
        wrapper: createWrapper(),
      });

      // Should start in loading state
      expect(result.current.isLoading).toBe(true);
      expect(result.current.projects).toEqual([]);
      expect(result.current.cacheInfo).toBeNull();

      // Wait for query to complete
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });
    });

    it('sets isFetching to true during refetch', async () => {
      const mockResponse: ProjectsResponse = {
        items: [],
        page_info: {
          has_next_page: false,
          has_previous_page: false,
          start_cursor: null,
          end_cursor: null,
          total_count: 0,
        },
      };

      // First call resolves immediately for initial load
      mockedApiRequest.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(() => useProjectCache(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Second call for refetch has a delay so we can observe isFetching
      mockedApiRequest.mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve(mockResponse), 50))
      );

      // Trigger refetch
      const refetchPromise = result.current.refetch();

      // Should eventually show fetching
      await waitFor(
        () => {
          expect(result.current.isFetching).toBe(true);
        },
        { timeout: 100 }
      );

      // Wait for refetch to complete
      await refetchPromise;

      await waitFor(() => {
        expect(result.current.isFetching).toBe(false);
      });
    });
  });

  describe('Success State', () => {
    it('returns projects on successful fetch', async () => {
      const mockResponse: ProjectsResponse = {
        items: [
          {
            id: '1',
            name: 'test-project',
            path: '/path/to/project',
            deployment_count: 5,
            last_deployment: '2025-01-01T00:00:00Z',
          },
          {
            id: '2',
            name: 'another-project',
            path: '/path/to/another',
            deployment_count: 3,
          },
        ],
        page_info: {
          has_next_page: false,
          has_previous_page: false,
          start_cursor: null,
          end_cursor: null,
          total_count: 2,
        },
      };

      mockedApiRequest.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useProjectCache(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.projects).toHaveLength(2);
      expect(result.current.projects[0].name).toBe('test-project');
      expect(result.current.projects[1].name).toBe('another-project');
      expect(result.current.error).toBeNull();
    });

    it('returns empty array when no projects', async () => {
      const mockResponse: ProjectsResponse = {
        items: [],
        page_info: {
          has_next_page: false,
          has_previous_page: false,
          start_cursor: null,
          end_cursor: null,
          total_count: 0,
        },
      };

      mockedApiRequest.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useProjectCache(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.projects).toEqual([]);
    });
  });

  describe('Error State', () => {
    it('handles API errors gracefully', async () => {
      const error = new Error('Network error');
      mockedApiRequest.mockRejectedValue(error);

      const { result } = renderHook(() => useProjectCache(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.error).toBeTruthy();
      expect(result.current.projects).toEqual([]);
    });

    it('handles 404 errors', async () => {
      const error = new Error('Not found');
      mockedApiRequest.mockRejectedValue(error);

      const { result } = renderHook(() => useProjectCache(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.error).toBeTruthy();
    });
  });

  describe('Cache Info Extraction', () => {
    it('extracts cache info from response when present', async () => {
      const mockResponse: ProjectsResponse = {
        items: [
          {
            id: '1',
            name: 'test-project',
            path: '/path/to/project',
            deployment_count: 5,
            cache_info: {
              cacheHit: true,
              lastFetched: '2025-01-01T10:00:00Z',
              isStale: false,
            },
          } as any,
        ],
        page_info: {
          has_next_page: false,
          has_previous_page: false,
          start_cursor: null,
          end_cursor: null,
          total_count: 1,
        },
      };

      mockedApiRequest.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useProjectCache(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.cacheInfo).not.toBeNull();
      expect(result.current.cacheInfo?.cacheHit).toBe(true);
      expect(result.current.cacheInfo?.isStale).toBe(false);
      expect(result.current.cacheInfo?.lastFetched).toBeInstanceOf(Date);
    });

    it('returns null cache info when not present in response', async () => {
      const mockResponse: ProjectsResponse = {
        items: [
          {
            id: '1',
            name: 'test-project',
            path: '/path/to/project',
            deployment_count: 5,
          },
        ],
        page_info: {
          has_next_page: false,
          has_previous_page: false,
          start_cursor: null,
          end_cursor: null,
          total_count: 1,
        },
      };

      mockedApiRequest.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useProjectCache(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.cacheInfo).toBeNull();
    });

    it('handles null lastFetched in cache info', async () => {
      const mockResponse: ProjectsResponse = {
        items: [
          {
            id: '1',
            name: 'test-project',
            path: '/path/to/project',
            deployment_count: 5,
            cache_info: {
              cacheHit: true,
              lastFetched: null,
              isStale: true,
            },
          } as any,
        ],
        page_info: {
          has_next_page: false,
          has_previous_page: false,
          start_cursor: null,
          end_cursor: null,
          total_count: 1,
        },
      };

      mockedApiRequest.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useProjectCache(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.cacheInfo).not.toBeNull();
      expect(result.current.cacheInfo?.lastFetched).toBeNull();
      expect(result.current.cacheInfo?.isStale).toBe(true);
    });
  });

  describe('forceRefresh', () => {
    it('bypasses cache with force_refresh query param', async () => {
      const mockResponse: ProjectsResponse = {
        items: [
          {
            id: '1',
            name: 'fresh-project',
            path: '/path/to/fresh',
            deployment_count: 1,
          },
        ],
        page_info: {
          has_next_page: false,
          has_previous_page: false,
          start_cursor: null,
          end_cursor: null,
          total_count: 1,
        },
      };

      mockedApiRequest.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useProjectCache(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Call forceRefresh
      await result.current.forceRefresh();

      // Should have called API with force_refresh param
      expect(mockedApiRequest).toHaveBeenCalledWith('/projects?force_refresh=true');
    });

    it('updates query cache with fresh data', async () => {
      const initialResponse: ProjectsResponse = {
        items: [
          {
            id: '1',
            name: 'old-project',
            path: '/path/to/old',
            deployment_count: 1,
          },
        ],
        page_info: {
          has_next_page: false,
          has_previous_page: false,
          start_cursor: null,
          end_cursor: null,
          total_count: 1,
        },
      };

      const freshResponse: ProjectsResponse = {
        items: [
          {
            id: '1',
            name: 'fresh-project',
            path: '/path/to/fresh',
            deployment_count: 2,
          },
        ],
        page_info: {
          has_next_page: false,
          has_previous_page: false,
          start_cursor: null,
          end_cursor: null,
          total_count: 1,
        },
      };

      mockedApiRequest.mockResolvedValueOnce(initialResponse);

      const { result } = renderHook(() => useProjectCache(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.projects[0].name).toBe('old-project');

      // Mock fresh data for forceRefresh
      mockedApiRequest.mockResolvedValueOnce(freshResponse);

      // Force refresh
      await result.current.forceRefresh();

      await waitFor(() => {
        expect(result.current.projects[0].name).toBe('fresh-project');
      });
    });
  });

  describe('Configuration Options', () => {
    it('respects enabled option set to false', async () => {
      const mockResponse: ProjectsResponse = {
        items: [],
        page_info: {
          has_next_page: false,
          has_previous_page: false,
          start_cursor: null,
          end_cursor: null,
          total_count: 0,
        },
      };

      mockedApiRequest.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useProjectCache({ enabled: false }), {
        wrapper: createWrapper(),
      });

      // Should not fetch when disabled
      expect(result.current.isLoading).toBe(false);
      expect(mockedApiRequest).not.toHaveBeenCalled();
    });

    it('uses custom staleTime when provided', async () => {
      const mockResponse: ProjectsResponse = {
        items: [],
        page_info: {
          has_next_page: false,
          has_previous_page: false,
          start_cursor: null,
          end_cursor: null,
          total_count: 0,
        },
      };

      mockedApiRequest.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useProjectCache({ staleTime: 120000 }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // We can't directly test staleTime, but we can verify the hook works with the option
      expect(result.current.projects).toEqual([]);
    });
  });

  describe('Refetch Behavior', () => {
    it('refetch uses TanStack Query cache', async () => {
      const mockResponse: ProjectsResponse = {
        items: [
          {
            id: '1',
            name: 'test-project',
            path: '/path/to/project',
            deployment_count: 5,
          },
        ],
        page_info: {
          has_next_page: false,
          has_previous_page: false,
          start_cursor: null,
          end_cursor: null,
          total_count: 1,
        },
      };

      mockedApiRequest.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useProjectCache(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      const initialCallCount = mockedApiRequest.mock.calls.length;

      // Call refetch
      await result.current.refetch();

      await waitFor(() => {
        expect(result.current.isFetching).toBe(false);
      });

      // Should have called API again (no force_refresh param)
      expect(mockedApiRequest).toHaveBeenCalledWith('/projects');
      expect(mockedApiRequest.mock.calls.length).toBeGreaterThan(initialCallCount);
    });
  });
});
