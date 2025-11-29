'use client';

import { useState } from 'react';
import { RefreshCw, AlertTriangle, TrendingUp } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { ProgressIndicator, ProgressStep } from './progress-indicator';
import { ConflictResolver } from './conflict-resolver';
import { useSync, type ConflictInfo } from '@/hooks/useSync';
import type { Artifact } from '@/types/artifact';

export interface SyncDialogProps {
  artifact: Artifact | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

type SyncState = 'ready' | 'syncing' | 'conflicts' | 'complete';

export function SyncDialog({ artifact, isOpen, onClose, onSuccess }: SyncDialogProps) {
  const [syncState, setSyncState] = useState<SyncState>('ready');
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [conflicts, setConflicts] = useState<ConflictInfo[]>([]);
  const [force, setForce] = useState(false);
  const [initialSteps] = useState<ProgressStep[]>([
    { step: 'Checking upstream', status: 'pending' },
    { step: 'Fetching updates', status: 'pending' },
    { step: 'Detecting conflicts', status: 'pending' },
    { step: 'Applying changes', status: 'pending' },
  ]);

  const syncMutation = useSync({
    onSuccess: (data) => {
      if (data.hasConflicts && data.conflicts) {
        setConflicts(data.conflicts);
        setSyncState('conflicts');
      } else {
        if (data.streamUrl) {
          setStreamUrl(data.streamUrl);
        }
      }
    },
    onError: () => {
      setSyncState('ready');
    },
    onConflict: (conflictList) => {
      setConflicts(conflictList);
      setSyncState('conflicts');
    },
  });

  const handleSync = async (mergeStrategy?: 'ours' | 'theirs') => {
    if (!artifact) return;

    setSyncState('syncing');

    try {
      await syncMutation.mutateAsync({
        artifactId: artifact.id,
        artifactName: artifact.name,
        artifactType: artifact.type,
        force: force || !!mergeStrategy,
        mergeStrategy,
      });
    } catch (error) {
      console.error('Sync failed:', error);
      setSyncState('ready');
    }
  };

  const handleConflictResolve = (strategy: 'ours' | 'theirs' | 'manual') => {
    if (strategy === 'manual') {
      // TODO: Implement manual conflict resolution UI
      return;
    }

    // Retry sync with chosen strategy
    setConflicts([]);
    handleSync(strategy);
  };

  const handleComplete = (success: boolean) => {
    if (success) {
      setSyncState('complete');
      setTimeout(() => {
        onSuccess?.();
        handleClose();
      }, 1500);
    } else {
      setSyncState('ready');
    }
  };

  const handleClose = () => {
    if (syncState !== 'syncing') {
      onClose();
      // Reset state
      setSyncState('ready');
      setStreamUrl(null);
      setConflicts([]);
      setForce(false);
    }
  };

  if (!artifact) return null;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-primary/10 p-2">
              <RefreshCw className="h-5 w-5 text-primary" />
            </div>
            <div>
              <DialogTitle>Sync Artifact</DialogTitle>
              <DialogDescription>Sync {artifact.name} with upstream source</DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {syncState === 'ready' && (
            <>
              {/* Artifact Info */}
              <div className="space-y-2 rounded-lg border p-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Current Version</span>
                  <code className="rounded bg-muted px-2 py-1 text-xs">
                    {artifact.upstreamStatus.currentVersion || artifact.version || 'N/A'}
                  </code>
                </div>
                {artifact.upstreamStatus.hasUpstream && (
                  <>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Upstream Version</span>
                      <code className="rounded bg-muted px-2 py-1 text-xs">
                        {artifact.upstreamStatus.upstreamVersion || 'Unknown'}
                      </code>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Source</span>
                      <span className="max-w-[200px] truncate font-mono text-xs">
                        {artifact.source}
                      </span>
                    </div>
                  </>
                )}
              </div>

              {/* Update Status */}
              {artifact.upstreamStatus.isOutdated ? (
                <div className="rounded-lg border border-yellow-500/50 bg-yellow-500/10 p-3">
                  <div className="flex items-start gap-2">
                    <TrendingUp className="mt-0.5 h-4 w-4 flex-shrink-0 text-yellow-600" />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-yellow-900 dark:text-yellow-100">
                        Update Available
                      </p>
                      <p className="mt-1 text-xs text-yellow-800 dark:text-yellow-200">
                        A new version is available. Syncing will update your local copy to the
                        latest version.
                      </p>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="rounded-lg border border-green-500/50 bg-green-500/10 p-3">
                  <div className="flex items-start gap-2">
                    <RefreshCw className="mt-0.5 h-4 w-4 flex-shrink-0 text-green-600" />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-green-900 dark:text-green-100">
                        Up to Date
                      </p>
                      <p className="mt-1 text-xs text-green-800 dark:text-green-200">
                        Your local copy is in sync with the upstream source.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Warning for local modifications */}
              {artifact.status === 'conflict' && (
                <div className="rounded-lg border border-orange-500/50 bg-orange-500/10 p-3">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-orange-600" />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-orange-900 dark:text-orange-100">
                        Local Modifications Detected
                      </p>
                      <p className="mt-1 text-xs text-orange-800 dark:text-orange-200">
                        This artifact has local modifications. Syncing may result in conflicts.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}

          {syncState === 'syncing' && (
            <ProgressIndicator
              streamUrl={streamUrl}
              enabled={syncState === 'syncing'}
              initialSteps={initialSteps}
              onComplete={handleComplete}
              onError={(error) => {
                console.error('Sync error:', error);
                setSyncState('ready');
              }}
            />
          )}

          {syncState === 'conflicts' && (
            <ConflictResolver
              conflicts={conflicts}
              onResolve={handleConflictResolve}
              onCancel={() => {
                setConflicts([]);
                setSyncState('ready');
              }}
            />
          )}
        </div>

        {syncState === 'ready' && (
          <DialogFooter>
            <Button variant="outline" onClick={handleClose} disabled={syncMutation.isPending}>
              Cancel
            </Button>
            <Button
              onClick={() => handleSync()}
              disabled={syncMutation.isPending || !artifact.upstreamStatus.hasUpstream}
            >
              {syncMutation.isPending ? 'Syncing...' : 'Sync Now'}
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
}
