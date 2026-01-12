'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, CheckCircle2, Loader2, ArrowDown, ArrowUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { useToast } from '@/hooks/use-toast';
import { DiffViewer, type ResolutionType } from '@/components/entity/diff-viewer';
import type { FileDiff } from '@/sdk/models/FileDiff';
import {
  getSyncStatus,
  pullChanges,
  pushChanges,
  resolveConflict,
  type SyncStatus,
  type SyncConflict,
} from '@/lib/api/context-sync';

interface ContextSyncStatusProps {
  entityId: string;
  entityName?: string;
  projectPath: string;
}

/**
 * ContextSyncStatus - Sync status display for context entities
 *
 * Shows pending changes, conflicts, and provides sync actions for context entities.
 * Integrates with the extended DiffViewer for conflict resolution.
 *
 * Features:
 * - Displays modified entities in project and collection
 * - Shows conflicts with diff preview
 * - Provides Pull/Push sync buttons
 * - Resolution actions (Keep Local/Remote) for conflicts
 * - Badge showing count of pending changes
 *
 * @example
 * ```tsx
 * <ContextSyncStatus
 *   entityId="spec_file:api-patterns"
 *   entityName="api-patterns"
 *   projectPath="/path/to/project"
 * />
 * ```
 */
export function ContextSyncStatus({
  entityId,
  entityName,
  projectPath,
}: ContextSyncStatusProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [selectedConflict, setSelectedConflict] = useState<SyncConflict | null>(null);

  // Fetch sync status
  const {
    data: syncStatus,
    isLoading: isLoadingStatus,
    error: statusError,
    refetch: refetchStatus,
  } = useQuery<SyncStatus>({
    queryKey: ['context-sync-status', projectPath],
    queryFn: () => getSyncStatus(projectPath),
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 60 * 1000, // Auto-refresh every 60 seconds
  });

  // Pull mutation
  const pullMutation = useMutation({
    mutationFn: (entityIds?: string[]) => pullChanges(projectPath, entityIds),
    onSuccess: (results) => {
      toast({
        title: 'Pull Complete',
        description: `Pulled ${results.length} ${results.length === 1 ? 'entity' : 'entities'} from project`,
      });
      queryClient.invalidateQueries({ queryKey: ['context-sync-status', projectPath] });
      queryClient.invalidateQueries({ queryKey: ['artifact-files'] });
    },
    onError: (error) => {
      toast({
        title: 'Pull Failed',
        description: error instanceof Error ? error.message : 'Failed to pull changes',
        variant: 'destructive',
      });
    },
  });

  // Push mutation
  const pushMutation = useMutation({
    mutationFn: (entityIds?: string[]) => pushChanges(projectPath, entityIds, false),
    onSuccess: (results) => {
      toast({
        title: 'Push Complete',
        description: `Pushed ${results.length} ${results.length === 1 ? 'entity' : 'entities'} to project`,
      });
      queryClient.invalidateQueries({ queryKey: ['context-sync-status', projectPath] });
      queryClient.invalidateQueries({ queryKey: ['artifact-files'] });
    },
    onError: (error) => {
      toast({
        title: 'Push Failed',
        description: error instanceof Error ? error.message : 'Failed to push changes',
        variant: 'destructive',
      });
    },
  });

  // Resolve conflict mutation
  const resolveMutation = useMutation({
    mutationFn: ({
      entityId,
      resolution,
      mergedContent,
    }: {
      entityId: string;
      resolution: ResolutionType;
      mergedContent?: string;
    }) => resolveConflict(projectPath, entityId, resolution, mergedContent),
    onSuccess: (result) => {
      toast({
        title: 'Conflict Resolved',
        description: result.message,
      });
      setSelectedConflict(null);
      queryClient.invalidateQueries({ queryKey: ['context-sync-status', projectPath] });
      queryClient.invalidateQueries({ queryKey: ['artifact-files'] });
    },
    onError: (error) => {
      toast({
        title: 'Resolution Failed',
        description: error instanceof Error ? error.message : 'Failed to resolve conflict',
        variant: 'destructive',
      });
    },
  });

  const handlePull = () => {
    pullMutation.mutate([entityId]);
  };

  const handlePush = () => {
    pushMutation.mutate([entityId]);
  };

  const handleResolve = (resolution: ResolutionType) => {
    if (!selectedConflict) return;

    resolveMutation.mutate({
      entityId: selectedConflict.entity_id,
      resolution,
    });
  };

  // Check if this specific entity has changes/conflicts
  const hasProjectChanges = syncStatus?.modified_in_project.includes(entityId) ?? false;
  const hasCollectionChanges = syncStatus?.modified_in_collection.includes(entityId) ?? false;
  const entityConflict = syncStatus?.conflicts.find((c) => c.entity_id === entityId);
  const hasPendingChanges = hasProjectChanges || hasCollectionChanges || !!entityConflict;
  const pendingCount =
    (hasProjectChanges ? 1 : 0) + (hasCollectionChanges ? 1 : 0) + (entityConflict ? 1 : 0);

  // Loading state
  if (isLoadingStatus) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
        <span className="ml-2 text-sm text-muted-foreground">Checking sync status...</span>
      </div>
    );
  }

  // Error state
  if (statusError) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          {statusError instanceof Error ? statusError.message : 'Failed to load sync status'}
        </AlertDescription>
      </Alert>
    );
  }

  // No changes state
  if (!hasPendingChanges) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <CheckCircle2 className="h-12 w-12 text-green-500" />
        <p className="mt-4 text-sm font-medium">No pending changes</p>
        <p className="mt-1 text-xs text-muted-foreground">
          {entityName || entityId} is in sync between collection and project
        </p>
        <Button onClick={() => refetchStatus()} variant="outline" size="sm" className="mt-4">
          Refresh Status
        </Button>
      </div>
    );
  }

  // Convert conflict to FileDiff for DiffViewer
  const conflictDiffs: FileDiff[] = entityConflict
    ? [
        {
          file_path: entityConflict.deployed_path.replace(/^.*\.claude\//, '.claude/'),
          status: 'modified',
          unified_diff: '', // Would need unified diff generation from conflict content
        },
      ]
    : [];

  return (
    <div className="space-y-4">
      {/* Pending Changes Summary */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Sync Status</CardTitle>
            <div className="flex items-center gap-2">
              <Badge variant="secondary">{pendingCount} pending</Badge>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Badge variant="outline" className="text-xs cursor-help">
                      Preview
                    </Badge>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Context sync detection works, but pull/push/resolve are not yet implemented.</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {/* Modified in project */}
          {hasProjectChanges && (
            <div className="flex items-center justify-between rounded-lg border bg-blue-500/10 p-3">
              <div className="flex items-center gap-2">
                <ArrowUp className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                <span className="text-sm font-medium">Modified in project</span>
              </div>
              <Button
                onClick={handlePull}
                disabled={pullMutation.isPending}
                size="sm"
                variant="outline"
              >
                {pullMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-3 w-3 animate-spin" />
                    Pulling...
                  </>
                ) : (
                  'Pull Changes'
                )}
              </Button>
            </div>
          )}

          {/* Modified in collection */}
          {hasCollectionChanges && (
            <div className="flex items-center justify-between rounded-lg border bg-green-500/10 p-3">
              <div className="flex items-center gap-2">
                <ArrowDown className="h-4 w-4 text-green-600 dark:text-green-400" />
                <span className="text-sm font-medium">Modified in collection</span>
              </div>
              <Button
                onClick={handlePush}
                disabled={pushMutation.isPending}
                size="sm"
                variant="outline"
              >
                {pushMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-3 w-3 animate-spin" />
                    Pushing...
                  </>
                ) : (
                  'Push Changes'
                )}
              </Button>
            </div>
          )}

          {/* Conflict */}
          {entityConflict && (
            <div className="space-y-3">
              <div className="flex items-center justify-between rounded-lg border border-red-500/20 bg-red-500/10 p-3">
                <div className="flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
                  <span className="text-sm font-medium text-red-700 dark:text-red-400">
                    Sync conflict detected
                  </span>
                </div>
                <Button
                  onClick={() => setSelectedConflict(entityConflict)}
                  size="sm"
                  variant="outline"
                  className="border-red-500/20 hover:bg-red-500/10"
                >
                  Resolve
                </Button>
              </div>

              {/* Show conflict diff if selected */}
              {selectedConflict && (
                <div className="overflow-hidden rounded-lg border">
                  <DiffViewer
                    files={conflictDiffs}
                    showResolutionActions={true}
                    onResolve={handleResolve}
                    localLabel="Project"
                    remoteLabel="Collection"
                    isResolving={resolveMutation.isPending}
                    previewMode={true}
                  />
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Info Alert */}
      <Alert>
        <AlertDescription className="text-xs">
          <strong>Pull:</strong> Update collection from project (project wins).
          <br />
          <strong>Push:</strong> Update project from collection (collection wins).
        </AlertDescription>
      </Alert>
    </div>
  );
}
