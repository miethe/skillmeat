'use client';

import { useState, useEffect, useMemo } from 'react';
import { Upload, Folder, AlertTriangle, Plus, Check } from 'lucide-react';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ProgressIndicator, ProgressStep } from './progress-indicator';
import { useDeployArtifact } from '@/hooks/use-deployments';
import type { ArtifactDeployRequest } from '@/types/deployments';
import { useProjects } from '@/hooks/useProjects';
import { CreateProjectDialog } from '@/app/projects/components/create-project-dialog';
import type { Artifact } from '@/types/artifact';

const CUSTOM_PATH_VALUE = '__custom__';

export interface DeployDialogProps {
  artifact: Artifact | null;
  existingDeploymentPaths?: string[];
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export function DeployDialog({ artifact, existingDeploymentPaths, isOpen, onClose, onSuccess }: DeployDialogProps) {
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [customPath, setCustomPath] = useState('');
  const [showCreateProject, setShowCreateProject] = useState(false);
  const [overwrite, setOverwrite] = useState(false);
  const [isDeploying, setIsDeploying] = useState(false);
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [initialSteps] = useState<ProgressStep[]>([
    { step: 'Validating artifact', status: 'pending' },
    { step: 'Checking project path', status: 'pending' },
    { step: 'Copying files', status: 'pending' },
    { step: 'Updating deployment registry', status: 'pending' },
  ]);

  const { data: projects, isLoading: projectsLoading } = useProjects();

  // Determine if using custom path mode
  const useCustomPath = selectedProjectId === CUSTOM_PATH_VALUE;

  // Get selected project object
  const selectedProject = selectedProjectId && !useCustomPath
    ? projects?.find((p) => p.id === selectedProjectId)
    : null;

  // Get the effective path for deployment
  const effectivePath = useCustomPath ? customPath : (selectedProject?.path || '');

  // Check if artifact is already deployed to a project
  const isAlreadyDeployed = (projectPath: string): boolean => {
    if (!Array.isArray(existingDeploymentPaths)) return false;
    // Check if any deployment path starts with this project path
    return existingDeploymentPaths.some(
      deployPath => deployPath.startsWith(projectPath + '/.claude/') ||
                    deployPath.startsWith(projectPath + '/')
    );
  };

  // Check if current selection is valid for deployment
  const canDeploy = useMemo(() => {
    if (!selectedProjectId) return false;

    if (useCustomPath) {
      // Custom path is valid if not empty
      return customPath.trim().length > 0;
    }

    // For project selection, check if not already deployed
    if (selectedProject) {
      return !isAlreadyDeployed(selectedProject.path);
    }

    return false;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProjectId, useCustomPath, customPath, selectedProject, existingDeploymentPaths]);

  // Reset selection when dialog opens for a new artifact
  useEffect(() => {
    if (isOpen) {
      setSelectedProjectId(null);
      setCustomPath('');
      setOverwrite(false);
    }
  }, [isOpen, artifact?.id]);

  const deployMutation = useDeployArtifact();

  const handleDeploy = async () => {
    if (!artifact) return;

    setIsDeploying(true);

    try {
      await deployMutation.mutateAsync({
        artifact_id: `${artifact.type}:${artifact.name}`,
        artifact_name: artifact.name,
        artifact_type: artifact.type,
        project_path: effectivePath || undefined,
        overwrite,
      });
      // Deployment successful
      handleComplete(true);
    } catch (error) {
      console.error('Deploy failed:', error);
      setIsDeploying(false);
    }
  };

  const handleProjectCreated = (newProject?: { id: string; path: string; name: string }) => {
    // Select the newly created project if provided
    if (newProject) {
      setSelectedProjectId(newProject.id);
    }
    setShowCreateProject(false);
  };

  const handleComplete = (success: boolean) => {
    setIsDeploying(false);

    if (success) {
      setTimeout(() => {
        onSuccess?.();
        onClose();
        // Reset state
        setSelectedProjectId(null);
        setCustomPath('');
        setOverwrite(false);
        setStreamUrl(null);
      }, 1500);
    }
  };

  const handleClose = () => {
    if (!isDeploying) {
      onClose();
      // Reset state
      setSelectedProjectId(null);
      setCustomPath('');
      setOverwrite(false);
      setStreamUrl(null);
      setIsDeploying(false);
    }
  };

  if (!artifact) return null;

  return (
    <>
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-primary/10 p-2">
              <Upload className="h-5 w-5 text-primary" />
            </div>
            <div>
              <DialogTitle>Deploy Artifact</DialogTitle>
              <DialogDescription>Deploy {artifact.name} to a project</DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {!isDeploying ? (
            <>
              {/* Artifact Info */}
              <div className="space-y-2 rounded-lg border p-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Artifact</span>
                  <span className="font-medium">{artifact.name}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Type</span>
                  <span className="font-medium capitalize">{artifact.type}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Version</span>
                  <code className="rounded bg-muted px-2 py-1 text-xs">
                    {artifact.version || 'N/A'}
                  </code>
                </div>
              </div>

              {/* Project Selector */}
              <div className="space-y-2">
                <label className="flex items-center gap-2 text-sm font-medium">
                  <Folder className="h-4 w-4" />
                  Target Project
                </label>
                <div className="flex gap-2">
                  <Select
                    value={selectedProjectId || ''}
                    onValueChange={(value) => setSelectedProjectId(value || null)}
                    disabled={isDeploying || projectsLoading}
                  >
                    <SelectTrigger className="flex-1" aria-label="Select target project">
                      <SelectValue placeholder={projectsLoading ? 'Loading projects...' : 'Select a project...'} />
                    </SelectTrigger>
                    <SelectContent>
                      {projects && projects.length > 0 ? (
                        <>
                          {projects.map((project) => {
                            const deployed = isAlreadyDeployed(project.path);
                            return (
                              <SelectItem key={project.id} value={project.id}>
                                <div className="flex items-center gap-2">
                                  {deployed && (
                                    <Check className="h-4 w-4 flex-shrink-0 text-green-500" />
                                  )}
                                  <div className="flex flex-col">
                                    <span className={deployed ? 'text-muted-foreground' : ''}>
                                      {project.name}
                                    </span>
                                    <span className="text-xs text-muted-foreground truncate max-w-[280px]">
                                      {project.path}
                                    </span>
                                  </div>
                                </div>
                              </SelectItem>
                            );
                          })}
                          <SelectSeparator />
                        </>
                      ) : !projectsLoading ? (
                        <div className="px-2 py-1.5 text-sm text-muted-foreground">
                          No projects found
                        </div>
                      ) : null}
                      <SelectItem value={CUSTOM_PATH_VALUE}>
                        <span className="text-muted-foreground">Custom path...</span>
                      </SelectItem>
                    </SelectContent>
                  </Select>
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={() => setShowCreateProject(true)}
                    disabled={isDeploying}
                    aria-label="Add new project"
                  >
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
                {selectedProject && (
                  <div>
                    <p className="text-xs text-muted-foreground">
                      Deploy to: {selectedProject.path}
                    </p>
                    {isAlreadyDeployed(selectedProject.path) && (
                      <p className="text-xs text-yellow-600">
                        Artifact is already deployed to this project
                      </p>
                    )}
                  </div>
                )}
              </div>

              {/* Custom Path Input (shown when "Custom path..." is selected) */}
              {useCustomPath && (
                <div className="space-y-2">
                  <label
                    htmlFor="customPath"
                    className="text-sm font-medium"
                  >
                    Custom Path
                  </label>
                  <Input
                    id="customPath"
                    placeholder="/path/to/project"
                    value={customPath}
                    onChange={(e) => setCustomPath(e.target.value)}
                    disabled={isDeploying}
                  />
                  <p className="text-xs text-muted-foreground">
                    The artifact will be deployed to the .claude directory in this path
                  </p>
                </div>
              )}

              {/* Overwrite Warning */}
              {artifact.usageStats.totalDeployments > 0 && (
                <div className="rounded-lg border border-yellow-500/50 bg-yellow-500/10 p-3">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-yellow-600" />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-yellow-900 dark:text-yellow-100">
                        Existing Deployments
                      </p>
                      <p className="mt-1 text-xs text-yellow-800 dark:text-yellow-200">
                        This artifact is already deployed to {artifact.usageStats.totalDeployments}{' '}
                        project(s). If the target project already has this artifact, it will be
                        overwritten.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : (
            <>
              {/* Progress Indicator */}
              <ProgressIndicator
                streamUrl={streamUrl}
                enabled={isDeploying}
                initialSteps={initialSteps}
                onComplete={handleComplete}
                onError={(error) => {
                  console.error('Deploy error:', error);
                  setIsDeploying(false);
                }}
              />
            </>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isDeploying}>
            Cancel
          </Button>
          <Button onClick={handleDeploy} disabled={isDeploying || deployMutation.isPending || !canDeploy}>
            {isDeploying ? 'Deploying...' : 'Deploy'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    {/* Create Project Dialog */}
    <CreateProjectDialog
      open={showCreateProject}
      onOpenChange={setShowCreateProject}
      onSuccess={handleProjectCreated}
    />
    </>
  );
}
