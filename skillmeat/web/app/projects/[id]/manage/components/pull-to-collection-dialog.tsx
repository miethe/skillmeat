'use client';

import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Entity } from '@/types/entity';
import { apiRequest } from '@/lib/api';
import { ArtifactSyncRequest, ArtifactDiffResponse } from '@/sdk';
import { Loader2, GitMerge, AlertTriangle } from 'lucide-react';
import { DiffViewer } from '@/components/entity/diff-viewer';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface PullToCollectionDialogProps {
  entity: Entity;
  projectPath: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function PullToCollectionDialog({
  entity,
  projectPath,
  open,
  onOpenChange,
  onSuccess,
}: PullToCollectionDialogProps) {
  const [isLoadingDiff, setIsLoadingDiff] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [diffData, setDiffData] = useState<ArtifactDiffResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Fetch diff when dialog opens
  useEffect(() => {
    if (open) {
      fetchDiff();
    } else {
      // Reset state when dialog closes
      setDiffData(null);
      setError(null);
    }
  }, [open, entity.id]);

  const fetchDiff = async () => {
    setIsLoadingDiff(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        project_path: projectPath,
      });

      const response = await apiRequest<ArtifactDiffResponse>(
        `/artifacts/${entity.id}/diff?${params.toString()}`
      );

      setDiffData(response);
    } catch (err) {
      console.error('Failed to fetch diff:', err);
      setError('Failed to load changes. The entity may not have any modifications.');
    } finally {
      setIsLoadingDiff(false);
    }
  };

  const handlePull = async () => {
    setIsSyncing(true);
    setError(null);
    try {
      const request: ArtifactSyncRequest = {
        project_path: projectPath,
        strategy: 'ours', // Pull from project to collection
      };

      await apiRequest(`/artifacts/${entity.id}/sync`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });

      // Success
      onSuccess?.();
    } catch (err) {
      console.error('Pull failed:', err);
      setError('Failed to pull changes to collection. Please try again.');
    } finally {
      setIsSyncing(false);
    }
  };

  const hasChanges = diffData?.files && diffData.files.length > 0;
  const hasDifferences = diffData?.files?.some(
    (file) => file.status !== 'unchanged'
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <GitMerge className="h-5 w-5" />
            Pull to Collection: {entity.name}
          </DialogTitle>
          <DialogDescription>
            Review and pull local changes from the project back to your collection
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 flex flex-col min-h-0">
          {/* Status Badge */}
          <div className="flex items-center gap-2 mb-4">
            <span className="text-sm text-muted-foreground">Status:</span>
            {entity.status === 'modified' && (
              <Badge variant="outline" className="bg-yellow-500/10 text-yellow-700 dark:text-yellow-400 border-yellow-500/20">
                <AlertTriangle className="h-3 w-3 mr-1" />
                Modified
              </Badge>
            )}
            {entity.status === 'synced' && (
              <Badge variant="outline" className="bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20">
                Synced
              </Badge>
            )}
            {entity.status === 'outdated' && (
              <Badge variant="outline" className="bg-orange-500/10 text-orange-700 dark:text-orange-400 border-orange-500/20">
                Outdated
              </Badge>
            )}
          </div>

          {/* Error Alert */}
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Loading State */}
          {isLoadingDiff && (
            <div className="flex items-center justify-center py-12">
              <div className="flex flex-col items-center gap-4">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                <p className="text-sm text-muted-foreground">Loading changes...</p>
              </div>
            </div>
          )}

          {/* No Changes */}
          {!isLoadingDiff && !error && (!hasChanges || !hasDifferences) && (
            <div className="flex flex-col items-center justify-center py-12 text-center border rounded-lg bg-muted/20">
              <GitMerge className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">No Changes Detected</h3>
              <p className="text-sm text-muted-foreground max-w-md">
                The project version of this entity is identical to the collection version.
              </p>
            </div>
          )}

          {/* Diff Viewer */}
          {!isLoadingDiff && !error && hasChanges && hasDifferences && (
            <div className="flex-1 min-h-0 border rounded-lg overflow-hidden">
              <DiffViewer
                files={diffData.files}
                leftLabel="Collection"
                rightLabel="Project (Local)"
              />
            </div>
          )}
        </div>

        <DialogFooter>
          <div className="flex items-center justify-between w-full">
            <div className="text-sm text-muted-foreground">
              {diffData?.files && (
                <>
                  {diffData.files.filter((f) => f.status === 'modified').length} modified,{' '}
                  {diffData.files.filter((f) => f.status === 'added').length} added,{' '}
                  {diffData.files.filter((f) => f.status === 'deleted').length} deleted
                </>
              )}
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isSyncing}>
                Cancel
              </Button>
              <Button
                onClick={handlePull}
                disabled={!hasChanges || !hasDifferences || isSyncing || isLoadingDiff}
              >
                {isSyncing ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Pulling...
                  </>
                ) : (
                  <>
                    <GitMerge className="h-4 w-4 mr-2" />
                    Pull to Collection
                  </>
                )}
              </Button>
            </div>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
