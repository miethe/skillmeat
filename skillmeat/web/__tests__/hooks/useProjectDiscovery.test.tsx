/**
 * Tests for useProjectDiscovery hook
 *
 * Tests DIS-3.6 (skip preference loading/state) and DIS-3.7 (form submission with skip list)
 */

import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode, ReactElement } from 'react';
import { useProjectDiscovery } from '@/hooks/useProjectDiscovery';
import * as api from '@/lib/api';
import * as skipPrefsLib from '@/lib/skip-preferences';
import type { DiscoveryResult, BulkImportResult } from '@/types/discovery';

// Mock modules
jest.mock('@/lib/api');
jest.mock('@/lib/skip-preferences');

const mockApiRequest = api.apiRequest as jest.MockedFunction<typeof api.apiRequest>;
const mockLoadSkipPrefs = skipPrefsLib.loadSkipPrefs as jest.MockedFunction<
  typeof skipPrefsLib.loadSkipPrefs
>;
const mockSaveSkipPrefs = skipPrefsLib.saveSkipPrefs as jest.MockedFunction<
  typeof skipPrefsLib.saveSkipPrefs
>;
const mockClearSkipPrefs = skipPrefsLib.clearSkipPrefs as jest.MockedFunction<
  typeof skipPrefsLib.clearSkipPrefs
>;
const mockBuildArtifactKey = skipPrefsLib.buildArtifactKey as jest.MockedFunction<
  typeof skipPrefsLib.buildArtifactKey
>;

describe('useProjectDiscovery', () => {
  let queryClient: QueryClient;
  let wrapper: ({ children }: { children: ReactNode }) => ReactElement;

  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();

    // Create a fresh query client for each test
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    // Create wrapper component
    wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    // Setup default mock implementations
    mockBuildArtifactKey.mockImplementation((type, name) => `${type}:${name}`);
  });

  afterEach(() => {
    queryClient.clear();
  });

  describe('DIS-3.6: Skip Preference Loading', () => {
    it('should load skip preferences when projectId is provided', () => {
      const mockSkipPrefs = [
        {
          artifact_key: 'skill:canvas-design',
          skip_reason: 'Not needed',
          added_date: '2024-01-01T00:00:00Z',
        },
      ];

      mockLoadSkipPrefs.mockReturnValue(mockSkipPrefs);

      const { result } = renderHook(
        () => useProjectDiscovery('/path/to/project', 'project-123'),
        { wrapper }
      );

      expect(mockLoadSkipPrefs).toHaveBeenCalledWith('project-123');
      expect(result.current.skipPrefs).toEqual(mockSkipPrefs);
    });

    it('should not load skip preferences when projectId is missing', () => {
      const { result } = renderHook(() => useProjectDiscovery('/path/to/project', undefined), {
        wrapper,
      });

      expect(mockLoadSkipPrefs).not.toHaveBeenCalled();
      expect(result.current.skipPrefs).toEqual([]);
    });

    it('should reload skip preferences when projectId changes', () => {
      const mockSkipPrefs1 = [
        {
          artifact_key: 'skill:canvas-design',
          skip_reason: 'Not needed',
          added_date: '2024-01-01T00:00:00Z',
        },
      ];
      const mockSkipPrefs2 = [
        {
          artifact_key: 'skill:other-skill',
          skip_reason: 'Not needed',
          added_date: '2024-01-01T00:00:00Z',
        },
      ];

      mockLoadSkipPrefs.mockReturnValueOnce(mockSkipPrefs1).mockReturnValueOnce(mockSkipPrefs2);

      const { result, rerender } = renderHook(
        ({ projectId }) => useProjectDiscovery('/path/to/project', projectId),
        {
          wrapper,
          initialProps: { projectId: 'project-123' },
        }
      );

      expect(result.current.skipPrefs).toEqual(mockSkipPrefs1);

      rerender({ projectId: 'project-456' });

      expect(mockLoadSkipPrefs).toHaveBeenCalledTimes(2);
      expect(mockLoadSkipPrefs).toHaveBeenLastCalledWith('project-456');
      expect(result.current.skipPrefs).toEqual(mockSkipPrefs2);
    });
  });

  describe('DIS-3.6: isArtifactSkipped helper', () => {
    it('should correctly identify skipped artifacts', () => {
      const mockSkipPrefs = [
        {
          artifact_key: 'skill:canvas-design',
          skip_reason: 'Not needed',
          added_date: '2024-01-01T00:00:00Z',
        },
      ];

      mockLoadSkipPrefs.mockReturnValue(mockSkipPrefs);

      const { result } = renderHook(
        () => useProjectDiscovery('/path/to/project', 'project-123'),
        { wrapper }
      );

      expect(result.current.isArtifactSkipped('skill', 'canvas-design')).toBe(true);
      expect(result.current.isArtifactSkipped('skill', 'other-skill')).toBe(false);
    });
  });

  describe('DIS-3.6: clearSkips helper', () => {
    it('should clear skip preferences', () => {
      const mockSkipPrefs = [
        {
          artifact_key: 'skill:canvas-design',
          skip_reason: 'Not needed',
          added_date: '2024-01-01T00:00:00Z',
        },
      ];

      mockLoadSkipPrefs.mockReturnValue(mockSkipPrefs);

      const { result } = renderHook(
        () => useProjectDiscovery('/path/to/project', 'project-123'),
        { wrapper }
      );

      act(() => {
        result.current.clearSkips();
      });

      expect(mockClearSkipPrefs).toHaveBeenCalledWith('project-123');
      expect(result.current.skipPrefs).toEqual([]);
    });

    it('should not call clearSkipPrefs when projectId is missing', () => {
      const { result } = renderHook(() => useProjectDiscovery('/path/to/project', undefined), {
        wrapper,
      });

      act(() => {
        result.current.clearSkips();
      });

      expect(mockClearSkipPrefs).not.toHaveBeenCalled();
    });
  });

  describe('DIS-3.7: Import with skip list', () => {
    it('should include skip_list in import request', async () => {
      const mockResult: BulkImportResult = {
        total_requested: 2,
        total_imported: 1,
        total_skipped: 1,
        total_failed: 0,
        imported_to_collection: 1,
        added_to_project: 0,
        results: [
          {
            artifact_id: 'skill:test-skill',
            status: 'success',
            message: 'Imported',
          },
          {
            artifact_id: 'skill:skipped-skill',
            status: 'skipped',
            message: 'Skipped',
            skip_reason: 'User preference',
          },
        ],
        duration_ms: 100,
      };

      mockApiRequest.mockResolvedValueOnce(mockResult);
      mockLoadSkipPrefs.mockReturnValue([]);

      const { result } = renderHook(
        () => useProjectDiscovery('/path/to/project', 'project-123'),
        { wrapper }
      );

      await act(async () => {
        await result.current.bulkImport({
          artifacts: [
            {
              source: 'local/skill/test-skill',
              artifact_type: 'skill',
              name: 'test-skill',
              scope: 'user',
              path: '/path/to/skill',
            },
          ],
          skip_list: ['skill:skipped-skill'],
        });
      });

      expect(mockApiRequest).toHaveBeenCalledWith(
        '/artifacts/discover/import?project_id=project-123',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            artifacts: [
              {
                source: 'local/skill/test-skill',
                artifact_type: 'skill',
                name: 'test-skill',
                scope: 'user',
                path: '/path/to/skill',
              },
            ],
            skip_list: ['skill:skipped-skill'],
          }),
        }
      );
    });

    it('should save skip preferences after successful import', async () => {
      const existingSkipPrefs = [
        {
          artifact_key: 'skill:existing-skip',
          skip_reason: 'Already skipped',
          added_date: '2024-01-01T00:00:00Z',
        },
      ];

      const mockResult: BulkImportResult = {
        total_requested: 1,
        total_imported: 1,
        total_skipped: 0,
        total_failed: 0,
        imported_to_collection: 1,
        added_to_project: 0,
        results: [
          {
            artifact_id: 'skill:test-skill',
            status: 'success',
            message: 'Imported',
          },
        ],
        duration_ms: 100,
      };

      mockApiRequest.mockResolvedValueOnce(mockResult);
      mockLoadSkipPrefs.mockReturnValue(existingSkipPrefs);

      const { result } = renderHook(
        () => useProjectDiscovery('/path/to/project', 'project-123'),
        { wrapper }
      );

      await act(async () => {
        await result.current.bulkImport({
          artifacts: [
            {
              source: 'local/skill/test-skill',
              artifact_type: 'skill',
              name: 'test-skill',
              scope: 'user',
              path: '/path/to/skill',
            },
          ],
          skip_list: ['skill:new-skip', 'skill:another-skip'],
        });
      });

      await waitFor(() => {
        expect(mockSaveSkipPrefs).toHaveBeenCalledWith('project-123', expect.any(Array));
      });

      const savedPrefs = mockSaveSkipPrefs.mock.calls[0]?.[1];
      expect(savedPrefs).toBeDefined();
      expect(savedPrefs).toHaveLength(3); // 1 existing + 2 new
      expect(savedPrefs).toEqual(
        expect.arrayContaining([
          existingSkipPrefs[0],
          expect.objectContaining({
            artifact_key: 'skill:new-skip',
            skip_reason: 'Skipped during import',
          }),
          expect.objectContaining({
            artifact_key: 'skill:another-skip',
            skip_reason: 'Skipped during import',
          }),
        ])
      );
    });

    it('should avoid duplicate skip preferences', async () => {
      const existingSkipPrefs = [
        {
          artifact_key: 'skill:existing-skip',
          skip_reason: 'Already skipped',
          added_date: '2024-01-01T00:00:00Z',
        },
      ];

      const mockResult: BulkImportResult = {
        total_requested: 1,
        total_imported: 1,
        total_skipped: 0,
        total_failed: 0,
        imported_to_collection: 1,
        added_to_project: 0,
        results: [
          {
            artifact_id: 'skill:test-skill',
            status: 'success',
            message: 'Imported',
          },
        ],
        duration_ms: 100,
      };

      mockApiRequest.mockResolvedValueOnce(mockResult);
      mockLoadSkipPrefs.mockReturnValue(existingSkipPrefs);

      const { result } = renderHook(
        () => useProjectDiscovery('/path/to/project', 'project-123'),
        { wrapper }
      );

      // Try to add a duplicate skip
      await act(async () => {
        await result.current.bulkImport({
          artifacts: [
            {
              source: 'local/skill/test-skill',
              artifact_type: 'skill',
              name: 'test-skill',
              scope: 'user',
              path: '/path/to/skill',
            },
          ],
          skip_list: ['skill:existing-skip', 'skill:new-skip'],
        });
      });

      await waitFor(() => {
        expect(mockSaveSkipPrefs).toHaveBeenCalled();
      });

      const savedPrefs = mockSaveSkipPrefs.mock.calls[0]?.[1];
      expect(savedPrefs).toBeDefined();
      expect(savedPrefs).toHaveLength(2); // Should not duplicate existing-skip
      expect(savedPrefs?.filter((p) => p.artifact_key === 'skill:existing-skip')).toHaveLength(1);
    });

    it('should not save skip preferences when skip_list is empty', async () => {
      const mockResult: BulkImportResult = {
        total_requested: 1,
        total_imported: 1,
        total_skipped: 0,
        total_failed: 0,
        imported_to_collection: 1,
        added_to_project: 0,
        results: [
          {
            artifact_id: 'skill:test-skill',
            status: 'success',
            message: 'Imported',
          },
        ],
        duration_ms: 100,
      };

      mockApiRequest.mockResolvedValueOnce(mockResult);
      mockLoadSkipPrefs.mockReturnValue([]);

      const { result } = renderHook(
        () => useProjectDiscovery('/path/to/project', 'project-123'),
        { wrapper }
      );

      await act(async () => {
        await result.current.bulkImport({
          artifacts: [
            {
              source: 'local/skill/test-skill',
              artifact_type: 'skill',
              name: 'test-skill',
              scope: 'user',
              path: '/path/to/skill',
            },
          ],
          skip_list: [],
        });
      });

      await waitFor(() => {
        expect(mockApiRequest).toHaveBeenCalled();
      });

      expect(mockSaveSkipPrefs).not.toHaveBeenCalled();
    });
  });

  describe('Discovery query', () => {
    it('should discover artifacts when refetchDiscovery is called', async () => {
      const mockDiscoveryResult: DiscoveryResult = {
        discovered_count: 2,
        importable_count: 2,
        artifacts: [
          {
            type: 'skill',
            name: 'test-skill',
            source: 'local/skill/test-skill',
            path: '/path/to/skill',
            discovered_at: '2024-01-01T00:00:00Z',
          },
        ],
        errors: [],
        scan_duration_ms: 50,
      };

      mockApiRequest.mockResolvedValueOnce(mockDiscoveryResult);
      mockLoadSkipPrefs.mockReturnValue([]);

      const { result } = renderHook(
        () => useProjectDiscovery('/path/to/project', 'project-123'),
        { wrapper }
      );

      result.current.refetchDiscovery();

      await waitFor(() => {
        expect(result.current.discoveredArtifacts).toHaveLength(1);
      });

      expect(result.current.discoveredCount).toBe(2);
      expect(result.current.importableCount).toBe(2);
    });
  });
});
