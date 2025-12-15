'use client';

import { useState, useEffect } from 'react';
import { Edit, Trash2, AlertTriangle } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useUpdateCollection, useDeleteCollection } from '@/hooks/use-collections';
import { useCollectionContext } from '@/hooks/use-collection-context';
import { useToast } from '@/hooks/use-toast';
import type { Collection } from '@/types/collections';
import type { UpdateCollectionRequest } from '@/types/collections';

export interface EditCollectionDialogProps {
  collection: Collection;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
  onDelete?: () => void;
}

export function EditCollectionDialog({
  collection,
  open,
  onOpenChange,
  onSuccess,
  onDelete,
}: EditCollectionDialogProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [errors, setErrors] = useState<{
    name?: string;
    description?: string;
  }>({});

  const { toast } = useToast();
  const updateMutation = useUpdateCollection();
  const deleteMutation = useDeleteCollection();
  const { setSelectedCollectionId, refreshCollections } = useCollectionContext();

  // Initialize form with collection data when dialog opens
  useEffect(() => {
    if (open && collection) {
      setName(collection.name);
      setDescription('');
      setErrors({});
    }
  }, [open, collection]);

  const validateForm = (): boolean => {
    const newErrors: { name?: string; description?: string } = {};

    // Name validation: required, 1-255 chars
    if (!name.trim()) {
      newErrors.name = 'Collection name is required';
    } else if (name.length < 1 || name.length > 255) {
      newErrors.name = 'Name must be between 1 and 255 characters';
    }

    // Description validation: optional, max 1000 chars
    if (description && description.length > 1000) {
      newErrors.description = 'Description must be less than 1000 characters';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleUpdate = async () => {
    if (!validateForm()) {
      return;
    }

    // Check if anything actually changed
    const hasChanges = name.trim() !== collection.name || description.trim() !== '';

    if (!hasChanges) {
      toast({
        title: 'No changes',
        description: 'No changes were made to the collection',
      });
      handleClose();
      return;
    }

    try {
      const requestBody: UpdateCollectionRequest = {
        name: name.trim() !== collection.name ? name.trim() : undefined,
      };

      await updateMutation.mutateAsync({
        id: collection.id,
        data: requestBody,
      });

      toast({
        title: 'Collection updated',
        description: `Successfully updated collection "${name}"`,
      });

      // Refresh collections list
      refreshCollections();

      // Close dialog and call success callback
      onOpenChange(false);
      onSuccess?.();
    } catch (error) {
      console.error('Failed to update collection:', error);
      toast({
        title: 'Failed to update collection',
        description: error instanceof Error ? error.message : 'An unexpected error occurred',
        variant: 'destructive',
      });
    }
  };

  const handleDelete = async () => {
    try {
      await deleteMutation.mutateAsync(collection.id);

      toast({
        title: 'Collection deleted',
        description: `Successfully deleted collection "${collection.name}"`,
      });

      // Refresh collections list
      refreshCollections();

      // Navigate away from deleted collection
      setSelectedCollectionId(null);

      // Close dialogs and call delete callback
      setShowDeleteConfirm(false);
      onOpenChange(false);
      onDelete?.();
    } catch (error) {
      console.error('Failed to delete collection:', error);
      toast({
        title: 'Failed to delete collection',
        description: error instanceof Error ? error.message : 'An unexpected error occurred',
        variant: 'destructive',
      });
    }
  };

  const handleClose = () => {
    if (!updateMutation.isPending && !deleteMutation.isPending) {
      setName(collection.name);
      setDescription('');
      setErrors({});
      onOpenChange(false);
    }
  };

  return (
    <>
      <Dialog open={open} onOpenChange={handleClose}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-primary/10 p-2">
                <Edit className="h-5 w-5 text-primary" />
              </div>
              <div>
                <DialogTitle>Edit Collection</DialogTitle>
                <DialogDescription>Update collection metadata and settings</DialogDescription>
              </div>
            </div>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Collection ID (Read-only) */}
            <div className="space-y-2">
              <Label>Collection ID</Label>
              <div className="rounded-md bg-muted px-3 py-2 font-mono text-sm text-muted-foreground">
                {collection.id}
              </div>
              <p className="text-xs text-muted-foreground">
                {collection.artifact_count} {collection.artifact_count === 1 ? 'artifact' : 'artifacts'}
              </p>
            </div>

            {/* Name Input */}
            <div className="space-y-2">
              <Label htmlFor="edit-name">
                Name <span className="text-destructive">*</span>
              </Label>
              <Input
                id="edit-name"
                placeholder="My Collection"
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  if (errors.name) {
                    setErrors((prev) => ({ ...prev, name: undefined }));
                  }
                }}
                disabled={updateMutation.isPending}
                className={errors.name ? 'border-destructive' : ''}
              />
              {errors.name && <p className="text-sm text-destructive">{errors.name}</p>}
            </div>

            {/* Description Input */}
            <div className="space-y-2">
              <Label htmlFor="edit-description">Description (Optional)</Label>
              <Textarea
                id="edit-description"
                placeholder="A collection of useful skills..."
                value={description}
                onChange={(e) => {
                  setDescription(e.target.value);
                  if (errors.description) {
                    setErrors((prev) => ({ ...prev, description: undefined }));
                  }
                }}
                disabled={updateMutation.isPending}
                className={errors.description ? 'border-destructive' : ''}
                rows={3}
              />
              {errors.description && (
                <p className="text-sm text-destructive">{errors.description}</p>
              )}
              <p className="text-xs text-muted-foreground">
                Maximum 1000 characters
              </p>
            </div>
          </div>

          <DialogFooter className="flex-col gap-2 sm:flex-row sm:justify-between">
            <Button
              variant="destructive"
              onClick={() => setShowDeleteConfirm(true)}
              disabled={updateMutation.isPending || deleteMutation.isPending}
              className="sm:mr-auto"
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete Collection
            </Button>
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={handleClose}
                disabled={updateMutation.isPending || deleteMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                onClick={handleUpdate}
                disabled={updateMutation.isPending || deleteMutation.isPending}
              >
                {updateMutation.isPending ? 'Updating...' : 'Update Collection'}
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-destructive/10 p-2">
                <AlertTriangle className="h-5 w-5 text-destructive" />
              </div>
              <div>
                <AlertDialogTitle>Are you sure?</AlertDialogTitle>
                <AlertDialogDescription>
                  This will delete the collection &quot;{collection.name}&quot; and remove all
                  artifact associations.
                </AlertDialogDescription>
              </div>
            </div>
          </AlertDialogHeader>

          <div className="rounded-lg border border-muted bg-muted/50 p-4">
            <p className="text-sm text-muted-foreground">
              <strong>Note:</strong> The artifacts themselves will not be deleted. They will
              remain in your collection and can be added to other collections.
            </p>
          </div>

          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteMutation.isPending}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? 'Deleting...' : 'Delete Collection'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
