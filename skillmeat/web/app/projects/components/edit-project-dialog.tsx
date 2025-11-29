'use client';

import { useState, useEffect } from 'react';
import { Edit } from 'lucide-react';
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
import { useUpdateProject } from '@/hooks/useProjects';
import { useToast } from '@/hooks/use-toast';
import type { ProjectSummary } from '@/types/project';
import type { ProjectUpdateRequest } from '@/sdk';

export interface EditProjectDialogProps {
  project: ProjectSummary;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function EditProjectDialog({
  project,
  open,
  onOpenChange,
  onSuccess,
}: EditProjectDialogProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [errors, setErrors] = useState<{
    name?: string;
  }>({});

  const { toast } = useToast();
  const updateMutation = useUpdateProject();

  // Initialize form with project data when dialog opens
  useEffect(() => {
    if (open && project) {
      setName(project.name);
      setDescription('');
      setErrors({});
    }
  }, [open, project]);

  const validateForm = (): boolean => {
    const newErrors: { name?: string } = {};

    // Name validation: 1-100 chars, alphanumeric + hyphens/underscores
    if (!name.trim()) {
      newErrors.name = 'Project name is required';
    } else if (name.length < 1 || name.length > 100) {
      newErrors.name = 'Name must be between 1 and 100 characters';
    } else if (!/^[a-zA-Z0-9_-]+$/.test(name)) {
      newErrors.name = 'Name can only contain letters, numbers, hyphens, and underscores';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleUpdate = async () => {
    if (!validateForm()) {
      return;
    }

    // Check if anything actually changed
    const hasChanges = name.trim() !== project.name || description.trim() !== '';

    if (!hasChanges) {
      toast({
        title: 'No changes',
        description: 'No changes were made to the project',
      });
      handleClose();
      return;
    }

    try {
      const requestBody: ProjectUpdateRequest = {
        name: name.trim() !== project.name ? name.trim() : null,
        description: description.trim() || null,
      };

      await updateMutation.mutateAsync({
        id: project.id,
        data: requestBody,
      });

      toast({
        title: 'Project updated',
        description: `Successfully updated project "${name}"`,
      });

      // Close dialog and call success callback
      onOpenChange(false);
      onSuccess?.();
    } catch (error) {
      console.error('Failed to update project:', error);
      toast({
        title: 'Failed to update project',
        description: error instanceof Error ? error.message : 'An unexpected error occurred',
        variant: 'destructive',
      });
    }
  };

  const handleClose = () => {
    if (!updateMutation.isPending) {
      setName(project.name);
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
              <Edit className="h-5 w-5 text-primary" />
            </div>
            <div>
              <DialogTitle>Edit Project</DialogTitle>
              <DialogDescription>Update project metadata and settings</DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Project Path (Read-only) */}
          <div className="space-y-2">
            <Label>Project Path</Label>
            <div className="rounded-md bg-muted px-3 py-2 font-mono text-sm text-muted-foreground">
              {project.path}
            </div>
            <p className="text-xs text-muted-foreground">Path cannot be changed after creation</p>
          </div>

          {/* Name Input */}
          <div className="space-y-2">
            <Label htmlFor="edit-name">
              Project Name <span className="text-destructive">*</span>
            </Label>
            <Input
              id="edit-name"
              placeholder="my-project"
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
            <p className="text-xs text-muted-foreground">
              Letters, numbers, hyphens, and underscores only
            </p>
          </div>

          {/* Description Input */}
          <div className="space-y-2">
            <Label htmlFor="edit-description">Description (Optional)</Label>
            <Textarea
              id="edit-description"
              placeholder="Brief description of this project..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={updateMutation.isPending}
              rows={3}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={updateMutation.isPending}>
            Cancel
          </Button>
          <Button onClick={handleUpdate} disabled={updateMutation.isPending}>
            {updateMutation.isPending ? 'Updating...' : 'Update Project'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
