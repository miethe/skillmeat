'use client';

import { useState, useEffect } from 'react';
import { Copy, Loader2, FolderOpen } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { useCollections, useCopyGroup, useToast } from '@/hooks';
import type { Group } from '@/types/groups';

export interface CopyGroupDialogProps {
  /** Control dialog open state */
  open: boolean;
  /** Callback when dialog open state changes */
  onOpenChange: (open: boolean) => void;
  /** The source group to copy */
  group: Group;
  /** Current collection ID (to exclude from targets) */
  sourceCollectionId: string;
  /** Callback invoked on successful copy */
  onSuccess?: () => void;
}

/**
 * Copy Group Dialog
 *
 * Allows users to copy a group (with all its artifacts) to another collection.
 *
 * Features:
 * - Radio button selection for target collection
 * - Source collection excluded from options
 * - Loading states during fetching and submission
 * - Empty state when no other collections available
 * - Error handling with toast notifications
 *
 * @example
 * ```tsx
 * <CopyGroupDialog
 *   open={isOpen}
 *   onOpenChange={setIsOpen}
 *   group={selectedGroup}
 *   sourceCollectionId="current-collection-id"
 *   onSuccess={() => console.log('Copied!')}
 * />
 * ```
 */
export function CopyGroupDialog({
  open,
  onOpenChange,
  group,
  sourceCollectionId,
  onSuccess,
}: CopyGroupDialogProps) {
  const [selectedCollectionId, setSelectedCollectionId] = useState<string | null>(null);

  const { data: collectionsData, isLoading } = useCollections();
  const copyGroupMutation = useCopyGroup();
  const { toast } = useToast();

  // Filter out the source collection from available targets
  const availableCollections = (collectionsData?.items || []).filter(
    (collection) => collection.id !== sourceCollectionId
  );

  // Reset state when dialog closes
  useEffect(() => {
    if (!open) {
      setSelectedCollectionId(null);
    }
  }, [open]);

  const handleCollectionSelect = (id: string) => {
    setSelectedCollectionId(id);
  };

  const handleSubmit = async () => {
    if (!selectedCollectionId) return;

    const targetCollection = availableCollections.find((c) => c.id === selectedCollectionId);

    try {
      await copyGroupMutation.mutateAsync({
        groupId: group.id,
        targetCollectionId: selectedCollectionId,
      });

      toast({
        title: 'Group copied',
        description: `"${group.name}" has been copied to ${targetCollection?.name || 'the selected collection'}.`,
      });

      onOpenChange(false);
      onSuccess?.();
    } catch (error) {
      console.error('Failed to copy group:', error);
      toast({
        title: 'Failed to copy group',
        description: error instanceof Error ? error.message : 'An unexpected error occurred',
        variant: 'destructive',
      });
    }
  };

  const handleClose = () => {
    if (!copyGroupMutation.isPending) {
      onOpenChange(false);
    }
  };

  const isPending = copyGroupMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Copy Group to Collection</DialogTitle>
          <DialogDescription>
            Copy &ldquo;{group.name}&rdquo; ({group.artifact_count} artifact
            {group.artifact_count !== 1 ? 's' : ''}) to another collection.
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          <Label className="text-sm font-medium">Select target collection</Label>

          {isLoading ? (
            <div className="mt-2 space-y-2">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          ) : availableCollections.length === 0 ? (
            <div className="mt-2 rounded-lg border border-dashed border-muted-foreground/25 p-6 text-center">
              <FolderOpen className="mx-auto h-8 w-8 text-muted-foreground/50" aria-hidden="true" />
              <p className="mt-2 text-sm text-muted-foreground">No other collections available.</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Create another collection first to copy this group.
              </p>
            </div>
          ) : (
            <>
              <ScrollArea className="mt-2 h-[200px] rounded-md border">
                <RadioGroup
                  value={selectedCollectionId ?? ''}
                  onValueChange={handleCollectionSelect}
                  className="p-2"
                  aria-label="Target collection selection"
                >
                  {availableCollections.map((collection) => (
                    <div
                      key={collection.id}
                      className="flex items-center space-x-2 rounded-md px-2 py-2 hover:bg-accent"
                    >
                      <RadioGroupItem
                        value={collection.id}
                        id={`collection-${collection.id}`}
                        disabled={isPending}
                        aria-label={`Select ${collection.name}`}
                      />
                      <Label
                        htmlFor={`collection-${collection.id}`}
                        className="flex flex-1 cursor-pointer items-center gap-2"
                      >
                        <FolderOpen className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                        <span>{collection.name}</span>
                        {collection.artifact_count !== undefined && (
                          <span className="ml-auto text-xs text-muted-foreground">
                            {collection.artifact_count} artifact
                            {collection.artifact_count !== 1 ? 's' : ''}
                          </span>
                        )}
                      </Label>
                    </div>
                  ))}
                </RadioGroup>
              </ScrollArea>

              <p className="mt-3 text-xs text-muted-foreground">
                The group and its artifacts will be copied to the selected collection. Original
                group remains unchanged.
              </p>
            </>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isPending}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!selectedCollectionId || isPending || availableCollections.length === 0}
            aria-label="Copy group to selected collection"
          >
            {isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                <span>Copying...</span>
              </>
            ) : (
              <>
                <Copy className="mr-2 h-4 w-4" aria-hidden="true" />
                Copy Group
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
