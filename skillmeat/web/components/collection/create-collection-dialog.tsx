'use client';

import { useState } from 'react';
import { FolderPlus } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useCreateCollection, useCollectionContext, useToast } from '@/hooks';
import type { CreateCollectionRequest } from '@/types/collections';

export interface CreateCollectionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: (collectionId: string) => void;
}

export function CreateCollectionDialog({
  open,
  onOpenChange,
  onSuccess,
}: CreateCollectionDialogProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [errors, setErrors] = useState<{
    name?: string;
    description?: string;
  }>({});

  const { toast } = useToast();
  const createMutation = useCreateCollection();
  const { setSelectedCollectionId, refreshCollections } = useCollectionContext();

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

  const handleCreate = async () => {
    if (!validateForm()) {
      return;
    }

    try {
      const requestBody: CreateCollectionRequest = {
        name: name.trim(),
      };

      const newCollection = await createMutation.mutateAsync(requestBody);

      toast({
        title: 'Collection created',
        description: `Successfully created collection "${name}"`,
      });

      // Refresh collections list
      refreshCollections();

      // Auto-select the new collection
      setSelectedCollectionId(newCollection.id);

      // Reset form
      setName('');
      setDescription('');
      setErrors({});

      // Close dialog and call success callback
      onOpenChange(false);
      onSuccess?.(newCollection.id);
    } catch (error) {
      console.error('Failed to create collection:', error);
      toast({
        title: 'Failed to create collection',
        description: error instanceof Error ? error.message : 'An unexpected error occurred',
        variant: 'destructive',
      });
    }
  };

  const handleClose = () => {
    if (!createMutation.isPending) {
      setName('');
      setDescription('');
      setErrors({});
      onOpenChange(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-primary/10 p-2">
              <FolderPlus className="h-5 w-5 text-primary" />
            </div>
            <div>
              <DialogTitle>Create Collection</DialogTitle>
              <DialogDescription>
                Create a new collection to organize your artifacts
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Name Input */}
          <div className="space-y-2">
            <Label htmlFor="name">
              Name <span className="text-destructive">*</span>
            </Label>
            <Input
              id="name"
              placeholder="My Collection"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                if (errors.name) {
                  setErrors((prev) => ({ ...prev, name: undefined }));
                }
              }}
              disabled={createMutation.isPending}
              className={errors.name ? 'border-destructive' : ''}
              autoFocus
            />
            {errors.name && <p className="text-sm text-destructive">{errors.name}</p>}
          </div>

          {/* Description Input */}
          <div className="space-y-2">
            <Label htmlFor="description">Description (Optional)</Label>
            <Textarea
              id="description"
              placeholder="A collection of useful skills..."
              value={description}
              onChange={(e) => {
                setDescription(e.target.value);
                if (errors.description) {
                  setErrors((prev) => ({ ...prev, description: undefined }));
                }
              }}
              disabled={createMutation.isPending}
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

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={createMutation.isPending}>
            Cancel
          </Button>
          <Button onClick={handleCreate} disabled={createMutation.isPending}>
            {createMutation.isPending ? 'Creating...' : 'Create Collection'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
