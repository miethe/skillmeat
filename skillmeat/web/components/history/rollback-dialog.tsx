/**
 * Rollback Dialog Component
 *
 * Multi-step confirmation dialog for rolling back collection to a previous snapshot.
 * Includes safety analysis, confirmation checkboxes, and result display.
 *
 * Phase 8: Versioning & Merge System
 */

'use client';

import { useState, useEffect } from 'react';
import { format } from 'date-fns';
import {
  RotateCcw,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  FileWarning,
  Shield,
  FileCheck,
  GitMerge,
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Label } from '@/components/ui/label';
import { useRollbackAnalysis, useRollback, useSnapshot } from '@/hooks';
import type { RollbackResponse } from '@/types/snapshot';

/**
 * Props for RollbackDialog component
 */
export interface RollbackDialogProps {
  /** Snapshot ID to rollback to */
  snapshotId: string;
  /** Optional collection name */
  collectionName?: string;
  /** Whether dialog is open */
  open: boolean;
  /** Callback to change open state */
  onOpenChange: (open: boolean) => void;
  /** Callback on successful rollback */
  onSuccess?: (result: RollbackResponse) => void;
}

/**
 * RollbackDialog - Confirmation dialog for snapshot rollback
 *
 * Multi-step flow:
 * 1. Display snapshot info and safety analysis
 * 2. Show confirmation checkboxes
 * 3. Execute rollback
 * 4. Display results
 *
 * @example
 * ```tsx
 * <RollbackDialog
 *   snapshotId="abc123..."
 *   collectionName="default"
 *   open={showDialog}
 *   onOpenChange={setShowDialog}
 *   onSuccess={(result) => console.log('Rollback complete:', result)}
 * />
 * ```
 */
export function RollbackDialog({
  snapshotId,
  collectionName,
  open,
  onOpenChange,
  onSuccess,
}: RollbackDialogProps) {
  // State
  const [confirmedRollback, setConfirmedRollback] = useState(false);
  const [preserveChanges, setPreserveChanges] = useState(true);
  const [rollbackResult, setRollbackResult] = useState<RollbackResponse | null>(null);

  // Hooks
  const { data: snapshot, isLoading: isLoadingSnapshot } = useSnapshot(snapshotId, collectionName);
  const { data: analysis, isLoading: isLoadingAnalysis, error: analysisError } = useRollbackAnalysis(
    snapshotId,
    collectionName
  );
  const rollbackMutation = useRollback();

  // Reset state when dialog opens/closes
  useEffect(() => {
    if (!open) {
      setConfirmedRollback(false);
      setPreserveChanges(true);
      setRollbackResult(null);
    }
  }, [open]);

  const handleRollback = async () => {
    try {
      const result = await rollbackMutation.mutateAsync({
        snapshotId,
        collectionName,
        preserveChanges,
        selectivePaths: undefined, // Full rollback
      });

      setRollbackResult(result);

      // Call onSuccess callback if provided
      if (onSuccess) {
        onSuccess(result);
      }
    } catch (error) {
      // Error is handled by mutation and displayed below
      console.error('Rollback failed:', error);
    }
  };

  const handleClose = () => {
    onOpenChange(false);
  };

  // Loading state
  const isLoading = isLoadingSnapshot || isLoadingAnalysis;
  const isRollingBack = rollbackMutation.isPending;

  // Show result view after successful rollback
  if (rollbackResult) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-green-600" />
              Rollback Complete
            </DialogTitle>
            <DialogDescription>
              Successfully rolled back to snapshot.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* Success stats */}
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-lg border bg-muted/50 p-4">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <GitMerge className="h-4 w-4" />
                  Files Merged
                </div>
                <p className="mt-1 text-2xl font-bold">{rollbackResult.filesMerged.length}</p>
              </div>
              <div className="rounded-lg border bg-muted/50 p-4">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <FileCheck className="h-4 w-4" />
                  Files Restored
                </div>
                <p className="mt-1 text-2xl font-bold">{rollbackResult.filesRestored.length}</p>
              </div>
            </div>

            {/* Conflicts */}
            {rollbackResult.conflicts.length > 0 && (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle>Manual Resolution Required</AlertTitle>
                <AlertDescription>
                  {rollbackResult.conflicts.length} file(s) have conflicts that require manual resolution.
                  <ScrollArea className="mt-2 max-h-[100px]">
                    <ul className="space-y-1">
                      {rollbackResult.conflicts.map((conflict, index) => (
                        <li key={index} className="font-mono text-xs">
                          {conflict.filePath}
                        </li>
                      ))}
                    </ul>
                  </ScrollArea>
                </AlertDescription>
              </Alert>
            )}

            {/* Safety snapshot */}
            {rollbackResult.safetySnapshotId && (
              <div className="flex items-center gap-2 rounded-lg border bg-muted/50 p-3">
                <Shield className="h-4 w-4 text-blue-600" />
                <div className="flex-1">
                  <p className="text-sm font-medium">Safety Snapshot Created</p>
                  <p className="font-mono text-xs text-muted-foreground">
                    {rollbackResult.safetySnapshotId}
                  </p>
                </div>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button onClick={handleClose}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <RotateCcw className="h-5 w-5" />
            Rollback to Snapshot?
          </DialogTitle>
          <DialogDescription>
            Review the safety analysis and confirm to rollback your collection to this snapshot.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Snapshot Info */}
          {snapshot && (
            <div className="rounded-lg border bg-muted/50 p-4">
              <div className="space-y-2">
                <div>
                  <p className="text-sm font-medium">Snapshot Message</p>
                  <p className="text-sm text-muted-foreground">{snapshot.message}</p>
                </div>
                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  <span>{format(new Date(snapshot.timestamp), 'PPpp')}</span>
                  <span>{snapshot.artifactCount} artifacts</span>
                </div>
              </div>
            </div>
          )}

          {/* Loading State */}
          {isLoading && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          )}

          {/* Analysis Error */}
          {analysisError && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Failed to Load Safety Analysis</AlertTitle>
              <AlertDescription>
                {analysisError instanceof Error ? analysisError.message : 'Unknown error occurred'}
              </AlertDescription>
            </Alert>
          )}

          {/* Safety Analysis */}
          {analysis && !isLoading && (
            <div className="space-y-3">
              {/* Safety Badge */}
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">Safety Status:</span>
                {analysis.isSafe ? (
                  <Badge variant="default" className="bg-green-600">
                    <CheckCircle2 className="mr-1 h-3 w-3" />
                    Safe to Rollback
                  </Badge>
                ) : (
                  <Badge variant="destructive">
                    <AlertTriangle className="mr-1 h-3 w-3" />
                    Has Conflicts
                  </Badge>
                )}
              </div>

              {/* Files with Conflicts */}
              {analysis.filesWithConflicts.length > 0 && (
                <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-3 dark:border-yellow-900 dark:bg-yellow-950">
                  <div className="mb-2 flex items-center gap-2 text-sm font-medium">
                    <FileWarning className="h-4 w-4 text-yellow-600" />
                    Files with Conflicts ({analysis.filesWithConflicts.length})
                  </div>
                  <ScrollArea className="max-h-[150px]">
                    <ul className="space-y-1">
                      {analysis.filesWithConflicts.map((file, index) => (
                        <li key={index} className="flex items-start gap-2 text-xs">
                          <FileWarning className="mt-0.5 h-3 w-3 flex-shrink-0 text-yellow-600" />
                          <span className="break-all font-mono">{file}</span>
                        </li>
                      ))}
                    </ul>
                  </ScrollArea>
                </div>
              )}

              {/* Files Safe to Restore */}
              {analysis.filesSafeToRestore.length > 0 && (
                <div className="rounded-lg border border-green-200 bg-green-50 p-3 dark:border-green-900 dark:bg-green-950">
                  <div className="mb-2 flex items-center gap-2 text-sm font-medium">
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                    Files Safe to Restore ({analysis.filesSafeToRestore.length})
                  </div>
                  <ScrollArea className="max-h-[150px]">
                    <ul className="space-y-1">
                      {analysis.filesSafeToRestore.map((file, index) => (
                        <li key={index} className="flex items-start gap-2 text-xs">
                          <CheckCircle2 className="mt-0.5 h-3 w-3 flex-shrink-0 text-green-600" />
                          <span className="break-all font-mono">{file}</span>
                        </li>
                      ))}
                    </ul>
                  </ScrollArea>
                </div>
              )}

              {/* Warnings */}
              {analysis.warnings.length > 0 && (
                <Alert>
                  <AlertTriangle className="h-4 w-4" />
                  <AlertTitle>Warnings</AlertTitle>
                  <AlertDescription>
                    <ul className="mt-2 space-y-1">
                      {analysis.warnings.map((warning, index) => (
                        <li key={index} className="text-sm">
                          {warning}
                        </li>
                      ))}
                    </ul>
                  </AlertDescription>
                </Alert>
              )}
            </div>
          )}

          {/* Rollback Error */}
          {rollbackMutation.error && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Rollback Failed</AlertTitle>
              <AlertDescription>
                {rollbackMutation.error instanceof Error
                  ? rollbackMutation.error.message
                  : 'Unknown error occurred'}
              </AlertDescription>
            </Alert>
          )}

          {/* Confirmation Checkboxes */}
          {analysis && !isLoading && (
            <div className="space-y-3 rounded-lg border p-4">
              <div className="flex items-start gap-3">
                <Checkbox
                  id="confirm-rollback"
                  checked={confirmedRollback}
                  onCheckedChange={(checked) => setConfirmedRollback(checked === true)}
                />
                <div className="flex-1">
                  <Label htmlFor="confirm-rollback" className="cursor-pointer font-medium">
                    I understand this will restore files
                  </Label>
                  <p className="text-xs text-muted-foreground">
                    This action will restore files from the snapshot and cannot be undone.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <Checkbox
                  id="preserve-changes"
                  checked={preserveChanges}
                  onCheckedChange={(checked) => setPreserveChanges(checked === true)}
                />
                <div className="flex-1">
                  <Label htmlFor="preserve-changes" className="cursor-pointer font-medium">
                    Preserve local changes (3-way merge)
                  </Label>
                  <p className="text-xs text-muted-foreground">
                    Attempt to merge uncommitted changes. Uncheck to discard all local modifications.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isRollingBack}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleRollback}
            disabled={!confirmedRollback || isLoading || isRollingBack || !!analysisError}
          >
            {isRollingBack ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Rolling Back...
              </>
            ) : (
              <>
                <RotateCcw className="mr-2 h-4 w-4" />
                Rollback to This Version
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
