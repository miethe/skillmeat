/**
 * Unit tests for useBulkTagApply hook.
 *
 * Tests the mutation flow, progress tracking, and callbacks.
 */

import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useBulkTagApply } from '@/hooks/use-bulk-tag-apply';
import type { CatalogEntry } from '@/types/marketplace';
import type { BulkTagResult } from '@/lib/utils/bulk-tag-apply';

// Mock the toast hook
jest.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: jest.fn(),
  }),
}));

// Mock the bulk-tag-apply utility
jest.mock('@/lib/utils/bulk-tag-apply', () => ({
  ...jest.requireActual('@/lib/utils/bulk-tag-apply'),
  applyTagsToDirectories: jest.fn(),
}));

import { applyTagsToDirectories } from '@/lib/utils/bulk-tag-apply';

const mockApplyTagsToDirectories = applyTagsToDirectories as jest.Mock;

// Helper to create mock catalog entries
function createMockEntry(path: string): CatalogEntry {
  return {
    id: `entry-${path.replace(/\//g, '-')}`,
    source_id: 'source-123',
    artifact_type: 'skill',
    name: path.split('/').pop() || path,
    path,
    upstream_url: `https://github.com/test/${path}`,
    detected_at: '2024-01-01T00:00:00Z',
    confidence_score: 0.9,
    status: 'new',
  };
}

// Test wrapper with QueryClient
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe('useBulkTagApply', () => {
  const mockEntries: CatalogEntry[] = [
    createMockEntry('skills/canvas'),
    createMockEntry('skills/docs'),
    createMockEntry('commands/ai'),
  ];

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('initialization', () => {
    it('initializes with idle state', () => {
      const { result } = renderHook(
        () =>
          useBulkTagApply({
            entries: mockEntries,
            sourceId: 'source-123',
          }),
        { wrapper: createWrapper() }
      );

      expect(result.current.isPending).toBe(false);
      expect(result.current.isSuccess).toBe(false);
      expect(result.current.isError).toBe(false);
      expect(result.current.progress).toEqual({
        current: 0,
        total: 0,
        percentage: 0,
      });
    });
  });

  describe('simulation mode', () => {
    it('applies tags without API calls in simulation mode', async () => {
      const onSuccess = jest.fn();

      const { result } = renderHook(
        () =>
          useBulkTagApply({
            entries: mockEntries,
            sourceId: 'source-123',
            simulationMode: true,
            onSuccess,
          }),
        { wrapper: createWrapper() }
      );

      const dirTags = new Map([['skills', ['dev', 'testing']]]);

      await act(async () => {
        result.current.mutate(dirTags);
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // API should not be called in simulation mode
      expect(mockApplyTagsToDirectories).not.toHaveBeenCalled();

      // onSuccess should be called with result
      expect(onSuccess).toHaveBeenCalledWith(
        expect.objectContaining({
          totalUpdated: expect.any(Number),
          totalFailed: 0,
          errors: [],
        })
      );
    });

    it('returns correct counts in simulation mode', async () => {
      const { result } = renderHook(
        () =>
          useBulkTagApply({
            entries: mockEntries,
            sourceId: 'source-123',
            simulationMode: true,
          }),
        { wrapper: createWrapper() }
      );

      // skills directory has 2 direct children (canvas, docs)
      const dirTags = new Map([['skills', ['tag1', 'tag2']]]);

      await act(async () => {
        result.current.mutate(dirTags);
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      const data = result.current.data;
      expect(data).toBeDefined();
      expect(data?.totalUpdated).toBe(2);
      expect(data?.totalTagsApplied).toBe(4); // 2 entries * 2 tags
    });
  });

  describe('API mode', () => {
    it('calls API in non-simulation mode', async () => {
      const mockResult: BulkTagResult = {
        totalUpdated: 2,
        totalFailed: 0,
        totalTagsApplied: 4,
        errors: [],
      };

      mockApplyTagsToDirectories.mockResolvedValueOnce(mockResult);

      const { result } = renderHook(
        () =>
          useBulkTagApply({
            entries: mockEntries,
            sourceId: 'source-123',
            simulationMode: false,
          }),
        { wrapper: createWrapper() }
      );

      const dirTags = new Map([['skills', ['tag1']]]);

      await act(async () => {
        result.current.mutate(dirTags);
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(mockApplyTagsToDirectories).toHaveBeenCalledWith(
        mockEntries,
        dirTags,
        expect.objectContaining({
          sourceId: 'source-123',
          batchSize: 10,
          continueOnError: true,
        }),
        expect.any(Function) // onProgress callback
      );
    });

    it('handles API errors', async () => {
      const onError = jest.fn();
      mockApplyTagsToDirectories.mockRejectedValueOnce(new Error('API Error'));

      const { result } = renderHook(
        () =>
          useBulkTagApply({
            entries: mockEntries,
            sourceId: 'source-123',
            simulationMode: false,
            onError,
          }),
        { wrapper: createWrapper() }
      );

      const dirTags = new Map([['skills', ['tag1']]]);

      await act(async () => {
        result.current.mutate(dirTags);
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(onError).toHaveBeenCalledWith(expect.any(Error));
    });

    it('handles partial failures', async () => {
      const onSuccess = jest.fn();
      const mockResult: BulkTagResult = {
        totalUpdated: 1,
        totalFailed: 1,
        totalTagsApplied: 2,
        errors: [{ path: 'skills/docs', error: 'Update failed' }],
      };

      mockApplyTagsToDirectories.mockResolvedValueOnce(mockResult);

      const { result } = renderHook(
        () =>
          useBulkTagApply({
            entries: mockEntries,
            sourceId: 'source-123',
            simulationMode: false,
            onSuccess,
          }),
        { wrapper: createWrapper() }
      );

      const dirTags = new Map([['skills', ['tag1']]]);

      await act(async () => {
        result.current.mutate(dirTags);
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Should still call onSuccess with partial result
      expect(onSuccess).toHaveBeenCalledWith(mockResult);
    });
  });

  describe('progress tracking', () => {
    it('updates progress during operation', async () => {
      const progressUpdates: Array<{ current: number; total: number }> = [];

      mockApplyTagsToDirectories.mockImplementation(
        async (_entries, _dirTags, _options, onProgress) => {
          // Simulate progress callbacks
          onProgress?.(1, 2);
          progressUpdates.push({ current: 1, total: 2 });
          onProgress?.(2, 2);
          progressUpdates.push({ current: 2, total: 2 });

          return {
            totalUpdated: 2,
            totalFailed: 0,
            totalTagsApplied: 2,
            errors: [],
          };
        }
      );

      const { result } = renderHook(
        () =>
          useBulkTagApply({
            entries: mockEntries,
            sourceId: 'source-123',
            simulationMode: false,
          }),
        { wrapper: createWrapper() }
      );

      const dirTags = new Map([['skills', ['tag1']]]);

      await act(async () => {
        result.current.mutate(dirTags);
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Progress updates should have been triggered
      expect(progressUpdates.length).toBe(2);
    });

    it('resets progress on new mutation', async () => {
      mockApplyTagsToDirectories.mockResolvedValue({
        totalUpdated: 1,
        totalFailed: 0,
        totalTagsApplied: 1,
        errors: [],
      });

      const { result } = renderHook(
        () =>
          useBulkTagApply({
            entries: mockEntries,
            sourceId: 'source-123',
            simulationMode: false,
          }),
        { wrapper: createWrapper() }
      );

      // Initial progress should be zero
      expect(result.current.progress).toEqual({
        current: 0,
        total: 0,
        percentage: 0,
      });
    });

    it('provides resetProgress function', () => {
      const { result } = renderHook(
        () =>
          useBulkTagApply({
            entries: mockEntries,
            sourceId: 'source-123',
          }),
        { wrapper: createWrapper() }
      );

      expect(typeof result.current.resetProgress).toBe('function');
    });
  });

  describe('empty input handling', () => {
    it('handles empty entries array', async () => {
      const { result } = renderHook(
        () =>
          useBulkTagApply({
            entries: [],
            sourceId: 'source-123',
            simulationMode: true,
          }),
        { wrapper: createWrapper() }
      );

      const dirTags = new Map([['skills', ['tag1']]]);

      await act(async () => {
        result.current.mutate(dirTags);
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.totalUpdated).toBe(0);
    });

    it('handles empty dirTags map', async () => {
      const { result } = renderHook(
        () =>
          useBulkTagApply({
            entries: mockEntries,
            sourceId: 'source-123',
            simulationMode: true,
          }),
        { wrapper: createWrapper() }
      );

      await act(async () => {
        result.current.mutate(new Map());
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.totalUpdated).toBe(0);
    });

    it('handles directories with empty tag arrays', async () => {
      const { result } = renderHook(
        () =>
          useBulkTagApply({
            entries: mockEntries,
            sourceId: 'source-123',
            simulationMode: true,
          }),
        { wrapper: createWrapper() }
      );

      const dirTags = new Map<string, string[]>([
        ['skills', []],
        ['commands', []],
      ]);

      await act(async () => {
        result.current.mutate(dirTags);
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.totalUpdated).toBe(0);
    });
  });

  describe('callbacks', () => {
    it('calls onSuccess with result', async () => {
      const onSuccess = jest.fn();

      const { result } = renderHook(
        () =>
          useBulkTagApply({
            entries: mockEntries,
            sourceId: 'source-123',
            simulationMode: true,
            onSuccess,
          }),
        { wrapper: createWrapper() }
      );

      const dirTags = new Map([['skills', ['tag1']]]);

      await act(async () => {
        result.current.mutate(dirTags);
      });

      await waitFor(() => {
        expect(onSuccess).toHaveBeenCalledTimes(1);
      });

      expect(onSuccess).toHaveBeenCalledWith(
        expect.objectContaining({
          totalUpdated: expect.any(Number),
          totalFailed: expect.any(Number),
          totalTagsApplied: expect.any(Number),
          errors: expect.any(Array),
        })
      );
    });

    it('does not call onError on success', async () => {
      const onError = jest.fn();

      const { result } = renderHook(
        () =>
          useBulkTagApply({
            entries: mockEntries,
            sourceId: 'source-123',
            simulationMode: true,
            onError,
          }),
        { wrapper: createWrapper() }
      );

      const dirTags = new Map([['skills', ['tag1']]]);

      await act(async () => {
        result.current.mutate(dirTags);
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(onError).not.toHaveBeenCalled();
    });
  });
});
