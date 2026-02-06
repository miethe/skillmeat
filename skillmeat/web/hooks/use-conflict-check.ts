/**
 * Unified conflict check hook for sync operations
 *
 * Provides pre-operation conflict detection for Pull, Push, and Deploy workflows.
 * Routes to the appropriate diff API endpoint based on direction and computes
 * derived state (hasChanges, hasConflicts, targetHasChanges) for the confirmation
 * dialog and merge button gating.
 *
 * Direction routing:
 * - 'deploy': GET /artifacts/{id}/diff?project_path=... (collection vs project)
 * - 'push':   GET /artifacts/{id}/diff?project_path=... (collection vs project, reverse perspective)
 * - 'pull':   GET /artifacts/{id}/upstream-diff         (source vs collection)
 */

import { useQuery } from '@tanstack/react-query';
import { apiRequest } from '@/lib/api';
import type { ArtifactDiffResponse } from '@/sdk/models/ArtifactDiffResponse';
import type { ArtifactUpstreamDiffResponse } from '@/sdk/models/ArtifactUpstreamDiffResponse';
import type { FileDiff } from '@/sdk/models/FileDiff';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Sync direction for conflict checking */
export type ConflictCheckDirection = 'deploy' | 'push' | 'pull';

/** Options for the conflict check hook */
export interface ConflictCheckOptions {
  /** Project path for deploy/push directions (ignored for pull) */
  projectPath?: string;
  /** Whether the query should execute. Defaults to true. */
  enabled?: boolean;
  /** Collection name for scoped queries */
  collection?: string;
}

/** Union of both diff response shapes that this hook can return */
export type ConflictCheckDiffData = ArtifactDiffResponse | ArtifactUpstreamDiffResponse;

/** Return type of the useConflictCheck hook */
export interface ConflictCheckResult {
  /** Raw diff response from the API (undefined while loading or on error) */
  diffData: ConflictCheckDiffData | undefined;
  /** Whether any file changes were detected in the diff */
  hasChanges: boolean;
  /** Whether conflicting changes exist (both sides modified the same files) */
  hasConflicts: boolean;
  /**
   * Whether the target side has modifications/additions.
   * Gates the merge button -- if the target has no changes, merge is not applicable.
   *
   * - deploy: target = project (project-side modifications)
   * - push: target = collection (collection-side modifications relative to project)
   * - pull: target = collection (collection-side modifications relative to upstream)
   */
  targetHasChanges: boolean;
  /** Whether the query is currently loading */
  isLoading: boolean;
  /** Error from the query, if any */
  error: Error | null;
}

// ---------------------------------------------------------------------------
// Query key factory
// ---------------------------------------------------------------------------

export const conflictCheckKeys = {
  all: ['conflict-check'] as const,
  check: (direction: ConflictCheckDirection, artifactId: string | number, projectPath?: string) =>
    [...conflictCheckKeys.all, direction, artifactId, projectPath] as const,
};

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/**
 * Compute whether the target side of a diff has meaningful changes.
 *
 * For deploy/push (ArtifactDiffResponse), the diff compares collection vs project.
 * - deploy target = project: files with status 'modified' or 'deleted' indicate
 *   the project has diverged (project has changes relative to collection).
 * - push target = collection: files with status 'modified' or 'added' indicate
 *   the collection has changes to push.
 *
 * For pull (ArtifactUpstreamDiffResponse), the diff compares source vs collection.
 * - pull target = collection: files with status 'modified' or 'added' indicate
 *   the collection has local modifications that could conflict with upstream.
 *
 * When change_origin is available on files, we use it for more precise detection:
 * - deploy: target has changes when any file has change_origin 'local' or 'both'
 * - push: target has changes when any file has change_origin 'upstream' or 'both'
 *   (from the project's perspective, collection is "upstream")
 * - pull: target has changes when any file has change_origin 'local' or 'both'
 */
function computeTargetHasChanges(
  direction: ConflictCheckDirection,
  files: Array<FileDiff>
): boolean {
  if (!files || files.length === 0) return false;

  // Check if any files have change_origin metadata (from the sync types)
  const hasChangeOrigin = files.some(
    (f) => (f as FileDiff & { change_origin?: string }).change_origin != null
  );

  if (hasChangeOrigin) {
    // Use change_origin for precise detection
    return files.some((f) => {
      const origin = (f as FileDiff & { change_origin?: string }).change_origin;
      switch (direction) {
        case 'deploy':
          // Target is project; local changes mean project was modified
          return origin === 'local' || origin === 'both';
        case 'push':
          // Target is collection; from diff perspective, collection changes
          // appear as 'upstream' since diff endpoint compares collection→project
          return origin === 'upstream' || origin === 'both';
        case 'pull':
          // Target is collection; local modifications relative to upstream source
          return origin === 'local' || origin === 'both';
        default:
          return false;
      }
    });
  }

  // Fallback: use file status when change_origin is not available
  return files.some((f) => {
    switch (direction) {
      case 'deploy':
        // For deploy, target (project) has changes if files show modifications
        // 'deleted' means the project has a file that collection doesn't
        // 'modified' means project version differs
        return f.status === 'modified' || f.status === 'deleted';
      case 'push':
        // For push, target (collection) has changes if files are modified or added
        return f.status === 'modified' || f.status === 'added';
      case 'pull':
        // For pull, target (collection) has local changes
        return f.status === 'modified' || f.status === 'added';
      default:
        return false;
    }
  });
}

/**
 * Compute whether there are conflicts (both sides modified same files).
 *
 * Uses change_origin 'both' when available; otherwise infers from summary.
 */
function computeHasConflicts(diffData: ConflictCheckDiffData): boolean {
  const files = diffData.files;

  // Check for explicit conflict markers via change_origin
  const hasConflict = files.some(
    (f) => (f as FileDiff & { change_origin?: string }).change_origin === 'both'
  );
  if (hasConflict) return true;

  // Check summary for conflict count (both response types have summary: Record<string, number>)
  if (diffData.summary && typeof diffData.summary === 'object') {
    const conflicts = (diffData.summary as Record<string, number>)['conflicts'];
    if (conflicts != null && conflicts > 0) return true;
  }

  return false;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Pre-operation conflict check for unified sync workflow.
 *
 * Routes to the appropriate diff API based on direction:
 * - deploy/push: `GET /artifacts/{id}/diff?project_path=...`
 * - pull: `GET /artifacts/{id}/upstream-diff`
 *
 * Returns derived state for the DiffViewer confirmation dialog:
 * - `hasChanges`: whether any diff was found
 * - `hasConflicts`: whether both sides have changes (merge required)
 * - `targetHasChanges`: gates the merge button
 *
 * @param direction - The sync direction ('deploy', 'push', or 'pull')
 * @param artifactId - The artifact identifier
 * @param opts - Optional configuration (projectPath, enabled, collection)
 * @returns Conflict check result with diff data and derived flags
 *
 * @example
 * ```tsx
 * const { diffData, hasChanges, hasConflicts, targetHasChanges, isLoading } =
 *   useConflictCheck('deploy', artifact.id, {
 *     projectPath: '/path/to/project',
 *     enabled: isDialogOpen,
 *   });
 *
 * if (hasConflicts) {
 *   // Show conflict resolution UI
 * }
 *
 * <Button disabled={!targetHasChanges}>Merge</Button>
 * ```
 */
export function useConflictCheck(
  direction: ConflictCheckDirection,
  artifactId: string | number,
  opts?: ConflictCheckOptions
): ConflictCheckResult {
  const { projectPath, enabled = true, collection } = opts ?? {};

  // For deploy/push, projectPath is required for the query to execute
  const needsProjectPath = direction === 'deploy' || direction === 'push';
  const queryEnabled = enabled && !!artifactId && (!needsProjectPath || !!projectPath);

  const {
    data: diffData,
    isLoading,
    error,
  } = useQuery<ConflictCheckDiffData>({
    queryKey: conflictCheckKeys.check(direction, artifactId, projectPath),

    queryFn: async (): Promise<ConflictCheckDiffData> => {
      const encodedId = encodeURIComponent(String(artifactId));

      if (direction === 'pull') {
        // Upstream diff: source vs collection
        const params = new URLSearchParams();
        if (collection) {
          params.set('collection', collection);
        }
        const queryString = params.toString();
        return apiRequest<ArtifactUpstreamDiffResponse>(
          `/artifacts/${encodedId}/upstream-diff${queryString ? `?${queryString}` : ''}`
        );
      }

      // Deploy/push: collection vs project diff
      const params = new URLSearchParams();
      if (projectPath) {
        params.set('project_path', projectPath);
      }
      if (collection) {
        params.set('collection', collection);
      }
      const queryString = params.toString();
      return apiRequest<ArtifactDiffResponse>(
        `/artifacts/${encodedId}/diff${queryString ? `?${queryString}` : ''}`
      );
    },

    enabled: queryEnabled,
    staleTime: 30_000, // 30 seconds (interactive/monitoring)
    retry: false,
  });

  // Derive computed state from response data
  const hasChanges = diffData?.has_changes ?? false;
  const hasConflicts = diffData ? computeHasConflicts(diffData) : false;
  const targetHasChanges = diffData ? computeTargetHasChanges(direction, diffData.files) : false;

  return {
    diffData,
    hasChanges,
    hasConflicts,
    targetHasChanges,
    isLoading,
    error: error as Error | null,
  };
}
