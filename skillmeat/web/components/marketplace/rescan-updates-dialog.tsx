/**
 * Rescan Updates Dialog
 *
 * Displays imported artifacts that have upstream updates available after a
 * marketplace source rescan. Users can select which artifacts to sync.
 *
 * Features:
 * - List of updated imports with checkboxes
 * - Auto-selection of items without local changes
 * - Warning badges for items with local changes
 * - Select all / Deselect all toggle
 * - Bulk sync operation with loading state
 * - Link to artifact detail for manual sync management
 */

'use client';

import { useState, useMemo, useCallback } from 'react';
import Link from 'next/link';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle,
  Check,
  RefreshCw,
  ExternalLink,
  Loader2,
  Package,
  Terminal,
  Bot,
  Server,
  Webhook,
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { apiRequest } from '@/lib/api';
import { useToast, sourceKeys } from '@/hooks';

// ============================================================================
// Types
// ============================================================================

export interface UpdatedImport {
  entryId: string;
  name: string;
  artifactType: string;
  currentSha: string;
  newSha: string;
  hasLocalChanges: boolean;
  importId: string;
}

export interface RescanUpdatesDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  sourceId: string;
  sourceName: string;
  updatedImports: UpdatedImport[];
  onSyncComplete?: () => void;
}

interface BulkSyncResponse {
  total: number;
  synced: number;
  skipped: number;
  failed: number;
  results: Array<{
    entry_id: string;
    artifact_name: string;
    success: boolean;
    message: string;
    has_conflicts: boolean;
    conflicts: string[] | null;
  }>;
}

// ============================================================================
// Icon Mapping
// ============================================================================

type ArtifactType = 'skill' | 'command' | 'agent' | 'mcp' | 'mcp_server' | 'hook';

const artifactTypeIcons: Record<ArtifactType, React.ComponentType<{ className?: string }>> = {
  skill: Package,
  command: Terminal,
  agent: Bot,
  mcp: Server,
  mcp_server: Server,
  hook: Webhook,
};

const artifactTypeIconColors: Record<ArtifactType, string> = {
  skill: 'text-blue-600 dark:text-blue-400',
  command: 'text-purple-600 dark:text-purple-400',
  agent: 'text-green-600 dark:text-green-400',
  mcp: 'text-orange-600 dark:text-orange-400',
  mcp_server: 'text-orange-600 dark:text-orange-400',
  hook: 'text-pink-600 dark:text-pink-400',
};

// ============================================================================
// Component
// ============================================================================

/**
 * RescanUpdatesDialog - Dialog for syncing updated imported artifacts
 *
 * Shows a list of imported artifacts that have upstream updates available.
 * Users can select which artifacts to sync, with warnings for those with
 * local modifications.
 */
export function RescanUpdatesDialog({
  open,
  onOpenChange,
  sourceId,
  sourceName,
  updatedImports,
  onSyncComplete,
}: RescanUpdatesDialogProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Initialize selected items: auto-select those without local changes
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => {
    const initial = new Set<string>();
    for (const item of updatedImports) {
      if (!item.hasLocalChanges) {
        initial.add(item.entryId);
      }
    }
    return initial;
  });

  // Track if user has been warned about local changes
  const [hasConfirmedLocalChanges, setHasConfirmedLocalChanges] = useState(false);

  // Check if any selected items have local changes
  const selectedWithLocalChanges = useMemo(() => {
    return updatedImports.filter((item) => selectedIds.has(item.entryId) && item.hasLocalChanges);
  }, [updatedImports, selectedIds]);

  // Sync mutation
  const syncMutation = useMutation({
    mutationFn: async (entryIds: string[]) => {
      return apiRequest<BulkSyncResponse>(`/marketplace/sources/${sourceId}/sync-imported`, {
        method: 'POST',
        body: JSON.stringify({ artifact_ids: entryIds }),
      });
    },
    onSuccess: (data) => {
      // Invalidate relevant queries
      queryClient.invalidateQueries({ queryKey: sourceKeys.catalog(sourceId) });
      queryClient.invalidateQueries({ queryKey: sourceKeys.detail(sourceId) });
      queryClient.invalidateQueries({ queryKey: ['artifacts'] });
      queryClient.invalidateQueries({ queryKey: ['collections'] });

      // Show result toast
      if (data.failed === 0) {
        toast({
          title: 'Sync Complete',
          description: `Successfully synced ${data.synced} artifact${data.synced !== 1 ? 's' : ''}`,
        });
      } else {
        toast({
          title: 'Sync Partially Complete',
          description: `Synced ${data.synced}, failed ${data.failed}`,
          variant: 'destructive',
        });
      }

      // Close dialog and notify parent
      onOpenChange(false);
      onSyncComplete?.();
    },
    onError: (error) => {
      toast({
        title: 'Sync Failed',
        description: error instanceof Error ? error.message : 'An error occurred during sync',
        variant: 'destructive',
      });
    },
  });

  // Toggle individual item selection
  const toggleSelection = useCallback((entryId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(entryId)) {
        next.delete(entryId);
      } else {
        next.add(entryId);
      }
      return next;
    });
    // Reset confirmation if selection changes
    setHasConfirmedLocalChanges(false);
  }, []);

  // Select all / Deselect all
  const toggleSelectAll = useCallback(() => {
    if (selectedIds.size === updatedImports.length) {
      // Deselect all
      setSelectedIds(new Set());
    } else {
      // Select all
      setSelectedIds(new Set(updatedImports.map((item) => item.entryId)));
    }
    setHasConfirmedLocalChanges(false);
  }, [selectedIds.size, updatedImports]);

  // Handle sync action
  const handleSync = useCallback(() => {
    // If there are selected items with local changes and not confirmed, show warning
    if (selectedWithLocalChanges.length > 0 && !hasConfirmedLocalChanges) {
      setHasConfirmedLocalChanges(true);
      return;
    }

    // Proceed with sync
    syncMutation.mutate(Array.from(selectedIds));
  }, [selectedWithLocalChanges, hasConfirmedLocalChanges, selectedIds, syncMutation]);

  // Handle dialog close
  const handleClose = useCallback(() => {
    if (!syncMutation.isPending) {
      onOpenChange(false);
      // Reset state
      setSelectedIds(
        new Set(updatedImports.filter((item) => !item.hasLocalChanges).map((item) => item.entryId))
      );
      setHasConfirmedLocalChanges(false);
    }
  }, [syncMutation.isPending, onOpenChange, updatedImports]);

  const isAllSelected = selectedIds.size === updatedImports.length;
  const isSomeSelected = selectedIds.size > 0 && selectedIds.size < updatedImports.length;

  return (
    <Dialog open={open} onOpenChange={(o) => !o && handleClose()}>
      <DialogContent className="sm:max-w-[550px]">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-primary/10 p-2">
              <RefreshCw className="h-5 w-5 text-primary" />
            </div>
            <div>
              <DialogTitle>Upstream Updates Available</DialogTitle>
              <DialogDescription>
                {updatedImports.length} imported artifact{updatedImports.length !== 1 ? 's' : ''}{' '}
                from {sourceName} {updatedImports.length !== 1 ? 'have' : 'has'} updates available
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Select all toggle */}
          <div className="flex items-center justify-between border-b pb-3">
            <div className="flex items-center gap-2">
              <Checkbox
                id="select-all"
                checked={isAllSelected}
                onCheckedChange={toggleSelectAll}
                aria-label={isAllSelected ? 'Deselect all' : 'Select all'}
                ref={(el) => {
                  if (el && isSomeSelected) {
                    el.dataset.state = 'indeterminate';
                  }
                }}
              />
              <label htmlFor="select-all" className="cursor-pointer text-sm font-medium">
                {isAllSelected ? 'Deselect All' : 'Select All'}
              </label>
            </div>
            <span className="text-sm text-muted-foreground">
              {selectedIds.size} of {updatedImports.length} selected
            </span>
          </div>

          {/* Artifact list */}
          <div
            className={cn(
              'space-y-2',
              updatedImports.length > 5 && 'max-h-[300px] overflow-y-auto pr-2'
            )}
          >
            {updatedImports.map((item) => {
              const Icon = artifactTypeIcons[item.artifactType as ArtifactType] || Package;
              const iconColor =
                artifactTypeIconColors[item.artifactType as ArtifactType] || 'text-gray-500';
              const isSelected = selectedIds.has(item.entryId);

              return (
                <div
                  key={item.entryId}
                  className={cn(
                    'flex items-center gap-3 rounded-lg border p-3 transition-colors',
                    isSelected ? 'border-primary/50 bg-primary/5' : 'border-border'
                  )}
                >
                  <Checkbox
                    id={`item-${item.entryId}`}
                    checked={isSelected}
                    onCheckedChange={() => toggleSelection(item.entryId)}
                    aria-label={`Select ${item.name}`}
                  />

                  <Icon className={cn('h-4 w-4 shrink-0', iconColor)} aria-hidden="true" />

                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="truncate text-sm font-medium">{item.name}</span>
                      {item.hasLocalChanges && (
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Badge
                                variant="outline"
                                className="shrink-0 gap-1 border-yellow-500 bg-yellow-50 text-yellow-700 dark:bg-yellow-950/50 dark:text-yellow-400"
                              >
                                <AlertTriangle className="h-3 w-3" aria-hidden="true" />
                                Local changes
                              </Badge>
                            </TooltipTrigger>
                            <TooltipContent side="top" className="max-w-xs">
                              <p className="text-sm">
                                This artifact has local modifications. Syncing may overwrite your
                                changes. Consider managing sync from the artifact detail page.
                              </p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      )}
                    </div>
                    <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                      <code className="rounded bg-muted px-1.5 py-0.5">{item.currentSha}</code>
                      <span aria-hidden="true">→</span>
                      <code className="rounded bg-muted px-1.5 py-0.5">{item.newSha}</code>
                    </div>
                  </div>

                  {item.hasLocalChanges && (
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button variant="ghost" size="sm" className="shrink-0" asChild>
                            <Link
                              href={`/collection/artifact/${item.importId}`}
                              aria-label={`View ${item.name} details`}
                            >
                              <ExternalLink className="h-4 w-4" aria-hidden="true" />
                            </Link>
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent side="top">
                          <p className="text-sm">Manage sync manually</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  )}
                </div>
              );
            })}
          </div>

          {/* Warning for local changes confirmation */}
          {hasConfirmedLocalChanges && selectedWithLocalChanges.length > 0 && (
            <div className="rounded-lg border border-yellow-500/50 bg-yellow-50 p-3 dark:bg-yellow-950/30">
              <div className="flex items-start gap-2">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-yellow-600" />
                <div>
                  <p className="text-sm font-medium text-yellow-900 dark:text-yellow-100">
                    Confirm Sync with Local Changes
                  </p>
                  <p className="mt-1 text-xs text-yellow-800 dark:text-yellow-200">
                    {selectedWithLocalChanges.length} selected artifact
                    {selectedWithLocalChanges.length !== 1 ? 's have' : ' has'} local modifications
                    that may be overwritten. Click &quot;Sync Selected&quot; again to confirm.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={syncMutation.isPending}>
            Cancel
          </Button>
          <Button onClick={handleSync} disabled={selectedIds.size === 0 || syncMutation.isPending}>
            {syncMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                Syncing...
              </>
            ) : hasConfirmedLocalChanges && selectedWithLocalChanges.length > 0 ? (
              <>
                <Check className="mr-2 h-4 w-4" aria-hidden="true" />
                Confirm Sync
              </>
            ) : (
              <>
                <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
                Sync Selected ({selectedIds.size})
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
