/**
 * SyncConfirmationDialog - Unified confirmation dialog for all sync directions
 *
 * A single configurable dialog used for Deploy, Push, and Pull operations.
 * Uses the `useConflictCheck` hook (Phase 1) to fetch diffs and embeds
 * the existing `DiffViewer` component for change preview.
 *
 * Direction determines labels, title, warning text, and button labels:
 * - deploy: Collection -> Project
 * - push:   Project -> Collection
 * - pull:   Source -> Collection
 */
'use client';

import { useMemo } from 'react';
import { useConflictCheck } from '@/hooks';
import { DiffViewer } from '@/components/entity/diff-viewer';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  ArrowDown,
  ArrowUp,
  Upload,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Artifact } from '@/types/artifact';
import type { ConflictCheckDirection } from '@/hooks';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface SyncConfirmationDialogProps {
  /** Sync direction: deploy, push, or pull */
  direction: ConflictCheckDirection;
  /** Artifact being synced */
  artifact: Artifact;
  /** Project path for deploy/push directions */
  projectPath: string;
  /** Controlled open state */
  open: boolean;
  /** Open state change handler */
  onOpenChange: (open: boolean) => void;
  /** Execute with overwrite strategy */
  onOverwrite: () => void;
  /** Route to merge workflow */
  onMerge: () => void;
  /** Optional cancel callback */
  onCancel?: () => void;
}

// ---------------------------------------------------------------------------
// Direction configuration
// ---------------------------------------------------------------------------

interface DirectionConfig {
  title: string;
  leftLabel: string;
  rightLabel: string;
  warningText: string;
  conflictWarning: string;
  confirmLabel: string;
  icon: typeof Upload;
}

const DIRECTION_CONFIG: Record<ConflictCheckDirection, DirectionConfig> = {
  deploy: {
    title: 'Deploy to Project',
    leftLabel: 'Collection',
    rightLabel: 'Project',
    warningText: 'This will overwrite project files with collection versions.',
    conflictWarning:
      'Both the collection and project have changes to the same files. Consider merging to avoid losing project modifications.',
    confirmLabel: 'Deploy',
    icon: Upload,
  },
  push: {
    title: 'Push to Collection',
    leftLabel: 'Project',
    rightLabel: 'Collection',
    warningText: 'This will overwrite collection files with project versions.',
    conflictWarning:
      'Both the project and collection have diverged. Consider merging to preserve collection changes.',
    confirmLabel: 'Push Changes',
    icon: ArrowUp,
  },
  pull: {
    title: 'Pull from Source',
    leftLabel: 'Source',
    rightLabel: 'Collection',
    warningText: 'This will overwrite collection files with upstream source.',
    conflictWarning:
      'Both the source and collection have changes. Consider merging to preserve your local modifications.',
    confirmLabel: 'Pull Changes',
    icon: ArrowDown,
  },
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function SyncConfirmationDialog({
  direction,
  artifact,
  projectPath,
  open,
  onOpenChange,
  onOverwrite,
  onMerge,
  onCancel,
}: SyncConfirmationDialogProps) {
  const config = DIRECTION_CONFIG[direction];
  const DirectionIcon = config.icon;

  // Fetch diff data only when dialog is open
  const { diffData, hasChanges, hasConflicts, targetHasChanges, isLoading, error } =
    useConflictCheck(direction, artifact.id, {
      projectPath,
      enabled: open,
    });

  // Compute summary text from diff response
  const summaryText = useMemo(() => {
    const summary = diffData?.summary ?? {};
    const parts = [
      summary.added && `${summary.added} added`,
      summary.modified && `${summary.modified} modified`,
      summary.deleted && `${summary.deleted} deleted`,
    ].filter(Boolean);
    return parts.join(', ');
  }, [diffData?.summary]);

  // Filter out unchanged files for the DiffViewer
  const changedFiles = useMemo(
    () => (diffData?.files ?? []).filter((f) => f.status !== 'unchanged'),
    [diffData?.files]
  );

  // Total changed file count
  const changedCount = changedFiles.length;

  const handleCancel = () => {
    onCancel?.();
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[90vh] max-w-4xl flex-col overflow-hidden">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <DirectionIcon className="h-5 w-5" />
            <DialogTitle>{config.title}</DialogTitle>
          </div>
          <DialogDescription>{config.warningText}</DialogDescription>
        </DialogHeader>

        {/* Content area */}
        <div className="flex-1 overflow-auto">
          {/* Loading state */}
          {isLoading && (
            <div className="space-y-4 p-4">
              <Skeleton className="h-6 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
              <Skeleton className="h-48 w-full" />
              <Skeleton className="h-4 w-2/3" />
            </div>
          )}

          {/* Error state */}
          {!isLoading && error && (
            <Alert variant="destructive" className="m-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Failed to load diff: {error.message || 'An unexpected error occurred.'}
                {' '}Please close the dialog and try again.
              </AlertDescription>
            </Alert>
          )}

          {/* No changes state */}
          {!isLoading && !error && !hasChanges && (
            <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
              <CheckCircle2 className="h-12 w-12 text-green-500" />
              <div>
                <p className="text-lg font-medium">No changes detected</p>
                <p className="text-sm text-muted-foreground">
                  All files are already in sync. Safe to proceed.
                </p>
              </div>
            </div>
          )}

          {/* Has changes state */}
          {!isLoading && !error && hasChanges && (
            <div className="flex flex-col gap-3">
              {/* Conflict warning */}
              {hasConflicts && (
                <Alert variant="destructive" className="mx-4 mt-2">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>{config.conflictWarning}</AlertDescription>
                </Alert>
              )}

              {/* Summary line */}
              <div className="px-4 text-sm text-muted-foreground">
                {changedCount} {changedCount === 1 ? 'file' : 'files'} changed
                {summaryText ? ` (${summaryText})` : ''}
              </div>

              {/* Diff viewer */}
              <div className="h-[50vh] min-h-[300px]">
                <DiffViewer
                  files={changedFiles}
                  leftLabel={config.leftLabel}
                  rightLabel={config.rightLabel}
                  previewMode
                />
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <DialogFooter className="gap-2 sm:gap-2">
          <Button variant="outline" onClick={handleCancel} aria-label="Cancel sync operation">
            Cancel
          </Button>

          {/* Merge button: only shown when there are changes */}
          {hasChanges && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="inline-flex">
                    <Button
                      variant={targetHasChanges ? 'secondary' : 'ghost'}
                      onClick={onMerge}
                      disabled={!targetHasChanges}
                      aria-label={
                        targetHasChanges
                          ? 'Open merge workflow'
                          : 'Merge unavailable: no local changes to merge'
                      }
                    >
                      Merge
                    </Button>
                  </span>
                </TooltipTrigger>
                {!targetHasChanges && (
                  <TooltipContent>
                    <p>No local changes to merge</p>
                  </TooltipContent>
                )}
              </Tooltip>
            </TooltipProvider>
          )}

          {/* Overwrite / Confirm button */}
          <Button
            variant={hasChanges ? 'destructive' : 'default'}
            onClick={onOverwrite}
            disabled={isLoading}
            aria-label={hasChanges ? config.confirmLabel : 'Confirm sync operation'}
            className={cn(!hasChanges && 'min-w-[100px]')}
          >
            {hasChanges ? config.confirmLabel : 'Confirm'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
