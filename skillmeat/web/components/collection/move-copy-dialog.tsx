'use client';

import { useState } from 'react';
import { Copy, MoveRight, FolderOpen, FolderPlus } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  useCollectionContext,
  useAddArtifactToCollection,
  useRemoveArtifactFromCollection,
  useToast,
} from '@/hooks';
import type { Artifact } from '@/types/artifact';
import { CreateCollectionDialog } from '@/components/collection/create-collection-dialog';

type OperationType = 'move' | 'copy';

export interface MoveCopyDialogProps {
  /** Control dialog open state */
  open: boolean;
  /** Callback when dialog open state changes */
  onOpenChange: (open: boolean) => void;
  /** Artifacts to move or copy - supports single or multiple */
  artifacts: Artifact[];
  /** Current collection ID (for move operation) */
  sourceCollectionId?: string;
  /** Callback invoked on successful move/copy */
  onSuccess?: () => void;
}

/**
 * Move/Copy to Collections Dialog
 *
 * Allows users to move or copy artifacts between collections.
 * - Copy: Add artifact to target collection (artifact stays in source)
 * - Move: Add to target, remove from source
 *
 * Features:
 * - Operation toggle (Copy/Move)
 * - Collection selection with artifact counts
 * - Batch support for multiple artifacts
 * - Loading states during operations
 * - Error handling with toast notifications
 *
 * @example
 * ```tsx
 * <MoveCopyDialog
 *   open={isOpen}
 *   onOpenChange={setIsOpen}
 *   artifacts={[artifact]}
 *   sourceCollectionId="default"
 *   onSuccess={() => console.log('Done!')}
 * />
 * ```
 */
export function MoveCopyDialog({
  open,
  onOpenChange,
  artifacts,
  sourceCollectionId,
  onSuccess,
}: MoveCopyDialogProps) {
  const [operation, setOperation] = useState<OperationType>('copy');
  const [selectedCollectionId, setSelectedCollectionId] = useState<string | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  const { collections } = useCollectionContext();
  const addArtifact = useAddArtifactToCollection();
  const removeArtifact = useRemoveArtifactFromCollection();
  const { toast } = useToast();

  // Filter out source collection for move operation
  const availableCollections = collections.filter((c) => c.id !== sourceCollectionId);

  const handleSubmit = async () => {
    if (!selectedCollectionId || artifacts.length === 0) return;

    try {
      for (const artifact of artifacts) {
        // Add to target collection
        await addArtifact.mutateAsync({
          collectionId: selectedCollectionId,
          artifactId: artifact.id,
        });

        // If move, remove from source
        if (operation === 'move' && sourceCollectionId) {
          await removeArtifact.mutateAsync({
            collectionId: sourceCollectionId,
            artifactId: artifact.id,
          });
        }
      }

      // Success toast
      const firstArtifact = artifacts[0];
      toast({
        title: `${operation === 'move' ? 'Moved' : 'Copied'} successfully`,
        description:
          artifacts.length === 1 && firstArtifact
            ? `"${firstArtifact.name}" has been ${operation === 'move' ? 'moved' : 'copied'} to the collection.`
            : `${artifacts.length} artifacts have been ${operation === 'move' ? 'moved' : 'copied'} to the collection.`,
      });

      onOpenChange(false);
      onSuccess?.();
    } catch (error) {
      console.error(`Failed to ${operation} artifacts:`, error);
      toast({
        title: `Failed to ${operation} artifacts`,
        description: error instanceof Error ? error.message : 'An unexpected error occurred',
        variant: 'destructive',
      });
    }
  };

  const handleClose = () => {
    if (!addArtifact.isPending && !removeArtifact.isPending) {
      setSelectedCollectionId(null);
      onOpenChange(false);
    }
  };

  const isPending = addArtifact.isPending || removeArtifact.isPending;
  const firstArtifact = artifacts[0];

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{operation === 'move' ? 'Move' : 'Copy'} to Collection</DialogTitle>
          <DialogDescription>
            {artifacts.length === 1 && firstArtifact
              ? `${operation === 'move' ? 'Move' : 'Copy'} "${firstArtifact.name}" to another collection.`
              : `${operation === 'move' ? 'Move' : 'Copy'} ${artifacts.length} artifacts to another collection.`}
          </DialogDescription>
        </DialogHeader>

        {/* Operation toggle */}
        <div className="flex items-center gap-4 py-2">
          <Button
            variant={operation === 'copy' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setOperation('copy')}
            disabled={isPending}
          >
            <Copy className="mr-2 h-4 w-4" />
            Copy
          </Button>
          <Button
            variant={operation === 'move' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setOperation('move')}
            disabled={!sourceCollectionId || isPending}
          >
            <MoveRight className="mr-2 h-4 w-4" />
            Move
          </Button>
        </div>

        {/* Collection selection */}
        <div className="py-4">
          <Label className="text-sm font-medium">Select collection</Label>
          <ScrollArea className="mt-2 h-[200px] rounded-md border">
            <RadioGroup
              value={selectedCollectionId ?? ''}
              onValueChange={setSelectedCollectionId}
              className="p-2"
              disabled={isPending}
            >
              {availableCollections.length === 0 ? (
                <div className="space-y-3 p-4 text-center">
                  <p className="text-sm text-muted-foreground">No other collections available.</p>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowCreateDialog(true)}
                    className="text-primary hover:text-primary/90"
                  >
                    <FolderPlus className="mr-2 h-4 w-4" />
                    Create one now
                  </Button>
                </div>
              ) : (
                availableCollections.map((collection) => (
                  <div
                    key={collection.id}
                    className="flex items-center space-x-2 rounded-md px-2 py-2 hover:bg-accent"
                  >
                    <RadioGroupItem value={collection.id} id={collection.id} />
                    <Label
                      htmlFor={collection.id}
                      className="flex flex-1 cursor-pointer items-center gap-2"
                    >
                      <FolderOpen className="h-4 w-4 text-muted-foreground" />
                      <span>{collection.name}</span>
                      <span className="ml-auto text-xs text-muted-foreground">
                        {collection.artifact_count} artifact
                        {collection.artifact_count !== 1 ? 's' : ''}
                      </span>
                    </Label>
                  </div>
                ))
              )}
            </RadioGroup>
          </ScrollArea>
        </div>

        {/* Info message */}
        {operation === 'move' && sourceCollectionId && (
          <div className="rounded-md bg-muted p-3">
            <p className="text-sm text-muted-foreground">
              Moving will remove the artifact{artifacts.length > 1 ? 's' : ''} from the current
              collection.
            </p>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isPending}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!selectedCollectionId || isPending}>
            {isPending ? (
              'Processing...'
            ) : operation === 'move' ? (
              <>
                <MoveRight className="mr-2 h-4 w-4" />
                Move
              </>
            ) : (
              <>
                <Copy className="mr-2 h-4 w-4" />
                Copy
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>

      <CreateCollectionDialog open={showCreateDialog} onOpenChange={setShowCreateDialog} />
    </Dialog>
  );
}
