/**
 * MergeModal Component (UI-3.7)
 *
 * A three-pane comparison dialog for merging two memory items.
 * Shows source and target memories side-by-side with a strategy selector
 * and live preview of the merge result.
 *
 * Merge strategies:
 * - keep_target: Keep target content, deprecate source
 * - keep_source: Replace target content with source, deprecate source
 * - combine: Concatenate both contents with separator, deprecate source
 */

'use client';

import * as React from 'react';
import { useState, useEffect, useMemo, useCallback } from 'react';
import { Loader2, GitMerge } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '@/components/ui/select';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import { useMergeMemoryItems } from '@/hooks';
import type { MemoryItemResponse } from '@/sdk/models/MemoryItemResponse';
import { MemoryTypeBadge } from './memory-type-badge';
import {
  getConfidenceTier,
  getConfidenceColorClasses,
} from './memory-utils';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type MergeStrategy = 'keep_target' | 'keep_source' | 'combine';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface MergeModalProps {
  /** Whether the dialog is open. */
  open: boolean;
  /** Callback to control open state. */
  onOpenChange: (open: boolean) => void;
  /** The source memory item to merge from. */
  sourceMemory: MemoryItemResponse | null;
  /** Optional pre-selected target memory item. */
  targetMemory?: MemoryItemResponse | null;
  /** All available memories for target selection (source is excluded). */
  allMemories: MemoryItemResponse[];
  /** Callback after successful merge. */
  onSuccess?: () => void;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/** Compact memory preview pane showing type, content, and confidence. */
function MemoryPane({
  memory,
  label,
}: {
  memory: MemoryItemResponse;
  label: string;
}) {
  const confidencePercent = Math.round(memory.confidence * 100);
  const tier = getConfidenceTier(memory.confidence);
  const colors = getConfidenceColorClasses(tier);

  return (
    <div className="space-y-2">
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
        {label}
      </p>
      <div className="rounded-md border p-3 space-y-2">
        <MemoryTypeBadge type={memory.type} />
        <p className="text-sm leading-relaxed line-clamp-4">
          {memory.content}
        </p>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className={cn('font-medium', colors.text)}>
            {confidencePercent}% confidence
          </span>
          <span>-</span>
          <span>{memory.status}</span>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * MergeModal -- side-by-side merge dialog with strategy selection and preview.
 *
 * @example
 * ```tsx
 * <MergeModal
 *   open={mergeOpen}
 *   onOpenChange={setMergeOpen}
 *   sourceMemory={selectedMemory}
 *   allMemories={memories}
 *   onSuccess={() => toast({ title: "Merged!" })}
 * />
 * ```
 */
export function MergeModal({
  open,
  onOpenChange,
  sourceMemory,
  targetMemory: preselectedTarget,
  allMemories,
  onSuccess,
}: MergeModalProps) {
  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------
  const [targetId, setTargetId] = useState<string>('');
  const [strategy, setStrategy] = useState<MergeStrategy>('keep_target');
  const [customContent, setCustomContent] = useState('');

  // Reset state when dialog opens or source changes
  useEffect(() => {
    if (open) {
      setTargetId(preselectedTarget?.id ?? '');
      setStrategy('keep_target');
      setCustomContent('');
    }
  }, [open, preselectedTarget]);

  // ---------------------------------------------------------------------------
  // Derived data
  // ---------------------------------------------------------------------------

  /** Available targets: all memories excluding the source. */
  const availableTargets = useMemo(() => {
    if (!sourceMemory) return [];
    return allMemories.filter((m) => m.id !== sourceMemory.id);
  }, [allMemories, sourceMemory]);

  /** Resolved target memory object. */
  const targetMemory = useMemo(
    () => availableTargets.find((m) => m.id === targetId) ?? null,
    [availableTargets, targetId]
  );

  /** Preview of the merge result based on the selected strategy. */
  const mergePreview = useMemo(() => {
    if (!sourceMemory || !targetMemory) return '';

    switch (strategy) {
      case 'keep_target':
        return targetMemory.content;
      case 'keep_source':
        return sourceMemory.content;
      case 'combine':
        if (customContent) return customContent;
        return `${targetMemory.content}\n\n---\n\n${sourceMemory.content}`;
      default:
        return '';
    }
  }, [sourceMemory, targetMemory, strategy, customContent]);

  // Initialize customContent when switching to combine strategy
  useEffect(() => {
    if (strategy === 'combine' && sourceMemory && targetMemory && !customContent) {
      setCustomContent(
        `${targetMemory.content}\n\n---\n\n${sourceMemory.content}`
      );
    }
  }, [strategy, sourceMemory, targetMemory, customContent]);

  // ---------------------------------------------------------------------------
  // Mutation
  // ---------------------------------------------------------------------------
  const mergeMutation = useMergeMemoryItems({
    onSuccess: () => {
      onOpenChange(false);
      onSuccess?.();
    },
  });

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------
  const handleMerge = useCallback(() => {
    if (!sourceMemory || !targetId) return;

    mergeMutation.mutate({
      source_id: sourceMemory.id,
      target_id: targetId,
      strategy,
      merged_content: strategy === 'combine' ? mergePreview : undefined,
    });
  }, [sourceMemory, targetId, strategy, mergePreview, mergeMutation]);

  const canMerge = !!sourceMemory && !!targetId && !mergeMutation.isPending;

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  if (!sourceMemory) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <GitMerge className="h-5 w-5" />
            Merge Memories
          </DialogTitle>
          <DialogDescription>
            Merge two memory items using the selected strategy. The source
            memory will be deprecated after a successful merge.
          </DialogDescription>
        </DialogHeader>

        {/* Side-by-side comparison */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {/* Source pane */}
          <MemoryPane memory={sourceMemory} label="Source Memory" />

          {/* Target pane */}
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Target Memory
            </p>

            {/* Target selector */}
            <Select value={targetId} onValueChange={setTargetId}>
              <SelectTrigger aria-label="Select target memory">
                <SelectValue placeholder="Select target..." />
              </SelectTrigger>
              <SelectContent>
                {availableTargets.map((m) => (
                  <SelectItem key={m.id} value={m.id}>
                    <span className="flex items-center gap-2">
                      <span className="capitalize text-xs text-muted-foreground">
                        [{m.type}]
                      </span>
                      <span className="truncate max-w-[200px]">
                        {m.content.slice(0, 60)}
                        {m.content.length > 60 ? '...' : ''}
                      </span>
                    </span>
                  </SelectItem>
                ))}
                {availableTargets.length === 0 && (
                  <SelectItem value="__none" disabled>
                    No other memories available
                  </SelectItem>
                )}
              </SelectContent>
            </Select>

            {/* Target preview */}
            {targetMemory && (
              <div className="rounded-md border p-3 space-y-2">
                <MemoryTypeBadge type={targetMemory.type} />
                <p className="text-sm leading-relaxed line-clamp-4">
                  {targetMemory.content}
                </p>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span
                    className={cn(
                      'font-medium',
                      getConfidenceColorClasses(
                        getConfidenceTier(targetMemory.confidence)
                      ).text
                    )}
                  >
                    {Math.round(targetMemory.confidence * 100)}% confidence
                  </span>
                  <span>-</span>
                  <span>{targetMemory.status}</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Strategy selection */}
        {targetMemory && (
          <>
            <div className="space-y-3">
              <Label className="text-sm font-medium">Strategy</Label>
              <RadioGroup
                value={strategy}
                onValueChange={(v) => setStrategy(v as MergeStrategy)}
                className="flex flex-wrap gap-4"
              >
                <div className="flex items-center gap-2">
                  <RadioGroupItem value="keep_target" id="strategy-keep-target" />
                  <Label htmlFor="strategy-keep-target" className="font-normal cursor-pointer">
                    Keep Target
                  </Label>
                </div>
                <div className="flex items-center gap-2">
                  <RadioGroupItem value="keep_source" id="strategy-keep-source" />
                  <Label htmlFor="strategy-keep-source" className="font-normal cursor-pointer">
                    Keep Source
                  </Label>
                </div>
                <div className="flex items-center gap-2">
                  <RadioGroupItem value="combine" id="strategy-combine" />
                  <Label htmlFor="strategy-combine" className="font-normal cursor-pointer">
                    Combine
                  </Label>
                </div>
              </RadioGroup>
            </div>

            {/* Preview / Editable combine content */}
            <div className="space-y-2">
              <Label className="text-sm font-medium">Preview</Label>
              {strategy === 'combine' ? (
                <Textarea
                  value={customContent}
                  onChange={(e) => setCustomContent(e.target.value)}
                  rows={5}
                  placeholder="Edit the combined content..."
                  aria-label="Combined merge content"
                />
              ) : (
                <div className="rounded-md border bg-muted/50 p-3">
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">
                    {mergePreview || 'Select a target memory to see preview'}
                  </p>
                </div>
              )}
            </div>
          </>
        )}

        {/* Mutation error */}
        {mergeMutation.error && (
          <p className="text-sm text-destructive">
            {mergeMutation.error.message || 'Merge failed. Please try again.'}
          </p>
        )}

        {/* Footer */}
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={mergeMutation.isPending}
          >
            Cancel
          </Button>
          <Button
            onClick={handleMerge}
            disabled={!canMerge}
          >
            {mergeMutation.isPending && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            )}
            Merge Memories
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
