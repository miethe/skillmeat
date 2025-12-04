/**
 * React Query hook for project-specific artifact discovery
 *
 * This hook provides discovery capabilities for a single project's .claude/ directory,
 * as opposed to the collection-wide discovery hook.
 */

import { useState, useEffect, useCallback } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiRequest } from '@/lib/api';
import {
  loadSkipPrefs,
  saveSkipPrefs,
  clearSkipPrefs,
  buildArtifactKey,
} from '@/lib/skip-preferences';
import type {
  DiscoveryResult,
  BulkImportRequest,
  BulkImportResult,
  SkipPreference,
} from '@/types/discovery';

/**
 * Hook for discovering artifacts in a specific project's .claude/ directory.
 *
 * @param projectPath - The filesystem path to the project
 * @param projectId - The unique project identifier (used for skip preferences)
 * @returns Discovery state and functions
 */
export function useProjectDiscovery(projectPath: string | undefined, projectId?: string) {
  const queryClient = useQueryClient();

  // Skip preferences state
  const [skipPrefs, setSkipPrefs] = useState<SkipPreference[]>([]);

  // Load skip preferences when project changes
  useEffect(() => {
    if (projectId) {
      const prefs = loadSkipPrefs(projectId);
      setSkipPrefs(prefs);
    } else {
      setSkipPrefs([]);
    }
  }, [projectId]);

  // Encode the project path for URL
  const encodedPath = projectPath ? encodeURIComponent(projectPath) : '';

  // Discovery query - only runs when manually triggered
  const discoveryQuery = useQuery({
    queryKey: ['artifacts', 'discover', 'project', projectPath],
    queryFn: async (): Promise<DiscoveryResult> => {
      if (!projectPath) {
        return { discovered_count: 0, importable_count: 0, artifacts: [], errors: [], scan_duration_ms: 0 };
      }

      const result = await apiRequest<DiscoveryResult>(
        `/artifacts/discover/project/${encodedPath}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        }
      );
      return result;
    },
    enabled: false, // Manual trigger only
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 1,
  });

  // Bulk import mutation with skip list integration
  const bulkImportMutation = useMutation({
    mutationFn: async (request: BulkImportRequest): Promise<BulkImportResult> => {
      const params = projectId ? `?project_id=${encodeURIComponent(projectId)}` : '';

      return await apiRequest<BulkImportResult>(`/artifacts/discover/import${params}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });
    },
    onSuccess: async (_result, request) => {
      // Save new skip preferences to LocalStorage after successful import
      if (projectId && request.skip_list && request.skip_list.length > 0) {
        const newPrefs = request.skip_list.map((key) => ({
          artifact_key: key,
          skip_reason: 'Skipped during import',
          added_date: new Date().toISOString(),
        }));

        // Merge with existing preferences, avoiding duplicates
        const combined = [...skipPrefs];
        for (const newPref of newPrefs) {
          if (!combined.some((p) => p.artifact_key === newPref.artifact_key)) {
            combined.push(newPref);
          }
        }

        saveSkipPrefs(projectId, combined);
        setSkipPrefs(combined);
      }

      // AWAIT all invalidations to ensure cache is fresh before mutation completes
      await queryClient.invalidateQueries({ queryKey: ['artifacts', 'discover', 'project', projectPath] });
      await queryClient.invalidateQueries({ queryKey: ['artifacts'] });
      if (projectId) {
        // Only invalidate the specific project detail, not the entire projects list
        await queryClient.invalidateQueries({ queryKey: ['projects', 'detail', projectId] });
      }
    },
  });

  // Check if an artifact is marked as skipped
  const isArtifactSkipped = useCallback(
    (artifactType: string, artifactName: string): boolean => {
      const key = buildArtifactKey(artifactType, artifactName);
      return skipPrefs.some((p) => p.artifact_key === key);
    },
    [skipPrefs]
  );

  // Clear all skip preferences for this project
  const clearSkips = useCallback(() => {
    if (projectId) {
      clearSkipPrefs(projectId);
      setSkipPrefs([]);
    }
  }, [projectId]);

  return {
    discoveredArtifacts: discoveryQuery.data?.artifacts || [],
    discoveredCount: discoveryQuery.data?.discovered_count || 0,
    importableCount: discoveryQuery.data?.importable_count || 0,
    isDiscovering: discoveryQuery.isFetching,
    discoverError: discoveryQuery.error,
    refetchDiscovery: discoveryQuery.refetch,
    bulkImport: bulkImportMutation.mutateAsync,
    isImporting: bulkImportMutation.isPending,
    // Skip preference integration (DIS-3.6)
    skipPrefs,
    isArtifactSkipped,
    clearSkips,
  };
}
