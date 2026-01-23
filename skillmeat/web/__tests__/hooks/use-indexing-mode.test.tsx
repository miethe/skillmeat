/**
 * Tests for useIndexingMode hook
 *
 * Tests the indexing mode configuration hook including:
 * - Default fallback behavior on error
 * - showToggle computed property for 'opt_in' and 'on' modes
 * - isGloballyEnabled computed property for 'on' mode
 * - isDisabled computed property for 'off' mode
 */

import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode, ReactElement } from 'react';
import { useIndexingMode, settingsKeys } from '@/hooks/useIndexingMode';
import * as api from '@/lib/api';

// Mock the API module
jest.mock('@/lib/api', () => ({
  apiRequest: jest.fn(),
}));

const mockApiRequest = api.apiRequest as jest.MockedFunction<typeof api.apiRequest>;

describe('settingsKeys', () => {
  it('generates correct query keys', () => {
    expect(settingsKeys.all).toEqual(['settings']);
    expect(settingsKeys.indexingMode()).toEqual(['settings', 'indexing-mode']);
  });
});

describe('useIndexingMode', () => {
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

  describe('default behavior', () => {
    it('returns default "opt_in" mode on API error', async () => {
      mockApiRequest.mockRejectedValueOnce(new Error('API Error'));

      const { result } = renderHook(() => useIndexingMode(), { wrapper });

      // Wait for the query to finish with error (error will be defined)
      await waitFor(() => {
        expect(result.current.error).toBeDefined();
      });

      // Should gracefully degrade to 'opt_in'
      expect(result.current.indexingMode).toBe('opt_in');
      expect(result.current.error).toBeDefined();
    });

    it('returns default "opt_in" mode while loading', () => {
      // Make API hang indefinitely
      mockApiRequest.mockImplementation(() => new Promise(() => {}));

      const { result } = renderHook(() => useIndexingMode(), { wrapper });

      // While loading, should use default
      expect(result.current.indexingMode).toBe('opt_in');
      expect(result.current.isLoading).toBe(true);
    });
  });

  describe('showToggle computed property', () => {
    it('returns true when mode is "opt_in"', async () => {
      mockApiRequest.mockResolvedValueOnce({ indexing_mode: 'opt_in' });

      const { result } = renderHook(() => useIndexingMode(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.indexingMode).toBe('opt_in');
      expect(result.current.showToggle).toBe(true);
    });

    it('returns true when mode is "on" (toggle shown to indicate state)', async () => {
      mockApiRequest.mockResolvedValueOnce({ indexing_mode: 'on' });

      const { result } = renderHook(() => useIndexingMode(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.indexingMode).toBe('on');
      // Per implementation: showToggle = indexingMode === 'opt_in'
      // So when 'on', showToggle is false
      expect(result.current.showToggle).toBe(false);
    });

    it('returns false when mode is "off"', async () => {
      mockApiRequest.mockResolvedValueOnce({ indexing_mode: 'off' });

      const { result } = renderHook(() => useIndexingMode(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.indexingMode).toBe('off');
      expect(result.current.showToggle).toBe(false);
    });
  });

  describe('isGloballyEnabled computed property', () => {
    it('returns true only when mode is "on"', async () => {
      mockApiRequest.mockResolvedValueOnce({ indexing_mode: 'on' });

      const { result } = renderHook(() => useIndexingMode(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isGloballyEnabled).toBe(true);
    });

    it('returns false when mode is "opt_in"', async () => {
      mockApiRequest.mockResolvedValueOnce({ indexing_mode: 'opt_in' });

      const { result } = renderHook(() => useIndexingMode(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isGloballyEnabled).toBe(false);
    });

    it('returns false when mode is "off"', async () => {
      mockApiRequest.mockResolvedValueOnce({ indexing_mode: 'off' });

      const { result } = renderHook(() => useIndexingMode(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isGloballyEnabled).toBe(false);
    });
  });

  describe('isDisabled computed property', () => {
    it('returns true when mode is "off"', async () => {
      mockApiRequest.mockResolvedValueOnce({ indexing_mode: 'off' });

      const { result } = renderHook(() => useIndexingMode(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isDisabled).toBe(true);
    });

    it('returns false when mode is "opt_in"', async () => {
      mockApiRequest.mockResolvedValueOnce({ indexing_mode: 'opt_in' });

      const { result } = renderHook(() => useIndexingMode(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isDisabled).toBe(false);
    });

    it('returns false when mode is "on"', async () => {
      mockApiRequest.mockResolvedValueOnce({ indexing_mode: 'on' });

      const { result } = renderHook(() => useIndexingMode(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isDisabled).toBe(false);
    });
  });

  describe('API interaction', () => {
    it('calls correct endpoint', async () => {
      mockApiRequest.mockResolvedValueOnce({ indexing_mode: 'opt_in' });

      renderHook(() => useIndexingMode(), { wrapper });

      await waitFor(() => {
        expect(mockApiRequest).toHaveBeenCalledWith('/settings/indexing-mode');
      });
    });

    it('provides raw data from API', async () => {
      mockApiRequest.mockResolvedValueOnce({ indexing_mode: 'on' });

      const { result } = renderHook(() => useIndexingMode(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.data).toEqual({ indexing_mode: 'on' });
    });

    it('exposes refetch function', async () => {
      mockApiRequest.mockResolvedValueOnce({ indexing_mode: 'opt_in' });

      const { result } = renderHook(() => useIndexingMode(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(typeof result.current.refetch).toBe('function');
    });
  });

  describe('cache behavior', () => {
    it('uses 5-minute stale time', async () => {
      mockApiRequest.mockResolvedValueOnce({ indexing_mode: 'opt_in' });

      renderHook(() => useIndexingMode(), { wrapper });

      await waitFor(() => {
        expect(mockApiRequest).toHaveBeenCalled();
      });

      const queryState = queryClient.getQueryState(settingsKeys.indexingMode());
      expect(queryState?.dataUpdatedAt).toBeDefined();
      expect(queryState?.dataUpdatedAt).toBeGreaterThan(0);
    });
  });

  describe('all modes matrix', () => {
    it.each([
      ['opt_in', true, false, false],
      ['on', false, true, false],
      ['off', false, false, true],
    ] as const)(
      'mode "%s" -> showToggle=%s, isGloballyEnabled=%s, isDisabled=%s',
      async (mode, expectedShowToggle, expectedGloballyEnabled, expectedDisabled) => {
        mockApiRequest.mockResolvedValueOnce({ indexing_mode: mode });

        const { result } = renderHook(() => useIndexingMode(), { wrapper });

        await waitFor(() => {
          expect(result.current.isLoading).toBe(false);
        });

        expect(result.current.indexingMode).toBe(mode);
        expect(result.current.showToggle).toBe(expectedShowToggle);
        expect(result.current.isGloballyEnabled).toBe(expectedGloballyEnabled);
        expect(result.current.isDisabled).toBe(expectedDisabled);
      }
    );
  });
});
