'use client';

import { useState } from 'react';
import { Folder, Plus } from 'lucide-react';
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
import { useCreateProject, useToast } from '@/hooks';
import type { ProjectCreateRequest } from '@/sdk';

export interface CreateProjectDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: (project?: ProjectDetail) => void;
}

interface ProjectDetail {
  id: string;
  path: string;
  name: string;
  deployment_count: number;
  last_deployment?: string;
}

export function CreateProjectDialog({ open, onOpenChange, onSuccess }: CreateProjectDialogProps) {
  const [name, setName] = useState('');
  const [path, setPath] = useState('');
  const [description, setDescription] = useState('');
  const [errors, setErrors] = useState<{
    name?: string;
    path?: string;
  }>({});

  const { toast } = useToast();
  const createMutation = useCreateProject();

  const validateForm = (): boolean => {
    const newErrors: { name?: string; path?: string } = {};

    // Name validation: 1-100 chars, alphanumeric + hyphens/underscores
    if (!name.trim()) {
      newErrors.name = 'Project name is required';
    } else if (name.length < 1 || name.length > 100) {
      newErrors.name = 'Name must be between 1 and 100 characters';
    } else if (!/^[a-zA-Z0-9_-]+$/.test(name)) {
      newErrors.name = 'Name can only contain letters, numbers, hyphens, and underscores';
    }

    // Path validation: must be absolute path
    if (!path.trim()) {
      newErrors.path = 'Project path is required';
    } else if (!path.startsWith('/')) {
      newErrors.path = 'Path must be an absolute path (starting with /)';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleCreate = async () => {
    if (!validateForm()) {
      return;
    }

    try {
      const requestBody: ProjectCreateRequest = {
        name: name.trim(),
        path: path.trim(),
        description: description.trim() || null,
      };

      const createdProject = await createMutation.mutateAsync(requestBody);

      toast({
        title: 'Project created',
        description: `Successfully created project "${name}"`,
      });

      // Reset form
      setName('');
      setPath('');
      setDescription('');
      setErrors({});

      // Close dialog and call success callback with created project
      onOpenChange(false);
      onSuccess?.(createdProject);
    } catch (error) {
      console.error('Failed to create project:', error);
      toast({
        title: 'Failed to create project',
        description: error instanceof Error ? error.message : 'An unexpected error occurred',
        variant: 'destructive',
      });
    }
  };

  const handleClose = () => {
    if (!createMutation.isPending) {
      setName('');
      setPath('');
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
              <Plus className="h-5 w-5 text-primary" />
            </div>
            <div>
              <DialogTitle>Create New Project</DialogTitle>
              <DialogDescription>
                Initialize a new project directory for artifact deployment
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Name Input */}
          <div className="space-y-2">
            <Label htmlFor="name">
              Project Name <span className="text-destructive">*</span>
            </Label>
            <Input
              id="name"
              placeholder="my-project"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                if (errors.name) {
                  setErrors((prev) => ({ ...prev, name: undefined }));
                }
              }}
              disabled={createMutation.isPending}
              className={errors.name ? 'border-destructive' : ''}
            />
            {errors.name && <p className="text-sm text-destructive">{errors.name}</p>}
            <p className="text-xs text-muted-foreground">
              Letters, numbers, hyphens, and underscores only
            </p>
          </div>

          {/* Path Input */}
          <div className="space-y-2">
            <Label htmlFor="path" className="flex items-center gap-2">
              <Folder className="h-4 w-4" />
              Project Path <span className="text-destructive">*</span>
            </Label>
            <Input
              id="path"
              placeholder="/home/user/projects/my-project"
              value={path}
              onChange={(e) => {
                setPath(e.target.value);
                if (errors.path) {
                  setErrors((prev) => ({ ...prev, path: undefined }));
                }
              }}
              disabled={createMutation.isPending}
              className={errors.path ? 'border-destructive' : ''}
            />
            {errors.path && <p className="text-sm text-destructive">{errors.path}</p>}
            <p className="text-xs text-muted-foreground">Absolute path to the project directory</p>
          </div>

          {/* Description Input */}
          <div className="space-y-2">
            <Label htmlFor="description">Description (Optional)</Label>
            <Textarea
              id="description"
              placeholder="Brief description of this project..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={createMutation.isPending}
              rows={3}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={createMutation.isPending}>
            Cancel
          </Button>
          <Button onClick={handleCreate} disabled={createMutation.isPending}>
            {createMutation.isPending ? 'Creating...' : 'Create Project'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
