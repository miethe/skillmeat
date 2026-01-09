'use client';

import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AlertCircle } from 'lucide-react';
import type { Entity } from '@/types/entity';
import type { ArtifactDiffResponse } from '@/sdk/models/ArtifactDiffResponse';
import type { ArtifactUpstreamDiffResponse } from '@/sdk/models/ArtifactUpstreamDiffResponse';
import type { FileDiff } from '@/sdk/models/FileDiff';
import { useToast } from '@/hooks/use-toast';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { apiRequest } from '@/lib/api';

// Phase 1 components
import { ArtifactFlowBanner } from './artifact-flow-banner';
import { ComparisonSelector, type ComparisonScope } from './comparison-selector';
import { DriftAlertBanner, type DriftStatus } from './drift-alert-banner';
import { SyncActionsFooter } from './sync-actions-footer';

// Existing components
import { DiffViewer } from '@/components/entity/diff-viewer';
import { SyncDialog } from '@/components/collection/sync-dialog';
import type { Artifact } from '@/types/artifact';

// ============================================================================
// Types
// ============================================================================

export interface SyncStatusTabProps {
  entity: Entity;
  mode: 'collection' | 'project';
  projectPath?: string;
  onClose: () => void;
}

interface PendingAction {
  type: 'pull' | 'push' | 'deploy' | 'merge';
  filePath?: string;
  direction?: 'upstream' | 'downstream';
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Convert Entity + upstream diff data to Artifact for SyncDialog compatibility
 */
function entityToArtifact(
  entity: Entity,
  upstreamDiff?: ArtifactUpstreamDiffResponse
): Artifact {
  return {
    id: entity.id,
    name: entity.name,
    type: entity.type,
    scope: 'user', // Default scope
    status: entity.status === 'conflict' ? 'conflict' : 'active',
    version: entity.version,
    source: entity.source,
    metadata: {
      description: entity.description,
      tags: entity.tags,
    },
    upstreamStatus: {
      hasUpstream: !!entity.source && entity.source !== 'local',
      upstreamUrl: entity.source,
      upstreamVersion: upstreamDiff?.upstream_version,
      currentVersion: entity.version,
      isOutdated: upstreamDiff?.has_changes ?? false,
      lastChecked: new Date().toISOString(),
    },
    usageStats: {
      totalDeployments: 0,
      activeProjects: 0,
      usageCount: 0,
    },
    createdAt: entity.deployedAt || new Date().toISOString(),
    updatedAt: entity.modifiedAt || new Date().toISOString(),
    aliases: entity.aliases,
  };
}

/**
 * Compute drift status from diff data
 */
function computeDriftStatus(
  diffData: ArtifactDiffResponse | ArtifactUpstreamDiffResponse | undefined
): DriftStatus {
  if (!diffData) return 'none';
  if (!diffData.has_changes) return 'none';

  // Check if any file has conflicts (basic heuristic: look for conflict markers)
  const hasConflicts = diffData.files.some(
    (f: FileDiff) => f.unified_diff?.includes('<<<<<<< ')
  );

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

/**
 * Check if entity has a valid upstream source (not local-only)
 * Returns false for: undefined, null, empty, 'local', 'local:*', 'unknown'
 */
function hasValidUpstreamSource(source: string | undefined | null): boolean {
  if (!source) return false;
  if (source === 'local' || source === 'unknown') return false;
  if (source.startsWith('local:')) return false;
  // Must look like a remote source (GitHub pattern with '/')
  return source.includes('/') && !source.startsWith('local');
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
        <div className="flex-1 space-y-2 p-6">
          {[...Array(12)].map((_, i) => (
            <Skeleton
              key={i}
              className="h-5"
              style={{ width: `${60 + Math.random() * 30}%` }}
            />
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
export function SyncStatusTab({
  entity,
  mode,
  projectPath,
  onClose,
}: SyncStatusTabProps) {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // ============================================================================
  // State
  // ============================================================================

  // Determine if we have a real source (not 'local' or 'unknown')
  const hasRealSource = !!entity.source && entity.source !== 'local' && entity.source !== 'unknown';

  const [comparisonScope, setComparisonScope] = useState<ComparisonScope>(
    mode === 'project'
      ? 'collection-vs-project'
      : hasRealSource
        ? 'source-vs-collection'
        : 'collection-vs-project'
  );
  const [pendingActions] = useState<PendingAction[]>([]);
  const [showSyncDialog, setShowSyncDialog] = useState(false);

  // ============================================================================
  // Queries
  // ============================================================================

  // Upstream diff (source vs collection)
  const {
    data: upstreamDiff,
    isLoading: upstreamLoading,
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
    enabled: !!entity.id
      && entity.collection !== 'discovered'
      && hasValidUpstreamSource(entity.source),
  });

  // Project diff (collection vs project)
  const {
    data: projectDiff,
    isLoading: projectLoading,
    error: projectError,
  } = useQuery<ArtifactDiffResponse>({
    queryKey: ['project-diff', entity.id, projectPath],
    queryFn: async () => {
      const params = new URLSearchParams({ project_path: projectPath! });
      return await apiRequest<ArtifactDiffResponse>(
        `/artifacts/${encodeURIComponent(entity.id)}/diff?${params}`
      );
    },
    enabled: !!entity.id && !!projectPath && mode === 'project' && entity.collection !== 'discovered',
  });

  // ============================================================================
  // Mutations
  // ============================================================================

  // Sync mutation (pull from source)
  const syncMutation = useMutation({
    mutationFn: async () => {
      return await apiRequest(
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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['upstream-diff', entity.id, entity.collection] });
      queryClient.invalidateQueries({ queryKey: ['project-diff', entity.id] });
      queryClient.invalidateQueries({ queryKey: ['artifacts'] });
      toast({
        title: 'Sync Successful',
        description: 'Pulled latest changes from source',
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Sync Failed',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  // Deploy mutation (deploy to project)
  const deployMutation = useMutation({
    mutationFn: async () => {
      return await apiRequest(
        `/artifacts/${encodeURIComponent(entity.id)}/deploy`,
        {
          method: 'POST',
          body: JSON.stringify({
            project_path: projectPath,
            overwrite: false,
          }),
        }
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project-diff', entity.id] });
      queryClient.invalidateQueries({ queryKey: ['upstream-diff', entity.id, entity.collection] });
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
        return await apiRequest(
          `/artifacts/${encodeURIComponent(entity.id)}/deploy`,
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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['upstream-diff', entity.id, entity.collection] });
      queryClient.invalidateQueries({ queryKey: ['project-diff', entity.id] });
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

  // Keep local mutation (dismiss drift alert)
  const keepLocalMutation = useMutation({
    mutationFn: async () => {
      // This is a no-op for now - just a UI acknowledgment
      // In the future, this could mark the drift as "acknowledged"
      return Promise.resolve();
    },
    onSuccess: () => {
      toast({
        title: 'Local Version Kept',
        description: 'Local changes preserved',
      });
    },
  });

  // ============================================================================
  // Event Handlers
  // ============================================================================

  const handleComparisonChange = (scope: ComparisonScope) => {
    setComparisonScope(scope);
  };

  const handlePullFromSource = () => {
    syncMutation.mutate();
  };

  const handleDeployToProject = () => {
    if (!projectPath) {
      toast({ title: 'Error', description: 'No project path', variant: 'destructive' });
      return;
    }
    deployMutation.mutate();
  };

  const handleTakeUpstream = () => {
    takeUpstreamMutation.mutate();
  };

  const handleKeepLocal = () => {
    keepLocalMutation.mutate();
  };

  const handleMerge = () => {
    setShowSyncDialog(true);
  };

  const handleApplyActions = () => {
    if (pendingActions.length === 0) return;
    toast({ title: 'Info', description: 'Batch actions not yet implemented' });
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
        // TODO: Implement source-vs-project diff query
        return projectDiff;
      default:
        return projectDiff;
    }
  }, [comparisonScope, upstreamDiff, projectDiff]);

  // Drift status
  const driftStatus = useMemo(
    () => computeDriftStatus(currentDiff),
    [currentDiff]
  );

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
            Sync status is not available for discovered artifacts. Import this artifact to your collection to enable sync tracking.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  // ============================================================================
  // Component Props
  // ============================================================================

  const bannerProps = {
    entity,
    sourceInfo: upstreamDiff
      ? {
          version: upstreamDiff.upstream_version,
          sha: upstreamDiff.upstream_version.slice(0, 7),
          hasUpdate: upstreamDiff.has_changes,
          source: upstreamDiff.upstream_source,
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
    onPushToCollection: () => toast({ title: 'Coming Soon' }),
    isPulling: syncMutation.isPending,
    isDeploying: deployMutation.isPending,
    isPushing: false,
  };

  const comparisonProps = {
    value: comparisonScope,
    onChange: handleComparisonChange,
    hasSource: !!entity.source && entity.source !== 'local' && entity.source !== 'unknown',
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
  };

  const diffProps = {
    files: currentDiff?.files || [],
    leftLabel: getLeftLabel(comparisonScope),
    rightLabel: getRightLabel(comparisonScope),
  };

  const footerProps = {
    onPullCollectionUpdates: handlePullFromSource,
    onPushLocalChanges: () => toast({ title: 'Coming Soon' }),
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
      keepLocalMutation.isPending,
  };

  // ============================================================================
  // Error & Loading States
  // ============================================================================

  // Determine if we have usable data
  const hasUpstreamData = !upstreamError && !!upstreamDiff;
  const hasProjectData = !projectError && !!projectDiff;
  const canShowAnyData = hasUpstreamData || hasProjectData;

  // Only show loading if we're loading AND don't have any data yet
  const isLoading = (upstreamLoading || projectLoading) && !canShowAnyData;

  // Only show blocking error if BOTH queries failed or if we can't show anything useful
  // For local-only artifacts: upstreamError is expected, so don't block if projectData is available
  const shouldBlockWithError =
    (projectError && !hasUpstreamData) || // Project failed and no upstream
    (upstreamError && projectError) ||     // Both failed
    (!hasValidUpstreamSource(entity.source) && projectError); // Local artifact and project failed

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

  if (isLoading) {
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
              No comparison data available for this scope.
              {!hasRealSource && " This artifact has no remote source."}
              {!projectPath && " No project deployment found."}
            </AlertDescription>
          </Alert>
        </div>
      </div>
    );
  }

  // ============================================================================
  // Render
  // ============================================================================

  // Convert Entity to Artifact for SyncDialog compatibility
  const artifactForSync = entityToArtifact(entity, upstreamDiff);

  return (
    <>
      <div className="flex h-full min-h-0 flex-col overflow-hidden">
        {/* Top: Flow Banner */}
        <div className="flex-shrink-0 border-b">
          <ArtifactFlowBanner {...bannerProps} />
        </div>

        {/* Middle: Full Width Content */}
        <div className="flex flex-1 min-w-0 flex-col overflow-hidden min-h-0">
          <div className="flex-shrink-0 space-y-2 border-b p-4">
            <ComparisonSelector {...comparisonProps} />
            <DriftAlertBanner {...alertProps} />
          </div>
          <div className="flex-1 overflow-hidden min-h-0 min-w-0">
            <div className="h-full min-h-[320px] max-h-[55vh] overflow-hidden">
              <DiffViewer {...diffProps} />
            </div>
          </div>
        </div>

        {/* Bottom: Actions Footer */}
        <div className="flex-shrink-0 border-t">
          <SyncActionsFooter {...footerProps} />
        </div>
      </div>

      {/* Sync Dialog for merge operations */}
      <SyncDialog
        artifact={artifactForSync}
        isOpen={showSyncDialog}
        onClose={() => setShowSyncDialog(false)}
        onSuccess={() => {
          queryClient.invalidateQueries({ queryKey: ['upstream-diff', entity.id, entity.collection] });
          queryClient.invalidateQueries({ queryKey: ['project-diff', entity.id] });
          queryClient.invalidateQueries({ queryKey: ['artifacts'] });
          toast({
            title: 'Sync Complete',
            description: 'Changes merged successfully',
          });
          setShowSyncDialog(false);
        }}
      />
    </>
  );
}
