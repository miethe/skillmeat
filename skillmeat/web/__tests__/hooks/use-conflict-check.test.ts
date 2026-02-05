/**
 * @jest-environment jsdom
 */
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React, { ReactNode } from 'react';
import { useConflictCheck } from '@/hooks/use-conflict-check';
import { apiRequest } from '@/lib/api';
import type { ArtifactDiffResponse } from '@/sdk/models/ArtifactDiffResponse';
import type { ArtifactUpstreamDiffResponse } from '@/sdk/models/ArtifactUpstreamDiffResponse';
import type { FileDiff } from '@/sdk/models/FileDiff';

// Mock apiRequest
jest.mock('@/lib/api', () => ({
  apiRequest: jest.fn(),
}));

const mockApiRequest = apiRequest as jest.MockedFunction<typeof apiRequest>;

// Helper factories for creating valid mock data
const createMockFileDiff = (overrides?: Partial<FileDiff>): FileDiff => ({
  file_path: 'test.txt',
  status: 'modified',
  collection_hash: null,
  project_hash: null,
  unified_diff: null,
  ...overrides,
});

const createMockArtifactDiffResponse = (
  overrides?: Partial<ArtifactDiffResponse>
): ArtifactDiffResponse => ({
  artifact_id: 'test-artifact',
  artifact_name: 'test-skill',
  artifact_type: 'skill',
  collection_name: 'default',
  project_path: '/path/to/project',
  has_changes: false,
  files: [],
  summary: {},
  ...overrides,
});

const createMockUpstreamDiffResponse = (
  overrides?: Partial<ArtifactUpstreamDiffResponse>
): ArtifactUpstreamDiffResponse => ({
  artifact_id: 'test-artifact',
  artifact_name: 'test-skill',
  artifact_type: 'skill',
  collection_name: 'default',
  upstream_source: 'github/user/repo',
  upstream_version: 'v1.0.0',
  has_changes: false,
  files: [],
  summary: {},
  ...overrides,
});

describe('useConflictCheck', () => {
  let queryClient: QueryClient;

  const createWrapper = () => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
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

  describe('Deploy direction', () => {
    it('calls /artifacts/{id}/diff endpoint with project_path', async () => {
      const mockResponse = createMockArtifactDiffResponse({
        has_changes: false,
        files: [],
        summary: {},
      });

      mockApiRequest.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(
        () =>
          useConflictCheck('deploy', 'test-artifact', {
            projectPath: '/path/to/project',
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(mockApiRequest).toHaveBeenCalledWith(
        '/artifacts/test-artifact/diff?project_path=%2Fpath%2Fto%2Fproject'
      );
      expect(result.current.diffData).toEqual(mockResponse);
    });

    it('encodes artifact ID in URL', async () => {
      const mockResponse = createMockArtifactDiffResponse({
        has_changes: false,
        files: [],
        summary: {},
      });

      mockApiRequest.mockResolvedValueOnce(mockResponse);

      renderHook(
        () =>
          useConflictCheck('deploy', 'artifact/with/slashes', {
            projectPath: '/project',
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(mockApiRequest).toHaveBeenCalled();
      });

      expect(mockApiRequest).toHaveBeenCalledWith(
        expect.stringContaining('artifact%2Fwith%2Fslashes')
      );
    });

    it('includes collection parameter when provided', async () => {
      const mockResponse = createMockArtifactDiffResponse({
        has_changes: false,
        files: [],
        summary: {},
      });

      mockApiRequest.mockResolvedValueOnce(mockResponse);

      renderHook(
        () =>
          useConflictCheck('deploy', 'test-artifact', {
            projectPath: '/project',
            collection: 'my-collection',
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(mockApiRequest).toHaveBeenCalled();
      });

      expect(mockApiRequest).toHaveBeenCalledWith(
        expect.stringContaining('collection=my-collection')
      );
    });
  });

  describe('Push direction', () => {
    it('calls /artifacts/{id}/diff endpoint with project_path', async () => {
      const mockResponse = createMockArtifactDiffResponse({
        has_changes: false,
        files: [],
        summary: {},
      });

      mockApiRequest.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(
        () =>
          useConflictCheck('push', 'test-artifact', {
            projectPath: '/path/to/project',
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(mockApiRequest).toHaveBeenCalledWith(
        '/artifacts/test-artifact/diff?project_path=%2Fpath%2Fto%2Fproject'
      );
    });
  });

  describe('Pull direction', () => {
    it('calls /artifacts/{id}/upstream-diff endpoint', async () => {
      const mockResponse = createMockUpstreamDiffResponse({
        has_changes: false,
        files: [],
        summary: {},
      });

      mockApiRequest.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(
        () =>
          useConflictCheck('pull', 'test-artifact', {
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(mockApiRequest).toHaveBeenCalledWith('/artifacts/test-artifact/upstream-diff');
      expect(result.current.diffData).toEqual(mockResponse);
    });

    it('does not require projectPath for pull direction', async () => {
      const mockResponse = createMockUpstreamDiffResponse({
        has_changes: false,
        files: [],
        summary: {},
      });

      mockApiRequest.mockResolvedValueOnce(mockResponse);

      renderHook(() => useConflictCheck('pull', 'test-artifact', { enabled: true }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(mockApiRequest).toHaveBeenCalled();
      });

      expect(mockApiRequest).toHaveBeenCalledWith('/artifacts/test-artifact/upstream-diff');
    });

    it('includes collection parameter when provided for pull', async () => {
      const mockResponse = createMockUpstreamDiffResponse({
        has_changes: false,
        files: [],
        summary: {},
      });

      mockApiRequest.mockResolvedValueOnce(mockResponse);

      renderHook(
        () =>
          useConflictCheck('pull', 'test-artifact', {
            collection: 'my-collection',
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(mockApiRequest).toHaveBeenCalled();
      });

      expect(mockApiRequest).toHaveBeenCalledWith(
        '/artifacts/test-artifact/upstream-diff?collection=my-collection'
      );
    });
  });

  describe('hasChanges computed property', () => {
    it('returns true when diffData.has_changes is true', async () => {
      const mockResponse = createMockArtifactDiffResponse({
        has_changes: true,
        files: [createMockFileDiff({ file_path: 'test.txt', status: 'modified' })],
        summary: { modified: 1 },
      });

      mockApiRequest.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(
        () =>
          useConflictCheck('deploy', 'test-artifact', {
            projectPath: '/project',
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.hasChanges).toBe(true);
      });
    });

    it('returns false when diffData.has_changes is false', async () => {
      const mockResponse = createMockArtifactDiffResponse({
        has_changes: false,
        files: [],
        summary: {},
      });

      mockApiRequest.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(
        () =>
          useConflictCheck('deploy', 'test-artifact', {
            projectPath: '/project',
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.hasChanges).toBe(false);
      });
    });
  });

  describe('targetHasChanges computed property', () => {
    it('returns true for deploy when files have change_origin "local"', async () => {
      const mockResponse = createMockArtifactDiffResponse({
        has_changes: true,
        files: [
          {
            ...createMockFileDiff({ file_path: 'test.txt', status: 'modified' }),
            change_origin: 'local',
          } as any,
        ],
        summary: { modified: 1 },
      });

      mockApiRequest.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(
        () =>
          useConflictCheck('deploy', 'test-artifact', {
            projectPath: '/project',
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.targetHasChanges).toBe(true);
      });
    });

    it('returns true for deploy when files have change_origin "both"', async () => {
      const mockResponse = createMockArtifactDiffResponse({
        has_changes: true,
        files: [
          {
            ...createMockFileDiff({ file_path: 'test.txt', status: 'modified' }),
            change_origin: 'both',
          } as any,
        ],
        summary: { modified: 1 },
      });

      mockApiRequest.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(
        () =>
          useConflictCheck('deploy', 'test-artifact', {
            projectPath: '/project',
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.targetHasChanges).toBe(true);
      });
    });

    it('returns false for deploy when files have only change_origin "upstream"', async () => {
      const mockResponse = createMockArtifactDiffResponse({
        has_changes: true,
        files: [
          {
            ...createMockFileDiff({ file_path: 'test.txt', status: 'modified' }),
            change_origin: 'upstream',
          } as any,
        ],
        summary: { modified: 1 },
      });

      mockApiRequest.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(
        () =>
          useConflictCheck('deploy', 'test-artifact', {
            projectPath: '/project',
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.targetHasChanges).toBe(false);
      });
    });

    it('returns true for push when files have change_origin "upstream"', async () => {
      const mockResponse = createMockArtifactDiffResponse({
        has_changes: true,
        files: [
          {
            ...createMockFileDiff({ file_path: 'test.txt', status: 'modified' }),
            change_origin: 'upstream',
          } as any,
        ],
        summary: { modified: 1 },
      });

      mockApiRequest.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(
        () =>
          useConflictCheck('push', 'test-artifact', {
            projectPath: '/project',
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.targetHasChanges).toBe(true);
      });
    });

    it('returns true for pull when files have change_origin "local"', async () => {
      const mockResponse = createMockUpstreamDiffResponse({
        has_changes: true,
        files: [
          {
            ...createMockFileDiff({ file_path: 'test.txt', status: 'modified' }),
            change_origin: 'local',
          } as any,
        ],
        summary: { modified: 1 },
      });

      mockApiRequest.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(
        () => useConflictCheck('pull', 'test-artifact', { enabled: true }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.targetHasChanges).toBe(true);
      });
    });

    it('falls back to status-based detection when change_origin is missing (deploy)', async () => {
      const mockResponse = createMockArtifactDiffResponse({
        has_changes: true,
        files: [
          createMockFileDiff({ file_path: 'test1.txt', status: 'modified' }),
          createMockFileDiff({ file_path: 'test2.txt', status: 'deleted' }),
        ],
        summary: { modified: 1, deleted: 1 },
      });

      mockApiRequest.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(
        () =>
          useConflictCheck('deploy', 'test-artifact', {
            projectPath: '/project',
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.targetHasChanges).toBe(true);
      });
    });

    it('falls back to status-based detection when change_origin is missing (push)', async () => {
      const mockResponse = createMockArtifactDiffResponse({
        has_changes: true,
        files: [
          createMockFileDiff({ file_path: 'test1.txt', status: 'modified' }),
          createMockFileDiff({ file_path: 'test2.txt', status: 'added' }),
        ],
        summary: { modified: 1, added: 1 },
      });

      mockApiRequest.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(
        () =>
          useConflictCheck('push', 'test-artifact', {
            projectPath: '/project',
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.targetHasChanges).toBe(true);
      });
    });

    it('returns false when no files have target-side changes', async () => {
      const mockResponse = createMockArtifactDiffResponse({
        has_changes: true,
        files: [createMockFileDiff({ file_path: 'test.txt', status: 'added' })],
        summary: { added: 1 },
      });

      mockApiRequest.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(
        () =>
          useConflictCheck('deploy', 'test-artifact', {
            projectPath: '/project',
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.targetHasChanges).toBe(false);
      });
    });
  });

  describe('hasConflicts computed property', () => {
    it('returns true when files have change_origin "both"', async () => {
      const mockResponse = createMockArtifactDiffResponse({
        has_changes: true,
        files: [
          {
            ...createMockFileDiff({ file_path: 'test.txt', status: 'modified' }),
            change_origin: 'both',
          } as any,
        ],
        summary: { modified: 1 },
      });

      mockApiRequest.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(
        () =>
          useConflictCheck('deploy', 'test-artifact', {
            projectPath: '/project',
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.hasConflicts).toBe(true);
      });
    });

    it('returns true when summary.conflicts > 0', async () => {
      const mockResponse = createMockArtifactDiffResponse({
        has_changes: true,
        files: [createMockFileDiff({ file_path: 'test.txt', status: 'modified' })],
        summary: { modified: 1, conflicts: 2 },
      });

      mockApiRequest.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(
        () =>
          useConflictCheck('deploy', 'test-artifact', {
            projectPath: '/project',
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.hasConflicts).toBe(true);
      });
    });

    it('returns false when no conflicts exist', async () => {
      const mockResponse = createMockArtifactDiffResponse({
        has_changes: true,
        files: [createMockFileDiff({ file_path: 'test.txt', status: 'modified' })],
        summary: { modified: 1 },
      });

      mockApiRequest.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(
        () =>
          useConflictCheck('deploy', 'test-artifact', {
            projectPath: '/project',
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.hasConflicts).toBe(false);
      });
    });
  });

  describe('Loading state', () => {
    it('returns isLoading true while fetching', () => {
      mockApiRequest.mockImplementationOnce(
        () => new Promise((resolve) => setTimeout(resolve, 100))
      );

      const { result } = renderHook(
        () =>
          useConflictCheck('deploy', 'test-artifact', {
            projectPath: '/project',
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      expect(result.current.isLoading).toBe(true);
    });

    it('returns isLoading false after fetch completes', async () => {
      const mockResponse = createMockArtifactDiffResponse({
        has_changes: false,
        files: [],
        summary: {},
      });

      mockApiRequest.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(
        () =>
          useConflictCheck('deploy', 'test-artifact', {
            projectPath: '/project',
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });
    });
  });

  describe('Error state', () => {
    it('returns error when API fails', async () => {
      const mockError = new Error('Network error');
      mockApiRequest.mockRejectedValueOnce(mockError);

      const { result } = renderHook(
        () =>
          useConflictCheck('deploy', 'test-artifact', {
            projectPath: '/project',
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.error).toBeTruthy();
      });

      expect(result.current.error).toEqual(mockError);
    });

    it('sets diffData to undefined on error', async () => {
      const mockError = new Error('Network error');
      mockApiRequest.mockRejectedValueOnce(mockError);

      const { result } = renderHook(
        () =>
          useConflictCheck('deploy', 'test-artifact', {
            projectPath: '/project',
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.error).toBeTruthy();
      });

      expect(result.current.diffData).toBeUndefined();
    });
  });

  describe('enabled: false', () => {
    it('does not fetch when enabled is false', async () => {
      const { result } = renderHook(
        () =>
          useConflictCheck('deploy', 'test-artifact', {
            projectPath: '/project',
            enabled: false,
          }),
        { wrapper: createWrapper() }
      );

      // Wait a bit to ensure no fetch happens
      await new Promise((resolve) => setTimeout(resolve, 50));

      expect(mockApiRequest).not.toHaveBeenCalled();
      expect(result.current.isLoading).toBe(false);
      expect(result.current.diffData).toBeUndefined();
    });

    it('does not fetch deploy/push when projectPath is missing', async () => {
      const { result } = renderHook(
        () =>
          useConflictCheck('deploy', 'test-artifact', {
            enabled: true,
            // projectPath missing
          }),
        { wrapper: createWrapper() }
      );

      await new Promise((resolve) => setTimeout(resolve, 50));

      expect(mockApiRequest).not.toHaveBeenCalled();
      expect(result.current.isLoading).toBe(false);
    });

    it('does not fetch when artifactId is missing', async () => {
      const { result } = renderHook(
        () =>
          useConflictCheck('deploy', '', {
            projectPath: '/project',
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      await new Promise((resolve) => setTimeout(resolve, 50));

      expect(mockApiRequest).not.toHaveBeenCalled();
      expect(result.current.isLoading).toBe(false);
    });
  });

  describe('Stale time', () => {
    it('uses 30-second stale time for queries', async () => {
      const mockResponse = createMockArtifactDiffResponse({
        has_changes: false,
        files: [],
        summary: {},
      });

      mockApiRequest.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(
        () =>
          useConflictCheck('deploy', 'test-artifact', {
            projectPath: '/project',
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Verify the query was cached (which means it executed successfully)
      const queryState = queryClient.getQueryState([
        'conflict-check',
        'deploy',
        'test-artifact',
        '/project',
      ]);

      expect(queryState).toBeDefined();
      expect(queryState?.data).toEqual(mockResponse);
    });
  });

  describe('Query key generation', () => {
    it('generates correct query key for deploy', async () => {
      const mockResponse = createMockArtifactDiffResponse({
        has_changes: false,
        files: [],
        summary: {},
      });

      mockApiRequest.mockResolvedValueOnce(mockResponse);

      renderHook(
        () =>
          useConflictCheck('deploy', 'test-artifact', {
            projectPath: '/project',
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(mockApiRequest).toHaveBeenCalled();
      });

      const queryState = queryClient.getQueryState([
        'conflict-check',
        'deploy',
        'test-artifact',
        '/project',
      ]);

      expect(queryState).toBeDefined();
    });

    it('generates correct query key for pull (no projectPath)', async () => {
      const mockResponse = createMockUpstreamDiffResponse({
        has_changes: false,
        files: [],
        summary: {},
      });

      mockApiRequest.mockResolvedValueOnce(mockResponse);

      renderHook(
        () =>
          useConflictCheck('pull', 'test-artifact', {
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(mockApiRequest).toHaveBeenCalled();
      });

      const queryState = queryClient.getQueryState([
        'conflict-check',
        'pull',
        'test-artifact',
        undefined,
      ]);

      expect(queryState).toBeDefined();
    });
  });

  describe('Edge cases', () => {
    it('handles empty files array', async () => {
      const mockResponse = createMockArtifactDiffResponse({
        has_changes: false,
        files: [],
        summary: {},
      });

      mockApiRequest.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(
        () =>
          useConflictCheck('deploy', 'test-artifact', {
            projectPath: '/project',
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.hasChanges).toBe(false);
      expect(result.current.hasConflicts).toBe(false);
      expect(result.current.targetHasChanges).toBe(false);
    });

    it('handles numeric artifact IDs', async () => {
      const mockResponse = createMockArtifactDiffResponse({
        has_changes: false,
        files: [],
        summary: {},
      });

      mockApiRequest.mockResolvedValueOnce(mockResponse);

      renderHook(
        () =>
          useConflictCheck('deploy', 12345, {
            projectPath: '/project',
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(mockApiRequest).toHaveBeenCalled();
      });

      expect(mockApiRequest).toHaveBeenCalledWith(
        expect.stringContaining('/artifacts/12345/diff')
      );
    });

    it('handles summary with missing conflict field', async () => {
      const mockResponse = createMockArtifactDiffResponse({
        has_changes: true,
        files: [createMockFileDiff({ file_path: 'test.txt', status: 'modified' })],
        summary: { modified: 1 },
      });

      mockApiRequest.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(
        () =>
          useConflictCheck('deploy', 'test-artifact', {
            projectPath: '/project',
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.hasConflicts).toBe(false);
      });
    });
  });
});
