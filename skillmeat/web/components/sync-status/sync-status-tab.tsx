'use client';

import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Loader2, AlertCircle } from 'lucide-react';
import type { Entity } from '@/types/entity';
import type { ArtifactDiffResponse } from '@/sdk/models/ArtifactDiffResponse';
import type { ArtifactUpstreamDiffResponse } from '@/sdk/models/ArtifactUpstreamDiffResponse';
import type { FileDiff } from '@/sdk/models/FileDiff';
import { useToast } from '@/hooks/use-toast';
import { Alert, AlertDescription } from '@/components/ui/alert';

// Phase 1 components
import { ArtifactFlowBanner } from './artifact-flow-banner';
import { ComparisonSelector, type ComparisonScope } from './comparison-selector';
import { DriftAlertBanner, type DriftStatus } from './drift-alert-banner';
import { FilePreviewPane } from './file-preview-pane';
import { SyncActionsFooter } from './sync-actions-footer';

// Existing components
import { FileTree, type FileNode } from '@/components/entity/file-tree';
import { DiffViewer } from '@/components/entity/diff-viewer';

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
 * Convert FileDiff[] to FileNode[] for FileTree
 */
function buildFileTree(files: FileDiff[]): FileNode[] {
  const root: FileNode[] = [];
  const pathMap = new Map<string, FileNode>();

  // Create nodes for all files
  files.forEach((file) => {
    const parts = file.file_path.split('/');
    let currentPath = '';

    parts.forEach((part, index) => {
      const parentPath = currentPath;
      currentPath = currentPath ? `${currentPath}/${part}` : part;
      const isLastPart = index === parts.length - 1;

      if (!pathMap.has(currentPath)) {
        const node: FileNode = {
          name: part,
          path: currentPath,
          type: isLastPart ? 'file' : 'directory',
          children: isLastPart ? undefined : [],
        };

        pathMap.set(currentPath, node);

        if (parentPath) {
          const parent = pathMap.get(parentPath);
          if (parent && parent.children) {
            parent.children.push(node);
          }
        } else {
          root.push(node);
        }
      }
    });
  });

  return root;
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
 * Get tier for FilePreviewPane based on comparison scope
 */
function getTierFromScope(scope: ComparisonScope): 'source' | 'collection' | 'project' {
  switch (scope) {
    case 'source-vs-collection':
      return 'source';
    case 'collection-vs-project':
      return 'collection';
    case 'source-vs-project':
      return 'project';
    default:
      return 'collection';
  }
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * SyncStatusTab - Orchestration component for 3-panel sync status UI
 *
 * Features:
 * - 3-tier flow visualization (Source → Collection → Project)
 * - Comparison scope selector (source-vs-collection, collection-vs-project, source-vs-project)
 * - File tree browser with diff highlighting
 * - Side-by-side diff viewer
 * - File preview pane
 * - Drift status alerts with actions
 * - Sync actions footer with batch operations
 *
 * Layout:
 * ```
 * ┌─────────────────────────────────────────────────────────┐
 * │              ArtifactFlowBanner (full width)            │
 * ├──────────┬───────────────────────────┬──────────────────┤
 * │ FileTree │  ComparisonSelector       │                  │
 * │ (240px)  │  DriftAlertBanner         │ FilePreviewPane  │
 * │          │  DiffViewer               │ (320px)          │
 * ├──────────┴───────────────────────────┴──────────────────┤
 * │              SyncActionsFooter (full width)             │
 * └─────────────────────────────────────────────────────────┘
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

  const [comparisonScope, setComparisonScope] = useState<ComparisonScope>(
    mode === 'project' ? 'collection-vs-project' : 'source-vs-collection'
  );
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [pendingActions, setPendingActions] = useState<PendingAction[]>([]);

  // ============================================================================
  // Queries
  // ============================================================================

  // Upstream diff (source vs collection)
  const {
    data: upstreamDiff,
    isLoading: upstreamLoading,
    error: upstreamError,
  } = useQuery<ArtifactUpstreamDiffResponse>({
    queryKey: ['upstream-diff', entity.id],
    queryFn: async () => {
      const response = await fetch(`/api/artifacts/${entity.id}/upstream-diff`);
      if (!response.ok) throw new Error('Failed to fetch upstream diff');
      return response.json();
    },
    enabled: !!entity.id && !!entity.source,
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
      const response = await fetch(`/api/artifacts/${entity.id}/diff?${params}`);
      if (!response.ok) throw new Error('Failed to fetch project diff');
      return response.json();
    },
    enabled: !!entity.id && !!projectPath && mode === 'project',
  });

  // File content for preview
  const {
    data: fileContent,
    isLoading: contentLoading,
  } = useQuery<string>({
    queryKey: ['file-content', entity.id, selectedFile],
    queryFn: async () => {
      const response = await fetch(
        `/api/artifacts/${entity.id}/files/${encodeURIComponent(selectedFile!)}`
      );
      if (!response.ok) throw new Error('Failed to fetch file content');
      return response.text();
    },
    enabled: !!entity.id && !!selectedFile,
  });

  // ============================================================================
  // Mutations
  // ============================================================================

  // Sync mutation (pull from source)
  const syncMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch(`/api/artifacts/${entity.id}/sync`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          // Empty body syncs from upstream source (not project)
          // project_path is omitted to trigger upstream sync
        }),
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Sync failed' }));
        throw new Error(errorData.detail || 'Sync failed');
      }
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['upstream-diff', entity.id] });
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
      const response = await fetch(`/api/artifacts/${entity.id}/deploy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: projectPath,
          overwrite: false,
        }),
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Deploy failed' }));
        throw new Error(errorData.detail || 'Deploy failed');
      }
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project-diff', entity.id] });
      queryClient.invalidateQueries({ queryKey: ['upstream-diff', entity.id] });
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
        const response = await fetch(`/api/artifacts/${entity.id}/deploy`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_path: projectPath,
            overwrite: true,
          }),
        });
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ detail: 'Failed to take upstream' }));
          throw new Error(errorData.detail || 'Failed to take upstream');
        }
        return response.json();
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['upstream-diff', entity.id] });
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

  const handleFileSelect = (path: string) => {
    setSelectedFile(path);
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
    toast({ title: 'Coming Soon', description: 'Merge workflow in Phase 3' });
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

  // File tree
  const fileTree = useMemo(
    () => buildFileTree(currentDiff?.files || []),
    [currentDiff?.files]
  );

  // Drift status
  const driftStatus = useMemo(
    () => computeDriftStatus(currentDiff),
    [currentDiff]
  );

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
    hasSource: !!entity.source,
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

  const fileTreeProps = {
    entityId: entity.id,
    files: fileTree,
    selectedPath: selectedFile,
    onSelect: handleFileSelect,
  };

  const diffProps = {
    files: currentDiff?.files || [],
    leftLabel: getLeftLabel(comparisonScope),
    rightLabel: getRightLabel(comparisonScope),
  };

  const previewProps = {
    filePath: selectedFile,
    content: fileContent || null,
    tier: getTierFromScope(comparisonScope),
    isLoading: contentLoading,
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

  const error = upstreamError || projectError;
  const isLoading = upstreamLoading || projectLoading;

  if (error) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <Alert variant="destructive" className="max-w-md">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load diff: {error.message}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          <p className="text-sm text-muted-foreground">Loading diff data...</p>
        </div>
      </div>
    );
  }

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <div className="flex h-full flex-col">
      {/* Top: Flow Banner */}
      <div className="flex-shrink-0 border-b">
        <ArtifactFlowBanner {...bannerProps} />
      </div>

      {/* Middle: 3-Panel Layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Panel: File Tree (240px fixed) */}
        <div className="w-60 flex-shrink-0 border-r">
          <FileTree {...fileTreeProps} />
        </div>

        {/* Center Panel: Comparison + Diff (flex-1) */}
        <div className="flex flex-1 flex-col overflow-hidden">
          <div className="flex-shrink-0 space-y-2 border-b p-4">
            <ComparisonSelector {...comparisonProps} />
            <DriftAlertBanner {...alertProps} />
          </div>
          <div className="flex-1 overflow-auto">
            <DiffViewer {...diffProps} />
          </div>
        </div>

        {/* Right Panel: File Preview (320px fixed) */}
        <div className="w-80 flex-shrink-0 border-l">
          <FilePreviewPane {...previewProps} />
        </div>
      </div>

      {/* Bottom: Actions Footer */}
      <div className="flex-shrink-0 border-t">
        <SyncActionsFooter {...footerProps} />
      </div>
    </div>
  );
}
