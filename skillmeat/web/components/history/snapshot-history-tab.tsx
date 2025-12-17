/**
 * SnapshotHistoryTab - Container component for artifact version history
 *
 * Integrates all history components (timeline, comparison, rollback) into a
 * unified interface for viewing and managing snapshot history.
 *
 * Phase 8: Versioning & Merge System
 */

'use client';

import { useState } from 'react';
import { Plus, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { useCreateSnapshot } from '@/hooks/use-snapshots';
import { useToast } from '@/hooks/use-toast';
import {
  VersionTimeline,
  VersionComparisonView,
  RollbackDialog,
} from '@/components/history';
import { cn } from '@/lib/utils';

/**
 * Props for SnapshotHistoryTab component
 */
export interface SnapshotHistoryTabProps {
  /** Optional collection name to filter snapshots */
  collectionName?: string;
  /** Additional CSS classes */
  className?: string;
}

/**
 * SnapshotHistoryTab - Container for version history management
 *
 * Features:
 * - Create new snapshots with custom message
 * - View snapshot timeline with metadata
 * - Compare two snapshots side-by-side
 * - Rollback to previous snapshot with safety analysis
 *
 * @example
 * Basic usage:
 * ```tsx
 * <SnapshotHistoryTab collectionName="default" />
 * ```
 *
 * @example
 * With custom styling:
 * ```tsx
 * <SnapshotHistoryTab
 *   collectionName="default"
 *   className="p-6 bg-muted/50"
 * />
 * ```
 */
export function SnapshotHistoryTab({
  collectionName,
  className,
}: SnapshotHistoryTabProps) {
  // State for managing different views and dialogs
  const [compareSnapshots, setCompareSnapshots] = useState<{
    id1: string;
    id2: string;
  } | null>(null);
  const [restoreSnapshotId, setRestoreSnapshotId] = useState<string | null>(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [snapshotMessage, setSnapshotMessage] = useState('');

  // Hooks
  const createSnapshotMutation = useCreateSnapshot();
  const { toast } = useToast();

  /**
   * Handle create snapshot button click
   */
  const handleCreateSnapshot = async () => {
    if (!collectionName) {
      toast({
        title: 'Collection Required',
        description: 'Please select a collection to create a snapshot',
        variant: 'destructive',
      });
      return;
    }

    try {
      const result = await createSnapshotMutation.mutateAsync({
        collectionName,
        message: snapshotMessage || undefined,
      });

      toast({
        title: 'Snapshot Created',
        description: `Successfully captured snapshot ${result.snapshot.id.substring(0, 8)}`,
      });

      // Reset form
      setSnapshotMessage('');
      setCreateDialogOpen(false);
    } catch (error) {
      toast({
        title: 'Failed to Create Snapshot',
        description: error instanceof Error ? error.message : 'Unknown error occurred',
        variant: 'destructive',
      });
    }
  };

  /**
   * Handle snapshot comparison request from timeline
   */
  const handleCompare = (id1: string, id2: string) => {
    setCompareSnapshots({ id1, id2 });
  };

  /**
   * Handle snapshot restoration request from timeline
   */
  const handleRestore = (snapshotId: string) => {
    setRestoreSnapshotId(snapshotId);
  };

  /**
   * Handle successful rollback
   */
  const handleRollbackSuccess = () => {
    toast({
      title: 'Rollback Complete',
      description: 'Collection successfully restored to previous snapshot',
    });
    setRestoreSnapshotId(null);
  };

  /**
   * Close comparison view
   */
  const handleCloseComparison = () => {
    setCompareSnapshots(null);
  };

  // Show comparison view when two snapshots are selected
  if (compareSnapshots) {
    return (
      <div className={cn('space-y-6', className)}>
        <VersionComparisonView
          snapshotId1={compareSnapshots.id1}
          snapshotId2={compareSnapshots.id2}
          collectionName={collectionName}
          onClose={handleCloseComparison}
        />
      </div>
    );
  }

  return (
    <div className={cn('space-y-6', className)}>
      {/* Header with Create Snapshot button */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Clock className="h-5 w-5 text-muted-foreground" />
          <h2 className="text-lg font-semibold">Version History</h2>
        </div>

        <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Create Snapshot
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle>Create Version Snapshot</DialogTitle>
              <DialogDescription>
                Capture the current state of your collection for future reference or rollback.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="snapshot-message">
                  Message (optional)
                </Label>
                <Input
                  id="snapshot-message"
                  placeholder="e.g., Before major update"
                  value={snapshotMessage}
                  onChange={(e) => setSnapshotMessage(e.target.value)}
                  disabled={createSnapshotMutation.isPending}
                />
                <p className="text-xs text-muted-foreground">
                  Add a description to help identify this snapshot later
                </p>
              </div>
              {collectionName && (
                <div className="rounded-lg border bg-muted/50 p-3">
                  <p className="text-sm">
                    <span className="font-medium">Collection:</span>{' '}
                    <span className="font-mono">{collectionName}</span>
                  </p>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setCreateDialogOpen(false)}
                disabled={createSnapshotMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                onClick={handleCreateSnapshot}
                disabled={!collectionName || createSnapshotMutation.isPending}
              >
                {createSnapshotMutation.isPending ? 'Creating...' : 'Create Snapshot'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Timeline */}
      <VersionTimeline
        collectionName={collectionName}
        onCompare={handleCompare}
        onRestore={handleRestore}
      />

      {/* Rollback Dialog */}
      {restoreSnapshotId && (
        <RollbackDialog
          snapshotId={restoreSnapshotId}
          collectionName={collectionName}
          open={!!restoreSnapshotId}
          onOpenChange={(open) => !open && setRestoreSnapshotId(null)}
          onSuccess={handleRollbackSuccess}
        />
      )}
    </div>
  );
}
