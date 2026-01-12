'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Settings, Trash2, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useProject, useUpdateProject, useToast } from '@/hooks';
import { DeleteProjectDialog } from '../../components/delete-project-dialog';
import type { ProjectUpdateRequest } from '@/sdk';

export default function ProjectSettingsPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;

  const { data: project, isLoading, error } = useProject(projectId);
  const updateMutation = useUpdateProject();
  const { toast } = useToast();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [errors, setErrors] = useState<{ name?: string }>({});
  const [hasChanges, setHasChanges] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);

  // Initialize form when project loads
  useState(() => {
    if (project) {
      setName(project.name);
      setDescription('');
    }
  });

  const validateForm = (): boolean => {
    const newErrors: { name?: string } = {};

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

  const handleNameChange = (value: string) => {
    setName(value);
    setHasChanges(value !== project?.name || description.trim() !== '');
    if (errors.name) {
      setErrors((prev) => ({ ...prev, name: undefined }));
    }
  };

  const handleDescriptionChange = (value: string) => {
    setDescription(value);
    setHasChanges(name !== project?.name || value.trim() !== '');
  };

  const handleSave = async () => {
    if (!project || !validateForm()) {
      return;
    }

    if (!hasChanges) {
      toast({
        title: 'No changes',
        description: 'No changes were made to the project',
      });
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
        title: 'Settings saved',
        description: `Successfully updated project "${name}"`,
      });

      setHasChanges(false);
    } catch (error) {
      console.error('Failed to update project:', error);
      toast({
        title: 'Failed to save settings',
        description: error instanceof Error ? error.message : 'An unexpected error occurred',
        variant: 'destructive',
      });
    }
  };

  const handleDeleteSuccess = () => {
    router.push('/projects');
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" onClick={() => router.back()}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <Card>
          <CardContent className="pt-6">
            <div className="animate-pulse space-y-4">
              <div className="h-8 w-1/3 rounded bg-muted" />
              <div className="h-4 w-1/2 rounded bg-muted" />
              <div className="h-32 rounded bg-muted" />
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" onClick={() => router.back()}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-destructive">
              <p>Failed to load project settings. Please try again.</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-4xl space-y-6">
      {/* Header */}
      <div className="space-y-4">
        <Button variant="ghost" onClick={() => router.back()}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>

        <div className="flex items-center gap-3">
          <Settings className="h-8 w-8 text-muted-foreground" />
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Project Settings</h1>
            <p className="text-sm text-muted-foreground">{project.name}</p>
          </div>
        </div>
      </div>

      {/* General Settings */}
      <Card>
        <CardHeader>
          <CardTitle>General</CardTitle>
          <CardDescription>Configure basic project information and metadata</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Project Path (Read-only) */}
          <div className="space-y-2">
            <Label>Project Path</Label>
            <div className="rounded-md bg-muted px-3 py-2 font-mono text-sm text-muted-foreground">
              {project.path}
            </div>
            <p className="text-xs text-muted-foreground">Path cannot be changed after creation</p>
          </div>

          {/* Project ID (Read-only) */}
          <div className="space-y-2">
            <Label>Project ID</Label>
            <div className="break-all rounded-md bg-muted px-3 py-2 font-mono text-sm text-muted-foreground">
              {project.id}
            </div>
          </div>

          {/* Name Input */}
          <div className="space-y-2">
            <Label htmlFor="settings-name">
              Project Name <span className="text-destructive">*</span>
            </Label>
            <Input
              id="settings-name"
              placeholder="my-project"
              value={name}
              onChange={(e) => handleNameChange(e.target.value)}
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
            <Label htmlFor="settings-description">Description (Optional)</Label>
            <Textarea
              id="settings-description"
              placeholder="Brief description of this project..."
              value={description}
              onChange={(e) => handleDescriptionChange(e.target.value)}
              disabled={updateMutation.isPending}
              rows={3}
            />
          </div>

          {/* Save Button */}
          <div className="flex justify-end pt-4">
            <Button onClick={handleSave} disabled={!hasChanges || updateMutation.isPending}>
              {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Statistics Card */}
      <Card>
        <CardHeader>
          <CardTitle>Project Statistics</CardTitle>
          <CardDescription>Overview of deployments and artifact usage</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Total Deployments</p>
              <p className="text-2xl font-bold">{project.deployment_count}</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Modified Artifacts</p>
              <p className="text-2xl font-bold">{project.stats.modified_count}</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Last Deployment</p>
              <p className="text-lg font-semibold">
                {project.last_deployment
                  ? new Date(project.last_deployment).toLocaleDateString()
                  : 'Never'}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Danger Zone */}
      <Card className="border-destructive">
        <CardHeader>
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            <CardTitle className="text-destructive">Danger Zone</CardTitle>
          </div>
          <CardDescription>
            Irreversible actions that can permanently affect this project
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-start justify-between rounded-lg border border-destructive/50 bg-destructive/5 p-4">
            <div className="flex-1">
              <h3 className="mb-1 text-sm font-semibold">Delete this project</h3>
              <p className="text-sm text-muted-foreground">
                Once you delete a project, it will be removed from SkillMeat tracking. This action
                cannot be undone.
              </p>
            </div>
            <Button
              variant="destructive"
              onClick={() => setIsDeleteOpen(true)}
              className="ml-4 flex-shrink-0"
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete Project
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Delete Dialog */}
      <DeleteProjectDialog
        project={project}
        open={isDeleteOpen}
        onOpenChange={setIsDeleteOpen}
        onSuccess={handleDeleteSuccess}
      />
    </div>
  );
}
