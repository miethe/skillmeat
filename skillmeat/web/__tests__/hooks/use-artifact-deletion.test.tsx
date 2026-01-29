/**
 * @jest-environment jsdom
 */
import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useArtifactDeletion, type DeletionParams } from '@/hooks/use-artifact-deletion';
import { deleteArtifactFromCollection } from '@/lib/api/artifacts';
import { undeployArtifact } from '@/lib/api/deployments';
import type { Artifact } from '@/types/artifact';

// Mock the API functions
jest.mock('@/lib/api/artifacts', () => ({
  deleteArtifactFromCollection: jest.fn(),
}));

jest.mock('@/lib/api/deployments', () => ({
  undeployArtifact: jest.fn(),
}));

const mockedDeleteArtifact = deleteArtifactFromCollection as jest.MockedFunction<
  typeof deleteArtifactFromCollection
>;
const mockedUndeployArtifact = undeployArtifact as jest.MockedFunction<typeof undeployArtifact>;

// Test wrapper with QueryClientProvider
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

// Mock artifact for testing
const mockArtifact: Artifact = {
  id: 'artifact-123',
  name: 'test-skill',
  type: 'skill',
  scope: 'user',
  syncStatus: 'synced',
  version: '1.0.0',
  source: 'user/repo/skill',
  description: 'A test skill',
  upstream: {
    enabled: true,
    updateAvailable: false,
  },
  usageStats: {
    totalDeployments: 2,
    activeProjects: 1,
    usageCount: 5,
  },
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-02T00:00:00Z',
};

describe('useArtifactDeletion', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Collection Deletion Only', () => {
    it('deletes artifact from collection only', async () => {
      mockedDeleteArtifact.mockResolvedValueOnce(undefined);

      const { result } = renderHook(() => useArtifactDeletion(), {
        wrapper: createWrapper(),
      });

      const params: DeletionParams = {
        artifact: mockArtifact,
        deleteFromCollection: true,
        deleteFromProjects: false,
        deleteDeployments: false,
        selectedProjectPaths: [],
        selectedDeploymentPaths: [],
      };

      await result.current.mutateAsync(params);

      // Assert deleteArtifactFromCollection was called
      expect(mockedDeleteArtifact).toHaveBeenCalledWith('artifact-123');
      expect(mockedDeleteArtifact).toHaveBeenCalledTimes(1);

      // Assert undeployArtifact was NOT called
      expect(mockedUndeployArtifact).not.toHaveBeenCalled();
    });

    it('returns correct result for collection deletion', async () => {
      mockedDeleteArtifact.mockResolvedValueOnce(undefined);

      const { result } = renderHook(() => useArtifactDeletion(), {
        wrapper: createWrapper(),
      });

      const params: DeletionParams = {
        artifact: mockArtifact,
        deleteFromCollection: true,
        deleteFromProjects: false,
        deleteDeployments: false,
        selectedProjectPaths: [],
        selectedDeploymentPaths: [],
      };

      const deletionResult = await result.current.mutateAsync(params);

      expect(deletionResult.collectionDeleted).toBe(true);
      expect(deletionResult.projectsUndeployed).toBe(0);
      expect(deletionResult.deploymentsDeleted).toBe(0);
      expect(deletionResult.errors).toEqual([]);
    });
  });

  describe('Project Undeploy', () => {
    it('undeploys from selected projects', async () => {
      const mockUndeployResponse = {
        success: true,
        message: 'Artifact undeployed successfully',
      };

      mockedUndeployArtifact.mockResolvedValue(mockUndeployResponse);

      const { result } = renderHook(() => useArtifactDeletion(), {
        wrapper: createWrapper(),
      });

      const params: DeletionParams = {
        artifact: mockArtifact,
        deleteFromCollection: false,
        deleteFromProjects: true,
        deleteDeployments: false,
        selectedProjectPaths: ['/path/1', '/path/2'],
        selectedDeploymentPaths: [],
      };

      const deletionResult = await result.current.mutateAsync(params);

      // Assert undeployArtifact called twice with correct params
      expect(mockedUndeployArtifact).toHaveBeenCalledTimes(2);
      expect(mockedUndeployArtifact).toHaveBeenCalledWith({
        artifact_name: 'test-skill',
        artifact_type: 'skill',
        project_path: '/path/1',
      });
      expect(mockedUndeployArtifact).toHaveBeenCalledWith({
        artifact_name: 'test-skill',
        artifact_type: 'skill',
        project_path: '/path/2',
      });

      // Assert result shows correct count
      expect(deletionResult.projectsUndeployed).toBe(2);
      expect(deletionResult.collectionDeleted).toBe(false);
      expect(deletionResult.errors).toEqual([]);
    });

    it('executes undeployments in parallel', async () => {
      let resolveCount = 0;
      const mockUndeployResponse = {
        success: true,
        message: 'Artifact undeployed successfully',
      };

      // Mock delays to verify parallelization
      mockedUndeployArtifact.mockImplementation(
        () =>
          new Promise((resolve) =>
            setTimeout(() => {
              resolveCount++;
              resolve(mockUndeployResponse);
            }, 50)
          )
      );

      const { result } = renderHook(() => useArtifactDeletion(), {
        wrapper: createWrapper(),
      });

      const params: DeletionParams = {
        artifact: mockArtifact,
        deleteFromCollection: false,
        deleteFromProjects: true,
        deleteDeployments: false,
        selectedProjectPaths: ['/path/1', '/path/2', '/path/3'],
        selectedDeploymentPaths: [],
      };

      const startTime = Date.now();
      await result.current.mutateAsync(params);
      const endTime = Date.now();

      // If parallel, should take ~50ms total, not 150ms (3 x 50ms)
      // Allow some buffer for test execution
      expect(endTime - startTime).toBeLessThan(150);
      expect(resolveCount).toBe(3);
    });
  });

  describe('Partial Failures', () => {
    it('handles partial failures gracefully', async () => {
      const mockUndeployResponse = {
        success: true,
        message: 'Artifact undeployed successfully',
      };

      // First call succeeds, second fails
      mockedUndeployArtifact
        .mockResolvedValueOnce(mockUndeployResponse)
        .mockRejectedValueOnce(new Error('Permission denied'));

      const { result } = renderHook(() => useArtifactDeletion(), {
        wrapper: createWrapper(),
      });

      const params: DeletionParams = {
        artifact: mockArtifact,
        deleteFromCollection: false,
        deleteFromProjects: true,
        deleteDeployments: false,
        selectedProjectPaths: ['/path/1', '/path/2'],
        selectedDeploymentPaths: [],
      };

      const deletionResult = await result.current.mutateAsync(params);

      // Should count only successes
      expect(deletionResult.projectsUndeployed).toBe(1);

      // Should include error for failed project
      expect(deletionResult.errors).toHaveLength(1);
      expect(deletionResult.errors[0]).toEqual({
        operation: 'undeploy:/path/2',
        error: 'Permission denied',
      });
    });

    it('continues with other operations if one fails', async () => {
      const mockUndeployResponse = {
        success: true,
        message: 'Artifact undeployed successfully',
      };

      // Middle one fails, others succeed
      mockedUndeployArtifact
        .mockResolvedValueOnce(mockUndeployResponse)
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce(mockUndeployResponse);

      const { result } = renderHook(() => useArtifactDeletion(), {
        wrapper: createWrapper(),
      });

      const params: DeletionParams = {
        artifact: mockArtifact,
        deleteFromCollection: false,
        deleteFromProjects: true,
        deleteDeployments: false,
        selectedProjectPaths: ['/path/1', '/path/2', '/path/3'],
        selectedDeploymentPaths: [],
      };

      const deletionResult = await result.current.mutateAsync(params);

      expect(deletionResult.projectsUndeployed).toBe(2);
      expect(deletionResult.errors).toHaveLength(1);
      expect(deletionResult.errors[0].operation).toBe('undeploy:/path/2');
    });
  });

  describe('Complete Failures', () => {
    it('throws error when all operations fail', async () => {
      mockedDeleteArtifact.mockRejectedValueOnce(new Error('Database error'));
      mockedUndeployArtifact.mockRejectedValue(new Error('Filesystem error'));

      const { result } = renderHook(() => useArtifactDeletion(), {
        wrapper: createWrapper(),
      });

      const params: DeletionParams = {
        artifact: mockArtifact,
        deleteFromCollection: true,
        deleteFromProjects: true,
        deleteDeployments: false,
        selectedProjectPaths: ['/path/1', '/path/2'],
        selectedDeploymentPaths: [],
      };

      await expect(result.current.mutateAsync(params)).rejects.toThrow(
        /All deletion operations failed/
      );
    });

    it('includes individual failures in error message', async () => {
      mockedDeleteArtifact.mockRejectedValueOnce(new Error('Database error'));
      mockedUndeployArtifact.mockRejectedValue(new Error('Filesystem error'));

      const { result } = renderHook(() => useArtifactDeletion(), {
        wrapper: createWrapper(),
      });

      const params: DeletionParams = {
        artifact: mockArtifact,
        deleteFromCollection: true,
        deleteFromProjects: true,
        deleteDeployments: false,
        selectedProjectPaths: ['/path/1'],
        selectedDeploymentPaths: [],
      };

      try {
        await result.current.mutateAsync(params);
        fail('Should have thrown error');
      } catch (error) {
        expect(error).toBeInstanceOf(Error);
        const errorMessage = (error as Error).message;
        expect(errorMessage).toContain('collection_deletion');
        expect(errorMessage).toContain('Database error');
        expect(errorMessage).toContain('undeploy:/path/1');
        expect(errorMessage).toContain('Filesystem error');
      }
    });
  });

  describe('Collection Deletion Error Handling', () => {
    it('handles collection deletion error', async () => {
      mockedDeleteArtifact.mockRejectedValueOnce(new Error('Not found'));

      const { result } = renderHook(() => useArtifactDeletion(), {
        wrapper: createWrapper(),
      });

      const params: DeletionParams = {
        artifact: mockArtifact,
        deleteFromCollection: true,
        deleteFromProjects: false,
        deleteDeployments: false,
        selectedProjectPaths: [],
        selectedDeploymentPaths: [],
      };

      await expect(result.current.mutateAsync(params)).rejects.toThrow(
        /All deletion operations failed/
      );
    });

    it('records collection deletion error in result', async () => {
      const mockUndeployResponse = {
        success: true,
        message: 'Artifact undeployed successfully',
      };

      mockedDeleteArtifact.mockRejectedValueOnce(new Error('Permission denied'));
      mockedUndeployArtifact.mockResolvedValueOnce(mockUndeployResponse);

      const { result } = renderHook(() => useArtifactDeletion(), {
        wrapper: createWrapper(),
      });

      const params: DeletionParams = {
        artifact: mockArtifact,
        deleteFromCollection: true,
        deleteFromProjects: true,
        deleteDeployments: false,
        selectedProjectPaths: ['/path/1'],
        selectedDeploymentPaths: [],
      };

      const deletionResult = await result.current.mutateAsync(params);

      expect(deletionResult.collectionDeleted).toBe(false);
      expect(deletionResult.projectsUndeployed).toBe(1);
      expect(deletionResult.errors).toHaveLength(1);
      expect(deletionResult.errors[0]).toEqual({
        operation: 'collection_deletion',
        error: 'Permission denied',
      });
    });
  });

  describe('Cache Invalidation', () => {
    it('invalidates all relevant caches on success', async () => {
      mockedDeleteArtifact.mockResolvedValueOnce(undefined);

      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false },
          mutations: { retry: false },
        },
      });

      const invalidateQueriesSpy = jest.spyOn(queryClient, 'invalidateQueries');

      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      );

      const { result } = renderHook(() => useArtifactDeletion(), { wrapper });

      const params: DeletionParams = {
        artifact: mockArtifact,
        deleteFromCollection: true,
        deleteFromProjects: false,
        deleteDeployments: false,
        selectedProjectPaths: [],
        selectedDeploymentPaths: [],
      };

      await result.current.mutateAsync(params);

      // Wait for cache invalidation
      await waitFor(() => {
        expect(invalidateQueriesSpy).toHaveBeenCalled();
      });

      // Verify all relevant cache keys were invalidated
      expect(invalidateQueriesSpy).toHaveBeenCalledWith({ queryKey: ['artifacts'] });
      expect(invalidateQueriesSpy).toHaveBeenCalledWith({ queryKey: ['deployments'] });
      expect(invalidateQueriesSpy).toHaveBeenCalledWith({ queryKey: ['collections'] });
      expect(invalidateQueriesSpy).toHaveBeenCalledWith({ queryKey: ['projects'] });
    });

    it('invalidates cache even on partial success', async () => {
      const mockUndeployResponse = {
        success: true,
        message: 'Artifact undeployed successfully',
      };

      mockedDeleteArtifact.mockRejectedValueOnce(new Error('Failed'));
      mockedUndeployArtifact.mockResolvedValueOnce(mockUndeployResponse);

      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false },
          mutations: { retry: false },
        },
      });

      const invalidateQueriesSpy = jest.spyOn(queryClient, 'invalidateQueries');

      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      );

      const { result } = renderHook(() => useArtifactDeletion(), { wrapper });

      const params: DeletionParams = {
        artifact: mockArtifact,
        deleteFromCollection: true,
        deleteFromProjects: true,
        deleteDeployments: false,
        selectedProjectPaths: ['/path/1'],
        selectedDeploymentPaths: [],
      };

      await result.current.mutateAsync(params);

      // Cache should still be invalidated (partial success)
      await waitFor(() => {
        expect(invalidateQueriesSpy).toHaveBeenCalled();
      });
    });
  });

  describe('Combined Operations', () => {
    it('performs both collection deletion and project undeploy', async () => {
      const mockUndeployResponse = {
        success: true,
        message: 'Artifact undeployed successfully',
      };

      mockedDeleteArtifact.mockResolvedValueOnce(undefined);
      mockedUndeployArtifact.mockResolvedValue(mockUndeployResponse);

      const { result } = renderHook(() => useArtifactDeletion(), {
        wrapper: createWrapper(),
      });

      const params: DeletionParams = {
        artifact: mockArtifact,
        deleteFromCollection: true,
        deleteFromProjects: true,
        deleteDeployments: false,
        selectedProjectPaths: ['/path/1', '/path/2'],
        selectedDeploymentPaths: [],
      };

      const deletionResult = await result.current.mutateAsync(params);

      expect(mockedDeleteArtifact).toHaveBeenCalledTimes(1);
      expect(mockedUndeployArtifact).toHaveBeenCalledTimes(2);
      expect(deletionResult.collectionDeleted).toBe(true);
      expect(deletionResult.projectsUndeployed).toBe(2);
      expect(deletionResult.errors).toEqual([]);
    });

    it('skips operations when flags are false', async () => {
      const { result } = renderHook(() => useArtifactDeletion(), {
        wrapper: createWrapper(),
      });

      const params: DeletionParams = {
        artifact: mockArtifact,
        deleteFromCollection: false,
        deleteFromProjects: false,
        deleteDeployments: false,
        selectedProjectPaths: ['/path/1'],
        selectedDeploymentPaths: [],
      };

      const deletionResult = await result.current.mutateAsync(params);

      expect(mockedDeleteArtifact).not.toHaveBeenCalled();
      expect(mockedUndeployArtifact).not.toHaveBeenCalled();
      expect(deletionResult.collectionDeleted).toBe(false);
      expect(deletionResult.projectsUndeployed).toBe(0);
      expect(deletionResult.errors).toEqual([]);
    });
  });

  describe('Error Object Handling', () => {
    it('handles non-Error objects in rejection', async () => {
      // Mock rejection with string instead of Error
      mockedUndeployArtifact.mockRejectedValueOnce('Something went wrong');

      const { result } = renderHook(() => useArtifactDeletion(), {
        wrapper: createWrapper(),
      });

      const params: DeletionParams = {
        artifact: mockArtifact,
        deleteFromCollection: false,
        deleteFromProjects: true,
        deleteDeployments: false,
        selectedProjectPaths: ['/path/1'],
        selectedDeploymentPaths: [],
      };

      await expect(result.current.mutateAsync(params)).rejects.toThrow(
        /All deletion operations failed/
      );
    });

    it('handles undefined error message gracefully', async () => {
      // Mock rejection with object without message
      const errorWithoutMessage = { code: 'ERR_UNKNOWN' };
      mockedUndeployArtifact.mockRejectedValueOnce(errorWithoutMessage);

      const { result } = renderHook(() => useArtifactDeletion(), {
        wrapper: createWrapper(),
      });

      const params: DeletionParams = {
        artifact: mockArtifact,
        deleteFromCollection: false,
        deleteFromProjects: true,
        deleteDeployments: false,
        selectedProjectPaths: ['/path/1'],
        selectedDeploymentPaths: [],
      };

      // Should throw since all operations failed, but check error contains "Unknown error"
      try {
        await result.current.mutateAsync(params);
        fail('Should have thrown error');
      } catch (error) {
        expect(error).toBeInstanceOf(Error);
        const errorMessage = (error as Error).message;
        expect(errorMessage).toContain('Unknown error');
      }
    });
  });
});
