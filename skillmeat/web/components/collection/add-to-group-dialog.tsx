'use client';

import { useState, useEffect } from 'react';
import { Layers, Plus, Loader2 } from 'lucide-react';
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
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { useGroups, useAddArtifactToGroup, useToast } from '@/hooks';
import type { Artifact } from '@/types/artifact';

export interface AddToGroupDialogProps {
  /** Control dialog open state */
  open: boolean;
  /** Callback when dialog open state changes */
  onOpenChange: (open: boolean) => void;
  /** The artifact to add to group(s) */
  artifact: Artifact;
  /** Collection ID to fetch groups from */
  collectionId: string;
  /** Callback invoked on successful addition */
  onSuccess?: () => void;
}

/**
 * Add to Group Dialog
 *
 * Allows users to add an artifact to one or more groups within a collection.
 *
 * Features:
 * - Checkbox list of available groups
 * - Multi-select support for adding to multiple groups
 * - Loading states during fetching and submission
 * - Empty state with action to create a group
 * - Error handling with toast notifications
 *
 * @example
 * ```tsx
 * <AddToGroupDialog
 *   open={isOpen}
 *   onOpenChange={setIsOpen}
 *   artifact={artifact}
 *   collectionId="default"
 *   onSuccess={() => console.log('Added!')}
 * />
 * ```
 */
export function AddToGroupDialog({
  open,
  onOpenChange,
  artifact,
  collectionId,
  onSuccess,
}: AddToGroupDialogProps) {
  const [selectedGroupIds, setSelectedGroupIds] = useState<Set<string>>(new Set());

  const { data: groupsData, isLoading } = useGroups(collectionId);
  const addArtifactToGroup = useAddArtifactToGroup();
  const { toast } = useToast();

  const groups = groupsData?.groups || [];

  // Reset selection when dialog closes
  useEffect(() => {
    if (!open) {
      setSelectedGroupIds(new Set());
    }
  }, [open]);

  const handleCheckboxChange = (groupId: string, checked: boolean) => {
    setSelectedGroupIds((prev) => {
      const next = new Set(prev);
      if (checked) {
        next.add(groupId);
      } else {
        next.delete(groupId);
      }
      return next;
    });
  };

  const handleSubmit = async () => {
    if (selectedGroupIds.size === 0) return;

    try {
      // Add artifact to each selected group
      for (const groupId of selectedGroupIds) {
        await addArtifactToGroup.mutateAsync({
          groupId,
          artifactId: artifact.id,
        });
      }

      // Success toast
      const groupCount = selectedGroupIds.size;
      toast({
        title: 'Added to group' + (groupCount > 1 ? 's' : ''),
        description:
          groupCount === 1
            ? `"${artifact.name}" has been added to the group.`
            : `"${artifact.name}" has been added to ${groupCount} groups.`,
      });

      onOpenChange(false);
      onSuccess?.();
    } catch (error) {
      console.error('Failed to add artifact to group:', error);
      toast({
        title: 'Failed to add to group',
        description: error instanceof Error ? error.message : 'An unexpected error occurred',
        variant: 'destructive',
      });
    }
  };

  const handleClose = () => {
    if (!addArtifactToGroup.isPending) {
      onOpenChange(false);
    }
  };

  const isPending = addArtifactToGroup.isPending;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Add to Group</DialogTitle>
          <DialogDescription>
            Add &quot;{artifact.name}&quot; to one or more groups in this collection.
          </DialogDescription>
        </DialogHeader>

        {/* Groups selection */}
        <div className="py-4">
          {isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          ) : groups.length === 0 ? (
            <div className="rounded-lg border border-dashed border-muted-foreground/25 p-6 text-center">
              <Layers className="mx-auto h-8 w-8 text-muted-foreground/50" />
              <p className="mt-2 text-sm text-muted-foreground">
                No groups in this collection yet.
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Create a group first to organize your artifacts.
              </p>
              <Button
                variant="ghost"
                size="sm"
                className="mt-3 text-primary hover:text-primary/90"
                onClick={() => onOpenChange(false)}
              >
                <Plus className="mr-2 h-4 w-4" />
                Create a group
              </Button>
            </div>
          ) : (
            <ScrollArea className="h-[200px] rounded-md border">
              <div className="p-2 space-y-1">
                {groups.map((group) => (
                  <div
                    key={group.id}
                    className="flex items-start space-x-3 py-2 px-2 rounded-md hover:bg-accent"
                  >
                    <Checkbox
                      id={`group-${group.id}`}
                      checked={selectedGroupIds.has(group.id)}
                      onCheckedChange={(checked) =>
                        handleCheckboxChange(group.id, checked === true)
                      }
                      disabled={isPending}
                      className="mt-0.5"
                    />
                    <div className="flex-1 min-w-0">
                      <Label
                        htmlFor={`group-${group.id}`}
                        className="text-sm font-medium cursor-pointer block"
                      >
                        {group.name}
                      </Label>
                      <div className="flex items-center gap-2 mt-0.5">
                        {group.description && (
                          <span className="text-xs text-muted-foreground truncate max-w-[200px]">
                            {group.description}
                          </span>
                        )}
                        <span className="text-xs text-muted-foreground shrink-0">
                          {group.artifact_count} artifact{group.artifact_count !== 1 ? 's' : ''}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isPending}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={selectedGroupIds.size === 0 || isPending || groups.length === 0}
          >
            {isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Adding...
              </>
            ) : (
              <>
                <Layers className="mr-2 h-4 w-4" />
                Add to Group{selectedGroupIds.size > 1 ? 's' : ''}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
