/**
 * Bulk Tag Application Dialog
 *
 * Dialog for applying tags to multiple catalog artifacts organized by directory.
 * Users can select directories and assign tags to all artifacts within each.
 *
 * Features:
 * - Directory grouping from catalog entries
 * - Checkbox selection for directories
 * - Artifact count per directory
 * - Tag input with autocomplete from existing tags
 * - Path-based suggested tags
 * - Loading state during apply operation
 * - Progress indicator during bulk operations
 * - Full accessibility support
 *
 * @example
 * ```tsx
 * // With external onApply callback
 * <BulkTagDialog
 *   open={showDialog}
 *   onOpenChange={setShowDialog}
 *   entries={catalogEntries}
 *   onApply={handleBulkTagApply}
 * />
 *
 * // With integrated bulk tag hook (recommended)
 * <BulkTagDialogWithHook
 *   open={showDialog}
 *   onOpenChange={setShowDialog}
 *   entries={catalogEntries}
 *   sourceId="source-123"
 *   onSuccess={(result) => console.log(`Tagged ${result.totalUpdated} artifacts`)}
 * />
 * ```
 */

'use client';

import { useState, useMemo, useCallback } from 'react';
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
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Progress } from '@/components/ui/progress';
import { Loader2, FolderOpen } from 'lucide-react';
import { cn } from '@/lib/utils';
import { groupByDirectory } from '@/lib/utils/directory-utils';
import { generateTagSuggestions } from '@/lib/utils/tag-suggestions';
import { DirectoryTagInput } from '@/components/marketplace/directory-tag-input';
import { useBulkTagApply } from '@/hooks/use-bulk-tag-apply';
import type { CatalogEntry } from '@/types/marketplace';
import type { BulkTagResult } from '@/lib/utils/bulk-tag-apply';

export interface BulkTagDialogProps {
  /** Whether the dialog is open */
  open: boolean;
  /** Callback when open state changes */
  onOpenChange: (open: boolean) => void;
  /** Catalog entries to extract directories from */
  entries: CatalogEntry[];
  /** Callback when tags are applied. Map of directory path to tags. */
  onApply: (dirTags: Map<string, string[]>) => Promise<void>;
  /** Optional progress state from external hook */
  progress?: { current: number; total: number; percentage: number };
}

/**
 * Props for the integrated dialog with built-in bulk tag hook
 */
export interface BulkTagDialogWithHookProps {
  /** Whether the dialog is open */
  open: boolean;
  /** Callback when open state changes */
  onOpenChange: (open: boolean) => void;
  /** Catalog entries to extract directories from */
  entries: CatalogEntry[];
  /** Source ID for API calls */
  sourceId: string;
  /** Callback when operation succeeds */
  onSuccess?: (result: BulkTagResult) => void;
  /** Callback when operation fails */
  onError?: (error: Error) => void;
  /** Use simulation mode (no API calls) */
  simulationMode?: boolean;
}

interface DirectoryInfo {
  path: string;
  artifactCount: number;
  suggestedTags: string[];
}

/**
 * BulkTagDialog - Dialog for bulk tag application to catalog artifacts by directory
 */
export function BulkTagDialog({
  open,
  onOpenChange,
  entries,
  onApply,
  progress,
}: BulkTagDialogProps) {
  // Track selected directories
  const [selectedDirs, setSelectedDirs] = useState<Set<string>>(new Set());
  // Track tags for each directory
  const [dirTags, setDirTags] = useState<Map<string, string[]>>(new Map());
  // Loading state during apply
  const [isApplying, setIsApplying] = useState(false);

  // Group entries by parent directory and compute directory info
  const directoryInfo = useMemo<DirectoryInfo[]>(() => {
    const grouped = groupByDirectory(entries);
    const info: DirectoryInfo[] = [];

    for (const [path, groupEntries] of grouped) {
      // Skip root-level entries (empty string path)
      if (!path) continue;

      info.push({
        path,
        artifactCount: groupEntries.length,
        suggestedTags: generateTagSuggestions(path),
      });
    }

    // Sort alphabetically by path
    return info.sort((a, b) => a.path.localeCompare(b.path));
  }, [entries]);

  // Toggle directory selection
  const toggleDirectory = useCallback((path: string) => {
    setSelectedDirs((prev) => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  }, []);

  // Add a tag to a directory
  const addTag = useCallback((path: string, tag: string) => {
    const trimmedTag = tag.trim().toLowerCase();
    if (!trimmedTag) return;

    setDirTags((prev) => {
      const next = new Map(prev);
      const existing = next.get(path) || [];
      if (!existing.includes(trimmedTag)) {
        next.set(path, [...existing, trimmedTag]);
      }
      return next;
    });
  }, []);

  // Remove a tag from a directory
  const removeTag = useCallback((path: string, tag: string) => {
    setDirTags((prev) => {
      const next = new Map(prev);
      const existing = next.get(path) || [];
      next.set(path, existing.filter((t) => t !== tag));
      return next;
    });
  }, []);

  // Add suggested tag (also selects the directory)
  const addSuggestedTag = useCallback(
    (path: string, tag: string) => {
      // Also select the directory if not already selected
      setSelectedDirs((prev) => {
        const next = new Set(prev);
        next.add(path);
        return next;
      });
      addTag(path, tag);
    },
    [addTag]
  );

  // Handle apply
  const handleApply = useCallback(async () => {
    // Build map of only selected directories with their tags
    const result = new Map<string, string[]>();
    for (const path of selectedDirs) {
      const tags = dirTags.get(path) || [];
      result.set(path, tags);
    }

    setIsApplying(true);
    try {
      await onApply(result);
      // Reset state on success
      setSelectedDirs(new Set());
      setDirTags(new Map());
      onOpenChange(false);
    } finally {
      setIsApplying(false);
    }
  }, [selectedDirs, dirTags, onApply, onOpenChange]);

  // Handle cancel
  const handleCancel = useCallback(() => {
    // Reset state
    setSelectedDirs(new Set());
    setDirTags(new Map());
    onOpenChange(false);
  }, [onOpenChange]);

  // Check if apply button should be disabled
  const isApplyDisabled = selectedDirs.size === 0 || isApplying;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-2xl"
        onCloseAutoFocus={(e) => e.preventDefault()}
        aria-describedby="bulk-tag-dialog-description"
      >
        <DialogHeader>
          <DialogTitle>Bulk Tag Application</DialogTitle>
          <DialogDescription id="bulk-tag-dialog-description">
            Apply tags to all artifacts in selected directories. Tags will be
            merged with existing tags on each artifact.
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          {directoryInfo.length === 0 ? (
            <div
              className="flex flex-col items-center justify-center py-8 text-center text-muted-foreground"
              role="status"
              aria-label="No directories available"
            >
              <FolderOpen className="mb-2 h-8 w-8" aria-hidden="true" />
              <p>No directories found in catalog entries.</p>
              <p className="text-sm">
                Root-level artifacts cannot be bulk-tagged.
              </p>
            </div>
          ) : (
            <ScrollArea className="h-[400px] pr-4">
              <div
                className="space-y-4"
                role="group"
                aria-label="Directory list for bulk tagging"
              >
                {directoryInfo.map((dir) => {
                  const isSelected = selectedDirs.has(dir.path);
                  const currentTags = dirTags.get(dir.path) || [];

                  return (
                    <div
                      key={dir.path}
                      className={cn(
                        'rounded-lg border p-4 transition-colors',
                        isSelected
                          ? 'border-primary bg-primary/5'
                          : 'border-border'
                      )}
                    >
                      {/* Directory header with checkbox */}
                      <div className="flex items-start gap-3">
                        <Checkbox
                          id={`dir-${dir.path}`}
                          checked={isSelected}
                          onCheckedChange={() => toggleDirectory(dir.path)}
                          aria-label={`Select ${dir.path}`}
                        />
                        <div className="flex-1 min-w-0">
                          <Label
                            htmlFor={`dir-${dir.path}`}
                            className="flex items-center gap-2 cursor-pointer font-medium"
                          >
                            <FolderOpen
                              className="h-4 w-4 text-muted-foreground shrink-0"
                              aria-hidden="true"
                            />
                            <span className="truncate">{dir.path}</span>
                            <Badge
                              variant="secondary"
                              className="ml-auto shrink-0"
                            >
                              {dir.artifactCount}{' '}
                              {dir.artifactCount === 1
                                ? 'artifact'
                                : 'artifacts'}
                            </Badge>
                          </Label>

                          {/* Tag input section with autocomplete */}
                          <div className="mt-3">
                            <DirectoryTagInput
                              directoryPath={dir.path}
                              currentTags={currentTags}
                              suggestedTags={dir.suggestedTags}
                              onAddTag={(tag) => addTag(dir.path, tag)}
                              onRemoveTag={(tag) => removeTag(dir.path, tag)}
                              onAddSuggestedTag={(tag) =>
                                addSuggestedTag(dir.path, tag)
                              }
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </ScrollArea>
          )}
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={handleCancel}
            disabled={isApplying}
          >
            Cancel
          </Button>
          <div className="flex items-center gap-4">
            {/* Progress indicator */}
            {isApplying && progress && progress.total > 0 && (
              <div className="flex items-center gap-2 min-w-[120px]">
                <Progress
                  value={progress.percentage}
                  className="h-2 w-20"
                  aria-label="Tag application progress"
                />
                <span className="text-xs text-muted-foreground">
                  {progress.current}/{progress.total}
                </span>
              </div>
            )}
            <Button
              type="button"
              onClick={handleApply}
              disabled={isApplyDisabled}
              aria-describedby={
                isApplyDisabled && !isApplying
                  ? 'apply-button-hint'
                  : undefined
              }
            >
              {isApplying ? (
                <>
                  <Loader2
                    className="mr-2 h-4 w-4 animate-spin"
                    aria-hidden="true"
                  />
                  Applying...
                </>
              ) : (
                <>Apply Tags</>
              )}
            </Button>
          </div>
          {isApplyDisabled && !isApplying && (
            <span id="apply-button-hint" className="sr-only">
              Select at least one directory to apply tags
            </span>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/**
 * BulkTagDialogWithHook - Dialog with integrated bulk tag apply hook
 *
 * This is a convenience wrapper that combines the BulkTagDialog with the
 * useBulkTagApply hook. Use this when you want automatic API integration
 * without managing the hook externally.
 *
 * @example
 * ```tsx
 * <BulkTagDialogWithHook
 *   open={showDialog}
 *   onOpenChange={setShowDialog}
 *   entries={catalogEntries}
 *   sourceId="source-123"
 *   onSuccess={(result) => {
 *     console.log(`Tagged ${result.totalUpdated} artifacts`);
 *   }}
 * />
 * ```
 */
export function BulkTagDialogWithHook({
  open,
  onOpenChange,
  entries,
  sourceId,
  onSuccess,
  onError,
  simulationMode = false,
}: BulkTagDialogWithHookProps) {
  const bulkTagApply = useBulkTagApply({
    entries,
    sourceId,
    simulationMode,
    onSuccess: (result) => {
      onSuccess?.(result);
      // Close dialog on successful completion
      if (result.totalFailed === 0) {
        onOpenChange(false);
      }
    },
    onError,
  });

  // Wrap mutation to match expected signature
  const handleApply = useCallback(
    async (dirTags: Map<string, string[]>) => {
      await bulkTagApply.mutateAsync(dirTags);
    },
    [bulkTagApply]
  );

  return (
    <BulkTagDialog
      open={open}
      onOpenChange={onOpenChange}
      entries={entries}
      onApply={handleApply}
      progress={bulkTagApply.progress}
    />
  );
}
