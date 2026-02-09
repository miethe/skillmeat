'use client';

import { useState } from 'react';
import { Upload, Folder, AlertTriangle, FileText, Loader2 } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import type { ContextEntity } from '@/types/context-entity';
import { ProfileSelector } from '@/components/profile-selector';
import {
  useProjects,
  useDeployContextEntity,
  useToast,
  useDeploymentProfiles,
  useProfileSelector,
} from '@/hooks';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';

export interface DeployToProjectDialogProps {
  entity: ContextEntity | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

/**
 * Dialog for deploying context entities to projects
 *
 * Allows users to select a project and deploy a context entity to the appropriate
 * path within the project's .claude directory. Shows preview of target path and
 * overwrite warnings.
 */
export function DeployToProjectDialog({
  entity,
  open,
  onOpenChange,
  onSuccess,
}: DeployToProjectDialogProps) {
  const [selectedProject, setSelectedProject] = useState<string>('');
  const [forceDeploy, setForceDeploy] = useState(false);

  // Real hooks for projects and deployment
  const { data: projects, isLoading: projectsLoading, error: projectsError } = useProjects();
  const deployEntity = useDeployContextEntity();
  const { data: deploymentProfiles } = useDeploymentProfiles(selectedProject || undefined);
  const { selectedProfileId, setSelectedProfileId, allProfiles, setAllProfiles } =
    useProfileSelector('claude_code');
  const { toast } = useToast();

  const isDeploying = deployEntity.isPending;

  const selectedProfile = deploymentProfiles?.find((p) => p.profile_id === selectedProfileId);
  const hasPlatformMismatch =
    !allProfiles &&
    !!selectedProfile &&
    !!entity?.target_platforms?.length &&
    !entity.target_platforms.includes(selectedProfile.platform);

  const rewritePathForProfilePreview = (pathPattern: string, rootDir?: string): string => {
    if (!rootDir) return pathPattern;
    const knownRoots = ['.claude', '.codex', '.gemini', '.cursor'];
    for (const root of knownRoots) {
      const prefix = `${root}/`;
      if (pathPattern.startsWith(prefix)) {
        return `${rootDir.replace(/\/$/, '')}/${pathPattern.slice(prefix.length)}`;
      }
    }
    return pathPattern;
  };

  // Compute target path based on selected project and entity path pattern
  const getTargetPath = () => {
    if (!selectedProject || !entity || !projects) return null;
    const project = projects.find((p) => p.id === selectedProject);
    if (!project) return null;
    if (allProfiles) return `${project.path}/<profile-root>/${entity.path_pattern}`;
    const profileRoot = selectedProfile?.root_dir;
    const effectivePattern = rewritePathForProfilePreview(entity.path_pattern, profileRoot);
    return `${project.path}/${effectivePattern}`;
  };

  const targetPath = getTargetPath();

  const handleDeploy = async () => {
    if (!entity || !selectedProject || !projects) return;
    const project = projects.find((p) => p.id === selectedProject);
    if (!project) return;

    try {
      await deployEntity.mutateAsync({
        id: entity.id,
        data: {
          project_path: project.path,
          deployment_profile_id: allProfiles ? undefined : selectedProfileId || undefined,
          all_profiles: allProfiles,
          force: forceDeploy,
        },
      });

      // Show success and close
      onSuccess?.();
      handleClose();
    } catch (error) {
      console.error('Deploy failed:', error);
      toast({
        title: 'Deploy Failed',
        description: error instanceof Error ? error.message : 'Failed to deploy context entity',
        variant: 'destructive',
      });
    }
  };

  const handleClose = () => {
    if (!isDeploying) {
      onOpenChange(false);
      // Reset state
      setSelectedProject('');
      setSelectedProfileId('claude_code');
      setAllProfiles(false);
      setForceDeploy(false);
    }
  };

  if (!entity) return null;

  return (
    <Dialog open={open} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-primary/10 p-2">
              <Upload className="h-5 w-5 text-primary" />
            </div>
            <div>
              <DialogTitle>Deploy Context Entity</DialogTitle>
              <DialogDescription>Deploy {entity.name} to a project</DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Entity Info Summary */}
          <div className="space-y-2 rounded-lg border p-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Entity</span>
              <span className="font-medium">{entity.name}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Type</span>
              <Badge variant="secondary" className="capitalize">
                {entity.entity_type?.replace('_', ' ') || 'Unknown'}
              </Badge>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Path Pattern</span>
              <code className="rounded bg-muted px-2 py-1 text-xs">{entity.path_pattern}</code>
            </div>
            {entity.category && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Category</span>
                <Badge variant="outline">{entity.category}</Badge>
              </div>
            )}
          </div>

          {/* Project Selector */}
          <div className="space-y-2">
            <label htmlFor="project" className="flex items-center gap-2 text-sm font-medium">
              <Folder className="h-4 w-4" aria-hidden="true" />
              Target Project
            </label>

            {projectsLoading ? (
              <div className="flex items-center gap-2 rounded-md border p-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading projects...
              </div>
            ) : projectsError ? (
              <div className="rounded-md border border-destructive/50 bg-destructive/10 p-2 text-sm text-destructive">
                Failed to load projects
              </div>
            ) : (
              <Select
                value={selectedProject}
                onValueChange={setSelectedProject}
                disabled={isDeploying || !projects || projects.length === 0}
              >
                <SelectTrigger id="project" aria-label="Select target project for deployment">
                  <SelectValue
                    placeholder={
                      projects && projects.length === 0 ? 'No projects found' : 'Select a project'
                    }
                  />
                </SelectTrigger>
                <SelectContent>
                  {projects?.map((project) => (
                    <SelectItem key={project.id} value={project.id}>
                      {project.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
            <p className="text-xs text-muted-foreground">
              The entity will be deployed to the selected deployment profile root
            </p>
          </div>

          {selectedProject && (
            <ProfileSelector
              profiles={deploymentProfiles}
              value={selectedProfileId}
              onValueChange={setSelectedProfileId}
              allProfiles={allProfiles}
              onAllProfilesChange={setAllProfiles}
              disabled={isDeploying}
            />
          )}

          {/* Target Path Preview */}
          {targetPath && (
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm font-medium">
                <FileText className="h-4 w-4" />
                Target Path
              </label>
              <div className="rounded-lg bg-muted p-3">
                <code className="break-all text-xs">{targetPath}</code>
              </div>
            </div>
          )}

          {hasPlatformMismatch && (
            <Alert className="border-destructive/40 bg-destructive/10">
              <AlertTriangle className="h-4 w-4 text-destructive" />
              <AlertTitle>Platform Target Mismatch</AlertTitle>
              <AlertDescription className="space-y-2">
                <p>
                  This entity targets {entity.target_platforms?.join(', ')}, but selected profile
                  platform is {selectedProfile?.platform}.
                </p>
                <div className="flex items-center gap-2">
                  <Switch
                    id="force-context-deploy"
                    checked={forceDeploy}
                    onCheckedChange={setForceDeploy}
                  />
                  <Label htmlFor="force-context-deploy">Force deploy anyway</Label>
                </div>
              </AlertDescription>
            </Alert>
          )}

          {/* Overwrite Warning */}
          {selectedProject && (
            <Alert className="border-yellow-500/50 bg-yellow-500/10">
              <AlertTriangle className="h-4 w-4 text-yellow-600" />
              <AlertTitle className="text-yellow-900 dark:text-yellow-100">
                Overwrite Warning
              </AlertTitle>
              <AlertDescription className="text-yellow-800 dark:text-yellow-200">
                If a file already exists at the target path, it will be overwritten. Make sure to
                back up any existing files before deploying.
              </AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={handleClose}
            disabled={isDeploying}
            aria-label="Cancel deployment"
          >
            Cancel
          </Button>
          <Button
            onClick={handleDeploy}
            disabled={!selectedProject || isDeploying || (hasPlatformMismatch && !forceDeploy)}
            aria-label={
              isDeploying
                ? 'Deploying entity to project'
                : `Deploy ${entity.name} to selected project`
            }
          >
            {isDeploying ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Deploying...
              </>
            ) : (
              'Deploy'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
