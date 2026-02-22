'use client';

import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, GitMerge } from 'lucide-react';
import type { Artifact } from '@/types/artifact';
import type { ArtifactDiffResponse } from '@/sdk/models/ArtifactDiffResponse';
import type { ArtifactUpstreamDiffResponse } from '@/sdk/models/ArtifactUpstreamDiffResponse';
import type { FileDiff } from '@/sdk/models/FileDiff';
import { useToast, useDriftDismissal } from '@/hooks';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { apiRequest } from '@/lib/api';
import type { ArtifactSyncResponse } from '@/sdk/models/ArtifactSyncResponse';
import { hasValidUpstreamSource, hasSourceLink } from '@/lib/sync-utils';
import { markStart, markEnd } from '@/lib/perf-marks';

// Phase 1 components
import { ArtifactFlowBanner } from './artifact-flow-banner';
import { ComparisonSelector, type ComparisonScope } from './comparison-selector';
import { DriftAlertBanner, type DriftStatus } from './drift-alert-banner';
import { SyncActionsFooter } from './sync-actions-footer';
import { SkillMemberDrift } from './skill-member-drift';

// Existing components
import { DiffViewer } from '@/components/entity/diff-viewer';
import { MergeWorkflow } from '@/components/entity/merge-workflow';
import { SyncDialog } from '@/components/collection/sync-dialog';
import { SyncConfirmationDialog } from './sync-confirmation-dialog';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

// ============================================================================
// Types
// ============================================================================

export interface SyncStatusTabProps {
  entity: Artifact;
  mode: 'collection' | 'project';
  projectPath?: string;
  onClose: () => void;
}

interface PendingAction {
  type: 'pull' | 'push' | 'deploy' | 'merge';
  filePath?: string;
  direction?: 'upstream' | 'downstream';
}

/** Response from the deploy API when using strategy='merge' (SYNC-A03) */
interface DeployMergeResponse {
  success: boolean;
  message: string;
  error_message?: string;
  strategy?: string;
  merge_details?: {
    files_copied: number;
    files_skipped: number;
    files_preserved: number;
    conflicts: number;
    file_actions: Array<{ file_path: string; action: string; detail?: string }>;
  };
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Compute drift status from diff data
 */
function computeDriftStatus(
  diffData: ArtifactDiffResponse | ArtifactUpstreamDiffResponse | undefined
): DriftStatus {
  if (!diffData) return 'none';
  if (!diffData.has_changes) return 'none';

  // Check if any file has conflicts (basic heuristic: look for conflict markers)
  const hasConflicts = diffData.files.some((f: FileDiff) => f.unified_diff?.includes('<<<<<<< '));

  if (hasConflicts) return 'conflict';
  return 'modified';
}

/**
 * Get left label for DiffViewer based on comparison scope
 */
function getLeftLabel(scope: ComparisonScope): string {
  switch (scope) {
    case 'collection-vs-project':
      return 'Collection';
    case 'source-vs-collection':
      return 'Source';
    case 'source-vs-project':
      return 'Source';
    default:
      return 'Before';
  }
}

/**
 * Get right label for DiffViewer based on comparison scope
 */
function getRightLabel(scope: ComparisonScope): string {
  switch (scope) {
    case 'collection-vs-project':
      return 'Project';
    case 'source-vs-collection':
      return 'Collection';
    case 'source-vs-project':
      return 'Project';
    default:
      return 'After';
  }
}

// ============================================================================
// Loading Skeleton
// ============================================================================

/**
 * SyncStatusTabSkeleton - Loading state matching the simplified layout
 *
 * Mimics the simplified structure:
 * - Top: ArtifactFlowBanner
 * - Middle: ComparisonSelector + DiffViewer (full width)
 * - Bottom: Actions Footer
 */
function SyncStatusTabSkeleton() {
  return (
    <div className="flex h-full flex-col">
      {/* Top: Flow Banner Skeleton */}
      <div className="flex-shrink-0 border-b p-4">
        <Skeleton className="h-24 w-full" />
      </div>

      {/* Middle: Full Width Content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Comparison Selector Skeleton */}
        <div className="flex-shrink-0 space-y-3 border-b p-4">
          <Skeleton className="h-10 w-64" />
          <Skeleton className="h-12 w-full" />
        </div>

        {/* Diff Content Skeleton */}
        <div className="min-h-0 flex-1 space-y-2 overflow-auto p-6">
          {[...Array(12)].map((_, i) => (
            <Skeleton key={i} className="h-5" style={{ width: `${60 + Math.random() * 30}%` }} />
          ))}
        </div>
      </div>

      {/* Bottom: Actions Footer Skeleton */}
      <div className="flex-shrink-0 border-t p-4">
        <div className="flex items-center justify-between">
          <div className="flex gap-2">
            <Skeleton className="h-9 w-32" />
            <Skeleton className="h-9 w-32" />
          </div>
          <div className="flex gap-2">
            <Skeleton className="h-9 w-20" />
            <Skeleton className="h-9 w-20" />
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * SyncStatusTab - Orchestration component for sync status UI
 *
 * Features:
 * - 3-tier flow visualization (Source → Collection → Project)
 * - Comparison scope selector (source-vs-collection, collection-vs-project, source-vs-project)
 * - Side-by-side diff viewer (full width)
 * - Drift status alerts with actions
 * - Sync actions footer with batch operations
 *
 * Layout:
 * ```
 * ┌────────────────────────────────────────────┐
 * │  ArtifactFlowBanner                        │
 * ├────────────────────────────────────────────┤
 * │  ComparisonSelector                        │
 * │  DriftAlertBanner                          │
 * │  DiffViewer (full width)                   │
 * ├────────────────────────────────────────────┤
 * │  SyncActionsFooter                         │
 * └────────────────────────────────────────────┘
 * ```
 *
 * @example
 * ```tsx
 * <SyncStatusTab
 *   entity={entity}
 *   mode="project"
 *   projectPath="/path/to/project"
 *   onClose={() => closeModal()}
 * />
 * ```
 */
export function SyncStatusTab({ entity, mode, projectPath, onClose }: SyncStatusTabProps) {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // ============================================================================
  // State
  // ============================================================================

  // Strict upstream check — must satisfy hasValidUpstreamSource() conditions (github origin,
  // tracking enabled, valid remote source). Aligns scope availability with query gate so
  // tabs never appear available when the upstream query will never fire.
  const hasValidUpstream = hasValidUpstreamSource(entity);

  // Display-only source check — less strict than hasValidUpstream.
  // Used for banner sourceInfo and scope tab visibility; does NOT gate query execution.
  const hasSource = hasSourceLink(entity);

  const [comparisonScope, setComparisonScope] = useState<ComparisonScope>(
    mode === 'project'
      ? 'collection-vs-project'
      : hasSource && !projectPath
        ? 'source-vs-collection'
        : 'collection-vs-project'
  );
  const [pendingActions] = useState<PendingAction[]>([]);
  const [showSyncDialog, setShowSyncDialog] = useState(false);

  // Merge workflow state (Phase 3: SYNC-A03)
  const [showMergeWorkflow, setShowMergeWorkflow] = useState(false);
  const [mergeDirection, setMergeDirection] = useState<'upstream' | 'downstream'>('downstream');

  // Track whether user has manually changed the comparison scope.
  // Prevents the smart-default effect from overriding an intentional selection.
  const userHasChangedScope = useRef(false);

  // Smart default: when projectPath becomes available, switch to the faster local
  // comparison (collection-vs-project) if the user hasn't manually chosen a scope yet.
  useEffect(() => {
    if (projectPath && !userHasChangedScope.current && comparisonScope === 'source-vs-collection') {
      setComparisonScope('collection-vs-project');
    }
  }, [projectPath, comparisonScope]);

  // ============================================================================
  // Queries
  // ============================================================================

  // Scope-aware diff loading (TASK-5.3):
  // The active (primary) comparison scope query loads immediately.
  // Secondary scope queries are deferred — they only become enabled after the
  // primary scope's query has successfully returned data. This ensures the user
  // sees meaningful content for their selected scope as fast as possible, while
  // background-prefetching the other scopes so switching feels instant.
  const isUpstreamPrimary = comparisonScope === 'source-vs-collection';
  const isProjectPrimary = comparisonScope === 'collection-vs-project';
  const isSourceProjectPrimary = comparisonScope === 'source-vs-project';

  // Upstream diff (source vs collection).
  // Fires immediately when it is the active scope.
  // Also fires immediately when source-vs-project is active (both require upstream data).
  // Deferred when collection-vs-project is active — enabled after project diff loads.
  const {
    data: upstreamDiff,
    isLoading: upstreamLoading,
    isSuccess: upstreamSuccess,
    error: upstreamError,
  } = useQuery<ArtifactUpstreamDiffResponse>({
    queryKey: ['upstream-diff', entity.id, entity.collection],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (entity.collection) {
        params.set('collection', entity.collection);
      }
      const queryString = params.toString();
      return await apiRequest<ArtifactUpstreamDiffResponse>(
        `/artifacts/${encodeURIComponent(entity.id)}/upstream-diff${queryString ? `?${queryString}` : ''}`
      );
    },
    enabled:
      !!entity.id &&
      entity.collection !== 'discovered' &&
      hasValidUpstreamSource(entity) &&
      // Enable immediately when this scope or source-vs-project is active (both require upstream);
      // defer only when collection-vs-project is active (equivalent to: !isProjectPrimary)
      (isUpstreamPrimary || isSourceProjectPrimary),
    staleTime: 30_000, // 30 sec interactive: diff data is expensive; reuse within TTL on reopen/switch
    gcTime: 300_000,   // 5 min: keep in cache after unmount so reopen flows hit cache
    retry: false,
  });

  // Project diff (collection vs project).
  // Fires immediately when it is the active scope.
  // Deferred when source-vs-collection or source-vs-project is active — enabled after
  // upstream diff loads (background prefetch once primary content is rendered).
  const {
    data: projectDiff,
    isLoading: projectLoading,
    isSuccess: projectSuccess,
    error: projectError,
  } = useQuery<ArtifactDiffResponse>({
    queryKey: ['project-diff', entity.id, projectPath],
    queryFn: async () => {
      const params = new URLSearchParams({ project_path: projectPath! });
      return await apiRequest<ArtifactDiffResponse>(
        `/artifacts/${encodeURIComponent(entity.id)}/diff?${params}`
      );
    },
    enabled:
      !!entity.id &&
      !!projectPath &&
      entity.collection !== 'discovered' &&
      // Enable immediately for primary scope; defer for upstream-based scopes (secondary)
      (isProjectPrimary || upstreamSuccess),
    staleTime: 30_000, // 30 sec interactive: diff data is expensive; reuse within TTL on reopen/switch
    gcTime: 300_000,   // 5 min: keep in cache after unmount so reopen flows hit cache
  });

  // Source-project diff (source vs project, bypassing collection).
  // This is the most expensive query. Load immediately when it is the active scope;
  // background-prefetch after EITHER upstream or project scope has successfully loaded.
  const primaryScopeLoaded = upstreamSuccess || projectSuccess;
  const {
    data: sourceProjectDiff,
    isLoading: sourceProjectLoading,
    error: sourceProjectError,
  } = useQuery<ArtifactDiffResponse>({
    queryKey: ['source-project-diff', entity.id, projectPath, entity.collection],
    queryFn: async () => {
      const params = new URLSearchParams({ project_path: projectPath! });
      if (entity.collection) {
        params.set('collection', entity.collection);
      }
      return await apiRequest<ArtifactDiffResponse>(
        `/artifacts/${encodeURIComponent(entity.id)}/source-project-diff?${params}`
      );
    },
    enabled:
      !!entity.id &&
      !!projectPath &&
      entity.collection !== 'discovered' &&
      hasValidUpstreamSource(entity) &&
      // Active scope loads immediately; otherwise background-prefetch after primary data lands
      (isSourceProjectPrimary || primaryScopeLoaded),
    staleTime: 30_000, // 30 sec interactive: most expensive diff query; reuse within TTL on reopen/switch
    gcTime: 300_000,   // 5 min: keep in cache after unmount so reopen flows hit cache
    retry: false,
  });

  // ============================================================================
  // Mutations
  // ============================================================================

  // Sync mutation (pull from source)
  const syncMutation = useMutation({
    mutationFn: async () => {
      return await apiRequest<ArtifactSyncResponse>(
        `/artifacts/${encodeURIComponent(entity.id)}/sync`,
        {
          method: 'POST',
          body: JSON.stringify({
            // Empty body syncs from upstream source (not project)
            // project_path is omitted to trigger upstream sync
          }),
        }
      );
    },
    onSuccess: (data: ArtifactSyncResponse) => {
      queryClient.invalidateQueries({ queryKey: ['artifacts'] });
      queryClient.invalidateQueries({ queryKey: ['deployments'] });
      queryClient.invalidateQueries({ queryKey: ['upstream-diff', entity.id, entity.collection] });
      queryClient.invalidateQueries({ queryKey: ['project-diff', entity.id] });
      queryClient.invalidateQueries({ queryKey: ['source-project-diff', entity.id] });
      queryClient.invalidateQueries({ queryKey: ['collections'] });
      if (data.conflicts && data.conflicts.length > 0) {
        toast({
          title: 'Pull completed with conflicts',
          description: `${data.conflicts.length} conflict(s) detected`,
          variant: 'destructive',
        });
      } else {
        toast({
          title: 'Sync Successful',
          description: data.message || 'Pulled latest changes from source',
        });
      }
    },
    onError: (error: Error) => {
      toast({
        title: 'Sync Failed',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  // Deploy mutation (deploy to project with overwrite)
  const deployMutation = useMutation({
    mutationFn: async () => {
      const params = new URLSearchParams();
      if (entity.collection) {
        params.set('collection', entity.collection);
      }
      const queryString = params.toString();
      const url = `/artifacts/${encodeURIComponent(entity.id)}/deploy${queryString ? `?${queryString}` : ''}`;
      return await apiRequest<{ success: boolean; message: string; error_message?: string }>(url, {
        method: 'POST',
        body: JSON.stringify({
          project_path: projectPath,
          overwrite: true, // User confirmed via dialog
        }),
      });
    },
    onSuccess: (data) => {
      if (!data.success) {
        toast({
          title: 'Deploy Failed',
          description: data.error_message || data.message || 'Deployment was not completed',
          variant: 'destructive',
        });
        return;
      }
      queryClient.invalidateQueries({ queryKey: ['project-diff', entity.id] });
      queryClient.invalidateQueries({ queryKey: ['upstream-diff', entity.id, entity.collection] });
      queryClient.invalidateQueries({ queryKey: ['source-project-diff', entity.id] });
      queryClient.invalidateQueries({ queryKey: ['artifacts'] });
      queryClient.invalidateQueries({ queryKey: ['deployments'] });
      toast({
        title: 'Deploy Successful',
        description: `Deployed ${entity.name} to project`,
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Deploy Failed',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  // Take upstream mutation (overwrite with upstream/collection version)
  const takeUpstreamMutation = useMutation({
    mutationFn: async () => {
      // Strategy depends on comparison scope
      if (comparisonScope === 'source-vs-collection') {
        // Pull from source to collection
        return syncMutation.mutateAsync();
      } else {
        // Deploy from collection to project (overwrite)
        const params = new URLSearchParams();
        if (entity.collection) {
          params.set('collection', entity.collection);
        }
        const queryString = params.toString();
        const url = `/artifacts/${encodeURIComponent(entity.id)}/deploy${queryString ? `?${queryString}` : ''}`;
        return await apiRequest<{ success: boolean; message: string; error_message?: string }>(
          url,
          {
            method: 'POST',
            body: JSON.stringify({
              project_path: projectPath,
              overwrite: true,
            }),
          }
        );
      }
    },
    onSuccess: (data) => {
      // Check if deploy response indicates failure (deploy returns { success, message, error_message })
      if (data && typeof data === 'object' && 'success' in data) {
        const deployData = data as { success: boolean; message: string; error_message?: string };
        if (!deployData.success) {
          toast({
            title: 'Failed to Apply Changes',
            description:
              deployData.error_message || deployData.message || 'Operation was not completed',
            variant: 'destructive',
          });
          return;
        }
      }
      queryClient.invalidateQueries({ queryKey: ['upstream-diff', entity.id, entity.collection] });
      queryClient.invalidateQueries({ queryKey: ['project-diff', entity.id] });
      queryClient.invalidateQueries({ queryKey: ['source-project-diff', entity.id] });
      toast({
        title: 'Changes Accepted',
        description: 'Upstream version applied successfully',
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Failed to Take Upstream',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  // Keep local mutation (acknowledge local changes are intentional)
  const keepLocalMutation = useMutation({
    mutationFn: async () => {
      // This is a local UI acknowledgment - no API call needed.
      // The drift banner dismissal is handled by useDriftDismissal hook.
    },
    onSuccess: () => {
      // Invalidate drift-related queries so UI re-evaluates after dismissal
      queryClient.invalidateQueries({ queryKey: ['upstream-diff', entity.id, entity.collection] });
      queryClient.invalidateQueries({ queryKey: ['project-diff', entity.id] });
      queryClient.invalidateQueries({ queryKey: ['source-project-diff', entity.id] });
      toast({
        title: 'Local Version Kept',
        description: 'Drift dismissed - local changes preserved',
      });
    },
  });

  // Push to collection mutation (push project changes back to collection)
  const pushToCollectionMutation = useMutation({
    mutationFn: async () => {
      if (!projectPath) throw new Error('No project path available');
      return await apiRequest<ArtifactSyncResponse>(
        `/artifacts/${encodeURIComponent(entity.id)}/sync`,
        {
          method: 'POST',
          body: JSON.stringify({
            project_path: projectPath,
            force: false,
            strategy: 'theirs',
          }),
        }
      );
    },
    onSuccess: (data: ArtifactSyncResponse) => {
      queryClient.invalidateQueries({ queryKey: ['artifacts'] });
      queryClient.invalidateQueries({ queryKey: ['deployments'] });
      queryClient.invalidateQueries({ queryKey: ['upstream-diff', entity.id, entity.collection] });
      queryClient.invalidateQueries({ queryKey: ['project-diff', entity.id] });
      queryClient.invalidateQueries({ queryKey: ['source-project-diff', entity.id] });
      queryClient.invalidateQueries({ queryKey: ['collections'] });
      if (data.conflicts && data.conflicts.length > 0) {
        toast({
          title: 'Push completed with conflicts',
          description: `${data.conflicts.length} conflict(s) detected`,
          variant: 'destructive',
        });
      } else {
        toast({
          title: 'Push Successful',
          description: data.message || 'Project changes pushed to collection',
        });
      }
    },
    onError: (error: Error) => {
      toast({
        title: 'Push Failed',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  // Deploy-merge mutation: attempts deploy with strategy='merge', routes to
  // MergeWorkflow if conflicts are detected (SYNC-A03)
  const deployMergeMutation = useMutation({
    mutationFn: async () => {
      const params = new URLSearchParams();
      if (entity.collection) {
        params.set('collection', entity.collection);
      }
      const queryString = params.toString();
      const url = `/artifacts/${encodeURIComponent(entity.id)}/deploy${queryString ? `?${queryString}` : ''}`;
      return await apiRequest<DeployMergeResponse>(url, {
        method: 'POST',
        body: JSON.stringify({
          project_path: projectPath,
          overwrite: false,
          strategy: 'merge',
        }),
      });
    },
    onSuccess: (data) => {
      if (!data.success) {
        toast({
          title: 'Merge Deploy Failed',
          description: data.error_message || data.message || 'Merge deployment was not completed',
          variant: 'destructive',
        });
        return;
      }

      // Check if merge had conflicts — route to full MergeWorkflow
      const hasConflicts = data.merge_details && data.merge_details.conflicts > 0;
      if (hasConflicts) {
        toast({
          title: 'Conflicts Detected',
          description: `${data.merge_details!.conflicts} file(s) have conflicting changes. Opening merge workflow.`,
        });
        setMergeDirection('downstream');
        setShowMergeWorkflow(true);
        return;
      }

      // No conflicts — merge succeeded cleanly
      queryClient.invalidateQueries({ queryKey: ['project-diff', entity.id] });
      queryClient.invalidateQueries({ queryKey: ['upstream-diff', entity.id, entity.collection] });
      queryClient.invalidateQueries({ queryKey: ['source-project-diff', entity.id] });
      queryClient.invalidateQueries({ queryKey: ['artifacts'] });
      queryClient.invalidateQueries({ queryKey: ['deployments'] });
      toast({
        title: 'Merge Deploy Successful',
        description: data.message || `Merged ${entity.name} to project`,
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Merge Deploy Failed',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  // ============================================================================
  // Event Handlers
  // ============================================================================

  const [showPushConfirm, setShowPushConfirm] = useState(false);
  const [showPullConfirm, setShowPullConfirm] = useState(false);
  const [showDeployConfirm, setShowDeployConfirm] = useState(false);

  // Performance instrumentation: track SyncStatusTab mount and time-to-first-data
  useEffect(() => {
    markStart('sync-tab.mount');
    markStart('sync-tab.first-data');
    return () => {
      markEnd('sync-tab.mount');
    };
  }, []);

  // Performance instrumentation: track when first comparison data arrives and renders
  const firstDataRendered = useRef(false);
  useEffect(() => {
    if (!firstDataRendered.current && (upstreamDiff || projectDiff || sourceProjectDiff)) {
      firstDataRendered.current = true;
      markEnd('sync-tab.activate');
      markEnd('sync-tab.first-data');
    }
  }, [upstreamDiff, projectDiff, sourceProjectDiff]);

  // Performance instrumentation: track comparison scope switches
  const prevScope = useRef(comparisonScope);
  useEffect(() => {
    if (prevScope.current !== comparisonScope) {
      markEnd(`sync-tab.scope.${prevScope.current}`);
      markStart(`sync-tab.scope.${comparisonScope}`);
      prevScope.current = comparisonScope;
    }
  }, [comparisonScope]);

  const handleComparisonChange = (scope: ComparisonScope) => {
    userHasChangedScope.current = true;
    markStart(`sync-tab.scope.${scope}`);
    setComparisonScope(scope);
  };

  const handlePullFromSource = useCallback(() => {
    setShowPullConfirm(true);
  }, []);

  const handleDeployToProject = useCallback(() => {
    if (!projectPath) {
      toast({ title: 'Error', description: 'No project path', variant: 'destructive' });
      return;
    }
    setShowDeployConfirm(true);
  }, [projectPath, toast]);

  const handleTakeUpstream = () => {
    takeUpstreamMutation.mutate();
  };

  const handleKeepLocal = () => {
    keepLocalMutation.mutate();
  };

  const handleMerge = () => {
    // Determine merge direction based on current comparison scope
    if (comparisonScope === 'source-vs-collection') {
      // Pull merge: source -> collection (use SyncDialog for upstream sync)
      setShowSyncDialog(true);
    } else {
      // Push or deploy merge: route to MergeWorkflow
      const direction = comparisonScope === 'collection-vs-project' ? 'downstream' : 'upstream';
      setMergeDirection(direction);
      setShowMergeWorkflow(true);
    }
  };

  const handlePushToCollection = useCallback(() => {
    if (!projectPath) {
      toast({ title: 'Error', description: 'No project path available', variant: 'destructive' });
      return;
    }
    setShowPushConfirm(true);
  }, [projectPath, toast]);

  const handleApplyActions = () => {
    if (pendingActions.length === 0) return;
    if (!projectPath) {
      toast({ title: 'Error', description: 'No project path available', variant: 'destructive' });
      return;
    }

    // Execute single-artifact mutations based on pending action types
    const pushActions = pendingActions.filter((a) => a.type === 'push');
    const pullActions = pendingActions.filter((a) => a.type === 'pull');

    if (pushActions.length > 0) {
      pushToCollectionMutation.mutate();
    }

    if (pullActions.length > 0) {
      syncMutation.mutate();
    }

    // Deploy actions go through the existing deploy mutation
    const deployActions = pendingActions.filter((a) => a.type === 'deploy');
    if (deployActions.length > 0) {
      deployMutation.mutate();
    }
  };

  const handleViewDiffs = () => {
    // Scroll to diff viewer - for now just a no-op
    // Could implement smooth scroll to diff section
  };

  // ============================================================================
  // Computed Values
  // ============================================================================

  // Current diff based on comparison scope
  const currentDiff = useMemo(() => {
    switch (comparisonScope) {
      case 'source-vs-collection':
        return upstreamDiff;
      case 'collection-vs-project':
        return projectDiff;
      case 'source-vs-project':
        return sourceProjectDiff;
      default:
        return projectDiff;
    }
  }, [comparisonScope, upstreamDiff, projectDiff, sourceProjectDiff]);

  // Drift status computed from current diff data
  const driftStatus = useMemo(() => {
    return computeDriftStatus(currentDiff);
  }, [currentDiff]);

  // Persistent drift dismissal (survives page refreshes, 24h expiry)
  const { isDismissed: isDriftDismissed, dismiss: dismissDrift } = useDriftDismissal({
    artifactId: entity.id,
    scope: comparisonScope,
    driftStatus,
  });

  // ============================================================================
  // Early Return: Discovered Artifacts
  // ============================================================================

  // Discovered artifacts are not in any collection yet - they need to be imported first
  // NOTE: This early return is placed AFTER all hooks to comply with React's rules of hooks
  if (entity.collection === 'discovered') {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <Alert className="max-w-md">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Sync status is not available for discovered artifacts. Import this artifact to your
            collection to enable sync tracking.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  // ============================================================================
  // Component Props
  // ============================================================================

  const bannerProps = {
    artifact: entity,
    sourceInfo: upstreamDiff
      ? {
          version: upstreamDiff.upstream_version,
          sha: upstreamDiff.upstream_version.slice(0, 7),
          hasUpdate: upstreamDiff.has_changes,
          source: upstreamDiff.upstream_source,
        }
      : hasSource
        ? {
            version: entity.source || 'unknown',
            sha: '...',
            hasUpdate: false,
            source: entity.source || '',
          }
        : null,
    collectionInfo: {
      version: entity.version || 'unknown',
      sha: entity.version?.slice(0, 7) || 'unknown',
    },
    projectInfo: projectDiff
      ? {
          version: entity.version || 'unknown',
          sha: entity.version?.slice(0, 7) || 'unknown',
          isModified: projectDiff.has_changes,
          projectPath: projectDiff.project_path,
        }
      : null,
    onPullFromSource: handlePullFromSource,
    onDeployToProject: handleDeployToProject,
    onPushToCollection: handlePushToCollection,
    isPulling: syncMutation.isPending,
    isDeploying: deployMutation.isPending,
    isPushing: pushToCollectionMutation.isPending,
  };

  const comparisonProps = {
    value: comparisonScope,
    onChange: handleComparisonChange,
    hasSource: hasSource,
    hasProject: !!projectPath,
  };

  const alertProps = {
    driftStatus,
    comparisonScope,
    summary: {
      added: currentDiff?.summary?.added || 0,
      modified: currentDiff?.summary?.modified || 0,
      deleted: currentDiff?.summary?.deleted || 0,
      unchanged: currentDiff?.summary?.unchanged || 0,
    },
    onViewDiffs: handleViewDiffs,
    onMerge: handleMerge,
    onTakeUpstream: handleTakeUpstream,
    onKeepLocal: handleKeepLocal,
    onDismiss: driftStatus !== 'none' ? dismissDrift : undefined,
  };

  // Scope-specific loading for the DiffViewer — show skeleton when the current scope's data is loading
  const isDiffLoading = useMemo(() => {
    switch (comparisonScope) {
      case 'source-vs-collection':
        return upstreamLoading;
      case 'collection-vs-project':
        return projectLoading;
      case 'source-vs-project':
        return sourceProjectLoading;
      default:
        return false;
    }
  }, [comparisonScope, upstreamLoading, projectLoading, sourceProjectLoading]);

  const diffProps = {
    files: currentDiff?.files || [],
    leftLabel: getLeftLabel(comparisonScope),
    rightLabel: getRightLabel(comparisonScope),
    isLoading: isDiffLoading,
  };

  const footerProps = {
    onPullCollectionUpdates: handlePullFromSource,
    onPushLocalChanges: handlePushToCollection,
    onMergeConflicts: handleMerge,
    onResolveAll: () => toast({ title: 'Coming Soon' }),
    onCancel: onClose,
    onApply: handleApplyActions,
    hasPendingActions: pendingActions.length > 0,
    hasConflicts: driftStatus === 'conflict',
    isApplying:
      syncMutation.isPending ||
      deployMutation.isPending ||
      takeUpstreamMutation.isPending ||
      keepLocalMutation.isPending ||
      pushToCollectionMutation.isPending,
  };

  // ============================================================================
  // Error & Loading States
  // ============================================================================

  // Determine if we have usable data
  const hasUpstreamData = !upstreamError && !!upstreamDiff;
  const hasProjectData = !projectError && !!projectDiff;
  const hasSourceProjectData = !sourceProjectError && !!sourceProjectDiff;
  const canShowAnyData = hasUpstreamData || hasProjectData || hasSourceProjectData;

  // Only show loading if we're loading AND don't have any data yet
  const isLoading = (upstreamLoading || projectLoading || sourceProjectLoading) && !canShowAnyData;

  // Only show blocking error if BOTH queries failed or if we can't show anything useful
  // For local-only artifacts: upstreamError is expected, so don't block if projectData is available
  const shouldBlockWithError =
    (projectError && !hasUpstreamData && !hasSourceProjectData) || // Project failed and no upstream/source-project
    (upstreamError && projectError && (!hasSourceProjectData || sourceProjectError)) || // All failed
    (!hasValidUpstreamSource(entity) && projectError); // Local artifact and project failed

  if (shouldBlockWithError) {
    const errorToShow = projectError || upstreamError;
    return (
      <div className="flex h-full items-center justify-center p-8">
        <Alert variant="destructive" className="max-w-md">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load diff: {errorToShow?.message || 'Unknown error'}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!entity) {
    return <SyncStatusTabSkeleton />;
  }

  // Handle case where selected comparison has no data
  if (!currentDiff && !isLoading && !shouldBlockWithError) {
    return (
      <div className="flex h-full flex-col">
        <div className="flex-shrink-0 border-b">
          <ArtifactFlowBanner {...bannerProps} />
        </div>
        <div className="flex-shrink-0 space-y-2 border-b p-4">
          <ComparisonSelector {...comparisonProps} />
        </div>
        <div className="flex flex-1 items-center justify-center p-8">
          <Alert className="max-w-md">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              {comparisonScope === 'source-vs-collection' || comparisonScope === 'source-vs-project'
                ? hasSource && !hasValidUpstream
                  ? 'Upstream tracking is not enabled for this artifact. Enable upstream tracking to compare with the source.'
                  : !hasSource
                    ? 'No upstream source configured for this artifact.'
                    : 'No comparison data available for this scope.'
                : !projectPath
                  ? 'No project deployment found. Deploy this artifact to a project to enable comparison.'
                  : 'No comparison data available for this scope.'}
            </AlertDescription>
          </Alert>
        </div>
      </div>
    );
  }

  // ============================================================================
  // Render
  // ============================================================================

  // Entity is an alias for Artifact - no conversion needed
  // SyncDialog accepts Artifact which Entity now satisfies directly

  return (
    <>
      <div className="flex h-full min-h-0 flex-col overflow-hidden">
        {/* Top: Flow Banner */}
        <div className="flex-shrink-0 border-b">
          <ArtifactFlowBanner {...bannerProps} />
        </div>

        {/* Middle: Full Width Content */}
        <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          <div className="flex-shrink-0 space-y-2 border-b p-4">
            <ComparisonSelector {...comparisonProps} />
            {!isDriftDismissed && <DriftAlertBanner {...alertProps} />}
            {/* Member drift rows — only rendered for skill artifacts */}
            {entity.type === 'skill' && (
              <SkillMemberDrift
                artifactId={entity.id}
                collection={entity.collection}
                projectId={projectPath}
                comparisonScope={comparisonScope}
              />
            )}
          </div>
          <div className="min-h-0 min-w-0 flex-1 overflow-auto">
            <DiffViewer {...diffProps} />
          </div>
        </div>

        {/* Bottom: Actions Footer */}
        <div className="flex-shrink-0 border-t">
          <SyncActionsFooter {...footerProps} />
        </div>
      </div>

      {/* Sync Dialog for merge operations */}
      <SyncDialog
        artifact={entity}
        isOpen={showSyncDialog}
        onClose={() => setShowSyncDialog(false)}
        onSuccess={() => {
          queryClient.invalidateQueries({
            queryKey: ['upstream-diff', entity.id, entity.collection],
          });
          queryClient.invalidateQueries({ queryKey: ['project-diff', entity.id] });
          queryClient.invalidateQueries({ queryKey: ['source-project-diff', entity.id] });
          queryClient.invalidateQueries({ queryKey: ['artifacts'] });
          toast({
            title: 'Sync Complete',
            description: 'Changes merged successfully',
          });
          setShowSyncDialog(false);
        }}
      />

      {/* Push confirmation dialog */}
      <SyncConfirmationDialog
        direction="push"
        artifact={entity}
        projectPath={projectPath || ''}
        open={showPushConfirm}
        onOpenChange={setShowPushConfirm}
        onOverwrite={() => {
          setShowPushConfirm(false);
          pushToCollectionMutation.mutate();
        }}
        onMerge={() => {
          setShowPushConfirm(false);
          setMergeDirection('upstream');
          setShowMergeWorkflow(true);
        }}
      />

      {/* Pull confirmation dialog: merge routes to SyncDialog (source -> collection) */}
      <SyncConfirmationDialog
        direction="pull"
        artifact={entity}
        projectPath={projectPath || ''}
        open={showPullConfirm}
        onOpenChange={setShowPullConfirm}
        onOverwrite={() => {
          setShowPullConfirm(false);
          syncMutation.mutate();
        }}
        onMerge={() => {
          setShowPullConfirm(false);
          setShowSyncDialog(true);
        }}
      />

      {/* Deploy confirmation dialog: merge attempts merge-deploy, falls back to MergeWorkflow on conflicts */}
      <SyncConfirmationDialog
        direction="deploy"
        artifact={entity}
        projectPath={projectPath || ''}
        open={showDeployConfirm}
        onOpenChange={setShowDeployConfirm}
        onOverwrite={() => {
          setShowDeployConfirm(false);
          deployMutation.mutate();
        }}
        onMerge={() => {
          setShowDeployConfirm(false);
          deployMergeMutation.mutate();
        }}
      />

      {/* Merge Workflow dialog for push/deploy merge operations (SYNC-A03) */}
      <Dialog open={showMergeWorkflow} onOpenChange={setShowMergeWorkflow}>
        <DialogContent className="flex max-h-[90vh] max-w-4xl flex-col overflow-hidden">
          <DialogHeader>
            <div className="flex items-center gap-2">
              <GitMerge className="h-5 w-5" />
              <DialogTitle>Merge Workflow</DialogTitle>
            </div>
            <DialogDescription>
              {mergeDirection === 'downstream'
                ? `Merge ${entity.name} from collection into project`
                : `Merge ${entity.name} from project into collection`}
            </DialogDescription>
          </DialogHeader>
          <div className="min-h-0 flex-1 overflow-auto">
            {showMergeWorkflow && projectPath && (
              <MergeWorkflow
                entityId={entity.id}
                projectPath={projectPath}
                direction={mergeDirection}
                onComplete={() => {
                  setShowMergeWorkflow(false);
                  queryClient.invalidateQueries({ queryKey: ['project-diff', entity.id] });
                  queryClient.invalidateQueries({
                    queryKey: ['upstream-diff', entity.id, entity.collection],
                  });
                  queryClient.invalidateQueries({ queryKey: ['source-project-diff', entity.id] });
                  queryClient.invalidateQueries({ queryKey: ['artifacts'] });
                  queryClient.invalidateQueries({ queryKey: ['deployments'] });
                  queryClient.invalidateQueries({ queryKey: ['collections'] });
                  toast({
                    title: 'Merge Complete',
                    description: 'Changes merged successfully',
                  });
                }}
                onCancel={() => {
                  setShowMergeWorkflow(false);
                }}
              />
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
