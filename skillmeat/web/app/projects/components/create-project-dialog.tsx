'use client';

import { useState } from 'react';
import { Folder, Plus, Settings } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { useCreateProject, useToast } from '@/hooks';
import { createDeploymentProfile } from '@/lib/api/deployment-profiles';
import { Platform } from '@/types/enums';
import { PLATFORM_DEFAULTS } from '@/lib/constants/platform-defaults';
import { CreateProfileForm } from '@/components/profiles';
import type { ProjectCreateRequest } from '@/sdk';
import type { CreateDeploymentProfileRequest } from '@/types/deployments';

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

// EPP-P3-02: Ordered platform list derived from PLATFORM_DEFAULTS
const PLATFORM_ENTRIES = Object.entries(PLATFORM_DEFAULTS) as [string, (typeof PLATFORM_DEFAULTS)[string]][];

// EPP-P3-02: Human-readable platform names
const PLATFORM_LABELS: Record<string, string> = {
  claude_code: 'Claude Code',
  codex: 'Codex',
  gemini: 'Gemini',
  cursor: 'Cursor',
  other: 'Other',
};

// EPP-P3-04: Per-platform customize dialog state
interface CustomizeDialogState {
  open: boolean;
  platform: string | null;
}

export function CreateProjectDialog({ open, onOpenChange, onSuccess }: CreateProjectDialogProps) {
  const [name, setName] = useState('');
  const [path, setPath] = useState('');
  const [description, setDescription] = useState('');
  const [errors, setErrors] = useState<{
    name?: string;
    path?: string;
  }>({});

  // EPP-P3-03: Platform toggle state — Map<platformKey, CreateDeploymentProfileRequest>
  const [pendingProfiles, setPendingProfiles] = useState<
    Map<string, CreateDeploymentProfileRequest>
  >(new Map());

  // EPP-P3-05: Track which platforms have been customized
  const [customizedPlatforms, setCustomizedPlatforms] = useState<Set<string>>(new Set());

  // EPP-P3-04: Customize nested dialog state
  const [customizeDialog, setCustomizeDialog] = useState<CustomizeDialogState>({
    open: false,
    platform: null,
  });

  const { toast } = useToast();
  const createMutation = useCreateProject();

  const validateForm = (): boolean => {
    const newErrors: { name?: string; path?: string } = {};

    if (!name.trim()) {
      newErrors.name = 'Project name is required';
    } else if (name.length < 1 || name.length > 100) {
      newErrors.name = 'Name must be between 1 and 100 characters';
    } else if (!/^[a-zA-Z0-9_-]+$/.test(name)) {
      newErrors.name = 'Name can only contain letters, numbers, hyphens, and underscores';
    }

    if (!path.trim()) {
      newErrors.path = 'Project path is required';
    } else if (!path.startsWith('/')) {
      newErrors.path = 'Path must be an absolute path (starting with /)';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // EPP-P3-03: Toggle a platform on/off
  const handlePlatformToggle = (platformKey: string, enabled: boolean) => {
    setPendingProfiles((prev) => {
      const next = new Map(prev);
      if (enabled) {
        const defaults = PLATFORM_DEFAULTS[platformKey]!;
        const profileId = `${platformKey}-default`;
        next.set(platformKey, {
          profile_id: profileId,
          platform: platformKey as Platform,
          root_dir: defaults.root_dir,
          artifact_path_map: { ...defaults.artifact_path_map },
          project_config_filenames: [...defaults.config_filenames],
          context_path_prefixes: [...defaults.context_prefixes],
          supported_artifact_types: [...defaults.supported_artifact_types],
        });
      } else {
        next.delete(platformKey);
        // Remove from customized set if toggled off
        setCustomizedPlatforms((prev) => {
          const next = new Set(prev);
          next.delete(platformKey);
          return next;
        });
      }
      return next;
    });
  };

  // EPP-P3-05: Update pending profile after customization
  const updatePendingProfile = (platformKey: string, data: CreateDeploymentProfileRequest) => {
    setPendingProfiles((prev) => {
      const next = new Map(prev);
      next.set(platformKey, data);
      return next;
    });
    setCustomizedPlatforms((prev) => new Set(prev).add(platformKey));
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

      // EPP-P3-06: Post pending profiles after project creation (non-fatal on failure)
      if (pendingProfiles.size > 0 && createdProject?.id) {
        const profileEntries = Array.from(pendingProfiles.entries());
        const profileResults = await Promise.allSettled(
          profileEntries.map(([, profileData]) =>
            createDeploymentProfile(createdProject.id, profileData)
          )
        );

        const failedProfiles = profileResults
          .map((result, i) => ({ result, platform: profileEntries[i]?.[0] ?? '' }))
          .filter(({ result }) => result.status === 'rejected');

        if (failedProfiles.length > 0) {
          const platformNames = failedProfiles
            .map(({ platform }) => PLATFORM_LABELS[platform] ?? platform)
            .join(', ');
          toast({
            title: 'Warning: Some profiles could not be created',
            description: `Profile creation failed for: ${platformNames}. You can add them later in project settings.`,
            variant: 'destructive',
          });
        }
      }

      // Reset form
      resetForm();

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

  const resetForm = () => {
    setName('');
    setPath('');
    setDescription('');
    setErrors({});
    setPendingProfiles(new Map());
    setCustomizedPlatforms(new Set());
  };

  const handleClose = () => {
    if (!createMutation.isPending) {
      resetForm();
      onOpenChange(false);
    }
  };

  const openCustomizeDialog = (platform: string) => {
    setCustomizeDialog({ open: true, platform });
  };

  const closeCustomizeDialog = () => {
    setCustomizeDialog({ open: false, platform: null });
  };

  const activePlatform = customizeDialog.platform;
  const activePlatformDefaults = activePlatform ? pendingProfiles.get(activePlatform) : undefined;

  return (
    <>
      <Dialog open={open} onOpenChange={handleClose}>
        <DialogContent className="sm:max-w-[540px]">
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

            {/* EPP-P3-01: Platform Profiles accordion */}
            <Accordion type="single" collapsible className="w-full">
              <AccordionItem value="platform-profiles" className="border rounded-md px-3">
                <AccordionTrigger className="py-3 text-sm font-medium hover:no-underline">
                  <div className="flex items-center gap-2">
                    <Settings className="h-4 w-4 text-muted-foreground" />
                    <span>Platform Profiles</span>
                    {pendingProfiles.size > 0 && (
                      <Badge variant="secondary" className="ml-1 h-5 px-1.5 text-xs">
                        {pendingProfiles.size}
                      </Badge>
                    )}
                  </div>
                </AccordionTrigger>
                <AccordionContent className="pb-3">
                  <p className="mb-3 text-xs text-muted-foreground">
                    Enable platforms to automatically create deployment profiles for this project.
                  </p>
                  {/* EPP-P3-02: Platform toggle cards */}
                  <div className="space-y-2" role="list" aria-label="Platform profiles">
                    {PLATFORM_ENTRIES.map(([platformKey]) => {
                      const isEnabled = pendingProfiles.has(platformKey);
                      const isCustomized = customizedPlatforms.has(platformKey);
                      const label = PLATFORM_LABELS[platformKey] ?? platformKey;

                      return (
                        <div
                          key={platformKey}
                          role="listitem"
                          className="flex items-center gap-3 rounded-md border bg-card px-3 py-2"
                        >
                          <Switch
                            id={`platform-toggle-${platformKey}`}
                            checked={isEnabled}
                            onCheckedChange={(checked) =>
                              handlePlatformToggle(platformKey, checked)
                            }
                            aria-label={`Enable ${label} platform profile`}
                            disabled={createMutation.isPending}
                          />
                          <Label
                            htmlFor={`platform-toggle-${platformKey}`}
                            className="flex-1 cursor-pointer text-sm font-medium"
                          >
                            {label}
                          </Label>
                          {/* EPP-P3-05: Customized indicator */}
                          {isCustomized && (
                            <Badge
                              variant="outline"
                              className="h-5 px-1.5 text-xs text-muted-foreground"
                            >
                              Customized
                            </Badge>
                          )}
                          {/* EPP-P3-02: Customize button */}
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            disabled={!isEnabled || createMutation.isPending}
                            onClick={() => openCustomizeDialog(platformKey)}
                            aria-label={`Customize ${label} profile`}
                            className="h-7 px-2 text-xs"
                          >
                            Customize
                          </Button>
                        </div>
                      );
                    })}
                  </div>
                </AccordionContent>
              </AccordionItem>
            </Accordion>
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

      {/* EPP-P3-04: Nested customize dialog */}
      {activePlatform && (
        <Dialog open={customizeDialog.open} onOpenChange={(o) => !o && closeCustomizeDialog()}>
          <DialogContent className="sm:max-w-[600px]">
            <DialogHeader>
              <DialogTitle>
                Customize {PLATFORM_LABELS[activePlatform] ?? activePlatform} Profile
              </DialogTitle>
              <DialogDescription>
                Configure the deployment profile for{' '}
                {PLATFORM_LABELS[activePlatform] ?? activePlatform}. Settings will be applied when
                the project is created.
              </DialogDescription>
            </DialogHeader>
            <div className="py-2">
              <CreateProfileForm
                contextMode="page"
                platformLock={activePlatform as Platform}
                defaultValues={activePlatformDefaults}
                onSubmit={(data) => {
                  updatePendingProfile(activePlatform, data);
                  closeCustomizeDialog();
                }}
                onCancel={closeCustomizeDialog}
              />
            </div>
          </DialogContent>
        </Dialog>
      )}
    </>
  );
}
